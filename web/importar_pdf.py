"""
importar_pdf.py — Parser de PDFs de cotizaciones AROLUZ

Extrae datos de cabecera, tabla de ítems y condiciones comerciales
de PDFs generados con el template Excel AROLUZ.
"""

import re
import io
from typing import Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Meses en español para parsear la fecha del header
_MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
}

# Mapeo de palabras clave en descripción → tipo de producto
_TIPO_MAP = [
    (re.compile(r"BANDEJA", re.I),                         "B"),
    (re.compile(r"CURVA\s+H(?:ORIZONTAL)?", re.I),         "CH"),
    (re.compile(r"CURVA\s+V(?:ERTICAL)?\s*EXT", re.I),     "CVE"),
    (re.compile(r"CURVA\s+V(?:ERTICAL)?\s*INT", re.I),     "CVI"),
    (re.compile(r"\bTEE\b", re.I),                         "T"),
    (re.compile(r"\bCRUZ\b", re.I),                        "C"),
    (re.compile(r"REDUCCI[OÓ]N", re.I),                    "R"),
    (re.compile(r"CAJA", re.I),                             "CP"),
]


def _inferir_tipo(descripcion: str) -> str:
    for pattern, tipo in _TIPO_MAP:
        if pattern.search(descripcion):
            return tipo
    return "MANUAL"


def _inferir_galvanizado(descripcion: str) -> str:
    d = descripcion.strip()
    if d.upper().startswith("GC"):
        return "GC"
    if d.upper().startswith("GO"):
        return "GO"
    return "N/A"


def _limpiar_numero(texto: str) -> float:
    """Parsea números con coma de miles y punto decimal (ej: '1,234.56')."""
    if not texto:
        return 0.0
    texto = texto.strip().replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def _parsear_fecha(texto_pagina: str) -> str:
    """
    Busca el patrón "DD de MES del AAAA" o "DD de MES de AAAA"
    y lo convierte a YYYY-MM-DD HH:MM:SS.
    """
    patron = re.search(
        r"(\d{1,2})\s+de\s+([a-záéíóúü]+)\s+de[l]?\s+(\d{4})",
        texto_pagina,
        re.I,
    )
    if not patron:
        return ""
    dia  = patron.group(1).zfill(2)
    mes  = _MESES.get(patron.group(2).lower(), "01")
    anio = patron.group(3)
    return f"{anio}-{mes}-{dia} 00:00:00"


_ETIQUETAS_CABECERA = r'(?:UBICACI[OÓ]N|RUC|ATENCI[OÓ]N|CORREO|FECHA|SE[ÑN]ORES?|PROYECTO)'


def _parsear_header(texto: str) -> dict:
    """Extrae campos del encabezado de la primera página."""

    def buscar(patron: str) -> str:
        """patron puede contener grupos regex (no se escapa)."""
        m = re.search(rf"{patron}\s*:?\s*(.+?)(?:\n|$)", texto, re.I)
        return m.group(1).strip() if m else ""

    def cortar(raw: str) -> str:
        """Corta el valor antes de otra etiqueta de cabecera en la misma línea."""
        # Si el raw empieza directo con una etiqueta (ej. "PROYECTO: ASCENT"),
        # el campo real estaba vacío — lo que sigue es el campo de la columna derecha
        if re.match(rf'^{_ETIQUETAS_CABECERA}\s*:', raw, re.I):
            return ""
        val = re.split(
            rf'\s{{2,}}|\s+(?={_ETIQUETAS_CABECERA}\s*:)',
            raw,
            flags=re.I,
        )[0].strip()
        # Si el resultado es solo otra etiqueta (ej. "CORREO:"), el campo estaba vacío
        if re.match(rf'^{_ETIQUETAS_CABECERA}\s*:?\s*$', val, re.I):
            return ""
        return val

    cliente_raw = cortar(buscar("SE[ÑN]ORES"))
    palabras_cliente = cliente_raw.split()
    cliente_nombre = " ".join(palabras_cliente[:2]) if palabras_cliente else ""

    return {
        "cliente_nombre":    cliente_nombre,
        "cliente_ruc":       cortar(buscar("RUC")),
        "atencion":          cortar(buscar("ATENCI[OÓ]N")),
        "atencion_email":    cortar(buscar("CORREO")),
        "proyecto":          cortar(buscar("PROYECTO")),
        "cliente_ubicacion": cortar(buscar("UBICACI[OÓ]N")),
        "fecha":             _parsear_fecha(texto),
    }


def _parsear_condiciones(texto: str) -> dict:
    """Extrae moneda y validez del texto de condiciones comerciales."""

    moneda  = "SOLES"
    validez = "30 días"

    m_moneda = re.search(r"MONEDA\s*:?\s*(.+?)(?:\n|$)", texto, re.I)
    if m_moneda:
        raw = m_moneda.group(1).strip().upper()
        if "DOLAR" in raw or "USD" in raw or "$" in raw:
            moneda = "DOLARES"
        else:
            moneda = "SOLES"

    m_validez = re.search(r"VALIDEZ\s+DE\s+LA\s+OFERTA\s*:?\s*(.+?)(?:\n|$)", texto, re.I)
    if m_validez:
        raw = m_validez.group(1).strip()
        # Normalizar: "30 DÍAS", "30 días", "30 dias" → "30 días"
        num = re.search(r"\d+", raw)
        if num:
            validez = f"{num.group()} días"

    return {"moneda": moneda, "validez": validez}


def _parsear_tablas(pdf) -> tuple[list, list]:
    """
    Extrae ítems de producto de todas las páginas del PDF.
    Retorna (items, advertencias).
    """
    items       = []
    advertencias = []
    encabezado_tabla = ""

    for pagina in pdf.pages:
        tablas = pagina.extract_tables()
        for tabla in tablas:
            for fila in tabla:
                if not fila:
                    continue

                # Limpiar celdas None
                fila = [str(c).strip() if c is not None else "" for c in fila]

                # Detectar fila de encabezado de tabla (DESCRIPCIÓN / UND / CANT…)
                if any("DESCRIPCI" in c.upper() for c in fila):
                    continue

                # Detectar fila amarilla de aviso (ej: "BANDEJAS Y TAPAS FABRICADAS…")
                # Suele tener solo 1 celda con texto largo o primera columna con todo el texto
                textos_fila = [c for c in fila if c]
                if len(textos_fila) == 1 and len(textos_fila[0]) > 30:
                    encabezado_tabla = textos_fila[0]
                    continue

                # Detectar filas de totales: SUBTOTAL, IGV, TOTAL
                primera = fila[0].upper() if fila else ""
                if any(kw in primera for kw in ("SUBTOTAL", "I.G.V", "IGV", "TOTAL", "VALIDEZ", "MONEDA", "CONDIC")):
                    continue

                # Filtrar filas vacías
                if not any(fila):
                    continue

                # Intentar parsear como fila de producto
                # Estructura esperada: [ITEM, DESCRIPCION, UND, CANT, P.UNIT, TOTAL]
                # o sin ITEM: [DESCRIPCION, UND, CANT, P.UNIT, TOTAL]
                item = _extraer_item_de_fila(fila)
                if item:
                    items.append(item)

    return items, advertencias, encabezado_tabla


def _extraer_item_de_fila(fila: list) -> Optional[dict]:
    """
    Intenta extraer un ítem de producto de una fila de tabla.
    Devuelve None si la fila no parece un producto válido.
    Soporta formatos con y sin columna ITEM al inicio.
    """
    # Limpiar fila
    fila = [c.strip() for c in fila]

    # Necesitamos al menos 4 celdas con contenido útil
    no_vacios = [c for c in fila if c]
    if len(no_vacios) < 3:
        return None

    # Detectar si la primera columna es número de ítem (solo dígitos)
    col_start = 0
    if fila[0].isdigit():
        col_start = 1

    # Después del posible número de ítem debería estar la descripción
    # y al final: UND, CANT, P.UNIT, TOTAL (en ese orden)
    # Usamos heurística: los últimos 3-4 campos son numéricos (excepto UND)

    resto = fila[col_start:]
    if len(resto) < 3:
        return None

    # Intentar identificar las columnas numéricas al final
    # Formato típico: descripción, und, cant, p.unit, total
    # El precio total (último) y p.unit (penúltimo) deben ser numéricos
    # La cantidad (antepenúltimo) también numérico
    # La unidad puede ser "UND", "ML", "JGO", etc.

    # Buscar el índice donde empieza la parte numérica
    # Estrategia: desde el final, identificar hasta 3 números seguidos
    nums_desde_final = 0
    for val in reversed(resto):
        if re.match(r"^[\d,.\s]+$", val) and val.strip():
            nums_desde_final += 1
        else:
            break

    if nums_desde_final < 2:
        return None

    # La descripción es todo antes de la zona numérica (con posible unidad antes)
    # zona_final = [und?, cant, p_unit, total] o [cant, p_unit, total]
    idx_num_start = len(resto) - nums_desde_final

    # El campo antes de los números podría ser la unidad
    unidad = "UND"
    if idx_num_start > 0:
        posible_und = resto[idx_num_start - 1]
        if posible_und and not re.match(r"^[\d,.]+$", posible_und):
            unidad = posible_und
            idx_num_start -= 1

    descripcion = " ".join(c for c in resto[:idx_num_start] if c).strip()
    if not descripcion:
        return None

    nums = [_limpiar_numero(v) for v in resto[len(resto) - nums_desde_final:]]

    # Asignar según cantidad de números disponibles
    if len(nums) >= 3:
        cantidad     = nums[-3]
        precio_unit  = nums[-2]
        # precio_total = nums[-1]  (lo ignoramos, lo recalculamos)
    elif len(nums) == 2:
        cantidad    = nums[0]
        precio_unit = nums[1]
    else:
        return None

    # Validar que la descripción no sea basura
    if len(descripcion) < 3:
        return None

    return {
        "descripcion":        descripcion,
        "unidad":             unidad if unidad else "UND",
        "cantidad":           int(cantidad) if cantidad == int(cantidad) else cantidad,
        "precio_unitario":    round(precio_unit, 4),
        "peso_unitario":      0.0,
        "tipo":               _inferir_tipo(descripcion),
        "tipo_galvanizado":   _inferir_galvanizado(descripcion),
        "porcentaje_ganancia": "N/A",
    }


def parsear_pdf(pdf_bytes: bytes) -> dict:
    """
    Parsea un PDF de cotización AROLUZ y extrae los datos estructurados.

    Retorna:
        {"ok": True, "datos": {...}, "advertencias": [...]}
        {"ok": False, "error": "..."}
    """
    if pdfplumber is None:
        return {"ok": False, "error": "pdfplumber no está instalado en el servidor"}

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if not pdf.pages:
                return {"ok": False, "error": "El PDF está vacío o es inválido"}

            # Extraer texto de todas las páginas
            textos = []
            for p in pdf.pages:
                t = p.extract_text() or ""
                textos.append(t)

            texto_completo = "\n".join(textos)

            # Verificar que hay texto (PDF no escaneado)
            if len(texto_completo.strip()) < 50:
                return {"ok": False, "error": "PDF escaneado sin texto extraíble — no soportado"}

            # Parsear header (página 1)
            header = _parsear_header(textos[0])

            # Parsear condiciones (puede estar en cualquier página)
            conds = _parsear_condiciones(texto_completo)

            # Parsear tabla de ítems (todas las páginas)
            items, advertencias, encabezado_tabla = _parsear_tablas(pdf)

            if not items:
                return {
                    "ok": False,
                    "error": "No se encontraron ítems de producto en el PDF. "
                             "Verifica que el PDF use el template AROLUZ estándar.",
                }

            # Calcular total
            total = sum(
                i["precio_unitario"] * i["cantidad"]
                for i in items
            )

            datos = {
                **header,
                **conds,
                "encabezado_tabla": encabezado_tabla,
                "items":            items,
                "total_precio":     round(total, 2),
                "n_items":          len(items),
            }

            return {"ok": True, "datos": datos, "advertencias": advertencias}

    except Exception as e:
        return {"ok": False, "error": f"Error al procesar el PDF: {str(e)}"}
