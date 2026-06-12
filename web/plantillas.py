# -*- coding: utf-8 -*-
"""Jinja2 compartido entre main.py y los routers HTML: templates, ctx() y permisos."""
import json as _json
from pathlib import Path
from urllib.parse import quote as _url_quote

from fastapi import Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup as _Markup

from web.rutas.carrito import get_carrito

TEMPLATES_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["urlencode_str"] = lambda s: _url_quote(str(s), safe="")
templates.env.filters.setdefault("tojson", lambda o: _Markup(_json.dumps(o, ensure_ascii=False)))


def ctx(request: Request, usuario: dict, **kwargs) -> dict:
    """Contexto base para todos los templates."""
    carrito = get_carrito(usuario["u"])
    total_carrito = sum(i["precio_unitario"] * i["cantidad"] for i in carrito)
    return {
        "request": request,
        "usuario": usuario,
        "n_carrito": len(carrito),
        "total_carrito": round(total_carrito, 2),
        **kwargs,
    }


def _permiso_usuario(usuario: dict, permiso: str, config: dict) -> bool:
    """ADMIN siempre puede. USER requiere que el permiso esté habilitado en config."""
    if usuario.get("r") == "ADMIN":
        return True
    return config.get("permisos_usuario", {}).get(permiso, True)
