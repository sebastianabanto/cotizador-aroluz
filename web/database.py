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
import secrets
import shutil
import sqlite3
from datetime import datetime as _dt
from pathlib import Path
from typing import Optional, Dict, List, Any

import bcrypt as _bcrypt

# Ruta de la base de datos
BASE_DIR = Path(__file__).parent
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
        "espesor_tapa": "1.2",
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


def init_db():
    """Crea las tablas necesarias si no existen."""
    _backup_db()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Migrar config de la raíz a web/data/ si aún no existe allí
    if not CONFIG_PATH.exists() and _CONFIG_RAIZ.exists():
        shutil.copy2(_CONFIG_RAIZ, CONFIG_PATH)
    conn = sqlite3.connect(DB_PATH)
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
            cantidad INTEGER NOT NULL DEFAULT 1,
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

    conn.commit()

    # Migraciones: agregar columnas nuevas si no existen (bases de datos existentes)
    _add_column_if_missing(conn, "clientes", "ruc", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "clientes", "ubicacion", "TEXT NOT NULL DEFAULT ''")
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
    # Promover al usuario admin a ADMIN si aún no lo es
    conn.execute("UPDATE usuarios SET rol='ADMIN' WHERE username='admin' AND rol='USER'")
    # ADMIN siempre tiene acceso a asistencias
    conn.execute("UPDATE usuarios SET ver_asistencias=1 WHERE rol='ADMIN'")
    conn.commit()

    # Crear usuario admin por defecto si no hay usuarios
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        _crear_usuario(conn, "admin", "aroluz2024", "Administrador", "ADMIN")
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

    conn.close()


def _seed_desde_json(conn):
    """Puebla clientes, atenciones y monedas desde catalogo_contactos.json (solo si están vacíos)."""
    json_path = os.path.join(os.path.dirname(__file__), "data", "catalogo_contactos.json")
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


# ─────────────────────────────────────────────
# Usuarios
# ─────────────────────────────────────────────

def verificar_usuario(username: str, password: str) -> Optional[Dict]:
    """Devuelve el usuario si las credenciales son válidas, None si no.

    Soporta migración transparente SHA256 → bcrypt: en el primer login con hash
    SHA256 legado, re-hashea con bcrypt automáticamente.
    """
    conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
        _crear_usuario(conn, username, password, nombre, rol, ver_asistencias)
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def cambiar_password(username: str, nueva_password: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM usuarios WHERE username=?", (username,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

def cargar_config() -> Dict:
    """Carga configuración desde cotizador_config.json, mergeando con defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            return _fusionar(CONFIG_DEFECTO, cfg)
        except Exception:
            pass
    return dict(CONFIG_DEFECTO)


def guardar_config(config: Dict) -> bool:
    """Guarda configuración en cotizador_config.json."""
    try:
        backup = CONFIG_PATH.parent / "cotizador_config_backup.json"
        if CONFIG_PATH.exists():
            import shutil
            shutil.copy2(CONFIG_PATH, backup)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _fusionar(defecto: Dict, cargada: Dict) -> Dict:
    resultado = {**defecto}
    for k, v in cargada.items():
        if k in resultado and isinstance(v, dict):
            resultado[k] = {**resultado[k], **v}
        else:
            resultado[k] = v
    return resultado


# ─────────────────────────────────────────────
# Catálogo (clientes, atenciones, monedas)
# ─────────────────────────────────────────────

def obtener_catalogo() -> Dict[str, List]:
    """Devuelve clientes, atenciones y monedas desde SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    clientes = [dict(r) for r in conn.execute(
        "SELECT codigo, nombre, ruc, ubicacion FROM clientes ORDER BY codigo"
    ).fetchall()]
    atenciones = [dict(r) for r in conn.execute(
        "SELECT nombre, codigo_empresa, email FROM atenciones ORDER BY nombre"
    ).fetchall()]
    monedas = [r["nombre"] for r in conn.execute("SELECT nombre FROM monedas ORDER BY nombre").fetchall()]

    conn.close()
    return {"clientes": clientes, "atenciones": atenciones, "monedas": monedas}


def obtener_cliente(codigo: str) -> Optional[Dict]:
    """Devuelve un cliente por su código, o None si no existe."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT codigo, nombre, ruc, ubicacion FROM clientes WHERE codigo=?", (codigo,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def obtener_atenciones_de_cliente(codigo_cliente: str) -> List[Dict]:
    """Devuelve las atenciones asociadas a un cliente."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT nombre, codigo_empresa, email FROM atenciones WHERE codigo_empresa=? ORDER BY nombre",
        (codigo_cliente,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def importar_catalogo_desde_excel(ruta_excel: str) -> Dict[str, int]:
    """
    Lee clientes, atenciones y monedas desde el Excel (.xlsm) y los guarda en SQLite.

    Estructura de las hojas:
      CLIENTES:  A=CODIGO  B=RAZÓN SOCIAL  C=RUC  D=UBICACIÓN
      ATENCIÓN:  A=CODIGO  B=NOMBRES       C=CORREO  D=CELULAR  E=RAZON SOCIAL (codigo_empresa)
      MONEDA:    A=nombre

    Usa INSERT OR REPLACE para actualizar registros existentes con los datos completos.
    Retorna conteo de registros procesados.
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl no está instalado")

    if not os.path.exists(ruta_excel):
        raise FileNotFoundError(f"Excel no encontrado: {ruta_excel}")

    # keep_vba=True permite abrir .xlsm sin errores
    wb = openpyxl.load_workbook(ruta_excel, read_only=True, data_only=True, keep_vba=True)
    conn = sqlite3.connect(DB_PATH)
    conteo = {"clientes": 0, "atenciones": 0, "monedas": 0}

    def _s(val) -> str:
        return str(val).strip() if val is not None else ""

    # Clientes: A=codigo, B=razón social, C=RUC, D=ubicación
    if "CLIENTES" in wb.sheetnames:
        ws = wb["CLIENTES"]
        for row in ws.iter_rows(min_row=2, max_col=4, values_only=True):
            codigo = _s(row[0])
            if not codigo:
                continue
            nombre = _s(row[1]) or codigo
            ruc = _s(row[2])
            ubicacion = _s(row[3])
            conn.execute(
                """INSERT INTO clientes (codigo, nombre, ruc, ubicacion)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(codigo) DO UPDATE SET
                     nombre=excluded.nombre,
                     ruc=excluded.ruc,
                     ubicacion=excluded.ubicacion""",
                (codigo, nombre, ruc, ubicacion),
            )
            conteo["clientes"] += 1

    # Atenciones: A=codigo_interno, B=nombres, C=correo, D=celular, E=razon_social (codigo_empresa)
    if "ATENCIÓN" in wb.sheetnames:
        ws = wb["ATENCIÓN"]
        for row in ws.iter_rows(min_row=2, max_col=5, values_only=True):
            nombre = _s(row[1])        # col B — nombre completo de la persona
            email = _s(row[2])         # col C — correo
            codigo_emp = _s(row[4])    # col E — código empresa (vincula con CLIENTES)
            if not nombre or not codigo_emp:
                continue
            conn.execute(
                """INSERT INTO atenciones (nombre, codigo_empresa, email)
                   VALUES (?, ?, ?)
                   ON CONFLICT(nombre) DO UPDATE SET
                     codigo_empresa=excluded.codigo_empresa,
                     email=excluded.email""",
                (nombre, codigo_emp, email),
            )
            conteo["atenciones"] += 1

    # Monedas: A=nombre
    if "MONEDA" in wb.sheetnames:
        ws = wb["MONEDA"]
        for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
            val = _s(row[0])
            if val:
                conn.execute(
                    "INSERT OR IGNORE INTO monedas (nombre) VALUES (?)", (val,)
                )
                conteo["monedas"] += 1

    conn.commit()
    conn.close()
    wb.close()
    return conteo


def agregar_cliente(codigo: str, nombre: str = "", ruc: str = "", ubicacion: str = "") -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO clientes (codigo, nombre, ruc, ubicacion) VALUES (?, ?, ?, ?)",
            (codigo.strip(), nombre.strip() or codigo.strip(), ruc.strip(), ubicacion.strip()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def agregar_atencion(nombre: str, codigo_empresa: str, email: str = "") -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO atenciones (nombre, codigo_empresa, email) VALUES (?, ?, ?)",
            (nombre.strip(), codigo_empresa.strip(), email.strip()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def eliminar_cliente(codigo: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM clientes WHERE codigo = ?", (codigo,))
    conn.commit()
    conn.close()
    return True


def eliminar_atencion(nombre: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM atenciones WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()
    return True


def editar_cliente(codigo: str, nuevo_nombre: str, ruc: str = "", ubicacion: str = "") -> bool:
    """Actualiza nombre, RUC y dirección de un cliente existente."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE clientes SET nombre=?, ruc=?, ubicacion=? WHERE codigo=?",
            (nuevo_nombre.strip(), ruc.strip(), ubicacion.strip(), codigo.strip()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def editar_atencion(nombre_actual: str, nuevo_nombre: str, nuevo_codigo_empresa: str, email: str = "") -> bool:
    """Actualiza nombre, código de empresa y email de una atención."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE atenciones SET nombre=?, codigo_empresa=?, email=? WHERE nombre=?",
            (nuevo_nombre.strip(), nuevo_codigo_empresa.strip(), email.strip(), nombre_actual.strip()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def exportar_contactos_xlsx() -> bytes:
    """
    Exporta clientes, atenciones y monedas a un .xlsx con 3 hojas.
    Retorna los bytes del archivo para streaming.

    Hojas:
      CLIENTES:   codigo · nombre · ruc · ubicacion
      ATENCIONES: nombre · codigo_empresa · email
      MONEDAS:    nombre
    """
    try:
        import openpyxl
        from openpyxl.styles import Font
    except ImportError:
        raise ImportError("openpyxl no está instalado")

    from io import BytesIO

    catalogo = obtener_catalogo()

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # quitar hoja vacía por defecto

    bold = Font(bold=True)

    # Hoja CLIENTES
    ws_cli = wb.create_sheet("CLIENTES")
    headers_cli = ["codigo", "nombre", "ruc", "ubicacion"]
    for col, h in enumerate(headers_cli, 1):
        cell = ws_cli.cell(row=1, column=col, value=h)
        cell.font = bold
    for row_idx, c in enumerate(catalogo["clientes"], 2):
        ws_cli.cell(row=row_idx, column=1, value=c.get("codigo", ""))
        ws_cli.cell(row=row_idx, column=2, value=c.get("nombre", ""))
        ws_cli.cell(row=row_idx, column=3, value=c.get("ruc", ""))
        ws_cli.cell(row=row_idx, column=4, value=c.get("ubicacion", ""))

    # Hoja ATENCIONES
    ws_ate = wb.create_sheet("ATENCIONES")
    headers_ate = ["nombre", "codigo_empresa", "email"]
    for col, h in enumerate(headers_ate, 1):
        cell = ws_ate.cell(row=1, column=col, value=h)
        cell.font = bold
    for row_idx, a in enumerate(catalogo["atenciones"], 2):
        ws_ate.cell(row=row_idx, column=1, value=a.get("nombre", ""))
        ws_ate.cell(row=row_idx, column=2, value=a.get("codigo_empresa", ""))
        ws_ate.cell(row=row_idx, column=3, value=a.get("email", ""))

    # Hoja MONEDAS
    ws_mon = wb.create_sheet("MONEDAS")
    cell = ws_mon.cell(row=1, column=1, value="nombre")
    cell.font = bold
    for row_idx, m in enumerate(catalogo["monedas"], 2):
        ws_mon.cell(row=row_idx, column=1, value=m)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def importar_contactos_desde_xlsx(contenido_bytes: bytes) -> Dict[str, int]:
    """
    Lee un .xlsx exportado por exportar_contactos_xlsx() e importa/actualiza
    clientes, atenciones y monedas en SQLite.

    Estructura esperada:
      Hoja CLIENTES:   col A=codigo, B=nombre, C=ruc, D=ubicacion
      Hoja ATENCIONES: col A=nombre, B=codigo_empresa, C=email
      Hoja MONEDAS:    col A=nombre

    Ignora filas donde la columna A esté vacía (encabezados u hojas vacías).
    Retorna conteo de filas procesadas por hoja.
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl no está instalado")

    from io import BytesIO

    wb = openpyxl.load_workbook(BytesIO(contenido_bytes), read_only=True, data_only=True)
    conn = sqlite3.connect(DB_PATH)
    conteo = {"clientes": 0, "atenciones": 0, "monedas": 0}

    def _s(val) -> str:
        return str(val).strip() if val is not None else ""

    # Hoja CLIENTES
    if "CLIENTES" in wb.sheetnames:
        ws = wb["CLIENTES"]
        for row in ws.iter_rows(min_row=2, max_col=4, values_only=True):
            codigo = _s(row[0]) if len(row) > 0 else ""
            if not codigo:
                continue
            nombre = _s(row[1]) if len(row) > 1 else ""
            ruc = _s(row[2]) if len(row) > 2 else ""
            ubicacion = _s(row[3]) if len(row) > 3 else ""
            conn.execute(
                """INSERT INTO clientes (codigo, nombre, ruc, ubicacion)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(codigo) DO UPDATE SET
                     nombre=excluded.nombre,
                     ruc=excluded.ruc,
                     ubicacion=excluded.ubicacion""",
                (codigo, nombre or codigo, ruc, ubicacion),
            )
            conteo["clientes"] += 1

    # Hoja ATENCIONES
    if "ATENCIONES" in wb.sheetnames:
        ws = wb["ATENCIONES"]
        for row in ws.iter_rows(min_row=2, max_col=3, values_only=True):
            nombre = _s(row[0]) if len(row) > 0 else ""
            if not nombre:
                continue
            codigo_empresa = _s(row[1]) if len(row) > 1 else ""
            email = _s(row[2]) if len(row) > 2 else ""
            conn.execute(
                """INSERT INTO atenciones (nombre, codigo_empresa, email)
                   VALUES (?, ?, ?)
                   ON CONFLICT(nombre) DO UPDATE SET
                     codigo_empresa=excluded.codigo_empresa,
                     email=excluded.email""",
                (nombre, codigo_empresa, email),
            )
            conteo["atenciones"] += 1

    # Hoja MONEDAS
    if "MONEDAS" in wb.sheetnames:
        ws = wb["MONEDAS"]
        for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
            val = _s(row[0]) if len(row) > 0 else ""
            if val:
                conn.execute("INSERT OR IGNORE INTO monedas (nombre) VALUES (?)", (val,))
                conteo["monedas"] += 1

    conn.commit()
    conn.close()
    wb.close()
    return conteo


def importar_catalogo_desde_json(ruta: str) -> Dict[str, int]:
    """
    Lee clientes, atenciones y monedas desde un JSON y los inserta en SQLite (INSERT OR IGNORE).
    Retorna conteo de registros procesados.
    """
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    with open(ruta, encoding="utf-8") as f:
        data = json.load(f)
    conn = sqlite3.connect(DB_PATH)
    conteo = {"clientes": 0, "atenciones": 0, "monedas": 0}
    for c in data.get("clientes", []):
        conn.execute(
            "INSERT OR IGNORE INTO clientes (codigo, nombre) VALUES (?, ?)",
            (c["codigo"], c.get("nombre", c["codigo"])),
        )
        conteo["clientes"] += 1
    for a in data.get("atenciones", []):
        conn.execute(
            "INSERT OR IGNORE INTO atenciones (nombre, codigo_empresa) VALUES (?, ?)",
            (a["nombre"], a["codigo_empresa"]),
        )
        conteo["atenciones"] += 1
    for m in data.get("monedas", []):
        conn.execute(
            "INSERT OR IGNORE INTO monedas (nombre) VALUES (?)", (m,)
        )
        conteo["monedas"] += 1
    conn.commit()
    conn.close()
    return conteo


# ─────────────────────────────────────────────
# Carrito persistente
# ─────────────────────────────────────────────

def get_carrito_db(username: str) -> List[Dict]:
    """Devuelve los items del carrito del usuario desde SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM carrito_items WHERE username=? ORDER BY id",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_item_carrito_db(username: str, item: Dict) -> int:
    """Inserta un item en el carrito. Retorna el id generado."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """INSERT INTO carrito_items
           (username, tipo, descripcion, precio_unitario, peso_unitario,
            cantidad, unidad, tipo_galvanizado, porcentaje_ganancia)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        ),
    )
    item_id = c.lastrowid
    conn.commit()
    conn.close()
    return item_id


def update_cantidad_carrito_db(item_id: int, username: str, cantidad: int) -> bool:
    """Actualiza la cantidad de un item. Retorna True si se actualizó."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE carrito_items SET cantidad=? WHERE id=? AND username=?",
        (cantidad, item_id, username),
    )
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_item_precio_carrito_db(item_id: int, username: str, precio_unitario: float, peso_unitario: float, descripcion: str) -> bool:
    """Actualiza precio, peso y descripción de un item del carrito."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE carrito_items SET precio_unitario=?, peso_unitario=?, descripcion=? WHERE id=? AND username=?",
        (round(precio_unitario, 4), round(peso_unitario, 6), descripcion, item_id, username),
    )
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_item_carrito_db(item_id: int, username: str) -> bool:
    """Elimina un item del carrito. Retorna True si se eliminó."""
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM carrito_items WHERE username=?", (username,))
    conn.commit()
    conn.close()


def cargar_cotizacion_al_carrito_db(cotizacion_id: int, username: str, require_ownership: bool = True) -> Optional[Dict]:
    """
    Limpia el carrito del usuario y copia los items de una cotización guardada.
    Devuelve los metadatos de la cotización para pre-llenar el formulario del carrito.
    Si require_ownership=False (admin), permite cargar cualquier cotización.
    Retorna None si la cotización no existe o (con require_ownership=True) no pertenece al usuario.
    """
    conn = sqlite3.connect(DB_PATH)
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
                cantidad, unidad, tipo_galvanizado, porcentaje_ganancia)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                username, item["tipo"], item["descripcion"],
                item["precio_unitario"], item["peso_unitario"],
                item["cantidad"], item["unidad"],
                item["tipo_galvanizado"], item["porcentaje_ganancia"],
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

    conn = sqlite3.connect(DB_PATH)
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
                cantidad, unidad, tipo_galvanizado, porcentaje_ganancia)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            ),
        )
    conn.commit()
    conn.close()
    return cotizacion_id


def listar_cotizaciones_db(
    username: Optional[str] = None,
    tipos: Optional[List[str]] = None,
    q: str = "",
) -> List[Dict]:
    """Lista cotizaciones guardadas con conteo de items.

    Params:
        username — filtra por usuario (obligatorio en uso normal)
        tipos    — lista de códigos de tipo (B, CH, …); si no está vacía, sólo
                   devuelve cotizaciones que contengan al menos uno de esos tipos
        q        — texto libre; filtra cotizaciones cuya descripción de ítem contenga
                   este texto (case-insensitive)
    """
    conn = sqlite3.connect(DB_PATH)
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
        conditions.append(
            "EXISTS (SELECT 1 FROM cotizacion_items ci3"
            " WHERE ci3.cotizacion_id = c.id AND LOWER(ci3.descripcion) LIKE ?)"
        )
        params.append(f"%{q.lower()}%")

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


def get_cotizacion_db(cotizacion_id: int) -> Optional[Dict]:
    """Devuelve cabecera + items de una cotización guardada."""
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    _add_column_if_missing(conn, "proyectos", "direccion", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "cliente",  "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "numero_oc", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyectos", "created_at", "TEXT")
    _add_column_if_missing(conn, "proyectos", "contacto",  "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "proyecto_adjuntos", "categoria", "TEXT NOT NULL DEFAULT 'oc'")
    conn.commit()
    conn.close()
    ADJUNTOS_DIR.mkdir(parents=True, exist_ok=True)


def get_proyectos_con_stats() -> List[Dict]:
    """Lista todos los proyectos con estadísticas, conteo de adjuntos e items OC."""
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE proyectos SET estado=?, updated_at=? WHERE nombre=?",
        (estado, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nombre),
    )
    conn.commit()
    conn.close()


def get_kpis_proyectos() -> Dict:
    """KPIs del pipeline: proyectos aprobados, en producción, despachados e items pendientes."""
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE proyectos SET direccion=? WHERE nombre=?",
        (direccion.strip(), nombre),
    )
    conn.commit()
    conn.close()


def update_proyecto_contacto(nombre: str, contacto: str):
    """Actualiza el contacto de la obra."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE proyectos SET contacto=? WHERE nombre=?",
        (contacto.strip(), nombre),
    )
    conn.commit()
    conn.close()


def update_proyecto_numero_oc(nombre: str, numero_oc: str):
    """Actualiza el número de orden de compra de la obra."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE proyectos SET numero_oc=? WHERE nombre=?",
        (numero_oc.strip(), nombre),
    )
    conn.commit()
    conn.close()


# ── Adjuntos ──

def add_adjunto(proyecto: str, filename: str, filepath: str, content_type: str = "", categoria: str = "oc") -> int:
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT filepath, filename, content_type FROM proyecto_adjuntos WHERE id=? AND proyecto=?",
        (adjunto_id, proyecto),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_adjunto(adjunto_id: int) -> Optional[str]:
    """Elimina el registro y retorna el filepath para borrar el archivo físico."""
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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


def crear_proyecto(nombre: str, cliente: str) -> bool:
    """Crea un proyecto manualmente en estado APROBADO. Retorna False si ya existe."""
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO proyectos (nombre, cliente, estado, created_at) VALUES (?, ?, 'APROBADO', ?)",
        (nombre.strip(), cliente.strip(), datetime.now().strftime("%Y-%m-%d")),
    )
    created = c.rowcount > 0
    conn.commit()
    conn.close()
    return created


def eliminar_proyecto(nombre: str) -> bool:
    """Elimina un proyecto, sus adjuntos físicos y sus items OC."""
    conn = sqlite3.connect(DB_PATH)
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
    conn.execute("DELETE FROM proyectos WHERE nombre=?", (nombre,))
    deleted = conn.total_changes > 0
    conn.commit()
    conn.close()
    return deleted


# ── OC Items CRUD ──

def get_oc_items(proyecto: str) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "DELETE FROM proyecto_oc_items WHERE id=? AND proyecto=?",
        (item_id, proyecto),
    )
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# Inicializar al importar
init_db()
init_proyectos()
