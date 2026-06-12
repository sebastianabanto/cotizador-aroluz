"""
database.py — Base de datos SQLite para usuarios y catálogo

Gestiona:
- Tabla de usuarios (autenticación)
- Configuración del sistema (leída desde cotizador_config.json)
- Catálogo de clientes/atenciones (desde Excel o tabla SQLite)
"""
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

# Ruta de la base de datos — BASE_DIR es web/ (este archivo vive en web/db/)
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "aroluz.db"
CONFIG_PATH = BASE_DIR / "data" / "cotizador_config.json"
_CONFIG_RAIZ = BASE_DIR.parent / "cotizador_config.json"

CONFIG_DEFECTO = {
    "rutas": {
        "carpeta_excel": "",
        "carpeta_pdfs": "",
    },
    "valores_defecto": {
        "ganancia": "30",
        "galvanizado": "GO",
        "espesor_producto": "1.5",
        "espesor_tapa": "1.5",
        "precios_go": {"1.2": 150.0, "1.5": 180.0, "2.0": 220.0},
        "precios_gc": {"1.2": 140.0, "1.5": 170.0, "2.0": 210.0},
        "dolar": 3.8,
        "usd_kg_productos": 1.0,
        "usd_kg_cajas": 3.0,
    },
    "interfaz": {
        "recordar_config": True,
        "recordar_medidas": True,
        "mostrar_validaciones": True,
    },
    "permisos_usuario": {
        "ver_historial": True,
        "ver_catalogo": True,
    },
    "factores_ganancia": {
        "30": {"B": 0.70, "CH": 0.50, "CVE": 0.50, "CVI": 0.50, "T": 0.60, "C": 0.70, "R": 0.20, "CP": 0.50},
        "35": {"B": 0.65, "CH": 0.45, "CVE": 0.45, "CVI": 0.45, "T": 0.55, "C": 0.65, "R": 0.15, "CP": 0.475},
    },
}


# ─────────────────────────────────────────────
# Inicialización
# ─────────────────────────────────────────────

def _backup_db():
    """Copia la DB a web/data/backups/ al iniciar. Conserva solo los últimos 7 backups."""
    if not DB_PATH.exists():
        return
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    ts = _dt.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"aroluz_{ts}.db"
    shutil.copy2(DB_PATH, dest)
    # Conservar solo los últimos 7 backups
    backups = sorted(backup_dir.glob("aroluz_*.db"))
    for old in backups[:-7]:
        old.unlink()


def _add_column_if_missing(conn, table: str, column: str, col_def: str):
    """Agrega una columna a una tabla si no existe (migración segura)."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
    except sqlite3.OperationalError:
        pass  # columna ya existe


def _migrate_cantidad_to_real(conn):
    """Migra carrito_items.cantidad de INTEGER a REAL si todavía es INTEGER."""
    rows = conn.execute("PRAGMA table_info(carrito_items)").fetchall()
    col = next((r for r in rows if r[1] == "cantidad"), None)
    if col is None or col[2].upper() == "REAL":
        return  # ya está bien
    # Recrear tabla con REAL
    conn.execute("ALTER TABLE carrito_items RENAME TO carrito_items_bak")
    conn.execute("""
        CREATE TABLE carrito_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            precio_unitario REAL NOT NULL,
            peso_unitario REAL NOT NULL,
            cantidad REAL NOT NULL DEFAULT 1,
            unidad TEXT NOT NULL DEFAULT 'UND',
            tipo_galvanizado TEXT NOT NULL DEFAULT 'GO',
            porcentaje_ganancia TEXT NOT NULL DEFAULT '30',
            descripcion_calculada TEXT DEFAULT NULL
        )
    """)
    conn.execute("""
        INSERT INTO carrito_items
            (id, username, tipo, descripcion, precio_unitario, peso_unitario,
             cantidad, unidad, tipo_galvanizado, porcentaje_ganancia, descripcion_calculada)
        SELECT id, username, tipo, descripcion, precio_unitario, peso_unitario,
               CAST(cantidad AS REAL), unidad, tipo_galvanizado, porcentaje_ganancia,
               descripcion_calculada
        FROM carrito_items_bak
    """)
    conn.execute("DROP TABLE carrito_items_bak")


def init_db():
    """Crea las tablas necesarias si no existen."""
    _backup_db()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Migrar config de la raíz a web/data/ si aún no existe allí
    if not CONFIG_PATH.exists() and _CONFIG_RAIZ.exists():
        shutil.copy2(_CONFIG_RAIZ, CONFIG_PATH)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT DEFAULT '',
            activo INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS atenciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            codigo_empresa TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS monedas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS carrito_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            precio_unitario REAL NOT NULL,
            peso_unitario REAL NOT NULL,
            cantidad REAL NOT NULL DEFAULT 1,
            unidad TEXT NOT NULL DEFAULT 'UND',
            tipo_galvanizado TEXT NOT NULL DEFAULT 'GO',
            porcentaje_ganancia TEXT NOT NULL DEFAULT '30'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cotizaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            fecha TEXT NOT NULL,
            cliente TEXT NOT NULL DEFAULT '',
            atencion TEXT NOT NULL DEFAULT '',
            proyecto TEXT NOT NULL DEFAULT '',
            moneda TEXT NOT NULL DEFAULT 'SOLES',
            total_precio REAL NOT NULL DEFAULT 0,
            total_peso REAL NOT NULL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cotizacion_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cotizacion_id INTEGER NOT NULL REFERENCES cotizaciones(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            precio_unitario REAL NOT NULL,
            peso_unitario REAL NOT NULL,
            cantidad INTEGER NOT NULL,
            unidad TEXT NOT NULL,
            tipo_galvanizado TEXT NOT NULL,
            porcentaje_ganancia TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reportes_asistencia (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo        TEXT NOT NULL UNIQUE,
            periodo_label  TEXT NOT NULL,
            fecha_subida   TEXT NOT NULL,
            subido_por     TEXT NOT NULL,
            nombre_archivo TEXT NOT NULL,
            num_empleados  INTEGER NOT NULL,
            datos_json     TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS email_imap_config (
            id       INTEGER PRIMARY KEY DEFAULT 1,
            host     TEXT NOT NULL DEFAULT '',
            port     INTEGER NOT NULL DEFAULT 993,
            username TEXT NOT NULL DEFAULT '',
            password TEXT NOT NULL DEFAULT '',
            folder   TEXT NOT NULL DEFAULT 'INBOX',
            days_back INTEGER NOT NULL DEFAULT 30
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS email_importados (
            message_id    TEXT PRIMARY KEY,
            proyecto      TEXT NOT NULL DEFAULT '',
            importado_at  TEXT NOT NULL
        )
    """)

    conn.commit()

    # Migraciones: agregar columnas nuevas si no existen (bases de datos existentes)
    _add_column_if_missing(conn, "clientes", "ruc", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "clientes", "ubicacion", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "clientes", "abreviacion", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "atenciones", "email", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "cotizaciones", "cliente_nombre", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "cotizaciones", "cliente_ruc", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "cotizaciones", "cliente_ubicacion", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "cotizaciones", "atencion_email", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "cotizaciones", "dolar_rate", "REAL NOT NULL DEFAULT 3.8")
    _add_column_if_missing(conn, "cotizaciones", "validez", "TEXT NOT NULL DEFAULT '30 días'")
    _add_column_if_missing(conn, "cotizaciones", "encabezado_tabla", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "usuarios", "rol", "TEXT NOT NULL DEFAULT 'USER'")
    _add_column_if_missing(conn, "usuarios", "ver_asistencias", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "carrito_items", "descripcion_calculada", "TEXT DEFAULT NULL")
    _add_column_if_missing(conn, "carrito_items", "posicion", "REAL DEFAULT NULL")
    _add_column_if_missing(conn, "carrito_items", "tapa_para_id", "INTEGER DEFAULT NULL")
    _add_column_if_missing(conn, "carrito_items", "precio_manual", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "cotizacion_items", "precio_manual", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "email_importados", "pdf_hash", "TEXT NOT NULL DEFAULT ''")
    _migrate_cantidad_to_real(conn)
    _add_column_if_missing(conn, "cotizaciones", "origen", "TEXT NOT NULL DEFAULT 'web'")
    # Promover al usuario admin a ADMIN si aún no lo es
    conn.execute("UPDATE usuarios SET rol='ADMIN' WHERE username='admin' AND rol='USER'")
    # ADMIN siempre tiene acceso a asistencias
    conn.execute("UPDATE usuarios SET ver_asistencias=1 WHERE rol='ADMIN'")
    conn.commit()

    # Crear usuario admin por defecto si no hay usuarios
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        _admin_pwd = os.environ.get("AROLUZ_ADMIN_PASSWORD") or "aroluz2024"
        _crear_usuario(conn, "admin", _admin_pwd, "Administrador", "ADMIN")
        print("Usuario admin creado. Cambiá la contraseña en /cuenta")

    # Seed inicial desde JSON si las tablas de catálogo están vacías
    c.execute("SELECT COUNT(*) FROM clientes")
    if c.fetchone()[0] == 0:
        _seed_desde_json(conn)
        conn.commit()

    # Poblar monedas por defecto si están vacías (fallback si JSON no tiene monedas)
    c.execute("SELECT COUNT(*) FROM monedas")
    if c.fetchone()[0] == 0:
        for m in ["SOLES", "DÓLARES"]:
            c.execute("INSERT OR IGNORE INTO monedas (nombre) VALUES (?)", (m,))
        conn.commit()

    # Índices para consultas frecuentes
    c.execute("CREATE INDEX IF NOT EXISTS idx_cotizaciones_username ON cotizaciones(username)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cotizaciones_fecha ON cotizaciones(fecha DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cotizaciones_proyecto ON cotizaciones(proyecto)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cotizacion_items_cotizacion_id ON cotizacion_items(cotizacion_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_carrito_items_username ON carrito_items(username)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_reportes_asistencia_periodo ON reportes_asistencia(periodo DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_atenciones_codigo_empresa ON atenciones(codigo_empresa)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_email_importados_pdf_hash ON email_importados(pdf_hash)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_email_importados_proyecto ON email_importados(proyecto)")
    conn.commit()

    conn.close()


def _seed_desde_json(conn):
    """Puebla clientes, atenciones y monedas desde catalogo_contactos.json (solo si están vacíos)."""
    json_path = str(BASE_DIR / "data" / "catalogo_contactos.json")
    if not os.path.exists(json_path):
        return
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    for c in data.get("clientes", []):
        conn.execute(
            "INSERT OR IGNORE INTO clientes (codigo, nombre, ruc, ubicacion) VALUES (?, ?, ?, ?)",
            (c["codigo"], c.get("nombre", c["codigo"]), c.get("ruc", ""), c.get("ubicacion", "")),
        )
    for a in data.get("atenciones", []):
        conn.execute(
            "INSERT OR IGNORE INTO atenciones (nombre, codigo_empresa, email) VALUES (?, ?, ?)",
            (a["nombre"], a["codigo_empresa"], a.get("email", "")),
        )
    for m in data.get("monedas", []):
        conn.execute(
            "INSERT OR IGNORE INTO monedas (nombre) VALUES (?)", (m,)
        )


def _crear_usuario(conn, username: str, password: str, nombre: str = "", rol: str = "USER", ver_asistencias: bool = False):
    ph = _hash_password(password)
    va = 1 if (rol == "ADMIN" or ver_asistencias) else 0
    conn.execute(
        "INSERT OR IGNORE INTO usuarios (username, password_hash, nombre, rol, ver_asistencias) VALUES (?, ?, ?, ?, ?)",
        (username, ph, nombre, rol, va),
    )
    conn.commit()


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=12)).decode()

