"""Rate limiter compartido (slowapi).

Instancia única importable desde main.py y los routers sin import circular.
Los endpoints decorados con @limiter.limit() deben aceptar `request: Request`.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
