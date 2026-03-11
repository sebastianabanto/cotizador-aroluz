"""
carrito.py — Endpoints del carrito de compras por sesión

El carrito se almacena en SQLite (tabla carrito_items), persistente entre reinicios.
"""
import re

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse
from typing import Optional

from web.auth import require_login
from web.database import (
    get_carrito_db,
    add_item_carrito_db,
    update_cantidad_carrito_db,
    update_item_precio_carrito_db,
    delete_item_carrito_db,
    clear_carrito_db,
    cargar_config,
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


_ESPESORES_VALIDOS = {"1.2", "1.5", "2.0"}


def _extraer_espesor(descripcion: str) -> Optional[float]:
    """Extrae el último espesor decimal (e.g. 1.5 de '1.5MM') de la descripción."""
    matches = re.findall(r'(\d+\.\d+)MM', descripcion)
    return float(matches[-1]) if matches else None


def _reemplazar_espesor(descripcion: str, nuevo_esp: float) -> str:
    """Reemplaza el último espesor decimal en la descripción."""
    matches = list(re.finditer(r'(\d+\.\d+)MM', descripcion))
    if not matches:
        return descripcion
    last = matches[-1]
    return descripcion[:last.start()] + f"{nuevo_esp:.1f}MM" + descripcion[last.end():]


@router.post("/cambiar_espesor")
async def api_cambiar_espesor(
    usuario: dict = Depends(require_login),
    nuevo_espesor: float = Form(...),
    parte: str = Form(...),        # "cuerpo" o "tapa"
    item_id: str = Form("all"),    # "all" o id numérico
):
    """Recalcula precio y peso de items del carrito al cambiar el espesor de plancha."""
    nuevo_esp_str = f"{nuevo_espesor:.1f}"
    if nuevo_esp_str not in _ESPESORES_VALIDOS:
        return JSONResponse({"ok": False, "error": "Espesor inválido"}, status_code=400)
    if parte not in ("cuerpo", "tapa"):
        return JSONResponse({"ok": False, "error": "Parte inválida"}, status_code=400)

    config = cargar_config()
    valores = config.get("valores_defecto", {})

    carrito = get_carrito(usuario["u"])
    actualizados = 0
    omitidos = []

    for item in carrito:
        # Filtrar por item_id si se especificó uno
        if item_id != "all" and str(item["id"]) != item_id:
            continue

        # Items sin cálculo predeterminado (manuales o de catálogo)
        if item["tipo_galvanizado"] == "N/A":
            omitidos.append(item["descripcion"])
            continue

        desc = item["descripcion"]
        es_tapa = "TAPA" in desc.upper()

        # Solo procesar la parte solicitada
        if parte == "tapa" and not es_tapa:
            continue
        if parte == "cuerpo" and es_tapa:
            continue

        # Extraer espesor actual
        esp_actual = _extraer_espesor(desc)
        if esp_actual is None:
            omitidos.append(desc)
            continue

        # Mismo espesor → sin cambio
        if abs(esp_actual - nuevo_espesor) < 0.001:
            continue

        esp_actual_str = f"{esp_actual:.1f}"
        tipo_galv = item["tipo_galvanizado"]
        precios_key = "precios_go" if tipo_galv == "GO" else "precios_gc"
        precios = valores.get(precios_key, {})

        pp_viejo = float(precios.get(esp_actual_str, 0))
        pp_nuevo = float(precios.get(nuevo_esp_str, 0))

        if pp_viejo <= 0 or pp_nuevo <= 0:
            omitidos.append(desc)
            continue

        # Nuevo precio: proporcional al precio de plancha (exacto para GO)
        nuevo_precio = item["precio_unitario"] * (pp_nuevo / pp_viejo)
        # Nuevo peso: proporcional al espesor (más material = más peso)
        nuevo_peso = item["peso_unitario"] * (nuevo_espesor / esp_actual)
        nueva_desc = _reemplazar_espesor(desc, nuevo_espesor)

        update_item_precio_carrito_db(
            item["id"], usuario["u"],
            nuevo_precio, nuevo_peso, nueva_desc,
        )
        actualizados += 1

    return JSONResponse({
        "ok": True,
        "actualizados": actualizados,
        "omitidos": omitidos,
    })


@router.get("/resumen")
async def api_resumen_carrito(usuario: dict = Depends(require_login)):
    """Resumen compacto para el badge de la navbar."""
    carrito = get_carrito(usuario["u"])
    total = sum(item["precio_unitario"] * item["cantidad"] for item in carrito)
    return JSONResponse({
        "cantidad_items": len(carrito),
        "total": round(total, 2),
    })
