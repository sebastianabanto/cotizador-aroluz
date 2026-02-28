import os
import subprocess
import sys
import time

# Ruta del archivo Excel original
def obtener_ruta_plantilla():
    """Obtiene la ruta de la plantilla desde el sistema de configuración"""
    try:
        from .configuracion import ConfiguracionManager  # ← CAMBIO AQUÍ (punto antes de configuracion)
        config_manager = ConfiguracionManager()
        ruta = config_manager.get_ruta_plantilla()
        print(f"📋 Ruta de plantilla obtenida: {ruta}")
        return ruta
    except Exception as e:
        print(f"⚠️  Error obteniendo ruta de configuración: {e}")
        import os
        # Fallback: buscar en carpeta plantillas relativa
        ruta_fallback = os.path.join(
            os.path.dirname(__file__),
            "plantillas",
            "COTIZACIÓN v1.2     12-07-2023.xlsm"
        )
        print(f"📋 Usando ruta fallback: {ruta_fallback}")
        return ruta_fallback
    
RUTA_PLANTILLA = obtener_ruta_plantilla()

def verificar_rutas():
    """Verifica que exista el archivo Excel original"""
    # ACTUALIZAR LA RUTA DINÁMICAMENTE
    global RUTA_PLANTILLA
    RUTA_PLANTILLA = obtener_ruta_plantilla()
    
    if not os.path.exists(RUTA_PLANTILLA):
        raise FileNotFoundError(f"No se encontró el archivo Excel en: {RUTA_PLANTILLA}")
    return True

def exportar_carrito_a_excel(carrito, datos_proyecto=None, mostrar_mensaje_callback=None):
    """
    VERSIÓN FINAL: Método híbrido optimizado con datos del proyecto
    - Abre Excel con método nativo (conserva formato original)
    - Conecta xlwings para llenar datos del carrito
    - NUEVO: Llena los campos de proyecto en las celdas específicas
    - Mantiene toda la configuración original del Excel
    
    Args:
        carrito: Lista de productos del carrito
        datos_proyecto: Diccionario con datos del proyecto {
            'proyecto': str,
            'titulo_provisional': str,
            'razon_social': str,
            'atencion': str,
            'moneda': str
        }
        mostrar_mensaje_callback: Función para mostrar mensajes en la GUI
    
    Returns:
        tuple: (success: bool, mensaje: str)
    """
    
    try:
        # Verificar rutas
        verificar_rutas()
        
        if not carrito:
            return False, "El carrito está vacío. No hay productos para exportar."
        
        # DEBUG: Mostrar datos recibidos
        print(f"🔍 DEBUG - Datos del proyecto recibidos: {datos_proyecto}")
        
        if mostrar_mensaje_callback:
            mostrar_mensaje_callback("Abriendo Excel...")
        
        print("🚀 Iniciando exportación con método híbrido...")
        
        # PASO 1: Abrir Excel con método nativo (que conserva formato)
        print(f"📂 Abriendo Excel: {os.path.basename(RUTA_PLANTILLA)}")
        print(f"🔍 DEBUG - Abriendo archivo: {RUTA_PLANTILLA}")
        os.startfile(RUTA_PLANTILLA)
        
        print("⏳ Esperando que Excel se cargue...")
        if mostrar_mensaje_callback:
            mostrar_mensaje_callback("Esperando que Excel se cargue...")
        
        time.sleep(5)  # Tiempo para carga completa
        
        # PASO 2: Conectar xlwings a la instancia existente
        if mostrar_mensaje_callback:
            mostrar_mensaje_callback("Conectando a Excel...")
        
        print("🔗 Conectando xlwings a Excel existente...")
        
        try:
            import xlwings as xw
        except ImportError:
            return False, "❌ xlwings no está instalado.\nInstale: pip install xlwings"
        
        # Buscar el libro abierto
        nombre_archivo = os.path.basename(RUTA_PLANTILLA)
        wb = None
        
        for book in xw.books:
            if nombre_archivo in book.name:
                wb = book
                print(f"✅ Conectado a: {book.name}")
                break
        
        if wb is None:
            # Fallback: usar el último libro abierto
            if len(xw.books) > 0:
                wb = xw.books[-1]
                print(f"✅ Conectado al último libro: {wb.name}")
            else:
                return False, "❌ No se encontró Excel abierto"
        
        ws = wb.sheets.active
        
        # PASO 3: NUEVO - Llenar datos del proyecto
        if datos_proyecto:
            if mostrar_mensaje_callback:
                mostrar_mensaje_callback("Escribiendo información del proyecto...")
            
            print("📋 Escribiendo información del proyecto...")
            print(f"🔍 DEBUG - Procesando datos: {datos_proyecto}")
            
            try:
                # Mapeo de campos a celdas específicas
                mapeo_celdas = {
                    'proyecto': 'B10',
                    'titulo_provisional': 'L3',
                    'razon_social': 'M5',
                    'atencion': 'M6',
                    'moneda': 'M8'
                }
                
                campos_escritos = 0
                
                for campo, celda in mapeo_celdas.items():
                    valor = datos_proyecto.get(campo, '').strip()
                    print(f"🔍 DEBUG - Campo '{campo}': valor='{valor}', celda={celda}")
                    
                    if valor:  # Solo escribir si hay valor
                        try:
                            # MANEJO ESPECIAL PARA CELDAS COMBINADAS
                            if celda == 'B10':
                                print(f"🎯 MANEJANDO CELDA COMBINADA B10")
                                # Para celdas combinadas, usar el rango completo
                                rango_combinado = ws.range('B10').merge_area
                                if rango_combinado:
                                    print(f"🔍 Rango combinado detectado: {rango_combinado}")
                                    # Escribir en todo el rango combinado
                                    ws.range(rango_combinado).value = valor
                                else:
                                    # Si no está combinada, escribir normal
                                    ws.range(celda).value = valor
                            else:
                                # Para celdas normales
                                ws.range(celda).clear_contents()
                                ws.range(celda).value = valor
                            
                            campos_escritos += 1
                            print(f"  ✅ {campo.upper()}: '{valor}' → {celda}")
                            
                        except Exception as e:
                            print(f"  ❌ Error escribiendo en {celda}: {e}")
                            
                            # FALLBACK: Intentar con método alternativo para celdas combinadas
                            if celda == 'B10':
                                try:
                                    print(f"🔄 Intentando método alternativo para B10...")
                                    # Método alternativo: usar la API directa de Excel
                                    ws.api.Range(celda).Value = valor
                                    print(f"  ✅ B10 escrito con método alternativo")
                                    campos_escritos += 1
                                except Exception as e2:
                                    print(f"  ❌ También falló método alternativo: {e2}")
                    else:
                        print(f"  ⚠️ {campo.upper()}: vacío → {celda} (no se escribió)")
                
                print(f"✅ Información del proyecto escrita: {campos_escritos} campos")
                
            except Exception as e:
                print(f"⚠️ Error escribiendo datos del proyecto: {e}")
                # Continuar con la exportación aunque falle esta parte
        else:
            print("ℹ️ No se proporcionaron datos del proyecto")
        
        # PASO 4: Llenar datos del carrito
        if mostrar_mensaje_callback:
            mostrar_mensaje_callback("Escribiendo productos...")
        
        print(f"📝 Escribiendo {len(carrito)} productos...")
        
        # Configuración
        fila_inicio = 17
        max_filas_disponibles = 15
        items_total = len(carrito)
        
        # Insertar filas si es necesario
        if items_total > max_filas_disponibles:
            filas_a_insertar = items_total - max_filas_disponibles
            
            print(f"📝 Insertando {filas_a_insertar} filas adicionales...")
            if mostrar_mensaje_callback:
                mostrar_mensaje_callback(f"Insertando {filas_a_insertar} filas...")
            
            for i in range(filas_a_insertar):
                ws.api.Rows(32).Insert()
                # Copiar formato de la fila 31
                ws.range('31:31').copy()
                ws.range('32:32').paste(paste='formats')
            
            wb.app.cut_copy_mode = False
            print(f"✅ Filas insertadas correctamente")
        
        # Llenar datos del carrito
        productos_escritos = 0
        for i, producto in enumerate(carrito):
            fila_actual = fila_inicio + i
            
            try:
                # Limpiar fila
                ws.range(f'A{fila_actual}:I{fila_actual}').clear_contents()
                
                # Llenar datos básicos
                ws.range(f'A{fila_actual}').value = i + 1
                ws.range(f'B{fila_actual}').value = producto.descripcion
                
                # Unidad
                unidad = getattr(producto, 'unidad', 'UND')
                ws.range(f'F{fila_actual}').value = unidad
                
                # Cantidad y precios
                ws.range(f'G{fila_actual}').value = producto.cantidad
                ws.range(f'H{fila_actual}').value = round(producto.precio_unitario, 2)
                ws.range(f'I{fila_actual}').formula = f"=G{fila_actual}*H{fila_actual}"
                
                productos_escritos += 1
                print(f"  ✅ {i+1}: {producto.descripcion[:40]}...")
                
            except Exception as e:
                print(f"  ❌ Error en fila {fila_actual}: {e}")
        
        print(f"✅ Productos escritos: {productos_escritos}/{len(carrito)}")

        # ===== COPIAR FORMATO DE CELDAS COMBINADAS B17:E17 =====
        print("🎨 Copiando formato de celdas combinadas...")
        
        try:
            # Copiar el formato de B17:E17 (primera fila de productos)
            rango_formato_origen = ws.range('B17:E17')
            
            # Aplicar a todas las filas de productos (desde B17 hasta la última fila)
            for i in range(items_total):
                fila_actual = fila_inicio + i
                
                # Solo copiar si no es la primera fila (que ya tiene el formato)
                if fila_actual > 17:
                    try:
                        rango_destino = ws.range(f'B{fila_actual}:E{fila_actual}')
                        
                        # Copiar formato
                        rango_formato_origen.copy()
                        rango_destino.api.PasteSpecial(Paste=-4122)  # xlPasteFormats = -4122
                        
                        print(f"  ✅ Formato copiado a fila {fila_actual}")
                    except Exception as e:
                        print(f"  ⚠️ Error en fila {fila_actual}: {e}")
            
            # Limpiar portapapeles
            wb.app.cut_copy_mode = False
            print(f"✅ Formato aplicado a {items_total} filas")
            
        except Exception as e:
            print(f"⚠️ Error copiando formato: {e}")


        # Limpiar filas no utilizadas y ELIMINAR filas vacías completamente
        ultima_fila_datos = fila_inicio + items_total - 1
        fila_limite = 31 + max(0, items_total - max_filas_disponibles)
        
        if ultima_fila_datos < fila_limite:
            print("🧹 Eliminando filas vacías completamente...")
            if mostrar_mensaje_callback:
                mostrar_mensaje_callback("Eliminando filas vacías...")
            
            # Calcular cuántas filas eliminar
            filas_a_eliminar = fila_limite - ultima_fila_datos
            fila_inicio_eliminacion = ultima_fila_datos + 1
            
            print(f"🗑️ Eliminando {filas_a_eliminar} filas desde la fila {fila_inicio_eliminacion}")
            
            # Eliminar filas vacías usando el equivalente a Ctrl + - (eliminar fila completa)
            try:
                # Seleccionar el rango de filas a eliminar
                rango_eliminar = f"{fila_inicio_eliminacion}:{fila_limite}"
                print(f"📋 Seleccionando filas: {rango_eliminar}")
                
                # Eliminar las filas completas (equivalente a Ctrl + - en filas completas)
                ws.api.Rows(rango_eliminar).Delete()
                
                print(f"✅ {filas_a_eliminar} filas eliminadas exitosamente")
                
            except Exception as e:
                print(f"⚠️ Error eliminando filas: {e}")
                # Fallback: solo limpiar contenido si no se pueden eliminar
                for fila in range(fila_inicio_eliminacion, fila_limite + 1):
                    try:
                        ws.range(f'A{fila}:I{fila}').clear_contents()
                    except:
                        pass
                print("✅ Contenido de filas limpiado (fallback)")
        else:
            print("ℹ️ No hay filas vacías que eliminar")
        
# ===== ACTUALIZAR FÓRMULAS DIRECTAMENTE (ANTES DE ELIMINAR FILAS) =====
        if mostrar_mensaje_callback:
            mostrar_mensaje_callback("Actualizando totales...")
        
        print("🔄 Actualizando fórmulas de suma...")
        
        # Calcular la última fila basándonos en la cantidad de productos
        cantidad_productos = len(carrito)
        ultima_fila_datos = fila_inicio + cantidad_productos - 1  # 17 + cantidad - 1
        
        print(f"📊 Productos en carrito: {cantidad_productos}")
        print(f"📊 Primera fila: I{fila_inicio}")
        print(f"📊 Última fila: I{ultima_fila_datos}")
        print(f"📊 Fórmula correcta: =SUMA(I{fila_inicio}:I{ultima_fila_datos})")
        
        # La fórmula está en la fila inmediatamente después de los datos
        fila_formula = ultima_fila_datos + 1
        
        celdas_actualizadas = 0
        
        # Actualizar columna I (PRECIO TOTAL)
        try:
            celda_i = ws.range(f'I{fila_formula}')
            nueva_formula_i = f"=SUM(I{fila_inicio}:I{ultima_fila_datos})"  # SUM en inglés
            celda_i.api.Formula = nueva_formula_i 
            celdas_actualizadas += 1
            print(f"  ✅ Columna I (fila {fila_formula}): {nueva_formula_i}")
        except Exception as e:
            print(f"  ❌ Error en columna I: {e}")
        
        # Actualizar columna J si tiene fórmula similar
        try:
            celda_j = ws.range(f'J{fila_formula}')
            formula_j_str = str(celda_j.api.Formula)
            if formula_j_str and ('SUM' in formula_j_str.upper() or 'SUMA' in formula_j_str.upper()):
                import re
                nueva_formula_j = re.sub(r'I17:I\d+', f'I{fila_inicio}:I{ultima_fila_datos}', formula_j_str)
                celda_j.api.Formula = nueva_formula_j
                celdas_actualizadas += 1
                print(f"  ✅ Columna J (fila {fila_formula}): {nueva_formula_j}")
        except Exception as e:
            print(f"  ⚠️ Columna J: {e}")
        
        # Actualizar columna K si tiene fórmula similar
        try:
            celda_k = ws.range(f'K{fila_formula}')
            formula_k_str = str(celda_k.api.Formula)
            if formula_k_str and ('SUM' in formula_k_str.upper() or 'SUMA' in formula_k_str.upper()):
                import re
                nueva_formula_k = re.sub(r'I17:I\d+', f'I{fila_inicio}:I{ultima_fila_datos}', formula_k_str)
                celda_k.api.Formula = nueva_formula_k
                celdas_actualizadas += 1
                print(f"  ✅ Columna K (fila {fila_formula}): {nueva_formula_k}")
        except Exception as e:
            print(f"  ⚠️ Columna K: {e}")
        
        print(f"✅ Fórmulas de suma actualizadas: {celdas_actualizadas} celdas")
        
        # Actualizar fórmulas en las columnas I, J, K
        for col in ['I', 'J', 'K']:
            try:
                celda = ws.range(f'{col}{fila_formula}')
                formula_str = str(celda.formula)
                
                print(f"  📝 Fórmula actual en {col}{fila_formula}: {formula_str}")
                
                # Buscar cualquier fórmula SUMA que contenga I17
                if formula_str and 'SUMA' in formula_str.upper() and 'I17' in formula_str:
                    print(f"  🎯 Encontrada fórmula SUMA en {col}{fila_formula}")
                    
                    # Extraer el patrón I17:I## y reemplazarlo
                    import re
                    nueva_formula = re.sub(r'I17:I\d+', f'I17:I{ultima_fila_datos}', formula_str)
                    
                    if nueva_formula != formula_str:
                        celda.formula = nueva_formula
                        celdas_actualizadas += 1
                        print(f"  ✅ ACTUALIZADA en {col}{fila_formula}: {nueva_formula}")
                    else:
                        print(f"  ℹ️ Fórmula ya correcta en {col}{fila_formula}")
                        
            except Exception as e:
                print(f"  ⚠️ Error en {col}{fila_formula}: {e}")
                continue
        
        print(f"✅ Fórmulas de suma actualizadas: {celdas_actualizadas} celdas")
        
        # Obtener rutas de configuración
        from .configuracion import ConfiguracionManager
        config_manager = ConfiguracionManager()
        config = config_manager.config
        
        carpeta_excel = config["rutas"]["carpeta_excel"]
        carpeta_pdfs = config["rutas"]["carpeta_pdfs"]
        
        # Convertir barras / a \ para Windows
        carpeta_excel = carpeta_excel.replace("/", "\\")
        carpeta_pdfs = carpeta_pdfs.replace("/", "\\")
        
        print(f"📁 Carpeta Excel: {carpeta_excel}")
        print(f"📁 Carpeta PDFs: {carpeta_pdfs}")
        
        # Recalcular todo antes de guardar
        wb.app.calculate()

        # Ejecutar macro GUARDAREXCEL con ruta
        try:
            if mostrar_mensaje_callback:
                mostrar_mensaje_callback("Ejecutando macro GUARDAREXCEL...")
            wb.app.api.Run("GUARDAREXCEL", carpeta_excel)
            print(f"✅ Macro GUARDAREXCEL ejecutada - Guardado en: {carpeta_excel}")
        except Exception as e:
            print(f"⚠️ Error ejecutando macro GUARDAREXCEL: {e}")
            if mostrar_mensaje_callback:
                mostrar_mensaje_callback("⚠️ Error ejecutando GUARDAREXCEL")

        # Ejecutar macro GUARDARPDF con ruta
        try:
            if mostrar_mensaje_callback:
                mostrar_mensaje_callback("Ejecutando macro GUARDARPDF...")
            wb.app.api.Run("GUARDARPDF", carpeta_pdfs)
            print(f"✅ Macro GUARDARPDF ejecutada - Guardado en: {carpeta_pdfs}")
        except Exception as e:
            print(f"⚠️ Error ejecutando macro GUARDARPDF: {e}")
            if mostrar_mensaje_callback:
                mostrar_mensaje_callback("⚠️ Error ejecutando GUARDARPDF")
        
        # ===== ABRIR CARPETA DE PDFs =====
        try:
            import subprocess
            print(f"📂 Abriendo carpeta de PDFs: {carpeta_pdfs}")
            subprocess.Popen(f'explorer "{carpeta_pdfs}"')
            print("✅ Carpeta abierta")
        except Exception as e:
            print(f"⚠️ Error abriendo carpeta: {e}")


        # Cerrar libro de cotización
        try:
            if len(wb.app.books) == 1:
                wb.app.quit()
                print("✅ Excel cerrado completamente (solo había este libro)")
            else:
                wb.close()
                print("✅ Libro de cotización cerrado (otros permanecen abiertos)")
        except Exception as e:
            print(f"⚠️ Error cerrando Excel: {e}")
            try:
                wb.app.kill()
                print("✅ Excel terminado forzosamente")
            except:
                print("⚠️ No se pudo cerrar Excel")

        if mostrar_mensaje_callback:
            mostrar_mensaje_callback("¡Exportación completada!")

        print("🎉 ¡Exportación completada exitosamente!")
        print("💡 Excel conserva todo su formato original")
        print("📋 Información del proyecto incluida")
        print("🔧 Macros VBA ejecutadas automáticamente (Excel + PDF)")

        # Mensaje de éxito para la GUI
        mensaje = f"✅ ¡Exportación completada!\n\n"
        mensaje += f"📊 Productos exportados: {len(carrito)}\n"
        mensaje += f"📂 Plantilla usada: {os.path.basename(RUTA_PLANTILLA)}\n"
        mensaje += f"🔧 Fórmulas actualizadas: {celdas_actualizadas}\n"
        mensaje += f"⚡ Macros ejecutadas: GUARDAREXCEL + GUARDARPDF\n"

        # Agregar información del proyecto si se proporcionó
        if datos_proyecto:
            campos_con_datos = [k for k, v in datos_proyecto.items() if v.strip()]
            mensaje += f"\n📋 Información del proyecto incluida ({len(campos_con_datos)} campos):\n"
            for campo, valor in datos_proyecto.items():
                if valor.strip():
                    mensaje += f"   • {campo.replace('_', ' ').title()}: {valor}\n"

        mensaje += f"\n💡 El proceso está completo:\n"
        mensaje += f"   ✅ Datos del carrito exportados\n"
        mensaje += f"   ✅ Información del proyecto escrita\n"
        mensaje += f"   ✅ Excel guardado por macro\n"
        mensaje += f"   ✅ PDF generado por macro\n"
        mensaje += f"   ✅ Libro cerrado automáticamente\n\n"
        mensaje += f"🎯 Listo para la siguiente cotización"

        return True, mensaje
        
    except Exception as e:
        error_msg = f"❌ Error durante la exportación: {str(e)}"
        print(error_msg)
        print(f"🔍 DEBUG - Datos del proyecto al fallar: {datos_proyecto}")
        return False, error_msg

def verificar_dependencias():
    """Verifica si está instalado xlwings"""
    try:
        import xlwings
        return []
    except ImportError:
        return ["xlwings"]

def instalar_dependencias():
    """Instala xlwings si no está disponible"""
    if not verificar_dependencias():
        return True, "xlwings ya está instalado."
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "xlwings"])
        return True, "xlwings instalado correctamente."
    except Exception as e:
        return False, f"Error instalando xlwings: {str(e)}"

def test_exportacion():
    """Función de prueba"""
    from .logica import ProductoCotizado, ProductoManual
    
    carrito_prueba = [
        ProductoCotizado("B", "GO - BANDEJA TIPO LISA 400X100X2400MM 1.5MM (C/UNION)", 150.50, 12.5, "GO", "30", 2),
        ProductoCotizado("B", "GO - TAPA BANDEJA 400MM 1.2MM", 45.30, 3.2, "GO", "30", 2),
        ProductoManual("TORNILLO ESPECIAL", "UND", 5.50, 0.1, 10)
    ]
    
    def mock_callback(mensaje):
        print(f"GUI: {mensaje}")
    
    resultado = exportar_carrito_a_excel(carrito_prueba, mock_callback)
    print(f"\nResultado final: {resultado}")

if __name__ == "__main__":
    deps = verificar_dependencias()
    if deps:
        print(f"Dependencias faltantes: {deps}")
        print("Ejecute: pip install " + " ".join(deps))
    else:
        print("xlwings está disponible.")
        print("Ejecutando prueba...")
        test_exportacion()