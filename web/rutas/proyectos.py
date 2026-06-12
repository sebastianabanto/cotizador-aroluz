# -*- coding: utf-8 -*-
"""API de proyectos/kanban: estado, adjuntos, OC items, crear/eliminar — extraído de web/main.py (refactor jun 2026)."""
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

# ─────────────────────────────────────────────
# API — Proyectos: estado, dirección, adjuntos
# ─────────────────────────────────────────────

@router.put("/api/proyecto/{nombre}/estado")
async def api_set_proyecto_estado(
    nombre: str,
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
        estado = body.get("estado", "")
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    if estado not in ESTADOS_KANBAN:
        return JSONResponse({"ok": False, "error": "Estado inválido"}, status_code=422)
    set_proyecto_estado(nombre, estado)
    return JSONResponse({"ok": True})


@router.patch("/api/proyecto/{nombre}/numero-oc")
async def api_update_numero_oc(
    nombre: str,
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
        numero_oc = body.get("numero_oc", "")
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    update_proyecto_numero_oc(nombre, numero_oc)
    return JSONResponse({"ok": True})


@router.patch("/api/proyecto/{nombre}/contacto")
async def api_update_contacto(
    nombre: str,
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
        contacto = body.get("contacto", "")
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    update_proyecto_contacto(nombre, contacto)
    return JSONResponse({"ok": True})


@router.patch("/api/proyecto/{nombre}/notas")
async def api_update_notas(
    nombre: str,
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
        notas = body.get("notas", "")
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    if len(notas) > 10_000:
        return JSONResponse({"ok": False, "error": "Notas demasiado largas."}, status_code=422)
    update_proyecto_notas(nombre, notas)
    return JSONResponse({"ok": True})


@router.patch("/api/proyecto/{nombre}/info")
async def api_update_proyecto_info(
    nombre: str,
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
        nuevo_nombre = body.get("nuevo_nombre", nombre)
        nuevo_cliente = body.get("nuevo_cliente", "")
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    ok = renombrar_proyecto(nombre, nuevo_nombre, nuevo_cliente)
    if not ok:
        return JSONResponse({"ok": False, "error": "Nombre duplicado o vacío"}, status_code=409)
    return JSONResponse({"ok": True, "nuevo_nombre": nuevo_nombre.strip()})


@router.patch("/api/proyecto/{nombre}/direccion")
async def api_update_direccion(
    nombre: str,
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
        direccion = body.get("direccion", "")
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    update_proyecto_direccion(nombre, direccion)
    return JSONResponse({"ok": True})


@router.get("/api/proyecto/{nombre}/adjuntos")
async def api_list_adjuntos(nombre: str, usuario: dict = Depends(require_login)):
    return JSONResponse({"ok": True, "adjuntos": list_adjuntos(nombre)})


@router.post("/api/proyecto/{nombre}/adjunto")
async def api_upload_adjunto(
    nombre: str,
    usuario: dict = Depends(require_login),
    archivo: UploadFile = File(...),
    categoria: str = Form("oc"),
):
    import shutil as _shutil
    ext = Path(archivo.filename or "").suffix.lower()
    if ext not in {".pdf", ".jpg", ".jpeg", ".png", ".webp"}:
        return JSONResponse(
            {"ok": False, "error": "Tipo no permitido. Use PDF, JPG o PNG."},
            status_code=422,
        )
    cat = categoria if categoria in ("oc", "ev") else "oc"
    slug = "".join(c if c.isalnum() or c in "-_. " else "_" for c in nombre)[:60]
    dest_dir = ADJUNTOS_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    import unicodedata as _ud
    from datetime import datetime as _dt2
    ts = _dt2.now().strftime("%Y%m%d_%H%M%S")
    _raw_name = Path(archivo.filename or "archivo").name
    # Normalizar Unicode (ej. tildes, ñ) a ASCII básico, reemplazar caracteres no seguros
    _ascii_name = _ud.normalize("NFKD", _raw_name).encode("ascii", "ignore").decode("ascii")
    _ascii_name = "".join(c if c.isalnum() or c in "-_. " else "_" for c in _ascii_name).strip() or "archivo"

    _es_imagen = ext in {".jpg", ".jpeg", ".png", ".webp"}

    if _es_imagen:
        # Imágenes → comprimir con Pillow: máx 1920px, JPEG 75%
        from PIL import Image as _Image
        import io as _io
        safe_name = f"{ts}_{Path(_ascii_name).stem}.jpg"
        dest = dest_dir / safe_name
        _img_data = await archivo.read()
        _img = _Image.open(_io.BytesIO(_img_data))
        _img = _img.convert("RGB")  # elimina canal alfa (PNG transparente → blanco)
        _MAX_W, _MAX_H = 1920, 1920
        if _img.width > _MAX_W or _img.height > _MAX_H:
            _img.thumbnail((_MAX_W, _MAX_H), _Image.LANCZOS)
        _buf = _io.BytesIO()
        _img.save(_buf, format="JPEG", quality=75, optimize=True)
        dest.write_bytes(_buf.getvalue())
        content_type = "image/jpeg"
    else:
        # PDFs → guardar sin modificar
        safe_name = f"{ts}_{_ascii_name}"
        dest = dest_dir / safe_name
        with dest.open("wb") as f:
            _shutil.copyfileobj(archivo.file, f)
        content_type = archivo.content_type or "application/pdf"

    adj_id = add_adjunto(nombre, archivo.filename or safe_name, str(dest), content_type, cat)
    return JSONResponse({"ok": True, "id": adj_id, "filename": archivo.filename})


def _servir_adjunto(adj_id: int, nombre: str, disposition: str, default_type: str) -> FileResponse:
    info = get_adjunto_filepath(adj_id, nombre)
    if not info:
        raise HTTPException(404, "Adjunto no encontrado")
    p = Path(info["filepath"]).resolve()
    try:
        if not p.is_relative_to(ADJUNTOS_DIR.resolve()):
            raise HTTPException(404, "Adjunto no encontrado")
    except ValueError:
        raise HTTPException(404, "Adjunto no encontrado")
    if not p.exists():
        raise HTTPException(404, "Archivo no encontrado en disco")
    return FileResponse(
        p,
        media_type=info.get("content_type") or default_type,
        headers={"Content-Disposition": f'{disposition}; filename="{info["filename"]}"'},
    )


@router.get("/api/proyecto/{nombre}/adjunto/{adj_id}/descargar")
async def api_descargar_adjunto(
    nombre: str, adj_id: int, usuario: dict = Depends(require_login),
):
    return _servir_adjunto(adj_id, nombre, "attachment", "application/octet-stream")


@router.get("/api/proyecto/{nombre}/adjunto/{adj_id}/ver")
async def api_ver_adjunto_inline(
    nombre: str, adj_id: int, usuario: dict = Depends(require_login),
):
    """Sirve el adjunto inline (para visualizar en iframe sin forzar descarga)."""
    return _servir_adjunto(adj_id, nombre, "inline", "application/pdf")


@router.delete("/api/proyecto/{nombre}/adjunto/{adj_id}")
async def api_delete_adjunto(
    nombre: str, adj_id: int, usuario: dict = Depends(require_login),
):
    filepath = delete_adjunto(adj_id)
    if filepath:
        try:
            Path(filepath).unlink(missing_ok=True)
        except Exception:
            pass
    return JSONResponse({"ok": True})


# ─────────────────────────────────────────────
# API — Proyectos: crear / eliminar (manual)
# ─────────────────────────────────────────────

@router.post("/api/proyecto")
async def api_crear_proyecto(
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
        nombre = (body.get("nombre") or "").strip()
        cliente = (body.get("cliente") or "").strip()
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    if not nombre:
        return JSONResponse({"ok": False, "error": "El nombre es requerido"}, status_code=422)
    ok = crear_proyecto(nombre, cliente)
    if not ok:
        return JSONResponse({"ok": False, "error": "Ya existe un proyecto con ese nombre"}, status_code=409)
    return JSONResponse({"ok": True})


@router.delete("/api/proyecto")
async def api_eliminar_proyecto(
    nombre: str,
    usuario: dict = Depends(require_admin),
):
    eliminar_proyecto(nombre)
    return JSONResponse({"ok": True})


# ─────────────────────────────────────────────
# API — OC Items
# ─────────────────────────────────────────────

@router.get("/api/proyecto/{nombre}/oc-items")
async def api_get_oc_items(nombre: str, usuario: dict = Depends(require_login)):
    try:
        items = get_oc_items(nombre)
        return JSONResponse({"ok": True, "items": items})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e), "items": []}, status_code=200)


@router.post("/api/proyecto/{nombre}/oc-items")
async def api_add_oc_item(
    nombre: str,
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    item_id = add_oc_item(
        proyecto=nombre,
        descripcion=body.get("descripcion", ""),
        unidad=body.get("unidad", "UND"),
        cantidad_pedida=float(body.get("cantidad_pedida", 0)),
        cantidad_despachada=float(body.get("cantidad_despachada", 0)),
        orden=int(body.get("orden", 0)),
    )
    return JSONResponse({"ok": True, "id": item_id})


@router.put("/api/proyecto/{nombre}/oc-item/{item_id}")
async def api_update_oc_item(
    nombre: str,
    item_id: int,
    request: Request,
    usuario: dict = Depends(require_login),
):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "JSON inválido"}, status_code=400)
    ok = update_oc_item(
        item_id=item_id,
        proyecto=nombre,
        descripcion=body.get("descripcion", ""),
        unidad=body.get("unidad", "UND"),
        cantidad_pedida=float(body.get("cantidad_pedida", 0)),
        cantidad_despachada=float(body.get("cantidad_despachada", 0)),
    )
    return JSONResponse({"ok": ok})


@router.delete("/api/proyecto/{nombre}/oc-item/{item_id}")
async def api_delete_oc_item(
    nombre: str,
    item_id: int,
    usuario: dict = Depends(require_login),
):
    ok = delete_oc_item(item_id, nombre)
    return JSONResponse({"ok": ok})

