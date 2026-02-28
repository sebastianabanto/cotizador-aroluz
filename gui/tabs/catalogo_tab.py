# -*- coding: utf-8 -*-
"""
Pestaña de catálogo de productos adicionales - VERSIÓN MEJORADA
Ahora con dos columnas de precios: +30% y +35%
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
from ..logica import agregar_producto_manual
from ..dialogs.popup_multiples_dialog import PopupMultiplesProductos


class CatalogoTab:
    """Pestaña del catálogo de productos adicionales"""
        
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.catalogo_data = None
        self.botones_filtro = {}
        self.filtro_activo = tk.StringVar(value="TODOS")
        
        # Crear frame principal
        self.frame = ttk.Frame(parent)
        self.frame.configure(style="Background.TFrame")
        
        # Cargar catálogo
        self.cargar_catalogo()
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Enfocar búsqueda al entrar a la pestaña
        def enfocar_busqueda_catalogo(event=None):
            self.busqueda_entry.focus_set()
        
        self.frame.bind("<Visibility>", enfocar_busqueda_catalogo)
    
    def cargar_catalogo(self):
        """Carga el catálogo desde Excel"""
        try:
            import pandas as pd
            ruta_catalogo = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "catalogo_productos.xlsx"
            )
            
            if os.path.exists(ruta_catalogo):
                df = pd.read_excel(ruta_catalogo)
                
                # Construir estructura jerárquica
                self.catalogo_data = {"categorias": []}
                
                for categoria in df['Categoria'].unique():
                    cat_data = {
                        "nombre": categoria,
                        "icono": self.obtener_icono(categoria),
                        "collapsed": False if categoria == df['Categoria'].unique()[0] else True,
                        "subcategorias": []
                    }
                    
                    df_cat = df[df['Categoria'] == categoria]
                    
                    for subcategoria in df_cat['Subcategoria'].unique():
                        df_sub = df_cat[df_cat['Subcategoria'] == subcategoria]
                        
                        subcat_data = {
                            "nombre": subcategoria,
                            "icono": "📏",
                            "collapsed": False if subcategoria == df_cat['Subcategoria'].iloc[0] else True,
                            "productos": df_sub[['Descripcion', 'Unidad', 'Precio +30%', 'Presentacion']].rename(
                                columns={
                                    'Descripcion': 'descripcion',
                                    'Unidad': 'unidad',
                                    'Precio +30%': 'precio_30',
                                    'Presentacion': 'presentacion'
                                }
                            ).to_dict('records')
                        }
                        
                        # Calcular precio +35% para cada producto
                        for prod in subcat_data['productos']:
                            precio_30 = prod.get('precio_30', 0.0)
                            # Fórmula: precio_35 = precio_30 * 1.35 / 1.30
                            prod['precio_35'] = precio_30 * (0.70 / 0.65) if precio_30 > 0 else 0.0
                        
                        cat_data['subcategorias'].append(subcat_data)
                    
                    self.catalogo_data['categorias'].append(cat_data)
                
                print(f"✅ Catálogo cargado: {len(df)} productos")
            else:
                print(f"⚠️ No se encontró: {ruta_catalogo}")
                self.catalogo_data = {"categorias": []}
                
        except Exception as e:
            print(f"❌ Error cargando catálogo: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"No se pudo cargar el catálogo:\n{e}")
            self.catalogo_data = {"categorias": []}
    
    def obtener_icono(self, categoria):
        """Retorna icono según categoría"""
        iconos = {
            "EMT": "🔌",
            "CAJAS": "📦",
            "PERNERÍA": "🔩"
        }
        return iconos.get(categoria, "📦")
    
    def crear_interfaz(self):
        """Crea la interfaz del catálogo"""
        # Frame superior con búsqueda y botones
        self.crear_toolbar()
        
        # Frame con tabla de productos
        self.crear_area_productos()
        
        # Footer con información
        self.crear_footer()

        # Configurar shortcuts
        self.configurar_shortcuts()

    def configurar_shortcuts(self):
        """Configura todos los shortcuts del catálogo"""
        
        # Enter para agregar con popup
        self.tree.bind("<Return>", lambda e: self.agregar_desde_tree())
        self.tree.bind("<KP_Enter>", lambda e: self.agregar_desde_tree())
        
        # Doble click también
        self.tree.bind("<Double-1>", lambda e: self.agregar_desde_tree())
        
        # Ctrl+F para enfocar búsqueda
        self.app.root.bind("<Control-f>", lambda e: self.verificar_y_enfocar_busqueda(e))
        
        # Esc en búsqueda para volver a tabla
        self.busqueda_entry.bind("<Escape>", lambda e: self.tree.focus_set())
        
        # Flechas en búsqueda mueven la tabla
        self.busqueda_entry.bind("<Down>", lambda e: self.mover_seleccion_abajo())
        self.busqueda_entry.bind("<Up>", lambda e: self.mover_seleccion_arriba())
        self.busqueda_entry.bind("<Return>", lambda e: self.agregar_desde_tree())
        
        # Función auxiliar para filtros
        def aplicar_filtro_shortcut(cat):
            if self.app.notebook.index(self.app.notebook.select()) == 2:
                self.aplicar_filtro(cat)
            return "break"
        
        # Ctrl+0/1/2/3 para filtros rápidos
        self.app.root.bind("<Control-Key-0>", lambda e: aplicar_filtro_shortcut("TODOS"))
        self.app.root.bind("<Control-Key-1>", lambda e: aplicar_filtro_shortcut("EMT"))
        self.app.root.bind("<Control-Key-2>", lambda e: aplicar_filtro_shortcut("CAJAS"))
        self.app.root.bind("<Control-Key-3>", lambda e: aplicar_filtro_shortcut("PERNERÍA"))
        
        # Ctrl+M para medidas
        self.app.root.bind("<Control-m>", lambda e: (self.subcategoria_combo.focus() if self.app.notebook.index(self.app.notebook.select()) == 2 else None, "break")[1])

    def mover_seleccion_abajo(self):
        """Mueve selección abajo sin perder foco en búsqueda"""
        items = self.tree.get_children()
        if not items:
            return "break"
        
        selection = self.tree.selection()
        if not selection:
            # Seleccionar primero
            self.tree.selection_set(items[0])
            self.tree.see(items[0])
        else:
            # Mover al siguiente
            current = selection[0]
            idx = items.index(current)
            if idx < len(items) - 1:
                next_item = items[idx + 1]
                self.tree.selection_set(next_item)
                self.tree.see(next_item)
        
        return "break"

    def mover_seleccion_arriba(self):
        """Mueve selección arriba sin perder foco en búsqueda"""
        items = self.tree.get_children()
        if not items:
            return "break"
        
        selection = self.tree.selection()
        if not selection:
            # Seleccionar último
            self.tree.selection_set(items[-1])
            self.tree.see(items[-1])
        else:
            # Mover al anterior
            current = selection[0]
            idx = items.index(current)
            if idx > 0:
                prev_item = items[idx - 1]
                self.tree.selection_set(prev_item)
                self.tree.see(prev_item)
        
        return "break"

    def verificar_y_enfocar_busqueda(self, event):
        """Verifica que estemos en catálogo antes de enfocar búsqueda"""
        if self.app.notebook.index(self.app.notebook.select()) == 2:
            self.busqueda_entry.focus_set()
            self.busqueda_entry.select_range(0, 'end')
            return "break"

    def enfocar_busqueda(self):
        """Enfoca el campo de búsqueda"""
        self.busqueda_entry.focus_set()
        self.busqueda_entry.select_range(0, 'end')

    def crear_toolbar(self):
        """Crea la barra de herramientas superior"""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", padx=15, pady=(15, 10))
        
        # FILA 1: Filtros rápidos por categoría
        filtros_frame = ttk.Frame(toolbar)
        filtros_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(filtros_frame, text="🔍 Filtrar:", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 10))
        
        # Botones de filtro
        filtros = [
            ("EMT", ""),
            ("CAJAS", ""),
            ("PERNERÍA", ""),
            ("TODOS", "")
        ]
        
        for nombre, icono in filtros:
            estilo = "Accent.TButton" if nombre == "TODOS" else "TButton"
            btn = ttk.Button(
                filtros_frame,
                text=f"{icono} {nombre}",
                command=lambda n=nombre: self.aplicar_filtro(n),
                width=14,
                style=estilo
            )
            btn.pack(side="left", padx=2)
            self.botones_filtro[nombre] = btn
        
        # Separador
        ttk.Separator(filtros_frame, orient="vertical").pack(side="left", fill="y", padx=10)
        
        # Filtro de subcategoría
        ttk.Label(filtros_frame, text="📏 Medida:", font=("Arial", 10)).pack(side="left", padx=(0, 5))
        
        self.subcategoria_var = tk.StringVar(value="Todas")
        self.subcategoria_combo = ttk.Combobox(
            filtros_frame,
            textvariable=self.subcategoria_var,
            state="readonly",
            width=18
        )
        self.subcategoria_combo.pack(side="left", padx=(0, 10))
        self.subcategoria_combo.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtro_subcategoria())
        
        # Actualizar opciones de subcategoría
        self.actualizar_subcategorias()
        
        # FILA 2: Búsqueda y otros botones
        busqueda_frame = ttk.Frame(toolbar)
        busqueda_frame.pack(fill="x")
        
        ttk.Label(busqueda_frame, text="🔎 Buscar:", font=("Arial", 10)).pack(side="left", padx=(0, 5))
        
        self.busqueda_var = tk.StringVar()
        self.busqueda_var.trace('w', self.filtrar_productos)
        
        self.busqueda_entry = ttk.Entry(busqueda_frame, textvariable=self.busqueda_var, width=30)
        self.busqueda_entry.pack(side="left", padx=(0, 15))
        
        # Botones de acción
        ttk.Button(busqueda_frame, text="🔄 Recargar", 
                command=self.recargar_catalogo, width=12).pack(side="left", padx=5)
        
        ttk.Button(busqueda_frame, text="⚙️ Gestionar", 
                command=self.abrir_gestion, width=12).pack(side="right", padx=5)
        
        ttk.Button(busqueda_frame, text="❓ Ayuda", 
          command=self.mostrar_ayuda_catalogo, width=10).pack(side="right", padx=5)

    def actualizar_subcategorias(self):
        """Actualiza las opciones del combobox de subcategorías según filtro activo"""
        if not self.catalogo_data:
            return
        
        subcategorias = ["Todas"]
        categoria_activa = self.filtro_activo.get()
        
        if categoria_activa == "TODOS":
            # Mostrar todas las subcategorías de todas las categorías
            for cat in self.catalogo_data['categorias']:
                for subcat in cat.get('subcategorias', []):
                    subcategorias.append(subcat['nombre'])
        else:
            # Mostrar solo subcategorías de la categoría activa
            for cat in self.catalogo_data['categorias']:
                if cat['nombre'] == categoria_activa:
                    for subcat in cat.get('subcategorias', []):
                        subcategorias.append(subcat['nombre'])
                    break
        
        self.subcategoria_combo['values'] = subcategorias
        self.subcategoria_combo.set("Todas")

    def aplicar_filtro_subcategoria(self):
        """Aplica filtro por subcategoría"""
        subcategoria = self.subcategoria_var.get()
        
        if subcategoria == "Todas":
            # Recargar con el filtro de categoría actual
            self.aplicar_filtro(self.filtro_activo.get())
            return
        
        # Filtrar por subcategoría
        self.llenar_tabla()
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            cat_item = values[0]
            subcat_item = values[1]
            
            # Aplicar filtro de categoría Y subcategoría
            categoria_ok = (self.filtro_activo.get() == "TODOS" or cat_item == self.filtro_activo.get())
            subcategoria_ok = (subcat_item == subcategoria)
            
            if not (categoria_ok and subcategoria_ok):
                self.tree.delete(item)
        
        # Actualizar status
        self.status_label.configure(
            text=f"Filtrando: {self.filtro_activo.get()} - {subcategoria}",
            foreground="blue"
        )

    def crear_area_productos(self):
        """Crea el área de productos en formato tabla plana con DOS COLUMNAS DE PRECIOS"""
        container = ttk.Frame(self.frame)
        container.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Crear Treeview con columnas para ambos precios - SELECCIÓN MÚLTIPLE HABILITADA
        columns = ("categoria", "subcategoria", "descripcion", "unidad", "precio_30", "precio_35", "presentacion", "accion")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=20, selectmode="extended")

        # Habilitar selección múltiple correctamente
        self.tree.configure(selectmode="extended")

        # Configurar columnas
        self.tree.heading("categoria", text="Categoría")
        self.tree.heading("subcategoria", text="Subcategoría")
        self.tree.heading("descripcion", text="Descripción")
        self.tree.heading("unidad", text="Unidad")
        self.tree.heading("precio_30", text="Precio +30%")
        self.tree.heading("precio_35", text="Precio +35%")
        self.tree.heading("presentacion", text="Presentación")
        self.tree.heading("accion", text="Acción")
        
        self.tree.column("categoria", width=100, anchor="center")
        self.tree.column("subcategoria", width=120, anchor="center")
        self.tree.column("descripcion", width=280, anchor="w")
        self.tree.column("unidad", width=70, anchor="center")
        self.tree.column("precio_30", width=90, anchor="center")
        self.tree.column("precio_35", width=90, anchor="center")
        self.tree.column("presentacion", width=100, anchor="center")
        self.tree.column("accion", width=80, anchor="center")
        
        # Scrollbar vertical
        scrollbar_y = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        
        # Scrollbar horizontal
        scrollbar_x = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=scrollbar_x.set)
        
        # Pack
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Eventos
        self.tree.bind("<Double-1>", lambda e: self.agregar_desde_tree())

        # Estilos base
        self.tree.tag_configure('sin_precio', background='#ffcccc')
        self.tree.tag_configure('emt', background='#e3f2fd')
        self.tree.tag_configure('cajas', background='#fff3e0')
        self.tree.tag_configure('perneria', background='#f3e5f5')
        
        # Llenar datos
        self.llenar_tabla()
 
    def llenar_tabla(self):
        """Llena la tabla con todos los productos mostrando ambos precios"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.catalogo_data or not self.catalogo_data.get('categorias'):
            return
        
        # Insertar productos
        for categoria in self.catalogo_data['categorias']:
            nombre_cat = categoria['nombre']
            
            for subcategoria in categoria.get('subcategorias', []):
                nombre_subcat = subcategoria['nombre']
                
                for producto in subcategoria.get('productos', []):
                    descripcion = producto.get('descripcion', '')
                    unidad = producto.get('unidad', 'UND')
                    precio_30 = producto.get('precio_30', 0.0)
                    precio_35 = producto.get('precio_35', 0.0)
                    presentacion = producto.get('presentacion', '')
                    
                    # Tags para estilo
                    tags = []
                    if precio_30 == 0.0:
                        tags.append('sin_precio')
                    
                    if nombre_cat == 'EMT':
                        tags.append('emt')
                    elif nombre_cat == 'CAJAS':
                        tags.append('cajas')
                    elif nombre_cat == 'PERNERÍA':
                        tags.append('perneria')
                    
                    self.tree.insert("", "end", values=(
                        nombre_cat,
                        nombre_subcat,
                        descripcion,
                        unidad,
                        f"{precio_30:.2f}",
                        f"{precio_35:.2f}",
                        presentacion,
                        "➕ Agregar"
                    ), tags=tuple(tags))
    
    def obtener_porcentaje_activo(self):
        """Obtiene el porcentaje de ganancia seleccionado en la pestaña Cotización"""
        try:
            # Acceder a la variable ganancia_var de la pestaña de cotización
            return self.app.cotizacion_tab.ganancia_var.get()
        except:
            # Por defecto retornar 30%
            return "30"
    
    def agregar_desde_tree(self):
        """Agrega uno o múltiples productos desde el tree al carrito"""
        selections = self.tree.selection()
        if not selections:
            return
        
        # Si solo hay 1 producto seleccionado, usar popup normal
        if len(selections) == 1:
            self.agregar_producto_individual(selections[0])
        else:
            # Múltiples productos seleccionados
            self.agregar_productos_multiples(selections)

    def agregar_producto_individual(self, item):
        """Agrega un solo producto (código original)"""
        # Obtener datos del producto
        item_values = self.tree.item(item)['values']
        categoria = item_values[0]
        subcategoria = item_values[1]
        descripcion = item_values[2]
        unidad = item_values[3]
        precio_30_str = item_values[4]
        precio_35_str = item_values[5]
        
        try:
            precio_30 = float(precio_30_str)
            precio_35 = float(precio_35_str)
            
            # Obtener porcentaje activo desde la pestaña Cotización
            porcentaje_activo = self.obtener_porcentaje_activo()
            
            # Seleccionar precio según el porcentaje
            if porcentaje_activo == "35":
                precio = precio_35
                label_porcentaje = "CON COMISIÓN"
            else:
                precio = precio_30
                label_porcentaje = "SIN COMISIÓN"
            
            # Verificar precio
            if precio <= 0:
                messagebox.showwarning(
                    "Precio no disponible",
                    f"El producto '{descripcion}' no tiene precio configurado.\n\n"
                    "Por favor, actualice el catálogo primero."
                )
                return
            
            # Mostrar popup para cantidad
            self.mostrar_popup_cantidad(descripcion, unidad, precio, 0, porcentaje_activo, label_porcentaje)
            
        except ValueError:
            messagebox.showerror("Error", "Error al leer el precio del producto.")

    def agregar_productos_multiples(self, selections):
        """Muestra popup para agregar múltiples productos a la vez"""
        productos_lista = []
        porcentaje_activo = self.obtener_porcentaje_activo()
        label_porcentaje = "CON COMISIÓN" if porcentaje_activo == "35" else "SIN COMISIÓN"
        
        # Recopilar información de todos los productos seleccionados
        for item in selections:
            item_values = self.tree.item(item)['values']
            descripcion = item_values[2]
            unidad = item_values[3]
            precio_30_str = item_values[4]
            precio_35_str = item_values[5]
            
            try:
                precio_30 = float(precio_30_str)
                precio_35 = float(precio_35_str)
                
                # Seleccionar precio según porcentaje
                precio = precio_35 if porcentaje_activo == "35" else precio_30
                
                if precio > 0:
                    productos_lista.append({
                        'descripcion': descripcion,
                        'unidad': unidad,
                        'precio': precio
                    })
            except ValueError:
                continue
        
        if not productos_lista:
            messagebox.showwarning("Advertencia", "Ningún producto seleccionado tiene precio válido.")
            return
        
        # Mostrar popup con todos los productos
        self.mostrar_popup_multiples(productos_lista, label_porcentaje)

    def mostrar_popup_multiples(self, productos, label_porcentaje):
        """Popup para agregar múltiples productos al carrito."""
        def on_agregar(count):
            self.app.carrito_tab.actualizar_carrito()
            self.status_label.configure(
                text=f"✅ {count} productos agregados - {label_porcentaje}",
                foreground="green"
            )

        PopupMultiplesProductos(
            self.app.root, productos, label_porcentaje,
            callback_agregar=on_agregar
        )

    def mostrar_popup_cantidad(self, descripcion, unidad, precio, peso, porcentaje, label_porcentaje):
        """Muestra popup para ingresar cantidad con indicador de porcentaje usado"""
        dialogo = tk.Toplevel(self.app.root)
        dialogo.title("Agregar al Carrito")
        dialogo.resizable(False, False)
        dialogo.transient(self.app.root)
        dialogo.grab_set()
        
        # Centrar ventana
        dialogo.update_idletasks()
        x = (dialogo.winfo_screenwidth() // 2) - 225
        y = (dialogo.winfo_screenheight() // 2) - 125
        dialogo.geometry(f"350x280+{x}+{y}")
        
        # Contenido
        main_frame = ttk.Frame(dialogo, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Descripción
        ttk.Label(
            main_frame, 
            text="Producto:", 
            font=("Arial", 10, "bold")
        ).pack(anchor="w")
        
        desc_text = descripcion if len(descripcion) <= 50 else descripcion[:47] + "..."
        ttk.Label(
            main_frame, 
            text=desc_text,
            wraplength=400
        ).pack(anchor="w", pady=(0, 10))
        
        # Info con indicador de porcentaje
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(info_frame, text=f"💰 Precio ({label_porcentaje}): S/ {precio:.2f}").pack(side="left", padx=(0, 15))
        
        # Indicador de porcentaje activo
        porcentaje_label = ttk.Label(
            main_frame,
            text=f"📊 Usando margen: {label_porcentaje}",
            font=("Arial", 9, "italic"),
            foreground="#0078d4"
        )
        porcentaje_label.pack(anchor="w", pady=(0, 10))
        
        # Cantidad
        ttk.Label(
            main_frame, 
            text=f"Cantidad ({unidad}):", 
            font=("Arial", 10, "bold")
        ).pack(anchor="w", pady=(0, 5))
        
        cantidad_var = tk.StringVar(value="0")
        cantidad_entry = ttk.Entry(main_frame, textvariable=cantidad_var, width=15, font=("Arial", 11))
        cantidad_entry.pack(anchor="w", pady=(0, 15))
        cantidad_entry.focus()
        cantidad_entry.select_range(0, 'end')
        
        # Total dinámico
        total_var = tk.StringVar(value=f"Total: S/ {precio:.2f}")
        total_label = ttk.Label(
            main_frame, 
            textvariable=total_var, 
            font=("Arial", 11, "bold"),
            foreground="#0078d4"
        )
        total_label.pack(anchor="w", pady=(0, 15))
        
        def actualizar_total(*args):
            try:
                cant = int(cantidad_var.get())
                if cant > 0:
                    total = precio * cant
                    total_var.set(f"Total: S/ {total:.2f}")
                else:
                    total_var.set("Total: S/ 0.00")
            except:
                total_var.set("Total: S/ ---")
        
        cantidad_var.trace('w', actualizar_total)
        
        # Botones
        def agregar():
            try:
                cantidad = int(cantidad_var.get())
                if cantidad <= 0:
                    messagebox.showerror("Error", "La cantidad debe ser mayor a 0")
                    cantidad_var.set("0")
                    cantidad_entry.focus()
                    cantidad_entry.select_range(0, 'end')
                    return
                
                # Agregar al carrito usando la función de logica.py
                agregar_producto_manual(descripcion, unidad, precio, peso, cantidad)
                
                # Actualizar carrito en GUI
                self.app.carrito_tab.actualizar_carrito()
                
                # Cerrar diálogo
                dialogo.destroy()
                
                # Actualizar status
                self.status_label.configure(
                    text=f"✅ Agregado: {descripcion} ({cantidad} {unidad}) - {label_porcentaje}",
                    foreground="green"
                )
                
            except ValueError:
                # Si no es número válido, resetear a 1 sin popup
                cantidad_var.set("1")
        
        botones_frame = ttk.Frame(main_frame)
        botones_frame.pack(fill="x")
        
        ttk.Button(
            botones_frame, 
            text="➕ Agregar al Carrito", 
            command=agregar,
            style="Accent.TButton"
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        ttk.Button(
            botones_frame,
            text="✖ Cancelar",
            command=dialogo.destroy
        ).pack(side="right", expand=True, fill="x", padx=(5, 0))
        
        # Shortcuts
        dialogo.bind("<Return>", lambda e: agregar())
        dialogo.bind("<Escape>", lambda e: dialogo.destroy())
    
    def filtrar_productos(self, *args):
        """Filtra productos según búsqueda en tiempo real"""
        termino = self.busqueda_var.get().lower()
        
        if not termino:
            # Si no hay búsqueda, aplicar solo filtros de categoría/subcategoría
            categoria_activa = self.filtro_activo.get()
            subcategoria_activa = self.subcategoria_var.get()
            
            if categoria_activa != "TODOS" or subcategoria_activa != "Todas":
                if subcategoria_activa != "Todas":
                    self.aplicar_filtro_subcategoria()
                else:
                    self.aplicar_filtro(categoria_activa)
            else:
                self.llenar_tabla()
            return
        
        # Filtrar por búsqueda
        self.llenar_tabla()
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            descripcion = str(values[2]).lower()
            categoria = str(values[0]).lower()
            subcategoria = str(values[1]).lower()
            
            # Buscar en descripción, categoría o subcategoría
            if termino not in descripcion and termino not in categoria and termino not in subcategoria:
                self.tree.delete(item)
        
        # Actualizar status
        items_visibles = len(self.tree.get_children())
        self.status_label.configure(
            text=f"🔍 Búsqueda: '{self.busqueda_var.get()}' - {items_visibles} resultados",
            foreground="blue"
        )
        
        # Seleccionar primer resultado
        items = self.tree.get_children()
        if items:
            self.tree.selection_set(items[0])
            self.tree.see(items[0])
    
    def limpiar_busqueda(self):
        """Limpia búsqueda y vuelve a tabla"""
        self.busqueda_var.set("")
        self.tree.focus()
        return "break"

    def crear_footer(self):
        """Crea el footer con información"""
        footer = ttk.Frame(self.frame)
        footer.pack(fill="x", padx=15, pady=(5, 15))
        
        # Frame izquierdo
        left_frame = ttk.Frame(footer)
        left_frame.pack(side="left")
        
        # Contador de productos
        total_productos = 0
        if self.catalogo_data and self.catalogo_data.get('categorias'):
            for cat in self.catalogo_data['categorias']:
                for subcat in cat.get('subcategorias', []):
                    total_productos += len(subcat.get('productos', []))
        
        self.info_label = ttk.Label(
            left_frame,
            text=f"📦 Total de productos: {total_productos}",
            font=("Arial", 9)
        )
        self.info_label.pack(side="left", padx=(0, 20))
        
        # Indicador de porcentaje activo
        porcentaje_activo = self.obtener_porcentaje_activo()
        self.porcentaje_footer = ttk.Label(
            left_frame,
            text=f"📊 Margen activo: +{porcentaje_activo}%",
            font=("Arial", 9, "bold"),
            foreground="#0078d4"
        )
        self.porcentaje_footer.pack(side="left")
        
        # Frame derecho para status
        right_frame = ttk.Frame(footer)
        right_frame.pack(side="right")
        
        self.status_label = ttk.Label(
            right_frame,
            text="Listo",
            font=("Arial", 9),
            foreground="gray"
        )
        self.status_label.pack()
        
        # Actualizar indicador de porcentaje cada segundo
        def actualizar_porcentaje():
            porcentaje = self.obtener_porcentaje_activo()
            margen_texto = "CON COMISIÓN" if porcentaje == "35" else "SIN COMISIÓN"
            self.porcentaje_footer.configure(text=f"📊 Margen activo: {margen_texto}")
            self.frame.after(1000, actualizar_porcentaje)
        
        actualizar_porcentaje()

    def aplicar_filtro(self, categoria):
        """Aplica filtro por categoría"""
        self.filtro_activo.set(categoria)
        
        # Actualizar estilos de botones
        for nombre, btn in self.botones_filtro.items():
            if nombre == categoria:
                btn.configure(style="Accent.TButton")
            else:
                btn.configure(style="TButton")
        
        # Limpiar búsqueda
        self.busqueda_var.set("")
        
        # Actualizar subcategorías disponibles
        self.actualizar_subcategorias()
        
        # Recargar toda la tabla
        self.llenar_tabla()
        
        # Si no es TODOS, ocultar los que no coinciden
        if categoria != "TODOS":
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                cat_item = values[0]
                
                if cat_item != categoria:
                    self.tree.delete(item)
        
        # Actualizar status
        if categoria == "TODOS":
            self.status_label.configure(text="Mostrando todas las categorías", foreground="gray")
        else:
            self.status_label.configure(text=f"Filtrando: {categoria}", foreground="blue")
        
        # Volver a enfocar búsqueda y seleccionar primer item
        self.busqueda_entry.focus_set()
        items = self.tree.get_children()
        if items:
            self.tree.selection_set(items[0])
            self.tree.see(items[0])

    def recargar_catalogo(self):
        """Recarga el catálogo desde el archivo"""
        # Recargar
        self.cargar_catalogo()
        self.llenar_tabla()
        
        # Actualizar footer
        total_productos = 0
        if self.catalogo_data and self.catalogo_data.get('categorias'):
            for cat in self.catalogo_data['categorias']:
                for subcat in cat.get('subcategorias', []):
                    total_productos += len(subcat.get('productos', []))
        
        self.info_label.configure(text=f"📦 Total de productos: {total_productos}")
        self.status_label.configure(text="✅ Catálogo recargado correctamente", foreground="green")
        
        messagebox.showinfo("Éxito", "✅ Catálogo recargado correctamente")
    
    def abrir_gestion(self):
        """Abre ventana de gestión del catálogo"""
        messagebox.showinfo(
            "Próximamente",
            "🚧 La gestión de catálogo estará disponible próximamente.\n\n"
            "Por ahora, puede editar el archivo:\n"
            "catalogo_productos.xlsx"
        )

    def mostrar_ayuda_catalogo(self):
        """Muestra ayuda de shortcuts del catálogo"""
        ayuda = tk.Toplevel(self.app.root)
        ayuda.title("Ayuda - Catálogo")
        ayuda.geometry("650x550")
        ayuda.resizable(False, False)
        ayuda.transient(self.app.root)
        ayuda.grab_set()
        
        # Centrar
        ayuda.update_idletasks()
        x = (ayuda.winfo_screenwidth() // 2) - 325
        y = (ayuda.winfo_screenheight() // 2) - 275
        ayuda.geometry(f"650x550+{x}+{y}")
        
        # Contenido
        main_frame = ttk.Frame(ayuda, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        ttk.Label(
            main_frame,
            text="📋 Guía de Catálogo - Shortcuts y Flujo",
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 20))
        
        # Canvas con scroll
        canvas = tk.Canvas(main_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        contenido = ttk.Frame(canvas)
        
        contenido.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=contenido, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Contenido de ayuda
        ayuda_texto = """
    🔍 FLUJO BÁSICO:
    1. Al entrar a Catálogo → Campo de búsqueda enfocado
    2. Escribe para filtrar productos
    3. Usa ↑↓ para navegar resultados (sin salir de búsqueda)
    4. Presiona Enter para agregar producto
    5. 💡 NUEVO: Usa Ctrl+Click para seleccionar múltiples productos

    💰 PRECIOS DINÁMICOS:
    • El catálogo muestra DOS columnas de precios:
      - Precio SIN COMISIÓN 
      - Precio CON COMISIÓN 
    • El precio usado depende del margen seleccionado en la pestaña COTIZACIÓN
    • El footer muestra qué margen está activo
    • Cambia el margen en Cotización y se aplicará automáticamente

    ⌨️ NAVEGACIÓN:
    • ↑ ↓         - Navegar entre productos (desde búsqueda o tabla)
    • Enter       - Agregar producto seleccionado
    • Ctrl+Click  - Seleccionar múltiples productos
    • Esc         - Desde búsqueda: volver a tabla
    • Ctrl+F      - Enfocar campo de búsqueda
    • Tab         - Cambiar entre campos

    🔧 FILTROS RÁPIDOS:
    • Ctrl+0      - Mostrar TODOS los productos
    • Ctrl+1      - Filtrar solo EMT
    • Ctrl+2      - Filtrar solo CAJAS
    • Ctrl+3      - Filtrar solo PERNERÍA
    • Ctrl+M      - Ir al selector de medidas (subcategorías)

    🎯 CONSEJOS:
    • No necesitas hacer click en nada, todo funciona con teclado
    • La búsqueda filtra en tiempo real
    • Puedes combinar filtros de categoría + medida + búsqueda
    • El doble click también agrega productos
    • Los colores indican categorías:
        - Azul claro: EMT
        - Naranja claro: CAJAS
        - Morado claro: PERNERÍA
        - Rojo: Sin precio configurado

    📊 TABLA:
    • Categoría     - Tipo principal (EMT, CAJAS, PERNERÍA)
    • Subcategoría  - Medida específica (1/2", 3/4", etc.)
    • Descripción   - Nombre completo del producto
    • Unidad        - UND, ML, etc.
    • Precio SIN COMISIÓN
    • Precio CON COMISIÓN
    • Presentación  - Empaque (PQT20, CAJ.150, etc.)
    """
        
        texto = tk.Text(
            contenido,
            wrap="word",
            width=75,
            height=28,
            font=("Consolas", 10),
            bg="#f5f5f5",
            relief="flat",
            padx=10,
            pady=10
        )
        texto.insert("1.0", ayuda_texto)
        texto.configure(state="disabled")
        texto.pack(fill="both", expand=True)
        
        # Shortcuts
        ayuda.bind("<Escape>", lambda e: ayuda.destroy())
        ayuda.bind("<Return>", lambda e: ayuda.destroy())
