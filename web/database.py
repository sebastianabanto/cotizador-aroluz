# -*- coding: utf-8 -*-
"""
database.py — Fachada retrocompatible sobre el paquete web/db/.

El código real vive en web/db/ (refactor jun 2026):
  core.py        init_db, migraciones, backups, paths, CONFIG_DEFECTO
  usuarios.py    autenticación y CRUD de usuarios
  config.py      cargar/guardar cotizador_config.json (con cache en memoria)
  catalogo.py    clientes, atenciones, monedas, import/export
  carrito.py     carrito persistente por usuario
  historial.py   cotizaciones guardadas, estadísticas, tendencias
  proyectos.py   kanban, adjuntos, OC items
  asistencias.py reportes de asistencia
  email.py       config IMAP (contraseña cifrada) y emails importados

Todo `from web.database import X` sigue funcionando igual que antes.
"""
from web.db.core import *          # noqa: F401,F403
from web.db.core import (          # noqa: F401 — privados usados fuera
    BASE_DIR, DB_PATH, CONFIG_PATH, CONFIG_DEFECTO, _CONFIG_RAIZ,
    _add_column_if_missing, _backup_db, _crear_usuario, _hash_password,
    init_db,
)
from web.db.usuarios import *      # noqa: F401,F403
from web.db.config import *        # noqa: F401,F403
from web.db.config import _fusionar  # noqa: F401
from web.db.catalogo import *      # noqa: F401,F403
from web.db.carrito import *       # noqa: F401,F403
from web.db.historial import *     # noqa: F401,F403
from web.db.historial import _fp_items, _parse_espesor  # noqa: F401
from web.db.proyectos import *     # noqa: F401,F403
from web.db.proyectos import (     # noqa: F401
    ADJUNTOS_DIR, ESTADOS_KANBAN, ESTADO_LABELS, init_proyectos,
)
from web.db.asistencias import *   # noqa: F401,F403
from web.db.email import *         # noqa: F401,F403
from web.db.email import (         # noqa: F401
    _cifrar_imap_password, _descifrar_imap_password,
)

# Inicializar al importar (mismo comportamiento que el database.py original)
init_db()
init_proyectos()
