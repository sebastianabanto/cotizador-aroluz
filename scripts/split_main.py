# -*- coding: utf-8 -*-
"""Split de web/main.py → routers (fase 4b). Extrae rangos, convierte @app. → @router.
y reporta nombres sin definir vía AST."""
import ast
import builtins
from pathlib import Path

SRC = Path("web/main.py")
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

# Rangos 1-indexados inclusivos (pueden ser varios por módulo)
MODULES = {
    "paginas":      [(139, 216), (537, 636), (1336, 1452)],
    "proyectos":    [(218, 524)],
    "config_admin": [(638, 1334)],
}

DOCS = {
    "paginas":      "Rutas HTML: login, home, cotizar, carrito, historial, catálogo, changelog, mi-config, usuarios, cuenta",
    "proyectos":    "API de proyectos/kanban: estado, adjuntos, OC items, crear/eliminar",
    "config_admin": "Configuración (ADMIN): precios, catálogo, clientes/atenciones, contactos, usuarios",
}

HEADER = '''# -*- coding: utf-8 -*-
"""{doc} — extraído de web/main.py (refactor jun 2026)."""
import io
import json
import os
import shutil as _shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import (
    HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse, FileResponse,
)

from web.auth import (
    require_login, require_admin, require_asistencias, get_session,
    verificar_usuario, set_session_cookie, clear_session_cookie,
)
from web.database import (
    cargar_config, guardar_config, obtener_catalogo,
    importar_catalogo_desde_excel, importar_catalogo_desde_json,
    exportar_contactos_xlsx, importar_contactos_desde_xlsx,
    agregar_cliente, agregar_atencion,
    eliminar_cliente, eliminar_atencion,
    editar_cliente, editar_atencion,
    obtener_cliente, obtener_atenciones_de_cliente,
    crear_usuario, cambiar_password, listar_usuarios,
    editar_usuario, toggle_activo_usuario, eliminar_usuario,
    get_kpis_proyectos, get_proyectos_con_stats, set_proyecto_estado,
    update_proyecto_direccion, update_proyecto_numero_oc, update_proyecto_contacto,
    update_proyecto_notas, renombrar_proyecto,
    add_adjunto, list_adjuntos, get_adjunto_filepath, delete_adjunto,
    crear_proyecto, eliminar_proyecto,
    get_oc_items, add_oc_item, update_oc_item, delete_oc_item,
    ESTADOS_KANBAN, ESTADO_LABELS, ADJUNTOS_DIR,
)
from web.changelog import VERSIONES as _CHANGELOG
from web.limits import limiter
from web.plantillas import templates, ctx, _permiso_usuario
from web.validators import validar_ruc

router = APIRouter()

'''

for name, ranges in MODULES.items():
    body = "".join("".join(lines[a - 1:b]) for a, b in ranges)
    body = body.replace("@app.", "@router.")
    src = HEADER.format(doc=DOCS[name]) + body
    Path(f"web/rutas/{name}.py").write_text(src, encoding="utf-8", newline="\n")

# ── AST: nombres sin definir ─────────────────────────────────────────────────
def undefined(src):
    tree = ast.parse(src)
    defined = set(dir(builtins)) | {"__file__", "__name__"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = node.args
            for arg in list(a.args) + list(a.posonlyargs) + list(a.kwonlyargs):
                defined.add(arg.arg)
            if a.vararg: defined.add(a.vararg.arg)
            if a.kwarg: defined.add(a.kwarg.arg)
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
        elif isinstance(node, (ast.For,)):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    defined.add(sub.id)
        elif isinstance(node, ast.comprehension):
            for sub in ast.walk(node.target):
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
        elif isinstance(node, ast.Global):
            defined.update(node.names)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return sorted(used - defined)

for name in MODULES:
    miss = undefined(Path(f"web/rutas/{name}.py").read_text(encoding="utf-8"))
    if miss:
        print(f"[{name}] sin definir: {miss}")
print("split main OK")
