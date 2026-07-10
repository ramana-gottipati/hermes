"""stock_chart.py — the live /dash/stock chart engine (the "one chart" rebuild).

Self-contained SNIPPET (same proven pattern as cpr_overlay / indicators_overlay /
mep_overlay / wolfe_overlay) that REPLACES the old 4-pane stretched stack with ONE
responsive price chart + a single four-family control rail. It reads the page data
already exposed as ``window.__wfdata`` ({series, zones}), builds the chart, and
RE-EXPOSES the exact ``window.__wfpc`` / ``window.__wfcandle`` / ``[data-ptf]``
contract the committed strategy overlays bind to — so CPR / MA / MEP / Wolfe keep
working untouched. **The CPR in particular stays owned by ``cpr_overlay.py``; this
module never draws it.**

What it does, vs the old inline block it supersedes:

  * ONE chart — DVPT / Delivery% / Traded-&-Delivery-value fold into docked sub-panes
    (overlay price scales) instead of three separate short-wide charts → kills the
    "stretch". Every per-day figure stays on the hover readout, so no data regresses.
  * The four-family rail (Ramana's taxonomy): **Chart-type** dropdown (Candles / Hollow
    / Heikin-Ashi / Line / Area; Renko + P&F flagged "soon") · **Strategies** (CPR /
    DVPT / MEP / Wolfe / RS — opt-in) · **Indicators** (MA / VWAP / Anchored-VWAP + the
    delivery / traded lanes) · **Drawings** (trendline / ray / rect / Fib / text / measure
    + 🧲 magnet + hide-all, persisted per-symbol). One shared rail; everything opt-in.
  * The strategy / indicator chips injected by the committed overlay snippets land in the
    right family because this rail pre-creates their anchors (``#stratBar`` for
    CPR/MEP, ``#cprBar`` for MA) and hides MA's duplicate label.
  * Same interval (D/W/M/Q) resample, range buttons, and crosshair readout as before —
    ``[data-ptf]`` / ``.rangebar`` are re-homed into the rail and re-bound here (the CPR
    ladder still hooks ``[data-ptf]`` additively, so it keeps following the interval).

dashboard.py wires it with two anchored hooks (uncommitted, like the other overlays):
an import, and replacing the old inline ``<script>`` block with the data island + the
``{token}``. No DB here; ``rs_overlay.py`` owns the one new endpoint. No circular import.
"""
from __future__ import annotations

# Plain string (NOT an f-string) so the JS braces survive; dashboard.py inserts it
# via its f-string template like `{_STOCK_CHART_SNIPPET}`, after a data island that
# sets `window.__wfdata` and the lightweight-charts <script>.
SNIPPET = """<script>
(function(){
  "use strict";
  // --- the fixed colour grammar (mirrors hermes-charts.js PALETTE) ----------
  // --- the colour grammar, SEEDED FROM THE DESIGN TOKENS (D-COL-4) -----------
  // canvas/lightweight-charts can't consume var(), so read the token VALUES once from
  // :root and build the whole C object from them. Every entry carries its exact current
  // hex as a fallback, so if a token is ever absent the chart is byte-identical to before
  // (no blank-canvas risk). Chart chrome (bg/grid/border/txt/ink) tracks the page surfaces;
  // indicator identities map to tokens holding their exact shipped value (no recolour).
  var _cs=getComputedStyle(document.documentElement);
  function _t(n,fb){ var v=_cs.getPropertyValue(n); return (v&&v.trim())||fb; }
  var C={up:_t('--up','#3fd486'),down:_t('--down','#ff6a7a'),line:_t('--chart-line','#1f6feb'),dvpt:_t('--chart-dvpt','#d29922'),dvptIdle:_t('--chart-idle','#30506b'),
    deliv:_t('--chart-blue','#58a6ff'),tval:_t('--line-2','#30363d'),dval:_t('--chart-dval','#2ea043'),vwap:_t('--accent-orange','#f0883e'),avwap:_t('--series-5','#db61a2'),
    rs:_t('--series-1','#39c5cf'),wolfe:_t('--chart-blue','#58a6ff'),harm:_t('--series-8','#f778ba'),bb:_t('--series-3','#a371f7'),atr:_t('--series-4','#56d364'),
    vol:_t('--chart-vol','#3b5168'),rsi:_t('--chart-rsi','#d2a8ff'),macd:_t('--chart-blue','#58a6ff'),macdSig:_t('--accent-orange','#f0883e'),cmp:_t('--series-1','#39c5cf'),
    txt:_t('--ink-2','#8b949e'),txtHi:_t('--ink','#e6edf3'),dim:_t('--ink-3','#7e90a8'), // --ink-3: AA-safe inline (stylesheet can't reach a JS-set color)
    border:_t('--line-2','#30363d'),grid:_t('--bg-3','#21262d'),bg:_t('--bg-2','#161b22')};
  function E(t,css,html){ var n=document.createElement(t); if(css)n.style.cssText=css; if(html!=null)n.innerHTML=html; return n; }
  function hexA(hex,a){ var h=hex.replace('#',''); if(h.length===3)h=h[0]+h[0]+h[1]+h[1]+h[2]+h[2];
    return 'rgba('+parseInt(h.slice(0,2),16)+','+parseInt(h.slice(2,4),16)+','+parseInt(h.slice(4,6),16)+','+a+')'; }
  function n2(v){ return v==null?'-':(Math.round(v*100)/100); }
  function cr(v){ return '\\u20b9'+Math.round(v).toLocaleString('en-IN'); }
  function chipCss(on,col){ return 'cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;'+
    'padding:3px 9px;border-radius:20px;user-select:none;white-space:nowrap;'+
    (on?('background:'+hexA(col,0.16)+';color:'+col):('border:1px solid var(--line-2);color:var(--ink-2)')); }
  function dot(col){ return '<span style="width:7px;height:7px;border-radius:50%;background:'+col+'"></span>'; }

  function boot(){
    var host=document.getElementById('priceChart'); if(!host) return;
    if(!window.LightweightCharts){ host.innerHTML='<div style="color:var(--ink-2);padding:20px">Chart library failed to load (offline?).</div>'; return; }
    var DATA=window.__wfdata; if(!DATA||!DATA.series||!DATA.series.length) return;
    var S0=DATA.series, ZONES=DATA.zones||[];        // S0 = raw daily, never mutated
    var iv='d', ctype='candle', RT=S0.slice();       // RT = current resampled rows
    // FUT = future WHITESPACE times appended to the price series so the time scale
    // extends past the last candle — drawings (trendlines, EPA projections, fib
    // anchors) can then land in real future space instead of snapping back to the
    // last bar. Weekday-stepped for daily; 7d/1mo/3mo for W/M/Q. Whitespace rows
    // carry no OHLC, so nothing else changes (readout falls back to the last bar).
    var FUT=[];
    function futureTimes(){ var N={d:60,w:26,m:12,q:8}[iv]||0, out=[];
      if(!N||!RT.length) return out;
      var t=new Date(RT[RT.length-1].time+'T00:00:00Z');
      for(var i=0;i<N;i++){
        if(iv==='d'){ do{ t.setUTCDate(t.getUTCDate()+1); }while(t.getUTCDay()===0||t.getUTCDay()===6); }
        else if(iv==='w'){ t.setUTCDate(t.getUTCDate()+7); }
        else if(iv==='m'){ t.setUTCMonth(t.getUTCMonth()+1); }
        else { t.setUTCMonth(t.getUTCMonth()+3); }
        out.push({time:t.toISOString().slice(0,10)});
      }
      return out; }

    // ---- the ONE chart ------------------------------------------------------
    // bounded host: height follows the viewport (clamp) instead of a fixed 480 — the
    // old fixed height + width-only observer made the chart grow wide but never tall
    // ("narrow top, broad sides"). max-width keeps it readable on ultra-wide monitors.
    host.style.cssText='height:clamp(420px,62vh,760px);max-width:1280px;margin:0 auto;position:relative;touch-action:none';
    // Mobile responsiveness (<=640px): a shorter chart so it isn't awkwardly portrait on a
    // narrow phone, and the four-family rail wraps + scrolls instead of overflowing the page.
    // touch-action:none on the host lets lightweight-charts own the pinch/drag gestures.
    if(!document.getElementById('hsc-mobile')){ var ms=E('style'); ms.id='hsc-mobile';
      ms.textContent='@media (max-width:640px){#priceChart{height:clamp(300px,52vh,460px)!important}'
        +'#priceChart .cfs{height:100vh!important}}';
      document.head.appendChild(ms); }
    var common={ layout:{background:{color:C.bg},textColor:C.txt,fontSize:11},
      grid:{vertLines:{color:C.grid},horzLines:{color:C.grid}},
      timeScale:{borderColor:C.border,rightOffset:3},
      rightPriceScale:{borderColor:C.border,scaleMargins:{top:0.06,bottom:0.28}},
      crosshair:{mode:0}, handleScroll:true, handleScale:true };
    var pc=LightweightCharts.createChart(host, Object.assign({height:host.clientHeight||480}, common));
    window.__wfpc=pc;
    var candle=pc.addCandlestickSeries({upColor:C.up,downColor:C.down,wickUpColor:C.up,wickDownColor:C.down,borderVisible:false});
    window.__wfcandle=candle;
    var pline=pc.addLineSeries({color:C.line,lineWidth:2,priceLineVisible:false,lastValueVisible:false}); pline.applyOptions({visible:false});
    var parea=pc.addAreaSeries({lineColor:C.line,topColor:'rgba(31,111,235,0.25)',bottomColor:'rgba(31,111,235,0.02)',lineWidth:2,priceLineVisible:false,lastValueVisible:false}); parea.applyOptions({visible:false});
    // Kagi: a single reversing line (thick/thin reduced to one stepped line for EOD)
    var kagiL=pc.addLineSeries({color:C.rs,lineWidth:2,lineStyle:0,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); kagiL.applyOptions({visible:false});
    // Institutional price zones (P1M/P3M/P6M/P12M/R12M) — part of the DVPT
    // footprint, so they show/hide WITH the DVPT chip (retained for toggling;
    // v4 price-lines have no `visible`, so we remove + re-create).
    var zoneLines=[];
    function setZones(v){
      if(v){ if(!zoneLines.length) zoneLines=ZONES.map(function(z){ return candle.createPriceLine({price:z.price,color:z.color||C.dim,lineWidth:1,lineStyle:2,axisLabelVisible:true,title:z.label||''}); }); }
      else { zoneLines.forEach(function(pl){ try{ candle.removePriceLine(pl); }catch(e){} }); zoneLines=[]; }
    }
    setZones(true);

    // docked flow sub-panes (overlay price scales, shared bottom band) — collapse
    // the old DVPT / Delivery% / Traded-value panes into the ONE chart.
    var FLOW={top:0.80, bottom:0.02};
    var dvptH=pc.addHistogramSeries({priceScaleId:'dvpt',priceFormat:{type:'volume'},lastValueVisible:false});
    pc.priceScale('dvpt').applyOptions({scaleMargins:FLOW});
    var delivL=pc.addLineSeries({priceScaleId:'deliv',color:C.deliv,lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
    pc.priceScale('deliv').applyOptions({scaleMargins:FLOW}); delivL.applyOptions({visible:false});
    var tvCap=0, tvCapRT=null;   // tvCapRT = the RT array tvCap was computed for (CL-VIEW-11 cache)
    function capInfo(){ return {priceRange:{minValue:0,maxValue:tvCap||1}}; }
    var tvalH=pc.addHistogramSeries({priceScaleId:'tv',priceFormat:{type:'volume'},color:C.tval,autoscaleInfoProvider:capInfo,lastValueVisible:false});
    var dvalH=pc.addHistogramSeries({priceScaleId:'tv',priceFormat:{type:'volume'},color:C.dval,autoscaleInfoProvider:capInfo,lastValueVisible:false});
    pc.priceScale('tv').applyOptions({scaleMargins:FLOW}); tvalH.applyOptions({visible:false}); dvalH.applyOptions({visible:false});

    // VWAP / Anchored-VWAP (Indicators) — line series on the price scale, opt-in.
    var vwapL=pc.addLineSeries({color:C.vwap,lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); vwapL.applyOptions({visible:false});
    var avwapL=pc.addLineSeries({color:C.avwap,lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); avwapL.applyOptions({visible:false});
    var avwapAnchor=null;   // {time} chosen via the AVWAP tool

    // Bollinger Bands (20,2) + ATR bands (close +/- k*ATR) — DESCRIPTIVE volatility
    // envelopes on the price scale, opt-in. Mid = SMA(20); upper/lower = mid +/- 2*stdev.
    // ATR bands use a 14-period ATR around the close. No buy/sell semantics — just bands.
    var bbU=pc.addLineSeries({color:C.bb,lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); bbU.applyOptions({visible:false});
    var bbM=pc.addLineSeries({color:C.bb,lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); bbM.applyOptions({visible:false});
    var bbL=pc.addLineSeries({color:C.bb,lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); bbL.applyOptions({visible:false});
    var atrU=pc.addLineSeries({color:C.atr,lineWidth:1,lineStyle:0,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); atrU.applyOptions({visible:false});
    var atrLo=pc.addLineSeries({color:C.atr,lineWidth:1,lineStyle:0,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); atrLo.applyOptions({visible:false});

    // =========================================================================
    //  LOWER INDICATOR PANE — a SECOND lightweight-charts instance under the
    //  price chart (v4 has no native panes), time-synced to it. Volume / RSI(14) /
    //  MACD(12,26,9), each opt-in. window.__wfpc (the price chart) is UNTOUCHED so
    //  every overlay keeps binding to it. DESCRIPTIVE — no buy/sell semantics.
    // =========================================================================
    var lpHost=E('div','height:0;min-height:0;max-width:1280px;margin:4px auto 0;position:relative;overflow:hidden;transition:min-height .12s');
    lpHost.id='lowerPane';
    var lp=LightweightCharts.createChart(lpHost, Object.assign({height:160}, common, {
      rightPriceScale:{borderColor:'#30363d',scaleMargins:{top:0.12,bottom:0.08}},
      timeScale:{borderColor:'#30363d',rightOffset:3,visible:true,minBarSpacing:0.02} }));
    window.__wflp=lp;   // exposed for completeness; overlays do NOT use it
    var volH=lp.addHistogramSeries({priceScaleId:'vol',priceFormat:{type:'volume'},color:C.vol,lastValueVisible:false}); volH.applyOptions({visible:false});
    lp.priceScale('vol').applyOptions({scaleMargins:{top:0.12,bottom:0.08}});
    var rsiL=lp.addLineSeries({priceScaleId:'rsi',color:C.rsi,lineWidth:1.5,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); rsiL.applyOptions({visible:false});
    lp.priceScale('rsi').applyOptions({scaleMargins:{top:0.12,bottom:0.08}});
    var rsiHi=null, rsiLo=null;   // 70/30 guide lines (created when RSI turns on)
    var macdH=lp.addHistogramSeries({priceScaleId:'macd',priceFormat:{type:'price',precision:2,minMove:0.01},lastValueVisible:false}); macdH.applyOptions({visible:false});
    var macdL=lp.addLineSeries({priceScaleId:'macd',color:C.macd,lineWidth:1.5,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); macdL.applyOptions({visible:false});
    var macdSigL=lp.addLineSeries({priceScaleId:'macd',color:C.macdSig,lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}); macdSigL.applyOptions({visible:false});
    lp.priceScale('macd').applyOptions({scaleMargins:{top:0.12,bottom:0.08}});

    // --- indicator math (descriptive) ---------------------------------------
    function emaSeries(vals,n){ var k=2/(n+1),out=[],e=null; for(var i=0;i<vals.length;i++){ e=(e==null)?vals[i]:(vals[i]*k+e*(1-k)); out.push(e); } return out; }
    function rsiFrom(R,n){ n=n||14; if(R.length<n+1) return []; var g=0,l=0,out=[];
      for(var i=1;i<R.length;i++){ var ch=R[i].close-R[i-1].close, up=ch>0?ch:0, dn=ch<0?-ch:0;
        if(i<=n){ g+=up; l+=dn; if(i===n){ g/=n; l/=n; var rs=l===0?100:g/l; out.push({time:R[i].time,value:l===0?100:(100-100/(1+rs))}); } }
        else { g=(g*(n-1)+up)/n; l=(l*(n-1)+dn)/n; var rs2=l===0?100:g/l; out.push({time:R[i].time,value:l===0?100:(100-100/(1+rs2))}); } }
      return out; }
    function macdFrom(R){ if(R.length<35) return {macd:[],sig:[],hist:[]}; var cl=R.map(function(d){return d.close;});
      var e12=emaSeries(cl,12), e26=emaSeries(cl,26); var md=[]; for(var i=0;i<cl.length;i++) md.push(e12[i]-e26[i]);
      var sg=emaSeries(md,9); var macd=[],sig=[],hist=[];
      for(var j=25;j<R.length;j++){ macd.push({time:R[j].time,value:md[j]}); sig.push({time:R[j].time,value:sg[j]});
        var hv=md[j]-sg[j]; hist.push({time:R[j].time,value:hv,color:hv>=0?'rgba(63,185,80,.6)':'rgba(248,81,73,.6)'}); }
      return {macd:macd,sig:sig,hist:hist}; }

    // ---- resample (D/W/M/Q) — ported verbatim from the proven inline block ---
    function isoWeekKey(s){ var d=new Date(s+'T00:00:00Z'); var jd=(d.getUTCDay()+6)%7;
      d.setUTCDate(d.getUTCDate()-jd+3); var iy=d.getUTCFullYear();
      var j4=new Date(Date.UTC(iy,0,4)); var j4d=(j4.getUTCDay()+6)%7;
      j4.setUTCDate(j4.getUTCDate()-j4d+3); var wk=1+Math.round((d-j4)/(7*86400000));
      return iy+'-W'+('0'+wk).slice(-2); }
    function pkey(s,tf){ if(tf==='w')return isoWeekKey(s); if(tf==='m')return s.slice(0,7);
      if(tf==='q'){ var y=s.slice(0,4),mo=parseInt(s.slice(5,7),10); return y+'-Q'+(Math.floor((mo-1)/3)+1); }
      return s; }
    function resample(tf){
      var mk=function(d){ return {time:d.time,open:d.open,high:d.high,low:d.low,close:d.close,
        dvpt:(d.dvpt||0),hot:(d.r1m!=null&&d.r1m>1),delivSum:(d.deliv!=null?d.deliv:0),delivN:(d.deliv!=null?1:0),
        tval:(d.tval||0),dval:(d.dval||0)}; };
      if(tf==='d') return S0.map(mk);
      var out=[],k=null,c=null;
      for(var i=0;i<S0.length;i++){ var d=S0[i],kk=pkey(d.time,tf);
        if(kk!==k){ if(c)out.push(c); k=kk; c=mk(d); }
        else { c.high=Math.max(c.high,d.high); c.low=Math.min(c.low,d.low); c.close=d.close; c.time=d.time;
          if((d.dvpt||0)>c.dvpt)c.dvpt=d.dvpt||0; if(d.r1m!=null&&d.r1m>1)c.hot=true;
          if(d.deliv!=null){ c.delivSum+=d.deliv; c.delivN++; }
          c.tval+=(d.tval||0); c.dval+=(d.dval||0); } }
      if(c)out.push(c);
      return out;
    }
    function rawOHLC(d){ return {time:d.time,open:d.open,high:d.high,low:d.low,close:d.close}; }
    function heikin(R){ var out=[],po=null,pcl=null;
      for(var i=0;i<R.length;i++){ var d=R[i]; var hc=(d.open+d.high+d.low+d.close)/4;
        var ho=(po==null)?(d.open+d.close)/2:(po+pcl)/2; var hh=Math.max(d.high,ho,hc); var hl=Math.min(d.low,ho,hc);
        out.push({time:d.time,open:ho,high:hh,low:hl,close:hc}); po=ho; pcl=hc; }
      return out; }
    // ---- Renko / Kagi — price-driven transforms keyed on the bar dates --------
    // EOD-only: lightweight-charts needs a unique ascending time per row, so when
    // several bricks/reversals complete on one date we keep the LAST one for that date
    // (faithful enough for daily investing — every intra-day brick has no EOD data).
    // brick = ATR-of-RT (a self-scaling box, no static rupee threshold — Ramana's rule).
    function brickSize(R){ var tr=[]; for(var i=1;i<R.length;i++){ var d=R[i],p=R[i-1];
        tr.push(Math.max(d.high-d.low, Math.abs(d.high-p.close), Math.abs(d.low-p.close))); }
      if(!tr.length) return null; tr.sort(function(a,b){return a-b;});
      var med=tr[Math.floor(tr.length/2)]; return med>0?med:null; }
    function renko(R){ var bs=brickSize(R); if(!bs||R.length<2) return R.map(rawOHLC);
      var out=[],lastByT={},base=R[0].close,dir=0;
      function push(t,o,c,up){ var row={time:t,open:o,high:Math.max(o,c),low:Math.min(o,c),close:c,_up:up};
        if(lastByT[t]!=null) out[lastByT[t]]=row; else { lastByT[t]=out.length; out.push(row); } }
      for(var i=0;i<R.length;i++){ var px=R[i].close,t=R[i].time;
        while(px-base>=bs){ var o=base,c=base+bs; base=c; dir=1; push(t,o,c,true); }
        while(base-px>=bs){ var o2=base,c2=base-bs; base=c2; dir=-1; push(t,o2,c2,false); } }
      if(!out.length) out=[{time:R[R.length-1].time,open:base,high:base,low:base,close:base,_up:dir>=0}];
      return out; }
    function kagi(R){ var bs=brickSize(R); if(!bs||R.length<2) return R.map(function(d){return {time:d.time,value:d.close};});
      // thick/thin Kagi reduced to a single reversing line (value series): the line only
      // turns when price reverses by >= one brick from the running extreme.
      var out=[],lastByT={},ext=R[0].close,dir=0,val=R[0].close;
      function put(t,v){ if(lastByT[t]!=null) out[lastByT[t]]={time:t,value:v}; else { lastByT[t]=out.length; out.push({time:t,value:v}); } }
      put(R[0].time,val);
      for(var i=1;i<R.length;i++){ var px=R[i].close,t=R[i].time;
        if(dir>=0){ if(px>ext){ ext=px; val=px; } else if(ext-px>=bs){ dir=-1; ext=px; val=px; } else val=ext; }
        else { if(px<ext){ ext=px; val=px; } else if(px-ext>=bs){ dir=1; ext=px; val=px; } else val=ext; }
        put(t,val); }
      return out; }

    // ---- apply current rows to every series ---------------------------------
    function paintPrice(){
      var data;
      if(ctype==='heikin') data=heikin(RT);
      else if(ctype==='renko'){ var rk=renko(RT);
        candle.setData(rk.map(function(d){return {time:d.time,open:d.open,high:d.high,low:d.low,close:d.close};}));
        // colour each brick by direction (up/down) regardless of open<close ordering
        candle.applyOptions({upColor:C.up,downColor:C.down,borderVisible:true,borderUpColor:C.up,borderDownColor:C.down,wickUpColor:'rgba(0,0,0,0)',wickDownColor:'rgba(0,0,0,0)'});
        pline.setData([]); parea.setData([]); if(kagiL)kagiL.setData([]); return; }
      else data=RT.map(rawOHLC);
      candle.setData(data.concat(FUT));   // whitespace tail = the future projection space
      pline.setData(RT.map(function(d){return {time:d.time,value:d.close};}).concat(FUT));
      parea.setData(RT.map(function(d){return {time:d.time,value:d.close};}).concat(FUT));
      if(kagiL) kagiL.setData(ctype==='kagi'?kagi(RT):[]);
    }
    function applyRows(){
      paintPrice();
      dvptH.setData(RT.map(function(d){return {time:d.time,value:d.dvpt,color:d.hot?C.dvpt:C.dvptIdle};}));
      delivL.setData(RT.filter(function(d){return d.delivN>0;}).map(function(d){return {time:d.time,value:d.delivSum/d.delivN};}));
      // CL-VIEW-11: the 98th-pctile traded-value cap depends only on RT (the resampled
      // rows), which changes only on an interval switch — not on indicator toggles. Cache
      // it keyed on the RT array identity so a chip toggle no longer re-sorts the full
      // series. resample() always returns a fresh array, so the identity check is exact.
      if(tvCapRT!==RT){
        var tv=RT.map(function(d){return d.tval;}).filter(function(v){return v!=null&&v>0;}).sort(function(a,b){return a-b;});
        tvCap=tv.length?tv[Math.min(tv.length-1,Math.floor(tv.length*0.98))]:0;
        tvCapRT=RT;
      }
      tvalH.setData(RT.filter(function(d){return d.tval!=null;}).map(function(d){return {time:d.time,value:d.tval};}));
      dvalH.setData(RT.filter(function(d){return d.dval!=null;}).map(function(d){return {time:d.time,value:d.dval};}));
      tvalH.setMarkers(tvCap>0?RT.filter(function(d){return d.tval!=null&&d.tval>tvCap;}).map(function(d){return {time:d.time,position:'aboveBar',color:C.dvpt,shape:'arrowUp'};}):[]);
      if(reg.vwap.on) vwapL.setData(vwapFrom(RT,0));
      if(reg.avwap.on) avwapL.setData(vwapFrom(RT, anchorIdx()));
      if(reg.bb.on){ var bb=bollinger(RT,20,2); bbU.setData(bb.up); bbM.setData(bb.mid); bbL.setData(bb.lo); }
      if(reg.atr.on){ var ab=atrBands(RT,14,2); atrU.setData(ab.up); atrLo.setData(ab.lo); }
      paintLower();
      if(draw) draw.redraw();
      // harmonic: D/W/M is detected on the resampled bars server-side, so when the
      // interval crosses into (or out of) W/M, re-fetch; otherwise just re-snap.
      if(reg && reg.harm && reg.harm.on){
        var want=(iv==='w'||iv==='m')?iv:'d';
        if(want!==harmTf){ harmData=null; harmToggle(true); }
        else if(harmData) harmDrawOne();
      }
    }
    function setIv(tf){ iv=tf; RT=resample(tf); FUT=futureTimes(); applyRows(); }

    // ---- compare state (rebased multi-symbol overlay) — built into cmpBar below
    var cmpReg={ items:[] };   // [{sym, series:[lwc points], line}]
    var CMP_COLORS=[_t('--series-1','#39c5cf'),_t('--series-2','#f0883e'),_t('--series-3','#a371f7'),_t('--series-4','#56d364'),_t('--series-5','#db61a2')];

    // ---- lower pane: recompute the active sub-indicators + manage pane height -
    var lpReg={
      vol:{label:'Volume',col:C.vol,on:false},
      rsi:{label:'RSI 14',col:C.rsi,on:false},
      macd:{label:'MACD',col:C.macd,on:false}
    };
    function lpAnyOn(){ return lpReg.vol.on||lpReg.rsi.on||lpReg.macd.on; }
    function paintLower(){
      if(lpReg.vol.on){ volH.setData(RT.map(function(d){ var vol=(d.tval&&d.close)?d.tval/d.close:0;
        return {time:d.time,value:vol,color:(d.close>=d.open)?'rgba(63,185,80,.45)':'rgba(248,81,73,.45)'}; })); }
      if(lpReg.rsi.on){ rsiL.setData(rsiFrom(RT,14));
        if(!rsiHi){ rsiHi=rsiL.createPriceLine({price:70,color:'#6e7681',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'70'});
          rsiLo=rsiL.createPriceLine({price:30,color:'#6e7681',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'30'}); } }
      if(lpReg.macd.on){ var m=macdFrom(RT); macdH.setData(m.hist); macdL.setData(m.macd); macdSigL.setData(m.sig); }
      syncLower();
    }
    // the lower pane is bounded + collapses to 0 when nothing is on (no empty strip).
    // NOTE: the page skin has an !important height rule that beats a plain inline height
    // on a bare child div, so we drive the host height via min-height + height!important
    // (min-height also isn't overridden) to make the pane reliably open/collapse.
    function lpHeight(){ return lpReg.macd.on?180:(lpAnyOn()?150:0); }
    function applyLowerHeight(){ var hh=lpHeight();
      lpHost.style.setProperty('height',hh+'px','important');
      lpHost.style.setProperty('min-height',hh+'px','important');
      if(hh){ requestAnimationFrame(function(){ lp.applyOptions({width:lpHost.clientWidth||host.clientWidth,height:hh}); syncLower();
        // a second, delayed sync — on first open the price range may not be readable in
        // the same frame the pane resizes, leaving the pane on the wrong window.
        setTimeout(syncLower,120); setTimeout(syncLower,360); }); } }
    // ONE-WAY sync: the price chart is the master, the lower pane follows it. We sync the
    // BAR SPACING + the right-edge logical position so the two x-axes line up bar-for-bar
    // (both carry the full daily series, so logical indices match). Matching barSpacing is
    // what makes the lower pane show the SAME window — without it LWC re-fits each chart to
    // its own minBarSpacing and they drift. One-way only (two-way ping-pongs → froze the
    // renderer); RAF-coalesced.
    function syncLower(){ if(!lpAnyOn())return; try{
      var bs=pc.timeScale().options().barSpacing;
      lp.timeScale().applyOptions({barSpacing:bs, minBarSpacing:0.02, rightOffset:pc.timeScale().scrollPosition()});
      var r=pc.timeScale().getVisibleLogicalRange(); if(r) lp.timeScale().setVisibleLogicalRange(r);
    }catch(e){} }
    var _syncRAF=null;
    pc.timeScale().subscribeVisibleLogicalRangeChange(function(r){ if(!lpAnyOn()||!r)return;
      if(_syncRAF)return; _syncRAF=requestAnimationFrame(function(){ _syncRAF=null; syncLower(); }); });
    function lpToggle(key,v){ lpReg[key].on=v;
      if(key==='vol') volH.applyOptions({visible:v});
      else if(key==='rsi'){ rsiL.applyOptions({visible:v}); if(rsiHi){rsiHi.applyOptions({lineWidth:v?1:0});} }
      else if(key==='macd'){ macdH.applyOptions({visible:v}); macdL.applyOptions({visible:v}); macdSigL.applyOptions({visible:v}); }
      if(v) paintLower(); applyLowerHeight(); }

    // ---- range --------------------------------------------------------------
    function setRange(nn){
      if(!nn||nn>=RT.length) pc.timeScale().fitContent();
      else pc.timeScale().setVisibleRange({from:RT[Math.max(0,RT.length-nn)].time, to:RT[RT.length-1].time});
    }
    function curRange(){ var b=document.querySelector('.rangebar button.on'); return b?parseInt(b.dataset.r):0; }

    // ---- chart type ---------------------------------------------------------
    // Families on ONE chart: candle-series renders Candles/Hollow/Heikin/Renko;
    // pline=Line, parea=Area, kagiL=Kagi. Visibility is mutually exclusive.
    function setType(t){ ctype=t;
      var isLine=(t==='line'), isArea=(t==='area'), isKagi=(t==='kagi');
      var isC=(!isLine&&!isArea&&!isKagi);   // candle series carries candle/hollow/heikin/renko
      candle.applyOptions({visible:isC}); pline.applyOptions({visible:isLine}); parea.applyOptions({visible:isArea}); kagiL.applyOptions({visible:isKagi});
      if(t==='hollow') candle.applyOptions({upColor:'rgba(0,0,0,0)',borderVisible:true,borderUpColor:C.up,borderDownColor:C.down,wickUpColor:C.up,wickDownColor:C.down});
      else if(t==='candle'||t==='heikin') candle.applyOptions({upColor:C.up,downColor:C.down,borderVisible:false,wickUpColor:C.up,wickDownColor:C.down});
      // renko sets its own brick options inside paintPrice
      paintPrice();
    }

    // ---- VWAP ---------------------------------------------------------------
    function vwapFrom(R,start){ var pv=0,vv=0,out=[];
      for(var i=0;i<R.length;i++){ if(i<start)continue; var d=R[i];
        var vol=(d.tval&&d.close)?d.tval/d.close:0; var tp=(d.high+d.low+d.close)/3;
        pv+=tp*vol; vv+=vol; out.push({time:d.time,value:vv>0?pv/vv:d.close}); }
      return out; }
    function anchorIdx(){ if(!avwapAnchor)return Math.max(0,RT.length-63);
      for(var i=0;i<RT.length;i++){ if(RT[i].time>=avwapAnchor) return i; } return 0; }

    // ---- Bollinger (n,k) + ATR(n) bands — descriptive volatility envelopes ----
    function bollinger(R,n,k){ n=n||20; k=k||2; var up=[],mid=[],lo=[];
      for(var i=0;i<R.length;i++){ if(i<n-1) continue; var s=0; for(var j=i-n+1;j<=i;j++) s+=R[j].close; var m=s/n;
        var vsum=0; for(var j2=i-n+1;j2<=i;j2++){ var dd=R[j2].close-m; vsum+=dd*dd; } var sd=Math.sqrt(vsum/n);
        mid.push({time:R[i].time,value:m}); up.push({time:R[i].time,value:m+k*sd}); lo.push({time:R[i].time,value:m-k*sd}); }
      return {up:up,mid:mid,lo:lo}; }
    function atrBands(R,n,k){ n=n||14; k=k||2; var tr=[],up=[],lo=[],prevA=null;
      for(var i=0;i<R.length;i++){ var d=R[i]; var t=(i===0)?(d.high-d.low):Math.max(d.high-d.low,Math.abs(d.high-R[i-1].close),Math.abs(d.low-R[i-1].close)); tr.push(t);
        var a; if(i<n-1){ continue; } else if(i===n-1){ var s=0; for(var j=0;j<n;j++) s+=tr[j]; a=s/n; } else { a=(prevA*(n-1)+t)/n; }
        prevA=a; up.push({time:d.time,value:d.close+k*a}); lo.push({time:d.time,value:d.close-k*a}); }
      return {up:up,lo:lo}; }

    // ---- crosshair readout (#priceRdt) — keyed on raw daily, like before ----
    var rdt=document.getElementById('priceRdt');
    var byT={}; S0.forEach(function(d){byT[d.time]=d;});
    function tkey(t){ return (typeof t==='object'&&t)?(t.year+'-'+('0'+t.month).slice(-2)+'-'+('0'+t.day).slice(-2)):t; }
    function showR(d){ if(!rdt)return; if(!d){ rdt.innerHTML=''; return; }
      var h='<b>'+d.time+'</b>&nbsp; O '+n2(d.open)+'&nbsp; H '+n2(d.high)+'&nbsp; L '+n2(d.low)+'&nbsp; <b>C '+n2(d.close)+'</b>'
        +(d.dvpt!=null?'&nbsp; &middot; <span style="color:'+C.dvpt+'">DVPT '+cr(d.dvpt)+(d.r1m>1?' inst':'')+'</span>':'')
        +(d.deliv!=null?'&nbsp; &middot; Deliv '+d.deliv.toFixed(1)+'%':'');
      if(d.tval!=null){ h+='&nbsp; &middot; Traded '+cr(d.tval); if(d.dval!=null)h+=' / Deliv '+cr(d.dval)+(d.tval>0?' ('+(d.dval/d.tval*100).toFixed(0)+'%)':''); }
      rdt.innerHTML=h; }
    pc.subscribeCrosshairMove(function(p){ if(!p||!p.time){ showR(S0[S0.length-1]); return; } showR(byT[tkey(p.time)]||S0[S0.length-1]); });

    // ---- overlay registry (this engine's own toggles) -----------------------
    // The docked bottom band is reserved ONLY while a flow lane is on. When DVPT
    // (and the other flow lanes) are off, collapse it so the price reclaims the
    // space — the lane is tied to its chip, not left as an empty strip.
    function reflow(){
      var any = reg.dvpt.on || reg.deliv.on || reg.flow.on || reg.rs.on;
      candle.priceScale().applyOptions({scaleMargins:{top:0.06, bottom: any?0.28:0.06}});
    }
    var reg={
      dvpt:{label:'DVPT',col:C.dvpt,on:true, fn:function(v){ dvptH.applyOptions({visible:v}); setZones(v); reflow(); }},
      rs:{label:'RS',col:C.rs,on:false, fn:function(v){ rsToggle(v); }},
      harm:{label:'Harmonic',col:C.harm,on:false, fn:function(v){ harmToggle(v); }},
      vwap:{label:'VWAP',col:C.vwap,on:false, fn:function(v){ if(v)vwapL.setData(vwapFrom(RT,0)); vwapL.applyOptions({visible:v}); }},
      avwap:{label:'Anchored VWAP',col:C.avwap,on:false, fn:function(v){ if(v){ avwapL.setData(vwapFrom(RT,anchorIdx())); pickAVWAP(); } avwapL.applyOptions({visible:v}); }},
      bb:{label:'Bollinger',col:C.bb,on:false, fn:function(v){ if(v){ var b=bollinger(RT,20,2); bbU.setData(b.up); bbM.setData(b.mid); bbL.setData(b.lo); } bbU.applyOptions({visible:v}); bbM.applyOptions({visible:v}); bbL.applyOptions({visible:v}); }},
      atr:{label:'ATR bands',col:C.atr,on:false, fn:function(v){ if(v){ var a=atrBands(RT,14,2); atrU.setData(a.up); atrLo.setData(a.lo); } atrU.applyOptions({visible:v}); atrLo.applyOptions({visible:v}); }},
      deliv:{label:'Delivery %',col:C.deliv,on:false, fn:function(v){ delivL.applyOptions({visible:v}); reflow(); }},
      flow:{label:'Traded \\u20b9',col:C.dval,on:false, fn:function(v){ tvalH.applyOptions({visible:v}); dvalH.applyOptions({visible:v}); reflow(); }}
    };
    function regChip(key){ var o=reg[key]; var c=E('span',chipCss(o.on,o.col),dot(o.col)+o.label);
      c.onclick=function(){ o.on=!o.on; o.fn(o.on); c.style.cssText=chipCss(o.on,o.col); c.innerHTML=dot(o.col)+o.label; if(typeof refreshLegend==='function')refreshLegend(); };
      o.chip=c; return c; }

    // =========================================================================
    //  THE FOUR-FAMILY RAIL — one shared, opt-in control bar (Ramana's taxonomy)
    // =========================================================================
    function famLabel(t){ return E('span','font-size:10px;letter-spacing:.4px;text-transform:uppercase;color:'+C.dim+';margin-right:4px',t); }
    function family(lbl, host){ var col=E('div','display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:3px 0');
      col.appendChild(famLabel(lbl)); if(host)col.appendChild(host); return col; }
    function sep(){ return E('span','width:1px;align-self:stretch;background:'+C.border+';margin:0 4px'); }

    var rail=E('div','background:#0e1320;border:1px solid '+C.border+';border-radius:10px;padding:6px 10px;margin:0 0 8px;display:flex;flex-direction:column;gap:2px;font-family:-apple-system,Segoe UI,Roboto,sans-serif');

    // -- family 1: chart type (dropdown — types are NOT indicators) ----------
    var typeSel=E('select','background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);border-radius:6px;font-size:12px;padding:4px 8px');
    [['candle','Candles'],['hollow','Hollow candles'],['heikin','Heikin Ashi'],['line','Line'],['area','Area'],
     ['renko','Renko'],['kagi','Kagi'],['pnf','Point & Figure (soon)',true]].forEach(function(o){
      var op=document.createElement('option'); op.value=o[0]; op.textContent=o[1]; if(o[2])op.disabled=true; typeSel.appendChild(op); });
    typeSel.onchange=function(){ if(typeSel.value==='pnf'){ typeSel.value=ctype; return; } setType(typeSel.value); };

    // -- family 2: strategies — pre-create #stratBar so CPR/MEP chips land here -
    var stratBar=E('div','display:flex;align-items:center;flex-wrap:wrap;gap:6px'); stratBar.id='stratBar';
    var wfChip=E('span',chipCss(false,C.wolfe),dot(C.wolfe)+'Wolfe');
    wfChip.onclick=function(){ var cb=document.getElementById('wfChk'); if(!cb)return; cb.checked=!cb.checked;
      cb.dispatchEvent(new Event('change')); wfChip._on=cb.checked; wfChip.style.cssText=chipCss(cb.checked,C.wolfe); wfChip.innerHTML=dot(C.wolfe)+'Wolfe'; };
    stratBar.appendChild(regChip('dvpt'));      // DVPT first; CPR/MEP append after
    stratBar.appendChild(wfChip);
    stratBar.appendChild(regChip('rs'));
    var harmChip=regChip('harm');
    harmChip.title='Harmonic XABCD — read by side (OOS backtest): BULL = a modest, fit-graded selection edge over drift; BEAR \\u2248 short-drift, tail/regime only. Descriptive, not a buy/sell signal.';
    stratBar.appendChild(harmChip);

    // -- family 3: indicators — #cprBar anchors MA's #maBar into this family ---
    var indBar=E('div','display:flex;align-items:center;flex-wrap:wrap;gap:6px');
    var maAnchor=E('span','display:inline-block;width:0'); maAnchor.id='cprBar'; indBar.appendChild(maAnchor);
    indBar.appendChild(regChip('vwap')); indBar.appendChild(regChip('avwap'));
    var bbChip=regChip('bb'); bbChip.title='Bollinger Bands (20, 2\\u03c3) \\u2014 descriptive volatility envelope around a 20-period mean, not a buy/sell signal.'; indBar.appendChild(bbChip);
    var atrChip=regChip('atr'); atrChip.title='ATR bands (close \\u00b1 2\\u00d7ATR-14) \\u2014 descriptive volatility envelope, not a buy/sell signal.'; indBar.appendChild(atrChip);
    indBar.appendChild(regChip('deliv')); indBar.appendChild(regChip('flow'));

    // -- family: LOWER PANE — volume / RSI / MACD chips drive the synced lower chart
    var lpBar=E('div','display:flex;align-items:center;flex-wrap:wrap;gap:6px');
    function lpChip(key){ var o=lpReg[key]; var c=E('span',chipCss(o.on,o.col),dot(o.col)+o.label);
      c.onclick=function(){ var nv=!o.on; lpToggle(key,nv); c.style.cssText=chipCss(o.on,o.col); c.innerHTML=dot(o.col)+o.label; refreshLegend(); };
      o.chip=c; return c; }
    var volChip=lpChip('vol'); volChip.title='Volume (\\u2248 traded value / close) in a synced lower pane. Descriptive.';
    var rsiChip=lpChip('rsi'); rsiChip.title='RSI(14) in a synced lower pane, with 30/70 guides. Descriptive momentum oscillator, not a buy/sell signal.';
    var macdChip=lpChip('macd'); macdChip.title='MACD(12,26,9): line, signal, histogram in a synced lower pane. Descriptive, not a buy/sell signal.';
    lpBar.appendChild(volChip); lpBar.appendChild(rsiChip); lpBar.appendChild(macdChip);

    // -- family: COMPARE — rebased multi-symbol overlay (focus vs index/peer) --
    var cmpBar=E('div','display:flex;align-items:center;flex-wrap:wrap;gap:4px');

    // -- family 4: drawings (built below; engine attaches to drawBar) ---------
    var drawBar=E('div','display:flex;align-items:center;flex-wrap:wrap;gap:4px');

    var row1=E('div','display:flex;align-items:flex-start;flex-wrap:wrap;gap:8px');
    row1.appendChild(family('Chart type',typeSel)); row1.appendChild(sep());
    row1.appendChild(family('Strategies',stratBar)); row1.appendChild(sep());
    row1.appendChild(family('Indicators',indBar)); row1.appendChild(sep());
    row1.appendChild(family('Lower pane',lpBar)); row1.appendChild(sep());
    row1.appendChild(family('Compare',cmpBar)); row1.appendChild(sep());
    row1.appendChild(family('Drawings',drawBar));
    rail.appendChild(row1);

    // -- compact second line: interval · range · Wolfe status (re-homed) ------
    var row2=E('div','display:flex;align-items:center;flex-wrap:wrap;gap:8px;border-top:1px solid var(--bg-2);margin-top:2px;padding-top:4px');
    var ivBar=document.getElementById('ivBar');
    var rangeBar=document.querySelector('.rangebar');
    var ctBar=document.getElementById('ctBar');
    var wfLbl=document.getElementById('wfLbl');
    var wfRow=document.getElementById('wfChk'); wfRow=wfRow?wfRow.closest('.fbar'):null;
    if(ivBar){ row2.appendChild(family('Interval',ivBar)); }
    if(rangeBar){ row2.appendChild(family('Range',rangeBar)); }
    if(wfLbl){ var st=E('span','font-size:12px;color:'+C.txt); st.appendChild(wfLbl); row2.appendChild(st); }
    rail.appendChild(row2);

    // -- legend / "Read" strip — names what each ACTIVE overlay means so the chart
    //    reads as a workstation, not a wall of lines. Descriptive grammar; updates
    //    on every toggle. Harmonic carries its read-by-side backtest caveat here.
    var legend=E('div','display:none;flex-wrap:wrap;gap:4px 12px;border-top:1px solid var(--bg-2);margin-top:2px;padding-top:4px;font-size:11px;color:'+C.txt);
    rail.appendChild(legend);
    var LEGEND={
      dvpt:[C.dvpt,'DVPT','rupee value traded; amber = institutional (1m+) day'],
      rs:[C.rs,'RS','relative strength vs the broad market (docked lane)'],
      harm:[C.harm,'Harmonic','XABCD reversal geometry — read by side: BULL = modest fit-graded edge, BEAR = tail/regime-only'],
      vwap:[C.vwap,'VWAP','session volume-weighted average price'],
      avwap:[C.avwap,'Anchored VWAP','VWAP from a chosen anchor bar'],
      bb:[C.bb,'Bollinger','20-period mean \\u00b1 2\\u03c3 volatility envelope (descriptive)'],
      atr:[C.atr,'ATR bands','close \\u00b1 2\\u00d7ATR(14) volatility envelope (descriptive)'],
      deliv:[C.deliv,'Delivery %','share of traded volume taken to delivery'],
      flow:[C.dval,'Traded / Delivery \\u20b9','rupee traded vs delivered value']
    };
    var LEGEND_LP={
      vol:[C.vol,'Volume','traded volume (\\u2248 value/close) \\u2014 lower pane'],
      rsi:[C.rsi,'RSI 14','momentum oscillator, 30/70 guides \\u2014 lower pane (descriptive)'],
      macd:[C.macd,'MACD','12/26/9 line, signal, histogram \\u2014 lower pane (descriptive)']
    };
    function legRow(col,name,desc){ return '<span style="display:inline-flex;align-items:center;gap:5px">'
        +'<span style="width:7px;height:7px;border-radius:50%;background:'+col+'"></span>'
        +'<b style="color:'+C.txtHi+'">'+name+'</b><span style="color:'+C.dim+'">'+desc+'</span></span>'; }
    function refreshLegend(){ var rows=[];
      for(var k in LEGEND){ if(reg[k]&&reg[k].on){ var L=LEGEND[k]; rows.push(legRow(L[0],L[1],L[2])); } }
      for(var k2 in LEGEND_LP){ if(lpReg[k2]&&lpReg[k2].on){ var L2=LEGEND_LP[k2]; rows.push(legRow(L2[0],L2[1],L2[2])); } }
      if(cmpReg&&cmpReg.items.length){ rows.push(legRow(C.cmp,'Compare','rebased to 100 at window start \\u2014 '+cmpReg.items.map(function(c){return c.sym;}).join(', ')+' (descriptive)')); }
      legend.innerHTML=rows.join(''); legend.style.display=rows.length?'flex':'none'; }

    // mount rail just above the chart box; hide the now-folded old rows + panes
    var wrap=host.closest('.chartwrap');
    if(wrap&&wrap.parentNode) wrap.parentNode.insertBefore(rail, wrap); else host.parentNode.insertBefore(rail, host);
    // mount the lower pane just BELOW the whole .chartwrap (NOT inside it — .chartwrap
    // constrains its children's height to the price chart, which clipped the pane to 0).
    // Collapsed (height:0) until a Volume/RSI/MACD chip turns on.
    var cwrap=host.closest('.chartwrap');
    if(cwrap&&cwrap.parentNode) cwrap.parentNode.insertBefore(lpHost, cwrap.nextSibling);
    else if(host.parentNode) host.parentNode.insertBefore(lpHost, host.nextSibling);
    if(ctBar) ctBar.style.display='none';
    if(wfRow) wfRow.style.display='none';
    ['dvptChart','delivChart','tvChart'].forEach(function(id){ var el=document.getElementById(id); if(el){ var w=el.closest('.chartwrap'); if(w)w.style.display='none'; } });

    // re-bind interval + range (their old handlers lived in the killed block);
    // CPR's own [data-ptf] listener still fires additively → ladder follows.
    document.querySelectorAll('[data-ptf]').forEach(function(b){
      b.onclick=function(){ document.querySelectorAll('[data-ptf]').forEach(function(x){x.classList.toggle('on',x===b);}); setIv(b.dataset.ptf); setRange(curRange()); }; });
    document.querySelectorAll('.rangebar button').forEach(function(b){
      b.onclick=function(){ document.querySelectorAll('.rangebar button').forEach(function(x){x.classList.remove('on');}); b.classList.add('on'); setRange(parseInt(b.dataset.r)); }; });

    // hide MA's duplicate "Indicators" label once it injects (my family owns it)
    (function tidy(n){ var mb=document.getElementById('maBar'); if(mb){ if(mb.firstChild&&mb.firstChild.tagName==='SPAN')mb.firstChild.style.display='none';
        mb.style.margin='0'; return; } if(n>0)setTimeout(function(){tidy(n-1);},80); })(30);

    // =========================================================================
    //  DRAWING ENGINE — curated T1 (trendline/ray/rect/Fib/text/measure) +
    //  magnet (snap nearest OHLC, still overridable) + hide-all + persistence.
    // =========================================================================
    var draw=makeDraw(pc,candle,host,drawBar,function(){return RT;},function(){return FUT;});

    // boot
    setIv('d'); setType('candle'); setRange(0); showR(S0[S0.length-1]); reflow(); refreshLegend();
    // observe BOTH width and height (the old observer watched width only -> chart grew
    // wide but never tall); height now tracks the clamp + the fullscreen container.
    var ro=new ResizeObserver(function(){ var w=host.clientWidth,h=host.clientHeight; if(w&&h)pc.applyOptions({width:w,height:h});
      var lw=lpHost.clientWidth, lh=lpHost.clientHeight; if(lw&&lh)lp.applyOptions({width:lw,height:lh}); });
    ro.observe(host); ro.observe(lpHost);
    // fullscreen (the requested "enlarge") — pure CSS overlay, no route change; the
    // ResizeObserver above refits the chart to the full viewport and back.
    (function(){
      if(!document.getElementById('cfs-style')){ var st=E('style'); st.id='cfs-style';
        st.textContent='.cfs{position:fixed!important;inset:0!important;z-index:9999!important;height:100vh!important;max-width:none!important;margin:0!important;border-radius:0!important;background:'+C.bg+'}';
        document.head.appendChild(st); }
      var fb=E('div','position:absolute;top:8px;right:8px;z-index:12;cursor:pointer;width:26px;height:26px;display:flex;align-items:center;justify-content:center;border:1px solid '+C.border+';border-radius:6px;background:rgba(13,17,23,.72);color:'+C.txt+';font-size:13px','\\u2922');
      fb.title='Fullscreen (Shift+F)';
      function tog(){ host.classList.toggle('cfs'); fb.innerHTML=host.classList.contains('cfs')?'\\u2715':'\\u2922';
        // force an explicit refit next frame — the ResizeObserver can miss the
        // position:fixed transition, leaving the chart short of the fullscreen host.
        requestAnimationFrame(function(){ var w=host.clientWidth,h=host.clientHeight; if(w&&h)pc.applyOptions({width:w,height:h}); }); }
      fb.onclick=tog;
      document.addEventListener('keydown',function(e){ if((e.key==='F'||e.key==='f')&&e.shiftKey){ e.preventDefault(); tog(); } else if(e.key==='Escape'&&host.classList.contains('cfs')) tog(); });
      host.appendChild(fb);
    })();

    // -------- RS docked lane (Strategies) — fetch /dash/rs/overlay on toggle --
    var rsL=null, rsLoaded=false;
    function rsToggle(v){
      if(!v){ if(rsL)rsL.applyOptions({visible:false}); reflow(); return; }
      if(rsLoaded){ if(rsL)rsL.applyOptions({visible:true}); reflow(); return; }
      rsLoaded=true; reflow(); var sym=new URLSearchParams(location.search).get('sym')||'';
      fetch('/dash/rs/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
        if(!d||!d.series||!d.series.length){ reg.rs.on=false; if(reg.rs.chip){reg.rs.chip.style.cssText=chipCss(false,C.rs);reg.rs.chip.innerHTML=dot(C.rs)+'RS';} reflow(); refreshLegend(); return; }
        rsL=pc.addLineSeries({priceScaleId:'rs',color:C.rs,lineWidth:1.5,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,title:'RS vs '+(d.benchmark||'Nifty 500')});
        pc.priceScale('rs').applyOptions({scaleMargins:{top:0.74,bottom:0.04}});  // docked in the bottom band, not over the candles
        rsL.setData(d.series.map(function(p){return {time:p.t,value:p.v};}));
      }).catch(function(){ rsLoaded=false; });
    }

    // -------- Harmonic XABCD overlay (Strategies) — fetch /dash/harmonic/overlay -----
    // Draws each detected pattern's X-A-B-C-D polyline + point markers (+ a projected PRZ
    // band for FORMING) on the price pane (window.__wfpc). DESCRIPTIVE — read by side per
    // the backtest (docs/harmonic-pattern-design.md: bull = edge, bear = tail). Point
    // dates are re-snapped onto the current bars so it survives the D/W/M/Q resample.
    var harmData=null, harmSeries=[], harmIdx=0, harmBox=null, harmLbl=null;
    function snapT(t){ if(iv==='d')return t; var best=t,bd=1e18;
      for(var i=0;i<RT.length;i++){ var dd=Math.abs(new Date(RT[i].time)-new Date(t)); if(dd<bd){bd=dd;best=RT[i].time;} } return best; }
    function harmClear(){ harmSeries.forEach(function(s){try{pc.removeSeries(s);}catch(e){}}); harmSeries=[]; }
    // Stepper (\\u25c0 Gartley \\u00b7 BULL \\u00b7 forming (1/3) \\u25b6) — like the Wolfe wave w-index:
    // step through the detected patterns ONE at a time (all-at-once buried the chart) and NAME
    // which harmonic it is. Built once, appended to the rail, shown only while Harmonic is on.
    function harmEnsureBox(){ if(harmBox) return;
      harmBox=E('div','display:none;align-items:center;gap:8px;margin-top:3px;font-size:12px;color:'+C.txt);
      var pv=E('span','cursor:pointer;border:1px solid var(--line-2);border-radius:6px;padding:0 8px;user-select:none','\\u25c0');
      var nx=E('span','cursor:pointer;border:1px solid var(--line-2);border-radius:6px;padding:0 8px;user-select:none','\\u25b6');
      pv.title='Previous harmonic pattern'; nx.title='Next harmonic pattern';
      harmLbl=E('span','','');
      pv.onclick=function(){ harmStep(-1); }; nx.onclick=function(){ harmStep(1); };
      harmBox.appendChild(pv); harmBox.appendChild(harmLbl); harmBox.appendChild(nx);
      rail.appendChild(harmBox); }
    function harmStep(dlt){ if(!harmData||!harmData.length) return;
      harmIdx=(harmIdx+dlt+harmData.length)%harmData.length; harmDrawOne(); }
    function harmDrawOne(){
      harmClear(); if(!harmData||!harmData.length) return;
      var p=harmData[harmIdx]; if(!p) return;
      var bull=p.dir==='BULL', col=bull?C.up:C.down, dashed=p.state==='FORMING';
      var seen={},clean=[];
      p.points.forEach(function(q){ var t=snapT(q.t); if(!seen[t]){ seen[t]=1; clean.push({time:t,value:q.price}); } });
      if(clean.length>=2){
        var ls=pc.addLineSeries({color:col,lineWidth:2,lineStyle:dashed?2:0,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,autoscaleInfoProvider:function(){return null;}});
        ls.setData(clean);
        ls.setMarkers(p.points.map(function(q,i){ var hi=bull?(i%2===1):(i%2===0);
          return {time:snapT(q.t),position:hi?'aboveBar':'belowBar',color:col,shape:'circle',text:q.label}; }));
        harmSeries.push(ls);
        if(p.state==='FORMING'&&p.prz){ var ct=snapT(p.points[p.points.length-1].t),rt=RT[RT.length-1].time;
          [p.prz.lo,p.prz.hi].forEach(function(lv){ if(lv==null)return;
            var z=pc.addLineSeries({color:C.harm,lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,autoscaleInfoProvider:function(){return null;}});
            z.setData([{time:ct,value:lv},{time:rt,value:lv}]); harmSeries.push(z); }); }
      }
      if(harmLbl){ var nm=p.name||'Harmonic', stt=(p.state==='FORMING')?'forming':'confirmed';
        harmLbl.innerHTML='<b style="color:'+col+'">'+nm+'</b> \\u00b7 '+(bull?'BULL':'BEAR')+' \\u00b7 '+stt
          +' <span style="opacity:.65">('+(harmIdx+1)+'/'+harmData.length+')</span>'; }
    }
    // harmonic timeframe (d/w/m) — detected on resampled bars server-side. Defaults to
    // 'd'; switching the price interval to W/M re-fetches W/M harmonics (the multi-TF
    // detection hand-off). The overlay returns the patterns for whatever tf is asked.
    var harmTf='d';
    function harmFetch(){ var sym=new URLSearchParams(location.search).get('sym')||'';
      var tf=(iv==='w'||iv==='m')?iv:'d';
      return fetch('/dash/harmonic/overlay?sym='+encodeURIComponent(sym)+'&tf='+tf).then(function(r){return r.json();}); }
    function harmToggle(v){
      if(!v){ harmClear(); if(harmBox) harmBox.style.display='none'; return; }
      harmEnsureBox();
      if(harmData && harmTf===((iv==='w'||iv==='m')?iv:'d')){ if(harmIdx>=harmData.length) harmIdx=0; harmBox.style.display='flex'; harmDrawOne(); return; }
      harmFetch().then(function(d){
        harmTf=(iv==='w'||iv==='m')?iv:'d';
        if(!d||!d.patterns||!d.patterns.length){ reg.harm.on=false; harmData=null; harmClear(); if(harmBox) harmBox.style.display='none';
          if(reg.harm.chip){ reg.harm.chip.style.cssText=chipCss(false,C.harm); reg.harm.chip.innerHTML=dot(C.harm)+'Harmonic'; }
          refreshLegend(); return; }
        harmData=d.patterns; harmIdx=0; harmBox.style.display='flex'; harmDrawOne();
      }).catch(function(){});
    }

    // anchored-VWAP: arm a one-shot click to choose the anchor bar
    function pickAVWAP(){ var once=function(p){ if(p&&p.time){ avwapAnchor=tkey(p.time); avwapL.setData(vwapFrom(RT,anchorIdx())); } pc.unsubscribeClick(once); };
      pc.subscribeClick(once); }

    // =======================================================================
    //  COMPARE — rebased multi-symbol overlay (focus vs index/peer), base 100
    //  at the window start, on a dedicated overlay price scale so the candles
    //  stay untouched. DESCRIPTIVE relative-performance lens, not a signal.
    // =======================================================================
    var cmpScaleInit=false, focusCmpLine=null;
    // Compare is a RECENT relative-performance lens — cap to ~2y (504 trading days) so it
    // is both analytically meaningful (rebased to 100 at the window start) and light
    // (rendering 5400-pt lines for every compared name froze the renderer). All legs share
    // the same window so they're directly comparable.
    var CMP_WINDOW=504;
    function tailWin(rows){ return (rows&&rows.length>CMP_WINDOW)?rows.slice(rows.length-CMP_WINDOW):rows; }
    function rebaseToWindow(rows){ // rows=[{t|time, c}] ascending -> [{time,value}] base 100 at first
      rows=tailWin(rows); if(!rows||rows.length<2) return [];
      var base=null; for(var i=0;i<rows.length;i++){ if(rows[i].c){ base=rows[i].c; break; } }
      if(!base) return [];
      return rows.map(function(r){ var tm=(r.time!=null?r.time:r.t); return {time:tm, value:r.c?(r.c/base*100):null}; })
                 .filter(function(p){return p.value!=null&&p.time!=null;});
    }
    function ensureCmpScale(){ if(cmpScaleInit) return;
      pc.priceScale('cmp').applyOptions({scaleMargins:{top:0.06,bottom:0.28},visible:true}); cmpScaleInit=true; }
    function focusRows(){ return S0.map(function(d){return {time:d.time,c:d.close};}); }   // focus stock raw close
    function drawFocusCmp(on){
      if(on){ ensureCmpScale(); if(!focusCmpLine){ focusCmpLine=pc.addLineSeries({priceScaleId:'cmp',color:C.txtHi,lineWidth:1.5,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,title:(new URLSearchParams(location.search).get('sym')||'this')}); }
        focusCmpLine.setData(rebaseToWindow(focusRows())); focusCmpLine.applyOptions({visible:true}); }
      else if(focusCmpLine){ focusCmpLine.applyOptions({visible:false}); } }
    var cmpMsgEl=null;
    function cmpMsg(t){ if(!cmpBar)return; if(!cmpMsgEl){ cmpMsgEl=E('span','font-size:11px;color:#d29922;margin-left:4px'); }
      cmpMsgEl.textContent=t||''; if(t&&cmpMsgEl.parentNode!==cmpBar)cmpBar.appendChild(cmpMsgEl);
      if(t)setTimeout(function(){ if(cmpMsgEl)cmpMsgEl.textContent=''; },3500); }
    function addCompare(name){ name=(name||'').trim(); if(!name) return;
      if(cmpReg.items.length>=4){ cmpMsg('Up to 4 symbols'); return; }
      if(cmpReg.items.some(function(c){return c.sym.toUpperCase()===name.toUpperCase();})) return;
      cmpMsg('loading '+name+'\\u2026');
      fetch('/dash/compare/series?sym='+encodeURIComponent(name)).then(function(r){return r.json();}).then(function(d){
        if(!d||!d.series||d.series.length<2){ cmpMsg('No series for "'+name+'"'); return; }
        cmpMsg('');
        ensureCmpScale(); drawFocusCmp(true);
        var col=CMP_COLORS[cmpReg.items.length%CMP_COLORS.length];
        var ln=pc.addLineSeries({priceScaleId:'cmp',color:col,lineWidth:1.5,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,title:d.sym});
        ln.setData(rebaseToWindow(d.series));
        cmpReg.items.push({sym:d.sym,line:ln,col:col});
        renderCmpBar(); refreshLegend(); reflowCmp();
      }).catch(function(err){ try{console.error('compare add failed:',err&&err.message,err);}catch(e){} cmpMsg('Could not load "'+name+'"'); });
    }
    function removeCompare(i){ var it=cmpReg.items[i]; if(!it) return; try{ pc.removeSeries(it.line); }catch(e){}
      cmpReg.items.splice(i,1);
      if(!cmpReg.items.length){ drawFocusCmp(false); if(cmpScaleInit){ pc.priceScale('cmp').applyOptions({visible:false}); } }
      renderCmpBar(); refreshLegend(); reflowCmp(); }
    function reflowCmp(){ /* keep candles readable: when compare is on, the cmp scale shares the right gutter */ }
    // ---- the Compare family UI (input + add + per-symbol chips) -------------
    function renderCmpBar(){ if(!cmpBar) return; cmpBar.innerHTML='';
      var inp=document.createElement('input'); inp.type='text'; inp.placeholder='+ symbol / index';
      inp.title='Add a symbol or index to compare (rebased to 100 at the window start)';
      inp.style.cssText='background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);border-radius:6px;font-size:12px;padding:3px 7px;width:120px';
      inp.onkeydown=function(e){ if(e.key==='Enter'){ addCompare(inp.value); inp.value=''; } };
      var addb=E('span','cursor:pointer;font-size:12px;color:var(--ink-2);border:1px solid var(--line-2);border-radius:6px;padding:3px 8px','add');
      addb.onclick=function(){ addCompare(inp.value); inp.value=''; };
      cmpBar.appendChild(inp); cmpBar.appendChild(addb);
      cmpReg.items.forEach(function(c,i){ var ch=E('span',chipCss(true,c.col),dot(c.col)+c.sym+' \\u00d7');
        ch.title='Remove '+c.sym; ch.style.cursor='pointer'; ch.onclick=function(){ removeCompare(i); }; cmpBar.appendChild(ch); }); }
    renderCmpBar();   // initial: just the input + add
    // expose a hook so the UI builder (below, after rail mount) can attach
    window.__cmpAdd=addCompare; window.__cmpRemove=removeCompare;
  }

  // ===========================================================================
  //  makeDraw — the drawing primitive + tool palette (its own closure)
  // ===========================================================================
  function makeDraw(pc, series, host, bar, getRows, getFut){
    var sym=new URLSearchParams(location.search).get('sym')||'_';
    var KEY='hdraw:'+sym;
    // localStorage = instant + offline cache; the SERVER store (/dash/drawings) is the
    // source of truth when reachable, so drawings follow you across device + browser.
    var items=[]; try{ items=JSON.parse(localStorage.getItem(KEY)||'[]'); }catch(e){ items=[]; }
    var tool=null, magnet=true, hidden=false, draft=null, sel=null, dragging=null, conflux=true;
    var FIB=[0,0.236,0.382,0.5,0.618,0.786,1];
    // Fib EXTENSION defaults — project targets beyond the move (a→b): 0/0.618/1 mark the
    // measured move; 1.272/1.618/2/2.618/4.236 are the default targets. A drawing can
    // carry its own level set (d.lv) chosen in the double-click editor from EXT_ALL.
    var FIBX=[0,0.618,1,1.272,1.618,2,2.618,4.236];
    var EXT_ALL=[0,0.618,1,1.13,1.272,1.382,1.618,2,2.382,2.618,3,3.618,4.236,4.618];
    // what each level IS — shown beside the checkbox in the editor (Ramana 2026-07-10)
    var FIBN={
      0:'anchor - start of the measured move', 0.236:'shallow retrace', 0.382:'standard retrace',
      0.5:'half-back of the move', 0.618:'golden retrace', 0.786:'deep retrace',
      1:'full move - the prior extreme',
      1.13:'bull-trap / false-breakout zone',
      1.272:'first major target beyond the prior extreme',
      1.382:'intermediate shelf before the golden level',
      1.618:'golden extension - the primary institutional target',
      2:'measured-move double',
      2.382:'minor target that front-runs 2.618',
      2.618:'major target for strongly trending stocks',
      3:'triple the original move',
      3.618:'extreme extension - strong macro runs',
      4.236:'ultimate extension - highly overextended zone',
      4.618:'Wolfe zone ratio (the detector G-component)'};
    function lvOf(d){ return d.lv||((d.t==='fibext')?FIBX:FIB); }

    // ---- server persistence (debounced) -------------------------------------
    var saveT=null, lastSent=null;
    function pushServer(){
      if(sym==='_') return;                       // no symbol → local-only
      var body=JSON.stringify(items);
      if(body===lastSent) return;                 // nothing changed since last push
      lastSent=body;
      try{ fetch('/dash/drawings?sym='+encodeURIComponent(sym),
        {method:'POST',headers:{'Content-Type':'application/json'},body:body,keepalive:true})
        .catch(function(){}); }catch(e){}
    }
    function save(){ try{ localStorage.setItem(KEY, JSON.stringify(items)); }catch(e){}
      if(saveT) clearTimeout(saveT); saveT=setTimeout(pushServer, 600); }   // coalesce rapid edits
    // flush a pending save when the tab is hidden / unloaded (don't lose the last edit)
    window.addEventListener('beforeunload', function(){ if(saveT){ clearTimeout(saveT); pushServer(); } });
    // on load, adopt the server copy if it has drawings (it wins over the local cache);
    // if the server is empty but we have a local cache, seed the server from it (migration).
    if(sym!=='_'){
      try{ fetch('/dash/drawings?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
        var srv=(d&&Array.isArray(d.items))?d.items:[];
        if(srv.length){ items=srv; try{ localStorage.setItem(KEY, JSON.stringify(items)); }catch(e){}
          lastSent=JSON.stringify(items); sel=null; redraw(); }
        else if(items.length){ pushServer(); }   // first-time migration: local -> server
      }).catch(function(){}); }catch(e){}
    }
    function bars(){ return getRows(); }
    function fut(){ return (getFut&&getFut())||[]; }
    function tstr(t){ if(t==null)return null; if(typeof t==='string')return t;
      if(typeof t==='object'&&t.year)return t.year+'-'+('0'+t.month).slice(-2)+'-'+('0'+t.day).slice(-2); return ''+t; }
    function nearestBarX(x){ var R=bars(),ts=pc.timeScale(),best=null,bd=1e9;
      for(var i=0;i<R.length;i++){ var cx=ts.timeToCoordinate(R[i].time); if(cx==null)continue; var dd=Math.abs(cx-x); if(dd<bd){bd=dd;best=R[i];} } return best; }
    function snap(x,y){
      // clicks PAST the last real bar resolve onto the whitespace (future) times, so a
      // trendline / EPA / fib anchor can be projected forward instead of snapping back.
      var R=bars(), ts=pc.timeScale();
      if(R.length){ var lx=ts.timeToCoordinate(R[R.length-1].time);
        if(lx!=null && x>lx+(ts.options().barSpacing||6)/2){
          var t=tstr(ts.coordinateToTime(x)); var FU=fut();
          if(t==null&&FU.length) t=FU[FU.length-1].time;   // beyond the whitespace end → clamp
          if(t!=null) return {time:t, price:series.coordinateToPrice(y)};
        } }
      var b=nearestBarX(x); if(!b) return {time:tstr(pc.timeScale().coordinateToTime(x)),price:series.coordinateToPrice(y)};
      var price=series.coordinateToPrice(y);
      if(magnet){ var cands=[b.open,b.high,b.low,b.close],bp=price,bd=1e9;
        for(var i=0;i<cands.length;i++){ var cy=series.priceToCoordinate(cands[i]); if(cy==null)continue; var dd=Math.abs(cy-y); if(dd<bd){bd=dd;bp=cands[i];} } price=bp; }
      return {time:b.time, price:price}; }
    function px(a){ var x=pc.timeScale().timeToCoordinate(a.time); if(x==null){ var R=bars(); var t=a.time;
        // snap off-axis anchor onto the nearest visible bar (resample-safe)
        var lo=0,hi=R.length-1,k=null; while(lo<=hi){var m=(lo+hi)>>1; if(R[m].time<=t){k=R[m].time;lo=m+1;}else hi=m-1;}
        if(k!=null)x=pc.timeScale().timeToCoordinate(k); }
      var y=series.priceToCoordinate(a.price); return (x==null||y==null)?null:{x:x,y:y}; }
    function extendPts(pa,pb,mode,W){ // mode: 0 segment · 1 ray beyond b · 2 both ways
      if(!mode) return [pa,pb];
      var dx=pb.x-pa.x, dy=pb.y-pa.y, a={x:pa.x,y:pa.y}, b={x:pb.x,y:pb.y};
      if(dx===0&&dy===0) return [pa,pb];
      function push(pt,sgn){ if(dx===0){ pt.y=(sgn*dy>0)?1e5:-1e5; return; }
        var X=(sgn*dx>0)?W+60:-60; pt.y=pa.y+dy*(X-pa.x)/dx; pt.x=X; }
      push(b,1); if(mode===2) push(a,-1); return [a,b]; }
    // narrow confluences ACROSS Fib drawings: extension levels (>1.0 ONLY — retrace
    // levels made false zones) from two DIFFERENT fib drawings agreeing within 2% —
    // BOTH rules mirror wolfe.fib_zones (tol_frac=0.02) so a manual two-leg drawing
    // finds the same zones the auto Wolfe calls. Shaded band, tightest-first, top 6.
    function confluxBands(){
      var sets=[];
      for(var i=0;i<items.length;i++){ var d=items[i]; if(d.t!=='fib'&&d.t!=='fibext') continue;
        var LV=lvOf(d), pr=[];
        for(var j=0;j<LV.length;j++){ if(LV[j]<=1) continue;
          pr.push({r:LV[j], v:d.a.price+(d.b.price-d.a.price)*LV[j]}); }
        if(pr.length) sets.push(pr); }
      if(sets.length<2) return [];
      var out=[];
      for(var a2=0;a2<sets.length;a2++) for(var b2=a2+1;b2<sets.length;b2++)
        for(var i2=0;i2<sets[a2].length;i2++) for(var j2=0;j2<sets[b2].length;j2++){
          var v1=sets[a2][i2].v, v2=sets[b2][j2].v, mid=(v1+v2)/2;
          if(mid&&Math.abs(v1-v2)<=0.02*Math.abs(mid))
            out.push({lo:Math.min(v1,v2),hi:Math.max(v1,v2),mid:mid,
                      lab:sets[a2][i2].r+'\\u2229'+sets[b2][j2].r}); }
      out.sort(function(q1,q2){return (q1.hi-q1.lo)-(q2.hi-q2.lo);});
      var ded=[];
      for(var k2=0;k2<out.length;k2++){ var z=out[k2], dup=false;
        for(var k3=0;k3<ded.length;k3++){ if(Math.abs(z.mid-ded[k3].mid)<=0.02*Math.abs(z.mid)){ dup=true; break; } }
        if(!dup) ded.push(z); }
      return ded.slice(0,6); }

    // the canvas primitive (top z) — paints every drawing + the live draft
    var reqUpd=null;
    var view={ zOrder:function(){return 'top';}, renderer:function(){ return { draw:function(tg){
      if(hidden) return;
      tg.useBitmapCoordinateSpace(function(sc){
        var x=sc.context,h=sc.horizontalPixelRatio,v=sc.verticalPixelRatio,W=sc.mediaSize.width;
        function L(a,b,col,w,dash){ var pa=px(a),pb=px(b); if(!pa||!pb)return; x.strokeStyle=col;x.lineWidth=(w||1)*v;
          x.setLineDash(dash?[4*h,3*h]:[]); x.beginPath(); x.moveTo(pa.x*h,pa.y*v); x.lineTo(pb.x*h,pb.y*v); x.stroke(); x.setLineDash([]); }
        function hline(a,col){ var pa=px(a); if(!pa)return; x.strokeStyle=col;x.lineWidth=1*v;x.setLineDash([]); x.beginPath(); x.moveTo(0,pa.y*v); x.lineTo(W*h,pa.y*v); x.stroke(); }
        function txt(s,X,Y,col){ x.fillStyle=col; x.font=(11*v)+'px -apple-system,Segoe UI,sans-serif'; x.fillText(s,X,Y); }
        function one(d,isSel){ var col=isSel?'#e6edf3':(d.col||'#58a6ff');
          if(d.t==='hline'){ hline(d.a,col); var pa=px(d.a); if(pa)txt(n2(d.a.price),6*h,(pa.y-4)*v,col); return; }
          if(d.t==='text'){ var pa=px(d.a); if(pa){ txt(d.text||'text',(pa.x+4)*h,pa.y*v,col); } return; }
          if(d.t==='trend'){ var ta=px(d.a),tb=px(d.b); if(!ta||!tb)return;
            var ee=extendPts(ta,tb,d.x|0,W);
            x.strokeStyle=col; x.lineWidth=(isSel?Math.max(2,(d.w||1.4)):(d.w||1.4))*v; x.setLineDash([]);
            x.beginPath(); x.moveTo(ee[0].x*h,ee[0].y*v); x.lineTo(ee[1].x*h,ee[1].y*v); x.stroke(); return; }
          if(d.t==='measure'){ L(d.a,d.b,col,1.4,true); var pb=px(d.b); if(pb){ var dp=d.b.price-d.a.price,pctv=d.a.price?dp/d.a.price*100:0;
              var nb=barsBetween(d.a.time,d.b.time), days=calDays(d.a.time,d.b.time);
              var w=(d.col||col)*1; var lw=(isSel?2:1.4);
              txt((dp>=0?'+':'')+n2(dp)+' ('+(pctv>=0?'+':'')+pctv.toFixed(1)+'%)',(pb.x+6)*h,(pb.y-6)*v,col);
              txt(nb+' bars \\u00b7 '+days+'d',(pb.x+6)*h,(pb.y+9)*v,hexA(col==='#e6edf3'?'#39c5cf':col,0.95)); } return; }
          if(d.t==='rect'){ var pa=px(d.a),pb=px(d.b); if(!pa||!pb)return; var X=Math.min(pa.x,pb.x)*h,Y=Math.min(pa.y,pb.y)*v,Wd=Math.abs(pb.x-pa.x)*h,Hd=Math.abs(pb.y-pa.y)*v;
            x.fillStyle=hexA(col==='#e6edf3'?'#58a6ff':col,0.10); x.fillRect(X,Y,Wd,Hd); x.strokeStyle=col;x.lineWidth=(isSel?2:1)*v;x.setLineDash([]);x.strokeRect(X,Y,Wd,Hd); return; }
          if(d.t==='fib'||d.t==='fibext'){ var pa=px(d.a),pb=px(d.b); if(!pa||!pb)return; var x0=Math.min(pa.x,pb.x),x1=Math.max(pa.x,pb.x);
            var LV=lvOf(d), fcol=(d.t==='fibext')?'#a371f7':'#d29922';
            for(var i=0;i<LV.length;i++){ var pr=d.a.price+(d.b.price-d.a.price)*LV[i]; var py=series.priceToCoordinate(pr); if(py==null)continue;
              x.strokeStyle=isSel?'#e6edf3':hexA(fcol,0.8);x.lineWidth=1*v;x.setLineDash(LV[i]>1?[3*h,2*h]:[]); x.beginPath();x.moveTo(x0*h,py*v);x.lineTo(x1*h,py*v);x.stroke(); x.setLineDash([]);
              txt(LV[i].toFixed(3)+'  '+n2(pr),(x1+4)*h,py*v,hexA(fcol,0.95)); } return; }
        }
        // bars/time helpers (closure over the current resampled rows)
        function barsBetween(t0,t1){ var R=bars(),i0=-1,i1=-1; for(var i=0;i<R.length;i++){ if(i0<0&&R[i].time>=t0)i0=i; if(R[i].time<=t1)i1=i; } if(i0<0||i1<0)return 0; return Math.abs(i1-i0); }
        function calDays(t0,t1){ var a=new Date(t0),b=new Date(t1); return Math.round(Math.abs(b-a)/86400000); }
        if(conflux){ var CB=confluxBands();
          for(var ci=0;ci<CB.length;ci++){ var zz=CB[ci];
            var cy1=series.priceToCoordinate(zz.hi), cy2=series.priceToCoordinate(zz.lo);
            if(cy1==null||cy2==null) continue;
            var yTop=Math.min(cy1,cy2), bh=Math.max(2,Math.abs(cy2-cy1));
            x.fillStyle='rgba(227,179,65,0.12)'; x.fillRect(0,yTop*v,W*h,bh*v);
            txt('conflux '+zz.lab+'  '+n2(zz.mid),6*h,(yTop-4)*v,'rgba(227,179,65,0.95)');
          } }
        for(var i=0;i<items.length;i++) one(items[i], items[i]===sel);
        if(draft) one(draft,false);
        // anchor handles on the selected drawing
        if(sel){ [sel.a,sel.b].forEach(function(a){ if(!a)return; var p=px(a); if(!p)return;
          x.fillStyle='#e6edf3'; x.beginPath(); x.arc(p.x*h,p.y*v,4*v,0,6.283); x.fill(); }); }
      });
    }};}};
    var prim={ attached:function(p){ reqUpd=p.requestUpdate; }, detached:function(){reqUpd=null;}, updateAllViews:function(){}, paneViews:function(){return [view];} };
    series.attachPrimitive(prim);
    function redraw(){ if(reqUpd)reqUpd(); }

    // --- a transparent capture layer over the chart (only "on" while drawing/editing)
    var cap=E('div','position:absolute;inset:0;cursor:crosshair;pointer-events:none;z-index:4'); host.appendChild(cap);
    function rel(e){ var r=host.getBoundingClientRect(); return {x:e.clientX-r.left, y:e.clientY-r.top}; }
    function arity(t){ return (t==='hline'||t==='text')?1:2; }
    function hitAnchor(x,y){ for(var i=0;i<items.length;i++){ var d=items[i]; var keys=['a','b'];
        for(var k=0;k<keys.length;k++){ var a=d[keys[k]]; if(!a)continue; var p=px(a); if(!p)continue;
          if(Math.abs(p.x-x)<8&&Math.abs(p.y-y)<8) return {d:d,key:keys[k]}; } } return null; }
    function hitBody(x,y){ var W=host.clientWidth||600;
      for(var i=items.length-1;i>=0;i--){ var d=items[i]; var pa=px(d.a); if(!pa)continue;
        if(d.t==='hline'){ if(Math.abs(pa.y-y)<6) return d; continue; }
        if(d.t==='text'){ if(Math.abs(pa.x-x)<40&&Math.abs(pa.y-y)<12) return d; continue; }
        var pb=d.b?px(d.b):null; if(!pb)continue;
        if(d.t==='rect'){ if(x>=Math.min(pa.x,pb.x)-4&&x<=Math.max(pa.x,pb.x)+4&&y>=Math.min(pa.y,pb.y)-4&&y<=Math.max(pa.y,pb.y)+4) return d; continue; }
        if(d.t==='fib'||d.t==='fibext'){
          // any of the drawing's LEVEL lines is a hit target (a 4.236 can sit far
          // outside the a-b anchor box), plus the anchor box itself.
          if(x>=Math.min(pa.x,pb.x)-4&&x<=Math.max(pa.x,pb.x)+64){
            var LV=lvOf(d), hitLv=false;
            for(var j=0;j<LV.length;j++){ var lp=d.a.price+(d.b.price-d.a.price)*LV[j];
              var yy=series.priceToCoordinate(lp); if(yy!=null&&Math.abs(yy-y)<5){ hitLv=true; break; } }
            if(hitLv) return d;
            if(y>=Math.min(pa.y,pb.y)-4&&y<=Math.max(pa.y,pb.y)+4) return d;
          }
          continue; }
        // segment distance for trend/measure (trend honours its extend mode)
        var ep=(d.t==='trend')?extendPts(pa,pb,d.x|0,W):[pa,pb];
        var dx=ep[1].x-ep[0].x,dy=ep[1].y-ep[0].y,L2=dx*dx+dy*dy; var tt=L2?((x-ep[0].x)*dx+(y-ep[0].y)*dy)/L2:0; tt=Math.max(0,Math.min(1,tt));
        var qx=ep[0].x+tt*dx,qy=ep[0].y+tt*dy; if(Math.hypot(x-qx,y-qy)<6) return d; }
      return null; }

    function onDown(e){ var p=rel(e);
      if(!tool){  // select / edit mode
        var ha=hitAnchor(p.x,p.y); if(ha){ sel=ha.d; dragging=ha; redraw(); e.preventDefault(); return; }
        var hb=hitBody(p.x,p.y); sel=hb||null; redraw(); return; }
      var s=snap(p.x,p.y);
      if(arity(tool)===1){ if(tool==='text'){ var t=prompt('Text:',''); if(t==null)return; items.push({t:'text',a:s,text:t,col:'#e6edf3'}); }
          else items.push({t:'hline',a:s,col:'#bc8cff'}); save(); sel=items[items.length-1]; finishTool(); redraw(); return; }
      draft={t:tool,a:s,b:s,col:toolCol(tool)}; e.preventDefault(); }
    function onMove(e){ var p=rel(e);
      if(draft){ draft.b=snap(p.x,p.y); redraw(); return; }
      if(dragging){ var s=snap(p.x,p.y); dragging.d[dragging.key]=s; redraw(); return; } }
    function onUp(e){
      if(draft){ var pa=px(draft.a),pb=px(draft.b);
        if(pa&&pb&&(Math.abs(pb.x-pa.x)>3||Math.abs(pb.y-pa.y)>3)){ items.push(draft); sel=draft; save(); }
        draft=null; finishTool(); redraw(); return; }
      if(dragging){ dragging=null; save(); } }
    cap.addEventListener('pointerdown',onDown); window.addEventListener('pointermove',onMove); window.addEventListener('pointerup',onUp);
    // Drawings are DIRECTLY editable (Ramana 2026-07-10): click one to select and drag
    // its anchors, double-click to configure — no need to arm the ⬎ edit mode first.
    // Capture phase: a hit swallows the event BEFORE the chart pans; a miss falls
    // through untouched, so normal chart scroll/zoom is unaffected.
    host.addEventListener('pointerdown',function(e){
      if(tool||editing||hidden) return;
      if(edPop&&edPop.contains(e.target)) return;
      var p=rel(e);
      var ha=hitAnchor(p.x,p.y);
      if(ha){ sel=ha.d; dragging=ha; e.stopPropagation(); e.preventDefault(); redraw(); return; }
      var hb=hitBody(p.x,p.y);
      if(hb){ if(sel!==hb){ sel=hb; redraw(); } e.stopPropagation(); e.preventDefault(); return; }
      if(sel){ sel=null; closeEditor(); redraw(); } },true);
    host.addEventListener('dblclick',function(e){
      if(hidden) return;
      if(edPop&&edPop.contains(e.target)) return;
      var p=rel(e);
      var ha=hitAnchor(p.x,p.y); var hb=ha?ha.d:hitBody(p.x,p.y);
      if(hb){ sel=hb; e.stopPropagation(); e.preventDefault(); redraw(); openEditor(hb,p.x,p.y); } },true);

    function toolCol(t){ return {trend:'#58a6ff',rect:'#58a6ff',fib:'#d29922',fibext:'#a371f7',measure:'#39c5cf'}[t]||'#58a6ff'; }
    function setTool(t){ tool=(tool===t)?null:t; cap.style.pointerEvents=(tool||editing)?'auto':'none';
      pc.applyOptions({handleScroll:!tool,handleScale:!tool}); paintTools(); }
    var editing=false;
    function setEdit(){ editing=!editing; tool=null; cap.style.pointerEvents=editing?'auto':'none';
      pc.applyOptions({handleScroll:!editing,handleScale:!editing}); paintTools(); }
    function finishTool(){ tool=null; if(!editing){ cap.style.pointerEvents='none'; pc.applyOptions({handleScroll:true,handleScale:true}); } paintTools(); }

    // =====================================================================
    //  PER-DRAWING EDITOR — double-click any drawing (or ⚙ in ≡ list).
    //  Common: colour · width · delete. Trend: extend segment/→/↔ (EPA ray).
    //  Text: content. Fib/FibX: the LEVEL PICKER — every catalogue level with
    //  its market role beside it; only ticked levels render (persisted, d.lv).
    // =====================================================================
    var edPop=null;
    function closeEditor(){ if(edPop&&edPop.parentNode){ edPop.parentNode.removeChild(edPop); } edPop=null; }
    function edRow(){ return E('div','display:flex;align-items:center;gap:6px;margin:5px 0'); }
    function openEditor(d,X,Y){ closeEditor();
      edPop=E('div','position:absolute;z-index:30;width:290px;max-height:370px;overflow:auto;background:#0e1320;border:1px solid #30363d;border-radius:8px;padding:9px;box-shadow:0 8px 24px rgba(0,0,0,.55);font-family:-apple-system,Segoe UI,sans-serif;font-size:11px;color:#c9d1d9');
      var head=E('div','display:flex;justify-content:space-between;align-items:center;margin-bottom:4px');
      head.appendChild(E('b','font-size:12px;color:#e6edf3',dlabel(d)));
      var xb=E('span','cursor:pointer;color:#8b949e;font-size:14px;padding:0 4px','\\u00d7'); xb.onclick=closeEditor; head.appendChild(xb);
      edPop.appendChild(head);
      var r1=edRow();
      var sw=document.createElement('input'); sw.type='color'; sw.value=normHex(d.col||toolCol(d.t));
      sw.style.cssText='width:26px;height:20px;border:none;background:none;padding:0;cursor:pointer'; sw.title='Colour';
      sw.oninput=function(){ d.col=sw.value; save(); redraw(); };
      r1.appendChild(sw);
      var wsel=document.createElement('select'); wsel.style.cssText='background:#161b22;border:1px solid #30363d;color:#c9d1d9;border-radius:4px;font-size:10px;padding:1px 2px';
      WIDS.forEach(function(w2){ var op=document.createElement('option'); op.value=w2; op.textContent=w2+'px'; if((d.w||1.4)==w2)op.selected=true; wsel.appendChild(op); });
      wsel.title='Line width'; wsel.onchange=function(){ d.w=parseFloat(wsel.value); save(); redraw(); }; r1.appendChild(wsel);
      if(d.t==='trend'){
        var ex=document.createElement('select'); ex.style.cssText=wsel.style.cssText;
        ex.title='Project the line past its anchors (EPA-style ray)';
        [[0,'segment'],[1,'extend \\u2192'],[2,'extend \\u2194']].forEach(function(o){ var op=document.createElement('option'); op.value=o[0]; op.textContent=o[1]; if((d.x|0)===o[0])op.selected=true; ex.appendChild(op); });
        ex.onchange=function(){ d.x=parseInt(ex.value,10); save(); redraw(); }; r1.appendChild(ex);
      }
      var del=E('span','cursor:pointer;color:#f85149;border:1px solid #30363d;border-radius:4px;padding:2px 7px;margin-left:auto','delete');
      del.onclick=function(){ var i=items.indexOf(d); if(i>=0){ items.splice(i,1); if(sel===d)sel=null; save(); renderPanel(); redraw(); } closeEditor(); };
      r1.appendChild(del); edPop.appendChild(r1);
      if(d.t==='text'){
        var r2=edRow(); var ti=document.createElement('input'); ti.type='text'; ti.value=d.text||'';
        ti.style.cssText='flex:1;background:#161b22;border:1px solid #30363d;color:#c9d1d9;border-radius:4px;font-size:11px;padding:3px 6px';
        ti.oninput=function(){ d.text=ti.value; save(); redraw(); }; r2.appendChild(ti); edPop.appendChild(r2);
      }
      if(d.t==='fib'||d.t==='fibext'){
        var cat=(d.t==='fibext')?EXT_ALL:FIB, cur=lvOf(d);
        edPop.appendChild(E('div','margin:6px 0 2px;color:#8b949e;font-size:10px;letter-spacing:.4px;text-transform:uppercase','Levels \\u2014 tick what this drawing shows'));
        cat.forEach(function(r){
          var row=E('label','display:flex;align-items:flex-start;gap:6px;padding:2px 0;cursor:pointer');
          var cb2=document.createElement('input'); cb2.type='checkbox'; cb2.checked=cur.indexOf(r)>=0; cb2.style.cssText='margin-top:2px';
          cb2.onchange=function(){ var nv=lvOf(d).slice(); var ix=nv.indexOf(r);
            if(cb2.checked&&ix<0)nv.push(r); if(!cb2.checked&&ix>=0)nv.splice(ix,1);
            nv.sort(function(a3,b3){return a3-b3;}); d.lv=nv; save(); redraw(); };
          row.appendChild(cb2);
          row.appendChild(E('span','flex:1;line-height:1.35','<b style="color:#e6edf3">'+r+'</b> <span style="color:#7e90a8">'+(FIBN[r]||'')+'</span>'));
          edPop.appendChild(row); });
        var rst=E('span','cursor:pointer;color:#58a6ff;font-size:10px;text-decoration:underline','reset to defaults');
        rst.onclick=function(){ d.lv=null; save(); redraw(); openEditor(d,X,Y); };
        edPop.appendChild(rst);
      }
      var hw=host.clientWidth||600, hh=host.clientHeight||400;
      edPop.style.left=Math.max(6,Math.min(X+12,hw-305))+'px';
      edPop.style.top=Math.max(6,Math.min(Y+12,hh-200))+'px';
      host.appendChild(edPop);
    }

    // --- the Drawings family UI -------------------------------------------
    var TOOLS=[['trend','\\u2571','Trend line \\u2014 double-click it to extend into a ray (EPA)'],['hline','\\u2014','Horizontal line'],['rect','\\u25ad','Rectangle'],
      ['fib','F','Fib retracement \\u2014 double-click the drawing to choose levels'],['fibext','Fx','Fib extension (project targets beyond the move) \\u2014 double-click the drawing to choose levels (1.13\\u20134.618, each named)'],['measure','\\u22b9','Measure (\\u0394price, \\u0394%, bars, days)'],['text','T','Text']];
    var btns={};
    function tbtn(css,title,html){ var b=E('span',css,html); b.title=title; return b; }
    function baseBtn(on){ return 'cursor:pointer;font-size:13px;line-height:1;color:'+(on?'var(--ink)':'var(--ink-2)')+';border:1px solid '+(on?'#58a6ff':'var(--line-2)')+';border-radius:5px;padding:3px 7px;min-width:22px;text-align:center'; }
    function paintTools(){ TOOLS.forEach(function(t){ if(btns[t[0]])btns[t[0]].style.cssText=baseBtn(tool===t[0]); });
      if(btns._edit)btns._edit.style.cssText=baseBtn(editing);
      if(btns._mag)btns._mag.style.cssText='cursor:pointer;font-size:11px;color:'+(magnet?'var(--ink)':'var(--ink-2)')+';border:1px solid '+(magnet?'#58a6ff':'var(--line-2)')+';border-radius:5px;padding:3px 7px';
      if(btns._cfx)btns._cfx.style.cssText='cursor:pointer;font-size:11px;color:'+(conflux?'var(--ink)':'var(--ink-2)')+';border:1px solid '+(conflux?'#58a6ff':'var(--line-2)')+';border-radius:5px;padding:3px 7px';
      if(btns._hide)btns._hide.style.cssText='cursor:pointer;font-size:11px;color:'+(hidden?'var(--ink)':'var(--ink-2)')+';border:1px solid '+(hidden?'#58a6ff':'var(--line-2)')+';border-radius:5px;padding:3px 7px'; }
    var edit=tbtn(baseBtn(false),'Select / edit \\u2014 or just click a drawing directly; double-click configures it; Del removes it','\\u2b0e'); edit.onclick=setEdit; btns._edit=edit; bar.appendChild(edit);
    TOOLS.forEach(function(t){ var b=tbtn(baseBtn(false),t[2],t[1]); b.onclick=function(){ setTool(t[0]); }; btns[t[0]]=b; bar.appendChild(b); });
    var mag=tbtn('','Magnet — snap to nearest OHLC (still draggable)','\\ud83e\\uddf2 magnet'); mag.onclick=function(){ magnet=!magnet; paintTools(); }; btns._mag=mag; bar.appendChild(mag);
    var cfx=tbtn('','Narrow confluences: shade where extension levels (>1.0 only) from two different Fib drawings agree within 2% \\u2014 the same rule the auto Wolfe zones use','conflux');
    cfx.onclick=function(){ conflux=!conflux; paintTools(); redraw(); }; btns._cfx=cfx; bar.appendChild(cfx);
    var hide=tbtn('','Hide all drawings (tap again to restore)','hide all'); hide.onclick=function(){ hidden=!hidden; paintTools(); redraw(); }; btns._hide=hide; bar.appendChild(hide);
    var clear=tbtn('cursor:pointer;font-size:11px;color:var(--ink-2);border:1px solid var(--line-2);border-radius:5px;padding:3px 7px','Delete all drawings','clear');
    clear.onclick=function(){ if(items.length&&confirm('Delete all '+items.length+' drawing(s)?')){ items=[]; sel=null; save(); renderPanel(); redraw(); } }; bar.appendChild(clear);

    // =====================================================================
    //  DRAWING MANAGER — per-drawing style (colour/width) + delete-one + a
    //  list panel + export / import JSON. Caps + never-throws like the store.
    // =====================================================================
    var WIDS=[1,1.4,2,3];
    var manageBtn=tbtn('cursor:pointer;font-size:11px;color:var(--ink-2);border:1px solid var(--line-2);border-radius:5px;padding:3px 7px','Manage drawings (style / delete / export)','\\u2261 list'); bar.appendChild(manageBtn);
    var panel=E('div','display:none;position:absolute;top:100%;right:0;z-index:20;margin-top:4px;width:280px;max-height:300px;overflow:auto;background:#0e1320;border:1px solid '+C.border+';border-radius:8px;padding:8px;box-shadow:0 6px 20px rgba(0,0,0,.5);font-family:-apple-system,Segoe UI,sans-serif');
    // anchor the panel to the rail's drawings cell (bar) so it floats under the controls
    if(bar&&bar.style){ bar.style.position='relative'; } bar.appendChild(panel);
    function dlabel(d){ return {trend:'Trend',hline:'H-line',rect:'Rect',fib:'Fib',fibext:'Fib ext',measure:'Measure',text:'Text'}[d.t]||d.t; }
    function renderPanel(){
      if(panel.style.display==='none') return;
      panel.innerHTML='';
      var head=E('div','display:flex;justify-content:space-between;align-items:center;margin-bottom:6px');
      head.appendChild(E('span','font-size:11px;color:'+C.txtHi+';font-weight:600','Drawings ('+items.length+')'));
      var io=E('div','display:flex;gap:4px');
      var exp=E('span','cursor:pointer;font-size:10px;color:var(--ink-2);border:1px solid var(--line-2);border-radius:4px;padding:2px 6px','export'); exp.title='Download all drawings as JSON'; exp.onclick=exportJSON;
      var imp=E('span','cursor:pointer;font-size:10px;color:var(--ink-2);border:1px solid var(--line-2);border-radius:4px;padding:2px 6px','import'); imp.title='Load drawings from a JSON file (replaces current)'; imp.onclick=importJSON;
      io.appendChild(exp); io.appendChild(imp); head.appendChild(io); panel.appendChild(head);
      if(!items.length){ panel.appendChild(E('div','font-size:11px;color:'+C.dim+';padding:6px 2px','No drawings yet. Pick a tool and draw on the chart.')); return; }
      items.forEach(function(d,idx){
        var row=E('div','display:flex;align-items:center;gap:6px;padding:3px 0;border-top:1px solid var(--bg-2)');
        var sw=document.createElement('input'); sw.type='color'; sw.value=normHex(d.col||toolCol(d.t)); sw.title='Colour';
        sw.style.cssText='width:22px;height:18px;border:none;background:none;padding:0;cursor:pointer';
        sw.oninput=function(){ d.col=sw.value; save(); redraw(); };
        var nm=E('span','flex:1;font-size:11px;color:'+C.txt,dlabel(d)+(d.t==='text'&&d.text?(': '+esc(d.text).slice(0,14)):''));
        nm.style.cursor='pointer'; nm.title='Select on chart'; nm.onclick=function(){ sel=d; redraw(); };
        var wsel=document.createElement('select'); wsel.style.cssText='background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);border-radius:4px;font-size:10px;padding:1px 2px';
        WIDS.forEach(function(w){ var op=document.createElement('option'); op.value=w; op.textContent=w+'px'; if((d.w||1.4)==w)op.selected=true; wsel.appendChild(op); });
        wsel.title='Line width'; wsel.onchange=function(){ d.w=parseFloat(wsel.value); save(); redraw(); };
        var cfg=E('span','cursor:pointer;font-size:11px;color:var(--ink-2);padding:0 3px','\\u2699'); cfg.title='Configure (levels / extend / colour)';
        cfg.onclick=function(){ sel=d; redraw(); openEditor(d,24,24); };
        var del=E('span','cursor:pointer;font-size:13px;color:#f85149;padding:0 3px','\\u00d7'); del.title='Delete this drawing';
        del.onclick=function(){ var i=items.indexOf(d); if(i>=0){ items.splice(i,1); if(sel===d)sel=null; save(); renderPanel(); redraw(); } };
        row.appendChild(sw); row.appendChild(nm); row.appendChild(wsel); row.appendChild(cfg); row.appendChild(del); panel.appendChild(row);
      });
    }
    function esc(s){ return (s||'').replace(/[<>&]/g,''); }
    function normHex(c){ if(!c)return '#58a6ff'; if(/^#[0-9a-fA-F]{6}$/.test(c))return c; if(/^#[0-9a-fA-F]{3}$/.test(c))return '#'+c[1]+c[1]+c[2]+c[2]+c[3]+c[3]; return '#58a6ff'; }
    function exportJSON(){ try{ var blob=new Blob([JSON.stringify(items,null,2)],{type:'application/json'});
      var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='drawings_'+sym+'.json'; a.click();
      setTimeout(function(){ URL.revokeObjectURL(a.href); },1000); }catch(e){} }
    function importJSON(){ try{ var inp=document.createElement('input'); inp.type='file'; inp.accept='application/json,.json';
      inp.onchange=function(){ var f=inp.files&&inp.files[0]; if(!f)return; var rd=new FileReader();
        rd.onload=function(){ try{ var arr=JSON.parse(rd.result); if(Array.isArray(arr)){ items=arr.slice(0,500); sel=null; save(); renderPanel(); redraw(); } else alert('That file is not a drawings array.'); }catch(e){ alert('Could not parse that JSON.'); } };
        rd.readAsText(f); }; inp.click(); }catch(e){} }
    manageBtn.onclick=function(){ var open=panel.style.display==='none'; panel.style.display=open?'block':'none';
      manageBtn.style.cssText='cursor:pointer;font-size:11px;color:'+(open?'var(--ink)':'var(--ink-2)')+';border:1px solid '+(open?'#58a6ff':'var(--line-2)')+';border-radius:5px;padding:3px 7px'; if(open)renderPanel(); };
    paintTools();

    // Del removes the selected drawing; Escape closes the editor popover.
    window.addEventListener('keydown',function(e){
      if(e.key==='Escape'&&edPop){ closeEditor(); return; }
      if((e.key==='Delete'||e.key==='Backspace')&&sel){
        var tg=e.target&&e.target.tagName; if(tg==='INPUT'||tg==='TEXTAREA'||tg==='SELECT') return;
        var i=items.indexOf(sel); if(i>=0){ items.splice(i,1); sel=null; closeEditor(); save(); renderPanel(); redraw(); e.preventDefault(); } } });

    return { redraw:redraw };
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
</script>"""
