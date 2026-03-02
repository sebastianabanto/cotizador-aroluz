import math

tipo_galvanizado = ""
dolar = 0
precio_galvanizado_kg = 0
factor_ganancia = 0
porcentaje_seleccionado = ""  # Para mantener el título (30 o 35)

# Sistema de carrito
carrito = []

class ProductoCotizado:
    def __init__(self, tipo, descripcion, precio_unitario, peso_unitario, tipo_galvanizado, porcentaje_ganancia, cantidad=1):
        self.tipo = tipo  # B, CH, CVE, etc.
        self.descripcion = descripcion  # Ya incluye tipo galvanizado, nombre, medidas y espesor
        self.precio_unitario = precio_unitario
        self.peso_unitario = peso_unitario
        self.tipo_galvanizado = tipo_galvanizado  # GO o GC
        self.porcentaje_ganancia = porcentaje_ganancia  # 30 o 35 (privado)
        self.cantidad = cantidad
    
    @property
    def precio_total(self):
        return self.precio_unitario * self.cantidad
    
    @property
    def peso_total(self):
        return self.peso_unitario * self.cantidad
class ProductoManual:
    """Clase para productos agregados manualmente al carrito"""
    def __init__(self, descripcion, unidad, precio_unitario, peso_unitario=0, cantidad=1):
        self.tipo = "MANUAL"
        self.descripcion = descripcion
        self.unidad = unidad  # "UND" o "ML"
        self.precio_unitario = precio_unitario
        self.peso_unitario = peso_unitario  # Ahora se puede especificar el peso
        self.tipo_galvanizado = "N/A"
        self.porcentaje_ganancia = "N/A"
        self.cantidad = cantidad
    
    @property
    def precio_total(self):
        return self.precio_unitario * self.cantidad
    
    @property
    def peso_total(self):
        return self.peso_unitario * self.cantidad

# Agregar esta función después de la función limpiar_carrito():

def agregar_producto_manual(descripcion, unidad, precio_unitario, peso_unitario, cantidad):
    """Agrega un producto manual al carrito"""
    producto = ProductoManual(descripcion, unidad, precio_unitario, peso_unitario, cantidad)
    carrito.append(producto)

def modificar_cantidad_carrito(indice, nueva_cantidad):
    """Modifica la cantidad de un producto en el carrito"""
    if 0 <= indice < len(carrito) and nueva_cantidad >= 1:
        carrito[indice].cantidad = nueva_cantidad
        return True
    return False

def eliminar_producto_carrito(indice):
    """Elimina un producto específico del carrito"""
    if 0 <= indice < len(carrito):
        del carrito[indice]
        return True
    return False

def generar_descripcion_producto(tipo_galvanizado, nombre_producto, tipo_superficie, medidas_texto, espesor):
    """Genera la descripción del producto principal con tipo de superficie"""
    if tipo_superficie == "LISA":
        tipo_texto = "TIPO LISA"
    elif tipo_superficie == "RANURADA":
        tipo_texto = "TIPO RANURADA"
    elif tipo_superficie == "ESCALERILLA":
        tipo_texto = "TIPO ESCALERILLA"
    else:
        tipo_texto = "TIPO LISA"  # Por defecto
    
    return f"{tipo_galvanizado} - {nombre_producto} {tipo_texto} {medidas_texto} {espesor:.1f}MM (C/UNION)"

def generar_descripcion_caja_pase(tipo_galvanizado, medidas_texto, tipo_salida, espesor):
    """Genera la descripción de caja de pase con tipo de salida"""
    if tipo_salida.upper() == "CIEGA":
        return f'{tipo_galvanizado} - CAJA DE PASE {medidas_texto} {tipo_salida} {espesor:.1f}MM'
    else:
        return f'{tipo_galvanizado} - CAJA DE PASE {medidas_texto} C/S {tipo_salida}" {espesor:.1f}MM'


def aplicar_precio_escalerilla(precio_base, tipo_superficie):
    """Aplica el incremento de precio para tipo escalerilla"""
    if tipo_superficie == "ESCALERILLA":
        return precio_base + 10  # +S/10 para escalerilla
    return precio_base

def configurar_sistema(ganancia_porcentaje, tipo_galv, precio_dolar=0, precio_galv_kg=0, es_caja_pase=False):
    """Configura las variables globales del sistema con soporte para cajas"""
    global tipo_galvanizado, dolar, precio_galvanizado_kg, factor_ganancia, porcentaje_seleccionado
    
    porcentaje_seleccionado = ganancia_porcentaje
    if ganancia_porcentaje == "30":
        factor_ganancia = 0.70
    elif ganancia_porcentaje == "35":
        factor_ganancia = 0.65
    
    tipo_galvanizado = tipo_galv
    dolar = precio_dolar
    
    # Usar precio específico para cajas de pase si se especifica
    if es_caja_pase and tipo_galv == "GC":
        precio_galvanizado_kg = 3.0  # Precio fijo para cajas
    else:
        precio_galvanizado_kg = precio_galv_kg

def agregar_al_carrito_gui(tipo, descripcion, precio_unitario, peso_unitario, cantidad, unidad="UND"):
    """Versión GUI de agregar al carrito"""
    producto = ProductoCotizado(tipo, descripcion, precio_unitario, peso_unitario, 
                               tipo_galvanizado, porcentaje_seleccionado, cantidad)
    producto.unidad = unidad
    carrito.append(producto)

def limpiar_carrito():
    """Vacía completamente el carrito"""
    global carrito
    carrito.clear()

def agregar_producto_manual(descripcion, unidad, precio_unitario, peso_unitario, cantidad):
    """Agrega un producto manual al carrito"""
    producto = ProductoManual(descripcion, unidad, precio_unitario, peso_unitario, cantidad)
    carrito.append(producto)

def modificar_cantidad_carrito(indice, nueva_cantidad):
    """Modifica la cantidad de un producto en el carrito"""
    if 0 <= indice < len(carrito) and nueva_cantidad >= 1:
        carrito[indice].cantidad = nueva_cantidad
        return True
    return False

def modificar_producto_manual(indice, descripcion, unidad, precio_unitario, peso_unitario, cantidad):
    """Modifica completamente un producto manual en el carrito"""
    if 0 <= indice < len(carrito) and hasattr(carrito[indice], 'tipo') and carrito[indice].tipo == "MANUAL":
        producto = carrito[indice]
        producto.descripcion = descripcion
        producto.unidad = unidad
        producto.precio_unitario = precio_unitario
        producto.peso_unitario = peso_unitario
        producto.cantidad = cantidad
        return True
    return False

def eliminar_producto_carrito(indice):
    """Elimina un producto específico del carrito"""
    if 0 <= indice < len(carrito):
        del carrito[indice]
        return True
    return False

def calcular_precio(area, pl_undmm2):
    return area * pl_undmm2

def calcular_peso(area, espesor):
    return area * 0.00000785 * espesor

def calcular_costo_galvanizado(peso):
    """Calcula el costo de galvanizado basado en peso, dólar y precio por kg"""
    if tipo_galvanizado == "GC":
        return peso * dolar * precio_galvanizado_kg
    return 0

def aplicar_costo_galvanizado(precio_base, peso):
    """Aplica el costo de galvanizado al precio base si es GC"""
    if tipo_galvanizado == "GC":
        costo_galvanizado = calcular_costo_galvanizado(peso)
        return precio_base + (costo_galvanizado / 0.95)
    return precio_base

def aplicar_ganancia(precio, factor_especifico=None):
    """Aplica el factor de ganancia al precio"""
    if factor_especifico is not None:
        return precio / factor_especifico
    return precio / factor_ganancia

def get_factor_ganancia_producto(producto):
    """Obtiene el factor de ganancia específico para cada producto según el porcentaje seleccionado"""
    factores = {
        "30": {
            "CH": 0.5,
            "CVE": 0.5,
            "CVI": 0.5,
            "T": 0.6,
            "C": 0.7,
            "R": 0.2,
            "CP": 0.5  # Para 30%: precio costo directo
        },
        "35": {
            "CH": 0.45,
            "CVE": 0.45,
            "CVI": 0.45,
            "T": 0.55,
            "C": 0.65,
            "R": 0.15,
            "CP": 0.475  # Para 35%: precio costo / 0.95
        }
    }
    
    return factores.get(porcentaje_seleccionado, {}).get(producto, factor_ganancia)

def calcular_precio_final(precio_base, peso, producto=None, precio_union=None, peso_union=None):
    """Calcula el precio final aplicando galvanizado y ganancia"""
    # Aplicar galvanizado
    precio_con_galvanizado = aplicar_costo_galvanizado(precio_base, peso)
    
    # Obtener factor específico del producto
    factor_producto = get_factor_ganancia_producto(producto) if producto else None
    
    # Aplicar ganancia
    precio_final = aplicar_ganancia(precio_con_galvanizado, factor_producto)
    
    if precio_union is not None and peso_union is not None:
        precio_union_con_galvanizado = aplicar_costo_galvanizado(precio_union, peso_union)
        precio_union_final = aplicar_ganancia(precio_union_con_galvanizado, factor_producto)
        return precio_final + precio_union_final, peso + peso_union
    
    return precio_final, peso

# FUNCIONES DE COTIZACIÓN ADAPTADAS PARA GUI

def cotizar_bandeja(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, alto):
    """Cotiza bandeja con parámetros proporcionados por la GUI"""
    pl_ancho_mm = 2400
    pl_mm2 = pl_ancho_mm * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    # Cálculos bandeja
    area = ((ancho) + (alto * 2)) * pl_ancho_mm
    precio = calcular_precio(area, pl_undmm2_producto)
    peso = calcular_peso(area, espesor_producto)
    
    # Cálculos unión
    area_union = ((ancho) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto)
    peso_union = calcular_peso(area_union, espesor_producto)
    
    # Calcular precio final
    precio_final, peso_final = calcular_precio_final(precio, peso, "B", precio_union, peso_union)
    
    descripcion_bandeja = f"{tipo_galvanizado} - BANDEJA {ancho:.0f}X{alto:.0f}X{pl_ancho_mm}MM {espesor_producto:.1f}MM (C/UNION)"
    resultados.append({
        'tipo': 'B',
        'descripcion': descripcion_bandeja,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # Cálculos tapa
    area_tapa = ((ancho) + (2.5 * 2 * 10)) * pl_ancho_mm
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa, peso_tapa, "B")
    
    descripcion_tapa = f"{tipo_galvanizado} - TAPA BANDEJA {ancho:.0f}MM {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'B',
        'descripcion': descripcion_tapa,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_curva_horizontal(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, alto):
    """Cotiza curva horizontal con parámetros proporcionados por la GUI"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    area = (ancho + 250) ** 2
    precio = calcular_precio(area, pl_undmm2_producto)
    peso = calcular_peso(area, espesor_producto)
    
    area_larguero_variable = ((ancho * 0.414 + 100) * 2 + ((ancho + 250) - (ancho * 0.414 + 100)) * math.sqrt(2)) * (alto + 15)
    precio_larguero_variable = calcular_precio(area_larguero_variable, pl_undmm2_producto)
    peso_larguero_variable = calcular_peso(area_larguero_variable, espesor_producto)
    
    area_larguero_pequeno = 412.13 * (alto + 15)
    precio_larguero_pequeno = calcular_precio(area_larguero_pequeno, pl_undmm2_producto)
    peso_larguero_pequeno = calcular_peso(area_larguero_pequeno, espesor_producto)
    
    # Peso y precio total de la curva (sin tapa)
    peso_curva = peso + peso_larguero_variable + peso_larguero_pequeno
    precio_curva = precio + precio_larguero_variable + precio_larguero_pequeno
    
    # Cálculos unión
    area_union = ((ancho) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto)
    peso_union = calcular_peso(area_union, espesor_producto)
    
    precio_final, peso_final = calcular_precio_final(precio_curva, peso_curva, "CH", precio_union, peso_union)
    
    descripcion_curva = f"{tipo_galvanizado} - CURVA HORIZONTAL {ancho:.0f}X{alto:.0f}MM {espesor_producto:.1f}MM (C/UNION)"
    resultados.append({
        'tipo': 'CH',
        'descripcion': descripcion_curva,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # Tapa
    area_tapa = ((ancho + 250) + 2) ** 2
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa, peso_tapa, "CH")
    
    descripcion_tapa = f"{tipo_galvanizado} - TAPA CURVA HORIZONTAL {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'CH',
        'descripcion': descripcion_tapa,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_curva_vertical(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, alto, tipo):
    """Cotiza curva vertical con parámetros proporcionados por la GUI"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    codigo_producto = "CVE" if tipo == "EXTERNA" else "CVI"
    
    if tipo == "EXTERNA":
        area = (ancho + 30) * 413
        area_lateral = 350 ** 2
        area_tapa = ((ancho + 40) * 577)
    else:  # INTERNA
        area = ((ancho + 40) * 577)
        area_lateral = 350 ** 2
        area_tapa = (ancho + 30) * 413
    
    precio = calcular_precio(area, pl_undmm2_producto)
    peso = calcular_peso(area, espesor_producto)
    precio_lateral = calcular_precio(area_lateral, pl_undmm2_producto) * 2
    peso_lateral = calcular_peso(area_lateral, espesor_producto) * 2
    
    # Peso y precio total de la curva (sin tapa)
    peso_curva = peso + peso_lateral
    precio_curva = precio + precio_lateral
    
    # Cálculos unión
    area_union = ((ancho) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto)
    peso_union = calcular_peso(area_union, espesor_producto)
    
    precio_final, peso_final = calcular_precio_final(precio_curva, peso_curva, codigo_producto, precio_union, peso_union)
    
    descripcion_curva = f"{tipo_galvanizado} - CURVA VERTICAL {tipo} {ancho:.0f}X{alto:.0f}MM {espesor_producto:.1f}MM (C/UNION)"
    resultados.append({
        'tipo': codigo_producto,
        'descripcion': descripcion_curva,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # Tapa
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa, peso_tapa, codigo_producto)
    
    descripcion_tapa = f"{tipo_galvanizado} - TAPA CURVA VERTICAL {tipo} {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': codigo_producto,
        'descripcion': descripcion_tapa,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_tee(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, derecha, izquierda, abajo, alto):
    """Cotiza TEE con parámetros proporcionados por la GUI"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    x_tee = (2 * 250 + abajo)
    y_tee = (derecha + alto + 250)
    area_tee = x_tee * y_tee
    precio_tee = calcular_precio(area_tee, pl_undmm2_producto)
    peso_kg_tee = calcular_peso(area_tee, espesor_producto)
    
    area_larguero_pequeno_tee = 412.13 * (alto + 15)
    precio_larguero_pequeno_tee = calcular_precio(area_larguero_pequeno_tee, pl_undmm2_producto)
    peso_kg_larguero_pequeno_tee = calcular_peso(area_larguero_pequeno_tee, espesor_producto)
    
    asdsa = ((derecha + 250) - izquierda)
    dsada = math.sqrt((150 ** 2) + (asdsa - 100) ** 2)
    area_larguero_variable_tee = (200 + dsada) * (alto + 15)
    precio_larguero_variable_tee = calcular_precio(area_larguero_variable_tee, pl_undmm2_producto)
    peso_kg_larguero_variable_tee = calcular_peso(area_larguero_variable_tee, espesor_producto)
    
    # Peso y precio total del TEE (sin tapa)
    peso_tee_total = peso_kg_tee + peso_kg_larguero_pequeno_tee + peso_kg_larguero_variable_tee
    precio_tee_total = precio_tee + precio_larguero_pequeno_tee + precio_larguero_variable_tee
    
    # Cálculos unión (2 uniones para TEE)
    area_union = ((derecha) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto) * 2
    peso_union = calcular_peso(area_union, espesor_producto) * 2
    
    precio_final, peso_final = calcular_precio_final(precio_tee_total, peso_tee_total, "T", precio_union, peso_union)
    
    descripcion_tee = f"{tipo_galvanizado} - TEE {derecha:.0f}X{izquierda:.0f}X{abajo:.0f}X{alto:.0f}MM {espesor_producto:.1f}MM (C/UNION)"
    resultados.append({
        'tipo': 'T',
        'descripcion': descripcion_tee,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # Tapa
    precio_tapa_tee = calcular_precio((2 * 250 + abajo) * (derecha + 252), pl_undmm2_tapa)
    peso_kg_tapa_tee = calcular_peso((2 * 250 + abajo) * (derecha + 252), espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa_tee, peso_kg_tapa_tee, "T")
    
    descripcion_tapa_tee = f"{tipo_galvanizado} - TAPA TEE {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'T',
        'descripcion': descripcion_tapa_tee,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_cruz(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, alto):
    """Cotiza cruz con parámetros proporcionados por la GUI"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    area = ((ancho) + 500) ** 2
    precio = calcular_precio(area, pl_undmm2_producto)
    peso = calcular_peso(area, espesor_producto)
    
    area_larguero_pequeno = 412.13 * (alto + 15)
    precio_larguero_pequeno = calcular_precio(area_larguero_pequeno, pl_undmm2_producto)
    peso_larguero_pequeno = calcular_peso(area_larguero_pequeno, espesor_producto)
    
    # Peso y precio total de la cruz (sin tapa)
    peso_cruz = peso + peso_larguero_pequeno * 4
    precio_cruz = precio + precio_larguero_pequeno * 4
    
    # Cálculos unión (3 uniones para CRUZ)
    area_union = ((ancho) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto) * 3
    peso_union = calcular_peso(area_union, espesor_producto) * 3
    
    precio_final, peso_final = calcular_precio_final(precio_cruz, peso_cruz, "C", precio_union, peso_union)
    
    descripcion_cruz = f"{tipo_galvanizado} - CRUZ {ancho:.0f}X{alto:.0f}MM {espesor_producto:.1f}MM (C/UNION)"
    resultados.append({
        'tipo': 'C',
        'descripcion': descripcion_cruz,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # Tapa
    area_tapa = ((ancho) + 500) ** 2
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa, peso_tapa, "C")
    
    descripcion_tapa_cruz = f"{tipo_galvanizado} - TAPA CRUZ {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'C',
        'descripcion': descripcion_tapa_cruz,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_reduccion(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho_mayor, alto, ancho_menor):
    """Cotiza reducción con parámetros proporcionados por la GUI"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    area_reduccion = (ancho_mayor * 413)
    precio_reduccion = calcular_precio(area_reduccion, pl_undmm2_producto)
    peso_kg_reduccion = calcular_peso(area_reduccion, espesor_producto)
    
    p_reduccion = ((ancho_mayor) - (ancho_menor)) / 2
    h_reduccion = math.sqrt((p_reduccion ** 2) + (212 ** 2))
    tot_reduccion = (200 + h_reduccion) * (alto + 12)
    precio_reduccion_larguero = calcular_precio(tot_reduccion, pl_undmm2_producto) * 2
    peso_kg_reduccion_larguero = calcular_peso(tot_reduccion, espesor_producto) * 2
    
    # Peso y precio total de la reducción (sin tapa)
    peso_reduccion_total = peso_kg_reduccion + peso_kg_reduccion_larguero
    precio_reduccion_total = precio_reduccion + precio_reduccion_larguero
    
    # Cálculos unión
    area_union = ((ancho_mayor) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto)
    peso_union = calcular_peso(area_union, espesor_producto)
    
    precio_final, peso_final = calcular_precio_final(precio_reduccion_total, peso_reduccion_total, "R", precio_union, peso_union)
    
    descripcion_reduccion = f"{tipo_galvanizado} - REDUCCION {ancho_mayor:.0f}X{alto:.0f} a {ancho_menor:.0f}X{alto:.0f}MM {espesor_producto:.1f}MM (C/UNION)"
    resultados.append({
        'tipo': 'R',
        'descripcion': descripcion_reduccion,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # Tapa
    area_tapa_reduccion = ((ancho_mayor + 4) * 413)
    precio_tapa_reduccion = calcular_precio(area_tapa_reduccion, pl_undmm2_tapa)
    peso_kg_tapa_reduccion = calcular_peso(area_tapa_reduccion, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa_reduccion, peso_kg_tapa_reduccion, "R")
    
    descripcion_tapa_reduccion = f"{tipo_galvanizado} - TAPA REDUCCION {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'R',
        'descripcion': descripcion_tapa_reduccion,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_caja_de_pase(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, largo, alto):
    """Cotiza caja de pase con parámetros proporcionados por la GUI"""
    
    # DECLARAR GLOBAL AL INICIO
    global precio_galvanizado_kg
    
    # Guardar valor original del precio galvanizado
    precio_galv_original = precio_galvanizado_kg
    
    # Establecer precio fijo de 3 USD/kg para cajas de pase
    if tipo_galvanizado == "GC":
        precio_galvanizado_kg = 3.0
    
    pl_ancho_mm = 2400
    pl_mm2 = pl_ancho_mm * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    # Conversión a mm (las medidas vienen en cm desde la GUI)
    ancho_mm = ancho * 10
    largo_mm = largo * 10
    alto_mm = alto * 10
    
    # CÁLCULOS CUERPO
    # El cuerpo es una U: pared izq + fondo + pared der, sheet width = largo
    area_cuerpo = (((alto_mm * 2) + ancho_mm) + 20) * largo_mm
    precio_cuerpo = calcular_precio(area_cuerpo, pl_undmm2_producto)
    peso_cuerpo = calcular_peso(area_cuerpo, espesor_producto)

    # CÁLCULOS CABECERA (2 unidades)
    area_cabecera = (alto_mm + 20) * (ancho_mm + 20) * 2
    precio_cabecera = calcular_precio(area_cabecera, pl_undmm2_producto)
    peso_cabecera = calcular_peso(area_cabecera, espesor_producto)

    # CÁLCULOS TAPA
    area_tapa = largo_mm * ancho_mm
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)

    # TOTALES CAJA
    precio_costo_total = precio_cuerpo + precio_cabecera + precio_tapa
    precio_venta_total = precio_costo_total * 2
    peso_total_caja = peso_cuerpo + peso_cabecera + peso_tapa

    # Aplicar galvanizado si es GC (con precio fijo 3 USD/kg)
    precio_con_galvanizado = aplicar_costo_galvanizado(precio_venta_total, peso_total_caja)

    # Aplicar ganancia según el porcentaje seleccionado
    if porcentaje_seleccionado == "30":
        precio_final = precio_con_galvanizado * 1.01
    elif porcentaje_seleccionado == "35":
        precio_final = (precio_con_galvanizado * 1.01) / 0.95
    else:
        precio_final = aplicar_ganancia(precio_con_galvanizado, None)

    descripcion_caja = f"{tipo_galvanizado} - CAJA DE PASE {ancho:.0f}X{largo:.0f}X{alto:.0f}CM {espesor_producto:.1f}MM (COMPLETA)"
    
    resultados.append({
        'tipo': 'CP',
        'descripcion': descripcion_caja,
        'precio_unitario': precio_final,
        'peso_unitario': peso_total_caja
    })
    
    # Restaurar valor original del precio galvanizado
    precio_galvanizado_kg = precio_galv_original
    
    return resultados

# CORRECCIONES EN logica.py - Todas las funciones de cotización con tapas mejoradas

def cotizar_bandeja_con_tipo(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, alto, tipo_superficie, es_metro_lineal=False):
    """Cotiza bandeja con tipo de superficie y opción metro lineal"""
    pl_ancho_mm = 2400
    pl_mm2 = pl_ancho_mm * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    # Cálculos bandeja
    area = ((ancho) + (alto * 2)) * pl_ancho_mm
    precio = calcular_precio(area, pl_undmm2_producto)
    peso = calcular_peso(area, espesor_producto)
    
    # Cálculos unión
    area_union = ((ancho) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto)
    peso_union = calcular_peso(area_union, espesor_producto)
    
    # Aplicar precio escalerilla
    precio_total = aplicar_precio_escalerilla(precio + precio_union, tipo_superficie)
    peso_final = peso + peso_union
    
    # Calcular precio final
    precio_final, peso_final = calcular_precio_final(precio_total, peso_final, "B")
    
    # Aplicar metro lineal si corresponde
    if es_metro_lineal:
        precio_final = precio_final / 2.4
        peso_final = peso_final / 2.4
    
    # Generar descripción
    medidas_texto = f"{ancho:.0f}X{alto:.0f}X{pl_ancho_mm}MM"
    descripcion_bandeja = generar_descripcion_producto(tipo_galvanizado, "BANDEJA", tipo_superficie, medidas_texto, espesor_producto)
    if es_metro_lineal:
        descripcion_bandeja += " - POR ML"
    resultados.append({
        'tipo': 'B',
        'descripcion': descripcion_bandeja,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # 🔧 TAPA MEJORADA: Incluir medidas completas del cuerpo
    area_tapa = ((ancho) + (2.5 * 2 * 10)) * pl_ancho_mm
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa, peso_tapa, "B")
    
    # Aplicar metro lineal a la tapa también
    if es_metro_lineal:
        precio_tapa_final = precio_tapa_final / 2.4
        peso_tapa_final = peso_tapa_final / 2.4
    
    # 🔧 NUEVA DESCRIPCIÓN CON MEDIDAS COMPLETAS
    descripcion_tapa = f"{tipo_galvanizado} - TAPA BANDEJA {ancho:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"
    if es_metro_lineal:
        descripcion_tapa += " - POR ML"

    resultados.append({
        'tipo': 'B',
        'descripcion': descripcion_tapa,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_curva_horizontal_con_tipo(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, alto, tipo_superficie):
    """Cotiza curva horizontal con tipo de superficie"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    area = (ancho + 250) ** 2
    precio = calcular_precio(area, pl_undmm2_producto)
    peso = calcular_peso(area, espesor_producto)
    
    area_larguero_variable = ((ancho * 0.414 + 100) * 2 + ((ancho + 250) - (ancho * 0.414 + 100)) * math.sqrt(2)) * (alto + 15)
    precio_larguero_variable = calcular_precio(area_larguero_variable, pl_undmm2_producto)
    peso_larguero_variable = calcular_peso(area_larguero_variable, espesor_producto)
    
    area_larguero_pequeno = 412.13 * (alto + 15)
    precio_larguero_pequeno = calcular_precio(area_larguero_pequeno, pl_undmm2_producto)
    peso_larguero_pequeno = calcular_peso(area_larguero_pequeno, espesor_producto)
    
    # Peso y precio total de la curva (sin tapa)
    peso_curva = peso + peso_larguero_variable + peso_larguero_pequeno
    precio_curva = precio + precio_larguero_variable + precio_larguero_pequeno
    
    # Cálculos unión
    area_union = ((ancho) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto)
    peso_union = calcular_peso(area_union, espesor_producto)
    
    # Aplicar precio escalerilla
    precio_total = aplicar_precio_escalerilla(precio_curva + precio_union, tipo_superficie)
    peso_final = peso_curva + peso_union
    
    precio_final, peso_final = calcular_precio_final(precio_total, peso_final, "CH")
    
    # Generar descripción
    medidas_texto = f"{ancho:.0f}X{alto:.0f}MM"
    descripcion_curva = generar_descripcion_producto(tipo_galvanizado, "CURVA HORIZONTAL", tipo_superficie, medidas_texto, espesor_producto)
    
    resultados.append({
        'tipo': 'CH',
        'descripcion': descripcion_curva,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # 🔧 TAPA MEJORADA: Incluir medidas del cuerpo
    area_tapa = ((ancho + 250) + 2) ** 2
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa, peso_tapa, "CH")
    
    # 🔧 NUEVA DESCRIPCIÓN CON MEDIDAS COMPLETAS
    descripcion_tapa = f"{tipo_galvanizado} - TAPA CURVA HORIZONTAL {ancho:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'CH',
        'descripcion': descripcion_tapa,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_curva_vertical_con_tipo(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, alto, tipo_curva, tipo_superficie):
    """Cotiza curva vertical con tipo de superficie"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    codigo_producto = "CVE" if tipo_curva == "EXTERNA" else "CVI"
    
    if tipo_curva == "EXTERNA":
        area = (ancho + 30) * 413
        area_lateral = 350 ** 2
        area_tapa = ((ancho + 40) * 577)
    else:  # INTERNA
        area = ((ancho + 40) * 577)
        area_lateral = 350 ** 2
        area_tapa = (ancho + 30) * 413
    
    precio = calcular_precio(area, pl_undmm2_producto)
    peso = calcular_peso(area, espesor_producto)
    precio_lateral = calcular_precio(area_lateral, pl_undmm2_producto) * 2
    peso_lateral = calcular_peso(area_lateral, espesor_producto) * 2
    
    # Peso y precio total de la curva (sin tapa)
    peso_curva = peso + peso_lateral
    precio_curva = precio + precio_lateral
    
    # Cálculos unión
    area_union = ((ancho) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto)
    peso_union = calcular_peso(area_union, espesor_producto)
    
    # Aplicar precio escalerilla
    precio_total = aplicar_precio_escalerilla(precio_curva + precio_union, tipo_superficie)
    peso_final = peso_curva + peso_union
    
    precio_final, peso_final = calcular_precio_final(precio_total, peso_final, codigo_producto)
    
    # Generar descripción
    medidas_texto = f"{ancho:.0f}X{alto:.0f}MM"
    nombre_producto = f"CURVA VERTICAL {tipo_curva}"
    descripcion_curva = generar_descripcion_producto(tipo_galvanizado, nombre_producto, tipo_superficie, medidas_texto, espesor_producto)
    
    resultados.append({
        'tipo': codigo_producto,
        'descripcion': descripcion_curva,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # 🔧 TAPA MEJORADA: Incluir medidas y tipo del cuerpo
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa, peso_tapa, codigo_producto)
    
    # 🔧 NUEVA DESCRIPCIÓN CON MEDIDAS COMPLETAS
    descripcion_tapa = f"{tipo_galvanizado} - TAPA CURVA VERTICAL {tipo_curva} {ancho:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': codigo_producto,
        'descripcion': descripcion_tapa,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_tee_con_tipo(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, derecha, izquierda, abajo, alto, tipo_superficie):
    """Cotiza TEE con tipo de superficie"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    x_tee = (2 * 250 + abajo)
    y_tee = (derecha + alto + 250)
    area_tee = x_tee * y_tee
    precio_tee = calcular_precio(area_tee, pl_undmm2_producto)
    peso_kg_tee = calcular_peso(area_tee, espesor_producto)
    
    area_larguero_pequeno_tee = 412.13 * (alto + 15)
    precio_larguero_pequeno_tee = calcular_precio(area_larguero_pequeno_tee, pl_undmm2_producto)
    peso_kg_larguero_pequeno_tee = calcular_peso(area_larguero_pequeno_tee, espesor_producto)
    
    asdsa = ((derecha + 250) - izquierda)
    dsada = math.sqrt((150 ** 2) + (asdsa - 100) ** 2)
    area_larguero_variable_tee = (200 + dsada) * (alto + 15)
    precio_larguero_variable_tee = calcular_precio(area_larguero_variable_tee, pl_undmm2_producto)
    peso_kg_larguero_variable_tee = calcular_peso(area_larguero_variable_tee, espesor_producto)
    
    # Peso y precio total del TEE (sin tapa)
    peso_tee_total = peso_kg_tee + peso_kg_larguero_pequeno_tee + peso_kg_larguero_variable_tee
    precio_tee_total = precio_tee + precio_larguero_pequeno_tee + precio_larguero_variable_tee
    
    # Cálculos unión (2 uniones para TEE)
    area_union = ((derecha) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto) * 2
    peso_union = calcular_peso(area_union, espesor_producto) * 2
    
    # Aplicar precio escalerilla
    precio_total = aplicar_precio_escalerilla(precio_tee_total + precio_union, tipo_superficie)
    peso_final = peso_tee_total + peso_union
    
    precio_final, peso_final = calcular_precio_final(precio_total, peso_final, "T")
    
    # Generar descripción
    medidas_texto = f"{derecha:.0f}X{izquierda:.0f}X{abajo:.0f}X{alto:.0f}MM"
    descripcion_tee = generar_descripcion_producto(tipo_galvanizado, "TEE", tipo_superficie, medidas_texto, espesor_producto)
    
    resultados.append({
        'tipo': 'T',
        'descripcion': descripcion_tee,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # 🔧 TAPA MEJORADA: Incluir medidas completas del TEE
    precio_tapa_tee = calcular_precio((2 * 250 + abajo) * (derecha + 252), pl_undmm2_tapa)
    peso_kg_tapa_tee = calcular_peso((2 * 250 + abajo) * (derecha + 252), espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa_tee, peso_kg_tapa_tee, "T")
    
    # 🔧 NUEVA DESCRIPCIÓN CON MEDIDAS COMPLETAS
    descripcion_tapa_tee = f"{tipo_galvanizado} - TAPA TEE {derecha:.0f}X{izquierda:.0f}X{abajo:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'T',
        'descripcion': descripcion_tapa_tee,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_cruz_con_tipo(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho, alto, tipo_superficie):
    """Cotiza cruz con tipo de superficie"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    area = ((ancho) + 500) ** 2
    precio = calcular_precio(area, pl_undmm2_producto)
    peso = calcular_peso(area, espesor_producto)
    
    area_larguero_pequeno = 412.13 * (alto + 15)
    precio_larguero_pequeno = calcular_precio(area_larguero_pequeno, pl_undmm2_producto)
    peso_larguero_pequeno = calcular_peso(area_larguero_pequeno, espesor_producto)
    
    # Peso y precio total de la cruz (sin tapa)
    peso_cruz = peso + peso_larguero_pequeno * 4
    precio_cruz = precio + precio_larguero_pequeno * 4
    
    # Cálculos unión (3 uniones para CRUZ)
    area_union = ((ancho) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto) * 3
    peso_union = calcular_peso(area_union, espesor_producto) * 3
    
    # Aplicar precio escalerilla
    precio_total = aplicar_precio_escalerilla(precio_cruz + precio_union, tipo_superficie)
    peso_final = peso_cruz + peso_union
    
    precio_final, peso_final = calcular_precio_final(precio_total, peso_final, "C")
    
    # Generar descripción
    medidas_texto = f"{ancho:.0f}X{alto:.0f}MM"
    descripcion_cruz = generar_descripcion_producto(tipo_galvanizado, "CRUZ", tipo_superficie, medidas_texto, espesor_producto)
    
    resultados.append({
        'tipo': 'C',
        'descripcion': descripcion_cruz,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # 🔧 TAPA MEJORADA: Incluir medidas del cuerpo
    area_tapa = ((ancho) + 500) ** 2
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa, peso_tapa, "C")
    
    # 🔧 NUEVA DESCRIPCIÓN CON MEDIDAS COMPLETAS
    descripcion_tapa_cruz = f"{tipo_galvanizado} - TAPA CRUZ {ancho:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'C',
        'descripcion': descripcion_tapa_cruz,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados

def cotizar_reduccion_con_tipo(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, ancho_mayor, alto, ancho_menor, tipo_superficie):
    """Cotiza reducción con tipo de superficie"""
    pl_mm2 = 2400 * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    area_reduccion = (ancho_mayor * 413)
    precio_reduccion = calcular_precio(area_reduccion, pl_undmm2_producto)
    peso_kg_reduccion = calcular_peso(area_reduccion, espesor_producto)
    
    p_reduccion = ((ancho_mayor) - (ancho_menor)) / 2
    h_reduccion = math.sqrt((p_reduccion ** 2) + (212 ** 2))
    tot_reduccion = (200 + h_reduccion) * (alto + 12)
    precio_reduccion_larguero = calcular_precio(tot_reduccion, pl_undmm2_producto) * 2
    peso_kg_reduccion_larguero = calcular_peso(tot_reduccion, espesor_producto) * 2
    
    # Peso y precio total de la reducción (sin tapa)
    peso_reduccion_total = peso_kg_reduccion + peso_kg_reduccion_larguero
    precio_reduccion_total = precio_reduccion + precio_reduccion_larguero
    
    # Cálculos unión
    area_union = ((ancho_mayor) + (alto * 2)) * 100
    precio_union = calcular_precio(area_union, pl_undmm2_producto)
    peso_union = calcular_peso(area_union, espesor_producto)
    
    # Aplicar precio escalerilla
    precio_total = aplicar_precio_escalerilla(precio_reduccion_total + precio_union, tipo_superficie)
    peso_final = precio_reduccion_total + peso_union
    
    precio_final, peso_final = calcular_precio_final(precio_total, peso_final, "R")
    
    # Generar descripción
    medidas_texto = f"{ancho_mayor:.0f}X{alto:.0f} a {ancho_menor:.0f}X{alto:.0f}MM"
    descripcion_reduccion = generar_descripcion_producto(tipo_galvanizado, "REDUCCION", tipo_superficie, medidas_texto, espesor_producto)
    
    resultados.append({
        'tipo': 'R',
        'descripcion': descripcion_reduccion,
        'precio_unitario': precio_final,
        'peso_unitario': peso_final
    })
    
    # 🔧 TAPA MEJORADA: Incluir medidas completas de la reducción
    area_tapa_reduccion = ((ancho_mayor + 4) * 413)
    precio_tapa_reduccion = calcular_precio(area_tapa_reduccion, pl_undmm2_tapa)
    peso_kg_tapa_reduccion = calcular_peso(area_tapa_reduccion, espesor_tapa)
    
    precio_tapa_final, peso_tapa_final = calcular_precio_final(precio_tapa_reduccion, peso_kg_tapa_reduccion, "R")
    
    # 🔧 NUEVA DESCRIPCIÓN CON MEDIDAS COMPLETAS
    descripcion_tapa_reduccion = f"{tipo_galvanizado} - TAPA REDUCCION {ancho_mayor:.0f}X{alto:.0f} a {ancho_menor:.0f}X{alto:.0f}MM {espesor_tapa:.1f}MM"
    resultados.append({
        'tipo': 'R',
        'descripcion': descripcion_tapa_reduccion,
        'precio_unitario': precio_tapa_final,
        'peso_unitario': peso_tapa_final
    })
    
    return resultados


def cotizar_caja_de_pase_con_tipo(precio_pl_producto, precio_pl_tapa, espesor_producto, espesor_tapa, dim1, dim2, dim3, tipo_salida):
    """
    Cotiza caja de pase con tipo de salida
    ESTANDARIZACIÓN: Ordena automáticamente las dimensiones para que:
    - ancho = dimensión mayor
    - largo = dimensión intermedia  
    - alto = dimensión menor
    """
    
    # DECLARAR GLOBAL AL INICIO
    global precio_galvanizado_kg
    
    # Guardar valor original del precio galvanizado
    precio_galv_original = precio_galvanizado_kg
    
    # Establecer precio fijo de 3 USD/kg para cajas de pase
    if tipo_galvanizado == "GC":
        precio_galvanizado_kg = 3.0
    
    # ESTANDARIZACIÓN DE MEDIDAS
    # Ordenar las dimensiones: mayor → intermedia → menor
    dimensiones = [dim1, dim2, dim3]
    dimensiones_ordenadas = sorted(dimensiones, reverse=True)
    
    ancho = dimensiones_ordenadas[0]  # Mayor
    largo = dimensiones_ordenadas[1]  # Intermedia
    alto = dimensiones_ordenadas[2]   # Menor
    
    # Mostrar la reordenación para verificación (opcional, remover en producción)
    print(f"📏 Dimensiones originales: {dim1} x {dim2} x {dim3}")
    print(f"📐 Dimensiones estandarizadas: {ancho} (ancho) x {largo} (largo) x {alto} (alto)")
    
    pl_ancho_mm = 2400
    pl_mm2 = pl_ancho_mm * 1200
    pl_undmm2_producto = precio_pl_producto / pl_mm2
    pl_undmm2_tapa = precio_pl_tapa / pl_mm2
    
    resultados = []
    
    # Conversión a mm (las medidas vienen en cm desde la GUI)
    ancho_mm = ancho * 10
    largo_mm = largo * 10
    alto_mm = alto * 10
    
    # CÁLCULOS CUERPO
    # El cuerpo es una U: pared izq + fondo + pared der, sheet width = largo
    area_cuerpo = (((alto_mm * 2) + ancho_mm) + 20) * largo_mm
    precio_cuerpo = calcular_precio(area_cuerpo, pl_undmm2_producto)
    peso_cuerpo = calcular_peso(area_cuerpo, espesor_producto)
    
    # CÁLCULOS CABECERA (2 unidades)
    # Área de las dos cabeceras (frente y atrás)
    area_cabecera = (alto_mm + 20) * (ancho_mm + 20) * 2
    precio_cabecera = calcular_precio(area_cabecera, pl_undmm2_producto)
    peso_cabecera = calcular_peso(area_cabecera, espesor_producto)
    
    # CÁLCULOS TAPA
    # La tapa siempre es ancho x largo (las dos dimensiones mayores)
    area_tapa = largo_mm * ancho_mm
    precio_tapa = calcular_precio(area_tapa, pl_undmm2_tapa)
    peso_tapa = calcular_peso(area_tapa, espesor_tapa)
    
    # TOTALES CAJA
    precio_costo_total = precio_cuerpo + precio_cabecera + precio_tapa
    precio_venta_total = precio_costo_total * 2
    peso_total_caja = peso_cuerpo + peso_cabecera + peso_tapa
    
    # Aplicar galvanizado si es GC (con precio fijo 3 USD/kg)
    precio_con_galvanizado = aplicar_costo_galvanizado(precio_venta_total, peso_total_caja)
    
    # Aplicar ganancia según el porcentaje seleccionado
    if porcentaje_seleccionado == "30":
        precio_final = precio_con_galvanizado * 1.01
    elif porcentaje_seleccionado == "35":
        precio_final = (precio_con_galvanizado * 1.01) / 0.95
    else:
        precio_final = aplicar_ganancia(precio_con_galvanizado, None)
    
    # Generar descripción con tipo de salida usando las medidas ESTANDARIZADAS EN MM
    # Convertir de CM a MM y mantener decimales si existen
    ancho_mm_desc = ancho * 10
    largo_mm_desc = largo * 10
    alto_mm_desc = alto * 10
    
    # Formatear: si es entero mostrar sin decimales, si tiene decimales mostrarlos
    def formato_medida(valor):
        if valor == int(valor):
            return f"{int(valor)}"
        else:
            return f"{valor:.1f}"
    
    medidas_texto = f"{formato_medida(ancho_mm_desc)}X{formato_medida(largo_mm_desc)}X{formato_medida(alto_mm_desc)}MM"
    descripcion_caja = generar_descripcion_caja_pase(tipo_galvanizado, medidas_texto, tipo_salida, espesor_producto)
    
    resultados.append({
        'tipo': 'CP',
        'descripcion': descripcion_caja,
        'precio_unitario': precio_final,
        'peso_unitario': peso_total_caja
    })
    
    # Restaurar valor original del precio galvanizado
    precio_galvanizado_kg = precio_galv_original
    
    return resultados

# FUNCIÓN AUXILIAR PARA VALIDACIÓN EN LA GUI
def validar_y_ordenar_dimensiones_caja(dim1, dim2, dim3):
    """
    Función auxiliar para mostrar en la GUI cómo quedarán ordenadas las dimensiones
    antes de cotizar. Útil para que el usuario vea la estandarización.
    
    Returns:
        tuple: (ancho_mayor, largo_intermedio, alto_menor, mensaje_info)
    """
    dimensiones = [dim1, dim2, dim3]
    dimensiones_ordenadas = sorted(dimensiones, reverse=True)
    
    ancho = dimensiones_ordenadas[0]  # Mayor
    largo = dimensiones_ordenadas[1]  # Intermedia  
    alto = dimensiones_ordenadas[2]   # Menor
    
    # Crear mensaje informativo
    if [dim1, dim2, dim3] == [ancho, largo, alto]:
        mensaje = f"✅ Dimensiones ya están ordenadas: {ancho} x {largo} x {alto}"
    else:
        mensaje = f"🔄 Dimensiones reordenadas: {dim1}x{dim2}x{dim3} → {ancho}x{largo}x{alto}\n"
        mensaje += f"   (Ancho: {ancho}, Largo: {largo}, Alto: {alto})"
    
    return ancho, largo, alto, mensaje

# FUNCIÓN ACTUALIZADA PARA GENERAR DESCRIPCIÓN
def generar_descripcion_caja_pase(tipo_galvanizado, medidas_texto, tipo_salida, espesor):
    """
    Genera la descripción de caja de pase con tipo de salida
    medidas_texto debe venir ya con formato: "30X20X15CM" (ancho x largo x alto)
    """
    if tipo_salida.upper() == "CIEGA":
        return f'{tipo_galvanizado} - CAJA DE PASE {medidas_texto} {tipo_salida} {espesor:.1f}MM'
    else:
        return f'{tipo_galvanizado} - CAJA DE PASE {medidas_texto} C/S {tipo_salida}" {espesor:.1f}MM'

# EJEMPLO DE USO
def ejemplo_uso():
    """Ejemplo de cómo usar la función estandarizada"""
    
    # Caso 1: Dimensiones ya ordenadas
    print("=== CASO 1: Dimensiones ya ordenadas ===")
    ancho, largo, alto, msg = validar_y_ordenar_dimensiones_caja(30, 20, 15)
    print(msg)
    
    # Caso 2: Dimensiones desordenadas  
    print("\n=== CASO 2: Dimensiones desordenadas ===")
    ancho, largo, alto, msg = validar_y_ordenar_dimensiones_caja(15, 30, 20)
    print(msg)
    
    # Caso 3: Dimensiones completamente invertidas
    print("\n=== CASO 3: Dimensiones invertidas ===")
    ancho, largo, alto, msg = validar_y_ordenar_dimensiones_caja(10, 25, 35)
    print(msg)
    
    print("\n=== EJEMPLO DE DESCRIPCIÓN GENERADA ===")
    desc = generar_descripcion_caja_pase("GO", "30X20X15CM", "3/4", 1.5)
    print(f"Descripción: {desc}")

if __name__ == "__main__":
    ejemplo_uso()