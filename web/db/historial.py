# -*- coding: utf-8 -*-
"""Historial de cotizaciones, estadísticas, tendencias y duplicados — extraído de web/database.py (refactor jun 2026)."""
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
# Historial de cotizaciones
# ─────────────────────────────────────────────

def guardar_cotizacion_db(
    username: str,
    cliente: str,
    atencion: str,
    proyecto: str,
    moneda: str,
    items: List[Dict],
    cliente_nombre: str = "",
    cliente_ruc: str = "",
    cliente_ubicacion: str = "",
    atencion_email: str = "",
    dolar_rate: float = 3.8,
    validez: str = "30 días",
    encabezado_tabla: str = "",
) -> int:
    """Guarda una cotización con sus items. Retorna el id de la cotización."""
    from datetime import datetime
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_precio = sum(i.get("precio_unitario", 0) * i.get("cantidad", 1) for i in items)
    total_peso = sum(i.get("peso_unitario", 0) * i.get("cantidad", 1) for i in items)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.execute(
        """INSERT INTO cotizaciones
           (username, fecha, cliente, atencion, proyecto, moneda, total_precio, total_peso,
            cliente_nombre, cliente_ruc, cliente_ubicacion, atencion_email,
            dolar_rate, validez, encabezado_tabla)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (username, fecha, cliente, atencion, proyecto, moneda,
         round(total_precio, 4), round(total_peso, 6),
         cliente_nombre, cliente_ruc, cliente_ubicacion, atencion_email,
         dolar_rate, validez, encabezado_tabla),
    )
    cotizacion_id = c.lastrowid
    for item in items:
        c.execute(
            """INSERT INTO cotizacion_items
               (cotizacion_id, tipo, descripcion, precio_unitario, peso_unitario,
                cantidad, unidad, tipo_galvanizado, porcentaje_ganancia, precio_manual)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cotizacion_id,
                item.get("tipo", ""),
                item.get("descripcion", ""),
                item.get("precio_unitario", 0),
                item.get("peso_unitario", 0),
                item.get("cantidad", 1),
                item.get("unidad", "UND"),
                item.get("tipo_galvanizado", "N/A"),
                item.get("porcentaje_ganancia", "N/A"),
                1 if item.get("precio_manual") else 0,
            ),
        )
    conn.commit()
    conn.close()
    return cotizacion_id


def guardar_cotizacion_importada_db(
    username: str,
    cliente: str,
    atencion: str,
    proyecto: str,
    moneda: str,
    items: List[Dict],
    cliente_nombre: str = "",
    cliente_ruc: str = "",
    cliente_ubicacion: str = "",
    atencion_email: str = "",
    dolar_rate: float = 3.8,
    validez: str = "30 días",
    encabezado_tabla: str = "",
    fecha: Optional[str] = None,
    origen: str = "pdf_import",
) -> int:
    """Guarda una cotización importada (p. ej. desde PDF) con fecha y origen personalizados."""
    from datetime import datetime
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_precio = sum(i.get("precio_unitario", 0) * i.get("cantidad", 1) for i in items)
    total_peso   = sum(i.get("peso_unitario", 0)  * i.get("cantidad", 1) for i in items)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.execute(
        """INSERT INTO cotizaciones
           (username, fecha, cliente, atencion, proyecto, moneda, total_precio, total_peso,
            cliente_nombre, cliente_ruc, cliente_ubicacion, atencion_email,
            dolar_rate, validez, encabezado_tabla, origen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (username, fecha, cliente, atencion, proyecto, moneda,
         round(total_precio, 4), round(total_peso, 6),
         cliente_nombre, cliente_ruc, cliente_ubicacion, atencion_email,
         dolar_rate, validez, encabezado_tabla, origen),
    )
    cotizacion_id = c.lastrowid
    for item in items:
        c.execute(
            """INSERT INTO cotizacion_items
               (cotizacion_id, tipo, descripcion, precio_unitario, peso_unitario,
                cantidad, unidad, tipo_galvanizado, porcentaje_ganancia, precio_manual)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cotizacion_id,
                item.get("tipo", "MANUAL"),
                item.get("descripcion", ""),
                item.get("precio_unitario", 0),
                item.get("peso_unitario", 0),
                item.get("cantidad", 1),
                item.get("unidad", "UND"),
                item.get("tipo_galvanizado", "N/A"),
                item.get("porcentaje_ganancia", "N/A"),
                1 if item.get("precio_manual") else 0,
            ),
        )
    conn.commit()
    conn.close()
    return cotizacion_id


def listar_cotizaciones_db(
    username: Optional[str] = None,
    tipos: Optional[List[str]] = None,
    q: str = "",
    galvanizados: Optional[List[str]] = None,
    ganancias: Optional[List[str]] = None,
) -> List[Dict]:
    """Lista cotizaciones guardadas con conteo de items.

    Params:
        username     — filtra por usuario (obligatorio en uso normal)
        tipos        — lista de códigos de tipo (B, CH, …); si no está vacía, sólo
                       devuelve cotizaciones que contengan al menos uno de esos tipos
        q            — texto libre; filtra cotizaciones cuya descripción de ítem contenga
                       este texto (case-insensitive)
        galvanizados — lista de valores de galvanizado (GO, GC, N/A); si no está vacía,
                       sólo devuelve cotizaciones que contengan al menos uno de esos tipos
        ganancias    — lista de valores de porcentaje_ganancia (30, 35, N/A); si no está
                       vacía, sólo devuelve cotizaciones que contengan al menos uno
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row

    conditions: List[str] = []
    params: List = []

    if username:
        conditions.append("c.username=?")
        params.append(username)

    if tipos:
        placeholders = ",".join("?" * len(tipos))
        conditions.append(
            f"EXISTS (SELECT 1 FROM cotizacion_items ci2"
            f" WHERE ci2.cotizacion_id = c.id AND ci2.tipo IN ({placeholders}))"
        )
        params.extend(tipos)

    if q:
        palabras = [p.strip() for p in q.split(",") if p.strip()]
        if palabras:
            like_clauses = " AND ".join(
                "LOWER(ci3.descripcion) LIKE ?" for _ in palabras
            )
            conditions.append(
                f"EXISTS (SELECT 1 FROM cotizacion_items ci3"
                f" WHERE ci3.cotizacion_id = c.id AND {like_clauses})"
            )
            params.extend(f"%{p.lower()}%" for p in palabras)

    if galvanizados:
        placeholders = ",".join("?" * len(galvanizados))
        conditions.append(
            f"EXISTS (SELECT 1 FROM cotizacion_items ci4"
            f" WHERE ci4.cotizacion_id = c.id AND ci4.tipo_galvanizado IN ({placeholders}))"
        )
        params.extend(galvanizados)

    if ganancias:
        placeholders = ",".join("?" * len(ganancias))
        conditions.append(
            f"EXISTS (SELECT 1 FROM cotizacion_items ci5"
            f" WHERE ci5.cotizacion_id = c.id AND ci5.porcentaje_ganancia IN ({placeholders}))"
        )
        params.extend(ganancias)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT c.*, COUNT(ci.id) AS total_items
        FROM cotizaciones c
        LEFT JOIN cotizacion_items ci ON ci.cotizacion_id = c.id
        {where}
        GROUP BY c.id
        ORDER BY c.id DESC
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_estadisticas_db(username: Optional[str] = None) -> Dict:
    """Devuelve métricas agregadas del historial de cotizaciones.

    Si username es None (admin) devuelve datos globales; si se indica un
    username devuelve únicamente los datos de ese usuario.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    if username:
        wp = [username]
        wc = "WHERE c.username=? AND (c.origen = 'web' OR c.origen IS NULL)"
    else:
        wp = []
        wc = "WHERE (c.origen = 'web' OR c.origen IS NULL)"

    # Totales globales
    row = conn.execute(
        f"SELECT COUNT(*) AS n, COALESCE(SUM(total_precio),0) AS total "
        f"FROM cotizaciones c {wc}", wp
    ).fetchone()
    total_cots     = row["n"]
    total_facturado = round(float(row["total"]), 2)

    # Por mes (últimos 12, orden cronológico)
    por_mes = list(reversed(conn.execute(f"""
        SELECT strftime('%Y-%m', fecha) AS mes,
               COUNT(*) AS cantidad,
               ROUND(COALESCE(SUM(total_precio),0), 2) AS total
        FROM cotizaciones c {wc}
        GROUP BY mes ORDER BY mes DESC LIMIT 12
    """, wp).fetchall()))

    # Top 5 clientes por cantidad de cotizaciones (excluye sin cliente)
    top_clientes = conn.execute(f"""
        SELECT COALESCE(NULLIF(TRIM(cliente_nombre),''), NULLIF(TRIM(cliente),''), 'Sin cliente') AS nombre,
               COUNT(*) AS cantidad,
               ROUND(COALESCE(SUM(total_precio),0), 2) AS total
        FROM cotizaciones c {wc}
        GROUP BY nombre HAVING nombre != 'Sin cliente' ORDER BY cantidad DESC LIMIT 5
    """, wp).fetchall()

    # Por tipo de producto
    if username:
        por_tipo = conn.execute("""
            SELECT ci.tipo, COUNT(*) AS cantidad
            FROM cotizacion_items ci
            JOIN cotizaciones c ON c.id = ci.cotizacion_id
            WHERE c.username=? AND (c.origen = 'web' OR c.origen IS NULL)
            GROUP BY ci.tipo ORDER BY cantidad DESC
        """, [username]).fetchall()
    else:
        por_tipo = conn.execute("""
            SELECT ci.tipo, COUNT(*) AS cantidad
            FROM cotizacion_items ci
            JOIN cotizaciones c ON c.id = ci.cotizacion_id
            WHERE (c.origen = 'web' OR c.origen IS NULL)
            GROUP BY ci.tipo ORDER BY cantidad DESC
        """).fetchall()

    # Por moneda
    por_moneda = conn.execute(f"""
        SELECT moneda, COUNT(*) AS cantidad, ROUND(COALESCE(SUM(total_precio),0),2) AS total
        FROM cotizaciones c {wc}
        GROUP BY moneda
    """, wp).fetchall()

    conn.close()
    return {
        "total_cotizaciones": total_cots,
        "total_facturado_soles": total_facturado,
        "por_mes":       [dict(r) for r in por_mes],
        "top_clientes":  [dict(r) for r in top_clientes],
        "por_tipo":      [dict(r) for r in por_tipo],
        "por_moneda":    [dict(r) for r in por_moneda],
    }


def _parse_espesor(desc: str) -> str:
    """Extrae el espesor nominal (1.2, 1.5, 2.0) de la descripción de un ítem."""
    d = desc.upper()
    if "1/20" in d:
        return "1.2"
    if "1/16" in d:
        return "1.5"
    m = _re.search(r'\b([12]\.\d)\s*MM', d)
    if m:
        v = m.group(1)
        if v in ("1.2", "1.5", "2.0"):
            return v
    return ""


def get_items_frecuentes_db(
    username: Optional[str] = None,
    cliente: str = "",
    proyecto: str = "",
    limit: int = 40,
) -> List[Dict]:
    """Devuelve ítems del historial ordenados por frecuencia de aparición."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row

    where_parts: List[str] = []
    params: List = []

    if username:
        where_parts.append("c.username = ?")
        params.append(username)
    if cliente.strip():
        like = f"%{cliente.strip()}%"
        where_parts.append("(c.cliente LIKE ? OR c.cliente_nombre LIKE ?)")
        params.extend([like, like])
    if proyecto.strip():
        where_parts.append("c.proyecto LIKE ?")
        params.append(f"%{proyecto.strip()}%")

    where = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    sql = f"""
        SELECT ci.descripcion, ci.tipo, COUNT(*) AS count
        FROM cotizacion_items ci
        JOIN cotizaciones c ON c.id = ci.cotizacion_id
        {where}
        GROUP BY ci.descripcion
        ORDER BY count DESC
        LIMIT ?
    """
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["espesor"] = _parse_espesor(d["descripcion"])
        result.append(d)
    return result


def get_tendencias_items_db(
    clientes: List[str],
    proyecto: str = "",
    q: str = "",
    username: Optional[str] = None,
    tipos: Optional[List[str]] = None,
    galvanizados: Optional[List[str]] = None,
    ganancias: Optional[List[str]] = None,
    monedas: Optional[List[str]] = None,
    espesores: Optional[List[str]] = None,
) -> List[Dict]:
    """Devuelve puntos de precio por ítem para graficar tendencias.

    Para cada cliente en `clientes` ejecuta una consulta y etiqueta los
    resultados con `cliente_idx` (0 = primer cliente, 1 = segundo).
    El precio se normaliza a S/ usando el `dolar_rate` de cada cotización.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    results: List[Dict] = []

    # Si no se especificó ningún cliente, hacer una pasada sin filtro de cliente (idx=0)
    iteracion = list(enumerate(clientes)) if clientes else [(0, "")]

    for idx, cli in iteracion:
        cli = (cli or "").strip()

        where_parts: List[str] = []
        params: List = []

        if cli:
            like_cli = f"%{cli}%"
            where_parts.append("(c.cliente LIKE ? OR c.cliente_nombre LIKE ?)")
            params.extend([like_cli, like_cli])

        if username:
            where_parts.append("c.username = ?")
            params.append(username)

        if proyecto.strip():
            where_parts.append("c.proyecto LIKE ?")
            params.append(f"%{proyecto.strip()}%")

        if q.strip():
            palabras = [p.strip() for p in q.split(",") if p.strip()]
            for p in palabras:
                where_parts.append("LOWER(ci.descripcion) LIKE ?")
                params.append(f"%{p.lower()}%")

        if tipos:
            placeholders = ",".join("?" * len(tipos))
            where_parts.append(f"ci.tipo IN ({placeholders})")
            params.extend(tipos)

        if galvanizados:
            placeholders = ",".join("?" * len(galvanizados))
            where_parts.append(f"ci.tipo_galvanizado IN ({placeholders})")
            params.extend(galvanizados)

        if ganancias:
            placeholders = ",".join("?" * len(ganancias))
            where_parts.append(f"ci.porcentaje_ganancia IN ({placeholders})")
            params.extend(ganancias)

        if monedas:
            placeholders = ",".join("?" * len(monedas))
            where_parts.append(f"c.moneda IN ({placeholders})")
            params.extend(monedas)

        sql = f"""
            SELECT
                c.id AS cotizacion_id,
                c.fecha,
                c.cliente,
                c.cliente_nombre,
                c.proyecto,
                c.moneda,
                c.dolar_rate,
                ci.descripcion,
                ci.precio_unitario,
                ci.tipo,
                ci.tipo_galvanizado
            FROM cotizaciones c
            JOIN cotizacion_items ci ON ci.cotizacion_id = c.id
            {"WHERE " + " AND ".join(where_parts) if where_parts else ""}
            ORDER BY c.fecha ASC, c.id ASC
        """
        rows = conn.execute(sql, params).fetchall()
        for row in rows:
            d = dict(row)
            moneda = d.get("moneda", "SOLES")
            dolar_rate = float(d.get("dolar_rate") or 3.8)
            precio_soles = (
                d["precio_unitario"] if moneda == "SOLES"
                else d["precio_unitario"] * dolar_rate
            )
            d["precio_soles"] = round(precio_soles, 2)
            # Filtrar precios inválidos: cero y valores centinela como 999
            if d["precio_soles"] <= 0 or abs(d["precio_soles"] - 999) < 0.5:
                continue
            d["espesor"] = _parse_espesor(d["descripcion"])
            d["galvanizado"] = d.get("tipo_galvanizado", "") or ""
            d["cliente_idx"] = idx
            d["cliente_label"] = d["cliente_nombre"] or d["cliente"] or cli or ""
            if espesores and d["espesor"] not in espesores:
                continue
            results.append(d)

    conn.close()
    return results


def get_cotizacion_db(cotizacion_id: int) -> Optional[Dict]:
    """Devuelve cabecera + items de una cotización guardada."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM cotizaciones WHERE id=?", (cotizacion_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    cotizacion = dict(row)
    items = conn.execute(
        "SELECT * FROM cotizacion_items WHERE cotizacion_id=? ORDER BY id",
        (cotizacion_id,),
    ).fetchall()
    cotizacion["items"] = [dict(i) for i in items]
    conn.close()
    return cotizacion


def eliminar_cotizacion_db(cotizacion_id: int, username: Optional[str]) -> bool:
    """Elimina una cotización. Si username es None (admin), elimina sin restricción de propiedad."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    if username is None:
        c.execute("DELETE FROM cotizaciones WHERE id=?", (cotizacion_id,))
    else:
        c.execute(
            "DELETE FROM cotizaciones WHERE id=? AND username=?",
            (cotizacion_id, username),
        )
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def eliminar_cotizaciones_bulk_db(ids: List[int]) -> int:
    """Elimina múltiples cotizaciones (admin). Retorna cantidad eliminada."""
    if not ids:
        return 0
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    placeholders = ",".join("?" * len(ids))
    c = conn.cursor()
    c.execute(f"DELETE FROM cotizaciones WHERE id IN ({placeholders})", ids)
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted


def _fp_items(items: list) -> str:
    """Fingerprint estable de una lista de ítems: hash MD5 de (descripcion, cantidad) ordenados."""
    import hashlib
    normalized = sorted(
        (str(i.get("descripcion", "")).strip().lower(),
         round(float(i.get("cantidad") or 1), 4))
        for i in items
    )
    raw = "|".join(f"{d}:{c}" for d, c in normalized)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def detectar_duplicados_db() -> List[Dict]:
    """
    Agrupa cotizaciones por (cliente_norm, proyecto_norm, total_redondeado, items_fp)
    y retorna solo los grupos con 2+ entradas. Ignora filas sin cliente y sin proyecto.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT c.id, c.username, c.fecha, c.cliente, c.proyecto, c.moneda,
               c.cliente_nombre, c.total_precio, c.dolar_rate, c.origen,
               COUNT(ci.id) AS total_items
        FROM cotizaciones c
        LEFT JOIN cotizacion_items ci ON ci.cotizacion_id = c.id
        GROUP BY c.id
        ORDER BY c.id ASC
    """).fetchall()

    item_rows = conn.execute("""
        SELECT cotizacion_id, descripcion, cantidad
        FROM cotizacion_items
    """).fetchall()
    conn.close()

    from collections import defaultdict
    items_by_cot: Dict[int, list] = defaultdict(list)
    for ir in item_rows:
        items_by_cot[ir["cotizacion_id"]].append({
            "descripcion": ir["descripcion"],
            "cantidad":    ir["cantidad"],
        })

    grupos: Dict[tuple, list] = defaultdict(list)
    for r in rows:
        cliente_n  = (r["cliente_nombre"] or r["cliente"] or "").strip().lower()
        proyecto_n = (r["proyecto"] or "").strip().lower()
        if not cliente_n and not proyecto_n:
            continue
        total_norm = round(float(r["total_precio"] or 0), 2)
        items_fp   = _fp_items(items_by_cot.get(r["id"], []))
        clave = (cliente_n, proyecto_n, total_norm, items_fp)
        grupos[clave].append(dict(r))

    return [
        {
            "cliente":  grupo[0].get("cliente_nombre") or grupo[0].get("cliente") or "",
            "proyecto": grupo[0].get("proyecto") or "",
            "total":    round(float(grupo[0].get("total_precio") or 0), 2),
            "cotizaciones": grupo,
        }
        for grupo in grupos.values()
        if len(grupo) >= 2
    ]


def fingerprints_cotizaciones_db() -> Dict[str, List[int]]:
    """
    Retorna dict fingerprint → [ids] para todas las cotizaciones.
    Fingerprint = 'cliente_norm|proyecto_norm|total_redondeado|items_fp'.
    Usado para detectar posibles duplicados durante la importación de PDFs.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT id, cliente_nombre, cliente, proyecto, total_precio
        FROM cotizaciones
    """).fetchall()

    item_rows = conn.execute("""
        SELECT cotizacion_id, descripcion, cantidad
        FROM cotizacion_items
    """).fetchall()
    conn.close()

    from collections import defaultdict
    items_by_cot: Dict[int, list] = defaultdict(list)
    for ir in item_rows:
        items_by_cot[ir["cotizacion_id"]].append({
            "descripcion": ir["descripcion"],
            "cantidad":    ir["cantidad"],
        })

    result: Dict[str, List[int]] = {}
    for r in rows:
        cliente  = (r["cliente_nombre"] or r["cliente"] or "").strip().lower()
        proyecto = (r["proyecto"] or "").strip().lower()
        total    = round(float(r["total_precio"] or 0), 2)
        items_fp = _fp_items(items_by_cot.get(r["id"], []))
        fp = f"{cliente}|{proyecto}|{total}|{items_fp}"
        result.setdefault(fp, []).append(r["id"])
    return result

