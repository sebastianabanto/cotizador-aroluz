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
│   └── historial.py        # GET /historial + export PDF/XLSX from saved quotes
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
