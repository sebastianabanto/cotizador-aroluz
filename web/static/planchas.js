/**
 * planchas.js — Módulo de Planchas: Guillotine Packer + Canvas rendering
 *
 * Flujo:
 * 1. Usuario agrega piezas → renderPiecesList()
 * 2. Click "Calcular" → runPacker() → canvas inmediato + fetch precios
 * 3. Click "Agregar al Carrito" → agregarAlCarrito()
 */

'use strict';

// ─── Paleta de colores para piezas ───────────────────────────────────────────
const PALETTE = [
  '#5b8dee','#f9654a','#2ec4b6','#f4c542','#9b59b6',
  '#e91e8c','#27ae60','#e67e22','#1abc9c','#3498db',
  '#e74c3c','#f39c12','#16a085','#8e44ad','#2c3e50',
  '#d35400','#c0392b','#7f8c8d',
];

// ─── Estado global ────────────────────────────────────────────────────────────
let piezas = [];       // [{id, ancho, alto, cantidad, nombre, color}]
let nextId = 1;
let ultimoResumen = null;   // último resumen del /calcular (para agregar al carrito)
let tabActiva = 0;
let ultimasPlanchas = [];   // resultado de planchas para re-render de tabs

// ─── Helpers ─────────────────────────────────────────────────────────────────
function getPieceColor(idx) {
  return PALETTE[idx % PALETTE.length];
}

function fmtNum(n, dec = 2) {
  return Number(n).toLocaleString('es-PE', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ─── Gestión de piezas ───────────────────────────────────────────────────────
function addPiece() {
  const ancho = parseFloat(document.getElementById('inp-ancho').value);
  const alto = parseFloat(document.getElementById('inp-alto').value);
  const cant = parseInt(document.getElementById('inp-cant').value) || 1;
  const nombre = document.getElementById('inp-nombre').value.trim();

  if (!ancho || !alto || ancho <= 0 || alto <= 0) {
    showFieldError('inp-ancho', 'Dimensiones inválidas');
    return;
  }

  const color = getPieceColor(nextId - 1);
  const n = nombre || `${ancho}×${alto}`;
  piezas.push({ id: nextId++, ancho, alto, cantidad: cant, nombre: n, color });

  // Limpiar inputs
  document.getElementById('inp-ancho').value = '';
  document.getElementById('inp-alto').value = '';
  document.getElementById('inp-cant').value = '1';
  document.getElementById('inp-nombre').value = '';
  document.getElementById('inp-ancho').focus();

  renderPiecesList();
  clearResult();
}

function removePiece(id) {
  piezas = piezas.filter(p => p.id !== id);
  renderPiecesList();
  clearResult();
}

function showFieldError(inputId, msg) {
  const el = document.getElementById(inputId);
  if (!el) return;
  el.classList.add('error');
  setTimeout(() => el.classList.remove('error'), 1500);
}

function renderPiecesList() {
  const container = document.getElementById('piezas-lista');
  if (!container) return;

  if (piezas.length === 0) {
    container.innerHTML = '<p class="piezas-vacia">Sin piezas. Agregá al menos una.</p>';
    return;
  }

  container.innerHTML = piezas.map(p => `
    <div class="pieza-item">
      <span class="pieza-color" style="background:${p.color}"></span>
      <span class="pieza-nombre">${escHtml(p.nombre)}</span>
      <span class="pieza-dims">${p.ancho}×${p.alto}mm</span>
      <span class="pieza-qty">×${p.cantidad}</span>
      <button class="pieza-remove" onclick="removePiece(${p.id})" title="Eliminar">✕</button>
    </div>
  `).join('');
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── Algoritmo Guillotina (JS) ────────────────────────────────────────────────
function guillotinePack(binW, binH, items, spacing = 4) {
  // items: [{ancho, alto, nombre, color}] ya expandidos por cantidad

  // Ordenar por área descendente
  const sorted = [...items].sort((a, b) => (b.ancho * b.alto) - (a.ancho * a.alto));

  const noColocadas = [];
  const colocables = [];

  for (const item of sorted) {
    const w = item.ancho, h = item.alto, sp = spacing;
    const fN = (w + sp <= binW) && (h + sp <= binH);
    const fR = (h + sp <= binW) && (w + sp <= binH);
    if (fN || fR) colocables.push(item);
    else noColocadas.push(item);
  }

  function bssfScore(rect, ew, eh) {
    return Math.min(rect.w - ew, rect.h - eh);
  }

  function findBestRect(freeRects, pw, ph, sp) {
    let bestScore = Infinity, bestRect = null, bestRotated = false;
    for (const rect of freeRects) {
      const ew = pw + sp, eh = ph + sp;
      if (ew <= rect.w && eh <= rect.h) {
        const s = bssfScore(rect, ew, eh);
        if (s < bestScore) { bestScore = s; bestRect = rect; bestRotated = false; }
      }
      const ew2 = ph + sp, eh2 = pw + sp;
      if (ew2 <= rect.w && eh2 <= rect.h) {
        const s = bssfScore(rect, ew2, eh2);
        if (s < bestScore) { bestScore = s; bestRect = rect; bestRotated = true; }
      }
    }
    return { rect: bestRect, rotated: bestRotated };
  }

  function place(bin, rect, pw, ph, rotated, sp, item) {
    const placedW = rotated ? ph : pw;
    const placedH = rotated ? pw : ph;
    const ew = placedW + sp, eh = placedH + sp;

    bin.placed.push({
      x: rect.x, y: rect.y,
      ancho_colocado: placedW, alto_colocado: placedH,
      ancho_original: pw, alto_original: ph,
      rotada: rotated, nombre: item.nombre, color: item.color,
    });

    const rightW = rect.w - ew;
    const bottomH = rect.h - eh;
    const ri = bin.freeRects.indexOf(rect);
    bin.freeRects.splice(ri, 1);

    if (rightW >= bottomH) {
      if (rightW > 0) {
        bin.freeRects.push({ x: rect.x + ew, y: rect.y, w: rightW, h: rect.h });
        bin.cortes.push({ tipo: 'V', posicion: rect.x + ew, desde: rect.y, hasta: rect.y + rect.h });
      }
      if (bottomH > 0) {
        bin.freeRects.push({ x: rect.x, y: rect.y + eh, w: ew, h: bottomH });
        bin.cortes.push({ tipo: 'H', posicion: rect.y + eh, desde: rect.x, hasta: rect.x + ew });
      }
    } else {
      if (bottomH > 0) {
        bin.freeRects.push({ x: rect.x, y: rect.y + eh, w: rect.w, h: bottomH });
        bin.cortes.push({ tipo: 'H', posicion: rect.y + eh, desde: rect.x, hasta: rect.x + rect.w });
      }
      if (rightW > 0) {
        bin.freeRects.push({ x: rect.x + ew, y: rect.y, w: rightW, h: eh });
        bin.cortes.push({ tipo: 'V', posicion: rect.x + ew, desde: rect.y, hasta: rect.y + eh });
      }
    }
  }

  const bins = [];

  for (const item of colocables) {
    const pw = item.ancho, ph = item.alto;
    let placed = false;

    for (const bin of bins) {
      const { rect, rotated } = findBestRect(bin.freeRects, pw, ph, spacing);
      if (rect) { place(bin, rect, pw, ph, rotated, spacing, item); placed = true; break; }
    }

    if (!placed) {
      const bin = {
        freeRects: [{ x: 0, y: 0, w: binW, h: binH }],
        placed: [], cortes: [],
      };
      bins.push(bin);
      const { rect, rotated } = findBestRect(bin.freeRects, pw, ph, spacing);
      if (rect) place(bin, rect, pw, ph, rotated, spacing, item);
    }
  }

  return { bins, noColocadas };
}

// ─── Canvas rendering ─────────────────────────────────────────────────────────
function renderCanvas(canvasEl, binW, binH, piezasColocadas, cortes) {
  const ctx = canvasEl.getContext('2d');
  const wrap = canvasEl.parentElement;
  const maxW = Math.max(200, (wrap.clientWidth || 600) - 4);
  const maxH = 460;
  const scale = Math.min(maxW / binW, maxH / binH);

  canvasEl.width  = Math.round(binW * scale);
  canvasEl.height = Math.round(binH * scale);
  canvasEl.style.maxWidth = '100%';

  // Fondo plancha
  ctx.fillStyle = '#dde6f5';
  ctx.fillRect(0, 0, canvasEl.width, canvasEl.height);

  // Cuadrícula suave
  ctx.strokeStyle = 'rgba(180,200,230,0.4)';
  ctx.lineWidth = 0.5;
  const gridStep = 200 * scale;
  for (let x = gridStep; x < canvasEl.width; x += gridStep) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvasEl.height); ctx.stroke();
  }
  for (let y = gridStep; y < canvasEl.height; y += gridStep) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvasEl.width, y); ctx.stroke();
  }

  // Piezas
  for (const p of piezasColocadas) {
    const px = p.x * scale, py = p.y * scale;
    const pw = p.ancho_colocado * scale, ph = p.alto_colocado * scale;

    // Relleno
    ctx.fillStyle = hexToRgba(p.color, 0.72);
    ctx.fillRect(px, py, pw, ph);

    // Borde
    ctx.strokeStyle = p.color;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(px + 0.75, py + 0.75, pw - 1.5, ph - 1.5);

    // Labels: dimensiones + nombre opcional
    const minDim = Math.min(pw, ph);
    if (minDim > 22) {
      const fontSize = Math.max(9, Math.min(13, minDim * 0.18));
      const dimLabel = `${p.ancho_original}×${p.alto_original}`;
      const autoLabel = `${p.ancho_original}×${p.alto_original}`;
      const hasName = p.nombre && p.nombre !== autoLabel;

      ctx.fillStyle = 'rgba(20,30,60,0.85)';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const cx = px + pw / 2, cy = py + ph / 2;

      if (hasName) {
        // 2 líneas: dimensiones arriba, nombre abajo
        ctx.font = `600 ${fontSize}px Barlow, sans-serif`;
        ctx.fillText(dimLabel, cx, cy - fontSize * 0.75);
        ctx.font = `${Math.max(8, fontSize - 1)}px Barlow, sans-serif`;
        // Truncar nombre si no cabe
        let nombreMostrar = p.nombre;
        const maxW = pw - 6;
        while (ctx.measureText(nombreMostrar).width > maxW && nombreMostrar.length > 3) {
          nombreMostrar = nombreMostrar.slice(0, -1);
        }
        if (nombreMostrar !== p.nombre) nombreMostrar += '…';
        ctx.fillText(nombreMostrar, cx, cy + fontSize * 0.65);
        if (p.rotada) {
          ctx.font = `${fontSize - 2}px Barlow, sans-serif`;
          ctx.fillText('↺', cx, cy + fontSize * 1.8);
        }
      } else {
        ctx.font = `600 ${fontSize}px Barlow, sans-serif`;
        ctx.fillText(dimLabel, cx, cy - (p.rotada ? fontSize * 0.7 : 0));
        if (p.rotada) {
          ctx.font = `${fontSize - 1}px Barlow, sans-serif`;
          ctx.fillText('↺', cx, cy + fontSize * 0.8);
        }
      }
    }
  }

  // Cortes (líneas punteadas)
  for (const c of cortes) {
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1.2;
    if (c.tipo === 'H') {
      ctx.strokeStyle = 'rgba(22, 160, 133, 0.7)';
      ctx.beginPath();
      ctx.moveTo(c.desde * scale, c.posicion * scale);
      ctx.lineTo(c.hasta * scale, c.posicion * scale);
      ctx.stroke();
    } else {
      ctx.strokeStyle = 'rgba(211, 84, 0, 0.7)';
      ctx.beginPath();
      ctx.moveTo(c.posicion * scale, c.desde * scale);
      ctx.lineTo(c.posicion * scale, c.hasta * scale);
      ctx.stroke();
    }
  }
  ctx.setLineDash([]);

  // Borde exterior de la plancha
  ctx.strokeStyle = '#7b96c0';
  ctx.lineWidth = 2;
  ctx.strokeRect(1, 1, canvasEl.width - 2, canvasEl.height - 2);

  // Dimensiones plancha
  ctx.fillStyle = '#4a6080';
  ctx.font = '10px Barlow, sans-serif';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillText(`${binW}mm`, 4, 3);
}

// ─── Tabs de planchas ─────────────────────────────────────────────────────────
function renderTabs(planchas, binW, binH) {
  const canvasArea = document.getElementById('canvas-area');
  if (!canvasArea) return;

  if (planchas.length === 0) {
    canvasArea.innerHTML = '<p class="planchas-empty-msg">Sin resultados</p>';
    return;
  }

  if (planchas.length === 1) {
    // Sin tabs, solo el canvas
    canvasArea.innerHTML = '<canvas id="canvas-0" class="planchas-canvas"></canvas>';
    const cv = document.getElementById('canvas-0');
    renderCanvas(cv, binW, binH, planchas[0].placed, planchas[0].cortes);
    return;
  }

  // Múltiples planchas: tabs
  const tabHeaders = planchas.map((_, i) => `
    <button class="ptab-btn${i === tabActiva ? ' active' : ''}"
            onclick="setTab(${i})" type="button">
      Plancha ${i + 1}
    </button>
  `).join('');

  const canvases = planchas.map((_, i) =>
    `<canvas id="canvas-${i}" class="planchas-canvas${i !== tabActiva ? ' hidden' : ''}"></canvas>`
  ).join('');

  canvasArea.innerHTML = `
    <div class="planchas-tabs">${tabHeaders}</div>
    <div class="planchas-canvas-wrap">${canvases}</div>
  `;

  planchas.forEach((plancha, i) => {
    const cv = document.getElementById(`canvas-${i}`);
    if (cv) renderCanvas(cv, binW, binH, plancha.placed, plancha.cortes);
  });
}

function setTab(idx) {
  tabActiva = idx;
  document.querySelectorAll('.ptab-btn').forEach((btn, i) =>
    btn.classList.toggle('active', i === idx)
  );
  document.querySelectorAll('.planchas-canvas').forEach((cv, i) =>
    cv.classList.toggle('hidden', i !== idx)
  );
}

// ─── Estadísticas ─────────────────────────────────────────────────────────────
function renderStats(resumen) {
  const bar = document.getElementById('stats-bar');
  if (!bar) return;

  const util = Math.round(resumen.utilizacion_promedio * 100);
  bar.innerHTML = `
    <div class="stat-box">
      <span class="stat-val">${resumen.n_planchas}</span>
      <span class="stat-lbl">Plancha${resumen.n_planchas !== 1 ? 's' : ''}</span>
    </div>
    <div class="stat-box">
      <span class="stat-val">${resumen.total_colocadas}/${resumen.total_solicitadas}</span>
      <span class="stat-lbl">Piezas</span>
    </div>
    <div class="stat-box stat-util" data-util="${util}">
      <span class="stat-val">${util}%</span>
      <span class="stat-lbl">Utilización</span>
    </div>
    <div class="stat-box">
      <span class="stat-val">${fmtNum(resumen.desperdicio_m2)} m²</span>
      <span class="stat-lbl">Desperdicio</span>
    </div>
  `;
}

// ─── Lista de cortes ──────────────────────────────────────────────────────────
function renderCuts(planchas) {
  const el = document.getElementById('cortes-lista');
  if (!el) return;

  const allCortes = planchas.flatMap((pl, i) =>
    pl.cortes.map(c => ({ ...c, plancha_n: i + 1 }))
  );

  if (allCortes.length === 0) {
    el.innerHTML = '<p style="color:var(--texto-suave);font-size:.85rem">Sin cortes registrados.</p>';
    return;
  }

  el.innerHTML = allCortes.map(c => `
    <div class="corte-item corte-${c.tipo.toLowerCase()}">
      <span class="corte-tipo">${c.tipo}</span>
      <span class="corte-desc">
        Plancha ${c.plancha_n} —
        ${c.tipo === 'H'
          ? `y=${Math.round(c.posicion)}mm, x: ${Math.round(c.desde)}→${Math.round(c.hasta)}`
          : `x=${Math.round(c.posicion)}mm, y: ${Math.round(c.desde)}→${Math.round(c.hasta)}`
        }
      </span>
    </div>
  `).join('');
}

// ─── Precio box ───────────────────────────────────────────────────────────────
function renderPrecioBox(resumen) {
  const box = document.getElementById('precio-box');
  if (!box) return;

  box.innerHTML = `
    <div class="precio-box-grid">
      <div class="precio-linea">
        <span class="precio-label">Precio por plancha</span>
        <span class="precio-val">S/ ${fmtNum(resumen.precio_unitario_plancha)}</span>
      </div>
      <div class="precio-linea">
        <span class="precio-label">Peso por plancha</span>
        <span class="precio-val">${fmtNum(resumen.peso_unitario_plancha)} kg</span>
      </div>
      <div class="precio-linea precio-total-linea">
        <span class="precio-label">Total (${resumen.n_planchas} plancha${resumen.n_planchas !== 1 ? 's' : ''})</span>
        <span class="precio-val precio-total-val">S/ ${fmtNum(resumen.precio_total)}</span>
      </div>
      <div class="precio-linea">
        <span class="precio-label">Peso total</span>
        <span class="precio-val">${fmtNum(resumen.peso_total)} kg</span>
      </div>
    </div>
    <button class="btn-agregar-carrito" onclick="agregarAlCarrito()" type="button">
      Agregar al Carrito
    </button>
  `;
  box.classList.remove('hidden');
}

// ─── No colocadas ─────────────────────────────────────────────────────────────
function renderNoColocadas(noColocadas) {
  const el = document.getElementById('no-colocadas');
  if (!el) return;

  if (!noColocadas || noColocadas.length === 0) {
    el.innerHTML = '';
    el.classList.add('hidden');
    return;
  }

  el.innerHTML = `
    <div class="alert-warning">
      ⚠️ Las siguientes piezas no caben en una plancha ${getBinDims()} y no fueron incluidas:
      <ul>${noColocadas.map(p => `<li>${escHtml(p.nombre)} (${p.ancho}×${p.alto}mm)</li>`).join('')}</ul>
    </div>
  `;
  el.classList.remove('hidden');
}

function getBinDims() {
  const w = document.getElementById('inp-ancho-plancha')?.value || '2400';
  const h = document.getElementById('inp-alto-plancha')?.value || '1200';
  return `${w}×${h}mm`;
}


// ─── Limpiar resultado ────────────────────────────────────────────────────────
function clearResult() {
  ultimoResumen = null;
  const canvasArea = document.getElementById('canvas-area');
  if (canvasArea) canvasArea.innerHTML = '<p class="planchas-empty-msg">Ingresá las piezas y presioná Calcular.</p>';
  const statsBar = document.getElementById('stats-bar');
  if (statsBar) statsBar.innerHTML = '';
  const precioBox = document.getElementById('precio-box');
  if (precioBox) { precioBox.innerHTML = ''; precioBox.classList.add('hidden'); }
  const noColocadas = document.getElementById('no-colocadas');
  if (noColocadas) { noColocadas.innerHTML = ''; noColocadas.classList.add('hidden'); }
  const cortesLista = document.getElementById('cortes-lista');
  if (cortesLista) cortesLista.innerHTML = '';
}

// ─── Orquestador principal ────────────────────────────────────────────────────
function runPacker() {
  if (piezas.length === 0) {
    toast('Agregá al menos una pieza antes de calcular.', 'error');
    return;
  }

  const binW = parseFloat(document.getElementById('inp-ancho-plancha')?.value || 2400);
  const binH = parseFloat(document.getElementById('inp-alto-plancha')?.value || 1200);
  const spacing = parseFloat(document.getElementById('inp-espaciado')?.value || 4);
  const espesor = document.querySelector('input[name="espesor"]:checked')?.value || '1.5';
  const galv = document.querySelector('input[name="galvanizado"]:checked')?.value || 'GO';

  // Expandir piezas por cantidad para el packer JS
  const items = [];
  piezas.forEach(p => {
    for (let i = 0; i < p.cantidad; i++) {
      items.push({ ancho: p.ancho, alto: p.alto, nombre: p.nombre, color: p.color });
    }
  });

  // Ejecutar packer JS (preview inmediato)
  const { bins, noColocadas } = guillotinePack(binW, binH, items, spacing);
  tabActiva = 0;

  // Guardar para re-render de tabs
  ultimasPlanchas = bins.map(b => ({ placed: b.placed, cortes: b.cortes }));

  // Render canvas
  renderTabs(ultimasPlanchas, binW, binH);

  // Stats preliminares (sin precio)
  const areaTotal = binW * binH;
  const n = bins.length;
  const totalColocadas = bins.reduce((s, b) => s + b.placed.length, 0);
  const totalSolicitadas = piezas.reduce((s, p) => s + p.cantidad, 0);
  const utilizaciones = bins.map(b => {
    const usada = b.placed.reduce((s, p) => s + p.ancho_colocado * p.alto_colocado, 0);
    return usada / areaTotal;
  });
  const utilProm = n > 0 ? utilizaciones.reduce((s, u) => s + u, 0) / n : 0;
  const desperdicio = (areaTotal * n - bins.reduce((s, b) =>
    s + b.placed.reduce((ss, p) => ss + p.ancho_colocado * p.alto_colocado, 0), 0)
  ) / 1_000_000;

  renderStats({
    n_planchas: n,
    total_colocadas: totalColocadas,
    total_solicitadas: totalSolicitadas,
    utilizacion_promedio: utilProm,
    desperdicio_m2: desperdicio,
  });

  renderCuts(ultimasPlanchas.map((pl, i) => ({ ...pl, idx: i })));
  renderNoColocadas(noColocadas);

  // Ocultar precio box mientras carga
  const precioBox = document.getElementById('precio-box');
  if (precioBox) {
    precioBox.innerHTML = '<div class="precio-loading">Calculando precio…</div>';
    precioBox.classList.remove('hidden');
  }

  // Fetch precio al servidor
  fetch('/api/planchas/calcular', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ancho_plancha: binW,
      alto_plancha: binH,
      espaciado: spacing,
      espesor,
      tipo_galvanizado: galv,
      piezas: piezas.map(p => ({
        ancho: p.ancho, alto: p.alto, cantidad: p.cantidad,
        nombre: p.nombre, color: p.color,
      })),
    }),
  })
  .then(r => r.json())
  .then(data => {
    if (!data.ok) {
      toast(data.error || 'Error al calcular precio', 'error');
      if (precioBox) precioBox.innerHTML = '';
      return;
    }
    ultimoResumen = data.resumen;
    renderStats(data.resumen);
    renderPrecioBox(data.resumen);

    // Re-render canvas con datos del servidor (por consistencia)
    const serverBins = data.planchas.map(pl => ({
      placed: pl.piezas,
      cortes: pl.cortes,
    }));
    ultimasPlanchas = serverBins;
    tabActiva = 0;
    renderTabs(ultimasPlanchas, binW, binH);
    renderCuts(data.planchas.map(pl => ({ ...pl, idx: pl.idx })));
  })
  .catch(err => {
    console.error(err);
    toast('Error de conexión al calcular precio', 'error');
    if (precioBox) precioBox.innerHTML = '';
  });
}

// ─── Agregar al carrito ───────────────────────────────────────────────────────
function agregarAlCarrito() {
  if (!ultimoResumen) {
    toast('Calculá primero antes de agregar al carrito.', 'error');
    return;
  }

  const btn = document.querySelector('.btn-agregar-carrito');
  if (btn) { btn.disabled = true; btn.textContent = 'Agregando…'; }

  fetch('/api/planchas/agregar-carrito', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      n_planchas: ultimoResumen.n_planchas,
      espesor: ultimoResumen.espesor,
      tipo_galvanizado: ultimoResumen.tipo_galvanizado,
      ancho_plancha: ultimoResumen.ancho_plancha,
      alto_plancha: ultimoResumen.alto_plancha,
      total_colocadas: ultimoResumen.total_colocadas,
      total_solicitadas: ultimoResumen.total_solicitadas,
      utilizacion_promedio: ultimoResumen.utilizacion_promedio,
      descripcion_piezas: ultimoResumen.descripcion_piezas,
    }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      toast(data.mensaje || 'Planchas agregadas al carrito', 'success');
      actualizarBadgeCarrito();
    } else {
      toast(data.error || 'Error al agregar', 'error');
    }
  })
  .catch(() => toast('Error de conexión', 'error'))
  .finally(() => {
    if (btn) { btn.disabled = false; btn.textContent = 'Agregar al Carrito'; }
  });
}

// ─── Inicialización ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  renderPiecesList();

  // Enter en inputs de pieza → agregar
  ['inp-ancho', 'inp-alto', 'inp-cant', 'inp-nombre'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') addPiece(); });
  });
});
