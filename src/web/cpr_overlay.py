"""/dash/cpr/overlay — the CPR Spine on the stock page's EXISTING price chart.

Mirrors `wolfe_overlay.py` so it drops onto the live `/dash/stock` chart without a
rewrite: dashboard.py exposes the price chart as `window.__wfpc` and its candle
series as `window.__wfcandle` (one line each) + drops one `{token}`; main.py includes
the router (one line). The SNIPPET draws the CPR Spine — the stepped amber band
(BC↔TC) + dashed pivot, regime tint, brighter coil, D/W/M confluence slab, U/∩
markers — as a lightweight-charts primitive ON the real candle series (so price
mapping is exact and the shared time-axis is never polluted). Segments that fall
entirely off the current axis (e.g. when the chart is resampled to W/M or zoomed)
are skipped — never a garbage full-width band. Default ON (the signature); a chip +
D/W/M toggle are injected by the snippet, so NO extra dashboard.py controls are
needed. Reuses `chart_view` for the cpr_signals→segments transform. No circular dep.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.core.db import get_conn
from src.web import chart_view

router = APIRouter()

_TFS = ("D", "W", "M")
_COLS = "period_end_date,p,bc,tc,width_pct,pattern,regime,confirmed"


@router.get("/dash/cpr/overlay")
def cpr_overlay(sym: str = Query("", max_length=24)):
    """JSON: {D:[seg],W:[seg],M:[seg],confluence:[...]} for the stock-page Spine."""
    sym = sym.strip().upper()
    if not sym:
        return JSONResponse(None)
    out: dict = {}
    with get_conn() as conn:
        for tf in _TFS:
            cur = conn.execute(
                f"SELECT {_COLS} FROM cpr_signals WHERE symbol=? AND timeframe=? "
                "ORDER BY period_end_date",
                (sym, tf),
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            out[tf] = chart_view.cpr_segments(rows, tf)
    out["confluence"] = chart_view.confluence(out)
    if not any(out.get(tf) for tf in _TFS):
        return JSONResponse(None)
    return JSONResponse(out)


# Self-contained drawer. Plain string (NOT an f-string) so the JS braces survive;
# dashboard.py inserts it via its f-string template like `{_WF_SNIPPET}`.
SNIPPET = """<script>
(function(){
  var PC=null, CS=null, prim=null, byTf={}, conf=[], tf='W', on=true;
  function chipCss(a){ return 'cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:3px 9px;border-radius:20px;'+(a?'background:rgba(210,153,34,0.18);color:#e3b341':'border:1px solid #30363d;color:#8b949e'); }
  function tfCss(a){ return 'cursor:pointer;font-size:11px;padding:2px 6px;border-radius:5px;'+(a?'background:rgba(210,153,34,0.2);color:#e3b341':'color:#6e7681'); }
  function makePrim(){
    var segs=[], confl=[], series=null, req=null, vis=true;
    var view={ zOrder:function(){return 'bottom';}, renderer:function(){ return { draw:function(tg){
      if(!vis||!series||!PC) return;
      tg.useBitmapCoordinateSpace(function(sc){
        var x=sc.context,h=sc.horizontalPixelRatio,v=sc.verticalPixelRatio,W=sc.mediaSize.width,ts=PC.timeScale();
        confl.forEach(function(z){ var yh=series.priceToCoordinate(z.hi),yl=series.priceToCoordinate(z.lo); if(yh==null||yl==null) return;
          x.fillStyle='rgba(227,179,65,'+(z.degrees>=3?0.26:0.15)+')'; x.fillRect(0,Math.min(yh,yl)*v,W*h,Math.abs(yl-yh)*v);
          x.fillStyle='#e3b341'; x.font=(10*v)+'px sans-serif'; x.fillText('D\\u00B7W\\u00B7M',6*h,(Math.min(yh,yl)-3)*v); });
        segs.forEach(function(s){ var rx0=ts.timeToCoordinate(s.t0), rx1=ts.timeToCoordinate(s.t1);
          if(rx0==null&&rx1==null) return;  /* segment entirely off the current axis — skip, no garbage band */
          var x0=(rx0==null?0:rx0), x1=(rx1==null?W:rx1); if(x1<=x0) x1=x0+1;
          var yT=series.priceToCoordinate(s.tc),yB=series.priceToCoordinate(s.bc),yP=series.priceToCoordinate(s.p); if(yT==null||yB==null) return;
          var bx=x0*h,bw=(x1-x0)*h,by=yT*v,bh=(yB-yT)*v;
          x.fillStyle=s.regime>=0?'rgba(63,185,80,.10)':'rgba(248,81,73,.10)'; x.fillRect(bx,by,bw,bh);
          x.fillStyle=s.coil?'rgba(210,153,34,0.42)':'rgba(210,153,34,0.20)'; x.fillRect(bx,by,bw,bh);
          x.strokeStyle=s.coil?'rgba(240,193,80,0.92)':'rgba(210,153,34,0.50)'; x.lineWidth=(s.coil?1.3:0.9)*v;
          x.beginPath(); x.moveTo(bx,by); x.lineTo(bx+bw,by); x.moveTo(bx,by+bh); x.lineTo(bx+bw,by+bh); x.stroke();
          if(yP!=null){ x.strokeStyle='#d29922'; x.lineWidth=(s.coil?1.6:1.2)*v; x.setLineDash(s.coil?[]:[4*h,3*h]); x.beginPath(); x.moveTo(bx,yP*v); x.lineTo(bx+bw,yP*v); x.stroke(); x.setLineDash([]); } });
      });
    }};}};
    return { attached:function(p){series=p.series; req=p.requestUpdate;}, detached:function(){series=null;}, updateAllViews:function(){},
      paneViews:function(){return [view];}, setData:function(d){segs=d.segs||[]; confl=d.confl||[]; if(req)req();}, setVisible:function(b){vis=!!b; if(req)req();} };
  }
  function markers(){ if(!CS) return; var mk=[]; (byTf[tf]||[]).forEach(function(s){
      if(s.pattern==='BULL_U') mk.push({time:s.t1||s.t0,position:'belowBar',color:'#3fb950',shape:'arrowUp',text:'U'+(s.confirmed?'':'?')});
      else if(s.pattern==='BEAR_INVU') mk.push({time:s.t1||s.t0,position:'aboveBar',color:'#f85149',shape:'arrowDown',text:'\\u2229'+(s.confirmed?'':'?')}); });
    mk.sort(function(a,b){return a.time<b.time?-1:(a.time>b.time?1:0);}); CS.setMarkers(on?mk:[]); }
  function render(){ if(prim) prim.setData({segs:byTf[tf]||[], confl:conf}); markers(); }
  function inject(){ var host=document.getElementById('priceChart'); if(!host||document.getElementById('cprBar')) return;
    var bar=document.createElement('div'); bar.id='cprBar'; bar.style.cssText='display:flex;gap:6px;align-items:center;margin:6px 0 2px;font-family:-apple-system,Segoe UI,sans-serif';
    var chip=document.createElement('span'); chip.style.cssText=chipCss(on); chip.innerHTML='<span style="width:7px;height:7px;border-radius:50%;background:#d29922"></span>CPR spine';
    chip.title='Central Pivot Range — support/resistance bands; narrow = coiled (move pending)';
    chip.onclick=function(){ on=!on; if(prim) prim.setVisible(on); markers(); chip.style.cssText=chipCss(on); }; bar.appendChild(chip);
    var tfs={}; ['D','W','M'].forEach(function(k){ var b=document.createElement('span'); tfs[k]=b; b.textContent=k; b.style.cssText=tfCss(k===tf);
      b.onclick=function(){ tf=k; render(); ['D','W','M'].forEach(function(j){ tfs[j].style.cssText=tfCss(j===tf); }); }; bar.appendChild(b); });
    host.parentNode.insertBefore(bar, host.nextSibling);
  }
  function setup(){ prim=makePrim(); CS.attachPrimitive(prim); render(); inject(); }
  function boot(){ if(!window.__wfpc||!window.__wfcandle){ return setTimeout(boot,60); } PC=window.__wfpc; CS=window.__wfcandle;
    var sym=new URLSearchParams(location.search).get('sym')||''; if(!sym) return;
    fetch('/dash/cpr/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
      if(!d||(!(d.D||[]).length&&!(d.W||[]).length&&!(d.M||[]).length)) return; byTf={D:d.D||[],W:d.W||[],M:d.M||[]}; conf=d.confluence||[]; setup();
    }).catch(function(){}); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
</script>"""
