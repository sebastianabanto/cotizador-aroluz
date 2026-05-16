"""changelog.py — Historial de versiones de la aplicación web AROLUZ."""

# Categorías disponibles: "nueva", "mejora", "corrección", "seguridad", "rendimiento"

VERSIONES = [
    {
        "version": "1.6",
        "fecha": "2026-05-16",
        "titulo": "Filtros inteligentes de correo + selector de mes",
        "cambios": [
            ("nueva",      "Filtro de 15 patrones de falsos positivos en sync de correo (solicitudes de documentos, consultas, homologaciones, seguimientos, anulaciones, etc.)"),
            ("nueva",      "Selector de mes/año con flechas ‹ › en el modal de sincronizar correo — sin posibilidad de elegir rango arbitrario"),
            ("mejora",     "Límite de emails escaneados ampliado de 80 a 300 por sincronización"),
            ("mejora",     "Tiempo de procesamiento extendido a 110 s para cubrir meses completos con alto volumen"),
        ],
    },
    {
        "version": "1.5",
        "fecha": "2026-05-15",
        "titulo": "Chips de cliente en kanban + mejoras de correo",
        "cambios": [
            ("nueva",      "Chips de cliente visibles en las tarjetas del kanban desde 1 sola obra"),
            ("mejora",     "Dashboard de asistencias con mejoras de visualización"),
            ("corrección", "Error 'Unexpected end of JSON' al sincronizar IMAP con rango largo de fechas"),
        ],
    },
    {
        "version": "1.4",
        "fecha": "2026-05-10",
        "titulo": "Módulo de correo IMAP — sincronización de OCs",
        "cambios": [
            ("nueva",      "Sincronización IMAP: detecta automáticamente correos con OC adjunta (formatos S10, JEF, CLASEM)"),
            ("nueva",      "Parser de PDF de órdenes de compra: extrae número OC, cliente, obra, lugar y fecha de entrega"),
            ("nueva",      "Importación con un clic: crea el proyecto en el kanban con ítems OC cargados"),
            ("nueva",      "Vista previa de PDF del correo antes de importar"),
            ("nueva",      "Geocodificación de dirección de entrega para ordenar ruta Norte→Sur"),
            ("nueva",      "Deduplicación doble: por message-id y por hash SHA-256 del PDF"),
            ("nueva",      "Pestaña 'Correo' en Configuración con presets Gmail / Outlook / Yahoo / Zoho"),
            ("nueva",      "Columnas fecha OC, fecha entrega y lugar en las tarjetas del kanban"),
            ("nueva",      "Notas libres por proyecto en la tarjeta kanban"),
        ],
    },
    {
        "version": "1.3",
        "fecha": "2026-03-20",
        "titulo": "Módulo Asistencias + mejoras mobile",
        "cambios": [
            ("nueva",      "Módulo de asistencias integrado en el mismo servidor (puerto 8000, ruta /asistencias/)"),
            ("nueva",      "Reporte PDF de asistencias generado con WeasyPrint"),
            ("mejora",     "PDF de cotización migrado de ReportLab programático a WeasyPrint + plantilla HTML"),
            ("mejora",     "Scroll fluido, touch targets de 44 px y font-size 16 px anti-zoom en iOS"),
            ("mejora",     "Inputs numéricos/decimales con inputmode correcto en dispositivos móviles"),
            ("corrección", "Cierre automático de sesión por inactividad (10 minutos)"),
        ],
    },
    {
        "version": "1.2",
        "fecha": "2026-03-01",
        "titulo": "Kanban de obras + importar OC desde PDF",
        "cambios": [
            ("nueva",      "Módulo Proyectos Kanban: tablero con columnas COTIZADO / APROBADO / DESPACHADO / ENTREGADO"),
            ("nueva",      "Importar ítems de OC desde PDF (tabla o texto libre, múltiples formatos)"),
            ("nueva",      "Adjuntos por proyecto: PDFs de OC y evidencias de despacho"),
            ("nueva",      "Ruta de despacho: selección de obras y ordenamiento N→S por geocodificación"),
            ("nueva",      "KPIs del pipeline en el home (cotizado, aprobado, despachado, entregado)"),
            ("nueva",      "Compresión automática de imágenes al subir adjuntos"),
            ("nueva",      "CI/CD: auto-deploy a Fly.io en cada push a main"),
            ("mejora",     "Historial con filtros avanzados, ordenamiento y estadísticas"),
            ("mejora",     "Carrito con cantidad decimal y soporte de metro lineal"),
            ("rendimiento","Índices SQLite en cotizaciones, atenciones y email_importados"),
        ],
    },
    {
        "version": "1.1",
        "fecha": "2026-02-15",
        "titulo": "Roles, historial y exportación mejorada",
        "cambios": [
            ("nueva",      "Roles ADMIN / USER: admin ve todo el historial, user solo el propio"),
            ("nueva",      "Página /historial con modal de detalle y exportación PDF/XLSX por cotización guardada"),
            ("nueva",      "Página /clientes con master-detail (RUC, ubicación, email de atención)"),
            ("nueva",      "Página /cuenta: cambio de contraseña para todos los roles"),
            ("nueva",      "Exportación en dólares (USD): conversión automática con la tasa guardada"),
            ("nueva",      "Validez de cotización seleccionable (15 / 30 / 60 / 90 días) en el carrito"),
            ("mejora",     "Header del PDF rediseñado: tabla azul con datos de empresa y subtítulo"),
            ("mejora",     "Carrito persistente en SQLite por usuario (ya no in-memory)"),
        ],
    },
    {
        "version": "1.0",
        "fecha": "2026-02-01",
        "titulo": "Lanzamiento de la versión web",
        "cambios": [
            ("nueva",      "Aplicación web FastAPI accesible desde cualquier dispositivo en la red"),
            ("nueva",      "Motor de cotización web (web/motor.py) con PricingConfig — independiente del desktop"),
            ("nueva",      "Autenticación con cookie firmada (itsdangerous, 7 días de duración)"),
            ("nueva",      "Cotización de los 7 tipos de producto: Bandeja, Curvas H/V, Tee, Cruz, Reducción, Caja de Pase"),
            ("nueva",      "Catálogo de precio fijo"),
            ("nueva",      "Exportación PDF (WeasyPrint) y XLSX (openpyxl) sin dependencia de Excel/Windows"),
            ("nueva",      "Base de datos SQLite auto-creada al primer arranque"),
            ("nueva",      "Deploy en Fly.io con disco persistente para datos y configuración"),
        ],
    },
]
