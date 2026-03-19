"""
config.py — Persistencia de reglas especiales por empleado.
Almacena en asistencias/data/excepciones.json
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
EXCEPCIONES_PATH = DATA_DIR / "excepciones.json"


def cargar_excepciones() -> list:
    """Devuelve lista de dicts {id, nombre} con empleados sin sábados."""
    if EXCEPCIONES_PATH.exists():
        data = json.loads(EXCEPCIONES_PATH.read_text(encoding="utf-8"))
        return data.get("sin_sabados", [])
    return []


def ids_sin_sabados() -> set:
    """Devuelve set de IDs (strings) de empleados que ignoran sábados."""
    return {str(e["id"]) for e in cargar_excepciones()}


def toggle_excepcion(emp_id: str, nombre: str) -> bool:
    """
    Alterna la excepción del empleado.
    Devuelve True si fue agregado, False si fue eliminado.
    """
    excepciones = cargar_excepciones()
    ids = {str(e["id"]) for e in excepciones}

    if emp_id in ids:
        excepciones = [e for e in excepciones if str(e["id"]) != emp_id]
        added = False
    else:
        excepciones.append({"id": emp_id, "nombre": nombre})
        added = True

    DATA_DIR.mkdir(exist_ok=True)
    EXCEPCIONES_PATH.write_text(
        json.dumps({"sin_sabados": excepciones}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return added
