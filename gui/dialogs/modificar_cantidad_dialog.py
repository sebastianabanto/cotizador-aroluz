# -*- coding: utf-8 -*-
"""
Dialogo para modificar cantidad de productos
"""
import tkinter as tk
from tkinter import ttk, messagebox
from ..logica import carrito, modificar_cantidad_carrito, modificar_producto_manual

def abrir_dialogo_modificar_cantidad(parent, carrito_tree, callback_actualizar):
    """Abre dialogo para editar cualquier producto del carrito"""
    
    selection = carrito_tree.selection()
    if not selection:
        messagebox.showwarning("Advertencia", "Seleccione un item para modificar")
        return
    
    # Obtener indice del item
    item_values = carrito_tree.item(selection[0])['values']
    indice = int(item_values[0]) - 1
    
    if 0 <= indice < len(carrito):
        producto = carrito[indice]
        
        # SIEMPRE mostrar el diálogo completo de edición
        ventana = tk.Toplevel(parent)
        ventana.title("Editar Producto")
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
            text="Editar Producto del Carrito",
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 15))
        
        # Frame de campos
        campos_frame = ttk.Frame(main_frame)
        campos_frame.pack(fill="both", expand=True)
        
        # Descripción
        ttk.Label(campos_frame, text="Descripción:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        desc_var = tk.StringVar(value=producto.descripcion)
        desc_entry = ttk.Entry(campos_frame, textvariable=desc_var, width=60)
        desc_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        desc_entry.focus()
        desc_entry.select_range(0, 'end')
        
        # Unidad
        ttk.Label(campos_frame, text="Unidad:").grid(row=2, column=0, sticky="w", pady=(0, 5))
        unidad_var = tk.StringVar(value=getattr(producto, 'unidad', 'UND'))
        unidad_combo = ttk.Combobox(
            campos_frame,
            textvariable=unidad_var,
            values=["UND", "ML"],
            state="readonly",
            width=15
        )
        unidad_combo.grid(row=3, column=0, sticky="w", pady=(0, 10))
        
        # Precio Unitario y Peso Unitario
        ttk.Label(campos_frame, text="Precio Unitario (S/):").grid(
            row=4, column=0, sticky="w", pady=(0, 5)
        )
        precio_var = tk.StringVar(value=f"{producto.precio_unitario:.2f}")
        precio_entry = ttk.Entry(campos_frame, textvariable=precio_var, width=20)
        precio_entry.grid(row=5, column=0, sticky="w", pady=(0, 10))
        
        ttk.Label(campos_frame, text="Peso Unitario (kg):").grid(
            row=4, column=1, sticky="w", pady=(0, 5), padx=(20, 0)
        )
        peso_var = tk.StringVar(value=f"{producto.peso_unitario:.2f}")
        peso_entry = ttk.Entry(campos_frame, textvariable=peso_var, width=20)
        peso_entry.grid(row=5, column=1, sticky="w", pady=(0, 10), padx=(20, 0))
        
        # Cantidad
        ttk.Label(campos_frame, text="Cantidad:").grid(row=6, column=0, sticky="w", pady=(0, 5))
        cantidad_var = tk.StringVar(value=str(producto.cantidad))
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
        
        def aplicar_cambio():
                    """Valida y aplica los cambios al producto"""
                    try:
                        descripcion = desc_var.get().strip()
                        unidad = unidad_var.get()
                        precio = float(precio_var.get())
                        peso = float(peso_var.get())
                        
                        # Verificar si cambió la unidad en productos tipo bandeja ANTES de validar cantidad
                        unidad_original = getattr(producto, 'unidad', 'UND')
                        if unidad != unidad_original and 'BANDEJA' in descripcion.upper():
                            # Intentar convertir automáticamente el precio
                            if unidad == "ML" and unidad_original == "UND":
                                # Convertir de UND a ML (dividir entre 2.4)
                                respuesta = messagebox.askyesno(
                                    "Conversión de Precio",
                                    f"Has cambiado de UND a ML.\n\n"
                                    f"¿Deseas ajustar automáticamente el precio?\n\n"
                                    f"Precio UND: S/ {precio:.2f}\n"
                                    f"Precio ML sugerido: S/ {precio/2.4:.2f}\n\n"
                                    f"(El precio por metro lineal se calcula dividiendo entre 2.4)"
                                )
                                if respuesta:
                                    precio = precio / 2.4
                                    peso = peso / 2.4
                                    precio_var.set(f"{precio:.2f}")
                                    peso_var.set(f"{peso:.2f}")
                            
                            elif unidad == "UND" and unidad_original == "ML":
                                # Convertir de ML a UND (multiplicar por 2.4)
                                respuesta = messagebox.askyesno(
                                    "Conversión de Precio",
                                    f"Has cambiado de ML a UND.\n\n"
                                    f"¿Deseas ajustar automáticamente el precio?\n\n"
                                    f"Precio ML: S/ {precio:.2f}\n"
                                    f"Precio UND sugerido: S/ {precio*2.4:.2f}\n\n"
                                    f"(El precio por unidad se calcula multiplicando por 2.4)"
                                )
                                if respuesta:
                                    precio = precio * 2.4
                                    peso = peso * 2.4
                                    precio_var.set(f"{precio:.2f}")
                                    peso_var.set(f"{peso:.2f}")
                        
                        # AHORA SÍ validar cantidad (después de posibles conversiones)
                        cantidad_str = cantidad_var.get().strip()
                        cantidad = float(cantidad_str)
                        
                        # Si es UND y no tiene decimales, convertir a int
                        if unidad == "UND":
                            if cantidad == int(cantidad):
                                cantidad = int(cantidad)
                        
                        # Validaciones
                        if not descripcion:
                            raise ValueError("La descripción no puede estar vacía")
                        if precio <= 0:
                            raise ValueError("El precio debe ser mayor a 0")
                        if peso < 0:
                            raise ValueError("El peso no puede ser negativo")
                        if cantidad <= 0:
                            raise ValueError("La cantidad debe ser mayor a 0")
                        
                        # Modificar el producto directamente en el carrito
                        producto.descripcion = descripcion
                        producto.unidad = unidad
                        producto.precio_unitario = precio
                        producto.peso_unitario = peso
                        producto.cantidad = cantidad
                        
                        # Actualizar vista
                        callback_actualizar()
                        ventana.destroy()
                        
                        # Mantener foco en el carrito
                        carrito_tree.focus_set()
                        if carrito_tree.get_children():
                            if not carrito_tree.selection():
                                carrito_tree.selection_set(carrito_tree.get_children()[0])
                        
                        messagebox.showinfo("Éxito", "Producto modificado exitosamente")
                        
                    except ValueError as e:
                        messagebox.showerror("Error de Validación", str(e))
                
        def cancelar():
            """Cancela y cierra el diálogo"""
            ventana.destroy()
            carrito_tree.focus_set()
        
        # Botones
        botones_frame = ttk.Frame(main_frame)
        botones_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(
            botones_frame,
            text="✓ Aplicar Cambios",
            command=aplicar_cambio,
            style="Accent.TButton"
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            botones_frame,
            text="✗ Cancelar",
            command=cancelar
        ).pack(side="left")
        
        # Shortcuts
        ventana.bind("<Return>", lambda e: aplicar_cambio())
        ventana.bind("<Escape>", lambda e: cancelar())
        
        # Configurar grid
        campos_frame.grid_columnconfigure(0, weight=1)
        campos_frame.grid_columnconfigure(1, weight=1)