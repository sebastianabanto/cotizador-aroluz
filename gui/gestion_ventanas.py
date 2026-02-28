# -*- coding: utf-8 -*-
"""
Ventanas Tkinter para gestión de clientes y atenciones.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import re

from .gestor_datos_excel import GestorDatosExcel


class VentanaGestionDatos:
    """Ventana principal para gestión de datos de clientes y atenciones"""

    def __init__(self, parent, ruta_excel: str):
        self.parent = parent
        self.gestor = GestorDatosExcel(ruta_excel)
        self.crear_ventana()
        self.cargar_datos_iniciales()

    def crear_ventana(self):
        """Crea la ventana de gestión"""
        self.ventana = tk.Toplevel(self.parent)
        self.ventana.title("🏢 Gestión de Clientes y Atenciones")
        self.ventana.geometry("1000x700")
        self.ventana.resizable(True, True)
        self.ventana.transient(self.parent)
        self.ventana.grab_set()

        # Centrar ventana
        self.ventana.update_idletasks()
        x = (self.ventana.winfo_screenwidth() // 2) - 500
        y = (self.ventana.winfo_screenheight() // 2) - 350
        self.ventana.geometry(f"1000x700+{x}+{y}")

        # Frame principal
        main_frame = ttk.Frame(self.ventana)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Crear pestañas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(0, 15))

        self.crear_pestaña_clientes()
        self.crear_pestaña_atenciones()

        # Botones globales
        self.crear_botones_principales(main_frame)

        # Shortcuts
        self.configurar_shortcuts()

    def crear_pestaña_clientes(self):
        """Crea la pestaña de gestión de clientes"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🏢 Clientes")

        # Toolbar
        toolbar_clientes = ttk.Frame(frame)
        toolbar_clientes.pack(fill="x", padx=15, pady=(15, 10))

        ttk.Button(toolbar_clientes, text="➕ Nuevo Cliente",
                  command=self.nuevo_cliente).pack(side="left", padx=(0, 10))
        ttk.Button(toolbar_clientes, text="✏️ Editar",
                  command=self.editar_cliente).pack(side="left", padx=(0, 10))
        ttk.Button(toolbar_clientes, text="🗑️ Eliminar",
                  command=self.eliminar_cliente).pack(side="left", padx=(0, 10))
        ttk.Button(toolbar_clientes, text="🔄 Actualizar",
                  command=self.actualizar_clientes).pack(side="left", padx=(0, 10))

        # Treeview para clientes
        tree_frame_clientes = ttk.Frame(frame)
        tree_frame_clientes.pack(fill="both", expand=True, padx=15, pady=10)

        # Scrollbars
        scroll_y_clientes = ttk.Scrollbar(tree_frame_clientes)
        scroll_y_clientes.pack(side="right", fill="y")

        scroll_x_clientes = ttk.Scrollbar(tree_frame_clientes, orient="horizontal")
        scroll_x_clientes.pack(side="bottom", fill="x")

        # Treeview
        self.tree_clientes = ttk.Treeview(tree_frame_clientes,
                                         yscrollcommand=scroll_y_clientes.set,
                                         xscrollcommand=scroll_x_clientes.set)

        # Configurar scrollbars
        scroll_y_clientes.config(command=self.tree_clientes.yview)
        scroll_x_clientes.config(command=self.tree_clientes.xview)

        # Configurar columnas
        self.tree_clientes["columns"] = ("codigo", "razon_social", "ruc", "ubicacion", "atenciones")
        self.tree_clientes["show"] = "headings"

        # Encabezados
        self.tree_clientes.heading("codigo", text="CÓDIGO")
        self.tree_clientes.heading("razon_social", text="RAZÓN SOCIAL")
        self.tree_clientes.heading("ruc", text="RUC")
        self.tree_clientes.heading("ubicacion", text="UBICACIÓN")
        self.tree_clientes.heading("atenciones", text="# ATENCIONES")

        # Anchos
        self.tree_clientes.column("codigo", width=120, anchor="center")
        self.tree_clientes.column("razon_social", width=250, anchor="w")
        self.tree_clientes.column("ruc", width=120, anchor="center")
        self.tree_clientes.column("ubicacion", width=200, anchor="w")
        self.tree_clientes.column("atenciones", width=80, anchor="center")

        self.tree_clientes.pack(fill="both", expand=True)

        # Doble click para editar
        self.tree_clientes.bind("<Double-1>", lambda e: self.editar_cliente())

    def crear_pestaña_atenciones(self):
        """Crea la pestaña de gestión de atenciones"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="👥 Atenciones")

        # Toolbar
        toolbar_atenciones = ttk.Frame(frame)
        toolbar_atenciones.pack(fill="x", padx=15, pady=(15, 10))

        ttk.Button(toolbar_atenciones, text="➕ Nueva Atención",
                  command=self.nueva_atencion).pack(side="left", padx=(0, 10))
        ttk.Button(toolbar_atenciones, text="✏️ Editar",
                  command=self.editar_atencion).pack(side="left", padx=(0, 10))
        ttk.Button(toolbar_atenciones, text="🗑️ Eliminar",
                  command=self.eliminar_atencion).pack(side="left", padx=(0, 10))
        ttk.Button(toolbar_atenciones, text="🔄 Actualizar",
                  command=self.actualizar_atenciones).pack(side="left", padx=(0, 10))

        # Filtro por cliente
        filtro_frame = ttk.Frame(toolbar_atenciones)
        filtro_frame.pack(side="right")

        ttk.Label(filtro_frame, text="Cliente:").pack(side="left", padx=(0, 5))
        self.filtro_cliente_var = tk.StringVar()
        self.filtro_cliente_combo = ttk.Combobox(filtro_frame, textvariable=self.filtro_cliente_var,
                                               width=15, state="readonly")
        self.filtro_cliente_combo.pack(side="left", padx=(0, 10))
        self.filtro_cliente_combo.bind('<<ComboboxSelected>>', self.filtrar_atenciones)

        ttk.Button(filtro_frame, text="🔍 Todos",
                  command=self.mostrar_todas_atenciones).pack(side="left")

        # Treeview para atenciones
        tree_frame_atenciones = ttk.Frame(frame)
        tree_frame_atenciones.pack(fill="both", expand=True, padx=15, pady=10)

        # Scrollbars
        scroll_y_atenciones = ttk.Scrollbar(tree_frame_atenciones)
        scroll_y_atenciones.pack(side="right", fill="y")

        scroll_x_atenciones = ttk.Scrollbar(tree_frame_atenciones, orient="horizontal")
        scroll_x_atenciones.pack(side="bottom", fill="x")

        # Treeview
        self.tree_atenciones = ttk.Treeview(tree_frame_atenciones,
                                           yscrollcommand=scroll_y_atenciones.set,
                                           xscrollcommand=scroll_x_atenciones.set)

        # Configurar scrollbars
        scroll_y_atenciones.config(command=self.tree_atenciones.yview)
        scroll_x_atenciones.config(command=self.tree_atenciones.xview)

        # Configurar columnas
        self.tree_atenciones["columns"] = ("codigo", "nombres", "correo", "celular", "cliente")
        self.tree_atenciones["show"] = "headings"

        # Encabezados
        self.tree_atenciones.heading("codigo", text="CÓDIGO")
        self.tree_atenciones.heading("nombres", text="NOMBRES")
        self.tree_atenciones.heading("correo", text="CORREO")
        self.tree_atenciones.heading("celular", text="CELULAR")
        self.tree_atenciones.heading("cliente", text="CLIENTE")

        # Anchos
        self.tree_atenciones.column("codigo", width=100, anchor="center")
        self.tree_atenciones.column("nombres", width=200, anchor="w")
        self.tree_atenciones.column("correo", width=180, anchor="w")
        self.tree_atenciones.column("celular", width=100, anchor="center")
        self.tree_atenciones.column("cliente", width=150, anchor="w")

        self.tree_atenciones.pack(fill="both", expand=True)

        # Doble click para editar
        self.tree_atenciones.bind("<Double-1>", lambda e: self.editar_atencion())

    def crear_botones_principales(self, parent):
        """Crea los botones principales de la ventana"""
        botones_frame = ttk.Frame(parent)
        botones_frame.pack(fill="x")

        ttk.Button(botones_frame, text="💾 Guardar Cambios",
                  command=self.guardar_cambios,
                  style="Accent.TButton").pack(side="left", padx=(0, 10))

        ttk.Button(botones_frame, text="📊 Estadísticas",
                  command=self.mostrar_estadisticas).pack(side="left", padx=(0, 10))

        ttk.Button(botones_frame, text="❓ Ayuda",
                  command=self.mostrar_ayuda).pack(side="left", padx=(0, 10))

        ttk.Button(botones_frame, text="❌ Cerrar",
                  command=self.cerrar_ventana).pack(side="right")

    def configurar_shortcuts(self):
        """Configura los atajos de teclado"""
        self.ventana.bind("<Control-s>", lambda e: self.guardar_cambios())
        self.ventana.bind("<Control-n>", lambda e: self.nuevo_cliente())
        self.ventana.bind("<Control-e>", lambda e: self.editar_cliente())
        self.ventana.bind("<Delete>", lambda e: self.eliminar_cliente())
        self.ventana.bind("<F5>", lambda e: self.actualizar_clientes())
        self.ventana.bind("<Escape>", lambda e: self.cerrar_ventana())

    def cargar_datos_iniciales(self):
        """Carga los datos iniciales del Excel"""
        try:
            if not self.gestor.verificar_archivo():
                messagebox.showerror("Error", f"No se encontró el archivo Excel:\n{self.gestor.ruta_excel}")
                return

            self.gestor.cargar_datos_completos()
            self.actualizar_clientes()
            self.actualizar_atenciones()
            self.actualizar_filtro_clientes()

            messagebox.showinfo("Datos cargados",
                              f"✅ Datos cargados exitosamente:\n"
                              f"🏢 Clientes: {len(self.gestor.datos_clientes)}\n"
                              f"👥 Atenciones: {len(self.gestor.datos_atenciones)}")

        except Exception as e:
            messagebox.showerror("Error", f"Error cargando datos:\n{str(e)}")

    def actualizar_clientes(self):
        """Actualiza la vista de clientes"""
        # Limpiar tree
        for item in self.tree_clientes.get_children():
            self.tree_clientes.delete(item)

        # Agregar datos
        for i, cliente in enumerate(self.gestor.datos_clientes):
            # Contar atenciones asociadas
            num_atenciones = len(self.gestor.obtener_atenciones_por_cliente(cliente['codigo']))

            self.tree_clientes.insert("", "end", values=(
                cliente['codigo'],
                cliente['razon_social'],
                cliente['ruc'],
                cliente['ubicacion'],
                num_atenciones
            ), tags=(str(i),))

    def actualizar_atenciones(self):
        """Actualiza la vista de atenciones"""
        # Limpiar tree
        for item in self.tree_atenciones.get_children():
            self.tree_atenciones.delete(item)

        # Agregar datos
        for i, atencion in enumerate(self.gestor.datos_atenciones):
            self.tree_atenciones.insert("", "end", values=(
                atencion['codigo'],
                atencion['nombres'],
                atencion['correo'],
                atencion['celular'],
                atencion['razon_social']
            ), tags=(str(i),))

    def actualizar_filtro_clientes(self):
        """Actualiza el combobox de filtro de clientes"""
        clientes = [""] + self.gestor.obtener_lista_clientes()
        self.filtro_cliente_combo['values'] = clientes

    def filtrar_atenciones(self, event=None):
        """Filtra atenciones por cliente seleccionado"""
        cliente_seleccionado = self.filtro_cliente_var.get()

        # Limpiar tree
        for item in self.tree_atenciones.get_children():
            self.tree_atenciones.delete(item)

        # Filtrar y mostrar
        atenciones_filtradas = []
        if cliente_seleccionado:
            atenciones_filtradas = self.gestor.obtener_atenciones_por_cliente(cliente_seleccionado)
        else:
            atenciones_filtradas = self.gestor.datos_atenciones

        for i, atencion in enumerate(atenciones_filtradas):
            self.tree_atenciones.insert("", "end", values=(
                atencion['codigo'],
                atencion['nombres'],
                atencion['correo'],
                atencion['celular'],
                atencion['razon_social']
            ))

    def mostrar_todas_atenciones(self):
        """Muestra todas las atenciones (quita filtro)"""
        self.filtro_cliente_var.set("")
        self.actualizar_atenciones()

    # OPERACIONES CRUD - CLIENTES
    def nuevo_cliente(self):
        """Abre ventana para crear nuevo cliente"""
        VentanaEditorCliente(self.ventana, self.gestor, callback=self.actualizar_clientes)

    def editar_cliente(self):
        """Abre ventana para editar cliente seleccionado"""
        seleccion = self.tree_clientes.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un cliente para editar")
            return

        # Obtener índice
        item = self.tree_clientes.item(seleccion[0])
        indice = int(item['tags'][0])

        VentanaEditorCliente(self.ventana, self.gestor, indice,
                           callback=lambda: [self.actualizar_clientes(), self.actualizar_filtro_clientes()])

    def eliminar_cliente(self):
        """Elimina cliente seleccionado"""
        seleccion = self.tree_clientes.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un cliente para eliminar")
            return

        # Obtener datos del cliente
        item = self.tree_clientes.item(seleccion[0])
        indice = int(item['tags'][0])
        cliente = self.gestor.datos_clientes[indice]

        # Verificar atenciones asociadas
        atenciones_asociadas = self.gestor.obtener_atenciones_por_cliente(cliente['codigo'])

        if atenciones_asociadas:
            respuesta = messagebox.askyesnocancel(
                "Cliente con atenciones",
                f"El cliente '{cliente['codigo']}' tiene {len(atenciones_asociadas)} atención(es) asociada(s).\n\n"
                "¿Qué desea hacer?\n\n"
                "SÍ = Eliminar cliente y sus atenciones\n"
                "NO = Solo eliminar cliente (las atenciones quedarán sin cliente)\n"
                "CANCELAR = No eliminar nada"
            )

            if respuesta is None:  # Cancelar
                return
            elif respuesta:  # Sí - eliminar todo
                eliminar_atenciones = True
            else:  # No - solo cliente
                eliminar_atenciones = False
        else:
            # Sin atenciones, confirmar eliminación
            if not messagebox.askyesno("Confirmar eliminación",
                                     f"¿Está seguro de eliminar el cliente '{cliente['codigo']}'?"):
                return
            eliminar_atenciones = False

        try:
            self.gestor.eliminar_cliente_con_atenciones(indice, eliminar_atenciones)
            self.actualizar_clientes()
            self.actualizar_atenciones()
            self.actualizar_filtro_clientes()
            messagebox.showinfo("Éxito", "Cliente eliminado correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"Error eliminando cliente:\n{str(e)}")

    # OPERACIONES CRUD - ATENCIONES
    def nueva_atencion(self):
        """Abre ventana para crear nueva atención"""
        VentanaEditorAtencion(self.ventana, self.gestor, callback=self.actualizar_atenciones)

    def editar_atencion(self):
        """Abre ventana para editar atención seleccionada"""
        seleccion = self.tree_atenciones.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una atención para editar")
            return

        # Obtener índice real en la lista completa
        item = self.tree_atenciones.item(seleccion[0])
        codigo_atencion = item['values'][0]

        # Encontrar índice en la lista completa
        indice = None
        for i, atencion in enumerate(self.gestor.datos_atenciones):
            if atencion['codigo'] == codigo_atencion:
                indice = i
                break

        if indice is not None:
            VentanaEditorAtencion(self.ventana, self.gestor, indice, callback=self.actualizar_atenciones)

    def eliminar_atencion(self):
        """Elimina atención seleccionada"""
        seleccion = self.tree_atenciones.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una atención para eliminar")
            return

        # Obtener datos de la atención
        item = self.tree_atenciones.item(seleccion[0])
        codigo_atencion = item['values'][0]
        nombres = item['values'][1]

        if not messagebox.askyesno("Confirmar eliminación",
                                 f"¿Está seguro de eliminar la atención '{nombres}'?"):
            return

        # Encontrar índice en la lista completa
        for i, atencion in enumerate(self.gestor.datos_atenciones):
            if atencion['codigo'] == codigo_atencion:
                try:
                    self.gestor.eliminar_atencion(i)
                    self.actualizar_atenciones()
                    messagebox.showinfo("Éxito", "Atención eliminada correctamente")
                    return
                except Exception as e:
                    messagebox.showerror("Error", f"Error eliminando atención:\n{str(e)}")
                    return

    def guardar_cambios(self):
        """Guarda todos los cambios en Excel"""
        try:
            respuesta = messagebox.askyesno(
                "Confirmar guardado",
                "¿Está seguro de guardar todos los cambios en Excel?\n\n"
                "Se creará un backup automático del archivo original."
            )

            if respuesta:
                self.gestor.guardar_cambios()
                messagebox.showinfo("Éxito", "✅ Cambios guardados correctamente\n📄 Backup creado automáticamente")
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando cambios:\n{str(e)}")

    def mostrar_estadisticas(self):
        """Muestra estadísticas de los datos"""
        total_clientes = len(self.gestor.datos_clientes)
        total_atenciones = len(self.gestor.datos_atenciones)

        # Clientes con/sin atenciones
        clientes_con_atenciones = 0
        clientes_sin_atenciones = 0

        for cliente in self.gestor.datos_clientes:
            atenciones = self.gestor.obtener_atenciones_por_cliente(cliente['codigo'])
            if atenciones:
                clientes_con_atenciones += 1
            else:
                clientes_sin_atenciones += 1

        # Atenciones sin cliente
        atenciones_sin_cliente = 0
        codigos_clientes = [c['codigo'] for c in self.gestor.datos_clientes]

        for atencion in self.gestor.datos_atenciones:
            if atencion['razon_social'] not in codigos_clientes:
                atenciones_sin_cliente += 1

        # Clientes con más atenciones
        cliente_mas_atenciones = ""
        max_atenciones = 0

        for cliente in self.gestor.datos_clientes:
            num_atenciones = len(self.gestor.obtener_atenciones_por_cliente(cliente['codigo']))
            if num_atenciones > max_atenciones:
                max_atenciones = num_atenciones
                cliente_mas_atenciones = cliente['codigo']

        # Crear mensaje
        estadisticas = f"""📊 ESTADÍSTICAS DE DATOS

🏢 CLIENTES:
   • Total: {total_clientes}
   • Con atenciones: {clientes_con_atenciones}
   • Sin atenciones: {clientes_sin_atenciones}

👥 ATENCIONES:
   • Total: {total_atenciones}
   • Sin cliente asignado: {atenciones_sin_cliente}

🏆 DESTACADOS:
   • Cliente con más atenciones: {cliente_mas_atenciones} ({max_atenciones} atenciones)

📈 CALIDAD DE DATOS:
   • Integridad: {((total_atenciones - atenciones_sin_cliente) / max(total_atenciones, 1) * 100):.1f}%
   • Cobertura: {(clientes_con_atenciones / max(total_clientes, 1) * 100):.1f}%
"""

        # Mostrar en ventana
        ventana_stats = tk.Toplevel(self.ventana)
        ventana_stats.title("📊 Estadísticas")
        ventana_stats.geometry("400x500")
        ventana_stats.resizable(False, False)
        ventana_stats.transient(self.ventana)

        # Centrar
        ventana_stats.update_idletasks()
        x = (ventana_stats.winfo_screenwidth() // 2) - 200
        y = (ventana_stats.winfo_screenheight() // 2) - 250
        ventana_stats.geometry(f"400x500+{x}+{y}")

        # Texto
        from tkinter import scrolledtext
        texto = scrolledtext.ScrolledText(ventana_stats, font=("Consolas", 10), wrap=tk.WORD)
        texto.pack(fill="both", expand=True, padx=20, pady=20)
        texto.insert("1.0", estadisticas)
        texto.configure(state="disabled")

        # Botón cerrar
        ttk.Button(ventana_stats, text="Cerrar",
                  command=ventana_stats.destroy).pack(pady=10)

    def mostrar_ayuda(self):
        """Muestra ayuda del sistema"""
        ayuda = """🆘 AYUDA - GESTIÓN DE DATOS

📋 FUNCIONES PRINCIPALES:
• Crear, editar y eliminar clientes
• Crear, editar y eliminar atenciones
• Mantener relaciones entre clientes y atenciones
• Guardar cambios directamente en Excel

⌨️ ATAJOS DE TECLADO:
• Ctrl+S: Guardar cambios
• Ctrl+N: Nuevo cliente
• Ctrl+E: Editar cliente
• Del: Eliminar seleccionado
• F5: Actualizar datos
• Esc: Cerrar ventana

🏢 GESTIÓN DE CLIENTES:
• Código: Identificador único (obligatorio)
• Razón Social: Nombre completo de la empresa
• RUC: Registro Único de Contribuyente (11 dígitos)
• Ubicación: Dirección legal de la empresa

👥 GESTIÓN DE ATENCIONES:
• Código: Identificador único (obligatorio)
• Nombres: Nombre completo de la persona
• Correo: Email de contacto
• Celular: Número de teléfono
• Cliente: Código del cliente asociado

⚠️ IMPORTANTE:
• Se crea backup automático antes de guardar
• Los cambios solo se aplican al presionar "Guardar Cambios"
• Al eliminar un cliente, puede elegir qué hacer con sus atenciones
• Las validaciones incluyen RUC y formato de email

🔗 RELACIONES:
• Una atención pertenece a un cliente (relación 1:N)
• Al cambiar el código de un cliente, se actualizan automáticamente las referencias
• Puede filtrar atenciones por cliente específico
"""

        # Mostrar en ventana
        ventana_ayuda = tk.Toplevel(self.ventana)
        ventana_ayuda.title("🆘 Ayuda del Sistema")
        ventana_ayuda.geometry("600x700")
        ventana_ayuda.resizable(True, True)
        ventana_ayuda.transient(self.ventana)

        # Centrar
        ventana_ayuda.update_idletasks()
        x = (ventana_ayuda.winfo_screenwidth() // 2) - 300
        y = (ventana_ayuda.winfo_screenheight() // 2) - 350
        ventana_ayuda.geometry(f"600x700+{x}+{y}")

        # Texto
        from tkinter import scrolledtext
        texto = scrolledtext.ScrolledText(ventana_ayuda, font=("Arial", 10), wrap=tk.WORD)
        texto.pack(fill="both", expand=True, padx=20, pady=20)
        texto.insert("1.0", ayuda)
        texto.configure(state="disabled")

        # Botón cerrar
        ttk.Button(ventana_ayuda, text="Cerrar",
                  command=ventana_ayuda.destroy).pack(pady=10)

    def cerrar_ventana(self):
        """Cierra la ventana con confirmación si hay cambios sin guardar"""
        # Por simplicidad, solo pregunta si quiere cerrar
        if messagebox.askokcancel("Cerrar", "¿Está seguro de cerrar la gestión de datos?"):
            self.ventana.destroy()


class VentanaEditorCliente:
    """Ventana para crear/editar clientes"""

    def __init__(self, parent, gestor: GestorDatosExcel, indice: int = None, callback=None):
        self.parent = parent
        self.gestor = gestor
        self.indice = indice  # None para nuevo, número para editar
        self.callback = callback
        self.cliente_actual = None

        if self.indice is not None:
            self.cliente_actual = self.gestor.datos_clientes[self.indice]

        self.crear_ventana()

    def crear_ventana(self):
        """Crea la ventana del editor"""
        titulo = "✏️ Editar Cliente" if self.indice is not None else "➕ Nuevo Cliente"

        self.ventana = tk.Toplevel(self.parent)
        self.ventana.title(titulo)
        self.ventana.geometry("500x400")
        self.ventana.resizable(False, False)
        self.ventana.transient(self.parent)
        self.ventana.grab_set()

        # Centrar
        self.ventana.update_idletasks()
        x = (self.ventana.winfo_screenwidth() // 2) - 250
        y = (self.ventana.winfo_screenheight() // 2) - 200
        self.ventana.geometry(f"500x400+{x}+{y}")

        # Frame principal
        main_frame = ttk.Frame(self.ventana, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Variables
        self.codigo_var = tk.StringVar()
        self.razon_social_var = tk.StringVar()
        self.ruc_var = tk.StringVar()
        self.ubicacion_var = tk.StringVar()

        # Si es edición, cargar datos
        if self.cliente_actual:
            self.codigo_var.set(self.cliente_actual['codigo'])
            self.razon_social_var.set(self.cliente_actual['razon_social'])
            self.ruc_var.set(self.cliente_actual['ruc'])
            self.ubicacion_var.set(self.cliente_actual['ubicacion'])

        # Campos
        # Código
        ttk.Label(main_frame, text="Código: *", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))
        codigo_entry = ttk.Entry(main_frame, textvariable=self.codigo_var, width=20, font=("Arial", 11))
        codigo_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        codigo_entry.focus()

        # Razón Social
        ttk.Label(main_frame, text="Razón Social: *", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 5))
        razon_entry = ttk.Entry(main_frame, textvariable=self.razon_social_var, width=60, font=("Arial", 11))
        razon_entry.grid(row=3, column=0, sticky="ew", pady=(0, 15))

        # RUC
        ttk.Label(main_frame, text="RUC:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 5))
        ruc_frame = ttk.Frame(main_frame)
        ruc_frame.grid(row=5, column=0, sticky="ew", pady=(0, 15))

        ruc_entry = ttk.Entry(ruc_frame, textvariable=self.ruc_var, width=15, font=("Arial", 11))
        ruc_entry.pack(side="left")
        ttk.Label(ruc_frame, text="(11 dígitos)", font=("Arial", 8), foreground="gray").pack(side="left", padx=(10, 0))

        # Ubicación
        ttk.Label(main_frame, text="Ubicación:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="w", pady=(0, 5))
        ubicacion_text = tk.Text(main_frame, width=60, height=4, font=("Arial", 10))
        ubicacion_text.grid(row=7, column=0, sticky="ew", pady=(0, 20))

        if self.cliente_actual:
            ubicacion_text.insert("1.0", self.cliente_actual['ubicacion'])

        # Vincular Text widget a StringVar manualmente
        def actualizar_ubicacion(*args):
            self.ubicacion_var.set(ubicacion_text.get("1.0", "end-1c"))

        ubicacion_text.bind("<KeyRelease>", actualizar_ubicacion)

        # Botones
        botones_frame = ttk.Frame(main_frame)
        botones_frame.grid(row=8, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(botones_frame, text="💾 Guardar",
                  command=self.guardar_cliente,
                  style="Accent.TButton").pack(side="left", padx=(0, 10))

        ttk.Button(botones_frame, text="❌ Cancelar",
                  command=self.ventana.destroy).pack(side="left")

        # Información
        if self.indice is not None and self.cliente_actual:
            # Mostrar atenciones asociadas
            atenciones = self.gestor.obtener_atenciones_por_cliente(self.cliente_actual['codigo'])
            ttk.Label(botones_frame,
                     text=f"👥 {len(atenciones)} atención(es) asociada(s)",
                     font=("Arial", 9), foreground="blue").pack(side="right")

        # Configurar grid
        main_frame.grid_columnconfigure(0, weight=1)

        # Shortcuts
        self.ventana.bind("<Control-s>", lambda e: self.guardar_cliente())
        self.ventana.bind("<Escape>", lambda e: self.ventana.destroy())
        self.ventana.bind("<Control-Return>", lambda e: self.guardar_cliente())

    def guardar_cliente(self):
        """Guarda el cliente (nuevo o editado)"""
        try:
            codigo = self.codigo_var.get().strip()
            razon_social = self.razon_social_var.get().strip()
            ruc = self.ruc_var.get().strip()
            ubicacion = self.ubicacion_var.get().strip()

            # Validaciones básicas
            if not codigo:
                raise ValueError("El código es obligatorio")
            if not razon_social:
                raise ValueError("La razón social es obligatoria")

            # Validar formato de código (sin espacios, caracteres especiales)
            if not re.match(r'^[A-Za-z0-9_-]+$', codigo):
                raise ValueError("El código solo puede contener letras, números, guiones y guiones bajos")

            if self.indice is None:
                # Nuevo cliente
                self.gestor.agregar_cliente(codigo, razon_social, ruc, ubicacion)
                messagebox.showinfo("Éxito", f"Cliente '{codigo}' agregado correctamente")
            else:
                # Editar cliente
                self.gestor.modificar_cliente(self.indice, codigo, razon_social, ruc, ubicacion)
                messagebox.showinfo("Éxito", f"Cliente '{codigo}' modificado correctamente")

            # Callback para actualizar vista
            if self.callback:
                self.callback()

            self.ventana.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))


class VentanaEditorAtencion:
    """Ventana para crear/editar atenciones"""

    def __init__(self, parent, gestor: GestorDatosExcel, indice: int = None, callback=None):
        self.parent = parent
        self.gestor = gestor
        self.indice = indice  # None para nuevo, número para editar
        self.callback = callback
        self.atencion_actual = None

        if self.indice is not None:
            self.atencion_actual = self.gestor.datos_atenciones[self.indice]

        self.crear_ventana()

    def crear_ventana(self):
        """Crea la ventana del editor"""
        titulo = "✏️ Editar Atención" if self.indice is not None else "➕ Nueva Atención"

        self.ventana = tk.Toplevel(self.parent)
        self.ventana.title(titulo)
        self.ventana.geometry("500x450")
        self.ventana.resizable(False, False)
        self.ventana.transient(self.parent)
        self.ventana.grab_set()

        # Centrar
        self.ventana.update_idletasks()
        x = (self.ventana.winfo_screenwidth() // 2) - 250
        y = (self.ventana.winfo_screenheight() // 2) - 225
        self.ventana.geometry(f"500x450+{x}+{y}")

        # Frame principal
        main_frame = ttk.Frame(self.ventana, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Variables
        self.codigo_var = tk.StringVar()
        self.nombres_var = tk.StringVar()
        self.correo_var = tk.StringVar()
        self.celular_var = tk.StringVar()
        self.cliente_var = tk.StringVar()

        # Si es edición, cargar datos
        if self.atencion_actual:
            self.codigo_var.set(self.atencion_actual['codigo'])
            self.nombres_var.set(self.atencion_actual['nombres'])
            self.correo_var.set(self.atencion_actual['correo'])
            self.celular_var.set(self.atencion_actual['celular'])
            self.cliente_var.set(self.atencion_actual['razon_social'])

        # Campos
        # Código
        ttk.Label(main_frame, text="Código: *", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))
        codigo_entry = ttk.Entry(main_frame, textvariable=self.codigo_var, width=20, font=("Arial", 11))
        codigo_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        codigo_entry.focus()

        # Nombres
        ttk.Label(main_frame, text="Nombres: *", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 5))
        nombres_entry = ttk.Entry(main_frame, textvariable=self.nombres_var, width=40, font=("Arial", 11))
        nombres_entry.grid(row=3, column=0, sticky="ew", pady=(0, 15))

        # Correo
        ttk.Label(main_frame, text="Correo:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 5))
        correo_frame = ttk.Frame(main_frame)
        correo_frame.grid(row=5, column=0, sticky="ew", pady=(0, 15))

        correo_entry = ttk.Entry(correo_frame, textvariable=self.correo_var, width=30, font=("Arial", 11))
        correo_entry.pack(side="left")
        ttk.Label(correo_frame, text="(formato: email@dominio.com)", font=("Arial", 8), foreground="gray").pack(side="left", padx=(10, 0))

        # Celular
        ttk.Label(main_frame, text="Celular:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="w", pady=(0, 5))
        celular_entry = ttk.Entry(main_frame, textvariable=self.celular_var, width=15, font=("Arial", 11))
        celular_entry.grid(row=7, column=0, sticky="w", pady=(0, 15))

        # Cliente
        ttk.Label(main_frame, text="Cliente:", font=("Arial", 10, "bold")).grid(row=8, column=0, sticky="w", pady=(0, 5))
        cliente_frame = ttk.Frame(main_frame)
        cliente_frame.grid(row=9, column=0, sticky="ew", pady=(0, 20))

        # Combobox con lista de clientes
        clientes = [""] + self.gestor.obtener_lista_clientes()
        cliente_combo = ttk.Combobox(cliente_frame, textvariable=self.cliente_var,
                                   values=clientes, width=20, state="readonly", font=("Arial", 11))
        cliente_combo.pack(side="left")

        # Botón para ver detalles del cliente
        ttk.Button(cliente_frame, text="👁️ Ver",
                  command=self.ver_detalle_cliente).pack(side="left", padx=(10, 0))

        # Botones principales
        botones_frame = ttk.Frame(main_frame)
        botones_frame.grid(row=10, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(botones_frame, text="💾 Guardar",
                  command=self.guardar_atencion,
                  style="Accent.TButton").pack(side="left", padx=(0, 10))

        ttk.Button(botones_frame, text="❌ Cancelar",
                  command=self.ventana.destroy).pack(side="left")

        # Configurar grid
        main_frame.grid_columnconfigure(0, weight=1)

        # Shortcuts
        self.ventana.bind("<Control-s>", lambda e: self.guardar_atencion())
        self.ventana.bind("<Escape>", lambda e: self.ventana.destroy())
        self.ventana.bind("<Control-Return>", lambda e: self.guardar_atencion())

    def ver_detalle_cliente(self):
        """Muestra detalles del cliente seleccionado"""
        codigo_cliente = self.cliente_var.get()
        if not codigo_cliente:
            messagebox.showinfo("Información", "Seleccione un cliente para ver sus detalles")
            return

        cliente = self.gestor.obtener_cliente_por_codigo(codigo_cliente)
        if cliente:
            detalle = f"""📋 DETALLES DEL CLIENTE

🏢 Código: {cliente['codigo']}
📄 Razón Social: {cliente['razon_social']}
🆔 RUC: {cliente['ruc']}
📍 Ubicación: {cliente['ubicacion']}

👥 Atenciones asociadas: {len(self.gestor.obtener_atenciones_por_cliente(codigo_cliente))}
"""
            messagebox.showinfo("Detalle del Cliente", detalle)
        else:
            messagebox.showwarning("Advertencia", f"No se encontró el cliente '{codigo_cliente}'")

    def guardar_atencion(self):
        """Guarda la atención (nueva o editada)"""
        try:
            codigo = self.codigo_var.get().strip()
            nombres = self.nombres_var.get().strip()
            correo = self.correo_var.get().strip()
            celular = self.celular_var.get().strip()
            cliente = self.cliente_var.get().strip()

            # Validaciones básicas
            if not codigo:
                raise ValueError("El código es obligatorio")
            if not nombres:
                raise ValueError("Los nombres son obligatorios")

            # Validar formato de código
            if not re.match(r'^[A-Za-z0-9_-]+$', codigo):
                raise ValueError("El código solo puede contener letras, números, guiones y guiones bajos")

            if self.indice is None:
                # Nueva atención
                self.gestor.agregar_atencion(codigo, nombres, correo, celular, cliente)
                messagebox.showinfo("Éxito", f"Atención '{codigo}' agregada correctamente")
            else:
                # Editar atención
                self.gestor.modificar_atencion(self.indice, codigo, nombres, correo, celular, cliente)
                messagebox.showinfo("Éxito", f"Atención '{codigo}' modificada correctamente")

            # Callback para actualizar vista
            if self.callback:
                self.callback()

            self.ventana.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))


# Función principal para abrir la gestión desde el programa principal
def abrir_gestion_datos(parent):
    """Función para abrir la gestión de datos desde el programa principal"""
    try:
        # Obtener ruta del Excel
        from configuracion import ConfiguracionManager
        config_manager = ConfiguracionManager()
        ruta_excel = config_manager.get_ruta_plantilla()

        # Verificar dependencias
        try:
            import openpyxl
        except ImportError:
            respuesta = messagebox.askyesno(
                "Dependencias faltantes",
                "Se requiere openpyxl para gestionar datos del Excel.\n\n"
                "¿Desea instalarlo automáticamente?"
            )
            if respuesta:
                import subprocess
                import sys
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
                    messagebox.showinfo("Éxito", "openpyxl instalado correctamente")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo instalar openpyxl:\n{e}")
                    return
            else:
                return

        # Abrir ventana de gestión
        VentanaGestionDatos(parent, ruta_excel)

    except Exception as e:
        messagebox.showerror("Error", f"Error abriendo gestión de datos:\n{str(e)}")
