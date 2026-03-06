"""
auth.py — Autenticación con sesiones firmadas (itsdangerous)

Usa cookies HTTP-only con tokens firmados HMAC.
No requiere base de datos de sesiones: el token ES la sesión.
"""
import json
import os
import secrets as _sec
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from web.database import verificar_usuario

load_dotenv()
# Clave secreta — se lee desde AROLUZ_SECRET_KEY en .env (producción)
# Si no está definida, se genera una clave aleatoria (dev — sesiones no persisten entre reinicios)
SECRET_KEY = os.environ.get("AROLUZ_SECRET_KEY") or _sec.token_hex(32)
COOKIE_NAME = "aroluz_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 días en segundos

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def crear_token(username: str, nombre: str = "", rol: str = "USER", ver_asistencias: bool = False) -> str:
    """Crea un token firmado con datos del usuario."""
    payload = {"u": username, "n": nombre, "r": rol, "va": ver_asistencias}
    return _serializer.dumps(payload, salt="login")


def verificar_token(token: str) -> Optional[dict]:
    """
    Verifica y decodifica el token.
    Retorna el payload o None si es inválido/expirado.
    """
    try:
        payload = _serializer.loads(token, salt="login", max_age=SESSION_MAX_AGE)
        return payload
    except (BadSignature, SignatureExpired):
        return None


def get_session(request: Request) -> Optional[dict]:
    """Extrae y valida el usuario de la cookie de sesión."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return verificar_token(token)


def require_login(request: Request) -> dict:
    """
    Dependency de FastAPI — redirige al login si no hay sesión válida.
    Uso: usuario = Depends(require_login)
    """
    session = get_session(request)
    if not session:
        # Almacenar URL original en query param para redirigir después del login
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return session


def set_session_cookie(response: RedirectResponse, username: str, nombre: str = "", rol: str = "USER", ver_asistencias: bool = False):
    """Establece la cookie de sesión en la respuesta."""
    token = crear_token(username, nombre, rol, ver_asistencias)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=SESSION_MAX_AGE,
        samesite="lax",
    )


def require_admin(request: Request) -> dict:
    """
    Dependency de FastAPI — redirige si no hay sesión o el usuario no es ADMIN.
    Para rutas que solo deben ser accesibles por administradores.
    """
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if session.get("r") != "ADMIN":
        raise HTTPException(status_code=303, headers={"Location": "/cotizar?msg=nopermiso"})
    return session


def require_asistencias(request: Request) -> dict:
    """
    Dependency de FastAPI — permite acceso a ADMIN o usuarios con ver_asistencias=True.
    """
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if not (session.get("r") == "ADMIN" or session.get("va")):
        raise HTTPException(status_code=303, headers={"Location": "/cotizar?msg=nopermiso"})
    return session


def clear_session_cookie(response: RedirectResponse):
    """Elimina la cookie de sesión."""
    response.delete_cookie(key=COOKIE_NAME)
