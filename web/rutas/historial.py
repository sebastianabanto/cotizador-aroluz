"""
historial.py — Endpoints para guardar y consultar cotizaciones finalizadas

Rutas:
  POST /api/historial/guardar                  — guarda carrito actual como cotización
  GET  /api/historial/lista                    — lista todas las cotizaciones del usuario
  POST /api/historial/exportar_multiple/pdf    — ZIP con PDFs de varias cotizaciones
  GET  /api/historial/{id}                     — detalle de una cotización
  DELETE /api/historial/{id}                   — elimina una cotización propia
  GET  /api/historial/{id}/exportar/pdf        — descarga PDF de cotización guardada
  GET  /api/historial/{id}/exportar/xlsx       — descarga XLSX de cotización guardada
"""
import io
import zipfile
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from web.auth import require_login
from web.database import (
    get_carrito_db,
    guardar_cotizacion_db,
    listar_cotizaciones_db,
    get_cotizacion_db,
    get_estadisticas_db,
    get_tendencias_items_db,
    get_items_frecuentes_db,
    eliminar_cotizacion_db,
    cargar_cotizacion_al_carrito_db,
)
from web.rutas.exportar import _generar_pdf

router = APIRouter(prefix="/api/historial", tags=["historial"])


@router.post("/guardar")
async def api_guardar_cotizacion(
    usuario: dict = Depends(require_login),
    cliente: str = Form(""),
    cliente_nombre: str = Form(""),
    cliente_ruc: str = Form(""),
    cliente_ubicacion: str = Form(""),
    atencion: str = Form(""),
    atencion_email: str = Form(""),
    moneda: str = Form("SOLES"),
    proyecto: str = Form(""),
    validez: str = Form("30 días"),
    encabezado_tabla: str = Form(""),
):
    items = get_carrito_db(usuario["u"])
    if not items:
        return JSONResponse({"ok": False, "error": "El carrito está vacío"}, status_code=400)

    cotizacion_id = guardar_cotizacion_db(
        username=usuario["u"],
        cliente=cliente,
        atencion=atencion,
        proyecto=proyecto,
        moneda=moneda,
        items=items,
        cliente_nombre=cliente_nombre,
        cliente_ruc=cliente_ruc,
        cliente_ubicacion=cliente_ubicacion,
        atencion_email=atencion_email,
        validez=validez,
        encabezado_tabla=encabezado_tabla,
    )
    return JSONResponse({"ok": True, "id": cotizacion_id})


@router.get("/estadisticas")
async def api_estadisticas(
    usuario: dict = Depends(require_login),
):
    es_admin = usuario.get("r") == "ADMIN"
    stats = get_estadisticas_db(username=None if es_admin else usuario["u"])
    return JSONResponse({"ok": True, "stats": stats})


@router.get("/lista")
async def api_listar_cotizaciones(
    usuario: dict = Depends(require_login),
    tipo: List[str] = Query(default=[]),
    q: str = Query(default=""),
    galvanizado: List[str] = Query(default=[]),
    ganancia: List[str] = Query(default=[]),
):
    es_admin = usuario.get("r") == "ADMIN"
    cotizaciones = listar_cotizaciones_db(
        username=None if es_admin else usuario["u"],
        tipos=tipo if tipo else None,
        q=q.strip(),
        galvanizados=galvanizado if galvanizado else None,
        ganancias=ganancia if ganancia else None,
    )
    return JSONResponse({"ok": True, "cotizaciones": cotizaciones})


@router.post("/exportar_multiple/pdf")
async def api_exportar_multiple_pdf(
    usuario: dict = Depends(require_login),
    ids: str = Form(...),
):
    """Genera un ZIP con un PDF por cada cotización seleccionada."""
    es_admin = usuario.get("r") == "ADMIN"
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
    if not id_list:
        return JSONResponse({"ok": False, "error": "Sin IDs válidos"}, status_code=400)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for cid in id_list:
            cotizacion = get_cotizacion_db(cid)
            if not cotizacion:
                continue
            if not es_admin and cotizacion["username"] != usuario["u"]:
                continue
            fecha = _formatear_fecha(cotizacion["fecha"])
            pdf_bytes = _generar_pdf(
                carrito=cotizacion["items"],
                cliente=cotizacion["cliente"],
                atencion=cotizacion["atencion"],
                moneda=cotizacion["moneda"],
                proyecto=cotizacion["proyecto"],
                fecha=fecha,
                cliente_nombre=cotizacion.get("cliente_nombre", ""),
                cliente_ruc=cotizacion.get("cliente_ruc", ""),
                cliente_ubicacion=cotizacion.get("cliente_ubicacion", ""),
                atencion_email=cotizacion.get("atencion_email", ""),
                dolar=float(cotizacion.get("dolar_rate", 3.8)),
                validez=cotizacion.get("validez", "30 días"),
                encabezado_tabla=cotizacion.get("encabezado_tabla", ""),
                cotizacion_id=cotizacion["id"],
            )
            try:
                _año = datetime.strptime(fecha, "%d/%m/%Y").year
            except Exception:
                _año = datetime.now().year
            _cliente_str = cotizacion.get("cliente_nombre") or cotizacion.get("cliente", "")
            _campos = [p.strip() for p in [
                _cliente_str, cotizacion.get("proyecto", ""),
            ] if p and p.strip()]
            _base = f"COT-{_año}-{cid:05d}" + (" " + " ".join(_campos) if _campos else "")
            for _c in r'\/:*?"<>|':
                _base = _base.replace(_c, "")
            zf.writestr(_base + ".pdf", pdf_bytes)

    zip_buffer.seek(0)
    filename = f"cotizaciones_{datetime.now().strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/items-frecuentes")
async def api_items_frecuentes(
    usuario: dict = Depends(require_login),
    cliente: str = Query(default=""),
    proyecto: str = Query(default=""),
    limit: int = Query(default=40),
):
    """Devuelve ítems del historial ordenados por frecuencia de aparición."""
    es_admin = usuario.get("r") == "ADMIN"
    username = None if es_admin else usuario["u"]
    items = get_items_frecuentes_db(username, cliente.strip(), proyecto.strip(), limit)
    return JSONResponse({"ok": True, "items": items})


@router.get("/tendencias")
async def api_tendencias(
    usuario: dict = Depends(require_login),
    cliente: str = Query(default=""),
    cliente2: str = Query(default=""),
    proyecto: str = Query(default=""),
    q: str = Query(default=""),
    tipo: List[str] = Query(default=[]),
    galvanizado: List[str] = Query(default=[]),
    ganancia: List[str] = Query(default=[]),
    moneda: List[str] = Query(default=[]),
    espesor: List[str] = Query(default=[]),
):
    """Devuelve series de precio unitario (S/) por ítem para graficar tendencias.

    Acepta hasta 2 clientes (modo comparación) y los mismos filtros de tipo,
    galvanizado, ganancia y moneda que usa la barra de filtros del historial.
    """
    from collections import defaultdict

    es_admin = usuario.get("r") == "ADMIN"
    username = None if es_admin else usuario["u"]

    clientes_list = [c for c in [cliente.strip(), cliente2.strip()] if c]

    series = []
    if clientes_list:
        rows = get_tendencias_items_db(
            clientes=clientes_list,
            proyecto=proyecto.strip(),
            q=q.strip(),
            username=username,
            tipos=tipo if tipo else None,
            galvanizados=galvanizado if galvanizado else None,
            ganancias=ganancia if ganancia else None,
            monedas=moneda if moneda else None,
            espesores=espesor if espesor else None,
        )

        grupos: dict = defaultdict(list)
        cliente_labels: dict = {}
        for row in rows:
            key = (row["descripcion"], row["cliente_idx"])
            grupos[key].append({
                "fecha": (row["fecha"] or "")[:10],
                "precio_soles": row["precio_soles"],
                "cotizacion_id": row["cotizacion_id"],
                "proyecto": row["proyecto"] or "",
                "espesor": row.get("espesor", ""),
                "galvanizado": row.get("galvanizado", ""),
            })
            cliente_labels[row["cliente_idx"]] = row["cliente_label"]

        for (desc, cli_idx), puntos in sorted(grupos.items()):
            series.append({
                "descripcion": desc,
                "cliente": cliente_labels.get(cli_idx, ""),
                "cliente_idx": cli_idx,
                "puntos": sorted(puntos, key=lambda p: p["fecha"]),
            })

    return JSONResponse({"ok": True, "series": series})


@router.get("/{cotizacion_id}")
async def api_get_cotizacion(
    cotizacion_id: int,
    usuario: dict = Depends(require_login),
):
    cotizacion = get_cotizacion_db(cotizacion_id)
    if not cotizacion:
        return JSONResponse({"ok": False, "error": "Cotización no encontrada"}, status_code=404)
    es_admin = usuario.get("r") == "ADMIN"
    if not es_admin and cotizacion["username"] != usuario["u"]:
        return JSONResponse({"ok": False, "error": "Sin permiso"}, status_code=403)
    return JSONResponse({"ok": True, "cotizacion": cotizacion})


@router.delete("/{cotizacion_id}")
async def api_eliminar_cotizacion(
    cotizacion_id: int,
    usuario: dict = Depends(require_login),
):
    es_admin = usuario.get("r") == "ADMIN"
    deleted = eliminar_cotizacion_db(cotizacion_id, None if es_admin else usuario["u"])
    if deleted:
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Cotización no encontrada o sin permiso"}, status_code=404)


@router.post("/{cotizacion_id}/cargar_al_carrito")
async def api_cargar_al_carrito(
    cotizacion_id: int,
    usuario: dict = Depends(require_login),
):
    es_admin = usuario.get("r") == "ADMIN"
    meta = cargar_cotizacion_al_carrito_db(
        cotizacion_id, usuario["u"], require_ownership=not es_admin
    )
    if not meta:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return JSONResponse(meta)


@router.get("/{cotizacion_id}/exportar/pdf")
async def api_exportar_pdf(
    cotizacion_id: int,
    usuario: dict = Depends(require_login),
):
    cotizacion = get_cotizacion_db(cotizacion_id)
    if not cotizacion:
        return JSONResponse({"ok": False, "error": "Cotización no encontrada"}, status_code=404)
    es_admin = usuario.get("r") == "ADMIN"
    if not es_admin and cotizacion["username"] != usuario["u"]:
        return JSONResponse({"ok": False, "error": "Sin permiso"}, status_code=403)

    fecha = _formatear_fecha(cotizacion["fecha"])
    pdf_bytes = _generar_pdf(
        carrito=cotizacion["items"],
        cliente=cotizacion["cliente"],
        atencion=cotizacion["atencion"],
        moneda=cotizacion["moneda"],
        proyecto=cotizacion["proyecto"],
        fecha=fecha,
        cliente_nombre=cotizacion.get("cliente_nombre", ""),
        cliente_ruc=cotizacion.get("cliente_ruc", ""),
        cliente_ubicacion=cotizacion.get("cliente_ubicacion", ""),
        atencion_email=cotizacion.get("atencion_email", ""),
        dolar=float(cotizacion.get("dolar_rate", 3.8)),
        validez=cotizacion.get("validez", "30 días"),
        encabezado_tabla=cotizacion.get("encabezado_tabla", ""),
        cotizacion_id=cotizacion["id"],
    )
    try:
        _fecha_doc = datetime.strptime(fecha, "%d/%m/%Y").strftime("%d-%m-%Y")
        _año = datetime.strptime(fecha, "%d/%m/%Y").year
    except Exception:
        _fecha_doc = datetime.now().strftime("%d-%m-%Y")
        _año = datetime.now().year
    es_importada = cotizacion.get("origen") == "pdf_import"
    _cliente_str = cotizacion.get("cliente_nombre") or cotizacion.get("cliente", "")
    _campos = [p.strip() for p in [
        _cliente_str,
        cotizacion.get("proyecto", ""),
        cotizacion.get("atencion", ""),
        _fecha_doc,
    ] if p and p.strip()]
    if es_importada:
        _base = "COT-" + " ".join(_campos) if _campos else "COTIZACIÓN"
    else:
        _base = " ".join([f"COT-{_año}-{cotizacion_id:05d}"] + _campos) if _campos else "COTIZACIÓN"
    for _c in r'\/:*?"<>|':
        _base = _base.replace(_c, "")
    nombre = _base + ".pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


def _formatear_fecha(fecha_iso: str) -> str:
    """Convierte '2026-02-18 14:30:00' → '18/02/2026'."""
    try:
        dt = datetime.strptime(fecha_iso, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return fecha_iso
