"""
router.py — Router FastAPI para procesamiento de asistencias biométricas.

Montado en /asistencias/ dentro del cotizador web (puerto 8000).
Requiere rol ADMIN (require_asistencias de web.auth).
"""

import io
import re
from datetime import date
from pathlib import Path
from typing import List

import json as _json

_MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
_MESES_COMPLETOS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _periodo_slug(periodo_raw: str) -> str:
    """De '2026-02-01 ~ 2026-02-28' extrae 'Feb2026'."""
    m = re.match(r"(\d{4})-(\d{2})-\d{2}", periodo_raw.strip())
    if not m:
        return "periodo"
    anio, mes = int(m.group(1)), int(m.group(2))
    return f"{_MESES_ES[mes - 1]}{anio}" if 1 <= mes <= 12 else f"{mes:02d}{anio}"


def _periodo_label(periodo_raw: str) -> str:
    """De '2026-02-01 ~ 2026-02-28' extrae 'Febrero 2026'."""
    m = re.match(r"(\d{4})-(\d{2})-\d{2}", periodo_raw.strip())
    if not m:
        return periodo_raw
    anio, mes = int(m.group(1)), int(m.group(2))
    if 1 <= mes <= 12:
        # Si hay dos fechas (quincena) agrega indicador
        partes = [p.strip() for p in periodo_raw.split("~")]
        if len(partes) == 2:
            d_inicio = int(partes[0].split("-")[2])
            d_fin    = int(partes[1].split("-")[2])
            if d_inicio == 1 and d_fin <= 15:
                return f"{_MESES_COMPLETOS[mes - 1]} {anio} — 1ª Quincena"
            elif d_inicio >= 16:
                return f"{_MESES_COMPLETOS[mes - 1]} {anio} — 2ª Quincena"
        return f"{_MESES_COMPLETOS[mes - 1]} {anio}"
    return periodo_raw


def _quincena_slug(quincena: int) -> str:
    return "mes" if quincena == 0 else f"Q{quincena}"


def _recalcular_emp(emp: dict) -> dict:
    """Recalcula totales de un empleado a partir de su detalle fusionado."""
    detalle = sorted(emp["detalle"], key=lambda d: d["dia"])
    dias_asistidos        = sum(1 for d in detalle if not d.get("ausente"))
    dias_habiles_ausentes = sum(1 for d in detalle if d.get("ausente") and not d.get("es_fin_semana"))
    dias_estimados        = sum(1 for d in detalle if d.get("estimado"))
    total_min = sum(round(d["horas"] * 60) for d in detalle if d.get("horas") is not None)
    h, m = divmod(int(total_min), 60)
    result = dict(emp)
    result["detalle"]               = detalle
    result["dias_asistidos"]        = dias_asistidos
    result["dias_habiles_ausentes"] = dias_habiles_ausentes
    result["dias_estimados"]        = dias_estimados
    result["horas_trabajadas"]      = round(total_min / 60, 4)
    result["horas_trabajadas_fmt"]  = f"{h}h {m:02d}m"
    return result


def _merge_resultados(r1: dict, r2: dict) -> dict:
    """Fusiona dos resultados del mismo mes (p.ej. dos quincenas) en uno consolidado."""
    # Determinar rango de fechas combinado
    fechas = []
    for resultado in (r1, r2):
        for parte in resultado.get("periodo", "").split("~"):
            parte = parte.strip()
            if re.match(r"\d{4}-\d{2}-\d{2}", parte):
                fechas.append(parte)
    start = min(fechas) if fechas else ""
    end   = max(fechas) if fechas else ""
    periodo_merged = f"{start} ~ {end}" if start and end else r1.get("periodo", "")

    # Fusionar empleados por ID
    emp_map: dict = {}
    for emp in r1.get("empleados", []):
        emp_map[emp["id"]] = dict(emp)
        emp_map[emp["id"]]["detalle"] = list(emp["detalle"])
    for emp in r2.get("empleados", []):
        eid = emp["id"]
        if eid not in emp_map:
            emp_map[eid] = dict(emp)
            emp_map[eid]["detalle"] = list(emp["detalle"])
        else:
            dias_existentes = {d["dia"] for d in emp_map[eid]["detalle"]}
            for d in emp["detalle"]:
                if d["dia"] not in dias_existentes:
                    emp_map[eid]["detalle"].append(d)
            emp_map[eid] = _recalcular_emp(emp_map[eid])

    empleados_merged = sorted(emp_map.values(), key=lambda e: e.get("nombre", ""))
    return {
        "periodo":           periodo_merged,
        "fecha_exportacion": r1.get("fecha_exportacion") or r2.get("fecha_exportacion", ""),
        "empleados":         empleados_merged,
    }


def _calcular_kpis(datos: dict) -> dict:
    """Calcula KPIs del período procesado.
    Solo cuenta empleados con al menos un día asistido (ignora despedidos/inactivos sin marcas).
    """
    empleados = datos.get("empleados", [])
    # Filtrar empleados que no tienen ninguna marca registrada
    empleados_activos = [e for e in empleados if e.get("dias_asistidos", 0) > 0]
    if not empleados_activos:
        return {
            "total_empleados": 0, "pct_asistencia": 0, "total_ausencias": 0,
            "total_estimados": 0, "prom_horas_dia": 0, "dias_habiles_mes": 0,
            "empleados_sin_falta": 0,
        }
    total_asistidos = sum(e["dias_asistidos"] for e in empleados_activos)
    total_ausencias = sum(e["dias_habiles_ausentes"] for e in empleados_activos)
    total_estimados = sum(e["dias_estimados"] for e in empleados_activos)
    total_horas     = sum(e["horas_trabajadas"] for e in empleados_activos)
    dias_habiles_mes = sum(1 for d in empleados_activos[0]["detalle"] if not d["es_fin_semana"])
    total_posible   = len(empleados_activos) * dias_habiles_mes if dias_habiles_mes else 1
    pct_asistencia  = round(total_asistidos / total_posible * 100, 1) if total_posible else 0
    prom_horas      = round(total_horas / total_asistidos, 2) if total_asistidos else 0
    return {
        "total_empleados":    len(empleados_activos),
        "pct_asistencia":     pct_asistencia,
        "total_ausencias":    total_ausencias,
        "total_estimados":    total_estimados,
        "prom_horas_dia":     prom_horas,
        "dias_habiles_mes":   dias_habiles_mes,
        "empleados_sin_falta": sum(1 for e in empleados_activos if e["dias_habiles_ausentes"] == 0),
    }


from fastapi import APIRouter, File, Form, UploadFile, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup as _Markup

from web.asistencias.parser import procesar_reporte
from web.asistencias import config as cfg
from web.auth import require_asistencias as require_admin
from web.rutas.carrito import get_carrito
from web import database as db

# web/asistencias/ → parent = web/
_WEB_DIR  = Path(__file__).parent.parent
DATA_DIR  = _WEB_DIR / "data" / "asistencias"
REPORTE_PATH = DATA_DIR / "ultimo_reporte.xls"
NOMBRE_PATH  = DATA_DIR / "ultimo_reporte_nombre.txt"
REPORTES_DIR = DATA_DIR / "reportes"

router = APIRouter()

# Todos los templates en web/templates/
_templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))


def _tojson_filter(value):
    return _Markup(_json.dumps(value, ensure_ascii=False, default=str))


_templates.env.filters["tojson"] = _tojson_filter
_templates.env.filters["periodo_mes_solo"] = lambda s: s.split(" — ")[0]


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
    # Limpiar solo el reporte temporal al recargar (las reglas de excepciones se mantienen)
    for path in (REPORTE_PATH, NOMBRE_PATH):
        if path.exists():
            path.unlink()
    reportes = db.listar_reportes_asistencia()
    return _templates.TemplateResponse(
        "asistencias/index.html",
        _ctx(request, usuario, resultado=None, error=None, reportes=reportes),
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
    reportes = db.listar_reportes_asistencia()
    if not archivo.filename.lower().endswith(".xls"):
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None, reportes=reportes,
                 error="El archivo debe ser un .xls (reporte del sistema biométrico)."),
        )

    try:
        contenido = await archivo.read()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        REPORTE_PATH.write_bytes(contenido)
        NOMBRE_PATH.write_text(archivo.filename, encoding="utf-8")
        resultado = procesar_reporte(contenido, sin_sabados=cfg.ids_sin_sabados())
    except Exception as exc:
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None, reportes=reportes,
                 error=f"Error al procesar el archivo: {exc}"),
        )

    return _templates.TemplateResponse(
        "asistencias/index.html",
        _ctx(request, usuario, resultado=resultado, error=None, reportes=reportes),
    )


@router.get("/reprocesar", response_class=HTMLResponse)
async def reprocesar(request: Request, usuario: dict = Depends(require_admin)):
    reportes = db.listar_reportes_asistencia()
    if not REPORTE_PATH.exists():
        return RedirectResponse("/asistencias/")

    try:
        resultado = _procesar_guardado()
    except Exception as exc:
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None, reportes=reportes,
                 error=f"Error al reprocesar: {exc}"),
        )

    return _templates.TemplateResponse(
        "asistencias/index.html",
        _ctx(request, usuario, resultado=resultado, error=None, reportes=reportes),
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


@router.post("/subir")
async def subir_reportes(
    request: Request,
    archivos: List[UploadFile] = File(...),
    forzar: str = Form(""),
    usuario: dict = Depends(require_admin),
):
    """Sube uno o varios XLS, los procesa y los guarda en SQLite.
    Si forzar='1', sobreescribe reportes duplicados.
    Devuelve JSON con guardados, duplicados y errores.
    """
    REPORTES_DIR.mkdir(parents=True, exist_ok=True)
    guardados = []
    duplicados = []
    errores = []
    forzar_ok = forzar == "1"

    for archivo in archivos:
        nombre = archivo.filename or "sin_nombre.xls"
        try:
            contenido = await archivo.read()
            resultado = procesar_reporte(contenido, sin_sabados=cfg.ids_sin_sabados())
            periodo_raw   = resultado.get("periodo", "")
            periodo_lbl   = _periodo_label(periodo_raw)
            num_emp       = sum(1 for e in resultado.get("empleados", []) if e.get("dias_asistidos", 0) > 0)
            datos_str     = _json.dumps(resultado, ensure_ascii=False, default=str)

            # ── Caso 1: período exacto ya existe ──────────────────────────────
            existente_id = db.periodo_existe(periodo_raw)
            if existente_id and not forzar_ok:
                duplicados.append({
                    "periodo":        periodo_raw,
                    "periodo_label":  periodo_lbl,
                    "nombre_archivo": nombre,
                    "id_existente":   existente_id,
                })
                continue

            if existente_id and forzar_ok:
                db.actualizar_reporte_asistencia(
                    existente_id, nombre, usuario["u"], num_emp, datos_str
                )
                (REPORTES_DIR / f"{existente_id}.xls").write_bytes(contenido)
                guardados.append({"periodo": periodo_raw, "periodo_label": periodo_lbl, "id": existente_id})
                continue

            # ── Caso 2: mismo mes → fusionar automáticamente ─────────────────
            m_mes = re.match(r"(\d{4})-(\d{2})-\d{2}", periodo_raw.strip())
            reporte_mismo_mes = None
            if m_mes:
                reporte_mismo_mes = db.buscar_reporte_por_mes(
                    int(m_mes.group(1)), int(m_mes.group(2))
                )

            if reporte_mismo_mes:
                datos_existente  = _json.loads(reporte_mismo_mes["datos_json"])
                resultado_merged = _merge_resultados(datos_existente, resultado)
                periodo_merged   = resultado_merged["periodo"]
                label_merged     = _periodo_label(periodo_merged)
                num_merged       = sum(1 for e in resultado_merged["empleados"]
                                       if e.get("dias_asistidos", 0) > 0)
                datos_merged     = _json.dumps(resultado_merged, ensure_ascii=False, default=str)
                db.fusionar_reporte_asistencia(
                    reporte_mismo_mes["id"], periodo_merged, label_merged,
                    usuario["u"], num_merged, datos_merged,
                )
                (REPORTES_DIR / f"{reporte_mismo_mes['id']}.xls").write_bytes(contenido)
                guardados.append({
                    "periodo":       periodo_merged,
                    "periodo_label": label_merged,
                    "id":            reporte_mismo_mes["id"],
                    "fusionado":     True,
                })
                continue

            # ── Caso 3: período nuevo ─────────────────────────────────────────
            nuevo_id = db.guardar_reporte_asistencia(
                periodo_raw, periodo_lbl, usuario["u"], nombre, num_emp, datos_str
            )
            (REPORTES_DIR / f"{nuevo_id}.xls").write_bytes(contenido)
            guardados.append({"periodo": periodo_raw, "periodo_label": periodo_lbl, "id": nuevo_id})
        except Exception as exc:
            errores.append({"nombre_archivo": nombre, "error": str(exc)})

    return JSONResponse({"guardados": guardados, "duplicados": duplicados, "errores": errores})


@router.delete("/reportes/{reporte_id}")
async def eliminar_reporte(reporte_id: int, usuario: dict = Depends(require_admin)):
    """Elimina un reporte guardado de DB y su XLS en disco."""
    ok = db.eliminar_reporte_asistencia(reporte_id)
    if not ok:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    xls_path = REPORTES_DIR / f"{reporte_id}.xls"
    if xls_path.exists():
        xls_path.unlink()
    return JSONResponse({"ok": True})


@router.get("/reportes/{reporte_id}/procesar", response_class=HTMLResponse)
async def procesar_reporte_guardado(
    reporte_id: int,
    request: Request,
    usuario: dict = Depends(require_admin),
):
    """Carga el XLS de un reporte guardado en la vista de procesamiento temporal (sin modificar el guardado)."""
    reportes = db.listar_reportes_asistencia()
    reporte  = db.obtener_reporte_asistencia(reporte_id)
    if not reporte:
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None, error="Reporte no encontrado.", reportes=reportes),
        )
    xls_path = REPORTES_DIR / f"{reporte_id}.xls"
    if not xls_path.exists():
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None,
                 error="El archivo XLS de este reporte no está disponible en disco.",
                 reportes=reportes),
        )
    try:
        contenido = xls_path.read_bytes()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        REPORTE_PATH.write_bytes(contenido)
        NOMBRE_PATH.write_text(reporte["nombre_archivo"], encoding="utf-8")
        resultado = procesar_reporte(contenido, sin_sabados=cfg.ids_sin_sabados())
    except Exception as exc:
        return _templates.TemplateResponse(
            "asistencias/index.html",
            _ctx(request, usuario, resultado=None,
                 error=f"Error al procesar el reporte: {exc}", reportes=reportes),
        )
    return _templates.TemplateResponse(
        "asistencias/index.html",
        _ctx(request, usuario, resultado=resultado, error=None, reportes=reportes),
    )


@router.get("/dashboard/{reporte_id}", response_class=HTMLResponse)
async def dashboard(reporte_id: int, request: Request, usuario: dict = Depends(require_admin)):
    """Dashboard estadístico de un reporte guardado."""
    reporte = db.obtener_reporte_asistencia(reporte_id)
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    datos      = _json.loads(reporte["datos_json"])
    kpis       = _calcular_kpis(datos)
    todos_rep  = db.listar_reportes_asistencia()
    carrito    = get_carrito(usuario["u"])
    total_carrito = sum(i["precio_unitario"] * i["cantidad"] for i in carrito)
    return _templates.TemplateResponse(
        "asistencias/dashboard.html",
        {
            "request":       request,
            "usuario":       usuario,
            "n_carrito":     len(carrito),
            "total_carrito": round(total_carrito, 2),
            "active":        "asistencias",
            "reporte":       reporte,
            "datos":         datos,
            "kpis":          kpis,
            "todos_reportes": todos_rep,
        },
    )


@router.get("/api/dashboard/{reporte_id}")
async def api_dashboard(reporte_id: int, usuario: dict = Depends(require_admin)):
    """Devuelve datos + KPIs de un reporte para el comparador AJAX."""
    reporte = db.obtener_reporte_asistencia(reporte_id)
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    try:
        datos = _json.loads(reporte["datos_json"])
        kpis  = _calcular_kpis(datos)
        reporte_meta = {k: v for k, v in reporte.items() if k != "datos_json"}
        return JSONResponse({"reporte": reporte_meta, "kpis": kpis, "datos": datos})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al procesar datos del reporte: {exc}")


@router.get("/reportes/{reporte_id}/pdf")
async def exportar_pdf_reporte(
    reporte_id: int,
    usuario: dict = Depends(require_admin),
    quincena: int = 0,
    depto: str = "todos",
    detalle: bool = False,
):
    """Exporta PDF de un reporte guardado en SQLite."""
    reporte = db.obtener_reporte_asistencia(reporte_id)
    if not reporte:
        return HTMLResponse("Reporte no encontrado", status_code=404)

    try:
        resultado = _json.loads(reporte["datos_json"])
    except Exception as exc:
        return HTMLResponse(f"Error al leer datos: {exc}", status_code=500)

    periodo_raw = resultado.get("periodo", reporte["periodo"])
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

    html_str = _templates.get_template("asistencias/reporte_pdf.html").render(
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

    html_str = _templates.get_template("asistencias/reporte_pdf.html").render(
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

    html_str = _templates.get_template("asistencias/reporte_pdf.html").render(
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
