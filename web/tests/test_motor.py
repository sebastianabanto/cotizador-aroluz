"""
test_motor.py — Suite de tests para web/motor.py

Cubre todas las funciones cotizar_* de AROLUZ Cotizador:
bandeja (B), curva horizontal (CH), curvas verticales (CVE/CVI),
tee (T), cruz (C), reducción (R) y caja de pase (CP).

Cómo correr:
    cd <raíz del proyecto>
    venv\\Scripts\\python.exe -m pytest web/tests/test_motor.py -v
"""
import math
import sys
import os
import pytest

# Asegurar que la raíz del proyecto esté en sys.path para poder importar web.motor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from web.motor import (
    PricingConfig,
    PL_MM2,
    calcular_peso,
    calcular_precio,
    aplicar_precio_escalerilla,
    aplicar_costo_galvanizado,
    calcular_precio_final,
    cotizar_bandeja,
    cotizar_curva_horizontal,
    cotizar_curva_vertical,
    cotizar_tee,
    cotizar_cruz,
    cotizar_reduccion,
    cotizar_caja_pase,
)


# ─────────────────────────────────────────────────────────────
# Fixtures de configuración de referencia
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def cfg_go():
    """PricingConfig estándar con galvanizado de origen (GO), ganancia 30%."""
    return PricingConfig(
        tipo_galvanizado="GO",
        dolar=3.8,
        precio_galvanizado_kg=2.5,
        porcentaje_ganancia="30",
    )


@pytest.fixture
def cfg_gc():
    """PricingConfig con galvanizado en caliente (GC), ganancia 30%."""
    return PricingConfig(
        tipo_galvanizado="GC",
        dolar=3.8,
        precio_galvanizado_kg=2.5,
        porcentaje_ganancia="30",
    )


@pytest.fixture
def cfg_go_35():
    """PricingConfig con galvanizado de origen (GO), ganancia 35%."""
    return PricingConfig(
        tipo_galvanizado="GO",
        dolar=3.8,
        precio_galvanizado_kg=2.5,
        porcentaje_ganancia="35",
    )


# Precios de plancha de referencia (S/) por espesor (mm)
PRECIO_1_2 = 280.0
PRECIO_1_5 = 340.0
PRECIO_2_0 = 450.0


# ─────────────────────────────────────────────────────────────
# Tests de funciones auxiliares puras
# ─────────────────────────────────────────────────────────────

class TestAuxiliares:

    def test_calcular_peso_formula_correcta(self):
        """calcular_peso usa densidad 0.00000785 kg/mm³."""
        area = 1_000_000  # mm²
        espesor = 1.5     # mm
        esperado = area * 0.00000785 * espesor
        assert calcular_peso(area, espesor) == pytest.approx(esperado)

    def test_calcular_precio_formula_correcta(self):
        """calcular_precio es área × precio_por_mm²."""
        area = 500_000
        pl_undmm2 = PRECIO_1_5 / PL_MM2
        esperado = area * pl_undmm2
        assert calcular_precio(area, pl_undmm2) == pytest.approx(esperado)

    def test_aplicar_precio_escalerilla_suma_10(self):
        """ESCALERILLA agrega exactamente S/10 al precio base."""
        precio_base = 100.0
        resultado = aplicar_precio_escalerilla(precio_base, "ESCALERILLA")
        assert resultado == pytest.approx(110.0)

    def test_aplicar_precio_lisa_sin_cambio(self):
        """LISA no modifica el precio base."""
        precio_base = 100.0
        assert aplicar_precio_escalerilla(precio_base, "LISA") == pytest.approx(precio_base)

    def test_aplicar_precio_ranurada_sin_cambio(self):
        """RANURADA no modifica el precio base."""
        precio_base = 100.0
        assert aplicar_precio_escalerilla(precio_base, "RANURADA") == pytest.approx(precio_base)

    def test_costo_galvanizado_go_es_cero(self, cfg_go):
        """GO no genera costo de galvanizado."""
        assert aplicar_costo_galvanizado(cfg_go, 100.0, 5.0) == pytest.approx(100.0)

    def test_costo_galvanizado_gc_mayor_que_go(self, cfg_go, cfg_gc):
        """GC genera un costo adicional, por lo que el precio resultante es mayor que GO."""
        precio_go = aplicar_costo_galvanizado(cfg_go, 100.0, 5.0)
        precio_gc = aplicar_costo_galvanizado(cfg_gc, 100.0, 5.0)
        assert precio_gc > precio_go

    def test_costo_galvanizado_gc_formula(self, cfg_gc):
        """GC: precio_base + (peso × dolar × precio_galv_kg / 0.95)."""
        precio_base = 50.0
        peso = 3.0
        costo_galv = peso * cfg_gc.dolar * cfg_gc.precio_galvanizado_kg / 0.95
        esperado = precio_base + costo_galv
        assert aplicar_costo_galvanizado(cfg_gc, precio_base, peso) == pytest.approx(esperado)

    def test_factor_ganancia_30_es_0_70(self, cfg_go):
        """Porcentaje ganancia '30' → factor 0.70."""
        assert cfg_go.factor_ganancia == pytest.approx(0.70)

    def test_factor_ganancia_35_es_0_65(self, cfg_go_35):
        """Porcentaje ganancia '35' → factor 0.65."""
        assert cfg_go_35.factor_ganancia == pytest.approx(0.65)

    def test_pl_mm2_constante(self):
        """Área estándar de plancha es 2400 × 1200 mm²."""
        assert PL_MM2 == 2400 * 1200


# ─────────────────────────────────────────────────────────────
# Tests de cotizar_bandeja
# ─────────────────────────────────────────────────────────────

class TestCotizarBandeja:

    def test_retorna_dos_items(self, cfg_go):
        """cotizar_bandeja devuelve exactamente 2 ítems: bandeja y tapa."""
        resultado = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)
        assert len(resultado) == 2

    def test_claves_presentes(self, cfg_go):
        """Cada ítem tiene las claves tipo, descripcion, precio_unitario, peso_unitario."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert {"tipo", "descripcion", "precio_unitario", "peso_unitario"} <= item.keys()

    def test_tipo_es_B(self, cfg_go):
        """El tipo del producto bandeja es 'B'."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["tipo"] == "B"

    def test_precio_soles_positivo(self, cfg_go):
        """El precio_unitario de la bandeja es un número positivo."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["precio_unitario"] > 0

    def test_peso_positivo(self, cfg_go):
        """El peso_unitario de la bandeja es un número positivo."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["peso_unitario"] > 0

    def test_precio_valor_exacto(self, cfg_go):
        """Precio bandeja 200×50×1.5mm GO LISA: valor calculado de referencia."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["precio_unitario"] == pytest.approx(126.488095, rel=1e-5)

    def test_peso_valor_exacto(self, cfg_go):
        """Peso bandeja 200×50×1.5mm GO LISA: valor calculado de referencia."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["peso_unitario"] == pytest.approx(8.83125, rel=1e-5)

    def test_descripcion_contiene_tipo_galvanizado_go(self, cfg_go):
        """La descripción de GO menciona 'GO'."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert "GO" in item["descripcion"]

    def test_descripcion_contiene_tipo_galvanizado_gc(self, cfg_gc):
        """La descripción de GC menciona 'GC'."""
        item = cotizar_bandeja(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert "GC" in item["descripcion"]

    def test_descripcion_contiene_bandeja(self, cfg_go):
        """La descripción menciona 'BANDEJA'."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert "BANDEJA" in item["descripcion"]

    def test_descripcion_escalerilla_en_texto(self, cfg_go):
        """Con ESCALERILLA, la descripción menciona 'ESCALERILLA'."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "ESCALERILLA")[0]
        assert "ESCALERILLA" in item["descripcion"]

    def test_descripcion_metro_lineal_en_texto(self, cfg_go):
        """Con es_metro_lineal=True, la descripción termina con '- POR ML'."""
        item = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, es_metro_lineal=True)[0]
        assert "POR ML" in item["descripcion"]

    def test_gc_mayor_que_go(self, cfg_go, cfg_gc):
        """GC incrementa el precio respecto a GO (mismo producto)."""
        precio_go = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        precio_gc = cotizar_bandeja(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        assert precio_gc > precio_go

    def test_ganancia_35_mayor_que_30(self, cfg_go, cfg_go_35):
        """Con ganancia '35', el precio final es mayor que con '30'."""
        precio_30 = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        precio_35 = cotizar_bandeja(cfg_go_35, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        assert precio_35 > precio_30

    def test_escalerilla_mayor_que_lisa(self, cfg_go):
        """ESCALERILLA produce precio mayor que LISA (mismo producto, +S/10 antes de ganancia)."""
        precio_lisa = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "LISA")[0]["precio_unitario"]
        precio_esc  = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "ESCALERILLA")[0]["precio_unitario"]
        assert precio_esc > precio_lisa

    def test_escalerilla_diferencia_exacta_sobre_lisa(self, cfg_go):
        """La diferencia de precio entre ESCALERILLA y LISA equivale a S/10 dividido por factor_ganancia."""
        precio_lisa = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "LISA")[0]["precio_unitario"]
        precio_esc  = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "ESCALERILLA")[0]["precio_unitario"]
        diferencia = precio_esc - precio_lisa
        # +S/10 al precio_base, luego dividido por factor_ganancia (0.70 para '30')
        esperado = 10.0 / cfg_go.factor_ganancia
        assert diferencia == pytest.approx(esperado, rel=1e-5)

    def test_metro_lineal_precio_es_precio_por_2_4(self, cfg_go):
        """El precio por metro lineal es el precio estándar dividido 2.4."""
        precio_std = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        precio_ml  = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, es_metro_lineal=True)[0]["precio_unitario"]
        assert precio_ml == pytest.approx(precio_std / 2.4, rel=1e-5)

    def test_tapa_tiene_tipo_B(self, cfg_go):
        """La tapa de la bandeja también tiene tipo 'B'."""
        tapa = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[1]
        assert tapa["tipo"] == "B"

    def test_tapa_descripcion_contiene_tapa_bandeja(self, cfg_go):
        """La descripción de la tapa menciona 'TAPA BANDEJA'."""
        tapa = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[1]
        assert "TAPA BANDEJA" in tapa["descripcion"]

    def test_dimensiones_minimas_no_lanza_excepcion(self, cfg_go):
        """Dimensiones muy pequeñas (ancho=10, alto=10) no lanzan excepción."""
        resultado = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 10, 10)
        assert resultado[0]["precio_unitario"] > 0


# ─────────────────────────────────────────────────────────────
# Tests de cotizar_curva_horizontal
# ─────────────────────────────────────────────────────────────

class TestCotizarCurvaHorizontal:

    def test_retorna_dos_items(self, cfg_go):
        """cotizar_curva_horizontal devuelve 2 ítems: curva y tapa."""
        resultado = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)
        assert len(resultado) == 2

    def test_tipo_es_CH(self, cfg_go):
        """El tipo de la curva horizontal es 'CH'."""
        item = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["tipo"] == "CH"

    def test_precio_valor_exacto(self, cfg_go):
        """Precio curva horizontal 200×50×1.5mm GO LISA: valor de referencia."""
        item = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["precio_unitario"] == pytest.approx(51.879431, rel=1e-5)

    def test_gc_mayor_que_go(self, cfg_go, cfg_gc):
        """GC produce precio mayor que GO en curva horizontal."""
        precio_go = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        precio_gc = cotizar_curva_horizontal(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        assert precio_gc > precio_go

    def test_escalerilla_mayor_que_lisa(self, cfg_go):
        """ESCALERILLA produce precio mayor que LISA en curva horizontal."""
        precio_lisa = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "LISA")[0]["precio_unitario"]
        precio_esc  = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "ESCALERILLA")[0]["precio_unitario"]
        assert precio_esc > precio_lisa

    def test_descripcion_contiene_curva_horizontal(self, cfg_go):
        """La descripción menciona 'CURVA HORIZONTAL'."""
        item = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert "CURVA HORIZONTAL" in item["descripcion"]

    def test_tapa_tiene_tipo_CH(self, cfg_go):
        """La tapa de la curva horizontal tiene tipo 'CH'."""
        tapa = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[1]
        assert tapa["tipo"] == "CH"

    def test_tapa_descripcion_contiene_tapa_curva(self, cfg_go):
        """La descripción de la tapa menciona 'TAPA CURVA HORIZONTAL'."""
        tapa = cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[1]
        assert "TAPA CURVA HORIZONTAL" in tapa["descripcion"]


# ─────────────────────────────────────────────────────────────
# Tests de cotizar_curva_vertical (CVE y CVI)
# ─────────────────────────────────────────────────────────────

class TestCotizarCurvaVertical:

    def test_tipo_cve_es_CVE(self, cfg_go):
        """Curva vertical EXTERNA tiene tipo 'CVE'."""
        item = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA")[0]
        assert item["tipo"] == "CVE"

    def test_tipo_cvi_es_CVI(self, cfg_go):
        """Curva vertical INTERNA tiene tipo 'CVI'."""
        item = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "INTERNA")[0]
        assert item["tipo"] == "CVI"

    def test_precio_cve_valor_exacto(self, cfg_go):
        """Precio CVE 200×50×1.5mm GO LISA: valor de referencia."""
        item = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA")[0]
        assert item["precio_unitario"] == pytest.approx(62.399107, rel=1e-5)

    def test_precio_cvi_valor_exacto(self, cfg_go):
        """Precio CVI 200×50×1.5mm GO LISA: valor de referencia."""
        item = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "INTERNA")[0]
        assert item["precio_unitario"] == pytest.approx(69.73373, rel=1e-5)

    def test_retorna_dos_items_cve(self, cfg_go):
        """cotizar_curva_vertical EXTERNA devuelve 2 ítems."""
        resultado = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA")
        assert len(resultado) == 2

    def test_retorna_dos_items_cvi(self, cfg_go):
        """cotizar_curva_vertical INTERNA devuelve 2 ítems."""
        resultado = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "INTERNA")
        assert len(resultado) == 2

    def test_gc_mayor_que_go_cve(self, cfg_go, cfg_gc):
        """GC produce precio mayor que GO en CVE."""
        precio_go = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA")[0]["precio_unitario"]
        precio_gc = cotizar_curva_vertical(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA")[0]["precio_unitario"]
        assert precio_gc > precio_go

    def test_gc_mayor_que_go_cvi(self, cfg_go, cfg_gc):
        """GC produce precio mayor que GO en CVI."""
        precio_go = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "INTERNA")[0]["precio_unitario"]
        precio_gc = cotizar_curva_vertical(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "INTERNA")[0]["precio_unitario"]
        assert precio_gc > precio_go

    def test_descripcion_cve_contiene_externa(self, cfg_go):
        """La descripción de CVE menciona 'EXTERNA'."""
        item = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA")[0]
        assert "EXTERNA" in item["descripcion"]

    def test_descripcion_cvi_contiene_interna(self, cfg_go):
        """La descripción de CVI menciona 'INTERNA'."""
        item = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "INTERNA")[0]
        assert "INTERNA" in item["descripcion"]

    def test_escalerilla_mayor_que_lisa_cve(self, cfg_go):
        """ESCALERILLA produce precio mayor que LISA en CVE."""
        precio_lisa = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA", "LISA")[0]["precio_unitario"]
        precio_esc  = cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA", "ESCALERILLA")[0]["precio_unitario"]
        assert precio_esc > precio_lisa


# ─────────────────────────────────────────────────────────────
# Tests de cotizar_tee
# ─────────────────────────────────────────────────────────────

class TestCotizarTee:

    def test_tipo_es_T(self, cfg_go):
        """El tipo de la tee es 'T'."""
        item = cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)[0]
        assert item["tipo"] == "T"

    def test_retorna_dos_items(self, cfg_go):
        """cotizar_tee devuelve 2 ítems: tee y tapa."""
        resultado = cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)
        assert len(resultado) == 2

    def test_precio_valor_exacto(self, cfg_go):
        """Precio tee 200×200×200×50mm GO LISA: valor de referencia."""
        item = cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)[0]
        assert item["precio_unitario"] == pytest.approx(78.182634, rel=1e-5)

    def test_gc_mayor_que_go(self, cfg_go, cfg_gc):
        """GC produce precio mayor que GO en tee."""
        precio_go = cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)[0]["precio_unitario"]
        precio_gc = cotizar_tee(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)[0]["precio_unitario"]
        assert precio_gc > precio_go

    def test_descripcion_contiene_tee(self, cfg_go):
        """La descripción menciona 'TEE'."""
        item = cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)[0]
        assert "TEE" in item["descripcion"]

    def test_tapa_descripcion_contiene_tapa_tee(self, cfg_go):
        """La descripción de la tapa menciona 'TAPA TEE'."""
        tapa = cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)[1]
        assert "TAPA TEE" in tapa["descripcion"]

    def test_escalerilla_mayor_que_lisa(self, cfg_go):
        """ESCALERILLA produce precio mayor que LISA en tee."""
        precio_lisa = cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50, "LISA")[0]["precio_unitario"]
        precio_esc  = cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50, "ESCALERILLA")[0]["precio_unitario"]
        assert precio_esc > precio_lisa


# ─────────────────────────────────────────────────────────────
# Tests de cotizar_cruz
# ─────────────────────────────────────────────────────────────

class TestCotizarCruz:

    def test_tipo_es_C(self, cfg_go):
        """El tipo de la cruz es 'C'."""
        item = cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["tipo"] == "C"

    def test_retorna_dos_items(self, cfg_go):
        """cotizar_cruz devuelve 2 ítems: cruz y tapa."""
        resultado = cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)
        assert len(resultado) == 2

    def test_precio_valor_exacto(self, cfg_go):
        """Precio cruz 200×50mm GO LISA: valor de referencia."""
        item = cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert item["precio_unitario"] == pytest.approx(115.889034, rel=1e-5)

    def test_gc_mayor_que_go(self, cfg_go, cfg_gc):
        """GC produce precio mayor que GO en cruz."""
        precio_go = cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        precio_gc = cotizar_cruz(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        assert precio_gc > precio_go

    def test_descripcion_contiene_cruz(self, cfg_go):
        """La descripción menciona 'CRUZ'."""
        item = cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]
        assert "CRUZ" in item["descripcion"]

    def test_tapa_descripcion_contiene_tapa_cruz(self, cfg_go):
        """La descripción de la tapa menciona 'TAPA CRUZ'."""
        tapa = cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[1]
        assert "TAPA CRUZ" in tapa["descripcion"]

    def test_escalerilla_mayor_que_lisa(self, cfg_go):
        """ESCALERILLA produce precio mayor que LISA en cruz."""
        precio_lisa = cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "LISA")[0]["precio_unitario"]
        precio_esc  = cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "ESCALERILLA")[0]["precio_unitario"]
        assert precio_esc > precio_lisa


# ─────────────────────────────────────────────────────────────
# Tests de cotizar_reduccion
# ─────────────────────────────────────────────────────────────

class TestCotizarReduccion:

    def test_tipo_es_R(self, cfg_go):
        """El tipo de la reducción es 'R'."""
        item = cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)[0]
        assert item["tipo"] == "R"

    def test_retorna_dos_items(self, cfg_go):
        """cotizar_reduccion devuelve 2 ítems: reducción y tapa."""
        resultado = cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)
        assert len(resultado) == 2

    def test_precio_valor_exacto(self, cfg_go):
        """Precio reducción 300→200×50mm GO LISA: valor de referencia."""
        item = cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)[0]
        assert item["precio_unitario"] == pytest.approx(36.379534, rel=1e-5)

    def test_gc_mayor_que_go(self, cfg_go, cfg_gc):
        """GC produce precio mayor que GO en reducción."""
        precio_go = cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)[0]["precio_unitario"]
        precio_gc = cotizar_reduccion(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)[0]["precio_unitario"]
        assert precio_gc > precio_go

    def test_descripcion_contiene_reduccion(self, cfg_go):
        """La descripción menciona 'REDUCCION'."""
        item = cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)[0]
        assert "REDUCCION" in item["descripcion"]

    def test_tapa_descripcion_contiene_tapa_reduccion(self, cfg_go):
        """La descripción de la tapa menciona 'TAPA REDUCCION'."""
        tapa = cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)[1]
        assert "TAPA REDUCCION" in tapa["descripcion"]

    def test_escalerilla_mayor_que_lisa(self, cfg_go):
        """ESCALERILLA produce precio mayor que LISA en reducción."""
        precio_lisa = cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200, "LISA")[0]["precio_unitario"]
        precio_esc  = cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200, "ESCALERILLA")[0]["precio_unitario"]
        assert precio_esc > precio_lisa


# ─────────────────────────────────────────────────────────────
# Tests de cotizar_caja_pase
# ─────────────────────────────────────────────────────────────

class TestCotizarCajaPase:

    def test_tipo_es_CP(self, cfg_go):
        """El tipo de la caja de pase es 'CP'."""
        item = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]
        assert item["tipo"] == "CP"

    def test_retorna_un_item(self, cfg_go):
        """cotizar_caja_pase devuelve exactamente 1 ítem (no lleva tapa separada)."""
        resultado = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")
        assert len(resultado) == 1

    def test_dimensiones_en_cm_convertidas_a_mm(self, cfg_go):
        """Las dimensiones se pasan en cm y se convierten a mm (×10) en la descripción."""
        item = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]
        # 20cm × 15cm × 10cm → 200mm × 150mm × 100mm en descripción
        assert "200X150X100MM" in item["descripcion"]

    def test_precio_go_valor_exacto(self, cfg_go):
        """Precio caja de pase 20×15×10cm GO CIEGA: valor de referencia."""
        item = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]
        assert item["precio_unitario"] == pytest.approx(34.76925, rel=1e-5)

    def test_precio_gc_valor_exacto(self, cfg_gc):
        """Precio caja de pase 20×15×10cm GC CIEGA: valor de referencia."""
        item = cotizar_caja_pase(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]
        assert item["precio_unitario"] == pytest.approx(55.576805, rel=1e-5)

    def test_gc_usa_3_usd_kg_por_defecto(self, cfg_gc):
        """GC en cajas de pase usa usd_kg_cajas=3.0 por defecto, ignorando precio_galvanizado_kg."""
        # cfg_gc tiene precio_galvanizado_kg=2.5; usd_kg_cajas por defecto es 3.0
        # Un config explícito con precio_galvanizado_kg=3.0 debe dar el mismo resultado
        cfg_gc_explicito = PricingConfig(
            tipo_galvanizado="GC",
            dolar=3.8,
            precio_galvanizado_kg=3.0,  # igual al usd_kg_cajas default
            porcentaje_ganancia="30",
        )
        precio_default  = cotizar_caja_pase(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]["precio_unitario"]
        precio_explicito = cotizar_caja_pase(cfg_gc_explicito, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]["precio_unitario"]
        assert precio_default == pytest.approx(precio_explicito, rel=1e-5)

    def test_gc_usd_kg_cajas_afecta_precio(self, cfg_gc):
        """Cambiar usd_kg_cajas en GC produce un precio diferente."""
        cfg_gc_alt = PricingConfig(
            tipo_galvanizado="GC",
            dolar=3.8,
            precio_galvanizado_kg=2.5,
            porcentaje_ganancia="30",
            usd_kg_cajas=2.5,  # distinto del default 3.0
        )
        precio_default = cotizar_caja_pase(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]["precio_unitario"]
        precio_alt     = cotizar_caja_pase(cfg_gc_alt, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]["precio_unitario"]
        assert precio_default != pytest.approx(precio_alt, rel=1e-3)

    def test_gc_mayor_que_go(self, cfg_go, cfg_gc):
        """GC produce precio mayor que GO en caja de pase."""
        precio_go = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]["precio_unitario"]
        precio_gc = cotizar_caja_pase(cfg_gc, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]["precio_unitario"]
        assert precio_gc > precio_go

    def test_descripcion_ciega(self, cfg_go):
        """Tipo de salida CIEGA aparece en la descripción."""
        item = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]
        assert "CIEGA" in item["descripcion"]

    def test_descripcion_con_salida_contiene_cs(self, cfg_go):
        """Tipo de salida diferente a CIEGA incluye 'C/S' en la descripción."""
        item = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "3/4")[0]
        assert "C/S" in item["descripcion"]

    def test_descripcion_contiene_caja_de_pase(self, cfg_go):
        """La descripción menciona 'CAJA DE PASE'."""
        item = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]
        assert "CAJA DE PASE" in item["descripcion"]

    def test_dimensiones_se_ordenan_mayor_a_menor(self, cfg_go):
        """Las dimensiones se ordenan de mayor a menor sin importar el orden de entrada."""
        # dim1=10, dim2=20, dim3=15 → debe ordenarse como 20×15×10 en la descripción
        item = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 10, 20, 15, "CIEGA")[0]
        assert "200X150X100MM" in item["descripcion"]

    def test_ganancia_35_mayor_que_30(self, cfg_go, cfg_go_35):
        """Con ganancia '35', el precio de caja de pase es mayor que con '30'."""
        precio_30 = cotizar_caja_pase(cfg_go,    PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]["precio_unitario"]
        precio_35 = cotizar_caja_pase(cfg_go_35, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")[0]["precio_unitario"]
        assert precio_35 > precio_30

    def test_dimensiones_minimas_no_lanza_excepcion(self, cfg_go):
        """Dimensiones mínimas (1cm × 1cm × 1cm) no lanzan excepción."""
        resultado = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 1, 1, 1, "CIEGA")
        assert resultado[0]["precio_unitario"] > 0


# ─────────────────────────────────────────────────────────────
# Tests transversales: GC vs GO para todos los tipos
# ─────────────────────────────────────────────────────────────

class TestGCvGOTransversal:
    """Verifica que GC produce precio mayor que GO en todos los tipos de producto."""

    @pytest.mark.parametrize("funcion,args", [
        (cotizar_bandeja,           (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)),
        (cotizar_curva_horizontal,  (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)),
        (cotizar_tee,               (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)),
        (cotizar_cruz,              (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)),
        (cotizar_reduccion,         (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)),
        (cotizar_caja_pase,         (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")),
    ])
    def test_gc_mayor_que_go(self, cfg_go, cfg_gc, funcion, args):
        """GC siempre produce precio mayor que GO para el mismo producto y dimensiones."""
        precio_go = funcion(cfg_go, *args)[0]["precio_unitario"]
        precio_gc = funcion(cfg_gc, *args)[0]["precio_unitario"]
        assert precio_gc > precio_go, f"Se esperaba GC > GO en {funcion.__name__}"


# ─────────────────────────────────────────────────────────────
# Tests transversales: ganancia 30 vs 35 para todos los tipos
# ─────────────────────────────────────────────────────────────

class TestGanancia35vs30Transversal:
    """Verifica que ganancia '35' produce precio mayor que '30' en todos los tipos."""

    @pytest.mark.parametrize("funcion,args", [
        (cotizar_bandeja,           (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)),
        (cotizar_curva_horizontal,  (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)),
        (cotizar_tee,               (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50)),
        (cotizar_cruz,              (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)),
        (cotizar_reduccion,         (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200)),
        (cotizar_caja_pase,         (PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA")),
    ])
    def test_ganancia_35_mayor_que_30(self, cfg_go, cfg_go_35, funcion, args):
        """Ganancia '35' siempre produce precio mayor que '30' para el mismo producto."""
        precio_30 = funcion(cfg_go,    *args)[0]["precio_unitario"]
        precio_35 = funcion(cfg_go_35, *args)[0]["precio_unitario"]
        assert precio_35 > precio_30, f"Se esperaba precio_35 > precio_30 en {funcion.__name__}"


# ─────────────────────────────────────────────────────────────
# Tests de valores borde
# ─────────────────────────────────────────────────────────────

class TestValoresBorde:

    def test_bandeja_dimensiones_muy_grandes(self, cfg_go):
        """Bandeja con dimensiones grandes (600×200mm) produce valores positivos finitos."""
        item = cotizar_bandeja(cfg_go, PRECIO_2_0, PRECIO_1_5, 2.0, 1.5, 600, 200)[0]
        assert item["precio_unitario"] > 0
        assert math.isfinite(item["precio_unitario"])

    def test_bandeja_precio_plancha_alto_aumenta_precio(self, cfg_go):
        """Precio de plancha más alto produce precio final mayor."""
        precio_bajo = cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50)[0]["precio_unitario"]
        precio_alto = cotizar_bandeja(cfg_go, PRECIO_2_0, PRECIO_1_5, 2.0, 1.5, 200, 50)[0]["precio_unitario"]
        assert precio_alto > precio_bajo

    def test_caja_pase_dimensiones_iguales(self, cfg_go):
        """Caja de pase con tres dimensiones iguales no lanza excepción."""
        resultado = cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 15, 15, 15, "CIEGA")
        assert resultado[0]["precio_unitario"] > 0

    def test_todas_las_funciones_devuelven_dicts_completos(self, cfg_go):
        """Todas las funciones cotizar_* devuelven al menos un ítem con las 4 claves requeridas."""
        claves_requeridas = {"tipo", "descripcion", "precio_unitario", "peso_unitario"}
        resultados = [
            cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50),
            cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50),
            cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA"),
            cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "INTERNA"),
            cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50),
            cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50),
            cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200),
            cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA"),
        ]
        for lista in resultados:
            for item in lista:
                assert claves_requeridas <= item.keys(), f"Faltan claves en {item}"

    def test_todas_las_funciones_devuelven_precios_positivos(self, cfg_go):
        """Todas las funciones cotizar_* devuelven precios positivos con valores válidos."""
        resultados = [
            cotizar_bandeja(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50),
            cotizar_curva_horizontal(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50),
            cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "EXTERNA"),
            cotizar_curva_vertical(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50, "INTERNA"),
            cotizar_tee(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 200, 200, 50),
            cotizar_cruz(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 200, 50),
            cotizar_reduccion(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 300, 50, 200),
            cotizar_caja_pase(cfg_go, PRECIO_1_5, PRECIO_1_2, 1.5, 1.2, 20, 15, 10, "CIEGA"),
        ]
        for lista in resultados:
            for item in lista:
                assert item["precio_unitario"] > 0, f"Precio no positivo: {item}"
                assert item["peso_unitario"] > 0, f"Peso no positivo: {item}"
