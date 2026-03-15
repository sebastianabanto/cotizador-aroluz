/**
 * importar.js — Modal "Importar tabla desde portapapeles" para el carrito.
 *
 * Flujo:
 *  1. abrirModalImportar() → muestra paso 1 (textarea)
 *  2. procesarTexto()      → parsea TSV → llama POST /api/carrito/importar/procesar
 *  3. renderPreview()      → muestra paso 2 con ✅ / 🔴 por ítem
 *  4. confirmarImportar()  → agrega todos al carrito → recarga
 */

'use strict';

// Resultados del backend (paso 2)
let _importarItems = [];

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
// 2. Parser TSV con auto-detección de encabezados
// ──────────────────────────────────────────────────────────────

function _parseTSV(text) {
  const rawLines = text.trim().split('\n');

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
    const desc = row[colDesc] || '';
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
  const text = document.getElementById('importar-paste').value.trim();
  if (!text) {
    toast('Pega primero una tabla', 'error');
    return;
  }

  const items = _parseTSV(text);
  if (!items.length) {
    toast('No se encontraron filas en la tabla', 'error');
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
      body: JSON.stringify(items),
    });
    data = await resp.json();
  } catch (err) {
    toast('Error de red al procesar la tabla', 'error');
    btn.disabled = false;
    btn.textContent = 'Procesar tabla';
    return;
  }

  btn.disabled = false;
  btn.textContent = 'Procesar tabla';

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
        fd.append('tipo',                item.tipo);
        fd.append('descripcion',         item.descripcion);
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
