const ES_ADMIN = window.__ES_ADMIN__;

// ── Estado global ──
let todasCotizaciones     = [];
let cotizacionesFiltradas = [];
let normalesFiltradas     = [];
let importadasFiltradas   = [];
let paginaActual          = 1;
const POR_PAGINA          = 8;
let fetchDebounce         = null;
let _importadasAbiertas   = false;

// ── Fetch desde servidor (aplica filtros tipo + q) ──
async function fetchLista(isInitial) {
  const tipos = [...document.querySelectorAll('.fil-tipo:checked')].map(cb => cb.value);
  const galvs = [...document.querySelectorAll('.fil-galv:checked')].map(cb => cb.value);
  const gans  = [...document.querySelectorAll('.fil-gan:checked')].map(cb => cb.value);
  const q     = document.getElementById('fil-desc').value.trim();

  const params = new URLSearchParams();
  tipos.forEach(t => params.append('tipo', t));
  galvs.forEach(g => params.append('galvanizado', g));
  gans.forEach(g => params.append('ganancia', g));
  if (q) params.append('q', q);

  const url  = '/api/historial/lista' + (params.toString() ? '?' + params.toString() : '');
  const data = await apiFetch(url);

  if (isInitial) {
    document.getElementById('historial-loading').style.display = 'none';
    if (!data.ok || !data.cotizaciones.length) {
      document.getElementById('historial-vacio').style.display = 'block';
      return;
    }
    document.getElementById('historial-tabla').style.display = 'block';
    document.getElementById('filtros-bar').style.display     = 'flex';
  }

  todasCotizaciones = (data.ok && data.cotizaciones) ? data.cotizaciones : [];
  filtrarHistorial();
}

// ── Debounce para cambios que disparan re-fetch ──
function triggerFetch() {
  clearTimeout(fetchDebounce);
  fetchDebounce = setTimeout(() => fetchLista(false), 300);
}

// ── Carga inicial ──
async function cargarHistorial() {
  if (ES_ADMIN) {
    document.getElementById('th-usuario').style.display = '';
  }
  await fetchLista(true);
}

// ── Render de la página actual ──
function _buildFila(c) {
  const fecha = formatearFecha(c.fecha);
  const dolar_rate   = c.dolar_rate || 3.8;
  const esUSD        = c.moneda === 'DOLARES';
  const sym          = esUSD ? '$' : 'S/';
  const totalDisplay = esUSD
    ? (c.total_precio / dolar_rate).toFixed(2)
    : parseFloat(c.total_precio).toFixed(2);
  const badgePdf = c.origen === 'pdf_import'
    ? ' <span style="background:#e8751a;color:white;border-radius:4px;font-size:0.65rem;padding:1px 5px;vertical-align:middle;">PDF</span>'
    : '';
  const tr = document.createElement('tr');
  tr.id = `row-${c.id}`;
  tr.innerHTML = `
    <td style="text-align:center; padding:0 4px;">
      <input type="checkbox" class="row-check" data-id="${c.id}" onchange="actualizarSeleccion()">
    </td>
    <td data-label="#" style="color:var(--texto-suave);font-size:0.8rem;">${c.id}${badgePdf}</td>
    <td data-label="Fecha" style="font-size:0.8rem;">${fecha}</td>
    <td data-label="Cliente">${c.cliente || '<span style="color:var(--texto-suave);">—</span>'}</td>
    <td data-label="Proyecto" style="font-size:0.875rem;">${c.proyecto || '<span style="color:var(--texto-suave);">—</span>'}</td>
    ${ES_ADMIN ? `<td data-label="Usuario" style="font-size:0.8rem;color:var(--texto-suave);">${c.username || '—'}</td>` : ''}
    <td data-label="Items" style="text-align:center;font-size:0.875rem;">
      <span style="background:var(--azul-claro);color:white;border-radius:12px;padding:2px 8px;font-size:0.75rem;font-weight:600;">
        ${c.total_items || '?'}
      </span>
    </td>
    <td data-label="Total" class="td-num" style="font-weight:600;">${sym} ${totalDisplay}</td>
    <td data-label="Acciones" style="text-align:center;">
      <div style="display:flex;gap:4px;justify-content:center;flex-wrap:wrap;">
        <button class="btn btn-secondary btn-sm" onclick="verDetalle(${c.id})">Ver</button>
        <button class="btn btn-primary btn-sm" onclick="descargarPdf(${c.id})">PDF</button>
        <button class="btn btn-secondary btn-sm" onclick="duplicarCotizacion(${c.id})" title="Copiar ítems al carrito actual (sin reemplazar)">📋</button>
        <button class="btn btn-secondary btn-sm btn-edit" onclick="editarCotizacion(${c.id})" title="Editar — cargar al carrito">✏️</button>
        <button class="btn btn-danger btn-sm" onclick="eliminarCotizacion(${c.id})">✕</button>
      </div>
    </td>
  `;
  return tr;
}

function renderHistorial() {
  const tbody = document.getElementById('tbody-historial');
  tbody.innerHTML = '';
  const cols = ES_ADMIN ? 9 : 8;

  if (!normalesFiltradas.length && !importadasFiltradas.length) {
    tbody.innerHTML = `<tr><td colspan="${cols}" style="text-align:center; padding:2rem; color:var(--texto-suave);">No hay cotizaciones que coincidan con los filtros.</td></tr>`;
    renderPaginacion();
    return;
  }

  // Normales — paginadas
  const inicio = (paginaActual - 1) * POR_PAGINA;
  const pagina = normalesFiltradas.slice(inicio, inicio + POR_PAGINA);
  for (const c of pagina) {
    tbody.appendChild(_buildFila(c));
  }

  // Importadas — colapsadas al final (fuera de paginación)
  if (importadasFiltradas.length) {
    _importadasAbiertas = false;
    const headerTr = document.createElement('tr');
    headerTr.id = 'row-importadas-header';
    headerTr.style.cssText = 'cursor:pointer; background:var(--gris-fondo);';
    headerTr.onclick = toggleImportadas;
    headerTr.innerHTML = `<td colspan="${cols}" style="font-size:0.8rem; color:var(--texto-suave); padding:6px 8px; user-select:none;">
      <span id="import-arrow">▶</span> 📁 Importadas desde PDF (${importadasFiltradas.length})
    </td>`;
    tbody.appendChild(headerTr);
    for (const c of importadasFiltradas) {
      const tr = _buildFila(c);
      tr.classList.add('row-importada');
      tr.style.display = 'none';
      tbody.appendChild(tr);
    }
  }

  renderPaginacion();
  actualizarSeleccion();  // sincronizar batch-bar y checkbox "select all" al repintar
}

function toggleImportadas() {
  _importadasAbiertas = !_importadasAbiertas;
  document.querySelectorAll('.row-importada').forEach(tr => {
    tr.style.display = _importadasAbiertas ? '' : 'none';
  });
  const arrow = document.getElementById('import-arrow');
  if (arrow) arrow.textContent = _importadasAbiertas ? '▼' : '▶';
}

// ── Paginación ──
function renderPaginacion() {
  const totalPaginas = Math.ceil(normalesFiltradas.length / POR_PAGINA);
  const ctrl = document.getElementById('paginacion-ctrl');
  if (totalPaginas <= 1) { ctrl.style.display = 'none'; return; }
  ctrl.style.display = 'flex';
  document.getElementById('pag-info').textContent = `Página ${paginaActual} de ${totalPaginas}`;
  document.getElementById('btn-prev').disabled = paginaActual === 1;
  document.getElementById('btn-next').disabled = paginaActual === totalPaginas;
}

function cambiarPagina(delta) {
  const totalPaginas = Math.ceil(normalesFiltradas.length / POR_PAGINA);
  paginaActual = Math.max(1, Math.min(paginaActual + delta, totalPaginas));
  renderHistorial();
}

// ── Descargar PDF desde historial ──
function descargarPdf(id) {
  const a = document.createElement('a');
  a.href = `/api/historial/${id}/exportar/pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// ── Filtros ──
function filtrarHistorial() {
  const filCli    = document.getElementById('fil-cliente').value.trim().toLowerCase();
  const filProy   = document.getElementById('fil-proyecto').value.trim().toLowerCase();
  const filMonedas = [...document.querySelectorAll('.fil-moneda:checked')].map(cb => cb.value);

  cotizacionesFiltradas = todasCotizaciones.filter(c => {
    const fechDate = (c.fecha || '').slice(0, 10);
    const matchCli = !filCli
      || (c.cliente        || '').toLowerCase().includes(filCli)
      || (c.cliente_nombre || '').toLowerCase().includes(filCli)
      || (c.cliente_ruc    || '').toLowerCase().includes(filCli);
    return matchCli
        && (!filProy        || (c.proyecto || '').toLowerCase().includes(filProy))
        && (!calFechaInicio || fechDate >= calFechaInicio)
        && (!calFechaFin    || fechDate <= calFechaFin)
        && (!filMonedas.length || filMonedas.includes(c.moneda));
  });

  // Ordenar por id descendente
  cotizacionesFiltradas.sort((a, b) => b.id - a.id);

  // Separar normales e importadas
  normalesFiltradas   = cotizacionesFiltradas.filter(c => c.origen !== 'pdf_import');
  importadasFiltradas = cotizacionesFiltradas.filter(c => c.origen === 'pdf_import');

  paginaActual = 1;
  renderHistorial();
}

function limpiarFiltros() {
  document.getElementById('fil-cliente').value  = '';
  document.getElementById('fil-proyecto').value = '';
  document.getElementById('fil-desc').value     = '';
  document.querySelectorAll('.fil-tipo').forEach(cb => cb.checked = false);
  document.querySelectorAll('.fil-galv').forEach(cb => cb.checked = false);
  document.querySelectorAll('.fil-gan').forEach(cb => cb.checked = false);
  document.querySelectorAll('.fil-moneda').forEach(cb => cb.checked = false);
  calFechaInicio = null;
  calFechaFin    = null;
  actualizarBotonFecha();
  fetchLista(false);
}

// ── Multi-select (tabla principal) ──
function seleccionarTodosTabla(checked) {
  document.querySelectorAll('.row-check').forEach(cb => {
    const tr = cb.closest('tr');
    if (tr && tr.style.display === 'none') return;
    cb.checked = checked;
  });
  const sel = document.getElementById('th-sel-todas');
  if (sel) { sel.checked = checked; sel.indeterminate = false; }
  actualizarSeleccion();
}

function actualizarSeleccion() {
  const checks = document.querySelectorAll('.row-check:checked');
  const total  = document.querySelectorAll('.row-check').length;
  const n      = checks.length;
  const bar    = document.getElementById('batch-bar');
  if (n > 0) {
    bar.style.display = 'flex';
    document.getElementById('batch-count').textContent = `${n} seleccionada${n !== 1 ? 's' : ''}`;
  } else {
    bar.style.display = 'none';
  }
  // Botón Comparar: solo visible con exactamente 2 seleccionadas
  const btnCmp = document.getElementById('btn-batch-comparar');
  if (btnCmp) btnCmp.style.display = n === 2 ? '' : 'none';

  const sel = document.getElementById('th-sel-todas');
  if (sel) {
    sel.indeterminate = n > 0 && n < total;
    sel.checked = n > 0 && n === total;
  }
}

// ── Duplicar cotización (copiar ítems al carrito SIN reemplazarlo) ──
async function duplicarCotizacion(id) {
  const data = await apiFetch(`/api/historial/${id}`);
  if (!data.ok) { toast('Error al obtener la cotización', 'error'); return; }
  const items = data.cotizacion.items;
  let ok = 0;
  for (const item of items) {
    const fd = new FormData();
    fd.append('tipo',               item.tipo);
    fd.append('descripcion',        item.descripcion);
    fd.append('precio_unitario',    item.precio_unitario);
    fd.append('peso_unitario',      item.peso_unitario);
    fd.append('cantidad',           item.cantidad);
    fd.append('unidad',             item.unidad);
    fd.append('tipo_galvanizado',   item.tipo_galvanizado);
    fd.append('porcentaje_ganancia',item.porcentaje_ganancia);
    const res = await apiFetch('/api/carrito/agregar', {method: 'POST', body: fd});
    if (res && res.ok !== false) ok++;
  }
  const n = items.length;
  toast(`${ok} ítem${ok !== 1 ? 's' : ''} copiado${ok !== 1 ? 's' : ''} al carrito — <a href="/carrito" style="color:inherit;font-weight:600;">Ver carrito →</a>`,
        ok === n ? 'success' : 'warning');
}

// ── Exportar múltiples como ZIP de PDFs ──
async function exportarMultiplePdf() {
  const ids = [...document.querySelectorAll('.row-check:checked')].map(cb => cb.dataset.id);
  if (!ids.length) return;
  const btn = document.getElementById('btn-batch-pdf');
  btn.disabled = true;
  btn.textContent = 'Generando ZIP…';
  try {
    const fd = new FormData();
    fd.append('ids', ids.join(','));
    const resp = await fetch('/api/historial/exportar_multiple/pdf', {method: 'POST', body: fd});
    if (!resp.ok) throw new Error('Error del servidor');
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `cotizaciones_${new Date().toISOString().slice(0, 10)}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast(`ZIP generado con ${ids.length} PDF${ids.length !== 1 ? 's' : ''}`, 'success');
  } catch (e) {
    toast('Error al generar el ZIP', 'error');
  }
  btn.disabled    = false;
  btn.textContent = 'Descargar PDFs (ZIP)';
}

// ── Date range picker ──
let calFechaInicio = null;
let calFechaFin    = null;
let calMes         = new Date(); calMes.setDate(1);

const CAL_MESES   = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
const CAL_DIASEM  = ['Lu','Ma','Mi','Ju','Vi','Sa','Do'];

function toggleCalendario() {
  const drop = document.getElementById('cal-dropdown');
  if (drop.style.display === 'none') { renderCalendario(); drop.style.display = 'block'; }
  else                               { drop.style.display = 'none'; }
}

function renderCalendario() {
  const year  = calMes.getFullYear();
  const month = calMes.getMonth();
  const diasMes = new Date(year, month + 1, 0).getDate();
  let dow = new Date(year, month, 1).getDay();
  dow = dow === 0 ? 6 : dow - 1;   // lunes como primer día

  const hoy = new Date().toISOString().slice(0, 10);

  let html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
      <button type="button" onclick="cambiarMes(-1)"
              style="background:none;border:1px solid var(--gris-borde);border-radius:4px;width:28px;height:28px;cursor:pointer;font-size:1.1rem;line-height:1;color:var(--texto);display:flex;align-items:center;justify-content:center;">‹</button>
      <span style="font-weight:600;font-size:0.875rem;color:var(--navy);">${CAL_MESES[month]} ${year}</span>
      <button type="button" onclick="cambiarMes(1)"
              style="background:none;border:1px solid var(--gris-borde);border-radius:4px;width:28px;height:28px;cursor:pointer;font-size:1.1rem;line-height:1;color:var(--texto);display:flex;align-items:center;justify-content:center;">›</button>
    </div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center;">`;

  CAL_DIASEM.forEach(d =>
    html += `<div style="font-size:0.68rem;color:var(--texto-suave);padding:4px 0;font-weight:600;">${d}</div>`
  );

  for (let i = 0; i < dow; i++) html += '<div></div>';

  for (let d = 1; d <= diasMes; d++) {
    const f   = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const ini = f === calFechaInicio;
    const fin = f === calFechaFin;
    const mid = calFechaInicio && calFechaFin && f > calFechaInicio && f < calFechaFin;
    const esHoy = f === hoy;

    let bg = 'transparent', col = 'inherit', fw = 'normal', br = '50%', op = '';
    if (ini || fin) { bg = 'var(--navy)'; col = 'white'; fw = '700'; }
    else if (mid)   { bg = 'rgba(12,35,64,0.1)'; br = '0'; }
    else if (esHoy) { col = 'var(--acento)'; fw = '600'; }

    html += `<div onclick="seleccionarDia('${f}')"
                  style="padding:5px 1px;cursor:pointer;border-radius:${br};background:${bg};color:${col};font-weight:${fw};font-size:0.82rem;transition:opacity .1s;"
                  onmouseenter="this.style.opacity='.7'" onmouseleave="this.style.opacity='1'">${d}</div>`;
  }

  html += '</div>';

  if (!calFechaInicio) {
    html += `<p style="font-size:0.72rem;color:var(--texto-suave);margin-top:0.6rem;text-align:center;">Seleccioná el día de inicio</p>`;
  } else if (!calFechaFin) {
    html += `<p style="font-size:0.72rem;color:var(--acento);margin-top:0.6rem;text-align:center;font-weight:600;">Ahora elegí el día de fin</p>`;
  } else {
    html += `<button type="button" onclick="limpiarFechas()"
                     style="margin-top:0.6rem;width:100%;background:none;border:1px solid var(--gris-borde);border-radius:4px;padding:4px 0;font-size:0.75rem;color:var(--texto-suave);cursor:pointer;">
               ✕ Limpiar fechas
             </button>`;
  }

  document.getElementById('cal-content').innerHTML = html;
}

function seleccionarDia(fecha) {
  if (!calFechaInicio || (calFechaInicio && calFechaFin)) {
    calFechaInicio = fecha;
    calFechaFin    = null;
  } else {
    if (fecha < calFechaInicio) { calFechaFin = calFechaInicio; calFechaInicio = fecha; }
    else                        { calFechaFin = fecha; }
    actualizarBotonFecha();
    filtrarHistorial();
    document.getElementById('cal-dropdown').style.display = 'none';
  }
  renderCalendario();
}

function cambiarMes(delta) {
  calMes.setMonth(calMes.getMonth() + delta);
  renderCalendario();
}

function actualizarBotonFecha() {
  const lbl = document.getElementById('fil-fecha-label');
  const fmt  = iso => { const [y,m,d] = iso.split('-'); return `${d}/${m}/${y}`; };
  if (!calFechaInicio && !calFechaFin)           lbl.textContent = 'Rango de fechas';
  else if (calFechaInicio && calFechaFin)        lbl.textContent = `${fmt(calFechaInicio)} – ${fmt(calFechaFin)}`;
  else                                            lbl.textContent = `${fmt(calFechaInicio)}…`;
}

function limpiarFechas() {
  calFechaInicio = null; calFechaFin = null;
  actualizarBotonFecha();
  filtrarHistorial();
  document.getElementById('cal-dropdown').style.display = 'none';
}

// Cerrar al hacer clic fuera del calendario
document.addEventListener('click', e => {
  const wrap = document.getElementById('fil-fecha-wrap');
  if (wrap && !wrap.contains(e.target))
    document.getElementById('cal-dropdown').style.display = 'none';
});

// ── Modal detalle ──
function formatearFecha(fechaIso) {
  try {
    const [fecha] = fechaIso.split(' ');
    const [y, m, d] = fecha.split('-');
    const hora = fechaIso.split(' ')[1] || '';
    return `${d}/${m}/${y}${hora ? ' ' + hora.slice(0,5) : ''}`;
  } catch (_) { return fechaIso; }
}

async function verDetalle(id) {
  // Subir z-index del modal detalle si hay otros modales abiertos encima
  const overlay = document.getElementById('modal-overlay');
  const importarAbierto = document.getElementById('modal-importar').style.display !== 'none';
  const statsAbierto    = document.getElementById('modal-stats').style.display    !== 'none';
  overlay.style.zIndex  = importarAbierto ? '1350' : (statsAbierto ? '1400' : '1000');

  const data = await apiFetch(`/api/historial/${id}`);
  if (!data.ok) { toast('Error al cargar detalle', 'error'); return; }
  const c = data.cotizacion;

  const esUSD     = c.moneda === 'DOLARES';
  const dolarRate = parseFloat(c.dolar_rate) || 3.8;
  const sym       = esUSD ? '$' : 'S/';
  const conv      = p => esUSD ? p / dolarRate : p;

  document.getElementById('modal-titulo').textContent = `Cotización #${c.id}`;
  document.getElementById('modal-info').innerHTML = `
    <div><b>Cliente:</b> ${c.cliente || '—'}</div>
    <div><b>Atención:</b> ${c.atencion || '—'}</div>
    <div><b>Proyecto:</b> ${c.proyecto || '—'}</div>
    <div><b>Moneda:</b> ${c.moneda}</div>
    <div><b>Validez:</b> ${c.validez || '30 días'}</div>
    <div><b>Fecha:</b> ${formatearFecha(c.fecha)}</div>
    <div><b>Guardado por:</b> ${c.username}</div>
  `;
  document.getElementById('modal-th-pu').textContent = `P.U. (${sym})`;
  document.getElementById('modal-th-pt').textContent = `P.T. (${sym})`;

  // Resetear checkbox "seleccionar todos"
  document.getElementById('modal-sel-todos').checked = false;
  document.getElementById('btn-agregar-carrito').disabled = false;
  document.getElementById('btn-agregar-carrito').textContent = '+ Agregar seleccionados al carrito';

  const tbody = document.getElementById('modal-tbody');
  tbody.innerHTML = '';
  let total_soles = 0;
  for (const item of c.items) {
    const pt_soles = item.precio_unitario * item.cantidad;
    total_soles += pt_soles;
    const tr = document.createElement('tr');
    const itemJson = JSON.stringify(item).replace(/"/g, '&quot;');
    tr.innerHTML = `
      <td style="text-align:center; padding:0 4px;">
        <input type="checkbox" class="item-check" data-item="${itemJson}">
      </td>
      <td style="font-size:0.8rem;">${item.descripcion}</td>
      <td style="text-align:center;">${item.cantidad}</td>
      <td style="text-align:center;">${item.unidad}</td>
      <td class="td-num">${sym} ${conv(item.precio_unitario).toFixed(2)}</td>
      <td class="td-num">${sym} ${conv(pt_soles).toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  }
  document.getElementById('modal-total').textContent = `${sym} ${conv(total_soles).toFixed(2)}`;
  document.getElementById('modal-overlay').style.display = 'flex';
}

function cerrarModal() {
  const overlay = document.getElementById('modal-overlay');
  overlay.style.display = 'none';
  overlay.style.zIndex  = '1000';
}

function seleccionarTodosModal(checked) {
  document.querySelectorAll('#modal-tbody .item-check').forEach(cb => cb.checked = checked);
}

async function agregarItemsAlCarrito() {
  const checks = [...document.querySelectorAll('#modal-tbody .item-check:checked')];
  if (!checks.length) { toast('Seleccioná al menos un ítem', 'error'); return; }
  const btn = document.getElementById('btn-agregar-carrito');
  btn.disabled = true;
  btn.textContent = 'Agregando…';
  let ok = 0;
  for (const cb of checks) {
    const item = JSON.parse(cb.dataset.item);
    const fd = new FormData();
    fd.append('tipo', item.tipo);
    fd.append('descripcion', item.descripcion);
    fd.append('precio_unitario', item.precio_unitario);
    fd.append('peso_unitario', item.peso_unitario);
    fd.append('cantidad', item.cantidad);
    fd.append('unidad', item.unidad);
    fd.append('tipo_galvanizado', item.tipo_galvanizado);
    fd.append('porcentaje_ganancia', item.porcentaje_ganancia);
    fd.append('precio_manual', item.precio_manual ? '1' : '0');
    const res = await apiFetch('/api/carrito/agregar', {method: 'POST', body: fd});
    if (res && res.ok !== false) ok++;
  }
  btn.disabled = false;
  btn.textContent = '+ Agregar seleccionados al carrito';
  if (ok === checks.length) {
    toast(`${ok} ítem${ok > 1 ? 's' : ''} agregado${ok > 1 ? 's' : ''} al carrito — <a href="/carrito" style="color:inherit;font-weight:600;">Ver carrito →</a>`, 'success');
  } else {
    toast(`${ok} de ${checks.length} ítems agregados`, 'warning');
  }
}
document.getElementById('modal-overlay').addEventListener('click', function(e) {
  if (e.target === this) cerrarModal();
});

// ── Eliminar ──
async function eliminarCotizacion(id) {
  if (!confirm(`¿Eliminar cotización #${id}? Esta acción no se puede deshacer.`)) return;
  const data = await apiFetch(`/api/historial/${id}`, { method: 'DELETE' });
  if (!data.ok) { toast(data.error || 'Error al eliminar', 'error'); return; }

  toast(`Cotización #${id} eliminada`, 'success');

  // Re-fetch para reflejar el estado real (puede haber más registros en el servidor)
  await fetchLista(false);

  // Si ya no quedan cotizaciones en absoluto → volver a estado vacío
  if (!todasCotizaciones.length && !cotizacionesFiltradas.length) {
    document.getElementById('historial-tabla').style.display = 'none';
    document.getElementById('filtros-bar').style.display     = 'none';
    document.getElementById('historial-vacio').style.display = 'block';
    return;
  }
}

// ── Editar cotización (cargar al carrito) ──
let _editarId = null;

function editarCotizacion(id) {
  _editarId = id;
  document.getElementById('modal-editar-num').textContent = `#${id}`;
  document.getElementById('modal-editar').style.display = 'flex';
}

function cerrarModalEditar() {
  document.getElementById('modal-editar').style.display = 'none';
  _editarId = null;
}

document.getElementById('modal-editar').addEventListener('click', function(e) {
  if (e.target === this) cerrarModalEditar();
});

async function confirmarEditar() {
  const btn = document.getElementById('btn-confirmar-editar');
  btn.disabled = true;
  btn.textContent = 'Cargando…';
  try {
    const resp = await fetch(`/api/historial/${_editarId}/cargar_al_carrito`, { method: 'POST' });
    if (!resp.ok) throw new Error('Error al cargar');
    const meta = await resp.json();

    // Pre-llenar sessionStorage del carrito con los metadatos de la cotización
    sessionStorage.setItem('carrito_form_v1', JSON.stringify({
      clienteInput:     meta.cliente && meta.cliente_nombre
                          ? `${meta.cliente} — ${meta.cliente_nombre}`
                          : (meta.cliente || ''),
      cliente:          meta.cliente || '',
      clienteNombre:    meta.cliente_nombre || '',
      clienteRuc:       meta.cliente_ruc || '',
      clienteUbicacion: meta.cliente_ubicacion || '',
      atencion:         meta.atencion || '',
      atencionEmail:    meta.atencion_email || '',
      proyecto:         meta.proyecto || '',
      moneda:           meta.moneda || 'SOLES',
      validez:          meta.validez || '30 días',
      encabezadoTabla:  meta.encabezado_tabla || '',
    }));
    sessionStorage.setItem('editando_desde_cotizacion_id', meta.id);

    window.location.href = '/carrito';
  } catch (e) {
    alert('Error al cargar la cotización. Intenta de nuevo.');
    btn.disabled = false;
    btn.textContent = 'Cargar al carrito';
  }
}

// ── Tendencias de Precios ──
let _tendChart          = null;
let _tendDebounce       = null;
let _tendSeries         = [];
let _tendAllDates       = [];
let TEND_CLIENTES       = [];
let _tendCliActual      = ['', ''];
let _tendItemsFrecuentes = [];

const TEND_PALETA = [
  '#1a3a5c', '#e8751a', '#2e7d32', '#7b1fa2',
  '#00838f', '#c62828', '#558b2f', '#4527a0',
];

function cerrarStats() {
  document.getElementById('modal-stats').style.display = 'none';
  _destruirChart();
}
document.getElementById('modal-stats').addEventListener('click', function(e) {
  if (e.target === this) { cerrarStats(); return; }
  if (!e.target.closest('.ac-wrapper')) {
    ['tend-c1-lista','tend-c2-lista'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
  }
});

// ── AC: helpers genéricos de teclado ──
function _tendAcKey(e, listaId, onSelect) {
  const lista = document.getElementById(listaId);
  if (!lista || lista.style.display === 'none') return;
  const items = [...lista.querySelectorAll('.ac-item')];
  const active = lista.querySelector('.ac-active');
  let idx = active ? items.indexOf(active) : -1;
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (active) active.classList.remove('ac-active');
    idx = Math.min(idx + 1, items.length - 1);
    if (items[idx]) { items[idx].classList.add('ac-active'); items[idx].scrollIntoView({block:'nearest'}); }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (active) active.classList.remove('ac-active');
    idx = Math.max(idx - 1, 0);
    if (items[idx]) { items[idx].classList.add('ac-active'); items[idx].scrollIntoView({block:'nearest'}); }
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (active) onSelect(active);
  } else if (e.key === 'Escape') {
    lista.style.display = 'none';
  }
}

// ── AC: Clientes ──
function _buildTendClientes() {
  const seen = new Set();
  TEND_CLIENTES = [];
  todasCotizaciones.forEach(c => {
    const nombre = (c.cliente_nombre || c.cliente || '').trim();
    const codigo = (c.cliente || '').trim();
    if (nombre && !seen.has(nombre)) {
      seen.add(nombre);
      TEND_CLIENTES.push({ nombre, codigo });
    }
  });
  TEND_CLIENTES.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
}

function _renderTendCliLista(n, filtrados) {
  const lista = document.getElementById(`tend-c${n}-lista`);
  const vacio = `<div class="ac-item ac-item-vacio" data-nombre=""><span class="ac-name ac-vacio-label">— Sin cliente —</span></div>`;
  if (!filtrados.length) {
    lista.innerHTML = vacio + '<div class="ac-sin-resultado">Sin resultados</div>';
  } else {
    lista.innerHTML = vacio + filtrados.slice(0, 60).map(c => {
      const codigoPart = c.codigo ? `<span class="ac-code">${c.codigo}</span><span class="ac-name"> — ${c.nombre}</span>`
                                  : `<span class="ac-name">${c.nombre}</span>`;
      return `<div class="ac-item" data-nombre="${c.nombre.replace(/"/g,'&quot;')}">${codigoPart}</div>`;
    }).join('');
    lista.querySelectorAll('.ac-item').forEach(el =>
      el.addEventListener('mousedown', () => seleccionarTendCliente(n, el.dataset.nombre))
    );
  }
  lista.style.display = 'block';
}

function onTendCli(n, action) {
  const inp = document.getElementById(`tend-c${n}-input`);
  const listaId = `tend-c${n}-lista`;
  if (action === 'input') {
    _tendCliActual[n-1] = '';
    const q = inp.value.trim().toLowerCase();
    const filtrados = q ? TEND_CLIENTES.filter(c =>
      c.nombre.toLowerCase().includes(q) || c.codigo.toLowerCase().includes(q)
    ) : TEND_CLIENTES;
    _renderTendCliLista(n, filtrados);
    triggerTendencias();
  } else if (action === 'focus') {
    inp.value = '';
    _renderTendCliLista(n, TEND_CLIENTES);
  } else if (action === 'blur') {
    setTimeout(() => {
      document.getElementById(listaId).style.display = 'none';
      if (!inp.value.trim() && _tendCliActual[n-1])
        inp.value = _tendCliActual[n-1];
    }, 200);
  }
}

function seleccionarTendCliente(n, nombre) {
  _tendCliActual[n-1] = nombre;
  document.getElementById(`tend-c${n}-input`).value = nombre;
  document.getElementById(`tend-c${n}-lista`).style.display = 'none';
  if (n === 1) cargarItemsFrecuentes();
  triggerTendencias();
}

document.getElementById('tend-c1-input').addEventListener('keydown', e =>
  _tendAcKey(e, 'tend-c1-lista', el => seleccionarTendCliente(1, el.dataset.nombre))
);
document.getElementById('tend-c2-input').addEventListener('keydown', e =>
  _tendAcKey(e, 'tend-c2-lista', el => seleccionarTendCliente(2, el.dataset.nombre))
);

// ── Panel izquierdo: ítems más cotizados ──
function renderTendItemsPanel(items) {
  const lista = document.getElementById('tend-items-lista');
  if (!items.length) {
    lista.innerHTML = '<div class="tend-items-placeholder">Sin ítems en el historial</div>';
    return;
  }
  const qActual = document.getElementById('tend-q-input').value.trim();
  lista.innerHTML = items.slice(0, 60).map(it => {
    const isActive = qActual && it.descripcion === qActual;
    const badge    = it.tipo ? `<span class="tend-item-tipo">${it.tipo}</span>` : '';
    const desc     = it.descripcion.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    return `<div class="tend-item-row${isActive ? ' tend-item-active' : ''}"
                 data-desc="${it.descripcion.replace(/"/g,'&quot;')}"
                 onclick="seleccionarTendItem(this.dataset.desc)">
      ${badge}<span class="tend-item-desc" title="${desc}">${desc}</span>
      <span class="tend-item-count">${it.count}×</span>
    </div>`;
  }).join('');
}

function seleccionarTendItem(desc) {
  const inp     = document.getElementById('tend-q-input');
  const esToggle = inp.value === desc;
  inp.value     = esToggle ? '' : desc;
  // Re-renderizar panel con nuevo estado activo
  const q = inp.value.trim().toLowerCase();
  renderTendItemsPanel(q
    ? _tendItemsFrecuentes.filter(it => it.descripcion.toLowerCase().includes(q))
    : _tendItemsFrecuentes
  );
  triggerTendencias();
}

function onTendItemSearch() {
  const q = document.getElementById('tend-q-input').value.trim().toLowerCase();
  renderTendItemsPanel(q
    ? _tendItemsFrecuentes.filter(it => it.descripcion.toLowerCase().includes(q))
    : _tendItemsFrecuentes
  );
  triggerTendencias();
}

// ── Cargar ítems frecuentes desde API y renderizar panel ──
async function cargarItemsFrecuentes() {
  const lista = document.getElementById('tend-items-lista');
  lista.innerHTML = '<div class="tend-items-placeholder">Cargando…</div>';
  try {
    const cli  = _tendCliActual[0] || '';
    const proy = (document.getElementById('tend-proyecto').value || '').trim();
    const params = new URLSearchParams({ cliente: cli, proyecto: proy, limit: 60 });
    const data = await apiFetch('/api/historial/items-frecuentes?' + params.toString());
    _tendItemsFrecuentes = (data && data.ok && Array.isArray(data.items)) ? data.items : [];
    renderTendItemsPanel(_tendItemsFrecuentes);
  } catch (e) {
    _tendItemsFrecuentes = [];
    lista.innerHTML = '<div class="tend-items-placeholder">Error al cargar ítems</div>';
  }
}

// ── Modo comparación ──
function toggleModoComparacion() {
  const on = document.getElementById('tend-modo-cmp').checked;
  document.getElementById('tend-cmp-cliente2-wrap').style.display = on ? 'flex' : 'none';
  if (!on) {
    document.getElementById('tend-c2-input').value = '';
    _tendCliActual[1] = '';
  }
  triggerTendencias();
}

// ── Rango de fechas del gráfico ──
function _getFilteredDates() {
  const desde = (document.getElementById('tend-fecha-desde').value || '').trim();
  const hasta = (document.getElementById('tend-fecha-hasta').value || '').trim();
  return _tendAllDates.filter(d => (!desde || d >= desde) && (!hasta || d <= hasta));
}

function tendLimpiarFechas() {
  document.getElementById('tend-fecha-desde').value = '';
  document.getElementById('tend-fecha-hasta').value = '';
  triggerTendencias();
}

// ── Debounce central ──
function triggerTendencias() {
  clearTimeout(_tendDebounce);
  _tendDebounce = setTimeout(cargarTendencias, 380);
}

// Igual que triggerTendencias pero también recarga el panel de ítems (p.ej. al cambiar proyecto)
function triggerTendenciasFull() {
  clearTimeout(_tendDebounce);
  _tendDebounce = setTimeout(async () => {
    await cargarItemsFrecuentes();
    cargarTendencias();
  }, 380);
}

// ── Abrir modal ──
async function abrirEstadisticas() {
  document.getElementById('modal-stats').style.display = 'flex';
  _buildTendClientes();

  // Rango por defecto: 3 meses hacia atrás (solo si los campos están vacíos)
  const desdeFld = document.getElementById('tend-fecha-desde');
  const hastaFld = document.getElementById('tend-fecha-hasta');
  if (!desdeFld.value && !hastaFld.value) {
    const hoy   = new Date();
    const desde = new Date(hoy.getFullYear(), hoy.getMonth() - 3, hoy.getDate());
    desdeFld.value = desde.toISOString().slice(0, 10);
    hastaFld.value = hoy.toISOString().slice(0, 10);
  }

  // Intentar pre-llenar cliente desde barra de filtros
  if (!_tendCliActual[0]) {
    const filCli = (document.getElementById('fil-cliente').value || '').trim().toLowerCase();
    if (filCli) {
      const match = TEND_CLIENTES.find(c =>
        c.nombre.toLowerCase().includes(filCli) || c.codigo.toLowerCase().includes(filCli)
      );
      if (match) {
        document.getElementById('tend-c1-input').value = match.nombre;
        _tendCliActual[0] = match.nombre;
      }
    }
  }

  // Siempre cargar ítems frecuentes (con o sin cliente)
  await Promise.all([cargarItemsFrecuentes(), cargarTendencias()]);
}

// ── Fetch y render ──
async function cargarTendencias() {
  const cli1    = _tendCliActual[0] || document.getElementById('tend-c1-input').value.trim();
  const cli2    = _tendCliActual[1] || document.getElementById('tend-c2-input').value.trim();
  const proy    = document.getElementById('tend-proyecto').value.trim();
  const q       = document.getElementById('tend-q-input').value.trim();
  const galvs   = [...document.querySelectorAll('.tend-galv:checked')].map(cb => cb.value);
  const esps    = [...document.querySelectorAll('.tend-esp:checked')].map(cb => cb.value);
  const gans    = [...document.querySelectorAll('.tend-gan:checked')].map(cb => cb.value);
  const monedas = [...document.querySelectorAll('.tend-moneda:checked')].map(cb => cb.value);

  const tendEmpty     = document.getElementById('tend-empty');
  const tendLoading   = document.getElementById('tend-loading');
  const tendNoData    = document.getElementById('tend-no-data');
  const tendChartWrap = document.getElementById('tend-chart-wrap');
  const tendHint      = document.getElementById('tend-hint');

  if (!cli1 && !q) {
    tendEmpty.style.display     = '';
    tendLoading.style.display   = 'none';
    tendNoData.style.display    = 'none';
    tendChartWrap.style.display = 'none';
    tendHint.style.display      = 'none';
    return;
  }

  tendEmpty.style.display     = 'none';
  tendNoData.style.display    = 'none';
  tendChartWrap.style.display = 'none';
  tendHint.style.display      = 'none';
  tendLoading.style.display   = '';

  const params = new URLSearchParams({ cliente: cli1, cliente2: cli2, proyecto: proy, q });
  galvs.forEach(g => params.append('galvanizado', g));
  esps.forEach(e => params.append('espesor', e));
  gans.forEach(g => params.append('ganancia', g));
  monedas.forEach(m => params.append('moneda', m));

  const data = await apiFetch('/api/historial/tendencias?' + params.toString());
  tendLoading.style.display = 'none';

  if (!data.ok || !data.series || !data.series.length) {
    tendNoData.style.display = '';
    _destruirChart();
    return;
  }

  tendChartWrap.style.display = '';
  tendHint.style.display      = '';
  // Dos rAFs: primero para que el cambio de display surta efecto,
  // segundo para que el navegador compute el layout del contenedor
  await new Promise(r => requestAnimationFrame(r));
  await new Promise(r => requestAnimationFrame(r));
  _renderTendChart(data.series, cli1, cli2);
}

function _destruirChart() {
  if (_tendChart) { _tendChart.destroy(); _tendChart = null; }
  _tendSeries   = [];
  _tendAllDates = [];
}

function _fmtFechaCorta(iso) {
  if (!iso || iso.length < 10) return iso;
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y.slice(2)}`;
}

function _renderTendChart(series, cli1Label, cli2Label) {
  if (typeof Chart === 'undefined') {
    console.error('[tendencias] Chart.js no disponible — revisar CDN');
    return;
  }
  _destruirChart();
  _tendSeries = series;

  const canvas        = document.getElementById('tend-chart');
  const tendChartWrap = document.getElementById('tend-chart-wrap');
  const tendNoData    = document.getElementById('tend-no-data');

  // Construir el universo completo de fechas con datos
  const fechasSet = new Set();
  series.forEach(s => s.puntos.forEach(p => fechasSet.add(p.fecha)));
  _tendAllDates = [...fechasSet].sort();

  // Aplicar filtro de rango de fechas (side-client, sin re-fetch)
  const windowDates = _getFilteredDates();

  // Si no hay datos en el rango, mostrar estado vacío
  if (!windowDates.length) {
    tendChartWrap.style.display = 'none';
    if (tendNoData) {
      tendNoData.style.display = '';
      tendNoData.querySelector('p').textContent = 'Sin datos en el rango seleccionado.';
    }
    return;
  }

  // Hay datos — mostrar canvas, ocultar mensajes
  if (tendNoData) tendNoData.style.display = 'none';
  tendChartWrap.style.display = '';
  canvas.style.display = 'block';
  canvas.style.width   = '100%';
  canvas.style.height  = '100%';
  void canvas.offsetHeight;  // forzar reflow para que Chart.js lea dimensiones correctas

  // modoComp: activado por modo comparación explícito (cli2) o cuando no hay cliente
  // y hay múltiples clientes en los datos (sin_cliente = !cli1Label)
  const sinCliente  = !cli1Label;
  const modoComp    = series.some(s => s.cliente_idx === 1) || sinCliente;
  const colorByDesc = new Map();
  let colorCounter  = 0;

  const datasets = series.map(s => {
    const esCli2 = s.cliente_idx === 1;
    if (!colorByDesc.has(s.descripcion))
      colorByDesc.set(s.descripcion, TEND_PALETA[colorCounter++ % TEND_PALETA.length]);
    const color = colorByDesc.get(s.descripcion);
    const label = modoComp
      ? `${s.descripcion}${s.cliente ? ' (' + s.cliente + ')' : (esCli2 ? ' (' + cli2Label + ')' : (cli1Label ? ' (' + cli1Label + ')' : ''))}`
      : s.descripcion;

    return {
      label,
      data: windowDates.map(fecha => {
        const p = s.puntos.find(pt => pt.fecha === fecha);
        return p != null ? p.precio_soles : null;
      }),
      borderColor: color,
      backgroundColor: color + '22',
      borderDash: esCli2 ? [6, 4] : [],
      borderWidth: 2,
      pointRadius: 6,
      pointHoverRadius: 9,
      pointBackgroundColor: color,
      spanGaps: false,
      tension: 0.15,
    };
  });

  const ctx = canvas.getContext('2d');
  _tendChart = new Chart(ctx, {
    type: 'line',
    data: { labels: windowDates.map(_fmtFechaCorta), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'nearest', intersect: true },
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 18, padding: 10 } },
        tooltip: {
          callbacks: {
            title: items => _fmtFechaCorta(windowDates[items[0].dataIndex]),
            label: item => {
              const s = series[item.datasetIndex];
              const p = s.puntos.find(pt => pt.fecha === windowDates[item.dataIndex]);
              const partes = [`S/ ${item.raw.toFixed(2)} P.U.`];
              if (p) {
                if (p.espesor) partes.push(`e=${p.espesor}mm`);
                if (p.galvanizado && p.galvanizado !== 'N/A') partes.push(p.galvanizado);
                if (p.proyecto) partes.push(p.proyecto);
              }
              return partes.join('  ·  ');
            },
            afterBody: () => ['↵ Clic para ver cotización'],
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: 'Fecha', font: { size: 11 } },
          ticks: { maxRotation: 45, font: { size: 10 } },
        },
        y: {
          title: { display: true, text: 'P.U. (S/)', font: { size: 11 } },
          ticks: {
            font: { size: 10 },
            callback: v => 'S/ ' + Number(v).toLocaleString('es-PE', {minimumFractionDigits:2, maximumFractionDigits:2}),
          },
        },
      },
      onClick: (event, elements) => {
        if (!elements.length) return;
        const el = elements[0];
        const s  = _tendSeries[el.datasetIndex];
        const p  = s.puntos.find(pt => pt.fecha === windowDates[el.index]);
        if (p) verDetalle(p.cotizacion_id);
      },
    },
  });
}

// ── Comparar cotizaciones ──
function cerrarComparar() {
  document.getElementById('modal-comparar').style.display = 'none';
}
document.getElementById('modal-comparar').addEventListener('click', function(e) {
  if (e.target === this) cerrarComparar();
});

async function compararCotizaciones() {
  const ids = [...document.querySelectorAll('.row-check:checked')].map(cb => cb.dataset.id);
  if (ids.length !== 2) return;

  document.getElementById('cmp-loading').style.display = 'block';
  document.getElementById('cmp-content').style.display = 'none';
  document.getElementById('modal-comparar').style.display = 'flex';

  const [r1, r2] = await Promise.all([
    apiFetch(`/api/historial/${ids[0]}`),
    apiFetch(`/api/historial/${ids[1]}`),
  ]);
  if (!r1.ok || !r2.ok) { toast('Error al cargar cotizaciones', 'error'); cerrarComparar(); return; }

  const c1 = r1.cotizacion;
  const c2 = r2.cotizacion;

  // Construir set de descripciones de cada lado para detectar solos/diffs
  const map1 = new Map(c1.items.map(it => [it.descripcion, it]));
  const map2 = new Map(c2.items.map(it => [it.descripcion, it]));

  function renderPanel(c, otherMap) {
    const esUSD = c.moneda === 'DOLARES';
    const dr    = parseFloat(c.dolar_rate) || 3.8;
    const sym   = esUSD ? '$' : 'S/';
    const conv  = p => esUSD ? p / dr : p;

    let total_soles = 0;
    const itemsHtml = c.items.map(it => {
      const pt = it.precio_unitario * it.cantidad;
      total_soles += pt;
      const other = otherMap.get(it.descripcion);
      let cls = '';
      if (!other) cls = 'cmp-item-solo';
      else if (other.precio_unitario !== it.precio_unitario || other.cantidad !== it.cantidad) cls = 'cmp-item-diff';
      return `<div class="cmp-item ${cls}">
        <span style="flex:1;">${it.descripcion}</span>
        <span style="white-space:nowrap; color:var(--texto-suave);">${it.cantidad} ${it.unidad}</span>
        <span style="white-space:nowrap; font-weight:600;">${sym} ${conv(it.precio_unitario).toFixed(2)}</span>
      </div>`;
    }).join('');

    return `<div class="cmp-panel">
      <div class="cmp-header">Cotización #${c.id}</div>
      <div class="cmp-meta">
        <span><b>Cliente:</b> ${c.cliente || '—'}</span>
        <span><b>Fecha:</b> ${formatearFecha(c.fecha)}</span>
        <span><b>Proyecto:</b> ${c.proyecto || '—'}</span>
        <span><b>Moneda:</b> ${c.moneda}</span>
        <span><b>Validez:</b> ${c.validez || '30 días'}</span>
        <span><b>Ítems:</b> ${c.items.length}</span>
      </div>
      ${itemsHtml}
      <div class="cmp-total">${sym} ${conv(total_soles).toFixed(2)}</div>
    </div>`;
  }

  const content = document.getElementById('cmp-content');
  content.innerHTML = renderPanel(c1, map2) + renderPanel(c2, map1);

  document.getElementById('cmp-loading').style.display = 'none';
  content.style.display = 'grid';
}

// Cargar al entrar
cargarHistorial();

// ═══════════════════════════════════════════════════════
// Importar PDFs + Gestionar Duplicados
// ═══════════════════════════════════════════════════════
let _impArchivos      = [];
let _impResultados    = [];
let _dupGrupos        = [];        // grupos detectados
let _dupIdsEliminar   = [];        // ids a eliminar en siguiente paso

// ── Tabs del modal ──
function cambiarTabImportar(tab) {
  const esImportar   = tab === 'importar';
  document.getElementById('imp-tab-content-importar').style.display   = esImportar   ? '' : 'none';
  document.getElementById('imp-tab-content-duplicados').style.display = !esImportar  ? '' : 'none';

  const btnImp = document.getElementById('imp-tab-importar');
  const btnDup = document.getElementById('imp-tab-duplicados');
  btnImp.style.borderBottomColor = esImportar  ? 'var(--azul)' : 'transparent';
  btnImp.style.color             = esImportar  ? 'var(--azul)' : 'var(--texto-suave)';
  btnDup.style.borderBottomColor = !esImportar ? 'var(--azul)' : 'transparent';
  btnDup.style.color             = !esImportar ? 'var(--azul)' : 'var(--texto-suave)';

  document.getElementById('imp-titulo').textContent = esImportar
    ? 'Importar cotizaciones desde PDF'
    : 'Gestionar Duplicados';

  if (!esImportar) cargarDuplicados();
}

function abrirModalImportar() {
  _impArchivos   = [];
  _impResultados = [];
  irPasoUpload();
  cambiarTabImportar('importar');
  document.getElementById('modal-importar').style.display = 'flex';
}

function cerrarModalImportar() {
  document.getElementById('modal-importar').style.display = 'none';
}

function cerrarYRefrescar() {
  cerrarModalImportar();
  fetchLista(false);
  if (document.getElementById('historial-vacio').style.display !== 'none') {
    cargarHistorial();
  }
}

document.getElementById('modal-importar').addEventListener('click', function(e) {
  if (e.target === this) cerrarModalImportar();
});

function irPasoUpload() {
  document.getElementById('imp-paso-upload').style.display    = 'block';
  document.getElementById('imp-paso-preview').style.display   = 'none';
  document.getElementById('imp-paso-resultado').style.display = 'none';
  document.getElementById('imp-file-input').value = '';
  document.getElementById('imp-archivos-lista').textContent = '';
  document.getElementById('imp-btn-analizar').disabled = true;
  _impArchivos = [];
}

function volverUpload() { irPasoUpload(); }

function onImpFileChange(event) {
  _impArchivos = Array.from(event.target.files);
  const lista = document.getElementById('imp-archivos-lista');
  if (_impArchivos.length === 0) {
    lista.textContent = '';
    document.getElementById('imp-btn-analizar').disabled = true;
    return;
  }
  lista.innerHTML = _impArchivos.map(f =>
    `<div>📄 ${f.name} <span style="color:var(--texto-suave);">(${(f.size/1024).toFixed(0)} KB)</span></div>`
  ).join('');
  document.getElementById('imp-btn-analizar').disabled = false;
}

// Drag & drop
(function() {
  const zona = document.querySelector('#imp-paso-upload > div[onclick]');
  if (!zona) return;
  zona.addEventListener('dragover', e => { e.preventDefault(); zona.style.borderColor = 'var(--azul)'; });
  zona.addEventListener('dragleave', () => { zona.style.borderColor = 'var(--gris-borde)'; });
  zona.addEventListener('drop', e => {
    e.preventDefault();
    zona.style.borderColor = 'var(--gris-borde)';
    const dt = e.dataTransfer;
    if (dt && dt.files.length) {
      _impArchivos = Array.from(dt.files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
      const lista = document.getElementById('imp-archivos-lista');
      lista.innerHTML = _impArchivos.map(f =>
        `<div>📄 ${f.name} <span style="color:var(--texto-suave);">(${(f.size/1024).toFixed(0)} KB)</span></div>`
      ).join('');
      document.getElementById('imp-btn-analizar').disabled = _impArchivos.length === 0;
    }
  });
})();

async function analizarPdfs() {
  const btn = document.getElementById('imp-btn-analizar');
  btn.disabled = true;
  btn.textContent = 'Analizando…';
  const form = new FormData();
  for (const f of _impArchivos) form.append('archivos', f, f.name);
  try {
    const resp = await fetch('/api/importar/parsear', { method: 'POST', body: form });
    const data = await resp.json();
    if (!data.ok) {
      toast(data.error || 'Error al analizar los PDFs', 'error');
      btn.disabled = false; btn.textContent = 'Analizar'; return;
    }
    _impResultados = data.resultados;
    mostrarPreview(_impResultados);
  } catch (e) {
    toast('Error de red al analizar los PDFs', 'error');
    btn.disabled = false; btn.textContent = 'Analizar';
  }
}

function mostrarPreview(resultados) {
  document.getElementById('imp-paso-upload').style.display   = 'none';
  document.getElementById('imp-paso-preview').style.display  = 'block';

  const tbody  = document.getElementById('imp-tbody-preview');
  const divErr = document.getElementById('imp-errores-lista');
  const divAdv = document.getElementById('imp-advertencias');
  const divDup = document.getElementById('imp-aviso-dup');

  tbody.innerHTML  = '';
  divErr.innerHTML = '';

  const errores = resultados.filter(r => !r.ok);
  const ok      = resultados.filter(r => r.ok);

  const todasAdv = resultados.flatMap(r => r.advertencias || []);
  if (todasAdv.length) {
    divAdv.style.display = 'block';
    divAdv.innerHTML = '⚠️ ' + todasAdv.join('<br>⚠️ ');
  } else {
    divAdv.style.display = 'none';
  }

  if (errores.length) {
    divErr.innerHTML = errores.map(r =>
      `<div style="color:var(--rojo);font-size:0.8rem;margin-top:0.25rem;">
         ✕ <strong>${r.nombre_archivo}</strong>: ${r.error}
       </div>`
    ).join('');
  }

  let hayDuplicados = false;
  ok.forEach((r, idx) => {
    const d   = r.datos;
    const sym = d.moneda === 'DOLARES' ? '$' : 'S/';
    const total = d.moneda === 'DOLARES'
      ? `$ ${(d.total_precio / 3.8).toFixed(2)}`
      : `S/ ${d.total_precio.toFixed(2)}`;
    const fecha = d.fecha ? d.fecha.slice(0, 10) : '—';
    const dups  = d.posibles_duplicados || [];
    if (dups.length) hayDuplicados = true;
    const dupBadge = dups.length
      ? `<span title="Posible duplicado de cotizaciones: #${dups.join(', #')}"
               style="background:#e57373;color:white;border-radius:4px;font-size:0.65rem;
                      padding:1px 5px;vertical-align:middle;cursor:help;">🔁 Dup #${dups.join(', #')}</span> `
      : '';

    const tr = document.createElement('tr');
    if (dups.length) tr.style.background = '#fff5f5';
    tr.dataset.idx = idx;
    tr.innerHTML = `
      <td style="text-align:center;">
        <input type="checkbox" class="imp-cb" data-idx="${idx}" checked>
      </td>
      <td style="max-width:160px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"
          title="${r.nombre_archivo}">${dupBadge}${r.nombre_archivo}</td>
      <td>${d.cliente_nombre || '<span style="color:var(--texto-suave);">—</span>'}</td>
      <td>${d.proyecto || '<span style="color:var(--texto-suave);">—</span>'}</td>
      <td>${fecha}</td>
      <td style="text-align:center;">${d.n_items}</td>
      <td style="text-align:right;">${total}</td>
    `;
    tbody.appendChild(tr);
  });

  divDup.style.display = hayDuplicados ? 'block' : 'none';

  if (!ok.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1rem; color:var(--texto-suave);">
      Ningún PDF pudo procesarse correctamente.</td></tr>`;
    document.getElementById('imp-btn-confirmar').disabled = true;
  } else {
    document.getElementById('imp-btn-confirmar').disabled = false;
  }
  document.getElementById('imp-sel-todas').checked = true;
}

function seleccionarTodasImp(checked) {
  document.querySelectorAll('.imp-cb').forEach(cb => cb.checked = checked);
}

async function confirmarImportacion() {
  const btn = document.getElementById('imp-btn-confirmar');
  btn.disabled = true;
  btn.textContent = 'Importando…';

  const seleccionadas = [];
  document.querySelectorAll('.imp-cb:checked').forEach(cb => {
    const idx = parseInt(cb.dataset.idx);
    const r = _impResultados.filter(r => r.ok)[idx];
    if (r) seleccionadas.push(r.datos);
  });

  if (!seleccionadas.length) {
    toast('No hay cotizaciones seleccionadas', 'error');
    btn.disabled = false; btn.textContent = 'Importar seleccionadas'; return;
  }

  try {
    const resp = await fetch('/api/importar/confirmar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cotizaciones: seleccionadas }),
    });
    const data = await resp.json();

    document.getElementById('imp-paso-preview').style.display   = 'none';
    document.getElementById('imp-paso-resultado').style.display = 'block';
    document.getElementById('imp-titulo').textContent = 'Importación completada';

    const errNum = (data.errores || []).length;
    if (data.total > 0) {
      document.getElementById('imp-resultado-icono').textContent = '✅';
      document.getElementById('imp-resultado-texto').innerHTML =
        `Se importaron <strong>${data.total}</strong> cotización${data.total > 1 ? 'es' : ''} correctamente al historial.` +
        (errNum ? `<br><span style="color:var(--rojo);">Fallaron: ${errNum}</span>` : '');
    } else {
      document.getElementById('imp-resultado-icono').textContent = '❌';
      document.getElementById('imp-resultado-texto').textContent =
        `No se pudo importar ninguna cotización. Errores: ${errNum}`;
    }
  } catch (e) {
    toast('Error de red al confirmar la importación', 'error');
    btn.disabled = false; btn.textContent = 'Importar seleccionadas';
  }
}

// ═══════════════════════════════════════════════════════
// Gestionar Duplicados
// ═══════════════════════════════════════════════════════
async function cargarDuplicados() {
  document.getElementById('dup-loading').style.display  = 'block';
  document.getElementById('dup-vacio').style.display    = 'none';
  document.getElementById('dup-content').style.display  = 'none';
  _dupGrupos = [];

  try {
    const data = await apiFetch('/api/importar/duplicados');
    document.getElementById('dup-loading').style.display = 'none';
    if (!data.ok || !data.grupos.length) {
      document.getElementById('dup-vacio').style.display = 'block';
      return;
    }
    _dupGrupos = data.grupos;
    renderDuplicados();
    document.getElementById('dup-content').style.display = 'block';
  } catch (e) {
    document.getElementById('dup-loading').style.display = 'none';
    toast('Error al cargar duplicados', 'error');
  }
}

function _fmtFecha(iso) {
  if (!iso) return '—';
  const [y,m,d] = iso.split('-');
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

function renderDuplicados() {
  const cont = document.getElementById('dup-grupos');
  cont.innerHTML = '';

  _dupGrupos.forEach((grupo, gi) => {
    const cots = grupo.cotizaciones;
    // El primero (mayor id) se sugiere conservar
    const wrapper = document.createElement('div');
    wrapper.style.cssText = 'border:1px solid var(--gris-borde); border-radius:8px; margin-bottom:1rem; overflow:hidden;';

    const header = document.createElement('div');
    header.style.cssText = 'background:var(--gris-fondo); padding:0.55rem 0.85rem; font-size:0.82rem; font-weight:600; color:var(--navy);';
    const clienteLabel  = grupo.cliente  || '(sin cliente)';
    const proyectoLabel = grupo.proyecto || '(sin proyecto)';
    const totalLabel    = grupo.total != null ? `S/ ${Number(grupo.total).toFixed(2)}` : '—';
    header.textContent = `👥 ${clienteLabel}  —  ${proyectoLabel}  —  Total: ${totalLabel}  (${cots.length} cotizaciones)`;
    wrapper.appendChild(header);

    const tbl = document.createElement('table');
    tbl.style.cssText = 'width:100%; font-size:0.81rem; border-collapse:collapse;';
    tbl.innerHTML = `<thead>
      <tr style="background:var(--azul); color:white;">
        <th style="padding:5px 8px; width:38px; text-align:center;">
          <span title="Marcar para ELIMINAR">Elim.</span>
        </th>
        <th style="padding:5px 8px; width:46px;">#</th>
        <th style="padding:5px 8px; width:130px;">Fecha</th>
        <th style="padding:5px 8px;">Proyecto</th>
        <th style="padding:5px 8px; width:50px; text-align:center;">Ítems</th>
        <th style="padding:5px 8px; width:110px; text-align:right;">Total</th>
        <th style="padding:5px 8px; width:80px;">Usuario</th>
        <th style="padding:5px 8px; width:55px; text-align:center;">Origen</th>
        <th style="padding:5px 8px; width:46px; text-align:center;">PDF</th>
      </tr>
    </thead>`;
    const tbody = document.createElement('tbody');
    cots.forEach((c, ci) => {
      const tr = document.createElement('tr');
      tr.style.borderTop = '1px solid var(--gris-borde)';
      if (ci === 0) tr.style.background = '#f0fff4'; // sugerido para conservar
      const esUSD = c.moneda === 'DOLARES';
      const dr = parseFloat(c.dolar_rate) || 3.8;
      const total = esUSD
        ? (parseFloat(c.total_precio) / dr).toFixed(2)
        : parseFloat(c.total_precio).toFixed(2);
      const sym = esUSD ? '$' : 'S/';
      const origenBadge = c.origen === 'pdf_import'
        ? '<span style="background:#e8751a;color:white;border-radius:4px;font-size:0.65rem;padding:1px 4px;">PDF</span>'
        : '<span style="background:var(--azul-claro);color:white;border-radius:4px;font-size:0.65rem;padding:1px 4px;">WEB</span>';
      const conservarLabel = ci === 0
        ? '<span style="font-size:0.65rem;color:#2e7d32;font-weight:600;">★ sugerido</span>'
        : '';
      tr.innerHTML = `
        <td style="text-align:center; padding:4px 8px;">
          <input type="checkbox" class="dup-cb" data-id="${c.id}" data-gi="${gi}"
                 ${ci === 0 ? '' : 'checked'}
                 onchange="dupActualizarConteo()">
        </td>
        <td style="padding:4px 8px; color:var(--texto-suave);">#${c.id} ${conservarLabel}</td>
        <td style="padding:4px 8px;">${formatearFecha(c.fecha)}</td>
        <td style="padding:4px 8px;">${c.proyecto || '—'}</td>
        <td style="text-align:center; padding:4px 8px;">${c.total_items || '?'}</td>
        <td style="text-align:right; padding:4px 8px; font-weight:600;">${sym} ${total}</td>
        <td style="padding:4px 8px; color:var(--texto-suave);">${c.username || '—'}</td>
        <td style="text-align:center; padding:4px 8px;">${origenBadge}</td>
        <td style="text-align:center; padding:4px 8px;">
          <button onclick="verDetalle(${c.id})" title="Ver detalle de cotización #${c.id}"
                  class="btn btn-secondary btn-sm">
            Ver
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    wrapper.appendChild(tbl);
    cont.appendChild(wrapper);
  });

  dupActualizarConteo();
}

function dupActualizarConteo() {
  const checks = document.querySelectorAll('.dup-cb:checked');
  const n = checks.length;
  document.getElementById('dup-cnt').textContent =
    n > 0 ? `${n} cotización${n !== 1 ? 'es' : ''} marcada${n !== 1 ? 's' : ''} para eliminar` : 'Ninguna seleccionada';
  document.getElementById('dup-btn-eliminar').disabled = n === 0;
}

function dupSeleccionarSugeridos() {
  // Conservar el más antiguo (primer elemento, menor id); marcar el resto para eliminar
  document.querySelectorAll('.dup-cb').forEach(cb => {
    const gi = parseInt(cb.dataset.gi);
    const grupo = _dupGrupos[gi];
    if (!grupo) return;
    const esMasAntiguo = grupo.cotizaciones[0].id == parseInt(cb.dataset.id);
    cb.checked = !esMasAntiguo;
  });
  dupActualizarConteo();
}

function dupConfirmarEliminar() {
  const checks = [...document.querySelectorAll('.dup-cb:checked')];
  if (!checks.length) return;
  _dupIdsEliminar = checks.map(cb => parseInt(cb.dataset.id));

  // Validar que en cada grupo quede al menos 1 sin marcar
  const porGrupo = {};
  document.querySelectorAll('.dup-cb').forEach(cb => {
    const gi = parseInt(cb.dataset.gi);
    if (!porGrupo[gi]) porGrupo[gi] = { total: 0, marcadas: 0 };
    porGrupo[gi].total++;
    if (cb.checked) porGrupo[gi].marcadas++;
  });
  const gruposSinConservar = Object.entries(porGrupo)
    .filter(([, v]) => v.marcadas >= v.total)
    .map(([gi]) => parseInt(gi));

  if (gruposSinConservar.length) {
    const nombres = gruposSinConservar.map(gi => {
      const g = _dupGrupos[gi];
      return `"${g.cliente || '—'} / ${g.proyecto || '—'}"`;
    }).join(', ');
    toast(`En el grupo ${nombres} no queda ninguna cotización para conservar. Desmarcá al menos una.`, 'error');
    return;
  }

  const n = _dupIdsEliminar.length;
  document.getElementById('dup-confirm-texto').innerHTML =
    `Se eliminarán <strong>${n}</strong> cotización${n !== 1 ? 'es' : ''} del historial de forma permanente.<br>
    <span style="font-size:0.8rem; color:var(--texto-suave);">IDs: #${_dupIdsEliminar.join(', #')}</span>`;
  document.getElementById('modal-dup-confirm').style.display = 'flex';
}

async function dupEjecutarEliminar() {
  document.getElementById('modal-dup-confirm').style.display = 'none';
  const btn = document.getElementById('dup-btn-eliminar');
  btn.disabled = true; btn.textContent = 'Eliminando…';

  try {
    const resp = await fetch('/api/importar/eliminar_duplicados', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: _dupIdsEliminar }),
    });
    const data = await resp.json();
    if (data.ok) {
      toast(`${data.eliminadas} cotización${data.eliminadas !== 1 ? 'es eliminadas' : ' eliminada'} correctamente`, 'success');
      await fetchLista(false);   // refrescar historial
      await cargarDuplicados();  // refrescar lista de duplicados
    } else {
      toast(data.error || 'Error al eliminar', 'error');
    }
  } catch (e) {
    toast('Error de red al eliminar duplicados', 'error');
  }
  btn.disabled = false; btn.textContent = 'Eliminar seleccionados';
  _dupIdsEliminar = [];
}
