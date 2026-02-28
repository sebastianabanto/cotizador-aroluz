# -*- coding: utf-8 -*-
"""
Diálogo modal para agregar múltiples productos del catálogo al carrito.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from ..logica import agregar_producto_manual


class PopupMultiplesProductos:
    """Diálogo que muestra una lista de productos con checkboxes y campos de cantidad."""

    def __init__(self, parent_root, productos, label_porcentaje, callback_agregar, callback_status=None):
        """
        parent_root:      ventana raíz (self.app.root en CatalogoTab)
        productos:        lista de dicts {'descripcion', 'unidad', 'precio'}
        label_porcentaje: texto del margen ("CON COMISIÓN" / "SIN COMISIÓN")
        callback_agregar: llamado con count (int) cuando se agregan productos con éxito
        callback_status:  opcional, llamado con texto de estado
        """
        self.parent_root = parent_root
        self.productos = productos
        self.label_porcentaje = label_porcentaje
        self.callback_agregar = callback_agregar
        self.callback_status = callback_status
        self._construir()

    def _construir(self):
        dialogo = tk.Toplevel(self.parent_root)
        dialogo.title("Agregar Múltiples Productos")
        dialogo.transient(self.parent_root)
        dialogo.grab_set()

        # Dimensiones dinámicas
        ancho = 400
        altura_base = 180
        altura_por_producto = 65
        altura_maxima = 600

        altura_calculada = altura_base + (len(self.productos) * altura_por_producto)
        altura = min(altura_calculada, altura_maxima)

        # Centrar
        x = (dialogo.winfo_screenwidth() // 2) - (ancho // 2)
        y = (dialogo.winfo_screenheight() // 2) - (altura // 2)
        dialogo.geometry(f"{ancho}x{altura}+{x}+{y}")
        dialogo.resizable(False, False)

        # ==================== CONTENEDOR PRINCIPAL ====================
        main = ttk.Frame(dialogo, padding=20)
        main.pack(fill="both", expand=True)

        # ==================== TÍTULO ====================
        ttk.Label(
            main,
            text=f"Agregar {len(self.productos)} productos",
            font=("Arial", 13, "bold")
        ).pack(pady=(0, 5))

        ttk.Label(
            main,
            text=f"Margen: {self.label_porcentaje}",
            font=("Arial", 9),
            foreground="#666"
        ).pack(pady=(0, 15))

        # ==================== DECIDIR SI USAR SCROLL O NO ====================
        usar_scroll = len(self.productos) > 7  # Usar scroll solo si hay más de 7 productos

        if usar_scroll:
            # ==================== CON SCROLL (muchos productos) ====================
            scroll_container = ttk.Frame(main)
            scroll_container.pack(fill="both", expand=True, pady=(0, 15))

            # Canvas con altura fija para que el scroll funcione
            canvas = tk.Canvas(scroll_container, highlightthickness=0, height=350)
            scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)

            # Frame interno donde van los productos
            inner_frame = ttk.Frame(canvas)

            # Configurar canvas
            canvas.configure(yscrollcommand=scrollbar.set)

            # Empaquetar PRIMERO scrollbar y canvas
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            # DESPUÉS crear la ventana en el canvas
            canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

            # Función de actualización MEJORADA
            def update_scroll(event=None):
                # Actualizar región de scroll basándose en el tamaño real del inner_frame
                inner_frame.update_idletasks()
                canvas.configure(scrollregion=(0, 0, inner_frame.winfo_reqwidth(), inner_frame.winfo_reqheight()))

                # Ajustar ancho del frame interno al canvas
                canvas_width = canvas.winfo_width()
                if canvas_width > 1:
                    canvas.itemconfig(canvas_window, width=canvas_width)

            # Bindings múltiples para asegurar actualización
            inner_frame.bind("<Configure>", update_scroll)
            canvas.bind("<Configure>", update_scroll)

            productos_frame = inner_frame
        else:
            # ==================== SIN SCROLL (pocos productos) ====================
            productos_frame = ttk.Frame(main)
            productos_frame.pack(fill="both", expand=True, pady=(0, 15))

        # ==================== LISTA DE PRODUCTOS ====================
        entries = []

        for i, prod in enumerate(self.productos):
            # Frame por producto
            item_frame = ttk.Frame(productos_frame)
            item_frame.pack(fill="x", padx=5, pady=3)

            # Primera fila: Checkbox + Descripción
            row1 = ttk.Frame(item_frame)
            row1.pack(fill="x")

            check_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(row1, variable=check_var).pack(side="left", padx=(0, 8))

            desc = prod['descripcion']
            if len(desc) > 40:
                desc = desc[:37] + "..."

            ttk.Label(
                row1,
                text=desc,
                font=("Arial", 9)
            ).pack(side="left", fill="x", expand=True)

            # Segunda fila: Precio + Cantidad
            row2 = ttk.Frame(item_frame)
            row2.pack(fill="x", padx=(25, 0), pady=(3, 0))

            ttk.Label(
                row2,
                text=f"S/ {prod['precio']:.2f}",
                font=("Arial", 9),
                foreground="#0066cc"
            ).pack(side="left")

            ttk.Frame(row2, width=20).pack(side="left")

            ttk.Label(row2, text="Cantidad:", font=("Arial", 9)).pack(side="left", padx=(0, 5))

            cant_var = tk.StringVar(value="1")
            entry = ttk.Entry(row2, textvariable=cant_var, width=8, justify="center")
            entry.pack(side="left", padx=(0, 5))

            ttk.Label(row2, text=prod['unidad'], font=("Arial", 9)).pack(side="left")

            # Separador
            if i < len(self.productos) - 1:
                ttk.Separator(item_frame, orient="horizontal").pack(fill="x", pady=(5, 0))

            entries.append({
                'check': check_var,
                'cantidad': cant_var,
                'producto': prod,
                'entry': entry
            })

        # FORZAR ACTUALIZACIÓN DEL SCROLL después de crear todos los productos
        if usar_scroll:
            def actualizar_scroll_final():
                inner_frame.update_idletasks()
                canvas.configure(scrollregion=(0, 0, inner_frame.winfo_reqwidth(), inner_frame.winfo_reqheight()))
                canvas.itemconfig(canvas_window, width=canvas.winfo_width())

            # Ejecutar después de que todo esté renderizado
            dialogo.after(100, actualizar_scroll_final)

        # ==================== TOTALES ====================
        total_label = ttk.Label(
            main,
            text="",
            font=("Arial", 10, "bold"),
            foreground="#0066cc"
        )
        total_label.pack(pady=(0, 15))

        def actualizar_total(*args):
            total_items = 0
            total_cant = 0
            total_precio = 0.0

            for e in entries:
                if e['check'].get():
                    try:
                        cant = int(e['cantidad'].get())
                        if cant > 0:
                            total_items += 1
                            total_cant += cant
                            total_precio += e['producto']['precio'] * cant
                    except:
                        pass

            total_label.configure(
                text=f"{total_items} productos | {total_cant} unidades | S/ {total_precio:.2f}"
            )

        for e in entries:
            e['cantidad'].trace('w', actualizar_total)
            e['check'].trace('w', actualizar_total)

        actualizar_total()

        # ==================== BOTONES ====================
        def agregar_todo():
            count = 0
            for e in entries:
                if e['check'].get():
                    try:
                        cant = int(e['cantidad'].get())
                        if cant > 0:
                            p = e['producto']
                            agregar_producto_manual(p['descripcion'], p['unidad'], p['precio'], 0, cant)
                            count += 1
                    except:
                        pass

            if count > 0:
                dialogo.destroy()
                self.callback_agregar(count)
            else:
                messagebox.showwarning("Advertencia", "No hay productos válidos para agregar")

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x")

        ttk.Button(
            btn_frame,
            text="➕ Agregar al Carrito",
            command=agregar_todo,
            style="Accent.TButton"
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="Cancelar",
            command=dialogo.destroy
        ).pack(side="right", fill="x", expand=True, padx=(5, 0))

        # ==================== SHORTCUTS ====================
        dialogo.bind("<Return>", lambda e: agregar_todo())
        dialogo.bind("<Escape>", lambda e: dialogo.destroy())

        # Foco en primer campo
        if entries:
            entries[0]['entry'].focus()
            entries[0]['entry'].select_range(0, 'end')
