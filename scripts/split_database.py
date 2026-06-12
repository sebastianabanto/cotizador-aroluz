# -*- coding: utf-8 -*-
"""Split mecánico de web/database.py → web/db/ (fase 4a del refactor).

Divide por rangos de líneas, agrega encabezado de imports a cada módulo y
reporta nombres sin definir (análisis AST) para detectar dependencias cruzadas.
"""
import ast
import builtins
from pathlib import Path

SRC = Path("web/database.py")
DST = Path("web/db")

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

# Rangos 1-indexados inclusivos
RANGES = {
    "core":        (1, 344),
    "usuarios":    (346, 466),
    "config":      (468, 526),
    "catalogo":    (528, 907),
    "carrito":     (909, 1203),
    "historial":   (1205, 1820),
    "proyectos":   (1822, 2222),
    "asistencias": (2224, 2350),
    "email":       (2352, 2489),
}

HEADER = '''# -*- coding: utf-8 -*-
"""{doc} — extraído de web/database.py (refactor jun 2026)."""
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

'''

DOCS = {
    "usuarios":    "Usuarios: autenticación y CRUD",
    "config":      "Config de precios: cargar/guardar cotizador_config.json (con cache)",
    "catalogo":    "Catálogo: clientes, atenciones, monedas, import/export Excel-JSON",
    "carrito":     "Carrito persistente por usuario",
    "historial":   "Historial de cotizaciones, estadísticas, tendencias y duplicados",
    "proyectos":   "Proyectos/kanban, adjuntos y OC items",
    "asistencias": "Reportes de asistencia",
    "email":       "Config IMAP (contraseña cifrada) y emails importados",
}

DST.mkdir(exist_ok=True)

mod_sources = {}
for name, (a, b) in RANGES.items():
    body = "".join(lines[a - 1:b])
    if name == "core":
        src = body  # conserva su propio encabezado original
    else:
        src = HEADER.format(doc=DOCS[name]) + body
    mod_sources[name] = src
    (DST / f"{name}.py").write_text(src, encoding="utf-8", newline="\n")

# __init__.py vacío (los imports los hace la fachada)
(DST / "__init__.py").write_text("", encoding="utf-8")

# ── Análisis de nombres sin definir ──────────────────────────────────────────
def defined_and_used(src):
    tree = ast.parse(src)
    defined = set(dir(builtins)) | {"__file__", "__name__"}
    used = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
            for arg in getattr(node.args, "args", []) if hasattr(node, "args") else []:
                pass
        elif isinstance(node, ast.Import):
            for n in node.names:
                defined.add((n.asname or n.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for n in node.names:
                defined.add(n.asname or n.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Name):
                        defined.add(sub.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)
        elif isinstance(node, ast.Global):
            defined.update(node.names)
    # nombres locales: argumentos y asignaciones dentro de funciones también caen
    # en "defined" vía el walk de Assign; los args:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = node.args
            for arg in list(a.args) + list(a.posonlyargs) + list(a.kwonlyargs):
                defined.add(arg.arg)
            if a.vararg: defined.add(a.vararg.arg)
            if a.kwarg: defined.add(a.kwarg.arg)
        elif isinstance(node, (ast.For, ast.comprehension)):
            tgt = node.target if isinstance(node, ast.For) else node.target
            for sub in ast.walk(tgt):
                if isinstance(sub, ast.Name):
                    defined.add(sub.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            defined.add(node.name)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars:
                    for sub in ast.walk(item.optional_vars):
                        if isinstance(sub, ast.Name):
                            defined.add(sub.id)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.append(node.id)
    return defined, used

for name, src in mod_sources.items():
    defined, used = defined_and_used(src)
    missing = sorted({u for u in used if u not in defined})
    if missing:
        print(f"[{name}] sin definir: {missing}")
print("split OK")
