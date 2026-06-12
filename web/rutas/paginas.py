# -*- coding: utf-8 -*-
"""Rutas HTML: login, home, cotizar, carrito, historial, catálogo, changelog, mi-config, usuarios, cuenta — extraído de web/main.py (refactor jun 2026)."""
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
from web.rutas.carrito import get_carrito
from web.validators import validar_ruc

router = APIRouter()

# ─────────────────────────────────────────────
# Login / Logout
# ─────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    session = get_session(request)
    if session:
        return RedirectResponse("/home", status_code=302)
    error = "Sesión cerrada por inactividad." if request.query_params.get("timeout") == "1" else None
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
@limiter.limit("5/minute")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = verificar_usuario(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuario o contraseña incorrectos"},
            status_code=401,
        )
    response = RedirectResponse("/home", status_code=302)
    set_session_cookie(response, user["username"], user.get("nombre", ""), user.get("rol", "USER"), user.get("ver_asistencias", False))
    return response


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse("/login", status_code=302)
    clear_session_cookie(response)
    return response


@router.get("/api/heartbeat")
async def heartbeat(usuario = Depends(get_session)):
    return {"ok": True}


# ─────────────────────────────────────────────
# Redirect raíz
# ─────────────────────────────────────────────

@router.get("/")
async def root(request: Request):
    session = get_session(request)
    if session:
        return RedirectResponse("/home", status_code=302)
    return RedirectResponse("/login", status_code=302)


# ─────────────────────────────────────────────
# Página Home
# ─────────────────────────────────────────────

@router.get("/home", response_class=HTMLResponse)
async def home_page(request: Request, usuario: dict = Depends(require_login)):
    kpis = get_kpis_proyectos()
    proyectos = get_proyectos_con_stats()
    catalogo = obtener_catalogo()
    return templates.TemplateResponse(
        "home.html",
        ctx(
            request, usuario,
            active="home",
            kpis=kpis,
            proyectos=proyectos,
            ESTADOS_KANBAN=ESTADOS_KANBAN,
            ESTADO_LABELS=ESTADO_LABELS,
            catalogo=catalogo,
        ),
    )

# ─────────────────────────────────────────────
# Página Cotización
# ─────────────────────────────────────────────

@router.get("/planchas", response_class=HTMLResponse)
async def planchas_page(request: Request, usuario: dict = Depends(require_login)):
    config = cargar_config()
    valores = config.get("valores_defecto", {})
    return templates.TemplateResponse(
        "cotizacion/planchas.html",
        ctx(request, usuario, active="planchas", config=valores),
    )


@router.get("/cotizar", response_class=HTMLResponse)
async def cotizar_page(request: Request, usuario: dict = Depends(require_login)):
    config = cargar_config()
    valores = config.get("valores_defecto", {})
    return templates.TemplateResponse(
        "cotizacion/cotizacion.html",
        ctx(request, usuario, config=valores),
    )


# ─────────────────────────────────────────────
# Página Carrito
# ─────────────────────────────────────────────

@router.get("/carrito", response_class=HTMLResponse)
async def carrito_page(request: Request, usuario: dict = Depends(require_login)):
    carrito = get_carrito(usuario["u"])
    catalogo = obtener_catalogo()
    config = cargar_config()
    total = sum(i["precio_unitario"] * i["cantidad"] for i in carrito)
    peso_total = sum(i["peso_unitario"] * i["cantidad"] for i in carrito)

    dolar = config.get("valores_defecto", {}).get("dolar", 3.8)
    return templates.TemplateResponse(
        "cotizacion/carrito.html",
        ctx(
            request,
            usuario,
            carrito=carrito,
            total=round(total, 2),
            peso_total=round(peso_total, 4),
            catalogo=catalogo,
            dolar=dolar,
        ),
    )


# ─────────────────────────────────────────────
# Página Historial
# ─────────────────────────────────────────────

@router.get("/historial", response_class=HTMLResponse)
async def historial_page(request: Request, usuario: dict = Depends(require_login)):
    config = cargar_config()
    if not _permiso_usuario(usuario, "ver_historial", config):
        return RedirectResponse("/cotizar?msg=nopermiso", status_code=303)
    es_admin = usuario.get("r") == "ADMIN"
    return templates.TemplateResponse(
        "cotizacion/historial.html",
        ctx(request, usuario, es_admin=es_admin),
    )


# ─────────────────────────────────────────────
# Página Catálogo
# ─────────────────────────────────────────────

@router.get("/catalogo", response_class=HTMLResponse)
async def catalogo_page(request: Request, usuario: dict = Depends(require_login)):
    config = cargar_config()
    if not _permiso_usuario(usuario, "ver_catalogo", config):
        return RedirectResponse("/cotizar?msg=nopermiso", status_code=303)
    ruta_json = Path(__file__).resolve().parent.parent.parent / "catalogo_productos.json"
    try:
        with open(ruta_json, encoding="utf-8") as f:
            catalogo_productos = json.load(f)
    except Exception:
        catalogo_productos = {"categorias": []}
    return templates.TemplateResponse(
        "cotizacion/catalogo.html",
        ctx(request, usuario, catalogo_productos=catalogo_productos),
    )


# ─────────────────────────────────────────────
# Página Changelog
# ─────────────────────────────────────────────

@router.get("/changelog", response_class=HTMLResponse)
async def changelog_page(request: Request, usuario: dict = Depends(require_admin)):
    return templates.TemplateResponse(
        "changelog.html",
        ctx(request, usuario, versiones=_CHANGELOG),
    )


# ─────────────────────────────────────────────
# Página Mi Configuración (accesible para todos los roles)
# Solo permite editar precios de plancha y cambiar contraseña
# ─────────────────────────────────────────────

@router.get("/mi-config", response_class=HTMLResponse)
async def mi_config_page(request: Request, usuario: dict = Depends(require_login)):
    config = cargar_config()
    return templates.TemplateResponse(
        "mi_config.html",
        ctx(request, usuario, config=config),
    )


@router.post("/mi-config/guardar_planchas")
async def mi_config_guardar_planchas(
    usuario: dict = Depends(require_login),
    go_12: float = Form(...),
    go_15: float = Form(...),
    go_20: float = Form(...),
    gc_12: float = Form(...),
    gc_15: float = Form(...),
    gc_20: float = Form(...),
):
    valores = [go_12, go_15, go_20, gc_12, gc_15, gc_20]
    if any(v <= 0 for v in valores):
        return JSONResponse({"ok": False, "error": "Los precios deben ser mayores a cero"}, status_code=422)
    config = cargar_config()
    config["valores_defecto"]["precios_go"] = {"1.2": go_12, "1.5": go_15, "2.0": go_20}
    config["valores_defecto"]["precios_gc"] = {"1.2": gc_12, "1.5": gc_15, "2.0": gc_20}
    ok = guardar_config(config)
    return JSONResponse({"ok": ok})


@router.post("/mi-config/cambiar_password")
@limiter.limit("5/minute")
async def mi_config_cambiar_password(
    request: Request,
    usuario: dict = Depends(require_login),
    password_actual: str = Form(...),
    password_nuevo: str = Form(...),
    password_confirmar: str = Form(...),
):
    from web.database import verificar_usuario as ver
    if password_nuevo != password_confirmar:
        return JSONResponse({"ok": False, "error": "Las contraseñas nuevas no coinciden"}, status_code=422)
    if len(password_nuevo) < 8:
        return JSONResponse({"ok": False, "error": "La contraseña debe tener al menos 8 caracteres"}, status_code=422)
    if not ver(usuario["u"], password_actual):
        return JSONResponse({"ok": False, "error": "Contraseña actual incorrecta"}, status_code=401)
    ok = cambiar_password(usuario["u"], password_nuevo)
    return JSONResponse({"ok": ok})


# ─────────────────────────────────────────────
# Página Usuarios (solo ADMIN)
# ─────────────────────────────────────────────

@router.get("/usuarios", response_class=HTMLResponse)
async def usuarios_page(request: Request, usuario: dict = Depends(require_admin)):
    usuarios = listar_usuarios()
    config = cargar_config()
    permisos_usuario = config.get("permisos_usuario", {"ver_historial": True, "ver_catalogo": True})
    return templates.TemplateResponse(
        "usuarios.html",
        ctx(request, usuario, usuarios=usuarios, permisos_usuario=permisos_usuario),
    )


# ─────────────────────────────────────────────
# Página Mi Cuenta (accesible para todos los roles)
# ─────────────────────────────────────────────

@router.get("/cuenta", response_class=HTMLResponse)
async def cuenta_page(request: Request, usuario: dict = Depends(require_login)):
    return templates.TemplateResponse(
        "cuenta.html",
        ctx(request, usuario),
    )


@router.post("/cuenta/cambiar_password")
@limiter.limit("5/minute")
async def cuenta_cambiar_password(
    request: Request,
    usuario: dict = Depends(require_login),
    password_actual: str = Form(...),
    password_nuevo: str = Form(...),
    password_confirmar: str = Form(...),
):
    from web.database import verificar_usuario as ver
    if password_nuevo != password_confirmar:
        return templates.TemplateResponse(
            "cuenta.html",
            ctx(request, usuario, error="Las contraseñas nuevas no coinciden"),
        )
    if len(password_nuevo) < 8:
        return templates.TemplateResponse(
            "cuenta.html",
            ctx(request, usuario, error="La contraseña debe tener al menos 8 caracteres"),
        )
    if not ver(usuario["u"], password_actual):
        return templates.TemplateResponse(
            "cuenta.html",
            ctx(request, usuario, error="Contraseña actual incorrecta"),
        )
    ok = cambiar_password(usuario["u"], password_nuevo)
    if ok:
        return templates.TemplateResponse(
            "cuenta.html",
            ctx(request, usuario, exito="Contraseña actualizada correctamente"),
        )
    return templates.TemplateResponse(
        "cuenta.html",
        ctx(request, usuario, error="Error al cambiar la contraseña"),
    )

