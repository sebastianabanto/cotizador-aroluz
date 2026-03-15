/* asistencias-dashboard.js — Gráficos SVG vanilla para el dashboard de asistencias */

document.addEventListener("DOMContentLoaded", function () {
    if (typeof DATOS_REPORTE === "undefined" || typeof KPIS === "undefined") return;
    // Solo empleados con al menos un día asistido (ignora inactivos/despedidos sin marcas)
    const empleados = (DATOS_REPORTE.empleados || []).filter(function(e) { return e.dias_asistidos > 0; });
    if (empleados.length === 0) return;

    renderBarrasHorizontales(empleados, "grafico-barras");
    renderHeatmap(empleados, "heatmap-wrap");
    renderHorasEntrada(empleados, "grafico-entrada");
});

// ── Colores ────────────────────────────────────────────────
const C_VERDE   = "#1e7e44";
const C_NARANJA = "#c47d0e";
const C_ROJO    = "#c0392b";
const C_AZUL    = "#1a56a0";
const C_AZUL_L  = "#5a9fd4";
const C_GRIS    = "#d0d5dd";
const C_TEXTO   = "#1e2530";
const C_SUB     = "#5a6472";

// ── Helpers SVG ────────────────────────────────────────────
function svgRect(x, y, w, h, fill, title, rx) {
    if (w <= 0) return "";
    return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" rx="${rx || 2}">` +
           (title ? `<title>${title}</title>` : "") + `</rect>`;
}

function svgText(x, y, txt, opts) {
    opts = opts || {};
    const anchor = opts.anchor || "start";
    const size   = opts.size   || 11;
    const fill   = opts.fill   || C_TEXTO;
    const weight = opts.weight || "normal";
    return `<text x="${x}" y="${y}" text-anchor="${anchor}" font-size="${size}" fill="${fill}" font-weight="${weight}">${_esc(txt)}</text>`;
}

function _esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function primerNombre(nombre) {
    return (nombre || "").split(" ")[0];
}

// ── 1. Barras apiladas horizontales ───────────────────────
function renderBarrasHorizontales(empleados, contenedorId) {
    const ANCHO      = 900;
    const ALTO_FILA  = 36;
    const MARGEN_IZQ = 140;
    const MARGEN_DER = 80;
    const BAR_H      = 20;
    const BAR_Y_OFF  = 6;
    const MARGEN_BOT = 24;

    const diasHabiles = empleados[0].detalle.filter(function(d) { return !d.es_fin_semana; }).length || 1;
    const anchoDisp   = ANCHO - MARGEN_IZQ - MARGEN_DER;
    const escala      = function(dias) { return Math.max(0, (dias / diasHabiles) * anchoDisp); };
    const altoBarras  = empleados.length * ALTO_FILA;
    const altoTotal   = altoBarras + MARGEN_BOT;

    let svg = `<svg width="100%" viewBox="0 0 ${ANCHO} ${altoTotal}" xmlns="http://www.w3.org/2000/svg">`;

    // Líneas de referencia verticales
    [0, 25, 50, 75, 100].forEach(function(pct) {
        const x = MARGEN_IZQ + (pct / 100) * anchoDisp;
        svg += `<line x1="${x}" y1="0" x2="${x}" y2="${altoBarras}" stroke="#e5e7eb" stroke-width="1"/>`;
        svg += svgText(x, altoBarras + 16, pct + "%", { anchor: "middle", size: 9, fill: C_SUB });
    });

    empleados.forEach(function(emp, i) {
        const y         = i * ALTO_FILA;
        const barY      = y + BAR_Y_OFF;
        const presentes = Math.max(0, emp.dias_asistidos - emp.dias_estimados);
        const estimados = emp.dias_estimados || 0;
        const ausentes  = emp.dias_habiles_ausentes || 0;

        // Calcular anchos proporcionales y capear al 100% del área disponible
        let wP = escala(presentes);
        let wE = escala(estimados);
        let wA = escala(ausentes);
        const wRaw = wP + wE + wA;
        if (wRaw > anchoDisp) {
            // Escalar proporcionalemente para que nunca supere el 100%
            const factor = anchoDisp / wRaw;
            wP *= factor;
            wE *= factor;
            wA *= factor;
        }
        const wTotal = wP + wE + wA; // ahora siempre <= anchoDisp

        // Nombre
        svg += svgText(MARGEN_IZQ - 10, barY + BAR_H * 0.75, primerNombre(emp.nombre),
                       { anchor: "end", size: 12, fill: C_TEXTO });

        // Barras
        let x = MARGEN_IZQ;
        svg += svgRect(x, barY, wP, BAR_H, C_VERDE,
                       emp.nombre + ": " + presentes + " días presentes");
        x += wP;
        if (estimados > 0) {
            svg += svgRect(x, barY, wE, BAR_H, C_NARANJA,
                           emp.nombre + ": " + estimados + " días sin marcado completo");
            x += wE;
        }
        if (ausentes > 0) {
            svg += svgRect(x, barY, wA, BAR_H, C_ROJO,
                           emp.nombre + ": " + ausentes + " días ausente");
        }

        // Etiqueta: siempre en la zona MARGEN_DER (a la derecha del área de barras)
        // xBase es el inicio del área de etiquetas: justo después del 100%
        const total    = presentes + estimados;
        const labelStr = total + "/" + diasHabiles;
        const xLabel   = MARGEN_IZQ + anchoDisp + 8; // posición fija en la zona derecha
        svg += svgText(xLabel, barY + BAR_H * 0.75, labelStr,
                       { size: 11, fill: C_TEXTO, weight: "600" });
    });

    svg += "</svg>";
    const cont = document.getElementById(contenedorId);
    if (cont) cont.innerHTML = svg;
}

// ── 2. Heatmap ─────────────────────────────────────────────
function renderHeatmap(empleados, contenedorId) {
    const cont = document.getElementById(contenedorId);
    if (!cont || empleados.length === 0) return;

    const dias = empleados[0].detalle;
    let html = '<table class="heatmap-tabla"><thead><tr>';
    html += '<th class="hm-nombre-col"></th>';
    dias.forEach(function(d) {
        const cls = d.es_fin_semana ? "hm-th-fds" : "hm-th-dia";
        html += `<th class="${cls}" title="${d.fecha}">${d.dia}</th>`;
    });
    html += "</tr></thead><tbody>";

    empleados.forEach(function(emp) {
        html += `<tr><td class="hm-nombre">${_esc(primerNombre(emp.nombre))}</td>`;
        emp.detalle.forEach(function(d) {
            let cls, title;
            if (d.es_fin_semana) {
                cls   = "hm-fds";
                title = "Fin de semana";
            } else if (d.ausente) {
                cls   = "hm-ausente";
                title = "Ausente";
            } else if (d.estimado) {
                const ent = d.entrada ? d.entrada + "*" : "?";
                const sal = d.salida  ? d.salida  + "*" : "?";
                cls   = "hm-estimado";
                title = ent + " → " + sal + (d.horas_fmt ? " (" + d.horas_fmt + ")" : "");
            } else {
                cls   = "hm-presente";
                const ent = d.entrada || "?";
                const sal = d.salida  || "?";
                title = ent + " → " + sal + (d.horas_fmt ? " (" + d.horas_fmt + ")" : "");
            }
            html += `<td class="${cls}" title="${_esc(title)}"></td>`;
        });
        html += "</tr>";
    });

    html += "</tbody></table>";
    cont.innerHTML = html;
}

// ── 3. Hora de entrada por día y empleado ─────────────────
function renderHorasEntrada(empleados, contenedorId) {
    const cont = document.getElementById(contenedorId);
    if (!cont || empleados.length === 0) return;

    const REF = 9 * 60; // 9:00 en minutos

    // Encontrar el rango real de horas de entrada
    let minMin = REF, maxMin = REF;
    let hayDatos = false;

    empleados.forEach(function(emp) {
        emp.detalle.forEach(function(d) {
            if (!d.es_fin_semana && !d.ausente && d.entrada) {
                const partes = d.entrada.replace(/\*/g, "").split(":");
                if (partes.length === 2) {
                    const mins = parseInt(partes[0]) * 60 + parseInt(partes[1]);
                    if (mins < minMin) minMin = mins;
                    if (mins > maxMin) maxMin = mins;
                    hayDatos = true;
                }
            }
        });
    });

    if (!hayDatos) {
        cont.innerHTML = '<p class="config-vacio">Sin datos de entrada disponibles.</p>';
        return;
    }

    // Extender el rango a múltiplos de 30 min con margen
    minMin = Math.floor(minMin / 30) * 30;
    maxMin = Math.ceil((maxMin + 15) / 30) * 30;
    if (minMin >= maxMin) maxMin = minMin + 60;
    const RANGO = maxMin - minMin;

    const MARGEN_IZQ = 46;
    const MARGEN_DER = 16;
    const MARGEN_SUP = 14;
    const MARGEN_INF = 30;
    const CHART_H    = 140;
    const BAR_W      = 5;
    const BAR_GAP    = 1;
    const GROUP_GAP  = 14;

    const nDias  = empleados[0].detalle.filter(function(d) { return !d.es_fin_semana; }).length;
    const groupW = nDias * (BAR_W + BAR_GAP);
    const totalW = empleados.length * (groupW + GROUP_GAP) - GROUP_GAP;
    const ANCHO  = totalW + MARGEN_IZQ + MARGEN_DER;
    const ALTO   = CHART_H + MARGEN_SUP + MARGEN_INF;

    function toY(mins) {
        // minMin → fondo del gráfico, maxMin → tope
        return MARGEN_SUP + CHART_H * (1 - (mins - minMin) / RANGO);
    }

    let svg = `<svg width="${ANCHO}" viewBox="0 0 ${ANCHO} ${ALTO}" xmlns="http://www.w3.org/2000/svg">`;

    // Fondo del área
    svg += `<rect x="${MARGEN_IZQ}" y="${MARGEN_SUP}" width="${totalW}" height="${CHART_H}" fill="#fafbfc" rx="3"/>`;

    // Líneas de tiempo horizontales (cada 30 min)
    for (let t = minMin; t <= maxMin; t += 30) {
        const y      = toY(t);
        const isRef  = (t === REF);
        const h = Math.floor(t / 60), m = t % 60;
        const label  = `${h}:${m < 10 ? "0" + m : m}`;
        svg += `<line x1="${MARGEN_IZQ}" y1="${y}" x2="${MARGEN_IZQ + totalW}" y2="${y}" `
             + `stroke="${isRef ? "#e74c3c" : "#d1d9e0"}" stroke-width="${isRef ? 1.5 : 1}"`
             + (isRef ? ' stroke-dasharray="5,3"' : "") + `/>`;
        svg += svgText(MARGEN_IZQ - 4, y + 4, label,
                       { anchor: "end", size: 9,
                         fill: isRef ? C_ROJO : C_SUB,
                         weight: isRef ? "600" : "normal" });
    }

    // Grupos por trabajador
    empleados.forEach(function(emp, gi) {
        const gX = MARGEN_IZQ + gi * (groupW + GROUP_GAP);

        // Separador entre grupos
        if (gi > 0) {
            svg += `<line x1="${gX - GROUP_GAP / 2}" y1="${MARGEN_SUP}" `
                 + `x2="${gX - GROUP_GAP / 2}" y2="${MARGEN_SUP + CHART_H}" `
                 + `stroke="#d1d9e0" stroke-width="0.5"/>`;
        }

        // Nombre del trabajador (debajo del gráfico)
        svg += svgText(gX + groupW / 2, MARGEN_SUP + CHART_H + 16,
                       primerNombre(emp.nombre), { anchor: "middle", size: 10, fill: C_TEXTO });

        // Barras por día laborable
        let dayIdx = 0;
        emp.detalle.forEach(function(d) {
            if (d.es_fin_semana) return;
            const bx = gX + dayIdx * (BAR_W + BAR_GAP);
            dayIdx++;

            if (d.ausente || !d.entrada) return;

            const partes = d.entrada.replace(/\*/g, "").split(":");
            if (partes.length !== 2) return;
            const mins = parseInt(partes[0]) * 60 + parseInt(partes[1]);

            // Color: verde = a tiempo, naranja = hasta 14 min tarde, rojo = 15+ min tarde
            const color = mins < REF ? C_VERDE : (mins < REF + 15 ? C_NARANJA : C_ROJO);

            // Altura de la barra desde el fondo hasta la hora de entrada
            const minsDisplay = Math.max(minMin + 1, Math.min(maxMin, mins));
            const barTopY = toY(minsDisplay);
            const barBotY = toY(minMin);
            const barH    = Math.max(2, barBotY - barTopY);

            const tip = `${emp.nombre} — ${d.fecha}: ${d.entrada}${d.estimado ? " (sin marca)" : ""}`;
            svg += svgRect(bx, barTopY, BAR_W, barH, color, tip, 1);
        });
    });

    svg += "</svg>";
    cont.innerHTML = svg;
}

// ── 4. Comparador: barras agrupadas ───────────────────────
async function cargarComparador(reporteIdB) {
    const cont = document.getElementById("grafico-comparacion");
    if (!reporteIdB) { cont.style.display = "none"; return; }

    cont.style.display = "";
    cont.innerHTML = '<p class="config-vacio">Cargando...</p>';

    try {
        const resp = await fetch("/asistencias/api/dashboard/" + reporteIdB);
        if (!resp.ok) {
            let detalle = "HTTP " + resp.status;
            try { const err = await resp.json(); detalle = err.detail || detalle; } catch(e) {}
            cont.innerHTML = '<p class="config-vacio">Error al cargar el período de comparación: ' + _esc(detalle) + '</p>';
            return;
        }
        const dataB = await resp.json();
        // Filtrar empleados sin marcas para el comparador
        const datosA = Object.assign({}, DATOS_REPORTE, {
            empleados: DATOS_REPORTE.empleados.filter(function(e) { return e.dias_asistidos > 0; })
        });
        const datosB = Object.assign({}, dataB.datos, {
            empleados: dataB.datos.empleados.filter(function(e) { return e.dias_asistidos > 0; })
        });
        renderBarrasAgrupadas(datosA, datosB, dataB.reporte, cont);
    } catch (err) {
        cont.innerHTML = '<p class="config-vacio">Error de conexión al cargar el período de comparación.</p>';
    }
}

function renderBarrasAgrupadas(datosA, datosB, reporteB, contenedor) {
    const ANCHO      = 600;
    const ALTO_FILA  = 44;
    const MARGEN_IZQ = 120;
    const MARGEN_DER = 60;
    const BAR_H      = 14;
    const GAP        = 4;

    const mapA = {};
    datosA.empleados.forEach(function(e) { mapA[e.nombre] = e; });
    const mapB = {};
    datosB.empleados.forEach(function(e) { mapB[e.nombre] = e; });
    const nombres = Object.keys(
        Object.assign({}, mapA, mapB)
    );

    const diasA = (datosA.empleados[0] || {detalle: []}).detalle
        .filter(function(d) { return !d.es_fin_semana; }).length || 1;
    const diasB = (datosB.empleados[0] || {detalle: []}).detalle
        .filter(function(d) { return !d.es_fin_semana; }).length || 1;

    const anchoDisp = ANCHO - MARGEN_IZQ - MARGEN_DER;
    const altoBarras = nombres.length * ALTO_FILA;
    const altoTotal = altoBarras + 50; // espacio para etiquetas % + leyenda

    let svg = `<svg width="100%" viewBox="0 0 ${ANCHO} ${altoTotal}" xmlns="http://www.w3.org/2000/svg">`;

    // Referencia
    [0, 25, 50, 75, 100].forEach(function(pct) {
        const x = MARGEN_IZQ + (pct / 100) * anchoDisp;
        svg += `<line x1="${x}" y1="0" x2="${x}" y2="${altoBarras}" stroke="#e5e7eb" stroke-width="1"/>`;
        svg += svgText(x, altoBarras + 14, pct + "%",
                       { anchor: "middle", size: 9, fill: C_SUB });
    });

    nombres.forEach(function(nombre, i) {
        const empA = mapA[nombre];
        const empB = mapB[nombre];
        const pctA = empA ? Math.round(empA.dias_asistidos / diasA * 100) : 0;
        const pctB = empB ? Math.round(empB.dias_asistidos / diasB * 100) : 0;
        const y    = i * ALTO_FILA;

        svg += svgText(MARGEN_IZQ - 8, y + BAR_H * 0.75,
                       primerNombre(nombre), { anchor: "end", size: 11, fill: C_TEXTO });

        // Barra A
        svg += svgRect(MARGEN_IZQ, y, (pctA / 100) * anchoDisp, BAR_H, C_AZUL,
                       datosA.periodo + ": " + pctA + "%");
        svg += svgText(MARGEN_IZQ + (pctA / 100) * anchoDisp + 4, y + BAR_H * 0.75,
                       pctA + "%", { size: 10, fill: C_AZUL });

        // Barra B
        const yB = y + BAR_H + GAP;
        svg += svgRect(MARGEN_IZQ, yB, (pctB / 100) * anchoDisp, BAR_H, C_AZUL_L,
                       datosB.periodo + ": " + pctB + "%");
        svg += svgText(MARGEN_IZQ + (pctB / 100) * anchoDisp + 4, yB + BAR_H * 0.75,
                       pctB + "%", { size: 10, fill: C_AZUL_L });
    });

    // Leyenda (posicionada debajo de las etiquetas de %)
    const lyY = altoBarras + 28;
    svg += `<rect x="${MARGEN_IZQ}" y="${lyY}" width="12" height="10" fill="${C_AZUL}" rx="2"/>`;
    svg += svgText(MARGEN_IZQ + 16, lyY + 9, datosA.periodo || "Período A",
                   { size: 10, fill: C_TEXTO });
    svg += `<rect x="${MARGEN_IZQ + 200}" y="${lyY}" width="12" height="10" fill="${C_AZUL_L}" rx="2"/>`;
    svg += svgText(MARGEN_IZQ + 216, lyY + 9,
                   (reporteB && reporteB.periodo) ? reporteB.periodo : "Período B",
                   { size: 10, fill: C_TEXTO });

    svg += "</svg>";
    contenedor.innerHTML = svg;
}
