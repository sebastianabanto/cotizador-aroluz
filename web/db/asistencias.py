# -*- coding: utf-8 -*-
"""Reportes de asistencia — extraído de web/database.py (refactor jun 2026)."""
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
# Reportes de asistencia
# ─────────────────────────────────────────────

def guardar_reporte_asistencia(
    periodo: str,
    periodo_label: str,
    subido_por: str,
    nombre_archivo: str,
    num_empleados: int,
    datos_json_str: str,
) -> int:
    """Inserta un reporte procesado. Devuelve el id insertado."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute(
        """INSERT INTO reportes_asistencia
           (periodo, periodo_label, fecha_subida, subido_por, nombre_archivo, num_empleados, datos_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (periodo, periodo_label, _dt.now().isoformat(timespec="seconds"),
         subido_por, nombre_archivo, num_empleados, datos_json_str),
    )
    nuevo_id = c.lastrowid
    conn.commit()
    conn.close()
    return nuevo_id


def listar_reportes_asistencia() -> List[Dict]:
    """Devuelve todos los reportes sin datos_json, ordenados por fecha_subida DESC."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        """SELECT id, periodo, periodo_label, fecha_subida, subido_por, nombre_archivo, num_empleados
           FROM reportes_asistencia ORDER BY periodo ASC"""
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def obtener_reporte_asistencia(reporte_id: int) -> Optional[Dict]:
    """Devuelve el reporte completo incluyendo datos_json, o None si no existe."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM reportes_asistencia WHERE id=?", (reporte_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def eliminar_reporte_asistencia(reporte_id: int) -> bool:
    """Elimina el reporte de DB. Devuelve True si existía."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute("DELETE FROM reportes_asistencia WHERE id=?", (reporte_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def periodo_existe(periodo: str) -> Optional[int]:
    """Devuelve el id del reporte si el período ya existe, o None."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute("SELECT id FROM reportes_asistencia WHERE periodo=?", (periodo,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def buscar_reporte_por_mes(anio: int, mes: int) -> Optional[Dict]:
    """Busca un reporte existente que cubra el mismo mes/año (quincena o mes completo)."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    patron = f"{anio:04d}-{mes:02d}-%"
    c.execute("SELECT * FROM reportes_asistencia WHERE periodo LIKE ?", (patron,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_reporte_asistencia(
    reporte_id: int,
    nombre_archivo: str,
    subido_por: str,
    num_empleados: int,
    datos_json_str: str,
):
    """Sobreescribe datos de un reporte existente (para duplicados confirmados)."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        """UPDATE reportes_asistencia
           SET nombre_archivo=?, subido_por=?, fecha_subida=?, num_empleados=?, datos_json=?
           WHERE id=?""",
        (nombre_archivo, subido_por, _dt.now().isoformat(timespec="seconds"),
         num_empleados, datos_json_str, reporte_id),
    )
    conn.commit()
    conn.close()


def fusionar_reporte_asistencia(
    reporte_id: int,
    periodo: str,
    periodo_label: str,
    subido_por: str,
    num_empleados: int,
    datos_json_str: str,
) -> None:
    """Actualiza un reporte con datos fusionados de dos quincenas del mismo mes."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        """UPDATE reportes_asistencia
           SET periodo=?, periodo_label=?, subido_por=?, fecha_subida=?,
               num_empleados=?, datos_json=?
           WHERE id=?""",
        (periodo, periodo_label, subido_por, _dt.now().isoformat(timespec="seconds"),
         num_empleados, datos_json_str, reporte_id),
    )
    conn.commit()
    conn.close()

