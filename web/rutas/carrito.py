"""
carrito.py — Endpoints del carrito de compras por sesión

El carrito se almacena en SQLite (tabla carrito_items), persistente entre reinicios.
"""
import json
import re
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from web.auth import require_login
from web.database import (
    get_carrito_db,
    add_item_carrito_db,
    update_cantidad_carrito_db,
    update_item_precio_carrito_db,
    update_item_campos_carrito_db,
    update_item_completo_carrito_db,
    delete_item_carrito_db,
    clear_carrito_db,
    mover_item_carrito_db,
    reordenar_carrito_db,
    cargar_config,
)
from web.motor import (
    PricingConfig,
    cotizar_bandeja,
    cotizar_curva_horizontal,
    cotizar_curva_vertical,
    cotizar_tee,
    cotizar_cruz,
    cotizar_reduccion,
    cotizar_caja_pase,
)

router = APIRouter(prefix="/api/carrito", tags=["carrito"])


def get_carrito(username: str):
    """Wrapper público — devuelve la lista de items del carrito desde DB."""
    return get_carrito_db(username)


@router.get("")
async def api_get_carrito(usuario: dict = Depends(require_login)):
    carrito = get_carrito(usuario["u"])
    total = sum(item["precio_unitario"] * item["cantidad"] for item in carrito)
    peso_total = sum(item["peso_unitario"] * item["cantidad"] for item in carrito)
    return JSONResponse({
        "ok": True,
        "carrito": carrito,
        "total": round(total, 2),
        "peso_total": round(peso_total, 4),
        "cantidad_items": len(carrito),
    })


@router.post("/agregar")
async def api_agregar_al_carrito(
    request: Request,
    usuario: dict = Depends(require_login),
    tipo: str = Form(...),
    descripcion: str = Form(...),
    precio_unitario: float = Form(...),
    peso_unitario: float = Form(...),
    cantidad: float = Form(1),
    unidad: str = Form("UND"),
    tipo_galvanizado: str = Form("GO"),
    porcentaje_ganancia: str = Form("30"),
    descripcion_calculada: Optional[str] = Form(None),
    precio_manual: int = Form(0),
):
    item = {
        "tipo": tipo,
        "descripcion": descripcion,
        "precio_unitario": round(precio_unitario, 4),
        "peso_unitario": round(peso_unitario, 6),
        "cantidad": max(0.01, round(cantidad, 2)),
        "unidad": unidad,
        "tipo_galvanizado": tipo_galvanizado,
        "porcentaje_ganancia": porcentaje_ganancia,
        "descripcion_calculada": descripcion_calculada,
        "precio_manual": precio_manual,
    }
    add_item_carrito_db(usuario["u"], item)
    n = len(get_carrito(usuario["u"]))
    return JSONResponse({"ok": True, "mensaje": "Producto agregado al carrito", "cantidad_items": n})


@router.post("/agregar_manual")
async def api_agregar_manual(
    request: Request,
    usuario: dict = Depends(require_login),
    descripcion: str = Form(...),
    unidad: str = Form("UND"),
    precio_unitario: float = Form(...),
    peso_unitario: float = Form(0),
    cantidad: int = Form(1),
):
    item = {
        "tipo": "MANUAL",
        "descripcion": descripcion,
        "precio_unitario": round(precio_unitario, 4),
        "peso_unitario": round(peso_unitario, 6),
        "cantidad": max(1, cantidad),
        "unidad": unidad,
        "tipo_galvanizado": "N/A",
        "porcentaje_ganancia": "N/A",
    }
    item_id = add_item_carrito_db(usuario["u"], item)
    item["id"] = item_id
    return JSONResponse({"ok": True, "item": item})


@router.post("/modificar/{item_id}")
async def api_modificar_cantidad(
    item_id: int,
    usuario: dict = Depends(require_login),
    cantidad: float = Form(...),
):
    if cantidad < 0.01:
        return JSONResponse({"ok": False, "error": "Cantidad inválida"}, status_code=400)
    updated = update_cantidad_carrito_db(item_id, usuario["u"], cantidad)
    if updated:
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)


@router.delete("/eliminar/{item_id}")
async def api_eliminar_item(
    item_id: int,
    usuario: dict = Depends(require_login),
):
    deleted = delete_item_carrito_db(item_id, usuario["u"])
    if deleted:
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)


@router.post("/limpiar")
async def api_limpiar_carrito(usuario: dict = Depends(require_login)):
    clear_carrito_db(usuario["u"])
    return JSONResponse({"ok": True, "mensaje": "Carrito limpiado"})


def _espesores_validos_desde_config(config: dict) -> set:
    """Extrae el conjunto de espesores válidos de la configuración (GO y GC)."""
    valores = config.get("valores_defecto", {})
    esps = set()
    for key in ("precios_go", "precios_gc"):
        esps.update(valores.get(key, {}).keys())
    return esps or {"1.2", "1.5", "2.0"}  # fallback si config está vacía


def _extraer_espesor(descripcion: str) -> Optional[float]:
    """Extrae el último espesor decimal (e.g. 1.5 de '1.5MM') de la descripción."""
    matches = re.findall(r'(\d+\.\d+)MM', descripcion)
    return float(matches[-1]) if matches else None


def _reemplazar_espesor(descripcion: str, nuevo_esp: float) -> str:
    """Reemplaza el último espesor decimal en la descripción."""
    matches = list(re.finditer(r'(\d+\.\d+)MM', descripcion))
    if not matches:
        return descripcion
    last = matches[-1]
    return descripcion[:last.start()] + f"{nuevo_esp:.1f}MM" + descripcion[last.end():]


@router.post("/cambiar_espesor")
async def api_cambiar_espesor(
    usuario: dict = Depends(require_login),
    nuevo_espesor: float = Form(...),
    parte: str = Form(...),        # "cuerpo" o "tapa"
    item_id: str = Form("all"),    # "all" o id numérico
):
    """Recalcula precio y peso de items del carrito al cambiar el espesor de plancha."""
    nuevo_esp_str = f"{nuevo_espesor:.1f}"
    config = cargar_config()
    espesores_validos = _espesores_validos_desde_config(config)
    if nuevo_esp_str not in espesores_validos:
        return JSONResponse({"ok": False, "error": "Espesor inválido"}, status_code=400)
    if parte not in ("cuerpo", "tapa"):
        return JSONResponse({"ok": False, "error": "Parte inválida"}, status_code=400)

    valores = config.get("valores_defecto", {})

    carrito = get_carrito(usuario["u"])
    actualizados = 0
    omitidos = []

    for item in carrito:
        # Filtrar por item_id si se especificó uno
        if item_id != "all" and str(item["id"]) != item_id:
            continue

        # Items sin cálculo predeterminado (manuales o de catálogo)
        if item["tipo_galvanizado"] == "N/A":
            omitidos.append(item["descripcion"])
            continue

        desc = item["descripcion"]
        desc_calc = item.get("descripcion_calculada") or None
        # Para detectar tapa y extraer espesor: preferir descripcion_calculada si existe
        desc_ref = desc_calc if desc_calc else desc
        es_tapa = "TAPA" in desc_ref.upper()

        # Solo procesar la parte solicitada
        if parte == "tapa" and not es_tapa:
            continue
        if parte == "cuerpo" and es_tapa:
            continue

        # Extraer espesor actual desde la referencia (calculada si existe, si no la original)
        esp_actual = _extraer_espesor(desc_ref)
        if esp_actual is None:
            # Último fallback: intentar desde la descripción original
            esp_actual = _extraer_espesor(desc)
        if esp_actual is None:
            omitidos.append(desc)
            continue

        # Mismo espesor → sin cambio
        if abs(esp_actual - nuevo_espesor) < 0.001:
            continue

        esp_actual_str = f"{esp_actual:.1f}"
        tipo_galv = item["tipo_galvanizado"]
        precios_key = "precios_go" if tipo_galv == "GO" else "precios_gc"
        precios = valores.get(precios_key, {})

        pp_viejo = float(precios.get(esp_actual_str, 0))
        pp_nuevo = float(precios.get(nuevo_esp_str, 0))

        if pp_viejo <= 0 or pp_nuevo <= 0:
            omitidos.append(desc)
            continue

        # Nuevo precio: proporcional al precio de plancha (exacto para GO)
        nuevo_precio = item["precio_unitario"] * (pp_nuevo / pp_viejo)
        # Nuevo peso: proporcional al espesor (más material = más peso)
        nuevo_peso = item["peso_unitario"] * (nuevo_espesor / esp_actual)

        if desc_calc:
            # Tiene descripcion_calculada: actualizarla y dejar descripcion intacta
            nueva_desc_calc = _reemplazar_espesor(desc_calc, nuevo_espesor)
            update_item_precio_carrito_db(
                item["id"], usuario["u"],
                nuevo_precio, nuevo_peso, desc,
                descripcion_calculada=nueva_desc_calc,
            )
        else:
            # Sin descripcion_calculada: comportamiento original (actualiza descripcion)
            nueva_desc = _reemplazar_espesor(desc, nuevo_espesor)
            update_item_precio_carrito_db(
                item["id"], usuario["u"],
                nuevo_precio, nuevo_peso, nueva_desc,
            )
        actualizados += 1

    return JSONResponse({
        "ok": True,
        "actualizados": actualizados,
        "omitidos": omitidos,
    })


@router.post("/editar/{item_id}")
async def api_editar_item(
    item_id: int,
    usuario: dict = Depends(require_login),
    descripcion: str = Form(...),
    unidad: str = Form("UND"),
    precio_unitario: float = Form(...),
    descripcion_calculada: Optional[str] = Form(None),
):
    """Edita descripción, unidad, precio y opcionalmente ítem programa de un item."""
    carrito = get_carrito(usuario["u"])
    item = next((i for i in carrito if i["id"] == item_id), None)
    if not item:
        return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)
    updated = update_item_campos_carrito_db(
        item_id, usuario["u"],
        descripcion.strip(), unidad.strip(),
        precio_unitario,
        descripcion_calculada.strip() if descripcion_calculada else None,
    )
    if updated:
        return JSONResponse({
            "ok": True,
            "cuerpo": {
                "id": item_id,
                "descripcion": descripcion.strip(),
                "unidad": unidad.strip(),
                "tipo_galvanizado": item["tipo_galvanizado"],
                "porcentaje_ganancia": item["porcentaje_ganancia"],
                "precio_unitario": precio_unitario,
                "peso_unitario": item.get("peso_unitario", 0),
                "descripcion_calculada": descripcion_calculada.strip() if descripcion_calculada else None,
                "tipo": item.get("tipo"),
                "precio_manual": bool(item.get("precio_manual", 0)),
            },
        })
    return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)


@router.post("/und_a_ml/{item_id}")
async def api_und_a_ml(
    item_id: int,
    usuario: dict = Depends(require_login),
):
    """Convierte un item de bandeja de UND a ML (divide precio y peso por 2.4)."""
    carrito = get_carrito(usuario["u"])
    item = next((i for i in carrito if i["id"] == item_id), None)
    if not item:
        return JSONResponse({"ok": False, "error": "Item no encontrado"}, status_code=404)
    if item["tipo"] != "B":
        return JSONResponse({"ok": False, "error": "Solo bandejas pueden convertirse a ML"}, status_code=400)
    if item["unidad"] == "ML":
        return JSONResponse({"ok": False, "error": "El item ya está en ML"}, status_code=400)

    nuevo_precio = item["precio_unitario"] / 2.4
    nuevo_peso   = item["peso_unitario"]   / 2.4
    desc_calc    = item.get("descripcion_calculada")
    nueva_desc_calc = (desc_calc + " - POR ML") if desc_calc else None

    update_item_campos_carrito_db(
        item_id, usuario["u"],
        item["descripcion"], "ML", nuevo_precio, nueva_desc_calc,
    )
    # Actualizar también el peso
    update_item_precio_carrito_db(
        item_id, usuario["u"], nuevo_precio, nuevo_peso,
        item["descripcion"], nueva_desc_calc,
    )
    return JSONResponse({"ok": True})


@router.get("/resumen")
async def api_resumen_carrito(usuario: dict = Depends(require_login)):
    """Resumen compacto para el badge de la navbar."""
    carrito = get_carrito(usuario["u"])
    total = sum(item["precio_unitario"] * item["cantidad"] for item in carrito)
    return JSONResponse({
        "cantidad_items": len(carrito),
        "total": round(total, 2),
    })


@router.post("/mover/{item_id}")
async def api_mover_item(
    item_id: int,
    usuario: dict = Depends(require_login),
    direccion: str = Form(...),
):
    """Mueve un ítem arriba o abajo en la tabla del carrito."""
    if direccion not in ("arriba", "abajo"):
        return JSONResponse({"ok": False, "error": "Dirección inválida"}, status_code=400)
    moved = mover_item_carrito_db(item_id, usuario["u"], direccion)
    return JSONResponse({"ok": moved})


@router.post("/reordenar")
async def api_reordenar_carrito(
    usuario: dict = Depends(require_login),
    orden: str = Form(...),
):
    """Reordena los ítems del carrito según el array JSON de IDs de cuerpos."""
    try:
        ids = json.loads(orden)
        if not isinstance(ids, list):
            raise ValueError
        ids = [int(i) for i in ids]
    except (ValueError, TypeError):
        return JSONResponse({"ok": False, "error": "orden inválido"}, status_code=400)
    reordenar_carrito_db(usuario["u"], ids)
    return JSONResponse({"ok": True, "carrito": get_carrito(usuario["u"])})


def _item_payload(item_id, descripcion, unidad, galvanizado, ganancia,
                  precio, peso, desc_calc, tipo, precio_manual) -> dict:
    """Dict estándar de un ítem en las respuestas de /recalcular."""
    return {
        "id": item_id,
        "descripcion": descripcion,
        "unidad": unidad,
        "tipo_galvanizado": galvanizado,
        "porcentaje_ganancia": ganancia,
        "precio_unitario": precio,
        "peso_unitario": peso,
        "descripcion_calculada": desc_calc,
        "tipo": tipo,
        "precio_manual": precio_manual,
    }


def _recalcular_manual(item, item_id, username, descripcion, unidad, precio_override):
    """Ítems manuales o de catálogo (tipo_galvanizado N/A): solo texto/precio/unidad."""
    precio_final = item["precio_unitario"]
    precio_es_manual = bool(item.get("precio_manual", 0))
    if precio_override is not None and abs(precio_override - float(item["precio_unitario"])) > 0.001:
        precio_final = precio_override
        precio_es_manual = True
    updated = update_item_campos_carrito_db(
        item_id, username, descripcion.strip(), unidad.strip(),
        precio_final, item.get("descripcion_calculada"),
    )
    return JSONResponse({
        "ok": updated,
        "cuerpo": _item_payload(
            item_id, descripcion.strip(), unidad.strip(),
            item["tipo_galvanizado"], item["porcentaje_ganancia"],
            precio_final, item.get("peso_unitario", 0),
            item.get("descripcion_calculada"), item.get("tipo"), precio_es_manual,
        ),
    })


def _recalcular_tapa_vinculada(item, carrito, config, item_id, username, espesor_tapa):
    """Tapa separada (tapa_para_id): recalcular usando el cuerpo como referencia."""
    cuerpo_item = next((i for i in carrito if i["id"] == item["tapa_para_id"]), None)
    if not cuerpo_item:
        return JSONResponse({"ok": False, "error": "Cuerpo del ítem no encontrado"}, status_code=404)
    parsed_c = parsear_descripcion(cuerpo_item["descripcion"])
    if not parsed_c.get("tipo"):
        return JSONResponse({"ok": False, "error": "No se reconoció el tipo del cuerpo"}, status_code=400)
    parsed_c["espesor_explicito"] = False  # forzar override del espesor
    galvanizado_c = cuerpo_item["tipo_galvanizado"]
    mm_vals_c = [float(m) for m in re.findall(r'(\d+\.\d+)MM', cuerpo_item["descripcion"].upper())]
    _validos = {1.2, 1.5, 2.0}
    esp_c = mm_vals_c[0] if mm_vals_c and mm_vals_c[0] in _validos else parsed_c.get("espesor", 1.5)
    ganancia_c = cuerpo_item["porcentaje_ganancia"]  # bloqueada al cuerpo
    ov_t = {
        "galvanizado_global": galvanizado_c,
        "espesor_cuerpo_global": esp_c,
        "espesor_tapa_global": espesor_tapa,
        "ganancia_global": ganancia_c,
    }
    es_ml_c = (cuerpo_item["unidad"] == "ML" and parsed_c.get("tipo") == "B")
    res_t = calcular_precio_importado(
        parsed_c, config, ov_t,
        con_tapa=True,
        es_metro_lineal=es_ml_c,
        espesor_tapa_item=espesor_tapa,
    )
    if res_t is None or not res_t.get("tapa"):
        return JSONResponse({"ok": False, "error": "No se pudo calcular el precio de la tapa"}, status_code=400)
    td = res_t["tapa"]
    updated = update_item_completo_carrito_db(
        item_id, username,
        td[2], item["unidad"],
        round(td[0], 4), round(td[1], 6),
        galvanizado_c, ganancia_c,
        td[2],
        precio_manual=False,
    )
    return JSONResponse({
        "ok": updated,
        "cuerpo": _item_payload(
            item_id, td[2], item["unidad"], galvanizado_c, ganancia_c,
            round(td[0], 4), round(td[1], 6), td[2], item.get("tipo"), False,
        ),
    })


def _recalcular_tapa_independiente(item, parsed, config, item_id, username, descripcion,
                                   unidad, ganancia, espesor_cuerpo, espesor_tapa, precio_override):
    """Tapa sin tapa_para_id (agregada con 'tapa aparte ON'): devolver el cálculo de la tapa."""
    galvanizado_t = item["tipo_galvanizado"] if not parsed.get("galvanizado_explicito") else parsed["galvanizado"]
    ov_t = {
        "galvanizado_global": galvanizado_t,
        "espesor_cuerpo_global": espesor_cuerpo,
        "espesor_tapa_global": espesor_tapa,
        "ganancia_global": ganancia,
    }
    es_ml_t = (unidad == "ML" and parsed.get("tipo") == "B")
    res_t = calcular_precio_importado(
        parsed, config, ov_t,
        con_tapa=True,
        es_metro_lineal=es_ml_t,
        espesor_tapa_item=espesor_tapa,
    )
    if res_t is None or not res_t.get("tapa"):
        return JSONResponse({"ok": False, "error": "No se pudo calcular el precio de la tapa"}, status_code=400)
    td = res_t["tapa"]
    nueva_descripcion = _reemplazar_espesor(descripcion.strip(), espesor_tapa)
    precio_tapa_final = round(td[0], 4)
    precio_tapa_es_manual = False
    if precio_override is not None and abs(precio_override - precio_tapa_final) > 0.001:
        precio_tapa_final = precio_override
        precio_tapa_es_manual = True
    updated = update_item_completo_carrito_db(
        item_id, username,
        nueva_descripcion, unidad.strip(),
        precio_tapa_final, round(td[1], 6),
        galvanizado_t, ganancia,
        td[2],
        precio_manual=precio_tapa_es_manual,
    )
    return JSONResponse({
        "ok": updated,
        "cuerpo": _item_payload(
            item_id, nueva_descripcion, unidad.strip(), galvanizado_t, ganancia,
            precio_tapa_final, round(td[1], 6), td[2], item.get("tipo"), precio_tapa_es_manual,
        ),
    })


@router.post("/recalcular/{item_id}")
async def api_recalcular_item(
    item_id: int,
    usuario: dict = Depends(require_login),
    descripcion: str = Form(...),
    ganancia: str = Form("30"),
    espesor_cuerpo: float = Form(1.5),
    espesor_tapa: float = Form(1.5),
    unidad: str = Form("UND"),
    con_tapa: str = Form("si"),  # "si" | "no"
    precio_override: Optional[float] = Form(None),  # precio manual del usuario
):
    """Recalcula precio y peso de un ítem con nuevos parámetros."""
    carrito = get_carrito(usuario["u"])
    item = next((i for i in carrito if i["id"] == item_id), None)
    if not item:
        return JSONResponse({"ok": False, "error": "Ítem no encontrado"}, status_code=404)

    # Items manuales o de catálogo: solo guardar texto/precio/unidad
    if item["tipo_galvanizado"] == "N/A":
        return _recalcular_manual(item, item_id, usuario["u"], descripcion, unidad, precio_override)

    config = cargar_config()

    # ── Tapa separada: recalcular usando el cuerpo como referencia ──
    if item.get("tapa_para_id"):
        return _recalcular_tapa_vinculada(item, carrito, config, item_id, usuario["u"], espesor_tapa)

    parsed = parsear_descripcion(descripcion)
    if not parsed.get("tipo"):
        return JSONResponse({"ok": False, "error": "No se reconoció el tipo de producto"}, status_code=400)

    # El formulario manda el espesor explícitamente — ignorar el parseado de la descripción
    # para que el override espesor_cuerpo_global siempre se aplique
    parsed["espesor_explicito"] = False

    # ── Tapa independiente: ítem sin tapa_para_id pero descripción de tapa ──
    # Ocurre cuando el usuario agregó el producto con "tapa aparte ON" desde el formulario.
    # El motor generó dos ítems separados; la tapa tiene tapa_para_id=None porque no pasó
    # por api_separar_tapas. Al recalcular, hay que devolver r[1] (tapa), no r[0] (cuerpo).
    if item.get("tapa_para_id") is None and bool(_ES_TAPA_IND_RE.search(descripcion)):
        return _recalcular_tapa_independiente(
            item, parsed, config, item_id, usuario["u"], descripcion,
            unidad, ganancia, espesor_cuerpo, espesor_tapa, precio_override,
        )

    incluir_tapa = (con_tapa == "si")

    galvanizado = item["tipo_galvanizado"] if not parsed.get("galvanizado_explicito") else parsed["galvanizado"]
    overrides = {
        "galvanizado_global": galvanizado,
        "espesor_cuerpo_global": espesor_cuerpo,
        "espesor_tapa_global": espesor_tapa,
        "ganancia_global": ganancia,
    }

    es_ml = unidad == "ML" and parsed.get("tipo") == "B"

    # Detectar tapa vinculada (ítem separado que apunta a este cuerpo)
    tapa_vinculada = next((i for i in carrito if i.get("tapa_para_id") == item_id), None)

    # Calcular con tapa siempre que haya una vinculada (para poder recalcular su precio)
    calcular_con_tapa = incluir_tapa or (tapa_vinculada is not None)
    resultado = calcular_precio_importado(
        parsed, config, overrides,
        con_tapa=calcular_con_tapa,
        es_metro_lineal=es_ml,
        espesor_tapa_item=espesor_tapa,
    )
    if resultado is None:
        return JSONResponse({"ok": False, "error": "No se pudo calcular el precio con esos parámetros"}, status_code=400)

    cuerpo = resultado["cuerpo"]
    tapa   = resultado.get("tapa")

    # Precio del cuerpo: combinado solo si no hay tapa vinculada (modo junto)
    if tapa and incluir_tapa and tapa_vinculada is None:
        nuevo_precio    = round(cuerpo[0] + tapa[0], 4)
        nuevo_peso      = round(cuerpo[1] + tapa[1], 6)
        nueva_desc_calc = f"{cuerpo[2]} + {tapa[2]}"
    else:
        nuevo_precio    = round(cuerpo[0], 4)
        nuevo_peso      = round(cuerpo[1], 6)
        nueva_desc_calc = cuerpo[2]

    nueva_descripcion = _reemplazar_espesor(descripcion.strip(), espesor_cuerpo)
    precio_es_manual = False
    if precio_override is not None and abs(precio_override - nuevo_precio) > 0.001:
        nuevo_precio = precio_override
        precio_es_manual = True
    updated = update_item_completo_carrito_db(
        item_id, usuario["u"],
        nueva_descripcion, unidad.strip(),
        nuevo_precio, nuevo_peso,
        galvanizado, ganancia,
        nueva_desc_calc,
        precio_manual=precio_es_manual,
    )

    # Propagar cambios a la tapa vinculada
    if tapa_vinculada:
        if not incluir_tapa:
            # Usuario eligió "Sin tapa" → eliminar tapa vinculada
            import sqlite3 as _sq
            from web.database import DB_PATH as _DB
            _c = _sq.connect(str(_DB), timeout=10)
            _c.execute("DELETE FROM carrito_items WHERE id=? AND username=?",
                       (tapa_vinculada["id"], usuario["u"]))
            _c.commit()
            _c.close()
        elif tapa:
            # Recalcular tapa con los nuevos parámetros (ganancia, espesor_tapa)
            update_item_completo_carrito_db(
                tapa_vinculada["id"], usuario["u"],
                tapa[2], unidad.strip(),
                round(tapa[0], 4), round(tapa[1], 6),
                galvanizado, ganancia,
                tapa[2],
            )

    response = {
        "ok": updated,
        "cuerpo": {
            "id": item_id,
            "descripcion": nueva_descripcion,
            "unidad": unidad.strip(),
            "tipo_galvanizado": galvanizado,
            "porcentaje_ganancia": ganancia,
            "precio_unitario": nuevo_precio,
            "peso_unitario": nuevo_peso,
            "descripcion_calculada": nueva_desc_calc,
            "tipo": item.get("tipo"),
            "precio_manual": precio_es_manual,
        },
    }
    if tapa_vinculada:
        if not incluir_tapa:
            response["tapa_action"] = "deleted"
            response["tapa_id"] = tapa_vinculada["id"]
        elif tapa:
            response["tapa_action"] = "updated"
            response["tapa"] = {
                "id": tapa_vinculada["id"],
                "descripcion": tapa[2],
                "unidad": unidad.strip(),
                "tipo_galvanizado": galvanizado,
                "porcentaje_ganancia": ganancia,
                "precio_unitario": round(tapa[0], 4),
                "peso_unitario": round(tapa[1], 6),
                "descripcion_calculada": tapa[2],
                "tipo": tapa_vinculada.get("tipo"),
                "precio_manual": False,
            }
    return JSONResponse(response)


@router.post("/separar_tapas")
async def api_separar_tapas(usuario: dict = Depends(require_login)):
    """Separa los ítems combinados cuerpo+tapa en dos filas independientes."""
    import sqlite3
    from web.database import DB_PATH

    _TAPA_RE = re.compile(
        r'\bC[/\\]?TAPA\b|\bCON\s+TAPA\b|\(C/UNI[ÓO]N\s+Y\s+TAPA\)|'
        r'\+\s*TAPA\b|\bY\s+TAPA\b',
        re.IGNORECASE,
    )

    config = cargar_config()
    carrito = get_carrito(usuario["u"])
    separados = 0
    for item in carrito:
        # Saltar tapas ya separadas
        if item.get("tapa_para_id"):
            continue
        # Saltar ítems manuales/catálogo
        if item.get("tipo_galvanizado") == "N/A":
            continue

        desc_calc = item.get("descripcion_calculada") or ""
        tiene_tapa = (
            " + TAPA " in desc_calc.upper()
            or bool(_TAPA_RE.search(item["descripcion"]))
        )
        if not tiene_tapa:
            continue

        # Parsear la descripción original para extraer tipo y dimensiones
        parsed = parsear_descripcion(item["descripcion"])
        if not parsed.get("tipo") or parsed["tipo"] == "CP":
            continue   # Caja de Pase no tiene tapa separable

        galvanizado = item["tipo_galvanizado"]
        ganancia    = item["porcentaje_ganancia"]

        # Extraer espesores de la descripcion_calculada si existe, si no de la descripcion
        desc_ref = desc_calc if desc_calc else item["descripcion"]
        mm_vals = [float(m) for m in re.findall(r'(\d+\.\d+)MM', desc_ref.upper())]
        validos = {1.2, 1.5, 2.0}
        esp_c = mm_vals[0] if mm_vals and mm_vals[0] in validos else parsed.get("espesor", 1.5)
        esp_t = mm_vals[1] if len(mm_vals) > 1 and mm_vals[1] in validos else esp_c

        overrides = {
            "galvanizado_global": galvanizado,
            "ganancia_global": ganancia,
            "espesor_cuerpo_global": esp_c,
            "espesor_tapa_global": esp_t,
        }

        resultado = calcular_precio_importado(
            parsed, config, overrides,
            con_tapa=True,
            es_metro_lineal=(item["unidad"] == "ML"),
            espesor_tapa_item=esp_t,
        )
        if resultado is None or not resultado.get("tapa"):
            continue

        cuerpo_data = resultado["cuerpo"]
        tapa_data   = resultado["tapa"]

        # Descripción del cuerpo: cambiar "(C/UNIÓN Y TAPA)" → "(C/UNIÓN SIN TAPA)"
        # Para otros patrones (ej. "+ TAPA"), quitarlos directamente
        _UNION_Y_TAPA_RE = re.compile(r'\(C/UNI[ÓO]N\s+Y\s+TAPA\)', re.IGNORECASE)
        if _UNION_Y_TAPA_RE.search(item["descripcion"]):
            desc_cuerpo = _UNION_Y_TAPA_RE.sub('(C/UNIÓN SIN TAPA)', item["descripcion"]).strip()
        else:
            desc_cuerpo = _TAPA_RE.sub('', item["descripcion"]).strip().rstrip(',-').strip()

        # Actualizar el item actual solo como cuerpo
        update_item_completo_carrito_db(
            item["id"], usuario["u"],
            desc_cuerpo, item["unidad"],
            round(cuerpo_data[0], 4), round(cuerpo_data[1], 6),
            galvanizado, ganancia,
            cuerpo_data[2],
        )
        # Insertar nueva fila de tapa vinculada
        tapa_item = {
            "tipo": item["tipo"],
            "descripcion": tapa_data[2],
            "precio_unitario": round(tapa_data[0], 4),
            "peso_unitario": round(tapa_data[1], 6),
            "cantidad": item["cantidad"],
            "unidad": item["unidad"],
            "tipo_galvanizado": galvanizado,
            "porcentaje_ganancia": ganancia,
            "descripcion_calculada": tapa_data[2],
        }
        add_item_carrito_db(usuario["u"], tapa_item, tapa_para_id=item["id"])
        separados += 1

    return JSONResponse({
        "ok": True,
        "separados": separados,
        "carrito": get_carrito(usuario["u"]),
    })


@router.post("/juntar_tapas")
async def api_juntar_tapas(usuario: dict = Depends(require_login)):
    """Une tapas separadas con su cuerpo correspondiente en un solo ítem combinado."""
    import sqlite3
    from web.database import DB_PATH

    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    tapas = conn.execute(
        "SELECT * FROM carrito_items WHERE username=? AND tapa_para_id IS NOT NULL",
        (usuario["u"],),
    ).fetchall()

    juntados = 0
    c = conn.cursor()
    for tapa in tapas:
        tapa = dict(tapa)
        cuerpo_id = tapa["tapa_para_id"]
        cuerpo = conn.execute(
            "SELECT * FROM carrito_items WHERE id=? AND username=?",
            (cuerpo_id, usuario["u"]),
        ).fetchone()
        if not cuerpo:
            continue
        cuerpo = dict(cuerpo)

        nuevo_precio = round(cuerpo["precio_unitario"] + tapa["precio_unitario"], 4)
        nuevo_peso   = round(cuerpo["peso_unitario"]   + tapa["peso_unitario"],   6)
        cuerpo_calc  = cuerpo.get("descripcion_calculada") or cuerpo["descripcion"]
        tapa_calc    = tapa.get("descripcion_calculada")   or tapa["descripcion"]
        nueva_calc   = f"{cuerpo_calc} + {tapa_calc}"

        # Restaurar "(C/UNIÓN SIN TAPA)" → "(C/UNIÓN Y TAPA)" en la descripción del cuerpo
        _SIN_TAPA_RE = re.compile(r'\(C/UNI[ÓO]N\s+SIN\s+TAPA\)', re.IGNORECASE)
        desc_cuerpo_orig = cuerpo["descripcion"]
        if _SIN_TAPA_RE.search(desc_cuerpo_orig):
            nueva_desc = _SIN_TAPA_RE.sub('(C/UNIÓN Y TAPA)', desc_cuerpo_orig).strip()
        else:
            nueva_desc = desc_cuerpo_orig

        c.execute(
            """UPDATE carrito_items
               SET precio_unitario=?, peso_unitario=?, descripcion_calculada=?, descripcion=?
               WHERE id=? AND username=?""",
            (nuevo_precio, nuevo_peso, nueva_calc, nueva_desc, cuerpo_id, usuario["u"]),
        )
        c.execute("DELETE FROM carrito_items WHERE id=? AND username=?", (tapa["id"], usuario["u"]))
        juntados += 1

    conn.commit()
    conn.close()
    return JSONResponse({
        "ok": True,
        "juntados": juntados,
        "carrito": get_carrito(usuario["u"]),
    })


# ─────────────────────────────────────────────
# Importar tabla desde portapapeles
# ─────────────────────────────────────────────

# Orden de prioridad: más específico primero para evitar falsos positivos
# Los keywords de una sola letra/código corto usan word-boundary (ver matching abajo)
_PRODUCT_KEYWORDS_ORDERED = [
    ("CP",  ["CAJA DE PASE", "CAJA DE PASO", "CAJAS DE PASE", "CAJAS DE PASO",
             "CAJA PASE", "CAJA FE GALV", "CAJA FE", "CAJA METALICA",
             "CAJAS METALICA", "CAJA FG", "CAJA F.G.", "CAJA F°G°", "CAJA F@G@",
             "CAJA"]),  # catch-all: "caja 300x300x100mm 3/4"
    ("CVE", ["CURVA VERTICAL EXTERNA", "CURVA VERTICAL EXTERIOR",
             "ACCESORIO CURVA VERTICAL EXTERNA", "ACCESORIO CURVA VERTICAL EXTERIOR",
             "CVE", "ACCESORIO CVE"]),
    ("CVI", ["CURVA VERTICAL INTERNA", "CURVA VERTICAL INTERIOR",
             "ACCESORIO CURVA VERTICAL INTERNA", "ACCESORIO CURVA VERTICAL INTERIOR",
             "CVI", "ACCESORIO CVI"]),
    ("CH",  ["CURVA HORIZONTAL", "ACCESORIO CURVA HORIZONTAL",
             "CURVA H", "ACCESORIO CURVA H", "ACCESORIO CH"]),
    ("T",   ["TEE", "ACCESORIO TEE", "ACCESORIO T", "T"]),
    ("C",   ["CRUZ", "ACCESORIO CRUZ", "ACCESORIO C"]),
    ("R",   ["REDUCCION", "REDUCCIÓN", "REDUC",
             "ACCESORIO REDUCCION", "ACCESORIO REDUCCIÓN", "ACCESORIO REDUC",
             "ACCESORIO R"]),
    ("B",   ["BANDEJA", "BDJ"]),
]

_CATALOGO_PATH = Path(__file__).resolve().parent.parent.parent / "catalogo_productos.json"

# ─────────────────────────────────────────────
# Búsqueda en catálogo de productos fijos
# ─────────────────────────────────────────────

def _cargar_catalogo_plano() -> list:
    """Carga catalogo_productos.json y devuelve todos los productos como lista plana."""
    try:
        with open(_CATALOGO_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    productos = []
    for cat in data.get("categorias", []):
        for sub in cat.get("subcategorias", []):
            for prod in sub.get("productos", []):
                productos.append({
                    "descripcion": prod.get("descripcion", ""),
                    "unidad": prod.get("unidad", "UND"),
                    "precio": float(prod.get("precio", 0)),
                })
    return productos


# Diámetros nominales EMT en mm → token pulgadas equivalente del catálogo.
# El catálogo usa notación en pulgadas; las listas de obra usan mm.
# Orden: del más grande al más pequeño para que re.sub no confunda "100" con "10".
_EMT_MM_A_PUL: dict[str, str] = {
    "102": "4pul",       # 4"
    "100": "4pul",       # 4"
    "80":  "3pul",       # 3"
    "76":  "3pul",       # 3"
    "65":  "2_1_2pul",   # 2 1/2"
    "50":  "2pul",       # 2"
    "40":  "1_1_2pul",   # 1 1/2"  (nominal Perú)
    "38":  "1_1_2pul",   # 1 1/2"
    "32":  "1_1_4pul",   # 1 1/4"
    "25":  "1pul",       # 1"
    "20":  "3_4pul",     # 3/4"
    "15":  "1_2pul",     # 1/2"
}


def _normalizar_para_match(texto: str) -> set:
    """Normaliza texto a conjunto de tokens para comparación fuzzy.

    Estrategia especial para especificaciones de diámetro en pulgadas:
    - Fracciones: "3/4" → "3_4" (token único para no confundir "3" y "4" por separado)
    - Pulgadas compuestas: '1 1/4"' → "1_1_4pul"
    - Pulgadas simples: '4"' → "4pul"
    - mm EMT: "40mm" → "1_1_2pul" (via _EMT_MM_A_PUL)
    Esto evita que "tubo EMT 4\"" coincida con "tubo EMT 3/4\"" por el token "4".
    """
    # Quitar acentos (NFD → ASCII)
    nfd = unicodedata.normalize("NFD", texto.lower())
    ascii_str = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Sinónimos: equiparar vocabulario de listas externas con el del catálogo
    ascii_str = re.sub(r'\btuberia\b', 'tubo', ascii_str)
    ascii_str = re.sub(r'\bconduit\b', 'emt', ascii_str)
    ascii_str = re.sub(r'\bcurvas\b', 'curva', ascii_str)
    ascii_str = re.sub(r'\babarzaderas?\b', 'abrazadera', ascii_str)   # typo frecuente
    ascii_str = re.sub(r'\babrazaderas\b', 'abrazadera', ascii_str)
    ascii_str = re.sub(r'\buniones\b', 'union', ascii_str)
    ascii_str = re.sub(r'\bconectores\b', 'conector', ascii_str)
    # Diámetros EMT en mm → token pulgadas equivalente (antes de procesar fracciones)
    def _mm_a_pul(m: re.Match) -> str:
        tok = _EMT_MM_A_PUL.get(m.group(1))
        return f" {tok} " if tok else m.group(0)
    ascii_str = re.sub(r'(\d+)\s*mm', _mm_a_pul, ascii_str)
    # Normalizar pulgadas compuestas antes de reemplazar chars especiales
    # Con comillas: "1 1/4\"" → "1_1_4pul"
    ascii_str = re.sub(r'(\d+)\s+(\d+)/(\d+)\s*"', r'\1_\2_\3pul', ascii_str)
    # Sin comillas: "1 1/2" → "1_1_2pul" (texto pegado desde tablas sin símbolo ")
    ascii_str = re.sub(r'(\d+)\s+(\d+)/(\d+)', r'\1_\2_\3pul', ascii_str)
    # "3/4\"" → "3_4pul"
    ascii_str = re.sub(r'(\d+)/(\d+)\s*"', r'\1_\2pul', ascii_str)
    # "4\"" → "4pul"
    ascii_str = re.sub(r'(\d+)\s*"', r'\1pul', ascii_str)
    # Fracciones sin comillas: "3/4" → "3_4pul" (mismo token que "3/4\"")
    ascii_str = re.sub(r'(\d+)/(\d+)', r'\1_\2pul', ascii_str)
    # Reemplazar caracteres no alfanuméricos por espacios
    limpio = re.sub(r"[^a-z0-9_]", " ", ascii_str)
    tokens = set(limpio.split())
    # Quitar tokens de una sola letra que no sean medidas conocidas
    tokens = {t for t in tokens if len(t) > 1 or t in ("m",)}
    # Stopwords: preposiciones vacías que crean falsos empates
    tokens -= {"de", "del", "el", "la", "los", "las", "un", "una", "al"}
    return tokens


def _buscar_en_catalogo(descripcion: str, ganancia: str = "30") -> Optional[dict]:
    """
    Busca el mejor match para la descripción en el catálogo de precio fijo.
    Retorna dict con {descripcion, unidad, precio_catalogo, score} o None si no hay match >= 0.45.

    Si la descripción menciona explícitamente "IMC" no se busca en el catálogo
    (el catálogo solo tiene productos EMT).
    """
    if re.search(r'\bIMC\b', descripcion, re.IGNORECASE):
        return None

    productos = _cargar_catalogo_plano()
    if not productos:
        return None

    tokens_query = _normalizar_para_match(descripcion)
    if not tokens_query:
        return None

    mejor_score = 0.0
    mejor_prod = None

    for prod in productos:
        tokens_prod = _normalizar_para_match(prod["descripcion"])
        if not tokens_prod:
            continue
        interseccion = tokens_query & tokens_prod
        # score = intersección / mínimo de los dos conjuntos
        score = len(interseccion) / min(len(tokens_query), len(tokens_prod))
        if score > mejor_score:
            mejor_score = score
            mejor_prod = prod

    if mejor_score < 0.45 or mejor_prod is None:
        return None

    precio_base = mejor_prod["precio"]
    precio = precio_base * 0.7 / 0.65 if ganancia == "35" else precio_base

    return {
        "descripcion": mejor_prod["descripcion"],
        "unidad": mejor_prod["unidad"],
        "precio_catalogo": precio,
        "score": mejor_score,
    }


_DIM_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)'
    r'(?:\s*[xX×]\s*(\d+(?:[.,]\d+)?))?'
    r'(?:\s*[xX×]\s*(\d+(?:[.,]\d+)?))?'
)
_ESP_RE = re.compile(r'(\d+[.,]\d+)\s*MM', re.IGNORECASE)
_ESPESORES_VALIDOS = {1.2, 1.5, 2.0}

# Detecta patrón "enteroXenteroXenteroMM" en Caja de Pase (dims en mm, no en cm)
# Ej: "500X300X200MM" → dims en mm → dividir /10 para pasar al motor (que espera cm)
_CP_DIMS_MM_RE = re.compile(r'\b(\d+)\s*[xX×]\s*(\d+)\s*[xX×]\s*(\d+)\s*MM\b', re.IGNORECASE)

# Espesores en notación fraccionaria pulgadas → mm equivalente en nuestro sistema
_FRAC_ESPESOR = {"1/20": 1.2, "1/16": 1.5}
_FRAC_ESP_RE = re.compile(r'1/(?:20|16)', re.IGNORECASE)

# Detecta tapas independientes (añadidas desde el formulario con "tapa aparte ON")
# cuya descripción empieza con "TAPA <tipo>" pero no tienen tapa_para_id vinculado
_ES_TAPA_IND_RE = re.compile(
    r'\bTAPA\s+(?:BANDEJA|CURVA|TEE|CRUZ|REDUCCION)\b', re.IGNORECASE
)


def parsear_descripcion(desc_raw: str) -> dict:
    """Extrae tipo, dimensiones, espesor, galvanizado y superficie de la descripción."""
    desc = desc_raw.upper().strip()

    # Tipo de producto (primer keyword que coincida)
    # Códigos cortos (≤3 chars) usan word-boundary para evitar falsos positivos
    tipo = None
    for codigo, keywords in _PRODUCT_KEYWORDS_ORDERED:
        for kw in keywords:
            if len(kw) <= 3:
                if re.search(r'\b' + re.escape(kw) + r'\b', desc):
                    tipo = codigo
                    break
            else:
                if kw in desc:
                    tipo = codigo
                    break
        if tipo:
            break

    # Normalizar separador "A" entre grupos de dimensiones
    # Caso 1: "700MM A 500MM" (reducción externa sin alto explícito) → "700X500MM"
    desc_dims = re.sub(r'(\d+)\s*(?:MM|CM)\s+[Aa]\s+(\d+)', r'\1X\2', desc)
    # Caso 2: "600X100 A 400X100" (clásico, dígito directo antes del espacio-A) → "600X100X400X100"
    desc_dims = re.sub(r'(?<=[0-9])\s+[Aa]\s+(?=[0-9])', 'X', desc_dims)
    # Reemplazar coma decimal por punto para el regex
    desc_dims = desc_dims.replace(",", ".")

    dims: list[float] = []
    m = _DIM_RE.search(desc_dims)
    if m:
        for g in m.groups():
            if g is not None:
                try:
                    dims.append(float(g))
                except ValueError:
                    pass

    # Espesor: último número decimal seguido de MM (ej: "1.20 MM", "1.5MM")
    esp_matches = _ESP_RE.findall(desc.replace(",", "."))
    espesor = 1.5
    espesor_explicito = False
    if esp_matches:
        try:
            val = float(esp_matches[-1])
            espesor = val if val in _ESPESORES_VALIDOS else 1.5
            espesor_explicito = True
        except ValueError:
            pass
    else:
        # Fallback: notación fraccionaria en pulgadas (ej: "1/20"" → 1.2mm, "1/16"" → 1.5mm)
        frac_m = _FRAC_ESP_RE.search(desc)
        if frac_m:
            espesor = _FRAC_ESPESOR.get(frac_m.group(0).upper(), 1.5)
            espesor_explicito = True

    galvanizado_explicito = bool(re.search(r'\bGC\b', desc))
    galvanizado = "GC" if galvanizado_explicito else "GO"

    # Detectar "C/TAPA" o "CON TAPA" en la descripción (frecuente en tablas externas)
    con_tapa_desc = bool(re.search(r'\bC[/\\]?TAPA\b|\bCON\s+TAPA\b', desc))

    superficie_explicita = False
    if "ESCALERILLA" in desc:
        superficie = "ESCALERILLA"
        superficie_explicita = True
    elif "RANURADA" in desc:
        superficie = "RANURADA"
        superficie_explicita = True
    elif "LISA" in desc:
        superficie = "LISA"
        superficie_explicita = True
    else:
        superficie = "RANURADA"  # default para texto libre; tabla usa global override

    # Tipo de apertura para Caja de Pase
    knockout = "CIEGA"
    knockout_explicito = False
    if tipo == "CP":
        if any(kw in desc for kw in ("CON SALIDA", "C/SALIDA", "C/S", "KNOCKOUT", "K.O.", "KO")):
            # Intentar extraer la medida específica del tubo: 1/2, 3/4, 1, MIXTO
            _size_m = re.search(r'\bC[/\\]S\s+(MIXTO|1/2|3/4|1(?![/\d]))', desc)
            knockout = _size_m.group(1) if _size_m else "CON SALIDA"
            knockout_explicito = True
        elif re.search(r'\b(3/4|1/2)\b', desc):
            # Fracción sola (ej: "300x300x100mm 3/4") → C/S con esa medida
            frac_ko = re.search(r'\b(3/4|1/2)\b', desc)
            knockout = frac_ko.group(1) if frac_ko else "CON SALIDA"
            knockout_explicito = True
        elif "CIEGA" in desc:
            knockout = "CIEGA"
            knockout_explicito = True

    # Caja de Pase: el motor espera dims en CM (multiplica ×10 internamente).
    # Reglas de conversión de unidades:
    #   1. Sufijo MM explícito (ej: "500X300X200MM") → dividir /10
    #   2. Sufijo CM explícito (ej: "15 X 15 X 10 CM") → ya están en CM, sin cambio
    #   3. Sin sufijo y max(dim) ≥ 100 → interpretar como MM → dividir /10
    #      (ej: "CAJA PASE 100X100X50 SAP" = 100x100x50 mm = 10x10x5 cm)
    if tipo == "CP" and dims:
        cp_mm_m = _CP_DIMS_MM_RE.search(desc)
        if cp_mm_m:
            dims = [d / 10.0 for d in dims]
        elif "CM" not in desc and dims and max(dims) >= 100:
            dims = [d / 10.0 for d in dims]

    return {
        "tipo": tipo,
        "dims": dims,
        "espesor": espesor,
        "espesor_explicito": espesor_explicito,
        "galvanizado": galvanizado,
        "galvanizado_explicito": galvanizado_explicito,
        "superficie": superficie,
        "superficie_explicita": superficie_explicita,
        "knockout": knockout,
        "knockout_explicito": knockout_explicito,
        "con_tapa_desc": con_tapa_desc,
    }


def calcular_precio_importado(
    parsed: dict,
    config: dict,
    overrides: Optional[dict] = None,
    con_tapa: bool = False,
    es_metro_lineal: bool = False,
    espesor_tapa_item: Optional[float] = None,
):
    """
    Calcula precio y peso usando motor.py dado un parsed de parsear_descripcion().
    overrides: galvanizado_global, espesor_cuerpo_global, espesor_tapa_global, ganancia_global,
               superficie_global — se aplican solo cuando el ítem no tiene valor explícito.
    con_tapa: si True, retorna también datos de la tapa como ítem separado.
    es_metro_lineal: divide precio/peso de bandeja por 2.4 y agrega "– POR ML".
    espesor_tapa_item: espesor específico de la tapa (por ítem); None = usar global o body.
    Retorna {"cuerpo": (precio, peso, desc), "tapa": (precio, peso, desc) | None} o None.
    """
    tipo = parsed.get("tipo")
    dims = parsed.get("dims", [])
    knockout = parsed.get("knockout", "CIEGA")

    if not tipo:
        return None

    ov = overrides or {}

    # Galvanizado: explícito en descripción > global override > default GO
    if parsed.get("galvanizado_explicito"):
        galvanizado = parsed.get("galvanizado", "GO")
    elif ov.get("galvanizado_global"):
        galvanizado = ov["galvanizado_global"]
    else:
        galvanizado = parsed.get("galvanizado", "GO")

    # Superficie: global override del bar (usuario lo eligió) > explícita en descripción > default RANURADA
    if ov.get("superficie_global"):
        superficie = ov["superficie_global"]
    elif parsed.get("superficie_explicita"):
        superficie = parsed.get("superficie", "RANURADA")
    else:
        superficie = parsed.get("superficie", "RANURADA")

    # Espesor cuerpo: explícito en descripción > global override > default 1.5
    if parsed.get("espesor_explicito"):
        espesor = parsed.get("espesor", 1.5)
    elif ov.get("espesor_cuerpo_global"):
        espesor = float(ov["espesor_cuerpo_global"])
    else:
        espesor = parsed.get("espesor", 1.5)

    # Espesor tapa: por ítem > global override > igual que cuerpo
    if espesor_tapa_item is not None:
        espesor_tapa = float(espesor_tapa_item)
    elif ov.get("espesor_tapa_global"):
        espesor_tapa = float(ov["espesor_tapa_global"])
    else:
        espesor_tapa = espesor  # mismo que cuerpo por defecto

    valores = config.get("valores_defecto", {})
    ganancia = ov.get("ganancia_global") or valores.get("ganancia", "30")
    dolar = float(valores.get("dolar", 3.8))
    usd_kg_productos = float(valores.get("usd_kg_productos", 1.0))
    usd_kg_cajas = float(valores.get("usd_kg_cajas", 3.0))

    esp_str = f"{espesor:.1f}"
    esp_tapa_str = f"{espesor_tapa:.1f}"
    precios_key = "precios_go" if galvanizado == "GO" else "precios_gc"
    precios = valores.get(precios_key, {})

    fallback_pl = float(list(precios.values())[0]) if precios else 180.0
    precio_pl = float(precios.get(esp_str, fallback_pl))
    precio_pl_tapa = float(precios.get(esp_tapa_str, fallback_pl))

    factores = config.get("factores_ganancia", {}).get(ganancia, {})
    cfg = PricingConfig(
        tipo_galvanizado=galvanizado,
        dolar=dolar,
        precio_galvanizado_kg=usd_kg_productos,
        porcentaje_ganancia=ganancia,
        usd_kg_cajas=usd_kg_cajas,
        factores_ganancia=factores,
    )

    try:
        if tipo == "B":
            if len(dims) < 2:
                return None
            r = cotizar_bandeja(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                dims[0], dims[1], superficie, es_metro_lineal)

        elif tipo == "CH":
            if len(dims) < 2:
                return None
            r = cotizar_curva_horizontal(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                         dims[0], dims[1], superficie)

        elif tipo == "CVE":
            if len(dims) < 2:
                return None
            r = cotizar_curva_vertical(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                       dims[0], dims[1], "EXTERNA", superficie)

        elif tipo == "CVI":
            if len(dims) < 2:
                return None
            r = cotizar_curva_vertical(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                       dims[0], dims[1], "INTERNA", superficie)

        elif tipo == "T":
            # Inferencia para TEE con solo 2 dimensiones (ancho x alto):
            # "TEE ... DE 700X100MM" → tee cuadrada: derecha=izquierda=abajo=700, alto=100
            if len(dims) == 2:
                dims = [dims[0], dims[0], dims[0], dims[1]]
            if len(dims) < 4:
                return None
            r = cotizar_tee(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                            dims[0], dims[1], dims[2], dims[3], superficie)

        elif tipo == "C":
            if len(dims) < 2:
                return None
            r = cotizar_cruz(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                             dims[0], dims[1], superficie)

        elif tipo == "R":
            # Inferencia para REDUCCION con solo 2 dimensiones (ancho_mayor x ancho_menor):
            # "REDUCCION ... DE 700MM A 500MM" → alto=100mm por defecto
            if len(dims) == 2:
                dims = [dims[0], 100.0, dims[1]]
            if len(dims) < 3:
                return None
            r = cotizar_reduccion(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                  dims[0], dims[1], dims[2], superficie)

        elif tipo == "CP":
            if len(dims) < 3:
                return None
            r = cotizar_caja_pase(cfg, precio_pl, precio_pl_tapa, espesor, espesor_tapa,
                                  dims[0], dims[1], dims[2], knockout)

        else:
            return None

        cuerpo = (r[0]["precio_unitario"], r[0]["peso_unitario"], r[0]["descripcion"])
        # Tapa: solo si con_tapa=True, tipo != CP, y el motor retornó un segundo ítem
        tapa = None
        if con_tapa and tipo != "CP" and len(r) > 1:
            tapa = (r[1]["precio_unitario"], r[1]["peso_unitario"], r[1]["descripcion"])

        return {"cuerpo": cuerpo, "tapa": tapa}

    except Exception:
        return None


class _ImportarItemIn(BaseModel):
    descripcion: str
    unidad: str = "UND"
    cantidad: int = 1
    con_tapa: bool = False          # True → agregar tapa como ítem separado (texto libre)
    espesor_tapa: Optional[float] = None  # None → usar global o mismo que cuerpo


class _ImportarRequestIn(BaseModel):
    items: list[_ImportarItemIn]
    galvanizado_global: Optional[str] = None    # "GO" | "GC"
    espesor_cuerpo_global: Optional[float] = None  # 1.2 | 1.5 | 2.0
    espesor_tapa_global: Optional[float] = None    # 1.2 | 1.5 | 2.0
    ganancia_global: Optional[str] = None       # "30" | "35"
    superficie_global: Optional[str] = None     # "LISA" | "RANURADA" | "ESCALERILLA"
    tapa_modo: str = "junto"                    # "junto" | "separada"


@router.post("/importar/procesar")
async def importar_procesar(
    body: _ImportarRequestIn,
    usuario: dict = Depends(require_login),
):
    """Analiza una lista de ítems y devuelve precios calculados aplicando parámetros globales."""
    config = cargar_config()
    overrides = {
        "galvanizado_global": body.galvanizado_global,
        "espesor_cuerpo_global": body.espesor_cuerpo_global,
        "espesor_tapa_global": body.espesor_tapa_global,
        "ganancia_global": body.ganancia_global,
        "superficie_global": body.superficie_global,
    }
    ganancia_efectiva = body.ganancia_global or config.get("valores_defecto", {}).get("ganancia", "30")
    results = []
    for item in body.items:
        parsed = parsear_descripcion(item.descripcion)
        es_ml = item.unidad == "ML" and parsed.get("tipo") == "B"
        # Todos los tipos que el motor cotiza con tapa incluyen la tapa en el precio del modal.
        # "C/Tapa: Junto" combina cuerpo+tapa en una línea; "Separada" genera dos líneas.
        tipo_soporta_tapa = parsed.get("tipo") in ("B", "CH", "CVE", "CVI", "T", "C", "R")
        con_tapa_efectivo = tipo_soporta_tapa or item.con_tapa or parsed.get("con_tapa_desc", False)

        precio_data = calcular_precio_importado(
            parsed, config, overrides,
            con_tapa=con_tapa_efectivo,
            es_metro_lineal=es_ml,
            espesor_tapa_item=item.espesor_tapa,
        )

        # Galvanizado efectivo para mostrar en resultado
        if parsed.get("galvanizado_explicito"):
            galv_efectivo = parsed["galvanizado"]
        else:
            galv_efectivo = body.galvanizado_global or parsed["galvanizado"]

        if precio_data is not None:
            cuerpo = precio_data["cuerpo"]

            # Enriquecer descripción del cuerpo con espesor/knockout si no venían explícitos
            desc_final = item.descripcion
            if parsed["tipo"] is not None:
                if parsed.get("espesor_explicito"):
                    esp_efectivo = parsed["espesor"]
                elif body.espesor_cuerpo_global:
                    esp_efectivo = body.espesor_cuerpo_global
                else:
                    esp_efectivo = parsed["espesor"]
                espesor_str = f"{esp_efectivo:.1f}MM"
                falta_espesor = not parsed["espesor_explicito"]
                falta_knockout = parsed["tipo"] == "CP" and not parsed["knockout_explicito"]

                if falta_knockout and falta_espesor:
                    desc_final = item.descripcion.rstrip() + f" {parsed['knockout']} {espesor_str}"
                elif falta_knockout:
                    desc_final = item.descripcion.rstrip() + f" {parsed['knockout']}"
                elif falta_espesor:
                    desc_final = item.descripcion.rstrip() + f" {espesor_str}"

            tapa = precio_data.get("tapa")

            if tapa and body.tapa_modo == "junto":
                # Combinar cuerpo + tapa en un único ítem (precio y peso sumados)
                results.append({
                    "descripcion": desc_final,
                    "unidad": item.unidad,
                    "cantidad": item.cantidad,
                    "tipo": parsed["tipo"] or "MANUAL",
                    "precio_unitario":       round(cuerpo[0] + tapa[0], 4),
                    "peso_unitario":         round(cuerpo[1] + tapa[1], 6),
                    "descripcion_calculada": f"{cuerpo[2]} + {tapa[2]}",
                    "tipo_galvanizado":      galv_efectivo,
                    "porcentaje_ganancia":   ganancia_efectiva,
                    "reconocido": True,
                    "error": None,
                })
            else:
                # Ítem cuerpo
                results.append({
                    "descripcion": desc_final,
                    "unidad": item.unidad,
                    "cantidad": item.cantidad,
                    "tipo": parsed["tipo"] or "MANUAL",
                    "precio_unitario":       round(cuerpo[0], 4),
                    "peso_unitario":         round(cuerpo[1], 6),
                    "descripcion_calculada": cuerpo[2],
                    "tipo_galvanizado":      galv_efectivo,
                    "porcentaje_ganancia":   ganancia_efectiva,
                    "reconocido": True,
                    "error": None,
                })
                # Ítem tapa separado (si aplica)
                if tapa:
                    results.append({
                        "descripcion": tapa[2],
                        "unidad": item.unidad,
                        "cantidad": item.cantidad,
                        "tipo": parsed["tipo"],
                        "precio_unitario":       round(tapa[0], 4),
                        "peso_unitario":         round(tapa[1], 6),
                        "descripcion_calculada": tapa[2],
                        "tipo_galvanizado":      galv_efectivo,
                        "porcentaje_ganancia":   ganancia_efectiva,
                        "reconocido": True,
                        "error": None,
                    })
        else:
            # Intentar match contra catálogo de productos fijos
            cat_match = _buscar_en_catalogo(item.descripcion, ganancia_efectiva)
            if cat_match:
                results.append({
                    "descripcion": cat_match["descripcion"],
                    "unidad": item.unidad,
                    "cantidad": item.cantidad,
                    "tipo": "CATALOGO",
                    "precio_unitario":       round(cat_match["precio_catalogo"], 4),
                    "peso_unitario":         0,
                    "descripcion_calculada": cat_match["descripcion"],
                    "tipo_galvanizado":      "N/A",
                    "porcentaje_ganancia":   ganancia_efectiva,
                    "reconocido": True,
                    "error": None,
                    "es_catalogo": True,
                })
            else:
                results.append({
                    "descripcion": item.descripcion,
                    "unidad": item.unidad,
                    "cantidad": item.cantidad,
                    "tipo": "MANUAL",
                    "precio_unitario":       None,
                    "peso_unitario":         None,
                    "descripcion_calculada": None,
                    "tipo_galvanizado":      galv_efectivo,
                    "porcentaje_ganancia":   ganancia_efectiva,
                    "reconocido": False,
                    "error": "No se reconoció el tipo o las dimensiones",
                })

    return JSONResponse({"ok": True, "items": results})
