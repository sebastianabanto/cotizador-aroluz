# configuracion.py
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
from pathlib import Path
import sys

class ConfiguracionManager:
    def __init__(self):
        self.archivo_config = "cotizador_config.json"
        self.archivo_backup = "cotizador_config_backup.json"
        self.carpeta_plantillas = "plantillas"
        self.plantilla_excel = "COTIZACIÓN v1.2     12-07-2023.xlsm"
        
        # Configuración por defecto
        self.config_defecto = {
            "rutas": {
                "carpeta_excel": "",
                "carpeta_pdfs": ""
            },
            "valores_defecto": {
                "ganancia": "30",
                "galvanizado": "GO",
                "precios_go": {"1.2": 150.0, "1.5": 180.0, "2.0": 220.0},
                "precios_gc": {"1.2": 140.0, "1.5": 170.0, "2.0": 210.0},
                "dolar": 3.8,
                "usd_kg_productos": 1.0,
                "usd_kg_cajas": 3.0
            },
            "interfaz": {
                "recordar_config": True,
                "recordar_medidas": True,
                "mostrar_validaciones": True
            }
        }
        
        self.config = self.cargar_configuracion()
        self.extraer_plantilla()
    
    def cargar_configuracion(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            if os.path.exists(self.archivo_config):
                with open(self.archivo_config, 'r', encoding='utf-8') as f:
                    config_cargada = json.load(f)
                    # Fusionar con configuración por defecto para asegurar todas las claves
                    return self.fusionar_config(self.config_defecto, config_cargada)
            else:
                return self.config_defecto.copy()
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            return self.config_defecto.copy()
    
    def fusionar_config(self, defecto, cargada):
        """Fusiona configuración cargada con la por defecto"""
        resultado = defecto.copy()
        for seccion, valores in cargada.items():
            if seccion in resultado:
                if isinstance(valores, dict):
                    resultado[seccion].update(valores)
                else:
                    resultado[seccion] = valores
        return resultado
    
    def guardar_configuracion(self):
        """Guarda la configuración actual"""
        try:
            # Crear backup antes de guardar
            if os.path.exists(self.archivo_config):
                shutil.copy2(self.archivo_config, self.archivo_backup)
            
            with open(self.archivo_config, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            return False
    
    def extraer_plantilla(self):
        """Extrae la plantilla Excel embebida a la carpeta de plantillas si no existe"""
        try:
            # Determinar ruta base según si es ejecutable o script
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            ruta_origen = os.path.join(base_path, self.plantilla_excel)

            # Crear carpeta de plantillas si no existe
            if not os.path.exists(self.carpeta_plantillas):
                os.makedirs(self.carpeta_plantillas)

            ruta_destino = os.path.join(self.carpeta_plantillas, self.plantilla_excel)

            # Si la plantilla no existe en destino, copiarla desde origen
            if not os.path.exists(ruta_destino):
                if os.path.exists(ruta_origen):
                    shutil.copy2(ruta_origen, ruta_destino)
                    print(f"✅ Plantilla extraída a: {ruta_destino}")
                else:
                    print("⚠️ Plantilla no encontrada en recursos")
            else:
                print("ℹ️ La plantilla ya existe, no se sobrescribió.")

        except Exception as e:
            print(f"❌ Error extrayendo plantilla: {e}")

    
    def get_ruta_plantilla(self):
        """Obtiene la ruta completa de la plantilla Excel"""
        return os.path.join(self.carpeta_plantillas, self.plantilla_excel)
    
    def validar_configuracion(self):
        """Valida que las carpetas configuradas existan"""
        errores = []
        
        # Validar carpeta Excel
        if self.config["rutas"]["carpeta_excel"]:
            if not os.path.exists(self.config["rutas"]["carpeta_excel"]):
                errores.append(f"❌ Carpeta Excel no existe: {self.config['rutas']['carpeta_excel']}")
        else:
            errores.append("❌ Carpeta Excel no configurada")
        
        # Validar carpeta PDFs
        if self.config["rutas"]["carpeta_pdfs"]:
            if not os.path.exists(self.config["rutas"]["carpeta_pdfs"]):
                errores.append(f"❌ Carpeta PDFs no existe: {self.config['rutas']['carpeta_pdfs']}")
        else:
            errores.append("❌ Carpeta PDFs no configurada")
        
        # Validar plantilla
        if not os.path.exists(self.get_ruta_plantilla()):
            errores.append(f"❌ Plantilla Excel no encontrada: {self.get_ruta_plantilla()}")
        
        return errores
    
    def mostrar_validacion_inicio(self, parent):
        """Muestra popup de validación al inicio si hay errores"""
        errores = self.validar_configuracion()
        
        if errores and self.config["interfaz"]["mostrar_validaciones"]:
            mensaje = "Se encontraron los siguientes problemas de configuración:\n\n"
            mensaje += "\n".join(errores)
            mensaje += "\n\n¿Desea abrir la configuración para corregirlos?"
            
            respuesta = messagebox.askyesno(
                "Problemas de Configuración",
                mensaje,
                icon="warning"
            )
            
            if respuesta:
                self.abrir_ventana_configuracion(parent)
                return False  # Indica que hubo problemas
        
        return len(errores) == 0  # True si no hay errores
    
    def abrir_ventana_configuracion(self, parent):
        """Abre la ventana de configuración"""
        VentanaConfiguracion(parent, self)
    
    def exportar_configuracion(self):
        """Exporta configuración a archivo .config"""
        archivo = filedialog.asksaveasfilename(
            title="Exportar Configuración",
            defaultextension=".config",
            filetypes=[("Archivos de configuración", "*.config"), ("Todos los archivos", "*.*")]
        )
        
        if archivo:
            try:
                with open(archivo, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Éxito", f"Configuración exportada a:\n{archivo}")
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Error exportando configuración:\n{e}")
                return False
    
    def importar_configuracion(self):
        """Importa configuración desde archivo .config"""
        archivo = filedialog.askopenfilename(
            title="Importar Configuración",
            filetypes=[("Archivos de configuración", "*.config"), ("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
        )
        
        if archivo:
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    config_importada = json.load(f)
                
                # Validar estructura básica
                if "rutas" in config_importada and "valores_defecto" in config_importada:
                    self.config = self.fusionar_config(self.config_defecto, config_importada)
                    self.guardar_configuracion()
                    messagebox.showinfo("Éxito", "Configuración importada correctamente")
                    return True
                else:
                    messagebox.showerror("Error", "El archivo no tiene el formato correcto")
                    return False
            except Exception as e:
                messagebox.showerror("Error", f"Error importando configuración:\n{e}")
                return False
    
    def restablecer_configuracion(self):
        """Restablece configuración a valores por defecto"""
        if messagebox.askyesno("Confirmar", "¿Está seguro de restablecer toda la configuración a valores por defecto?"):
            self.config = self.config_defecto.copy()
            self.guardar_configuracion()
            messagebox.showinfo("Éxito", "Configuración restablecida a valores por defecto")
            return True
        return False


class VentanaConfiguracion:
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.config_temporal = config_manager.config.copy()
        
        self.crear_ventana()
    
    def crear_ventana(self):
        """Crea la ventana de configuración"""
        self.ventana = tk.Toplevel(self.parent)
        self.ventana.title("⚙️ Configuración del Cotizador")
        self.ventana.geometry("600x500")
        self.ventana.resizable(True, True)
        self.ventana.transient(self.parent)
        self.ventana.grab_set()
        
        # Centrar ventana
        self.ventana.update_idletasks()
        x = (self.ventana.winfo_screenwidth() // 2) - (300)
        y = (self.ventana.winfo_screenheight() // 2) - (250)
        self.ventana.geometry(f"600x500+{x}+{y}")
        
        # Frame principal
        main_frame = ttk.Frame(self.ventana)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Crear notebook para pestañas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(0, 20))
        
        # Crear pestañas
        self.crear_pestana_rutas()
        self.crear_pestana_valores()
        self.crear_pestana_interfaz()
        
        # Botones inferiores
        self.crear_botones(main_frame)
        
        # Shortcuts
        self.ventana.bind("<Escape>", lambda e: self.cancelar())
        self.ventana.bind("<Control-s>", lambda e: self.guardar())
    
    def crear_pestana_rutas(self):
        """Crea la pestaña de rutas"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📁 Rutas")
        
        # Frame con padding
        content_frame = ttk.Frame(frame)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Carpeta Excel
        ttk.Label(content_frame, text="📂 Carpeta de Exportación Excel:", 
                font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        excel_frame = ttk.Frame(content_frame)
        excel_frame.pack(fill="x", pady=(0, 20))
        
        self.var_carpeta_excel = tk.StringVar(value=self.config_temporal["rutas"]["carpeta_excel"])
        ttk.Entry(excel_frame, textvariable=self.var_carpeta_excel, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(excel_frame, text="📁 Explorar", 
                command=lambda: self.explorar_carpeta(self.var_carpeta_excel)).pack(side="right", padx=(10, 0))
        
        # Carpeta PDFs
        ttk.Label(content_frame, text="📂 Carpeta de Exportación PDFs:", 
                font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        pdf_frame = ttk.Frame(content_frame)
        pdf_frame.pack(fill="x", pady=(0, 20))
        
        self.var_carpeta_pdfs = tk.StringVar(value=self.config_temporal["rutas"]["carpeta_pdfs"])
        ttk.Entry(pdf_frame, textvariable=self.var_carpeta_pdfs, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(pdf_frame, text="📁 Explorar", 
                command=lambda: self.explorar_carpeta(self.var_carpeta_pdfs)).pack(side="right", padx=(10, 0))
        
        # ========== NUEVO: Plantilla Excel ==========
        ttk.Label(content_frame, text="📄 Plantilla Excel:", 
                font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        plantilla_frame = ttk.Frame(content_frame)
        plantilla_frame.pack(fill="x", pady=(0, 20))
        
        self.var_plantilla_excel = tk.StringVar(
            value=self.config_temporal["rutas"].get("plantilla_excel", self.config_manager.get_ruta_plantilla())
        )
        ttk.Entry(plantilla_frame, textvariable=self.var_plantilla_excel, width=50, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(plantilla_frame, text="📁 Examinar...", 
                command=self.seleccionar_plantilla_excel).pack(side="right", padx=(10, 0))
        # ============================================
        
        # Información de plantilla
        info_frame = ttk.LabelFrame(content_frame, text="ℹ️ Información de Plantilla", padding=10)
        info_frame.pack(fill="x", pady=(20, 0))
        
        ruta_plantilla = self.config_manager.get_ruta_plantilla()
        existe = "✅ Disponible" if os.path.exists(ruta_plantilla) else "❌ No encontrada"
        
        ttk.Label(info_frame, text=f"Plantilla Excel: {existe}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Ubicación: {ruta_plantilla}", 
                font=("Arial", 8), foreground="gray").pack(anchor="w")
    
    def crear_pestana_valores(self):
        """Crea la pestaña de valores por defecto"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⚙️ Valores por Defecto")
        
        # Scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollable components
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=20)
        scrollbar.pack(side="right", fill="y", padx=(0, 20), pady=20)
        
        content = scrollable_frame
        
        # Factor de ganancia
        ganancia_frame = ttk.LabelFrame(content, text="Factor de Ganancia", padding=10)
        ganancia_frame.pack(fill="x", pady=(0, 15))
        
        self.var_ganancia = tk.StringVar(value=self.config_temporal["valores_defecto"]["ganancia"])
        ttk.Radiobutton(ganancia_frame, text="30% (Factor 0.70)", 
                       variable=self.var_ganancia, value="30").pack(anchor="w")
        ttk.Radiobutton(ganancia_frame, text="35% (Factor 0.65)", 
                       variable=self.var_ganancia, value="35").pack(anchor="w")
        
        # Tipo de galvanizado
        galv_frame = ttk.LabelFrame(content, text="Tipo de Galvanizado por Defecto", padding=10)
        galv_frame.pack(fill="x", pady=(0, 15))
        
        self.var_galvanizado = tk.StringVar(value=self.config_temporal["valores_defecto"]["galvanizado"])
        ttk.Radiobutton(galv_frame, text="GO - Galvanizado de Origen", 
                       variable=self.var_galvanizado, value="GO").pack(anchor="w")
        ttk.Radiobutton(galv_frame, text="GC - Galvanizado en Caliente", 
                       variable=self.var_galvanizado, value="GC").pack(anchor="w")
        
        # Precios GO
        go_frame = ttk.LabelFrame(content, text="Precios GO por Defecto (S/)", padding=10)
        go_frame.pack(fill="x", pady=(0, 15))
        
        go_grid = ttk.Frame(go_frame)
        go_grid.pack(fill="x")
        
        self.var_go_12 = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["precios_go"]["1.2"]))
        self.var_go_15 = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["precios_go"]["1.5"]))
        self.var_go_20 = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["precios_go"]["2.0"]))
        
        ttk.Label(go_grid, text="PL 1.2mm:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(go_grid, textvariable=self.var_go_12, width=10).grid(row=0, column=1, padx=(0, 15))
        ttk.Label(go_grid, text="PL 1.5mm:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Entry(go_grid, textvariable=self.var_go_15, width=10).grid(row=0, column=3, padx=(0, 15))
        ttk.Label(go_grid, text="PL 2.0mm:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        ttk.Entry(go_grid, textvariable=self.var_go_20, width=10).grid(row=0, column=5)
        
        # Precios GC
        gc_frame = ttk.LabelFrame(content, text="Precios GC por Defecto (S/)", padding=10)
        gc_frame.pack(fill="x", pady=(0, 15))
        
        gc_grid = ttk.Frame(gc_frame)
        gc_grid.pack(fill="x")
        
        self.var_gc_12 = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["precios_gc"]["1.2"]))
        self.var_gc_15 = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["precios_gc"]["1.5"]))
        self.var_gc_20 = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["precios_gc"]["2.0"]))
        
        ttk.Label(gc_grid, text="PL 1.2mm:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(gc_grid, textvariable=self.var_gc_12, width=10).grid(row=0, column=1, padx=(0, 15))
        ttk.Label(gc_grid, text="PL 1.5mm:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Entry(gc_grid, textvariable=self.var_gc_15, width=10).grid(row=0, column=3, padx=(0, 15))
        ttk.Label(gc_grid, text="PL 2.0mm:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        ttk.Entry(gc_grid, textvariable=self.var_gc_20, width=10).grid(row=0, column=5)
        
        # Valores adicionales
        adicionales_frame = ttk.LabelFrame(content, text="Valores Adicionales", padding=10)
        adicionales_frame.pack(fill="x", pady=(0, 15))
        
        add_grid = ttk.Frame(adicionales_frame)
        add_grid.pack(fill="x")
        
        self.var_dolar = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["dolar"]))
        self.var_usd_productos = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["usd_kg_productos"]))
        self.var_usd_cajas = tk.StringVar(value=str(self.config_temporal["valores_defecto"]["usd_kg_cajas"]))
        
        ttk.Label(add_grid, text="Dólar (S/):").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(add_grid, textvariable=self.var_dolar, width=10).grid(row=0, column=1, padx=(0, 15))
        
        ttk.Label(add_grid, text="USD/kg Productos:").grid(row=1, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(add_grid, textvariable=self.var_usd_productos, width=10).grid(row=1, column=1, padx=(0, 15))
        
        ttk.Label(add_grid, text="USD/kg Cajas:").grid(row=1, column=2, sticky="w", padx=(0, 5))
        ttk.Entry(add_grid, textvariable=self.var_usd_cajas, width=10).grid(row=1, column=3)
    
    def crear_pestana_interfaz(self):
        """Crea la pestaña de interfaz"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🎨 Interfaz")
        
        content_frame = ttk.Frame(frame)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        opciones_frame = ttk.LabelFrame(content_frame, text="Opciones de Interfaz", padding=15)
        opciones_frame.pack(fill="x")
        
        self.var_recordar_config = tk.BooleanVar(value=self.config_temporal["interfaz"]["recordar_config"])
        self.var_recordar_medidas = tk.BooleanVar(value=self.config_temporal["interfaz"]["recordar_medidas"])
        self.var_mostrar_validaciones = tk.BooleanVar(value=self.config_temporal["interfaz"]["mostrar_validaciones"])
        
        ttk.Checkbutton(opciones_frame, text="☑️ Recordar configuración al abrir", 
                       variable=self.var_recordar_config).pack(anchor="w", pady=5)
        ttk.Checkbutton(opciones_frame, text="☑️ Recordar medidas entre productos (familia)", 
                       variable=self.var_recordar_medidas).pack(anchor="w", pady=5)
        ttk.Checkbutton(opciones_frame, text="☑️ Mostrar validaciones al inicio", 
                       variable=self.var_mostrar_validaciones).pack(anchor="w", pady=5)
    
    def crear_botones(self, parent):
        """Crea los botones de la ventana"""
        botones_frame = ttk.Frame(parent)
        botones_frame.pack(fill="x")
        
        # Botones izquierda
        ttk.Button(botones_frame, text="📤 Exportar", 
                  command=self.exportar).pack(side="left", padx=(0, 5))
        ttk.Button(botones_frame, text="📥 Importar", 
                  command=self.importar).pack(side="left", padx=5)
        ttk.Button(botones_frame, text="🔄 Restablecer", 
                  command=self.restablecer).pack(side="left", padx=5)
        
        # Botones derecha
        ttk.Button(botones_frame, text="❌ Cancelar", 
                  command=self.cancelar).pack(side="right")
        ttk.Button(botones_frame, text="💾 Guardar", 
                  command=self.guardar).pack(side="right", padx=(0, 10))
    
    def explorar_carpeta(self, var_destino):
        """Abre diálogo para seleccionar carpeta"""
        carpeta = filedialog.askdirectory(
            title="Seleccionar Carpeta",
            initialdir=var_destino.get() if var_destino.get() else os.path.expanduser("~")
        )
        if carpeta:
            var_destino.set(carpeta)
    
    def seleccionar_plantilla_excel(self):
        """Abre diálogo para seleccionar archivo de plantilla Excel"""
        # Obtener directorio inicial
        ruta_actual = self.var_plantilla_excel.get()
        directorio_inicial = ""
        
        if ruta_actual and os.path.exists(os.path.dirname(ruta_actual)):
            directorio_inicial = os.path.dirname(ruta_actual)
        elif os.path.exists("plantillas"):
            directorio_inicial = "plantillas"
        
        archivo = filedialog.askopenfilename(
            title="Seleccionar Plantilla Excel",
            filetypes=[
                ("Archivos Excel con Macros", "*.xlsm"),
                ("Archivos Excel", "*.xlsx"),
                ("Todos los archivos", "*.*")
            ],
            initialdir=directorio_inicial
        )
        
        if archivo:
            self.var_plantilla_excel.set(archivo)

    def actualizar_config_temporal(self):
        """Actualiza la configuración temporal con los valores del formulario"""
        try:
            # Rutas
            self.config_temporal["rutas"]["carpeta_excel"] = self.var_carpeta_excel.get()
            self.config_temporal["rutas"]["carpeta_pdfs"] = self.var_carpeta_pdfs.get()
            self.config_temporal["rutas"]["plantilla_excel"] = self.var_plantilla_excel.get()
            
            # Valores por defecto
            self.config_temporal["valores_defecto"]["ganancia"] = self.var_ganancia.get()
            self.config_temporal["valores_defecto"]["galvanizado"] = self.var_galvanizado.get()
            
            # Precios GO
            self.config_temporal["valores_defecto"]["precios_go"]["1.2"] = float(self.var_go_12.get())
            self.config_temporal["valores_defecto"]["precios_go"]["1.5"] = float(self.var_go_15.get())
            self.config_temporal["valores_defecto"]["precios_go"]["2.0"] = float(self.var_go_20.get())
            
            # Precios GC
            self.config_temporal["valores_defecto"]["precios_gc"]["1.2"] = float(self.var_gc_12.get())
            self.config_temporal["valores_defecto"]["precios_gc"]["1.5"] = float(self.var_gc_15.get())
            self.config_temporal["valores_defecto"]["precios_gc"]["2.0"] = float(self.var_gc_20.get())
            
            # Valores adicionales
            self.config_temporal["valores_defecto"]["dolar"] = float(self.var_dolar.get())
            self.config_temporal["valores_defecto"]["usd_kg_productos"] = float(self.var_usd_productos.get())
            self.config_temporal["valores_defecto"]["usd_kg_cajas"] = float(self.var_usd_cajas.get())
            
            # Interfaz
            self.config_temporal["interfaz"]["recordar_config"] = self.var_recordar_config.get()
            self.config_temporal["interfaz"]["recordar_medidas"] = self.var_recordar_medidas.get()
            self.config_temporal["interfaz"]["mostrar_validaciones"] = self.var_mostrar_validaciones.get()
            
            return True
        except ValueError as e:
            messagebox.showerror("Error", f"Error en los valores numéricos:\n{e}")
            return False
    
    def guardar(self):
        """Guarda la configuración"""
        if self.actualizar_config_temporal():
            self.config_manager.config = self.config_temporal.copy()
            if self.config_manager.guardar_configuracion():
                messagebox.showinfo("Éxito", "Configuración guardada correctamente")
                self.ventana.destroy()
            else:
                messagebox.showerror("Error", "Error guardando la configuración")
    
    def cancelar(self):
        """Cancela y cierra la ventana"""
        if messagebox.askyesno("Confirmar", "¿Descartar los cambios?"):
            self.ventana.destroy()
    
    def exportar(self):
        """Exporta la configuración actual"""
        if self.actualizar_config_temporal():
            # Temporalmente usar la config del formulario para exportar
            config_original = self.config_manager.config
            self.config_manager.config = self.config_temporal
            resultado = self.config_manager.exportar_configuracion()
            self.config_manager.config = config_original
            return resultado
    
    def importar(self):
        """Importa configuración desde archivo"""
        if self.config_manager.importar_configuracion():
            # Actualizar formulario con la nueva configuración
            self.config_temporal = self.config_manager.config.copy()
            self.actualizar_formulario()
    
    def restablecer(self):
        """Restablece a valores por defecto"""
        if messagebox.askyesno("Confirmar", "¿Restablecer todos los valores a su configuración por defecto?"):
            self.config_temporal = self.config_manager.config_defecto.copy()
            self.actualizar_formulario()
    
    def actualizar_formulario(self):
        """Actualiza el formulario con los valores de config_temporal"""
        # Rutas
        self.var_carpeta_excel.set(self.config_temporal["rutas"]["carpeta_excel"])
        self.var_carpeta_pdfs.set(self.config_temporal["rutas"]["carpeta_pdfs"])
        self.var_plantilla_excel.set(self.config_temporal["rutas"].get("plantilla_excel", self.config_manager.get_ruta_plantilla()))
                
        # Valores por defecto
        self.var_ganancia.set(self.config_temporal["valores_defecto"]["ganancia"])
        self.var_galvanizado.set(self.config_temporal["valores_defecto"]["galvanizado"])
        
        # Precios
        self.var_go_12.set(str(self.config_temporal["valores_defecto"]["precios_go"]["1.2"]))
        self.var_go_15.set(str(self.config_temporal["valores_defecto"]["precios_go"]["1.5"]))
        self.var_go_20.set(str(self.config_temporal["valores_defecto"]["precios_go"]["2.0"]))
        self.var_gc_12.set(str(self.config_temporal["valores_defecto"]["precios_gc"]["1.2"]))
        self.var_gc_15.set(str(self.config_temporal["valores_defecto"]["precios_gc"]["1.5"]))
        self.var_gc_20.set(str(self.config_temporal["valores_defecto"]["precios_gc"]["2.0"]))
        
        # Valores adicionales
        self.var_dolar.set(str(self.config_temporal["valores_defecto"]["dolar"]))
        self.var_usd_productos.set(str(self.config_temporal["valores_defecto"]["usd_kg_productos"]))
        self.var_usd_cajas.set(str(self.config_temporal["valores_defecto"]["usd_kg_cajas"]))
        
        # Interfaz
        self.var_recordar_config.set(self.config_temporal["interfaz"]["recordar_config"])
        self.var_recordar_medidas.set(self.config_temporal["interfaz"]["recordar_medidas"])
        self.var_mostrar_validaciones.set(self.config_temporal["interfaz"]["mostrar_validaciones"])