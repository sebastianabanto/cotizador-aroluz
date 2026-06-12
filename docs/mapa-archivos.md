# Mapa de archivos — AROLUZ Cotizador Web

> Propósito: ubicar rápido qué archivo toca cada cosa, sin tener que explorar el repo.
> Última actualización: 2026-06-12 (v3.1, post-refactor). Tamaños aproximados en líneas.

## Backend (`web/`)

| Archivo | Líneas | Responsabilidad |
|---------|-------:|-----------------|
| `web/main.py` | ~130 | Solo arma la app: middleware, security headers, mount static, includes de routers |
| `web/database.py` | ~45 | **Fachada** retrocompatible — re-exporta todo desde `web/db/` y ejecuta `init_db()` al importar |
| `web/plantillas.py` | ~40 | Jinja2 compartido: `templates`, `ctx()`, `_permiso_usuario()` |
| `web/auth.py` | ~115 | Cookies firmadas (itsdangerous), `require_login`, `require_admin`, hashing bcrypt |
| `web/limits.py` | ~10 | Rate limiter slowapi compartido (sin import circular) |
| `web/validators.py` | ~12 | Validaciones compartidas (`validar_ruc`) |
| `web/motor.py` | ~510 | Motor de precios puro: `PricingConfig` + 7 funciones `cotizar_*`. **Único con tests** |
| `web/changelog.py` | ~285 | `VERSIONES[]` — actualizar SIEMPRE antes de deploy |
| `web/guillotine.py` | — | Algoritmo de corte de planchas |
| `web/importar_pdf.py` | — | Parsing de PDFs de cotizaciones para importar al carrito |

## Acceso a datos (`web/db/`) — split de database.py, jun 2026

| Archivo | Responsabilidad |
|---------|-----------------|
| `core.py` | `DB_PATH`/`BASE_DIR`/`CONFIG_DEFECTO`, `init_db()`, migraciones, backups rotados (7), seed |
| `usuarios.py` | Autenticación y CRUD de usuarios |
| `config.py` | `cargar_config()` (cache en memoria) / `guardar_config()` (invalida cache) |
| `catalogo.py` | Clientes, atenciones, monedas, import/export Excel-JSON |
| `carrito.py` | Carrito persistente por usuario |
| `historial.py` | Cotizaciones guardadas, estadísticas, tendencias, duplicados |
| `proyectos.py` | Kanban (`ESTADOS_KANBAN`), adjuntos (`ADJUNTOS_DIR`), OC items |
| `asistencias.py` | Reportes de asistencia |
| `email.py` | Config IMAP (contraseña cifrada Fernet, prefijo `enc:`), emails importados, dominios |

## Rutas (`web/rutas/`)

| Archivo | Líneas | Endpoints |
|---------|-------:|-----------|
| `paginas.py` | ~340 | Rutas HTML: login/logout, home, cotizar, carrito, historial, catálogo, changelog, mi-config, usuarios, cuenta |
| `proyectos.py` | ~370 | API kanban: estado, adjuntos (subir/descargar/ver con validación de path), OC items, crear/eliminar |
| `config_admin.py` | ~760 | Configuración ADMIN: precios, catálogo JSON CRUD, clientes/atenciones, contactos, usuarios (con rate limiting) |
| `carrito.py` | ~1 500 | CRUD carrito, recalcular (dividido en `_recalcular_*`), tapas separadas/juntas, reordenar, importar |
| `email_imap.py` | ~1 590 | Config IMAP, sync, parseo OC (S10/JEF/CLASEM), importar a kanban, geocode Lima. *Frágil: no refactorizar sin tests* |
| `exportar.py` | ~920 | PDF (WeasyPrint + `cotizacion_pdf.html`, fallback Playwright) y XLSX. **No tocar diseño del PDF** |
| `planchas.py` | ~815 | Cálculo de planchas/guillotina |
| `historial.py` | ~355 | Historial CRUD + `/api/tendencias` (series por cliente/global) |
| `cotizar.py` | ~265 | 7 endpoints `POST /api/cotizar/{tipo}` → `motor.py` |
| `importar_pdf.py` | ~180 | Importar PDF de cotización |

## Templates (`web/templates/`)

| Archivo | Líneas | Página |
|---------|-------:|--------|
| `cotizacion/carrito.html` | ~780 | Carrito — su JS vive en `static/carrito.js`; datos Jinja vía `window.__CLIENTES__/__ATENCIONES__/__DOLAR__/__CARRITO__`. Helpers in-place documentados en CLAUDE.md |
| `cotizacion/historial.html` | ~740 | Historial + filtros + modal tendencias Chart.js — JS en `static/historial.js` (`window.__ES_ADMIN__`) |
| `home.html` | ~2 265 | Dashboard kanban de proyectos/OC, drag-drop, KPIs (JS aún inline) |
| `configuracion.html` | ~1 480 | Config admin: precios, IMAP, catálogo, permisos (JS aún inline) |
| `cotizacion/cotizacion.html` | ~455 | Formulario de cotización 3 paneles — JS en `static/cotizacion.js` (`window.__PLANCHA_GO__/__PLANCHA_GC__`) |
| `usuarios.html` | ~810 | Gestión de usuarios (ADMIN) |
| `asistencias/index.html` | ~760 | Registro de asistencias |
| `cotizacion/configuracion_catalogo.html` | ~675 | Categorías/productos del catálogo |
| `cotizacion/catalogo.html` | ~650 | Browser del catálogo |
| `cotizacion/clientes.html` | ~525 | Clientes master-detail |
| `cotizacion/cotizacion_pdf.html` | ~450 | **Plantilla oficial del PDF — diseño intocable** |
| `base.html` | ~250 | Layout: nav, dropdown ADMIN, bottom-nav móvil, toasts, shortcuts (Alt+C/R/K), heartbeat sesión, helper `formData()` |
| `login.html`, `cuenta.html`, `mi_config.html`, `changelog.html`, `cotizacion/planchas.html`, `asistencias/dashboard.html` | — | Páginas menores |

## Static (`web/static/`)

| Archivo | Líneas | Contenido |
|---------|-------:|-----------|
| `style.css` | ~2 740 | CSS global (variables `:root`, responsive 599/480/420px, bottom-nav, container queries) |
| `home.css` | ~1 665 | Kanban (⚠ redefine `:root` — pendiente unificar) |
| `asistencias.css` | ~800 | Asistencias (⚠ redefine `:root`) |
| `carrito.js` | ~1 940 | JS del carrito (extraído de carrito.html jun 2026) |
| `historial.js` | ~1 565 | JS del historial/tendencias (extraído jun 2026) |
| `importar.js` | ~1 025 | Modal importar OC/PDF al carrito |
| `cotizacion.js` | ~865 | JS del formulario de cotización (extraído jun 2026) |
| `planchas.js` | ~765 | UI de planchas |
| `asistencias-dashboard.js` | ~565 | Dashboard asistencias |
| `cotizar-layout.js` | ~85 | Layout del formulario de cotización |

## Datos y deploy

| Ruta | Qué es |
|------|--------|
| `web/data/aroluz.db` | SQLite (gitignored). Backups rotados en `web/data/backups/` |
| `web/data/cotizador_config.json` | Config de precios (en disco persistente de Fly) |
| `web/data/adjuntos/` | PDFs/imágenes de proyectos |
| `fly.toml` / `render.yaml` / `Dockerfile` | Deploy. Fly: app `sistema-cotizador-aroluz`, volumen en `/app/web/data`, `TZ=America/Lima` |
| `requirements.txt` | Deps web (sin pywin32/xlwings) |
| `web/tests/` | pytest — solo `test_motor.py` por ahora |

## Desktop (legacy estable — no tocar `gui/logica.py`)

`main.py` → `gui/main_window.py`. Lógica en `gui/logica.py` (globals), export Excel vía xlwings + plantilla `.xlsm`. Ver CLAUDE.md.
