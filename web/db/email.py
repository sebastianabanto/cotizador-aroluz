# -*- coding: utf-8 -*-
"""Config IMAP (contraseña cifrada) y emails importados — extraído de web/database.py (refactor jun 2026)."""
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

# ── IMAP / correo electrónico ────────────────────────────────────────────────

# La contraseña IMAP se guarda cifrada (Fernet) con prefijo "enc:". La clave se
# deriva de AROLUZ_SECRET_KEY; sin esa env var se persiste una clave propia en
# web/data/.imap_key para que el descifrado sobreviva reinicios.
_ENC_PREFIX = "enc:"


def _imap_fernet():
    import base64 as _b64
    import hashlib as _hashlib
    from cryptography.fernet import Fernet
    secret = os.environ.get("AROLUZ_SECRET_KEY")
    if not secret:
        key_file = DB_PATH.parent / ".imap_key"
        if key_file.exists():
            secret = key_file.read_text().strip()
        else:
            import secrets as _sec
            secret = _sec.token_hex(32)
            key_file.write_text(secret)
    return Fernet(_b64.urlsafe_b64encode(_hashlib.sha256(secret.encode()).digest()))


def _cifrar_imap_password(password: str) -> str:
    if not password:
        return ""
    return _ENC_PREFIX + _imap_fernet().encrypt(password.encode()).decode()


def _descifrar_imap_password(stored: str) -> str:
    if not stored:
        return ""
    if not stored.startswith(_ENC_PREFIX):
        return stored  # valor legacy en texto plano — se re-cifra al guardar
    try:
        return _imap_fernet().decrypt(stored[len(_ENC_PREFIX):].encode()).decode()
    except Exception:
        # Clave cambiada o token corrupto: forzar reconfiguración en Ajustes → Correo
        return ""


def get_email_imap_config() -> Optional[Dict]:
    """Devuelve la configuración IMAP guardada, o None si aún no está configurada."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM email_imap_config WHERE id=1").fetchone()
    conn.close()
    if not row or not row["host"]:
        return None
    cfg = dict(row)
    cfg["password"] = _descifrar_imap_password(cfg.get("password") or "")
    return cfg


def save_email_imap_config(host: str, port: int, username: str, password: str,
                            folder: str, days_back: int) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        """INSERT INTO email_imap_config (id, host, port, username, password, folder, days_back)
           VALUES (1, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
               host=excluded.host, port=excluded.port, username=excluded.username,
               password=excluded.password, folder=excluded.folder, days_back=excluded.days_back""",
        (host, port, username, _cifrar_imap_password(password), folder, days_back),
    )
    conn.commit()
    conn.close()


def email_ya_importado(message_id: str) -> bool:
    """True si el message_id ya fue importado y el proyecto todavía existe."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute(
        """SELECT ei.proyecto FROM email_importados ei
           JOIN proyectos p ON p.nombre = ei.proyecto
           WHERE ei.message_id = ?""",
        (message_id,),
    ).fetchone()
    conn.close()
    return row is not None


def pdf_hash_ya_importado(pdf_hash: str) -> bool:
    """True si ya se importó un PDF con ese hash SHA-256 y el proyecto aún existe.
    Permite detectar reenvíos/respuestas que adjuntan el mismo PDF."""
    if not pdf_hash:
        return False
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute(
        """SELECT ei.proyecto FROM email_importados ei
           JOIN proyectos p ON p.nombre = ei.proyecto
           WHERE ei.pdf_hash = ?""",
        (pdf_hash,),
    ).fetchone()
    conn.close()
    return row is not None


def registrar_email_importado(message_id: str, proyecto: str, pdf_hash: str = "") -> None:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        """INSERT OR IGNORE INTO email_importados (message_id, proyecto, importado_at, pdf_hash)
           VALUES (?, ?, ?, ?)""",
        (message_id, proyecto, _dt.now().strftime("%Y-%m-%d %H:%M:%S"), pdf_hash),
    )
    conn.commit()
    conn.close()


def get_dominios_clientes() -> set:
    """Devuelve el conjunto de dominios de correo de las atenciones registradas (ej. {'empresa.com'})."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute("SELECT email FROM atenciones WHERE email != ''").fetchall()
    conn.close()
    dominios = set()
    for (email_addr,) in rows:
        if "@" in email_addr:
            domain = email_addr.split("@", 1)[1].strip().lower()
            if domain:
                dominios.add(domain)
    return dominios


def get_cliente_nombre_por_dominio(domain: str) -> str:
    """Devuelve el nombre del cliente registrado con ese dominio de correo, o '' si no existe."""
    if not domain:
        return ""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute(
        """SELECT c.nombre FROM atenciones a
           JOIN clientes c ON c.codigo = a.codigo_empresa
           WHERE lower(a.email) LIKE ? LIMIT 1""",
        (f"%@{domain.lower()}",),
    ).fetchone()
    conn.close()
    return row[0] if row else ""

