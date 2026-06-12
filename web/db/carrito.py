# -*- coding: utf-8 -*-
"""Carrito persistente por usuario — extraído de web/database.py (refactor jun 2026)."""
import hashlib
import json
import os
import re as _re
import secrets
import shutil
import sqlite3
from datetime import datetime as _dt
from pathlib import Path
from typing import Optional, Dict, List, Any

import bcrypt as _bcrypt

from web.db.core import (
    BASE_DIR, DB_PATH, CONFIG_PATH, _CONFIG_RAIZ, CONFIG_DEFECTO,
    _add_column_if_missing, _crear_usuario, _hash_password,
)

# ─────────────────────────────────────────────
# Carrito persistente
# ─────────────────────────────────────────────

def get_carrito_db(username: str) -> List[Dict]:
    """Devuelve los items del carrito del usuario desde SQLite."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM carrito_items WHERE username=? ORDER BY COALESCE(posicion, id)",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_item_carrito_db(username: str, item: Dict, tapa_para_id: Optional[int] = None) -> int:
    """Inserta un item en el carrito. Retorna el id generado."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    # Determinar posicion: siguiente entero después del máximo actual (solo cuerpos)
    max_pos = c.execute(
        "SELECT COALESCE(MAX(COALESCE(posicion, id)), 0) FROM carrito_items WHERE username=? AND tapa_para_id IS NULL",
        (username,),
    ).fetchone()[0]
    if tapa_para_id is not None:
        # Tapa: posicion = posicion del cuerpo + 0.5
        cuerpo_pos = c.execute(
            "SELECT COALESCE(posicion, id) FROM carrito_items WHERE id=?",
            (tapa_para_id,),
        ).fetchone()
        new_pos = float(cuerpo_pos[0]) + 0.5 if cuerpo_pos else float(int(max_pos) + 1)
    else:
        new_pos = float(int(max_pos) + 1)
    c.execute(
        """INSERT INTO carrito_items
           (username, tipo, descripcion, precio_unitario, peso_unitario,
            cantidad, unidad, tipo_galvanizado, porcentaje_ganancia, descripcion_calculada,
            posicion, tapa_para_id, precio_manual)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            username,
            item.get("tipo", ""),
            item.get("descripcion", ""),
            item.get("precio_unitario", 0),
            item.get("peso_unitario", 0),
            item.get("cantidad", 1),
            item.get("unidad", "UND"),
            item.get("tipo_galvanizado", "GO"),
            item.get("porcentaje_ganancia", "30"),
            item.get("descripcion_calculada") or None,
            new_pos,
            tapa_para_id,
            1 if item.get("precio_manual") else 0,
        ),
    )
    item_id = c.lastrowid
    conn.commit()
    conn.close()
    return item_id


def update_cantidad_carrito_db(item_id: int, username: str, cantidad: float) -> bool:
    """Actualiza la cantidad de un item. Retorna True si se actualizó."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        "UPDATE carrito_items SET cantidad=? WHERE id=? AND username=?",
        (cantidad, item_id, username),
    )
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_item_precio_carrito_db(
    item_id: int, username: str,
    precio_unitario: float, peso_unitario: float,
    descripcion: str, descripcion_calculada: Optional[str] = None,
) -> bool:
    """Actualiza precio, peso y descripción de un item del carrito.
    Si se pasa descripcion_calculada, actualiza ese campo en vez de descripcion.
    Siempre resetea precio_manual a 0 (precio recalculado automáticamente)."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    if descripcion_calculada is not None:
        c.execute(
            "UPDATE carrito_items SET precio_unitario=?, peso_unitario=?, descripcion_calculada=?, precio_manual=0 WHERE id=? AND username=?",
            (round(precio_unitario, 4), round(peso_unitario, 6), descripcion_calculada, item_id, username),
        )
    else:
        c.execute(
            "UPDATE carrito_items SET precio_unitario=?, peso_unitario=?, descripcion=?, precio_manual=0 WHERE id=? AND username=?",
            (round(precio_unitario, 4), round(peso_unitario, 6), descripcion, item_id, username),
        )
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_item_campos_carrito_db(
    item_id: int, username: str,
    descripcion: str, unidad: str,
    precio_unitario: float, descripcion_calculada: Optional[str] = None,
) -> bool:
    """Actualiza descripción, unidad, precio y opcionalmente descripcion_calculada de un item."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        """UPDATE carrito_items
           SET descripcion=?, unidad=?, precio_unitario=?, descripcion_calculada=?
           WHERE id=? AND username=?""",
        (descripcion, unidad, round(precio_unitario, 4),
         descripcion_calculada or None, item_id, username),
    )
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_item_carrito_db(item_id: int, username: str) -> bool:
    """Elimina un item del carrito. Retorna True si se eliminó."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        "DELETE FROM carrito_items WHERE id=? AND username=?",
        (item_id, username),
    )
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def clear_carrito_db(username: str):
    """Vacía todo el carrito del usuario."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("DELETE FROM carrito_items WHERE username=?", (username,))
    conn.commit()
    conn.close()


def mover_item_carrito_db(item_id: int, username: str, direccion: str) -> bool:
    """Mueve un item cuerpo arriba o abajo en el carrito. Las tapas vinculadas se mueven junto."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    # Solo cuerpos (no tapas separadas)
    cuerpos = conn.execute(
        """SELECT id, COALESCE(posicion, id) AS pos FROM carrito_items
           WHERE username=? AND tapa_para_id IS NULL ORDER BY COALESCE(posicion, id)""",
        (username,),
    ).fetchall()
    cuerpos = [(r["id"], r["pos"]) for r in cuerpos]

    idx = next((i for i, (cid, _) in enumerate(cuerpos) if cid == item_id), None)
    if idx is None:
        conn.close()
        return False
    if direccion == "arriba" and idx == 0:
        conn.close()
        return False
    if direccion == "abajo" and idx == len(cuerpos) - 1:
        conn.close()
        return False

    target_idx = idx - 1 if direccion == "arriba" else idx + 1
    cur_id, cur_pos = cuerpos[idx]
    tgt_id, tgt_pos = cuerpos[target_idx]

    c = conn.cursor()
    # Swap posicion de los dos cuerpos
    c.execute("UPDATE carrito_items SET posicion=? WHERE id=? AND username=?", (tgt_pos, cur_id, username))
    c.execute("UPDATE carrito_items SET posicion=? WHERE id=? AND username=?", (cur_pos, tgt_id, username))
    # Actualizar tapas vinculadas a cada cuerpo
    c.execute("UPDATE carrito_items SET posicion=? WHERE tapa_para_id=? AND username=?", (tgt_pos + 0.5, cur_id, username))
    c.execute("UPDATE carrito_items SET posicion=? WHERE tapa_para_id=? AND username=?", (cur_pos + 0.5, tgt_id, username))
    conn.commit()
    conn.close()
    return True


def reordenar_carrito_db(username: str, ids_ordenados: list) -> bool:
    """Establece la posición de los cuerpos según el orden indicado. Las tapas siguen a su cuerpo."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    for idx, item_id in enumerate(ids_ordenados):
        posicion = (idx + 1) * 10
        c.execute(
            "UPDATE carrito_items SET posicion=? WHERE id=? AND username=? AND tapa_para_id IS NULL",
            (posicion, item_id, username),
        )
        c.execute(
            "UPDATE carrito_items SET posicion=? WHERE tapa_para_id=? AND username=?",
            (posicion + 0.5, item_id, username),
        )
    conn.commit()
    conn.close()
    return True


def update_item_completo_carrito_db(
    item_id: int, username: str,
    descripcion: str, unidad: str,
    precio_unitario: float, peso_unitario: float,
    tipo_galvanizado: str, porcentaje_ganancia: str,
    descripcion_calculada: Optional[str] = None,
    precio_manual: bool = False,
) -> bool:
    """Actualiza todos los campos calculables de un item."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        """UPDATE carrito_items
           SET descripcion=?, unidad=?, precio_unitario=?, peso_unitario=?,
               tipo_galvanizado=?, porcentaje_ganancia=?, descripcion_calculada=?,
               precio_manual=?
           WHERE id=? AND username=?""",
        (descripcion, unidad, round(precio_unitario, 4), round(peso_unitario, 6),
         tipo_galvanizado, porcentaje_ganancia,
         descripcion_calculada or None, 1 if precio_manual else 0,
         item_id, username),
    )
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def cargar_cotizacion_al_carrito_db(cotizacion_id: int, username: str, require_ownership: bool = True) -> Optional[Dict]:
    """
    Limpia el carrito del usuario y copia los items de una cotización guardada.
    Devuelve los metadatos de la cotización para pre-llenar el formulario del carrito.
    Si require_ownership=False (admin), permite cargar cualquier cotización.
    Retorna None si la cotización no existe o (con require_ownership=True) no pertenece al usuario.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row

    if require_ownership:
        row = conn.execute(
            "SELECT * FROM cotizaciones WHERE id=? AND username=?",
            (cotizacion_id, username),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM cotizaciones WHERE id=?",
            (cotizacion_id,),
        ).fetchone()
    if not row:
        conn.close()
        return None

    # Limpiar carrito actual
    conn.execute("DELETE FROM carrito_items WHERE username=?", (username,))

    # Copiar items de cotizacion_items → carrito_items
    items = conn.execute(
        "SELECT * FROM cotizacion_items WHERE cotizacion_id=? ORDER BY id",
        (cotizacion_id,),
    ).fetchall()
    for item in items:
        conn.execute(
            """INSERT INTO carrito_items
               (username, tipo, descripcion, precio_unitario, peso_unitario,
                cantidad, unidad, tipo_galvanizado, porcentaje_ganancia, precio_manual)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                username, item["tipo"], item["descripcion"],
                item["precio_unitario"], item["peso_unitario"],
                item["cantidad"], item["unidad"],
                item["tipo_galvanizado"], item["porcentaje_ganancia"],
                item["precio_manual"] if "precio_manual" in item.keys() else 0,
            ),
        )
    conn.commit()

    meta = {
        "id": row["id"],
        "cliente": row["cliente"],
        "cliente_nombre": row["cliente_nombre"],
        "cliente_ruc": row["cliente_ruc"],
        "cliente_ubicacion": row["cliente_ubicacion"],
        "atencion": row["atencion"],
        "atencion_email": row["atencion_email"],
        "proyecto": row["proyecto"],
        "moneda": row["moneda"],
        "validez": row["validez"],
        "encabezado_tabla": row["encabezado_tabla"],
    }
    conn.close()
    return meta

