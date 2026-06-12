"""email_imap.py — Router para sincronización de correo vía IMAP."""
import email as _email_mod
import email.header
import email.utils
import hashlib
import imaplib
import io
import re
import time
import unicodedata
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from web.auth import require_login, require_admin
from web.limits import limiter
from web.database import (
    ADJUNTOS_DIR,
    add_adjunto,
    add_oc_item,
    crear_proyecto,
    email_ya_importado,
    get_cliente_nombre_por_dominio,
    get_dominios_clientes,
    get_email_imap_config,
    pdf_hash_ya_importado,
    proyecto_existe,
    registrar_email_importado,
    save_email_imap_config,
    update_proyecto_numero_oc,
)

router = APIRouter()


# ── Palabras clave de OC ──────────────────────────────────────────────────────

# Patrones que indican que el correo es una orden de compra
_OC_PATTERNS = [
    r"\bOC\b",
    r"\bO\.C\.\b",
    r"ORDEN\s+DE\s+COMPRA",
    r"ORDEN_DE_COMPRA",
    r"PURCHASE\s+ORDER",
    r"\bP\.O\.\b",
    r"\bPEDIDO\b",
    r"NOTA\s+DE\s+PEDIDO",
    r"SOLICITUD\s+DE\s+COMPRA",
]
_OC_RE = re.compile("|".join(_OC_PATTERNS), re.IGNORECASE)

# Patrones que identifican un INGRESO/RECEPCIÓN de OC — se deben EXCLUIR
_INGRESO_OC_RE = re.compile(
    r"(?:"
    r"\bINGRESO\s+(?:POR\s+)?(?:ORDEN\s+(?:DE\s+)?COMPRA|O\.?C\.?|O/C)"
    r"|\bINGRESO\s+DE\s+ALMAC[EÉ]N"
    r"|\bNOTA\s+DE\s+INGRESO\b"
    r"|\bING\.?\s+(?:OC\b|O\.?C\.?|O/C)"
    r"|\bIOC[-_/]"
    r")",
    re.IGNORECASE,
)

# Patrones de falsos positivos: correos que mencionan OC pero NO son órdenes de compra
_FALSO_POSITIVO_RE = re.compile(
    r"(?:"
    # Solicitudes de documentos / calidad / certificados / fichas
    r"SOLICITUD\s+DE\s+DOCUMENTOS"
    r"|DOCUMENTOS\s+DE\s+CALIDAD"
    r"|SOLICITUD\s+DE\s+CALIDAD"
    r"|SOLICITUD\s+DE\s+CERTIFICAD[OA]S?"
    r"|FICHA\s+T[EÉ]CNICA"
    # Homologación
    r"|SOLICITUD\s+DE\s+HOMOLOGACI[OÓ]N"
    r"|\bHOMOLOGACI[OÓ]N\b"
    # Solicitudes de cotización / precio (no son compras todavía)
    r"|SOLICITUD\s+DE\s+COTIZACI[OÓ]N"
    r"|SOLICITUD\s+DE\s+PRECIO"
    # Consultas (ej: "Consulta sobre OC", "Consulta de precios")
    r"|\bCONSULTA\s+(?:SOBRE|DE|POR|ACERCA|RESPECTO)"
    # Seguimiento de OC existente
    r"|\bSEGUIMIENTO\s+(?:DE\s+)?(?:OC\b|O\.C\.|O/C|ORDEN)"
    # Confirmación de recepción / acuse de recibo
    r"|CONFIRMACI[OÓ]N\s+DE\s+RECEPCI[OÓ]N"
    r"|RECEPCI[OÓ]N\s+DE\s+(?:OC\b|O\.C\.|O/C|ORDEN)"
    # Validación / observaciones / anulación de OC
    r"|VALIDACI[OÓ]N\s+DE\s+(?:OC\b|O\.C\.|O/C|ORDEN)"
    r"|OBSERVACIONES\s+(?:A\s+LA\s+|DE\s+)?(?:OC\b|O\.C\.|O/C|ORDEN)"
    r"|ANULACI[OÓ]N\s+DE\s+(?:OC\b|O\.C\.|O/C|ORDEN)"
    # Garantía / muestra / información
    r"|SOLICITUD\s+DE\s+GARANT[IÍ]A"
    r"|SOLICITUD\s+DE\s+MUESTRA"
    r"|REQUERIMIENTO\s+DE\s+INFORMACI[OÓ]N"
    r")",
    re.IGNORECASE,
)


def _texto_es_oc(texto: str) -> bool:
    return bool(_OC_RE.search(texto))


def _texto_es_ingreso_oc(texto: str) -> bool:
    """True si el texto indica que es un ingreso/recepción de OC (no una OC)."""
    return bool(_INGRESO_OC_RE.search(texto))


def _texto_es_falso_positivo(texto: str) -> bool:
    """True si el asunto parece relacionado con OC pero NO es una orden de compra real."""
    return bool(_FALSO_POSITIVO_RE.search(texto))


def _sender_domain(from_header: str) -> str:
    """Extrae el dominio del remitente, en minúsculas. Ej: 'empresa.com'."""
    _, addr = email.utils.parseaddr(from_header)
    if "@" in addr:
        return addr.split("@", 1)[1].strip().lower()
    return ""


# ── Helpers de decodificación ─────────────────────────────────────────────────

def _decode_header(value: str) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            try:
                decoded.append(data.decode(charset or "utf-8", errors="replace"))
            except Exception:
                decoded.append(data.decode("latin-1", errors="replace"))
        else:
            decoded.append(str(data))
    return " ".join(decoded).strip()


def _extraer_oc(texto: str) -> str:
    """Extrae el número de OC del texto; soporta códigos alfanuméricos (ej. JEF8977)."""
    patterns = [
        r"OC[-_]([A-Z]{1,8}\d+)",               # OC-JEF8977 → JEF8977
        r"OC\s*[-#:N°]*\s*([A-Z]{2,8}-\d{3,})", # OC EDEM-0191 → EDEM-0191
        r"OC\s*[-#:N°]*\s*([A-Z]{2,8}\d+)",     # OC JEF8977 → JEF8977
        r"OC\s*[-#:N°]*\s*(\d+)",
        r"O\.C\.\s*[-#:N°]*\s*(\d+)",
        r"ORDEN\s+DE\s+COMPRA\s*[-#:N°]*\s*(\d+)",
        r"PEDIDO\s*[-#:N°]*\s*(\d+)",
        r"PO\s*[-#:N°]*\s*(\d+)",
        r"N[°o]?\s*(\d{3,})",
    ]
    texto_upper = texto.upper()
    for pat in patterns:
        m = re.search(pat, texto_upper)
        if m:
            return m.group(1)
    return ""


def _cliente_de_oc(numero_oc: str) -> str:
    """Extrae el prefijo alfabético de un código de OC. Ej: 'JEF8977' → 'JEF'. Solo si ≥3 letras."""
    if not numero_oc:
        return ""
    m = re.match(r"^([A-Z]{3,8})\d+$", numero_oc.upper())
    return m.group(1) if m else ""


_TRIVIAL_DOMINIOS = {"www", "mail", "smtp", "pop", "imap", "m", "webmail", "com", "net", "org", "edu", "gob", "gov", "co"}


def _dominio_a_empresa(domain: str) -> str:
    """'enersac.pe' → 'ENERSAC'. Elimina TLD y subdominios triviales."""
    if not domain:
        return ""
    partes = domain.lower().split(".")
    candidates = [p for p in partes[:-1] if p not in _TRIVIAL_DOMINIOS and len(p) >= 2]
    return candidates[-1].upper() if candidates else ""


# Segmentos de asunto que se consideran ruido y se descartan
_NOISE_SEGMENT_RE = re.compile(
    r"^(VALIDACI[OÓ]N|AROLUZ|CONTADO)$|"
    r"CR[EÉ]DITO|"
    r"^COT\.\s*\w+|"
    r"^REQ\.\s*\w+|"
    r"^V\d+$",
    re.IGNORECASE,
)


def _limpiar_asunto(asunto: str, numero_oc: str) -> str:
    """Extrae el nombre de obra del asunto descartando segmentos de ruido."""
    limpio = re.sub(r"^(re|fw|fwd|rv|rve):\s*", "", asunto.strip(), flags=re.IGNORECASE)
    segmentos = [s.strip() for s in re.split(r"\s*[-–]\s*", limpio) if s.strip()]
    resultado = []
    for seg in segmentos:
        # Descartar segmentos que contienen patrones de OC
        if _OC_RE.search(seg):
            continue
        # Descartar el número de OC si aparece solo
        if numero_oc and re.search(re.escape(numero_oc), seg, re.IGNORECASE):
            continue
        # Descartar tokens de ruido conocidos
        if _NOISE_SEGMENT_RE.search(seg):
            continue
        # Descartar tokens muy cortos (≤3 chars: códigos de empresa, siglas)
        if len(seg) <= 3:
            continue
        resultado.append(seg)
    return " - ".join(resultado)


def _body_text(msg) -> str:
    """Extrae el texto plano del cuerpo del email (partes text/plain o text/html)."""
    chunks = []
    for part in msg.walk():
        ct = part.get_content_type()
        if ct not in ("text/plain", "text/html"):
            continue
        try:
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            chunks.append(payload.decode(charset, errors="replace"))
            if len(chunks) >= 3:  # suficiente para detectar keywords
                break
        except Exception:
            continue
    return " ".join(chunks)


# ── IMAP helpers ──────────────────────────────────────────────────────────────

_IMAP_TIMEOUT = 20  # segundos

def _conectar_imap(cfg: dict) -> imaplib.IMAP4_SSL:
    imap = imaplib.IMAP4_SSL(cfg["host"], cfg["port"], timeout=_IMAP_TIMEOUT)
    imap.login(cfg["username"], cfg["password"])
    return imap


_HDR_FIELDS = "(BODY[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID CONTENT-TYPE)])"


def _pdf_es_oc(filename: str) -> bool:
    """True si el nombre del archivo sugiere que es una orden de compra."""
    return bool(_OC_RE.search(filename)) or "ORDEN" in filename.upper()


def _collect_pdfs(msg) -> list:
    """
    Devuelve lista de dicts {index, filename} donde index es la posición
    de walk del adjunto (invariante al ordenar la lista).
    Los PDFs que parecen OC (por nombre) se muestran primero.
    """
    pdfs = []
    for part in msg.walk():
        ct = part.get_content_type() or ""
        fn = _decode_header(part.get_filename() or "")
        if (ct == "application/pdf" or fn.lower().endswith(".pdf")) and fn:
            pdfs.append({"index": len(pdfs), "filename": fn})
    pdfs.sort(key=lambda p: (0 if _pdf_es_oc(p["filename"]) else 1))
    return pdfs


def _get_pdf_bytes_from_msg(msg, pdf_index: int = 0) -> Optional[bytes]:
    """Devuelve los bytes del PDF en la posición pdf_index dentro del mensaje."""
    pdf_count = 0
    for part in msg.walk():
        ct = part.get_content_type() or ""
        fn = _decode_header(part.get_filename() or "")
        if not ((ct == "application/pdf" or fn.lower().endswith(".pdf")) and fn):
            continue
        if pdf_count == pdf_index:
            payload = part.get_payload(decode=True)
            return payload if isinstance(payload, bytes) else None
        pdf_count += 1
    return None


def _pdf_hash(pdf_bytes: bytes) -> str:
    """SHA-256 hex del contenido del PDF, para detectar duplicados entre reenvíos."""
    return hashlib.sha256(pdf_bytes).hexdigest()


# ── Normalización de fechas ────────────────────────────────────────────────────

_MESES_NUM = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "may": "05", "jun": "06", "jul": "07", "ago": "08",
    "sep": "09", "set": "09", "oct": "10", "nov": "11", "dic": "12",
    "jan": "01", "apr": "04", "aug": "08", "dec": "12",
}


def _normalizar_fecha(s: str) -> str:
    """Normaliza cualquier formato de fecha reconocible a dd/mm/yyyy."""
    s = s.strip()
    if not s:
        return s
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if m:
        d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{d}/{mo}/{('20' + y) if len(y) == 2 else y}"
    m = re.match(r"^(\d{1,2})[-.](\d{1,2})[-.](\d{2,4})$", s)
    if m:
        d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{d}/{mo}/{('20' + y) if len(y) == 2 else y}"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    m = re.match(r"^(\d{1,2})\s+(?:de\s+)?(\w+?)(?:\s+de)?\s+(\d{4})$", s, re.IGNORECASE)
    if m:
        mes_num = _MESES_NUM.get(m.group(2).lower()[:3])
        if mes_num:
            return f"{m.group(1).zfill(2)}/{mes_num}/{m.group(3)}"
    return s


# ── Patrones para formato S10 ─────────────────────────────────────────────────
# S10 usa "Número [OC]" / "Fecha [dd/mm/yyyy]" / "Facturar a [empresa]" /
# "Proyecto ... \n [valor]" / "Lugar de entrega [dirección]" / "Fecha de entrega [fecha]"

_S10_NUMERO_RE = re.compile(
    # Sin IGNORECASE: sólo "Número" con mayúscula y tilde, no "número de Orden..."
    # v? cubre el artefacto de pdfplumber "Número vEDEM-0191" (columna adyacente fusionada)
    # (?:\s+\d[A-Z0-9\-]*)? permite código con espacio: "ERF 1ER-0433"
    r"\bNúmero\s+v?([A-Z][A-Z0-9\-]{1,}(?:\s+\d[A-Z0-9\-]*)?|\d{4,})",
)
# "Fecha dd/mm/yyyy" con capital F — no coincide con "Fecha de entrega" (que tiene "de" antes del número)
_S10_FECHA_OC_RE = re.compile(
    r"\bFecha\s+(\d{1,2}/\d{1,2}/\d{2,4})",
)
_S10_CLIENTE_RE = re.compile(r"\bFacturar\s+a\s+(.+)")
# "Proyecto Almacén Pedido(s)\n077 PROYECTO ELEMENT De Materiales 0571"
_S10_PROYECTO_RE = re.compile(
    r"^Proyecto\s+Almac[eé]n\b[^\n]*\n([^\n]{4,})",
    re.IGNORECASE | re.MULTILINE,
)
_S10_PROYECTO_SIMPLE_RE = re.compile(
    r"^Proyecto\b[ \t]*\n([^\n]{4,})",
    re.IGNORECASE | re.MULTILINE,
)
# Se detiene antes de "Móvil", "Celular", "Nextel" o "Fax" que aparecen en la misma línea
_S10_LUGAR_RE = re.compile(
    r"Lugar\s+de\s+entrega\s+(.+?)(?=\s+(?:M[óo]vil|Celular|Nextel|Fax)|\n|$)",
    re.IGNORECASE,
)
_S10_FECHA_ENTREGA_RE = re.compile(
    r"Fecha\s+de\s+entrega\s+(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# ── Patrones para formatos no-S10 (ej. JEF Servicios, otros) ─────────────────
# JEF usa "Nº 0001-0008977" / "Lima,dd/mm/yyyy" / empresa en primer línea /
# "Glosa : descripción" / "Dirección Entrega : dirección" / "Fecha Entrega : fecha"

_GEN_NUMERO_RE = re.compile(
    r"(?:N[°oºrR][o°\.]?\s*|ORDEN\s+DE\s+COMPRA\s+N[°oº\.]\s*)"
    r"(\d{3,4}-\d{4,8}|\d{3,4}-\d{3,4}-[A-Z]{2,8}-\d{4,}|\d{3,}-\d{3,}|[A-Z]{1,8}\d{3,8}|\d{4,})",
    re.IGNORECASE,
)
_GEN_FECHA_OC_CIUDAD_RE = re.compile(
    r"(?:Lima|Callao|Arequipa|Trujillo|Chiclayo|Piura|Cusco|Iquitos)\s*,\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
_GEN_FECHA_STANDALONE_RE = re.compile(
    r"(?<!\w)Fecha\s*:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
_GEN_GLOSA_RE = re.compile(r"Glosa\s*[:\-]\s*(.+)", re.IGNORECASE)
_GEN_DIR_ENTREGA_RE = re.compile(
    r"Direcci[oó]n\s+(?:de\s+)?[Ee]ntrega\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)
_GEN_FECHA_ENTREGA_RE = re.compile(
    r"Fecha\s+(?:de\s+)?[Ee]ntrega\s*[:\-]\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# ── Patrones de fallback (etiquetas genéricas) ────────────────────────────────

_PDF_LABEL_RE = re.compile(
    r"(?:GLOSA|OBRA|PROYECTO|NOMBRE\s+DE\s+(?:LA\s+)?OBRA|NOMBRE\s+DEL\s+PROYECTO"
    r"|DESCRIPCI[OÓ]N(?:\s+DEL\s+(?:TRABAJO|PROYECTO|SERVICIO))?"
    r"|REFERENCIA|TRABAJO|SERVICIO|DENOMINACI[OÓ]N)\s*[:\-–]\s*(.+)",
    re.IGNORECASE,
)
_PDF_LUGAR_RE = re.compile(
    r"(?:LUGAR\s+DE\s+ENTREGA|DIRECCI[OÓ]N\s+DE\s+ENTREGA(?:\s+DE\s+MERCADER[IÍ]A)?"
    r"|DIRECCI[OÓ]N\s+DE\s+DESPACHO"
    r"|PUNTO\s+DE\s+ENTREGA|DESPACHAR\s+A|ENTREGAR\s+EN|DESTINO"
    r"|EFECTUAR\s+LA\s+ENTREGA\s+EN)\s*[:\-–]\s*(.+)",
    re.IGNORECASE,
)
_PDF_FECHA_ENTREGA_RE = re.compile(
    r"(?:FECHA\s+DE\s+ENTREGA|PLAZO\s+DE\s+ENTREGA"
    r"|FECHA\s+(?:L[IÍ]MITE|M[AÁ]X(?:IMA)?|REQUERIDA|SOLICITADA))\s*[:\-–]\s*(.+)",
    re.IGNORECASE,
)
_PDF_CODE_RE = re.compile(
    r"\b([A-Z]{2,5}-\d{3,8})\s*[-–]\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\s]{3,80})\b",
    re.IGNORECASE,
)
_PDF_LABEL_KEYWORDS = (
    "GLOSA", "OBRA", "PROYECTO", "REFERENCIA",
    "DESCRIPCION", "DESCRIPCIÓN", "TRABAJO", "SERVICIO", "DENOMINACION",
)
_PDF_LUGAR_KEYWORDS = (
    "LUGAR DE ENTREGA", "DIRECCIÓN DE ENTREGA", "DIRECCION DE ENTREGA",
    "DIRECCIÓN DE ENTREGA DE MERCADERIA", "DIRECCION DE ENTREGA DE MERCADERIA",
    "DIRECCIÓN DE DESPACHO", "DIRECCION DE DESPACHO", "PUNTO DE ENTREGA",
    "DESPACHAR A", "DESTINO", "EFECTUAR LA ENTREGA EN",
)
_PDF_FECHA_ENTREGA_KEYWORDS = (
    "FECHA DE ENTREGA", "PLAZO DE ENTREGA", "FECHA LÍMITE",
    "FECHA LIMITE", "FECHA REQUERIDA", "FECHA SOLICITADA",
)
# Valores que parecen nombres de obra pero son títulos de sección del documento
_LABEL_BLACKLIST = frozenset({
    "ORDEN DE COMPRA", "ORDEN DE COMPRA N", "NOTA DE PEDIDO",
    "PURCHASE ORDER", "SOLICITUD DE COMPRA", "REQUERIMIENTO",
})

_CAMPOS_PDF_RE = [
    ("nombre_obra",   _PDF_LABEL_RE),
    ("lugar_entrega", _PDF_LUGAR_RE),
    ("fecha_entrega", _PDF_FECHA_ENTREGA_RE),
]
_CAMPOS_PDF_KWS = [
    (_PDF_LABEL_KEYWORDS,         "nombre_obra"),
    (_PDF_LUGAR_KEYWORDS,         "lugar_entrega"),
    (_PDF_FECHA_ENTREGA_KEYWORDS, "fecha_entrega"),
]


_CAMPO_LABEL_CUT_RE = re.compile(
    r"\s+(?:FECHA\s+DE\s+EMISI[OÓ]N|RUC\s*:|\bPROVEEDOR\s*:|\bRUBRO\s*:)",
    re.IGNORECASE,
)
# Cortar lugar_entrega cuando pdfplumber fusiona líneas de horarios/contacto/referencias
_LUGAR_CORTE_RE = re.compile(
    r"\s+(?:Ref\.|HORARIOS?\s*:|CONTACTO\s*:|TEL[EÉ]FONOS?\s*:|I\.G\.V\.|\bIGV\b"
    r"|TOTAL\s+S/|DESCUENTO|OBSERVACI|ATENCION\s+DE\s+ENTREGA|DIRECCI[OÓ]N\s+DE\s+ENTREGA\s+DE\s+COMP)",
    re.IGNORECASE,
)


def _limpiar_valor_pdf(val: str) -> str:
    first_line = val.strip().splitlines()[0] if val.strip() else val.strip()
    # Cortar cuando pdfplumber fusiona el valor con etiquetas de campo adyacentes
    first_line = _CAMPO_LABEL_CUT_RE.split(first_line, maxsplit=1)[0]
    return re.sub(r"\s+", " ", first_line).strip(".:,;-– ")


def _limpiar_lugar(val: str) -> str:
    """Limpia lugar_entrega cortando antes de horarios/contacto/referencias fusionadas."""
    # Primero: tomar la primera línea real
    lineas = [ln.strip() for ln in val.splitlines() if ln.strip()]
    if not lineas:
        return ""
    primera = lineas[0]
    # Cortar si hay texto administrativo fusionado en la misma línea
    primera = _LUGAR_CORTE_RE.split(primera, maxsplit=1)[0]
    return re.sub(r"\s+", " ", primera).strip(".:,;-– ")


def _limpiar_proyecto_s10(raw: str) -> str:
    """'077 PROYECTO ELEMENT De Materiales 0571' → '077 PROYECTO ELEMENT'."""
    return re.sub(
        r"\s+De\s+(?:Materiales|Servicios|Activos|Suministros)\b.*$",
        "", raw.strip(), flags=re.IGNORECASE,
    ).strip()


_EMPRESA_SKIP_INICIO_RE = re.compile(
    r"^(?:Tel[eé]fono|Celular|Web|RUC|Fax|Nextel|E-?mail|Direcci[oó]n|Fecha|Lugar|"
    r"Forma\s+de\s+Pago|Cta\.?|Cuenta|Centro|Gestor|Aprobado|Solicitante|Tratado|"
    r"Proveedor|Observaci[oó]n|Item|Proyecto|Almac[eé]n)",
    re.IGNORECASE,
)


def _extraer_empresa_emisora(texto: str) -> str:
    """Primera empresa encontrada (sufijo S.A.C./S.R.L./E.I.R.L./SAC etc.) que no sea AROLUZ."""
    for line in texto.splitlines()[:20]:
        line = line.strip()
        if len(line) < 5:
            continue
        # Saltear líneas que empiezan con datos de contacto u otros campos no-empresa
        if _EMPRESA_SKIP_INICIO_RE.match(line):
            continue
        # Capturar hasta el sufijo empresarial (con o sin puntos ni punto final)
        m = re.search(
            r"^(.+?(?:S\.A\.C\.?|S\.R\.L\.?|E\.I\.R\.L\.?|S\.A\.?"
            r"|\bSAC\b|\bSRL\b|\bEIRL\b))",
            line, re.IGNORECASE,
        )
        if m:
            empresa = m.group(1).strip()
            if "AROLUZ" not in empresa.upper():
                return empresa[:100]
    return ""


def _parsear_s10(texto: str, tables: list, out: dict) -> None:
    """Extrae campos de OCs en formato S10. Modifica out en place."""

    if not out["numero_oc"]:
        m = _S10_NUMERO_RE.search(texto)
        if m:
            out["numero_oc"] = m.group(1).strip()

    if not out["fecha_oc"]:
        m = _S10_FECHA_OC_RE.search(texto)
        if m:
            out["fecha_oc"] = m.group(1).strip()

    if not out["cliente"]:
        m = _S10_CLIENTE_RE.search(texto)
        if m:
            val = _limpiar_valor_pdf(m.group(1))
            if len(val) >= 3 and not re.match(r"^(?:AV\.|JR\.|CA\.|URB\.|MZ\.)", val, re.IGNORECASE):
                out["cliente"] = val

    if not out["nombre_obra"]:
        m = _S10_PROYECTO_RE.search(texto) or _S10_PROYECTO_SIMPLE_RE.search(texto)
        if m:
            clean = _limpiar_proyecto_s10(m.group(1))
            if len(clean) >= 4:
                out["nombre_obra"] = clean[:150]

    if not out["lugar_entrega"]:
        m = _S10_LUGAR_RE.search(texto)
        if m:
            out["lugar_entrega"] = _limpiar_lugar(m.group(1))

    if not out["fecha_entrega"]:
        m = _S10_FECHA_ENTREGA_RE.search(texto)
        if m:
            out["fecha_entrega"] = m.group(1).strip()

    # Tablas S10: celdas con etiqueta exacta → valor en celda adyacente
    _S10_TABLE_KEYS: dict = {
        "numero_oc":     ("NUMERO", "NÚMERO"),
        "fecha_oc":      ("FECHA",),
        "cliente":       ("FACTURAR A",),
        "nombre_obra":   ("PROYECTO",),
        "lugar_entrega": ("LUGAR DE ENTREGA",),
        "fecha_entrega": ("FECHA DE ENTREGA",),
    }
    for table in tables:
        for row in (table or []):
            if not row:
                continue
            for i, cell in enumerate(row):
                if not cell:
                    continue
                cell_up = re.sub(r"\s+", " ", cell.strip()).upper()
                for field, kws in _S10_TABLE_KEYS.items():
                    if out[field]:
                        continue
                    if cell_up in kws:
                        for j in range(i + 1, min(i + 3, len(row))):
                            val = _limpiar_valor_pdf(row[j] or "")
                            if len(val) >= 2:
                                if field == "nombre_obra":
                                    val = _limpiar_proyecto_s10(val)
                                out[field] = val[:200]
                                break


_TABLA_HDR_KWS = ("ITEM", "DESCRIPCI", "CODIGO", "PRECIO UNIT", "V. UNIT", "TOTAL")


def _parsear_generico(texto: str, tables: list, textos_pag: list, out: dict) -> None:
    """Fallback para formatos no-S10. Solo rellena campos aún vacíos."""

    if not out["numero_oc"]:
        # Alta prioridad: patrones específicos con prefijo explícito antes del fallback genérico
        m = re.search(r"\bORDEN\s+DE\s+COMPRA\s+NRO\s*[:\-]\s*(\S+)", texto, re.IGNORECASE)
        if not m:
            m = re.search(r"\bNro\.\s+(\d{5,})", texto, re.IGNORECASE)
        if not m:
            m = re.search(r"\b(OC[-_]\d{2,4}[-_]\d{2,4})\b", texto, re.IGNORECASE)
        if not m:
            m = _GEN_NUMERO_RE.search(texto)
        if m:
            out["numero_oc"] = m.group(1).strip()

    if not out["fecha_oc"]:
        m = _GEN_FECHA_OC_CIUDAD_RE.search(texto) or _GEN_FECHA_STANDALONE_RE.search(texto)
        if m:
            out["fecha_oc"] = m.group(1).strip()

    if not out["nombre_obra"]:
        m = _GEN_GLOSA_RE.search(texto)
        if m:
            val = _limpiar_valor_pdf(m.group(1))
            if len(val) >= 4 and val.upper() not in _LABEL_BLACKLIST:
                out["nombre_obra"] = val[:150]

    # Patrón "PROYECTO : valor\ncontinuación" (MPS y similares — label con dos puntos)
    if not out["nombre_obra"]:
        m = re.search(r"\bPROYECTO\s*[:\-]\s*([^\n]{4,})", texto, re.IGNORECASE)
        if m:
            partes = [_limpiar_valor_pdf(m.group(1))]
            # Si la primera parte termina incompleta (última palabra ≤2 chars), tomar la siguiente línea
            primer = partes[0]
            ultimo_token = primer.rsplit(None, 1)[-1] if primer else ""
            if len(ultimo_token) <= 2:
                resto = texto[m.end():].lstrip()
                _TABLA_HDR_KWS = ("ITEM", "DESCRIPCI", "CODIGO", "PRECIO UNIT", "V. UNIT", "TOTAL")
                for ln in resto.splitlines():
                    ln = ln.strip()
                    if not ln or re.match(r"^\d{1,2}/", ln):
                        continue
                    if re.search(r"(?:FECHA|RUC|DIRE|TELE|FORMA|SOLICIT|PROVEEDOR|AREA|DATOS)\b", ln, re.IGNORECASE):
                        break
                    # Saltear líneas que son encabezados de tabla
                    if any(kw in ln.upper() for kw in _TABLA_HDR_KWS):
                        break
                    partes.append(_limpiar_valor_pdf(ln))
                    break
            val = " ".join(p for p in partes if p and p.upper() not in _LABEL_BLACKLIST)
            if len(val) >= 4:
                out["nombre_obra"] = val[:150]

    if not out["lugar_entrega"]:
        m = _GEN_DIR_ENTREGA_RE.search(texto)
        if m:
            val = m.group(1).strip()
            if len(val) < 60:
                # Primera línea no vacía después del match
                nxt = next((ln.strip() for ln in texto[m.end():].splitlines() if ln.strip()), "")
                if nxt:
                    if not re.match(r"\w[\w\s]*:", nxt):
                        # Línea limpia de continuación
                        val = val + " " + nxt
                    else:
                        # Línea tipo "ETIQUETA: valor_col_izq  CONTINUACION_ADDR" (2 columnas mergeadas)
                        # Extraer la parte derecha que sigue al primer par etiqueta:valor
                        right = re.match(r"^\w[\w\s]*:\s*\S+\s+(.+)", nxt)
                        if right and len(right.group(1).strip()) >= 4:
                            val = val + " " + right.group(1).strip()
            out["lugar_entrega"] = _limpiar_lugar(val)[:200]

    if not out["fecha_entrega"]:
        m = _GEN_FECHA_ENTREGA_RE.search(texto)
        if m:
            out["fecha_entrega"] = m.group(1).strip()

    if not out["cliente"]:
        # Patrón explícito "FACTURA A NOMBRE DE:" (CLASEM y similares)
        m = re.search(r"FACTURA\s+A\s+NOMBRE\s+DE\s*[:\-]\s*(.+)", texto, re.IGNORECASE)
        if m:
            out["cliente"] = _limpiar_valor_pdf(m.group(1))[:100]
    if not out["cliente"]:
        out["cliente"] = _extraer_empresa_emisora(texto)

    # Nombre de obra: código-proyecto "PC-25099 - UTP HUAMANGA"
    if not out["nombre_obra"]:
        for t in textos_pag:
            m = _PDF_CODE_RE.search(t)
            if m:
                desc = _limpiar_valor_pdf(m.group(2))
                if len(desc) >= 3:
                    out["nombre_obra"] = f"{m.group(1).strip()} - {desc}"[:150]
                    break

    # Nombre de obra: etiquetas genéricas como último recurso
    if not out["nombre_obra"]:
        m = _PDF_LABEL_RE.search(texto)
        if m:
            val = _limpiar_valor_pdf(m.group(1))
            if len(val) >= 4 and val.upper() not in _LABEL_BLACKLIST:
                out["nombre_obra"] = val[:150]

    # Tablas genéricas (etiqueta+valor en misma celda o en celdas adyacentes)
    for table in tables:
        for row in (table or []):
            if not row:
                continue
            for i, cell in enumerate(row):
                if not cell:
                    continue
                cell_clean = re.sub(r"\s+", " ", cell.strip())
                cell_up = cell_clean.upper()

                for field, rx in _CAMPOS_PDF_RE:
                    if out[field]:
                        continue
                    m2 = rx.search(cell_clean)
                    if m2:
                        limpiar = _limpiar_lugar if field == "lugar_entrega" else _limpiar_valor_pdf
                        val = limpiar(m2.group(1))
                        if field == "nombre_obra" and val.upper() in _LABEL_BLACKLIST:
                            continue
                        if len(val) >= (4 if field == "nombre_obra" else 2):
                            out[field] = val[:200]

                for kws, field in _CAMPOS_PDF_KWS:
                    if out[field]:
                        continue
                    if any(kw in cell_up for kw in kws):
                        for j in range(i + 1, min(i + 3, len(row))):
                            clean_cell = row[j] or ""
                            val = (_limpiar_lugar if field == "lugar_entrega" else _limpiar_valor_pdf)(clean_cell)
                            if field == "nombre_obra" and val.upper() in _LABEL_BLACKLIST:
                                continue
                            if len(val) >= 2:
                                out[field] = val[:200]
                                break


_UNIDADES_CONOCIDAS = {
    "UND", "UN", "UNI", "UNID", "PZA", "PZ", "PZS",
    "ML", "MLL", "LT", "LTS", "GLN", "GAL",
    "KG", "KGS", "GR", "GRS", "TN",
    "M", "M2", "M3", "ML", "KM",
    "JGO", "JGS", "SET", "KIT",
    "GLB", "GBL",
    "HH", "HM", "HR", "HRS",
    "ROLLO", "ROLLOS", "BOL", "BOLS", "CJA", "CAJA", "CAJAS",
    "PAR", "PARES", "DOC", "DZ",
}

_ITEM_HEADER_KWS = {"DESCRIPCI", "UNIDAD", "CANTIDAD", "CANT.", "CANT", "ITEM", "PARTIDA", "GLOSA", "DESCRIPCIÓN"}
_SKIP_ROW_KWS   = {"TOTAL", "SUBTOTAL", "IGV", "IMPUESTO", "SON:", "PRECIO UNITARIO", "VALOR UNIT"}


def _es_numero(s: str) -> bool:
    """True si s parece un número (entero o decimal, con coma o punto)."""
    if not s:
        return False
    cleaned = s.strip().replace(",", ".").replace(" ", "")
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _parsear_numero(s: str) -> float:
    try:
        return float(s.strip().replace(",", ".").replace(" ", ""))
    except ValueError:
        return 0.0


def _parece_codigo_articulo(token: str) -> bool:
    """
    True si el token parece un código de artículo (no una palabra descriptiva española).
    Criterios: solo mayúsculas/dígitos, ≥5 chars, con ratio de vocales ≤35% (códigos tienen
    pocas vocales; palabras como BANDEJA/CAJA tienen ≥40%).
    """
    if not token:
        return False
    if re.match(r'^\d{5,}$', token):   # puramente numérico largo
        return True
    if not re.match(r'^[A-Z0-9]{5,20}$', token):
        return False
    letras = [c for c in token if c.isalpha()]
    if not letras:
        return True
    vocales = sum(1 for c in letras if c in "AEIOU")
    return (vocales / len(letras)) <= 0.35


def _extraer_items_oc(tables: list) -> list:
    """
    Detecta la tabla de ítems de la OC y devuelve lista de dicts:
    {descripcion, unidad, cantidad_pedida}
    Solo procesa tablas cuya fila de encabezado contiene ≥2 keywords de ítems.
    """
    items: list = []

    for table in tables:
        if not table or len(table) < 2:
            continue

        # Buscar fila de encabezado
        header_row_idx = None
        col_desc = col_unit = col_cant = col_precio = col_total = col_item = None

        for ri, row in enumerate(table[:4]):
            if not row:
                continue
            cells_up = [re.sub(r"\s+", " ", str(c or "")).strip().upper() for c in row]
            hits = sum(1 for c in cells_up if any(kw in c for kw in _ITEM_HEADER_KWS))
            if hits < 2:
                continue

            for ci, cu in enumerate(cells_up):
                if col_item is None and cu in ("ITEM", "ÍTEM", "ITEM.", "N°", "NRO", "ORD", "ORD.", "SEQ"):
                    col_item = ci
                if col_desc is None and any(kw in cu for kw in ("DESCRIPCI", "GLOSA", "PARTIDA", "CONCEPTO", "MATERIAL", "PRODUCTO", "BIEN")):
                    col_desc = ci
                if col_unit is None and ("UNIDAD" in cu or "UNID" in cu or cu in ("UN", "UND", "UM", "U.M.")):
                    col_unit = ci
                if col_cant is None and any(kw in cu for kw in ("CANTIDAD", "CANT", "QTY", "CTIDAD", "PEDIDO", "PED.")):
                    col_cant = ci
                if col_precio is None and any(kw in cu for kw in ("PRECIO", "P.U.", "V.UNIT", "VALOR UNIT", "PRECIO UNIT", "P. UNIT")):
                    col_precio = ci
                if col_total is None and any(kw in cu for kw in ("IMPORTE", "MONTO", "TOTAL")):
                    col_total = ci

            if col_desc is not None:
                header_row_idx = ri
                break

        if header_row_idx is None or col_desc is None:
            continue

        # Columnas a saltar en el fallback de cantidad
        _skip_cant = set(filter(lambda x: x is not None, [col_desc, col_unit, col_precio, col_total, col_item]))

        # Extraer filas de datos
        for row in table[header_row_idx + 1:]:
            try:
                if not row or not isinstance(row, (list, tuple)) or len(row) <= col_desc:
                    continue
                desc = re.sub(r"\s+", " ", str(row[col_desc] or "")).strip()

                # Eliminar código de artículo al inicio (numérico o alfanumérico tipo CJOUFYCWAX)
                tokens = desc.split(None, 1)
                if len(tokens) == 2 and _parece_codigo_articulo(tokens[0]):
                    desc = tokens[1]

                if len(desc) < 4:
                    continue
                if re.match(r"^\d{1,6}$", desc):
                    continue
                desc_up = desc.upper()
                if any(kw in desc_up for kw in _SKIP_ROW_KWS):
                    continue
            except Exception:
                continue

            # Unidad
            unit = ""
            if col_unit is not None and col_unit < len(row):
                unit = re.sub(r"\s+", " ", str(row[col_unit] or "")).strip().upper()[:10]
            if not unit or unit not in _UNIDADES_CONOCIDAS:
                for ci2, cell in enumerate(row):
                    if ci2 == col_desc:
                        continue
                    val = re.sub(r"\s+", " ", str(cell or "")).strip().upper()
                    if val in _UNIDADES_CONOCIDAS:
                        unit = val
                        break

            # Cantidad — intentar col_cant primero (incluyendo extracción de celda fusionada)
            cant = 0.0
            if col_cant is not None and col_cant < len(row):
                cant_raw = re.sub(r"\s+", " ", str(row[col_cant] or "")).strip()
                cant = _parsear_numero(cant_raw)
                if cant == 0.0:
                    m_num = re.search(r'\d+(?:[,\.]\d+)?', cant_raw)
                    if m_num:
                        cant = _parsear_numero(m_num.group())

            # Fallback: primera celda numérica que no sea item/precio/total
            # Si col_cant fue detectado, solo buscar a su izquierda (antes del precio)
            if cant == 0.0:
                right_limit = col_cant if col_cant is not None else len(row)
                for ci2 in range(right_limit):
                    if ci2 in _skip_cant:
                        continue
                    val = str(row[ci2] if ci2 < len(row) else "").strip()
                    if _es_numero(val):
                        n = _parsear_numero(val)
                        if 0 < n <= 100000:
                            cant = n
                            break

            if cant > 0:
                items.append({
                    "descripcion": desc[:200],
                    "unidad": unit or "UND",
                    "cantidad_pedida": cant,
                })

        if items:
            break

    return items


# ── Extracción de ítems desde texto plano (S10, PROYESEL, CLASEM) ──────────

_ITEM_HDR_TEXT_RE = re.compile(
    r"(?:"
    r"\bDESCRIPCI[OÓ]N\b.{0,120}\b(?:CANT(?:IDAD)?\.?|UND\.?|UNIDAD)\b"
    r"|"
    r"\bRECURSO\b.{0,80}\b(?:CANT(?:IDAD)?\.?|UND\.?)\b"  # S10: "Recurso Und Cantidad"
    r")",
    re.IGNORECASE,
)

_ITEM_STOP_TEXT_RE = re.compile(
    r"^\s*(?:SUB[\s\-]?TOTAL|I\.G\.V\.|IGV|TOTAL\b|DESCUENTO|OBSERVACI)",
    re.IGNORECASE,
)

# (?<!\w) y (?!\w) en lugar de \b para soportar unidades con punto final (UND., UN.)
_ITEM_TEXT_RE = re.compile(
    r"^(?:\d{1,3}\s+)?(?:[A-Z0-9]{5,15}\s+)?"      # [seq] [código artículo numérico o alfanumérico]
    r"(.{5,}?)\s+"                                   # descripción (non-greedy)
    r"(?<!\w)(UND\.?|UN\.?|ML|M2|M3|KG|GLB|GBL|PZA|JGO?|PT|TN|CJ|BLS?|LT|GAL"
    r"|HRS?|DIA(?:S)?|EST|SER|SVC|PIE|PZS?|BOL|ROLLO|CAJA|CAJAS|SET|KIT)(?!\w)\s*"
    r"([\d,\.]+)\s+"                                 # cantidad
    r"(?:S/\.\s*)?([\d,\.]+)",                       # precio unitario (S/. opcional)
    re.IGNORECASE,
)


def _extraer_items_oc_texto(textos: list) -> list:
    """
    Extrae ítems OC desde texto plano cuando pdfplumber no detecta tabla estructurada.
    Soporta formatos PROYESEL, CLASEM/ESPARQ y S10.
    """
    items: list = []
    in_items = False
    done = False

    for texto in textos:
        if done:
            break
        for linea in texto.splitlines():
            linea = linea.strip()
            if not linea:
                continue

            if not in_items:
                if _ITEM_HDR_TEXT_RE.search(linea):
                    in_items = True
                continue

            if _ITEM_STOP_TEXT_RE.match(linea):
                done = True
                break

            m = _ITEM_TEXT_RE.match(linea)
            if not m:
                continue

            desc = re.sub(r"\s+", " ", m.group(1)).strip(" .:,\"'")
            if not desc or len(desc) < 4:
                continue
            if re.match(r"^\d{1,6}$", desc):
                continue

            try:
                cant = float(m.group(3).replace(",", ""))
                precio = float(m.group(4).replace(",", ""))
            except ValueError:
                continue

            if cant <= 0:
                continue

            items.append({
                "descripcion": desc[:200],
                "unidad": m.group(2).upper().rstrip("."),
                "cantidad_pedida": cant,
                "cantidad_despachada": 0.0,
            })

    return items


def _extraer_campos_pdf(pdf_bytes: bytes) -> dict:
    """
    Extrae del PDF: nombre_obra, lugar_entrega, fecha_entrega, fecha_oc, numero_oc, cliente.
    Soporta S10 (Número/Facturar a/Proyecto) y formatos no-S10 (Nº/Glosa/Dirección Entrega).
    Las fechas se normalizan a dd/mm/yyyy.
    """
    out = {
        "nombre_obra": "", "lugar_entrega": "", "fecha_entrega": "",
        "fecha_oc": "", "numero_oc": "", "cliente": "",
        "es_ingreso": False, "items_oc": [],
    }
    if not pdf_bytes:
        return out
    try:
        import pdfplumber
    except ImportError:
        return out

    textos: list[str] = []
    tables: list = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:4]:
                try:
                    t = page.extract_text() or ""
                    if t:
                        textos.append(t)
                except Exception:
                    pass
                try:
                    tbls = page.extract_tables() or []
                    tables.extend(tbls)
                except Exception:
                    pass
    except Exception:
        return out

    if not textos:
        return out

    # Detectar ingreso/recepción de OC en las primeras 20 líneas del PDF
    primeras = "\n".join(textos[0].splitlines()[:20])
    if _texto_es_ingreso_oc(primeras):
        out["es_ingreso"] = True
        return out

    texto = "\n".join(textos)
    # Detecta S10 por "Número" (capital N + tilde, seguido de código OC) — sin IGNORECASE
    # para no confundir con "número de Orden de Compra" en texto de condiciones
    is_s10 = bool(re.search(r"\bNúmero\s+v?[A-Z0-9]", texto))

    if is_s10:
        _parsear_s10(texto, tables, out)

    _parsear_generico(texto, tables, textos, out)

    for campo in ("fecha_oc", "fecha_entrega"):
        if out[campo]:
            out[campo] = _normalizar_fecha(out[campo])

    for campo in out:
        if isinstance(out[campo], str) and out[campo]:
            out[campo] = out[campo][:200]

    try:
        out["items_oc"] = _extraer_items_oc(tables)
    except Exception:
        out["items_oc"] = []

    # Si la extracción por tabla no encontró nada, intentar desde texto plano
    if not out["items_oc"]:
        try:
            out["items_oc"] = _extraer_items_oc_texto(textos)
        except Exception:
            pass

    return out


def _buscar_emails_con_pdf(cfg: dict) -> list:
    dominios_clientes = get_dominios_clientes()
    propia_cuenta = cfg.get("username", "").lower().strip()

    imap = _conectar_imap(cfg)
    imap.select(cfg.get("folder", "INBOX"), readonly=True)

    if cfg.get("since_override"):
        try:
            since_date = datetime.strptime(cfg["since_override"], "%Y-%m-%d").strftime("%d-%b-%Y")
        except ValueError:
            since_date = (datetime.now() - timedelta(days=int(cfg.get("days_back", 15)))).strftime("%d-%b-%Y")
    else:
        since_date = (datetime.now() - timedelta(days=int(cfg.get("days_back", 15)))).strftime("%d-%b-%Y")

    search_criteria = f"SINCE {since_date}"
    if cfg.get("until_override"):
        try:
            until_date = (datetime.strptime(cfg["until_override"], "%Y-%m-%d") + timedelta(days=1)).strftime("%d-%b-%Y")
            search_criteria += f" BEFORE {until_date}"
        except ValueError:
            pass

    status, uids_raw = imap.search(None, search_criteria)
    if status != "OK":
        imap.logout()
        return []

    uids = uids_raw[0].split()
    if not uids:
        imap.logout()
        return []

    # Paso 1: leer encabezados de los últimos 300 emails y pre-filtrar
    candidatos = []
    for uid in reversed(uids[-300:]):
        try:
            status, hdr_data = imap.fetch(uid, _HDR_FIELDS)
            if status != "OK" or not hdr_data or not hdr_data[0]:
                continue
            hdr_raw = hdr_data[0][1]
            if not isinstance(hdr_raw, bytes):
                continue
            # Debe ser multipart (probable adjunto)
            if b"multipart" not in hdr_raw.lower():
                continue

            hdr_msg = _email_mod.message_from_bytes(hdr_raw)
            subject  = _decode_header(hdr_msg.get("Subject", ""))
            from_hdr = hdr_msg.get("From", "")
            domain   = _sender_domain(from_hdr)

            # Ignorar correos enviados desde la propia cuenta IMAP
            _, from_addr = email.utils.parseaddr(from_hdr)
            if propia_cuenta and from_addr.lower().strip() == propia_cuenta:
                continue

            # Excluir ingresos/recepciones de OC por asunto
            if _texto_es_ingreso_oc(subject):
                continue

            # Excluir falsos positivos (consultas, solicitudes de docs, seguimientos, etc.)
            if _texto_es_falso_positivo(subject):
                continue

            subject_ok = _texto_es_oc(subject)
            domain_ok  = bool(domain and domain in dominios_clientes)

            # Solo procesar si el asunto parece OC o el dominio es de un cliente conocido
            if not subject_ok and not domain_ok:
                continue

            candidatos.append((uid, hdr_raw, subject_ok, domain_ok))
        except Exception:
            continue

    resultados = []
    _deadline = time.time() + 110  # 110 s — toleramos espera de mes completo
    # Paso 2: descargar emails candidatos y buscar PDFs
    for uid, hdr_raw, subject_ok, domain_ok in candidatos:
        if time.time() > _deadline:
            break
        try:
            hdr_msg    = _email_mod.message_from_bytes(hdr_raw)
            message_id = hdr_msg.get("Message-ID", "").strip() or f"uid-{uid.decode()}"
            if email_ya_importado(message_id):
                continue

            status, data = imap.fetch(uid, "(RFC822)")
            if status != "OK" or not data or not data[0]:
                continue
            raw = data[0][1]
            if not isinstance(raw, bytes):
                continue
            msg = _email_mod.message_from_bytes(raw)

            # Si el asunto no era definitivo, verificar cuerpo del email
            if not subject_ok and not _texto_es_oc(_body_text(msg)):
                continue

            pdfs = _collect_pdfs(msg)
            if not pdfs:
                continue

            # Excluir si algún PDF se llama como ingreso/recepción de OC
            if any(_texto_es_ingreso_oc(p["filename"]) for p in pdfs):
                continue

            subject  = _decode_header(msg.get("Subject", ""))
            from_name, from_email_addr = email.utils.parseaddr(msg.get("From", ""))
            from_name  = _decode_header(from_name) or from_email_addr.split("@")[0]
            domain     = _sender_domain(msg.get("From", ""))
            numero_oc  = _extraer_oc(subject)
            nombre_obra = _limpiar_asunto(subject, numero_oc)

            # Obtener bytes del PDF preferido (primero tras ordenar por OC).
            # pdfs[0]["index"] es el walk-order index real, no la posición en el array.
            pdf_bytes_0 = _get_pdf_bytes_from_msg(msg, pdfs[0]["index"])

            # Descartar si el mismo contenido PDF ya fue importado en un proyecto
            # vigente (cubre reenvíos y respuestas con el mismo adjunto).
            if pdf_bytes_0 and pdf_hash_ya_importado(_pdf_hash(pdf_bytes_0)):
                continue

            # PDF tiene prioridad sobre el asunto para todos los campos
            datos_pdf = _extraer_campos_pdf(pdf_bytes_0) if pdf_bytes_0 else {}
            # Excluir si el PDF es un ingreso/recepción de OC (detectado en su contenido)
            if datos_pdf.get("es_ingreso"):
                continue
            if datos_pdf.get("nombre_obra"):
                nombre_obra = datos_pdf["nombre_obra"]
            if datos_pdf.get("numero_oc"):
                numero_oc = datos_pdf["numero_oc"]

            # Derivar cliente: PDF > cliente registrado por dominio > dominio del email
            cliente_sugerido = (
                datos_pdf.get("cliente")
                or get_cliente_nombre_por_dominio(domain)
                or _dominio_a_empresa(domain)
                or from_name
            )

            items_oc = datos_pdf.get("items_oc", [])
            resultados.append({
                "message_id":      message_id,
                "subject":         subject,
                "from_name":       from_name,
                "from_email":      from_email_addr,
                "date":            msg.get("Date", ""),
                "numero_oc":       numero_oc,
                "nombre_obra":     nombre_obra[:120],
                "pdfs":            pdfs,
                "cliente_conocido": domain_ok,
                "cliente_sugerido": cliente_sugerido,
                "lugar_entrega":   datos_pdf.get("lugar_entrega", ""),
                "fecha_entrega":   datos_pdf.get("fecha_entrega", ""),
                "fecha_oc":        datos_pdf.get("fecha_oc", ""),
                "n_items_oc":      len(items_oc),
            })
        except Exception:
            continue

    imap.logout()
    return resultados


def _descargar_pdf_adjunto(cfg: dict, message_id: str, pdf_index: int) -> Optional[tuple]:
    """
    Descarga el PDF en la posición pdf_index dentro de la lista de PDFs del email.
    pdf_index es el índice dentro de los PDFs encontrados (0, 1, 2…), no el walk index.
    """
    imap = _conectar_imap(cfg)
    imap.select(cfg.get("folder", "INBOX"), readonly=True)

    if message_id.startswith("uid-"):
        uids = [message_id[4:].encode()]
    else:
        escaped = message_id.replace("\\", "\\\\").replace('"', '\\"')
        status, uids_raw = imap.search(None, f'HEADER Message-ID "{escaped}"')
        if status != "OK" or not uids_raw[0]:
            # Fallback: buscar sin angle brackets si el Message-ID los incluye
            clean_id = message_id.strip("<>")
            if clean_id != message_id:
                escaped2 = clean_id.replace("\\", "\\\\").replace('"', '\\"')
                status, uids_raw = imap.search(None, f'HEADER Message-ID "{escaped2}"')
            if status != "OK" or not uids_raw[0]:
                imap.logout()
                return None
        uids = uids_raw[0].split()

    if not uids:
        imap.logout()
        return None

    status, data = imap.fetch(uids[-1], "(RFC822)")
    imap.logout()

    if status != "OK" or not data or not data[0]:
        return None
    raw = data[0][1]
    if not isinstance(raw, bytes):
        return None

    msg = _email_mod.message_from_bytes(raw)

    # Recolectar PDFs en el mismo orden que _collect_pdfs y devolver el solicitado
    pdf_count = 0
    for part in msg.walk():
        ct = part.get_content_type() or ""
        fn = _decode_header(part.get_filename() or "")
        if not ((ct == "application/pdf" or fn.lower().endswith(".pdf")) and fn):
            continue
        if pdf_count == pdf_index:
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                return (payload, fn)
        pdf_count += 1

    return None


_CIUDADES_PE = ("LIMA", "CALLAO", "AREQUIPA", "TRUJILLO", "CHICLAYO", "PIURA", "CUSCO", "IQUITOS")

# Formato S10: "LIMA-LIMA-LOS OLIVOS" o "LIMA - LIMA - LOS OLIVOS" al final de la dirección
_S10_DISTRITO_RE = re.compile(
    r'\b(?:LIMA|CALLAO)\s*-\s*[\w\s]+?\s*-\s*([\w][\w\s]+?)\s*$',
    re.IGNORECASE,
)

# Latitudes aproximadas de distritos de Lima Metropolitana (norte → sur, mayor → menor)
_DISTRITO_LAT: dict[str, float] = {
    "ANCÓN": -11.775, "ANCON": -11.775,
    "SANTA ROSA": -11.805,
    "CARABAYLLO": -11.892,
    "PUENTE PIEDRA": -11.865,
    "COMAS": -11.943,
    "LURIGANCHO": -11.925, "LURIGANCHO-CHOSICA": -11.925,
    "SAN JUAN DE LURIGANCHO": -11.997,
    "LOS OLIVOS": -11.990,
    "INDEPENDENCIA": -11.990,
    "SAN MARTIN DE PORRES": -11.984, "SAN MARTÍN DE PORRES": -11.984,
    "CHACLACAYO": -11.982,
    "RIMAC": -12.024,
    "EL AGUSTINO": -12.045,
    "SANTA ANITA": -12.044,
    "CERCADO DE LIMA": -12.046, "LIMA CERCADO": -12.046,
    "BREÑA": -12.059,
    "CALLAO": -12.057,
    "BELLAVISTA": -12.062,
    "LA PERLA": -12.072,
    "LA VICTORIA": -12.065,
    "JESUS MARIA": -12.074, "JESÚS MARÍA": -12.074,
    "PUEBLO LIBRE": -12.078,
    "LA PUNTA": -12.076,
    "SAN MIGUEL": -12.077,
    "LINCE": -12.084,
    "MAGDALENA DEL MAR": -12.089, "MAGDALENA": -12.089,
    "SAN ISIDRO": -12.097,
    "ATE": -12.027, "ATE VITARTE": -12.027,
    "LA MOLINA": -12.076,
    "CIENEGUILLA": -12.066,
    "SAN BORJA": -12.103,
    "SURQUILLO": -12.112,
    "MIRAFLORES": -12.121,
    "BARRANCO": -12.143,
    "SANTIAGO DE SURCO": -12.144, "SURCO": -12.144,
    "SAN JUAN DE MIRAFLORES": -12.157,
    "VILLA MARIA DEL TRIUNFO": -12.164, "VILLA MARÍA DEL TRIUNFO": -12.164,
    "VILLA EL SALVADOR": -12.210,
    "CHORRILLOS": -12.174,
    "PACHACAMAC": -12.240,
    "LURÍN": -12.273, "LURIN": -12.273,
    "PUNTA HERMOSA": -12.333,
    "PUNTA NEGRA": -12.374,
    "SAN BARTOLO": -12.394,
    "SANTA MARIA DEL MAR": -12.413,
    "PUCUSANA": -12.483,
}

_DISTRITO_LAT_SORTED = sorted(_DISTRITO_LAT, key=len, reverse=True)


def _lat_por_distrito(q_up: str) -> Optional[float]:
    """Devuelve latitud desde el diccionario de distritos si la dirección contiene uno conocido."""
    # 1) Extraer distrito del sufijo S10 (LIMA-PROVINCIA-DISTRITO)
    m = _S10_DISTRITO_RE.search(q_up)
    if m:
        nombre = m.group(1).strip().upper()
        # Eliminar posibles palabras extra al final (ej. "LOS OLIVOS 2" → "LOS OLIVOS")
        for key in _DISTRITO_LAT_SORTED:
            if nombre.startswith(key):
                return _DISTRITO_LAT[key]

    # 2) Buscar cualquier distrito conocido mencionado en la dirección
    for key in _DISTRITO_LAT_SORTED:
        if re.search(r'\b' + re.escape(key) + r'\b', q_up):
            return _DISTRITO_LAT[key]

    return None


def _nominatim_get(query: str) -> Optional[float]:
    """Llama a Nominatim y devuelve latitud o None. Bloqueante — solo para distritos desconocidos."""
    import json as _json
    import time as _time
    import urllib.parse as _up
    import urllib.request as _ur

    _time.sleep(1.2)  # respetar rate limit de Nominatim (1 req/s)
    url = "https://nominatim.openstreetmap.org/search?" + _up.urlencode({
        "q": query, "format": "json", "limit": 1, "countrycodes": "pe",
    })
    req = _ur.Request(url, headers={
        "User-Agent": "AROLUZ-Cotizador/1.0 (sistemas@aroluz.pe)",
        "Accept-Language": "es",
    })
    with _ur.urlopen(req, timeout=8) as resp:
        data = _json.loads(resp.read())
    if data:
        return float(data[0]["lat"])
    return None


@router.get("/geocode")
def geocode_address(q: str = Query(...), usuario: dict = Depends(require_login)):
    """
    Geocodifica una dirección para ordenar la ruta N→S.
    Estrategia 1: lookup instantáneo de distritos Lima (dict hardcodeado).
    Estrategia 2: Nominatim como fallback (1.2 s de delay para respetar rate limit).
    """
    if not q.strip():
        return JSONResponse({"ok": False, "lat": None})

    q_up = q.upper().strip()

    # Estrategia 1: diccionario de distritos Lima (instantáneo)
    lat = _lat_por_distrito(q_up)
    if lat is not None:
        return JSONResponse({"ok": True, "lat": lat})

    # Estrategia 2: Nominatim (fallback para direcciones fuera del dict)
    city_present = any(c in q_up for c in _CIUDADES_PE)
    query = q if city_present else q + ", Lima, Peru"
    try:
        lat = _nominatim_get(query)
        if lat is not None:
            return JSONResponse({"ok": True, "lat": lat})
    except Exception:
        pass

    return JSONResponse({"ok": False, "lat": None})


# ── Modelos ───────────────────────────────────────────────────────────────────

class ImapConfigBody(BaseModel):
    host: str
    port: int = 993
    username: str
    password: str
    folder: str = "INBOX"
    days_back: int = 30


class ImportarEmailBody(BaseModel):
    message_id: str
    pdf_index: int = 0
    nombre_obra: str
    cliente: str
    numero_oc: str = ""
    lugar_entrega: str = ""
    fecha_entrega: str = ""
    fecha_oc: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/pdf-preview")
async def email_pdf_preview(
    message_id: str = Query(...),
    pdf_index: int = Query(default=0),
    usuario: dict = Depends(require_login),
):
    """Descarga y retorna el PDF del email para previsualizarlo antes de importar."""
    cfg = get_email_imap_config()
    if not cfg:
        return JSONResponse({"ok": False, "error": "Correo IMAP no configurado."}, status_code=400)
    try:
        result = await run_in_threadpool(_descargar_pdf_adjunto, cfg, message_id, pdf_index)
        if result is None:
            return JSONResponse({"ok": False, "error": "No se pudo obtener el PDF."}, status_code=404)
        pdf_bytes, pdf_filename = result
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{pdf_filename}"'},
        )
    except imaplib.IMAP4.error as exc:
        return JSONResponse({"ok": False, "error": f"Error IMAP: {exc}"}, status_code=400)
    except OSError as exc:
        return JSONResponse({"ok": False, "error": f"No se pudo conectar: {exc}"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"Error inesperado: {exc}"}, status_code=500)


@router.get("/config")
async def email_get_config(usuario: dict = Depends(require_admin)):
    cfg = get_email_imap_config()
    if not cfg:
        return JSONResponse({"ok": True, "configurado": False})
    masked = dict(cfg)
    pwd_len = len(cfg.get("password", ""))
    masked["password"] = "•" * 8 if pwd_len else ""
    return JSONResponse({"ok": True, "configurado": True, "config": masked})


@router.post("/config")
@limiter.limit("10/minute")
async def email_save_config(request: Request, body: ImapConfigBody, usuario: dict = Depends(require_admin)):
    if not body.host.strip() or not body.username.strip():
        return JSONResponse({"ok": False, "error": "Host y usuario son obligatorios."}, status_code=422)
    password = body.password
    if not password:
        existing = get_email_imap_config()
        password = existing["password"] if existing else ""
    if not password:
        return JSONResponse({"ok": False, "error": "Ingresá la contraseña la primera vez que configurás."}, status_code=422)
    save_email_imap_config(
        body.host.strip(), body.port,
        body.username.strip(), password,
        body.folder.strip() or "INBOX", body.days_back,
    )
    return JSONResponse({"ok": True})


@router.post("/sync")
async def email_sync(
    since: str = Query(default=""),
    until: str = Query(default=""),
    usuario: dict = Depends(require_login),
):
    cfg = get_email_imap_config()
    if not cfg:
        return JSONResponse(
            {"ok": False, "error": "Correo IMAP no configurado. Configuralo en Ajustes → Correo."},
            status_code=400,
        )
    if since:
        cfg["since_override"] = since
    if until:
        cfg["until_override"] = until
    try:
        emails = await run_in_threadpool(_buscar_emails_con_pdf, cfg)
        return JSONResponse({"ok": True, "emails": emails})
    except imaplib.IMAP4.error as exc:
        return JSONResponse({"ok": False, "error": f"Error IMAP: {exc}"}, status_code=400)
    except OSError as exc:
        return JSONResponse({"ok": False, "error": f"No se pudo conectar al servidor: {exc}"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"Error inesperado: {exc}"}, status_code=500)


@router.post("/importar")
async def email_importar(body: ImportarEmailBody, usuario: dict = Depends(require_login)):
    cfg = get_email_imap_config()
    if not cfg:
        return JSONResponse({"ok": False, "error": "Correo IMAP no configurado."}, status_code=400)

    nombre   = body.nombre_obra.strip()
    cliente  = body.cliente.strip()
    numero_oc = body.numero_oc.strip()

    if not nombre:
        return JSONResponse({"ok": False, "error": "El nombre de la obra no puede estar vacío."}, status_code=422)

    if proyecto_existe(nombre):
        return JSONResponse({"ok": True, "omitido": True, "proyecto": nombre})

    try:
        result = await run_in_threadpool(_descargar_pdf_adjunto, cfg, body.message_id, body.pdf_index)
        if result is None:
            return JSONResponse({"ok": False, "error": "No se pudo descargar el PDF del correo."}, status_code=400)

        pdf_bytes, pdf_filename = result
        hash_pdf = _pdf_hash(pdf_bytes)

        proyecto_creado = crear_proyecto(
            nombre, cliente,
            lugar_entrega=body.lugar_entrega.strip(),
            fecha_entrega=body.fecha_entrega.strip(),
            fecha_oc=body.fecha_oc.strip(),
        )
        if numero_oc:
            update_proyecto_numero_oc(nombre, numero_oc)

        slug = "".join(c if c.isalnum() or c in "-_. " else "_" for c in nombre)[:60]
        dest_dir = ADJUNTOS_DIR / slug
        dest_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_fn = unicodedata.normalize("NFKD", pdf_filename).encode("ascii", "ignore").decode("ascii")
        safe_fn = "".join(c if c.isalnum() or c in "-_. " else "_" for c in safe_fn).strip() or "oc.pdf"
        dest = dest_dir / f"{ts}_{safe_fn}"
        dest.write_bytes(pdf_bytes)
        add_adjunto(nombre, pdf_filename, str(dest), "application/pdf", "oc")

        # Extraer ítems OC del PDF y guardarlos (solo si el proyecto es nuevo)
        n_items = 0
        if proyecto_creado:
            try:
                datos_pdf = _extraer_campos_pdf(pdf_bytes)
                for orden, item in enumerate(datos_pdf.get("items_oc", []), start=1):
                    add_oc_item(
                        nombre,
                        item["descripcion"],
                        item.get("unidad", "UND"),
                        item.get("cantidad_pedida", 0),
                        0,  # cantidad_despachada
                        orden,
                    )
                    n_items += 1
            except Exception:
                pass  # los ítems son opcionales; no fallar si el parser falla

        registrar_email_importado(body.message_id, nombre, pdf_hash=hash_pdf)
        return JSONResponse({
            "ok": True,
            "proyecto": nombre,
            "ya_existia": not proyecto_creado,
            "n_items_importados": n_items,
        })

    except imaplib.IMAP4.error as exc:
        return JSONResponse({"ok": False, "error": f"Error IMAP: {exc}"}, status_code=400)
    except OSError as exc:
        return JSONResponse({"ok": False, "error": f"No se pudo conectar al servidor: {exc}"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"Error inesperado: {exc}"}, status_code=500)
