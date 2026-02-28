/* ═══════════════════════════════════════════════════════════════
   AROLUZ — cotizar-layout.js
   Layout responsive de /cotizar (mobile-first)

   Breakpoints (alineados con style.css):
     <600px   → mobile: config como acordeón full-width, carrito oculto
     600–719px → compact: config colapsado, carrito visible
     ≥720px   → desktop: config expandido, carrito visible

   Responsabilidades de este módulo:
     · window.matchMedia → colapsa/expande config-panel en resize
     · Registra toggles manuales de config y carrito
     · En desktop, persiste preferencia collapsed en localStorage
     · Cuando el ancho baja de 720px el panel siempre queda colapsado

   Lo que NO hace este módulo (lo maneja CSS):
     · Visibilidad de paneles en mobile (display: none / block)
     · Wrapping del tipo-bar
     · Tamaño de fuentes y paddings
   ═══════════════════════════════════════════════════════════════ */
'use strict';

(function initCotizarLayout() {

  const configPanel  = document.getElementById('config-panel');
  const carritoPanel = document.getElementById('carrito-live-panel');
  const layout       = document.querySelector('.cotizar-layout');

  if (!configPanel || !layout) return;

  const STORAGE_KEY = 'aroluz_config_collapsed';

  // ── Breakpoint desktop ──────────────────────────────────────
  // Una sola MediaQueryList cubre todo:
  //   matches = true  → ≥720px: desktop-layout, config según preferencia guardada
  //   matches = false → <720px: compact/mobile, config siempre colapsado
  //   (<600px el CSS muestra config como acordeón y oculta el carrito)
  const mqDesktop = window.matchMedia('(min-width: 720px)');

  function applyLayout() {
    if (mqDesktop.matches) {
      // ≥720px — Desktop: respetar preferencia guardada (por defecto expandido)
      const savedCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
      configPanel.classList.toggle('collapsed', savedCollapsed);
      layout.classList.add('desktop-layout');
      layout.classList.remove('mobile-layout');
    } else {
      // <720px — Compact / mobile: siempre colapsado
      configPanel.classList.add('collapsed');
      layout.classList.remove('desktop-layout');
      // mobile-layout solo cuando CSS también oculta los paneles
      if (window.innerWidth < 600) {
        layout.classList.add('mobile-layout');
      } else {
        layout.classList.remove('mobile-layout');
      }
    }
  }

  // Responde a cambios de breakpoint (resize automático sin polling)
  mqDesktop.addEventListener('change', applyLayout);

  // ── Toggles manuales ──────────────────────────────────────
  // En desktop: guardar preferencia en localStorage al hacer toggle.
  // En compact/mobile: sin persistencia (siempre arranca colapsado).

  document.getElementById('config-toggle')
    ?.addEventListener('click', () => {
      configPanel.classList.toggle('collapsed');
      if (mqDesktop.matches) {
        localStorage.setItem(STORAGE_KEY, configPanel.classList.contains('collapsed'));
      }
    });

  document.getElementById('carrito-toggle')
    ?.addEventListener('click', () => {
      carritoPanel?.classList.toggle('collapsed');
    });

  // Aplicar layout inicial
  applyLayout();

})();
