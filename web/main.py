"""
main.py — Aplicación FastAPI principal de AROLUZ Cotizador Web

Solo arma la app: middleware, estáticos y routers. Las rutas viven en web/rutas/:
  paginas.py       páginas HTML (login, home, cotizar, carrito, historial, etc.)
  proyectos.py     API kanban: estado, adjuntos, OC items
  config_admin.py  configuración ADMIN: precios, catálogo, clientes, usuarios
  cotizar/carrito/exportar/historial/planchas/importar_pdf/email_imap.py  APIs
"""
import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en el path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from web.limits import limiter
from web.rutas import cotizar as rutas_cotizar
from web.rutas import carrito as rutas_carrito
from web.rutas import exportar as rutas_exportar
from web.rutas import historial as rutas_historial
from web.rutas import planchas as rutas_planchas
from web.rutas import importar_pdf as rutas_importar_pdf
from web.rutas import email_imap as rutas_email_imap
from web.rutas import paginas as rutas_paginas
from web.rutas import proyectos as rutas_proyectos
from web.rutas import config_admin as rutas_config_admin
from web.asistencias.router import router as asistencias_router

# ─────────────────────────────────────────────
# Configurar app
# ─────────────────────────────────────────────

app = FastAPI(
    title="AROLUZ Cotizador Web",
    description="Cotizador de bandejas porta cables AROLUZ",
    version="2.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as _SRequest
from starlette.responses import Response as _SResponse

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: _SRequest, call_next):
        response: _SResponse = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "worker-src blob: https://cdnjs.cloudflare.com; "
            "connect-src 'self' https://nominatim.openstreetmap.org;"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Archivos estáticos (templates/ctx viven en web/plantillas.py)
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Incluir routers
app.include_router(rutas_paginas.router)
app.include_router(rutas_proyectos.router)
app.include_router(rutas_config_admin.router)
app.include_router(rutas_cotizar.router)
app.include_router(rutas_carrito.router)
app.include_router(rutas_exportar.router)
app.include_router(rutas_historial.router)
app.include_router(rutas_planchas.router)
app.include_router(rutas_importar_pdf.router)
app.include_router(rutas_email_imap.router, prefix="/api/email")
app.include_router(asistencias_router, prefix="/asistencias")


# ─────────────────────────────────────────────
# Manejo de errores de autenticación
# ─────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 303 and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=303)
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="AROLUZ Cotizador Web")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload en desarrollo")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  AROLUZ Cotizador Web v2.0")
    print(f"  URL: http://localhost:{args.port}")
    print(f"  Red local: http://0.0.0.0:{args.port}")
    print(f"{'='*50}\n")

    uvicorn.run(
        "web.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
