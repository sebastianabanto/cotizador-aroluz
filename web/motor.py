"""
motor.py — Motor de precios puro (sin globals)

Reimplementa la lógica de gui/logica.py usando PricingConfig como
parámetro en lugar de variables globales. Esto lo hace thread-safe
para uso en FastAPI con múltiples requests concurrentes.
"""
import math
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


# ─────────────────────────────────────────────
# Configuración de precios (reemplaza globals)
# ─────────────────────────────────────────────

@dataclass
class PricingConfig:
    """Configuración de precios para una cotización. Inmutable por request."""
    tipo_galvanizado: str       # "GO" o "GC"
    dolar: float                # Tipo de cambio S/ por USD
    precio_galvanizado_kg: float  # USD/kg para galvanizado en caliente (productos)
    porcentaje_ganancia: str    # "30" o "35"
    usd_kg_cajas: float = 3.0  # USD/kg para galvanizado de Cajas de Pase

    @property
    def factor_ganancia(self) -> float:
        return 0.70 if self.porcentaje_ganancia == "30" else 0.65


PL_MM2 = 2400 * 1200  # Área estándar de plancha en mm²


# ─────────────────────────────────────────────
# Funciones auxiliares puras
# ─────────────────────────────────────────────

def calcular_precio(area: float, pl_undmm2: float) -> float:
    return area * pl_undmm2


def calcular_peso(area: float, espesor: float) -> float:
    return area * 0.00000785 * espesor


def aplicar_precio_escalerilla(precio_base: float, tipo_superficie: str) -> float:
    if tipo_superficie == "ESCALERILLA":
        return precio_base + 10
    return precio_base


def calcular_costo_galvanizado(cfg: PricingConfig, peso: float) -> float:
    if cfg.tipo_galvanizado == "GC":
        return peso * cfg.dolar * cfg.precio_galvanizado_kg
    return 0.0


def aplicar_costo_galvanizado(cfg: PricingConfig, precio_base: float, peso: float) -> float:
    if cfg.tipo_galvanizado == "GC":
        costo = calcular_costo_galvanizado(cfg, peso)
        return precio_base + (costo / 0.95)
    return precio_base


def get_factor_ganancia_producto(cfg: PricingConfig, producto: str) -> float:
    factores = {
        "30": {"CH": 0.5, "CVE": 0.5, "CVI": 0.5, "T": 0.6, "C": 0.7, "R": 0.2, "CP": 0.5},
        "35": {"CH": 0.45, "CVE": 0.45, "CVI": 0.45, "T": 0.55, "C": 0.65, "R": 0.15, "CP": 0.475},
    }
    return factores.get(cfg.porcentaje_ganancia, {}).get(producto, cfg.factor_ganancia)


def aplicar_ganancia(cfg: PricingConfig, precio: float, producto: Optional[str] = None) -> float:
    factor = get_factor_ganancia_producto(cfg, producto) if producto else cfg.factor_ganancia
    return precio / factor


def calcular_precio_final(
    cfg: PricingConfig,
    precio_base: float,
    peso: float,
    producto: Optional[str] = None,
    precio_union: Optional[float] = None,
    peso_union: Optional[float] = None,
):
    precio_con_galv = aplicar_costo_galvanizado(cfg, precio_base, peso)
    precio_final = aplicar_ganancia(cfg, precio_con_galv, producto)

    if precio_union is not None and peso_union is not None:
        precio_u_con_galv = aplicar_costo_galvanizado(cfg, precio_union, peso_union)
        precio_u_final = aplicar_ganancia(cfg, precio_u_con_galv, producto)
        return precio_final + precio_u_final, peso + peso_union

    return precio_final, peso


def generar_descripcion_producto(
    cfg: PricingConfig,
    nombre_producto: str,
    tipo_superficie: str,
    medidas_texto: str,
    espesor: float,
) -> str:
    tipos = {"LISA": "TIPO LISA", "RANURADA": "TIPO RANURADA", "ESCALERILLA": "TIPO ESCALERILLA"}
    tipo_texto = tipos.get(tipo_superficie, "TIPO LISA")
    return f"{cfg.tipo_galvanizado} - {nombre_producto} {tipo_texto} {medidas_texto} {espesor:.1f}MM (C/UNION)"


def generar_descripcion_caja_pase(
    tipo_galvanizado: str,
    medidas_texto: str,
    tipo_salida: str,
    espesor: float,
) -> str:
    if tipo_salida.upper() == "CIEGA":
        return f'{tipo_galvanizado} - CAJA DE PASE {medidas_texto} {tipo_salida} {espesor:.1f}MM'
    else:
        return f'{tipo_galvanizado} - CAJA DE PASE {medidas_texto} C/S {tipo_salida}" {espesor:.1f}MM'


# ─────────────────────────────────────────────
# Funciones de cotización (thread-safe)
# ─────────────────────────────────────────────

def cotizar_bandeja(
    cfg: PricingConfig,
    precio_pl_producto: float,
    precio_pl_tapa: float,
    espesor_producto: float,
    espesor_tapa: float,
    ancho: float,
    alto: float,
    tipo_superficie: str = "LISA",
    es_metro_lineal: bool = False,
) -> List[Dict[str, Any]]:
    pl_ancho_mm = 2400
    pl_undmm2_p = precio_pl_producto / PL_MM2
    pl_undmm2_t = precio_pl_tapa / PL_MM2

    area = (ancho + alto * 2) * pl_ancho_mm
    precio = calcular_precio(area, pl_undmm2_p)
    peso = calcular_peso(area, espesor_producto)

    area_u = (ancho + alto * 2) * 100
    precio_u = calcular_precio(area_u, pl_undmm2_p)
    peso_u = calcular_peso(area_u, espesor_producto)

    precio_total = aplicar_precio_escalerilla(precio + precio_u, tipo_superficie)
    precio_final, peso_final = calcular_precio_final(cfg, precio_total, peso + peso_u, "B")

    if es_metro_lineal:
        precio_final /= 2.4
        peso_final /= 2.4

    medidas = f"{ancho:.0f}X{alto:.0f}X{pl_ancho_mm}MM"
    desc = generar_descripcion_producto(cfg, "BANDEJA", tipo_superficie, medidas, espesor_producto)
    if es_metro_lineal:
        desc += " - POR ML"

    # Tapa
    area_t = (ancho + 2.5 * 2 * 10) * pl_ancho_mm
    precio_t = calcular_precio(area_t, pl_undmm2_t)
    peso_t = calcular_peso(area_t, espesor_tapa)
    precio_tf, peso_tf = calcular_precio_final(cfg, precio_t, peso_t, "B")
    if es_metro_lineal:
        precio_tf /= 2.4
        peso_tf /= 2.4

    desc_t = f"{cfg.tipo_galvanizado} - TAPA BANDEJA {ancho:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"
    if es_metro_lineal:
        desc_t += " - POR ML"

    return [
        {"tipo": "B", "descripcion": desc, "precio_unitario": precio_final, "peso_unitario": peso_final},
        {"tipo": "B", "descripcion": desc_t, "precio_unitario": precio_tf, "peso_unitario": peso_tf},
    ]


def cotizar_curva_horizontal(
    cfg: PricingConfig,
    precio_pl_producto: float,
    precio_pl_tapa: float,
    espesor_producto: float,
    espesor_tapa: float,
    ancho: float,
    alto: float,
    tipo_superficie: str = "LISA",
) -> List[Dict[str, Any]]:
    pl_undmm2_p = precio_pl_producto / PL_MM2
    pl_undmm2_t = precio_pl_tapa / PL_MM2

    area = (ancho + 250) ** 2
    precio = calcular_precio(area, pl_undmm2_p)
    peso = calcular_peso(area, espesor_producto)

    area_lv = (
        (ancho * 0.414 + 100) * 2
        + ((ancho + 250) - (ancho * 0.414 + 100)) * math.sqrt(2)
    ) * (alto + 15)
    precio_lv = calcular_precio(area_lv, pl_undmm2_p)
    peso_lv = calcular_peso(area_lv, espesor_producto)

    area_lp = 412.13 * (alto + 15)
    precio_lp = calcular_precio(area_lp, pl_undmm2_p)
    peso_lp = calcular_peso(area_lp, espesor_producto)

    peso_curva = peso + peso_lv + peso_lp
    precio_curva = precio + precio_lv + precio_lp

    area_u = (ancho + alto * 2) * 100
    precio_u = calcular_precio(area_u, pl_undmm2_p)
    peso_u = calcular_peso(area_u, espesor_producto)

    precio_total = aplicar_precio_escalerilla(precio_curva + precio_u, tipo_superficie)
    precio_final, peso_final = calcular_precio_final(cfg, precio_total, peso_curva + peso_u, "CH")

    medidas = f"{ancho:.0f}X{alto:.0f}MM"
    desc = generar_descripcion_producto(cfg, "CURVA HORIZONTAL", tipo_superficie, medidas, espesor_producto)

    # Tapa
    area_t = ((ancho + 250) + 2) ** 2
    precio_t = calcular_precio(area_t, pl_undmm2_t)
    peso_t = calcular_peso(area_t, espesor_tapa)
    precio_tf, peso_tf = calcular_precio_final(cfg, precio_t, peso_t, "CH")
    desc_t = f"{cfg.tipo_galvanizado} - TAPA CURVA HORIZONTAL {ancho:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"

    return [
        {"tipo": "CH", "descripcion": desc, "precio_unitario": precio_final, "peso_unitario": peso_final},
        {"tipo": "CH", "descripcion": desc_t, "precio_unitario": precio_tf, "peso_unitario": peso_tf},
    ]


def cotizar_curva_vertical(
    cfg: PricingConfig,
    precio_pl_producto: float,
    precio_pl_tapa: float,
    espesor_producto: float,
    espesor_tapa: float,
    ancho: float,
    alto: float,
    tipo_curva: str = "EXTERNA",
    tipo_superficie: str = "LISA",
) -> List[Dict[str, Any]]:
    pl_undmm2_p = precio_pl_producto / PL_MM2
    pl_undmm2_t = precio_pl_tapa / PL_MM2
    codigo = "CVE" if tipo_curva == "EXTERNA" else "CVI"

    if tipo_curva == "EXTERNA":
        area = (ancho + 30) * 413
        area_lateral = 350 ** 2
        area_tapa_calc = (ancho + 40) * 577
    else:
        area = (ancho + 40) * 577
        area_lateral = 350 ** 2
        area_tapa_calc = (ancho + 30) * 413

    precio = calcular_precio(area, pl_undmm2_p)
    peso = calcular_peso(area, espesor_producto)
    precio_lat = calcular_precio(area_lateral, pl_undmm2_p) * 2
    peso_lat = calcular_peso(area_lateral, espesor_producto) * 2

    peso_curva = peso + peso_lat
    precio_curva = precio + precio_lat

    area_u = (ancho + alto * 2) * 100
    precio_u = calcular_precio(area_u, pl_undmm2_p)
    peso_u = calcular_peso(area_u, espesor_producto)

    precio_total = aplicar_precio_escalerilla(precio_curva + precio_u, tipo_superficie)
    precio_final, peso_final = calcular_precio_final(cfg, precio_total, peso_curva + peso_u, codigo)

    medidas = f"{ancho:.0f}X{alto:.0f}MM"
    desc = generar_descripcion_producto(
        cfg, f"CURVA VERTICAL {tipo_curva}", tipo_superficie, medidas, espesor_producto
    )

    # Tapa
    precio_t = calcular_precio(area_tapa_calc, pl_undmm2_t)
    peso_t = calcular_peso(area_tapa_calc, espesor_tapa)
    precio_tf, peso_tf = calcular_precio_final(cfg, precio_t, peso_t, codigo)
    desc_t = f"{cfg.tipo_galvanizado} - TAPA CURVA VERTICAL {tipo_curva} {ancho:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"

    return [
        {"tipo": codigo, "descripcion": desc, "precio_unitario": precio_final, "peso_unitario": peso_final},
        {"tipo": codigo, "descripcion": desc_t, "precio_unitario": precio_tf, "peso_unitario": peso_tf},
    ]


def cotizar_tee(
    cfg: PricingConfig,
    precio_pl_producto: float,
    precio_pl_tapa: float,
    espesor_producto: float,
    espesor_tapa: float,
    derecha: float,
    izquierda: float,
    abajo: float,
    alto: float,
    tipo_superficie: str = "LISA",
) -> List[Dict[str, Any]]:
    pl_undmm2_p = precio_pl_producto / PL_MM2
    pl_undmm2_t = precio_pl_tapa / PL_MM2

    x_tee = 2 * 250 + abajo
    y_tee = derecha + alto + 250
    area_tee = x_tee * y_tee
    precio_tee = calcular_precio(area_tee, pl_undmm2_p)
    peso_tee = calcular_peso(area_tee, espesor_producto)

    area_lp = 412.13 * (alto + 15)
    precio_lp = calcular_precio(area_lp, pl_undmm2_p)
    peso_lp = calcular_peso(area_lp, espesor_producto)

    d = (derecha + 250) - izquierda
    lv_len = math.sqrt(150 ** 2 + (d - 100) ** 2)
    area_lv = (200 + lv_len) * (alto + 15)
    precio_lv = calcular_precio(area_lv, pl_undmm2_p)
    peso_lv = calcular_peso(area_lv, espesor_producto)

    peso_total = peso_tee + peso_lp + peso_lv
    precio_total_base = precio_tee + precio_lp + precio_lv

    area_u = (derecha + alto * 2) * 100
    precio_u = calcular_precio(area_u, pl_undmm2_p) * 2
    peso_u = calcular_peso(area_u, espesor_producto) * 2

    precio_esc = aplicar_precio_escalerilla(precio_total_base + precio_u, tipo_superficie)
    precio_final, peso_final = calcular_precio_final(cfg, precio_esc, peso_total + peso_u, "T")

    medidas = f"{derecha:.0f}X{izquierda:.0f}X{abajo:.0f}X{alto:.0f}MM"
    desc = generar_descripcion_producto(cfg, "TEE", tipo_superficie, medidas, espesor_producto)

    # Tapa
    precio_t = calcular_precio((2 * 250 + abajo) * (derecha + 252), pl_undmm2_t)
    peso_t = calcular_peso((2 * 250 + abajo) * (derecha + 252), espesor_tapa)
    precio_tf, peso_tf = calcular_precio_final(cfg, precio_t, peso_t, "T")
    desc_t = f"{cfg.tipo_galvanizado} - TAPA TEE {derecha:.0f}X{izquierda:.0f}X{abajo:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"

    return [
        {"tipo": "T", "descripcion": desc, "precio_unitario": precio_final, "peso_unitario": peso_final},
        {"tipo": "T", "descripcion": desc_t, "precio_unitario": precio_tf, "peso_unitario": peso_tf},
    ]


def cotizar_cruz(
    cfg: PricingConfig,
    precio_pl_producto: float,
    precio_pl_tapa: float,
    espesor_producto: float,
    espesor_tapa: float,
    ancho: float,
    alto: float,
    tipo_superficie: str = "LISA",
) -> List[Dict[str, Any]]:
    pl_undmm2_p = precio_pl_producto / PL_MM2
    pl_undmm2_t = precio_pl_tapa / PL_MM2

    area = (ancho + 500) ** 2
    precio = calcular_precio(area, pl_undmm2_p)
    peso = calcular_peso(area, espesor_producto)

    area_lp = 412.13 * (alto + 15)
    precio_lp = calcular_precio(area_lp, pl_undmm2_p)
    peso_lp = calcular_peso(area_lp, espesor_producto)

    peso_cruz = peso + peso_lp * 4
    precio_cruz = precio + precio_lp * 4

    area_u = (ancho + alto * 2) * 100
    precio_u = calcular_precio(area_u, pl_undmm2_p) * 3
    peso_u = calcular_peso(area_u, espesor_producto) * 3

    precio_esc = aplicar_precio_escalerilla(precio_cruz + precio_u, tipo_superficie)
    precio_final, peso_final = calcular_precio_final(cfg, precio_esc, peso_cruz + peso_u, "C")

    medidas = f"{ancho:.0f}X{alto:.0f}MM"
    desc = generar_descripcion_producto(cfg, "CRUZ", tipo_superficie, medidas, espesor_producto)

    # Tapa
    area_t = (ancho + 500) ** 2
    precio_t = calcular_precio(area_t, pl_undmm2_t)
    peso_t = calcular_peso(area_t, espesor_tapa)
    precio_tf, peso_tf = calcular_precio_final(cfg, precio_t, peso_t, "C")
    desc_t = f"{cfg.tipo_galvanizado} - TAPA CRUZ {ancho:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"

    return [
        {"tipo": "C", "descripcion": desc, "precio_unitario": precio_final, "peso_unitario": peso_final},
        {"tipo": "C", "descripcion": desc_t, "precio_unitario": precio_tf, "peso_unitario": peso_tf},
    ]


def cotizar_reduccion(
    cfg: PricingConfig,
    precio_pl_producto: float,
    precio_pl_tapa: float,
    espesor_producto: float,
    espesor_tapa: float,
    ancho_mayor: float,
    alto: float,
    ancho_menor: float,
    tipo_superficie: str = "LISA",
) -> List[Dict[str, Any]]:
    pl_undmm2_p = precio_pl_producto / PL_MM2
    pl_undmm2_t = precio_pl_tapa / PL_MM2

    area_r = ancho_mayor * 413
    precio_r = calcular_precio(area_r, pl_undmm2_p)
    peso_r = calcular_peso(area_r, espesor_producto)

    p = (ancho_mayor - ancho_menor) / 2
    h = math.sqrt(p ** 2 + 212 ** 2)
    tot = (200 + h) * (alto + 12)
    precio_rl = calcular_precio(tot, pl_undmm2_p) * 2
    peso_rl = calcular_peso(tot, espesor_producto) * 2

    peso_total = peso_r + peso_rl
    precio_total_base = precio_r + precio_rl

    area_u = (ancho_mayor + alto * 2) * 100
    precio_u = calcular_precio(area_u, pl_undmm2_p)
    peso_u = calcular_peso(area_u, espesor_producto)

    precio_esc = aplicar_precio_escalerilla(precio_total_base + precio_u, tipo_superficie)
    precio_final, peso_final = calcular_precio_final(cfg, precio_esc, peso_total + peso_u, "R")

    medidas = f"{ancho_mayor:.0f}X{alto:.0f} a {ancho_menor:.0f}X{alto:.0f}MM"
    desc = generar_descripcion_producto(cfg, "REDUCCION", tipo_superficie, medidas, espesor_producto)

    # Tapa
    area_t = (ancho_mayor + 4) * 413
    precio_t = calcular_precio(area_t, pl_undmm2_t)
    peso_t = calcular_peso(area_t, espesor_tapa)
    precio_tf, peso_tf = calcular_precio_final(cfg, precio_t, peso_t, "R")
    desc_t = f"{cfg.tipo_galvanizado} - TAPA REDUCCION {ancho_mayor:.0f}X{alto:.0f} a {ancho_menor:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"

    return [
        {"tipo": "R", "descripcion": desc, "precio_unitario": precio_final, "peso_unitario": peso_final},
        {"tipo": "R", "descripcion": desc_t, "precio_unitario": precio_tf, "peso_unitario": peso_tf},
    ]


def cotizar_caja_pase(
    cfg: PricingConfig,
    precio_pl_producto: float,
    precio_pl_tapa: float,
    espesor_producto: float,
    espesor_tapa: float,
    dim1: float,
    dim2: float,
    dim3: float,
    tipo_salida: str,
) -> List[Dict[str, Any]]:
    # Para cajas de pase GC se usa usd_kg_cajas (configurable, por defecto 3.0 USD/kg)
    cfg_caja = PricingConfig(
        tipo_galvanizado=cfg.tipo_galvanizado,
        dolar=cfg.dolar,
        precio_galvanizado_kg=cfg.usd_kg_cajas if cfg.tipo_galvanizado == "GC" else cfg.precio_galvanizado_kg,
        porcentaje_ganancia=cfg.porcentaje_ganancia,
        usd_kg_cajas=cfg.usd_kg_cajas,
    )

    # Estandarizar: mayor→ancho, intermedia→largo, menor→alto
    dims = sorted([dim1, dim2, dim3], reverse=True)
    ancho, largo, alto = dims

    pl_undmm2_p = precio_pl_producto / PL_MM2
    pl_undmm2_t = precio_pl_tapa / PL_MM2

    ancho_mm = ancho * 10
    largo_mm = largo * 10
    alto_mm = alto * 10

    # El cuerpo es una U: pared izq + fondo + pared der, sheet width = largo
    area_cuerpo = ((alto_mm * 2 + ancho_mm) + 20) * largo_mm
    precio_cuerpo = calcular_precio(area_cuerpo, pl_undmm2_p)
    peso_cuerpo = calcular_peso(area_cuerpo, espesor_producto)

    area_cabecera = (alto_mm + 20) * (ancho_mm + 20) * 2
    precio_cabecera = calcular_precio(area_cabecera, pl_undmm2_p)
    peso_cabecera = calcular_peso(area_cabecera, espesor_producto)

    area_tapa = largo_mm * ancho_mm
    precio_tapa_calc = calcular_precio(area_tapa, pl_undmm2_t)
    peso_tapa_calc = calcular_peso(area_tapa, espesor_tapa)

    precio_costo = precio_cuerpo + precio_cabecera + precio_tapa_calc
    precio_venta = precio_costo * 2
    peso_total = peso_cuerpo + peso_cabecera + peso_tapa_calc

    precio_con_galv = aplicar_costo_galvanizado(cfg_caja, precio_venta, peso_total)

    if cfg.porcentaje_ganancia == "30":
        precio_final = precio_con_galv * 1.01
    elif cfg.porcentaje_ganancia == "35":
        precio_final = (precio_con_galv * 1.01) / 0.95
    else:
        precio_final = precio_con_galv / cfg.factor_ganancia

    def fmt(v: float) -> str:
        return str(int(v)) if v == int(v) else f"{v:.1f}"

    medidas = f"{fmt(ancho_mm)}X{fmt(largo_mm)}X{fmt(alto_mm)}MM"
    desc = generar_descripcion_caja_pase(cfg.tipo_galvanizado, medidas, tipo_salida, espesor_producto)

    return [
        {"tipo": "CP", "descripcion": desc, "precio_unitario": precio_final, "peso_unitario": peso_total},
    ]
