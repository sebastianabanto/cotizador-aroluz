# -*- coding: utf-8 -*-
"""
Ventana principal del Cotizador Aroluz - Coordinador
"""
import tkinter as tk
from tkinter import ttk
from .configuracion import ConfiguracionManager  # <- AGREGAR PUNTO
from . import lector_excel                        # <- AGREGAR PUNTO

from .utils.shortcuts import ShortcutsManager
from .tabs.cotizacion_tab import CotizacionTab
from .tabs.carrito_tab import CarritoTab
from .tabs.catalogo_tab import CatalogoTab  # ← NUEVO IMPORT
from .dialogs import mostrar_ayuda_shortcuts


class CotizadorAroluz:
    """Ventana principal - Coordinador de componentes"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Cotizador Aroluz - Sistema Mejorado")
        self.config_manager = ConfiguracionManager()
        
        # Datos Excel
        self.datos_excel = {
            'razones_sociales': ['Cargando...'],
            'atenciones': ['Cargando...'],
            'monedas': ['Cargando...']
        }
        
        # Configurar ventana
        self.configurar_ventana()
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Configurar shortcuts
        self.shortcuts_manager = ShortcutsManager(self)
        self.shortcuts_manager.configurar_todos()
        
        # Forzar Ctrl+Enter para cotizar desde cualquier lugar
        def forzar_cotizar(event):
            print("🔔 Ctrl+Enter detectado!")
            
            try:
                # Cambiar a pestaña de cotización si no está activa
                if self.notebook.index(self.notebook.select()) != 0:
                    self.notebook.select(0)
                    self.root.after(100, self.cotizar_producto)
                else:
                    # Si ya estamos en cotización, enfocar primer campo de medidas
                    widget_actual = self.root.focus_get()
                    
                    # Si el foco está en un radiobutton, mover a primer Entry de medidas
                    if widget_actual and 'radiobutton' in str(widget_actual).lower():
                        print("   → Foco en radiobutton, buscando primer Entry...")
                        self.cotizacion_tab.enfocar_primer_campo_medidas()
                        # Dar tiempo para que se enfoque y luego cotizar
                        self.root.after(100, self.cotizar_producto)
                    else:
                        # Foco está bien, cotizar directamente
                        self.cotizar_producto()
                
                return "break"
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
                return "break"
        
        self.root.bind_all("<Control-Return>", forzar_cotizar)
        self.root.bind_all("<Control-KP_Enter>", forzar_cotizar)

        
        # Configuracion inicial
        self.config_manager.mostrar_validacion_inicio(self.root)
        self.cotizacion_tab.aplicar_configuracion_inicial()
        self.actualizar_datos_excel()
        
        self.root.focus_set()
    
    def configurar_ventana(self):
        """Configura tamano y posicion"""
        ancho_ventana = 750
        alto_ventana = 750
        
        ancho_pantalla = self.root.winfo_screenwidth()
        alto_pantalla = self.root.winfo_screenheight()
        
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2) - 40
        
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
    
    def crear_interfaz(self):
        """Crea la interfaz usando componentes modulares"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Crear pestanas usando componentes
        self.cotizacion_tab = CotizacionTab(self.notebook, self)
        self.carrito_tab = CarritoTab(self.notebook, self)
        self.catalogo_tab = CatalogoTab(self.notebook, self)

        self.notebook.add(self.cotizacion_tab.frame, text="Cotizacion")
        self.notebook.add(self.carrito_tab.frame, text="Carrito")
        self.notebook.add(self.catalogo_tab.frame, text="📦 Catálogo")  # ← NUEVA PESTAÑA
    
    def actualizar_datos_excel(self):
        """Actualiza datos desde Excel"""
        try:
            self.datos_excel = lector_excel.leer_todos_los_datos()
            self.carrito_tab.actualizar_combos_proyecto(self.datos_excel)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error al cargar datos:\n{str(e)}")
    
    # Metodos de navegacion (llamados por shortcuts)
    def cambiar_pestana(self, indice):
        """Cambia a la pestana especificada"""
        try:
            self.notebook.select(indice)
        except:
            pass
    
    def limpiar_seleccion(self):
        """Limpia seleccion del carrito"""
        try:
            self.carrito_tab.limpiar_seleccion()
        except:
            pass
    
    # Delegacion a pestana de cotizacion
    def seleccionar_producto(self, codigo):
        """Selecciona producto (llamado por shortcuts)"""
        self.cotizacion_tab.seleccionar_producto(codigo)
    
    def cotizar_producto(self):
        """Cotiza producto (llamado por shortcut)"""
        self.cotizacion_tab.cotizar_producto()
    
    def limpiar_campos(self):
        """Limpia campos (llamado por shortcut)"""
        self.cotizacion_tab.limpiar_campos()
    
    # Delegacion a pestana de carrito
    def actualizar_carrito(self):
        """Actualiza carrito (llamado por shortcut)"""
        self.carrito_tab.actualizar_carrito()
    
    def eliminar_seleccionado(self):
        """Elimina item seleccionado (llamado por shortcut)"""
        self.carrito_tab.eliminar_seleccionado()
    
    def modificar_cantidad(self):
        """Modifica cantidad (llamado por shortcut)"""
        self.carrito_tab.modificar_cantidad()
    
    def agregar_manual(self):
        """Abre dialogo agregar manual (llamado por shortcut)"""
        self.carrito_tab.agregar_manual()
    
    def limpiar_carrito_gui(self):
        """Limpia todo el carrito (llamado por boton)"""
        self.carrito_tab.limpiar_carrito_gui()
    
    def exportar_a_excel(self):
        """Exporta a Excel (llamado por shortcut)"""
        self.carrito_tab.exportar_a_excel()
    
    # Otros metodos
    def mostrar_ayuda_shortcuts(self):
        """Muestra ayuda de shortcuts"""
        mostrar_ayuda_shortcuts(self.root)
    
    def abrir_configuracion(self):
        """Abre configuracion"""
        self.config_manager.abrir_ventana_configuracion(self.root)
    
    def abrir_gestion_datos(self):
        """Abre gestion de datos"""
        from .gestion_ventanas import abrir_gestion_datos
        try:
            abrir_gestion_datos(self.root)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error:\n{str(e)}")


def main():
    """Punto de entrada principal"""
    root = tk.Tk()
    app = CotizadorAroluz(root)
    
    # Configurar estilos
    style = ttk.Style()
    try:
        style.theme_use('clam')
        style.configure("Accent.TButton", foreground="white", background="#0078d4")
        style.configure("Background.TFrame", background="#f0f0f0")
        root.configure(bg="#f0f0f0")
    except:
        pass
    
    root.mainloop()


if __name__ == "__main__":
    main()