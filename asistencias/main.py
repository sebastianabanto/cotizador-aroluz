"""
main.py — Router FastAPI para procesamiento de asistencias biométricas.

Montado en /asistencias/ dentro del cotizador web (puerto 8000).
Requiere rol ADMIN (require_admin de web.auth).
"""

import io
import re
from datetime import date
from pathlib import Path

import json as _json

_MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _periodo_slug(periodo_raw: str) -> str:
    """De '2026-02-01 ~ 2026-02-28' extrae 'Feb2026'."""
    m = re.match(r"(\d{4})-(\d{2})-\d{2}", periodo_raw.strip())
    if not m:
        return "periodo"
    anio, mes = int(m.group(1)), int(m.group(2))
    return f"{_MESES_ES[mes - 1]}{anio}" if 1 <= mes <= 12 else f"{mes:02d}{anio}"


def _quincena_slug(quincena: int) -> str:
    return "mes" if quincena == 0 else f"Q{quincena}"


from fastapi import APIRouter, File, Form, UploadFile, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from asistencias.parser import procesar_reporte
from asistencias import config as cfg
from web.auth import require_asistencias as require_admin
from web.rutas.carrito import get_carrito

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORTE_PATH = DATA_DIR / "ultimo_reporte.xls"
NOMBRE_PATH  = DATA_DIR / "ultimo_reporte_nombre.txt"

router = APIRouter()

# Templates para páginas HTML — apunta a web/templates/ para extender base.html
_templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "web" / "templates"))

# Templates para PDF — usa asistencias/templates/ (no hereda base.html)
_pdf_templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _tojson_filter(value):
    return _json.dumps(value, ensure_ascii=False, default=str)


_templates.env.filters["tojson"] = _tojson_filter
_pdf_templates.env.filters["tojson"] = _tojson_filter


def _ctx(request: Request, usuario: dict, **kwargs) -> dict:
    nombre = NOMBRE_PATH.read_text(encoding="utf-8").strip() if NOMBRE_PATH.exists() else None
    carrito = get_carrito(usuario["u"])
    total_carrito = sum(i["precio_unitario"] * i["cantidad"] for i in carrito)
    return {
        "request":          request,
        "usuario":          usuario,
        "n_carrito":        len(carrito),
        "total_carrito":    round(total_carrito, 2),
        "active":           "asistencias",
        "excepciones":      cfg.cargar_excepciones(),
        "ids_sin_sabados":  cfg.ids_sin_sabados(),
        "ultimo_archivo":   nombre,
        **kwargs,
    }


def _procesar_guardado():
    contenido = REPORTE_PATH.read_bytes()
    return procesar_reporte(contenido, sin_sabados=cfg.ids_sin_sabados())


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, usuario: dict = Depends(require_admin)):
    # Limpiar todo al recargar: reporte guardado + reglas especiales
    for path in (REPORTE_PATH, NOMBRE_PATH, cfg.EXCEPCIONES_PATH):
        if path.exists():
            path.unlink()
    return _templates.TemplateResponse(
        "asistencias/index.html",
        _ctx(request, usuario, resultado=None, error=None),
    )


@router.get("/procesar")
async def procesar_get():
    return RedirectResponse("/asistencias/", status_code=303)


@router.post("/procesar", response_class=HTMLResponse)
async def procesar(
    request: Request,
    archivo: UploadFile = File(...),
    usuario: dict = Depends(require_admin),
):
    if not archivo.filename.lower().endswith(".xls"):
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None,
                 error="El archivo debe ser un .xls (reporte del sistema biométrico)."),
        )

    try:
        contenido = await archivo.read()
        DATA_DIR.mkdir(exist_ok=True)
        REPORTE_PATH.write_bytes(contenido)
        NOMBRE_PATH.write_text(archivo.filename, encoding="utf-8")
        resultado = procesar_reporte(contenido, sin_sabados=cfg.ids_sin_sabados())
    except Exception as exc:
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None,
                 error=f"Error al procesar el archivo: {exc}"),
        )

    return _templates.TemplateResponse(
        "asistencias/index.html",
        _ctx(request, usuario, resultado=resultado, error=None),
    )


@router.get("/reprocesar", response_class=HTMLResponse)
async def reprocesar(request: Request, usuario: dict = Depends(require_admin)):
    if not REPORTE_PATH.exists():
        return RedirectResponse("/asistencias/")

    try:
        resultado = _procesar_guardado()
    except Exception as exc:
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None,
                 error=f"Error al reprocesar: {exc}"),
        )

    return _templates.TemplateResponse(
        "asistencias/index.html",
        _ctx(request, usuario, resultado=resultado, error=None),
    )


@router.post("/excepciones/toggle")
async def toggle_excepcion(
    usuario: dict = Depends(require_admin),
    emp_id: str = Form(...),
    nombre: str = Form(...),
):
    cfg.toggle_excepcion(emp_id, nombre)
    return RedirectResponse("/asistencias/reprocesar", status_code=303)


def _header_pdf_html(titulo: str, periodo: str, quincena_texto: str = "",
                     depto: str = "", n_empleados: int = None) -> str:
    """Construye el HTML del encabezado para Playwright header_template."""
    meta_parts = [f"<b>Período:</b> {periodo}"]
    if quincena_texto:
        meta_parts.append(f"<b>Detalle:</b> {quincena_texto}")
    if depto and depto != "todos":
        meta_parts.append(f"<b>Departamento:</b> {depto}")
    if n_empleados is not None:
        meta_parts.append(f"<b>Empleados:</b> {n_empleados}")
    meta = " &nbsp;|&nbsp; ".join(meta_parts)
    return (
        '<div style="width:100%;font-family:Helvetica,Arial,sans-serif;'
        'padding:0 20mm;box-sizing:border-box;">'
        '<div style="border-bottom:2px solid #1a56a0;padding-bottom:5px;">'
        '<div style="font-size:13pt;font-weight:700;color:#1a56a0;line-height:1.3;">AROLUZ E.I.R.L.</div>'
        f'<div style="font-size:9pt;font-weight:600;color:#333;margin-top:2px;line-height:1.3;">{titulo}</div>'
        f'<div style="font-size:7.5pt;color:#555;margin-top:2px;line-height:1.3;">{meta}</div>'
        '</div>'
        '</div>'
    )


def _footer_pdf_html(hoy: str) -> str:
    """Construye el HTML del pie para Playwright footer_template."""
    return (
        '<div style="width:100%;font-family:Helvetica,Arial,sans-serif;'
        'padding:0 20mm;box-sizing:border-box;">'
        '<div style="font-size:7.5pt;color:#777;border-top:1px solid #ccc;padding-top:3px;">'
        'AROLUZ E.I.R.L. — Control de Asistencias'
        f'&nbsp;&nbsp;&nbsp;&nbsp;Generado el {hoy}'
        '&nbsp;&nbsp;&nbsp;&nbsp;Página <span class="pageNumber"></span>'
        ' / <span class="totalPages"></span>'
        '</div>'
        '</div>'
    )


def _html_a_pdf(html_str: str, header_html: str = "", footer_html: str = "") -> bytes:
    """Genera PDF desde un string HTML usando Playwright + Chromium."""
    import concurrent.futures
    from playwright.sync_api import sync_playwright

    def _run():
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_str, wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A4",
                margin={"top": "32mm", "bottom": "14mm", "left": "20mm", "right": "20mm"},
                display_header_footer=True,
                header_template=header_html or "<span></span>",
                footer_template=footer_html or "<span></span>",
            )
            browser.close()
        return pdf_bytes

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_run).result(timeout=60)


def _totales_periodo(detalle: list, quincena: int) -> dict:
    asistidos = ausencias = total_min = estimados = 0
    for d in detalle:
        en_periodo = (quincena == 0 or
                      (quincena == 1 and d["dia"] <= 15) or
                      (quincena == 2 and d["dia"] >= 16))
        if not en_periodo:
            continue
        if not d["ausente"]:
            asistidos += 1
        if d["ausente"] and not d["es_fin_semana"]:
            ausencias += 1
        if d["horas"] is not None:
            total_min += round(d["horas"] * 60)
        if d["estimado"]:
            estimados += 1
    h, m = divmod(total_min, 60)
    return {"asistidos": asistidos, "ausencias": ausencias,
            "estimados": estimados, "horas_fmt": f"{h}h {m:02d}m"}


@router.post("/excepciones/toggle-ajax")
async def toggle_excepcion_ajax(
    usuario: dict = Depends(require_admin),
    emp_id: str = Form(...),
    nombre: str = Form(...),
):
    cfg.toggle_excepcion(emp_id, nombre)
    activo = str(emp_id) in cfg.ids_sin_sabados()
    empleado = None
    if REPORTE_PATH.exists():
        resultado = _procesar_guardado()
        empleado = next(
            (e for e in resultado["empleados"] if str(e["id"]) == str(emp_id)),
            None,
        )
    return JSONResponse({"activo": activo, "empleado": empleado})


@router.get("/exportar/pdf")
async def exportar_pdf_todos(
    usuario: dict = Depends(require_admin),
    quincena: int = 0,
    depto: str = "todos",
    detalle: bool = False,
):
    if not REPORTE_PATH.exists():
        return RedirectResponse("/asistencias/")

    try:
        resultado = _procesar_guardado()
    except Exception as exc:
        return HTMLResponse(f"Error al procesar: {exc}", status_code=500)

    periodo_raw = resultado.get("periodo", "")
    empleados_filtrados = []
    for emp in resultado["empleados"]:
        if depto != "todos" and emp["departamento"] != depto:
            continue
        totales = _totales_periodo(emp["detalle"], quincena)
        if totales["asistidos"] == 0:
            continue
        emp_data = dict(emp)
        emp_data["totales_periodo"] = totales
        if detalle:
            emp_data["detalle_periodo"] = [
                d for d in emp["detalle"]
                if quincena == 0 or (quincena == 1 and d["dia"] <= 15) or (quincena == 2 and d["dia"] >= 16)
            ]
        empleados_filtrados.append(emp_data)

    quincena_texto = "" if quincena == 0 else ("1ª Quincena" if quincena == 1 else "2ª Quincena")
    modo = "todos_detalle" if detalle else "todos"

    html_str = _pdf_templates.get_template("reporte_pdf.html").render(
        modo=modo,
        empleados=empleados_filtrados,
        periodo=periodo_raw,
        quincena_texto=quincena_texto,
        depto=depto,
        hoy=date.today().strftime("%d/%m/%Y"),
    )

    titulo = ("Reporte de Asistencias — Detalle por Empleado" if detalle
              else "Reporte de Asistencias — Resumen General")
    header = _header_pdf_html(titulo, periodo_raw, quincena_texto, depto, len(empleados_filtrados))
    footer = _footer_pdf_html(date.today().strftime("%d/%m/%Y"))

    try:
        pdf_bytes = _html_a_pdf(html_str, header, footer)
    except Exception as exc:
        return HTMLResponse(f"Error al generar PDF: {exc}", status_code=500)

    depto_slug = depto.replace(" ", "_") if depto != "todos" else "Todos"
    tipo_slug  = "detalle" if detalle else "simple"
    nombre = f"asistencias_{_periodo_slug(periodo_raw)}_{_quincena_slug(quincena)}_{depto_slug}_{tipo_slug}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/exportar/pdf/{emp_id}")
async def exportar_pdf_empleado(
    emp_id: str,
    usuario: dict = Depends(require_admin),
    quincena: int = 0,
):
    if not REPORTE_PATH.exists():
        return RedirectResponse("/asistencias/")

    try:
        resultado = _procesar_guardado()
    except Exception as exc:
        return HTMLResponse(f"Error al procesar: {exc}", status_code=500)

    empleado = next(
        (e for e in resultado["empleados"] if str(e["id"]) == str(emp_id)),
        None,
    )
    if not empleado:
        return HTMLResponse("Empleado no encontrado", status_code=404)

    periodo_raw = resultado.get("periodo", "")
    detalle_filtrado = [
        d for d in empleado["detalle"]
        if quincena == 0 or (quincena == 1 and d["dia"] <= 15) or (quincena == 2 and d["dia"] >= 16)
    ]
    totales = _totales_periodo(empleado["detalle"], quincena)
    quincena_texto = "" if quincena == 0 else ("1ª Quincena" if quincena == 1 else "2ª Quincena")

    html_str = _pdf_templates.get_template("reporte_pdf.html").render(
        modo="empleado",
        empleado=empleado,
        detalle=detalle_filtrado,
        totales=totales,
        periodo=periodo_raw,
        quincena_texto=quincena_texto,
        hoy=date.today().strftime("%d/%m/%Y"),
    )

    titulo = f"Reporte de Asistencias — {empleado['nombre']}"
    header = _header_pdf_html(titulo, periodo_raw, quincena_texto,
                               depto=empleado["departamento"])
    footer = _footer_pdf_html(date.today().strftime("%d/%m/%Y"))

    try:
        pdf_bytes = _html_a_pdf(html_str, header, footer)
    except Exception as exc:
        return HTMLResponse(f"Error al generar PDF: {exc}", status_code=500)

    nombre_seg = empleado["nombre"].replace(" ", "_")[:30]
    nombre = f"asistencias_{_periodo_slug(periodo_raw)}_{_quincena_slug(quincena)}_{nombre_seg}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
