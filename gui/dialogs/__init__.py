# -*- coding: utf-8 -*-
"""
Dialogos modales del sistema
"""
from .ayuda_dialog import mostrar_ayuda_shortcuts
from .agregar_manual_dialog import abrir_dialogo_agregar_manual
from .modificar_cantidad_dialog import abrir_dialogo_modificar_cantidad
from .confirmar_producto_dialog import abrir_dialogo_confirmar_producto
from .popup_multiples_dialog import PopupMultiplesProductos

__all__ = [
    'mostrar_ayuda_shortcuts',
    'abrir_dialogo_agregar_manual',
    'abrir_dialogo_modificar_cantidad',
    'abrir_dialogo_confirmar_producto',
    'PopupMultiplesProductos',
]