# -*- coding: utf-8 -*-
"""Proyectos/kanban, adjuntos y OC items — extraído de web/database.py (refactor jun 2026)."""
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
# Proyectos (Kanban de obras)
# ─────────────────────────────────────────────

ESTADOS_KANBAN = ['APROBADO', 'EN_PRODUCCION', 'DESPACHADO']
ESTADO_LABELS = {
    'APROBADO':      'Aprobado con OC',
    'EN_PRODUCCION': 'En Producción',
    'DESPACHADO':    'Despachado',
}

ADJUNTOS_DIR = BASE_DIR / "data" / "adjuntos"


def init_proyectos():
    """Crea tablas proyectos + proyecto_adjuntos + proyecto_oc_items."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS proyectos (
            nombre TEXT PRIMARY KEY,
            estado TEXT NOT NULL DEFAULT 'APROBADO',
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS proyecto_adjuntos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT '',
            uploaded_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS proyecto_oc_items (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto            TEXT NOT NULL,
            descripcion         TEXT NOT NULL DEFAULT '',
            unidad              TEXT NOT NULL DEFAULT 'UND',
            cantidad_pedida     REAL NOT NULL DEFAULT 0,
            cantidad_despachada REAL NOT NULL DEFAULT 0,
            orden               INTEGER NOT NULL DEFAULT 0
        )
    """)
    # Migraciones de columnas
    _add_column_if_missing(conn, "proyectos", "direccion",     "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "cliente",       "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "numero_oc",     "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "created_at",    "TEXT")
    _add_column_if_missing(conn, "proyectos", "contacto",      "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "lugar_entrega", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "fecha_entrega", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "fecha_oc",      "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "notas",         "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyecto_adjuntos", "categoria", "TEXT NOT NULL DEFAULT 'oc'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proyectos_estado ON proyectos(estado)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proyecto_adjuntos_proyecto ON proyecto_adjuntos(proyecto)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proyecto_oc_items_proyecto ON proyecto_oc_items(proyecto)")
    conn.commit()
    conn.close()
    ADJUNTOS_DIR.mkdir(parents=True, exist_ok=True)


def get_proyectos_con_stats() -> List[Dict]:
    """Lista todos los proyectos con estadísticas, conteo de adjuntos e items OC."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT
            p.nombre,
            p.estado,
            p.cliente,
            p.numero_oc,
            p.direccion,
            p.updated_at,
            p.created_at,
            p.contacto,
            p.lugar_entrega,
            p.fecha_entrega,
            p.fecha_oc,
            COALESCE(p.notas, '') AS notas,
            COALESCE(SUM(c.total_precio), 0) AS total_cotizado,
            MAX(c.fecha) AS ultima_fecha,
            (SELECT c2.cliente_nombre FROM cotizaciones c2
             WHERE c2.proyecto = p.nombre ORDER BY c2.fecha DESC LIMIT 1) AS cliente_nombre,
            (SELECT COUNT(*) FROM proyecto_adjuntos pa
             WHERE pa.proyecto = p.nombre AND pa.categoria = 'oc') AS n_oc_docs,
            (SELECT COUNT(*) FROM proyecto_adjuntos pa
             WHERE pa.proyecto = p.nombre AND pa.categoria = 'ev') AS n_evidencia,
            (SELECT COUNT(*) FROM proyecto_oc_items oi
             WHERE oi.proyecto = p.nombre) AS n_items,
            (SELECT COUNT(*)
             FROM proyecto_oc_items oi2
             WHERE oi2.proyecto = p.nombre
               AND oi2.cantidad_pedida > oi2.cantidad_despachada) AS items_pendientes
        FROM proyectos p
        LEFT JOIN cotizaciones c ON c.proyecto = p.nombre
        GROUP BY p.nombre, p.estado, p.cliente, p.direccion
        ORDER BY p.nombre
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_proyecto_estado(nombre: str, estado: str):
    """Actualiza el estado Kanban de un proyecto."""
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "UPDATE proyectos SET estado=?, updated_at=? WHERE nombre=?",
        (estado, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nombre),
    )
    conn.commit()
    conn.close()


def get_kpis_proyectos() -> Dict:
    """KPIs del pipeline: proyectos aprobados, en producción, despachados e items pendientes."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT
            COUNT(CASE WHEN p.estado = 'APROBADO'      THEN 1 END) AS n_aprobado,
            COUNT(CASE WHEN p.estado = 'EN_PRODUCCION' THEN 1 END) AS n_produccion,
            COUNT(CASE WHEN p.estado = 'DESPACHADO'    THEN 1 END) AS n_despachado,
            COALESCE(SUM(CASE WHEN p.estado = 'APROBADO'
                THEN COALESCE(c_sum.total, 0) ELSE 0 END), 0) AS total_aprobado,
            (SELECT COUNT(*)
             FROM proyecto_oc_items oi
             JOIN proyectos pj ON pj.nombre = oi.proyecto
             WHERE pj.estado != 'DESPACHADO'
               AND oi.cantidad_pedida > oi.cantidad_despachada) AS items_pendientes
        FROM proyectos p
        LEFT JOIN (
            SELECT proyecto, SUM(total_precio) AS total
            FROM cotizaciones GROUP BY proyecto
        ) c_sum ON c_sum.proyecto = p.nombre
    """).fetchone()
    conn.close()
    return dict(row) if row else {
        "n_aprobado": 0, "total_aprobado": 0.0, "n_produccion": 0, "n_despachado": 0,
        "items_pendientes": 0,
    }


def update_proyecto_direccion(nombre: str, direccion: str):
    """Actualiza la dirección manual de la obra."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "UPDATE proyectos SET direccion=? WHERE nombre=?",
        (direccion.strip(), nombre),
    )
    conn.commit()
    conn.close()


def update_proyecto_notas(nombre: str, notas: str):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("UPDATE proyectos SET notas=? WHERE nombre=?", (notas.strip(), nombre))
    conn.commit()
    conn.close()


def update_proyecto_contacto(nombre: str, contacto: str):
    """Actualiza el contacto de la obra."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "UPDATE proyectos SET contacto=? WHERE nombre=?",
        (contacto.strip(), nombre),
    )
    conn.commit()
    conn.close()


def update_proyecto_numero_oc(nombre: str, numero_oc: str):
    """Actualiza el número de orden de compra de la obra."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "UPDATE proyectos SET numero_oc=? WHERE nombre=?",
        (numero_oc.strip(), nombre),
    )
    conn.commit()
    conn.close()


# ── Adjuntos ──

def add_adjunto(proyecto: str, filename: str, filepath: str, content_type: str = "", categoria: str = "oc") -> int:
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        """INSERT INTO proyecto_adjuntos (proyecto, filename, filepath, content_type, uploaded_at, categoria)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (proyecto, filename, filepath, content_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), categoria),
    )
    adj_id = c.lastrowid
    conn.commit()
    conn.close()
    return adj_id


def list_adjuntos(proyecto: str) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, proyecto, filename, content_type, uploaded_at, categoria FROM proyecto_adjuntos"
        " WHERE proyecto=? ORDER BY uploaded_at DESC",
        (proyecto,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_adjunto_filepath(adjunto_id: int, proyecto: str) -> Optional[dict]:
    """Devuelve el filepath de un adjunto verificando que pertenezca al proyecto."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT filepath, filename, content_type FROM proyecto_adjuntos WHERE id=? AND proyecto=?",
        (adjunto_id, proyecto),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_adjunto(adjunto_id: int) -> Optional[str]:
    """Elimina el registro y retorna el filepath para borrar el archivo físico."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute(
        "SELECT filepath FROM proyecto_adjuntos WHERE id=?", (adjunto_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    filepath = row[0]
    conn.execute("DELETE FROM proyecto_adjuntos WHERE id=?", (adjunto_id,))
    conn.commit()
    conn.close()
    return filepath


# ── Proyectos: creación/eliminación manual ──

def renombrar_proyecto(nombre: str, nuevo_nombre: str, nuevo_cliente: str) -> bool:
    """Renombra un proyecto y actualiza el cliente. Cascada manual a tablas relacionadas."""
    nuevo_nombre = nuevo_nombre.strip()
    nuevo_cliente = nuevo_cliente.strip()
    if not nuevo_nombre:
        return False
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        conn.execute("BEGIN")
        if nuevo_nombre != nombre:
            # Verificar que el nuevo nombre no exista ya
            existe = conn.execute(
                "SELECT 1 FROM proyectos WHERE nombre=?", (nuevo_nombre,)
            ).fetchone()
            if existe:
                conn.rollback()
                conn.close()
                return False
            conn.execute("UPDATE cotizaciones SET proyecto=? WHERE proyecto=?", (nuevo_nombre, nombre))
            conn.execute("UPDATE proyecto_adjuntos SET proyecto=? WHERE proyecto=?", (nuevo_nombre, nombre))
            conn.execute("UPDATE proyecto_oc_items SET proyecto=? WHERE proyecto=?", (nuevo_nombre, nombre))
            conn.execute("UPDATE proyectos SET nombre=?, cliente=? WHERE nombre=?", (nuevo_nombre, nuevo_cliente, nombre))
        else:
            conn.execute("UPDATE proyectos SET cliente=? WHERE nombre=?", (nuevo_cliente, nombre))
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        return False
    conn.close()
    return True


def crear_proyecto(
    nombre: str,
    cliente: str,
    lugar_entrega: str = "",
    fecha_entrega: str = "",
    fecha_oc: str = "",
) -> bool:
    """Crea un proyecto en estado APROBADO. Retorna False si ya existe."""
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        """INSERT OR IGNORE INTO proyectos
           (nombre, cliente, estado, created_at, lugar_entrega, fecha_entrega, fecha_oc)
           VALUES (?, ?, 'APROBADO', ?, ?, ?, ?)""",
        (nombre.strip(), cliente.strip(), datetime.now().strftime("%Y-%m-%d"),
         lugar_entrega.strip(), fecha_entrega.strip(), fecha_oc.strip()),
    )
    created = c.rowcount > 0
    conn.commit()
    conn.close()
    return created


def proyecto_existe(nombre: str) -> bool:
    """Retorna True si ya hay un proyecto con ese nombre exacto."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT 1 FROM proyectos WHERE nombre=?", (nombre.strip(),)).fetchone()
    conn.close()
    return row is not None


def eliminar_proyecto(nombre: str) -> bool:
    """Elimina un proyecto, sus adjuntos físicos y sus items OC."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    adjuntos = conn.execute(
        "SELECT filepath FROM proyecto_adjuntos WHERE proyecto=?", (nombre,)
    ).fetchall()
    for adj in adjuntos:
        try:
            Path(adj["filepath"]).unlink(missing_ok=True)
        except Exception:
            pass
    conn.execute("DELETE FROM proyecto_adjuntos WHERE proyecto=?", (nombre,))
    conn.execute("DELETE FROM proyecto_oc_items WHERE proyecto=?", (nombre,))
    conn.execute("DELETE FROM email_importados WHERE proyecto=?", (nombre,))
    c_del = conn.execute("DELETE FROM proyectos WHERE nombre=?", (nombre,))
    deleted = c_del.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ── OC Items CRUD ──

def get_oc_items(proyecto: str) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM proyecto_oc_items WHERE proyecto=? ORDER BY orden, id",
        (proyecto,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_oc_item(
    proyecto: str,
    descripcion: str,
    unidad: str,
    cantidad_pedida: float,
    cantidad_despachada: float,
    orden: int = 0,
) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        """INSERT INTO proyecto_oc_items
           (proyecto, descripcion, unidad, cantidad_pedida, cantidad_despachada, orden)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (proyecto, descripcion, unidad, cantidad_pedida, cantidad_despachada, orden),
    )
    item_id = c.lastrowid
    conn.commit()
    conn.close()
    return item_id


def update_oc_item(
    item_id: int,
    proyecto: str,
    descripcion: str,
    unidad: str,
    cantidad_pedida: float,
    cantidad_despachada: float,
) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        """UPDATE proyecto_oc_items
           SET descripcion=?, unidad=?, cantidad_pedida=?, cantidad_despachada=?
           WHERE id=? AND proyecto=?""",
        (descripcion, unidad, cantidad_pedida, cantidad_despachada, item_id, proyecto),
    )
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_oc_item(item_id: int, proyecto: str) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        "DELETE FROM proyecto_oc_items WHERE id=? AND proyecto=?",
        (item_id, proyecto),
    )
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

