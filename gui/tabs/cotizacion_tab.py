# -*- coding: utf-8 -*-
"""
Pestana de cotizacion
"""
import tkinter as tk
from tkinter import ttk, messagebox
from ..logica import (
    configurar_sistema,
    cotizar_bandeja_con_tipo,
    cotizar_curva_horizontal_con_tipo,
    cotizar_curva_vertical_con_tipo,
    cotizar_tee_con_tipo,
    cotizar_cruz_con_tipo,
    cotizar_reduccion_con_tipo,
    cotizar_caja_de_pase_con_tipo,
    agregar_al_carrito_gui,
    carrito,
)


class CotizacionTab:
    """Pestana de cotizacion de productos"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Variables
        self.tipo_superficie_var = tk.StringVar(value="LISA")
        self.tipo_salida_var = tk.StringVar(value="CIEGA")
        self.metro_lineal_var = tk.BooleanVar(value=False)
        self.recordar_medidas_var = tk.BooleanVar(value=False)
        
        self.ultimas_medidas = {
            'ancho': '', 'alto': '', 'largo': '',
            'derecha': '', 'izquierda': '', 'abajo': '',
            'ancho_mayor': '', 'ancho_menor': '', 'origen': ''
        }
        
        # Crear frame principal
        self.frame = ttk.Frame(parent)
        self.frame.configure(style="Background.TFrame")
        
        # Crear interfaz
        self.crear_interfaz()
                    
        # Enfocar primer campo de medidas al mostrar la pestaña
        def enfocar_medidas(event=None):
            self.enfocar_primer_campo_medidas()
        
        self.frame.bind("<Visibility>", enfocar_medidas)
    
    def crear_interfaz(self):
        """Crea la interfaz de cotizacion"""
        main_container = ttk.Frame(self.frame)
        main_container.pack(expand=True)
        
        content_frame = ttk.Frame(main_container, width=757, height=757)
        content_frame.pack(padx=20, pady=20)
        content_frame.pack_propagate(False)
        
        main_content = ttk.Frame(content_frame)
        main_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame de configuracion
        self.crear_frame_configuracion(main_content)
        
        # Frame de producto
        self.crear_frame_producto(main_content)
    
    def crear_frame_configuracion(self, parent):
        """Crea el frame de configuracion de precios"""
        config_frame = ttk.LabelFrame(parent, text="Configuracion", padding=8)
        config_frame.pack(fill="x", pady=(0, 8))
        
        # Primera fila: Ganancia y Galvanizado
        config_row1 = ttk.Frame(config_frame)
        config_row1.pack(fill="x", pady=(0, 6))
        
        # Factor de ganancia
        ganancia_frame = ttk.LabelFrame(config_row1, text="Factor de Ganancia", padding=6)
        ganancia_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        self.ganancia_var = tk.StringVar(value="30")
        ttk.Radiobutton(ganancia_frame, text="SIN COMISIÓN", 
                       variable=self.ganancia_var, value="30").pack(anchor="w", pady=1)
        ttk.Radiobutton(ganancia_frame, text="CON COMISIÓN", 
                       variable=self.ganancia_var, value="35").pack(anchor="w", pady=1)
        
        # Tipo de galvanizado
        galv_frame = ttk.LabelFrame(config_row1, text="Tipo de Galvanizado", padding=6)
        galv_frame.pack(side="right", fill="both", expand=True)
        
        self.galvanizado_var = tk.StringVar(value="GO")
        ttk.Radiobutton(galv_frame, text="GO - Galvanizado de Origen", 
                       variable=self.galvanizado_var, value="GO", 
                       command=self.on_galvanizado_change).pack(anchor="w", pady=1)
        ttk.Radiobutton(galv_frame, text="GC - Galvanizado en Caliente", 
                       variable=self.galvanizado_var, value="GC",
                       command=self.on_galvanizado_change).pack(anchor="w", pady=1)
        
        # Segunda fila: Precios
        self.crear_frame_precios(config_frame)
    
    def crear_frame_precios(self, parent):
        """Crea el frame de precios de planchas"""
        precios_frame = ttk.LabelFrame(parent, text="Precios de Planchas", padding=6)
        precios_frame.pack(fill="x")
        
        precios_container = ttk.Frame(precios_frame)
        precios_container.pack(fill="x")
        
        # Precios GO
        go_frame = ttk.LabelFrame(precios_container, text="Precios GO (S/)", padding=6)
        go_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        ttk.Label(go_frame, text="PL 1.2mm:").grid(row=0, column=0, sticky="w", pady=1)
        self.precio_go_12_var = tk.StringVar()
        ttk.Entry(go_frame, textvariable=self.precio_go_12_var, width=10).grid(row=0, column=1, padx=(4, 0), pady=1)
        
        ttk.Label(go_frame, text="PL 1.5mm:").grid(row=1, column=0, sticky="w", pady=1)
        self.precio_go_15_var = tk.StringVar()
        ttk.Entry(go_frame, textvariable=self.precio_go_15_var, width=10).grid(row=1, column=1, padx=(4, 0), pady=1)
        
        ttk.Label(go_frame, text="PL 2.0mm:").grid(row=2, column=0, sticky="w", pady=1)
        self.precio_go_20_var = tk.StringVar()
        ttk.Entry(go_frame, textvariable=self.precio_go_20_var, width=10).grid(row=2, column=1, padx=(4, 0), pady=1)
        
        # Precios GC
        self.gc_frame = ttk.LabelFrame(precios_container, text="Precios GC", padding=6)
        self.gc_frame.pack(side="right", fill="both", expand=True)
        
        ttk.Label(self.gc_frame, text="Dolar (S/):").grid(row=0, column=0, sticky="w", pady=1)
        self.dolar_var = tk.StringVar()
        ttk.Entry(self.gc_frame, textvariable=self.dolar_var, width=8).grid(row=0, column=1, padx=(4, 0), pady=1)
        
        ttk.Label(self.gc_frame, text="Galv.(USD/kg):").grid(row=0, column=2, sticky="w", pady=1, padx=(6, 0))
        self.precio_galv_var = tk.StringVar()
        ttk.Entry(self.gc_frame, textvariable=self.precio_galv_var, width=8).grid(row=0, column=3, padx=(4, 0), pady=1)
        
        ttk.Label(self.gc_frame, text="PL 1.2mm:").grid(row=1, column=0, sticky="w", pady=1)
        self.precio_gc_12_var = tk.StringVar()
        ttk.Entry(self.gc_frame, textvariable=self.precio_gc_12_var, width=8).grid(row=1, column=1, padx=(4, 0), pady=1)
        
        ttk.Label(self.gc_frame, text="PL 1.5mm:").grid(row=1, column=2, sticky="w", pady=1, padx=(6, 0))
        self.precio_gc_15_var = tk.StringVar()
        ttk.Entry(self.gc_frame, textvariable=self.precio_gc_15_var, width=8).grid(row=1, column=3, padx=(4, 0), pady=1)
        
        ttk.Label(self.gc_frame, text="PL 2.0mm:").grid(row=2, column=0, sticky="w", pady=1)
        self.precio_gc_20_var = tk.StringVar()
        ttk.Entry(self.gc_frame, textvariable=self.precio_gc_20_var, width=8).grid(row=2, column=1, padx=(4, 0), pady=1)
    
    def on_galvanizado_change(self):
        """Maneja el cambio de tipo de galvanizado"""
        tipo_galv = self.galvanizado_var.get()
        
        for widget in self.gc_frame.winfo_children():
            if isinstance(widget, ttk.Entry):
                if tipo_galv == "GC":
                    widget.configure(state="normal")
                else:
                    widget.configure(state="disabled")
    
    def crear_frame_producto(self, parent):
        """Crea el frame de seleccion de producto"""
        producto_frame = ttk.LabelFrame(parent, text="Cotizacion de Productos", padding=8)
        producto_frame.pack(fill="both", expand=True)
        
        producto_frame.grid_columnconfigure(0, weight=1)
        producto_frame.grid_columnconfigure(1, weight=1)
        producto_frame.grid_columnconfigure(2, weight=1)
        producto_frame.grid_rowconfigure(1, weight=1)
        
        # Seleccion de producto
        seleccion_frame = ttk.LabelFrame(producto_frame, text="Seleccionar Producto", padding=6)
        seleccion_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 6), pady=(0, 8))
        
        self.producto_var = tk.StringVar(value="B")
        productos = [
            ("B", "BANDEJA CON TAPA"),
            ("CH", "CURVA HORIZONTAL CON TAPA"),
            ("CVE", "CURVA VERTICAL EXTERNA CON TAPA"),
            ("CVI", "CURVA VERTICAL INTERNA CON TAPA"),
            ("T", "TEE CON TAPA"),
            ("C", "CRUZ CON TAPA"),
            ("R", "REDUCCION CON TAPA"),
            ("CP", "CAJA DE PASE")
        ]
        
        productos_grid = ttk.Frame(seleccion_frame)
        productos_grid.pack(fill="x")
        
        for i, (codigo, nombre) in enumerate(productos):
            row = i // 2
            col = i % 2
            ttk.Radiobutton(productos_grid, text=nombre, 
                           variable=self.producto_var, value=codigo,
                           command=self.on_producto_change).grid(row=row, column=col, sticky="w", padx=(0, 15), pady=1)
        
        # Medidas
        medidas_container = ttk.LabelFrame(producto_frame, text="Medidas del Producto", padding=6)
        medidas_container.grid(row=1, column=0, sticky="nsew", padx=(0, 3), pady=0)
        
        self.medidas_frame = ttk.Frame(medidas_container)
        self.medidas_frame.pack(fill="both", expand=True)
        
        # Espesores
        espesores_container = ttk.LabelFrame(producto_frame, text="Espesores", padding=6)
        espesores_container.grid(row=1, column=1, sticky="nsew", padx=(3, 6), pady=0)
        
        ttk.Label(espesores_container, text="Espesor Producto (mm):").grid(row=0, column=0, sticky="w", pady=2)
        self.espesor_producto_var = tk.StringVar(value="1.5")
        ttk.Combobox(espesores_container, textvariable=self.espesor_producto_var, 
                    values=["1.2", "1.5", "2.0"], width=10, state="readonly").grid(row=0, column=1, padx=(4, 0), pady=2)
        
        ttk.Label(espesores_container, text="Espesor Tapa (mm):").grid(row=1, column=0, sticky="w", pady=2)
        self.espesor_tapa_var = tk.StringVar(value="1.2")
        ttk.Combobox(espesores_container, textvariable=self.espesor_tapa_var, 
                    values=["1.2", "1.5", "2.0"], width=10, state="readonly").grid(row=1, column=1, padx=(4, 0), pady=2)
        
        # Cantidad y acciones
        acciones_container = ttk.LabelFrame(producto_frame, text="Cantidad y Acciones", padding=6)
        acciones_container.grid(row=0, column=2, rowspan=3, sticky="nsew", padx=(6, 0), pady=0)
        
        self.tipos_frame = ttk.Frame(acciones_container)
        self.tipos_frame.pack(fill="x", pady=(0, 15))
        
        cantidad_frame = ttk.Frame(acciones_container)
        cantidad_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(cantidad_frame, text="Cantidad:").pack(side="left")
        self.cantidad_var = tk.StringVar(value="1")
        self.cantidad_entry = ttk.Entry(cantidad_frame, textvariable=self.cantidad_var, width=12)
        self.cantidad_entry.pack(side="right")
        
        self.metro_lineal_check = ttk.Checkbutton(acciones_container, text="Cotizar por Metro Lineal", 
                                                variable=self.metro_lineal_var,
                                                command=self.on_metro_lineal_change)
        
        ttk.Button(acciones_container, text="Cotizar y Agregar", 
                command=self.cotizar_producto,
                style="Accent.TButton").pack(fill="x", pady=(15, 2))
        
        # Status
        status_frame = ttk.Frame(producto_frame)
        status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Configure los precios y seleccione un producto", 
                                    foreground="blue")
        self.status_label.pack()
        
        # Inicializar
        self.on_producto_change()

    def on_producto_change(self):
        """Maneja el cambio de producto seleccionado"""
        # Limpiar frame de medidas
        for widget in self.medidas_frame.winfo_children():
            widget.destroy()
        
        # Limpiar frame de tipos
        for widget in self.tipos_frame.winfo_children():
            widget.destroy()
        
        # Ocultar checkbox metro lineal
        self.metro_lineal_check.pack_forget()
        
        producto = self.producto_var.get()
        
        # Configurar USD/kg segun producto
        if producto == "CP":
            self.precio_galv_var.set("3")
            for widget in self.gc_frame.winfo_children():
                if isinstance(widget, ttk.Entry) and str(widget['textvariable']) == str(self.precio_galv_var):
                    widget.configure(state="disabled")
                    break
        else:
            self.precio_galv_var.set("1")
            for widget in self.gc_frame.winfo_children():
                if isinstance(widget, ttk.Entry) and str(widget['textvariable']) == str(self.precio_galv_var):
                    if self.galvanizado_var.get() == "GC":
                        widget.configure(state="normal")
                    else:
                        widget.configure(state="disabled")
                    break
        
        # Crear tipos segun producto
        if producto == "CP":
            ttk.Label(self.tipos_frame, text="Tipo de salida:", font=("Arial", 9, "bold")).pack(anchor="w")
            for valor, texto in [("CIEGA", "CIEGA"), ("3/4", "3/4\""), ("1/2", "1/2\""), ("1", "1\"")]:
                ttk.Radiobutton(self.tipos_frame, text=texto, 
                            variable=self.tipo_salida_var, value=valor).pack(anchor="w", pady=1)
        
        elif producto:
            ttk.Label(self.tipos_frame, text="Tipo de superficie:", font=("Arial", 9, "bold")).pack(anchor="w")
            for valor, texto in [("RANURADA", "Ranurada"), ("ESCALERILLA", "Escalerilla"), ("LISA", "Lisa")]:
                ttk.Radiobutton(self.tipos_frame, text=texto, 
                            variable=self.tipo_superficie_var, value=valor).pack(anchor="w", pady=1)

            if producto == "B":
                self.metro_lineal_check.pack(anchor="w", pady=(10, 0))
        
        # Resetear valores
        self.tipo_superficie_var.set("RANURADA")
        self.tipo_salida_var.set("CIEGA")
        self.metro_lineal_var.set(False)
        self.cantidad_var.set("0")
        
        # Crear campos de medidas
        self.crear_campos_medidas(producto)
    
    def guardar_medidas_actuales(self, producto):
            """Guarda las medidas actuales según el producto"""
            try:
                if producto in ["B", "CH", "CVE", "CVI", "C"]:
                    self.ultimas_medidas['ancho'] = self.ancho_var.get()
                    self.ultimas_medidas['alto'] = self.alto_var.get()
                    self.ultimas_medidas['origen'] = producto
                    print(f"💾 Medidas guardadas: {self.ancho_var.get()} x {self.alto_var.get()} (origen: {producto})")
                
                elif producto == "T":
                    # Guardar medidas específicas de TEE
                    self.ultimas_medidas['derecha'] = self.derecha_var.get()
                    self.ultimas_medidas['izquierda'] = self.izquierda_var.get()
                    self.ultimas_medidas['abajo'] = self.abajo_var.get()
                    self.ultimas_medidas['alto'] = self.alto_var.get()
                    
                    # TAMBIÉN guardar como ancho/alto para compatibilidad con otros productos
                    # Usar "derecha" como ancho de referencia
                    self.ultimas_medidas['ancho'] = self.derecha_var.get()
                    self.ultimas_medidas['origen'] = producto
                    print(f"💾 Medidas TEE guardadas (derecha como ancho: {self.derecha_var.get()})")
                
                elif producto == "R":
                    self.ultimas_medidas['ancho_mayor'] = self.ancho_mayor_var.get()
                    self.ultimas_medidas['alto'] = self.alto_var.get()
                    self.ultimas_medidas['ancho_menor'] = self.ancho_menor_var.get()
                    self.ultimas_medidas['origen'] = producto
                    print(f"💾 Medidas REDUCCIÓN guardadas")
                
                elif producto == "CP":
                    # Caja de pase no guarda medidas (son diferentes cada vez)
                    pass
                    
            except Exception as e:
                print(f"⚠️ Error guardando medidas: {e}")
    
    def cargar_medidas_guardadas(self, producto_actual):
        """Carga las medidas guardadas si son compatibles con el producto actual"""
        try:
            origen = self.ultimas_medidas.get('origen')
            
            print(f"🔍 Cargando medidas: origen={origen}, destino={producto_actual}")
            print(f"🔍 Medidas disponibles: {self.ultimas_medidas}")
            
            # Productos compatibles: B, CH, CVE, CVI, C (todos usan ancho x alto)
            productos_compatibles_ancho_alto = ["B", "CH", "CVE", "CVI", "C"]
            
            if producto_actual in productos_compatibles_ancho_alto:
                # CRUZ, BANDEJA, CURVAS, etc - todos usan ancho x alto
                ancho_guardado = self.ultimas_medidas.get('ancho')
                alto_guardado = self.ultimas_medidas.get('alto')
                
                if ancho_guardado:
                    self.ancho_var.set(ancho_guardado)
                    print(f"📥 Ancho cargado: {ancho_guardado}")
                
                if alto_guardado:
                    self.alto_var.set(alto_guardado)
                    print(f"📥 Alto cargado: {alto_guardado}")
            
            elif producto_actual == "T":
                # TEE: Si viene de producto ancho x alto, usar ancho para derecha/izquierda/abajo
                if origen in productos_compatibles_ancho_alto:
                    ancho_guardado = self.ultimas_medidas.get('ancho')
                    alto_guardado = self.ultimas_medidas.get('alto')
                    
                    if ancho_guardado:
                        # Derecha, Izquierda y Abajo = ancho de la bandeja
                        self.derecha_var.set(ancho_guardado)
                        self.izquierda_var.set(ancho_guardado)
                        self.abajo_var.set(ancho_guardado)
                        print(f"📥 TEE: Derecha/Izquierda/Abajo = {ancho_guardado}")
                    
                    if alto_guardado:
                        # Alto se mantiene
                        self.alto_var.set(alto_guardado)
                        print(f"📥 TEE: Alto = {alto_guardado}")
                
                elif origen == "T":
                    # Si viene de otra TEE, cargar tal cual
                    if self.ultimas_medidas.get('derecha'):
                        self.derecha_var.set(self.ultimas_medidas['derecha'])
                    if self.ultimas_medidas.get('izquierda'):
                        self.izquierda_var.set(self.ultimas_medidas['izquierda'])
                    if self.ultimas_medidas.get('abajo'):
                        self.abajo_var.set(self.ultimas_medidas['abajo'])
                    if self.ultimas_medidas.get('alto'):
                        self.alto_var.set(self.ultimas_medidas['alto'])
                    print(f"📥 Medidas TEE cargadas desde otra TEE")
            
            elif producto_actual == "R":
                # REDUCCIÓN: ancho mayor = ancho guardado, ancho menor = ancho - 100
                ancho_guardado = self.ultimas_medidas.get('ancho')
                alto_guardado = self.ultimas_medidas.get('alto')
                
                if ancho_guardado:
                    try:
                        ancho_num = float(ancho_guardado)
                        ancho_menor = ancho_num - 100
                        
                        self.ancho_mayor_var.set(str(ancho_guardado))
                        self.ancho_menor_var.set(str(int(ancho_menor)))
                        print(f"📥 REDUCCIÓN: {ancho_guardado} → {int(ancho_menor)} (menor 100mm)")
                    except ValueError:
                        print(f"⚠️ No se pudo calcular ancho menor")
                
                if alto_guardado:
                    # Alto se mantiene
                    self.alto_var.set(alto_guardado)
                    print(f"📥 REDUCCIÓN: Alto = {alto_guardado}")
            
        except Exception as e:
            print(f"⚠️ Error cargando medidas: {e}")
            import traceback
            traceback.print_exc()

    def crear_campos_medidas(self, producto):
        """Crea los campos de medidas segun el producto"""
        if producto in ["B", "CH", "CVE", "CVI", "C"]:
            ttk.Label(self.medidas_frame, text="Ancho (mm):").grid(row=0, column=0, sticky="w", pady=2)
            self.ancho_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.ancho_var, width=15).grid(row=0, column=1, padx=(10, 0), pady=2)
            
            ttk.Label(self.medidas_frame, text="Alto (mm):").grid(row=1, column=0, sticky="w", pady=2)
            self.alto_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.alto_var, width=15).grid(row=1, column=1, padx=(10, 0), pady=2)
        
        elif producto == "T":
            ttk.Label(self.medidas_frame, text="Derecha (mm):").grid(row=0, column=0, sticky="w", pady=2)
            self.derecha_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.derecha_var, width=15).grid(row=0, column=1, padx=(10, 0), pady=2)
            
            ttk.Label(self.medidas_frame, text="Izquierda (mm):").grid(row=1, column=0, sticky="w", pady=2)
            self.izquierda_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.izquierda_var, width=15).grid(row=1, column=1, padx=(10, 0), pady=2)
            
            ttk.Label(self.medidas_frame, text="Abajo (mm):").grid(row=2, column=0, sticky="w", pady=2)
            self.abajo_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.abajo_var, width=15).grid(row=2, column=1, padx=(10, 0), pady=2)
            
            ttk.Label(self.medidas_frame, text="Alto (mm):").grid(row=3, column=0, sticky="w", pady=2)
            self.alto_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.alto_var, width=15).grid(row=3, column=1, padx=(10, 0), pady=2)
        
        elif producto == "R":
            ttk.Label(self.medidas_frame, text="Ancho Mayor (mm):").grid(row=0, column=0, sticky="w", pady=2)
            self.ancho_mayor_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.ancho_mayor_var, width=15).grid(row=0, column=1, padx=(10, 0), pady=2)
            
            ttk.Label(self.medidas_frame, text="Alto (mm):").grid(row=1, column=0, sticky="w", pady=2)
            self.alto_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.alto_var, width=15).grid(row=1, column=1, padx=(10, 0), pady=2)
            
            ttk.Label(self.medidas_frame, text="Ancho Menor (mm):").grid(row=2, column=0, sticky="w", pady=2)
            self.ancho_menor_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.ancho_menor_var, width=15).grid(row=2, column=1, padx=(10, 0), pady=2)
        
        elif producto == "CP":
            ttk.Label(self.medidas_frame, text="Ancho (cm):").grid(row=0, column=0, sticky="w", pady=2)
            self.ancho_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.ancho_var, width=15).grid(row=0, column=1, padx=(10, 0), pady=2)
            
            ttk.Label(self.medidas_frame, text="Largo (cm):").grid(row=1, column=0, sticky="w", pady=2)
            self.largo_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.largo_var, width=15).grid(row=1, column=1, padx=(10, 0), pady=2)
            
            ttk.Label(self.medidas_frame, text="Alto (cm):").grid(row=2, column=0, sticky="w", pady=2)
            self.alto_var = tk.StringVar()
            ttk.Entry(self.medidas_frame, textvariable=self.alto_var, width=15).grid(row=2, column=1, padx=(10, 0), pady=2)
            
            info_label = ttk.Label(self.medidas_frame, 
                                text="El sistema ordenara automaticamente:\nMayor -> Ancho, Intermedio -> Largo, Menor -> Alto", 
                                font=("Arial", 8), foreground="blue")
            info_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
            
            self.sincronizar_espesores_caja_pase()
        
        # Agregar checkbox recordar medidas (excepto para CP)
        if producto != "CP":
            self.crear_checkbox_recordar_medidas()

        # ===== NUEVO: CARGAR MEDIDAS GUARDADAS =====
        if self.recordar_medidas_var.get() and self.ultimas_medidas.get('origen'):
            self.cargar_medidas_guardadas(producto)

        # ===== CONFIGURAR TAB PARA MOVER FOCO A CANTIDAD =====
        # Buscar todos los Entry de medidas y configurar Tab
        for widget in self.medidas_frame.winfo_children():
            if isinstance(widget, ttk.Entry):
                widget.bind("<Tab>", self.manejar_tab_en_medidas)
                widget.bind("<Return>", lambda e: self.enfocar_cantidad())    
        
        # ===== ENFOCAR AUTOMÁTICAMENTE EL PRIMER CAMPO DE MEDIDAS =====
        self.app.root.after(100, self.enfocar_primer_campo_medidas)
    
    def sincronizar_espesores_caja_pase(self):
        """Sincroniza espesores para caja de pase"""
        def on_espesor_change(*args):
            if self.producto_var.get() == "CP":
                espesor_actual = self.espesor_producto_var.get()
                self.espesor_tapa_var.set(espesor_actual)
        
        self.espesor_producto_var.trace('w', on_espesor_change)
    
    def crear_checkbox_recordar_medidas(self):
        """Crea checkbox para recordar medidas"""
        max_row = 0
        for child in self.medidas_frame.winfo_children():
            if hasattr(child, 'grid_info'):
                info = child.grid_info()
                if info and 'row' in info:
                    max_row = max(max_row, int(info['row']))
        
        self.familia_frame = ttk.Frame(self.medidas_frame)
        self.familia_frame.grid(row=max_row + 1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        
        ttk.Checkbutton(self.familia_frame, text="Recordar medidas", 
                       variable=self.recordar_medidas_var).pack(anchor="w")
    
    def on_metro_lineal_change(self):
        """Maneja el cambio en metro lineal"""
        if self.metro_lineal_var.get():
            self.cantidad_entry.configure(validate="key", 
                                        validatecommand=(self.app.root.register(self.validar_decimal), '%P'))
        else:
            self.cantidad_entry.configure(validate="key", 
                                        validatecommand=(self.app.root.register(self.validar_entero), '%P'))
    
    def validar_decimal(self, valor):
        """Valida numero decimal"""
        if valor == "":
            return True
        try:
            float(valor)
            return float(valor) > 0
        except:
            return False
    
    def validar_entero(self, valor):
        """Valida numero entero"""
        if valor == "":
            return True
        try:
            int(valor)
            return int(valor) > 0
        except:
            return False

    def cotizar_producto(self):
        """Cotiza el producto y lo agrega al carrito"""
        try:
            # Validar configuracion
            self.validar_configuracion()
            
            # Configurar logica
            self.configurar_logica()
            
            # Obtener precios de plancha
            espesor_producto = float(self.espesor_producto_var.get())
            espesor_tapa = float(self.espesor_tapa_var.get())
            precio_plancha_producto = self.obtener_precio_plancha(espesor_producto)
            precio_plancha_tapa = self.obtener_precio_plancha(espesor_tapa)
            
            producto = self.producto_var.get()
            cantidad = float(self.cantidad_var.get()) if self.metro_lineal_var.get() else int(self.cantidad_var.get())
            
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
            
            # Guardar medidas si está activado "Recordar medidas"
            if self.recordar_medidas_var.get():
                self.guardar_medidas_actuales(producto)
            
            # Cotizar segun tipo de producto
            if producto == "B":
                self.cotizar_bandeja(precio_plancha_producto, precio_plancha_tapa, cantidad)
            elif producto == "CH":
                self.cotizar_curva_horizontal(precio_plancha_producto, precio_plancha_tapa, cantidad)
            elif producto == "CVE":
                self.cotizar_curva_vertical_externa(precio_plancha_producto, precio_plancha_tapa, cantidad)
            elif producto == "CVI":
                self.cotizar_curva_vertical_interna(precio_plancha_producto, precio_plancha_tapa, cantidad)
            elif producto == "T":
                self.cotizar_tee(precio_plancha_producto, precio_plancha_tapa, cantidad)
            elif producto == "C":
                self.cotizar_cruz(precio_plancha_producto, precio_plancha_tapa, cantidad)
            elif producto == "R":
                self.cotizar_reduccion(precio_plancha_producto, precio_plancha_tapa, cantidad)
            elif producto == "CP":
                self.cotizar_caja_pase(precio_plancha_producto, cantidad)
            
        # Actualizar carrito
            self.app.carrito_tab.actualizar_carrito()
            
            # Actualizar contador
            cantidad_items = len(carrito)
            if cantidad_items == 1:
                texto_contador = "1 producto en el carrito"
            else:
                texto_contador = f"{cantidad_items} productos en el carrito"
            
            self.status_label.configure(text=texto_contador, foreground="green")
            
            # Resetear cantidad a 0 (fusible anti-error)
            self.cantidad_var.set("0")
            
            # Regresar foco a medidas para siguiente producto
            self.app.root.after(100, self.enfocar_primer_campo_medidas)

        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.status_label.configure(text=f"Error: {str(e)}", foreground="red")
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado: {str(e)}")
            self.status_label.configure(text="Error al cotizar", foreground="red")
    
    def cotizar_bandeja(self, precio_plancha_prod, precio_plancha_tapa, cantidad):
            """Cotiza una bandeja"""
            ancho = float(self.ancho_var.get())
            alto = float(self.alto_var.get())
            tipo_superficie = self.tipo_superficie_var.get()
            es_metro_lineal = self.metro_lineal_var.get()
            espesor_prod = float(self.espesor_producto_var.get())
            espesor_tapa = float(self.espesor_tapa_var.get())
            
            # Llamar a la función correcta
            resultados = cotizar_bandeja_con_tipo(
                precio_plancha_prod, precio_plancha_tapa,
                espesor_prod, espesor_tapa,
                ancho, alto, tipo_superficie, es_metro_lineal
            )
            
            # Agregar cada resultado al carrito
            for resultado in resultados:
                unidad = "ML" if es_metro_lineal else "UND"
                agregar_al_carrito_gui(
                    resultado['tipo'],
                    resultado['descripcion'],
                    resultado['precio_unitario'],
                    resultado['peso_unitario'],
                    cantidad,
                    unidad
                )

    def cotizar_curva_horizontal(self, precio_plancha_prod, precio_plancha_tapa, cantidad):
            """Cotiza una curva horizontal"""
            ancho = float(self.ancho_var.get())
            alto = float(self.alto_var.get())
            tipo_superficie = self.tipo_superficie_var.get()
            espesor_prod = float(self.espesor_producto_var.get())
            espesor_tapa = float(self.espesor_tapa_var.get())
            
            resultados = cotizar_curva_horizontal_con_tipo(
                precio_plancha_prod, precio_plancha_tapa,
                espesor_prod, espesor_tapa,
                ancho, alto, tipo_superficie
            )
            
            for resultado in resultados:
                agregar_al_carrito_gui(
                    resultado['tipo'],
                    resultado['descripcion'],
                    resultado['precio_unitario'],
                    resultado['peso_unitario'],
                    cantidad,
                    "UND"
                )

    def cotizar_curva_vertical_externa(self, precio_plancha_prod, precio_plancha_tapa, cantidad):
            """Cotiza una curva vertical externa"""
            ancho = float(self.ancho_var.get())
            alto = float(self.alto_var.get())
            tipo_superficie = self.tipo_superficie_var.get()
            espesor_prod = float(self.espesor_producto_var.get())
            espesor_tapa = float(self.espesor_tapa_var.get())
            
            resultados = cotizar_curva_vertical_con_tipo(
                precio_plancha_prod, precio_plancha_tapa,
                espesor_prod, espesor_tapa,
                ancho, alto, "EXTERNA", tipo_superficie
            )
            
            for resultado in resultados:
                agregar_al_carrito_gui(
                    resultado['tipo'],
                    resultado['descripcion'],
                    resultado['precio_unitario'],
                    resultado['peso_unitario'],
                    cantidad,
                    "UND"
                )

    def cotizar_curva_vertical_interna(self, precio_plancha_prod, precio_plancha_tapa, cantidad):
            """Cotiza una curva vertical interna"""
            ancho = float(self.ancho_var.get())
            alto = float(self.alto_var.get())
            tipo_superficie = self.tipo_superficie_var.get()
            espesor_prod = float(self.espesor_producto_var.get())
            espesor_tapa = float(self.espesor_tapa_var.get())
            
            resultados = cotizar_curva_vertical_con_tipo(
                precio_plancha_prod, precio_plancha_tapa,
                espesor_prod, espesor_tapa,
                ancho, alto, "INTERNA", tipo_superficie
            )
            
            for resultado in resultados:
                agregar_al_carrito_gui(
                    resultado['tipo'],
                    resultado['descripcion'],
                    resultado['precio_unitario'],
                    resultado['peso_unitario'],
                    cantidad,
                    "UND"
                )

    def cotizar_tee(self, precio_plancha_prod, precio_plancha_tapa, cantidad):
            """Cotiza un TEE"""
            derecha = float(self.derecha_var.get())
            izquierda = float(self.izquierda_var.get())
            abajo = float(self.abajo_var.get())
            alto = float(self.alto_var.get())
            tipo_superficie = self.tipo_superficie_var.get()
            espesor_prod = float(self.espesor_producto_var.get())
            espesor_tapa = float(self.espesor_tapa_var.get())
            
            resultados = cotizar_tee_con_tipo(
                precio_plancha_prod, precio_plancha_tapa,
                espesor_prod, espesor_tapa,
                derecha, izquierda, abajo, alto, tipo_superficie
            )
            
            for resultado in resultados:
                agregar_al_carrito_gui(
                    resultado['tipo'],
                    resultado['descripcion'],
                    resultado['precio_unitario'],
                    resultado['peso_unitario'],
                    cantidad,
                    "UND"
                )

    
    def cotizar_cruz(self, precio_plancha_prod, precio_plancha_tapa, cantidad):
            """Cotiza una cruz"""
            ancho = float(self.ancho_var.get())
            alto = float(self.alto_var.get())
            tipo_superficie = self.tipo_superficie_var.get()
            espesor_prod = float(self.espesor_producto_var.get())
            espesor_tapa = float(self.espesor_tapa_var.get())
            
            resultados = cotizar_cruz_con_tipo(
                precio_plancha_prod, precio_plancha_tapa,
                espesor_prod, espesor_tapa,
                ancho, alto, tipo_superficie
            )
            
            for resultado in resultados:
                agregar_al_carrito_gui(
                    resultado['tipo'],
                    resultado['descripcion'],
                    resultado['precio_unitario'],
                    resultado['peso_unitario'],
                    cantidad,
                    "UND"
                )

            
    def cotizar_reduccion(self, precio_plancha_prod, precio_plancha_tapa, cantidad):
            """Cotiza una reducción"""
            ancho_mayor = float(self.ancho_mayor_var.get())
            alto = float(self.alto_var.get())
            ancho_menor = float(self.ancho_menor_var.get())
            tipo_superficie = self.tipo_superficie_var.get()
            espesor_prod = float(self.espesor_producto_var.get())
            espesor_tapa = float(self.espesor_tapa_var.get())
            
            resultados = cotizar_reduccion_con_tipo(
                precio_plancha_prod, precio_plancha_tapa,
                espesor_prod, espesor_tapa,
                ancho_mayor, alto, ancho_menor, tipo_superficie
            )
            
            for resultado in resultados:
                agregar_al_carrito_gui(
                    resultado['tipo'],
                    resultado['descripcion'],
                    resultado['precio_unitario'],
                    resultado['peso_unitario'],
                    cantidad,
                    "UND"
                )

        
    def cotizar_caja_pase(self, precio_plancha, cantidad):
            """Cotiza una caja de pase"""
            dim1 = float(self.ancho_var.get())
            dim2 = float(self.largo_var.get())
            dim3 = float(self.alto_var.get())
            tipo_salida = self.tipo_salida_var.get()
            espesor = float(self.espesor_producto_var.get())
            
            resultados = cotizar_caja_de_pase_con_tipo(
                precio_plancha, precio_plancha,  # Mismo precio para producto y tapa
                espesor, espesor,  # Mismo espesor para producto y tapa
                dim1, dim2, dim3, tipo_salida
            )
            
            for resultado in resultados:
                agregar_al_carrito_gui(
                    resultado['tipo'],
                    resultado['descripcion'],
                    resultado['precio_unitario'],
                    resultado['peso_unitario'],
                    cantidad,
                    "UND"
                )
            
        
    def validar_configuracion(self):
        """Valida que la configuracion este completa"""
        tipo_galv = self.galvanizado_var.get()
        espesor_producto = float(self.espesor_producto_var.get())
        espesor_tapa = float(self.espesor_tapa_var.get())
        espesores_necesarios = {espesor_producto, espesor_tapa}
        
        if tipo_galv == "GO":
            for espesor in espesores_necesarios:
                if espesor == 1.2 and not self.precio_go_12_var.get():
                    raise ValueError("Debe llenar el precio de plancha GO 1.2mm")
                elif espesor == 1.5 and not self.precio_go_15_var.get():
                    raise ValueError("Debe llenar el precio de plancha GO 1.5mm")
                elif espesor == 2.0 and not self.precio_go_20_var.get():
                    raise ValueError("Debe llenar el precio de plancha GO 2.0mm")
        else:
            if not (self.dolar_var.get() and self.precio_galv_var.get()):
                raise ValueError("Debe llenar el precio del dolar y galvanizado para GC")
            
            for espesor in espesores_necesarios:
                if espesor == 1.2 and not self.precio_gc_12_var.get():
                    raise ValueError("Debe llenar el precio de plancha GC 1.2mm")
                elif espesor == 1.5 and not self.precio_gc_15_var.get():
                    raise ValueError("Debe llenar el precio de plancha GC 1.5mm")
                elif espesor == 2.0 and not self.precio_gc_20_var.get():
                    raise ValueError("Debe llenar el precio de plancha GC 2.0mm")
    
    def configurar_logica(self):
        """Configura las variables globales de logica.py"""
        ganancia_porcentaje = self.ganancia_var.get()
        tipo_galv = self.galvanizado_var.get()
        
        precio_dolar = 0
        precio_galv_kg = 0
        
        if tipo_galv == "GC":
            precio_dolar = float(self.dolar_var.get() or "0")
            precio_galv_kg = float(self.precio_galv_var.get() or "0")
        
        configurar_sistema(ganancia_porcentaje, tipo_galv, precio_dolar, precio_galv_kg)
    
    def obtener_precio_plancha(self, espesor):
        """Obtiene el precio de plancha segun tipo y espesor"""
        tipo_galv = self.galvanizado_var.get()
        
        try:
            if tipo_galv == "GO":
                if espesor == 1.2:
                    return float(self.precio_go_12_var.get() or "0")
                elif espesor == 1.5:
                    return float(self.precio_go_15_var.get() or "0")
                elif espesor == 2.0:
                    return float(self.precio_go_20_var.get() or "0")
            else:
                if espesor == 1.2:
                    return float(self.precio_gc_12_var.get() or "0")
                elif espesor == 1.5:
                    return float(self.precio_gc_15_var.get() or "0")
                elif espesor == 2.0:
                    return float(self.precio_gc_20_var.get() or "0")
        except ValueError:
            return 0
        
        return 0
    
    def aplicar_configuracion_inicial(self):
        """Aplica la configuracion inicial al cargar"""
        config = self.app.config_manager.config
        
        if config["interfaz"]["recordar_config"]:
            valores = config["valores_defecto"]
            
            self.ganancia_var.set(valores["ganancia"])
            self.galvanizado_var.set(valores["galvanizado"])
            
            self.precio_go_12_var.set(str(valores["precios_go"]["1.2"]))
            self.precio_go_15_var.set(str(valores["precios_go"]["1.5"]))
            self.precio_go_20_var.set(str(valores["precios_go"]["2.0"]))
            
            self.precio_gc_12_var.set(str(valores["precios_gc"]["1.2"]))
            self.precio_gc_15_var.set(str(valores["precios_gc"]["1.5"]))
            self.precio_gc_20_var.set(str(valores["precios_gc"]["2.0"]))
            
            self.dolar_var.set(str(valores["dolar"]))
            
            self.recordar_medidas_var.set(config["interfaz"]["recordar_medidas"])
            
            self.on_galvanizado_change()
    
    def seleccionar_producto(self, codigo):
        """Selecciona un producto por codigo"""
        try:
            self.producto_var.set(codigo)
            self.on_producto_change()
            self.app.root.after(100, self.enfocar_primer_campo_medidas)
        except:
            pass
    
    def enfocar_primer_campo_medidas(self):
        """Enfoca el primer campo de medidas"""
        try:
            for widget in self.medidas_frame.winfo_children():
                if isinstance(widget, ttk.Entry):
                    widget.focus_set()
                    break
        except:
            pass
    
    def manejar_tab_en_medidas(self, event):
        """Maneja Tab en campos de medidas - si es el último campo, ir a cantidad"""
        try:
            widget_actual = event.widget
            entries = [w for w in self.medidas_frame.winfo_children() if isinstance(w, ttk.Entry)]
            
            # Si es el último Entry, ir a cantidad
            if entries and widget_actual == entries[-1]:
                self.enfocar_cantidad()
                return "break"  # Prevenir comportamiento normal de Tab
        except:
            pass
    
    def enfocar_cantidad(self):
        """Enfoca el campo de cantidad y configura regreso a medidas"""
        try:
            self.cantidad_entry.focus_set()
            self.cantidad_entry.select_range(0, 'end')  # Seleccionar todo el texto
            
            # Configurar Tab y Enter para regresar a medidas
            self.cantidad_entry.bind("<Tab>", lambda e: self.regresar_a_medidas())
            self.cantidad_entry.bind("<Return>", lambda e: self.regresar_a_medidas())
        except:
            pass
    
    def regresar_a_medidas(self):
        """Regresa el foco al primer campo de medidas"""
        try:
            self.enfocar_primer_campo_medidas()
            return "break"  # Prevenir comportamiento normal
        except:
            pass        

    
    def limpiar_campos(self):
        """Limpia todos los campos de entrada"""
        self.cantidad_var.set("1")
        
        for widget in self.medidas_frame.winfo_children():
            if isinstance(widget, ttk.Entry):
                widget.delete(0, 'end')
        
        self.status_label.configure(text="Campos limpiados", foreground="blue")