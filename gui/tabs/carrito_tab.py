# -*- coding: utf-8 -*-
"""
Pestana del carrito de compras
"""
import tkinter as tk
from tkinter import ttk, messagebox
from ..logica import carrito, limpiar_carrito, eliminar_producto_carrito  # <- DOS PUNTOS
from ..dialogs import abrir_dialogo_agregar_manual, abrir_dialogo_modificar_cantidad

class CarritoTab:
    """Pestana del carrito de compras"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Crear frame principal
        self.frame = ttk.Frame(parent)
        self.frame.configure(style="Background.TFrame")
        
        # Crear interfaz
        self.crear_interfaz()

        # Variables
        self.atenciones_completas = {}

        # Configurar shortcuts del carrito
        self.configurar_shortcuts_carrito()

        # Enfocar RAZON SOCIAL al mostrar la pestaña
        def enfocar_razon_social(event=None):
            self.razon_social_combo.focus_set()
        
        self.frame.bind("<Visibility>", enfocar_razon_social)
    
    def crear_interfaz(self):
        """Crea la interfaz del carrito"""
        # Seccion de informacion del proyecto
        self.crear_seccion_proyecto()
        
        # Toolbar
        self.crear_toolbar()
        
        # Treeview del carrito
        self.crear_treeview()
        
        # Totales
        self.crear_seccion_totales()
        
    def crear_seccion_proyecto(self):
        """Crea la seccion de informacion del proyecto"""
        info_frame = ttk.LabelFrame(self.frame, text="Informacion del Proyecto", padding=10)
        info_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        self.proyecto_var = tk.StringVar()
        self.titulo_provisional_var = tk.StringVar()
        self.razon_social_var = tk.StringVar()
        self.atencion_var = tk.StringVar()
        self.moneda_var = tk.StringVar()
        
        # Bandera para evitar duplicados
        self.autocompletando = False
        
        # Primera fila: PROYECTO y TITULO PROVISIONAL
        fila1_frame = ttk.Frame(info_frame)
        fila1_frame.pack(fill="x", pady=(0, 8))
        
        proyecto_frame = ttk.Frame(fila1_frame)
        proyecto_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(proyecto_frame, text="PROYECTO:", font=("Arial", 9, "bold")).pack(side="left")
        self.proyecto_entry = ttk.Entry(proyecto_frame, textvariable=self.proyecto_var, width=25)
        self.proyecto_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        
        titulo_frame = ttk.Frame(fila1_frame)
        titulo_frame.pack(side="right", fill="x", expand=True)
        ttk.Label(titulo_frame, text="TITULO PROVISIONAL:", font=("Arial", 9, "bold")).pack(side="left")
        ttk.Entry(titulo_frame, textvariable=self.titulo_provisional_var, width=30).pack(
            side="left", padx=(5, 0), fill="x", expand=True
        )
        
        # Segunda fila: RAZON SOCIAL, ATENCION y MONEDA
        fila2_frame = ttk.Frame(info_frame)
        fila2_frame.pack(fill="x")
        
        razon_frame = ttk.Frame(fila2_frame)
        razon_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(razon_frame, text="RAZON SOCIAL:", font=("Arial", 9, "bold")).pack(side="left")
        self.razon_social_combo = ttk.Combobox(razon_frame, textvariable=self.razon_social_var, width=20)
        self.razon_social_combo.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.razon_social_combo.bind('<<ComboboxSelected>>', self.on_razon_social_change)
        
        # Forzar mayúsculas automáticamente
        def forzar_mayusculas(*args):
            valor = self.razon_social_var.get()
            if valor != valor.upper():
                cursor_pos = self.razon_social_combo.index('insert')
                self.razon_social_var.set(valor.upper())
                self.razon_social_combo.icursor(cursor_pos)
        
        self.razon_social_var.trace('w', forzar_mayusculas)
        
        # Manejar autocompletado
        def manejar_tecla_razon(event):
            # Ignorar teclas especiales
            if event.keysym in ('Tab', 'Return', 'BackSpace', 'Delete', 'Left', 'Right', 'Up', 'Down', 'Shift_L', 'Shift_R'):
                return
            
            # Si ya está autocompletando, no hacer nada
            if self.autocompletando:
                return
            
            # Si es una letra
            if len(event.char) == 1 and event.char.isalpha():
                cursor_pos = self.razon_social_combo.index('insert')
                
                # Cancelar autocompletado anterior si existe
                if hasattr(self, '_autocompletar_timer') and self._autocompletar_timer:
                    self.app.root.after_cancel(self._autocompletar_timer)
                
                # Autocompletar después de un delay
                self._autocompletar_timer = self.app.root.after(100, lambda: autocompletar_razon_despues(cursor_pos + 1))
        
        def autocompletar_razon_despues(cursor_pos):
            self._autocompletar_timer = None  # Limpiar timer
            valor = self.razon_social_var.get()
            
            # Solo autocompletar si el cursor está al final
            if valor and cursor_pos == len(valor):
                opciones = self.razon_social_combo['values']
                for opcion in opciones:
                    if len(opcion) > len(valor) and opcion.upper().startswith(valor.upper()):
                        self.autocompletando = True
                        self.razon_social_combo.set(opcion)
                        self.razon_social_combo.icursor(cursor_pos)
                        self.razon_social_combo.selection_range(cursor_pos, 'end')
                        # Desactivar bandera
                        self.app.root.after(200, lambda: setattr(self, 'autocompletando', False))
                        break
        
        self.razon_social_combo.bind('<Key>', manejar_tecla_razon)
        
        atencion_frame = ttk.Frame(fila2_frame)
        atencion_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(atencion_frame, text="ATENCION:", font=("Arial", 9, "bold")).pack(side="left")
        self.atencion_combo = ttk.Combobox(atencion_frame, textvariable=self.atencion_var, width=20)
        self.atencion_combo.pack(side="left", padx=(5, 0), fill="x", expand=True)
        
        moneda_frame = ttk.Frame(fila2_frame)
        moneda_frame.pack(side="right")
        ttk.Label(moneda_frame, text="MONEDA:", font=("Arial", 9, "bold")).pack(side="left")
        self.moneda_combo = ttk.Combobox(moneda_frame, textvariable=self.moneda_var, width=10, state="readonly")
        self.moneda_combo.pack(side="left", padx=(5, 0))

        # Variable para tipo de cambio
        self.tipo_cambio = 1.0  # Por defecto 1 (SOLES)

        # Detectar cambio de moneda
        def on_moneda_change(event):
            moneda = self.moneda_var.get()
            if moneda == "DÓLARES AMERICANOS":
                self.solicitar_tipo_cambio()
            else:
                self.tipo_cambio = 1.0
                self.actualizar_carrito()

        self.moneda_combo.bind('<<ComboboxSelected>>', on_moneda_change)
        
        # Guardar datos completos
        self.atenciones_completas = {}
        
        # Configurar navegación con Tab
        def ir_a_atencion():
            self.on_razon_social_change(None)  # Actualizar atenciones primero
            self.app.root.after(50, lambda: (
                self.atencion_combo.focus_set(),
                self.atencion_combo.event_generate('<Button-1>')
            ))
            return "break"
        
        self.razon_social_combo.bind('<Tab>', lambda e: ir_a_atencion())
        self.atencion_combo.bind('<Tab>', lambda e: (self.proyecto_entry.focus_set(), "break"))

    def crear_toolbar(self):
        """Crea la barra de herramientas"""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", padx=15, pady=(5, 8))
        
        ttk.Button(toolbar, text="Actualizar", command=self.actualizar_carrito, width=10).pack(
            side="left", padx=5
        )
        ttk.Button(toolbar, text="Agregar Manual", command=self.agregar_manual, width=15).pack(
            side="left", padx=5
        )
        ttk.Button(toolbar, text="Modificar", command=self.modificar_cantidad, width=10).pack(
            side="left", padx=5
        )
        ttk.Button(toolbar, text="Eliminar Selec.", command=self.eliminar_seleccionado, width=15).pack(
            side="left", padx=5
        )
        ttk.Button(toolbar, text="Limpiar Todo", command=self.limpiar_carrito_gui, width=12).pack(
            side="left", padx=5
        )
        ttk.Button(toolbar, text="Exportar Excel", command=self.exportar_a_excel, width=15).pack(
            side="left", padx=5
        )
        ttk.Button(toolbar, text="Gestionar Datos", command=self.app.abrir_gestion_datos, width=15).pack(
            side="left", padx=5
        )
        ttk.Button(toolbar, text="Config", command=self.app.abrir_configuracion, width=8).pack(
            side="right", padx=(5, 0)
        )
        ttk.Button(toolbar, text="?", command=self.app.mostrar_ayuda_shortcuts, width=3).pack(
            side="right", padx=(5, 0)
        )
    
    def crear_treeview(self):
        """Crea el treeview del carrito"""
        carrito_container = ttk.Frame(self.frame)
        carrito_container.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(carrito_container)
        tree_scroll_y.pack(side="right", fill="y")
        
        tree_scroll_x = ttk.Scrollbar(carrito_container, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")
        
        # Treeview
        self.carrito_tree = ttk.Treeview(
            carrito_container,
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            selectmode="extended"
        )
        
        tree_scroll_y.config(command=self.carrito_tree.yview)
        tree_scroll_x.config(command=self.carrito_tree.xview)
        
        # Columnas
        self.carrito_tree["columns"] = (
            "item", "descripcion", "unidad", "cantidad", 
            "precio_unit", "precio_total", "peso_total"
        )
        self.carrito_tree["show"] = "headings"
        
        # Encabezados
        self.carrito_tree.heading("item", text="ITEM")
        self.carrito_tree.heading("descripcion", text="DESCRIPCION")
        self.carrito_tree.heading("unidad", text="UND/ML")
        self.carrito_tree.heading("cantidad", text="CANT.")
        self.carrito_tree.heading("precio_unit", text="P. UNIT")
        self.carrito_tree.heading("precio_total", text="TOTAL")
        self.carrito_tree.heading("peso_total", text="PESO")
        
        # Anchos
        self.carrito_tree.column("item", width=50, anchor="center", minwidth=40)
        self.carrito_tree.column("descripcion", width=350, anchor="w", minwidth=280)
        self.carrito_tree.column("unidad", width=70, anchor="center", minwidth=60)
        self.carrito_tree.column("cantidad", width=70, anchor="center", minwidth=60)
        self.carrito_tree.column("precio_unit", width=90, anchor="center", minwidth=80)
        self.carrito_tree.column("precio_total", width=100, anchor="center", minwidth=90)
        self.carrito_tree.column("peso_total", width=80, anchor="center", minwidth=70)
        
        self.carrito_tree.pack(fill="both", expand=True)
    
    def crear_seccion_totales(self):
        """Crea la seccion de totales"""
        totales_frame = ttk.LabelFrame(self.frame, text="Totales", padding=10)
        totales_frame.pack(fill="x", padx=15, pady=8)
        
        self.lbl_total_precio = ttk.Label(
            totales_frame, 
            text="Precio Total SIN IGV: S/0.00", 
            font=("Arial", 12, "bold")
        )
        self.lbl_total_precio.pack(side="left")
        
        self.lbl_total_peso = ttk.Label(
            totales_frame, 
            text="Peso Total: 0.00 kg", 
            font=("Arial", 12, "bold")
        )
        self.lbl_total_peso.pack(side="right")

        self.status_label = ttk.Label(
            totales_frame,
            text="",
            font=("Arial", 10),
            foreground="gray"
        )
        self.status_label.pack(side="left", padx=(20, 0))

    def actualizar_carrito(self):
        """Actualiza la vista del carrito"""
        # Limpiar tree
        for item in self.carrito_tree.get_children():
            self.carrito_tree.delete(item)
        
        total_precio = 0
        total_peso = 0
        
        # Determinar símbolo de moneda
        simbolo = "$" if self.moneda_var.get() == "DÓLARES AMERICANOS" else "S/"
        
        # Agregar items
        for i, item in enumerate(carrito):
            # Convertir precios según tipo de cambio
            precio_unitario_display = item.precio_unitario / self.tipo_cambio
            precio_total_display = item.precio_total / self.tipo_cambio
            peso_total = item.peso_total
            
            # Determinar unidad
            if hasattr(item, 'unidad'):
                unidad = item.unidad
            else:
                unidad = "UND"
            
            self.carrito_tree.insert("", "end", values=(
                i + 1,
                item.descripcion,
                unidad,
                item.cantidad,
                f"{simbolo}{precio_unitario_display:.2f}",
                f"{simbolo}{precio_total_display:.2f}",
                f"{peso_total:.2f}"
            ), tags=(str(i),))
            
            total_precio += precio_total_display
            total_peso += peso_total
        
        # Actualizar totales
        self.lbl_total_precio.configure(text=f"Precio Total SIN IGV: {simbolo}{total_precio:.2f}")
        self.lbl_total_peso.configure(text=f"Peso Total: {total_peso:.2f} kg")
        self.actualizar_titulo_carrito()

    def actualizar_titulo_carrito(self):
        """Actualiza el titulo de la pestana carrito con la cantidad de items"""
        cantidad_items = len(carrito)
        if cantidad_items > 0:
            titulo = f"Carrito ({cantidad_items})"
        else:
            titulo = "Carrito"
        
        # Actualizar titulo de la pestana
        try:
            self.parent.tab(1, text=titulo)
        except:
            pass
    
    def eliminar_seleccionado(self):
        """Elimina el item seleccionado del carrito"""
        selection = self.carrito_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un item para eliminar")
            return
        
        if messagebox.askyesno("Confirmar", "Esta seguro de eliminar el item seleccionado?"):
            item_id = self.carrito_tree.item(selection[0])['values'][0]
            index = int(item_id) - 1
            
            if eliminar_producto_carrito(index):
                self.actualizar_carrito()
                messagebox.showinfo("Exito", "Item eliminado del carrito")
            else:
                messagebox.showerror("Error", "No se pudo eliminar el item")
    
    def limpiar_carrito_gui(self):
        """Vacia el carrito"""
        if carrito:
            if messagebox.askyesno("Confirmar", "Esta seguro de vaciar todo el carrito?"):
                limpiar_carrito()
                self.actualizar_carrito()
                messagebox.showinfo("Exito", "Carrito vaciado")
        else:
            messagebox.showinfo("Informacion", "El carrito ya esta vacio")
    
    def agregar_manual(self):
        """Abre dialogo para agregar producto manual"""
        abrir_dialogo_agregar_manual(self.app.root, self.actualizar_carrito)
    
    def modificar_cantidad(self):
        """Abre dialogo para modificar cantidad"""
        abrir_dialogo_modificar_cantidad(self.app.root, self.carrito_tree, self.actualizar_carrito)
        
        # Devolver foco al tree después de modificar
        self.app.root.after(100, lambda: self.carrito_tree.focus_set())

    def limpiar_seleccion(self):
        """Limpia la seleccion del carrito"""
        try:
            self.carrito_tree.selection_remove(self.carrito_tree.selection())
            self.app.root.focus_set()
        except:
            pass
    
    def actualizar_combos_proyecto(self, datos_excel):
        """Actualiza los combos con datos de Excel"""
        try:
            self.razon_social_combo['values'] = datos_excel.get('razones_sociales', [])
            self.atenciones_completas = datos_excel.get('atenciones_completas', {})
            self.atencion_combo['values'] = datos_excel.get('atenciones', [])
            self.moneda_combo['values'] = datos_excel.get('monedas', [])
            if not self.moneda_var.get() and 'SOLES' in datos_excel.get('monedas', []):
                self.moneda_var.set("SOLES")

        except:
            pass

    def on_razon_social_change(self, event=None):
        """Filtra atenciones cuando se selecciona una razon social"""
        codigo_seleccionado = self.razon_social_var.get().strip()
        
        if codigo_seleccionado and self.atenciones_completas:
            # Filtrar atenciones cuyo código de empresa coincida
            atenciones_filtradas = [
                atencion for atencion, codigo_empresa in self.atenciones_completas.items()
                if codigo_empresa == codigo_seleccionado
            ]
            
            self.atencion_combo['values'] = atenciones_filtradas
            
            # Limpiar selección actual si no está en la lista filtrada
            if self.atencion_var.get() not in atenciones_filtradas:
                self.atencion_var.set('')
        else:
            # Mostrar todas las atenciones
            self.atencion_combo['values'] = list(self.atenciones_completas.keys()) if self.atenciones_completas else []

    def exportar_a_excel(self):

        """Exporta el carrito a Excel"""
        if not carrito:
            messagebox.showwarning("Advertencia", "El carrito esta vacio")
            return
        
        # Obtener datos del proyecto
        proyecto = self.proyecto_var.get().strip()
        titulo = self.titulo_provisional_var.get().strip()
        razon_social = self.razon_social_var.get().strip()
        atencion = self.atencion_var.get().strip()
        moneda = self.moneda_var.get().strip()
        
        # Crear ventana de progreso
        ventana_progreso = tk.Toplevel(self.app.root)
        ventana_progreso.title("Exportando...")
        ventana_progreso.geometry("400x150")
        ventana_progreso.resizable(False, False)
        ventana_progreso.transient(self.app.root)
        ventana_progreso.grab_set()
        
        # Centrar ventana
        ventana_progreso.update_idletasks()
        x = (ventana_progreso.winfo_screenwidth() // 2) - 200
        y = (ventana_progreso.winfo_screenheight() // 2) - 75
        ventana_progreso.geometry(f"400x150+{x}+{y}")
        
        # Contenido
        ttk.Label(
            ventana_progreso, 
            text="Exportando a Excel...", 
            font=("Arial", 12)
        ).pack(pady=20)
        
        self.mensaje_progreso = tk.StringVar(value="Preparando...")
        ttk.Label(
            ventana_progreso, 
            textvariable=self.mensaje_progreso
        ).pack(pady=10)
        
        progress = ttk.Progressbar(
            ventana_progreso, 
            mode='indeterminate', 
            length=300
        )
        progress.pack(pady=10)
        progress.start()
        
        # Funcion para actualizar mensaje
        def actualizar_mensaje(msg):
            self.mensaje_progreso.set(msg)
            ventana_progreso.update()
        
        # Ejecutar exportacion en segundo plano
        self.app.root.after(100, lambda: self.ejecutar_exportacion(
            ventana_progreso, 
            actualizar_mensaje,
            proyecto, 
            titulo, 
            razon_social, 
            atencion, 
            moneda
        ))
 
    def ejecutar_exportacion(self, ventana_progreso, actualizar_mensaje, 
                                proyecto, titulo, razon_social, atencion, moneda):
            """Ejecuta la exportacion a Excel"""
            try:
                # ✅ CORRECCIÓN: Import relativo correcto
                from .. import exportar_excel
                
                # ✅ CORRECCIÓN: Preparar datos del proyecto como diccionario
                datos_proyecto = {
                    'proyecto': proyecto,
                    'titulo_provisional': titulo,
                    'razon_social': razon_social,
                    'atencion': atencion,
                    'moneda': moneda
                }
                
                # ✅ CORRECCIÓN: Llamar con parámetros en el orden correcto
                # La función espera: (carrito, datos_proyecto, mostrar_mensaje_callback)
                exito, mensaje = exportar_excel.exportar_carrito_a_excel(
                    carrito,
                    datos_proyecto,
                    actualizar_mensaje
                )
                
                # Cerrar ventana de progreso
                ventana_progreso.destroy()
                
                if exito:
                    messagebox.showinfo("Exportacion completada", mensaje)
                else:
                    messagebox.showerror("Error en exportacion", mensaje)
                    
            except Exception as e:
                ventana_progreso.destroy()
                messagebox.showerror("Error", f"Error durante la exportacion:\n{str(e)}")

    def configurar_shortcuts_carrito(self):
        """Configura shortcuts para navegación en carrito"""
        
        # Shift+Flechas para selección múltiple
        self.carrito_tree.bind("<Shift-Up>", self.seleccionar_multiple_arriba)
        self.carrito_tree.bind("<Shift-Down>", self.seleccionar_multiple_abajo)
        
        # Ctrl+A para seleccionar todo
        self.carrito_tree.bind("<Control-a>", self.seleccionar_todo)
        
        # Delete o Suprimir para eliminar seleccionados
        self.carrito_tree.bind("<Delete>", lambda e: self.eliminar_seleccionados_multiples())
        
        # Enter para modificar cantidad del seleccionado
        self.carrito_tree.bind("<Return>", lambda e: self.modificar_cantidad())
        self.carrito_tree.bind("<KP_Enter>", lambda e: self.modificar_cantidad())
        
        # Dar foco al tree cuando se muestre la pestaña
        def enfocar_carrito(event=None):
            self.carrito_tree.focus_set()
            # Seleccionar primer item si hay
            items = self.carrito_tree.get_children()
            if items and not self.carrito_tree.selection():
                self.carrito_tree.selection_set(items[0])
                self.carrito_tree.focus(items[0])
        
        self.frame.bind("<Visibility>", enfocar_carrito)

    def seleccionar_multiple_arriba(self, event):
        """Extiende selección hacia arriba"""
        items = self.carrito_tree.get_children()
        if not items:
            return "break"
        
        selection = self.carrito_tree.selection()
        if not selection:
            # Seleccionar último
            self.carrito_tree.selection_set(items[-1])
            self.carrito_tree.see(items[-1])
        else:
            # Obtener el primer item seleccionado
            first_selected = selection[0]
            idx = items.index(first_selected)
            
            if idx > 0:
                prev_item = items[idx - 1]
                # Agregar a la selección existente
                self.carrito_tree.selection_add(prev_item)
                self.carrito_tree.see(prev_item)
        
        return "break"

    def seleccionar_multiple_abajo(self, event):
        """Extiende selección hacia abajo"""
        items = self.carrito_tree.get_children()
        if not items:
            return "break"
        
        selection = self.carrito_tree.selection()
        if not selection:
            # Seleccionar primero
            self.carrito_tree.selection_set(items[0])
            self.carrito_tree.see(items[0])
        else:
            # Obtener el último item seleccionado
            last_selected = selection[-1]
            idx = items.index(last_selected)
            
            if idx < len(items) - 1:
                next_item = items[idx + 1]
                # Agregar a la selección existente
                self.carrito_tree.selection_add(next_item)
                self.carrito_tree.see(next_item)
        
        return "break"

    def seleccionar_todo(self, event):
        """Selecciona todos los items del carrito"""
        items = self.carrito_tree.get_children()
        if items:
            self.carrito_tree.selection_set(items)
        return "break"

    def eliminar_seleccionados_multiples(self):
        """Elimina todos los items seleccionados"""
        
        selection = self.carrito_tree.selection()
        if not selection:
            self.status_label.configure(text="⚠️ No hay productos seleccionados", foreground="orange")
            return
        
        cantidad = len(selection)
        
        # Confirmar si son múltiples
        if cantidad > 1:
            respuesta = messagebox.askyesno(
                "Confirmar",
                f"¿Eliminar {cantidad} productos seleccionados del carrito?"
            )
            if not respuesta:
                self.app.root.after(50, self.carrito_tree.focus_set)
                return
        
        # Eliminar del carrito
        from ..logica import carrito
        
        # Obtener índices en orden inverso para no desajustar
        indices = []
        for item in selection:
            try:
                index = self.carrito_tree.index(item)
                indices.append(index)
            except:
                pass
        
        # Ordenar de mayor a menor para eliminar sin problemas
        indices.sort(reverse=True)
        
        for index in indices:
            if 0 <= index < len(carrito):
                carrito.pop(index)
        
        # Actualizar GUI
        self.actualizar_carrito()
        
        # Actualizar status
        if cantidad == 1:
            self.status_label.configure(text="✅ Producto eliminado del carrito", foreground="green")
        else:
            self.status_label.configure(text=f"✅ {cantidad} productos eliminados del carrito", foreground="green")
        
        # Devolver foco y seleccionar siguiente item
        def restaurar_foco():
            items = self.carrito_tree.get_children()
            if items:
                idx_seleccionar = min(indices[0] if indices else 0, len(items) - 1)
                self.carrito_tree.selection_set(items[idx_seleccionar])
                self.carrito_tree.see(items[idx_seleccionar])
                self.carrito_tree.focus(items[idx_seleccionar])
            self.carrito_tree.focus_set()
        
        self.app.root.after(50, restaurar_foco) 

    def solicitar_tipo_cambio(self):
        """Solicita el tipo de cambio para conversión a dólares"""
        dialogo = tk.Toplevel(self.app.root)
        dialogo.title("Tipo de Cambio")
        dialogo.geometry("350x180")
        dialogo.resizable(False, False)
        dialogo.transient(self.app.root)
        dialogo.grab_set()
        
        # Centrar
        dialogo.update_idletasks()
        x = (dialogo.winfo_screenwidth() // 2) - 175
        y = (dialogo.winfo_screenheight() // 2) - 90
        dialogo.geometry(f"350x180+{x}+{y}")
        
        main_frame = ttk.Frame(dialogo, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(
            main_frame,
            text="Ingrese el tipo de cambio (USD):",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(
            main_frame,
            text="S/ 1.00 USD = S/ ?",
            font=("Arial", 9)
        ).pack(anchor="w", pady=(0, 10))
        
        tc_var = tk.StringVar(value=str(self.tipo_cambio if self.tipo_cambio != 1.0 else "3.80"))
        tc_entry = ttk.Entry(main_frame, textvariable=tc_var, width=15, font=("Arial", 11))
        tc_entry.pack(anchor="w", pady=(0, 20))
        tc_entry.focus()
        tc_entry.select_range(0, 'end')
        
        def aplicar():
            try:
                tc = float(tc_var.get())
                if tc <= 0:
                    messagebox.showerror("Error", "El tipo de cambio debe ser mayor a 0")
                    return
                
                self.tipo_cambio = tc
                dialogo.destroy()
                self.actualizar_carrito()
                
            except ValueError:
                messagebox.showerror("Error", "Ingrese un tipo de cambio válido")
        
        def cancelar():
            # Volver a SOLES si cancela
            self.moneda_var.set("SOLES")
            self.tipo_cambio = 1.0
            dialogo.destroy()
        
        # Manejar cierre con X
        dialogo.protocol("WM_DELETE_WINDOW", cancelar)
        
        botones_frame = ttk.Frame(main_frame)
        botones_frame.pack(fill="x")
        
        ttk.Button(
            botones_frame,
            text="✓ Aplicar",
            command=aplicar,
            style="Accent.TButton"
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            botones_frame,
            text="✗ Cancelar",
            command=cancelar
        ).pack(side="left")
        
        dialogo.bind("<Return>", lambda e: aplicar())
        dialogo.bind("<Escape>", lambda e: cancelar())