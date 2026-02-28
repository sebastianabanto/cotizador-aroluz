# -*- coding: utf-8 -*-
"""
Dialogo de ayuda con shortcuts
"""
import tkinter as tk
from tkinter import ttk, scrolledtext


def mostrar_ayuda_shortcuts(parent):
    """Muestra ventana con todos los shortcuts disponibles"""
    
    ayuda_texto = """
SHORTCUTS DISPONIBLES

Navegacion entre pestanas:
  Ctrl+1 o F1    ->  Ir a Cotizacion
  Ctrl+2 o F2    ->  Ir a Carrito
  Ctrl+3 o F3    ->  Ir a Catálogo  ← NUEVO

Acciones rapidas:
  Ctrl+Enter     ->  Cotizar y Agregar
  Ctrl+L         ->  Limpiar Campos
  Ctrl+R         ->  Actualizar Carrito
  Ctrl+D         ->  Gestion de Datos
  Ctrl+A         ->  Agregar Producto Manual
  Ctrl+M         ->  Modificar Cantidad
  Ctrl+E         ->  Exportar a Excel
  Ctrl+G         ->  Abrir Configuracion
  Escape         ->  Limpiar Seleccion
  F12            ->  Mostrar esta ayuda

Seleccion de productos (Alt + numero):
  Alt+1          ->  Bandeja
  Alt+2          ->  Curva Horizontal
  Alt+3          ->  Curva Vertical Externa
  Alt+4          ->  Curva Vertical Interna
  Alt+5          ->  TEE
  Alt+6          ->  Cruz
  Alt+7          ->  Reduccion
  Alt+8          ->  Caja de Pase

Navegacion general:
  Tab            ->  Siguiente campo
  Shift+Tab      ->  Campo anterior
  Enter          ->  Activar boton/radiobutton (cuando tiene focus)
    """
    
    ventana_ayuda = tk.Toplevel(parent)
    ventana_ayuda.title("Ayuda - Shortcuts de Teclado")
    ventana_ayuda.geometry("500x600")
    ventana_ayuda.resizable(False, False)
    ventana_ayuda.transient(parent)
    ventana_ayuda.grab_set()
    
    texto_ayuda = scrolledtext.ScrolledText(
        ventana_ayuda, 
        font=("Consolas", 10), 
        wrap=tk.WORD
    )
    texto_ayuda.pack(fill="both", expand=True, padx=20, pady=20)
    texto_ayuda.insert("1.0", ayuda_texto)
    texto_ayuda.configure(state="disabled")
    
    ttk.Button(
        ventana_ayuda, 
        text="Cerrar", 
        command=ventana_ayuda.destroy
    ).pack(pady=10)
    
    ventana_ayuda.bind("<Escape>", lambda e: ventana_ayuda.destroy())
    ventana_ayuda.focus_set()