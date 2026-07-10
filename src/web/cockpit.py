"""Cockpit — registry-driven, full-bleed HOME + MARKETS render (collision-isolated).

Why a separate module: the big UI rebuild lives here so it doesn't fight the
parallel sessions editing dashboard.py. dashboard.py imports `render_home` /
`render_markets` and wraps the returned INNER html in its own `_shell`. We reuse
dashboard's helpers (`_mv_*`, `_rs_strip`, formatters, constants) via a LAZY
`from src.web import dashboard as D` inside each function — that breaks the import
cycle (dashboard imports us at top; we import it only at call-time, by when it is
fully loaded).

STRATEGY_REGISTRY is the single source of truth for the strategy pillars: add one
entry and it appears in the home count-strip + hub automatically — the user's
"a new strategy should auto-update the dashboard" ask (D-UI-7: strategy = a lens).
"""
from __future__ import annotations

import json
import math
import statistics

# stock_rs does NOT import dashboard, so these top-level imports are cycle-safe.
try:
    from src.automation.stock_rs import leaders_laggards, conviction_shortlist
except Exception:  # keep the page resilient if the module shifts
    leaders_laggards = conviction_shortlist = None
# insider_events imports only core.db — cycle-safe; single source for the
# INSIDER pillar count (== strategist card == board_health, by construction).
try:
    from src.automation.insider_events import flagged_symbols as _insider_flagged
except Exception:  # noqa: BLE001
    _insider_flagged = None


def _near(g) -> bool:
    """Close vs the value-weighted key price (the 🎯 launch band), −1%…+5%."""
    return g is not None and -1.0 <= g <= 5.0


# --- Two-axis trend verdict (THE "trends not properly identified" fix) --------
# The old page showed only `rs_vs_broad_trend_state` — the RS RATIO (index ÷ Nifty
# 500) trend, which reads "DOWNTREND" for an index that is rising in price but
# merely lagging the broad market. These derive the ABSOLUTE price trend on-read
# from the index's OWN levels and present it BESIDE the RS trend. Deterministic,
# zero-LLM. The css_state values map to the existing `.p-*` pill classes.
def _abs_trend(pa200, pa50, r3, off52h=None, abv52l=None):
    """Absolute price-trend verdict from the index's own levels. Returns
    (label, css_state, score 0-3). score = #{above 200d, above 50d, 3m ret > 0}."""
    score = ((1 if (pa200 or 0) > 0 else 0)
             + (1 if (pa50 or 0) > 0 else 0)
             + (1 if (r3 or 0) > 0 else 0))
    if off52h is not None and off52h >= -2:
        return ("NEAR HIGH", "BREAKOUT", score)
    if abv52l is not None and abv52l <= 2:
        return ("NEAR LOW", "BREAKDOWN", score)
    if score == 3:
        return ("UPTREND", "UPTREND", score)
    if score == 2:
        return ("UP-BIASED", "UPTREND", score)
    if score == 1:
        return ("MIXED", "CONSOLIDATING", score)
    return ("DOWNTREND", "DOWNTREND", score)


def _rel_trend(st, s1, s3, s6, s12):
    """Relative-strength verdict (vs Nifty 500): the RS trend state confirmed by
    how many horizon slopes are rising. Returns (label, css_state)."""
    rs_up_n = sum(1 for v in (s1, s3, s6, s12) if v is not None and v > 1)
    up = st in ("UPTREND", "BREAKOUT")
    down = st in ("DOWNTREND", "BREAKDOWN")
    if up and rs_up_n >= 3:
        return ("LEADING", "UPTREND")
    if down and rs_up_n <= 1:
        return ("LAGGING", "DOWNTREND")
    return ("IN-LINE", "CONSOLIDATING")


def _index_verdict(is_broad, abs_label, abs_score, rel_label):
    """The composite headline: broad indices report just their ABS trend; sectors
    cross the ABS×REL matrix into an actionable verdict. When RS is IN-LINE the
    headline DEFERS to the (decisive) price trend so it can never contradict the
    PRICE pill beside it — the whole point is that the price trend IS identified."""
    if is_broad:
        return abs_label
    abs_up = (abs_score >= 2 or abs_label == "NEAR HIGH") and abs_label != "NEAR LOW"
    abs_down = abs_score == 0 or abs_label == "NEAR LOW"
    leading = rel_label == "LEADING"
    lagging = rel_label == "LAGGING"
    if abs_up and leading:
        return "MARKET LEADER"
    if abs_up and lagging:
        return "RISING BUT LAGGING"
    if abs_down and leading:
        return "DEFENSIVE / RELATIVE WINNER"
    if abs_down and lagging:
        return "AVOID"
    if abs_up:
        return "RISING · IN-LINE"
    if abs_down:
        return "FALLING · IN-LINE"
    return "NEUTRAL"


# --- Deterministic CCI coverage state (PROVEN / UNPROVEN / + STALE) ------------
# From the settled-promise count + the recency of the scored concall period
# (as_of_period is a 'Mon YYYY' label). A name is UNPROVEN until any guidance
# promise resolves; PROVEN once ≥1 has; STALE if the newest scored period is
# older than ~2 quarters. Degrades to '' (no badge) when there's no concall data.
_CCI_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
               "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def _cci_period_ym(period):
    if not period:
        return None
    parts = str(period).strip().split()
    if len(parts) != 2:
        return None
    mo = _CCI_MONTHS.get(parts[0][:3].lower())
    try:
        yr = int(parts[1])
    except ValueError:
        return None
    return (yr, mo) if mo else None


def cci_state(row):
    """Returns (label, tone) — label ∈ {'', 'UNPROVEN', 'PROVEN', '… · STALE'};
    tone ∈ {'', 'mut', 'pos', 'stale'} for colouring."""
    if not row:
        return ("", "")
    settled = row.get("n_promises_resolved") or 0
    calls = row.get("n_concalls") or 0
    if settled >= 1:
        base, tone = "PROVEN", "pos"
    elif calls >= 1:
        base, tone = "UNPROVEN", "mut"
    else:
        return ("", "")
    ym = _cci_period_ym(row.get("as_of_period"))
    if ym:
        import datetime as _dt
        now = _dt.date.today()
        months_old = (now.year - ym[0]) * 12 + (now.month - ym[1])
        if months_old > 6:
            return (base + " · STALE", "stale")
    return (base, tone)


# --- Deterministic sector weather (tailwind / headwind / recovery / …) ---------
# First-match-wins. Slope-only inputs are sufficient (breadth + accum-skew refine
# but are optional, so the badge ships everywhere — markets bundle, /dash/sectors,
# /dash/index). Returns (key, reasons[]). Zero LLM.
# Weather badge palette — kept in lockstep with rotation_view.PHASE (D-PITCH-2: the ONE
# rotation colour contract) so the markets/sectors weather badge speaks the same value
# language as /dash/rotation: green = improving/leading, red = weakening/lagging, amber =
# rolling-over caution, blue-free. (accent, dim-bg, border) per state.
_WEATHER = {
    "TAILWIND":     ("🌤 Tailwind",     "#3fd486", "#102a1d", "#1f6f3a"),
    "RECOVERY":     ("🌅 Recovery",     "#7fe6b0", "#10271d", "#2f8f63"),
    "HEADWIND":     ("🌧 Headwind",     "#ff6a7a", "#2e161b", "#8f1f2a"),
    "ROLLING-OVER": ("⛅ Rolling over",  "#f6b73c", "#2e2611", "#5a4a1f"),
    "NEUTRAL":      ("☁ Neutral",       "#7e90a8", "#1a232f", "var(--line-2)"),
}


def sector_weather(s1, s3, s6, s12, st, breadth=None, accum_skew=None):
    """Classify a sector's weather from its RS slopes + trend state (+ optional
    constituent breadth / accumulation skew). First-match-wins."""
    a1, a3, a6, a12 = (s1 or 0.0), (s3 or 0.0), (s6 or 0.0), (s12 or 0.0)
    up = st in ("UPTREND", "BREAKOUT")
    down = st in ("DOWNTREND", "BREAKDOWN")
    R = []
    if (up and a3 > 1 and a1 > 0
            and (breadth is None or breadth >= 55)
            and (accum_skew is None or accum_skew >= 0)):
        R = [f"RS {(st or '').lower()}", f"3m slope {a3:+.1f}", f"1m {a1:+.1f}"]
        if breadth is not None:
            R.append(f"{breadth:.0f}% members RS-up")
        return "TAILWIND", R
    if ((a6 < 0 or a12 < 0) and a1 > 1 and a3 > a6
            and (breadth is None or breadth > 40)):
        R = ["longer-horizon RS still negative", f"1m slope {a1:+.1f} turning up",
             f"3m {a3:+.1f} > 6m {a6:+.1f}"]
        return "RECOVERY", R
    if (down and a3 < -1
            and (breadth is None or breadth < 45)
            and (accum_skew is None or accum_skew <= 0)):
        R = [f"RS {(st or '').lower()}", f"3m slope {a3:+.1f}"]
        if breadth is not None:
            R.append(f"only {breadth:.0f}% members RS-up")
        return "HEADWIND", R
    if up and a1 < 0 and a12 > 0:
        R = [f"12m slope {a12:+.1f} positive", f"1m {a1:+.1f} rolling over"]
        return "ROLLING-OVER", R
    return "NEUTRAL", [f"3m slope {a3:+.1f}"]


def _weather_badge(key, reasons=None):
    label, col, bg, bd = _WEATHER.get(key, _WEATHER["NEUTRAL"])
    ti = ""
    if reasons:
        ti = ' title="' + " · ".join(reasons).replace('"', "'") + '"'
    return (f'<span style="display:inline-block;font-size:10px;font-weight:700;'
            f'padding:2px 8px;border-radius:9px;letter-spacing:.3px;white-space:nowrap;'
            f'background:{bg};color:{col};border:1px solid {bd}"{ti}>{label}</span>')


def _news_card(conn, esc, limit=8):
    """Read-only "latest market brief" — newest sent_news rows (title→url, source,
    date). Market-wide (sent_news has no sector tag); explicitly context, NOT a
    signal; NO LLM at render. Silent (empty string) if the table is absent/empty."""
    try:
        rows = conn.execute(
            "SELECT title, source, url, sent_at FROM sent_news "
            "ORDER BY sent_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
    except Exception:
        return ""
    if not rows:
        return ""
    items = []
    for r in rows:
        title = esc(r["title"] or "")
        src = esc(r["source"] or "")
        when = esc((r["sent_at"] or "")[:10])
        url = r["url"] or ""
        href = url if (url.startswith("http://") or url.startswith("https://")) else ""
        head = (f'<a class="row" style="display:inline;color:var(--ink)" target="_blank" '
                f'rel="noopener" href="{esc(href)}">{title}</a>' if href else title)
        items.append(
            f'<tr><td class="l">{head}</td>'
            f'<td class="r mut" style="font-size:11px">{src}</td>'
            f'<td class="r mut" style="font-size:11px">{when}</td></tr>')
    return ('<div class="card ck-board" style="border-top:2px solid var(--ink-3)">'
            '<div class="ck-h">📰 Latest headlines'
            '<span class="sub" style="margin:0;font-weight:400">context, not a signal · market-wide</span></div>'
            f'<table class="ck-t"><tbody>{"".join(items)}</tbody></table></div>')


# Index charts (own-price candles/line AND the RS-ratio chart) on ONE page — the
# cockpit-framed superset of the old /dash/ratio, with the SAME rich charting as
# the stock page: chart-type toggle (candles/line), Daily/Weekly/Monthly/Quarterly
# interval resampling, range buttons, and 50/200-period MAs recomputed per interval.
# Plain template (braces are JS): __CDN__/__DATA__ get .replace()d. __DATA__ =
# {price:[{t,o,h,l,c}], ratio:[{t,r}]} (daily; MAs + ratio crosses computed client-
# side per interval). Each chart owns its OWN scoped control bars so they don't clash.
_INDEX_CHART_JS = """
<script src="__CDN__"></script>
<script>
const IXD = __DATA__;
(function(){
  if(!window.LightweightCharts){ ['idxChart','idxRatioChart'].forEach(function(id){var h=document.getElementById(id); if(h) h.innerHTML='<div style="color:#8b949e;padding:20px">Chart library failed to load (offline?).</div>';}); return; }
  const common={
    layout:{ background:{color:'#161b22'}, textColor:'#8b949e', fontSize:11 },
    grid:{ vertLines:{color:'#21262d'}, horzLines:{color:'#21262d'} },
    timeScale:{ borderColor:'#30363d', rightOffset:3 },
    rightPriceScale:{ borderColor:'#30363d' },
    crosshair:{ mode:0 }, handleScroll:true, handleScale:true,
  };
  function tkey(t){ return (typeof t==='object'&&t)?(t.year+'-'+('0'+t.month).slice(-2)+'-'+('0'+t.day).slice(-2)):t; }
  function f2(v){ return v!=null?Number(v).toLocaleString('en-IN',{maximumFractionDigits:2}):'—'; }
  function f4(v){ return v!=null?Number(v).toFixed(4):'—'; }
  // ISO-week / month / quarter keys (close-of-period), mirroring the stock page.
  function isoWeekKey(s){ var d=new Date(s+'T00:00:00Z'); var jd=(d.getUTCDay()+6)%7; d.setUTCDate(d.getUTCDate()-jd+3);
    var iy=d.getUTCFullYear(); var j4=new Date(Date.UTC(iy,0,4)); var j4d=(j4.getUTCDay()+6)%7; j4.setUTCDate(j4.getUTCDate()-j4d+3);
    var wk=1+Math.round((d-j4)/(7*86400000)); return iy+'-W'+('0'+wk).slice(-2); }
  function pkey(s,tf){ if(tf==='w') return isoWeekKey(s); if(tf==='m') return s.slice(0,7);
    if(tf==='q'){ var y=s.slice(0,4),mo=parseInt(s.slice(5,7),10); return y+'-Q'+(Math.floor((mo-1)/3)+1); } return s; }
  function resampleOHLC(arr,tf){ if(tf==='d') return arr.slice(); var out=[],k=null,c=null;
    for(var i=0;i<arr.length;i++){ var d=arr[i],kk=pkey(d.t,tf);
      if(kk!==k){ if(c) out.push(c); k=kk; c={t:d.t,o:d.o,h:d.h,l:d.l,c:d.c}; }
      else { c.h=Math.max(c.h,d.h); c.l=Math.min(c.l,d.l); c.c=d.c; c.t=d.t; } }
    if(c) out.push(c); return out; }
  function resampleLine(arr,tf){ if(tf==='d') return arr.slice(); var out=[],k=null,last=null;
    for(var i=0;i<arr.length;i++){ var d=arr[i],kk=pkey(d.t,tf); if(kk!==k){ if(last) out.push(last); k=kk; } last=d; }
    if(last) out.push(last); return out; }
  function sma(vals,w){ var out=[],run=0; for(var i=0;i<vals.length;i++){ run+=vals[i].value; if(i>=w) run-=vals[i-w].value;
    if(i>=w-1) out.push({time:vals[i].time,value:run/w}); } return out; }
  function curR(sel){ var b=document.querySelector(sel+' button.on'); return b?parseInt(b.dataset.r):252; }
  function wireRange(sel, chart, getBars){
    var btns=document.querySelectorAll(sel+' button'); if(!btns.length) return function(){};
    function setRange(n){ var data=getBars(); if(!data.length) return; if(!n||n>=data.length){ chart.timeScale().fitContent(); return; }
      var from=data[data.length-n].t, to=data[data.length-1].t; chart.timeScale().setVisibleRange({from:from,to:to}); }
    btns.forEach(function(b){ b.onclick=function(){ btns.forEach(function(x){x.classList.remove('on');}); b.classList.add('on'); setRange(parseInt(b.dataset.r)); }; });
    return setRange;
  }
  function wireToggle(sel, cb){ document.querySelectorAll(sel+' button').forEach(function(b){
    b.onclick=function(){ document.querySelectorAll(sel+' button').forEach(function(x){x.classList.toggle('on',x===b);}); cb(b.dataset); }; }); }

  // ===== own-price chart: candles/line × D·W·M·Q × range, 50/200-MA per interval =====
  var pHost=document.getElementById('idxChart');
  if(pHost && IXD.price && IXD.price.length){
    var pc=LightweightCharts.createChart(pHost, Object.assign({height:320}, common));
    var candle=pc.addCandlestickSeries({upColor:'#3fd486',downColor:'#ff6a7a',wickUpColor:'#3fd486',wickDownColor:'#ff6a7a',borderVisible:false});
    var pline=pc.addLineSeries({color:'#1f6feb',lineWidth:2,priceLineVisible:false});
    var pm50=pc.addLineSeries({color:'#d29922',lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
    var pm200=pc.addLineSeries({color:'#6e7681',lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
    var ptf='d', ptype='candle', pbars=IXD.price.slice();
    var pSet=wireRange('#idxPriceRange', pc, function(){return IXD.price;});
    function pApply(){
      pbars=resampleOHLC(IXD.price, ptf);
      if(ptype==='candle'){ candle.setData(pbars.map(function(b){return {time:b.t,open:b.o,high:b.h,low:b.l,close:b.c};})); pline.setData([]); }
      else { pline.setData(pbars.map(function(b){return {time:b.t,value:b.c};})); candle.setData([]); }
      var closes=pbars.map(function(b){return {time:b.t,value:b.c};});
      pm50.setData(sma(closes,50)); pm200.setData(sma(closes,200));
      pSet(curR('#idxPriceRange'));
    }
    wireToggle('#idxPriceType', function(ds){ ptype=ds.itype; pApply(); });
    wireToggle('#idxPriceTf', function(ds){ ptf=ds.itf; pApply(); });
    pApply();
    var prdt=document.getElementById('idxRdt');
    pc.subscribeCrosshairMove(function(p){ var t,o,h,l,c;
      if(p&&p.time&&p.seriesData){ t=tkey(p.time); var cd=p.seriesData.get(candle); var ld=p.seriesData.get(pline);
        if(cd){ o=cd.open;h=cd.high;l=cd.low;c=cd.close; } else if(ld){ c=ld.value; } }
      else { var last=pbars[pbars.length-1]; if(last){ t=last.t;o=last.o;h=last.h;l=last.l;c=last.c; } }
      if(prdt) prdt.innerHTML='<b>'+(t||'')+'</b>'+(o!=null?'&nbsp; O '+f2(o)+' H '+f2(h)+' L '+f2(l):'')+'&nbsp; <b>C '+f2(c)+'</b>'; });
    var prz=null; new ResizeObserver(function(){ if(prz) clearTimeout(prz); prz=setTimeout(function(){ pc.applyOptions({}); },100); }).observe(pHost);
  }

  // ===== RS-ratio chart: line × D·W·M·Q × range (a ratio has no OHLC → line only) =====
  var rHost=document.getElementById('idxRatioChart');
  if(rHost && IXD.ratio && IXD.ratio.length){
    var rc=LightweightCharts.createChart(rHost, Object.assign({height:280}, common));
    var rl=rc.addLineSeries({color:'#1f6feb',lineWidth:2,priceLineVisible:false});
    var rm50=rc.addLineSeries({color:'#d29922',lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
    var rm200=rc.addLineSeries({color:'#6e7681',lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
    var rtf='d', rbars=IXD.ratio.slice();
    var rSet=wireRange('#idxRatioRange', rc, function(){return IXD.ratio;});
    function rApply(){
      rbars=resampleLine(IXD.ratio, rtf);
      var vals=rbars.map(function(d){return {time:d.t,value:d.r};});
      rl.setData(vals);
      var m50=sma(vals,50), m200=sma(vals,200); rm50.setData(m50); rm200.setData(m200);
      var m50map={}; m50.forEach(function(p){m50map[p.time]=p.value;});
      var win=(rtf==='d'?252:rtf==='w'?52:rtf==='m'?12:4), mk=[];
      for(var i=0;i<vals.length;i++){ var t=vals[i].time, v=vals[i].value, mv=m50map[t];
        if(i>0){ var pv=vals[i-1].value, pmv=m50map[vals[i-1].time];
          if(mv!=null&&pmv!=null){ if(pv<pmv&&v>=mv) mk.push({time:t,position:'belowBar',color:'#3fd486',shape:'arrowUp',text:'↑50'});
            else if(pv>=pmv&&v<mv) mk.push({time:t,position:'aboveBar',color:'#ff6a7a',shape:'arrowDown',text:'↓50'}); } }
        if(i>=win-1){ var hi=true; for(var j=i-win+1;j<i;j++){ if(vals[j].value>=v){ hi=false; break; } } if(hi) mk.push({time:t,position:'aboveBar',color:'#3fd486',shape:'circle'}); } }
      mk.sort(function(a,b){return a.time<b.time?-1:(a.time>b.time?1:0);});
      rl.setMarkers(mk);
      rSet(curR('#idxRatioRange'));
    }
    wireToggle('#idxRatioTf', function(ds){ rtf=ds.itf; rApply(); });
    rApply();
    var rrdt=document.getElementById('idxRatioRdt');
    rc.subscribeCrosshairMove(function(p){ var t,r,a,b;
      if(p&&p.time&&p.seriesData){ t=tkey(p.time); var x=p.seriesData.get(rl); r=x?x.value:null; var y=p.seriesData.get(rm50); a=y?y.value:null; var z=p.seriesData.get(rm200); b=z?z.value:null; }
      else { var last=rbars[rbars.length-1]; if(last){ t=last.t; r=last.r; } }
      if(rrdt) rrdt.innerHTML='<b>'+(t||'')+'</b>&nbsp; ratio <b>'+f4(r)+'</b>&nbsp; · 50-MA '+f4(a)+'&nbsp; · 200-MA '+f4(b); });
    var rrz=null; new ResizeObserver(function(){ if(rrz) clearTimeout(rrz); rrz=setTimeout(function(){ rc.applyOptions({}); },100); }).observe(rHost);
  }
})();
</script>
"""


# --- THE STRATEGY REGISTRY ----------------------------------------------------
# One entry per pillar. `count(conn, sig_date, D) -> int | None` is the live count
# (None = not-yet-live). Adding an entry here makes the pillar appear on the home
# count-strip automatically. accent = the pillar's colour across the whole UI.
STRATEGY_REGISTRY = [
    {"key": "CONV", "label": "Conviction", "accent": "#d2a8ff", "href": "/dash/conviction",
     "cta": "all-pillars aligned",
     "thesis": "Every pillar aligned — an RS leader institutions are accumulating now, with the entry.",
     "count": lambda conn, d, D: (len(conviction_shortlist(limit=300)) if conviction_shortlist else 0)},
    {"key": "POS", "label": "Positioning", "accent": "#58a6ff", "href": "/dash/stocks",
     "cta": "SS/S triggers today",
     "thesis": "Where institutional delivery money is positioning now — DVPT vs its own peak-day baselines.",
     "count": lambda conn, d, D: conn.execute(
         "SELECT COUNT(*) c FROM stock_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
         "WHERE s.trade_date=? AND s.trigger_rank IN ('SS','S') " + D._SCAN_FILTERS, (d,)).fetchone()["c"]},
    {"key": "MEP", "label": "Accum/Distrib", "accent": "#db61a2", "href": "/dash/mep",
     "cta": "signed — accum & distrib",
     "thesis": "Signed accumulation vs distribution (descriptor) — who is being absorbed. SIGNED where DVPT is side-blind; a character/confirmation lens, not a picker (D62 — predictive role failed its DSR gate).",
     "count": lambda conn, d, D: conn.execute(
         "SELECT COUNT(*) c FROM mep_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
         "WHERE s.trade_date=? AND s.mep_state_smooth='STRONG_ACCUM' " + D._SCAN_FILTERS, (d,)).fetchone()["c"]},
    {"key": "RS", "label": "Relative Strength", "accent": "var(--up)", "href": "/dash/leaders",
     "cta": "strong-in-strong leaders",
     "thesis": "Beating the broad market and leading its own sector.",
     "count": lambda conn, d, D: (len(leaders_laggards("leaders", limit=400)) if leaders_laggards else 0)},
    {"key": "CPR", "label": "Structure · CPR", "accent": "#bc8cff", "href": "/dash/cpr",
     "cta": "fresh reversals",
     "thesis": "Multi-timeframe CPR — has price just turned (U / ∩) and is it coiled? Amplified when higher TFs agree.",
     "count": lambda conn, d, D: len(D._cpr_setups(conn, fresh_only=True, limit=200))},
    {"key": "QUAL", "label": "Quality · pt14", "accent": "#d29922", "href": "/dash/screener",
     "cta": "names scored",
     "thesis": "Is the business worth owning — the patearn 14-pattern durability score.",
     "count": lambda conn, d, D: conn.execute("SELECT COUNT(DISTINCT symbol) c FROM pattern_scores").fetchone()["c"]},
    {"key": "CCI", "label": "Mgmt Credibility", "accent": "#39c5cf", "href": "/dash/concalls",
     "cta": "concall credibility",
     "thesis": "Do managements keep their promises? Measurable guidance-accuracy + a deterioration / ⛔veto avoid-tape, from earnings concalls. (Pilot — backfill accruing.)",
     "count": lambda conn, d, D: conn.execute("SELECT COUNT(DISTINCT symbol) c FROM concall_scores").fetchone()["c"]},
    {"key": "LAUNCH", "label": "Launchpad", "accent": "#f0883e", "href": "/dash/launchpad",
     "cta": "fresh triggers today",
     "thesis": "Validated explosive-move precursors (momentum-continuation ∪ coiled ∪ pullback) from the nightly launchpad_signals snapshot. D56 research — net-of-costs, walk-forward-positive momentum core; a setup screen, not advice.",
     # was hardcoded None ("—" on the front page) because the live scan cost ~9s;
     # the S84 nightly snapshot removed that excuse — count the FRESH rising edge.
     "count": lambda conn, d, D: conn.execute(
         "SELECT COUNT(*) c FROM launchpad_signals WHERE age<=2").fetchone()["c"]},
    {"key": "INSIDER", "label": "Insider activity", "accent": "#f778ba", "href": "/dash/insider",
     "cta": "fresh promoter buying",
     "thesis": "Skin in the game — principals (promoters/directors/KMP) net-buying on the open market with their own money, bought within the last 30 days. SEBI PIT filings, plumbing classified out. Descriptive.",
     "count": lambda conn, d, D: (len(_insider_flagged(conn)[0])
                                  if _insider_flagged else None)},
    {"key": "GROWTH", "label": "Growth-intent", "accent": "#7ee787", "href": "/dash/growth",
     "cta": "companies committing",
     "thesis": "Forward growth PROPOSALS from concalls — capex, expansion, debt-cut, new products — ₹-normalised. Companies with a growth-polarity commitment in the last 12 months.",
     "count": lambda conn, d, D: conn.execute(
         "SELECT COUNT(DISTINCT symbol) c FROM concall_signals WHERE is_growth_intent=1 "
         "AND COALESCE(polarity,1)>=0 AND (year*100+month) >= "
         "(SELECT MAX(year*100+month)-100 FROM concall_signals WHERE is_growth_intent=1)"
     ).fetchone()["c"]},
    {"key": "MOM", "label": "Momentum", "accent": "#ffa657", "href": "/dash/markets/momentum-scan",
     "cta": "top-decile ensemble",
     "thesis": "Equal-weight momentum ensemble (12m · 52w-high · risk-adj · low-vol), top decile. Attribution says this is momentum BETA, not selection — a tilt you ride knowingly, never a buy list.",
     "count": lambda conn, d, D: conn.execute(
         "SELECT COUNT(*) c FROM momentum_scan WHERE as_of=(SELECT MAX(as_of) FROM momentum_scan) "
         "AND ensemble_pctile>=90").fetchone()["c"]},
    {"key": "WOLFE", "label": "Wolfe", "accent": "#8b949e", "href": "/dash/wolfe/scan",
     "cta": "winner-profile setups",
     "thesis": "Winner-profile wave scan from the nightly wolfe_signals snapshot — read by SIDE (bulls carried the edge in testing; bears are tail-only). Descriptive overlay.",
     "count": lambda conn, d, D: conn.execute(
         "SELECT COUNT(*) c FROM wolfe_signals WHERE universe='nifty500'").fetchone()["c"]},
]


# Scoped styles for the cockpit + markets grids. Plain string (NOT an f-string) so
# the CSS braces don't need doubling. Self-contained — no edit to _BASE_CSS needed.
_CKPT_CSS = """
<style>
.ck-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:4px 0 14px;}
.ck-tile{display:block;background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:11px 13px;color:inherit;text-decoration:none;}
.ck-tile:hover{border-color:#484f58;}
.ck-tile .ck-n{font-size:26px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1;}
.ck-tile .ck-l{font-size:12px;font-weight:700;margin-top:5px;color:var(--ink);}
.ck-tile .ck-c{font-size:10.5px;color:var(--ink-2);margin-top:2px;}
.ckpt{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:12px;align-items:start;margin-bottom:14px;}
.ck-board{margin:0;padding:12px 14px;}
.ck-h{display:flex;align-items:baseline;gap:8px;font-size:14px;font-weight:700;margin-bottom:8px;}
.ck-h .em{font-size:15px;}
table.ck-t{width:100%;border-collapse:collapse;font-size:12.5px;}
table.ck-t td{padding:5px 6px;border-bottom:1px solid #1c2128;white-space:nowrap;vertical-align:middle;}
table.ck-t tr:last-child td{border-bottom:none;}
table.ck-t td.l{text-align:left;} table.ck-t td.r{text-align:right;font-variant-numeric:tabular-nums;}
.ck-board a.more{display:inline-block;margin-top:8px;color:#58a6ff;font-size:12px;text-decoration:none;}
.ck-board a.more:hover{text-decoration:underline;}
.mkt-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:9px;margin-bottom:6px;}
</style>
"""


# --- Screener row VIRTUALIZER (the real lag fix for Nifty 500) ----------------
# Only the visible window of rows lives in the DOM (recycled on scroll), the way
# TradeTiger/TradingView keep 500-row grids smooth. Sole row-controller: it owns
# filter / sort / export / CPR-gate / windowing over a JS array of the
# already-server-rendered <tr> nodes (no re-render of the micro-viz). The screener
# table drops its `dt` class so _DT_JS leaves it alone. Hard safety net: ANY error
# restores the full grid, so the worst case is "unvirtualized", never "broken".
SCREENER_VIRT_JS = """
<script>
(function(){
  var tb=null, ALL=null;
  try{
    var wrap=document.querySelector('.scrwrap'); var tbl=document.querySelector('table.scr');
    if(!wrap||!tbl||!tbl.tBodies[0]) return;
    tb=tbl.tBodies[0];
    ALL=Array.prototype.slice.call(tb.rows).filter(function(r){return !r.classList.contains('vspacer');});
    if(!ALL.length) return;
    ALL.forEach(function(r){ r._hascpr=r.classList.contains('has-cpr'); r._txt=r.textContent.toLowerCase(); });
    var padT=document.createElement('tr'); padT.className='vspacer'; padT.appendChild(document.createElement('td'));
    var padB=document.createElement('tr'); padB.className='vspacer'; padB.appendChild(document.createElement('td'));
    padT.firstChild.style.cssText=padB.firstChild.style.cssText='padding:0;border:0;height:0';
    var rowH=33, filt='', sCol=-1, sDir=1, cprOnly=false, view=ALL, cnt=null;
    function cellv(r,i){ var c=r.cells[i]; if(!c) return ''; var t=c.textContent.trim();
      var n=parseFloat(t.replace(/[,%×₹\\s]/g,'')); return isNaN(n)? t.toLowerCase() : n; }
    function compute(){ view=ALL;
      if(filt) view=view.filter(function(r){return r._txt.indexOf(filt)>=0;});
      if(cprOnly) view=view.filter(function(r){return r._hascpr;});
      if(sCol>=0){ view=view.slice().sort(function(a,b){ var x=cellv(a,sCol),y=cellv(b,sCol);
        return x===y?0:((x<y?-1:1)*sDir); }); }
      if(cnt) cnt.textContent=view.length+' rows'; }
    function render(){
      var st=wrap.scrollTop, h=wrap.clientHeight||600, vis=Math.ceil(h/rowH), BUF=10;
      var first=Math.max(0, Math.floor(st/rowH)-BUF);
      var last=Math.min(view.length, first+vis+2*BUF);
      padT.firstChild.style.height=(first*rowH)+'px';
      padB.firstChild.style.height=(Math.max(0,view.length-last)*rowH)+'px';
      var frag=document.createDocumentFragment(); frag.appendChild(padT);
      for(var i=first;i<last;i++) frag.appendChild(view[i]);
      frag.appendChild(padB);
      tb.innerHTML=''; tb.appendChild(frag);
    }
    // toolbar (filter + CSV + count) — same slot the _DT_JS toolbar used
    var tool=document.createElement('div'); tool.className='dttool';
    var fi=document.createElement('input'); fi.className='dtf'; fi.type='text'; fi.placeholder='filter rows…';
    var ex=document.createElement('button'); ex.type='button'; ex.className='dtx'; ex.textContent='⬇ CSV';
    cnt=document.createElement('span'); cnt.className='dtcount';
    tool.appendChild(fi); tool.appendChild(ex); tool.appendChild(cnt);
    wrap.parentNode.insertBefore(tool, wrap);
    compute(); render();
    if(view.length && view[0].offsetHeight){ rowH=view[0].offsetHeight; render(); }
    var tick=false;
    wrap.addEventListener('scroll', function(){ if(!tick){ tick=true;
      requestAnimationFrame(function(){ render(); tick=false; }); } }, {passive:true});
    fi.addEventListener('input', function(){ filt=fi.value.trim().toLowerCase(); compute(); wrap.scrollTop=0; render(); });
    var heads=tbl.querySelectorAll('thead tr.scol th');
    Array.prototype.forEach.call(heads, function(th,i){ th.style.cursor='pointer';
      th.addEventListener('click', function(){ if(sCol===i) sDir=-sDir; else { sCol=i; sDir=1; }
        Array.prototype.forEach.call(heads,function(h){h.classList.remove('sorta','sortd');});
        th.classList.add(sDir>0?'sorta':'sortd'); compute(); wrap.scrollTop=0; render(); }); });
    ex.addEventListener('click', function(){ var out=[]; var hs=[];
      Array.prototype.forEach.call(heads,function(h){hs.push('"'+h.textContent.trim().replace(/"/g,'""')+'"');});
      out.push(hs.join(','));
      view.forEach(function(r){ var cs=[]; Array.prototype.forEach.call(r.cells,function(c){
        cs.push('"'+c.textContent.trim().replace(/"/g,'""')+'"'); }); out.push(cs.join(',')); });
      var a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([out.join('\\n')],{type:'text/csv'}));
      a.download='screener.csv'; document.body.appendChild(a); a.click(); a.remove(); });
    // the CPR-confirmed gate (a button in _SCREENER_JS) toggles the table's
    // `cpr-only` class — fold it into the virtual filter instead of CSS row-hiding.
    new MutationObserver(function(){ var c=tbl.classList.contains('cpr-only');
      if(c!==cprOnly){ cprOnly=c; compute(); wrap.scrollTop=0; render(); } })
      .observe(tbl, {attributes:true, attributeFilter:['class']});
  }catch(e){
    try{ if(tb&&ALL){ tb.innerHTML=''; ALL.forEach(function(r){ tb.appendChild(r); }); } }catch(_){}
  }
})();
</script>
"""


def _state_label(st) -> str:
    """Whole-word RS/trend-state label for a pill — "UPTREND"→"Uptrend",
    "BREAKOUT"→"Breakout", "CONSOLIDATING"→"Consolidating", "STRONG_ACCUM"→"Strong
    Accum". Replaces the old `{st[:5]}` slice that rendered truncated "UPTRE"/"BREAK"/
    "CONSO"/"DOWNT" on Leaders/Sectors. Mirrors dashboard._state_label so both modules
    show the same text. The `p-{st}` colour class still uses the raw state — only the
    visible text changes. Output is the title-case of a fixed enum vocabulary (HTML-safe)."""
    s = ("" if st is None else str(st)).strip()
    if not s or s == "—":
        return s or "—"
    return s.replace("_", " ").title()


def _ck_tile(n, label, accent, cta="", href="") -> str:
    """One cockpit count-strip tile (shared by the strategy detail renders)."""
    a = f' href="{href}"' if href else ""
    tag = "a" if href else "div"
    c = f'<div class="ck-c">{cta}</div>' if cta else ""
    return (f'<{tag} class="ck-tile"{a} style="border-top:3px solid {accent}">'
            f'<div class="ck-n" style="color:{accent}">{n}</div>'
            f'<div class="ck-l">{label}</div>{c}</{tag}>')


def _ck_strip(tiles) -> str:
    """Wrap a list of _ck_tile() html into the .ck-tiles count strip."""
    return '<div class="ck-tiles">' + "".join(tiles) + '</div>'


def _board(title_html, sub, inner_html, href, cta, accent):
    return (f'<div class="card ck-board" style="border-top:2px solid {accent}">'
            f'<div class="ck-h">{title_html}'
            f'<span class="sub" style="margin:0;font-weight:400">{sub}</span></div>'
            f'{inner_html}<a class="more" href="{href}">{cta} →</a></div>')


# --- MEP instrument language (signed accumulation/distribution; D62, descriptor) ---
# Self-contained in cockpit.py (parallel-safe — no edit to dashboard.py's _mv_*).
def _mv_adbar(score):
    """Signed accumulation/distribution mini-bar. Centre = 0; green-right =
    accumulation, red-left = distribution. Clamped to ±2 for display."""
    if score is None:
        return '<span class="mut">—</span>'
    v = max(-2.0, min(2.0, score))
    frac = v / 2.0 * 50.0          # -50 .. +50 x-units from centre
    if v >= 0:
        x, w, col = 50.0, frac, "var(--up)"
    else:
        x, w, col = 50.0 + frac, -frac, "var(--down)"
    return (f'<svg width="92" height="16" viewBox="0 0 100 16" preserveAspectRatio="none" '
            f'style="vertical-align:middle">'
            f'<rect x="0" y="6.5" width="100" height="3" rx="1.5" style="fill:var(--bg-3)"/>'
            f'<rect x="{x:.1f}" y="4.5" width="{w:.1f}" height="7" rx="1.5" style="fill:{col}"/>'
            f'<line x1="50" y1="2" x2="50" y2="14" stroke-width="1" style="stroke:var(--ink-3)"/></svg>')


def _mep_pill(state):
    """Coloured MEP state badge."""
    if not state:
        return '<span class="mut">—</span>'
    c = {"STRONG_ACCUM": "var(--up)", "ACCUM": "var(--up)", "NEUTRAL": "#8b949e",
         "DISTRIB": "#f0883e", "STRONG_DISTRIB": "var(--down)"}.get(state, "#8b949e")
    txt = {"STRONG_ACCUM": "STRONG ACC", "ACCUM": "ACCUM", "NEUTRAL": "NEUTRAL",
           "DISTRIB": "DISTRIB", "STRONG_DISTRIB": "STRONG DIST"}.get(state, state)
    return (f'<span style="display:inline-block;padding:1px 6px;border-radius:6px;'
            f'font-size:10.5px;font-weight:700;color:{c};border:1px solid {c}55;'
            f'background:{c}14">{txt}</span>')


def render_home(sig_date, idx_date) -> str:
    """Full-bleed, registry-driven market cockpit. Reuses dashboard's instrument
    helpers so home speaks the same visual language as the screener."""
    from src.web import dashboard as D
    esc, pct, q, num = D._esc, D._pct, D._q, D._num

    nifty, breadth, lead = {}, None, None
    top_sectors, weak_sectors, top_stocks, stealth = [], [], [], []
    mep_accum, mep_distrib = [], []
    counts = {}
    with D.get_conn() as conn:
        if idx_date:
            r = conn.execute(
                "SELECT ret_1d_pct r1d, pct_above_200d_avg a200 FROM index_signals "
                "WHERE index_name='Nifty 50' AND trade_date=?", (idx_date,)).fetchone()
            nifty = dict(r) if r else {}
            b = conn.execute(
                "SELECT AVG(CASE WHEN pct_above_200d_avg>0 THEN 1.0 ELSE 0 END)*100 p "
                "FROM index_signals WHERE trade_date=? AND pct_above_200d_avg IS NOT NULL",
                (idx_date,)).fetchone()
            breadth = b["p"] if b and b["p"] is not None else None
            lr = conn.execute(
                "SELECT index_name FROM index_signals WHERE trade_date=? AND index_name IN "
                f"({','.join('?' for _ in D.LEADERSHIP_SET)}) "
                "ORDER BY COALESCE(ret_3m_pct,-999) DESC LIMIT 1",
                (idx_date, *D.LEADERSHIP_SET)).fetchone()
            lead = lr["index_name"] if lr else None
            sec_cols = ("index_name nm, rs_vs_broad_trend_state st, rs_vs_broad_slope_1m s1, "
                        "rs_vs_broad_slope_3m s3, rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12, "
                        "rs_vs_broad_slope_18m s18, rs_vs_broad_slope_24m s24")
            top_sectors = [dict(x) for x in conn.execute(
                f"SELECT {sec_cols} FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL "
                f"AND index_name IN ({D._real_sectors_in()}) ORDER BY COALESCE(rs_vs_broad_slope_3m,-999) DESC LIMIT 6",
                (idx_date,)).fetchall()]
            weak_sectors = [dict(x) for x in conn.execute(
                f"SELECT {sec_cols} FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL "
                f"AND index_name IN ({D._real_sectors_in()}) ORDER BY COALESCE(rs_vs_broad_slope_3m,999) ASC LIMIT 4",
                (idx_date,)).fetchall()]
        if sig_date:
            pos_cols = ("s.symbol, s.trigger_rank rank, s.is_ath_dvpt ath, s.accum_character ch, "
                        "s.delivery_value_per_trade dvpt, s.power_dvpt_1m p1, s.power_dvpt_2m p2, "
                        "s.power_dvpt_3m p3, s.power_dvpt_6m p6, s.power_dvpt_12m p12")
            top_stocks = [dict(x) for x in conn.execute(
                f"SELECT {pos_cols}, s.price_vs_hot_avg_pct pvh FROM stock_signals s "
                f"JOIN bhavcopy_rows b USING(symbol,trade_date) WHERE s.trade_date=? "
                f"AND s.delivery_value_per_trade IS NOT NULL {D._SCAN_FILTERS} "
                f"ORDER BY COALESCE(s.is_ath_dvpt,0) DESC, COALESCE(s.p_score,-1) DESC, "
                f"COALESCE(s.r_score,-1) DESC LIMIT 7", (sig_date,)).fetchall()]
            stealth = [dict(x) for x in conn.execute(
                f"SELECT {pos_cols}, s.p_score psc, s.pct_from_52w_high pfh FROM stock_signals s "
                f"JOIN bhavcopy_rows b USING(symbol,trade_date) WHERE s.trade_date=? "
                f"AND s.accum_character='ACCUMULATION' AND s.p_score>=3 "
                f"AND COALESCE(s.trade_count_ratio_1m_6m,99)<=1.1 AND s.pct_from_52w_high<=-10 "
                f"{D._SCAN_FILTERS} ORDER BY s.p_score DESC, s.pct_from_52w_high ASC LIMIT 6",
                (sig_date,)).fetchall()]
            # boards lead with the smoothed PHASE (held regimes), daily score kept
            mep_cols = ("s.symbol, s.mep_score sc, s.mep_state st, "
                        "s.mep_score_smooth ph, s.mep_state_smooth phst")
            mep_accum = [dict(x) for x in conn.execute(
                f"SELECT {mep_cols} FROM mep_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
                f"WHERE s.trade_date=? AND s.mep_score_smooth IS NOT NULL {D._SCAN_FILTERS} "
                f"ORDER BY s.mep_score_smooth DESC LIMIT 7", (sig_date,)).fetchall()]
            mep_distrib = [dict(x) for x in conn.execute(
                f"SELECT {mep_cols} FROM mep_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
                f"WHERE s.trade_date=? AND s.mep_score_smooth IS NOT NULL {D._SCAN_FILTERS} "
                f"ORDER BY s.mep_score_smooth ASC LIMIT 6", (sig_date,)).fetchall()]
        for e in STRATEGY_REGISTRY:
            try:
                counts[e["key"]] = e["count"](conn, sig_date, D)
            except Exception:
                counts[e["key"]] = None

    conv_rows = conviction_shortlist(limit=60) if conviction_shortlist else []
    lead_rows = leaders_laggards("leaders", limit=300) if leaders_laggards else []

    # --- regime banner ---
    a200 = nifty.get("a200")
    nifty_up = a200 is not None and a200 > 0
    if breadth is None:
        bcls, blabel = "b-neu", "NO DATA"
    elif breadth >= 60 and nifty_up:
        bcls, blabel = "b-on", "RISK-ON"
    elif breadth < 40 or not nifty_up:
        bcls, blabel = "b-off", "RISK-OFF"
    else:
        bcls, blabel = "b-neu", "NEUTRAL"
    lead_txt = {"Nifty 50": "Large-caps leading", "Nifty Midcap 150": "Mid-caps leading",
                "Nifty Smallcap 250": "Small-caps leading"}.get(lead, lead or "—")
    breadth_txt = f"{breadth:.0f}%" if breadth is not None else "—"

    search = ('<form class="search" action="/dash/stock" method="get" autocomplete="off">'
              '<input name="sym" placeholder="Enter NSE ticker — e.g. RELIANCE" '
              'autocapitalize="characters"/><button type="submit">Go</button></form>')
    banner = (f'<div class="banner {bcls}" style="font-size:15px">{blabel}'
              f'<small>· Nifty 50 {pct(nifty.get("r1d"))} today · {breadth_txt} of indices &gt; 200-DMA '
              f'· {esc(lead_txt)}</small></div>')

    # --- registry-driven count strip ---
    tiles = []
    for e in STRATEGY_REGISTRY:
        c = counts.get(e["key"])
        cval = "—" if c is None else str(c)
        tiles.append(
            f'<a class="ck-tile" href="{e["href"]}" style="border-top:3px solid {e["accent"]}" '
            f'title="{esc(e["thesis"])}"><div class="ck-n" style="color:{e["accent"]}">{cval}</div>'
            f'<div class="ck-l">{esc(e["label"])}</div><div class="ck-c">{esc(e["cta"])}</div></a>')
    count_strip = '<div class="ck-tiles">' + "".join(tiles) + '</div>'

    # --- boards (instrument language) ---
    def trig_rows(rows, score_cell=None):
        out = []
        for r in rows:
            rank = r.get("rank") or "-"
            ath = "⚡" if r.get("ath") else ""
            ladder = D._mv_ladder(r.get("dvpt"), r.get("p1"), r.get("p2"),
                                  r.get("p3"), r.get("p6"), r.get("p12"))
            extra = score_cell(r) if score_cell else f'<td><span class="pill p-{rank}">{rank}</span></td>'
            out.append(
                f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                f'<span class="sym">{ath}{esc(r["symbol"])}</span></a></td>'
                f'<td class="l">{ladder}</td>{extra}'
                f'<td class="l">{D._char_pill(r.get("ch"))}</td></tr>')
        return f'<table class="ck-t"><tbody>{"".join(out)}</tbody></table>'

    boards = []

    # Conviction — the payoff board
    if conv_rows:
        cr = ""
        for r in conv_rows[:7]:
            nk = (_near(r.get("gap_to_key_p3m")) or _near(r.get("gap_to_key_p6m"))
                  or _near(r.get("gap_to_key_p12m")))
            star = "★ " if (r.get("pt14_tier") and not r.get("pt14_dq")) else ""
            cr += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                   f'<span class="sym">{star}{esc(r["symbol"])}</span></a></td>'
                   f'<td class="l mut">{esc(r.get("primary_sector") or "—")}</td>'
                   f'<td class="r">{r.get("rs_rank") if r.get("rs_rank") is not None else "—"}</td>'
                   f'<td class="r">{"🎯" if nk else ""}</td></tr>')
        boards.append(_board('<span class="em">⭐</span> Conviction shortlist', 'all pillars aligned',
                             f'<table class="ck-t"><tbody>{cr}</tbody></table>',
                             "/dash/conviction", "See the full shortlist", "#d2a8ff"))

    # Top triggers — Positioning instrument
    if top_stocks:
        boards.append(_board('<span class="em">⚡</span> Top triggers', 'DVPT-vs-power ladder',
                             trig_rows(top_stocks), "/dash/stocks", "See all triggers", "#58a6ff"))

    # Sector rotation — RS heat strips
    if top_sectors:
        def sect_rows(rows):
            o = ""
            for r in rows:
                st = r["st"] or "—"
                wk, wr = sector_weather(r["s1"], r["s3"], r["s6"], r["s12"], r["st"])
                o += (f'<tr><td class="l"><a class="row" href="/dash/index?idx={q(r["nm"])}">'
                      f'<span class="sym">{esc(r["nm"])}</span></a></td>'
                      f'<td class="l">{D._rs_strip(r["s1"], r["s3"], r["s6"], r["s12"], r.get("s18"), r.get("s24"))}</td>'
                      f'<td>{_weather_badge(wk, wr)}</td>'
                      f'<td class="r">{pct(r["s3"])}</td></tr>')
            return o
        inner = ('<table class="ck-t"><tbody>' + sect_rows(top_sectors)
                 + '<tr><td colspan="4" class="mut" style="padding-top:8px;font-size:11px">WEAKEST</td></tr>'
                 + sect_rows(weak_sectors) + '</tbody></table>'
                 + '<div class="mut" style="font-size:11px;margin-top:6px">'
                   '<a class="row" style="display:inline" href="/dash/rrg">⟳ Rotation map (RRG) — quadrants &amp; tails</a></div>')
        boards.append(_board('<span class="em">📈</span> Sector rotation', 'RS vs Nifty 500 · 1m/3m/6m/12m/18m/24m',
                             inner, "/dash/sectors", "See full rotation", "var(--up)"))

    # Strong-in-strong leaders
    if lead_rows:
        lr = ""
        for r in lead_rows[:7]:
            lr += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                   f'<span class="sym">{esc(r["symbol"])}</span></a></td>'
                   f'<td class="l mut">{esc(r["primary_sector"] or "—")}</td>'
                   f'<td class="r">{r["rs_rank"] if r["rs_rank"] is not None else "—"}</td></tr>')
        boards.append(_board('<span class="em">🏆</span> Strong-in-strong', 'stock + sector both leading',
                             f'<table class="ck-t"><tbody>{lr}</tbody></table>',
                             "/dash/leaders", "Leaders &amp; laggards", "var(--up)"))

    # Stealth accumulation
    if stealth:
        def stealth_score(r):
            psc = r.get("psc") or 0
            tag = "SS" if psc >= 5 else "S" if psc == 4 else "A"
            return (f'<td><span class="pill p-{tag}">{psc}/5</span></td>'
                    f'<td class="r">{pct(r.get("pfh"))}</td>')
        boards.append(_board('<span class="em">🕵</span> Stealth accumulation', 'concentrated, still off the highs',
                             trig_rows(stealth, score_cell=stealth_score),
                             "/dash/strategies/stealth", "See the full screen", "#58a6ff"))

    # MEP — signed accumulation/distribution (descriptor; D62). Additive, Phase-A
    # placement (appended after the DVPT boards). SIGNED, so it can carry a
    # distribution-watch board DVPT structurally cannot.
    def mep_rows(rows):
        out = ""
        for r in rows:
            sc = r.get("sc")
            ph = r.get("ph")
            phv = ph if ph is not None else sc
            scol = "var(--up)" if (phv is not None and phv >= 0) else "var(--down)"
            dtxt = ("%+.2f" % sc) if sc is not None else "—"
            out += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                    f'<span class="sym">{esc(r["symbol"])}</span></a></td>'
                    f'<td class="l">{_mv_adbar(phv)}</td>'
                    f'<td class="l">{_mep_pill(r.get("phst"))}</td>'
                    f'<td class="r" style="color:{scol}" title="phase score (today {dtxt})">'
                    f'{phv:+.2f}</td></tr>')
        return f'<table class="ck-t"><tbody>{out}</tbody></table>'
    if mep_accum:
        boards.append(_board('<span class="em">📈</span> Net accumulation', 'signed pressure · MEP (descriptor)',
                             mep_rows(mep_accum), "/dash/mep?dir=accum", "Open the MEP screen", "#db61a2"))
    if mep_distrib:
        boards.append(_board('<span class="em">📉</span> Distribution watch', 'net selling pressure · MEP',
                             mep_rows(mep_distrib), "/dash/mep?dir=distrib", "Open the MEP screen", "#db61a2"))

    # RS Band (the level lens) — cheapest / richest sectors vs their own history.
    from src.web.rsband_view import band_home_inner          # additive; '' if band table empty
    _band_inner = band_home_inner()
    if _band_inner:
        boards.append(_board('<span class="em">📊</span> RS Band',
                             'cheap &harr; rich vs own history · level lens', _band_inner,
                             "/dash/rsband", "Open the band", "#d29922"))

    cockpit = '<div class="ckpt">' + "".join(boards) + '</div>'

    fresh = (f'<div class="sub" style="margin-top:6px">Stock signals <b>{sig_date or "—"}</b> · '
             f'Index signals <b>{idx_date or "—"}</b> · updated nightly 7:30 PM IST. '
             f'Every count above is a live lens — open it to screen.</div>')

    return _CKPT_CSS + search + banner + count_strip + cockpit + fresh


def _row_trends(v):
    """Attach the on-read ABS + REL verdicts + weather to an index_signals row
    dict (mutates + returns it). `is_broad` = no RS benchmark."""
    is_broad = v.get("bb") is None
    al, acss, asc = _abs_trend(v.get("a200"), v.get("pa50"), v.get("r3m"),
                               v.get("off52h"), v.get("abv52l"))
    v["abs_label"], v["abs_css"], v["abs_score"] = al, acss, asc
    if is_broad:
        v["rel_label"], v["rel_css"], v["weather"], v["wreasons"] = None, None, None, None
    else:
        rl, rcss = _rel_trend(v.get("st"), v.get("s1"), v.get("s3"), v.get("s6"), v.get("s12"))
        v["rel_label"], v["rel_css"] = rl, rcss
        v["weather"], v["wreasons"] = sector_weather(
            v.get("s1"), v.get("s3"), v.get("s6"), v.get("s12"), v.get("st"))
    v["mom"] = 0.6 * (v.get("s3") or 0.0) + 0.4 * (v.get("s6") or 0.0)
    return v


_MKT_COLS = (
    "g.index_name nm, g.ret_1d_pct r1d, g.ret_1m_pct r1m, g.ret_3m_pct r3m, "
    "g.pct_above_50d_avg pa50, g.pct_above_200d_avg a200, g.pct_off_52w_high off52h, "
    "g.pct_above_52w_low abv52l, g.rs_vs_broad_trend_state st, g.broad_benchmark bb, "
    "g.rs_vs_broad_slope_1m s1, g.rs_vs_broad_slope_3m s3, g.rs_vs_broad_slope_6m s6, "
    "g.rs_vs_broad_slope_12m s12, g.rs_vs_broad_slope_18m s18, g.rs_vs_broad_slope_24m s24, "
    "x.close_value close")


def render_markets(idx_date) -> str:
    """Full-bleed markets cockpit: a regime banner + breadth tiles, a momentum-
    ranked sector rotation strip (weather badges + both-trend pills), broad &
    sector cards, the full sortable+clickable index bundle, and a read-only
    latest-headlines card. Every index card/row → its /dash/index detail page."""
    from src.web import dashboard as D
    esc, pct, q, num = D._esc, D._pct, D._q, D._num

    allrows = {}
    breadth = nifty1d = None
    news = ""
    if idx_date:
        with D.get_conn() as conn:
            for r in conn.execute(
                f"SELECT {_MKT_COLS} FROM index_signals g "
                "LEFT JOIN index_rows x USING(index_name,trade_date) "
                "WHERE g.trade_date=?", (idx_date,)).fetchall():
                allrows[r["nm"]] = _row_trends(dict(r))
            b = conn.execute(
                "SELECT AVG(CASE WHEN pct_above_200d_avg>0 THEN 1.0 ELSE 0 END)*100 p "
                "FROM index_signals WHERE trade_date=? AND pct_above_200d_avg IS NOT NULL",
                (idx_date,)).fetchone()
            breadth = b["p"] if b and b["p"] is not None else None
            n = allrows.get("Nifty 50")
            nifty1d = n.get("r1d") if n else None
            news = _news_card(conn, esc)
    if not allrows:
        return _CKPT_CSS + '<div class="empty">No index data yet.</div>'

    # --- regime read (Nifty 50 absolute trend + breadth + sector RS + size) ---
    nifty = allrows.get("Nifty 50", {})
    n_abs = nifty.get("abs_label", "—")
    n_sc = nifty.get("abs_score", 0)
    real_present = [allrows[s] for s in D.REAL_SECTORS if s in allrows]
    rs_up_secs = sum(1 for v in real_present if v.get("st") in ("UPTREND", "BREAKOUT"))
    sect_rs_pct = (rs_up_secs / len(real_present) * 100) if real_present else None
    lead_idx = None
    best = -1e9
    for s in D.LEADERSHIP_SET:
        v = allrows.get(s)
        if v and v.get("r3m") is not None and v["r3m"] > best:
            best, lead_idx = v["r3m"], s
    lead_txt = {"Nifty 50": "Large-caps leading", "Nifty Midcap 150": "Mid-caps leading",
                "Nifty Smallcap 250": "Small-caps leading"}.get(lead_idx, lead_idx or "—")
    bcls = "b-on" if n_sc >= 2 else ("b-off" if n_sc == 0 else "b-neu")
    breadth_txt = f"{breadth:.0f}%" if breadth is not None else "—"
    sect_txt = f"{sect_rs_pct:.0f}%" if sect_rs_pct is not None else "—"
    banner = (f'<div class="banner {bcls}" style="font-size:15px">Nifty 50 · {esc(n_abs)}'
              f'<small>· 1d {pct(nifty1d)} · {breadth_txt} of indices &gt; 200-DMA '
              f'· {sect_txt} of sectors in RS uptrend · {esc(lead_txt)}</small></div>')

    hdr = ('<div class="ck-tiles" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">'
           f'<div class="ck-tile" style="border-top:3px solid #58a6ff"><div class="ck-n">{pct(nifty1d)}</div>'
           f'<div class="ck-l">Nifty 50 · today</div>'
           f'<div class="ck-c"><span class="pill p-{nifty.get("abs_css","C")}">{esc(n_abs)}</span></div></div>'
           f'<div class="ck-tile" style="border-top:3px solid var(--up)"><div class="ck-n">{breadth_txt}</div>'
           f'<div class="ck-l">indices &gt; 200-DMA</div><div class="ck-c">absolute price breadth</div></div>'
           f'<div class="ck-tile" style="border-top:3px solid var(--up)"><div class="ck-n" style="color:var(--up)">{sect_txt}</div>'
           f'<div class="ck-l">sectors in RS uptrend</div><div class="ck-c">vs Nifty 500</div></div>'
           f'<div class="ck-tile" style="border-top:3px solid #d2a8ff"><div class="ck-n" style="font-size:15px;padding-top:7px">{esc(lead_txt)}</div>'
           f'<div class="ck-l">size leadership</div><div class="ck-c">by 3m return</div></div></div>')

    def maj_card(v):
        bits = [f'<span class="pill p-{v["abs_css"]}">{esc(v["abs_label"])}</span>']
        if v.get("weather"):  # sectors only (broad indices have no RS/weather)
            bits.append(_weather_badge(v["weather"], v.get("wreasons")))
        strip = D._rs_strip(v["s1"], v["s3"], v["s6"], v["s12"], v.get("s18"), v.get("s24"))
        rel = (f'<span class="pill p-{v["rel_css"]}" style="margin-left:6px">{esc(v["rel_label"])}</span>'
               if v.get("rel_label") else '')
        return (f'<a class="maj" href="/dash/index?idx={q(v["nm"])}">'
                f'<div class="nm">{esc(v["nm"])} {" ".join(bits)}</div>'
                f'<div class="rr"><span class="mut">PRICE</span><span>{num(v["close"],0)}</span>'
                f'<span>1d {pct(v["r1d"])}</span><span>1m {pct(v["r1m"])}</span>'
                f'<span>3m {pct(v["r3m"])}</span></div>'
                f'<div class="rr"><span class="grp">RS</span>{strip}{rel}</div></a>')

    # Momentum-ranked sector rotation strip (real sectors, strongest first).
    rot = sorted(real_present, key=lambda v: -(v.get("mom") or -1e9))
    rot_html = "".join(maj_card(v) for v in rot[:8])
    broad_html = "".join(maj_card(allrows[n]) for n in D.MAJOR_BROAD if n in allrows)

    # Group the bundle by SIZE membership, not by `bb` — cap-segment size indexes
    # (Smallcap 250, the Midcaps, Next 50, …) now carry an RS benchmark but still
    # belong under "Broad / size", not "Sectoral" (D67).
    from src.automation.index_signals import SIZE_BASED_INDEX_NAMES as _SIZE_NAMES
    bundle = sorted(allrows.values(), key=lambda v: (v["r3m"] is None, -(v["r3m"] or 0)))
    brows = []
    for v in bundle:
        grp = "broad" if (v["nm"] or "").upper() in _SIZE_NAMES else "sector"
        st = v["st"] or ""
        rs_chip = (f'<span class="pill p-{st}">{_state_label(st)}</span>' if st else '<span class="mut">—</span>')
        abs_chip = f'<span class="pill p-{v["abs_css"]}">{esc(v["abs_label"])}</span>'
        wx = _weather_badge(v["weather"], v.get("wreasons")) if v.get("weather") else '<span class="mut">—</span>'
        brows.append(
            f'<tr data-grp="{grp}"><td class="sym"><a class="row" style="display:inline" '
            f'href="/dash/index?idx={q(v["nm"])}">{esc(v["nm"])}</a></td>'
            f'<td class="num">{pct(v["r1d"])}</td><td class="num">{pct(v["r1m"])}</td>'
            f'<td class="num">{pct(v["r3m"])}</td>'
            f'<td>{D._rs_strip(v["s1"], v["s3"], v["s6"], v["s12"], v.get("s18"), v.get("s24"))}</td>'
            f'<td>{abs_chip}</td><td>{rs_chip}</td><td>{wx}</td></tr>')
    js = ("<script>function mflt(g,el){document.querySelectorAll('#mbundle tr[data-grp]').forEach("
          "function(r){r.style.display=(g==='all'||r.dataset.grp===g)?'':'none';});"
          "document.querySelectorAll('#mbar .fbtn').forEach(function(b){b.classList.remove('on');});"
          "el.classList.add('on');}</script>")

    # Dedicated "Rotation" card cluster — the rotation family as first-class tiles
    # (RS Rotation was an orphan route; RRG/Sectors were only inline links). Pure
    # links, reuses .ck-tile styling. Additive; nothing existing removed.
    rotation_cards = (
        '<div class="ghdr" style="margin-top:12px">Rotation</div>'
        '<div class="ck-tiles" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">'
        '<a class="ck-tile" style="border-top:3px solid #79c0ff" href="/dash/rotation">'
        '<div class="ck-n" style="font-size:16px;line-height:1.2;padding-top:6px">🌅 RS Rotation</div>'
        '<div class="ck-l">stocks × sectors · 4-phase weather</div>'
        '<div class="ck-c">Recovery · Tailwind · Rolling-over · Headwind</div></a>'
        '<a class="ck-tile" style="border-top:3px solid #58a6ff" href="/dash/rrg">'
        '<div class="ck-n" style="font-size:16px;line-height:1.2;padding-top:6px">⟳ RRG map</div>'
        '<div class="ck-l">sector relative-rotation graph</div>'
        '<div class="ck-c">RS-Ratio × RS-Momentum + tails</div></a>'
        '<a class="ck-tile" style="border-top:3px solid var(--up)" href="/dash/sectors">'
        '<div class="ck-n" style="font-size:16px;line-height:1.2;padding-top:6px">📈 Sector Rotation</div>'
        '<div class="ck-l">RS heat per sector · sortable</div>'
        '<div class="ck-c">vs Nifty 500 · 1m/3m/6m/12m/18m/24m</div></a>'
        '<a class="ck-tile" style="border-top:3px solid #d29922" href="/dash/rsband">'
        '<div class="ck-n" style="font-size:16px;line-height:1.2;padding-top:6px">📊 RS Band</div>'
        '<div class="ck-l">support ↔ resistance per sector</div>'
        '<div class="ck-c">cheap vs rich vs its own history · the level lens</div></a>'
        '</div>')

    return (_CKPT_CSS
            + '<h2 style="margin-top:2px">Markets <span class="sub" style="margin:0">regime · indexes · sectors</span></h2>'
            + banner + hdr + rotation_cards
            + '<div class="sub" style="margin-top:2px">Tap any index → its full detail page: '
              'price trend, relative strength, valuation &amp; constituent roll-up. '
              '<a class="row" style="display:inline" href="/dash/compare?idx=Nifty+50&idx=Nifty+500">⇄ Compare indices</a> · '
              '<a class="row" style="display:inline" href="/dash/rrg">⟳ Rotation map (RRG)</a></div>'
            + '<div class="ghdr">Sector rotation · strongest momentum first (0.6·3m + 0.4·6m RS)</div>'
            + f'<div class="mkt-grid">{rot_html}</div>'
            + '<div class="ghdr">Broad / size</div>'
            + f'<div class="mkt-grid">{broad_html}</div>'
            + '<h2>Full index bundle <span class="sub" style="margin:0">price trend + RS heat per index · sortable</span></h2>'
            + '<div id="mbar" class="fbar">'
              "<button class=\"fbtn on\" onclick=\"mflt('all',this)\">All</button>"
              "<button class=\"fbtn\" onclick=\"mflt('broad',this)\">Broad/Size</button>"
              "<button class=\"fbtn\" onclick=\"mflt('sector',this)\">Sectoral</button></div>"
            + '<div class="card" style="padding:6px 10px"><table id="mbundle" class="dt" style="font-size:12.5px">'
              '<thead><tr><th class="l">Index</th><th class="num">1d</th><th class="num">1m</th>'
              '<th class="num">3m</th><th class="l">RS 1m/3m/6m/12m/18m/24m</th><th>Price trend</th>'
              '<th>RS trend</th><th>Weather</th></tr></thead>'
            + f'<tbody>{"".join(brows)}</tbody></table></div>' + js
            + ('<h2>Latest headlines <span class="sub" style="margin:0">market-wide</span></h2>'
               + '<div class="mkt-grid" style="grid-template-columns:1fr">' + news + '</div>' if news else ''))


def _idx_median(xs):
    if not xs:
        return None
    xs = sorted(xs)
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2.0


def render_index_detail(idx, idx_date, sig_date) -> str:
    """Full-bleed single-index analytics page (/dash/index). Branches broad vs
    sector on broad_benchmark. The headline is a TWO-AXIS verdict — the ABSOLUTE
    price trend (derived on-read from the index's own 50/200-DMA + 3m return + 52w
    position) shown BESIDE the existing RS trend — which fixes "trends not properly
    identified". Adds the own-price chart, returns/MA/52w/valuation, and the
    EQUAL-WEIGHT bottom-up constituent roll-up. Deterministic, zero-LLM."""
    from src.web import dashboard as D
    esc, pct, q, num = D._esc, D._pct, D._q, D._num
    idx = (idx or "").strip()
    if not idx:
        return _CKPT_CSS + '<div class="empty">No index selected. Reach this from Markets or Sectors.</div>'

    S, IR, hist, pe_hist, momrows, members, rd = {}, {}, [], [], [], [], []
    rsx, cap, n5 = {}, {}, {}
    quad_tail = []
    with D.get_conn() as conn:
        known = conn.execute("SELECT 1 FROM index_rows WHERE index_name=? LIMIT 1", (idx,)).fetchone()
        if not known:
            return _CKPT_CSS + f'<div class="empty">Unknown index <b>{esc(idx)}</b>.</div>'
        sig = conn.execute(
            "SELECT close_value iclose, broad_benchmark bb, rs_vs_broad_trend_state st, "
            "ret_1d_pct r1d, ret_1w_pct r1w, ret_1m_pct r1m, ret_3m_pct r3m, ret_6m_pct r6m, "
            "ret_12m_pct r12m, pct_above_50d_avg pa50, pct_above_200d_avg a200, "
            "pct_off_52w_high off52h, pct_above_52w_low abv52l, rs_vs_broad_today rs, "
            "rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3, rs_vs_broad_slope_6m s6, "
            "rs_vs_broad_slope_12m s12, rs_vs_broad_slope_18m s18, rs_vs_broad_slope_24m s24, "
            "rs_vs_broad_above_50ma a50, rs_vs_broad_above_200ma a200ma, "
            "rs_vs_broad_new_52w_high nh FROM index_signals WHERE index_name=? "
            "ORDER BY trade_date DESC LIMIT 1", (idx,)).fetchone()
        S = dict(sig) if sig else {}
        irow = conn.execute(
            "SELECT open_value o, high_value h, low_value l, close_value close, points_change pts, "
            "change_pct chg, volume vol, turnover_cr tov, pe, pb, dividend_yield dy, trade_date td "
            "FROM index_rows WHERE index_name=? ORDER BY trade_date DESC LIMIT 1", (idx,)).fetchone()
        IR = dict(irow) if irow else {}
        hist = [dict(r) for r in conn.execute(
            "SELECT trade_date t, open_value o, high_value h, low_value l, close_value c "
            "FROM index_rows WHERE index_name=? AND close_value IS NOT NULL "
            "ORDER BY trade_date ASC", (idx,)).fetchall()]
        pe_hist = [r["pe"] for r in conn.execute(
            "SELECT pe FROM index_rows WHERE index_name=? AND pe IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT 252", (idx,)).fetchall()]
        momrows = [r["mom"] for r in conn.execute(
            "WITH latest AS (SELECT MAX(trade_date) d FROM index_signals) "
            "SELECT (0.6*COALESCE(rs_vs_broad_slope_3m,0)+0.4*COALESCE(rs_vs_broad_slope_6m,0)) mom "
            "FROM index_signals, latest WHERE trade_date=latest.d AND broad_benchmark IS NOT NULL").fetchall()]
        # Mini-RRG tail: this index's RS-Ratio × RS-Momentum journey vs Nifty 500 —
        # the canonical rotation space the depth panel's "Quadrant" and /dash/rrg use
        # (improving → leading → weakening → lagging). ~6 months daily, sampled at
        # render. Empty (→ graceful empty-state) until enough ratio history exists.
        from src.automation import rrg as _rrg
        quad_tail = _rrg.tail(idx, "Nifty 500", n=130, conn=conn)
        syms = D._sector_symbols(conn, idx)
        if syms and sig_date:
            ph = ",".join("?" for _ in syms)
            members = [dict(r) for r in conn.execute(
                f"SELECT s.symbol, s.rs_rank, s.rs_vs_broad_trend_state st, s.accum_character ch, "
                f"s.is_ath_dvpt ath, s.pct_from_52w_high pfh, s.p_score, s.trigger_rank rank, "
                f"s.delivery_value_today dvt, s.delivery_value_per_trade dvpt, s.power_dvpt_1m p1, "
                f"s.power_dvpt_2m p2, s.power_dvpt_3m p3, s.power_dvpt_6m p6, s.power_dvpt_12m p12, "
                f"s.price_vs_hot_avg_pct pvh, s.primary_sector sec, b.close cmp, b.prev_close pc, "
                f"m.mep_score mep, m.mep_state mst "
                f"FROM stock_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
                f"LEFT JOIN mep_signals m ON (m.symbol=s.symbol AND m.trade_date=s.trade_date) "
                f"WHERE s.trade_date=? AND s.symbol IN ({ph}) {D._SCAN_FILTERS}",
                (sig_date, *syms)).fetchall()]
        # RS-ratio curve (index ÷ Nifty 500) — the chart Ramana reviews; the
        # cockpit page is the superset of the old /dash/ratio. Empty for broad/size
        # indices (no ratio vs themselves), which simply hides the ratio chart.
        for r in conn.execute(
                "SELECT trade_date t, ratio FROM ratio_rows "
                "WHERE numerator=? AND denominator='Nifty 500' AND ratio IS NOT NULL "
                "ORDER BY trade_date ASC", (idx,)).fetchall():
            rd.append({"t": r["t"], "r": round(r["ratio"], 4)})
        # RS-DEPTH (the RRG / Mansfield / capture work — covers SIZE indices too, which
        # have no ratio series). Latest row, preferring vs Nifty 500 then Nifty 50.
        try:
            for den in ("Nifty 500", "Nifty 50"):
                x = conn.execute(
                    "SELECT rs_momentum, quadrant, mansfield, rsi_of_rs, improving_entry, "
                    "weakening_warning FROM rs_extras WHERE numerator=? AND denominator=? "
                    "ORDER BY trade_date DESC LIMIT 1", (idx, den)).fetchone()
                if x:
                    rsx = dict(x)
                    rsx["den"] = den
                    c = conn.execute(
                        "SELECT down_capture_252 dc, up_capture_252 uc FROM capture_signals "
                        "WHERE numerator=? AND denominator=? ORDER BY trade_date DESC LIMIT 1",
                        (idx, den)).fetchone()
                    cap = dict(c) if c else {}
                    break
        except Exception:
            rsx, cap = {}, {}
        # Nifty 500 returns — the broad benchmark, for the size-index RS read.
        n5r = conn.execute("SELECT ret_1m_pct r1m, ret_3m_pct r3m, ret_6m_pct r6m, ret_12m_pct r12m "
                           "FROM index_signals WHERE index_name='Nifty 500' "
                           "ORDER BY trade_date DESC LIMIT 1").fetchone()
        n5 = dict(n5r) if n5r else {}

    is_broad = S.get("bb") is None

    # --- roll-up stats (EQUAL-WEIGHT — membership carries no weight_pct) -------
    N = len(members)
    rs_ranks = [m["rs_rank"] for m in members if m.get("rs_rank") is not None]
    n_up = sum(1 for m in members if m.get("st") in ("UPTREND", "BREAKOUT"))
    breadth_pct = (n_up / N * 100) if N else None
    n_leaders = sum(1 for m in members if (m.get("rs_rank") or 0) >= 80)
    avg_rs = (sum(rs_ranks) / len(rs_ranks)) if rs_ranks else None
    med_rs = _idx_median(rs_ranks)
    n_acc = sum(1 for m in members if m.get("ch") == "ACCUMULATION")
    n_dist = sum(1 for m in members if m.get("ch") == "DISTRIBUTION")
    n_cons = sum(1 for m in members if m.get("ch") == "CONSOLIDATION")
    n_neu = sum(1 for m in members if m.get("ch") == "NEUTRAL")
    n_near = sum(1 for m in members if m.get("pfh") is not None and m["pfh"] >= -5)
    n_ath = sum(1 for m in members if m.get("ath"))
    accum_skew = n_acc - n_dist

    # --- the two-axis verdict -------------------------------------------------
    al, acss, asc = _abs_trend(S.get("a200"), S.get("pa50"),
                               S.get("r3m"), S.get("off52h"), S.get("abv52l"))
    rl, rcss = (None, None) if is_broad else _rel_trend(
        S.get("st"), S.get("s1"), S.get("s3"), S.get("s6"), S.get("s12"))
    verdict = _index_verdict(is_broad, al, asc, rl)
    if is_broad:
        weather, wreasons = None, None
    else:
        weather, wreasons = sector_weather(S.get("s1"), S.get("s3"), S.get("s6"), S.get("s12"),
                                           S.get("st"), breadth=breadth_pct, accum_skew=accum_skew)
    if al == "NEAR HIGH":
        bcls = "b-on"
    elif al == "NEAR LOW":
        bcls = "b-off"
    else:
        bcls = "b-on" if asc >= 2 else ("b-off" if asc == 0 else "b-neu")

    abs_pill = f'<span class="pill p-{acss}">PRICE: {esc(al)}</span>'
    rel_pill = f'<span class="pill p-{rcss}">RS: {esc(rl)}</span>' if rl else ''
    wbadge = _weather_badge(weather, wreasons) if (not is_broad and weather) else ''
    raw = (f'{pct(S.get("pa50"))} vs 50-DMA · {pct(S.get("a200"))} vs 200-DMA · '
           f'3m ret {pct(S.get("r3m"))} · {pct(S.get("off52h"))} off 52w-high · '
           f'{pct(S.get("abv52l"))} above 52w-low')
    kind = "broad / size index" if is_broad else "sector"
    head = (f'<h2 style="margin-top:2px">{esc(idx)} '
            f'<span class="sub" style="margin:0">{kind} · {esc(IR.get("td") or idx_date or "")}</span></h2>')
    banner = (f'<div class="banner {bcls}" style="font-size:16px">{esc(verdict)}'
              f'<small>{abs_pill} {rel_pill} {wbadge}</small></div>'
              f'<div class="sub" style="margin-top:-6px">{raw}'
              + ('' if is_broad else ' &nbsp;<span class="mut">PRICE = its own trend · '
                 'RS = vs Nifty 500 — the two can disagree.</span>') + '</div>')

    # --- own-price OHLC (candles/line; MAs computed client-side per interval) ---
    cd = []
    for r in hist:
        c = r["c"]
        if c is None:
            continue
        o = r["o"] if r["o"] is not None else c
        hi = r["h"] if r["h"] is not None else c
        lo = r["l"] if r["l"] is not None else c
        cd.append({"t": r["t"], "o": round(o, 2), "h": round(hi, 2),
                   "l": round(lo, 2), "c": round(c, 2)})
    chart_css = ("<style>.rangebar{display:flex;gap:6px;margin:8px 0 4px;}"
                 ".rangebar button{background:var(--bg-3);color:var(--ink);border:1px solid var(--line-2);"
                 "border-radius:6px;padding:4px 12px;font-size:12px;cursor:pointer;}"
                 ".rangebar button.on{background:#1f6feb;border-color:#1f6feb;color:#fff;}"
                 ".chartwrap{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;"
                 "padding:8px;margin-bottom:6px;}.chartlbl{color:var(--ink-2);font-size:11px;"
                 "text-transform:uppercase;letter-spacing:.4px;margin:2px 4px 4px;}</style>")
    chart_html = ""
    if cd:
        chart_html = (
            '<h2>Price <span class="sub" style="margin:0">candles / line · D·W·M·Q · 50/200-MA</span></h2>'
            '<div class="fbar" id="idxPriceType"><button class="fbtn on" data-itype="candle">Candles</button>'
            '<button class="fbtn" data-itype="line">Line</button></div>'
            '<div class="fbar" id="idxPriceTf"><button class="fbtn on" data-itf="d">Daily</button>'
            '<button class="fbtn" data-itf="w">Weekly</button><button class="fbtn" data-itf="m">Monthly</button>'
            '<button class="fbtn" data-itf="q">Quarterly</button></div>'
            '<div class="rangebar" id="idxPriceRange"><button data-r="63">3M</button>'
            '<button data-r="126">6M</button><button data-r="252" class="on">1Y</button>'
            '<button data-r="504">2Y</button><button data-r="1260">5Y</button><button data-r="0">Max</button></div>'
            f'<div class="chartwrap"><div class="chartlbl">{esc(idx)} · price (candles / line) + 50/200-MA</div>'
            '<div id="idxRdt" style="font-size:12px;color:var(--ink);font-variant-numeric:tabular-nums;'
            'min-height:16px;margin:2px 0 3px"></div><div id="idxChart" style="height:320px"></div></div>')

    # --- today snapshot: KPI + OHLC/valuation + returns + technicals ----------
    def _v(x, d=2, suf=""):
        return f"{x:,.{d}f}{suf}" if x is not None else "—"
    iclose = IR.get("close") if IR.get("close") is not None else S.get("iclose")
    pts = IR.get("pts")
    kpi = ('<div class="kpi">'
           f'<div class="box"><div class="num">{_v(iclose, 2)}</div>'
           f'<div class="lbl">close{(" " + ("%+.0f" % pts)) if pts is not None else ""}</div></div>'
           f'<div class="box"><div class="num">{pct(IR.get("chg"))}</div><div class="lbl">today</div></div>'
           f'<div class="box"><div class="num" style="font-size:18px;padding-top:6px">{pct(S.get("r1m"))}</div>'
           f'<div class="lbl">1m return</div></div></div>')
    pe_today = IR.get("pe")
    val_pctl = None
    if pe_today is not None and pe_hist:
        below = sum(1 for x in pe_hist if x < pe_today)
        val_pctl = round(below / len(pe_hist) * 100)
    val_txt = (f' · <span class="mut">{val_pctl}th pctile of {len(pe_hist)}d (higher = richer)</span>'
               if val_pctl is not None else '')
    # Actual MA + 52-week LEVELS (data-first — the % beside the level, not %-only).
    _cl = [d["c"] for d in cd]
    dma50 = (sum(_cl[-50:]) / 50) if len(_cl) >= 50 else None
    dma200 = (sum(_cl[-200:]) / 200) if len(_cl) >= 200 else None
    _o52, _a52 = S.get("off52h"), S.get("abv52l")
    hi52 = (iclose / (1 + _o52 / 100.0)) if (iclose and _o52 is not None) else None
    lo52 = (iclose / (1 + _a52 / 100.0)) if (iclose and _a52 is not None) else None
    stats = ('<div class="card" style="padding:6px 10px"><table><tbody>'
             f'<tr><td class="mut">Open</td><td>{_v(IR.get("o"))}</td>'
             f'<td class="mut">High</td><td>{_v(IR.get("h"))}</td>'
             f'<td class="mut">Low</td><td>{_v(IR.get("l"))}</td></tr>'
             f'<tr><td class="mut">Volume</td><td>{_v(IR.get("vol"), 0)}</td>'
             f'<td class="mut">Turnover</td><td>{("₹" + _v(IR.get("tov"), 0) + " Cr") if IR.get("tov") is not None else "—"}</td>'
             f'<td class="mut">Div yld</td><td>{_v(IR.get("dy"), 2, "%")}</td></tr>'
             f'<tr><td class="mut">P/E</td><td>{_v(pe_today)}{val_txt}</td>'
             f'<td class="mut">P/B</td><td>{_v(IR.get("pb"))}</td>'
             f'<td class="mut">50-DMA</td><td>{_v(dma50)} <span class="mut">({pct(S.get("pa50"))})</span></td></tr>'
             f'<tr><td class="mut">200-DMA</td><td>{_v(dma200)} <span class="mut">({pct(S.get("a200"))})</span></td>'
             f'<td class="mut">52w high</td><td>{_v(hi52)} <span class="mut">({pct(_o52)})</span></td>'
             f'<td class="mut">52w low</td><td>{_v(lo52)} <span class="mut">({pct(_a52)})</span></td></tr>'
             '</tbody></table></div>')
    rets = " · ".join(f'{lbl} {pct(S.get(k))}' for lbl, k in
                      (("1d", "r1d"), ("1w", "r1w"), ("1m", "r1m"),
                       ("3m", "r3m"), ("6m", "r6m"), ("12m", "r12m")))
    snapshot = (kpi + stats
                + f'<div class="sub" style="margin:6px 0 10px"><b>Returns</b> &nbsp;{rets}</div>')

    # --- relative strength: ratio chart (sectors) + RS-DEPTH for EVERY index
    # (incl. SIZE indices, which have no ratio series but DO carry the RRG /
    # Mansfield / capture work) + a link to the full RRG. ----------------------
    rs_block = ""
    rsdepth = ""
    if rsx:
        def _sg(v, suf="", d=2):
            return (f"{v:+.{d}f}{suf}" if isinstance(v, (int, float)) else '<span class="mut">—</span>')
        flagbits = []
        if rsx.get("improving_entry"):
            flagbits.append('<span class="pos">improving ▲</span>')
        if rsx.get("weakening_warning"):
            flagbits.append('<span class="neg">weakening ▼</span>')
        rsdepth = (
            '<div class="card"><div class="ck-h">RS depth '
            f'<span class="sub" style="margin:0;font-weight:400">vs {esc(rsx.get("den") or "Nifty 500")} · RRG / Mansfield / capture</span></div>'
            '<table><tbody>'
            f'<tr><td class="mut">Quadrant</td><td><b>{esc(rsx.get("quadrant") or "—")}</b></td>'
            f'<td class="mut">RS momentum</td><td>{_sg(rsx.get("rs_momentum"))}</td></tr>'
            f'<tr><td class="mut">Mansfield RS</td><td>{_sg(rsx.get("mansfield"))}</td>'
            f'<td class="mut">RSI-of-RS</td><td>{_sg(rsx.get("rsi_of_rs"), "", 0)}</td></tr>'
            f'<tr><td class="mut">Up-capture 1y</td><td>{_sg(cap.get("uc"), "%", 0)}</td>'
            f'<td class="mut">Down-capture 1y</td><td>{_sg(cap.get("dc"), "%", 0)}</td></tr>'
            '</tbody></table>'
            + (f'<div class="sub" style="margin:6px 0 0">{" · ".join(flagbits)}</div>' if flagbits else '')
            + '<a class="more" href="/dash/rrg">Full Relative Rotation Graph &amp; RS-depth table &#8594;</a></div>')

    if not is_broad:
        s3 = S.get("s3")
        # Mini-RRG: this index's RS-Ratio × RS-Momentum rotation journey vs Nifty 500
        # — the SAME canonical quadrants (improving → leading → weakening → lagging) as
        # the RS-depth panel below and the full /dash/rrg, so the page speaks one
        # rotation language (D68). Tail pre-fetched in the data block.
        from src.web.mini_rrg import mini_rrg_card
        quad = mini_rrg_card(quad_tail, den="Nifty 500", tail_label="last ~6 months", size=280)
        my_mom = 0.6 * (s3 or 0) + 0.4 * (S.get("s6") or 0)
        moms = sorted(momrows)
        pctl = 50
        if moms:
            below = sum(1 for m in moms if m < my_mom)
            pctl = max(1, min(99, round(below / len(moms) * 99)))
        # dense: the RANK is the hero (big number), the bar is a compact support strip —
        # not a thin bar lost in an empty card (space ∝ importance).
        gauge = (f'<div class="card" style="display:flex;align-items:center;gap:12px">'
                 f'<div style="font-size:28px;font-weight:700;line-height:1;white-space:nowrap">{pctl}'
                 f'<span class="sub" style="margin:0;font-size:14px">/99</span></div>'
                 f'<div style="flex:1;min-width:0">'
                 f'<div class="bar" style="margin:0 0 4px"><span style="width:{pctl}%"></span></div>'
                 f'<div class="sub" style="margin:0;font-size:11px;line-height:1.3">RS momentum — stronger than '
                 f'{pctl}% of {len(moms)} sectors (0.6·3m + 0.4·6m slope)</div></div></div>')
        rs_strip = D._rs_strip(S.get("s1"), S.get("s3"), S.get("s6"), S.get("s12"), S.get("s18"), S.get("s24"))
        if rd:
            ratio_chart = (
                '<div class="fbar" id="idxRatioTf"><button class="fbtn on" data-itf="d">Daily</button>'
                '<button class="fbtn" data-itf="w">Weekly</button><button class="fbtn" data-itf="m">Monthly</button>'
                '<button class="fbtn" data-itf="q">Quarterly</button></div>'
                '<div class="rangebar" id="idxRatioRange"><button data-r="63">3M</button>'
                '<button data-r="126">6M</button><button data-r="252" class="on">1Y</button>'
                '<button data-r="504">2Y</button><button data-r="1260">5Y</button>'
                '<button data-r="0">Max</button></div>'
                f'<div class="chartwrap"><div class="chartlbl">{esc(idx)} ÷ Nifty 500 — relative-strength ratio (line) '
                '· amber=50-MA · grey=200-MA · ↑/↓50 crosses · ● new high (per interval)</div>'
                '<div id="idxRatioRdt" style="font-size:12px;color:var(--ink);font-variant-numeric:tabular-nums;'
                'min-height:16px;margin:2px 0 3px"></div><div id="idxRatioChart" style="height:280px"></div></div>')
        else:
            ratio_chart = ('<div class="card" style="max-width:560px"><div class="sub" style="margin:0">No RS-ratio series on record '
                           'for this index yet.</div></div>')
        rs_block = (
            '<h2>Relative strength <span class="sub" style="margin:0">vs Nifty 500 · the RS-ratio chart</span></h2>'
            f'<div class="sub" style="margin-bottom:6px">{rs_strip} &nbsp; '
            f'3m RS slope {pct(s3)} · trend <span class="pill p-{rcss or "C"}">{esc(rl or "—")}</span>. '
            f'<a class="row" style="display:inline" href="/dash/ratio?idx={q(idx)}">Standalone ratio page (also vs Nifty 50) &#8594;</a>'
            f' &nbsp;·&nbsp; <a class="row" style="display:inline" href="/dash/compare?idx={q(idx)}&idx=Nifty+500">⇄ Compare (rebased) vs Nifty 500</a></div>'
            + ratio_chart
            # 2-col: the (tall) rotation mini beside a STACK of momentum + depth so the
            # column heights balance — kills the dead space the old 3-equal-col grid left
            # under the two short cards. Width-capped so nothing stretches; wraps on mobile.
            + '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start;margin-bottom:14px">'
            + f'<div style="flex:1 1 300px;max-width:400px">{quad}</div>'
            + '<div style="flex:1 1 340px;max-width:520px;display:flex;flex-direction:column;gap:12px">'
            + gauge + rsdepth + '</div></div>')
    elif idx != "Nifty 500":
        # SIZE / broad index (e.g. Midcap 150, Smallcap 250, Next 50, Nifty 50) — no
        # single ratio-line series, so its relative strength = its return vs the broad
        # market (Nifty 500), per window, computed directly. Plus the Compare chart +
        # the full RRG, and the RS-depth panel when this exact index is in the RRG data.
        def _rsrow(lbl, k):
            iv, bv = S.get(k), n5.get(k)
            diff = (iv - bv) if (iv is not None and bv is not None) else None
            return (f'<tr><td class="mut">{lbl}</td><td class="r">{pct(iv)}</td>'
                    f'<td class="r">{pct(bv)}</td><td class="r"><b>{pct(diff)}</b></td></tr>')
        rstab = ('<div class="card" style="padding:6px 10px"><table><thead><tr><th></th>'
                 f'<th class="r">{esc(idx)}</th><th class="r">Nifty 500</th><th class="r">RS = outperf.</th>'
                 '</tr></thead><tbody>'
                 + _rsrow("1m", "r1m") + _rsrow("3m", "r3m") + _rsrow("6m", "r6m") + _rsrow("12m", "r12m")
                 + '</tbody></table></div>')
        links = (f'<a class="row" style="display:inline" href="/dash/compare?idx={q(idx)}&idx=Nifty+500">'
                 '⇄ Compare (rebased) vs Nifty 500</a> &nbsp;·&nbsp; '
                 '<a class="row" style="display:inline" href="/dash/rrg">Full RRG &amp; rotation &#8594;</a>')
        rs_block = (
            '<h2>Relative strength <span class="sub" style="margin:0">vs Nifty 500</span></h2>'
            '<div class="sub" style="margin-bottom:6px">How this index has done <b>relative to the broad '
            f'market</b> (its return minus Nifty 500\'s, per window). {links}</div>' + rstab
            + (('<div class="mkt-grid" style="grid-template-columns:repeat(auto-fit,minmax(240px,1fr))">'
                + rsdepth + '</div>') if rsdepth else ''))

    # --- bottom-up constituent roll-up (EQUAL-WEIGHT) -------------------------
    rollup = ""
    if N:
        breadth_txt = f"{breadth_pct:.0f}%" if breadth_pct is not None else "—"
        avg_txt = f"{avg_rs:.0f}" if avg_rs is not None else "—"
        med_txt = f"{med_rs:.0f}" if med_rs is not None else "—"
        tiles = _ck_strip([
            _ck_tile(N, "Constituents", "#58a6ff", "equal-weight roll-up"),
            _ck_tile(breadth_txt, "In RS uptrend", "var(--up)", "members RS-up vs Nifty 500"),
            _ck_tile(n_leaders, "RS leaders", "var(--up)", "rs_rank ≥ 80"),
            _ck_tile(avg_txt, "Avg RS rank", "#d2a8ff", f"median {med_txt}"),
            _ck_tile(n_near, "Near 52w-high", "#d29922", "within 5%"),
            _ck_tile(n_ath, "ATH-DVPT", "#f0883e", "all-time delivery peak"),
        ])
        tot_ch = n_acc + n_dist + n_cons + n_neu
        if tot_ch:
            def _seg(n, col):
                w = n / tot_ch * 100
                return f'<span style="width:{w:.1f}%;background:{col}"></span>' if n else ''
            bar = ('<div style="display:flex;height:12px;border-radius:6px;overflow:hidden;'
                   'margin:2px 0 6px;background:var(--bg-3)">'
                   + _seg(n_acc, "var(--up)") + _seg(n_cons, "#bb8009")
                   + _seg(n_neu, "#484f58") + _seg(n_dist, "var(--down)") + '</div>')
            split = (f'<div class="card"><div class="ck-h">Accumulation split'
                     '<span class="sub" style="margin:0;font-weight:400">delivery character across members</span></div>'
                     + bar +
                     f'<div class="sub" style="margin:0">🟢 {n_acc} accumulation · 🟡 {n_cons} consolidation · '
                     f'⚪ {n_neu} neutral · 🔴 {n_dist} distribution · net skew '
                     f'<b>{accum_skew:+d}</b></div></div>')
        else:
            split = ""
        drill = (f'<a class="row" style="display:inline" href="/dash/stocks?sector={q(idx)}">'
                 f'See all {N} constituent stocks &#8594;</a>')
        # FULL sortable PARTICIPANTS table — every liquid member (the constituents
        # Ramana asked to see, incl. for size indices like Midcap/Smallcap), not a
        # top-8. Now carries Themes chips + signed-MEP PER MEMBER + an "accumulating
        # only" filter, via the shared _participants_table (also used by /dash/theme).
        sorted_members = sorted(members, key=lambda mm: (mm.get("rs_rank") is None, -(mm.get("rs_rank") or 0)))
        from src.automation import theme_tags as TT
        with D.get_conn() as _tc:
            mtags = TT.approved_tags_for(_tc, [m["symbol"] for m in sorted_members])
        # theme breakdown — which themes are most represented inside this index
        tb_counts = {}
        for _labs in mtags.values():
            for _lab in _labs:
                tb_counts[_lab] = tb_counts.get(_lab, 0) + 1
        theme_break = ""
        if tb_counts:
            _top = sorted(tb_counts.items(), key=lambda kv: -kv[1])[:10]
            _chips = "".join(f'<a class="tchip" href="/dash/theme?tag={q(lab)}">{esc(lab)} <b>{c}</b></a>'
                             for lab, c in _top)
            theme_break = ('<div class="card"><div class="ck-h">Themes inside'
                           '<span class="sub" style="margin:0;font-weight:400">multi-label · members per theme</span>'
                           f'</div><div class="chips">{_chips}</div></div>')
        participants = (
            '<h3 style="margin:14px 0 6px">All participants '
            f'<span class="sub" style="margin:0">{N} liquid members · sort · filter</span></h3>'
            + _participants_table(sorted_members, mtags))
        rollup = ('<h2>Inside the index <span class="sub" style="margin:0">bottom-up · equal-weight · '
                  f'{N} liquid members</span></h2>'
                  '<div class="sub" style="margin-top:2px">Membership carries no free-float weight, so every '
                  f'roll-up here is <b>equal-weight</b>. Breadth = share of members whose RS vs Nifty 500 is in an '
                  f'uptrend. {drill}</div>' + tiles + split + theme_break + participants)

        # leaders & laggards within the index (by rs_rank)
        ranked = [m for m in members if m.get("rs_rank") is not None]
        ranked.sort(key=lambda m: m["rs_rank"], reverse=True)

        def _ll(rows):
            o = ""
            for m in rows:
                o += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(m["symbol"])}">'
                      f'<span class="sym">{esc(m["symbol"])}</span></a></td>'
                      f'<td class="r">{m["rs_rank"]}</td>'
                      f'<td class="l">{D._char_pill(m.get("ch"))}</td>'
                      f'<td class="r">{pct(m.get("pfh"))}</td></tr>')
            return f'<table class="ck-t"><tbody>{o}</tbody></table>'
        if ranked:
            lead_board = _board('🏆 RS leaders', 'strongest in the index', _ll(ranked[:8]),
                                f"/dash/stocks?sector={q(idx)}", "All constituents", "var(--up)")
            lag_board = _board('🐌 RS laggards', 'weakest in the index', _ll(ranked[-8:][::-1]),
                               f"/dash/stocks?sector={q(idx)}", "All constituents", "var(--down)")
        else:
            lead_board = lag_board = ""

        # intra-index DVPT (where institutional delivery money is positioning)
        dv = sorted(members, key=lambda m: (1 if m.get("ath") else 0,
                                            m.get("p_score") or -1, m.get("dvt") or 0), reverse=True)
        dvrows = ""
        for m in dv[:8]:
            if not m.get("dvpt"):
                continue
            rank = m.get("rank") or "-"
            athg = "⚡" if m.get("ath") else ""
            ladder = D._mv_ladder(m.get("dvpt"), m.get("p1"), m.get("p2"), m.get("p3"),
                                  m.get("p6"), m.get("p12"))
            pvh = m.get("pvh")
            entry = ("🟢 disc" if (pvh is not None and pvh < -3)
                     else "🔴 ext" if (pvh is not None and pvh > 3) else "🟡 at-cost")
            dvrows += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(m["symbol"])}">'
                       f'<span class="sym">{athg}{esc(m["symbol"])}</span></a></td>'
                       f'<td class="l">{ladder}</td>'
                       f'<td><span class="pill p-{rank}">{rank}</span></td>'
                       f'<td class="l">{entry}</td></tr>')
        dvpt_board = (_board('⚡ Intra-index DVPT', 'institutional delivery positioning',
                             f'<table class="ck-t"><tbody>{dvrows}</tbody></table>',
                             "/dash/stocks", "Positioning screen", "#58a6ff")
                      if dvrows else "")
        # intra-index MEP — signed accumulation AND distribution (descriptor, D62).
        # Both ends; separate query over this index's constituents (member fetch untouched).
        mep_board = ""
        msyms = [m["symbol"] for m in members if m.get("symbol")]
        if msyms and sig_date:
            ph = ",".join("?" for _ in msyms)
            with D.get_conn() as conn:
                _mq = ("SELECT symbol, mep_score sc, mep_state st, mep_score_smooth ph, "
                       "mep_state_smooth phst FROM mep_signals "
                       f"WHERE trade_date=? AND mep_score_smooth IS NOT NULL AND symbol IN ({ph}) "
                       "ORDER BY mep_score_smooth {} LIMIT 5")
                maccum = [dict(x) for x in conn.execute(_mq.format("DESC"), (sig_date, *msyms)).fetchall()]
                mdistrib = [dict(x) for x in conn.execute(_mq.format("ASC"), (sig_date, *msyms)).fetchall()]

            def _mrow(x):
                sc = x.get("sc"); ph = x.get("ph")
                phv = ph if ph is not None else sc
                scol = "var(--up)" if (phv is not None and phv >= 0) else "var(--down)"
                dtxt = ("%+.2f" % sc) if sc is not None else "—"
                return (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(x["symbol"])}#mep">'
                        f'<span class="sym">{esc(x["symbol"])}</span></a></td>'
                        f'<td class="l">{_mv_adbar(phv)}</td><td class="l">{_mep_pill(x.get("phst"))}</td>'
                        f'<td class="r" style="color:{scol}" title="phase score (today {dtxt})">{phv:+.2f}</td></tr>')
            if maccum or mdistrib:
                mr = "".join(_mrow(x) for x in maccum)
                if mdistrib:
                    mr += ('<tr><td colspan="4" class="mut" style="padding-top:8px;font-size:11px">'
                           'DISTRIBUTING</td></tr>' + "".join(_mrow(x) for x in mdistrib))
                mep_board = _board('📊 Intra-index MEP', 'accumulation &amp; distribution · signed',
                                   f'<table class="ck-t"><tbody>{mr}</tbody></table>',
                                   "/dash/mep", "Open the MEP screen", "#db61a2")
        boards = "".join(b for b in (lead_board, lag_board, dvpt_board, mep_board) if b)
        if boards:
            rollup += '<div class="ckpt">' + boards + '</div>'
    elif not is_broad:
        rollup = ('<h2>Inside the index</h2><div class="empty">No liquid constituent signals on record '
                  'for this index yet.</div>')

    chart_js = (_INDEX_CHART_JS.replace("__CDN__", D._LWC_CDN)
                .replace("__DATA__", json.dumps({"price": cd, "ratio": rd})))
    crumb = ('<div class="sub" style="margin:0 0 6px">&#8592; '
             '<a class="row" style="display:inline" href="/dash/markets">Markets</a> · '
             '<a class="row" style="display:inline" href="/dash/sectors">Sectors</a></div>')
    # Price first (own candles) → today's snapshot → relative strength (RS heat +
    # ratio chart) → RS BAND (the level lens) → constituent roll-up. Price leads.
    from src.web.rsband_view import band_section          # additive; '' for broad/size indices
    band_block = band_section(num=idx)
    return (_CKPT_CSS + chart_css + crumb + head + banner + chart_html + snapshot
            + rs_block + band_block + rollup + chart_js)


# --- Launchpad: the data-validated explosive-move SETUP screen (D56) ----------
# Ports research/explosive_moves/launchpad_scan.launchpad_flags to a live, render-
# time screen over today's liquid universe — the same corporate-action-adjusted
# close the research used (via src.automation.adjust), RAW volume for the volume
# ratio, RAW turnover for the liquidity median. The validated MOMENTUM core
# (MOM_CONT/COILED, ≥₹5cr) is backtest "S1": net of costs over 2012-2026 it ran
# CAGR +4.0% / MaxDD -27.6% / hit 39% / PF 1.31 / beta 0.42, and BOTH walk-forward
# windows (2012-19 +2.2%, 2020-26 +5.1%) were net-positive. PULLBACK is the weaker
# mean-reversion diversifier (only the recent regime net-positive). A SETUP screen —
# entry candidates, regime-gated (Nifty 50 > 200-DMA); moves are infrequent.
_LP_LIQ = 5e7   # ₹5 cr trailing-median turnover — the S1-core liquidity floor


def _lp_at(adj, vols, vals, s):
    """The validated flags + metrics at index s over adjusted-close/volume/turnover
    arrays (oldest→newest). Returns (flags, metrics) or None when too little history."""
    if s < 23:
        return None
    if not (adj[s] and adj[s] > 0):
        return None

    def r(k):
        j = s - k
        return (adj[s] / adj[j] - 1.0) if (j >= 0 and adj[j] and adj[j] > 0) else None
    ret_1, ret_22 = r(1), r(22)
    if ret_22 is None:
        return None
    seg66 = [x for x in adj[max(0, s - 66):s + 1] if x and x > 0]
    lr = [math.log(seg66[i] / seg66[i - 1]) for i in range(1, len(seg66))]
    vol66 = statistics.pstdev(lr) if len(lr) >= 30 else None
    vol22 = statistics.pstdev(lr[-22:]) if len(lr) >= 22 else None
    vratio = (vol22 / vol66) if (vol66 and vol22 is not None) else None
    seg22 = [x for x in adj[max(0, s - 21):s + 1] if x and x > 0]
    rng = ((max(seg22) - min(seg22)) / (sum(seg22) / len(seg22))) if seg22 else None
    v22 = [v for v in vols[max(0, s - 21):s + 1] if v is not None]
    v66 = [v for v in vols[max(0, s - 65):s + 1] if v is not None]
    vr_vol = ((sum(v22) / len(v22)) / (sum(v66) / len(v66))) if (v22 and v66 and sum(v66)) else None
    prior_val = [v for v in vals[max(0, s - 22):s] if v is not None]   # trailing 22, excludes today
    med_turn = statistics.median(prior_val) if prior_val else None
    flags = []
    if ret_22 > 0.07 and vr_vol is not None and vr_vol <= 1.48 and rng is not None and rng > 0.096:
        flags.append("MOM_CONT")
    if ret_22 <= 0.07 and vol66 is not None and vol66 > 0.024 and ret_1 is not None and ret_1 <= -0.022:
        flags.append("PULLBACK")
    if vratio is not None and vratio < 1 and ret_22 >= 0.10:
        flags.append("COILED")
    return flags, {"ret22": ret_22, "ret1": ret_1, "vratio": vratio, "rng": rng,
                   "vol66": vol66, "med_turn": med_turn}


def _lp_features(closes, prev_closes, vols, vals):
    """Today's flags + metrics for ONE symbol, PLUS the rising-edge age: how many
    consecutive sessions (ending today) the setup has been on. age 0 = it just
    triggered today (off yesterday) — a genuine FRESH entry (the backtest enters on
    the rising edge, not the 8th day of a run). Returns (flags, metrics) or None."""
    from src.automation import adjust
    n = len(closes)
    if n < 30:
        return None
    adj = adjust.adjusted_closes([{"close": c, "prev_close": p}
                                  for c, p in zip(closes, prev_closes)])
    if not adj or adj[-1] is None:
        return None
    s = n - 1
    today = _lp_at(adj, vols, vals, s)
    if not today:
        return None
    flags, m = today
    days_on = 0
    for k in range(0, 7):                 # today + up to 6 prior sessions (cap)
        r = _lp_at(adj, vols, vals, s - k)
        if r and r[0]:
            days_on += 1
        else:
            break
    m["age"] = (days_on - 1) if days_on > 0 else None   # 0 = fresh today; 6 = "5+" sustained
    return flags, m


_LP_FLAG = {
    "MOM_CONT": ("MOM·CONT", "p-S", "momentum continuing, volume not yet expanded"),
    "COILED": ("COILED", "p-SS", "up ≥10% but realized-vol contracting — coiled"),
    "PULLBACK": ("PULLBACK", "p-A", "shaken in volatility — mean-reversion leg (weaker)"),
}


def _lp_net_buyers(conn):
    """Symbols with a GENUINE one-sided institutional NET BUYER on the latest deals
    day (bulk_block_deals ⋈ client_classify): non-churn category, |net|/(buy+sell)≥0.6,
    net>0 (mirrors launchpad_scan.genuine_net_buyers). Returns (symbol_set, deals_date).
    Degrades to (set(), None) if the deals feed / classifier isn't available."""
    try:
        from src.automation import client_classify as cc
        td = conn.execute("SELECT MAX(trade_date) d FROM bulk_block_deals").fetchone()
        td = td["d"] if td else None
        if not td:
            return set(), None
        rows = conn.execute(
            "SELECT symbol, client_name, side, SUM(qty) q FROM bulk_block_deals "
            "WHERE trade_date=? GROUP BY symbol, client_name, side", (td,)).fetchall()
    except Exception:
        return set(), None
    agg = {}
    for r in rows:
        a = agg.setdefault((r["symbol"], r["client_name"]), {"BUY": 0, "SELL": 0})
        a[r["side"]] = a.get(r["side"], 0) + (r["q"] or 0)
    out = set()
    for (sym, client), a in agg.items():
        b, s = a.get("BUY", 0), a.get("SELL", 0)
        tot = b + s
        if tot <= 0:
            continue
        try:
            cat = cc.classify_client(client)
        except Exception:
            continue
        if cat not in cc.CHURN and (b - s) > 0 and abs(b - s) / tot >= 0.6:
            out.add(sym)
    return out, td


_LP_MEMO: dict = {}


def _lp_live(conn, T):
    """Live-scan fallback for render_launchpad when the nightly launchpad_signals
    snapshot is absent or stale (fresh install, first day, holiday edge). Memoised
    per bhav date so only the FIRST render pays the whole-universe scan (the
    AUD-04 audit-lane-cache pattern); the nightly persist normally makes this
    path dead."""
    got = _LP_MEMO.get(T)
    if got is None:
        from src.automation import launchpad_signals as LPS
        hits, _t, deals_td = LPS.scan(conn)
        _LP_MEMO.clear()               # hold ONE date's scan at a time — never grows
        _LP_MEMO[T] = got = (hits, deals_td)
    return got


def render_launchpad(sig_date, idx_date) -> str:
    """Full-bleed live Launchpad — the validated explosive-move precursor universe
    over today's liquid (≥₹5cr) names, read from the nightly launchpad_signals
    snapshot (memoised live-scan fallback). Honest framing: the raw
    pattern is COMMON in a trend (a precursor universe, not a buy list); the actionable
    cut is the FRESH rising edge (the setup just turned on) + a ⭐ when a genuine
    institutional bulk/block net-buyer is present on the same name (the research's
    high-conviction intersection)."""
    from src.web import dashboard as D
    esc, pct, num = D._esc, D._pct, D._num

    T = regime_a200 = None
    hits, deals_td = [], None
    with D.get_conn() as conn:
        # No series='EQ' filter here: it defeats idx_bhav_date and turns a 0.1ms
        # index-max into a 3.2s scan of the 16GB table (measured S84). Every
        # trading day has EQ rows, so the MAX is identical; a hypothetical
        # mismatch only routes to the live-scan fallback, never a wrong page.
        tr = conn.execute("SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()
        T = tr["d"] if tr else None
        if not T:
            return _CKPT_CSS + '<div class="empty">No bhavcopy data yet.</div>'
        rg = conn.execute("SELECT pct_above_200d_avg a200 FROM index_signals "
                          "WHERE index_name='Nifty 50' ORDER BY trade_date DESC LIMIT 1").fetchone()
        regime_a200 = rg["a200"] if rg else None
        # The whole-universe gather (was ~9s per request, EVERY request) is now
        # PRE-COMPUTED nightly into launchpad_signals (hermes-launchpad-scan.timer,
        # wolfe_signals pattern) — read the snapshot when it matches today's bhav
        # date; otherwise fall back to a per-date-memoised live scan.
        snap = None
        try:
            from src.automation import launchpad_signals as LPS
            snap = LPS.latest(conn)
        except Exception:  # noqa: BLE001 — the snapshot is an accelerator, never fatal
            snap = None
        if snap is not None and snap.get("scan_date") == T:
            hits, deals_td = snap["hits"], snap.get("deals_date")
        else:
            hits, deals_td = _lp_live(conn, T)

    n_universe = len(hits)
    fresh = [h for h in hits if (h[2]["age"] is not None and h[2]["age"] <= 2)]
    n_buyer = sum(1 for _, _, m in hits if m.get("buyer"))
    n_co = sum(1 for _, f, _ in hits if "COILED" in f)
    # actionable order: a named institutional buyer first, then freshest, then most liquid
    fresh.sort(key=lambda h: (0 if h[2].get("buyer") else 1, h[2]["age"], -(h[2]["med_turn"] or 0)))
    CAP = 80
    shown, n_more = fresh[:CAP], max(0, len(fresh) - CAP)

    regime_on = regime_a200 is not None and regime_a200 > 0
    rcls = "b-on" if regime_on else "b-off"
    regime = (f'<div class="banner {rcls}">Regime · {"RISK-ON" if regime_on else "RISK-OFF"}'
              f'<small>Nifty 50 {pct(regime_a200)} vs its 200-DMA — the validated book '
              f'{"is active (trades these)" if regime_on else "stands aside"} when Nifty 50 is '
              f'{"above" if regime_on else "below"} its 200-DMA. (Setups still shown; regime is the timing gate.)</small></div>')

    deals_note = (f"bulk/block · {esc(deals_td)}" if deals_td else "deals feed pending")
    strip = _ck_strip([
        _ck_tile(len(fresh), "Fresh triggers", "var(--up)", "setup just turned on (≤2 sessions)"),
        _ck_tile(f"⭐ {n_buyer}", "With genuine buyer", "#d2a8ff", deals_note),
        _ck_tile(n_universe, "Precursor universe", "#f0883e", f"raw pattern · ₹{_LP_LIQ/1e7:.0f}cr+ · not a buy list"),
        _ck_tile(n_co, "Coiled", "#58a6ff", "vol contracting, up ≥10%"),
    ])

    def flagpills(flags):
        return " ".join(f'<span class="pill {c}" title="{esc(t)}">{l}</span>'
                        for l, c, t in (_LP_FLAG.get(f, (f, "p-C", "")) for f in flags))

    def age_cell(a):
        if a is None:
            return '<span class="mut">—</span>'
        if a == 0:
            return '<span class="pos" title="setup turned on TODAY (off yesterday)"><b>fresh</b></span>'
        return f'<span class="mut">{a}d ago</span>' if a < 6 else '<span class="mut">5d+</span>'

    if shown:
        trs = ""
        for sym, flags, m in shown:
            star = ('<span title="genuine institutional net-buyer in bulk/block deals">⭐</span>'
                    if m.get("buyer") else '')
            vr = m["vratio"]
            trs += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(sym)}">'
                    f'<span class="sym">{star}{esc(sym)}</span></a></td>'
                    f'<td class="l">{flagpills(flags)}</td>'
                    f'<td>{age_cell(m["age"])}</td>'
                    f'<td class="r">{pct((m["ret22"] or 0)*100)}</td>'
                    f'<td class="r">{num(vr,2) if vr is not None else "—"}</td>'
                    f'<td class="r">{pct((m["rng"] or 0)*100) if m["rng"] is not None else "—"}</td>'
                    f'<td class="r">₹{num((m["med_turn"] or 0)/1e7,1)} cr</td></tr>')
        more = (f'<div class="sub" style="margin:6px 0 0">+{n_more} more fresh triggers (showing the '
                f'{CAP} most liquid). ' if n_more else '')
        sustained = n_universe - len(fresh)
        more += (f'{sustained} names match the pattern but have been running &gt;2 sessions (sustained, '
                 f'not fresh) — they\'re in the precursor universe, not this fresh-trigger shortlist.</div>'
                 if sustained else '</div>')
        table = ('<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt">'
                 '<thead><tr><th class="l">Symbol</th><th class="l">Setup</th><th>Trigger age</th>'
                 '<th>22d ret</th><th>vol 22/66</th><th>22d range</th><th>med turnover</th></tr></thead>'
                 f'<tbody>{trs}</tbody></table></div>' + more)
    else:
        table = (f'<div class="empty">No <b>fresh</b> triggers today'
                 + (f' (though {n_universe} names are mid-pattern, already running). ' if n_universe
                    else ' — that\'s normal; the validated setup is infrequent. ')
                 + 'The edge is in selectivity, not frequency.</div>')

    evidence = (
        '<div class="card" style="border-color:#f0883e">'
        '<div class="ck-h"><span class="em">🚀</span> What this is — and the honest evidence'
        '<span class="sub" style="margin:0;font-weight:400">D56 explosive-move research</span></div>'
        '<div class="sub" style="margin:0;line-height:1.5">A <b>precursor screen</b>, not a buy list. The raw '
        'momentum/coiled/pullback pattern is <b>common</b> in a trend (the "precursor universe"); the backtest '
        'didn\'t buy all of them — over 2012–2026 it <b>selected ~84 trades a year</b> from days like these. '
        'So this screen leads with the <b>fresh rising edge</b> (the setup just turned on, not its 8th day) and '
        'stars (⭐) any name a <b>genuine institutional bulk/block net-buyer</b> hit on the same day (non-churn '
        'category, one-sided ≥60% net) — the research\'s high-conviction intersection (rare; the deals feed is young, '
        'so most days show none). The momentum core (MOM·CONT / COILED, ≥₹5 cr) is backtest <b>S1</b>: net of costs, '
        'regime-gated, CAGR <b>+4.0%</b> · MaxDD −27.6% · hit <b>39%</b> · PF <b>1.31</b> · beta 0.42, and <b>both</b> '
        'walk-forward windows (2012–19 +2.2% · 2020–26 +5.1%) net-positive. PULLBACK is the weaker mean-reversion leg. '
        'DVPT on the stock page is the per-name <b>confirmation</b> read, not the predictor (the D56 reconciliation). '
        'Not advice; size + manage risk yourself.</div></div>')

    head = ('<h2 style="margin-top:2px">🚀 Launchpad '
            f'<span class="sub" style="margin:0">validated explosive-move setups · {esc(T or "")}</span></h2>'
            '<div class="sub" style="margin-top:2px">Fresh triggers from the data-validated precursor universe '
            '(momentum-continuation ∪ coiled ∪ pullback) over today\'s liquid names. ⭐ = a genuine institutional '
            'net-buyer hit it too. Tap a name → its full stock page (price · DVPT confirmation · RS · quality).</div>')
    return _CKPT_CSS + head + regime + strip + table + evidence


def render_strategies(sig_date, idx_date) -> str:
    """Full-bleed, registry-driven STRATEGY HUB — same cockpit language as home/markets.
    The count-strip is driven by STRATEGY_REGISTRY (a new pillar auto-appears), then a
    board per pillar previews TODAY's top names. Replaces the old narrow .scard hub."""
    from src.web import dashboard as D
    esc = D._esc

    counts, conv, pos, rs, qual, cpr_top, cci = {}, [], [], [], [], [], []
    with D.get_conn() as conn:
        for e in STRATEGY_REGISTRY:
            try:
                counts[e["key"]] = e["count"](conn, sig_date, D)
            except Exception:
                counts[e["key"]] = None
        if sig_date:
            cpr_top = D._cpr_setups(conn, limit=6)
            cx = "(0.55*COALESCE(s.p_score,0)/5.0*100.0 + 0.45*COALESCE(s.rs_rank,0))"
            conv = [dict(r) for r in conn.execute(
                f"SELECT s.symbol, {cx} v, s.primary_sector sec FROM stock_signals s "
                f"JOIN bhavcopy_rows b USING (symbol, trade_date) WHERE s.trade_date=? "
                f"AND s.delivery_value_per_trade IS NOT NULL {D._SCAN_FILTERS} ORDER BY v DESC LIMIT 6",
                (sig_date,)).fetchall()]
            pos = [dict(r) for r in conn.execute(
                f"SELECT s.symbol, s.trigger_rank v, s.primary_sector sec FROM stock_signals s "
                f"JOIN bhavcopy_rows b USING (symbol, trade_date) WHERE s.trade_date=? "
                f"AND s.delivery_value_per_trade IS NOT NULL {D._SCAN_FILTERS} "
                f"ORDER BY COALESCE(s.is_ath_dvpt,0) DESC, COALESCE(s.p_score,-1) DESC, "
                f"COALESCE(s.delivery_value_today,0) DESC LIMIT 6", (sig_date,)).fetchall()]
            rs = [dict(r) for r in conn.execute(
                f"SELECT s.symbol, s.rs_rank v, s.primary_sector sec FROM stock_signals s "
                f"JOIN bhavcopy_rows b USING (symbol, trade_date) WHERE s.trade_date=? "
                f"AND s.rs_rank IS NOT NULL {D._SCAN_FILTERS} ORDER BY s.rs_rank DESC LIMIT 6",
                (sig_date,)).fetchall()]
        qual = [dict(r) for r in conn.execute(
            "SELECT p.symbol, p.ns_base v, p.tier FROM pattern_scores p "
            "JOIN (SELECT symbol, MAX(scored_at) m FROM pattern_scores GROUP BY symbol) x "
            "ON x.symbol=p.symbol AND x.m=p.scored_at WHERE p.ns_base IS NOT NULL "
            "ORDER BY p.ns_base DESC LIMIT 6").fetchall()]
        cci = [dict(r) for r in conn.execute(
            "SELECT s.symbol, s.composite_score v, s.tier, s.forward_direction fd FROM concall_scores s "
            "JOIN (SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x "
            "ON x.symbol=s.symbol AND x.m=s.last_updated WHERE COALESCE(s.veto_active,0)=0 "
            "AND s.composite_score IS NOT NULL ORDER BY s.composite_score DESC LIMIT 6").fetchall()]

    reg = {e["key"]: e for e in STRATEGY_REGISTRY}

    # --- registry count strip ---
    tiles = []
    for e in STRATEGY_REGISTRY:
        c = counts.get(e["key"])
        cval = "—" if c is None else str(c)
        tiles.append(
            f'<a class="ck-tile" href="{e["href"]}" style="border-top:3px solid {e["accent"]}" '
            f'title="{esc(e["thesis"])}"><div class="ck-n" style="color:{e["accent"]}">{cval}</div>'
            f'<div class="ck-l">{esc(e["label"])}</div><div class="ck-c">{esc(e["cta"])}</div></a>')
    strip = '<div class="ck-tiles">' + "".join(tiles) + '</div>'

    def name_rows(rows, fmt):
        if not rows:
            return '<table class="ck-t"><tbody><tr><td class="mut">No names today.</td></tr></tbody></table>'
        o = ""
        for r in rows:
            o += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                  f'<span class="sym">{esc(r["symbol"])}</span></a></td>'
                  f'<td class="l mut">{esc(r.get("sec") or r.get("tier") or "")}</td>'
                  f'<td class="r">{fmt(r)}</td></tr>')
        return f'<table class="ck-t"><tbody>{o}</tbody></table>'

    def b(key, rows, fmt):
        e = reg[key]
        return _board(esc(e["label"]), e["cta"], name_rows(rows, fmt), e["href"],
                      "Open the full screen", e["accent"])

    boards = [
        b("CONV", conv, lambda r: f'{r["v"]:.0f}' if r.get("v") is not None else "—"),
        b("POS", pos, lambda r: f'<span class="pill p-{r.get("v") or "-"}">{esc(r.get("v") or "-")}</span>'),
        b("RS", rs, lambda r: f'#{r["v"]}' if r.get("v") is not None else "—"),
        b("CPR", [{"symbol": s.get("symbol"), "sec": (s.get("conv") or {}).get("anchor"),
                   "v": (s.get("conv") or {}).get("tier")} for s in cpr_top],
          lambda r: esc(r.get("v") or "")),
        b("QUAL", qual, lambda r: f'{r["v"]:.0f}' if r.get("v") is not None else "—"),
        b("CCI", cci, lambda r: (f'{D._cci_num(r.get("v"))} {D._cci_fwd(r.get("fd"))}')),
    ]
    hub = '<div class="ckpt">' + "".join(boards) + '</div>'

    head = ('<h2 style="margin-top:2px">Strategies '
            '<span class="sub" style="margin:0">one lens per pillar · today\'s best names</span></h2>'
            '<div class="sub" style="margin-top:2px">Each tile is a live count — open it to screen. '
            'A new strategy added to the registry appears here automatically.</div>')
    return _CKPT_CSS + head + strip + hub


# --- CCI: Management Credibility full-bleed board (the "credible screen") ------
def _cci_tierpill(t) -> str:
    t = t or "—"
    col = "var(--up)" if t in ("A+", "A") else ("var(--down)" if t == "D" else "var(--ink-2)")
    return f'<span style="color:{col};font-weight:700">{t}</span>'


def render_concalls(view: str) -> str:
    """Full-bleed Management-Credibility board (CCI). Cockpit language: a count-strip
    (leaders / avoid / unproven / vetoed) + the view toggle + the data-first table
    (raw measurables beside every verdict, D-UI-1; behaviour shown as 'AI — not
    ranked', D61). Replaces the old narrow _shell page."""
    from src.web import dashboard as D
    esc = D._esc
    view = "leaders" if view == "leaders" else "avoid"

    with D.get_conn() as conn:
        sc = [dict(r) for r in conn.execute(
            "SELECT s.* FROM concall_scores s JOIN (SELECT symbol, MAX(last_updated) m "
            "FROM concall_scores GROUP BY symbol) x ON x.symbol=s.symbol AND x.m=s.last_updated").fetchall()]
        beh = {r["symbol"]: dict(r) for r in conn.execute(
            "SELECT b.symbol, b.credibility, b.courage, b.evasion FROM concall_behavior b "
            "JOIN (SELECT symbol, MAX(id) m FROM concall_behavior GROUP BY symbol) x "
            "ON x.symbol=b.symbol AND x.m=b.id").fetchall()}
    for r in sc:
        r.update(beh.get(r["symbol"], {}))

    n_total = len(sc)
    n_leaders = sum(1 for r in sc if not r.get("veto_active"))
    n_avoid = sum(1 for r in sc if r.get("veto_active") or (r.get("deterioration_score") or 0) > 0)
    n_unproven = sum(1 for r in sc if r.get("guidance_accuracy_score") is None)
    n_veto = sum(1 for r in sc if r.get("veto_active"))
    n_proven = sum(1 for r in sc if (r.get("n_promises_resolved") or 0) >= 1)

    if view == "leaders":
        rows = [r for r in sc if not r.get("veto_active")]
        rows.sort(key=lambda r: (r.get("composite_score") or 0), reverse=True)
    else:
        rows = sorted(sc, key=lambda r: ((r.get("deterioration_score") or 0)
                                         + (60 if r.get("veto_active") else 0)), reverse=True)

    trs = []
    for r in rows:
        veto = (f'<span style="color:var(--down)" title="{esc(r.get("veto_reason") or "")}">⛔ '
                f'{esc((r.get("veto_reason") or "")[:18])}</span>' if r.get("veto_active")
                else '<span class="mut">—</span>')
        ga = r.get("guidance_accuracy_score")
        ga_cell = (f'{ga:.0f}% <span class="mut">({r.get("n_promises_resolved") or 0})</span>'
                   if ga is not None else '<span class="mut">unproven</span>')
        det = r.get("deterioration_score") or 0
        det_cell = f'<span style="color:var(--down)">{int(det)}</span>' if det else '<span class="mut">0</span>'
        trs.append(
            f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
            f'<span class="sym">{esc(r["symbol"])}</span></a></td>'
            f'<td>{_cci_tierpill(r.get("tier"))}</td>'
            f'<td class="num">{D._cci_num(r.get("composite_score"))}</td>'
            f'<td>{D._cci_fwd(r.get("forward_direction"))}</td>'
            f'<td class="l">{veto}</td>'
            f'<td class="l">{ga_cell}</td>'
            f'<td class="num">{D._cci_num(r.get("quantification_rate"), "%")}</td>'
            f'<td class="num">{det_cell}</td>'
            f'<td class="mut">{esc(r.get("as_of_period") or "")}</td>'
            f'<td class="num mut">{r.get("n_concalls") or 0}</td>'
            f'<td class="num">{r.get("n_promises_resolved") or 0}</td>'
            f'<td class="num mut">{D._cci_num(r.get("credibility"))}</td>'
            f'<td class="num mut">{D._cci_num(r.get("courage"))}</td>'
            f'<td class="num mut">{D._cci_num(r.get("evasion"))}</td></tr>')

    head = ('<th class="l">Symbol</th><th>Tier</th><th class="num">Score</th><th>Forward</th>'
            '<th class="l">Veto</th><th class="l">Guidance acc.</th><th class="num">Quantif%</th>'
            '<th class="num">Deterior.</th><th>As of</th><th class="num">#Calls</th><th class="num">#Settled</th>'
            '<th class="num mut">Cred·AI</th><th class="num mut">Courage·AI</th><th class="num mut">Evasion·AI</th>')
    body_rows = "".join(trs) or '<tr><td colspan="14" class="mut" style="padding:14px">No scored concalls yet — the backfill is accruing (≈18/day via the cron).</td></tr>'
    table = (f'<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt" style="font-size:12.5px">'
             f'<thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>')

    def tile(n, label, accent, cta, href=""):
        a = f' href="{href}"' if href else ""
        tag = "a" if href else "div"
        return (f'<{tag} class="ck-tile"{a} style="border-top:3px solid {accent}">'
                f'<div class="ck-n" style="color:{accent}">{n}</div>'
                f'<div class="ck-l">{label}</div><div class="ck-c">{cta}</div></{tag}>')
    strip = ('<div class="ck-tiles">'
             + tile(n_proven, "Proven names", "var(--up)", "≥1 promise settled vs actuals")
             + tile(n_leaders, "Credibility leaders", "var(--up)", "veto-excluded, ranked")
             + tile(n_avoid, "Avoid tape", "var(--down)", "veto / deterioration")
             + tile(n_veto, "⛔ Vetoed", "var(--down)", "pledge / auditor / pt14")
             + tile(n_unproven, "Unproven", "var(--ink-2)", "no settled promises yet")
             + tile(n_total, "Scored", "#39c5cf", "names with concall data")
             + '</div>')

    def tab(key, label):
        on = " on" if key == view else ""
        return f'<a class="fbtn{on}" href="/dash/concalls?view={key}">{label}</a>'

    note = ("Avoid tape — worst-first (veto + deterioration)." if view == "avoid"
            else "Credibility leaders — veto-excluded, best measurable composite on top.")
    head_html = (
        '<h2 style="margin-top:2px">Management Credibility '
        '<span class="sub" style="margin:0">CCI · concall intelligence</span></h2>'
        f'<div class="fbar" style="margin:6px 0">{tab("avoid", "⚠ Avoid tape")}{tab("leaders", "★ Credibility leaders")}'
        '<a class="fbtn" href="/dash/credibility" title="Promise-vs-delivery fingerprint — every settled '
        'promise plotted over time (flagship A)">◔ Fingerprint</a></div>'
        f'<div class="sub" style="margin-top:0"><b>{note}</b> Ranking uses <b>measurable items only</b> '
        '(D61): guidance accuracy, quantification %, the ⛔ veto, and deterministic deterioration. '
        'The last three <b>·AI</b> columns are a model read shown <b>for context — NOT ranked</b>. '
        'A name is <b>unproven</b> until its promises resolve. <b>Pilot</b> — the historical backfill '
        'accrues ≈18 concalls/day via the nightly cron; open any name for its full dossier. '
        '<span style="color:var(--ink-3)">Corpus provenance (guardrail-#8 disclosure): ~98.6% of '
        'transcripts were <b>discovered</b> via Screener.in links (legacy path, frozen; BSE-primary '
        'migration in progress) — extraction and settlement run on the primary documents themselves.'
        '</span></div>')
    return _CKPT_CSS + head_html + strip + table


# --- Strategy DETAIL screens — cockpit migration (§3.A.2) ---------------------
# Each returns INNER html (cockpit language: count-strip + data-first table[s]),
# reusing the SAME data fetch + instruments the old narrow handlers used. The
# dashboard.py handlers are thin wrappers that wrap these in _shell(..., wide=True).

def render_mep(sig_date=None, focus="") -> str:
    """Full-bleed MEP screen — SIGNED accumulation AND distribution (descriptor,
    D62). BOTH ends, data-first: every raw signed term shown beside the verdict.
    The real destination behind every accumulation/distribution link; DVPT keeps
    its own screen at /dash/stocks."""
    from src.web import dashboard as D
    from src.web import glossary as G   # `?` hover-help on the MEP column headers
    esc, num, pct = D._esc, D._num, D._pct
    # `focus` pre-selects one side so the Net-accumulation / Distribution-watch home
    # cards land on THEIR rows (else the distribution names sit below 150 accum rows).
    focus = focus if focus in ("accum", "distrib") else ""
    if sig_date is None:
        with D.get_conn() as conn:
            r = conn.execute("SELECT MAX(trade_date) d FROM mep_signals").fetchone()
            sig_date = r["d"] if r else None
    counts, accum, distrib = {}, [], []
    # headline = the smoothed PHASE (ph/phst); the daily score (sc/st) sits
    # underneath as the granular "today" read. Order + count by the phase.
    cols = ("s.symbol, b.close cmp, s.mep_score sc, s.mep_state st, "
            "s.mep_score_smooth ph, s.mep_state_smooth phst, s.pressure pr, "
            "s.clv cv, s.drift_22d dr, s.updown_vol_22d uv, s.compression cp")
    if sig_date:
        with D.get_conn() as conn:
            for x in conn.execute(
                    "SELECT s.mep_state_smooth st, COUNT(*) c FROM mep_signals s "
                    "JOIN bhavcopy_rows b USING(symbol,trade_date) "
                    f"WHERE s.trade_date=? AND s.mep_state_smooth IS NOT NULL {D._SCAN_FILTERS} "
                    "GROUP BY s.mep_state_smooth", (sig_date,)).fetchall():
                counts[x["st"]] = x["c"]
            accum = [dict(x) for x in conn.execute(
                f"SELECT {cols} FROM mep_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
                f"WHERE s.trade_date=? AND s.mep_score_smooth IS NOT NULL {D._SCAN_FILTERS} "
                "ORDER BY s.mep_score_smooth DESC LIMIT 150", (sig_date,)).fetchall()]
            distrib = [dict(x) for x in conn.execute(
                f"SELECT {cols} FROM mep_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
                f"WHERE s.trade_date=? AND s.mep_score_smooth IS NOT NULL {D._SCAN_FILTERS} "
                "ORDER BY s.mep_score_smooth ASC LIMIT 150", (sig_date,)).fetchall()]
    strip = _ck_strip([
        _ck_tile(counts.get("STRONG_ACCUM", 0), "Strong accum", "var(--up)", "sustained · weeks"),
        _ck_tile(counts.get("ACCUM", 0), "Accumulating", "var(--up)", "phase"),
        _ck_tile(counts.get("NEUTRAL", 0), "Consolidating", "var(--ink-2)", "no clear side"),
        _ck_tile(counts.get("DISTRIB", 0), "Distributing", "#f0883e", "phase"),
        _ck_tile(counts.get("STRONG_DISTRIB", 0), "Strong distrib", "var(--down)", "sustained · weeks"),
    ])

    def n3(v):
        return f'{v:+.3f}' if v is not None else '—'

    def row_html(r, direction):
        sc = r["sc"]                       # daily score (granular, shown underneath)
        ph = r["ph"]                       # smoothed phase score (the headline)
        phv = ph if ph is not None else sc
        scol = "var(--up)" if (phv is not None and phv >= 0) else "var(--down)"
        dcol = "var(--up)" if (sc is not None and sc >= 0) else "var(--down)"
        hide = ' style="display:none"' if (focus and direction != focus) else ''
        return (f'<tr data-mepdir="{direction}"{hide}>'
                f'<td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}#mep">'
                f'<span class="sym">{esc(r["symbol"])}</span></a></td>'
                f'<td class="num">{num(r["cmp"], 1)}</td>'
                f'<td class="l">{_mv_adbar(phv)}</td>'
                f'<td class="l">{_mep_pill(r["phst"])}</td>'
                f'<td class="num" style="color:{scol}">{phv:+.2f}</td>'
                f'<td class="num mut" title="today\'s raw daily score">'
                f'{("%+.2f" % sc) if sc is not None else "—"}</td>'
                f'<td class="num mut">{n3(r["pr"])}</td>'
                f'<td class="num mut">{n3(r["cv"])}</td>'
                f'<td class="num mut">{pct(r["dr"] * 100) if r["dr"] is not None else "—"}</td>'
                f'<td class="num mut">{n3(r["uv"])}</td>'
                f'<td class="num mut">{num(r["cp"], 2)}</td></tr>')

    if accum or distrib:
        rows_html = ("".join(row_html(r, "accum") for r in accum)
                     + "".join(row_html(r, "distrib") for r in distrib))
        on_all = "" if focus else " on"
        on_acc = " on" if focus == "accum" else ""
        on_dis = " on" if focus == "distrib" else ""
        pills = ('<div id="mepbar" class="fbar">'
                 f"<button class=\"fbtn{on_all}\" onclick=\"mflt('all',this)\">All</button>"
                 f"<button class=\"fbtn{on_acc}\" onclick=\"mflt('accum',this)\">📈 Accumulating</button>"
                 f"<button class=\"fbtn{on_dis}\" onclick=\"mflt('distrib',this)\">📉 Distributing</button></div>")
        # Headers carry a `?` glossary popover (G.gloss) keyed on the real source
        # column, so every MEP term explains itself in-place (AUD: MEP had zero
        # explainability affordance; Pat/glossary now covers CLV/Pressure/Drift…).
        thead = (
            '<thead><tr>'
            f'<th class="l">Symbol</th><th>{G.gloss("close", "CMP")}</th>'
            f'<th class="l">{G.gloss("mep_score", "Accum ↔ Distrib")}</th>'
            f'<th class="l">{G.gloss("mep_state_smooth", "Phase")}</th>'
            f'<th>{G.gloss("mep_score_smooth", "Phase score")}</th>'
            f'<th>{G.gloss("mep_score", "Today")}</th>'
            f'<th>{G.gloss("pressure", "Pressure")}</th>'
            f'<th>{G.gloss("clv", "CLV")}</th>'
            f'<th>{G.gloss("drift_22d", "Drift")}</th>'
            f'<th>{G.gloss("updown_vol_22d", "Up/Dn vol")}</th>'
            f'<th>{G.gloss("compression", "Compress")}</th>'
            '</tr></thead>')
        table = (pills + '<div class="card" style="padding:6px 10px;overflow-x:auto">'
                 '<table id="meptbl" class="dt">' + thead
                 + f'<tbody>{rows_html}</tbody></table></div>')
        js = ("<script>function mflt(f,el){"
              "document.querySelectorAll('#meptbl tr[data-mepdir]').forEach(function(r){"
              "r.style.display=(f==='all'||r.dataset.mepdir===f)?'':'none';});"
              "document.querySelectorAll('#mepbar .fbtn').forEach(function(b){b.classList.remove('on');});"
              "el.classList.add('on');}</script>")
    else:
        table = '<div class="empty">No MEP signals for the latest day yet.</div>'
        js = ""
    head = ('<h2 style="margin-top:2px">📊 Accumulation &amp; Distribution '
            '<span class="sub" style="margin:0">MEP — signed, descriptor (D62)</span></h2>'
            '<div class="sub" style="margin-top:2px">A SIGNED read — '
            '<b style="color:var(--up)">+ accumulation</b> vs <b style="color:var(--down)">− distribution</b>, '
            'judged vs each stock\'s OWN history (the side DVPT is blind to). The headline '
            '<b>Phase</b> is a smoothed, hysteresis-banded regime that HOLDS for weeks '
            '(accumulation → consolidation → distribution); <b>Today</b> is the raw daily '
            'score underneath. Top 150 each end by phase; every raw signed term beside the '
            'verdict. Descriptor / confirmation, not a picker. Sort · filter · ⬇ export.</div>')
    return G.css() + _CKPT_CSS + head + strip + table + js


def render_conviction(limit) -> str:
    """Full-bleed Conviction shortlist (cross-pillar synthesis, D45). Count-strip
    (total / 🎯near-key / ★quality) + the All/Near-key/Quality filter + the 8-col
    data-first table — unchanged data, cockpit framing."""
    from src.web import dashboard as D
    esc, num = D._esc, D._num
    rows = conviction_shortlist(limit=limit) if conviction_shortlist else []

    # MEP confirmation lens (signed accumulation/distribution; descriptor — D62:
    # DISPLAY ONLY, never a ranking input). Per-render lookup keeps the
    # conviction_shortlist ranking untouched.
    mep_by = {}
    if rows:
        _syms = [r["symbol"] for r in rows]
        _ph = ",".join("?" for _ in _syms)
        try:
            with D.get_conn() as conn:
                _md = conn.execute("SELECT MAX(trade_date) m FROM mep_signals").fetchone()
                _mdate = _md["m"] if _md else None
                if _mdate:
                    mep_by = {x["symbol"]: (x["mep_state_smooth"] or x["mep_state"]) for x in conn.execute(
                        f"SELECT symbol, mep_state, mep_state_smooth FROM mep_signals WHERE trade_date=? AND symbol IN ({_ph})",
                        (_mdate, *_syms)).fetchall()}
        except Exception:
            mep_by = {}

    n_near = n_qual = 0
    trs = []
    for r in rows:
        g3 = r.get("gap_to_key_p3m")
        nearkey = (D.is_near_key(g3) or D.is_near_key(r.get("gap_to_key_p6m"))
                   or D.is_near_key(r.get("gap_to_key_p12m")))
        pvh = r.get("pvh")
        bits = []
        if nearkey:
            bits.append("🎯 near key")
        if pvh is not None and pvh < -3:
            bits.append("🟢 discount")
        elif pvh is not None and pvh > 3:
            bits.append("🔴 extended")
        entry = " ".join(bits) if bits else "🟡 at-cost"
        tier, dq = r.get("pt14_tier"), r.get("pt14_dq")
        if tier and not dq:
            qual = f'<span class="pill p-SS">★ {esc(tier)}</span>'
        elif tier and dq:
            qual = f'<span class="pill p-DOWNTREND">{esc(tier)} ✗</span>'
        else:
            qual = '<span class="mut">unscored</span>'
        if nearkey:
            n_near += 1
        if tier and not dq:
            n_qual += 1
        g3s = f'{g3:+.1f}%' if g3 is not None else '—'
        kp3 = r.get("key_price_p3m")
        trs.append(
            f'<tr data-nearkey="{1 if nearkey else 0}" data-qual="{1 if (tier and not dq) else 0}">'
            f'<td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
            f'<span class="sym">{esc(r["symbol"])}</span></a></td>'
            f'<td>{r.get("rs_rank") if r.get("rs_rank") is not None else "—"}</td>'
            f'<td class="l mut">{esc(r.get("primary_sector") or "—")}</td>'
            f'<td>{D._char_pill(r.get("accum_character"))}</td>'
            f'<td>{_mep_pill(mep_by.get(r["symbol"]))}</td>'
            f'<td class="l">{entry}</td>'
            f'<td class="l">{("₹"+num(kp3,1)) if kp3 else "—"} <span class="mut">({g3s})</span></td>'
            f'<td><span class="pill p-{r.get("trigger_rank") or "C"}">{r.get("trigger_rank") or "-"}</span> '
            f'{r.get("p_score") or 0}/5</td>'
            f'<td>{qual}</td></tr>')

    strip = _ck_strip([
        _ck_tile(len(rows), "Conviction names", "#d2a8ff", "all pillars aligned"),
        _ck_tile(n_near, "🎯 Near key", "var(--up)", "buyable entry band"),
        _ck_tile(n_qual, "★ Quality-confirmed", "#d29922", "pt14 not failing"),
    ])
    if trs:
        pills = ('<div id="cvbar" class="fbar">'
                 "<button class=\"fbtn on\" onclick=\"cflt('all',this)\">All</button>"
                 "<button class=\"fbtn\" onclick=\"cflt('nearkey',this)\">🎯 Near key</button>"
                 "<button class=\"fbtn\" onclick=\"cflt('qual',this)\">★ Quality-confirmed</button></div>")
        table = (pills + '<div class="card" style="padding:6px 10px;overflow-x:auto"><table id="cvtbl" class="dt">'
                 '<thead><tr><th class="l">Symbol</th><th>RS rank</th><th class="l">Sector</th><th>Character</th>'
                 '<th>MEP</th><th class="l">Entry</th><th class="l">Key 3m</th><th>Rank·p</th><th>Quality</th></tr></thead>'
                 f'<tbody>{"".join(trs)}</tbody></table></div>')
        js = ("<script>function cflt(f,el){"
              "document.querySelectorAll('#cvtbl tr[data-nearkey]').forEach(function(r){"
              "r.style.display=(f==='all'||r.dataset[f]==='1')?'':'none';});"
              "document.querySelectorAll('#cvbar .fbtn').forEach(function(b){"
              "b.classList.remove('on');});el.classList.add('on');}</script>")
    else:
        table = ('<div class="empty">No names clear all three pillars today — that\'s normal; '
                 'conviction is rare. Try <a class="row" style="display:inline" href="/dash/leaders">'
                 'leaders</a> or the <a class="row" style="display:inline" href="/dash/stocks">screen</a>.</div>')
        js = ""
    head = ('<h2 style="margin-top:2px">⭐ Conviction shortlist '
            '<span class="sub" style="margin:0">all three pillars aligned</span></h2>'
            '<div class="sub" style="margin-top:2px">An RS leader institutions are accumulating now, with the '
            'entry read; pt14 quality confirms where scored. Sort · filter · ⬇ export. '
            '🎯 = buyable near the institutional key price · ★ = pt14 quality-confirmed.</div>')
    return _CKPT_CSS + head + strip + table + js


def render_leaders() -> str:
    """Full-bleed strong-in-strong leaders + weak-in-weak laggards (D33c). Count-strip
    (leaders / laggards) + the two RS-aligned tables."""
    from src.web import dashboard as D
    esc, q = D._esc, D._q
    leaders = leaders_laggards("leaders", limit=60) if leaders_laggards else []
    laggards = leaders_laggards("laggards", limit=40) if leaders_laggards else []

    def tbl(rows, up):
        if not rows:
            return ('<div class="card"><div class="sub" style="margin:0">None right now — '
                    f'no stock has all three RS layers aligned {"up" if up else "down"}.</div></div>')
        trs = ""
        for r in rows:
            rk = r["rs_rank"]
            bs = r["broad_state"] or "—"
            ss = r["sector_state"] or "—"
            xs = r["sector_broad_state"] or "—"
            trs += (
                f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                f'<span class="sym">{esc(r["symbol"])}</span></a></td>'
                f'<td>{rk if rk is not None else ""}</td>'
                # RSI-RS column: CAPTURED from the live VPS file during the S83d fork-check —
                # a sibling session's uncommitted live-only work (AUD-27 discipline: live is
                # truth, capture verbatim; attribution: parallel session, not S83d).
                f'<td>{("%.0f" % r.get("rsi")) if r.get("rsi") is not None else "-"}</td>'
                f'<td class="l"><a class="row" href="/dash/index?idx={q(r["primary_sector"])}">'
                f'{esc(r["primary_sector"])}</a></td>'
                f'<td><span class="pill p-{bs}">{esc(_state_label(bs))}</span></td>'
                f'<td><span class="pill p-{ss}">{esc(_state_label(ss))}</span></td>'
                f'<td><span class="pill p-{xs}">{esc(_state_label(xs))}</span></td></tr>')
        return ('<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt">'
                '<thead><tr><th class="l">Symbol</th><th>RS rank</th><th>RSI-RS</th><th class="l">Sector</th>'
                '<th>stock vs broad</th><th>stock vs sector</th><th>sector vs broad</th></tr></thead>'
                f'<tbody>{trs}</tbody></table></div>')

    strip = _ck_strip([
        _ck_tile(len(leaders), "Leaders", "var(--up)", "strong-in-strong"),
        _ck_tile(len(laggards), "Laggards", "var(--down)", "weak-in-weak"),
    ])
    head = ('<h2 style="margin-top:2px">Leaders &amp; laggards '
            '<span class="sub" style="margin:0">all three RS layers aligned</span></h2>'
            '<div class="sub" style="margin-top:2px">A stock leading its sector <b>and</b> the market, with the '
            'sector leading the market too (leaders) — or all three down (laggards). Strongest / weakest first.</div>')
    return (_CKPT_CSS + head + strip
            + '<div class="ghdr">★ Leaders — strong-in-strong</div>' + tbl(leaders, True)
            + '<div class="ghdr" style="margin-top:14px">Laggards — weak-in-weak</div>' + tbl(laggards, False))


def _sector_rows(idx_date, order_sql):
    """Shared index_signals fetch for the sector RS screens."""
    from src.web import dashboard as D
    if not idx_date:
        return []
    with D.get_conn() as conn:
        return [dict(r) for r in conn.execute(
            f"""SELECT index_name nm, rs_vs_broad_trend_state st,
                       rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3,
                       rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12,
                       rs_vs_broad_slope_18m s18, rs_vs_broad_slope_24m s24,
                       ret_1m_pct r1, ret_3m_pct r3,
                       (0.6*COALESCE(rs_vs_broad_slope_3m,0)+0.4*COALESCE(rs_vs_broad_slope_6m,0)) mom
                FROM index_signals
                WHERE trade_date=? AND broad_benchmark IS NOT NULL
                  AND index_name IN ({D._real_sectors_in()})
                ORDER BY {order_sql}""", (idx_date,)).fetchall()]


def render_sectors() -> str:
    """Full-bleed sector rotation — RS heat per real sector. Count-strip
    (rising / falling / breakout) + the sortable RS table."""
    from src.web import dashboard as D
    esc, pct, q = D._esc, D._pct, D._q
    _, idx_date = D._latest_dates()
    order = ("CASE rs_vs_broad_trend_state WHEN 'BREAKOUT' THEN 0 WHEN 'UPTREND' THEN 1 "
             "WHEN 'CONSOLIDATING' THEN 2 WHEN 'DOWNTREND' THEN 3 WHEN 'BREAKDOWN' THEN 4 ELSE 5 END "
             "ASC, COALESCE(rs_vs_broad_slope_3m,-999) DESC")
    rows = _sector_rows(idx_date, order)
    if not rows:
        return _CKPT_CSS + '<div class="empty">No index signals yet. Run the index backfill on the VPS.</div>'

    rising = sum(1 for r in rows if (r["s3"] or 0) > 0)
    falling = sum(1 for r in rows if (r["s3"] or 0) < 0)
    brk = sum(1 for r in rows if r["st"] == "BREAKOUT")
    strip = _ck_strip([
        _ck_tile(rising, "Rising · 3m RS", "var(--up)", "outperforming Nifty 500"),
        _ck_tile(falling, "Falling · 3m RS", "var(--down)", "underperforming"),
        _ck_tile(brk, "Breakout", "#d2a8ff", "fresh RS breakout"),
    ])
    trs = []
    for r in rows:
        st = r["st"] or "—"
        nm = r["nm"]
        strip_rs = D._rs_strip(r["s1"], r["s3"], r["s6"], r["s12"], r.get("s18"), r.get("s24"))
        wk, wr = sector_weather(r["s1"], r["s3"], r["s6"], r["s12"], r["st"])
        trs.append(
            f'<tr><td class="l"><a class="row" href="/dash/index?idx={q(nm)}">'
            f'<span class="sym">{esc(nm)}</span></a></td>'
            f'<td>{pct(r["r1"])}</td><td>{pct(r["r3"])}</td>'
            f'<td class="l rsgrp"><a class="row" style="display:inline" href="/dash/index?idx={q(nm)}">{strip_rs}</a></td>'
            f'<td><span class="pill p-{st}">{_state_label(st)}</span></td>'
            f'<td>{_weather_badge(wk, wr)}</td>'
            f'<td>{pct(r["s3"])}</td></tr>')
    head = ('<h2 style="margin-top:2px">Sector rotation '
            '<span class="sub" style="margin:0">RS vs Nifty 500 · strongest first</span></h2>'
            '<div class="sub" style="margin-top:2px">Real economic sectors (factor/thematic indices live under '
            'Markets). Tap a sector → its detail page: price trend, RS &amp; constituent roll-up. '
            '<a class="row" style="display:inline" href="/dash/rs">Full RS ranking →</a> · '
            '<a class="row" style="display:inline" href="/dash/rrg">⟳ Rotation map (RRG) →</a></div>')
    table = ('<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt">'
             '<thead><tr><th colspan="3">RETURN</th>'
             '<th colspan="4" class="rsgrp grp">RELATIVE STRENGTH vs Nifty 500</th></tr>'
             '<tr><th class="l">Sector</th><th>1m</th><th>3m</th>'
             '<th class="l rsgrp">1m / 3m / 6m / 12m / 18m / 24m</th><th>Trend</th><th>Weather</th><th>RS 3m</th></tr></thead>'
             f'<tbody>{"".join(trs)}</tbody></table></div>')
    return _CKPT_CSS + head + strip + table


def render_rs() -> str:
    """Full-bleed cross-sector RS-momentum ranking (0.6·3m + 0.4·6m slope). Count-strip
    (top sector / # rising) + the ranked table with the percentile bar."""
    from src.web import dashboard as D
    esc, pct, q = D._esc, D._pct, D._q
    _, idx_date = D._latest_dates()
    rows = _sector_rows(idx_date, "mom DESC")
    if not rows:
        return _CKPT_CSS + '<div class="empty">No index signals yet. Run the index backfill on the VPS.</div>'

    moms = sorted(r["mom"] for r in rows)
    n_mom = len(moms)

    def pctl(m):
        if not n_mom:
            return 50
        below = sum(1 for x in moms if x < m)
        return max(1, min(99, round(below / n_mom * 99)))

    rising = sum(1 for r in rows if (r["mom"] or 0) > 0)
    top_nm = rows[0]["nm"] if rows else "—"
    strip = _ck_strip([
        _ck_tile(esc(top_nm), "Top momentum", "var(--up)", "strongest RS"),
        _ck_tile(rising, "Rising", "var(--up)", "positive RS momentum"),
        _ck_tile(len(rows), "Sectors ranked", "#58a6ff", "by 0.6·3m + 0.4·6m"),
    ])
    trs = []
    for i, r in enumerate(rows, 1):
        st = r["st"] or "—"
        nm = r["nm"]
        strip_rs = D._rs_strip(r["s1"], r["s3"], r["s6"], r["s12"], r.get("s18"), r.get("s24"))
        p = pctl(r["mom"])
        trs.append(
            f'<tr><td class="mut">{i}</td>'
            f'<td class="l"><a class="row" href="/dash/index?idx={q(nm)}">'
            f'<span class="sym">{esc(nm)}</span></a></td>'
            f'<td class="l">{strip_rs}</td>'
            f'<td>{pct(r["mom"])}</td>'
            f'<td><span class="pill p-{st}">{_state_label(st)}</span></td>'
            f'<td style="min-width:70px"><div class="bar"><span style="width:{p}%"></span></div></td></tr>')
    head = ('<h2 style="margin-top:2px">RS-momentum ranking '
            '<span class="sub" style="margin:0">sectors, strongest first</span></h2>'
            '<div class="sub" style="margin-top:2px">All sectors by RS momentum (0.6·3m + 0.4·6m slope vs '
            'Nifty 500). Tap a sector → its detail page. '
            '<a class="row" style="display:inline" href="/dash/sectors">← Sector rotation</a></div>')
    table = ('<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt">'
             '<thead><tr><th>#</th><th class="l">Sector</th><th class="l">1m/3m/6m/12m/18m/24m</th>'
             '<th>Mom</th><th>Trend</th><th>Pctl</th></tr></thead>'
             f'<tbody>{"".join(trs)}</tbody></table></div>')
    return _CKPT_CSS + head + strip + table


# ===========================================================================
# THEME TAGS (session 33) — the multi-label thematic layer surfaces. Data layer
# = company_tags + src/automation/theme_tags.py (deterministic index seed +
# Haiku-proposed/Ramana-approved). ADDITIVE: a lens beside sector + index.
# ===========================================================================

def _member_snapshot(conn, symbols, sig_date) -> list:
    """Per-member EOD snapshot for the participants table (shared by the index
    detail + theme detail pages). Same shape as render_index_detail's inline
    members query, plus the signed-MEP score/state (LEFT JOIN)."""
    from src.web import dashboard as D
    if not symbols or not sig_date:
        return []
    out = []
    for i in range(0, len(symbols), 800):           # SQLite param cap safety
        chunk = symbols[i:i + 800]
        ph = ",".join("?" for _ in chunk)
        out += [dict(r) for r in conn.execute(
            f"SELECT s.symbol, s.rs_rank, s.rs_vs_broad_trend_state st, s.accum_character ch, "
            f"s.is_ath_dvpt ath, s.pct_from_52w_high pfh, s.p_score, s.trigger_rank rank, "
            f"s.delivery_value_today dvt, s.price_vs_hot_avg_pct pvh, s.primary_sector sec, "
            f"b.close cmp, m.mep_score mep, m.mep_state mst, "
            f"m.mep_score_smooth mep_ph, m.mep_state_smooth mst_ph "
            f"FROM stock_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
            f"LEFT JOIN mep_signals m ON (m.symbol=s.symbol AND m.trade_date=s.trade_date) "
            f"WHERE s.trade_date=? AND s.symbol IN ({ph}) {D._SCAN_FILTERS}",
            (sig_date, *chunk)).fetchall()]
    return out


def _participants_table(members, tags_map) -> str:
    """The canonical participants table (index detail + theme detail). Columns:
    Symbol · Sector · Themes · RS rank · Trigger · p · Character · MEP · %52wH ·
    DVPT · Δhot. `tags_map` = {symbol: [labels]}. An "accumulating only" CSS
    toggle (signed-MEP ACCUM/STRONG_ACCUM, or character=ACCUMULATION fallback)."""
    from src.web import dashboard as D
    esc, pct, num = D._esc, D._pct, D._num
    rows = ""
    for m in members:
        sym = m["symbol"]
        rk = m.get("rank") or "-"
        athg = "⚡" if m.get("ath") else ""
        chips = D._tag_chips(tags_map.get(sym, []), cap=3) or '<span class="mut">—</span>'
        # headline the smoothed PHASE; daily score kept as the cell tooltip
        mst = m.get("mst_ph") or m.get("mst")
        mep_v = m.get("mep_ph") if m.get("mep_ph") is not None else m.get("mep")
        if mep_v is None and not mst:
            mep_cell = '<span class="mut">—</span>'
        else:
            _dt = ("%+.2f" % m["mep"]) if m.get("mep") is not None else "—"
            mep_cell = (f'<span title="phase (today {_dt})">{_mv_adbar(mep_v)}'
                        f'&nbsp;{_mep_pill(mst)}</span>')
        is_acc = mst in ("ACCUM", "STRONG_ACCUM") or m.get("ch") == "ACCUMULATION"
        cls = ' class="is-acc"' if is_acc else ''
        rows += (f'<tr{cls}><td class="l"><a class="row" href="/dash/stock?sym={esc(sym)}">'
                 f'<span class="sym">{athg}{esc(sym)}</span></a></td>'
                 f'<td class="l mut">{esc(m.get("sec") or "—")}</td>'
                 f'<td class="l">{chips}</td>'
                 f'<td class="r">{m["rs_rank"] if m.get("rs_rank") is not None else "—"}</td>'
                 f'<td><span class="pill p-{rk}">{rk}</span></td>'
                 f'<td class="r mut">{m.get("p_score") or 0}</td>'
                 f'<td class="l">{D._char_pill(m.get("ch"))}</td>'
                 f'<td class="l">{mep_cell}</td>'
                 f'<td class="r">{pct(m.get("pfh"))}</td>'
                 f'<td class="r">{("₹" + num((m.get("dvt") or 0) / 1e7, 1) + "cr") if m.get("dvt") else "—"}</td>'
                 f'<td class="r">{pct(m.get("pvh"))}</td></tr>')
    # The toggle wraps BOTH the checkbox and the table in one .ptbl container so
    # the checkbox's closest('.ptbl') resolves to an ANCESTOR (a sibling .ptbl
    # would return null and the toggle would silently throw).
    return ('<div class="ptbl"><label class="accfilter"><input type="checkbox" onchange="'
            "this.closest('.ptbl').classList.toggle('acc-only',this.checked)"
            '"> Accumulating only <span class="mut">(signed-MEP)</span></label>'
            '<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt">'
            '<thead><tr><th class="l">Symbol</th><th class="l">Sector</th><th class="l">Themes</th>'
            '<th>RS rank</th><th>Trigger</th><th>p</th><th class="l">Character</th>'
            '<th class="l">MEP</th><th>%52wH</th><th>DVPT</th><th>Δhot</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div></div>')


def render_themes(idx_date) -> str:
    """Themes browse — the multi-label thematic layer, grouped like the sectors
    page. Count-strip + one board per vocab group; each theme links to its
    participants drill (/dash/theme?tag=)."""
    from src.web import dashboard as D
    from src.automation import theme_tags as TT
    esc, q = D._esc, D._q
    with D.get_conn() as conn:
        counts = TT.theme_counts(conn)
        tagged = conn.execute("SELECT COUNT(DISTINCT symbol) FROM company_tags WHERE approved=1").fetchone()[0]
        n_prop = conn.execute("SELECT COUNT(*) FROM company_tags WHERE approved=0 AND source='ai'").fetchone()[0]
    n_themes = len(TT.THEME_VOCAB)
    n_await = sum(1 for t in TT.THEME_VOCAB if counts.get(t["label"], 0) == 0)
    strip = _ck_strip([
        _ck_tile(n_themes, "Themes", "#58a6ff", "controlled vocabulary"),
        _ck_tile(tagged, "Companies tagged", "var(--up)", "≥1 approved theme"),
        _ck_tile(n_await, "Awaiting tags", "#d29922", "cross-cutting · AI/manual"),
    ])
    boards = []
    for g in TT.THEME_GROUPS:
        items = [t for t in TT.THEME_VOCAB if t["group"] == g]
        trows = ""
        for t in items:
            c = counts.get(t["label"], 0)
            cc = str(c) if c else '<span class="mut">awaiting</span>'
            trows += (f'<a class="trow" href="/dash/theme?tag={q(t["label"])}">'
                      f'<span class="tn">{esc(t["label"])}</span>'
                      f'<span class="tb">{esc(t["blurb"])}</span>'
                      f'<span class="tc">{cc}</span></a>')
        boards.append(f'<div class="card ck-board"><div class="ck-h">{esc(g)}'
                      f'<span class="sub" style="margin:0;font-weight:400">{len(items)} themes</span>'
                      f'</div>{trows}</div>')
    review = (f' · <a class="row" style="display:inline" href="/dash/tags-review">'
              f'Review &amp; add tags{(" (" + str(n_prop) + " proposed)") if n_prop else ""} →</a>')
    head = ('<h2 style="margin-top:2px">Themes <span class="sub" style="margin:0">'
            'multi-label · beside sector &amp; index</span></h2>'
            '<div class="sub" style="margin-top:2px">A company can carry several themes at once — an '
            'EPC name is Infrastructure + Industrialization-proxy + Transport. Sector &amp; capex themes '
            'are <b>seeded deterministically from the NSE thematic indices</b> (a fact); cross-cutting '
            'themes are filled by review. Tap a theme → its participants.' + review + '</div>')
    return (_CKPT_CSS + head + strip
            + '<div class="theme-groups">' + "".join(boards) + '</div>')


def render_theme_detail(name, idx_date, sig_date) -> str:
    """One theme's participants drill — roll-up tiles + the full participants
    table (same as the index page), with the provenance of the tag shown."""
    from src.web import dashboard as D
    from src.automation import theme_tags as TT
    esc, q = D._esc, D._q
    name = (name or "").strip()
    if not name:
        return _CKPT_CSS + '<div class="empty">No theme specified. <a class="row" href="/dash/themes">All themes →</a></div>'
    entry = TT.vocab_entry(name)
    with D.get_conn() as conn:
        syms = TT.theme_members(conn, name)
        members = _member_snapshot(conn, syms, sig_date) if syms else []
        tags_map = TT.approved_tags_for(conn, [m["symbol"] for m in members]) if members else {}
        prov = {r[0]: r[1] for r in conn.execute(
            "SELECT source, COUNT(DISTINCT symbol) c FROM company_tags WHERE tag=? AND approved=1 GROUP BY source",
            (name,)).fetchall()}
    members.sort(key=lambda m: (m.get("rs_rank") is None, -(m.get("rs_rank") or 0)))
    N = len(members)
    n_up = sum(1 for m in members if m.get("st") in ("UPTREND", "BREAKOUT"))
    n_lead = sum(1 for m in members if (m.get("rs_rank") or 0) >= 80)
    n_acc = sum(1 for m in members if (m.get("mst_ph") or m.get("mst")) in ("ACCUM", "STRONG_ACCUM") or m.get("ch") == "ACCUMULATION")
    n_ath = sum(1 for m in members if m.get("ath"))
    blurb = entry["blurb"] if entry else ""
    grp = entry["group"] if entry else "—"
    prov_bits = []
    if prov.get("index"):
        prov_bits.append(f'{prov["index"]} index-seeded')
    if prov.get("ramana"):
        prov_bits.append(f'{prov["ramana"]} approved')
    if prov.get("ai"):
        prov_bits.append(f'{prov["ai"]} AI')
    prov_txt = " · ".join(prov_bits) if prov_bits else "no members yet"
    crumb = ('<div class="sub" style="margin-top:2px"><a class="row" style="display:inline" '
             'href="/dash/themes">← All themes</a> · group: <b>' + esc(grp) + '</b> · ' + esc(prov_txt) + '</div>')
    head = (f'<h2 style="margin-top:2px">{esc(name)} '
            f'<span class="sub" style="margin:0">{esc(blurb)}</span></h2>' + crumb)
    if not members:
        empty = ('<div class="card" style="margin-top:10px">No tagged participants with EOD signals yet. '
                 'Cross-cutting themes fill up via <a class="row" style="display:inline" '
                 'href="/dash/tags-review">review &amp; add tags</a>.</div>')
        return _CKPT_CSS + head + empty
    strip = _ck_strip([
        _ck_tile(N, "Participants", "#58a6ff", "tagged + liquid"),
        _ck_tile(n_up, "In RS uptrend", "var(--up)", "vs Nifty 500"),
        _ck_tile(n_lead, "RS leaders", "var(--up)", "rs_rank ≥ 80"),
        _ck_tile(n_acc, "Accumulating", "var(--up)", "signed-MEP / character"),
        _ck_tile(n_ath, "ATH-DVPT", "#f0883e", "all-time delivery peak"),
    ])
    cmp_link = ('<div class="sub" style="margin:10px 0 0"><a class="row" style="display:inline" '
                f'href="/dash/screener?scope=all">Open the screener (type &quot;{esc(name)}&quot; to filter) →</a></div>')
    table = _participants_table(members, tags_map)
    return (_CKPT_CSS + head + strip
            + '<h3 style="margin:14px 0 6px">Participants '
            f'<span class="sub" style="margin:0">{N} tagged · sort · filter</span></h3>'
            + table + cmp_link)


def _tag_act_btn(action, symbol, tag, label, nxt="/dash/tags-review") -> str:
    """A one-click POST button (approve/reject/remove) for the review surface.
    Destructive actions (remove) get a browser confirm() guard so a stray click
    can't silently hard-delete a manual tag (D81 — no one-click irreversible delete)."""
    from src.web import dashboard as D
    esc = D._esc
    onsub = ""
    if action == "remove":
        # JS single-quoted string: escape backslashes/quotes so the tag/symbol
        # (controlled vocab, but be safe) can't break out of the confirm() call.
        def _js(s):
            return str(s).replace("\\", "\\\\").replace("'", "\\'").replace('"', "&quot;")
        msg = (f"Remove the “{_js(tag)}” tag from {_js(symbol)}? "
               "This permanently deletes your manual tag and can’t be undone from here.")
        onsub = f" onsubmit=\"return confirm('{msg}')\""
    return (f'<form method="post" action="/dash/tags" style="display:inline"{onsub}>'
            f'<input type="hidden" name="action" value="{action}">'
            f'<input type="hidden" name="symbol" value="{esc(symbol)}">'
            f'<input type="hidden" name="tag" value="{esc(tag)}">'
            f'<input type="hidden" name="nxt" value="{esc(nxt)}">'
            f'<button type="submit" class="tbtn">{label}</button></form>')


def _render_entity_tags(sym, added="", err="") -> str:
    """Per-company tag editor (/dash/tags-review?sym=X) — ALL of one company's
    themes in one place: index facts (locked), your approved tags (removable), and
    pending proposals (approve/reject), + an inline add form + a dismissed list
    (restore). Linked from the stock page header. Honest: shows source + why."""
    from src.web import dashboard as D
    from src.automation import theme_tags as TT
    esc, q = D._esc, D._q
    with D.get_conn() as conn:
        tags = TT.tags_with_provenance(conn, sym)
        ab = conn.execute("SELECT about, screener_industry FROM company_about WHERE symbol=?", (sym,)).fetchone()
        dismissed = [r[0] for r in conn.execute(
            "SELECT tag FROM company_tags WHERE symbol=? AND source='rejected' ORDER BY tag", (sym,)).fetchall()]
    nxt = f"/dash/tags-review?sym={q(sym)}"
    note = ""
    if added:
        note = f'<div class="card" style="border-left:3px solid var(--up);margin-bottom:8px">Saved: <b>{esc(added)}</b></div>'
    elif err:
        note = (f'<div class="card" style="border-left:3px solid var(--down);margin-bottom:8px">Could not save '
                f'<b>{esc(err)}</b> — must be a vocabulary theme.</div>')
    _src = {"index": "index · membership fact", "ramana": "you added",
            "keyword": "keyword-proposed", "ai": "AI-proposed (Gemini)"}
    trows, have = "", set()
    for t in tags:
        have.add(t["tag"])
        if t["approved"]:
            chip = D._tag_chips([t["tag"]], link=False)
            action = ('<span class="mut">🔒 locked (membership fact)</span>' if t["source"] == "index"
                      else _tag_act_btn("remove", sym, t["tag"], "✕ remove", nxt))
        else:
            chip = D._tag_chips([t["tag"]], link=False, proposed={t["tag"]})
            action = (_tag_act_btn("approve", sym, t["tag"], "✓ approve", nxt) + " "
                      + _tag_act_btn("reject", sym, t["tag"], "✕ dismiss", nxt))
        trows += (f'<tr><td class="l">{chip}</td><td class="mut">{esc(_src.get(t["source"], t["source"]))}</td>'
                  f'<td class="l mut">{esc(t.get("note") or "")}</td><td class="l">{action}</td></tr>')
    if not trows:
        trows = '<tr><td class="mut" colspan="4">No themes yet — add one below.</td></tr>'
    opts = "".join(f'<option value="{esc(t["label"])}">{esc(t["label"])} · {esc(t["group"])}</option>'
                   for t in TT.THEME_VOCAB if t["label"] not in have)
    addform = (('<form method="post" action="/dash/tags" class="card" '
                'style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0">'
                '<input type="hidden" name="action" value="add">'
                f'<input type="hidden" name="symbol" value="{esc(sym)}">'
                f'<input type="hidden" name="nxt" value="{esc(nxt)}">'
                f'<span class="sub" style="margin:0">Add a theme to <b>{esc(sym)}</b>:</span>'
                '<select name="tag" style="background:var(--bg-1);border:1px solid var(--line-2);color:var(--ink);'
                f'border-radius:6px;padding:6px 8px">{opts}</select>'
                '<button type="submit" class="tbtn">+ Add</button></form>')
               if opts else f'<div class="sub" style="margin:10px 0">{esc(sym)} already carries every vocabulary theme.</div>')
    dis_html = ""
    if dismissed:
        chips = "".join(
            f'<span class="tchip" style="opacity:.6">{esc(d)}</span> {_tag_act_btn("unreject", sym, d, "↺ restore", nxt)} '
            for d in dismissed)
        dis_html = (f'<h3 style="margin:14px 0 6px">Dismissed <span class="sub" style="margin:0">'
                    f"won't be re-proposed · restore to allow again</span></h3>"
                    f'<div class="card">{chips}</div>')
    about_html = ""
    if ab and ab[0]:
        about_html = (f'<div class="card sub" style="margin-bottom:8px"><b>What the engine reads</b> '
                      f'(Screener · {esc(ab[1] or "—")}): {esc((ab[0] or "")[:280])}…</div>')
    n_prop = sum(1 for t in tags if not t["approved"])
    approve_all_sym = ""
    if n_prop:
        approve_all_sym = (
            '<form method="post" action="/dash/tags" style="display:inline;margin-left:8px">'
            '<input type="hidden" name="action" value="approve_symbol">'
            f'<input type="hidden" name="symbol" value="{esc(sym)}">'
            f'<input type="hidden" name="nxt" value="{esc(nxt)}">'
            f'<button type="submit" class="tbtn tbtn-go">✓ Approve all {n_prop} proposed</button></form>')
    head = (f'<h2 style="margin-top:2px">Themes · {esc(sym)} '
            '<span class="sub" style="margin:0">all tags for this company · edit</span></h2>'
            f'<div class="sub" style="margin-top:2px"><a class="row" style="display:inline" href="/dash/stock?sym={q(sym)}">'
            f'← {esc(sym)} stock page</a> · <a class="row" style="display:inline" href="/dash/tags-review">all proposals</a> · '
            f'<a class="row" style="display:inline" href="/dash/themes">all themes</a>{approve_all_sym}</div>')
    table = ('<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt">'
             '<thead><tr><th class="l">Theme</th><th class="l">Source</th><th class="l">Why / match</th>'
             '<th class="l">Action</th></tr></thead>'
             f'<tbody>{trows}</tbody></table></div>')
    return _CKPT_CSS + head + note + about_html + table + addform + dis_html


def render_tags_review(added="", err="", sym="") -> str:
    """Approve AI-proposed theme tags + manually add/remove tags (session 33).

    The human-in-the-loop surface Ramana locked: the deterministic index seed is
    a fact; the FREE keyword proposer (or the opt-in Gemini-only top-up) PROPOSES
    cross-cutting tags (approved=0) here for sign-off; and Ramana can hand-add any
    vocabulary tag (source='ramana')."""
    from src.web import dashboard as D
    from src.automation import theme_tags as TT
    esc, q = D._esc, D._q
    sym = (sym or "").upper().strip()
    if sym:                                   # per-company editor (linked from the stock page)
        return _render_entity_tags(sym, added, err)
    with D.get_conn() as conn:
        pending = TT.proposals_pending(conn)
        manual = [dict(r) for r in conn.execute(
            "SELECT symbol, tag, as_of FROM company_tags WHERE source='ramana' AND approved=1 "
            "ORDER BY as_of DESC, symbol LIMIT 200").fetchall()]
    note = ""
    if added:
        note = f'<div class="card" style="border-left:3px solid var(--up);margin-bottom:8px">Saved: <b>{esc(added)}</b></div>'
    elif err:
        note = (f'<div class="card" style="border-left:3px solid var(--down);margin-bottom:8px">Could not save '
                f'<b>{esc(err)}</b> — the tag must be in the controlled vocabulary.</div>')
    opts = "".join(f'<option value="{esc(t["label"])}">{esc(t["label"])} · {esc(t["group"])}</option>'
                   for t in TT.THEME_VOCAB)
    addform = ('<form method="post" action="/dash/tags" class="card" '
               'style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px">'
               '<input type="hidden" name="action" value="add">'
               '<input type="hidden" name="nxt" value="/dash/tags-review">'
               f'<input name="symbol" value="{esc(sym)}" placeholder="TICKER" autocapitalize="characters" '
               'style="background:var(--bg-1);border:1px solid var(--line-2);color:var(--ink);border-radius:6px;padding:6px 8px;width:130px"/>'
               '<select name="tag" style="background:var(--bg-1);border:1px solid var(--line-2);color:var(--ink);'
               f'border-radius:6px;padding:6px 8px">{opts}</select>'
               '<button type="submit" class="tbtn">+ Add tag</button>'
               '<span class="sub" style="margin:0">manual tags are approved instantly (source=ramana)</span></form>')
    if pending:
        _srcpill = {"keyword": "rule", "ai": "AI·gemini", "index": "index"}
        # GROUP BY theme so you can "approve all" a theme in one click (scan it,
        # dismiss the odd FP first, then bulk-approve the rest), instead of N clicks.
        by_tag = {}
        for p in pending:
            by_tag.setdefault(p["tag"], []).append(p)
        groups = ""
        for tag in sorted(by_tag, key=lambda t: (-len(by_tag[t]), t)):
            items = by_tag[tag]
            rows = "".join(
                f'<tr><td class="l"><a class="row" style="display:inline" href="/dash/tags-review?sym={q(p["symbol"])}">'
                f'{esc(p["symbol"])}</a></td>'
                f'<td class="mut">{esc(_srcpill.get(p.get("source"), p.get("source") or "—"))}</td>'
                f'<td class="l mut">{esc(p.get("note") or "")}</td>'
                f'<td class="l">{_tag_act_btn("approve", p["symbol"], tag, "✓")} '
                f'{_tag_act_btn("reject", p["symbol"], tag, "✕")}</td></tr>'
                for p in items)
            approve_all = (f'<form method="post" action="/dash/tags" style="display:inline;margin-left:auto">'
                           f'<input type="hidden" name="action" value="approve_theme">'
                           f'<input type="hidden" name="tag" value="{esc(tag)}">'
                           f'<input type="hidden" name="nxt" value="/dash/tags-review">'
                           f'<button type="submit" class="tbtn tbtn-go">✓ Approve all {len(items)}</button></form>')
            groups += (f'<div class="card" style="margin-bottom:10px;padding:6px 10px">'
                       f'<div class="ck-h" style="display:flex;align-items:center;gap:8px">'
                       f'{D._tag_chips([tag], link=False)}<span class="sub" style="margin:0">{len(items)} proposed</span>'
                       f'{approve_all}</div>'
                       '<div style="overflow-x:auto"><table class="dt"><thead><tr><th class="l">Symbol</th>'
                       '<th class="l">Source</th><th class="l">Why / match</th><th class="l">Action</th></tr></thead>'
                       f'<tbody>{rows}</tbody></table></div></div>')
        pend_html = (f'<h3 style="margin:16px 0 6px">Proposals '
                     f'<span class="sub" style="margin:0">{len(pending)} across {len(by_tag)} themes · '
                     'approve-all per theme, dismiss the odd FP</span></h3>' + groups)
    else:
        pend_html = ('<h3 style="margin:16px 0 6px">Proposals</h3>'
                     '<div class="card sub" style="margin:0">No proposals pending. The FREE keyword proposer '
                     '(<code>theme_tags --keyword-propose</code> — ₹0, no LLM) reads business descriptions from '
                     '<code>company_about</code> and proposes cross-cutting tags (Industrialization-proxy, '
                     'Make-in-India, …) for review here, filling as the Screener cadence captures descriptions. An '
                     'optional Gemini-only top-up (<code>--llm-propose</code>, never Claude) adds nuance.</div>')
    if manual:
        mrows = "".join(
            f'<tr><td class="l"><a class="row" style="display:inline" href="/dash/stock?sym={q(m["symbol"])}">'
            f'{esc(m["symbol"])}</a></td><td class="l">{D._tag_chips([m["tag"]], link=False)}</td>'
            f'<td class="l mut">{esc(m.get("as_of") or "")}</td>'
            f'<td class="l">{_tag_act_btn("remove", m["symbol"], m["tag"], "✕ remove")}</td></tr>'
            for m in manual)
        man_html = (f'<h3 style="margin:16px 0 6px">Your manual tags '
                    f'<span class="sub" style="margin:0">{len(manual)} added</span></h3>'
                    '<div class="card" style="padding:6px 10px;overflow-x:auto"><table class="dt">'
                    '<thead><tr><th class="l">Symbol</th><th class="l">Tag</th><th class="l">Added</th>'
                    '<th class="l">Action</th></tr></thead>'
                    f'<tbody>{mrows}</tbody></table></div>')
    else:
        man_html = ""
    head = ('<h2 style="margin-top:2px">Review &amp; add tags '
            '<span class="sub" style="margin:0">human-in-the-loop · rules propose, you approve</span></h2>'
            '<div class="sub" style="margin-top:2px">Index-seeded tags are facts and refresh automatically. '
            'Use this page to approve keyword/LLM proposals and to hand-add the cross-cutting themes no index '
            'captures. <a class="row" style="display:inline" href="/dash/themes">← All themes</a></div>')
    return _CKPT_CSS + head + note + addform + pend_html + man_html
