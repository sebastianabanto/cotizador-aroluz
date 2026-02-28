# -*- coding: utf-8 -*-
"""
Dialogo para agregar productos manualmente
"""
import tkinter as tk
from tkinter import ttk, messagebox
from ..logica import agregar_producto_manual  # <- DOS PUNTOS


def abrir_dialogo_agregar_manual(parent, callback_actualizar_carrito):
    """Abre ventana para agregar producto manual al carrito"""
    
    ventana = tk.Toplevel(parent)
    ventana.title("Agregar Producto Manual")
    ventana.geometry("400x300")
    ventana.resizable(False, False)
    ventana.transient(parent)
    ventana.grab_set()
    
    # Centrar ventana
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (400 // 2)
    y = (ventana.winfo_screenheight() // 2) - (300 // 2)
    ventana.geometry(f"400x300+{x}+{y}")
    
    # Frame principal
    main_frame = ttk.Frame(ventana, padding=20)
    main_frame.pack(fill="both", expand=True)
    
    # Descripcion
    ttk.Label(main_frame, text="Descripcion:").grid(row=0, column=0, sticky="w", pady=(0, 5))
    desc_var = tk.StringVar()
    desc_entry = ttk.Entry(main_frame, textvariable=desc_var, width=40)
    desc_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    desc_entry.focus()
    
    # Unidad
    ttk.Label(main_frame, text="Unidad:").grid(row=2, column=0, sticky="w", pady=(0, 5))
    unidad_var = tk.StringVar(value="UND")
    unidad_combo = ttk.Combobox(
        main_frame, 
        textvariable=unidad_var, 
        values=["UND", "ML"], 
        state="readonly", 
        width=15
    )
    unidad_combo.grid(row=3, column=0, sticky="w", pady=(0, 10))
    
    # Precio unitario
    ttk.Label(main_frame, text="Precio Unitario (S/):").grid(row=4, column=0, sticky="w", pady=(0, 5))
    precio_var = tk.StringVar()
    precio_entry = ttk.Entry(main_frame, textvariable=precio_var, width=20)
    precio_entry.grid(row=5, column=0, sticky="w", pady=(0, 10))
    
    # Peso unitario (opcional)
    ttk.Label(main_frame, text="Peso Unitario (kg) - Opcional:").grid(
        row=4, column=1, sticky="w", pady=(0, 5), padx=(20, 0)
    )
    peso_var = tk.StringVar(value="0")
    peso_entry = ttk.Entry(main_frame, textvariable=peso_var, width=15)
    peso_entry.grid(row=5, column=1, sticky="w", pady=(0, 10), padx=(20, 0))
    
    # Cantidad
    ttk.Label(main_frame, text="Cantidad:").grid(row=6, column=0, sticky="w", pady=(0, 5))
    cantidad_var = tk.StringVar(value="1")
    cantidad_entry = ttk.Entry(main_frame, textvariable=cantidad_var, width=20)
    cantidad_entry.grid(row=7, column=0, sticky="w", pady=(0, 20))
    
    # Funcion para agregar
    def agregar_producto():
        try:
            descripcion = desc_var.get().strip()
            unidad = unidad_var.get()
            precio = float(precio_var.get())
            peso = float(peso_var.get() or "0")
            cantidad = int(cantidad_var.get())
            
            if not descripcion:
                raise ValueError("La descripcion no puede estar vacia")
            if precio <= 0:
                raise ValueError("El precio debe ser mayor a 0")
            if peso < 0:
                raise ValueError("El peso no puede ser negativo")
            if cantidad < 1:
                raise ValueError("La cantidad debe ser al menos 1")
            
            agregar_producto_manual(descripcion, unidad, precio, peso, cantidad)
            callback_actualizar_carrito()
            ventana.destroy()
            messagebox.showinfo("Exito", "Producto agregado exitosamente")
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
    # Botones
    botones_frame = ttk.Frame(main_frame)
    botones_frame.grid(row=8, column=0, columnspan=2, sticky="ew")
    
    ttk.Button(botones_frame, text="Agregar", command=agregar_producto).pack(side="left", padx=(0, 10))
    ttk.Button(botones_frame, text="Cancelar", command=ventana.destroy).pack(side="left")
    
    # Shortcuts
    ventana.bind("<Return>", lambda e: agregar_producto())
    ventana.bind("<Escape>", lambda e: ventana.destroy())