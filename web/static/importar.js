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

// Ítems parseados del paso 1 (para poder re-procesar desde paso 2 sin volver)
let _ultimoItemsParsed = [];

// Parámetros globales configurados en el paso 0
let _importarConfig = {
  galvanizado_global: 'GO',
  ganancia_global: '30',
  espesor_cuerpo_global: 1.5,
  espesor_tapa_global: 1.5,
  superficie_global: 'RANURADA',
  tapa_modo: 'junto',
};

// Flags: el usuario eligió ACTIVAMENTE estos controles en la barra del paso 2.
// false = el radio está pre-seleccionado visualmente pero NO es un override activo.
// true  = el usuario hizo click → se aplica a todos los ítems.
let _p2SupOverride   = false;
let _p2EspTapaOverride = false;

// ── Encabezados reconocidos para auto-detección de columnas ──
const _HEADER_RE = {
  descripcion: /DESCRIP|DETALLE|PRODUCTO|ITEM|C[ÓO]DIGO|NOMBRE/i,
  unidad:      /\bUND\b|\bUNIDAD\b|\bUN\/ML\b|\bUN\b|\bU\.M\.\b|\bUM\b|\bMTS\b|\bMT\b/i,
  cantidad:    /CANT|QTY|\bN[°º]\b|N[°]|CANTIDAD|METRADO/i,
  precio:      /^P\.?\s*U\.?$|P[\s._]?UNIT|PRECIO[\s._]*U/i,
  // TOTAL se excluye adrede: en tablas de cotización TOTAL = precio total, no cantidad
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

function _leerConfigImportar() {
  const galv = document.querySelector('input[name="imp-galv"]:checked');
  const gan  = document.querySelector('input[name="imp-ganancia"]:checked');
  const espC = document.querySelector('input[name="imp-esp-cuerpo"]:checked');

  _importarConfig.galvanizado_global      = galv ? galv.value : 'GO';
  _importarConfig.ganancia_global         = gan  ? gan.value  : '30';
  _importarConfig.espesor_cuerpo_global   = espC ? parseFloat(espC.value) : 1.5;
  _importarConfig.espesor_tapa_global     = null;  // null → backend usa mismo espesor que cuerpo
  _importarConfig.superficie_global       = null;  // null → backend respeta la superficie de cada item
  const tapaModo = document.querySelector('input[name="imp-tapa-modo"]:checked');
  _importarConfig.tapa_modo              = tapaModo ? tapaModo.value : 'junto';
}

// Actualiza el estilo visual de los botones Sin/Con comisión
function _actualizarBotonesComision() {
  const lbl30 = document.getElementById('imp-lbl-30');
  const lbl35 = document.getElementById('imp-lbl-35');
  const val = document.querySelector('input[name="imp-ganancia"]:checked')?.value;
  if (!lbl30 || !lbl35) return;
  const BASE = 'display:flex; align-items:center; gap:6px; cursor:pointer; padding:0.3rem 0.75rem; border-radius:6px; font-size:0.82rem; font-weight:600; transition:all .15s;';
  if (val === '30') {
    lbl30.style.cssText = BASE + 'border:2px solid #1a6fad; background:#e8f0fb; color:#1a6fad;';
    lbl35.style.cssText = BASE + 'border:2px solid #d1d5db; background:#fff; color:#6b7280;';
  } else {
    lbl30.style.cssText = BASE + 'border:2px solid #d1d5db; background:#fff; color:#6b7280;';
    lbl35.style.cssText = BASE + 'border:2px solid #1a8a4a; background:#e8f5ee; color:#1a8a4a;';
  }
}

// Actualiza el estilo visual de los botones Calcular/Manual y el hint
function _actualizarBotonesModoPrecio() {
  const lblAroluz = document.getElementById('imp-lbl-aroluz');
  const lblManual = document.getElementById('imp-lbl-manual');
  const hint      = document.getElementById('imp-modo-precio-hint');
  const val = document.querySelector('input[name="imp-modo-precio"]:checked')?.value;
  if (!lblAroluz || !lblManual) return;
  const BASE = 'display:flex; align-items:center; gap:6px; cursor:pointer; padding:0.3rem 0.75rem; border-radius:6px; font-size:0.82rem; font-weight:600; transition:all .15s;';
  if (val === 'aroluz') {
    lblAroluz.style.cssText = BASE + 'border:2px solid #1a6fad; background:#e8f0fb; color:#1a6fad;';
    lblManual.style.cssText = BASE + 'border:2px solid #d1d5db; background:#fff; color:#6b7280;';
    if (hint) hint.style.display = 'none';
  } else {
    lblAroluz.style.cssText = BASE + 'border:2px solid #d1d5db; background:#fff; color:#6b7280;';
    lblManual.style.cssText = BASE + 'border:2px solid #7c3aed; background:#f5f0ff; color:#7c3aed;';
    if (hint) hint.style.display = '';
  }
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

      // ── Excepción: línea con formato tabla "descripción  UND  cantidad" ──
      // Ej: "TUBO CONDUIT EMT 3/4" X 3 M    UND    100"
      //     "CURVA CONDUIT EMT DE 1"    UND    50"
      const tablaM = _DUC_RE.exec(line);
      if (tablaM) {
        const desc = _normalizarDimensiones(tablaM[1].trim());
        const unidad = tablaM[2].toUpperCase().replace(/\.$/, '');
        const n = Math.round(parseFloat(tablaM[3].replace(',', '.')));
        if (desc && !isNaN(n) && n > 0) rows.push({ descripcion: desc, unidad, cantidad: n, con_tapa: false, espesor_tapa: null });
      }
      continue;
    }

    // ── Formato CANT → UND → DESC (ej: "12.00  MTS  BANDEJA...") ──
    // Cubre metrados externos donde la cantidad va primero con decimal
    const cudM = _CUD_RE.exec(line);
    if (cudM) {
      const cant = Math.round(parseFloat(cudM[1].replace(',', '.'))) || 1;
      let und = cudM[2].toUpperCase();
      if (und === 'MTS' || und === 'MT') und = 'ML';
      const hasCTapa = /\bC[/\\]?TAPA\b|\bCON\s+TAPA\b/i.test(cudM[3]);
      const d = _normalizarDimensiones(cudM[3].trim());
      if (d) rows.push({ descripcion: d, unidad: und, cantidad: cant, con_tapa: hasCTapa, espesor_tapa: null });
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
// 2b. Parser regex para tablas pegadas sin tabuladores
//     (copiadas de PDF, Word, web — espacios simples entre columnas)
// ──────────────────────────────────────────────────────────────

// Formato: N° + descripción + UND/ML/... + cantidad [+ precio unitario] [+ total]
// El grupo (.+) es greedy → backtracking fuerza a encontrar la ÚLTIMA keyword de unidad
const _REGEX_TABLE_LINE = /^\s*\d+\s+(.+)\s+(UND|ML|MTS|MT|M2|KG|JGO|GLB|PZA)\s+(\d+(?:[.,]\d+)?)(?:\s+[\d.,]+)*\s*$/i;

function _isRegexTableFormat(cleanLines) {
  const dataLines = cleanLines.filter(l => /^\s*\d/.test(l));
  if (dataLines.length < 1) return false;
  const matches = dataLines.filter(l => _REGEX_TABLE_LINE.test(l)).length;
  return matches / dataLines.length >= 0.6;
}

function _parseRegexTable(cleanLines) {
  const rows = [];
  for (const line of cleanLines) {
    const m = _REGEX_TABLE_LINE.exec(line);
    if (!m) continue;
    const desc = _normalizarDimensiones(m[1].trim());
    if (!desc) continue;
    const unidad   = m[2].toUpperCase();
    const cantidad = Math.round(parseFloat(m[3].replace(',', '.'))) || 1;
    rows.push({ descripcion: desc, unidad, cantidad });
  }
  return rows;
}

// ──────────────────────────────────────────────────────────────
// 2d. Parser para formato metrado/presupuesto externo
//     Estructura por ítem:
//       {código_largo} {inicio_descripción}
//       {continuación_descripción...}  (0 o más líneas)
//       {N°} {UND|ML} {cantidad.decimal} {precio} {dcto} {parcial}
//     Ítems sin línea de datos (sin código asignado) se ignoran.
// ──────────────────────────────────────────────────────────────

const _METRADO_DATA_RE = /^\s*\d{1,3}\s+(UND|ML|M2|KG|JGO|GLB|PZA)\s+(\d+[.,]\d+)/i;
const _METRADO_CODE_RE = /^\s*\d{6,}\s+(.*)/;

function _isMetradoFormat(lines) {
  const dataLines = lines.filter(l => _METRADO_DATA_RE.test(l));
  const codeLines = lines.filter(l => _METRADO_CODE_RE.test(l));
  return dataLines.length >= 1 && codeLines.length >= 1;
}

function _parseMetrado(lines) {
  const rows = [];
  const headerRe = /^Item\b|^C[oó]digo\b|^ITEM\b/i;
  let descParts = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (headerRe.test(trimmed)) continue;

    // Línea de datos: N° + UND/ML + cantidad decimal + precios
    const dataM = _METRADO_DATA_RE.exec(trimmed);
    if (dataM) {
      const unidad   = dataM[1].toUpperCase();
      const cantidad = Math.round(parseFloat(dataM[2].replace(',', '.'))) || 1;
      const desc     = _normalizarDimensiones(descParts.join(' ').trim());
      if (desc) rows.push({ descripcion: desc, unidad, cantidad });
      descParts = [];
      continue;
    }

    // Línea de código: inicia nueva descripción
    const codeM = _METRADO_CODE_RE.exec(trimmed);
    if (codeM) {
      descParts = codeM[1].trim() ? [codeM[1].trim()] : [];
      continue;
    }

    // Línea de continuación de descripción
    if (descParts.length > 0) {
      descParts.push(trimmed);
    }
    // Líneas huérfanas (tras línea de datos, antes del siguiente código) → se ignoran
  }

  return rows;
}

// ──────────────────────────────────────────────────────────────
// 2d. Parser CANT → UND → DESC  (ej: "12.00  MTS  BANDEJA...")
//     Formato típico de metrados externos: cantidad primero, unidad, descripción
// ──────────────────────────────────────────────────────────────

// Acepta separación por tab O por 1+ espacios entre los tres campos.
// El campo de cantidad puede ser entero ("1") o decimal ("12.00").
const _CUD_RE = /^(\d+(?:[.,]\d+)?)\s+(UND|ML|MTS|MT|M2|KG|JGO|GLB|PZA)\s+(.+)$/i;

function _isCantUndDescFormat(lines) {
  const dataLines = lines.filter(l => /^\d/.test(l));
  if (dataLines.length < 1) return false;
  const hits = dataLines.filter(l => _CUD_RE.test(l.trim()));
  return hits.length / dataLines.length >= 0.7;
}

function _parseCantUndDesc(lines) {
  const rows = [];
  for (const line of lines) {
    const m = _CUD_RE.exec(line.trim());
    if (!m) continue;
    const cantidad = Math.round(parseFloat(m[1].replace(',', '.'))) || 1;
    let unidad = m[2].toUpperCase();
    if (unidad === 'MTS' || unidad === 'MT') unidad = 'ML';
    const rawDesc = m[3].trim();
    const hasCTapa = /\bC[/\\]?TAPA\b|\bCON\s+TAPA\b/i.test(rawDesc);
    const desc = _normalizarDimensiones(rawDesc);
    if (desc) rows.push({ descripcion: desc, unidad, cantidad, con_tapa: hasCTapa, espesor_tapa: null });
  }
  return rows;
}

// ──────────────────────────────────────────────────────────────
// 2e. Parser DESC + UND + CANT  (listas de Word/PDF con 1+ espacios)
//     Ej: "TUBO CONDUIT EMT 3/4   UND   20"
// ──────────────────────────────────────────────────────────────

// ── Patrón: DESCRIPCION + espacio(s) + UND[.]|ML|... + espacio(s) + CANTIDAD ──
// Cubre listas pegadas desde Word/PDF con 1 o más espacios entre columnas.
// El punto opcional (\.?) acepta variantes como "und." o "UND."
const _DUC_RE = /^(.+?)\s+(UND|ML|MTS|MT|M2|KG|JGO|GLB|PZA)\.?\s+(\d+(?:[.,]\d+)?)\s*$/i;

function _isDescUndCantFormat(lines) {
  const nonEmpty = lines.filter(l => l.trim());
  if (nonEmpty.length < 1) return false;
  const hits = nonEmpty.filter(l => _DUC_RE.test(l.trim()));
  return hits.length / nonEmpty.length >= 0.6;
}

function _parseDescUndCant(lines) {
  const rows = [];
  for (const line of lines) {
    const m = _DUC_RE.exec(line.trim());
    if (!m) continue;
    const desc = _normalizarDimensiones(m[1].trim());
    if (!desc) continue;
    let unidad = m[2].toUpperCase().replace(/\.$/, '');
    if (unidad === 'MTS' || unidad === 'MT') unidad = 'ML';
    const n = Math.round(parseFloat(m[3].replace(',', '.')));
    if (isNaN(n) || n <= 0) continue;
    rows.push({ descripcion: desc, unidad, cantidad: n });
  }
  return rows;
}

// ──────────────────────────────────────────────────────────────
// 2c. Parser TSV con auto-detección de encabezados
// ──────────────────────────────────────────────────────────────

function _parseTSV(text) {
  const rawLines = text.trim().split('\n');

  const cleanLines = rawLines.map(l => l.trim()).filter(l => l.length > 0);

  // ── DESC · UND · CANT (con 1+ espacio, líneas sin dígito inicial) ──
  if (_isDescUndCantFormat(cleanLines)) {
    return _parseDescUndCant(cleanLines);
  }

  // ── Detectar formato CANT → UND → DESC antes que nada ──
  if (_isCantUndDescFormat(cleanLines)) {
    return _parseCantUndDesc(cleanLines);
  }

  // ── Detectar formato metrado/presupuesto externo primero ──
  if (_isMetradoFormat(cleanLines)) {
    return _parseMetrado(cleanLines);
  }

  // ── Detectar formato multi-línea ──
  if (_isMultiLineFormat(cleanLines)) {
    return _parseMultiLine(cleanLines);
  }

  // Auto-detectar separador: si alguna línea tiene tab → TSV (Excel/Sheets)
  // Si no hay tabs → intentar regex (tablas PDF/web) antes de 2+ espacios
  const hasTabs = rawLines.some(l => l.includes('\t'));

  // ── Regex-based: tablas PDF/web con espacios simples ──
  if (!hasTabs && _isRegexTableFormat(cleanLines)) {
    return _parseRegexTable(cleanLines);
  }
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
  let colDesc = 0, colUnd = -1, colCant = -1, colPrecio = -1;
  let headerMatches = 0;

  for (let c = 0; c < firstRow.length; c++) {
    const cell = firstRow[c];
    if (_HEADER_RE.descripcion.test(cell)) { colDesc = c; headerMatches++; }
    if (_HEADER_RE.unidad.test(cell))      { colUnd  = c; headerMatches++; }
    if (_HEADER_RE.cantidad.test(cell))    { colCant = c; headerMatches++; }
    if (_HEADER_RE.precio.test(cell))      { colPrecio = c; }
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
    } else if (firstRow.length >= 4 && _isIntCol(0) && _isIntCol(1)) {
      // Formato de 4+ columnas: [nº item, cantidad, unidad, descripción]
      // Col 0 son números de ítem (1,2,3...) — los descartamos como colDesc
      colDesc = firstRow.length - 1; // descripción en la última columna
      colCant = 1;
      colUnd  = 2;
    } else if (firstRow.length >= 4 && _isIntCol(0) && !_isIntCol(1)) {
      // Formato: [N°ítem, descripción, unidad?, cantidad, precio?, total?]
      // (típico al copiar una tabla de cotización completa)
      colDesc = 1;
      // Buscar desde col 2: primera columna no-entera = unidad, primera entera después = cantidad
      let foundUnit = false;
      for (let c = 2; c < firstRow.length; c++) {
        if (!foundUnit && !_isIntCol(c)) { colUnd = c; foundUnit = true; }
        else if (foundUnit && colCant === -1 && _isIntCol(c)) { colCant = c; break; }
      }
      // Fallback: si no hay columna de unidad, la primera entera desde col2 = cantidad
      if (!foundUnit && _isIntCol(2)) colCant = 2;
    } else if (firstRow.length >= 3) {
      // Detectar formato CANT → UND → DESC (ej: "12.00  MTS  BANDEJA RANURADA...")
      // Condición: col0 es numérica en todas las filas Y col1 es una keyword de unidad
      const _UNIT_KW = /^(UND|ML|MTS|MT|M2|KG|JGO|GLB|PZA)$/i;
      const col1IsUnit = lines.slice(startRow).some(r => _UNIT_KW.test((r[1] || '').trim()));
      if (_isIntCol(0) && col1IsUnit) {
        colCant = 0;
        colUnd  = 1;
        colDesc = 2;
      } else {
        // Orden clásico: desc, und, cant
        colUnd  = _isIntCol(1) ? -1 : 1;
        colCant = _isIntCol(1) ? 1 : (_isIntCol(2) ? 2 : -1);
      }
    }
  }

  const rows = [];
  for (let i = startRow; i < lines.length; i++) {
    const row = lines[i];
    const desc = _normalizarDimensiones(row[colDesc] || '');
    if (!desc) continue;

    // Normalizar unidad
    let unidad = (colUnd >= 0 && row[colUnd]) ? row[colUnd].trim().toUpperCase() : 'UND';
    if (unidad === 'MTS' || unidad === 'MT') unidad = 'ML';
    if (unidad === 'PZA' || unidad === 'PIEZAS') unidad = 'UND';
    let cantidad = 1;
    if (colCant >= 0 && row[colCant]) {
      // Acepta "5", "5.00", "5,00" (Excel puede exportar con decimales)
      const n = Math.round(parseFloat((row[colCant] || '').replace(',', '.')));
      if (!isNaN(n) && n > 0) cantidad = n;
    }
    let precio_excel = null;
    if (colPrecio >= 0 && row[colPrecio]) {
      const p = parseFloat((row[colPrecio] || '').replace(',', '.'));
      if (!isNaN(p) && p > 0) precio_excel = p;
    }
    rows.push({ descripcion: desc, unidad: unidad || 'UND', cantidad, precio_excel });
  }

  // ── Safety check: si las descripciones son todas numéricas, la asignación
  //    de columnas fue incorrecta → intentar como CANT→UND→DESC ──
  if (rows.length > 0 && rows.every(r => /^\d+([.,]\d+)?$/.test(r.descripcion.trim()))) {
    const cudRows = _parseCantUndDesc(cleanLines);
    if (cudRows.length > 0) return cudRows;
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
    toast('Pega primero el contenido o escribe productos', 'error');
    return;
  }

  let items = _parseTSV(text);
  if (!items.length) items = _parseTextoLibre(text);
  if (!items.length) {
    toast('No se encontraron productos en el texto', 'error');
    return;
  }

  _ultimoItemsParsed = items;

  const modoPrecio = document.querySelector('input[name="imp-modo-precio"]:checked')?.value ?? 'aroluz';

  if (modoPrecio === 'manual') {
    // Modo manual: omitir backend, ir directo al preview con ítems manuales
    _importarItems = items.map(i => ({
      descripcion:           i.descripcion,
      unidad:                i.unidad,
      cantidad:              i.cantidad,
      reconocido:            false,
      tipo:                  'MANUAL',
      precio_unitario:       i.precio_excel ?? null,
      peso_unitario:         null,
      descripcion_calculada: null,
      tipo_galvanizado:      _importarConfig.galvanizado_global,
      porcentaje_ganancia:   _importarConfig.ganancia_global,
      error:                 null,
      es_manual_excel:       true,
    }));
    renderPreview(_importarItems);
    _sincronizarP2Opciones();
    document.getElementById('importar-paso1').style.display = 'none';
    document.getElementById('importar-paso2').style.display = '';
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
    btn.textContent = 'Procesar';
    return;
  }

  btn.disabled = false;
  btn.textContent = 'Procesar';

  if (!data.ok) {
    toast(data.error || 'Error al procesar', 'error');
    return;
  }

  _importarItems = data.items;
  renderPreview(_importarItems);
  _sincronizarP2Opciones();
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

  const tbody = document.getElementById('importar-preview-tbody');
  tbody.innerHTML = items.map((item, idx) => {
    const esCatalogo = !!item.es_catalogo;
    const tienePrecionManual = !item.reconocido && item.precio_unitario != null;
    const checkedByDefault = item.reconocido || tienePrecionManual;
    const icon = item.reconocido
      ? (esCatalogo ? '📦' : '✅')
      : (tienePrecionManual ? '📋' : '🔴');
    let precio, subtotal;
    if (item.reconocido) {
      precio   = `S/ ${Number(item.precio_unitario).toFixed(2)}`;
      subtotal = `<strong>S/ ${(Number(item.precio_unitario) * item.cantidad).toFixed(2)}</strong>`;
    } else if (tienePrecionManual) {
      precio   = `<span style="color:#7c3aed; font-size:0.85rem;">S/ ${Number(item.precio_unitario).toFixed(2)}</span>`;
      subtotal = `<strong style="color:#7c3aed;">S/ ${(Number(item.precio_unitario) * item.cantidad).toFixed(2)}</strong>`;
    } else {
      precio   = '<span style="color:#c0392b; font-size:0.78rem;">sin precio</span>';
      subtotal = '—';
    }
    const descCorta = item.descripcion.length > 70
      ? item.descripcion.slice(0, 70) + '…'
      : item.descripcion;
    let itemCalc;
    if (esCatalogo) {
      itemCalc = `<span style="font-size:0.78rem; color:#1a8a4a; font-weight:600;">📦 Catálogo</span>`;
    } else if (item.descripcion_calculada) {
      itemCalc = `<span title="${item.descripcion_calculada.replace(/"/g, '&quot;')}" style="font-size:0.78rem; color:#2563eb;">${item.descripcion_calculada.length > 60 ? item.descripcion_calculada.slice(0, 60) + '…' : item.descripcion_calculada}</span>`;
    } else {
      itemCalc = '<span style="color:#aaa; font-size:0.78rem;">—</span>';
    }
    const rowStyle = checkedByDefault ? '' : 'opacity:0.45;';
    return `<tr class="importar-item ${item.reconocido ? 'ok' : 'error'}" style="${rowStyle}" data-idx="${idx}">
      <td style="padding:4px 6px; text-align:center;">
        <input type="checkbox" class="imp-chk-item" data-idx="${idx}"
               ${checkedByDefault ? 'checked' : ''}
               onchange="_onImportarChkChange()"
               style="cursor:pointer;">
      </td>
      <td style="padding:4px 6px;" title="${item.descripcion.replace(/"/g, '&quot;')}">${icon} ${descCorta}</td>
      <td style="padding:4px 6px; text-align:center;">${item.unidad}</td>
      <td style="padding:4px 6px; text-align:center;">${item.cantidad}</td>
      <td style="padding:4px 6px;">${itemCalc}</td>
      <td style="padding:4px 6px; text-align:right;">${precio}</td>
      <td style="padding:4px 6px; text-align:right;">${subtotal}</td>
    </tr>`;
  }).join('');

  // Mostrar botón "Excluir no reconocidos" solo si hay alguno sin reconocer
  const btnExcluir = document.getElementById('btn-excluir-no-reconocidos');
  if (btnExcluir) btnExcluir.style.display = err > 0 ? '' : 'none';

  // Sincronizar header checkbox
  const chkTodos = document.getElementById('imp-chk-todos');
  if (chkTodos) chkTodos.checked = true; // todos reconocidos marcados, pero los 🔴 estarán desmarcados

  _actualizarResumenSeleccion();
  _actualizarTotalesImportar();
}

function _actualizarTotalesImportar() {
  const checks = document.querySelectorAll('.imp-chk-item');
  let totalPrecio = 0, totalPeso = 0;
  checks.forEach(chk => {
    if (!chk.checked) return;
    const idx = parseInt(chk.dataset.idx, 10);
    const item = _importarItems[idx];
    if (!item || item.precio_unitario == null) return;
    totalPrecio += Number(item.precio_unitario) * item.cantidad;
    totalPeso   += Number(item.peso_unitario || 0) * item.cantidad;
  });
  const div = document.getElementById('importar-totales');
  if (!div) return;
  div.innerHTML = `
    <span style="font-weight:700; color:var(--texto);">TOTAL</span>
    <span style="font-weight:700; color:#1a6fad; font-size:1rem;">S/ ${totalPrecio.toFixed(2)}</span>
    <span style="color:var(--borde,#d1d5db);">│</span>
    <span style="color:var(--texto-secundario,#6b7280);">Peso total</span>
    <span style="font-weight:600; color:var(--texto);">${totalPeso.toFixed(2)} kg</span>`;
}

/** Actualiza el texto del resumen y el botón de confirmar según los checkboxes marcados. */
function _actualizarResumenSeleccion() {
  const total    = _importarItems.length;
  const ok       = _importarItems.filter(i => i.reconocido).length;
  const err      = total - ok;
  const checks   = document.querySelectorAll('.imp-chk-item');
  const seleccionados = Array.from(checks).filter(c => c.checked).length;

  const esModomanual = _importarItems.some(i => i.es_manual_excel);
  let resumenTxt;
  if (esModomanual) {
    const conPrecio = _importarItems.filter(i => i.precio_unitario != null).length;
    const sinPrecio = total - conPrecio;
    resumenTxt = `${total} ítem(s) importados como manuales`;
    if (conPrecio) resumenTxt += ` — ${conPrecio} con precio del Excel`;
    if (sinPrecio) resumenTxt += ` — ${sinPrecio} sin precio (completar en carrito)`;
  } else if (err > 0) {
    resumenTxt = `${total} ítem(s) — ${ok} reconocidos, ${err} no identificados`;
    if (seleccionados < total) resumenTxt += ` — ${seleccionados} seleccionados para agregar`;
  } else {
    resumenTxt = `${total} ítem(s) — todos con precio calculado`;
  }
  document.getElementById('importar-resumen').textContent = resumenTxt;

  const btnConfirmar = document.getElementById('btn-importar-confirmar');
  btnConfirmar.textContent = `Agregar ${seleccionados} ítem(s) al carrito`;
  btnConfirmar.disabled = seleccionados === 0;

  // Header checkbox: indeterminate si hay mezcla
  const chkTodos = document.getElementById('imp-chk-todos');
  if (chkTodos) {
    chkTodos.indeterminate = seleccionados > 0 && seleccionados < total;
    chkTodos.checked = seleccionados === total;
  }
}

function _onImportarChkChange() {
  // Actualizar opacidad de la fila
  document.querySelectorAll('.imp-chk-item').forEach(chk => {
    const fila = chk.closest('tr');
    if (fila) fila.style.opacity = chk.checked ? '' : '0.45';
  });
  _actualizarResumenSeleccion();
  _actualizarTotalesImportar();
}

/** Selecciona o deselecciona todos los ítems. */
function toggleTodosImportar(checked) {
  document.querySelectorAll('.imp-chk-item').forEach(chk => {
    chk.checked = checked;
    const fila = chk.closest('tr');
    if (fila) fila.style.opacity = checked ? '' : '0.45';
  });
  _actualizarResumenSeleccion();
  _actualizarTotalesImportar();
}

/** Desmarca (excluye) todos los ítems no reconocidos. */
function toggleNoReconocidos() {
  const checks = document.querySelectorAll('.imp-chk-item');
  // Determinar si hay alguno no reconocido marcado actualmente
  const hayMarcados = Array.from(checks).some((chk, idx) => chk.checked && !_importarItems[idx]?.reconocido);
  checks.forEach((chk, idx) => {
    if (!_importarItems[idx]?.reconocido) {
      chk.checked = !hayMarcados; // si había marcados → desmarcar; si no → marcar
      const fila = chk.closest('tr');
      if (fila) fila.style.opacity = chk.checked ? '' : '0.45';
    }
  });
  const btn = document.getElementById('btn-excluir-no-reconocidos');
  if (btn) btn.textContent = hayMarcados ? 'Incluir no reconocidos' : 'Excluir no reconocidos';
  _actualizarResumenSeleccion();
}

// ──────────────────────────────────────────────────────────────
// 5. Confirmar — agregar todos al carrito
// ──────────────────────────────────────────────────────────────

async function confirmarImportar() {
  if (!_importarItems.length) return;

  // Solo los ítems cuyo checkbox esté marcado
  const checks = document.querySelectorAll('.imp-chk-item');
  const itemsAgregar = _importarItems.filter((_, idx) => checks[idx]?.checked);
  if (!itemsAgregar.length) {
    toast('No hay ítems seleccionados para agregar', 'error');
    return;
  }

  const btn = document.getElementById('btn-importar-confirmar');
  btn.disabled = true;
  btn.textContent = 'Agregando…';

  let errores = 0;

  for (const item of itemsAgregar) {
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
        const fd = new FormData();
        fd.append('descripcion',     item.descripcion);
        fd.append('unidad',          item.unidad);
        fd.append('precio_unitario', item.precio_unitario ?? 0);
        fd.append('peso_unitario',   0);
        fd.append('cantidad',        item.cantidad);
        await fetch('/api/carrito/agregar_manual', { method: 'POST', body: fd });
      }
    } catch (_) {
      errores++;
    }
  }

  cerrarModalImportar();

  const totalAgregados = itemsAgregar.length - errores;
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

// ──────────────────────────────────────────────────────────────
// Sincronización en vivo paso 2
// ──────────────────────────────────────────────────────────────

/**
 * Sincroniza los radios del paso 2 con los valores actuales de _importarConfig.
 * Se llama justo antes de mostrar el paso 2.
 */
function _sincronizarP2Opciones() {
  // Resetear flags de override — los controles son solo visuales hasta que el usuario los toque
  _p2SupOverride     = false;
  _p2EspTapaOverride = false;

  const gan = document.querySelector(`input[name="p2-ganancia"][value="${_importarConfig.ganancia_global || '30'}"]`);
  if (gan) gan.checked = true;
  const galv = document.querySelector(`input[name="p2-galv"][value="${_importarConfig.galvanizado_global || 'GO'}"]`);
  if (galv) galv.checked = true;
  const espCVal = (_importarConfig.espesor_cuerpo_global || 1.5).toFixed(1);
  const espC = document.querySelector(`input[name="p2-esp-c"][value="${espCVal}"]`);
  if (espC) espC.checked = true;
  const espTVal = (_importarConfig.espesor_tapa_global || 1.5).toFixed(1);
  const espT = document.querySelector(`input[name="p2-esp-t"][value="${espTVal}"]`);
  if (espT) espT.checked = true;
  const sup = document.querySelector(`input[name="p2-sup"][value="${_importarConfig.superficie_global || 'RANURADA'}"]`);
  if (sup) sup.checked = true;
  const tapaModo = document.querySelector(`input[name="p2-tapa-modo"][value="${_importarConfig.tapa_modo || 'junto'}"]`);
  if (tapaModo) tapaModo.checked = true;
}

/**
 * Lee las opciones de la barra del paso 2, actualiza _importarConfig
 * y sincroniza los radios del paso 1.
 */
function _leerConfigP2() {
  const gan  = document.querySelector('input[name="p2-ganancia"]:checked');
  const galv = document.querySelector('input[name="p2-galv"]:checked');
  const espC = document.querySelector('input[name="p2-esp-c"]:checked');
  const espT = document.querySelector('input[name="p2-esp-t"]:checked');
  const sup  = document.querySelector('input[name="p2-sup"]:checked');

  _importarConfig.ganancia_global       = gan  ? gan.value  : '30';
  _importarConfig.galvanizado_global    = galv ? galv.value : 'GO';
  _importarConfig.espesor_cuerpo_global = espC ? parseFloat(espC.value) : 1.5;
  // Solo aplicar como override si el usuario los tocó activamente
  _importarConfig.espesor_tapa_global   = _p2EspTapaOverride ? (espT ? parseFloat(espT.value) : null) : null;
  _importarConfig.superficie_global     = _p2SupOverride     ? (sup  ? sup.value : null) : null;
  const tapaModoP2 = document.querySelector('input[name="p2-tapa-modo"]:checked');
  _importarConfig.tapa_modo             = tapaModoP2 ? tapaModoP2.value : 'junto';

  // Sincronizar también los radios del paso 1 para que sean consistentes al volver
  const p1gan = document.querySelector(`input[name="imp-ganancia"][value="${_importarConfig.ganancia_global}"]`);
  if (p1gan) { p1gan.checked = true; _actualizarBotonesComision(); }
  const p1galv = document.querySelector(`input[name="imp-galv"][value="${_importarConfig.galvanizado_global}"]`);
  if (p1galv) p1galv.checked = true;
  const p1espC = document.querySelector(`input[name="imp-esp-cuerpo"][value="${_importarConfig.espesor_cuerpo_global.toFixed(1)}"]`);
  if (p1espC) p1espC.checked = true;
}

/**
 * Llamado al cambiar cualquier opción en paso 1 (via onchange en los radios).
 * Si ya hay ítems procesados (_ultimoItemsParsed), re-procesa automáticamente
 * y muestra paso 2 con los precios actualizados. Si no, no hace nada.
 */
async function _autoReprocesar() {
  if (!_ultimoItemsParsed.length) return;
  // En modo manual no hay nada que recalcular en el backend
  const modoPrecio = document.querySelector('input[name="imp-modo-precio"]:checked')?.value ?? 'aroluz';
  if (modoPrecio === 'manual') return;
  _leerConfigImportar();
  _sincronizarP2Opciones();

  const btnConf = document.getElementById('btn-importar-confirmar');
  if (btnConf) { btnConf.disabled = true; btnConf.textContent = 'Actualizando…'; }

  let data;
  try {
    const resp = await fetch('/api/carrito/importar/procesar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: _ultimoItemsParsed, ..._importarConfig }),
    });
    data = await resp.json();
  } catch {
    if (btnConf) { btnConf.disabled = false; btnConf.textContent = `Agregar ${_importarItems.length} ítem(s) al carrito`; }
    return;
  }

  if (!data.ok) {
    if (btnConf) { btnConf.disabled = false; btnConf.textContent = `Agregar ${_importarItems.length} ítem(s) al carrito`; }
    return;
  }

  _importarItems = data.items;
  renderPreview(_importarItems);
  // Pasar automáticamente al paso 2 para mostrar el preview actualizado
  document.getElementById('importar-paso1').style.display = 'none';
  document.getElementById('importar-paso2').style.display = '';
}

/**
 * Llamado al cambiar cualquier opción en la barra del paso 2.
 * Re-llama al backend con los mismos ítems parseados y actualiza el preview.
 */
async function p2ActualizarPreview() {
  _leerConfigP2();
  if (!_ultimoItemsParsed.length) return;
  // En modo manual los precios no se recalculan con el backend
  if (_importarItems.some(i => i.es_manual_excel)) return;

  const btnConf = document.getElementById('btn-importar-confirmar');
  if (btnConf) { btnConf.disabled = true; btnConf.textContent = 'Actualizando…'; }

  let data;
  try {
    const resp = await fetch('/api/carrito/importar/procesar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: _ultimoItemsParsed, ..._importarConfig }),
    });
    data = await resp.json();
  } catch {
    toast('Error de red al actualizar precios', 'error');
    if (btnConf) { btnConf.disabled = false; btnConf.textContent = `Agregar ${_importarItems.length} ítem(s) al carrito`; }
    return;
  }

  if (!data.ok) {
    toast(data.error || 'Error al actualizar', 'error');
    if (btnConf) { btnConf.disabled = false; btnConf.textContent = `Agregar ${_importarItems.length} ítem(s) al carrito`; }
    return;
  }

  _importarItems = data.items;
  renderPreview(_importarItems);
}
