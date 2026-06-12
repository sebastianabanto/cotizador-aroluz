// ── Estado global ──
let tipoActual    = 'bandeja';
let calcTimer     = null;
let calcAbort     = null; // AbortController para cancelar requests anteriores
let _agregando    = false; // guard anti-doble-tap móvil
let medidasRecordadas = null; // { tipo, ancho, alto }
let _lastResult   = { prod: null, tapa: null }; // últimos resultados de la API
let _prevConTapa  = null; // para detectar cambio de modo juntos↔separado
// Si es F5/recarga, limpiar panel en vivo Y carrito real
const _navType = performance.getEntriesByType('navigation')[0]?.type;
if (_navType === 'reload') {
  sessionStorage.removeItem('carritoLive');
  fetch('/api/carrito/limpiar', { method: 'POST' }).then(() => {
    const badge = document.getElementById('nav-badge-carrito');
    if (badge) { badge.textContent = '0'; badge.style.display = 'none'; }
  });
}
const carritoSesion = JSON.parse(sessionStorage.getItem('carritoLive') || '[]');

const TITULOS = {
  bandeja: 'Bandeja', curva_horizontal: 'Curva Horizontal',
  curva_vertical: 'Curva Vertical', tee: 'TEE', cruz: 'Cruz',
  reduccion: 'Reducción', caja_pase: 'Caja de Pase',
};

// Campos ancho/alto representativos por tipo (para "arrastrar" dimensiones)
const CAMPO_ANCHO = {
  bandeja: 'b-ancho', curva_horizontal: 'ch-ancho', curva_vertical: 'cv-ancho',
  tee: ['t-derecha','t-izquierda','t-abajo'], cruz: 'c-ancho',
  reduccion: 'r-mayor', caja_pase: null,
};
const CAMPO_ALTO = {
  bandeja: 'b-alto', curva_horizontal: 'ch-alto', curva_vertical: 'cv-alto',
  tee: 't-alto', cruz: 'c-alto', reduccion: 'r-alto', caja_pase: null,
};

// Estado inicial sin FOUC: config colapsado bajo 720px
// Los toggles manuales y el resize dinámico son gestionados por cotizar-layout.js
if (window.innerWidth < 720) {
  document.getElementById('config-panel')?.classList.add('collapsed');
}

// ── Selección de tipo de producto ──
document.querySelectorAll('.tipo-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    const tipo = this.dataset.tipo;
    if (tipo === tipoActual) return;

    // Capturar dimensiones antes de cambiar
    const ancho = getAnchoActual();
    const alto  = getAltoActual();

    tipoActual = tipo;
    document.querySelectorAll('.tipo-btn').forEach(b => b.classList.toggle('active', b === this));
    document.querySelectorAll('.form-producto').forEach(f => f.style.display = 'none');
    document.getElementById(`form-${tipo}`).style.display = '';
    document.getElementById('form-titulo').textContent = TITULOS[tipo] || tipo;
    ocultarResultado();
    actualizarEstadoTapaAparte();

    // Propagar dimensiones al nuevo tipo
    if (medidasRecordadas) {
      aplicarMedidasRecordadas(tipo);
    } else {
      aplicarDimensionesCompartidas(tipo, ancho, alto);
    }

    actualizarIndicador();
    scheduleCalc();

    // Auto-foco al primer campo de medidas del nuevo tipo
    const primerInput = document.querySelector(`#form-${tipo} .form-input:not([type=checkbox])`);
    if (primerInput) setTimeout(() => primerInput.focus(), 30);
  });
});

// ── Chips de radio (sidebar + curva vertical) ──
document.querySelectorAll('.chip-group').forEach(group => {
  group.querySelectorAll('input[type=radio]').forEach(radio => {
    radio.addEventListener('change', function() {
      group.querySelectorAll('.chip-label').forEach(l => l.classList.remove('selected'));
      this.closest('.chip-label').classList.add('selected');
      if (this.name === 'galv') actualizarPreciosPlancha(this.value);
      scheduleCalc();
    });
  });
});

// ── Precios de plancha (por galvanizado) ──
const PLANCHA_GO = window.__PLANCHA_GO__;
const PLANCHA_GC = window.__PLANCHA_GC__;

function getPreciosPlancha() {
  return {
    '1.2': parseFloat(document.getElementById('plancha-12').value) || PLANCHA_GO['1.2'],
    '1.5': parseFloat(document.getElementById('plancha-15').value) || PLANCHA_GO['1.5'],
    '2.0': parseFloat(document.getElementById('plancha-20').value) || PLANCHA_GO['2.0'],
  };
}

function actualizarPreciosPlancha(galv) {
  const precios = galv === 'GC' ? PLANCHA_GC : PLANCHA_GO;
  document.getElementById('plancha-12').value = precios['1.2'];
  document.getElementById('plancha-15').value = precios['1.5'];
  document.getElementById('plancha-20').value = precios['2.0'];
  const badge = document.getElementById('plancha-badge');
  badge.textContent = galv;
  badge.className = 'galv-badge ' + (galv === 'GC' ? 'gc' : 'go');
}

// ── Auto-cálculo: dispara al cambiar inputs ──
document.addEventListener('input', e => {
  if (e.target.matches('.form-input, .form-select-sm, #esp-prod, #esp-tapa')) scheduleCalc();
  if (e.target.matches('#cant-main, #cant-prod, #cant-tapa')) actualizarSubtotales();
});
document.addEventListener('change', e => {
  if (e.target.matches('.form-input, .form-select-sm, #esp-prod, #esp-tapa, #b-ml')) scheduleCalc();
  if (e.target.classList.contains('check-contapa')) { actualizarEstadoTapaAparte(); actualizarQtyMode(); }
  if (e.target.classList.contains('check-tapaapart')) actualizarQtyMode();
  if (e.target.matches('#b-ml') && !e.target.checked) {
    // Al desactivar "Por metro lineal", redondear cantidades a entero
    ['cant-main','cant-prod','cant-tapa'].forEach(id => {
      const inp = document.getElementById(id);
      if (inp) inp.value = Math.max(1, Math.round(parseFloat(inp.value) || 1));
    });
    actualizarSubtotales();
  }
});

function scheduleCalc() {
  clearTimeout(calcTimer);
  // Dimear resultado visible para indicar que está recalculando
  const box = document.getElementById('resultado-box');
  if (box.classList.contains('visible')) box.classList.add('recalculando');
  calcTimer = setTimeout(calcularReal, 200);
}

// ── Forzar cálculo inmediato si hay uno pendiente (evita el "fantasma" al agregar) ──
async function ensureCalcFresh() {
  if (calcTimer !== null) {
    clearTimeout(calcTimer);
    calcTimer = null;
    await calcularReal();
  }
}

// ── Leer configuración global ──
function getGlobal() {
  return {
    galv:          document.querySelector('input[name=galv]:checked')?.value    || 'GO',
    ganancia:      document.querySelector('input[name=ganancia]:checked')?.value || '30',
    sup:           document.querySelector('input[name=sup]:checked')?.value     || 'LISA',
    espProd:       document.getElementById('esp-prod').value,
    espTapa:       document.getElementById('esp-tapa').value,
    planchaPrecios: getPreciosPlancha(),
  };
}

// ── Helpers para dimensiones ──
function getAnchoActual() {
  const c = CAMPO_ANCHO[tipoActual];
  if (!c) return null;
  const id = Array.isArray(c) ? c[0] : c;
  const v = +document.getElementById(id)?.value;
  return v > 0 ? v : null;
}
function getAltoActual() {
  const c = CAMPO_ALTO[tipoActual];
  if (!c) return null;
  const v = +document.getElementById(c)?.value;
  return v > 0 ? v : null;
}
function aplicarDimensionesCompartidas(tipo, ancho, alto) {
  if (ancho) {
    const c = CAMPO_ANCHO[tipo];
    if (c) (Array.isArray(c) ? c : [c]).forEach(id => {
      const el = document.getElementById(id); if (el) el.value = ancho;
    });
  }
  if (alto) {
    const c = CAMPO_ALTO[tipo];
    if (c) { const el = document.getElementById(c); if (el) el.value = alto; }
  }
}

// ── Medidas recordadas ──
function getMedidasActuales() {
  const n = id => { const v = +document.getElementById(id)?.value; return v > 0 ? v : null; };
  if (tipoActual === 'bandeja')          return { ancho: n('b-ancho'),  alto: n('b-alto') };
  if (tipoActual === 'curva_horizontal') return { ancho: n('ch-ancho'), alto: n('ch-alto') };
  if (tipoActual === 'curva_vertical')   return { ancho: n('cv-ancho'), alto: n('cv-alto') };
  if (tipoActual === 'tee')             return { ancho: n('t-derecha'), alto: n('t-alto') };
  if (tipoActual === 'cruz')            return { ancho: n('c-ancho'),  alto: n('c-alto') };
  if (tipoActual === 'reduccion')       return { ancho: n('r-mayor'),  alto: n('r-alto') };
  return null;
}
function aplicarMedidasRecordadas(tipo) {
  if (!medidasRecordadas || tipo === 'caja_pase') return;
  const { ancho, alto } = medidasRecordadas;
  const s = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
  if      (tipo === 'bandeja')          { s('b-ancho', ancho);  s('b-alto', alto); }
  else if (tipo === 'curva_horizontal') { s('ch-ancho', ancho); s('ch-alto', alto); }
  else if (tipo === 'curva_vertical')   { s('cv-ancho', ancho); s('cv-alto', alto); }
  else if (tipo === 'tee')             { s('t-derecha', ancho); s('t-izquierda', ancho); s('t-abajo', ancho); s('t-alto', alto); }
  else if (tipo === 'cruz')            { s('c-ancho', ancho);  s('c-alto', alto); }
  else if (tipo === 'reduccion')       { s('r-mayor', ancho);  s('r-menor', Math.max(ancho-100,1)); s('r-alto', alto); }
}
function recordarMedidas() {
  if (tipoActual === 'caja_pase') return;
  const m = getMedidasActuales();
  if (!m || !m.ancho || !m.alto) { toast('Ingresá medidas antes de recordar', 'error'); return; }
  medidasRecordadas = { tipo: tipoActual, ancho: m.ancho, alto: m.alto };
  actualizarIndicador();
}
function limpiarRecordar() {
  medidasRecordadas = null;
  actualizarIndicador();
}
function actualizarIndicador() {
  const btnBar  = document.getElementById('btn-recordar-bar');
  const chip    = document.getElementById('chip-recordar');
  const chipNom = document.getElementById('chip-recordar-nombre');
  const esCaja  = tipoActual === 'caja_pase';
  if (medidasRecordadas) {
    btnBar.style.display = 'none';
    chip.style.display   = 'inline-flex';
    chipNom.textContent  = `${medidasRecordadas.ancho}×${medidasRecordadas.alto}mm`;
  } else {
    btnBar.style.display = esCaja ? 'none' : '';
    chip.style.display   = 'none';
  }
  document.querySelectorAll('.tipo-btn').forEach(btn => {
    btn.classList.toggle('tiene-record',
      !!medidasRecordadas && btn.dataset.tipo === medidasRecordadas.tipo);
  });
}

// ── Auto-recordar medidas al ingresar dimensiones ──
function _autoRecordar() {
  if (tipoActual === 'caja_pase') return;
  const m = getMedidasActuales();
  if (m && m.ancho && m.alto) recordarMedidas();
}
const _DIM_IDS = [
  'b-ancho','b-alto','ch-ancho','ch-alto','cv-ancho','cv-alto',
  't-derecha','t-izquierda','t-abajo','t-alto',
  'c-ancho','c-alto','r-mayor','r-menor','r-alto',
];
document.addEventListener('DOMContentLoaded', () => {
  _DIM_IDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', _autoRecordar);
  });

  // ── Teclado numérico + bloqueo de caracteres no numéricos ──
  document.querySelectorAll('input[type=number]').forEach(inp => {
    const isDecimal = parseFloat(inp.getAttribute('step') || '1') % 1 !== 0;
    inp.setAttribute('inputmode', isDecimal ? 'decimal' : 'numeric');
    inp.addEventListener('keydown', e => {
      const nav = ['Backspace','Delete','Tab','Escape','Enter',
                   'ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'];
      if (nav.includes(e.key) || e.ctrlKey || e.metaKey) return;
      if (isDecimal && (e.key === '.' || e.key === ',')) return;
      if (!/^\d$/.test(e.key)) e.preventDefault();
    });
  });
});

// ── Cálculo real con la API ──
async function calcularReal() {
  const g = getGlobal();
  const n = id => { const v = +document.getElementById(id)?.value; return v > 0 ? v : null; };

  let body = {
    tipo_galvanizado: g.galv,
    ganancia: g.ganancia,
    tipo_superficie: g.sup,
    espesor_producto: g.espProd,
    espesor_tapa: g.espTapa,
    precio_plancha_producto: g.planchaPrecios[g.espProd],
    precio_plancha_tapa: g.planchaPrecios[g.espTapa],
  };

  if (tipoActual === 'bandeja') {
    const ancho = n('b-ancho'), alto = n('b-alto');
    if (!ancho || !alto) return ocultarResultado();
    body.ancho = ancho; body.alto = alto;
    body.es_metro_lineal = document.getElementById('b-ml').checked;

  } else if (tipoActual === 'curva_horizontal') {
    const ancho = n('ch-ancho'), alto = n('ch-alto');
    if (!ancho || !alto) return ocultarResultado();
    body.ancho = ancho; body.alto = alto;

  } else if (tipoActual === 'curva_vertical') {
    const ancho = n('cv-ancho'), alto = n('cv-alto');
    if (!ancho || !alto) return ocultarResultado();
    body.ancho = ancho; body.alto = alto;
    body.tipo_curva = document.querySelector('input[name=tipo_curva]:checked')?.value || 'EXTERNA';

  } else if (tipoActual === 'tee') {
    const d = n('t-derecha'), i = n('t-izquierda'), ab = n('t-abajo'), alto = n('t-alto');
    if (!d || !i || !ab || !alto) return ocultarResultado();
    body.derecha = d; body.izquierda = i; body.abajo = ab; body.alto = alto;

  } else if (tipoActual === 'cruz') {
    const ancho = n('c-ancho'), alto = n('c-alto');
    if (!ancho || !alto) return ocultarResultado();
    body.ancho = ancho; body.alto = alto;

  } else if (tipoActual === 'reduccion') {
    const mayor = n('r-mayor'), menor = n('r-menor'), alto = n('r-alto');
    if (!mayor || !menor || !alto) return ocultarResultado();
    body.ancho_mayor = mayor; body.ancho_menor = menor; body.alto = alto;

  } else if (tipoActual === 'caja_pase') {
    const d1 = n('cp-d1'), d2 = n('cp-d2'), d3 = n('cp-d3');
    if (!d1 || !d2 || !d3) return ocultarResultado();
    body.dim1 = d1; body.dim2 = d2; body.dim3 = d3;
    body.tipo_salida = document.getElementById('cp-salida').value;
  }

  // Cancelar request anterior si sigue en vuelo
  if (calcAbort) calcAbort.abort();
  calcAbort = new AbortController();

  try {
    const resp = await fetch(`/api/cotizar/${tipoActual}`, {
      method: 'POST',
      body: formData(body),
      signal: calcAbort.signal,
    });
    const data = await resp.json();
    document.getElementById('resultado-box').classList.remove('recalculando');
    if (data.ok && data.resultados?.length > 0) {
      const prod = data.resultados[0];
      const tapa = data.resultados.length > 1 ? data.resultados[1] : null;
      _lastResult = { prod, tapa };
      mostrarResultado(prod, tapa);
    } else {
      ocultarResultado();
    }
  } catch (e) {
    document.getElementById('resultado-box').classList.remove('recalculando');
    if (e.name !== 'AbortError') ocultarResultado();
  }
}

// ── Mostrar resultado ──
function mostrarResultado(prod, tapa) {
  document.getElementById('resultado-box').classList.add('visible');
  document.getElementById('resultado-desc').textContent        = prod.descripcion;
  // Flash al actualizar precio (fix D)
  const _precioEl = document.getElementById('resultado-precio');
  _precioEl.textContent = `S/ ${prod.precio_unitario.toFixed(2)}`;
  _precioEl.classList.remove('price-updated');
  void _precioEl.offsetWidth; // reflow para reiniciar la animación
  _precioEl.classList.add('price-updated');
  document.getElementById('resultado-peso').textContent        = `Peso: ${prod.peso_unitario.toFixed(2)} kg/und`;
  document.getElementById('resultado-hint').textContent        = prod.descripcion.includes('POR ML') ? 'Precio por metro lineal' : '';
  document.getElementById('msg-medidas').style.display         = 'none';

  const secTapa = document.getElementById('seccion-tapa');
  if (tapa) {
    secTapa.style.display = '';
    document.getElementById('resultado-tapa-desc').textContent       = tapa.descripcion;
    document.getElementById('resultado-tapa-precio').textContent     = `S/ ${tapa.precio_unitario.toFixed(2)}`;
    document.getElementById('resultado-tapa-peso').textContent       = `Peso: ${tapa.peso_unitario.toFixed(2)} kg/und`;
  } else {
    secTapa.style.display = 'none';
  }

  actualizarQtyMode();
}

function ocultarResultado() {
  _lastResult = { prod: null, tapa: null };
  document.getElementById('resultado-box').classList.remove('visible');
  document.getElementById('msg-medidas').style.display = '';
}

// ── Modo con/sin tapa ──
function getConTapa() {
  if (tipoActual === 'caja_pase') return false; // tapa incluida en precio, no se agrega por separado
  if (!_lastResult.tapa) return false; // sin tapa en resultado
  const cb = document.querySelector(`#form-${tipoActual} .check-contapa`);
  return cb ? cb.checked : true;
}

function getTapaAparte() {
  if (tipoActual === 'caja_pase') return false;
  if (!getConTapa()) return false;
  const cb = document.querySelector(`#form-${tipoActual} .check-tapaapart`);
  return cb ? cb.checked : false;
}

function actualizarEstadoTapaAparte() {
  if (tipoActual === 'caja_pase') return;
  const cbContapa = document.querySelector(`#form-${tipoActual} .check-contapa`);
  const lblAparte = document.querySelector(`#form-${tipoActual} .lbl-tapaapart`);
  const cbAparte  = document.querySelector(`#form-${tipoActual} .check-tapaapart`);
  if (!lblAparte || !cbAparte) return;
  const on = cbContapa ? cbContapa.checked : true;
  lblAparte.classList.toggle('disabled', !on);
  if (!on) cbAparte.checked = false;
}

function actualizarQtyMode() {
  const con = getConTapa();
  const hayTapa = !!_lastResult.tapa;

  // Modo "juntos": una cantidad, un botón + Carrito
  document.getElementById('acciones-ambos').style.display        = (con && hayTapa) ? 'flex' : 'none';
  // Modo "separados": controles individuales por producto y tapa
  document.getElementById('acciones-prod-individual').style.display = (!con) ? 'flex' : 'none';
  document.getElementById('acciones-tapa-individual').style.display = (!con && hayTapa) ? 'flex' : 'none';

  // Sincronizar cantidad SOLO al cambiar de modo "juntos" → "separado"
  // (nunca en cada recalc, para no pisar lo que el usuario ya escribió)
  if (_prevConTapa === true && !con) {
    document.getElementById('cant-prod').value = document.getElementById('cant-main').value;
    if (hayTapa) document.getElementById('cant-tapa').value = document.getElementById('cant-main').value;
  }
  _prevConTapa = con;

  // Actualizar descripción del cuerpo según modo tapa
  if (_lastResult.prod) {
    const desc = con
      ? _lastResult.prod.descripcion
      : _lastResult.prod.descripcion.replace('(C/UNION)', '(C/UNIÓN SIN TAPA)');
    document.getElementById('resultado-desc').textContent = desc;
  }

  // Mostrar/ocultar fila total (precio cuerpo + tapa combinados)
  const totalEl = document.getElementById('resultado-total');
  if (totalEl) {
    if (con && _lastResult.tapa && _lastResult.prod) {
      const total = _lastResult.prod.precio_unitario + _lastResult.tapa.precio_unitario;
      totalEl.textContent = `TOTAL: S/ ${total.toFixed(2)}`;
      totalEl.style.display = '';
    } else {
      totalEl.style.display = 'none';
    }
  }

  actualizarSubtotales();
}

// ── Cantidad ──
function cambiarCant(cual, delta) {
  const ids = { prod: 'cant-prod', tapa: 'cant-tapa', main: 'cant-main' };
  const inp = document.getElementById(ids[cual]);
  if (inp) inp.value = fmtCant(Math.max(0.01, (parseFloat(inp.value) || 1) + delta));
  actualizarSubtotales();
}

// ── Agregar ítem individual (prod o tapa) ──
async function agregarItem(cual) {
  if (_agregando) return;
  _agregando = true;
  try {
    await ensureCalcFresh();
    const r = cual === 'prod' ? _lastResult.prod : _lastResult.tapa;
    if (!r) return;
    const g    = getGlobal();
    const conTapa = getConTapa();
    const cantId  = conTapa ? 'cant-main' : (cual === 'prod' ? 'cant-prod' : 'cant-tapa');
    const cant    = parseFloat(document.getElementById(cantId).value) || 1;

    // Si se agrega solo el cuerpo sin tapa, usar descripción "(C/UNIÓN SIN TAPA)"
    const descFinal = (cual === 'prod' && !getConTapa())
      ? r.descripcion.replace('(C/UNION)', '(C/UNIÓN SIN TAPA)')
      : r.descripcion;

    const data = await apiFetch('/api/carrito/agregar', {
      method: 'POST',
      body: formData({
        tipo: r.tipo,
        descripcion: descFinal,
        precio_unitario: r.precio_unitario,
        peso_unitario: r.peso_unitario,
        cantidad: cant,
        tipo_galvanizado: g.galv,
        porcentaje_ganancia: g.ganancia,
        unidad: r.descripcion.includes('POR ML') ? 'ML' : 'UND',
      }),
    });
    if (data.ok) {
      const btnId = cual === 'prod' ? 'btn-agregar-prod' : 'btn-agregar-tapa';
      const lbl   = cual === 'prod' ? '+ Producto' : '+ Tapa';
      flashBtn(btnId, lbl);
      toast('Agregado al carrito');
      const ctxKey = getContextKey();
      const grupo = cual === 'prod'
        ? { prod: { desc: descFinal, cant, precio: r.precio_unitario }, tapa: null }
        : { prod: null, tapa: { desc: descFinal, cant, precio: r.precio_unitario } };
      carritoSesion.push({ id: Date.now(), label: descFinal.split(' - ').slice(0,2).join(' - '), ctxKey, ...grupo, abierto: false });
      document.getElementById(cantId).value = 1;
      renderCarritoLive();
      actualizarBadgeCarrito();
      animarBadge();
      // Volver el foco al primer campo de medidas
      const primerInput = document.querySelector(`#form-${tipoActual} .form-input:not([type=checkbox])`);
      if (primerInput) setTimeout(() => primerInput.focus(), 80);
    } else {
      toast('Error al agregar', 'error');
    }
  } finally {
    _agregando = false;
  }
}

// ── Agregar producto + tapa juntos ──
async function agregarAmbos() {
  if (_agregando) return;
  _agregando = true;
  try {
    await ensureCalcFresh();
    if (!document.getElementById('resultado-box').classList.contains('visible')) return;
    const { prod, tapa } = _lastResult;
    if (!prod) return;
    const g    = getGlobal();
    const cant = parseFloat(document.getElementById('cant-main').value) || 1;
    const tapaAparte = getTapaAparte();

    // ── Modo combinado: tapa aparte OFF → 1 solo ítem con precio sumado ──
    if (!tapaAparte && tapa) {
      const descCombinada = prod.descripcion.replace('(C/UNION)', '(C/UNIÓN Y TAPA)');
      const r1c = await apiFetch('/api/carrito/agregar', {
        method: 'POST',
        body: formData({
          tipo: prod.tipo,
          descripcion: descCombinada,
          precio_unitario: prod.precio_unitario + tapa.precio_unitario,
          peso_unitario: prod.peso_unitario + tapa.peso_unitario,
          cantidad: cant,
          tipo_galvanizado: g.galv,
          porcentaje_ganancia: g.ganancia,
          unidad: prod.descripcion.includes('POR ML') ? 'ML' : 'UND',
        }),
      });
      if (!r1c.ok) { toast('Error al agregar', 'error'); return; }
      flashBtn('btn-agregar-ambos', '+ Carrito');
      toast('Producto (c/tapa) agregado');
      document.getElementById('cant-main').value = 1;
      carritoSesion.push({
        id: Date.now(),
        label: descCombinada.split(' - ').slice(0,2).join(' - '),
        ctxKey: getContextKey(), abierto: false,
        prod: { desc: descCombinada, cant, precio: prod.precio_unitario + tapa.precio_unitario },
        tapa: null, combinado: true,
      });
      renderCarritoLive();
      actualizarBadgeCarrito();
      animarBadge();
      const primerInputC = document.querySelector(`#form-${tipoActual} .form-input:not([type=checkbox])`);
      if (primerInputC) setTimeout(() => primerInputC.focus(), 80);
      return;
    }

    // ── Modo separado: tapa aparte ON → 2 ítems independientes ──
    const r1 = await apiFetch('/api/carrito/agregar', {
      method: 'POST',
      body: formData({
        tipo: prod.tipo, descripcion: prod.descripcion,
        precio_unitario: prod.precio_unitario, peso_unitario: prod.peso_unitario,
        cantidad: cant, tipo_galvanizado: g.galv, porcentaje_ganancia: g.ganancia,
        unidad: prod.descripcion.includes('POR ML') ? 'ML' : 'UND',
      }),
    });
    if (!r1.ok) { toast('Error al agregar producto', 'error'); return; }

    let r2 = { ok: true };
    if (tapa) {
      r2 = await apiFetch('/api/carrito/agregar', {
        method: 'POST',
        body: formData({
          tipo: tapa.tipo, descripcion: tapa.descripcion,
          precio_unitario: tapa.precio_unitario, peso_unitario: tapa.peso_unitario,
          cantidad: cant, tipo_galvanizado: g.galv, porcentaje_ganancia: g.ganancia,
          unidad: tapa.descripcion.includes('POR ML') ? 'ML' : 'UND',
        }),
      });
    }

    if (r2.ok) {
      flashBtn('btn-agregar-ambos', '+ Carrito');
      toast(tapa ? 'Producto + tapa agregados' : 'Producto agregado');
      document.getElementById('cant-main').value = 1;
      const label = prod.descripcion.split(' - ').slice(0,2).join(' - ');
      carritoSesion.push({
        id: Date.now(), label, ctxKey: getContextKey(), abierto: false,
        prod: { desc: prod.descripcion, cant, precio: prod.precio_unitario },
        tapa: tapa ? { desc: tapa.descripcion, cant, precio: tapa.precio_unitario } : null,
      });
      renderCarritoLive();
      actualizarBadgeCarrito();
      animarBadge();
      // Volver el foco al primer campo de medidas
      const primerInputA = document.querySelector(`#form-${tipoActual} .form-input:not([type=checkbox])`);
      if (primerInputA) setTimeout(() => primerInputA.focus(), 80);
    } else {
      toast('Error al agregar tapa', 'error');
    }
  } finally {
    _agregando = false;
  }
}

// ── Bounce en badge del carrito (fix E) ──
function animarBadge() {
  ['bn-badge-carrito', 'nav-badge-carrito'].forEach(id => {
    const b = document.getElementById(id);
    if (b && b.style.display !== 'none') {
      b.classList.remove('badge-bounce');
      void b.offsetWidth;
      b.classList.add('badge-bounce');
    }
  });
}

// ── Feedback visual en botón ──
function flashBtn(id, textoOriginal) {
  const btn = document.getElementById(id);
  if (!btn) return;
  btn.textContent = '✓'; btn.classList.add('ok');
  setTimeout(() => { btn.textContent = textoOriginal; btn.classList.remove('ok'); }, 1200);
}

// ── Clave de contexto (para live panel) ──
function getContextKey() {
  const g = getGlobal();
  const n = id => document.getElementById(id)?.value || '';
  let dims = '';
  if      (tipoActual === 'bandeja')           dims = `${n('b-ancho')}x${n('b-alto')}`;
  else if (tipoActual === 'curva_horizontal')  dims = `${n('ch-ancho')}x${n('ch-alto')}`;
  else if (tipoActual === 'curva_vertical')    dims = `${n('cv-ancho')}x${n('cv-alto')}|${document.querySelector('input[name=tipo_curva]:checked')?.value}`;
  else if (tipoActual === 'tee')               dims = `${n('t-derecha')}x${n('t-izquierda')}x${n('t-abajo')}x${n('t-alto')}`;
  else if (tipoActual === 'cruz')              dims = `${n('c-ancho')}x${n('c-alto')}`;
  else if (tipoActual === 'reduccion')         dims = `${n('r-mayor')}x${n('r-menor')}x${n('r-alto')}`;
  else if (tipoActual === 'caja_pase')         dims = `${n('cp-d1')}x${n('cp-d2')}x${n('cp-d3')}`;
  return `${tipoActual}|${dims}|${g.galv}|${g.sup}`;
}

// ── Render del mini carrito en vivo ──
function renderCarritoLive() {
  const container = document.getElementById('carrito-live-items');
  const footer    = document.getElementById('carrito-live-footer');
  const countEl   = document.getElementById('carrito-live-count');
  const totalEl   = document.getElementById('carrito-live-total-txt');

  const aviso = document.getElementById('carrito-live-aviso');
  countEl.textContent = carritoSesion.length;
  sessionStorage.setItem('carritoLive', JSON.stringify(carritoSesion));

  if (carritoSesion.length === 0) {
    container.innerHTML = '<p class="carrito-live-empty">Todavía no agregaste productos.</p>';
    footer.style.display = 'none';
    if (aviso) aviso.style.display = 'none';
    return;
  }
  if (aviso) aviso.style.display = '';

  let html = '';
  carritoSesion.forEach((g) => {
    let tagHtml = '';
    let cantDisplay = g.prod ? g.prod.cant : (g.tapa ? g.tapa.cant : 1);
    const esCombinado = g.combinado || (g.prod && !g.tapa && g.prod.desc?.includes('C/UNIÓN Y TAPA'));
    if (g.prod && g.tapa)       tagHtml = '<span class="cli-tag ct">C/T</span>';
    else if (esCombinado)       tagHtml = '<span class="cli-tag ct">C/T</span>';
    else if (g.prod && !g.tapa) tagHtml = '<span class="cli-tag st">S/T</span>';
    else if (!g.prod && g.tapa) tagHtml = '<span class="cli-tag tapa">Solo Tapa</span>';

    const labelEsc = g.label.replace(/"/g, '&quot;');
    html += `<div class="cli-grupo">
      <div class="cli-row" onclick="toggleGrupoLive(${g.id})">
        <span class="cli-arrow${g.abierto ? ' open' : ''}">▶</span>
        <span class="cli-label" title="${labelEsc}">${g.label}</span>
        ${tagHtml}
        <span class="cli-qty">×${cantDisplay}</span>
        <button class="cli-del" onclick="event.stopPropagation(); deleteGrupoLive(${g.id})" title="Quitar">×</button>
      </div>
      <div class="cli-detail${g.abierto ? ' open' : ''}">`;
    if (g.prod) html += `<div class="cli-detail-line"><span><strong>Producto:</strong> ×${g.prod.cant} = S/ ${(g.prod.cant * g.prod.precio).toFixed(2)}</span></div>`;
    if (g.tapa) html += `<div class="cli-detail-line"><span><strong>Tapa:</strong> ×${g.tapa.cant} = S/ ${(g.tapa.cant * g.tapa.precio).toFixed(2)}</span></div>`;
    html += `</div></div>`;
  });

  const totalUnds = carritoSesion.reduce((s, g) => s + (g.prod?.cant || 0) + (g.tapa?.cant || 0), 0);
  const totalSoles = carritoSesion.reduce((s, g) =>
    s + (g.prod ? g.prod.cant * g.prod.precio : 0)
      + (g.tapa ? g.tapa.cant * g.tapa.precio : 0), 0);
  container.innerHTML = html;
  totalEl.textContent = `${totalUnds} ítem${totalUnds !== 1 ? 's' : ''}`;
  document.getElementById('carrito-live-total-soles').textContent = `S/ ${totalSoles.toFixed(2)}`;
  footer.style.display = '';
}

function toggleGrupoLive(id) {
  const g = carritoSesion.find(x => x.id === id);
  if (g) { g.abierto = !g.abierto; renderCarritoLive(); }
}
function deleteGrupoLive(id) {
  const idx = carritoSesion.findIndex(x => x.id === id);
  if (idx !== -1) carritoSesion.splice(idx, 1);
  renderCarritoLive();
  actualizarBadgeCarrito();
}

// ── Subtotales dinámicos ──
function actualizarSubtotales() {
  if (!_lastResult.prod) return; // sin resultado, nada que mostrar
  const con = getConTapa();
  const hayTapa = !!_lastResult.tapa;
  const modoJuntos = con && hayTapa;

  // Subtotal producto (modo separado)
  const stProd = document.getElementById('subtotal-prod');
  if (stProd) {
    if (!modoJuntos && _lastResult.prod) {
      const cantProd = parseFloat(document.getElementById('cant-prod').value) || 1;
      document.getElementById('cant-display-prod').textContent = cantProd;
      document.getElementById('precio-total-prod').textContent = `S/ ${(cantProd * _lastResult.prod.precio_unitario).toFixed(2)}`;
      stProd.style.display = cantProd > 1 ? '' : 'none';
    } else {
      stProd.style.display = 'none';
    }
  }

  // Subtotal tapa (modo separado)
  const stTapa = document.getElementById('subtotal-tapa');
  if (stTapa) {
    if (!modoJuntos && _lastResult.tapa) {
      const cantTapa = parseFloat(document.getElementById('cant-tapa').value) || 1;
      document.getElementById('cant-display-tapa').textContent = cantTapa;
      document.getElementById('precio-total-tapa').textContent = `S/ ${(cantTapa * _lastResult.tapa.precio_unitario).toFixed(2)}`;
      stTapa.style.display = cantTapa > 1 ? '' : 'none';
    } else {
      stTapa.style.display = 'none';
    }
  }

  // Subtotal combinado (modo juntos)
  const stMain = document.getElementById('subtotal-main');
  if (stMain) {
    if (modoJuntos && _lastResult.prod) {
      const cantMain = parseFloat(document.getElementById('cant-main').value) || 1;
      document.getElementById('cant-display-main').textContent = cantMain;
      const precioTotal = cantMain * (_lastResult.prod.precio_unitario + (_lastResult.tapa?.precio_unitario || 0));
      document.getElementById('precio-total-main').textContent = `S/ ${precioTotal.toFixed(2)}`;
      stMain.style.display = cantMain > 1 ? '' : 'none';
    } else {
      stMain.style.display = 'none';
    }
  }
}


// ── Restaurar panel en vivo al cargar ──
renderCarritoLive();

// ── Aviso al cerrar/F5 si hay ítems (no al navegar internamente) ──
let _navegandoInternamente = false;
document.querySelectorAll('a[href^="/"]').forEach(a => {
  a.addEventListener('click', () => { _navegandoInternamente = true; });
});
window.addEventListener('beforeunload', e => {
  if (carritoSesion.length > 0 && !_navegandoInternamente) {
    e.preventDefault();
    e.returnValue = '';
  }
  setTimeout(() => { _navegandoInternamente = false; }, 200);
});


// ── Enter / Ctrl+Enter → agregar al carrito ──
document.addEventListener('keydown', async e => {
  if (e.key !== 'Enter') return;
  if (document.activeElement.tagName === 'SELECT' || document.activeElement.tagName === 'BUTTON') return;
  e.preventDefault();

  if (e.ctrlKey || e.metaKey) {
    // Ctrl+Enter: cancelar debounce pendiente, forzar cálculo ahora y agregar
    clearTimeout(calcTimer);
    calcTimer = null;
    await calcularReal();
    const conTapa = getConTapa();
    if (conTapa && _lastResult.tapa) agregarAmbos();
    else if (_lastResult.prod)       agregarItem('prod');
  } else {
    // Enter simple: solo agregar si el resultado ya está visible
    if (document.getElementById('resultado-box').classList.contains('visible')) {
      const conTapa = getConTapa();
      if (conTapa && _lastResult.tapa) agregarAmbos();
      else agregarItem('prod');
    }
  }
});

// ── Alt+1..7 → seleccionar tipo de producto (espeja desktop) ──
const _TIPOS_ORDEN = [
  'bandeja', 'curva_horizontal', 'curva_vertical',
  'tee', 'cruz', 'reduccion', 'caja_pase'
];
document.addEventListener('keydown', e => {
  if (!e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
  const idx = parseInt(e.key) - 1;
  if (idx >= 0 && idx < _TIPOS_ORDEN.length) {
    e.preventDefault();
    const btn = document.querySelector(`.tipo-btn[data-tipo="${_TIPOS_ORDEN[idx]}"]`);
    if (btn) btn.click();
  }
});

// ── Tab en el último campo de medidas → salta al input de cantidad ──
function bindTabEnMedidas(formId) {
  const form = document.getElementById(formId);
  if (!form) return;
  const inputs = [...form.querySelectorAll('.form-input[type=number]')];
  const ultimo = inputs[inputs.length - 1];
  if (!ultimo) return;
  ultimo.addEventListener('keydown', e => {
    if (e.key !== 'Tab' || e.shiftKey) return;
    const box = document.getElementById('resultado-box');
    if (!box.classList.contains('visible')) return;
    // Determinar qué input de cantidad es el activo según modo
    const cantId = getConTapa() ? 'cant-main' : 'cant-prod';
    const cantInput = document.getElementById(cantId);
    if (cantInput) {
      e.preventDefault();
      cantInput.focus();
      cantInput.select();
    }
  });
}
// Registrar para cada tipo
['bandeja','curva_horizontal','curva_vertical','tee','cruz','reduccion','caja_pase']
  .forEach(t => bindTabEnMedidas(`form-${t}`));

// ── Tab en cant-main/prod/tapa → vuelve al primer campo del form actual ──
function bindTabEnCantidad(cantId) {
  const inp = document.getElementById(cantId);
  if (!inp) return;
  inp.addEventListener('keydown', e => {
    if (e.key !== 'Tab' || e.shiftKey) return;
    const primerInput = document.querySelector(
      `#form-${tipoActual} .form-input:not([type=checkbox])`
    );
    if (primerInput) {
      e.preventDefault();
      primerInput.focus();
      primerInput.select();
    }
  });
}
bindTabEnCantidad('cant-main');
bindTabEnCantidad('cant-prod');
bindTabEnCantidad('cant-tapa');

// ── Inicializar badge de plancha con el galvanizado por defecto ──
(function() {
  const galvInit = document.querySelector('input[name=galv]:checked')?.value || 'GO';
  const badge = document.getElementById('plancha-badge');
  if (badge) badge.className = 'galv-badge ' + (galvInit === 'GC' ? 'gc' : 'go');
})();
