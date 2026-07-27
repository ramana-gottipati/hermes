"""src/web/home/stock_chart_g.py — the Graphite stock chart (W1). ADDITIVE, isolated.

WHY THIS EXISTS RATHER THAN A REUSE (the recorded verdict, W1):
`src/web/stock_chart_v3.py` (the M4 fork) and `src/web/stock_chart.py` (the classic engine) are
BOTH unusable from this package — `stock_chart_v3` is on the `tests/test_home_isolation.py` BANNED
list by name, and the classic engine's `SNIPPET` binds legacy DOM (`.chartlbl`, `.rangebar`,
`#ivBar`, `.fbar`) plus the `dashboard` module, which is banned too. So the chart is RE-IMPLEMENTED
here in the Graphite idiom, carrying the parts a stock page owes: the proprietary candle identity
(blue-up / grey-down with crisp outlines, straight off `tokens.py`'s `--candle-*` variables),
institutional price zones, the DVPT and delivery-percentage panes, range control, a crosshair
readout, fullscreen, and the branded one-click screenshot. The analyst WORKSTATION on top of that
(drawings · fib · Wolfe/harmonic/CPR/MA overlays · compare · indicator panes) is NOT reproduced —
it stays on classic `/dash/stock`, linked from the section header. See the W1 report for the
block-level parity list.

DOM safety: the data island is emitted inside `<script type="application/json">` (never executable),
with `<` escaped, and the client parses it with `JSON.parse`. No server value is ever interpolated
into JavaScript source.
"""
from __future__ import annotations

import html as _html
import json as _json
import urllib.parse as _uq

_LWC_CDN = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"

RANGES = (("3M", 63), ("6M", 126), ("1Y", 252), ("2Y", 504), ("5Y", 1260), ("Max", 0))


COLS = ("t", "o", "h", "l", "c", "dvpt", "dp", "r1m", "tv", "dv")


def _payload(island: dict) -> str:
    """The island as inert JSON. `</script>` and `<` can never close the tag.

    Rows are emitted as COMPACT ARRAYS in `COLS` order rather than objects: at the full-archive
    depth (`?chart=max`, ~5,400 sessions for the deepest name) the repeated key names alone cost
    ~50 bytes a row — enough to push the document past the 1,000,000-byte archetype budget. The
    client re-labels them in one pass. Rupee figures round to whole rupees; the paise are noise at
    crore scale and cost bytes on every row.
    """
    rows = []
    for s in (island or {}).get("series") or []:
        rows.append([s.get("t"), _f(s.get("o")), _f(s.get("h")), _f(s.get("l")), _f(s.get("c")),
                     _i(s.get("dvpt")), _f(s.get("dp")), _f(s.get("r1m")),
                     _i(s.get("tv")), _i(s.get("dv"))])
    zones = [{"label": z.get("label"), "price": _f(z.get("price"))}
             for z in ((island or {}).get("zones") or []) if _f(z.get("price")) is not None]
    body = {"cols": list(COLS), "rows": rows, "zones": zones}
    # `allow_nan=False` is the BACKSTOP, not the guard: Python emits bare `NaN`/`Infinity` by
    # default, which are NOT valid JSON, so the browser's `JSON.parse` throws and the ENTIRE chart
    # silently disappears (the client catch returns). `_f`/`_i` already coerce every non-finite to
    # null; if one ever slips past, fail to an empty island (an honest blank pane) rather than a
    # dead canvas. Non-finite values are real here: the corporate-action back-adjustment divides.
    try:
        txt = _json.dumps(body, separators=(",", ":"), default=str, allow_nan=False)
    except (ValueError, TypeError):
        txt = _json.dumps({"cols": list(COLS), "rows": [], "zones": []}, separators=(",", ":"))
    return txt.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def _finite(v):
    """float(v) when it is a real, finite number — else None. NaN/±inf must never reach the
    payload: they are invalid JSON and would blank the whole chart."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (f != f or f in (float("inf"), float("-inf"))) else f


def _f(v):
    return _finite(v)


def _i(v):
    f = _finite(v)
    if f is None:
        return None
    try:
        return int(round(f))
    except (OverflowError, ValueError):     # belt-and-braces: round() on a huge float
        return None


def chart_html(sym: str, name: str, island: dict, deep: bool = False) -> str:
    """The chart block. `deep=True` means the caller already asked the read layer for the full
    archive (`?chart=max`), so the 'Load full history' affordance is not offered again."""
    series = (island or {}).get("series") or []
    s_sym = _html.escape(str(sym or ""))
    s_name = _html.escape(str(name or ""))
    if not series:
        return ('<p class="g-empty">No price tape for this symbol yet — the chart appears once the '
                "bhav copy carries it.</p>")
    last = series[-1]
    hdr = (str(last.get("t") or "")[:10] + " · close " + ("%s" % last.get("c")))
    adj_note = ("" if not (island or {}).get("adjusted") else
                '<span class="g-cnote">split / bonus back-adjusted</span>')
    # URL-QUOTE the symbol, do not merely HTML-escape it: `&` is legal in NSE tickers (M&M,
    # M&MFIN, J&KBANK) and `clean_symbol` preserves it, so `?sym=M&amp;M` decodes to `sym=M`
    # plus a stray `M` param — the "Full history" link would silently open the wrong stock.
    deeper = ("" if deep else
              '<a class="g-cbtn" href="?sym=' + _html.escape(_uq.quote(str(sym or "")))
              + '&amp;chart=max">Full history</a>')
    btns = "".join('<button type="button" class="g-cbtn' + (" on" if lab == "1Y" else "") +
                   '" data-r="' + str(n) + '">' + lab + "</button>" for lab, n in RANGES)
    return (
        '<div class="g-chart" id="g-chart">'
        '<div class="g-cbar">'
        '<span class="g-crange" role="group" aria-label="Chart range">' + btns + "</span>"
        '<span class="g-csp"></span>'
        '<button type="button" class="g-cbtn" id="g-cshot" aria-label="Download a branded PNG of this chart">Save PNG</button>'
        '<button type="button" class="g-cbtn" id="g-cfull" aria-label="Toggle fullscreen chart">Fullscreen</button>'
        + deeper +
        "</div>"
        '<div class="g-cwrap">'
        '<div class="g-chead"><b>' + s_sym + "</b>" + (" · " + s_name if s_name else "")
        + '<span class="g-cnote">' + _html.escape(hdr) + "</span>" + adj_note + "</div>"
        '<div class="g-crdt" id="g-crdt" aria-live="off"></div>'
        '<div class="g-chost" id="g-cprice"></div>'
        '<div class="g-clab">Delivery size per trade (DVPT) — amber marks an institutional-intensity day</div>'
        '<div class="g-chost sm" id="g-cdvpt"></div>'
        '<div class="g-clab">Delivery %</div>'
        '<div class="g-chost sm" id="g-cdeliv"></div>'
        '<div class="g-clab">Traded value (bar) with the delivered part highlighted — how much of '
        'the turnover actually changed hands</div>'
        '<div class="g-chost sm" id="g-cval"></div>'
        "</div>"
        '<script type="application/json" id="g-cdata">' + _payload(island) + "</script>"
        '<script src="' + _LWC_CDN + '" defer></script>'
        + _SNIPPET + "</div>")


CSS = """<style>/* g-chart */
:root[data-ui-g] .g-chart{margin:2px 0 6px}
:root[data-ui-g] .g-cbar{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:8px}
:root[data-ui-g] .g-csp{flex:1}
:root[data-ui-g] .g-crange{display:inline-flex;gap:2px;background:var(--bg-2);border:1px solid var(--line-2);
  border-radius:var(--r-pill);padding:3px}
:root[data-ui-g] .g-cbtn{background:var(--bg-3);border:1px solid var(--line-2);color:var(--ink-2);
  border-radius:8px;padding:5px 11px;font:600 12px var(--font);cursor:pointer;text-decoration:none;display:inline-block}
:root[data-ui-g] .g-crange .g-cbtn{border:0;background:transparent;border-radius:var(--r-pill);padding:4px 10px}
:root[data-ui-g] .g-cbtn:hover{border-color:var(--accent);color:var(--ink)}
:root[data-ui-g] .g-crange .g-cbtn.on{color:var(--on-accent);background:linear-gradient(120deg,var(--accent),var(--accent-hi))}
:root[data-ui-g] .g-cwrap{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:10px 12px 12px;position:relative}
:root[data-ui-g] .g-chead{font-size:12.5px;color:var(--ink-2);display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
:root[data-ui-g] .g-chead b{color:var(--ink);font-size:14px}
:root[data-ui-g] .g-cnote{font:600 10.5px/1 var(--mono);color:var(--ink-3);background:var(--bg-2);
  border:1px solid var(--line);border-radius:var(--r-pill);padding:4px 8px}
:root[data-ui-g] .g-crdt{font:600 11.5px/1.5 var(--mono);color:var(--ink);min-height:18px;margin:4px 0 2px}
:root[data-ui-g] .g-chost{height:320px;width:100%}
:root[data-ui-g] .g-chost.sm{height:110px}
:root[data-ui-g] .g-clab{font-size:11px;color:var(--ink-3);margin:8px 0 2px}
:root[data-ui-g] .g-cwrap.g-cfs{position:fixed;inset:0;z-index:9999;border-radius:0;overflow:auto;
  background:var(--bg-0);padding:14px 18px}
:root[data-ui-g] .g-cwrap.g-cfs .g-chost{height:62vh}
:root[data-ui-g] .g-cwrap.g-cfs .g-chost.sm{height:14vh}
:root[data-ui-g] .g-cbrand{position:absolute;right:16px;bottom:14px;z-index:3;pointer-events:none;
  display:inline-flex;align-items:center;gap:6px;padding:4px 11px;border-radius:var(--r-pill);
  background:var(--bg-2);border:1px solid var(--accent);font:700 12px var(--font);color:var(--ink)}
:root[data-ui-g] .g-cbrand i{width:7px;height:7px;border-radius:50%;background:var(--accent);display:inline-block;font-style:normal}
</style>"""


# The chart engine. Plain string (no f-string) — the VPS runs 3.10, where a backslash inside an
# f-string expression is a syntax error, and this snippet is full of escapes.
_SNIPPET = """<script>
(function(){
  function boot(){
    var el=document.getElementById('g-cdata'), host=document.getElementById('g-cprice');
    if(!el||!host) return;
    if(!window.LightweightCharts){ host.innerHTML='<p class="g-empty">The chart library did not load (offline?). Every number on this page is still readable below.</p>'; return; }
    var D; try{ D=JSON.parse(el.textContent||'{}'); }catch(e){ return; }
    // rows arrive as compact arrays in D.cols order (payload budget) — re-label them once
    var CO=D.cols||[], S=(D.rows||[]).map(function(r){
      var o={}; for(var i=0;i<CO.length;i++) o[CO[i]]=r[i]; return o; });
    if(!S.length) return;
    var cs=getComputedStyle(document.documentElement);
    function T(n,f){ var v=cs.getPropertyValue(n); return (v&&v.trim())||f; }
    var CUP=T('--candle-up','#4d9dff'), CDN=T('--candle-dn','#8496ad'),
        CUPL=T('--candle-up-line','#a9d0ff'), CDNL=T('--candle-dn-line','#c6d1e2'),
        INK=T('--ink-2','#9fb0c0'), LINE=T('--line','#223040'), BG=T('--bg-0','#080b11'),
        ACC=T('--accent','#17b0aa'), WARN=T('--warn','#f4b740'), INK3=T('--ink-3','#6f8394');
    var common={ layout:{background:{color:BG},textColor:INK,fontSize:11},
      grid:{vertLines:{color:LINE},horzLines:{color:LINE}},
      timeScale:{borderColor:LINE,rightOffset:3},
      rightPriceScale:{borderColor:LINE}, crosshair:{mode:0},
      handleScroll:true, handleScale:true };
    function mk(node,h){ return LightweightCharts.createChart(node,
      Object.assign({width:Math.max(0,node.clientWidth),height:h},common)); }
    var pc=mk(host,host.clientHeight||320);
    // the proprietary identity: blue-up / grey-down bodies, always outlined (D144)
    var candle=pc.addCandlestickSeries({upColor:CUP,downColor:CDN,borderVisible:true,
      borderUpColor:CUPL,borderDownColor:CDNL,wickUpColor:CUPL,wickDownColor:CDNL});
    candle.setData(S.map(function(d){return {time:d.t,open:d.o,high:d.h,low:d.l,close:d.c};}));
    (D.zones||[]).forEach(function(z){ try{ candle.createPriceLine({price:z.price,color:ACC,
      lineWidth:1,lineStyle:2,axisLabelVisible:true,title:z.label}); }catch(e){} });

    var dh=document.getElementById('g-cdvpt'), vh=document.getElementById('g-cdeliv'),
        th=document.getElementById('g-cval');
    var dc=dh?mk(dh,dh.clientHeight||110):null, vc=vh?mk(vh,vh.clientHeight||110):null,
        tc=th?mk(th,th.clientHeight||110):null;
    if(dc){ dc.addHistogramSeries({priceLineVisible:false}).setData(
      S.filter(function(d){return d.dvpt!=null;}).map(function(d){
        return {time:d.t,value:d.dvpt,color:(d.r1m!=null&&d.r1m>1)?WARN:INK3}; })); }
    if(vc){ vc.addLineSeries({color:ACC,lineWidth:2,priceLineVisible:false}).setData(
      S.filter(function(d){return d.dp!=null;}).map(function(d){
        return {time:d.t,value:d.dp}; })); }
    if(tc){ // turnover in muted grey, the delivered part over it in the accent — same axis
      tc.addHistogramSeries({priceLineVisible:false,color:INK3}).setData(
        S.filter(function(d){return d.tv!=null;}).map(function(d){
          return {time:d.t,value:d.tv}; }));
      tc.addHistogramSeries({priceLineVisible:false,color:ACC}).setData(
        S.filter(function(d){return d.dv!=null;}).map(function(d){
          return {time:d.t,value:d.dv}; })); }
    var CHARTS=[pc,dc,vc,tc];

    // range control — the island is server-bounded; these buttons slice it client-side
    function setRange(n){ if(!n||n>=S.length){ CHARTS.forEach(function(c){ if(c)c.timeScale().fitContent(); }); return; }
      var from=S[S.length-n].t, to=S[S.length-1].t;
      CHARTS.forEach(function(c){ if(c) try{ c.timeScale().setVisibleRange({from:from,to:to}); }catch(e){} }); }
    var rbtns=document.querySelectorAll('.g-crange .g-cbtn');
    Array.prototype.forEach.call(rbtns,function(b){ b.addEventListener('click',function(){
      Array.prototype.forEach.call(rbtns,function(x){x.classList.remove('on');});
      b.classList.add('on'); setRange(parseInt(b.getAttribute('data-r'),10)); }); });
    setRange(252);

    // crosshair readout — every number on the chart is legible as text too
    var rdt=document.getElementById('g-crdt');
    function tk(t){ return (typeof t==='object'&&t)?(t.year+'-'+('0'+t.month).slice(-2)+'-'+('0'+t.day).slice(-2)):t; }
    var byT={}; S.forEach(function(d){ byT[d.t]=d; });
    function show(p){ var d=(p&&p.time)?byT[tk(p.time)]:S[S.length-1]; if(!d||!rdt) return;
      var bits=[d.t,'O '+d.o,'H '+d.h,'L '+d.l,'C '+d.c];
      if(d.dp!=null) bits.push('deliv '+d.dp+'%');
      if(d.dvpt!=null) bits.push('DVPT '+Math.round(d.dvpt).toLocaleString('en-IN'));
      if(d.tv!=null) bits.push('turnover '+Math.round(d.tv/1e7).toLocaleString('en-IN')+' cr');
      rdt.textContent=bits.join('  ·  '); }
    pc.subscribeCrosshairMove(show); show(null);

    // keep every canvas bound to its column (observe the stable parent, width-gated)
    var wrap=host.closest('.g-cwrap');
    function fit(){ [[pc,host],[dc,dh],[vc,vh],[tc,th]].forEach(function(pr){
      var c=pr[0],n=pr[1]; if(!c||!n) return; var w=n.clientWidth,h=n.clientHeight;
      if(w>0&&h>0) try{ c.resize(w,h); }catch(e){} }); }
    var tmr=null; function later(){ if(tmr)clearTimeout(tmr); tmr=setTimeout(fit,120); }
    if(window.ResizeObserver&&wrap) new ResizeObserver(later).observe(wrap);
    window.addEventListener('resize',later);

    // fullscreen (Shift+F / Escape) + the brand mark that rides the chart in both states
    var brand=document.createElement('div'); brand.className='g-cbrand';
    brand.innerHTML='<i></i>patearn'; if(wrap) wrap.appendChild(brand);
    var fb=document.getElementById('g-cfull');
    function togFs(){ if(!wrap) return; wrap.classList.toggle('g-cfs');
      if(fb) fb.textContent=wrap.classList.contains('g-cfs')?'Exit fullscreen':'Fullscreen';
      requestAnimationFrame(fit); }
    if(fb) fb.addEventListener('click',togFs);
    document.addEventListener('keydown',function(e){
      if((e.key==='F'||e.key==='f')&&e.shiftKey&&!/^(INPUT|TEXTAREA)$/.test((e.target||{}).tagName||'')){ e.preventDefault(); togFs(); }
      else if(e.key==='Escape'&&wrap&&wrap.classList.contains('g-cfs')) togFs(); });

    // one-click branded PNG: the price canvas under a title strip + the patearn mark
    var sb=document.getElementById('g-cshot');
    if(sb) sb.addEventListener('click',function(){
      var src; try{ src=pc.takeScreenshot(); }catch(e){ return; }
      if(!src) return;
      var head=document.querySelector('.g-chead'), title=head?head.textContent.replace(/\\s+/g,' ').trim():'';
      var PAD=44, cv=document.createElement('canvas');
      cv.width=src.width; cv.height=src.height+PAD;
      var g=cv.getContext('2d');
      g.fillStyle=BG; g.fillRect(0,0,cv.width,cv.height);
      g.drawImage(src,0,PAD);
      g.fillStyle=T('--ink','#e8eef4'); g.font='600 15px system-ui,-apple-system,Segoe UI,Roboto,sans-serif';
      g.fillText(title.slice(0,110),14,27);
      g.fillStyle=ACC; g.beginPath(); g.arc(cv.width-78,20,4,0,6.284); g.fill();
      g.fillStyle=T('--ink','#e8eef4'); g.font='700 14px system-ui,-apple-system,Segoe UI,Roboto,sans-serif';
      g.fillText('patearn',cv.width-68,25);
      var a=document.createElement('a');
      a.href=cv.toDataURL('image/png');
      a.download=(title.split(' ')[0]||'chart')+'-patearn.png';
      document.body.appendChild(a); a.click();
      setTimeout(function(){ try{a.remove();}catch(e){} },0); });
  }
  if(window.LightweightCharts) boot();
  else window.addEventListener('load',boot);
})();
</script>"""


def _selftest() -> int:
    empty = chart_html("TCS", "Tata Consultancy", {"series": [], "zones": []})
    assert "g-empty" in empty and "g-chart" not in empty
    isl = {"series": [{"t": "2026-01-0%d" % i, "o": 10 + i, "h": 11 + i, "l": 9 + i, "c": 10 + i,
                       "dvpt": 1000 * i, "dp": 40 + i, "r1m": 1.2, "tv": 5, "dv": 3}
                      for i in range(1, 6)],
           "zones": [{"label": "P3M", "price": 12.5}], "adjusted": True}
    html = chart_html("TCS", "Tata Consultancy <b>", isl, deep=False)
    assert 'id="g-cdata"' in html and 'type="application/json"' in html
    assert "&lt;b&gt;" in html, "the company name must be escaped"
    assert "back-adjusted" in html and "Full history" in html
    assert "candle-up" in _SNIPPET and "takeScreenshot" in _SNIPPET
    for host in ("g-cprice", "g-cdvpt", "g-cdeliv", "g-cval"):
        assert 'id="' + host + '"' in html, host
    # the payload-budget guard: compact rows must keep a full-archive island well inside 1 MB
    deep_isl = {"series": [{"t": "2024-01-01", "o": 1234.55, "h": 1240.1, "l": 1220.05,
                            "c": 1235.75, "dvpt": 1234567.0, "dp": 56.7, "r1m": 1.23,
                            "tv": 1234567890.12, "dv": 987654321.55}] * 6000,
                "zones": []}
    deep_bytes = len(chart_html("RELIANCE", "Reliance Industries", deep_isl, deep=True).encode())
    assert deep_bytes < 640_000, deep_bytes
    # DOM safety: no raw '<' may survive inside the JSON island
    isl2 = {"series": [{"t": "2026-01-01", "o": 1, "h": 1, "l": 1, "c": 1}],
            "zones": [{"label": "</script><img src=x>", "price": 1}]}
    p = _payload(isl2)
    assert "<" not in p and "\\u003c" in p
    assert "Full history" not in chart_html("TCS", "", isl, deep=True)
    # no legacy/preview marker may appear in this module's output
    for m in ("pv3-", "data-ui-v3", "uk-sub", "chartlbl", "rangebar"):
        assert m not in html and m not in CSS, m
    print("home/stock_chart_g selftest OK — island inert, identity tokens, no legacy markers")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
