history.scrollRestoration = 'manual';
// ── Datos embebidos ──
const CLIENTES   = window.__CLIENTES__;
const ATENCIONES = window.__ATENCIONES__;
const DOLAR      = window.__DOLAR__;  // tipo de cambio S/ por USD
const MONEDAS    = [
  { valor: 'SOLES',   nombre: 'Soles (S/)' },
  { valor: 'DOLARES', nombre: 'Dólares Americanos ($)' },
];

// ── Persistencia del formulario — definida aquí para que esté disponible globalmente ──
const _FORM_KEY = 'carrito_form_v1';
function guardarFormulario() {
  sessionStorage.setItem(_FORM_KEY, JSON.stringify({
    moneda:           document.getElementById('moneda')?.value || 'SOLES',
    validez:          document.getElementById('validez')?.value || '30 días',
    cliente:          document.getElementById('cliente')?.value || '',
    clienteInput:     document.getElementById('cliente-input')?.value || '',
    clienteNombre:    document.getElementById('cliente-nombre')?.value || '',
    clienteRuc:       document.getElementById('cliente-ruc')?.value || '',
    clienteUbicacion: document.getElementById('cliente-ubicacion')?.value || '',
    atencion:         document.getElementById('atencion')?.value || '',
    atencionEmail:    document.getElementById('atencion-email')?.value || '',
    proyecto:         document.getElementById('proyecto')?.value || '',
    encabezadoTabla:  document.getElementById('encabezado-tabla')?.value || '',
  }));
}

function limpiarCamposProyecto() {
  _clienteActual = { codigo: '', nombre: '' };
  document.getElementById('cliente-input').value = '';
  document.getElementById('cliente').value = '';
  document.getElementById('cliente-nombre').value = '';
  document.getElementById('cliente-ruc').value = '';
  document.getElementById('cliente-ubicacion').value = '';
  _atencionActual = { valor: '', nombre: '' };
  document.getElementById('atencion-input').value = '';
  document.getElementById('atencion').value = '';
  document.getElementById('atencion-email').value = '';
  document.getElementById('proyecto').value = '';
  document.getElementById('encabezado-tabla').value = '';
}

// Datos del carrito indexados por id para actualización dinámica
const carritoMap = new Map(window.__CARRITO__.map(i => [i.id, i]));

// ── Conversión de moneda ──
function esDolares() { return document.getElementById('moneda').value === 'DOLARES'; }
function sym()       { return esDolares() ? '$' : 'S/'; }
function conv(soles) { return esDolares() ? soles / DOLAR : soles; }

function cambiarMoneda() {
  const s = sym();
  // Encabezados
  document.getElementById('th-pu').textContent = `P.U. (${s})`;
  document.getElementById('th-pt').textContent = `P.T. (${s})`;
  // Celdas P.U.
  document.querySelectorAll('[data-precio-soles]').forEach(el => {
    const pu = parseFloat(el.dataset.precioSoles);
    el.textContent = `${s} ${conv(pu).toFixed(2)}`;
  });
  // Celdas P.T. (usando carritoMap para respetar cantidades actuales)
  carritoMap.forEach((item, id) => {
    const ptEl = document.getElementById(`pt-${id}`);
    if (ptEl) ptEl.textContent = `${s} ${conv(item.precio_unitario * item.cantidad).toFixed(2)}`;
  });
  actualizarTotales();
}

// ── Autocomplete genérico: navegación teclado ──
function _acKeydown(e, listaId, onSelect) {
  const lista = document.getElementById(listaId);
  const items = [...lista.querySelectorAll('.ac-item')];
  if (!items.length) return;
  let idx = items.findIndex(it => it.classList.contains('ac-active'));
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    idx = Math.min(idx + 1, items.length - 1);
    items.forEach((it, i) => it.classList.toggle('ac-active', i === idx));
    items[idx]?.scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    idx = Math.max(idx - 1, 0);
    items.forEach((it, i) => it.classList.toggle('ac-active', i === idx));
    items[idx]?.scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'Enter' && idx >= 0) {
    e.preventDefault();
    onSelect(items[idx]);
  } else if (e.key === 'Escape') {
    lista.style.display = 'none';
  }
}

// ── Autocomplete Cliente ──
let _clienteActual = { codigo: '', nombre: '', abreviacion: '' };

function renderListaCliente(filtrados) {
  const lista = document.getElementById('cliente-lista');
  const itemVacio = `<div class="ac-item ac-item-vacio" data-codigo="" data-nombre="">
    <span class="ac-name ac-vacio-label">— Sin cliente —</span>
  </div>`;
  if (!filtrados.length) {
    lista.innerHTML = itemVacio + '<div class="ac-sin-resultado">Sin resultados</div>';
  } else {
    lista.innerHTML = itemVacio + filtrados.map(c =>
      `<div class="ac-item" data-codigo="${c.codigo}" data-nombre="${c.nombre.replace(/"/g,'&quot;')}">
        <span class="ac-code">${c.abreviacion || c.codigo}</span>
        <span class="ac-name"> — ${c.nombre}</span>
      </div>`
    ).join('');
    lista.querySelectorAll('.ac-item').forEach(el => {
      el.addEventListener('mousedown', () =>
        seleccionarCliente(el.dataset.codigo, el.dataset.nombre)
      );
    });
  }
  lista.style.display = 'block';
}

function onClienteInput() {
  const q = document.getElementById('cliente-input').value.trim().toLowerCase();
  document.getElementById('cliente').value = '';
  const filtrados = q
    ? CLIENTES.filter(c =>
        c.codigo.toLowerCase().includes(q) ||
        c.nombre.toLowerCase().includes(q) ||
        (c.abreviacion || '').toLowerCase().includes(q)
      )
    : CLIENTES;
  renderListaCliente(filtrados);
}

function onClienteFocus() {
  document.getElementById('cliente-input').value = '';
  renderListaCliente(CLIENTES);
}

function onClienteBlur() {
  setTimeout(() => {
    const inp = document.getElementById('cliente-input');
    const hiddenVal = document.getElementById('cliente').value;
    // Restaurar texto visible solo si el hidden tiene un código seleccionado
    if (!inp.value.trim() && hiddenVal) {
      inp.value = `${_clienteActual.abreviacion || _clienteActual.codigo} — ${_clienteActual.nombre}`;
    }
  }, 200);
}

function seleccionarCliente(codigo, nombre) {
  const c = codigo ? CLIENTES.find(x => x.codigo === codigo) : null;
  const label = c?.abreviacion || codigo;
  _clienteActual = { codigo, nombre, abreviacion: c?.abreviacion || '' };
  document.getElementById('cliente-input').value = codigo ? `${label} — ${nombre}` : '';
  document.getElementById('cliente').value = codigo;
  document.getElementById('cliente-lista').style.display = 'none';
  document.getElementById('cliente-nombre').value = c?.nombre || '';
  document.getElementById('cliente-ruc').value = c?.ruc || '';
  document.getElementById('cliente-ubicacion').value = c?.ubicacion || '';
  filtrarAtenciones(codigo);
  guardarFormulario();
}

document.getElementById('cliente-input').addEventListener('keydown', e =>
  _acKeydown(e, 'cliente-lista', it => seleccionarCliente(it.dataset.codigo, it.dataset.nombre))
);

// ── Autocomplete Atención ──
let _atencionActual = { valor: '', nombre: '' };

function _atencionesFiltradas(codigoCliente) {
  return codigoCliente
    ? ATENCIONES.filter(a => a.codigo_empresa === codigoCliente)
    : ATENCIONES;
}

function renderListaAtencion(lista_at) {
  const lista = document.getElementById('atencion-lista');
  const itemVacio = `<div class="ac-item ac-item-vacio" data-valor="">
    <span class="ac-name ac-vacio-label">— Sin atención —</span>
  </div>`;
  if (!lista_at.length) {
    lista.innerHTML = itemVacio + '<div class="ac-sin-resultado">Sin resultados</div>';
  } else {
    lista.innerHTML = itemVacio + lista_at.map(a =>
      `<div class="ac-item" data-valor="${a.nombre.replace(/"/g,'&quot;')}">
        <span class="ac-name">${a.nombre}</span>
      </div>`
    ).join('');
  }
  lista.querySelectorAll('.ac-item').forEach(el => {
    el.addEventListener('mousedown', () => seleccionarAtencion(el.dataset.valor));
  });
  lista.style.display = 'block';
}

function onAtencionInput() {
  const q = document.getElementById('atencion-input').value.trim().toLowerCase();
  document.getElementById('atencion').value = '';
  const base = _atencionesFiltradas(document.getElementById('cliente').value);
  const filtradas = q ? base.filter(a => a.nombre.toLowerCase().includes(q)) : base;
  renderListaAtencion(filtradas);
}

function onAtencionFocus() {
  document.getElementById('atencion-input').value = '';
  renderListaAtencion(_atencionesFiltradas(document.getElementById('cliente').value));
}

function onAtencionBlur() {
  setTimeout(() => {
    const inp = document.getElementById('atencion-input');
    const hiddenVal = document.getElementById('atencion').value;
    if (!inp.value.trim() && hiddenVal) {
      inp.value = _atencionActual.nombre;
    }
  }, 200);
}

function seleccionarAtencion(valor) {
  _atencionActual = { valor, nombre: valor };
  document.getElementById('atencion-input').value = valor;  // vacío si sin atención
  document.getElementById('atencion').value = valor;
  document.getElementById('atencion-lista').style.display = 'none';
  const a = valor ? ATENCIONES.find(x => x.nombre === valor) : null;
  document.getElementById('atencion-email').value = a?.email || '';
  guardarFormulario();
}

function filtrarAtenciones(codigoCliente) {
  // Resetear atención al cambiar cliente
  _atencionActual = { valor: '', nombre: '' };
  document.getElementById('atencion-input').value = '';
  document.getElementById('atencion').value = '';
  document.getElementById('atencion-email').value = '';
}

document.getElementById('atencion-input').addEventListener('keydown', e =>
  _acKeydown(e, 'atencion-lista', it => seleccionarAtencion(it.dataset.valor))
);

// ── Autocomplete Moneda ──
let _monedaActual = { valor: 'SOLES', nombre: 'Soles (S/)' };

function renderListaMoneda(filtradas) {
  const lista = document.getElementById('moneda-lista');
  lista.innerHTML = filtradas.map(m =>
    `<div class="ac-item" data-valor="${m.valor}">
      <span class="ac-code">${m.valor === 'SOLES' ? 'S/' : '$'}</span>
      <span class="ac-name"> — ${m.nombre}</span>
    </div>`
  ).join('');
  lista.querySelectorAll('.ac-item').forEach(el => {
    el.addEventListener('mousedown', () => seleccionarMoneda(el.dataset.valor));
  });
  lista.style.display = 'block';
}

function onMonedaInput() {
  const q = document.getElementById('moneda-input').value.trim().toLowerCase();
  const filtradas = q
    ? MONEDAS.filter(m => m.nombre.toLowerCase().includes(q) || m.valor.toLowerCase().includes(q))
    : MONEDAS;
  renderListaMoneda(filtradas);
}

function onMonedaFocus() {
  document.getElementById('moneda-input').value = '';
  renderListaMoneda(MONEDAS);
}

function onMonedaBlur() {
  setTimeout(() => {
    const inp = document.getElementById('moneda-input');
    if (!inp.value.trim() && _monedaActual.valor) {
      inp.value = _monedaActual.nombre;
      document.getElementById('moneda').value = _monedaActual.valor;
      guardarFormulario();
    }
  }, 200);
}

function seleccionarMoneda(valor) {
  const m = MONEDAS.find(x => x.valor === valor);
  if (!m) return;
  _monedaActual = { valor: m.valor, nombre: m.nombre };
  document.getElementById('moneda-input').value = m.nombre;
  document.getElementById('moneda').value = m.valor;
  document.getElementById('moneda-lista').style.display = 'none';
  cambiarMoneda();
  guardarFormulario();
}

document.getElementById('moneda-input').addEventListener('keydown', e =>
  _acKeydown(e, 'moneda-lista', it => seleccionarMoneda(it.dataset.valor))
);

// Cerrar dropdowns al hacer click fuera
document.addEventListener('click', e => {
  if (!e.target.closest('.ac-wrapper')) {
    document.getElementById('cliente-lista').style.display   = 'none';
    document.getElementById('atencion-lista').style.display  = 'none';
    document.getElementById('moneda-lista').style.display    = 'none';
  }
});

// ── Carrito ──
function cambiarCant(itemId, delta) {
  const inp = document.getElementById(`cant-${itemId}`);
  inp.value = fmtCant(Math.max(0.01, parseFloat(inp.value || 1) + delta));
  actualizarCant(itemId);
}

async function actualizarCant(itemId) {
  const cant = parseFloat(document.getElementById(`cant-${itemId}`).value) || 1;
  const fd = formData({ cantidad: cant });
  const data = await apiFetch(`/api/carrito/modificar/${itemId}`, { method: 'POST', body: fd });
  if (data.ok) {
    const item = carritoMap.get(itemId);
    item.cantidad = cant;
    document.getElementById(`pt-${itemId}`).textContent =
      `${sym()} ${conv(item.precio_unitario * cant).toFixed(2)}`;
    actualizarTotales();
  }
}

async function eliminarItem(itemId) {
  if (!confirm('¿Eliminar este ítem del carrito?')) return;
  const data = await apiFetch(`/api/carrito/eliminar/${itemId}`, { method: 'DELETE' });
  if (data.ok) {
    _navegandoInternamente = true;
    sessionStorage.setItem('_reloadProgramatico', '1');
    window.location.reload();
  } else {
    toast('Error al eliminar', 'error');
  }
}

async function limpiarCarrito() {
  if (!confirm('¿Limpiar el carrito y los datos del proyecto?')) return;
  const data = await apiFetch('/api/carrito/limpiar', { method: 'POST' });
  if (data.ok) {
    // Limpiar DOM antes de recargar para que pagehide→guardarFormulario
    // guarde valores vacíos y no restaure los anteriores al recargar
    limpiarCamposProyecto();
    seleccionarMoneda('SOLES');
    guardarFormulario();
    sessionStorage.removeItem('editando_desde_cotizacion_id');
    sessionStorage.removeItem('carritoLive');
    _navegandoInternamente = true;
    sessionStorage.setItem('_reloadProgramatico', '1');
    window.location.reload();
  }
}

// Actualiza la fila de un ítem en el DOM con los nuevos datos del backend (sin recargar)
function _actualizarFilaCarrito(item) {
  const tr = document.getElementById(`fila-${item.id}`);
  if (!tr) return;

  // Mezclar con datos existentes (preservar cantidad y otros campos no enviados)
  const prev = carritoMap.get(item.id) || {};
  const itm = { ...prev, ...item };
  carritoMap.set(item.id, itm);

  // Celda descripción (índice 2): 2 divs — descripción principal + subtítulo
  const divs = tr.cells[2].querySelectorAll('div');
  if (divs[0]) divs[0].textContent = itm.descripcion;
  if (divs[1]) {
    const com = itm.porcentaje_ganancia === '35' ? 'Con comisión' : 'Sin comisión';
    if (itm.tipo_galvanizado === 'N/A') {
      const prefijo = itm.tipo === 'MANUAL' ? 'Manual' : 'Catálogo';
      divs[1].textContent = `${prefijo} · ${com} · ${itm.unidad}`;
    } else {
      divs[1].textContent = `${itm.tipo_galvanizado} · ${com} · ${parseFloat(itm.peso_unitario).toFixed(2)} kg/und`;
    }
  }

  // Celda unidad (índice 4)
  if (tr.cells[4]) tr.cells[4].textContent = itm.unidad;

  // P.U. y P.T.
  const puEl = document.getElementById(`pu-${item.id}`);
  if (puEl) {
    puEl.dataset.precioSoles = itm.precio_unitario;
    puEl.textContent = `${sym()} ${conv(itm.precio_unitario).toFixed(2)}`;
    puEl.classList.toggle('pu-manual', !!itm.precio_manual);
  }
  const ptEl = document.getElementById(`pt-${item.id}`);
  if (ptEl) {
    ptEl.textContent = `${sym()} ${conv(itm.precio_unitario * itm.cantidad).toFixed(2)}`;
  }
}

function _eliminarFilaCarrito(itemId) {
  document.getElementById(`fila-${itemId}`)?.remove();
  carritoMap.delete(itemId);
}

// Genera el HTML de una fila del carrito (espejo del template Jinja en líneas 117-167)
function _renderFilaCarrito(item, cuerpoIdx) {
  const esTapaSep = !!item.tapa_para_id;
  const s  = sym();
  const pu = conv(item.precio_unitario);
  const pt = conv(item.precio_unitario * item.cantidad);
  const descEsc = _pl_escHtml(item.descripcion);

  const col1 = esTapaSep
    ? `<span style="color:var(--texto-suave); font-size:0.7rem; padding-left:4px;">↳</span>`
    : `<span class="drag-handle" title="Arrastrar para reordenar">⠿</span>`;

  const numCell = esTapaSep ? '' : cuerpoIdx;

  const com = item.porcentaje_ganancia === '35' ? 'Con comisión' : 'Sin comisión';
  const subtitulo = item.tipo_galvanizado === 'N/A'
    ? `${item.tipo === 'MANUAL' ? 'Manual' : 'Catálogo'} · ${com} · ${item.unidad}`
    : `${item.tipo_galvanizado} · ${com} · ${parseFloat(item.peso_unitario).toFixed(2)} kg/und`;

  const descStyle = esTapaSep
    ? 'font-size:0.875rem; padding-left:0.75rem; color:var(--texto-suave);'
    : 'font-size:0.875rem;';
  const puClass = item.precio_manual ? ' pu-manual' : '';

  const tr = document.createElement('tr');
  tr.id = `fila-${item.id}`;
  if (esTapaSep) {
    tr.className = 'fila-tapa-sep';
    tr.dataset.tapaDe = item.tapa_para_id;
  } else {
    tr.draggable = true;
  }
  tr.innerHTML = `
    <td style="text-align:center; padding:2px 0;">${col1}</td>
    <td data-label="#">${numCell}</td>
    <td data-label="">
      <div style="${descStyle}">${descEsc}</div>
      <div style="font-size:0.75rem; color:var(--texto-suave);">${subtitulo}</div>
    </td>
    <td data-label="Cant.">
      <div class="cantidad-ctrl">
        <button onclick="cambiarCant(${item.id}, -1)" aria-label="Restar cantidad">−</button>
        <input type="number" id="cant-${item.id}" value="${fmtCant(item.cantidad)}" min="0.01" max="999" step="any"
               onchange="actualizarCant(${item.id})" aria-label="Cantidad"
               inputmode="decimal" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
        <button onclick="cambiarCant(${item.id}, 1)" aria-label="Sumar cantidad">+</button>
      </div>
    </td>
    <td data-label="Und." style="text-align:center;">${item.unidad}</td>
    <td data-label="P.U." class="td-num${puClass}" id="pu-${item.id}" data-precio-soles="${item.precio_unitario}">
      ${s} ${pu.toFixed(2)}
    </td>
    <td data-label="P.T." class="td-num" id="pt-${item.id}">
      ${s} ${pt.toFixed(2)}
    </td>
    <td data-label="" style="white-space:nowrap;">
      <button class="btn btn-secondary btn-sm" style="padding:0 6px; margin-right:2px;"
        onclick="abrirModalEditar(${item.id})" title="Editar ítem">✏️</button>
      <button class="btn btn-danger btn-sm" onclick="eliminarItem(${item.id})"
        aria-label="Eliminar ${descEsc}">✕</button>
    </td>`;
  return tr;
}

// Reconstruye toda la tabla del carrito a partir de la lista del backend (sin recargar)
function _reconstruirTablaCarrito(carrito) {
  const tbody = document.getElementById('tbody-carrito');
  if (!tbody) return;
  tbody.innerHTML = '';
  carritoMap.clear();
  let cuerpoIdx = 0;
  carrito.forEach(item => {
    if (!item.tapa_para_id) cuerpoIdx += 1;
    tbody.appendChild(_renderFilaCarrito(item, cuerpoIdx));
    carritoMap.set(item.id, item);
  });
  actualizarTotales();
  const summarySpan = document.querySelector('#det-lista summary span:first-child');
  if (summarySpan) {
    const n = carritoMap.size;
    summarySpan.textContent = `Productos (${n} item${n !== 1 ? 's' : ''})`;
  }
}

function actualizarTotales() {
  let totalSoles = 0;
  let peso = 0;
  carritoMap.forEach(item => {
    totalSoles += item.precio_unitario * item.cantidad;
    peso       += item.peso_unitario   * item.cantidad;
  });
  const totalDisplay = document.getElementById('total-display');
  totalDisplay.textContent = `${sym()} ${conv(totalSoles).toFixed(2)}`;
  totalDisplay.dataset.totalSoles = totalSoles;
  if (document.getElementById('peso-display')) {
    document.getElementById('peso-display').textContent = `${peso.toFixed(2)} kg`;
  }
  const movil = document.getElementById('total-movil-val');
  if (movil) movil.textContent = `${sym()} ${conv(totalSoles).toFixed(2)}`;
  const pesoMovil = document.getElementById('peso-movil-val');
  if (pesoMovil) pesoMovil.textContent = `${peso.toFixed(2)} kg`;
}

async function agregarManual() {
  const desc = document.getElementById('m-desc').value.trim();
  if (!desc) { toast('Ingrese una descripción', 'error'); return; }

  const fd = formData({
    descripcion: desc,
    precio_unitario: document.getElementById('m-precio').value,
    cantidad: document.getElementById('m-cantidad').value,
    unidad: document.getElementById('m-unidad').value,
    peso_unitario: document.getElementById('m-peso').value,
  });

  const data = await apiFetch('/api/carrito/agregar_manual', { method: 'POST', body: fd });
  if (!data.ok) { toast('Error al agregar', 'error'); return; }

  const tbody = document.getElementById('tbody-carrito');
  if (!tbody) {
    // Carrito estaba vacío → recargar para mostrar la tabla completa
    _navegandoInternamente = true;
    sessionStorage.setItem('_reloadProgramatico', '1');
    window.location.reload();
    return;
  }

  // Insertar fila directamente sin recargar
  const item = data.item;
  carritoMap.set(item.id, item);

  const idx = tbody.rows.length + 1;
  const s   = sym();
  const pu  = conv(item.precio_unitario);
  const pt  = conv(item.precio_unitario * item.cantidad);

  const tr = document.createElement('tr');
  tr.id = `fila-${item.id}`;
  tr.draggable = true;
  tr.innerHTML = `
    <td style="text-align:center; padding:2px 0;">
      <span class="drag-handle" title="Arrastrar para reordenar">⠿</span>
    </td>
    <td data-label="#">${idx}</td>
    <td data-label="">
      <div style="font-size:0.875rem;">${_pl_escHtml(item.descripcion)}</div>
      <div style="font-size:0.75rem; color:var(--texto-suave);">Manual · N/A · ${item.unidad}</div>
    </td>
    <td data-label="Cant.">
      <div class="cantidad-ctrl">
        <button onclick="cambiarCant(${item.id}, -1)" aria-label="Restar cantidad">−</button>
        <input type="number" id="cant-${item.id}" value="${fmtCant(item.cantidad)}" min="0.01" max="999" step="any"
               onchange="actualizarCant(${item.id})" aria-label="Cantidad"
               inputmode="decimal" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
        <button onclick="cambiarCant(${item.id}, 1)" aria-label="Sumar cantidad">+</button>
      </div>
    </td>
    <td data-label="Und." style="text-align:center;">${item.unidad}</td>
    <td data-label="P.U." class="td-num" id="pu-${item.id}" data-precio-soles="${item.precio_unitario}">
      ${s} ${pu.toFixed(2)}
    </td>
    <td data-label="P.T." class="td-num" id="pt-${item.id}">
      ${s} ${pt.toFixed(2)}
    </td>
    <td data-label="" style="white-space:nowrap;">
      <button class="btn btn-secondary btn-sm" style="padding:0 6px; margin-right:2px;"
        onclick="abrirModalEditar(${item.id})" title="Editar ítem">✏️</button>
      <button class="btn btn-danger btn-sm" onclick="eliminarItem(${item.id})"
        aria-label="Eliminar ${_pl_escHtml(item.descripcion)}">✕</button>
    </td>`;
  tbody.appendChild(tr);

  // Scroll suave al final del contenedor de la tabla
  const tableContainer = tbody.closest('.table-container');
  if (tableContainer) {
    tableContainer.scrollTo({ top: tableContainer.scrollHeight, behavior: 'smooth' });
  }

  // Actualizar totales y contador del summary
  actualizarTotales();
  const summarySpan = document.querySelector('#det-lista summary span:first-child');
  if (summarySpan) {
    const n = carritoMap.size;
    summarySpan.textContent = `Productos (${n} item${n !== 1 ? 's' : ''})`;
  }

  // Limpiar formulario manual
  document.getElementById('m-desc').value    = '';
  document.getElementById('m-precio').value  = '0';
  document.getElementById('m-cantidad').value = '1';
  document.getElementById('m-peso').value    = '0';
  document.getElementById('m-unidad').value  = 'UND';

  toast('Producto manual agregado');
}

async function exportar(formato, btnEl) {
  if (document.querySelectorAll('#tbody-carrito tr').length === 0) {
    toast('El carrito está vacío', 'error');
    return;
  }
  const labelOriginal = btnEl ? btnEl.textContent : '';
  const labelGenerando = formato === 'xlsx' ? 'Generando XLSX…' : 'Generando PDF…';
  if (btnEl) { btnEl.disabled = true; btnEl.textContent = labelGenerando; }

  const clienteNombre = document.getElementById('cliente-nombre')?.value
    || document.getElementById('cliente-input')?.value
    || '';

  const fd = formData({
    cliente: document.getElementById('cliente')?.value || '',
    cliente_nombre: clienteNombre,
    cliente_ruc: document.getElementById('cliente-ruc')?.value || '',
    cliente_ubicacion: document.getElementById('cliente-ubicacion')?.value || '',
    atencion: document.getElementById('atencion')?.value || '',
    atencion_email: document.getElementById('atencion-email')?.value || '',
    moneda: document.getElementById('moneda')?.value || 'SOLES',
    proyecto: document.getElementById('proyecto')?.value || '',
    validez: document.getElementById('validez')?.value || '30 días',
    encabezado_tabla: document.getElementById('encabezado-tabla')?.value || '',
  });

  let resp;
  try {
    resp = await fetch(`/api/exportar/${formato}`, { method: 'POST', body: fd });
  } catch (fetchErr) {
    toast('Error de red al exportar', 'error');
    if (btnEl) { btnEl.disabled = false; btnEl.textContent = labelOriginal; }
    return;
  }
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    toast(err.error || 'Error al exportar', 'error');
    if (btnEl) { btnEl.disabled = false; btnEl.textContent = labelOriginal; }
    return;
  }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = resp.headers.get('Content-Disposition')?.match(/filename="(.+)"/)?.[1]
    || `cotizacion.${formato}`;
  a.click();
  URL.revokeObjectURL(url);
  limpiarCamposProyecto();
  // Limpiar DOM del carrito visualmente
  carritoMap.clear();
  document.getElementById('tbody-carrito').innerHTML = '';
  document.getElementById('total-display').textContent = '—';
  const _pd = document.getElementById('peso-display');
  if (_pd) _pd.textContent = '0.00 kg';
  const _mv = document.getElementById('total-movil-val');
  if (_mv) _mv.textContent = '—';
  const _pm = document.getElementById('peso-movil-val');
  if (_pm) _pm.textContent = '0.00 kg';
  const _secExp = document.querySelector('.card:has(#validez)');
  if (_secExp) _secExp.style.display = 'none';
  const msgDescargado = formato === 'xlsx' ? 'XLSX descargado — redirigiendo al historial…' : 'PDF descargado — redirigiendo al historial…';
  toast(msgDescargado, 'success');
  await fetch('/api/carrito/limpiar', { method: 'POST' });
  sessionStorage.removeItem('carrito_form_v1');
  sessionStorage.removeItem('editando_desde_cotizacion_id');
  sessionStorage.removeItem('carritoLive');
  _navegandoInternamente = true;
  setTimeout(() => { window.location.href = '/historial'; }, 2800);
}

async function guardarCotizacion() {
  const cliente = document.getElementById('cliente')?.value || '';
  const proyecto = document.getElementById('proyecto')?.value || '';
  if (!cliente && !proyecto) {
    toast('Ingrese al menos cliente o proyecto antes de guardar', 'error');
    return;
  }
  const fd = formData({
    cliente: cliente,
    cliente_nombre: document.getElementById('cliente-nombre')?.value || '',
    cliente_ruc: document.getElementById('cliente-ruc')?.value || '',
    cliente_ubicacion: document.getElementById('cliente-ubicacion')?.value || '',
    atencion: document.getElementById('atencion')?.value || '',
    atencion_email: document.getElementById('atencion-email')?.value || '',
    moneda: document.getElementById('moneda')?.value || 'SOLES',
    proyecto: proyecto,
    validez: document.getElementById('validez')?.value || '30 días',
    encabezado_tabla: document.getElementById('encabezado-tabla')?.value || '',
  });
  const data = await apiFetch('/api/historial/guardar', { method: 'POST', body: fd });
  if (data.ok) {
    limpiarCamposProyecto();
    // Limpiar DOM del carrito visualmente
    carritoMap.clear();
    document.getElementById('tbody-carrito').innerHTML = '';
    document.getElementById('total-display').textContent = '—';
    const _pd2 = document.getElementById('peso-display');
    if (_pd2) _pd2.textContent = '0.00 kg';
    const _mv2 = document.getElementById('total-movil-val');
    if (_mv2) _mv2.textContent = '—';
    const _pm2 = document.getElementById('peso-movil-val');
    if (_pm2) _pm2.textContent = '0.00 kg';
    const _secExp2 = document.querySelector('.card:has(#validez)');
    if (_secExp2) _secExp2.style.display = 'none';
    await fetch('/api/carrito/limpiar', { method: 'POST' });
    sessionStorage.removeItem('carrito_form_v1');
    sessionStorage.removeItem('editando_desde_cotizacion_id');
    sessionStorage.removeItem('carritoLive');
    toast(`Cotización #${data.id} guardada — redirigiendo al historial…`, 'success');
    _navegandoInternamente = true;
    setTimeout(() => { window.location.href = '/historial'; }, 2800);
  } else {
    toast(data.error || 'Error al guardar', 'error');
  }
}

// ── Aviso al cerrar/F5 si hay ítems (no al navegar internamente) ──
let _navegandoInternamente = false;
document.querySelectorAll('a[href^="/"]').forEach(a => {
  a.addEventListener('click', () => { _navegandoInternamente = true; });
});
window.addEventListener('beforeunload', e => {
  if (carritoMap.size > 0 && !_navegandoInternamente) {
    e.preventDefault();
    e.returnValue = '';
  }
  setTimeout(() => { _navegandoInternamente = false; }, 200);
});

// ── Persistencia del formulario ──
function restaurarFormulario() {
  let f;
  try { f = JSON.parse(sessionStorage.getItem(_FORM_KEY) || 'null'); } catch { return; }
  if (!f) return;

  if (f.cliente) {
    const _cr = CLIENTES.find(x => x.codigo === f.cliente);
    _clienteActual = { codigo: f.cliente, nombre: f.clienteNombre || '', abreviacion: _cr?.abreviacion || '' };
    document.getElementById('cliente-input').value = f.clienteInput || `${_cr?.abreviacion || f.cliente} — ${f.clienteNombre || ''}`;
    document.getElementById('cliente').value = f.cliente;
    document.getElementById('cliente-nombre').value = f.clienteNombre || '';
    document.getElementById('cliente-ruc').value = f.clienteRuc || '';
    document.getElementById('cliente-ubicacion').value = f.clienteUbicacion || '';
  }
  if (f.atencion) {
    _atencionActual = { valor: f.atencion, nombre: f.atencion };
    document.getElementById('atencion-input').value = f.atencion;
    document.getElementById('atencion').value = f.atencion;
    document.getElementById('atencion-email').value = f.atencionEmail || '';
  }
  if (f.proyecto) {
    document.getElementById('proyecto').value = f.proyecto;
  }
  if (f.encabezadoTabla) {
    const et = document.getElementById('encabezado-tabla');
    if (et) et.value = f.encabezadoTabla;
  }
  if (f.moneda) {
    const m = MONEDAS.find(x => x.valor === f.moneda) || MONEDAS[0];
    _monedaActual = { valor: m.valor, nombre: m.nombre };
    document.getElementById('moneda-input').value = m.nombre;
    document.getElementById('moneda').value = m.valor;
    if (document.getElementById('th-pu')) cambiarMoneda();
  }
  if (f.validez) {
    const vs = document.getElementById('validez');
    if (vs) vs.value = f.validez;
  }
}

document.getElementById('cliente-input')?.addEventListener('input', guardarFormulario);
document.getElementById('proyecto')?.addEventListener('input', guardarFormulario);
document.getElementById('encabezado-tabla')?.addEventListener('input', guardarFormulario);
document.getElementById('validez')?.addEventListener('change', guardarFormulario);
window.addEventListener('pagehide', guardarFormulario);

// ── Vaciar carrito real Y panel en vivo si el usuario hace F5 ──
const _navType = performance.getEntriesByType('navigation')[0]?.type;
const _yaVaciado      = sessionStorage.getItem('carritoVaciadoPorF5');
const _esProgramatico = sessionStorage.getItem('_reloadProgramatico');
sessionStorage.removeItem('_reloadProgramatico');

// ── Banner: editando copia desde historial ──
const _editandoDesdeId = sessionStorage.getItem('editando_desde_cotizacion_id');
// En F5 (reload del usuario) no restaurar los campos — deben quedar en blanco.
// En recarga programática (_esProgramatico) sí restaurar (el formulario ya fue
// limpiado antes de recargar, así que restaurar trae valores vacíos).
if (_navType === 'reload' && !_esProgramatico) {
  sessionStorage.removeItem(_FORM_KEY); // evitar que la 2ª recarga también restaure
} else {
  restaurarFormulario();
}
// Moneda: si restaurarFormulario no puso nada (o no se llamó), mostrar valor por defecto
if (!document.getElementById('moneda-input').value) {
  document.getElementById('moneda-input').value = _monedaActual.nombre;
  document.getElementById('moneda').value = _monedaActual.valor;
}
if (_editandoDesdeId) {
  const banner = document.createElement('div');
  banner.className = 'banner-editando';
  banner.innerHTML = `✏️ Editando copia de cotización <strong>#${_editandoDesdeId}</strong> — al guardar al historial se creará una <strong>nueva cotización</strong>. <button onclick="this.parentElement.remove(); sessionStorage.removeItem('editando_desde_cotizacion_id')" style="margin-left:auto; background:none; border:none; cursor:pointer; font-size:1.1rem; color:var(--texto-suave);" title="Cerrar aviso">✕</button>`;
  document.querySelector('.container')?.prepend(banner);
}
if (_navType === 'reload' && !_yaVaciado && !_esProgramatico) {
  sessionStorage.setItem('carritoVaciadoPorF5', '1');
  sessionStorage.removeItem('carritoLive');
  sessionStorage.removeItem('editando_desde_cotizacion_id');
  fetch('/api/carrito/limpiar', { method: 'POST' }).then(() => {
    _navegandoInternamente = true;
    location.reload();
  });
} else {
  sessionStorage.removeItem('carritoVaciadoPorF5');
}

// ════════════════════════════════════════════
// Modal cambio de espesor
// ════════════════════════════════════════════
let _espParte   = 'cuerpo';  // 'cuerpo' o 'tapa'
let _espItemId  = 'all';     // 'all' o número

function abrirModalEspesor(parte, itemId) {
  _espParte  = parte;
  _espItemId = String(itemId);

  const titulos = { cuerpo: 'Cambiar espesor — Cuerpos', tapa: 'Cambiar espesor — Tapas' };
  document.getElementById('modal-esp-titulo').textContent = titulos[parte] || 'Cambiar espesor';

  const scope = itemId === 'all'
    ? `Todos los <strong>${parte === 'tapa' ? 'tapas' : 'cuerpos'}</strong> del carrito serán recalculados.`
    : `Solo este ítem será recalculado. Los ítems manuales o de catálogo se omiten automáticamente.`;
  document.getElementById('modal-esp-desc').innerHTML =
    scope + '<br><span style="font-size:0.8em;color:#888;">Nota: el precio se ajusta proporcionalmente al precio de plancha configurado.</span>';

  document.getElementById('modal-esp-aviso').style.display = 'none';
  document.getElementById('modal-espesor').style.display = 'flex';
}

function abrirModalEspesorItem(itemId) {
  // Detectar automáticamente si el ítem es cuerpo o tapa
  const item = carritoMap.get(itemId);
  if (!item) return;
  const esTapa = item.descripcion.toUpperCase().includes('TAPA');
  abrirModalEspesor(esTapa ? 'tapa' : 'cuerpo', itemId);
  // Ajustar título para ítem específico
  document.getElementById('modal-esp-titulo').textContent =
    esTapa ? 'Cambiar espesor — Esta tapa' : 'Cambiar espesor — Este cuerpo';
  document.getElementById('modal-esp-desc').innerHTML =
    `<strong>Ítem:</strong> ${item.descripcion.slice(0, 80)}${item.descripcion.length > 80 ? '…' : ''}` +
    '<br><span style="font-size:0.8em;color:#888;">Los ítems manuales o de catálogo no son recalculables.</span>';
}

function cerrarModalEspesor() {
  document.getElementById('modal-espesor').style.display = 'none';
}

document.getElementById('modal-espesor').addEventListener('click', function(e) {
  if (e.target === this) cerrarModalEspesor();
});

// ════════════════════════════════════════════
// Modal editar ítem
// ════════════════════════════════════════════

// Actualiza la descripción cuando el usuario cambia Con/Sin tapa
function _actualizarDescConTapa(val) {
  const descEl = document.getElementById('edit-desc');
  let desc = descEl.value;
  if (val === 'no') {
    const pares = [
      [/\(C\/UNI[ÓO]N\s+Y\s+TAPA\)/gi, '(C/UNIÓN SIN TAPA)'],
      [/\bCON\s+TAPA\b/gi, 'SIN TAPA'],
      [/\bC\/TAPA\b/gi, 'SIN TAPA'],
      [/\bC\/T\b/gi, 'S/T'],
    ];
    let changed = false;
    for (const [re, repl] of pares) {
      const nuevo = desc.replace(re, repl);
      if (nuevo !== desc) { desc = nuevo; changed = true; break; }
    }
    if (!changed && !/SIN\s+TAPA/i.test(desc)) desc = desc.trimEnd() + ' SIN TAPA';
  } else {
    const pares = [
      [/\(C\/UNI[ÓO]N\s+SIN\s+TAPA\)/gi, '(C/UNIÓN Y TAPA)'],
      [/\bSIN\s+TAPA\b/gi, 'C/TAPA'],
      [/\bS\/T\b/gi, 'C/T'],
    ];
    for (const [re, repl] of pares) {
      const nuevo = desc.replace(re, repl);
      if (nuevo !== desc) { desc = nuevo; break; }
    }
  }
  descEl.value = desc;
}

document.querySelectorAll('input[name="edit-con-tapa"]').forEach(r =>
  r.addEventListener('change', () => _actualizarDescConTapa(r.value))
);

// Flag para saber si el modal está editando una tapa separada
let _editandoTapaSep = false;
// Precio original del ítem al abrir el modal (para detectar cambio manual)
let _editPrecioOriginal = null;
// Parámetros de cálculo originales (para detectar si el usuario los cambió)
let _editCalcOrig = null;

// Actualiza el textarea readonly de la tapa separada cuando cambia el espesor
document.querySelectorAll('input[name="edit-esp-tapa"]').forEach(r =>
  r.addEventListener('change', () => {
    if (!_editandoTapaSep) return;
    const nuevoEsp = r.value; // e.g. "2.0"
    const descEl = document.getElementById('edit-desc');
    // Reemplaza todos los valores decimales seguidos de MM (ej: 1.5MM → 2.0MM)
    descEl.value = descEl.value.replace(/\b(\d+\.\d+)MM\b/gi, nuevoEsp + 'MM');
  })
);

function _renderUnidadContainer(esManual, tipo, unidad) {
  const cont = document.getElementById('edit-unidad-container');
  if (esManual) {
    cont.innerHTML = `<input type="text" id="edit-und-text" class="form-control" value="${_pl_escHtml(unidad)}"
      style="text-transform:uppercase;" autocorrect="off" autocapitalize="characters" spellcheck="false">`;
  } else {
    // Bandejas: radio UND/ML; otros: select estándar
    if (tipo === 'B') {
      const sel = (u) => u === unidad ? ' checked' : '';
      cont.innerHTML = `<div style="display:flex; gap:0.9rem; padding-top:0.45rem; flex-wrap:wrap;">
        <label style="display:flex;align-items:center;gap:5px;font-size:0.82rem;cursor:pointer;">
          <input type="radio" name="edit-unidad-radio" value="UND" id="edit-unidad-und"${sel('UND')}> UND
        </label>
        <label style="display:flex;align-items:center;gap:5px;font-size:0.82rem;cursor:pointer;">
          <input type="radio" name="edit-unidad-radio" value="ML" id="edit-unidad-ml"${sel('ML')}> ML
        </label>
      </div>`;
    } else {
      const opts = ['UND','ML','M2','KG','JGO'].map(u =>
        `<option value="${u}"${u === unidad ? ' selected' : ''}>${u}</option>`
      ).join('');
      cont.innerHTML = `<select id="edit-und-text" class="form-control">${opts}</select>`;
    }
  }
}

function abrirModalEditar(itemId) {
  const item = carritoMap.get(itemId);
  if (!item) return;
  const esManual   = item.tipo_galvanizado === 'N/A';
  const esTapaSep  = !!item.tapa_para_id;
  const ESP_VALIDOS = [1.2, 1.5, 2.0];

  _editandoTapaSep = esTapaSep;

  document.getElementById('edit-id').value = itemId;
  document.getElementById('edit-tipo').value = item.tipo || '';
  document.getElementById('edit-tipo-galv').value = item.tipo_galvanizado || '';
  document.getElementById('edit-es-manual').value = esManual ? '1' : '0';

  // Descripción: readonly para tapas separadas (se recalcula desde el cuerpo en el backend)
  const descEl = document.getElementById('edit-desc');
  descEl.value    = item.descripcion;
  descEl.readOnly = esTapaSep;
  descEl.style.color      = esTapaSep ? 'var(--texto-suave,#6b7280)' : '';
  descEl.style.background = esTapaSep ? 'var(--fondo-tabla,#f4f7fc)' : '';
  descEl.title = esTapaSep ? 'La descripción se genera automáticamente desde el cuerpo' : '';

  // Precio: tapas separadas → sin redondeo al alza (lo calcula el backend)
  const precioEl = document.getElementById('edit-precio');
  const precioMostrado = esTapaSep
    ? parseFloat(item.precio_unitario).toFixed(2)
    : (Math.ceil(item.precio_unitario * 100) / 100).toFixed(2);
  precioEl.value    = precioMostrado;
  _editPrecioOriginal = parseFloat(precioMostrado);
  precioEl.readOnly = esTapaSep;
  precioEl.style.color      = esTapaSep ? 'var(--texto-suave,#6b7280)' : '';
  precioEl.style.background = esTapaSep ? 'var(--fondo-tabla,#f4f7fc)' : '';

  // Unidad: tapas separadas → texto fijo (unidad bloqueada al cuerpo)
  if (esTapaSep) {
    document.getElementById('edit-unidad-container').innerHTML =
      `<span style="padding-top:0.45rem; display:inline-block; color:var(--texto-suave,#6b7280); font-size:0.85rem;">${item.unidad}</span>`;
  } else {
    _renderUnidadContainer(esManual, item.tipo, item.unidad);
  }

  // Avanzado: solo para calculados
  document.getElementById('edit-avanzado').style.display = esManual ? 'none' : '';

  if (!esManual) {
    // Comisión: ocultar para tapas separadas (bloqueada al cuerpo)
    document.getElementById('edit-comision-row').style.display = esTapaSep ? 'none' : '';
    if (!esTapaSep) {
      const ganEl = document.getElementById(`edit-ganancia-${item.porcentaje_ganancia || '30'}`);
      if (ganEl) ganEl.checked = true; else document.getElementById('edit-ganancia-30').checked = true;
    }

    // Espesor: leer MM de la descripcion_calculada (cuerpo) o descripcion (tapa sep)
    const descRef = esTapaSep
      ? (item.descripcion || '')
      : (item.descripcion_calculada || item.descripcion);
    const mmVals = [...descRef.matchAll(/(\d+\.\d+)MM/gi)].map(m => parseFloat(m[1]));
    const espC = ESP_VALIDOS.includes(mmVals[0]) ? mmVals[0].toFixed(1) : '1.5';
    let espT;
    if (esTapaSep) {
      espT = espC; // para tapa sep, el único MM en su descripcion es el de la tapa
    } else {
      // Si hay tapa vinculada como ítem separado, leer su espesor de ese ítem directamente
      const _tapaVinc = Array.from(carritoMap.values()).find(i => i.tapa_para_id === itemId);
      if (_tapaVinc) {
        const _mmT = [...(_tapaVinc.descripcion || '').matchAll(/(\d+\.\d+)MM/gi)].map(m => parseFloat(m[1]));
        espT = ESP_VALIDOS.includes(_mmT[0]) ? _mmT[0].toFixed(1) : espC;
      } else {
        espT = ESP_VALIDOS.includes(mmVals[1]) ? mmVals[1].toFixed(1) : espC;
      }
    }
    const ecEl = document.querySelector(`input[name="edit-esp-cuerpo"][value="${espC}"]`);
    if (ecEl) ecEl.checked = true;
    const etEl = document.querySelector(`input[name="edit-esp-tapa"][value="${espT}"]`);
    if (etEl) etEl.checked = true;

    // Espesor cuerpo: ocultar para tapas separadas
    document.getElementById('edit-esp-cuerpo-row').style.display = esTapaSep ? 'none' : '';

    // Espesor tapa: ocultar para CP
    document.getElementById('edit-esp-tapa-row').style.display = (item.tipo === 'CP') ? 'none' : '';

    // Fila unidad: solo bandejas (mostrada dentro del container, no en avanzado)
    document.getElementById('edit-unidad-row').style.display = 'none';

    // Fila tapa (Con/Sin): ocultar para tapas separadas y CP
    const tapaRow = document.getElementById('edit-tapa-row');
    if (!esTapaSep && item.tipo !== 'CP') {
      tapaRow.style.display = '';
      const _tapaRe = /\bC[\/\\]?TAPA\b|\bCON\s+TAPA\b|\(C\/UNI[ÓO]N\s+Y\s+TAPA\)|\+\s*TAPA\b|\bY\s+TAPA\b/i;
      const tieneTapaEnDesc = (item.descripcion_calculada || '').toUpperCase().includes('+ TAPA')
                              || _tapaRe.test(item.descripcion || '');
      // Si hay una tapa vinculada como ítem separado, también hay tapa
      const tieneTapaVinculada = Array.from(carritoMap.values()).some(i => i.tapa_para_id === itemId);
      const tapVal = (tieneTapaEnDesc || tieneTapaVinculada) ? 'si' : 'no';
      const tapaEl = document.querySelector(`input[name="edit-con-tapa"][value="${tapVal}"]`);
      if (tapaEl) tapaEl.checked = true;
    } else {
      tapaRow.style.display = 'none';
    }
  }

  // Ítem programa: solo para manuales
  const progGroup = document.getElementById('edit-item-prog-group');
  if (esManual && item.descripcion_calculada) {
    progGroup.style.display = '';
    document.getElementById('edit-item-prog').value = item.descripcion_calculada;
  } else {
    progGroup.style.display = 'none';
    document.getElementById('edit-item-prog').value = '';
  }
  // Guardar parámetros de cálculo originales para detectar si cambian
  if (!esManual) {
    const ganEl = document.querySelector('input[name="edit-ganancia"]:checked');
    const ecEl  = document.querySelector('input[name="edit-esp-cuerpo"]:checked');
    const etEl  = document.querySelector('input[name="edit-esp-tapa"]:checked');
    const ctEl  = document.querySelector('input[name="edit-con-tapa"]:checked');
    _editCalcOrig = {
      ganancia:     ganEl ? ganEl.value : '30',
      espCuerpo:    ecEl  ? ecEl.value  : '1.5',
      espTapa:      etEl  ? etEl.value  : '1.5',
      conTapa:      ctEl  ? ctEl.value  : 'si',
    };
  } else {
    _editCalcOrig = null;
  }

  document.getElementById('modal-editar').style.display = 'flex';
  setTimeout(() => document.getElementById('edit-desc').focus(), 50);
}

function cerrarModalEditar() {
  document.getElementById('modal-editar').style.display = 'none';
}

document.getElementById('modal-editar').addEventListener('click', function(e) {
  if (e.target === this) cerrarModalEditar();
});

document.getElementById('modal-editar').addEventListener('keydown', function(e) {
  if (e.key !== 'Enter') return;
  // Ctrl+Enter desde textarea guarda; Enter simple dentro de textarea inserta salto
  if (e.target.tagName === 'TEXTAREA' && !e.ctrlKey) return;
  // No disparar si el foco está en un botón
  if (e.target.tagName === 'BUTTON') return;
  e.preventDefault();
  guardarEdicion();
});

async function guardarEdicion() {
  const itemId    = document.getElementById('edit-id').value;
  const desc      = document.getElementById('edit-desc').value.trim();
  const esManual  = document.getElementById('edit-es-manual').value === '1';
  const prog      = document.getElementById('edit-item-prog').value.trim();

  if (!desc) { toast('La descripción no puede estar vacía', 'error'); return; }

  const btn = document.getElementById('btn-guardar-edicion');
  btn.disabled = true; btn.textContent = 'Guardando…';

  // Leer unidad del contenedor dinámico
  function _leerUnidad() {
    const radio = document.querySelector('input[name="edit-unidad-radio"]:checked');
    if (radio) return radio.value;
    const sel = document.getElementById('edit-und-text');
    return sel ? sel.value.trim().toUpperCase() || 'UND' : 'UND';
  }

  let data;
  if (esManual) {
    const und    = _leerUnidad();
    const precio = parseFloat(document.getElementById('edit-precio').value);
    if (isNaN(precio) || precio < 0) { toast('Precio inválido', 'error'); btn.disabled = false; btn.textContent = 'Guardar'; return; }
    const precioRedondeado = Math.ceil(precio * 100) / 100;
    const fd = formData({ descripcion: desc, unidad: und, precio_unitario: precioRedondeado, descripcion_calculada: prog });
    data = await apiFetch(`/api/carrito/editar/${itemId}`, { method: 'POST', body: fd });
  } else {
    const ganancia  = document.querySelector('input[name="edit-ganancia"]:checked')?.value || '30';
    const espCuerpo = document.querySelector('input[name="edit-esp-cuerpo"]:checked')?.value || '1.5';
    const espTapa   = document.querySelector('input[name="edit-esp-tapa"]:checked')?.value || espCuerpo;
    const conTapa   = document.querySelector('input[name="edit-con-tapa"]:checked')?.value || 'si';
    const und       = _leerUnidad();
    const precioActual = parseFloat(document.getElementById('edit-precio').value);
    const precioChanged = !isNaN(precioActual) && precioActual >= 0 && _editPrecioOriginal !== null
      && Math.abs(precioActual - _editPrecioOriginal) > 0.001;

    // Si ningún parámetro de cálculo cambió → solo actualizar desc/precio sin recalcular
    const calcCambio = !_editCalcOrig
      || ganancia  !== _editCalcOrig.ganancia
      || espCuerpo !== _editCalcOrig.espCuerpo
      || espTapa   !== _editCalcOrig.espTapa
      || conTapa   !== _editCalcOrig.conTapa;

    if (!calcCambio) {
      const item = carritoMap.get(itemId);
      const precioFinal = precioChanged
        ? Math.ceil(precioActual * 100) / 100
        : item?.precio_unitario ?? _editPrecioOriginal;
      const fd = formData({ descripcion: desc, unidad: und, precio_unitario: precioFinal,
        descripcion_calculada: item?.descripcion_calculada ?? '' });
      data = await apiFetch(`/api/carrito/editar/${itemId}`, { method: 'POST', body: fd });
    } else {
      const precioOverride = precioChanged ? precioActual : null;
      const fd = formData({
        descripcion: desc, ganancia, espesor_cuerpo: espCuerpo, espesor_tapa: espTapa,
        unidad: und, con_tapa: conTapa,
        ...(precioOverride !== null ? { precio_override: precioOverride } : {}),
      });
      data = await apiFetch(`/api/carrito/recalcular/${itemId}`, { method: 'POST', body: fd });
    }
  }

  btn.disabled = false; btn.textContent = 'Guardar';
  if (data.ok) {
    cerrarModalEditar();
    toast('Ítem actualizado', 'success');

    // Actualizar la fila del cuerpo in-place (sin recargar → mantiene scroll)
    if (data.cuerpo) _actualizarFilaCarrito(data.cuerpo);

    // Manejar tapa vinculada
    if (data.tapa_action === 'updated' && data.tapa) {
      _actualizarFilaCarrito(data.tapa);
    } else if (data.tapa_action === 'deleted' && data.tapa_id) {
      _eliminarFilaCarrito(data.tapa_id);
    }

    actualizarTotales();
  } else {
    toast(data.error || 'Error al guardar', 'error');
  }
}

async function convertirAML(itemId) {
  if (!confirm('¿Convertir este ítem de UND a ML (metro lineal)?\nEl precio y peso se dividirán por 2.4.')) return;
  const data = await apiFetch(`/api/carrito/und_a_ml/${itemId}`, { method: 'POST' });
  if (data.ok) {
    toast('Convertido a ML', 'success');
    _navegandoInternamente = true;
    sessionStorage.setItem('_reloadProgramatico', '1');
    setTimeout(() => window.location.reload(), 600);
  } else {
    toast(data.error || 'Error al convertir', 'error');
  }
}

// ── Drag & Drop reordering ──
let _dragId           = null;
let _dropTargetId     = null;
let _dropBefore       = true;
let _ptrOnHandle      = false;  // rastrear si pointerdown fue sobre el handle

function _ddIndicator() {
  let el = document.getElementById('dd-drop-line');
  if (!el) {
    el = document.createElement('tr');
    el.id = 'dd-drop-line';
    el.innerHTML = `<td colspan="8" class="dd-drop-cell"></td>`;
  }
  return el;
}

function _ddCleanup(tbody) {
  document.getElementById('dd-drop-line')?.remove();
  tbody?.querySelectorAll('.dd-dragging').forEach(r => r.classList.remove('dd-dragging'));
  _dragId = null;
  _dropTargetId = null;
  _ptrOnHandle = false;
}

function _initDragDrop() {
  const tbody = document.getElementById('tbody-carrito');
  if (!tbody || tbody._ddBound) return;
  tbody._ddBound = true;

  // Registrar si el puntero bajó sobre el handle (antes de que dispare dragstart)
  tbody.addEventListener('pointerdown', e => {
    _ptrOnHandle = !!e.target.closest('.drag-handle');
  });

  tbody.addEventListener('dragstart', e => {
    // Solo permitir el drag si el gesto empezó sobre el handle
    if (!_ptrOnHandle) { e.preventDefault(); return; }
    const tr = e.target.closest('tr');
    if (!tr || tr.classList.contains('fila-tapa-sep')) { e.preventDefault(); return; }

    _dragId = parseInt(tr.id.replace('fila-', ''));
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(_dragId));

    // Diferir la clase para que el ghost del navegador no la capture
    requestAnimationFrame(() => {
      tr.classList.add('dd-dragging');
      const tapa = tbody.querySelector(`tr[data-tapa-de="${_dragId}"]`);
      if (tapa) tapa.classList.add('dd-dragging');
    });
  });

  tbody.addEventListener('dragend', () => _ddCleanup(tbody));

  tbody.addEventListener('dragover', e => {
    if (_dragId === null) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const tr = e.target.closest('tr');
    if (!tr || !tr.id?.startsWith('fila-')) return;
    const tid = parseInt(tr.id.replace('fila-', ''));
    if (isNaN(tid) || tid === _dragId || tr.dataset.tapaDe) return;

    const rect = tr.getBoundingClientRect();
    const before = e.clientY < rect.top + rect.height / 2;

    if (tid === _dropTargetId && before === _dropBefore) return;
    _dropTargetId = tid;
    _dropBefore   = before;

    const ind = _ddIndicator();
    if (before) {
      tbody.insertBefore(ind, tr);
    } else {
      const tapa = tbody.querySelector(`tr[data-tapa-de="${tid}"]`);
      const after = tapa || tr;
      after.after(ind);
    }
  });

  tbody.addEventListener('dragleave', e => {
    if (!tbody.contains(e.relatedTarget)) {
      document.getElementById('dd-drop-line')?.remove();
      _dropTargetId = null;
    }
  });

  tbody.addEventListener('drop', async e => {
    e.preventDefault();
    if (_dragId === null || _dropTargetId === null) { _ddCleanup(tbody); return; }

    // Calcular nuevo orden a partir del DOM actual (sin las clases dd-dragging)
    const cuerpos = [...tbody.querySelectorAll('tr[draggable]:not(.fila-tapa-sep)')]
      .filter(tr => !tr.classList.contains('dd-dragging'))
      .map(tr => parseInt(tr.id.replace('fila-', '')));

    const targetIdx = cuerpos.indexOf(_dropTargetId);
    const insertAt  = _dropBefore ? targetIdx : targetIdx + 1;
    cuerpos.splice(insertAt, 0, _dragId);

    _ddCleanup(tbody);

    const fd = formData({ orden: JSON.stringify(cuerpos) });
    const data = await apiFetch('/api/carrito/reordenar', { method: 'POST', body: fd });
    if (data.ok && data.carrito) {
      _reconstruirTablaCarrito(data.carrito);
    } else {
      toast('Error al reordenar', 'error');
    }
  });
}

document.addEventListener('DOMContentLoaded', _initDragDrop);

// ── Drag-and-drop táctil (mobile) ──
function _initTouchDrag() {
  const tbody = document.getElementById('tbody-carrito');
  if (!tbody || tbody._touchBound) return;
  tbody._touchBound = true;

  let _tid      = null;   // id del item arrastrado
  let _clone    = null;   // elemento flotante
  let _offX     = 0;      // offset dedo dentro del clone
  let _offY     = 0;
  let _targetId = null;   // id del item objetivo
  let _before   = true;

  function _removeClone() { _clone?.remove(); _clone = null; }

  function _onTouchMove(e) {
    if (_tid === null || !_clone) return;
    e.preventDefault();
    const t = e.touches[0];
    _clone.style.left = (t.clientX - _offX) + 'px';
    _clone.style.top  = (t.clientY - _offY) + 'px';

    // Detectar fila bajo el dedo
    _clone.style.visibility = 'hidden';
    const el = document.elementFromPoint(t.clientX, t.clientY);
    _clone.style.visibility = '';
    const tr = el?.closest('tr');
    if (!tr || !tr.id?.startsWith('fila-') || tr.dataset.tapaDe) return;
    const targetId = parseInt(tr.id.replace('fila-', ''));
    if (isNaN(targetId) || targetId === _tid) return;

    const rect = tr.getBoundingClientRect();
    _before = t.clientY < rect.top + rect.height / 2;
    _targetId = targetId;
    const ind = _ddIndicator();
    if (_before) { tbody.insertBefore(ind, tr); }
    else { const tapa = tbody.querySelector(`tr[data-tapa-de="${targetId}"]`); (tapa || tr).after(ind); }
  }

  async function _onTouchEnd() {
    document.removeEventListener('touchmove', _onTouchMove);
    document.removeEventListener('touchend',  _onTouchEnd);
    document.removeEventListener('touchcancel', _onTouchEnd);

    _removeClone();
    tbody.querySelectorAll('.dd-dragging').forEach(r => r.classList.remove('dd-dragging'));
    document.getElementById('dd-drop-line')?.remove();

    if (_tid !== null && _targetId !== null) {
      const cuerpos = [...tbody.querySelectorAll('tr[draggable]:not(.fila-tapa-sep)')]
        .filter(r => parseInt(r.id.replace('fila-', '')) !== _tid)
        .map(r => parseInt(r.id.replace('fila-', '')));
      const idx = cuerpos.indexOf(_targetId);
      cuerpos.splice(_before ? idx : idx + 1, 0, _tid);

      const fd = formData({ orden: JSON.stringify(cuerpos) });
      const data = await apiFetch('/api/carrito/reordenar', { method: 'POST', body: fd });
      if (data.ok && data.carrito) { _reconstruirTablaCarrito(data.carrito); }
      else { toast('Error al reordenar', 'error'); }
    }
    _tid = null; _targetId = null;
  }

  tbody.addEventListener('touchstart', e => {
    const handle = e.target.closest('.drag-handle');
    if (!handle) return;
    const tr = handle.closest('tr');
    if (!tr || tr.classList.contains('fila-tapa-sep')) return;

    _tid = parseInt(tr.id.replace('fila-', ''));
    const touch = e.touches[0];
    const rect = tr.getBoundingClientRect();
    _offX = touch.clientX - rect.left;
    _offY = touch.clientY - rect.top;

    const cloneEl = tr.cloneNode(true);
    cloneEl.id = '';
    cloneEl.className = 'dd-touch-clone';
    cloneEl.style.width = rect.width + 'px';
    cloneEl.style.left  = (touch.clientX - _offX) + 'px';
    cloneEl.style.top   = (touch.clientY - _offY) + 'px';
    document.body.appendChild(cloneEl);
    _clone = cloneEl;

    requestAnimationFrame(() => {
      tr.classList.add('dd-dragging');
      tbody.querySelector(`tr[data-tapa-de="${_tid}"]`)?.classList.add('dd-dragging');
    });

    document.addEventListener('touchmove',   _onTouchMove,  { passive: false });
    document.addEventListener('touchend',    _onTouchEnd);
    document.addEventListener('touchcancel', _onTouchEnd);
  }, { passive: true });
}

document.addEventListener('DOMContentLoaded', _initTouchDrag);

// ── Tapas juntas / separadas ──
let _tapasModo = 'junto'; // 'junto' | 'separada'

function _actualizarBtnTapas() {
  const btn = document.getElementById('btn-tapas-modo');
  if (!btn) return;
  if (_tapasModo === 'junto') {
    btn.textContent = 'Tapas: juntas';
    btn.style.cssText = '';
  } else {
    btn.textContent = 'Tapas: separadas';
    btn.style.background = '#e8f0fb';
    btn.style.borderColor = '#2563eb';
    btn.style.color = '#2563eb';
    btn.style.fontWeight = '600';
  }
}

async function toggleTapasModo() {
  const btn = document.getElementById('btn-tapas-modo');
  btn.disabled = true;

  if (_tapasModo === 'junto') {
    const data = await apiFetch('/api/carrito/separar_tapas', { method: 'POST' });
    btn.disabled = false;
    if (!data.ok) { toast('Error al separar tapas', 'error'); return; }
    if (data.separados > 0) {
      _tapasModo = 'separada';
      _actualizarBtnTapas();
      if (data.carrito) _reconstruirTablaCarrito(data.carrito);
      toast(`${data.separados} ítem(s) separados en cuerpo + tapa`, 'success');
    } else {
      toast('No hay ítems con tapa combinada para separar', 'error');
    }
  } else {
    const data = await apiFetch('/api/carrito/juntar_tapas', { method: 'POST' });
    btn.disabled = false;
    if (!data.ok) { toast('Error al juntar tapas', 'error'); return; }
    if (data.juntados > 0) {
      _tapasModo = 'junto';
      _actualizarBtnTapas();
      if (data.carrito) _reconstruirTablaCarrito(data.carrito);
      toast(`${data.juntados} tapa(s) unidas a su cuerpo`, 'success');
    } else {
      toast('No hay tapas separadas para unir', 'error');
    }
  }
}

// Detectar modo inicial según si hay filas de tapa separada
document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelectorAll('.fila-tapa-sep').length > 0) {
    _tapasModo = 'separada';
    _actualizarBtnTapas();
  }
});

// importar.js se carga después de este bloque
async function aplicarEspesor() {
  const nuevoEspesor = document.getElementById('modal-esp-select').value;
  const btn = document.getElementById('btn-aplicar-espesor');
  btn.disabled = true;
  btn.textContent = 'Aplicando…';

  const fd = formData({
    nuevo_espesor: nuevoEspesor,
    parte: _espParte,
    item_id: _espItemId,
  });

  const data = await apiFetch('/api/carrito/cambiar_espesor', { method: 'POST', body: fd });

  btn.disabled = false;
  btn.textContent = 'Aplicar';

  if (!data.ok) {
    toast(data.error || 'Error al cambiar espesor', 'error');
    return;
  }

  let msg = `${data.actualizados} ítem(s) actualizados a ${nuevoEspesor} mm.`;

  if (data.omitidos && data.omitidos.length > 0) {
    // Mostrar aviso en el modal antes de cerrar
    const avisoEl = document.getElementById('modal-esp-aviso');
    avisoEl.innerHTML = `<strong>⚠️ ${data.omitidos.length} ítem(s) omitidos</strong> (manuales o sin cálculo predeterminado):<ul style="margin:0.4rem 0 0; padding-left:1.2rem;">` +
      data.omitidos.map(d => `<li style="font-size:0.78rem;">${d.slice(0, 70)}${d.length > 70 ? '…' : ''}</li>`).join('') +
      '</ul>';
    avisoEl.style.display = 'block';
    msg += ` (${data.omitidos.length} omitidos — ver detalle en el modal)`;
    toast(msg, data.actualizados > 0 ? 'success' : 'error');
    // No cerrar aún para que el usuario lea los omitidos
    if (data.actualizados > 0) {
      setTimeout(() => {
        cerrarModalEspesor();
        sessionStorage.setItem('_reloadProgramatico', '1');
        _navegandoInternamente = true;
        window.location.reload();
      }, 3500);
    }
  } else {
    cerrarModalEspesor();
    if (data.actualizados > 0) {
      toast(msg, 'success');
      sessionStorage.setItem('_reloadProgramatico', '1');
      _navegandoInternamente = true;
      setTimeout(() => window.location.reload(), 700);
    } else {
      toast('No hay ítems para cambiar con esos parámetros.', 'error');
    }
  }
}

// ════════════════════════════════════════════
// Ver planchas necesarias
// ════════════════════════════════════════════

function _pl_hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${alpha})`;
}
function _pl_escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function _pl_renderCanvas(canvasEl, binW, binH, piezasColocadas, cortes) {
  const dpr = window.devicePixelRatio || 1;
  const wrap = canvasEl.parentElement;
  const maxW = Math.max(200, (wrap.clientWidth || 700) - 8);
  const maxH = 460;
  const scale = Math.min(maxW / binW, maxH / binH);

  // Tamaño CSS (lo que se ve en pantalla)
  const cssW = Math.round(binW * scale);
  const cssH = Math.round(binH * scale);

  // Tamaño físico del buffer (dpr × para pantallas de alta densidad)
  canvasEl.width  = Math.round(cssW * dpr);
  canvasEl.height = Math.round(cssH * dpr);
  canvasEl.style.width  = cssW + 'px';
  canvasEl.style.height = cssH + 'px';
  canvasEl.style.maxWidth = '100%';

  const ctx = canvasEl.getContext('2d');
  ctx.scale(dpr, dpr);   // a partir de aquí todo se dibuja en coordenadas CSS

  // Fondo
  ctx.fillStyle = '#dde6f5';
  ctx.fillRect(0, 0, cssW, cssH);

  // Grilla de referencia
  ctx.strokeStyle = 'rgba(150,175,215,0.35)'; ctx.lineWidth = 0.5;
  const gStep = 200 * scale;
  for (let x = gStep; x < cssW; x += gStep) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,cssH); ctx.stroke(); }
  for (let y = gStep; y < cssH; y += gStep) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(cssW,y); ctx.stroke(); }

  // Piezas
  for (const p of piezasColocadas) {
    const px=p.x*scale, py=p.y*scale, pw=p.ancho_colocado*scale, ph=p.alto_colocado*scale;
    ctx.fillStyle = _pl_hexToRgba(p.color, 0.72);
    ctx.fillRect(px, py, pw, ph);
    ctx.strokeStyle = p.color; ctx.lineWidth = 1.5;
    ctx.strokeRect(px+0.75, py+0.75, pw-1.5, ph-1.5);

    const minDim = Math.min(pw, ph);
    if (minDim > 12) {
      const isPortrait = ph > pw * 1.4;
      const textW = isPortrait ? ph : pw;
      const textH = isPortrait ? pw : ph;
      const sd = Math.min(pw, ph), ld = Math.max(pw, ph);
      const fsDim = Math.max(6, Math.min(14, Math.min(sd * 0.22, ld * 0.085)));
      const fsNom = Math.max(5, fsDim * 0.80);
      const cx = px + pw / 2, cy = py + ph / 2;
      ctx.save();
      ctx.beginPath(); ctx.rect(px + 1, py + 1, pw - 2, ph - 2); ctx.clip();
      if (isPortrait) { ctx.translate(cx, cy); ctx.rotate(-Math.PI / 2); ctx.translate(-cx, -cy); }
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(255,255,255,0.92)';
      const dimLbl = `${p.ancho_original}×${p.alto_original}`;
      ctx.font = `${fsNom}px system-ui,sans-serif`;
      const maxLineW = textW * 0.92;
      const nomLines = [];
      let curLine = '';
      for (const word of (p.nombre || '').split(' ')) {
        const test = curLine ? curLine + ' ' + word : word;
        if (ctx.measureText(test).width <= maxLineW) { curLine = test; }
        else { if (curLine) nomLines.push(curLine); curLine = word; }
      }
      if (curLine) nomLines.push(curLine);
      const lineH = fsNom * 1.25, dimLineH = fsDim * 1.25;
      const maxNomLines = Math.max(0, Math.floor((textH * 0.88 - dimLineH) / lineH));
      const visLines = nomLines.slice(0, maxNomLines);
      const blockH = dimLineH + visLines.length * lineH;
      const yTop = cy - blockH / 2;
      ctx.font = `700 ${fsDim}px system-ui,sans-serif`;
      ctx.fillText(dimLbl, cx, yTop + fsDim * 0.5);
      ctx.font = `${fsNom}px system-ui,sans-serif`;
      visLines.forEach((line, i) => ctx.fillText(line, cx, yTop + dimLineH + lineH * (i + 0.45)));
      ctx.restore();
    }
  }

  // Líneas de corte
  for (const c of cortes) {
    ctx.setLineDash([5, 4]); ctx.lineWidth = 1;
    if (c.tipo === 'H') {
      ctx.strokeStyle = 'rgba(22,160,133,0.75)';
      ctx.beginPath(); ctx.moveTo(c.desde*scale, c.posicion*scale); ctx.lineTo(c.hasta*scale, c.posicion*scale); ctx.stroke();
    } else {
      ctx.strokeStyle = 'rgba(211,84,0,0.75)';
      ctx.beginPath(); ctx.moveTo(c.posicion*scale, c.desde*scale); ctx.lineTo(c.posicion*scale, c.hasta*scale); ctx.stroke();
    }
  }

  // Borde exterior y dimensión
  ctx.setLineDash([]);
  ctx.strokeStyle = '#7b96c0'; ctx.lineWidth = 2;
  ctx.strokeRect(1, 1, cssW - 2, cssH - 2);
  ctx.fillStyle = '#4a6080'; ctx.font = '10px system-ui,sans-serif';
  ctx.textAlign = 'left'; ctx.textBaseline = 'top';
  ctx.fillText(`${binW}×${binH}mm`, 5, 4);
}

const _plModalData = {}; // { grupoIdx: { planchas, binW, binH } }
const _plModalTabs  = {};
let   _plModalGrupos = null; // data.grupos completo para PDF

function _plDownloadHD(gi) {
  const gData = _plModalData[gi];
  if (!gData) return;
  const ti = _plModalTabs[gi] || 0;
  const pl = gData.planchas[ti];
  if (!pl) return;
  const binW = gData.binW, binH = gData.binH;
  const hdScale = 4;
  const tmpCanvas = document.createElement('canvas');
  tmpCanvas.width  = binW * hdScale / 2;
  tmpCanvas.height = binH * hdScale / 2;
  const ctx = tmpCanvas.getContext('2d');
  const w = tmpCanvas.width, h = tmpCanvas.height;
  const scale = Math.min(w / binW, h / binH);
  ctx.fillStyle = '#dde6f5';
  ctx.fillRect(0, 0, w, h);
  const gStep = 200 * scale;
  ctx.strokeStyle = 'rgba(150,175,215,0.35)'; ctx.lineWidth = 1;
  for (let x = gStep; x < w; x += gStep) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,h); ctx.stroke(); }
  for (let y = gStep; y < h; y += gStep) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.stroke(); }
  for (const p of pl.piezas) {
    const px=p.x*scale, py=p.y*scale, pw=p.ancho_colocado*scale, ph=p.alto_colocado*scale;
    ctx.fillStyle = _pl_hexToRgba(p.color, 0.72);
    ctx.fillRect(px,py,pw,ph);
    ctx.strokeStyle = p.color; ctx.lineWidth = 3;
    ctx.strokeRect(px+1.5,py+1.5,pw-3,ph-3);
    const minDim = Math.min(pw,ph);
    if (minDim > 24) {
      const isPortrait = ph > pw * 1.4;
      const textW = isPortrait ? ph : pw;
      const textH = isPortrait ? pw : ph;
      const sd = Math.min(pw, ph), ld = Math.max(pw, ph);
      const fsDim = Math.max(12, Math.min(28, Math.min(sd * 0.22, ld * 0.085)));
      const fsNom = Math.max(10, fsDim * 0.80);
      const cx = px+pw/2, cy = py+ph/2;
      ctx.save();
      ctx.beginPath(); ctx.rect(px+1, py+1, pw-2, ph-2); ctx.clip();
      if (isPortrait) { ctx.translate(cx, cy); ctx.rotate(-Math.PI / 2); ctx.translate(-cx, -cy); }
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(255,255,255,0.92)';
      const dimLbl = `${p.ancho_original}×${p.alto_original}`;
      ctx.font = `${fsNom}px system-ui,sans-serif`;
      const maxLineW = textW * 0.92;
      const nomLines = [];
      let curLine = '';
      for (const word of (p.nombre || '').split(' ')) {
        const test = curLine ? curLine + ' ' + word : word;
        if (ctx.measureText(test).width <= maxLineW) { curLine = test; }
        else { if (curLine) nomLines.push(curLine); curLine = word; }
      }
      if (curLine) nomLines.push(curLine);
      const lineH = fsNom * 1.25, dimLineH = fsDim * 1.25;
      const maxNomLines = Math.max(0, Math.floor((textH * 0.88 - dimLineH) / lineH));
      const visLines = nomLines.slice(0, maxNomLines);
      const blockH = dimLineH + visLines.length * lineH;
      const yTop = cy - blockH / 2;
      ctx.font = `700 ${fsDim}px system-ui,sans-serif`;
      ctx.fillText(dimLbl, cx, yTop + fsDim * 0.5);
      ctx.font = `${fsNom}px system-ui,sans-serif`;
      visLines.forEach((line, i) => ctx.fillText(line, cx, yTop + dimLineH + lineH * (i + 0.45)));
      ctx.restore();
    }
  }
  for (const c of pl.cortes) {
    ctx.setLineDash([10,8]); ctx.lineWidth = 2.5;
    if (c.tipo==='H') {
      ctx.strokeStyle='rgba(22,160,133,0.75)';
      ctx.beginPath(); ctx.moveTo(c.desde*scale,c.posicion*scale); ctx.lineTo(c.hasta*scale,c.posicion*scale); ctx.stroke();
    } else {
      ctx.strokeStyle='rgba(211,84,0,0.75)';
      ctx.beginPath(); ctx.moveTo(c.posicion*scale,c.desde*scale); ctx.lineTo(c.posicion*scale,c.hasta*scale); ctx.stroke();
    }
  }
  ctx.setLineDash([]);
  ctx.strokeStyle='#7b96c0'; ctx.lineWidth=4;
  ctx.strokeRect(2,2,w-4,h-4);
  const link = document.createElement('a');
  link.download = `plancha-g${gi+1}-${ti+1}-hd.png`;
  link.href = tmpCanvas.toDataURL('image/png');
  link.click();
}

function _plSetTab(gi, ti) {
  _plModalTabs[gi] = ti;
  document.querySelectorAll(`[id^="plm-g${gi}-tab-"]`).forEach((b,i) => b.classList.toggle('active', i===ti));
  document.querySelectorAll(`[id^="plm-g${gi}-cv-"]`).forEach((d,i) => d.classList.toggle('hidden', i!==ti));
  // Re-renderizar con dimensiones reales (evita distorsión por display:none)
  const gData = _plModalData[gi];
  if (gData) {
    const cv = document.getElementById(`plm-g${gi}-canvas-${ti}`);
    const pl  = gData.planchas[ti];
    if (cv && pl) _pl_renderCanvas(cv, gData.binW, gData.binH, pl.piezas, pl.cortes);
  }
}

async function verPlanchasNecesarias() {
  const btn = document.getElementById('btn-ver-planchas');
  if (btn) { btn.disabled = true; btn.textContent = 'Calculando…'; }
  try {
    const data = await apiFetch('/api/planchas/desde-carrito', { method: 'POST' });
    if (!data.ok) { toast(data.error || 'Error al calcular planchas', 'error'); return; }
    _renderModalPlanchas(data);
  } catch(e) {
    toast('Error de conexión', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Ver planchas necesarias'; }
  }
}

function _renderModalPlanchas(data) {
  document.getElementById('modal-planchas-overlay')?.remove();
  const { grupos, items_ignorados, leyenda } = data;
  _plModalGrupos = grupos;

  let warnHtml = '';
  if (items_ignorados && items_ignorados.length > 0) {
    warnHtml = `<div class="modal-planchas-alert-warn">
      ⚠️ Ítems sin desarrollos calculables (manuales, catálogo, planchas):
      <ul style="margin:0.35rem 0 0;padding-left:1.2rem;">
        ${items_ignorados.map(d=>`<li>${_pl_escHtml(d.slice(0,80))}</li>`).join('')}
      </ul></div>`;
  }

  let gruposHtml = '';
  if (!grupos || grupos.length === 0) {
    gruposHtml = `<div class="modal-planchas-vacio">No hay productos con desarrollos calculables en el carrito.</div>`;
  } else {
    grupos.forEach((g, gi) => {
      const res = g.resumen;
      const util = Math.round((res.utilizacion_promedio||0)*100);
      const statsHtml = `<div class="planchas-stats" style="margin-bottom:0.75rem;">
        <div class="stat-box"><span class="stat-val">${res.n_planchas}</span><span class="stat-lbl">Plancha${res.n_planchas!==1?'s':''}</span></div>
        <div class="stat-box"><span class="stat-val">${res.total_colocadas}/${res.total_solicitadas}</span><span class="stat-lbl">Piezas</span></div>
        <div class="stat-box stat-util" data-util="${util}"><span class="stat-val">${util}%</span><span class="stat-lbl">Utilización</span></div>
        <div class="stat-box"><span class="stat-val">${res.desperdicio_m2.toFixed(3)} m²</span><span class="stat-lbl">Desperdicio</span></div>
        <button class="btn-download-hd" onclick="_plDownloadHD(${gi})" type="button" title="Descargar plancha activa en alta resolución">⬇ HD</button>
      </div>`;
      let tabsHtml = '', canvasesHtml = '';
      if (g.planchas.length > 1) {
        tabsHtml = `<div class="planchas-tabs">${g.planchas.map((_,i)=>`<button class="ptab-btn${i===0?' active':''}" id="plm-g${gi}-tab-${i}" onclick="_plSetTab(${gi},${i})" type="button">Plancha ${i+1}</button>`).join('')}</div>`;
        canvasesHtml = g.planchas.map((pl,i)=>`<div id="plm-g${gi}-cv-${i}" class="modal-planchas-canvas-wrap${i>0?' hidden':''}"><canvas id="plm-g${gi}-canvas-${i}" class="modal-planchas-canvas"></canvas></div>`).join('');
      } else if (g.planchas.length === 1) {
        canvasesHtml = `<div class="modal-planchas-canvas-wrap"><canvas id="plm-g${gi}-canvas-0" class="modal-planchas-canvas"></canvas></div>`;
      }
      let noColHtml = '';
      if (g.no_colocadas && g.no_colocadas.length > 0) {
        noColHtml = `<div class="modal-planchas-alert-danger">⚠️ ${g.no_colocadas.length} pieza(s) no caben en 2400×1200mm:<ul style="margin:0.35rem 0 0;padding-left:1.2rem;">${g.no_colocadas.map(p=>`<li>${_pl_escHtml(p.nombre)} (${p.ancho}×${p.alto}mm)</li>`).join('')}</ul></div>`;
      }
      gruposHtml += `<div class="modal-planchas-grupo"><div class="modal-planchas-grupo-title">Plancha ${g.espesor}mm — ${g.tipo_galvanizado}</div>${statsHtml}${tabsHtml}${canvasesHtml}${noColHtml}</div>`;
    });
  }

  let leyendaHtml = '';
  if (leyenda && leyenda.length > 0) {
    leyendaHtml = `<div class="modal-planchas-leyenda">${leyenda.map(l=>`<div class="leyenda-item"><span class="leyenda-dot" style="background:${l.color};"></span><span>${_pl_escHtml(l.label)}</span></div>`).join('')}</div>`;
  }

  document.body.insertAdjacentHTML('beforeend', `
    <div id="modal-planchas-overlay" class="modal-planchas-overlay" role="dialog" aria-modal="true"
         onclick="if(event.target===this)cerrarModalPlanchas()">
      <div class="modal-planchas-inner">
        <div class="modal-planchas-header">
          <h2 class="modal-planchas-titulo">Planchas Necesarias</h2>
          <button class="btn-download-hd" id="btn-pdf-planchas-modal" onclick="descargarPdfPlanchasModal()" type="button" title="Descargar PDF con todas las planchas">⬇ PDF</button>
          <button class="modal-planchas-close" onclick="cerrarModalPlanchas()" aria-label="Cerrar">✕</button>
        </div>
        ${warnHtml}${gruposHtml}${leyendaHtml}
      </div>
    </div>`);

  if (grupos) {
    grupos.forEach((g, gi) => {
      // Guardar datos para re-render al cambiar tab
      _plModalData[gi] = { planchas: g.planchas, binW: 2400, binH: 1200 };
      g.planchas.forEach((pl, pi) => {
        const cv = document.getElementById(`plm-g${gi}-canvas-${pi}`);
        if (cv) _pl_renderCanvas(cv, 2400, 1200, pl.piezas, pl.cortes);
      });
    });
  }
}

async function descargarPdfPlanchasModal() {
  if (!_plModalGrupos || _plModalGrupos.length === 0) {
    toast('No hay planchas calculadas', 'error');
    return;
  }
  const btn = document.getElementById('btn-pdf-planchas-modal');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ PDF…'; }

  const cliente  = document.getElementById('cliente-nombre')?.value
                || document.getElementById('cliente')?.value || '';
  const proyecto = document.getElementById('proyecto')?.value || '';

  try {
    const resp = await fetch('/api/planchas/exportar-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        grupos:   _plModalGrupos,
        cliente,
        proyecto,
        bin_w: 2400,
        bin_h: 1200,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      toast(err.error || 'Error al generar PDF', 'error');
      return;
    }
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = 'planchas.pdf';
    a.click();
    URL.revokeObjectURL(url);
  } catch(e) {
    toast('Error de conexión', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '⬇ PDF'; }
  }
}

function cerrarModalPlanchas() {
  document.getElementById('modal-planchas-overlay')?.remove();
}

// ════════════════════════════════════════════
// Modal nuevo cliente + atención
// ════════════════════════════════════════════
function abrirModalNuevoCliente() {
  ['nc-nombre','nc-ruc','nc-ubicacion','nc-atencion','nc-email'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('nc-error').style.display = 'none';
  const modal = document.getElementById('modal-nuevo-cliente');
  modal.style.display = 'flex';
  document.getElementById('nc-nombre').focus();
}

function cerrarModalNuevoCliente() {
  document.getElementById('modal-nuevo-cliente').style.display = 'none';
}

document.getElementById('modal-nuevo-cliente').addEventListener('click', function(e) {
  if (e.target === this) cerrarModalNuevoCliente();
});

async function guardarNuevoCliente() {
  const nombre   = document.getElementById('nc-nombre').value.trim();
  const ruc      = document.getElementById('nc-ruc').value.trim();
  const ubicacion= document.getElementById('nc-ubicacion').value.trim();
  const atencion = document.getElementById('nc-atencion').value.trim();
  const email    = document.getElementById('nc-email').value.trim();
  const errEl    = document.getElementById('nc-error');

  if (!nombre) { errEl.textContent = 'El nombre del cliente es obligatorio.'; errEl.style.display=''; return; }
  if (!atencion) { errEl.textContent = 'El nombre del contacto es obligatorio.'; errEl.style.display=''; return; }
  if (ruc && !/^\d{11}$/.test(ruc)) { errEl.textContent = 'El RUC debe tener exactamente 11 dígitos.'; errEl.style.display=''; return; }
  errEl.style.display = 'none';

  // Generar código de cliente a partir del nombre (3-4 letras en mayúscula)
  const codigo = nombre.replace(/[^a-zA-Z0-9]/g, '').substring(0, 8).toUpperCase() || 'CLI' + Date.now();

  const btn = document.getElementById('btn-nc-guardar');
  btn.disabled = true; btn.textContent = 'Guardando…';

  try {
    // 1. Crear cliente
    const fdCliente = new FormData();
    fdCliente.append('codigo', codigo);
    fdCliente.append('nombre', nombre);
    fdCliente.append('ruc', ruc);
    fdCliente.append('ubicacion', ubicacion);
    const r1 = await fetch('/api/cliente/nuevo', { method: 'POST', body: fdCliente });
    const d1 = await r1.json();
    if (!d1.ok) { errEl.textContent = d1.error || 'Error al crear cliente.'; errEl.style.display=''; return; }

    // 2. Crear atención
    const fdAt = new FormData();
    fdAt.append('nombre', atencion);
    fdAt.append('codigo_empresa', d1.codigo);
    fdAt.append('email', email);
    const r2 = await fetch('/api/atencion/nueva', { method: 'POST', body: fdAt });
    const d2 = await r2.json();
    if (!d2.ok) { errEl.textContent = d2.error || 'Error al crear atención.'; errEl.style.display=''; return; }

    // 3. Actualizar arrays en memoria y pre-seleccionar
    const nuevoCliente = { codigo: d1.codigo, nombre: nombre, ruc: ruc, ubicacion: ubicacion };
    CLIENTES.push(nuevoCliente);
    ATENCIONES.push({ nombre: atencion, codigo_empresa: d1.codigo, email: email });

    // Pre-seleccionar el nuevo cliente
    _clienteActual = { codigo: d1.codigo, nombre: nombre };
    document.getElementById('cliente-input').value = nombre;
    document.getElementById('cliente').value = d1.codigo;
    document.getElementById('cliente-nombre').value = nombre;
    document.getElementById('cliente-ruc').value = ruc;
    document.getElementById('cliente-ubicacion').value = ubicacion;

    // Pre-seleccionar la nueva atención
    _atencionActual = { valor: atencion, nombre: atencion };
    document.getElementById('atencion-input').value = atencion;
    document.getElementById('atencion').value = atencion;
    document.getElementById('atencion-email').value = email;

    cerrarModalNuevoCliente();
    toast('Cliente y contacto guardados correctamente', 'success');
  } catch(e) {
    errEl.textContent = 'Error de conexión.'; errEl.style.display='';
  } finally {
    btn.disabled = false; btn.textContent = 'Guardar';
  }
}
