"""
guillotine.py — Algoritmo de corte guillotina (multi-plancha)

Heurística: Best Short Side Fit (BSSF) + Split Longer Axis + rotación 90°.
Multi-plancha: si una pieza no cabe en ninguna plancha existente, se abre una nueva.
"""
from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────
# Dataclasses de entrada
# ─────────────────────────────────────────────

@dataclass
class Pieza:
    ancho: float
    alto: float
    cantidad: int
    nombre: str
    color: str = "#4fffb0"


# ─────────────────────────────────────────────
# Dataclasses de salida
# ─────────────────────────────────────────────

@dataclass
class PiezaColocada:
    ancho_original: float
    alto_original: float
    x: float
    y: float
    ancho_colocado: float
    alto_colocado: float
    rotada: bool
    nombre: str
    color: str
    plancha_idx: int


@dataclass
class Corte:
    tipo: str        # "H" (horizontal) o "V" (vertical)
    posicion: float  # coordenada del corte (y para H, x para V)
    desde: float     # inicio del segmento de corte
    hasta: float     # fin del segmento de corte
    plancha_idx: int


@dataclass
class ResultadoPlancha:
    idx: int
    piezas: List[PiezaColocada]
    cortes: List[Corte]
    area_usada: float
    area_total: float
    utilizacion: float  # 0.0–1.0


@dataclass
class ResultadoPacking:
    planchas: List[ResultadoPlancha]
    total_colocadas: int
    total_solicitadas: int
    no_colocadas: List[dict]  # [{"nombre": ..., "ancho": ..., "alto": ...}]


# ─────────────────────────────────────────────
# Algoritmo guillotina
# ─────────────────────────────────────────────

def _bssf_score(rect: dict, ew: float, eh: float) -> float:
    """Best Short Side Fit: menor valor = mejor ajuste."""
    return min(rect["w"] - ew, rect["h"] - eh)


def _find_best_rect(free_rects: list, pw: float, ph: float, sp: float):
    """Busca el mejor rectángulo libre para la pieza con tamaño pw×ph y espaciado sp.
    Retorna (rect, rotated) o (None, False)."""
    best_score = float("inf")
    best_rect = None
    best_rotated = False

    for rect in free_rects:
        # Sin rotación
        ew, eh = pw + sp, ph + sp
        if ew <= rect["w"] and eh <= rect["h"]:
            s = _bssf_score(rect, ew, eh)
            if s < best_score:
                best_score, best_rect, best_rotated = s, rect, False
        # Rotado 90°
        ew2, eh2 = ph + sp, pw + sp
        if ew2 != ew or eh2 != eh:  # solo si diferente (no cuadrado)
            if ew2 <= rect["w"] and eh2 <= rect["h"]:
                s = _bssf_score(rect, ew2, eh2)
                if s < best_score:
                    best_score, best_rect, best_rotated = s, rect, True

    return best_rect, best_rotated


def _place(bin_data: dict, rect: dict, pw: float, ph: float,
           rotated: bool, sp: float, nombre: str, color: str, plancha_idx: int):
    """Coloca la pieza en el rectángulo libre y divide el espacio restante (SLA)."""
    placed_w = ph if rotated else pw
    placed_h = pw if rotated else ph
    ew, eh = placed_w + sp, placed_h + sp

    bin_data["placed"].append({
        "x": rect["x"],
        "y": rect["y"],
        "ancho_colocado": placed_w,
        "alto_colocado": placed_h,
        "ancho_original": pw,
        "alto_original": ph,
        "rotada": rotated,
        "nombre": nombre,
        "color": color,
    })

    right_w = rect["w"] - ew
    bottom_h = rect["h"] - eh

    # Remover rect usado
    bin_data["free_rects"].remove(rect)

    # Split Longer Axis
    if right_w >= bottom_h:
        # Tira vertical (derecha) recibe la altura completa
        if right_w > 0:
            bin_data["free_rects"].append({
                "x": rect["x"] + ew, "y": rect["y"], "w": right_w, "h": rect["h"]
            })
            bin_data["cortes"].append({
                "tipo": "V", "posicion": rect["x"] + ew,
                "desde": rect["y"], "hasta": rect["y"] + rect["h"],
                "plancha_idx": plancha_idx,
            })
        # Tira horizontal (abajo) limitada a la tira izquierda
        if bottom_h > 0:
            bin_data["free_rects"].append({
                "x": rect["x"], "y": rect["y"] + eh, "w": ew, "h": bottom_h
            })
            bin_data["cortes"].append({
                "tipo": "H", "posicion": rect["y"] + eh,
                "desde": rect["x"], "hasta": rect["x"] + ew,
                "plancha_idx": plancha_idx,
            })
    else:
        # Tira horizontal (abajo) recibe el ancho completo
        if bottom_h > 0:
            bin_data["free_rects"].append({
                "x": rect["x"], "y": rect["y"] + eh, "w": rect["w"], "h": bottom_h
            })
            bin_data["cortes"].append({
                "tipo": "H", "posicion": rect["y"] + eh,
                "desde": rect["x"], "hasta": rect["x"] + rect["w"],
                "plancha_idx": plancha_idx,
            })
        # Tira vertical (derecha) limitada a la tira superior
        if right_w > 0:
            bin_data["free_rects"].append({
                "x": rect["x"] + ew, "y": rect["y"], "w": right_w, "h": eh
            })
            bin_data["cortes"].append({
                "tipo": "V", "posicion": rect["x"] + ew,
                "desde": rect["y"], "hasta": rect["y"] + eh,
                "plancha_idx": plancha_idx,
            })


def guillotine_pack(
    ancho_plancha: float,
    alto_plancha: float,
    piezas: List[Pieza],
    espaciado: float = 4.0,
) -> ResultadoPacking:
    """
    Empaqueta las piezas en una o más planchas usando el algoritmo guillotina.
    Heurística: BSSF + SLA + rotación 90°.
    """
    total_solicitadas = sum(p.cantidad for p in piezas)

    # Expandir por cantidad y ordenar por área descendente
    items = []
    for p in piezas:
        for _ in range(p.cantidad):
            items.append({
                "ancho": p.ancho, "alto": p.alto,
                "nombre": p.nombre, "color": p.color,
            })
    items.sort(key=lambda x: x["ancho"] * x["alto"], reverse=True)

    no_colocadas: List[dict] = []
    colocables = []

    for item in items:
        w, h, sp = item["ancho"], item["alto"], espaciado
        fits = (w + sp <= ancho_plancha and h + sp <= alto_plancha) or \
               (h + sp <= ancho_plancha and w + sp <= alto_plancha)
        if fits:
            colocables.append(item)
        else:
            no_colocadas.append({"nombre": item["nombre"], "ancho": w, "alto": h})

    bins: List[dict] = []

    def _new_bin():
        return {
            "free_rects": [{"x": 0, "y": 0, "w": ancho_plancha, "h": alto_plancha}],
            "placed": [],
            "cortes": [],
        }

    for item in colocables:
        pw, ph = item["ancho"], item["alto"]
        placed = False

        for b_idx, bd in enumerate(bins):
            rect, rotated = _find_best_rect(bd["free_rects"], pw, ph, espaciado)
            if rect is not None:
                _place(bd, rect, pw, ph, rotated, espaciado,
                       item["nombre"], item["color"], b_idx)
                placed = True
                break

        if not placed:
            bd = _new_bin()
            bins.append(bd)
            b_idx = len(bins) - 1
            rect, rotated = _find_best_rect(bd["free_rects"], pw, ph, espaciado)
            if rect is not None:
                _place(bd, rect, pw, ph, rotated, espaciado,
                       item["nombre"], item["color"], b_idx)

    # Construir resultados
    area_total = ancho_plancha * alto_plancha
    planchas: List[ResultadoPlancha] = []
    total_colocadas = 0

    for i, bd in enumerate(bins):
        area_usada = sum(p["ancho_colocado"] * p["alto_colocado"] for p in bd["placed"])
        utilizacion = area_usada / area_total if area_total > 0 else 0.0

        piezas_colocadas = [
            PiezaColocada(
                ancho_original=p["ancho_original"],
                alto_original=p["alto_original"],
                x=p["x"], y=p["y"],
                ancho_colocado=p["ancho_colocado"],
                alto_colocado=p["alto_colocado"],
                rotada=p["rotada"],
                nombre=p["nombre"], color=p["color"],
                plancha_idx=i,
            )
            for p in bd["placed"]
        ]

        cortes = [
            Corte(
                tipo=c["tipo"], posicion=c["posicion"],
                desde=c["desde"], hasta=c["hasta"],
                plancha_idx=i,
            )
            for c in bd["cortes"]
        ]

        total_colocadas += len(piezas_colocadas)
        planchas.append(ResultadoPlancha(
            idx=i,
            piezas=piezas_colocadas,
            cortes=cortes,
            area_usada=area_usada,
            area_total=area_total,
            utilizacion=round(utilizacion, 4),
        ))

    return ResultadoPacking(
        planchas=planchas,
        total_colocadas=total_colocadas,
        total_solicitadas=total_solicitadas,
        no_colocadas=no_colocadas,
    )
