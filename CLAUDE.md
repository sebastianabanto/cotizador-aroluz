# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AROLUZ Cotizador is a Python + Tkinter desktop app for quoting structural cable tray products. A FastAPI web version was implemented in February 2026 and lives in `web/` within this same directory.

**Two apps coexist:**
- `main.py` — desktop app (Tkinter, Windows only)
- `web/main.py` — web app (FastAPI, any device on the network)

---

## Running the App

```bash
# Activate venv (Windows)
venv\Scripts\activate

# Run desktop app
python main.py
```

There is no `requirements.txt`. Dependencies are tracked only inside `venv/`. Key packages installed: `openpyxl`, `xlwings`, `xlsxwriter`, `pandas`, `pillow`, `reportlab`, `pywin32`, `fastapi`, `uvicorn`, `pydantic`, `jinja2`, `itsdangerous`, `python-multipart`.

To recreate the venv from scratch:
```bash
pip install openpyxl xlwings xlsxwriter pandas pillow reportlab pywin32 fastapi uvicorn pydantic python-dotenv jinja2 itsdangerous python-multipart
```

**IMPORTANT — venv pip quirk:** The `pip.exe` wrapper in this venv points to a sibling venv. Always install packages using:
```bash
venv\Scripts\python.exe -m pip install <package>
```

**Export to Excel (desktop)** requires Windows + Microsoft Excel installed — `gui/exportar_excel.py` uses xlwings COM automation to run VBA macros in `plantillas/COTIZACIÓN v1.2 12-07-2023.xlsm`.

**Export web** uses ReportLab (PDF) and openpyxl (XLSX) — no Windows/Excel dependency.

### Running the Web App

```bash
# Double-click (Windows)
iniciar_web.bat

# Or directly:
venv\Scripts\python.exe -m uvicorn web.main:app --host 0.0.0.0 --port 8000
```

URL: `http://localhost:8000` — default login: `admin` / `aroluz2024`

---

## Architecture

### Web Architecture (added Feb 2026)

```
web/
├── main.py          # FastAPI app — all page routes + mounts API routers
├── motor.py         # Pure pricing engine — PricingConfig dataclass replaces logica.py globals
├── auth.py          # Signed session cookies (itsdangerous HMAC, 7-day expiry)
├── database.py      # SQLite (web/data/aroluz.db) — users, clients (RUC/ubicación),
│                    #   atenciones (email), monedas, carrito_items,
│                    #   cotizaciones + cotizacion_items (historial snapshot)
├── rutas/
│   ├── cotizar.py          # POST /api/cotizar/{tipo} — calls motor.py, returns JSON
│   ├── carrito.py          # GET/POST /api/carrito — SQLite-persisted cart per user
│   ├── exportar.py         # POST /api/exportar/{pdf|xlsx} — streaming file download
│   ├── historial.py        # GET /historial + export PDF/XLSX from saved quotes
│   └── email_imap.py       # GET+POST /api/email/* — sync IMAP, parse OC PDFs, geocode
├── templates/
│   ├── base.html                   # Base layout (nav, session, messages)
│   ├── login.html
│   ├── cotizacion.html             # Main quoting form
│   ├── cotizacion_pdf.html         # PDF preview template (ReportLab via HTML)
│   ├── carrito.html                # Cart view + validez selector
│   ├── catalogo.html               # Fixed-price catalog browser
│   ├── configuracion.html          # Settings page (pricing config)
│   ├── configuracion_catalogo.html # Catalog import from Excel
│   ├── clientes.html               # Clients master-detail (JS vanilla)
│   └── historial.html              # Quote history + filter bar
├── static/
│   ├── style.css                   # Full CSS — no external frameworks
│   ├── cotizar-layout.js           # JS for quoting form UI behavior
│   └── IMAGEN_LOGO_AROLUZEIRL_BARRITA.png
└── data/
    └── aroluz.db    # SQLite — auto-created on first run
```

**Key design decisions:**
- `web/motor.py` reimplements `gui/logica.py` functions with `PricingConfig` as a parameter instead of globals. `gui/logica.py` is NOT modified — desktop app still works.
- Cart is persisted in SQLite (`carrito_items` table, keyed by username). No longer in-memory.
- Historial de cotizaciones stored in `cotizaciones` + `cotizacion_items` tables (snapshot at export time, includes `dolar_rate` and `validez` columns).
- Auth uses itsdangerous `URLSafeTimedSerializer` — no JWT library needed.
- Catalog (clients, atenciones, monedas) is seeded from the Excel file via `database.importar_catalogo_desde_excel()` or added manually via the Config page.
- Clients have `ruc` and `ubicacion` fields; atenciones have `email`. Added via `_add_column_if_missing()` migration.
- Export PDF/XLSX converts prices to USD when `moneda = DOLARES` using the saved `dolar_rate`.
- PDF header redesigned: blue table with company info + subtitle. Carrito allows selecting `validez` (15/30/60/90 días).
- Historial page has filter bar (client, project, date range) and shows correct currency symbol (S/ or $).

### Módulo Email IMAP (agregado may 2026)

**Propósito:** Evitar la carga manual de órdenes de compra. Conecta a la bandeja IMAP de la empresa, detecta automáticamente los correos que contienen OC (por asunto o dominio del remitente), extrae los datos del PDF adjunto y crea el proyecto correspondiente en el kanban con un solo clic.

**Endpoints** (prefijo `/api/email/`, montado en `web/main.py`):

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/api/email/config` | Devuelve la configuración IMAP guardada (contraseña enmascarada). Solo admin. |
| `POST` | `/api/email/config` | Guarda host, puerto, usuario, contraseña, carpeta y `days_back`. Solo admin. |
| `POST` | `/api/email/sync` | Conecta al IMAP, escanea los últimos N emails y devuelve los que detecta como OC con PDF adjunto. Acepta `?since=` y `?until=` para filtrar por fecha. |
| `POST` | `/api/email/importar` | Descarga el PDF del email indicado, crea el proyecto en la BD (con `lugar_entrega`, `fecha_entrega`, `fecha_oc`), guarda el PDF en disco, importa los ítems OC y registra el email como importado. |
| `GET`  | `/api/email/pdf-preview` | Retorna el PDF del email como `StreamingResponse` para previsualizarlo en el navegador antes de importar. |
| `GET`  | `/api/email/geocode` | Geocodifica una dirección para ordenar la ruta N→S. Usa primero un dict de distritos de Lima (instantáneo) y luego Nominatim como fallback. |

**Formatos de OC soportados:**

- **S10** — identificado por la etiqueta `Número` (capital N, con tilde). Extrae `Número`, `Fecha`, `Facturar a`, `Proyecto Almacén`, `Lugar de entrega`, `Fecha de entrega`.
- **JEF** — usa `Nº 0001-XXXXXX`, fecha con ciudad (`Lima, dd/mm/yyyy`), `Glosa`, `Dirección Entrega`.
- **CLASEM / genérico** — detecta `FACTURA A NOMBRE DE`, `PROYECTO :`, `Dirección de Entrega`, etiquetas genéricas (`OBRA`, `REFERENCIA`, `DESCRIPCIÓN`, etc.) y el patrón `CÓDIGO - NOMBRE DE OBRA`.

**Tablas SQLite nuevas:**

| Tabla | Descripción |
|-------|-------------|
| `email_imap_config` | Fila única (id=1) con host, port, username, password, folder, days_back. |
| `email_importados` | Registro de emails procesados: `message_id` (PK), `proyecto`, `importado_at`, `pdf_hash` (SHA-256 para detectar reenvíos con el mismo adjunto). |

**Columnas nuevas en `proyectos`** (migración automática con `_add_column_if_missing`):

| Columna | Descripción |
|---------|-------------|
| `lugar_entrega` | Dirección de entrega extraída del PDF o ingresada manualmente. |
| `fecha_entrega` | Fecha de entrega solicitada (formato dd/mm/yyyy). |
| `fecha_oc` | Fecha de emisión de la OC (formato dd/mm/yyyy). |
| `notas` | Campo libre de observaciones del proyecto. |

**Flujo típico:**
1. Admin configura IMAP en Ajustes → Correo (`POST /api/email/config`).
2. Usuario abre la pantalla de correo y hace clic en "Sincronizar" (`POST /api/email/sync`).
3. Aparece la lista de emails detectados con datos pre-rellenados (nombre de obra, cliente, N° OC).
4. Usuario revisa el PDF (`GET /api/email/pdf-preview`), ajusta los campos si es necesario e importa (`POST /api/email/importar`).
5. El proyecto aparece automáticamente en el kanban en estado APROBADO con sus ítems OC cargados.

**Notas de implementación:**
- Operaciones IMAP se ejecutan con `run_in_threadpool` para no bloquear el event loop de FastAPI.
- Deduplicación doble: por `message_id` (evita reimportar el mismo email) y por `pdf_hash` SHA-256 (evita duplicados por reenvíos con el mismo adjunto).
- Correos de ingreso/recepción de OC (`INGRESO POR OC`, `NOTA DE INGRESO`, etc.) se filtran tanto en el asunto como en el contenido del PDF.
- La geocodificación usa un diccionario hardcodeado de ~50 distritos de Lima Metropolitana para evitar latencia; Nominatim se llama solo si el distrito no está en el dict.

---

**Known limitations / pending polish:**
- No catalog import UI for the initial Excel file (must enter path manually in Config page)
- PDF/XLSX export does not use the existing `.xlsm` VBA template
- No role-based access (all users have same permissions)
- No deploy to cloud yet (Railway/Render — code is compatible)

---

### Desktop Entry Point Flow

`main.py` → `gui/__init__.py` → `gui/main_window.py:CotizadorAroluz`

`CotizadorAroluz.__init__` creates a `ttk.Notebook` with three tabs, loads Excel data, and registers keyboard shortcuts.

### Key Files

| File | Role |
|------|------|
| `gui/logica.py` | Core business logic. Contains module-level globals (`carrito`, `tipo_galvanizado`, `dolar`, `precio_galvanizado_kg`, `factor_ganancia`) used as shared state across the app. Also contains `ProductoCotizado`, `ProductoManual` classes and all `cotizar_*` calculation functions. |
| `gui/configuracion.py` | `ConfiguracionManager` — reads/writes `cotizador_config.json`. Merges saved config with defaults on load. Also handles extracting the Excel template from `plantillas/`. |
| `gui/lector_excel.py` | Reads `catalogo_productos.xlsx` at startup for customer names, attention types, and currency data. |
| `gui/exportar_excel.py` | Hybrid export: openpyxl writes data, then xlwings opens the `.xlsm` template and triggers VBA macros. |
| `gui/gestor_datos_excel.py` | CRUD operations on the Excel data file. |
| `gui/tabs/cotizacion_tab.py` | Product selection, dimension inputs, real-time price preview, calls `logica.py` functions. |
| `gui/tabs/carrito_tab.py` | Shopping cart view, project/attention selectors, triggers export. |
| `gui/tabs/catalogo_tab.py` | Fixed-price catalog browser. |
| `gui/utils/shortcuts.py` | `ShortcutsManager` — binds Ctrl+1–8 for product selection, Ctrl+Enter to quote, Ctrl+Q/W/E for tab switching. |
| `gui/dialogs/` | `agregar_manual_dialog.py`, `modificar_cantidad_dialog.py`, `confirmar_producto_dialog.py`, `ayuda_dialog.py` |

### Global State in `logica.py`

`logica.py` uses module-level mutable variables as the single source of truth. Before any cotización, `configurar_sistema()` must be called to set `tipo_galvanizado`, `dolar`, `precio_galvanizado_kg`, and `factor_ganancia`. The `carrito` list is shared globally and mutated in place.

### Two Generations of Cotización Functions

`logica.py` contains two sets of cotización functions:
- **Original**: `cotizar_bandeja()`, `cotizar_curva_horizontal()`, etc. — used by the console `main()` and still imported in `cotizacion_tab.py`.
- **Newer `_con_tipo` versions**: `cotizar_bandeja_con_tipo()`, etc. — add `tipo_superficie` (LISA/RANURADA/ESCALERILLA) support and improved descriptions with full dimensions.

`cotizacion_tab.py` currently imports the original functions (lines 7–16). Prefer the `_con_tipo` variants for any new work.

---

## Domain Concepts

**Product types** (tipo codes): `B` (Bandeja), `CH` (Curva H), `CVE`/`CVI` (Curva V Ext/Int), `T` (Tee), `C` (Cruz), `R` (Reducción), `CP` (Caja Pase).

**Galvanization**: `GO` (origin galvanized, no extra cost) or `GC` (hot-dip, adds `peso × dolar × precio_galvanizado_kg / 0.95`). Cajas de Pase always use `3.0 USD/kg` regardless of the configured rate.

**Surface types**: LISA, RANURADA, ESCALERILLA. ESCALERILLA adds `+S/10` to `precio_base`.

**Pricing factors** per product type: each product code (B, CH, CVE, T, C, R, CP) has a different divisor depending on whether `ganancia = "30"` or `"35"`. These are hardcoded in `get_factor_ganancia_producto()` in `logica.py`.

**Sheet area**: Standard sheet is 2400 × 1200 mm. `pl_undmm2 = precio_plancha / (2400 × 1200)`.

**Caja de Pase dimensions**: input in **cm** (converted ×10 to mm internally). Other product dimensions are in **mm** throughout.

---

## Configuration

`cotizador_config.json` (root) — auto-created with defaults if missing. Key sections:
- `rutas.plantilla_excel` — path to `.xlsm` template (configured by user via UI)
- `valores_defecto` — ganancia factor, galvanization, sheet prices per thickness (1.2/1.5/2.0 mm) for GO and GC, dollar rate, USD/kg rates
- `interfaz` — `recordar_config`, `recordar_medidas`, `mostrar_validaciones`

A backup is kept at `cotizador_config_backup.json`.

## Data Files

- `catalogo_productos.xlsx` — loaded at startup; must exist or the app shows an error. Contains customer names, attention types, currency options.
- `plantillas/COTIZACIÓN v1.2 12-07-2023.xlsm` — Excel template with macros. Path is configurable via `cotizador_config.json`.

---

## Working Conventions

- **No Figma MCP** — do not use the Figma MCP integration. User does not use it.
- **No JS frameworks** — web app uses HTML + CSS + JS vanilla + Jinja2. No React, Vue, or Bootstrap.
- **Language** — always respond to the user in **Español**.
- **Never touch `gui/logica.py`** — web logic lives exclusively in `web/motor.py`.
- **Install packages** always via `venv\Scripts\python.exe -m pip install <package>` (never `pip.exe` directly).
- **NUNCA cambiar el formato/diseño del PDF exportado** — la plantilla oficial es `web/templates/cotizacion_pdf.html`. Si hay un problema técnico con el generador de PDF (Playwright, WeasyPrint, etc.), se debe cambiar el motor de renderizado, NUNCA el diseño/estructura del template ni sustituirlo por otra implementación (ej. ReportLab programático). El aspecto visual del PDF es decisión exclusiva del usuario.

---

## Archivos clave del módulo web

| Archivo | Rol |
|---------|-----|
| `web/motor.py` | PricingConfig dataclass + 7 funciones `cotizar_*` |
| `web/main.py` | FastAPI app + todas las rutas HTML |
| `web/auth.py` | Sesiones firmadas (cookie HTTP-only, 7 días) |
| `web/database.py` | SQLite: usuarios, clientes, atenciones, monedas + `cargar_config()` |
| `web/rutas/cotizar.py` | 7 endpoints `POST /api/cotizar/{tipo}` |
| `web/rutas/carrito.py` | Carrito SQLite persistente por usuario |
| `web/rutas/exportar.py` | PDF + XLSX streaming download |
| `web/rutas/historial.py` | Historial guardado: CRUD + export PDF/XLSX |
| `web/rutas/email_imap.py` | Router IMAP: sync de emails, parseo de OC (S10/JEF/CLASEM), geocodificación Lima |
| `web/templates/base.html` | Layout base (nav, sesión, mensajes) |
| `web/templates/cotizacion.html` | Formulario de cotización principal |
| `web/templates/cotizacion_pdf.html` | Preview PDF (WeasyPrint) |
| `web/templates/carrito.html` | Carrito + selector de validez |
| `web/templates/catalogo.html` | Catálogo de precio fijo |
| `web/templates/configuracion.html` | Config de precios |
| `web/templates/configuracion_catalogo.html` | Importar catálogo desde Excel |
| `web/templates/clientes.html` | Clientes master-detail (JS vanilla) |
| `web/templates/historial.html` | Historial + barra de filtros + col Usuario (solo admin) |
| `web/templates/cuenta.html` | Mi Cuenta — cambiar contraseña (todos los roles) |
| `web/static/style.css` | CSS completo responsive (sin Bootstrap) |
| `web/static/cotizar-layout.js` | JS para el formulario de cotización |
| `web/static/IMAGEN_LOGO_*.png` | Logo de la empresa |
| `web/data/aroluz.db` | SQLite auto-creada al primer arranque |
