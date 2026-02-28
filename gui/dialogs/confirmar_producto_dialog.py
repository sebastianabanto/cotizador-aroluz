# -*- coding: utf-8 -*-
"""
Dialogo para confirmar/editar producto antes de agregarlo al carrito desde cotización
"""
import tkinter as tk
from tkinter import ttk, messagebox


def abrir_dialogo_confirmar_producto(parent, producto_data, callback_agregar):
    """
    Abre diálogo para confirmar/editar producto antes de agregarlo al carrito
    
    Args:
        parent: Ventana padre
        producto_data: Dict con {
            'tipo': str,
            'descripcion': str,
            'precio_unitario': float,
            'peso_unitario': float,
            'cantidad': int/float,
            'unidad': str  # "UND" o "ML"
        }
        callback_agregar: Función a llamar si se confirma (recibe producto_data modificado)
    """
    
    ventana = tk.Toplevel(parent)
    ventana.title("Confirmar Producto")
    ventana.geometry("500x420")
    ventana.resizable(False, False)
    ventana.transient(parent)
    ventana.grab_set()
    
    # Centrar ventana
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - 250
    y = (ventana.winfo_screenheight() // 2) - 210
    ventana.geometry(f"500x420+{x}+{y}")
    
    main_frame = ttk.Frame(ventana, padding=20)
    main_frame.pack(fill="both", expand=True)
    
    # Título
    ttk.Label(
        main_frame,
        text="Confirmar Producto al Carrito",
        font=("Arial", 12, "bold")
    ).pack(pady=(0, 15))
    
    # Frame de campos
    campos_frame = ttk.Frame(main_frame)
    campos_frame.pack(fill="both", expand=True)
    
    # Descripción
    ttk.Label(campos_frame, text="Descripción:", font=("Arial", 10, "bold")).grid(
        row=0, column=0, sticky="w", pady=(0, 5)
    )
    desc_var = tk.StringVar(value=producto_data['descripcion'])
    desc_entry = ttk.Entry(campos_frame, textvariable=desc_var, width=60)
    desc_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    desc_entry.focus()
    desc_entry.select_range(0, 'end')
    
    # Unidad
    ttk.Label(campos_frame, text="Unidad:").grid(row=2, column=0, sticky="w", pady=(0, 5))
    unidad_var = tk.StringVar(value=producto_data['unidad'])
    unidad_combo = ttk.Combobox(
        campos_frame,
        textvariable=unidad_var,
        values=["UND", "ML"],
        state="readonly",
        width=15
    )
    unidad_combo.grid(row=3, column=0, sticky="w", pady=(0, 10))
    
    # Precio Unitario y Peso Unitario (en la misma fila)
    ttk.Label(campos_frame, text="Precio Unitario (S/):").grid(
        row=4, column=0, sticky="w", pady=(0, 5)
    )
    precio_var = tk.StringVar(value=f"{producto_data['precio_unitario']:.2f}")
    precio_entry = ttk.Entry(campos_frame, textvariable=precio_var, width=20)
    precio_entry.grid(row=5, column=0, sticky="w", pady=(0, 10))
    
    ttk.Label(campos_frame, text="Peso Unitario (kg):").grid(
        row=4, column=1, sticky="w", pady=(0, 5), padx=(20, 0)
    )
    peso_var = tk.StringVar(value=f"{producto_data['peso_unitario']:.2f}")
    peso_entry = ttk.Entry(campos_frame, textvariable=peso_var, width=20)
    peso_entry.grid(row=5, column=1, sticky="w", pady=(0, 10), padx=(20, 0))
    
    # Cantidad
    ttk.Label(campos_frame, text="Cantidad:").grid(row=6, column=0, sticky="w", pady=(0, 5))
    cantidad_var = tk.StringVar(value=str(producto_data['cantidad']))
    cantidad_entry = ttk.Entry(campos_frame, textvariable=cantidad_var, width=20)
    cantidad_entry.grid(row=7, column=0, sticky="w", pady=(0, 15))
    
    # Total calculado
    total_frame = ttk.Frame(campos_frame)
    total_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    
    total_precio_var = tk.StringVar(value="Total: S/ 0.00")
    total_peso_var = tk.StringVar(value="Peso Total: 0.00 kg")
    
    ttk.Label(
        total_frame,
        textvariable=total_precio_var,
        font=("Arial", 11, "bold"),
        foreground="#0078d4"
    ).pack(side="left", padx=(0, 20))
    
    ttk.Label(
        total_frame,
        textvariable=total_peso_var,
        font=("Arial", 11, "bold"),
        foreground="#666"
    ).pack(side="left")
    
    def actualizar_totales(*args):
        """Actualiza los totales cuando cambian precio, peso o cantidad"""
        try:
            precio = float(precio_var.get())
            peso = float(peso_var.get())
            cantidad = float(cantidad_var.get())
            
            total_precio = precio * cantidad
            total_peso = peso * cantidad
            
            total_precio_var.set(f"Total: S/ {total_precio:.2f}")
            total_peso_var.set(f"Peso Total: {total_peso:.2f} kg")
        except:
            total_precio_var.set("Total: S/ ---")
            total_peso_var.set("Peso Total: --- kg")
    
    # Vincular cambios para actualizar totales
    precio_var.trace('w', actualizar_totales)
    peso_var.trace('w', actualizar_totales)
    cantidad_var.trace('w', actualizar_totales)
    
    # Calcular totales iniciales
    actualizar_totales()
    
    def agregar_producto():
        """Valida y agrega el producto al carrito"""
        try:
            descripcion = desc_var.get().strip()
            unidad = unidad_var.get()
            precio = float(precio_var.get())
            peso = float(peso_var.get())
            cantidad_str = cantidad_var.get()
            
            # Validar unidad y cantidad
            if unidad == "ML":
                cantidad = float(cantidad_str)
            else:
                cantidad = int(cantidad_str)
            
            # Validaciones
            if not descripcion:
                raise ValueError("La descripción no puede estar vacía")
            if precio <= 0:
                raise ValueError("El precio debe ser mayor a 0")
            if peso < 0:
                raise ValueError("El peso no puede ser negativo")
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
            
            # Crear producto modificado
            producto_modificado = {
                'tipo': producto_data['tipo'],
                'descripcion': descripcion,
                'precio_unitario': precio,
                'peso_unitario': peso,
                'cantidad': cantidad,
                'unidad': unidad
            }
            
            # Llamar callback
            callback_agregar(producto_modificado)
            
            # Cerrar ventana
            ventana.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error de Validación", str(e))
    
    def cancelar():
        """Cancela y cierra el diálogo"""
        ventana.destroy()
    
    # Botones
    botones_frame = ttk.Frame(main_frame)
    botones_frame.pack(fill="x", pady=(15, 0))
    
    ttk.Button(
        botones_frame,
        text="✓ Agregar al Carrito",
        command=agregar_producto,
        style="Accent.TButton"
    ).pack(side="left", padx=(0, 10))
    
    ttk.Button(
        botones_frame,
        text="✗ Cancelar",
        command=cancelar
    ).pack(side="left")
    
    # Shortcuts
    ventana.bind("<Return>", lambda e: agregar_producto())
    ventana.bind("<Escape>", lambda e: cancelar())
    
    # Configurar grid para que se expanda
    campos_frame.grid_columnconfigure(0, weight=1)
    campos_frame.grid_columnconfigure(1, weight=1)