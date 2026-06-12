# -*- coding: utf-8 -*-
"""Config de precios: cargar/guardar cotizador_config.json (con cache) — extraído de web/database.py (refactor jun 2026)."""
import hashlib
import json
import os
import re as _re
import secrets
import shutil
import sqlite3
from datetime import datetime as _dt
from pathlib import Path
from typing import Optional, Dict, List, Any

import bcrypt as _bcrypt

from web.db.core import (
    BASE_DIR, DB_PATH, CONFIG_PATH, _CONFIG_RAIZ, CONFIG_DEFECTO,
    _add_column_if_missing, _crear_usuario, _hash_password,
)

# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

# Cache en memoria del config: evita leer el JSON del disco en cada request.
# Se invalida explícitamente en guardar_config(). Se devuelve siempre una copia
# profunda para que los callers puedan mutar el dict sin corromper el cache.
_config_cache: Optional[Dict] = None


def cargar_config() -> Dict:
    """Carga configuración desde cotizador_config.json, mergeando con defaults."""
    global _config_cache
    import copy
    if _config_cache is not None:
        return copy.deepcopy(_config_cache)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            resultado = _fusionar(CONFIG_DEFECTO, cfg)
            # Migración: corregir espesor_tapa si quedó en el valor antiguo por defecto
            vd = resultado.get("valores_defecto", {})
            if vd.get("espesor_tapa") == "1.2" and cfg.get("valores_defecto", {}).get("espesor_tapa") == "1.2":
                vd["espesor_tapa"] = "1.5"
                guardar_config(resultado)
            _config_cache = copy.deepcopy(resultado)
            return resultado
        except Exception:
            pass
    return dict(CONFIG_DEFECTO)


def guardar_config(config: Dict) -> bool:
    """Guarda configuración en cotizador_config.json."""
    global _config_cache
    try:
        backup = CONFIG_PATH.parent / "cotizador_config_backup.json"
        if CONFIG_PATH.exists():
            import shutil
            shutil.copy2(CONFIG_PATH, backup)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        _config_cache = None
        return True
    except Exception:
        _config_cache = None
        return False


def _fusionar(defecto: Dict, cargada: Dict) -> Dict:
    resultado = {**defecto}
    for k, v in cargada.items():
        if k in resultado and isinstance(v, dict):
            resultado[k] = {**resultado[k], **v}
        else:
            resultado[k] = v
    return resultado

