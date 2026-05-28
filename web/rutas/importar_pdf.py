"""
rutas/importar_pdf.py — Endpoints para importar cotizaciones desde PDF

POST /api/importar/parsear              — recibe PDFs, retorna preview de datos extraídos
POST /api/importar/confirmar            — recibe datos confirmados y los guarda en historial
GET  /api/importar/duplicados           — detecta grupos de cotizaciones duplicadas en historial
POST /api/importar/eliminar_duplicados  — elimina cotizaciones duplicadas (admin)
"""

from fastapi import APIRouter, UploadFile, File, Depends, Request
from fastapi.responses import JSONResponse
from typing import List

from web.auth import require_admin
from web.importar_pdf import parsear_pdf
from web.database import (
    guardar_cotizacion_importada_db,
    obtener_catalogo,
    detectar_duplicados_db,
    eliminar_cotizaciones_bulk_db,
    fingerprints_cotizaciones_db,
    _fp_items,
)


def _cruzar_cliente_con_bd(nombre_pdf: str, clientes: list) -> dict | None:
    """
    Busca en la BD un cliente cuyas primeras 2 palabras coincidan
    con las primeras 2 palabras del nombre extraído del PDF.
    Retorna el dict del cliente de BD si hay coincidencia, o None si no.
    """
    if not nombre_pdf or not clientes:
        return None

    import re as _re

    def palabras_clave(s: str) -> list:
        s = _re.sub(r"[^\w\s]", "", s.upper())
        return s.split()[:2]

    clave_pdf = palabras_clave(nombre_pdf)
    if not clave_pdf:
        return None

    for cliente in clientes:
        if palabras_clave(cliente.get("nombre", "")) == clave_pdf:
            return cliente

    return None

router = APIRouter()


@router.post("/api/importar/parsear")
async def importar_parsear(
    archivos: List[UploadFile] = File(...),
    session: dict = Depends(require_admin),
):
    """
    Recibe una lista de PDFs, los parsea y retorna un preview de los datos
    extraídos para que el usuario pueda revisar antes de confirmar.
    Incluye `posibles_duplicados` por cada resultado para alertar si ya existe.
    """
    clientes_bd  = obtener_catalogo().get("clientes", [])
    fps_existentes = fingerprints_cotizaciones_db()

    resultados = []
    for archivo in archivos:
        pdf_bytes = await archivo.read()
        resultado = parsear_pdf(pdf_bytes)
        # Enriquecer con datos oficiales de la BD
        if resultado.get("ok") and resultado.get("datos"):
            datos = resultado["datos"]
            cliente_bd = _cruzar_cliente_con_bd(datos.get("cliente_nombre", ""), clientes_bd)
            if cliente_bd:
                datos["cliente_nombre"]    = cliente_bd["nombre"]
                datos["cliente_ruc"]       = cliente_bd.get("ruc", "") or ""
                datos["cliente_ubicacion"] = cliente_bd.get("ubicacion", "") or ""
            # Detectar posibles duplicados contra el historial existente
            cliente_n  = (datos.get("cliente_nombre") or "").strip().lower()
            proyecto_n = (datos.get("proyecto") or "").strip().lower()
            total      = round(float(datos.get("total_precio") or 0), 2)
            items_fp   = _fp_items(datos.get("items") or [])
            fp = f"{cliente_n}|{proyecto_n}|{total}|{items_fp}"
            if fp in fps_existentes:
                datos["posibles_duplicados"] = fps_existentes[fp]
            else:
                datos["posibles_duplicados"] = []
        # Rechazar cotizaciones en blanco (sin cliente, proyecto ni atención)
        if resultado.get("ok") and resultado.get("datos"):
            d = resultado["datos"]
            if not d.get("cliente_nombre") and not d.get("proyecto") and not d.get("atencion"):
                resultado = {
                    "ok": False,
                    "error": "Cotización en blanco — no contiene cliente, proyecto ni atención",
                }

        resultados.append({
            "nombre_archivo": archivo.filename,
            **resultado,
        })

    return JSONResponse({"ok": True, "resultados": resultados})


@router.get("/api/importar/duplicados")
async def importar_duplicados(
    session: dict = Depends(require_admin),
):
    """Detecta grupos de cotizaciones duplicadas en el historial."""
    grupos = detectar_duplicados_db()
    return JSONResponse({"ok": True, "grupos": grupos})


@router.post("/api/importar/eliminar_duplicados")
async def importar_eliminar_duplicados(
    request: Request,
    session: dict = Depends(require_admin),
):
    """Elimina múltiples cotizaciones identificadas como duplicados (admin)."""
    body = await request.json()
    ids  = body.get("ids", [])
    if not ids:
        return JSONResponse({"ok": False, "error": "Sin IDs"}, status_code=400)
    eliminadas = eliminar_cotizaciones_bulk_db([int(i) for i in ids])
    return JSONResponse({"ok": True, "eliminadas": eliminadas})


@router.post("/api/importar/confirmar")
async def importar_confirmar(
    request: Request,
    session: dict = Depends(require_admin),
):
    """
    Recibe un array de cotizaciones ya parseadas (y revisadas por el usuario)
    y las guarda en el historial con origen='pdf_import'.
    """
    body = await request.json()
    cotizaciones = body.get("cotizaciones", [])
    if not cotizaciones:
        return JSONResponse({"ok": False, "error": "No se recibieron cotizaciones"}, status_code=400)

    username = session.get("u", "admin")
    importadas = []
    errores = []

    for i, cot in enumerate(cotizaciones):
        try:
            items  = cot.get("items", [])
            fecha  = cot.get("fecha", "") or None

            cot_id = guardar_cotizacion_importada_db(
                username          = username,
                cliente           = cot.get("cliente_nombre", ""),
                atencion          = cot.get("atencion", ""),
                proyecto          = cot.get("proyecto", ""),
                moneda            = cot.get("moneda", "SOLES"),
                items             = items,
                cliente_nombre    = cot.get("cliente_nombre", ""),
                cliente_ruc       = cot.get("cliente_ruc", ""),
                cliente_ubicacion = cot.get("cliente_ubicacion", ""),
                atencion_email    = cot.get("atencion_email", ""),
                dolar_rate        = float(cot.get("dolar_rate", 3.8)),
                validez           = cot.get("validez", "30 días"),
                encabezado_tabla  = cot.get("encabezado_tabla", ""),
                fecha             = fecha,
                origen            = "pdf_import",
            )
            importadas.append({"indice": i, "id": cot_id})
        except Exception as e:
            errores.append({"indice": i, "error": str(e)})

    return JSONResponse({
        "ok":        True,
        "importadas": importadas,
        "errores":    errores,
        "total":      len(importadas),
    })
