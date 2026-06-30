"""/dash/mep/overlay — MEP (accumulation vs distribution) phase tint on the stock chart.

Mirrors `cpr_overlay.py`: a `/dash/mep/overlay` endpoint that returns contiguous
**smoothed-phase** bands from `mep_signals.mep_state_smooth` (session-35's stable phase,
not the whippy daily score), plus a self-contained SNIPPET that tints the price-chart
background green (accumulation) / red (distribution) as a canvas primitive on
`window.__wfcandle`. Default OFF — an opt-in lens, since the CPR Spine is the default-on
signature; fetch-on-first-toggle (Wolfe-style). The chip joins the existing CPR/MA chip
row. dashboard.py drops one `{token}`; main.py includes the router. No circular dep.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.core.db import get_conn

router = APIRouter()

# smoothed-phase state -> tint key (NEUTRAL / None -> no band)
_TINT = {"ACCUM": "A", "STRONG_ACCUM": "SA", "DISTRIB": "D", "STRONG_DISTRIB": "SD"}


@router.get("/dash/mep/overlay")
def mep_overlay(sym: str = Query("", max_length=24)):
    """JSON: {bands:[{t0,t1,k}]} — contiguous accumulation/distribution phase runs."""
    sym = sym.strip().upper()
    if not sym:
        return JSONResponse(None)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT trade_date, mep_state_smooth FROM mep_signals WHERE symbol=? ORDER BY trade_date",
            (sym,),
        ).fetchall()
    bands: list[dict] = []
    run_start = None
    run_k = None
    last = None
    for r in rows:
        date, state = r[0], r[1]
        k = _TINT.get(state)
        if k != run_k:
            if run_k is not None and run_start is not None:
                bands.append({"t0": str(run_start), "t1": str(date), "k": run_k})
            run_start, run_k = date, k
        last = date
    if run_k is not None and run_start is not None and last is not None:
        bands.append({"t0": str(run_start), "t1": str(last), "k": run_k})
    if not bands:
        return JSONResponse(None)
    return JSONResponse({"bands": bands})


# Plain string (NOT an f-string) so the JS braces survive; dashboard.py inserts it
# via its f-string template like `{_CPR_SNIPPET}`.
SNIPPET = """<script>
(function(){
  var PC=null, CS=null, prim=null, bands=null, on=false, loaded=false;
  var COL={A:'rgba(63,212,134,0.07)',SA:'rgba(63,212,134,0.15)',D:'rgba(255,106,122,0.07)',SD:'rgba(255,106,122,0.15)'};
  function chipCss(a){ return 'cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:3px 9px;border-radius:20px;'+(a?'background:rgba(188,140,255,0.16);color:#cda9ff':'border:1px solid #30363d;color:#8b949e'); }
  function makePrim(){ var req=null, vis=true;
    var view={ zOrder:function(){return 'bottom';}, renderer:function(){ return { draw:function(tg){
      if(!vis||!PC||!bands) return;
      tg.useBitmapCoordinateSpace(function(sc){
        var x=sc.context,h=sc.horizontalPixelRatio,v=sc.verticalPixelRatio,H=sc.mediaSize.height,W=sc.mediaSize.width,ts=PC.timeScale();
        bands.forEach(function(b){ var rx0=ts.timeToCoordinate(b.t0), rx1=ts.timeToCoordinate(b.t1);
          if(rx0==null&&rx1==null) return; var x0=(rx0==null?0:rx0), x1=(rx1==null?W:rx1); if(x1<=x0) x1=x0+1;
          x.fillStyle=COL[b.k]||'rgba(0,0,0,0)'; x.fillRect(x0*h,0,(x1-x0)*h,H*v); });
      });
    }};}};
    return { attached:function(p){req=p.requestUpdate;}, detached:function(){}, updateAllViews:function(){}, paneViews:function(){return [view];}, redraw:function(){if(req)req();}, setVisible:function(b){vis=!!b; if(req)req();} };
  }
  function setChip(){ var c=document.getElementById('mepChip'); if(c) c.style.cssText=chipCss(on); }
  function toggle(){ on=!on; setChip();
    if(on){ if(loaded){ if(prim) prim.setVisible(true); return; } loaded=true;
      var sym=new URLSearchParams(location.search).get('sym')||'';
      fetch('/dash/mep/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
        if(!d||!d.bands||!d.bands.length) return; bands=d.bands; prim=makePrim(); CS.attachPrimitive(prim);
      }).catch(function(){ loaded=false; });
    } else { if(prim) prim.setVisible(false); }
  }
  function makeChip(){ var c=document.createElement('span'); c.id='mepChip'; c.style.cssText=chipCss(on);
    c.innerHTML='<span style="width:7px;height:7px;border-radius:50%;background:#bc8cff"></span>MEP';
    c.title='Accumulation (green) vs distribution (red) phase \\u2014 smoothed'; c.onclick=toggle; return c; }
  function place(tries){ if(document.getElementById('mepChip')) return;
    var bar=document.getElementById('stratBar')||document.getElementById('maBar');
    if(bar){ bar.appendChild(makeChip()); return; }
    if(tries>0){ setTimeout(function(){place(tries-1);},80); return; }
    var host=document.getElementById('priceChart'); if(!host) return;
    var b=document.createElement('div'); b.id='mepBar'; b.style.cssText='display:flex;gap:6px;align-items:center;margin:4px 0 2px;font-family:-apple-system,Segoe UI,sans-serif';
    b.appendChild(makeChip()); host.parentNode.insertBefore(b, host.nextSibling);
  }
  function boot(){ if(!window.__wfpc||!window.__wfcandle){ return setTimeout(boot,60); } PC=window.__wfpc; CS=window.__wfcandle; place(25); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
</script>"""
