"""
planchas.py — API para el módulo de Planchas (Guillotine Packer)

POST /api/planchas/calcular         — Corre el packer y calcula precios
POST /api/planchas/agregar-carrito  — Agrega las planchas al carrito
POST /api/planchas/desde-carrito    — Analiza el carrito y calcula planchas necesarias
"""
import math
import re
from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator

from web.auth import require_login
from web.database import add_item_carrito_db, cargar_config, get_carrito_db
from web.guillotine import Pieza, guillotine_pack

router = APIRouter(prefix="/api/planchas", tags=["planchas"])


# ─────────────────────────────────────────────
# Modelos de entrada
# ─────────────────────────────────────────────

class PiezaIn(BaseModel):
    ancho: float
    alto: float
    cantidad: int = 1
    nombre: str = ""
    color: str = "#4fffb0"

    @validator("ancho", "alto")
    def positivo(cls, v):
        if v <= 0:
            raise ValueError("Las dimensiones deben ser positivas")
        return v

    @validator("cantidad")
    def cantidad_valida(cls, v):
        if v < 1:
            raise ValueError("La cantidad debe ser al menos 1")
        return min(v, 200)


class CalcularRequest(BaseModel):
    ancho_plancha: float = 2400.0
    alto_plancha: float = 1200.0
    espaciado: float = 4.0
    espesor: str = "1.5"
    tipo_galvanizado: str = "GO"
    piezas: List[PiezaIn]

    @validator("piezas")
    def al_menos_una(cls, v):
        if not v:
            raise ValueError("Debe ingresar al menos una pieza")
        if len(v) > 50:
            raise ValueError("Máximo 50 tipos de piezas")
        return v

    @validator("tipo_galvanizado")
    def galv_valido(cls, v):
        if v not in ("GO", "GC"):
            raise ValueError("Tipo de galvanizado inválido")
        return v

    @validator("espesor")
    def espesor_valido(cls, v):
        if v not in ("1.2", "1.5", "2.0"):
            raise ValueError("Espesor inválido")
        return v


class AgregarCarritoRequest(BaseModel):
    n_planchas: int
    espesor: str
    tipo_galvanizado: str
    ancho_plancha: float = 2400.0
    alto_plancha: float = 1200.0
    total_colocadas: int
    total_solicitadas: int
    utilizacion_promedio: float
    descripcion_piezas: str = ""


# ─────────────────────────────────────────────
# Helpers de precio
# ─────────────────────────────────────────────

def _calcular_precio_plancha(espesor: str, tipo_galvanizado: str,
                              ancho: float, alto: float,
                              config: dict) -> dict:
    """Calcula precio de costo y peso de UNA plancha completa (sin markup)."""
    valores = config.get("valores_defecto", {})
    precios_key = "precios_go" if tipo_galvanizado == "GO" else "precios_gc"
    precios = valores.get(precios_key, {})
    precio_pl = float(precios.get(espesor, 150.0))

    espesor_f = float(espesor)
    peso_pl = ancho * alto * 0.00000785 * espesor_f

    costo_galv = 0.0
    if tipo_galvanizado == "GC":
        dolar = float(valores.get("dolar", 3.8))
        usd_kg = float(valores.get("usd_kg_productos", 1.0))
        costo_galv = (peso_pl * dolar * usd_kg) / 0.95

    precio_costo = precio_pl + costo_galv

    return {
        "precio_unitario": round(precio_costo, 4),
        "peso_unitario": round(peso_pl, 4),
    }


def _resumen_piezas(piezas: List[PiezaIn]) -> str:
    """Genera texto resumen: '3×600×400, 5×300×300'."""
    parts = []
    for p in piezas:
        n = p.nombre or f"{p.ancho:.0f}×{p.alto:.0f}"
        if p.cantidad > 1:
            parts.append(f"{p.cantidad}×{n}")
        else:
            parts.append(n)
    return ", ".join(parts)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.post("/calcular")
async def api_calcular_planchas(
    req: CalcularRequest,
    usuario: dict = Depends(require_login),
):
    """Corre el algoritmo guillotina y calcula precios de plancha."""
    try:
        piezas_obj = [
            Pieza(
                ancho=p.ancho, alto=p.alto, cantidad=p.cantidad,
                nombre=p.nombre or f"{p.ancho:.0f}×{p.alto:.0f}",
                color=p.color,
            )
            for p in req.piezas
        ]

        resultado = guillotine_pack(
            ancho_plancha=req.ancho_plancha,
            alto_plancha=req.alto_plancha,
            piezas=piezas_obj,
            espaciado=req.espaciado,
        )

        # Serializar resultado
        planchas_json = []
        for rp in resultado.planchas:
            planchas_json.append({
                "idx": rp.idx,
                "piezas": [
                    {
                        "x": pc.x, "y": pc.y,
                        "ancho_colocado": pc.ancho_colocado,
                        "alto_colocado": pc.alto_colocado,
                        "ancho_original": pc.ancho_original,
                        "alto_original": pc.alto_original,
                        "rotada": pc.rotada,
                        "nombre": pc.nombre,
                        "color": pc.color,
                        "plancha_idx": pc.plancha_idx,
                    }
                    for pc in rp.piezas
                ],
                "cortes": [
                    {
                        "tipo": c.tipo, "posicion": c.posicion,
                        "desde": c.desde, "hasta": c.hasta,
                        "plancha_idx": c.plancha_idx,
                    }
                    for c in rp.cortes
                ],
                "area_usada": round(rp.area_usada, 2),
                "area_total": round(rp.area_total, 2),
                "utilizacion": rp.utilizacion,
            })

        # Precios
        config = cargar_config()
        precios = _calcular_precio_plancha(
            req.espesor, req.tipo_galvanizado,
            req.ancho_plancha, req.alto_plancha, config,
        )

        n_planchas = len(resultado.planchas)
        util_promedio = (
            sum(rp.utilizacion for rp in resultado.planchas) / n_planchas
            if n_planchas > 0 else 0.0
        )
        area_total_m2 = (req.ancho_plancha * req.alto_plancha) / 1_000_000
        area_usada_m2 = sum(
            rp.area_usada / 1_000_000 for rp in resultado.planchas
        )
        desperdicio_m2 = round(area_total_m2 * n_planchas - area_usada_m2, 4)

        resumen = {
            "n_planchas": n_planchas,
            "total_colocadas": resultado.total_colocadas,
            "total_solicitadas": resultado.total_solicitadas,
            "utilizacion_promedio": round(util_promedio, 4),
            "desperdicio_m2": desperdicio_m2,
            "precio_unitario_plancha": precios["precio_unitario"],
            "peso_unitario_plancha": precios["peso_unitario"],
            "precio_total": round(precios["precio_unitario"] * n_planchas, 4),
            "peso_total": round(precios["peso_unitario"] * n_planchas, 4),
            "espesor": req.espesor,
            "tipo_galvanizado": req.tipo_galvanizado,
            "ancho_plancha": req.ancho_plancha,
            "alto_plancha": req.alto_plancha,
            "descripcion_piezas": _resumen_piezas(req.piezas),
        }

        return JSONResponse({
            "ok": True,
            "planchas": planchas_json,
            "resumen": resumen,
            "no_colocadas": resultado.no_colocadas,
        })

    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=422)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Error interno: {e}"}, status_code=500)


@router.post("/agregar-carrito")
async def api_agregar_planchas_carrito(
    req: AgregarCarritoRequest,
    usuario: dict = Depends(require_login),
):
    """Agrega las planchas calculadas al carrito del usuario."""
    try:
        if req.n_planchas < 1:
            return JSONResponse({"ok": False, "error": "n_planchas inválido"}, status_code=422)

        # Recalcular precio desde el config actual (evita manipulación del cliente)
        config = cargar_config()
        precios = _calcular_precio_plancha(
            req.espesor, req.tipo_galvanizado,
            req.ancho_plancha, req.alto_plancha, config,
        )

        desc = (
            f"PLANCHA {req.ancho_plancha:.0f}×{req.alto_plancha:.0f}mm "
            f"esp.{req.espesor}mm {req.tipo_galvanizado}"
        )

        n = req.n_planchas
        util_pct = round(req.utilizacion_promedio * 100)
        desc_calc = (
            f"{n} PLANCHA{'S' if n > 1 else ''} {req.espesor}mm {req.tipo_galvanizado}"
            f" — {req.total_colocadas}/{req.total_solicitadas} piezas"
            f"{': ' + req.descripcion_piezas if req.descripcion_piezas else ''}"
            f" — Util. {util_pct}%"
        )

        item = {
            "tipo": "PL",
            "descripcion": desc,
            "descripcion_calculada": desc_calc,
            "precio_unitario": precios["precio_unitario"],
            "peso_unitario": precios["peso_unitario"],
            "cantidad": req.n_planchas,
            "unidad": "UND",
            "tipo_galvanizado": req.tipo_galvanizado,
        }

        add_item_carrito_db(usuario["u"], item)

        n_items = len(get_carrito_db(usuario["u"]))

        return JSONResponse({
            "ok": True,
            "mensaje": f"{req.n_planchas} plancha(s) agregada(s) al carrito",
            "cantidad_items": n_items,
        })

    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Error al agregar: {e}"}, status_code=500)


# ─────────────────────────────────────────────
# Helpers para "desde-carrito"
# ─────────────────────────────────────────────

_PALETTE = [
    '#5b8dee', '#f9654a', '#2ec4b6', '#f4c542', '#9b59b6',
    '#e91e8c', '#27ae60', '#e67e22', '#1abc9c', '#3498db',
    '#e74c3c', '#f39c12', '#16a085', '#8e44ad', '#2c3e50',
    '#d35400', '#c0392b', '#7f8c8d',
]


def _extraer_espesor_str(descripcion: str) -> Optional[str]:
    """Extrae el espesor de la descripción como string ('1.5')."""
    matches = re.findall(r'(\d+\.\d+)MM', descripcion.upper())
    if matches:
        return f"{float(matches[-1]):.1f}"
    return None


def _parsear_dims(desc: str, tipo: str) -> Optional[dict]:
    """Parsea las dimensiones relevantes de la descripción del motor según el tipo."""
    u = desc.upper()

    if tipo == "B":
        m = re.search(r'(\d+)X(\d+)X2400MM', u)
        if m:
            return {"ancho": int(m.group(1)), "alto": int(m.group(2))}
        # tapa bandeja: "TAPA BANDEJA 600X100MM"
        m = re.search(r'(\d+)X(\d+)MM', u)
        if m:
            return {"ancho": int(m.group(1)), "alto": int(m.group(2))}

    elif tipo == "T":
        m = re.search(r'(\d+)X(\d+)X(\d+)X(\d+)MM', u)
        if m:
            return {
                "derecha": int(m.group(1)), "izquierda": int(m.group(2)),
                "abajo": int(m.group(3)), "alto": int(m.group(4)),
            }

    elif tipo == "R":
        m = re.search(r'(\d+)X(\d+)\s*A\s*(\d+)X(\d+)MM', u)
        if m:
            return {
                "ancho_mayor": int(m.group(1)), "alto": int(m.group(2)),
                "ancho_menor": int(m.group(3)),
            }

    elif tipo == "CP":
        m = re.search(r'(\d+(?:\.\d+)?)X(\d+(?:\.\d+)?)X(\d+(?:\.\d+)?)MM', u)
        if m:
            return {
                "ancho_mm": float(m.group(1)),
                "largo_mm": float(m.group(2)),
                "alto_mm":  float(m.group(3)),
            }

    elif tipo in ("CH", "CVE", "CVI", "C"):
        m = re.search(r'(\d+)X(\d+)MM', u)
        if m:
            return {"ancho": int(m.group(1)), "alto": int(m.group(2))}

    return None


def _short_label(tipo: str, dims: dict, es_tapa: bool) -> str:
    prefix = "Tapa " if es_tapa else ""
    if tipo == "B":
        return f"{prefix}Bandeja {dims['ancho']}×{dims['alto']}"
    if tipo == "CH":
        return f"{prefix}Curva H {dims['ancho']}×{dims['alto']}"
    if tipo == "CVE":
        return f"{prefix}Curva VE {dims['ancho']}×{dims['alto']}"
    if tipo == "CVI":
        return f"{prefix}Curva VI {dims['ancho']}×{dims['alto']}"
    if tipo == "T":
        return f"{prefix}Tee {dims['derecha']}×{dims['izquierda']}×{dims['abajo']}×{dims['alto']}"
    if tipo == "C":
        return f"{prefix}Cruz {dims['ancho']}×{dims['alto']}"
    if tipo == "R":
        return f"{prefix}Reduc. {dims['ancho_mayor']}→{dims['ancho_menor']}×{dims['alto']}"
    if tipo == "CP":
        return f"Caja {int(dims['ancho_mm'])}×{int(dims['largo_mm'])}×{int(dims['alto_mm'])}"
    return f"{prefix}{tipo}"


def _desarrollos_item(
    tipo: str, dims: dict, es_tapa: bool,
    carrito_cant: int, label: str, color: str,
) -> List[Pieza]:
    """Calcula los desarrollos rectangulares de plancha para un ítem del carrito."""
    # parts: [(nombre_pieza, ancho_mm, alto_mm), ...]
    parts: list = []

    if tipo == "B":
        ancho, alto = dims["ancho"], dims["alto"]
        if es_tapa:
            parts = [
                ("Tapa",  ancho + 50,      2400),
            ]
        else:
            parts = [
                ("Cuerpo", ancho + alto * 2, 2400),
                ("Unión",  ancho + alto * 2, 100),
            ]

    elif tipo == "CH":
        ancho, alto = dims["ancho"], dims["alto"]
        if es_tapa:
            parts = [("Tapa", ancho + 252, ancho + 252)]
        else:
            lv = (
                (ancho * 0.414 + 100) * 2
                + ((ancho + 250) - (ancho * 0.414 + 100)) * math.sqrt(2)
            )
            parts = [
                ("Cuerpo",           ancho + 250,      ancho + 250),
                ("Larguero",         math.ceil(lv),    alto + 15),
                ("Larguero pequeño", 413,               alto + 15),
                ("Unión",            ancho + alto * 2, 100),
            ]

    elif tipo == "CVE":
        ancho, alto = dims["ancho"], dims["alto"]
        if es_tapa:
            parts = [("Tapa", ancho + 40, 577)]
        else:
            parts = [
                ("Cuerpo",  ancho + 30,       413),
                ("Lateral", 350,              350),
                ("Lateral", 350,              350),
                ("Unión",   ancho + alto * 2, 100),
            ]

    elif tipo == "CVI":
        ancho, alto = dims["ancho"], dims["alto"]
        if es_tapa:
            parts = [("Tapa", ancho + 30, 413)]
        else:
            parts = [
                ("Cuerpo",  ancho + 40,       577),
                ("Lateral", 350,              350),
                ("Lateral", 350,              350),
                ("Unión",   ancho + alto * 2, 100),
            ]

    elif tipo == "T":
        derecha   = dims["derecha"]
        izquierda = dims["izquierda"]
        abajo     = dims["abajo"]
        alto      = dims["alto"]
        if es_tapa:
            parts = [("Tapa", 500 + abajo, derecha + 252)]
        else:
            d  = (derecha + 250) - izquierda
            lv = 200 + math.sqrt(150 ** 2 + (d - 100) ** 2)
            parts = [
                ("Cuerpo",           500 + abajo,        derecha + alto + 250),
                ("Larguero pequeño", 413,                 alto + 15),
                ("Larguero",         math.ceil(lv),       alto + 15),
                ("Unión",            derecha + alto * 2,  100),
                ("Unión",            derecha + alto * 2,  100),
            ]

    elif tipo == "C":
        ancho, alto = dims["ancho"], dims["alto"]
        if es_tapa:
            parts = [("Tapa", ancho + 500, ancho + 500)]
        else:
            parts = (
                [("Cuerpo",           ancho + 500,      ancho + 500)]
                + [("Larguero pequeño", 413,              alto + 15)] * 4
                + [("Unión",            ancho + alto * 2, 100)] * 3
            )

    elif tipo == "R":
        ancho_mayor = dims["ancho_mayor"]
        alto        = dims["alto"]
        ancho_menor = dims["ancho_menor"]
        if es_tapa:
            parts = [("Tapa", ancho_mayor + 4, 413)]
        else:
            p    = (ancho_mayor - ancho_menor) / 2
            lv_r = 200 + math.sqrt(p ** 2 + 212 ** 2)
            parts = [
                ("Cuerpo",   ancho_mayor,             413),
                ("Larguero", math.ceil(lv_r),          alto + 12),
                ("Larguero", math.ceil(lv_r),          alto + 12),
                ("Unión",    ancho_mayor + alto * 2,   100),
            ]

    elif tipo == "CP":
        ancho_mm = dims["ancho_mm"]
        largo_mm = dims["largo_mm"]
        alto_mm  = dims["alto_mm"]
        parts = [
            ("Cuerpo",   alto_mm * 2 + ancho_mm + 20, largo_mm),
            ("Cabecera", alto_mm + 20,                 ancho_mm + 20),
            ("Cabecera", alto_mm + 20,                 ancho_mm + 20),
            ("Tapa",     largo_mm,                     ancho_mm),
        ]

    result: List[Pieza] = []
    for k in range(1, carrito_cant + 1):
        k_sfx = f" #{k}" if carrito_cant > 1 else ""
        for n, (nombre_pieza, a, h) in enumerate(parts, 1):
            result.append(Pieza(
                ancho=max(1, int(math.ceil(float(a)))),
                alto=max(1, int(math.ceil(float(h)))),
                cantidad=1,
                nombre=f"{nombre_pieza} {label}{k_sfx} p.{n}",
                color=color,
            ))
    return result


# ─────────────────────────────────────────────
# Endpoint: planchas desde el carrito
# ─────────────────────────────────────────────

@router.post("/desde-carrito")
async def api_planchas_desde_carrito(usuario: dict = Depends(require_login)):
    """Analiza el carrito del usuario y calcula cuántas planchas se necesitan."""
    try:
        carrito = get_carrito_db(usuario["u"])

        items_ignorados: List[str] = []
        leyenda: List[dict] = []
        grupos: dict = {}   # {(espesor_str, galv): [Pieza]}
        color_idx = 0

        for item in carrito:
            # Ignorar manuales, catálogos y planchas previamente calculadas
            tipo  = item.get("tipo", "")
            galv  = item.get("tipo_galvanizado", "")
            if galv == "N/A" or tipo == "PL":
                items_ignorados.append(item["descripcion"])
                continue

            cant = item.get("cantidad", 1)
            desc = item.get("descripcion_calculada") or item.get("descripcion", "")

            es_tapa = "TAPA" in desc.upper()
            dims    = _parsear_dims(desc, tipo)
            if dims is None:
                items_ignorados.append(item["descripcion"])
                continue

            espesor_str = _extraer_espesor_str(desc)
            if espesor_str is None:
                items_ignorados.append(item["descripcion"])
                continue

            color = _PALETTE[color_idx % len(_PALETTE)]
            color_idx += 1
            label = _short_label(tipo, dims, es_tapa)

            leyenda.append({"color": color, "label": label, "id": item["id"]})

            piezas = _desarrollos_item(tipo, dims, es_tapa, cant, label, color)
            key = (espesor_str, galv)
            grupos.setdefault(key, []).extend(piezas)

        grupos_json = []
        for (espesor_str, galv), piezas in grupos.items():
            resultado = guillotine_pack(2400, 1200, piezas, espaciado=0.0)

            n = len(resultado.planchas)
            util_prom = (
                sum(rp.utilizacion for rp in resultado.planchas) / n
                if n > 0 else 0.0
            )
            area_total_m2 = (2400 * 1200) / 1_000_000
            area_usada_m2 = sum(rp.area_usada / 1_000_000 for rp in resultado.planchas)
            desperdicio   = round(area_total_m2 * n - area_usada_m2, 4)

            planchas_json = []
            for rp in resultado.planchas:
                planchas_json.append({
                    "idx": rp.idx,
                    "piezas": [
                        {
                            "x": pc.x, "y": pc.y,
                            "ancho_colocado": pc.ancho_colocado,
                            "alto_colocado": pc.alto_colocado,
                            "ancho_original": pc.ancho_original,
                            "alto_original": pc.alto_original,
                            "rotada": pc.rotada,
                            "nombre": pc.nombre,
                            "color": pc.color,
                            "plancha_idx": pc.plancha_idx,
                        }
                        for pc in rp.piezas
                    ],
                    "cortes": [
                        {
                            "tipo": c.tipo, "posicion": c.posicion,
                            "desde": c.desde, "hasta": c.hasta,
                            "plancha_idx": c.plancha_idx,
                        }
                        for c in rp.cortes
                    ],
                    "area_usada": round(rp.area_usada, 2),
                    "area_total": round(rp.area_total, 2),
                    "utilizacion": rp.utilizacion,
                })

            grupos_json.append({
                "espesor": espesor_str,
                "tipo_galvanizado": galv,
                "planchas": planchas_json,
                "resumen": {
                    "n_planchas": n,
                    "total_colocadas": resultado.total_colocadas,
                    "total_solicitadas": resultado.total_solicitadas,
                    "utilizacion_promedio": round(util_prom, 4),
                    "desperdicio_m2": desperdicio,
                },
                "no_colocadas": resultado.no_colocadas,
            })

        return JSONResponse({
            "ok": True,
            "grupos": grupos_json,
            "items_ignorados": items_ignorados,
            "leyenda": leyenda,
        })

    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Error: {e}"}, status_code=500)
