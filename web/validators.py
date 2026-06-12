"""Validaciones compartidas entre rutas."""
import re
from typing import Optional


def validar_ruc(ruc: str) -> Optional[str]:
    """Valida un RUC peruano opcional. Devuelve None si es válido (o vacío),
    o el mensaje de error si no lo es."""
    if ruc and not re.fullmatch(r"\d{11}", ruc):
        return "El RUC debe tener exactamente 11 dígitos numéricos"
    return None
