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


class _Jinja2TemplatesCompat(Jinja2Templates):
    """Jinja2Templates con compatibilidad para la firma antigua de TemplateResponse.

    Starlette <0.36 aceptaba: TemplateResponse("nombre.html", {"request": req, ...})
    Starlette ≥1.0  requiere: TemplateResponse(req, "nombre.html", {...})

    Esta subclase detecta el estilo de la llamada y normaliza a la nueva firma.
    """

    def TemplateResponse(self, name_or_request, context_or_name=None, context=None, **kw):  # type: ignore[override]
        if isinstance(name_or_request, str):
            # Firma antigua: TemplateResponse("plantilla.html", {"request": req, ...})
            name = name_or_request
            ctx: dict = dict(context_or_name) if isinstance(context_or_name, dict) else {}
            req = ctx.pop("request", None)
            return super().TemplateResponse(req, name, ctx, **kw)
        # Firma nueva: TemplateResponse(req, "plantilla.html", {...})
        return super().TemplateResponse(name_or_request, context_or_name, context, **kw)


templates = _Jinja2TemplatesCompat(directory=str(TEMPLATES_DIR))
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
