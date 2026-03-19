/**
 * importar.js — Modal "Importar productos" para el carrito.
 *
 * Flujo:
 *  1. abrirModalImportar() → muestra paso 1 directamente (texto libre activo)
 *  2. procesarTexto()      → lee opciones globales → parsea → llama POST /api/carrito/importar/procesar
 *  3. renderPreview()      → muestra paso 2 con ✅ / 🔴 por ítem
 *  4. confirmarImportar()  → agrega todos al carrito → recarga
 */

'use strict';

// Resultados del backend (paso 2)
let _importarItems = [];

// Modo activo en paso 1
let _importarModo = 'tabla'; // 'tabla' | 'libre'

// Parámetros globales configurados en el paso 0
let _importarConfig = {
  galvanizado_global: 'GO',
  ganancia_global: '30',
  espesor_cuerpo_global: 1.5,
  espesor_tapa_global: 1.2,
  superficie_global: 'LISA',
};

// ── Encabezados reconocidos para auto-detección de columnas ──
const _HEADER_RE = {
  descripcion: /DESCRIP|DETALLE|PRODUCTO|ITEM|C[ÓO]DIGO|NOMBRE/i,
  unidad:      /\bUND\b|\bUNIDAD\b|\bUN\b|\bU\.M\.\b|\bUM\b/i,
  cantidad:    /CANT|QTY|\bN[°º]\b|N[°]|CANTIDAD|METRADO|\bTOTAL\b/i,
};

// ──────────────────────────────────────────────────────────────
// 1. Abrir / cerrar modal
// ──────────────────────────────────────────────────────────────

function abrirModalImportar() {
  irPaso1();
  document.getElementById('importar-paste').value = '';
  _importarItems = [];
  document.getElementById('modal-importar').style.display = 'flex';
  setModoImportar('libre');
  setTimeout(() => document.getElementById('importar-paste').focus(), 50);
}

function cerrarModalImportar() {
  document.getElementById('modal-importar').style.display = 'none';
  document.getElementById('importar-paste').value = '';
  _importarItems = [];
}

function irPaso1() {
  document.getElementById('importar-paso1').style.display = '';
  document.getElementById('importar-paso2').style.display = 'none';
}

function _leerConfigImportar() {
  const galv = document.querySelector('input[name="imp-galv"]:checked');
  const gan  = document.querySelector('input[name="imp-ganancia"]:checked');
  const espC = document.querySelector('input[name="imp-esp-cuerpo"]:checked');
  const espT = document.querySelector('input[name="imp-esp-tapa"]:checked');
  const sup  = document.querySelector('input[name="imp-superficie"]:checked');

  _importarConfig.galvanizado_global      = galv ? galv.value : 'GO';
  _importarConfig.ganancia_global         = gan  ? gan.value  : '30';
  _importarConfig.espesor_cuerpo_global   = espC ? parseFloat(espC.value) : 1.5;
  // Libre: espesor tapa null → backend usa mismo espesor que cuerpo por defecto
  _importarConfig.espesor_tapa_global     = _importarModo === 'libre' ? null : (espT ? parseFloat(espT.value) : 1.2);
  // Libre: superficie null → backend usa RANURADA por defecto; per-ítem overrides desde desc
  _importarConfig.superficie_global       = _importarModo === 'libre' ? null : (sup ? sup.value  : 'LISA');
}

// Cerrar al hacer click en el overlay
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('modal-importar');
  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === this) cerrarModalImportar();
    });
  }
});

// ──────────────────────────────────────────────────────────────
// Cambiar modo del paso 1 (tabla / libre)
// ──────────────────────────────────────────────────────────────

function setModoImportar(modo) {
  _importarModo = modo;

  const btnTabla    = document.getElementById('btn-modo-tabla');
  const btnLibre    = document.getElementById('btn-modo-libre');
  const ayudaTabla  = document.getElementById('imp-ayuda-tabla');
  const ayudaLibre  = document.getElementById('imp-ayuda-libre');
  const textarea    = document.getElementById('importar-paste');
  const btnProcesar = document.getElementById('btn-importar-procesar');

  if (!btnTabla) return; // paso1 aún no está en DOM

  // Estilos de tab: activo vs inactivo (se aplican directo para evitar conflicto con inline styles)
  const _estiloActivo   = 'color:#2563eb; border-bottom:2px solid #2563eb; font-weight:600; margin-bottom:-2px;';
  const _estiloInactivo = 'color:#6b7280; border-bottom:2px solid transparent; font-weight:normal; margin-bottom:-2px;';
  const _base = 'padding:0.4rem 1rem; font-size:0.85rem; border:none; background:none; cursor:pointer; ';

  if (modo === 'tabla') {
    btnTabla.setAttribute('style', _base + _estiloActivo);
    btnLibre.setAttribute('style', _base + _estiloInactivo);
    ayudaTabla.style.display = 'block';
    ayudaLibre.style.display = 'none';
    textarea.placeholder = 'Pega aquí la tabla (Tab entre columnas)…';
    btnProcesar.textContent = 'Procesar tabla';
  } else {
    btnTabla.setAttribute('style', _base + _estiloInactivo);
    btnLibre.setAttribute('style', _base + _estiloActivo);
    ayudaTabla.style.display = 'none';
    ayudaLibre.style.display = 'block';
    textarea.placeholder = 'Escribe un producto por línea:\n5 und bandeja 500x100mm 1.5mm ct\n10 ml bandeja esc 400x100mm 1.5mm ct 1.2mm\n3 und bandeja lisa 300x100mm st\n8 und gc curva horizontal 300x100mm 1.5mm\n2 und curva vertical 400x100mm 1.2mm\n4 und tee 300x300x300x100mm\n6 und reduccion 600x400x100mm\n10 und caja de pase 50x30x10\n56 und caja 300x300x100mm 3/4\n# SIN COMISIÓN – GO (línea de config, se ignora como ítem)';
    btnProcesar.textContent = 'Procesar texto';
  }
}

// ──────────────────────────────────────────────────────────────
// Parser texto libre: una línea por producto
// Formato: N und/ml [tipo] [dims] [espesor] [ct [esp_tapa]|st] [gc|go] [superficie]
// ──────────────────────────────────────────────────────────────

function _parseTextoLibre(text) {
  const rows = [];

  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;

    // ── Líneas de configuración global (no empiezan con dígito) ──
    if (!/^\d/.test(line)) {
      if (/\bsin\s+comisi[oó]n\b/i.test(line)) _importarConfig.ganancia_global = '30';
      if (/\bcon\s+comisi[oó]n\b/i.test(line)) _importarConfig.ganancia_global = '35';
      // GO/GC al final o suelto (ej: "SIN COMISIÓN – GO", "GC")
      const galvH = /\b(GO|GC)\s*$/i.exec(line);
      if (galvH) _importarConfig.galvanizado_global = galvH[1].toUpperCase();
      continue;
    }

    // ── Parsear cantidad y unidad ──
    let cantidad = 1, unidad = 'UND', desc;
    // "N und/ml desc"
    const mFmt = /^(\d+)\s+(und?s?|unidad(?:es)?|ml)\b\s*(.*)/i.exec(line);
    if (mFmt) {
      const n = parseInt(mFmt[1], 10);
      if (n > 0 && n <= 9999) {
        cantidad = n;
        unidad = /^ml$/i.test(mFmt[2]) ? 'ML' : 'UND';
        desc = mFmt[3].trim();
      } else {
        desc = line;
      }
    } else {
      // Fallback: "N desc" (sin und/ml)
      const mSimple = /^(\d+)(?:\s+|[x×.,;-]\s+)(.+)$/i.exec(line);
      if (mSimple) {
        const n = parseInt(mSimple[1], 10);
        if (n > 0 && n <= 9999) { cantidad = n; desc = mSimple[2].trim(); }
        else desc = line;
      } else {
        desc = line;
      }
    }

    // ── Parsear con/sin tapa ──
    let con_tapa = true;
    let espesor_tapa = null;

    // "sin tapa" o "st" → sin tapa
    if (/\b(sin\s+tapa|st)\b/i.test(desc)) {
      con_tapa = false;
      desc = desc.replace(/\b(sin\s+tapa|st)\b/gi, ' ');
    } else {
      // "ct 1.5mm" → tapa con espesor específico
      const ctEsp = /\bct\s+(\d+[.,]\d+)\s*mm\b/i.exec(desc);
      if (ctEsp) {
        espesor_tapa = parseFloat(ctEsp[1].replace(',', '.'));
        desc = desc.replace(ctEsp[0], ' ');
      } else {
        // "ct" solo → tapa al mismo espesor que el cuerpo (espesor_tapa=null → backend usa body)
        desc = desc.replace(/\bct\b/gi, ' ');
      }
    }

    // ── Normalizar abreviatura "esc" → "ESCALERILLA" ──
    desc = desc.replace(/\besc\b/gi, 'ESCALERILLA');

    // ── Curva vertical sin externa/interna → agregar EXTERNA por defecto ──
    if (/\bcurva\s+vertical\b/i.test(desc) && !/\b(extern[ao]|intern[ao]|cve|cvi)\b/i.test(desc)) {
      desc = desc.replace(/\bcurva\s+vertical\b/i, 'CURVA VERTICAL EXTERNA');
    }

    // ── Conversiones de unidades ──
    desc = desc.replace(/(\d+(?:[.,]\d+)?)\s*cm\b/gi, (_, v) =>
      String(Math.round(parseFloat(v.replace(',', '.')) * 10)));
    desc = desc.replace(/(\d+(?:[.,]\d+)?)\s*m\b(?!m)/gi, (_, v) =>
      String(Math.round(parseFloat(v.replace(',', '.')) * 1000)));

    desc = _normalizarDimensiones(desc);
    desc = desc.replace(/\s+/g, ' ').trim();

    if (desc) {
      rows.push({ descripcion: desc, unidad, cantidad, con_tapa, espesor_tapa });
    }
  }
  return rows;
}

// ──────────────────────────────────────────────────────────────
// 2a. Parser multi-línea: número / descripción / und / cantidad
//     (formato típico al pegar desde tablas Word / PDF / sistemas externos)
// ──────────────────────────────────────────────────────────────

function _isMultiLineFormat(lines) {
  // Necesita al menos 4 líneas (1 ítem completo)
  const numGroups = Math.floor(lines.length / 4);
  if (numGroups < 1) return false;
  // Verificar los primeros 3 grupos (o menos si hay pocos): línea 0,4,8... = entero positivo
  const check = Math.min(numGroups, 3);
  for (let g = 0; g < check; g++) {
    const i = g * 4;
    const numStr = lines[i].trim();
    const n = parseInt(numStr, 10);
    if (isNaN(n) || n <= 0 || String(n) !== numStr) return false;
    // línea i+3 = cantidad numérica
    const q = parseFloat(lines[i + 3].replace(',', '.'));
    if (isNaN(q) || q <= 0) return false;
  }
  return true;
}

function _parseMultiLine(lines) {
  const rows = [];
  for (let i = 0; i + 3 < lines.length; i += 4) {
    const desc     = _normalizarDimensiones(lines[i + 1].trim());
    const unidad   = (lines[i + 2].trim().toUpperCase()) || 'UND';
    const cantRaw  = lines[i + 3].replace(',', '.');
    const cantidad = Math.round(parseFloat(cantRaw)) || 1;
    if (desc) rows.push({ descripcion: desc, unidad, cantidad });
  }
  return rows;
}

// ── Normalizar dimensiones: en un patrón N x N x 0.XX, el tercer valor
//    < 1 no tiene sentido como milímetros → se multiplica x 100
//    Ej: "100 X 100 X 0.50" → "100 X 100 X 50"
//    Solo aplica a la tercera dimensión en patrones de 3 dimensiones (NxNxN).
function _normalizarDimensiones(desc) {
  // 1. NxNx0.X → NxNx(X*100)   ej: 100x100x0.50 → 100x100x50
  desc = desc.replace(
    /(\d+(?:[.,]\d+)?)\s*([xX])\s*(\d+(?:[.,]\d+)?)\s*([xX])\s*(0[.,]\d+)/g,
    (match, d1, x1, d2, x2, d3) => {
      const val = Math.round(parseFloat(d3.replace(',', '.')) * 100);
      return `${d1}${x1}${d2}${x2}${val}`;
    }
  );

  // 2. "troquelada/con troquel/con salida [para] [tubo] X" → "C/S X""
  //    Medidas válidas: 1/2, 3/4, 1  (exactas, nada más)
  //    Dos medidas combinadas → C/S MIXTO
  desc = desc.replace(
    /(troquelad[ao]|con\s+troquel|con\s+salida)\s*(?:para\s+)?(?:tubo\s+)?(1\/2|3\/4|1"?)(?:\s*[yY&,\-]\s*(1\/2|3\/4|1"?))?\s*"?/gi,
    (_, _kw, s1, s2) => s2 ? 'C/S MIXTO' : `C/S ${s1.replace('"', '')}"`
  );

  return desc;
}

// ──────────────────────────────────────────────────────────────
// 2b. Parser TSV con auto-detección de encabezados
// ──────────────────────────────────────────────────────────────

function _parseTSV(text) {
  const rawLines = text.trim().split('\n');

  // ── Detectar formato multi-línea primero ──
  const cleanLines = rawLines.map(l => l.trim()).filter(l => l.length > 0);
  if (_isMultiLineFormat(cleanLines)) {
    return _parseMultiLine(cleanLines);
  }

  // Auto-detectar separador: si alguna línea tiene tab → TSV (Excel/Sheets)
  // Si no hay tabs → columnas separadas por 2+ espacios (Word, PDF, sistema externo)
  const hasTabs = rawLines.some(l => l.includes('\t'));
  const _splitLine = hasTabs
    ? (l) => l.split('\t').map(c => c.trim().replace(/^["']|["']$/g, ''))
    : (l) => l.split(/\s{2,}/).map(c => c.trim().replace(/^["']|["']$/g, ''));

  const lines = rawLines
    .map(l => _splitLine(l))
    .filter(l => l.some(c => c));

  if (!lines.length) return [];

  // Intentar detectar encabezados en la primera fila
  // Requiere ≥2 columnas reconocidas para no confundir "UND" en datos con un header
  const firstRow = lines[0];
  let colDesc = 0, colUnd = -1, colCant = -1;
  let headerMatches = 0;

  for (let c = 0; c < firstRow.length; c++) {
    const cell = firstRow[c];
    if (_HEADER_RE.descripcion.test(cell)) { colDesc = c; headerMatches++; }
    if (_HEADER_RE.unidad.test(cell))      { colUnd  = c; headerMatches++; }
    if (_HEADER_RE.cantidad.test(cell))    { colCant = c; headerMatches++; }
  }
  const headersDetected = headerMatches >= 2;

  const startRow = headersDetected ? 1 : 0;

  // Fallback sin encabezados: intentar detectar columna de cantidad por contenido
  if (!headersDetected) {
    colDesc = 0;
    // Acepta enteros puros ("5") y decimales con valor entero ("5.00", "5,00") de Excel
    const _isNumericInt = (v) => {
      const n = parseFloat(v.replace(',', '.'));
      return !isNaN(n) && n > 0 && Math.round(n) === n;
    };
    const _isIntCol = (colIdx) => {
      const vals = lines.slice(startRow).map(r => (r[colIdx] || '').trim());
      const nonEmpty = vals.filter(v => v);
      if (!nonEmpty.length) return false;
      return nonEmpty.every(v => _isNumericInt(v));
    };
    if (firstRow.length === 2) {
      // Dos columnas: desc + (und o cant)
      if (_isIntCol(1)) {
        colUnd  = -1;
        colCant = 1;
      } else {
        colUnd  = 1;
        colCant = -1;
      }
    } else if (firstRow.length >= 3) {
      // Tres o más columnas: desc, und, cant (orden clásico)
      // Pero si col1 parece entero, puede ser cant y col2 und
      colUnd  = _isIntCol(1) ? -1 : 1;
      colCant = _isIntCol(1) ? 1 : (_isIntCol(2) ? 2 : -1);
    }
  }

  const rows = [];
  for (let i = startRow; i < lines.length; i++) {
    const row = lines[i];
    const desc = _normalizarDimensiones(row[colDesc] || '');
    if (!desc) continue;

    const unidad = (colUnd >= 0 && row[colUnd]) ? row[colUnd] : 'UND';
    let cantidad = 1;
    if (colCant >= 0 && row[colCant]) {
      // Acepta "5", "5.00", "5,00" (Excel puede exportar con decimales)
      const n = Math.round(parseFloat((row[colCant] || '').replace(',', '.')));
      if (!isNaN(n) && n > 0) cantidad = n;
    }
    rows.push({ descripcion: desc, unidad: unidad || 'UND', cantidad });
  }
  return rows;
}

// ──────────────────────────────────────────────────────────────
// 3. Procesar texto → llamar backend
// ──────────────────────────────────────────────────────────────

async function procesarTexto() {
  _leerConfigImportar();
  const text = document.getElementById('importar-paste').value.trim();
  if (!text) {
    toast(_importarModo === 'libre' ? 'Escribe al menos un producto' : 'Pega primero una tabla', 'error');
    return;
  }

  const items = _importarModo === 'libre' ? _parseTextoLibre(text) : _parseTSV(text);
  if (!items.length) {
    toast(_importarModo === 'libre' ? 'No se encontraron productos en el texto' : 'No se encontraron filas en la tabla', 'error');
    return;
  }

  const btn = document.getElementById('btn-importar-procesar');
  btn.disabled = true;
  btn.textContent = 'Procesando…';

  let data;
  try {
    const resp = await fetch('/api/carrito/importar/procesar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items, ..._importarConfig }),
    });
    data = await resp.json();
  } catch (err) {
    toast('Error de red al procesar', 'error');
    btn.disabled = false;
    btn.textContent = _importarModo === 'libre' ? 'Procesar texto' : 'Procesar tabla';
    return;
  }

  btn.disabled = false;
  btn.textContent = _importarModo === 'libre' ? 'Procesar texto' : 'Procesar tabla';

  if (!data.ok) {
    toast(data.error || 'Error al procesar', 'error');
    return;
  }

  _importarItems = data.items;
  renderPreview(_importarItems);
  document.getElementById('importar-paso1').style.display = 'none';
  document.getElementById('importar-paso2').style.display = '';
}

// ──────────────────────────────────────────────────────────────
// 4. Renderizar preview (paso 2)
// ──────────────────────────────────────────────────────────────

function renderPreview(items) {
  const total = items.length;
  const ok    = items.filter(i => i.reconocido).length;
  const err   = total - ok;

  const resumen = err > 0
    ? `${total} ítem(s) — ${ok} con precio calculado, ${err} sin precio (se agregarán como manuales con precio 0)`
    : `${total} ítem(s) — todos con precio calculado`;
  document.getElementById('importar-resumen').textContent = resumen;

  const tbody = document.getElementById('importar-preview-tbody');
  tbody.innerHTML = items.map(item => {
    const icon   = item.reconocido ? '✅' : '🔴';
    const precio = item.reconocido
      ? `S/ ${Number(item.precio_unitario).toFixed(2)}`
      : '<span style="color:#c0392b; font-size:0.78rem;">sin precio</span>';
    const descCorta = item.descripcion.length > 70
      ? item.descripcion.slice(0, 70) + '…'
      : item.descripcion;
    const itemCalc = item.descripcion_calculada
      ? `<span title="${item.descripcion_calculada.replace(/"/g, '&quot;')}" style="font-size:0.78rem; color:#2563eb;">${item.descripcion_calculada.length > 60 ? item.descripcion_calculada.slice(0, 60) + '…' : item.descripcion_calculada}</span>`
      : '<span style="color:#aaa; font-size:0.78rem;">—</span>';
    return `<tr class="importar-item ${item.reconocido ? 'ok' : 'error'}">
      <td style="padding:4px 6px;">${icon}</td>
      <td style="padding:4px 6px;" title="${item.descripcion.replace(/"/g, '&quot;')}">${descCorta}</td>
      <td style="padding:4px 6px; text-align:center;">${item.unidad}</td>
      <td style="padding:4px 6px; text-align:center;">${item.cantidad}</td>
      <td style="padding:4px 6px;">${itemCalc}</td>
      <td style="padding:4px 6px; text-align:right;">${precio}</td>
    </tr>`;
  }).join('');

  const btnConfirmar = document.getElementById('btn-importar-confirmar');
  btnConfirmar.textContent = `Agregar ${total} ítem(s) al carrito`;
  btnConfirmar.disabled = false;
}

// ──────────────────────────────────────────────────────────────
// 5. Confirmar — agregar todos al carrito
// ──────────────────────────────────────────────────────────────

async function confirmarImportar() {
  if (!_importarItems.length) return;

  const btn = document.getElementById('btn-importar-confirmar');
  btn.disabled = true;
  btn.textContent = 'Agregando…';

  let errores = 0;

  for (const item of _importarItems) {
    try {
      if (item.reconocido) {
        // Producto calculado → agregar con tipo y precio
        const fd = new FormData();
        // Usar descripcion_calculada (motor) como descripcion principal del ítem en carrito
        const descPrincipal = item.descripcion_calculada || item.descripcion;
        fd.append('tipo',                item.tipo);
        fd.append('descripcion',         descPrincipal);
        fd.append('precio_unitario',     item.precio_unitario);
        fd.append('peso_unitario',       item.peso_unitario || 0);
        fd.append('cantidad',            item.cantidad);
        fd.append('unidad',              item.unidad);
        fd.append('tipo_galvanizado',    item.tipo_galvanizado || 'GO');
        fd.append('porcentaje_ganancia', item.porcentaje_ganancia || '30');
        if (item.descripcion_calculada) fd.append('descripcion_calculada', item.descripcion_calculada);
        await fetch('/api/carrito/agregar', { method: 'POST', body: fd });
      } else {
        // No reconocido → agregar como manual con precio 0
        const fd = new FormData();
        fd.append('descripcion',     item.descripcion);
        fd.append('unidad',          item.unidad);
        fd.append('precio_unitario', 0);
        fd.append('peso_unitario',   0);
        fd.append('cantidad',        item.cantidad);
        await fetch('/api/carrito/agregar_manual', { method: 'POST', body: fd });
      }
    } catch (_) {
      errores++;
    }
  }

  cerrarModalImportar();

  const totalAgregados = _importarItems.length - errores;
  if (errores > 0) {
    toast(`${totalAgregados} ítem(s) agregados (${errores} con error de red)`, 'error');
  } else {
    toast(`${totalAgregados} ítem(s) agregados al carrito`, 'success');
  }

  setTimeout(() => {
    if (typeof _navegandoInternamente !== 'undefined') _navegandoInternamente = true;
    sessionStorage.setItem('_reloadProgramatico', '1');
    window.location.reload();
  }, 800);
}
