# Auditoría técnica — junio 2026

> Snapshot de hallazgos al 2026-06-12 (v3.0). Los ítems se trackean en [`ROADMAP.md`](../ROADMAP.md); este doc conserva el detalle archivo:línea. Las líneas pueden desfasar con el tiempo.

## Seguridad

| Severidad | Hallazgo | Ubicación | Estado |
|-----------|----------|-----------|--------|
| 🔴 | `StreamingResponse(open(p,"rb"))` sin cierre → fuga de file descriptors | `web/main.py:391,409`, `web/rutas/exportar.py:315` | Corregido jun 2026 (`FileResponse`) |
| 🔴 | Contraseña IMAP en texto plano en tabla `email_imap_config` | `web/database.py:~2354` | Corregido jun 2026 (Fernet con `AROLUZ_SECRET_KEY`) |
| 🟠 | Sin validar que `filepath` de adjuntos esté dentro de `ADJUNTOS_DIR` | `web/main.py:380-394` | Corregido jun 2026 (`is_relative_to`) |
| 🟠 | Rate limiting solo en login; faltaba en cambiar password, crear usuario, config IMAP, importar | `web/main.py` | Corregido jun 2026 |
| 🟠 | Contraseña admin inicial hardcodeada (`aroluz2024`) | `web/database.py:~277` | Corregido jun 2026 (`AROLUZ_ADMIN_PASSWORD` env con fallback) |
| 🟡 | Sin tokens CSRF en formularios POST | todos los templates | Pendiente (P1) |
| 🟢 | Fortalezas: bcrypt + migración SHA256, security headers (CSP, X-Frame-Options), queries parametrizadas (sin SQLi), dedup IMAP doble (message_id + SHA-256) | — | — |

## Eficiencia

| Hallazgo | Ubicación | Estado |
|----------|-----------|--------|
| `cargar_config()` lee JSON del disco en cada request | `web/rutas/cotizar.py` (todas las funciones) | Corregido jun 2026 (cache + invalidación al guardar) |
| ~88 `conn.close()` sin context manager — fuga si hay excepción antes del close | `web/database.py` (todo el archivo) | Pendiente — se resuelve con refactor `web/db/` (P3) |
| Posible N+1 en sync IMAP (query por email para dedup) | `web/rutas/email_imap.py:~1300-1400` | Pendiente (P2) |
| Conexión IMAP sin cierre garantizado ante excepción | `web/rutas/email_imap.py:~1461` (`_conectar_imap`) | Pendiente (P2) |

## Mantenibilidad

| Hallazgo | Detalle |
|----------|---------|
| Archivos gigantes backend | `database.py` 2 436, `main.py` 1 481, `email_imap.py` 1 592, `carrito.py` 1 405 líneas |
| JS inline masivo (~5 700 líneas) | `carrito.html` 1 941, `historial.html` 1 567, `cotizacion.html` 879 |
| Función gigante | `api_recalcular_item` — `web/rutas/carrito.py:385-597` (212 líneas) |
| Código duplicado | Validación RUC (`database.py:~690` y `main.py:~843` → `web/validators.py`); `toggleCat` en catalogo.html y configuracion_catalogo.html |
| CSS | `style.css` 2 742 líneas monolítico; `home.css` y `asistencias.css` redefinen `:root` |
| Código muerto | `web/templates/Basurero/` (4 994 líneas) — **eliminado jun 2026** |

## UX/UI

- ~25 instancias de `location.reload()`/`href` fuera del patrón in-place (carrito ya migrado, resto pendiente).
- 22 `confirm()` nativos del navegador para acciones destructivas (sin modal propio).
- Estados de carga: solo `btn.disabled + texto "⏳"`, sin spinner global.
- Accesibilidad: faltan `aria-live` en regiones dinámicas y `aria-label` en botones emoji; sí hay `.sr-only`, labels `for=`, 54 atributos aria en cotización.
- ~502 estilos inline en templates de cotización.
- Positivo: sistema de toasts centralizado (207 usos), bottom-nav móvil, shortcuts de teclado, heartbeat de sesión, drag-drop táctil.

## Testing

- Solo `web/tests/test_motor.py`. Sin tests de auth, carrito, parseo OC, historial.
- Riesgo principal: parsers de OC en `email_imap.py` sin fixtures — bloquea su refactor.

## Repo

- `landing_page/` contiene un borrador real (index.html, catálogo PDF, CSV de obras) — no es basura; decisión pendiente en roadmap P5.
- Sin README.md (existe CLAUDE.md como doc principal).
- Sin Swagger (`docs_url` deshabilitado u oculto).
