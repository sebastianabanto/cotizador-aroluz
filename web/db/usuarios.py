# -*- coding: utf-8 -*-
"""Usuarios: autenticación y CRUD — extraído de web/database.py (refactor jun 2026)."""
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
# Usuarios
# ─────────────────────────────────────────────

def verificar_usuario(username: str, password: str) -> Optional[Dict]:
    """Devuelve el usuario si las credenciales son válidas, None si no.

    Soporta migración transparente SHA256 → bcrypt: en el primer login con hash
    SHA256 legado, re-hashea con bcrypt automáticamente.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT id, username, password_hash, nombre, rol, ver_asistencias FROM usuarios WHERE username=? AND activo=1",
        (username,),
    )
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    ph = row["password_hash"]
    if ph.startswith("$2"):
        # Hash bcrypt moderno
        ok = _bcrypt.checkpw(password.encode(), ph.encode())
    else:
        # Hash SHA256 legado (64 chars hex) — verificar y migrar a bcrypt
        ok = (hashlib.sha256(password.encode()).hexdigest() == ph)
        if ok:
            new_ph = _hash_password(password)
            conn.execute(
                "UPDATE usuarios SET password_hash=? WHERE username=?",
                (new_ph, username),
            )
            conn.commit()
    conn.close()
    if not ok:
        return None
    return {"id": row["id"], "username": row["username"], "nombre": row["nombre"], "rol": row["rol"], "ver_asistencias": bool(row["ver_asistencias"])}


def crear_usuario(username: str, password: str, nombre: str = "", rol: str = "USER", ver_asistencias: bool = False) -> bool:
    """Crea un nuevo usuario. Retorna True si fue exitoso."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        _crear_usuario(conn, username, password, nombre, rol, ver_asistencias)
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def cambiar_password(username: str, nueva_password: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        ph = _hash_password(nueva_password)
        conn.execute(
            "UPDATE usuarios SET password_hash=? WHERE username=?",
            (ph, username),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def listar_usuarios() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, username, nombre, activo, rol, ver_asistencias FROM usuarios").fetchall()
    conn.close()
    return [{**dict(r), "ver_asistencias": bool(r["ver_asistencias"])} for r in rows]


def editar_usuario(username: str, nombre: str, rol: str, ver_asistencias: bool = False) -> bool:
    """Edita nombre, rol y permisos de un usuario existente."""
    if rol not in ("ADMIN", "USER"):
        rol = "USER"
    va = 1 if (rol == "ADMIN" or ver_asistencias) else 0
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute(
            "UPDATE usuarios SET nombre=?, rol=?, ver_asistencias=? WHERE username=?",
            (nombre, rol, va, username),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def toggle_activo_usuario(username: str) -> dict:
    """Alterna el estado activo/inactivo de un usuario."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        row = conn.execute("SELECT activo FROM usuarios WHERE username=?", (username,)).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "error": "Usuario no encontrado"}
        nuevo = 0 if row[0] else 1
        conn.execute("UPDATE usuarios SET activo=? WHERE username=?", (nuevo, username))
        conn.commit()
        conn.close()
        return {"ok": True, "activo": bool(nuevo)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def eliminar_usuario(username: str) -> bool:
    """Elimina un usuario permanentemente."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("DELETE FROM usuarios WHERE username=?", (username,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

