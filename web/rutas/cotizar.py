"""
cotizar.py — Endpoints de cotización

Recibe parámetros del formulario, llama al motor de precios,
devuelve los resultados como JSON para que el frontend los muestre.
"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse
from typing import Optional

from web.auth import require_login
from web.motor import (
    PricingConfig,
    cotizar_bandeja,
    cotizar_curva_horizontal,
    cotizar_curva_vertical,
    cotizar_tee,
    cotizar_cruz,
    cotizar_reduccion,
    cotizar_caja_pase,
)
from web.database import cargar_config

router = APIRouter(prefix="/api/cotizar", tags=["cotizar"])


def _get_pricing_config(
    tipo_galvanizado: str,
    ganancia: str,
    config: Optional[dict] = None,
) -> PricingConfig:
    """Construye PricingConfig desde los parámetros y la configuración actual."""
    if config is None:
        config = cargar_config()
    valores = config.get("valores_defecto", {})

    precios_key = "precios_go" if tipo_galvanizado == "GO" else "precios_gc"
    # precio_galvanizado_kg se usa solo en GC
    precio_galv_kg = float(valores.get("usd_kg_productos", 1.0))
    usd_kg_cajas = float(valores.get("usd_kg_cajas", 3.0))
    dolar = float(valores.get("dolar", 3.8))

    return PricingConfig(
        tipo_galvanizado=tipo_galvanizado,
        dolar=dolar,
        precio_galvanizado_kg=precio_galv_kg,
        porcentaje_ganancia=ganancia,
        usd_kg_cajas=usd_kg_cajas,
    )


def _precios_plancha(espesor: float, tipo_galvanizado: str, config: dict) -> float:
    """Retorna el precio de la plancha para el espesor y tipo de galvanizado dado."""
    valores = config.get("valores_defecto", {})
    precios_key = "precios_go" if tipo_galvanizado == "GO" else "precios_gc"
    precios = valores.get(precios_key, {})
    esp_str = f"{espesor:.1f}"
    return float(precios.get(esp_str, 150.0))


@router.post("/bandeja")
async def api_cotizar_bandeja(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo_galvanizado: str = Form(...),
    ganancia: str = Form(...),
    espesor_producto: float = Form(...),
    espesor_tapa: float = Form(...),
    ancho: float = Form(...),
    alto: float = Form(...),
    tipo_superficie: str = Form("LISA"),
    es_metro_lineal: bool = Form(False),
):
    config = cargar_config()
    cfg = _get_pricing_config(tipo_galvanizado, ganancia, config)
    pp = _precios_plancha(espesor_producto, tipo_galvanizado, config)
    pt = _precios_plancha(espesor_tapa, tipo_galvanizado, config)

    resultados = cotizar_bandeja(cfg, pp, pt, espesor_producto, espesor_tapa, ancho, alto, tipo_superficie, es_metro_lineal)
    return JSONResponse({"ok": True, "resultados": resultados})


@router.post("/curva_horizontal")
async def api_cotizar_curva_horizontal(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo_galvanizado: str = Form(...),
    ganancia: str = Form(...),
    espesor_producto: float = Form(...),
    espesor_tapa: float = Form(...),
    ancho: float = Form(...),
    alto: float = Form(...),
    tipo_superficie: str = Form("LISA"),
):
    config = cargar_config()
    cfg = _get_pricing_config(tipo_galvanizado, ganancia, config)
    pp = _precios_plancha(espesor_producto, tipo_galvanizado, config)
    pt = _precios_plancha(espesor_tapa, tipo_galvanizado, config)

    resultados = cotizar_curva_horizontal(cfg, pp, pt, espesor_producto, espesor_tapa, ancho, alto, tipo_superficie)
    return JSONResponse({"ok": True, "resultados": resultados})


@router.post("/curva_vertical")
async def api_cotizar_curva_vertical(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo_galvanizado: str = Form(...),
    ganancia: str = Form(...),
    espesor_producto: float = Form(...),
    espesor_tapa: float = Form(...),
    ancho: float = Form(...),
    alto: float = Form(...),
    tipo_curva: str = Form("EXTERNA"),
    tipo_superficie: str = Form("LISA"),
):
    config = cargar_config()
    cfg = _get_pricing_config(tipo_galvanizado, ganancia, config)
    pp = _precios_plancha(espesor_producto, tipo_galvanizado, config)
    pt = _precios_plancha(espesor_tapa, tipo_galvanizado, config)

    resultados = cotizar_curva_vertical(cfg, pp, pt, espesor_producto, espesor_tapa, ancho, alto, tipo_curva, tipo_superficie)
    return JSONResponse({"ok": True, "resultados": resultados})


@router.post("/tee")
async def api_cotizar_tee(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo_galvanizado: str = Form(...),
    ganancia: str = Form(...),
    espesor_producto: float = Form(...),
    espesor_tapa: float = Form(...),
    derecha: float = Form(...),
    izquierda: float = Form(...),
    abajo: float = Form(...),
    alto: float = Form(...),
    tipo_superficie: str = Form("LISA"),
):
    config = cargar_config()
    cfg = _get_pricing_config(tipo_galvanizado, ganancia, config)
    pp = _precios_plancha(espesor_producto, tipo_galvanizado, config)
    pt = _precios_plancha(espesor_tapa, tipo_galvanizado, config)

    resultados = cotizar_tee(cfg, pp, pt, espesor_producto, espesor_tapa, derecha, izquierda, abajo, alto, tipo_superficie)
    return JSONResponse({"ok": True, "resultados": resultados})


@router.post("/cruz")
async def api_cotizar_cruz(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo_galvanizado: str = Form(...),
    ganancia: str = Form(...),
    espesor_producto: float = Form(...),
    espesor_tapa: float = Form(...),
    ancho: float = Form(...),
    alto: float = Form(...),
    tipo_superficie: str = Form("LISA"),
):
    config = cargar_config()
    cfg = _get_pricing_config(tipo_galvanizado, ganancia, config)
    pp = _precios_plancha(espesor_producto, tipo_galvanizado, config)
    pt = _precios_plancha(espesor_tapa, tipo_galvanizado, config)

    resultados = cotizar_cruz(cfg, pp, pt, espesor_producto, espesor_tapa, ancho, alto, tipo_superficie)
    return JSONResponse({"ok": True, "resultados": resultados})


@router.post("/reduccion")
async def api_cotizar_reduccion(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo_galvanizado: str = Form(...),
    ganancia: str = Form(...),
    espesor_producto: float = Form(...),
    espesor_tapa: float = Form(...),
    ancho_mayor: float = Form(...),
    alto: float = Form(...),
    ancho_menor: float = Form(...),
    tipo_superficie: str = Form("LISA"),
):
    config = cargar_config()
    cfg = _get_pricing_config(tipo_galvanizado, ganancia, config)
    pp = _precios_plancha(espesor_producto, tipo_galvanizado, config)
    pt = _precios_plancha(espesor_tapa, tipo_galvanizado, config)

    resultados = cotizar_reduccion(cfg, pp, pt, espesor_producto, espesor_tapa, ancho_mayor, alto, ancho_menor, tipo_superficie)
    return JSONResponse({"ok": True, "resultados": resultados})


@router.post("/caja_pase")
async def api_cotizar_caja_pase(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo_galvanizado: str = Form(...),
    ganancia: str = Form(...),
    espesor_producto: float = Form(...),
    espesor_tapa: float = Form(...),
    dim1: float = Form(...),
    dim2: float = Form(...),
    dim3: float = Form(...),
    tipo_salida: str = Form("CIEGA"),
):
    config = cargar_config()
    cfg = _get_pricing_config(tipo_galvanizado, ganancia, config)
    pp = _precios_plancha(espesor_producto, tipo_galvanizado, config)
    # Caja de pase: cuerpo y tapa siempre del mismo espesor
    pt = pp

    resultados = cotizar_caja_pase(cfg, pp, pt, espesor_producto, espesor_producto, dim1, dim2, dim3, tipo_salida)
    return JSONResponse({"ok": True, "resultados": resultados})
