# -*- coding: utf-8 -*-
"""
Gestor de shortcuts de teclado
"""

class ShortcutsManager:
    """Gestiona todos los shortcuts del sistema"""
    
    def __init__(self, app):
        self.app = app
        
    def configurar_todos(self):
        """Configura todos los shortcuts"""
        self.configurar_navegacion()
        self.configurar_acciones()
        self.configurar_productos()
        self.configurar_enter_widgets()
        
    def configurar_navegacion(self):
        """Shortcuts de navegacion entre pestanas"""
        root = self.app.root
        
        def cambiar_pestana_seguro(numero, event):
            """Cambiar solo si NO estamos haciendo click en el tree del catálogo"""
            try:
                widget = root.focus_get()
                # Si el foco está en el tree del catálogo, ignorar
                if hasattr(self.app, 'catalogo_tab') and widget == self.app.catalogo_tab.tree:
                    return "break"
            except:
                pass
            
            self.app.cambiar_pestana(numero)
            return "break"
        
        root.bind("<Control-1>", lambda e: cambiar_pestana_seguro(0, e))
        root.bind("<Control-2>", lambda e: cambiar_pestana_seguro(1, e))
        root.bind("<Control-3>", lambda e: cambiar_pestana_seguro(2, e))
        root.bind("<F1>", lambda e: self.app.cambiar_pestana(0))
        root.bind("<F2>", lambda e: self.app.cambiar_pestana(1))
        root.bind("<F3>", lambda e: self.app.cambiar_pestana(2))
        root.bind("<Escape>", lambda e: self.app.limpiar_seleccion())
        
    def configurar_acciones(self):
        """Shortcuts de acciones principales"""
        root = self.app.root
        root.bind("<Control-Return>", lambda e: self.app.cotizar_producto())
        root.bind("<Control-l>", lambda e: self.app.limpiar_campos())
        root.bind("<Control-r>", lambda e: self.app.actualizar_carrito())
        root.bind("<Control-Delete>", lambda e: self.app.eliminar_seleccionado())
        root.bind("<Control-m>", lambda e: self.app.modificar_cantidad())
        root.bind("<Control-a>", lambda e: self.app.agregar_manual())
        root.bind("<Control-d>", lambda e: self.app.abrir_gestion_datos())
        root.bind("<Control-e>", lambda e: self.app.exportar_a_excel())
        root.bind("<Control-g>", lambda e: self.app.abrir_configuracion())
        root.bind("<F12>", lambda e: self.app.mostrar_ayuda_shortcuts())
        
    def configurar_productos(self):
        """Shortcuts para seleccion de productos"""
        root = self.app.root
        root.bind("<Alt-1>", lambda e: self.app.seleccionar_producto("B"))
        root.bind("<Alt-2>", lambda e: self.app.seleccionar_producto("CH"))
        root.bind("<Alt-3>", lambda e: self.app.seleccionar_producto("CVE"))
        root.bind("<Alt-4>", lambda e: self.app.seleccionar_producto("CVI"))
        root.bind("<Alt-5>", lambda e: self.app.seleccionar_producto("T"))
        root.bind("<Alt-6>", lambda e: self.app.seleccionar_producto("C"))
        root.bind("<Alt-7>", lambda e: self.app.seleccionar_producto("R"))
        root.bind("<Alt-8>", lambda e: self.app.seleccionar_producto("CP"))
        
    def configurar_enter_widgets(self):
        """Configura Enter en botones y radiobuttons"""
        self.configurar_enter_botones()
        self.configurar_enter_radiobuttons()
    
    def configurar_enter_botones(self):
        """Enter activa botones con focus"""
        self.buscar_y_configurar_botones(self.app.root)
    
    def buscar_y_configurar_botones(self, parent):
        """Busca recursivamente botones y configura Enter"""
        from tkinter import ttk
        for child in parent.winfo_children():
            if isinstance(child, ttk.Button):
                child.bind("<Return>", lambda e, cmd=child['command']: self.ejecutar_comando(cmd))
                child.bind("<KP_Enter>", lambda e, cmd=child['command']: self.ejecutar_comando(cmd))
            if hasattr(child, 'winfo_children'):
                self.buscar_y_configurar_botones(child)
    
    def ejecutar_comando(self, comando):
        """Ejecuta comando de forma segura"""
        try:
            if comando and callable(comando):
                comando()
            elif isinstance(comando, str):
                eval(comando)
        except:
            pass
        return "break"
    
    def configurar_enter_radiobuttons(self):
        """Enter activa radiobuttons"""
        if hasattr(self.app, '_pending_radiobutton_config'):
            try:
                self.app.root.after_cancel(self.app._pending_radiobutton_config)
            except:
                pass
        
        def configurar_recursivo(parent):
            from tkinter import ttk
            for child in parent.winfo_children():
                if isinstance(child, ttk.Radiobutton):
                    child.bind("<Return>", lambda e, rb=child: self.activar_radiobutton(rb))
                    child.bind("<KP_Enter>", lambda e, rb=child: self.activar_radiobutton(rb))
                if hasattr(child, 'winfo_children'):
                    configurar_recursivo(child)
        
        self.app._pending_radiobutton_config = self.app.root.after(
            100, lambda: configurar_recursivo(self.app.root)
        )
    
    def activar_radiobutton(self, radiobutton):
        """Activa un radiobutton"""
        try:
            radiobutton.invoke()
            return "break"
        except:
            pass