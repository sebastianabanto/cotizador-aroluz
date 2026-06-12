# ROADMAP — AROLUZ Cotizador

> Última actualización: 2026-06-12 · Versión actual: **3.0** (ver `web/changelog.py`)
> Docs relacionados: [`docs/mapa-archivos.md`](docs/mapa-archivos.md) · [`docs/auditoria-2026-06.md`](docs/auditoria-2026-06.md)

## Dónde estamos parados

Dos apps coexisten: **desktop** (`main.py`, Tkinter, congelada/estable) y **web** (`web/main.py`, FastAPI, desarrollo activo desde feb 2026, desplegada en Fly.io).

**Módulos web funcionando (v3.0, jun 2026):**

| Módulo | Ruta | Estado |
|--------|------|--------|
| Cotizador (7 tipos de producto) | `/cotizar` | ✅ Estable |
| Carrito persistente (SQLite, in-place) | `/carrito` | ✅ Estable |
| Catálogo precio fijo | `/catalogo` | ✅ Estable |
| Historial + filtros + **tendencias de precios** (Chart.js) | `/historial` | ✅ v3.0: tendencias globales sin cliente |
| Clientes (RUC/ubicación) + atenciones (email) | `/clientes` | ✅ Estable |
| Kanban de proyectos/OC + adjuntos | `/home` | ✅ Estable |
| Correo IMAP → importar OC (S10/JEF/CLASEM) | Ajustes → Correo | ✅ Estable |
| Cálculo de planchas (guillotina) | `/planchas` | ✅ Estable |
| Asistencias + dashboard | `/asistencias/` | ✅ Estable |
| Usuarios y roles ADMIN/USER | `/usuarios` | ✅ Estable |
| Export PDF (WeasyPrint) / XLSX | desde carrito e historial | ✅ Estable |
| Changelog visible | `/changelog` | ✅ Estable |

**Deploy:** Fly.io (`fly.toml`, app `sistema-cotizador-aroluz`, disco persistente) + alternativa Render (`render.yaml`). Regla: actualizar `web/changelog.py` antes de cada deploy.

---

## Backlog priorizado

### P1 — Seguridad 🔴
- [x] File descriptor leaks en `StreamingResponse(open(...))` → `FileResponse` *(jun 2026)*
- [x] Validar path traversal al servir adjuntos (`is_relative_to`) *(jun 2026)*
- [x] Cifrar contraseña IMAP en BD (Fernet, clave de `AROLUZ_SECRET_KEY`) *(jun 2026)*
- [x] Rate limiting en endpoints sensibles (cambiar password, crear usuario, config IMAP) *(jun 2026)*
- [x] Contraseña admin inicial vía `AROLUZ_ADMIN_PASSWORD` (env) *(jun 2026)*
- [ ] Tokens CSRF en formularios POST (la cookie firmada mitiga, pero no protege contra CSRF)
- [ ] Auditoría de roles: revisar que cada endpoint de escritura valide rol, no solo sesión

### P2 — Eficiencia 🟠
- [x] Cache en memoria de `cargar_config()` con invalidación al guardar *(jun 2026)*
- [ ] Context manager `get_conn()` en el 100 % de accesos SQLite (~88 `conn.close()` sueltos) — se resuelve junto con el refactor 4a
- [ ] N+1 en sync IMAP: precargar `message_id`/`pdf_hash` existentes en un set antes del loop
- [ ] Revisar índices SQLite para queries de tendencias (`cotizacion_items` por descripción/fecha)

### P3 — Refactor / Mantenibilidad 🟡
- [ ] `web/database.py` (2 400+ líneas) → paquete `web/db/` con fachada retrocompatible
- [ ] `web/main.py` (1 500 líneas) → routers (`paginas`, `config_admin`, `proyectos`)
- [ ] Extraer JS inline a `web/static/` (carrito ~1 900, historial ~1 600, cotización ~880 líneas)
- [ ] Unificar variables CSS: `home.css` y `asistencias.css` no deben redefinir `:root`
- [ ] Dividir `api_recalcular_item` (`web/rutas/carrito.py`, 212 líneas) en funciones privadas
- [ ] `web/rutas/email_imap.py` (1 600 líneas): **primero** tests de parseo de OC (S10/JEF/CLASEM) con PDFs fixtures, **después** refactor — el parsing es frágil
- [ ] Eliminar duplicados: `validar_ruc` (usar `web/validators.py`), `toggleCat` en varios templates

### P4 — UX / UI 🔵
- [ ] Spinner/loading global reutilizable (hoy solo se deshabilitan botones con texto "⏳")
- [ ] Modal de confirmación propio para reemplazar los 22 `confirm()` nativos
- [ ] Eliminar los ~25 `location.reload()`/`href` restantes fuera del carrito (patrón in-place ya documentado en CLAUDE.md)
- [ ] Accesibilidad: `aria-live` en regiones dinámicas (totales del carrito), `aria-label` en botones emoji (👤, etc.), escape para cerrar modales de forma consistente
- [ ] Reducir los ~500 estilos inline en templates de cotización (mover a clases)
- [ ] Validación JS de formularios antes de submit (hoy solo `required` HTML)

### P5 — Funcionalidad pendiente 🟢
- [ ] Tests: solo existe `web/tests/test_motor.py`. Prioridad: auth, carrito (recalcular), parseo OC, historial/tendencias
- [ ] Swagger/OpenAPI (`docs_url="/api/docs"`) protegido para admin
- [ ] File picker / autodetección para importar `catalogo_productos.xlsx` (hoy ruta manual en Config)
- [ ] `landing_page/` — hay un borrador (index.html, catálogo PDF, obras CSV, premio PYME): decidir si se publica y dónde (¿Fly.io estático?)
- [ ] Backups de BD: existe rotación local (7 copias); evaluar copia externa (Fly volumes snapshot / S3)

---

## Cómo mantener este roadmap

- Al completar un ítem: marcar `[x]` y añadir `*(mes año)*`.
- Al detectar deuda nueva: agregarla en la sección de prioridad que corresponda.
- Cada release: nueva entrada en `web/changelog.py` (obligatorio antes de deploy) y revisar si este archivo sigue al día.
