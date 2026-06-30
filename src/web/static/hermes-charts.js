/*
 * ⚠️ DEPRECATED / NOT LIVE (L3 triage, 2026-06-29). This file is the ORIGINAL
 * "CPR Spine" engine. It is NOT wired into the running app: `/static` is not mounted
 * in main.py, and the live /dash/stock chart is built by `src/web/stock_chart.py`'s
 * SNIPPET (which superseded this in S42, commit ad49c30) — a bounded, four-family,
 * drawing-capable engine that the live overlays (CPR/MA/MEP/RS/Wolfe/Harmonic) bind
 * to via window.__wfpc. Keep this file as the reference implementation of the CPR
 * Spine design only. Do NOT mistake it for live code; do NOT re-wire it without an
 * explicit decision (see docs/L3-chart-inventory.md §3). Safe to `git rm` if the tree
 * is ever cleaned (along with _chart_demo.html + chart_view.render_stock_chart).
 *
 * hermes-charts.js — the reusable Patearn chart engine (reference / deprecated).
 *
 * ONE responsive price chart + a four-family control bar (chart-type · proprietary
 * strategies · standard indicators · drawings), an overlay registry (per-item
 * show/hide), and the signature **CPR Spine** drawn as a canvas primitive.
 *
 * Built on lightweight-charts v4.1.x (the same lib the app already ships, with the
 * Series Primitives API for the CPR bands). Pure namespace global — no build step,
 * no framework. A page hands it a JSON contract; the engine renders everything.
 *
 *   HermesCharts.createStockChart(containerEl, contract, opts) -> api
 *
 * contract = {
 *   symbol, name, rank, read,                 // header + plain-English "Read:" line
 *   series:[{time,open,high,low,close,dvpt,r1m,deliv,tval,dval}],   // daily, ascending
 *   zones:[{price,color,label}],              // institutional horizontal levels
 *   cpr:{ D:[seg], W:[seg], M:[seg] },        // per-timeframe CPR segments (below)
 *   confluence:[{lo,hi,degrees}]              // merged D/W/M S/R slabs
 * }
 *   seg = {t0,t1,p,bc,tc,regime,width,coil,pattern,confirmed}
 *     t0,t1 = period start/end (times present on the axis); p/bc/tc = CPR lines;
 *     regime = +1/-1 (close vs pivot); coil = compressed; pattern = 'BULL_U'|'BEAR_INVU'|null
 *
 * Design language is fixed in PALETTE so every chart on the site speaks one grammar.
 */
window.HermesCharts = (function () {
  'use strict';

  // --- the signature grammar: one fixed hue per strategy, reused site-wide -----
  var PALETTE = {
    bg: '#0d1117', panel: '#0e1320', grid: '#1c2128', border: '#21262d',
    text: '#8b949e', textHi: '#e6edf3', textDim: '#6e7681',
    up: '#3fb950', down: '#f85149',
    cpr: '#d29922', cprSlab: '#e3b341', cprUpTint: 'rgba(63,185,80,.10)', cprDnTint: 'rgba(248,81,73,.10)',
    dvpt: '#bc8cff', dvptDist: '#db61a2', dvptIdle: '#30506b',
    rs: '#39c5cf', wolfe: '#58a6ff',
    ma20: '#8b949e', ma50: '#58a6ff', ma200: '#d29922'
  };

  // --- tiny DOM helper ---------------------------------------------------------
  function E(tag, css, html) {
    var n = document.createElement(tag);
    if (css) n.setAttribute('style', css);
    if (html != null) n.innerHTML = html;
    return n;
  }
  function fmtInr(v) {
    if (v == null) return '—';
    return '₹' + Math.round(v).toLocaleString('en-IN');
  }
  function num(v, d) { return v == null ? '—' : Number(v).toFixed(d == null ? 2 : d); }

  // --- simple moving average over closes --------------------------------------
  function sma(series, n) {
    var out = [], sum = 0, q = [];
    for (var i = 0; i < series.length; i++) {
      var c = series[i].close; sum += c; q.push(c);
      if (q.length > n) sum -= q.shift();
      if (q.length === n) out.push({ time: series[i].time, value: sum / n });
    }
    return out;
  }

  /* ===========================================================================
   * The CPR Spine primitive — a v4.1 ISeriesPrimitive that paints, behind the
   * candles: confluence S/R slabs, then the stepped translucent CPR ribbon
   * (BC↔TC band + dashed pivot), brightening into a solid "coil" when compressed.
   * =========================================================================== */
  function makeCprPrimitive() {
    var chart = null, series = null, requestUpdate = null;
    var segs = [], confl = [], visible = true;

    function xFor(ts, t, fallback, w) {
      var x = ts.timeToCoordinate(t);
      return x == null ? fallback : x;
    }

    var paneView = {
      zOrder: function () { return 'bottom'; },
      renderer: function () {
        return {
          draw: function (target) {
            if (!visible || !chart || !series) return;
            target.useBitmapCoordinateSpace(function (scope) {
              var ctx = scope.context;
              var hpr = scope.horizontalPixelRatio, vpr = scope.verticalPixelRatio;
              var W = scope.mediaSize.width;
              var ts = chart.timeScale();

              // 1) confluence slabs — full-width brighter amber S/R zones
              for (var c = 0; c < confl.length; c++) {
                var z = confl[c];
                var yHi = series.priceToCoordinate(z.hi);
                var yLo = series.priceToCoordinate(z.lo);
                if (yHi == null || yLo == null) continue;
                ctx.fillStyle = 'rgba(227,179,65,' + (z.degrees >= 3 ? 0.26 : 0.15) + ')';
                ctx.fillRect(0, Math.min(yHi, yLo) * vpr, W * hpr, Math.abs(yLo - yHi) * vpr);
                ctx.fillStyle = '#e3b341';
                ctx.font = (10 * vpr) + 'px -apple-system,Segoe UI,Roboto,sans-serif';
                ctx.fillText('D·W·M', 6 * hpr, (Math.min(yHi, yLo) - 3) * vpr);
              }

              // 2) the CPR ribbon — one stepped band per period
              for (var i = 0; i < segs.length; i++) {
                var s = segs[i];
                var x0 = xFor(ts, s.t0, 0, W);
                var x1 = xFor(ts, s.t1, W, W);
                if (x1 <= x0) x1 = x0 + 1;
                var yT = series.priceToCoordinate(s.tc);
                var yB = series.priceToCoordinate(s.bc);
                var yP = series.priceToCoordinate(s.p);
                if (yT == null || yB == null) continue;
                var bx = x0 * hpr, bw = (x1 - x0) * hpr;
                var by = yT * vpr, bh = (yB - yT) * vpr;

                // regime wash, then the amber band (brighter when coiled)
                ctx.fillStyle = s.regime >= 0 ? PALETTE.cprUpTint : PALETTE.cprDnTint;
                ctx.fillRect(bx, by, bw, bh);
                ctx.fillStyle = s.coil ? 'rgba(210,153,34,0.42)' : 'rgba(210,153,34,0.20)';
                ctx.fillRect(bx, by, bw, bh);
                // TC / BC edges — the stepped "spine" definition that reads at any zoom
                ctx.strokeStyle = s.coil ? 'rgba(240,193,80,0.92)' : 'rgba(210,153,34,0.50)';
                ctx.lineWidth = (s.coil ? 1.3 : 0.9) * vpr;
                ctx.beginPath();
                ctx.moveTo(bx, by); ctx.lineTo(bx + bw, by);
                ctx.moveTo(bx, by + bh); ctx.lineTo(bx + bw, by + bh);
                ctx.stroke();
                // pivot line (dashed normally, solid + bright when coiled)
                if (yP != null) {
                  ctx.strokeStyle = PALETTE.cpr; ctx.lineWidth = (s.coil ? 1.6 : 1.2) * vpr;
                  ctx.setLineDash(s.coil ? [] : [4 * hpr, 3 * hpr]);
                  ctx.beginPath(); ctx.moveTo(bx, yP * vpr); ctx.lineTo(bx + bw, yP * vpr); ctx.stroke();
                  ctx.setLineDash([]);
                }
              }
            });
          }
        };
      }
    };

    return {
      attached: function (p) { chart = p.chart; series = p.series; requestUpdate = p.requestUpdate; },
      detached: function () { chart = series = requestUpdate = null; },
      updateAllViews: function () {},
      paneViews: function () { return [paneView]; },
      setData: function (d) { segs = (d && d.segs) || []; confl = (d && d.confl) || []; if (requestUpdate) requestUpdate(); },
      setVisible: function (v) { visible = !!v; if (requestUpdate) requestUpdate(); }
    };
  }

  /* ===========================================================================
   * createStockChart — assemble the frame, the one chart, the overlay registry,
   * and the four-family control bar.
   * =========================================================================== */
  function createStockChart(host, contract, opts) {
    opts = opts || {};
    if (!window.LightweightCharts) {
      host.innerHTML = '<div style="color:#8b949e;padding:20px">Chart library failed to load (offline?).</div>';
      return null;
    }
    var S = contract.series || [];
    var byTime = {}; S.forEach(function (d) { byTime[d.time] = d; });

    // ---- frame ---------------------------------------------------------------
    host.innerHTML = '';
    host.style.cssText = 'background:' + PALETTE.bg + ';border:1px solid ' + PALETTE.border + ';border-radius:10px;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,sans-serif';

    var head = E('div', 'display:flex;align-items:center;gap:8px;padding:10px 14px 4px');
    head.appendChild(E('span', 'font-size:14px;color:' + PALETTE.textHi + ';font-weight:600', contract.symbol || ''));
    if (contract.name) head.appendChild(E('span', 'font-size:12px;color:' + PALETTE.text, contract.name + ' · price + structure'));
    if (contract.rank) head.appendChild(E('span', 'margin-left:auto;font-size:11px;color:' + PALETTE.up + ';border:1px solid #1f6f3a;border-radius:4px;padding:1px 6px', contract.rank));
    host.appendChild(head);

    var bar = E('div', 'padding:4px 12px 8px');
    host.appendChild(bar);

    var readout = E('div', 'font-size:12px;color:#c9d1d9;font-variant-numeric:tabular-nums;min-height:16px;padding:0 14px 3px');
    host.appendChild(readout);

    var chartDiv = E('div', 'height:' + (opts.height || 460) + 'px');
    host.appendChild(chartDiv);

    if (contract.read) {
      var read = E('div', 'padding:9px 14px 12px;font-size:12px;color:#c9d1d9;border-top:1px solid #161b22;line-height:1.55');
      read.innerHTML = '<span style="color:' + PALETTE.text + '">Read:</span> ' + contract.read;
      host.appendChild(read);
    }

    // ---- the ONE chart -------------------------------------------------------
    var common = {
      layout: { background: { color: PALETTE.bg }, textColor: PALETTE.text, fontSize: 11 },
      grid: { vertLines: { color: PALETTE.grid }, horzLines: { color: PALETTE.grid } },
      timeScale: { borderColor: '#30363d', rightOffset: 4 },
      rightPriceScale: { borderColor: '#30363d', scaleMargins: { top: 0.06, bottom: 0.26 } },
      crosshair: { mode: 0 },
      handleScroll: true, handleScale: true,
      width: chartDiv.clientWidth || 800, height: opts.height || 460
    };
    var chart = LightweightCharts.createChart(chartDiv, common);

    var candle = chart.addCandlestickSeries({
      upColor: PALETTE.up, downColor: PALETTE.down, wickUpColor: PALETTE.up,
      wickDownColor: PALETTE.down, borderVisible: false
    });
    candle.setData(S.map(function (d) { return { time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }; }));
    (contract.zones || []).forEach(function (z) {
      candle.createPriceLine({ price: z.price, color: z.color || '#6e7681', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: z.label || '' });
    });

    var pline = chart.addLineSeries({ color: '#1f6feb', lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
    pline.setData(S.map(function (d) { return { time: d.time, value: d.close }; }));
    pline.applyOptions({ visible: false });

    // CPR Spine primitive
    var cprPrim = makeCprPrimitive();
    candle.attachPrimitive(cprPrim);
    var cprTf = opts.cprTf || 'W';
    function loadCpr(tf) {
      cprTf = tf;
      var segs = (contract.cpr && contract.cpr[tf]) || [];
      cprPrim.setData({ segs: segs, confl: contract.confluence || [] });
      // reversal markers from the active timeframe
      var mk = [];
      segs.forEach(function (s) {
        if (s.pattern === 'BULL_U') mk.push({ time: s.t1 || s.t0, position: 'belowBar', color: PALETTE.up, shape: 'arrowUp', text: 'U' + (s.confirmed ? '' : '?') });
        else if (s.pattern === 'BEAR_INVU') mk.push({ time: s.t1 || s.t0, position: 'aboveBar', color: PALETTE.down, shape: 'arrowDown', text: '∩' + (s.confirmed ? '' : '?') });
      });
      cprMarkers = mk; refreshMarkers();
    }

    // DVPT institutional markers (amber ▲ on r1m>1 days) — live on the candles
    var dvptMarkers = S.filter(function (d) { return d.r1m != null && d.r1m > 1; })
      .map(function (d) { return { time: d.time, position: 'aboveBar', color: PALETTE.dvpt, shape: 'circle' }; });
    var cprMarkers = [];
    function refreshMarkers() {
      var all = [];
      if (reg.cpr.visible) all = all.concat(cprMarkers);
      if (reg.dvpt.visible) all = all.concat(dvptMarkers);
      all.sort(function (a, b) { return a.time < b.time ? -1 : a.time > b.time ? 1 : 0; });
      candle.setMarkers(all);
    }

    // moving averages (computed client-side)
    var ma50 = chart.addLineSeries({ color: PALETTE.ma50, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    ma50.setData(sma(S, 50)); ma50.applyOptions({ visible: true });
    var ma200 = chart.addLineSeries({ color: PALETTE.ma200, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    ma200.setData(sma(S, 200)); ma200.applyOptions({ visible: true });

    // docked DVPT sub-pane (overlay price scale, bottom band — collapses the old
    // 4-chart stack into ONE chart)
    var dvpt = chart.addHistogramSeries({ priceScaleId: 'dvpt', priceFormat: { type: 'volume' }, lastValueVisible: false });
    dvpt.setData(S.map(function (d) { return { time: d.time, value: d.dvpt || 0, color: (d.r1m != null && d.r1m > 1) ? PALETTE.dvpt : PALETTE.dvptIdle }; }));
    chart.priceScale('dvpt').applyOptions({ scaleMargins: { top: 0.80, bottom: 0 } });

    // ---- overlay registry (per-item show/hide) -------------------------------
    var reg = {
      cpr: { label: 'CPR spine', color: PALETTE.cpr, group: 'strat', visible: true, apply: function (v) { cprPrim.setVisible(v); refreshMarkers(); } },
      dvpt: { label: 'DVPT', color: PALETTE.dvpt, group: 'strat', visible: true, apply: function (v) { dvpt.applyOptions({ visible: v }); refreshMarkers(); } },
      rs: { label: 'RS band', color: PALETTE.rs, group: 'strat', visible: false, apply: function (v) {} },
      wolfe: { label: 'Wolfe', color: PALETTE.wolfe, group: 'strat', visible: false, apply: function (v) {} },
      ma: { label: 'MA 50/200', color: PALETTE.ma200, group: 'ind', visible: true, apply: function (v) { ma50.applyOptions({ visible: v }); ma200.applyOptions({ visible: v }); } },
      zones: { label: 'Zones', color: PALETTE.text, group: 'ind', visible: true, apply: function (v) { candle.applyOptions({ priceLineVisible: false }); } }
    };

    // ---- the four-family control bar -----------------------------------------
    function chip(o, key) {
      var on = o.visible;
      var c = E('span', 'cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:3px 9px;border-radius:20px;user-select:none;' +
        (on ? ('background:' + hexA(o.color, 0.16) + ';color:' + lighten(o.color)) : ('border:1px solid #30363d;color:' + PALETTE.text)),
        '<span style="width:7px;height:7px;border-radius:50%;background:' + o.color + '"></span>' + o.label);
      c.onclick = function () {
        o.visible = !o.visible; o.apply(o.visible);
        c.setAttribute('style', 'cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:3px 9px;border-radius:20px;user-select:none;' +
          (o.visible ? ('background:' + hexA(o.color, 0.16) + ';color:' + lighten(o.color)) : ('border:1px solid #30363d;color:' + PALETTE.text)));
        c.innerHTML = '<span style="width:7px;height:7px;border-radius:50%;background:' + o.color + '"></span>' + o.label;
      };
      return c;
    }
    function label(t) { return E('span', 'font-size:10px;letter-spacing:.4px;text-transform:uppercase;color:' + PALETTE.textDim + ';margin-right:2px', t); }
    function sep() { return E('span', 'width:1px;align-self:stretch;background:' + PALETTE.border + ';margin:2px 4px'); }
    function family(lbl, kids) {
      var col = E('div', 'display:flex;flex-direction:column;gap:5px');
      col.appendChild(label(lbl));
      var row = E('div', 'display:flex;flex-wrap:wrap;gap:6px;align-items:center');
      kids.forEach(function (k) { row.appendChild(k); });
      col.appendChild(row); return col;
    }

    // chart-type dropdown (space-efficient — types are NOT indicators)
    var typeSel = E('select', 'background:#161b22;border:1px solid #30363d;color:#c9d1d9;border-radius:6px;font-size:12px;padding:4px 8px');
    ['Candles', 'Line'].forEach(function (t) { var o = document.createElement('option'); o.textContent = t; typeSel.appendChild(o); });
    typeSel.onchange = function () {
      var ln = typeSel.value === 'Line';
      candle.applyOptions({ visible: !ln }); pline.applyOptions({ visible: ln });
    };

    // CPR timeframe (D/W/M) mini-toggle lives with the CPR strategy
    var tfWrap = E('span', 'display:inline-flex;gap:3px;margin-left:4px');
    ['D', 'W', 'M'].forEach(function (tf) {
      var b = E('span', 'cursor:pointer;font-size:11px;padding:2px 6px;border-radius:5px;' + (tf === cprTf ? 'background:' + hexA(PALETTE.cpr, 0.2) + ';color:#e3b341' : 'color:' + PALETTE.textDim), tf);
      b.onclick = function () {
        loadCpr(tf);
        tfWrap.querySelectorAll('span').forEach(function (x) { x.setAttribute('style', 'cursor:pointer;font-size:11px;padding:2px 6px;border-radius:5px;color:' + PALETTE.textDim); });
        b.setAttribute('style', 'cursor:pointer;font-size:11px;padding:2px 6px;border-radius:5px;background:' + hexA(PALETTE.cpr, 0.2) + ';color:#e3b341');
      };
      tfWrap.appendChild(b);
    });

    var strat = [chip(reg.cpr, 'cpr'), tfWrap, chip(reg.dvpt, 'dvpt'), chip(reg.rs, 'rs'), chip(reg.wolfe, 'wolfe')];
    var ind = [chip(reg.ma, 'ma'), chip(reg.zones, 'zones'), E('span', 'font-size:12px;color:' + PALETTE.textDim + ';border:1px dashed #30363d;border-radius:20px;padding:3px 9px;cursor:pointer', '+ add')];
    var draw = ['trendline', 'horizontal', 'rectangle', 'text', 'measure'].map(function (t) {
      return E('span', 'cursor:pointer;color:' + PALETTE.text + ';font-size:12px;padding:2px 4px', drawIcon(t));
    });
    var magnet = E('span', 'cursor:pointer;color:' + PALETTE.text + ';font-size:11px;border:1px solid #30363d;border-radius:5px;padding:2px 7px;margin-left:2px', '🧲 magnet');
    var hideAll = E('span', 'cursor:pointer;color:' + PALETTE.text + ';font-size:11px;border:1px solid #30363d;border-radius:5px;padding:2px 7px', 'hide all');

    var row = E('div', 'display:flex;flex-wrap:wrap;align-items:flex-end;gap:14px');
    row.appendChild(family('Chart type', [typeSel]));
    row.appendChild(sep());
    row.appendChild(family('Strategies · proprietary', strat));
    row.appendChild(sep());
    row.appendChild(family('Indicators · standard', ind));
    row.appendChild(sep());
    row.appendChild(family('Drawings', draw.concat([magnet, hideAll])));
    bar.appendChild(row);

    // range buttons
    var rangebar = E('div', 'display:flex;gap:6px;margin-top:8px');
    [['3M', 63], ['6M', 126], ['1Y', 252], ['2Y', 504], ['Max', 0]].forEach(function (r) {
      var b = E('span', 'cursor:pointer;font-size:11px;color:' + PALETTE.text + ';border:1px solid #30363d;border-radius:5px;padding:2px 8px', r[0]);
      b.onclick = function () {
        rangebar.querySelectorAll('span').forEach(function (x) { x.style.color = PALETTE.text; x.style.borderColor = '#30363d'; });
        b.style.color = PALETTE.textHi; b.style.borderColor = '#8b949e';
        setRange(r[1]);
      };
      if (r[1] === 0) { b.style.color = PALETTE.textHi; b.style.borderColor = '#8b949e'; }
      rangebar.appendChild(b);
    });
    bar.appendChild(rangebar);

    function setRange(n) {
      if (!n || n >= S.length) chart.timeScale().fitContent();
      else chart.timeScale().setVisibleRange({ from: S[S.length - n].time, to: S[S.length - 1].time });
    }

    // ---- crosshair readout ---------------------------------------------------
    function showR(d) {
      if (!d) { readout.innerHTML = ''; return; }
      var pc = d.open ? ((d.close - d.open) / d.open * 100) : 0;
      readout.innerHTML = '<b style="color:' + PALETTE.textHi + '">' + d.time + '</b>&nbsp; O ' + num(d.open) +
        '&nbsp; H ' + num(d.high) + '&nbsp; L ' + num(d.low) + '&nbsp; <b style="color:' + PALETTE.textHi + '">C ' + num(d.close) + '</b>' +
        '&nbsp; <span style="color:' + (pc >= 0 ? PALETTE.up : PALETTE.down) + '">' + (pc >= 0 ? '+' : '') + pc.toFixed(2) + '%</span>' +
        (d.dvpt != null ? '&nbsp;·&nbsp;<span style="color:' + PALETTE.dvpt + '">DVPT ' + fmtInr(d.dvpt) + (d.r1m > 1 ? ' inst' : '') + '</span>' : '') +
        (d.deliv != null ? '&nbsp;·&nbsp;Deliv ' + num(d.deliv, 1) + '%' : '');
    }
    function tkey(t) { return (typeof t === 'object' && t) ? (t.year + '-' + ('0' + t.month).slice(-2) + '-' + ('0' + t.day).slice(-2)) : t; }
    chart.subscribeCrosshairMove(function (p) {
      if (!p || !p.time) { showR(S[S.length - 1]); return; }
      showR(byTime[tkey(p.time)] || S[S.length - 1]);
    });
    showR(S[S.length - 1]);

    // ---- responsive (kills the "stretch": width follows the container) -------
    var ro = new ResizeObserver(function () {
      var w = chartDiv.clientWidth;
      if (w) chart.applyOptions({ width: w });
    });
    ro.observe(chartDiv);

    // boot
    loadCpr(cprTf);
    refreshMarkers();
    setRange(0);

    return {
      chart: chart, candle: candle,
      setCprTimeframe: loadCpr,
      toggle: function (id, v) { if (reg[id]) { reg[id].visible = v; reg[id].apply(v); } },
      destroy: function () { ro.disconnect(); chart.remove(); }
    };
  }

  // --- colour helpers ----------------------------------------------------------
  function hexA(hex, a) {
    var h = hex.replace('#', ''); if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
  }
  function lighten(hex) {
    var h = hex.replace('#', ''); if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var r = Math.min(255, parseInt(h.slice(0, 2), 16) + 60), g = Math.min(255, parseInt(h.slice(2, 4), 16) + 60), b = Math.min(255, parseInt(h.slice(4, 6), 16) + 60);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }
  function drawIcon(t) {
    return { trendline: '╱', horizontal: '──', rectangle: '▭', text: 'T', measure: '⊹' }[t] || '·';
  }

  return { createStockChart: createStockChart, palette: PALETTE };
})();
