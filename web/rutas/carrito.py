"""
carrito.py — Endpoints del carrito de compras por sesión

El carrito se almacena en SQLite (tabla carrito_items), persistente entre reinicios.
"""
import json
import re
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from web.auth import require_login
from web.database import (
    get_carrito_db,
    add_item_carrito_db,
    update_cantidad_carrito_db,
    update_item_precio_carrito_db,
    update_item_campos_carrito_db,
    delete_item_carrito_db,
    clear_carrito_db,
    cargar_config,
)
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
    descripcion_calculada: Optional[str] = Form(None),
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
        "descripcion_calculada": descripcion_calculada,
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


def _espesores_validos_desde_config(config: dict) -> set:
    """Extrae el conjunto de espesores válidos de la configuración (GO y GC)."""
    valores = config.get("valores_defecto", {})
    esps = set()
    for key in ("precios_go", "precios_gc"):
        esps.update(valores.get(key, {}).keys())
    return esps or {"1.2", "1.5", "2.0"}  # fallback si config está vacía


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
    config = cargar_config()
    espesores_validos = _espesores_validos_desde_config(config)
    if nuevo_esp_str not in espesores_validos:
        return JSONResponse({"ok": False, "error": "Espesor inválido"}, status_code=400)
    if parte not in ("cuerpo", "tapa"):
        return JSONResponse({"ok": False, "error": "Parte inválida"}, status_code=400)

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
        desc_calc = item.get("descripcion_calculada") or None
        # Para detectar tapa y extraer espesor: preferir descripcion_calculada si existe
        desc_ref = desc_calc if desc_calc else desc
        es_tapa = "TAPA" in desc_ref.upper()

        # Solo procesar la parte solicitada
        if parte == "tapa" and not es_tapa:
            continue
        if parte == "cuerpo" and es_tapa:
            continue

        # Extraer espesor actual desde la referencia (calculada si existe, si no la original)
        esp_actual = _extraer_espesor(desc_ref)
        if esp_actual is None:
            # Último fallback: intentar desde la descripción original
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

        if desc_calc:
            # Tiene descripcion_calculada: actualizarla y dejar descripcion intacta
            nueva_desc_calc = _reemplazar_espesor(desc_calc, nuevo_espesor)
            update_item_precio_carrito_db(
                item["id"], usuario["u"],
                nuevo_precio, nuevo_peso, desc,
                descripcion_calculada=nueva_desc_calc,
            )
        else:
            # Sin descripcion_calculada: comportamiento original (actualiza descripcion)
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


@router.post("/editar/{item_id}")
async def api_editar_item(
    item_id: int,
    usuario: dict = Depends(require_login),
    descripcion: str = Form(...),
    unidad: str = Form("UND"),
    precio_unitario: float = Form(...),
    descripcion_calculada: Optional[str] = Form(None),
):
    """Edita descripción, unidad, precio y opcionalmente ítem programa de un item."""
    updated = update_item_campos_carrito_db(
        item_id, usuario["u"],
        descripcion.strip(), unidad.strip(),
        precio_unitario,
        descripcion_calculada.strip() if descripcion_calculada else None,
    )
    if updated:
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)


@router.post("/und_a_ml/{item_id}")
async def api_und_a_ml(
    item_id: int,
    usuario: dict = Depends(require_login),
):
    """Convierte un item de bandeja de UND a ML (divide precio y peso por 2.4)."""
    carrito = get_carrito(usuario["u"])
    item = next((i for i in carrito if i["id"] == item_id), None)
    if not item:
        return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)
    if item["tipo"] != "B":
        return JSONResponse({"ok": False, "error": "Solo bandejas pueden convertirse a ML"}, status_code=400)
    if item["unidad"] == "ML":
        return JSONResponse({"ok": False, "error": "El item ya está en ML"}, status_code=400)

    nuevo_precio = item["precio_unitario"] / 2.4
    nuevo_peso   = item["peso_unitario"]   / 2.4
    desc_calc    = item.get("descripcion_calculada")
    nueva_desc_calc = (desc_calc + " - POR ML") if desc_calc else None

    update_item_campos_carrito_db(
        item_id, usuario["u"],
        item["descripcion"], "ML", nuevo_precio, nueva_desc_calc,
    )
    # Actualizar también el peso
    update_item_precio_carrito_db(
        item_id, usuario["u"], nuevo_precio, nuevo_peso,
        item["descripcion"], nueva_desc_calc,
    )
    return JSONResponse({"ok": True})


@router.get("/resumen")
async def api_resumen_carrito(usuario: dict = Depends(require_login)):
    """Resumen compacto para el badge de la navbar."""
    carrito = get_carrito(usuario["u"])
    total = sum(item["precio_unitario"] * item["cantidad"] for item in carrito)
    return JSONResponse({
        "cantidad_items": len(carrito),
        "total": round(total, 2),
    })


# ─────────────────────────────────────────────
# Importar tabla desde portapapeles
# ─────────────────────────────────────────────

# Orden de prioridad: más específico primero para evitar falsos positivos
# Los keywords de una sola letra/código corto usan word-boundary (ver matching abajo)
_PRODUCT_KEYWORDS_ORDERED = [
    ("CP",  ["CAJA DE PASE", "CAJA DE PASO", "CAJAS DE PASE", "CAJAS DE PASO",
             "CAJA PASE", "CAJA FE GALV", "CAJA FE", "CAJA METALICA",
             "CAJAS METALICA", "CAJA FG", "CAJA F.G.", "CAJA F°G°", "CAJA F@G@",
             "CAJA"]),  # catch-all: "caja 300x300x100mm 3/4"
    ("CVE", ["CURVA VERTICAL EXTERNA", "ACCESORIO CURVA VERTICAL EXTERNA",
             "CVE", "ACCESORIO CVE"]),
    ("CVI", ["CURVA VERTICAL INTERNA", "ACCESORIO CURVA VERTICAL INTERNA",
             "CVI", "ACCESORIO CVI"]),
    ("CH",  ["CURVA HORIZONTAL", "ACCESORIO CURVA HORIZONTAL",
             "CURVA H", "ACCESORIO CURVA H", "ACCESORIO CH"]),
    ("T",   ["TEE", "ACCESORIO TEE", "ACCESORIO T", "T"]),
    ("C",   ["CRUZ", "ACCESORIO CRUZ", "ACCESORIO C"]),
    ("R",   ["REDUCCION", "REDUCCIÓN", "REDUC",
             "ACCESORIO REDUCCION", "ACCESORIO REDUCCIÓN", "ACCESORIO REDUC",
             "ACCESORIO R"]),
    ("B",   ["BANDEJA", "BDJ"]),
]

_CATALOGO_PATH = Path(__file__).resolve().parent.parent.parent / "catalogo_productos.json"

# ─────────────────────────────────────────────
# Búsqueda en catálogo de productos fijos
# ─────────────────────────────────────────────

def _cargar_catalogo_plano() -> list:
    """Carga catalogo_productos.json y devuelve todos los productos como lista plana."""
    try:
        with open(_CATALOGO_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    productos = []
    for cat in data.get("categorias", []):
        for sub in cat.get("subcategorias", []):
            for prod in sub.get("productos", []):
                productos.append({
                    "descripcion": prod.get("descripcion", ""),
                    "unidad": prod.get("unidad", "UND"),
                    "precio": float(prod.get("precio", 0)),
                })
    return productos


def _normalizar_para_match(texto: str) -> set:
    """Normaliza texto a conjunto de tokens para comparación fuzzy.

    Estrategia especial para especificaciones de diámetro en pulgadas:
    - Fracciones: "3/4" → "3_4" (token único para no confundir "3" y "4" por separado)
    - Pulgadas compuestas: '1 1/4"' → "1_1_4pul"
    - Pulgadas simples: '4"' → "4pul"
    Esto evita que "tubo EMT 4\"" coincida con "tubo EMT 3/4\"" por el token "4".
    """
    # Quitar acentos (NFD → ASCII)
    nfd = unicodedata.normalize("NFD", texto.lower())
    ascii_str = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Normalizar pulgadas compuestas antes de reemplazar chars especiales
    # "1 1/4\"" → "1_1_4pul"
    ascii_str = re.sub(r'(\d+)\s+(\d+)/(\d+)\s*"', r'\1_\2_\3pul', ascii_str)
    # "3/4\"" → "3_4pul"
    ascii_str = re.sub(r'(\d+)/(\d+)\s*"', r'\1_\2pul', ascii_str)
    # "4\"" → "4pul"
    ascii_str = re.sub(r'(\d+)\s*"', r'\1pul', ascii_str)
    # Preservar fracciones sin pulgadas: "3/4" → "3_4"
    ascii_str = re.sub(r'(\d+)/(\d+)', r'\1_\2', ascii_str)
    # Reemplazar caracteres no alfanuméricos por espacios
    limpio = re.sub(r"[^a-z0-9_]", " ", ascii_str)
    tokens = set(limpio.split())
    # Quitar tokens de una sola letra que no sean medidas conocidas
    tokens = {t for t in tokens if len(t) > 1 or t in ("m",)}
    return tokens


def _buscar_en_catalogo(descripcion: str, ganancia: str = "30") -> Optional[dict]:
    """
    Busca el mejor match para la descripción en el catálogo de precio fijo.
    Retorna dict con {descripcion, unidad, precio_catalogo, score} o None si no hay match >= 0.45.

    Si la descripción menciona explícitamente "IMC" no se busca en el catálogo
    (el catálogo solo tiene productos EMT).
    """
    if re.search(r'\bIMC\b', descripcion, re.IGNORECASE):
        return None

    productos = _cargar_catalogo_plano()
    if not productos:
        return None

    tokens_query = _normalizar_para_match(descripcion)
    if not tokens_query:
        return None

    mejor_score = 0.0
    mejor_prod = None

    for prod in productos:
        tokens_prod = _normalizar_para_match(prod["descripcion"])
        if not tokens_prod:
            continue
        interseccion = tokens_query & tokens_prod
        # score = intersección / mínimo de los dos conjuntos
        score = len(interseccion) / min(len(tokens_query), len(tokens_prod))
        if score > mejor_score:
            mejor_score = score
            mejor_prod = prod

    if mejor_score < 0.45 or mejor_prod is None:
        return None

    precio_base = mejor_prod["precio"]
    precio = precio_base * 0.7 / 0.65 if ganancia == "35" else precio_base

    return {
        "descripcion": mejor_prod["descripcion"],
        "unidad": mejor_prod["unidad"],
        "precio_catalogo": precio,
        "score": mejor_score,
    }


_DIM_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)'
    r'(?:\s*[xX×]\s*(\d+(?:[.,]\d+)?))?'
    r'(?:\s*[xX×]\s*(\d+(?:[.,]\d+)?))?'
)
_ESP_RE = re.compile(r'(\d+[.,]\d+)\s*MM', re.IGNORECASE)
_ESPESORES_VALIDOS = {1.2, 1.5, 2.0}

# Detecta patrón "enteroXenteroXenteroMM" en Caja de Pase (dims en mm, no en cm)
# Ej: "500X300X200MM" → dims en mm → dividir /10 para pasar al motor (que espera cm)
_CP_DIMS_MM_RE = re.compile(r'\b(\d+)\s*[xX×]\s*(\d+)\s*[xX×]\s*(\d+)\s*MM\b', re.IGNORECASE)

# Espesores en notación fraccionaria pulgadas → mm equivalente en nuestro sistema
_FRAC_ESPESOR = {"1/20": 1.2, "1/16": 1.5}
_FRAC_ESP_RE = re.compile(r'1/(?:20|16)', re.IGNORECASE)


def parsear_descripcion(desc_raw: str) -> dict:
    """Extrae tipo, dimensiones, espesor, galvanizado y superficie de la descripción."""
    desc = desc_raw.upper().strip()

    # Tipo de producto (primer keyword que coincida)
    # Códigos cortos (≤3 chars) usan word-boundary para evitar falsos positivos
    tipo = None
    for codigo, keywords in _PRODUCT_KEYWORDS_ORDERED:
        for kw in keywords:
            if len(kw) <= 3:
                if re.search(r'\b' + re.escape(kw) + r'\b', desc):
                    tipo = codigo
                    break
            else:
                if kw in desc:
                    tipo = codigo
                    break
        if tipo:
            break

    # Normalizar separador "A" entre grupos de dimensiones (ej: "600X100 A 400X100")
    desc_dims = re.sub(r'(?<=[0-9])\s+[Aa]\s+(?=[0-9])', 'X', desc)
    # Reemplazar coma decimal por punto para el regex
    desc_dims = desc_dims.replace(",", ".")

    dims: list[float] = []
    m = _DIM_RE.search(desc_dims)
    if m:
        for g in m.groups():
            if g is not None:
                try:
                    dims.append(float(g))
                except ValueError:
                    pass

    # Espesor: último número decimal seguido de MM (ej: "1.20 MM", "1.5MM")
    esp_matches = _ESP_RE.findall(desc.replace(",", "."))
    espesor = 1.5
    espesor_explicito = False
    if esp_matches:
        try:
            val = float(esp_matches[-1])
            espesor = val if val in _ESPESORES_VALIDOS else 1.5
            espesor_explicito = True
        except ValueError:
            pass
    else:
        # Fallback: notación fraccionaria en pulgadas (ej: "1/20"" → 1.2mm, "1/16"" → 1.5mm)
        frac_m = _FRAC_ESP_RE.search(desc)
        if frac_m:
            espesor = _FRAC_ESPESOR.get(frac_m.group(0).upper(), 1.5)
            espesor_explicito = True

    galvanizado_explicito = bool(re.search(r'\bGC\b', desc))
    galvanizado = "GC" if galvanizado_explicito else "GO"

    superficie_explicita = False
    if "ESCALERILLA" in desc:
        superficie = "ESCALERILLA"
        superficie_explicita = True
    elif "RANURADA" in desc:
        superficie = "RANURADA"
        superficie_explicita = True
    elif "LISA" in desc:
        superficie = "LISA"
        superficie_explicita = True
    else:
        superficie = "RANURADA"  # default para texto libre; tabla usa global override

    # Tipo de apertura para Caja de Pase
    knockout = "CIEGA"
    knockout_explicito = False
    if tipo == "CP":
        if any(kw in desc for kw in ("CON SALIDA", "C/SALIDA", "C/S", "KNOCKOUT", "K.O.", "KO")):
            # Intentar extraer la medida específica del tubo: 1/2, 3/4, 1, MIXTO
            _size_m = re.search(r'\bC[/\\]S\s+(MIXTO|1/2|3/4|1(?![/\d]))', desc)
            knockout = _size_m.group(1) if _size_m else "CON SALIDA"
            knockout_explicito = True
        elif re.search(r'\b(3/4|1/2)\b', desc):
            # Fracción sola (ej: "300x300x100mm 3/4") → C/S con esa medida
            frac_ko = re.search(r'\b(3/4|1/2)\b', desc)
            knockout = frac_ko.group(1) if frac_ko else "CON SALIDA"
            knockout_explicito = True
        elif "CIEGA" in desc:
            knockout = "CIEGA"
            knockout_explicito = True

    # Caja de Pase: el motor espera dims en CM (multiplica ×10 internamente).
    # Reglas de conversión de unidades:
    #   1. Sufijo MM explícito (ej: "500X300X200MM") → dividir /10
    #   2. Sufijo CM explícito (ej: "15 X 15 X 10 CM") → ya están en CM, sin cambio
    #   3. Sin sufijo y max(dim) ≥ 100 → interpretar como MM → dividir /10
    #      (ej: "CAJA PASE 100X100X50 SAP" = 100x100x50 mm = 10x10x5 cm)
    if tipo == "CP" and dims:
        cp_mm_m = _CP_DIMS_MM_RE.search(desc)
        if cp_mm_m:
            dims = [d / 10.0 for d in dims]
        elif "CM" not in desc and dims and max(dims) >= 100:
            dims = [d / 10.0 for d in dims]

    return {
        "tipo": tipo,
        "dims": dims,
        "espesor": espesor,
        "espesor_explicito": espesor_explicito,
        "galvanizado": galvanizado,
        "galvanizado_explicito": galvanizado_explicito,
        "superficie": superficie,
        "superficie_explicita": superficie_explicita,
        "knockout": knockout,
        "knockout_explicito": knockout_explicito,
    }


def calcular_precio_importado(
    parsed: dict,
    config: dict,
    overrides: Optional[dict] = None,
    con_tapa: bool = False,
    es_metro_lineal: bool = False,
    espesor_tapa_item: Optional[float] = None,
):
    """
    Calcula precio y peso usando motor.py dado un parsed de parsear_descripcion().
    overrides: galvanizado_global, espesor_cuerpo_global, espesor_tapa_global, ganancia_global,
               superficie_global — se aplican solo cuando el ítem no tiene valor explícito.
    con_tapa: si True, retorna también datos de la tapa como ítem separado.
    es_metro_lineal: divide precio/peso de bandeja por 2.4 y agrega "– POR ML".
    espesor_tapa_item: espesor específico de la tapa (por ítem); None = usar global o body.
    Retorna {"cuerpo": (precio, peso, desc), "tapa": (precio, peso, desc) | None} o None.
    """
    tipo = parsed.get("tipo")
    dims = parsed.get("dims", [])
    knockout = parsed.get("knockout", "CIEGA")

    if not tipo:
        return None

    ov = overrides or {}

    # Galvanizado: explícito en descripción > global override > default GO
    if parsed.get("galvanizado_explicito"):
        galvanizado = parsed.get("galvanizado", "GO")
    elif ov.get("galvanizado_global"):
        galvanizado = ov["galvanizado_global"]
    else:
        galvanizado = parsed.get("galvanizado", "GO")

    # Superficie: explícita en descripción > global override > default RANURADA
    if parsed.get("superficie_explicita"):
        superficie = parsed.get("superficie", "RANURADA")
    elif ov.get("superficie_global"):
        superficie = ov["superficie_global"]
    else:
        superficie = parsed.get("superficie", "RANURADA")

    # Espesor cuerpo: explícito en descripción > global override > default 1.5
    if parsed.get("espesor_explicito"):
        espesor = parsed.get("espesor", 1.5)
    elif ov.get("espesor_cuerpo_global"):
        espesor = float(ov["espesor_cuerpo_global"])
    else:
        espesor = parsed.get("espesor", 1.5)

    # Espesor tapa: por ítem > global override > igual que cuerpo
    if espesor_tapa_item is not None:
        espesor_tapa = float(espesor_tapa_item)
    elif ov.get("espesor_tapa_global"):
        espesor_tapa = float(ov["espesor_tapa_global"])
    else:
        espesor_tapa = espesor  # mismo que cuerpo por defecto

    valores = config.get("valores_defecto", {})
    ganancia = ov.get("ganancia_global") or valores.get("ganancia", "30")
    dolar = float(valores.get("dolar", 3.8))
    usd_kg_productos = float(valores.get("usd_kg_productos", 1.0))
    usd_kg_cajas = float(valores.get("usd_kg_cajas", 3.0))

    esp_str = f"{espesor:.1f}"
    esp_tapa_str = f"{espesor_tapa:.1f}"
    precios_key = "precios_go" if galvanizado == "GO" else "precios_gc"
    precios = valores.get(precios_key, {})

    fallback_pl = float(list(precios.values())[0]) if precios else 180.0
    precio_pl = float(precios.get(esp_str, fallback_pl))
    precio_pl_tapa = float(precios.get(esp_tapa_str, fallback_pl))

    cfg = PricingConfig(
        tipo_galvanizado=galvanizado,
        dolar=dolar,
        precio_galvanizado_kg=usd_kg_productos,
        porcentaje_ganancia=ganancia,
        usd_kg_cajas=usd_kg_cajas,
    )

    try:
        if tipo == "B":
            if len(dims) < 2:
                return None
            r = cotizar_bandeja(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                dims[0], dims[1], superficie, es_metro_lineal)

        elif tipo == "CH":
            if len(dims) < 2:
                return None
            r = cotizar_curva_horizontal(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                         dims[0], dims[1], superficie)

        elif tipo == "CVE":
            if len(dims) < 2:
                return None
            r = cotizar_curva_vertical(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                       dims[0], dims[1], "EXTERNA", superficie)

        elif tipo == "CVI":
            if len(dims) < 2:
                return None
            r = cotizar_curva_vertical(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                       dims[0], dims[1], "INTERNA", superficie)

        elif tipo == "T":
            if len(dims) < 4:
                return None
            r = cotizar_tee(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                            dims[0], dims[1], dims[2], dims[3], superficie)

        elif tipo == "C":
            if len(dims) < 2:
                return None
            r = cotizar_cruz(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                             dims[0], dims[1], superficie)

        elif tipo == "R":
            if len(dims) < 3:
                return None
            r = cotizar_reduccion(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                  dims[0], dims[1], dims[2], superficie)

        elif tipo == "CP":
            if len(dims) < 3:
                return None
            r = cotizar_caja_pase(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                  dims[0], dims[1], dims[2], knockout)

        else:
            return None

        cuerpo = (r[0]["precio_unitario"], r[0]["peso_unitario"], r[0]["descripcion"])
        # Tapa: solo si con_tapa=True, tipo != CP, y el motor retornó un segundo ítem
        tapa = None
        if con_tapa and tipo != "CP" and len(r) > 1:
            tapa = (r[1]["precio_unitario"], r[1]["peso_unitario"], r[1]["descripcion"])

        return {"cuerpo": cuerpo, "tapa": tapa}

    except Exception:
        return None


class _ImportarItemIn(BaseModel):
    descripcion: str
    unidad: str = "UND"
    cantidad: int = 1
    con_tapa: bool = False          # True → agregar tapa como ítem separado (texto libre)
    espesor_tapa: Optional[float] = None  # None → usar global o mismo que cuerpo


class _ImportarRequestIn(BaseModel):
    items: list[_ImportarItemIn]
    galvanizado_global: Optional[str] = None    # "GO" | "GC"
    espesor_cuerpo_global: Optional[float] = None  # 1.2 | 1.5 | 2.0
    espesor_tapa_global: Optional[float] = None    # 1.2 | 1.5 | 2.0
    ganancia_global: Optional[str] = None       # "30" | "35"
    superficie_global: Optional[str] = None     # "LISA" | "RANURADA" | "ESCALERILLA"


@router.post("/importar/procesar")
async def importar_procesar(
    body: _ImportarRequestIn,
    usuario: dict = Depends(require_login),
):
    """Analiza una lista de ítems y devuelve precios calculados aplicando parámetros globales."""
    config = cargar_config()
    overrides = {
        "galvanizado_global": body.galvanizado_global,
        "espesor_cuerpo_global": body.espesor_cuerpo_global,
        "espesor_tapa_global": body.espesor_tapa_global,
        "ganancia_global": body.ganancia_global,
        "superficie_global": body.superficie_global,
    }
    ganancia_efectiva = body.ganancia_global or config.get("valores_defecto", {}).get("ganancia", "30")
    results = []
    for item in body.items:
        parsed = parsear_descripcion(item.descripcion)
        es_ml = item.unidad == "ML" and parsed.get("tipo") == "B"

        precio_data = calcular_precio_importado(
            parsed, config, overrides,
            con_tapa=item.con_tapa,
            es_metro_lineal=es_ml,
            espesor_tapa_item=item.espesor_tapa,
        )

        # Galvanizado efectivo para mostrar en resultado
        if parsed.get("galvanizado_explicito"):
            galv_efectivo = parsed["galvanizado"]
        else:
            galv_efectivo = body.galvanizado_global or parsed["galvanizado"]

        if precio_data is not None:
            cuerpo = precio_data["cuerpo"]

            # Enriquecer descripción del cuerpo con espesor/knockout si no venían explícitos
            desc_final = item.descripcion
            if parsed["tipo"] is not None:
                if parsed.get("espesor_explicito"):
                    esp_efectivo = parsed["espesor"]
                elif body.espesor_cuerpo_global:
                    esp_efectivo = body.espesor_cuerpo_global
                else:
                    esp_efectivo = parsed["espesor"]
                espesor_str = f"{esp_efectivo:.1f}MM"
                falta_espesor = not parsed["espesor_explicito"]
                falta_knockout = parsed["tipo"] == "CP" and not parsed["knockout_explicito"]

                if falta_knockout and falta_espesor:
                    desc_final = item.descripcion.rstrip() + f" {parsed['knockout']} {espesor_str}"
                elif falta_knockout:
                    desc_final = item.descripcion.rstrip() + f" {parsed['knockout']}"
                elif falta_espesor:
                    desc_final = item.descripcion.rstrip() + f" {espesor_str}"

            # Ítem cuerpo
            results.append({
                "descripcion": desc_final,
                "unidad": item.unidad,
                "cantidad": item.cantidad,
                "tipo": parsed["tipo"] or "MANUAL",
                "precio_unitario":       round(cuerpo[0], 4),
                "peso_unitario":         round(cuerpo[1], 6),
                "descripcion_calculada": cuerpo[2],
                "tipo_galvanizado":      galv_efectivo,
                "porcentaje_ganancia":   ganancia_efectiva,
                "reconocido": True,
                "error": None,
            })

            # Ítem tapa (si aplica)
            tapa = precio_data.get("tapa")
            if tapa:
                results.append({
                    "descripcion": tapa[2],
                    "unidad": item.unidad,
                    "cantidad": item.cantidad,
                    "tipo": parsed["tipo"],
                    "precio_unitario":       round(tapa[0], 4),
                    "peso_unitario":         round(tapa[1], 6),
                    "descripcion_calculada": tapa[2],
                    "tipo_galvanizado":      galv_efectivo,
                    "porcentaje_ganancia":   ganancia_efectiva,
                    "reconocido": True,
                    "error": None,
                })
        else:
            # Intentar match contra catálogo de productos fijos
            cat_match = _buscar_en_catalogo(item.descripcion, ganancia_efectiva)
            if cat_match:
                results.append({
                    "descripcion": cat_match["descripcion"],
                    "unidad": item.unidad,
                    "cantidad": item.cantidad,
                    "tipo": "CATALOGO",
                    "precio_unitario":       round(cat_match["precio_catalogo"], 4),
                    "peso_unitario":         0,
                    "descripcion_calculada": cat_match["descripcion"],
                    "tipo_galvanizado":      "N/A",
                    "porcentaje_ganancia":   ganancia_efectiva,
                    "reconocido": True,
                    "error": None,
                    "es_catalogo": True,
                })
            else:
                results.append({
                    "descripcion": item.descripcion,
                    "unidad": item.unidad,
                    "cantidad": item.cantidad,
                    "tipo": "MANUAL",
                    "precio_unitario":       None,
                    "peso_unitario":         None,
                    "descripcion_calculada": None,
                    "tipo_galvanizado":      galv_efectivo,
                    "porcentaje_ganancia":   ganancia_efectiva,
                    "reconocido": False,
                    "error": "No se reconoció el tipo o las dimensiones",
                })

    return JSONResponse({"ok": True, "items": results})
