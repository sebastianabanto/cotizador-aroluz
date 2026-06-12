# -*- coding: utf-8 -*-
"""Extrae el bloque <script> inline grande de cada template a web/static/*.js
(fase 4c). Las expresiones Jinja quedan en un script inline corto via window.__X__."""
import re
from pathlib import Path

JOBS = [
    {
        "template": "web/templates/cotizacion/carrito.html",
        "js_out": "web/static/carrito.js",
        # (texto en el JS extraído) → (reemplazo)
        "js_subs": [
            ("const CLIENTES   = {{ catalogo.clientes  | tojson }};",
             "const CLIENTES   = window.__CLIENTES__;"),
            ("const ATENCIONES = {{ catalogo.atenciones | tojson }};",
             "const ATENCIONES = window.__ATENCIONES__;"),
            ("const DOLAR      = {{ dolar }};  // tipo de cambio S/ por USD",
             "const DOLAR      = window.__DOLAR__;  // tipo de cambio S/ por USD"),
            ("const carritoMap = new Map({{ carrito | tojson }}.map(i => [i.id, i]));",
             "const carritoMap = new Map(window.__CARRITO__.map(i => [i.id, i]));"),
        ],
        "inline": """<script>
window.__CLIENTES__   = {{ catalogo.clientes  | tojson }};
window.__ATENCIONES__ = {{ catalogo.atenciones | tojson }};
window.__DOLAR__      = {{ dolar }};
window.__CARRITO__    = {{ carrito | tojson }};
</script>
<script src="/static/carrito.js?v=31"></script>""",
    },
    {
        "template": "web/templates/cotizacion/historial.html",
        "js_out": "web/static/historial.js",
        "js_subs": [
            ("const ES_ADMIN = {{ es_admin | tojson }};",
             "const ES_ADMIN = window.__ES_ADMIN__;"),
        ],
        "inline": """<script>
window.__ES_ADMIN__ = {{ es_admin | tojson }};
</script>
<script src="/static/historial.js?v=31"></script>""",
    },
    {
        "template": "web/templates/cotizacion/cotizacion.html",
        "js_out": "web/static/cotizacion.js",
        "js_subs": [
            ("const PLANCHA_GO = { '1.2': {{ config.precios_go['1.2'] }}, '1.5': {{ config.precios_go['1.5'] }}, '2.0': {{ config.precios_go['2.0'] }} };",
             "const PLANCHA_GO = window.__PLANCHA_GO__;"),
            ("const PLANCHA_GC = { '1.2': {{ config.precios_gc['1.2'] }}, '1.5': {{ config.precios_gc['1.5'] }}, '2.0': {{ config.precios_gc['2.0'] }} };",
             "const PLANCHA_GC = window.__PLANCHA_GC__;"),
        ],
        "inline": """<script>
window.__PLANCHA_GO__ = { '1.2': {{ config.precios_go['1.2'] }}, '1.5': {{ config.precios_go['1.5'] }}, '2.0': {{ config.precios_go['2.0'] }} };
window.__PLANCHA_GC__ = { '1.2': {{ config.precios_gc['1.2'] }}, '1.5': {{ config.precios_gc['1.5'] }}, '2.0': {{ config.precios_gc['2.0'] }} };
</script>
<script src="/static/cotizacion.js?v=31"></script>""",
    },
]

PAT = re.compile(r"<script(?![^>]*src)[^>]*>\n?(.*?)</script>", re.S)

for job in JOBS:
    tpl = Path(job["template"])
    txt = tpl.read_text(encoding="utf-8")
    if job["js_out"].split("/")[-1] + "?v=" in txt:
        print(f"{tpl.name}: ya procesado, skip")
        continue
    blocks = PAT.findall(txt)
    big = max(blocks, key=len)  # el bloque grande de la página
    js = big
    for old, new in job["js_subs"]:
        if old not in js:
            raise SystemExit(f"NO ENCONTRADO en {job['js_out']}: {old[:60]}")
        js = js.replace(old, new)
    if "{{" in js or "{%" in js:
        rest = re.findall(r"\{\{.*?\}\}|\{%.*?%\}", js)
        raise SystemExit(f"Jinja restante en {job['js_out']}: {rest[:5]}")
    Path(job["js_out"]).write_text(js, encoding="utf-8", newline="\n")
    # reemplazar el bloque completo en el template
    full_block_pat = re.compile(r"<script(?![^>]*src)[^>]*>\n?" + re.escape(big) + r"</script>", re.S)
    txt2, n = full_block_pat.subn(job["inline"], txt)
    if n != 1:
        raise SystemExit(f"no se pudo reemplazar el bloque en {tpl}")
    tpl.write_text(txt2, encoding="utf-8", newline="\n")
    print(f"{tpl.name}: extraidas {big.count(chr(10))} lineas -> {job['js_out']}")
print("extract OK")
