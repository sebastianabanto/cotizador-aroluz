# -*- coding: utf-8 -*-
"""
Interfaz de consola original (CLI). No usada por la GUI. Preservada por compatibilidad.
Para ejecutar: python -m gui.cli_console
"""
from . import logica
from .logica import (
    ProductoCotizado,
    cotizar_bandeja, cotizar_curva_horizontal, cotizar_curva_vertical,
    cotizar_tee, cotizar_cruz, cotizar_reduccion, cotizar_caja_de_pase,
)


def pedir_medidas_caja_pase(mensaje, cantidad=3):
    """Función específica para pedir medidas de caja de pase (3 dimensiones)"""
    while True:
        entrada = input(mensaje).replace("x", "X")
        if entrada.strip() == "0":
            return None
        try:
            partes = [float(x.strip()) for x in entrada.split("X") if x.strip()]
            if len(partes) == cantidad:
                return partes
            print(f"Error: Debe ingresar {cantidad} valores numéricos separados por 'X'. Ejemplo: 20X30X15")
        except ValueError:
            print("Error: Ingrese solo números. Ejemplo: 20X30X15")


def pedir_medidas(mensaje, cantidad=2):
    while True:
        entrada = input(mensaje).replace("x", "X")
        if entrada.strip() == "0":
            return None
        partes = [float(x.strip()) for x in entrada.split("X") if x.strip()]
        if len(partes) == cantidad:
            return partes
        print(f"Error: Debe ingresar {cantidad} valores numéricos separados por 'X'. Ejemplo: 400X100")


def agregar_al_carrito(tipo, descripcion, precio_unitario, peso_unitario):
    """Agrega un producto al carrito preguntando la cantidad"""
    while True:
        try:
            cantidad = int(input(f"¿Cuántas unidades de '{descripcion}'? (mínimo 1): "))
            if cantidad >= 1:
                break
            print("La cantidad debe ser al menos 1.")
        except ValueError:
            print("Ingrese un número entero válido.")

    producto = ProductoCotizado(tipo, descripcion, precio_unitario, peso_unitario,
                               logica.tipo_galvanizado, logica.porcentaje_seleccionado, cantidad)
    logica.carrito.append(producto)
    print(f"✓ Agregado al carrito: {descripcion} (x{cantidad})")
    print("=" * 80)


def mostrar_carrito():
    """Muestra el contenido actual del carrito en formato tabla"""
    if not logica.carrito:
        print("\n🛒 El carrito está vacío")
        return

    print(f"\n🛒 CARRITO ACTUAL")
    print("=" * 120)

    # Encabezados de la tabla
    print(f"{'#':<3} {'DESCRIPCIÓN':<65} {'UND':<8} {'CANT':<6} {'TOTAL':<10} {'PESO(kg)':<10}")
    print("=" * 120)

    total_precio = 0
    total_peso = 0

    for i, producto in enumerate(logica.carrito, 1):
        print(f"{i:<3} {producto.descripcion:<65} ${producto.precio_unitario:<7.2f} {producto.cantidad:<6} ${producto.precio_total:<9.2f} {producto.peso_total:<10.2f}")
        total_precio += producto.precio_total
        total_peso += producto.peso_total

    print("=" * 120)
    print(f"{'TOTALES GENERALES:':<75} ${total_precio:<9.2f} {total_peso:<10.2f}")
    print("=" * 120)


def modificar_carrito():
    """Permite modificar cantidades o eliminar productos del carrito"""
    if not logica.carrito:
        print("🛒 El carrito está vacío")
        return

    while True:
        mostrar_carrito()
        print("\nOpciones:")
        print("1-N  -> Modificar cantidad del producto N")
        print("D-N  -> Eliminar producto N del carrito")
        print("0    -> Volver al menú principal")

        opcion = input("Seleccione opción: ").strip().upper()

        if opcion == "0":
            break
        elif opcion.startswith("D-"):
            try:
                indice = int(opcion[2:]) - 1
                if 0 <= indice < len(logica.carrito):
                    producto_eliminado = logica.carrito.pop(indice)
                    print(f"✓ Eliminado: {producto_eliminado.descripcion}")
                else:
                    print("Número de producto inválido.")
            except ValueError:
                print("Formato inválido. Use D-N (ejemplo: D-1)")
        elif "-" not in opcion:
            try:
                indice = int(opcion) - 1
                if 0 <= indice < len(logica.carrito):
                    nueva_cantidad = int(input(f"Nueva cantidad para '{logica.carrito[indice].descripcion}': "))
                    if nueva_cantidad >= 1:
                        logica.carrito[indice].cantidad = nueva_cantidad
                        print(f"✓ Cantidad actualizada")
                    else:
                        print("La cantidad debe ser al menos 1.")
                else:
                    print("Número de producto inválido.")
            except ValueError:
                print("Ingrese un número válido.")
        else:
            print("Opción no válida.")


def generar_reporte_final():
    """Genera el reporte final para exportar a Excel"""
    if not logica.carrito:
        print("🛒 El carrito está vacío. No hay nada que reportar.")
        return

    print(f"\n📋 REPORTE FINAL DE COTIZACIÓN")

    # Mostrar configuraciones usadas
    tipos_galv = set(p.tipo_galvanizado for p in logica.carrito)
    print(f"Tipos de galvanizado: {', '.join(tipos_galv)}")
    if any(p.tipo_galvanizado == "GC" for p in logica.carrito):
        print(f"Precio dólar: {logica.dolar} | Precio galvanizado: {logica.precio_galvanizado_kg} USD/kg")

    print("=" * 120)

    # Tabla de productos
    print(f"{'#':<3} {'DESCRIPCIÓN':<65} {'UND':<8} {'CANT':<6} {'TOTAL':<10} {'PESO(kg)':<10}")
    print("=" * 120)

    total_precio = 0
    total_peso = 0

    for i, producto in enumerate(logica.carrito, 1):
        print(f"{i:<3} {producto.descripcion:<65} ${producto.precio_unitario:<7.2f} {producto.cantidad:<6} ${producto.precio_total:<9.2f} {producto.peso_total:<10.2f}")
        total_precio += producto.precio_total
        total_peso += producto.peso_total

    print("=" * 120)
    print(f"{'TOTALES GENERALES:':<75} ${total_precio:<9.2f} {total_peso:<10.2f}")
    print("=" * 120)

    # Aquí es donde luego conectaremos con Excel
    print("\n💡 Datos listos para exportar a Excel")


def main():
    while True:  # Bucle principal
        print("Bienvenido al cotizador de productos Aroluz.")

        # Verificar si hay productos en carrito con diferente ganancia
        ganancia_carrito = None
        if logica.carrito:
            ganancia_carrito = logica.carrito[0].porcentaje_ganancia
            print(f"🛒 Carrito actual con ganancia: {ganancia_carrito}%")

        # Solicitar factor de ganancia al inicio
        while True:
            if ganancia_carrito:
                print(f"Factor actual: {ganancia_carrito}%")
                cambiar = input("¿Desea mantener el mismo factor de ganancia? (S/N): ").strip().upper()
                if cambiar == "S":
                    ganancia_input = ganancia_carrito
                    break
                else:
                    print("⚠️ Cambiar el factor de ganancia eliminará todos los productos del carrito.")
                    confirmar = input("¿Está seguro de continuar? (S/N): ").strip().upper()
                    if confirmar == "S":
                        logica.carrito.clear()
                        print("✓ Carrito vaciado")
                        ganancia_carrito = None
                    else:
                        ganancia_input = ganancia_carrito
                        break

            if not ganancia_carrito:
                ganancia_input = input("Seleccione el factor de ganancia: 30 (30%) o 35 (35%): ").strip()

            if str(ganancia_input) == "30":
                logica.factor_ganancia = 0.70
                logica.porcentaje_seleccionado = "30"
                break
            elif str(ganancia_input) == "35":
                logica.factor_ganancia = 0.65
                logica.porcentaje_seleccionado = "35"
                break
            print("Entrada no válida. Ingrese 30 o 35.")

        # Solicitar tipo de galvanizado
        while True:
            logica.tipo_galvanizado = input("Seleccione el tipo de galvanizado: GO (Galvanizado de Origen) o GC (Galvanizado en Caliente): ").strip().upper()
            if logica.tipo_galvanizado in ("GO", "GC"):
                break
            print("Entrada no válida. Ingrese GO o GC.")

        # Si es GC, solicitar precio del dólar y precio por kg
        if logica.tipo_galvanizado == "GC":
            while True:
                try:
                    logica.dolar = float(input("Ingrese el precio del dólar: "))
                    if logica.dolar > 0:
                        break
                    print("El precio del dólar debe ser mayor a 0.")
                except ValueError:
                    print("Ingrese un valor numérico válido.")

            while True:
                try:
                    logica.precio_galvanizado_kg = float(input("Ingrese el precio en dólares por kg de galvanizado: "))
                    if logica.precio_galvanizado_kg > 0:
                        break
                    print("El precio por kg debe ser mayor a 0.")
                except ValueError:
                    print("Ingrese un valor numérico válido.")

            print(f"Configuración GC: Dólar = {logica.dolar}, Precio galvanizado = {logica.precio_galvanizado_kg} USD/kg")

        print(f"Factor de ganancia seleccionado: {logica.porcentaje_seleccionado}%")
        print(f"Tipo de galvanizado seleccionado: {logica.tipo_galvanizado}")
        print("=" * 100)

        while True:  # Bucle interno para cotizar productos
            print("\n🛒 MENÚ PRINCIPAL")
            print("Productos a cotizar:")
            print("B   -> BANDEJA CON TAPA")
            print("CH  -> CURVA HORIZONTAL CON TAPA")
            print("CVE -> CURVA VERTICAL EXTERNA con tapa")
            print("CVI -> CURVA VERTICAL INTERNA con tapa")
            print("T   -> TEE con tapa")
            print("C   -> CRUZ con tapa")
            print("R   -> REDUCCION con tapa")
            print("CP  -> CAJA DE PASE")
            print("\nGestión del carrito:")
            print("V   -> Ver carrito")
            print("M   -> Modificar carrito (cantidades/eliminar)")
            print("L   -> Limpiar carrito")
            print("F   -> Generar reporte final")
            print("\nSalir:")
            print("9   -> Cambiar tipo de galvanizado")
            print("0   -> Salir del programa")

            opcion = input("Seleccione opción: ").strip().upper()

            if opcion == "0":
                if logica.carrito:
                    print("⚠️  Tiene productos en el carrito.")
                    confirmar = input("¿Está seguro de salir sin generar reporte? (S/N): ").strip().upper()
                    if confirmar != "S":
                        continue
                print("¡Gracias por usar el cotizador Aroluz!")
                return

            elif opcion == "9":
                print("Cambiando configuración de galvanizado...")
                break  # Volver al inicio para cambiar galvanizado

            elif opcion == "V":
                mostrar_carrito()

            elif opcion == "M":
                modificar_carrito()

            elif opcion == "L":
                logica.limpiar_carrito()

            elif opcion == "F":
                generar_reporte_final()

            elif opcion == "B":
                medidas = pedir_medidas("Ingrese las medidas de la bandeja en el formato anchoXalto (ejemplo: 400X100 mm). Ingrese 0 para cancelar: ")
                if medidas:
                    ancho, alto = medidas
                    preciopl = float(input("Ingrese el precio de la plancha PL: "))
                    espesor = float(input("Ingrese el espesor (mm): "))
                    resultados = cotizar_bandeja(preciopl, preciopl, espesor, espesor, ancho, alto)
                    for resultado in resultados:
                        agregar_al_carrito(resultado['tipo'], resultado['descripcion'],
                                         resultado['precio_unitario'], resultado['peso_unitario'])

            elif opcion == "CH":
                medidas = pedir_medidas("Ingrese las medidas de la curva horizontal en el formato anchoXalto (ejemplo: 400X100 mm). Ingrese 0 para cancelar: ")
                if medidas:
                    ancho, alto = medidas
                    preciopl = float(input("Ingrese el precio de la plancha PL: "))
                    espesor = float(input("Ingrese el espesor (mm): "))
                    resultados = cotizar_curva_horizontal(preciopl, preciopl, espesor, espesor, ancho, alto)
                    for resultado in resultados:
                        agregar_al_carrito(resultado['tipo'], resultado['descripcion'],
                                         resultado['precio_unitario'], resultado['peso_unitario'])

            elif opcion == "CVE":
                medidas = pedir_medidas("Ingrese las medidas de la curva vertical EXTERNA en el formato anchoXalto (ejemplo: 400X100 mm). Ingrese 0 para cancelar: ")
                if medidas:
                    ancho, alto = medidas
                    preciopl = float(input("Ingrese el precio de la plancha PL: "))
                    espesor = float(input("Ingrese el espesor (mm): "))
                    resultados = cotizar_curva_vertical(preciopl, preciopl, espesor, espesor, ancho, alto, "EXTERNA")
                    for resultado in resultados:
                        agregar_al_carrito(resultado['tipo'], resultado['descripcion'],
                                         resultado['precio_unitario'], resultado['peso_unitario'])

            elif opcion == "CVI":
                medidas = pedir_medidas("Ingrese las medidas de la curva vertical INTERNA en el formato anchoXalto (ejemplo: 400X100 mm). Ingrese 0 para cancelar: ")
                if medidas:
                    ancho, alto = medidas
                    preciopl = float(input("Ingrese el precio de la plancha PL: "))
                    espesor = float(input("Ingrese el espesor (mm): "))
                    resultados = cotizar_curva_vertical(preciopl, preciopl, espesor, espesor, ancho, alto, "INTERNA")
                    for resultado in resultados:
                        agregar_al_carrito(resultado['tipo'], resultado['descripcion'],
                                         resultado['precio_unitario'], resultado['peso_unitario'])

            elif opcion == "T":
                print("Cotización de TEE (3 salidas):")
                while True:
                    valores_tee = input("Ingrese las medidas (mayor a menor) en el formato: DERECHA X IZQUIERDA X ABAJO X ALTO (ejemplo: 600X400X300X100 mm). Ingrese 0 para cancelar: ")
                    valores_tee = valores_tee.replace("x", "X")
                    if valores_tee.strip() == "0":
                        print("Cotización de TEE cancelada.")
                        break
                    try:
                        derecha, izquierda, abajo, alto = [float(x.strip()) for x in valores_tee.split("X")]
                        preciopl = float(input("Ingrese el precio de la plancha PL: "))
                        espesor = float(input("Ingrese el espesor (mm): "))
                        resultados = cotizar_tee(preciopl, preciopl, espesor, espesor, derecha, izquierda, abajo, alto)
                        for resultado in resultados:
                            agregar_al_carrito(resultado['tipo'], resultado['descripcion'],
                                             resultado['precio_unitario'], resultado['peso_unitario'])
                        break
                    except ValueError:
                        print("Error: Debe ingresar 4 valores numéricos separados por 'X'.")
                        continue

            elif opcion == "C":
                medidas = pedir_medidas("Ingrese las medidas de la cruz en el formato anchoXalto (ejemplo: 400X100 mm). Ingrese 0 para cancelar: ")
                if medidas:
                    ancho, alto = medidas
                    preciopl = float(input("Ingrese el precio de la plancha PL: "))
                    espesor = float(input("Ingrese el espesor (mm): "))
                    resultados = cotizar_cruz(preciopl, preciopl, espesor, espesor, ancho, alto)
                    for resultado in resultados:
                        agregar_al_carrito(resultado['tipo'], resultado['descripcion'],
                                         resultado['precio_unitario'], resultado['peso_unitario'])

            elif opcion == "CP":
                medidas = pedir_medidas_caja_pase("Ingrese las medidas de la caja de pase en el formato anchoXlargoXalto (ejemplo: 20X30X15 cm). Ingrese 0 para cancelar: ", 3)
                if medidas:
                    ancho, largo, alto = medidas
                    preciopl = float(input("Ingrese el precio de la plancha PL: "))
                    espesor = float(input("Ingrese el espesor (mm): "))
                    resultados = cotizar_caja_de_pase(preciopl, preciopl, espesor, espesor, ancho, largo, alto)
                    for resultado in resultados:
                        agregar_al_carrito(resultado['tipo'], resultado['descripcion'],
                                       resultado['precio_unitario'], resultado['peso_unitario'])

            elif opcion == "R":
                print("Cotización de REDUCCION (entrada y salida):")
                while True:
                    valores_reduccion = input("Ingrese las medidas en el formato: ANCHO MAYOR X ALTO X ANCHO MENOR X ALTO (ejemplo: 400X100X300X100 mm). Ingrese 0 para cancelar: ")
                    valores_reduccion = valores_reduccion.replace("x", "X")
                    if valores_reduccion.strip() == "0":
                        print("Cotización de REDUCCION cancelada.")
                        break
                    try:
                        ancho_inicial, alto_inicial, ancho_final, alto_final = [float(x.strip()) for x in valores_reduccion.split("X")]
                    except Exception:
                        print("Error: Formato incorrecto. Ejemplo válido: 400X100X300X100")
                        continue

                    if alto_inicial != alto_final:
                        print("Error: La altura debe ser la misma para ambas medidas.")
                        continue
                    if ancho_inicial <= ancho_final:
                        print("Error: El ancho inicial debe ser mayor que el ancho final.")
                        continue

                    preciopl = float(input("Ingrese el precio de la plancha PL: "))
                    espesor = float(input("Ingrese el espesor (mm): "))
                    resultados = cotizar_reduccion(preciopl, preciopl, espesor, espesor, ancho_inicial, alto_inicial, ancho_final)
                    for resultado in resultados:
                        agregar_al_carrito(resultado['tipo'], resultado['descripcion'],
                                         resultado['precio_unitario'], resultado['peso_unitario'])
                    break

            else:
                print("❌ Opción no válida.")


if __name__ == "__main__":
    main()
