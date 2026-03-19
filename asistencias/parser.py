"""
parser.py — Lógica de lectura y cálculo del reporte de asistencia biométrico.

Estructura real de "Reporte de Asistencia":
  Fila 3 (índice 2):
      col 0 = "Periodo:", col 2 = "2026-02-01 ~ 2026-02-28"
      col 11 = fecha de exportación
  Fila 4 (índice 3):
      col 0 = 1.0, col 1 = 2.0, ..., col 27 = 28.0  (número de día → col_índice)
  Filas de empleado (pares de filas a partir de índice 4):
      Fila impar = encabezado: col 2=ID, col 10=Nombre, col 20=Departamento
      Fila par   = marcas:     col (día-1) = string concatenada tipo "11:0120:25"
"""

import re
import datetime
from typing import Optional

import xlrd

NOMBRE_HOJA = "Reporte de Asistencia"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_marcas(celda: str) -> list:
    """Divide una cadena de marcas en tokens HH:MM (grupos de 5 chars)."""
    celda = str(celda).strip()
    if not celda or celda in ("0", "0.0", ""):
        return []
    marcas = []
    i = 0
    while i + 4 < len(celda):
        token = celda[i : i + 5]
        if re.match(r"^\d{2}:\d{2}$", token):
            marcas.append(token)
        i += 5
    return marcas


def _hhmm_a_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _min_a_hhmm(minutos) -> str:
    minutos = max(0, int(round(float(minutos))))
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _parsear_fecha_inicio(periodo: str) -> Optional[datetime.date]:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", periodo.strip())
    if m:
        return datetime.date.fromisoformat(m.group(1))
    return None


# ─── Función principal ────────────────────────────────────────────────────────

def procesar_reporte(contenido_bytes: bytes, sin_sabados: set = None) -> dict:
    """
    Procesa el .xls del sistema biométrico y devuelve un dict con:
    - periodo, fecha_exportacion
    - empleados: lista de dicts con detalle por empleado
    """
    wb = xlrd.open_workbook(file_contents=contenido_bytes)

    # Buscar la hoja correcta
    try:
        ws = wb.sheet_by_name(NOMBRE_HOJA)
    except xlrd.biffh.XLRDError:
        # Si no existe por nombre, intentar índice 2
        ws = wb.sheet_by_index(2)

    def cell_str(row, col):
        try:
            v = ws.cell_value(row, col)
            if v is None:
                return ""
            s = str(v).strip()
            # xlrd puede devolver float para fechas como "2026-03-01" → 46101.0
            # Lo dejamos como string
            return s
        except Exception:
            return ""

    # ── Metadatos (fila 3, índice 2) ─────────────────────────────────────────
    periodo_raw = cell_str(2, 2)          # C3
    fecha_exp_raw = cell_str(2, 11)       # L3

    fecha_inicio = _parsear_fecha_inicio(periodo_raw)

    # ── Mapeo día → columna (fila 4, índice 3) ───────────────────────────────
    # col 0 = día 1, col 1 = día 2, ..., col 27 = día 28
    columnas_dia: dict = {}  # dia_num (int) → col_idx (int)
    for col in range(ws.ncols):
        v = ws.cell_value(3, col)
        try:
            dia_num = int(float(v))
            if 1 <= dia_num <= 31:
                columnas_dia[dia_num] = col
        except (ValueError, TypeError):
            pass

    DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    sin_sabados = {str(x) for x in (sin_sabados or set())}

    # ── Recorrer filas de empleados (pares desde índice 4) ───────────────────
    empleados = []
    fila = 4  # índice de la primera fila de encabezado de empleado

    while fila < ws.nrows:
        emp_id = cell_str(fila, 2)    # col C → valor del ID
        nombre = cell_str(fila, 10)   # col K → Nombre
        depto  = cell_str(fila, 20)   # col U → Departamento

        if not nombre:
            fila += 2
            continue

        fila_marcas = fila + 1
        ignorar_sabados = str(emp_id) in sin_sabados

        # ── Recolectar marcas completas (≥ 2) para calcular promedios ────────
        # Se calculan promedios separados para días L-V/Dom y para Sábados
        entradas_min    = []   # L-V y Dom
        salidas_min     = []
        entradas_min_sab = []  # solo Sábados
        salidas_min_sab  = []
        dias_raw: dict = {}  # dia_num → lista de strings HH:MM

        for dia_num, col_idx in columnas_dia.items():
            celda = ""
            if fila_marcas < ws.nrows:
                celda = cell_str(fila_marcas, col_idx)
            marcas = _parse_marcas(celda)
            # Empleados con regla especial: ignorar marcas de sábado
            if ignorar_sabados and fecha_inicio:
                try:
                    if fecha_inicio.replace(day=dia_num).weekday() == 5:
                        marcas = []
                except ValueError:
                    pass
            dias_raw[dia_num] = marcas
            if len(marcas) >= 2:
                e_min = _hhmm_a_min(marcas[0])
                s_min = _hhmm_a_min(marcas[-1])
                if fecha_inicio and fecha_inicio.replace(day=dia_num).weekday() == 5:
                    entradas_min_sab.append(e_min)
                    salidas_min_sab.append(s_min)
                else:
                    entradas_min.append(e_min)
                    salidas_min.append(s_min)

        prom_entrada     = (sum(entradas_min)     / len(entradas_min))     if entradas_min     else None
        prom_salida      = (sum(salidas_min)      / len(salidas_min))      if salidas_min      else None
        prom_entrada_sab = (sum(entradas_min_sab) / len(entradas_min_sab)) if entradas_min_sab else prom_entrada
        prom_salida_sab  = (sum(salidas_min_sab)  / len(salidas_min_sab))  if salidas_min_sab  else prom_salida

        # ── Calcular detalle por día ──────────────────────────────────────────
        detalle = []
        total_min = 0
        dias_asistidos = 0
        dias_habiles_ausentes = 0
        dias_estimados = 0

        for dia_num in sorted(columnas_dia.keys()):
            marcas = dias_raw.get(dia_num, [])

            if fecha_inicio:
                try:
                    fecha = fecha_inicio.replace(day=dia_num)
                except ValueError:
                    fila += 2
                    continue
            else:
                fecha = None

            es_fin_semana = (fecha.weekday() >= 5) if fecha else False
            dia_nombre = DIAS_ES[fecha.weekday()] if fecha else "???"
            fecha_str = f"{dia_nombre} {dia_num:02d}"

            entrada: Optional[str] = None
            salida:  Optional[str] = None
            horas:   Optional[float] = None
            horas_fmt: Optional[str] = None
            estimado = False
            estimado_entrada = False   # solo la entrada fue estimada
            estimado_salida  = False   # solo la salida fue estimada
            ausente  = False

            if len(marcas) == 0:
                ausente = True
                if not es_fin_semana:
                    dias_habiles_ausentes += 1

            elif len(marcas) == 1:
                marca_min = _hhmm_a_min(marcas[0])

                es_sabado = fecha is not None and fecha.weekday() == 5
                umbral = 13 * 60 if es_sabado else 14 * 60
                p_entrada = prom_entrada_sab if es_sabado else prom_entrada
                p_salida  = prom_salida_sab  if es_sabado else prom_salida

                if marca_min < umbral:
                    # Marca real = ENTRADA, se estima la SALIDA
                    if p_salida is not None:
                        dias_asistidos += 1
                        entrada = marcas[0]
                        salida = _min_a_hhmm(p_salida)
                        mins = max(0, int(round(p_salida)) - marca_min)
                        horas = mins / 60
                        horas_fmt = f"{mins // 60}h {mins % 60:02d}m"
                        total_min += mins
                        estimado = True
                        estimado_salida = True
                        dias_estimados += 1
                    else:
                        ausente = True
                        if not es_fin_semana:
                            dias_habiles_ausentes += 1
                else:
                    # Marca real = SALIDA, se estima la ENTRADA
                    if p_entrada is not None:
                        dias_asistidos += 1
                        salida = marcas[0]
                        entrada = _min_a_hhmm(p_entrada)
                        mins = max(0, marca_min - int(round(p_entrada)))
                        horas = mins / 60
                        horas_fmt = f"{mins // 60}h {mins % 60:02d}m"
                        total_min += mins
                        estimado = True
                        estimado_entrada = True
                        dias_estimados += 1
                    else:
                        ausente = True
                        if not es_fin_semana:
                            dias_habiles_ausentes += 1

            else:
                # 2+ marcas: primera=entrada, última=salida
                dias_asistidos += 1
                entrada = marcas[0]
                salida  = marcas[-1]
                e = _hhmm_a_min(entrada)
                s = _hhmm_a_min(salida)
                mins = max(0, s - e)
                horas = mins / 60
                horas_fmt = f"{mins // 60}h {mins % 60:02d}m"
                total_min += mins

            detalle.append({
                "dia":              dia_num,
                "fecha":            fecha_str,
                "es_fin_semana":    es_fin_semana,
                "entrada":          entrada,
                "salida":           salida,
                "horas":            horas,
                "horas_fmt":        horas_fmt,
                "estimado":         estimado,
                "estimado_entrada": estimado_entrada,
                "estimado_salida":  estimado_salida,
                "ausente":          ausente,
            })

        h = total_min // 60
        m = total_min % 60

        empleados.append({
            "id":                    emp_id,
            "nombre":                nombre,
            "departamento":          depto,
            "dias_asistidos":        dias_asistidos,
            "dias_habiles_ausentes": dias_habiles_ausentes,
            "horas_trabajadas":      total_min / 60,
            "horas_trabajadas_fmt":  f"{h}h {m:02d}m",
            "dias_estimados":        dias_estimados,
            "detalle":               detalle,
        })

        fila += 2

    return {
        "periodo":           periodo_raw,
        "fecha_exportacion": fecha_exp_raw,
        "empleados":         empleados,
    }
