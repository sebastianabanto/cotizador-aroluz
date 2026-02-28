"""
carrito.py — Endpoints del carrito de compras por sesión

El carrito se almacena en SQLite (tabla carrito_items), persistente entre reinicios.
"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse

from web.auth import require_login
from web.database import (
    get_carrito_db,
    add_item_carrito_db,
    update_cantidad_carrito_db,
    delete_item_carrito_db,
    clear_carrito_db,
)

router = APIRouter(prefix="/api/carrito", tags=["carrito"])


def get_carrito(username: str):
    """Wrapper público — devuelve la lista de items del carrito desde DB."""
    return get_carrito_db(username)


@router.get("")
async def api_get_carrito(usuario: dict = Depends(require_login)):
    carrito = get_carrito(usuario["u"])
    total = sum(item["precio_unitario"] * item["cantidad"] for item in carrito)
    peso_total = sum(item["peso_unitario"] * item["cantidad"] for item in carrito)
    return JSONResponse({
        "ok": True,
        "carrito": carrito,
        "total": round(total, 2),
        "peso_total": round(peso_total, 4),
        "cantidad_items": len(carrito),
    })


@router.post("/agregar")
async def api_agregar_al_carrito(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo: str = Form(...),
    descripcion: str = Form(...),
    precio_unitario: float = Form(...),
    peso_unitario: float = Form(...),
    cantidad: int = Form(1),
    unidad: str = Form("UND"),
    tipo_galvanizado: str = Form("GO"),
    porcentaje_ganancia: str = Form("30"),
):
    item = {
        "tipo": tipo,
        "descripcion": descripcion,
        "precio_unitario": round(precio_unitario, 4),
        "peso_unitario": round(peso_unitario, 6),
        "cantidad": max(1, cantidad),
        "unidad": unidad,
        "tipo_galvanizado": tipo_galvanizado,
        "porcentaje_ganancia": porcentaje_ganancia,
    }
    add_item_carrito_db(usuario["u"], item)
    n = len(get_carrito(usuario["u"]))
    return JSONResponse({"ok": True, "mensaje": "Producto agregado al carrito", "cantidad_items": n})


@router.post("/agregar_manual")
async def api_agregar_manual(
    request: Request,
    usuario: dict = Depends(require_login),
    descripcion: str = Form(...),
    unidad: str = Form("UND"),
    precio_unitario: float = Form(...),
    peso_unitario: float = Form(0),
    cantidad: int = Form(1),
):
    item = {
        "tipo": "MANUAL",
        "descripcion": descripcion,
        "precio_unitario": round(precio_unitario, 4),
        "peso_unitario": round(peso_unitario, 6),
        "cantidad": max(1, cantidad),
        "unidad": unidad,
        "tipo_galvanizado": "N/A",
        "porcentaje_ganancia": "N/A",
    }
    add_item_carrito_db(usuario["u"], item)
    return JSONResponse({"ok": True, "mensaje": "Producto manual agregado"})


@router.post("/modificar/{item_id}")
async def api_modificar_cantidad(
    item_id: int,
    usuario: dict = Depends(require_login),
    cantidad: int = Form(...),
):
    if cantidad < 1:
        return JSONResponse({"ok": False, "error": "Cantidad inválida"}, status_code=400)
    updated = update_cantidad_carrito_db(item_id, usuario["u"], cantidad)
    if updated:
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)


@router.delete("/eliminar/{item_id}")
async def api_eliminar_item(
    item_id: int,
    usuario: dict = Depends(require_login),
):
    deleted = delete_item_carrito_db(item_id, usuario["u"])
    if deleted:
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)


@router.post("/limpiar")
async def api_limpiar_carrito(usuario: dict = Depends(require_login)):
    clear_carrito_db(usuario["u"])
    return JSONResponse({"ok": True, "mensaje": "Carrito limpiado"})


@router.get("/resumen")
async def api_resumen_carrito(usuario: dict = Depends(require_login)):
    """Resumen compacto para el badge de la navbar."""
    carrito = get_carrito(usuario["u"])
    total = sum(item["precio_unitario"] * item["cantidad"] for item in carrito)
    return JSONResponse({
        "cantidad_items": len(carrito),
        "total": round(total, 2),
    })
