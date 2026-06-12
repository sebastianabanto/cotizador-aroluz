# Mapa de archivos — AROLUZ Cotizador Web

> Propósito: ubicar rápido qué archivo toca cada cosa, sin tener que explorar el repo.
> Última actualización: 2026-06-12 (v3.0). Tamaños aproximados en líneas.

## Backend (`web/`)

| Archivo | Líneas | Responsabilidad |
|---------|-------:|-----------------|
| `web/main.py` | ~1 480 | App FastAPI, middleware, security headers, rate limiter, **todas las rutas HTML** (login, home, cotizar, carrito, historial, catálogo, config, usuarios, cuenta, changelog), endpoints de config/usuarios/clientes/adjuntos. *Candidato a split (P3)* |
| `web/database.py` | ~2 440 | TODO el acceso SQLite: init/migraciones, usuarios, clientes/atenciones/monedas, carrito, cotizaciones+items, proyectos+adjuntos+OC items, config IMAP, asistencias, tendencias, backups BD, `cargar_config()`. *Candidato a split (P3)* |
| `web/auth.py` | ~115 | Cookies firmadas (itsdangerous), `require_user`, `require_admin`, hashing bcrypt |
| `web/motor.py` | ~510 | Motor de precios puro: `PricingConfig` + 7 funciones `cotizar_*`. **Único con tests** |
| `web/changelog.py` | ~270 | `VERSIONES[]` — actualizar SIEMPRE antes de deploy |
| `web/guillotine.py` | — | Algoritmo de corte de planchas |
| `web/importar_pdf.py` | — | Parsing de PDFs de cotizaciones para importar al carrito |
| `web/validators.py` | — | Validaciones compartidas (RUC, etc.) |

## Rutas API (`web/rutas/`)

| Archivo | Líneas | Endpoints |
|---------|-------:|-----------|
| `carrito.py` | ~1 400 | CRUD carrito, recalcular ítem (función grande L385-597), tapas separadas/juntas, reordenar, importar |
| `email_imap.py` | ~1 590 | Config IMAP, sync, parseo OC (S10/JEF/CLASEM), importar a kanban, geocode Lima. *Frágil: no refactorizar sin tests* |
| `exportar.py` | ~920 | PDF (WeasyPrint + `cotizacion_pdf.html`, fallback Playwright) y XLSX. **No tocar diseño del PDF** |
| `planchas.py` | ~815 | Cálculo de planchas/guillotina |
| `historial.py` | ~355 | Historial CRUD + `/api/tendencias` (series por cliente/global) |
| `cotizar.py` | ~265 | 7 endpoints `POST /api/cotizar/{tipo}` → `motor.py` |
| `importar_pdf.py` | ~180 | Importar PDF de cotización |

## Templates (`web/templates/`)

| Archivo | Líneas | Página |
|---------|-------:|--------|
| `cotizacion/carrito.html` | ~2 715 | Carrito (≈1 940 líneas de JS inline: CRUD in-place, autocomplete, export). Helpers in-place documentados en CLAUDE.md |
| `cotizacion/historial.html` | ~2 300 | Historial + filtros + modal tendencias Chart.js (≈1 570 JS inline) |
| `home.html` | ~2 265 | Dashboard kanban de proyectos/OC, drag-drop, KPIs |
| `configuracion.html` | ~1 480 | Config admin: precios, IMAP, catálogo, permisos |
| `cotizacion/cotizacion.html` | ~1 315 | Formulario de cotización 3 paneles (≈880 JS inline) |
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
| `importar.js` | ~1 025 | Modal importar OC/PDF al carrito |
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
