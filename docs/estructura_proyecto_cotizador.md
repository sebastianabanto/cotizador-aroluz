# Estructura del Proyecto Cotizador Aroluz

```
COTIZADOR_AROLUZ/
│
├── cotizador_config.json          # Configuración principal del sistema
├── catalogo_productos.json        # Configuración de productos con precios fijos
├── main.py                        # Punto de entrada principal
│
├── gui/                          # Módulo principal de interfaz gráfica
│   ├── __init__.py               # Importa CotizadorAroluz y main
│   ├── main_window.py            # Ventana principal - coordinador
│   ├── configuracion.py          # Gestor de configuración del sistema
│   ├── exportar_excel.py         # Exportación híbrida a Excel con macros
│   ├── gestor_datos_excel.py     # CRUD completo de clientes y atenciones
│   ├── lector_excel.py           # Lectura de datos desde Excel
│   ├── logica.py                 # Lógica de cálculos y carrito
│   │
│   ├── dialogs/                  # Diálogos modales del sistema
│   │   ├── __init__.py
│   │   ├── ayuda_dialog.py       # Ventana de ayuda con shortcuts
│   │   ├── agregar_manual_dialog.py  # Diálogo agregar productos manuales
│   │   └── modificar_cantidad_dialog.py  # Diálogo modificar cantidades
│   │
│   ├── frames/                   # Frames reutilizables (actualmente vacío)
│   │   └── __init__.py
│   │
│   ├── tabs/                     # Pestañas del notebook principal
│   │   ├── __init__.py
│   │   ├── cotizacion_tab.py     # Pestaña de cotización de productos
│   │   ├── carrito_tab.py        # Pestaña del carrito de compras
│   │   └── catalogo_tab.py       # Pestaña de productos con precios fijos
│   │
│   └── utils/                    # Utilidades del sistema
│       ├── __init__.py
│       └── shortcuts.py          # Gestor de shortcuts de teclado
│
└── plantillas/                   # Carpeta para plantillas Excel (creada automáticamente)
    └── COTIZACIÓN v1.2     12-07-2023.xlsm  # Plantilla Excel con macros

```

## Descripción de Archivos Principales

### 📁 **Root (Raíz)**
- `cotizador_config.json` - Configuración principal (rutas, valores por defecto, interfaz)
- `main.py` - Punto de entrada que importa y ejecuta la GUI

### 📁 **gui/ (Módulo Principal)**
- `main_window.py` - Coordinador principal, maneja pestañas y shortcuts
- `configuracion.py` - Sistema completo de configuración con GUI
- `logica.py` - Cálculos de cotización, clases de productos, carrito
- `lector_excel.py` - Lectura de datos de clientes, atenciones y monedas
- `exportar_excel.py` - Exportación híbrida (nativa + xlwings) con macros
- `gestor_datos_excel.py` - CRUD completo para gestión de datos Excel

### 📁 **gui/tabs/ (Pestañas)**
- `cotizacion_tab.py` - Interfaz de cotización (configuración + productos)
- `carrito_tab.py` - Interfaz del carrito (proyecto + items + exportación)

### 📁 **gui/dialogs/ (Diálogos)**
- `ayuda_dialog.py` - Ventana de ayuda con todos los shortcuts
- `agregar_manual_dialog.py` - Agregar productos manuales al carrito
- `modificar_cantidad_dialog.py` - Modificar cantidades o editar manuales

### 📁 **gui/utils/ (Utilidades)**
- `shortcuts.py` - Gestor completo de shortcuts de teclado

### 📁 **plantillas/ (Auto-creada)**
- Contiene la plantilla Excel con macros VBA para exportación

## Características del Proyecto

✅ **Arquitectura Modular**: Separación clara por responsabilidades  
✅ **Sistema de Configuración**: Persistente con GUI de gestión  
✅ **Gestión de Datos**: CRUD completo para Excel con backups  
✅ **Exportación Avanzada**: Método híbrido con macros automáticas  
✅ **Shortcuts Completos**: Sistema de atajos de teclado integral  
✅ **Interfaz Profesional**: Pestañas, diálogos y componentes modulares  

## Flujo de Ejecución

1. **main.py** → importa **gui.main** → ejecuta **CotizadorAroluz**
2. **main_window.py** coordina **tabs/** y **utils/shortcuts.py**
3. **cotizacion_tab.py** usa **logica.py** para cálculos
4. **carrito_tab.py** usa **exportar_excel.py** para generar archivos
5. **Todos los módulos** usan **configuracion.py** para settings

