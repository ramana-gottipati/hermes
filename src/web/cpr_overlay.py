"""/dash/cpr/overlay — the CPR Spine on the stock page's EXISTING price chart.

Mirrors `wolfe_overlay.py`: a JSON endpoint (CPR segments from cpr_signals) + a
self-contained SNIPPET that draws the CPR Spine as a primitive on the existing candle
series (`window.__wfcandle`). Reuses `chart_view` for the cpr_signals→segments transform.

Ramana's corrections (2026-06-24):
  * Default OFF — it's a proprietary strategy you call up, not a default. Lives in a
    "Strategies" chip group, fetch-on-first-toggle.
  * The CPR **degree follows the chart's timeframe** — daily chart → daily CPR, weekly →
    weekly, monthly → monthly (it hooks the existing D/W/M/Q interval buttons; quarterly
    has no CPR so it hides). No independent CPR timeframe toggle.
  * The U / ∩ reversal marker sits on the **middle candle** (C1, the valley/peak). The
    pattern is flagged in cpr_signals on C0 (the signal bar); the flagged segment's `t0`
    IS C1's date, so the marker uses `s.t0`.
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


# Plain string (NOT an f-string) so the JS braces survive; dashboard.py inserts it
# via its f-string template like `{_WF_SNIPPET}`.
SNIPPET = """<script>
(function(){
  var PC=null, CS=null, prim=null, byTf={}, conf=[], tf='D', on=false, loaded=false;
  // CPR degree follows the chart's interval button (data-ptf): d->D w->W m->M q->none.
  function ivTf(){ var b=document.querySelector('[data-ptf].on'); var p=b?b.dataset.ptf:'d'; return p==='w'?'W':(p==='m'?'M':(p==='q'?null:'D')); }
  function chipCss(a){ return 'cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:3px 9px;border-radius:20px;'+(a?'background:rgba(210,153,34,0.18);color:#e3b341':'border:1px solid #30363d;color:#8b949e'); }
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
          if(rx0==null&&rx1==null) return; var x0=(rx0==null?0:rx0), x1=(rx1==null?W:rx1); if(x1<=x0) x1=x0+1;
          var yT=series.priceToCoordinate(s.tc),yB=series.priceToCoordinate(s.bc),yP=series.priceToCoordinate(s.p); if(yT==null||yB==null) return;
          var bx=x0*h,bw=(x1-x0)*h,by=yT*v,bh=(yB-yT)*v;
          x.fillStyle=s.regime>=0?'rgba(63,185,80,.10)':'rgba(248,81,73,.10)'; x.fillRect(bx,by,bw,bh);
          x.fillStyle=s.coil?'rgba(210,153,34,0.42)':'rgba(210,153,34,0.20)'; x.fillRect(bx,by,bw,bh);
          x.strokeStyle=s.coil?'rgba(240,193,80,0.92)':'rgba(210,153,34,0.50)'; x.lineWidth=(s.coil?1.3:0.9)*v;
          x.beginPath(); x.moveTo(bx,by); x.lineTo(bx+bw,by); x.moveTo(bx,by+bh); x.lineTo(bx+bw,by+bh); x.stroke();
          if(yP!=null){ x.strokeStyle='#d29922'; x.lineWidth=(s.coil?1.6:1.2)*v; x.setLineDash(s.coil?[]:[4*h,3*h]); x.beginPath(); x.moveTo(bx,yP*v); x.lineTo(bx+bw,yP*v); x.stroke(); x.setLineDash([]); } });
      });
    }};}};
    return { attached:function(p){series=p.series; req=p.requestUpdate;}, detached:function(){series=null;}, updateAllViews:function(){}, paneViews:function(){return [view];}, setData:function(d){segs=d.segs||[]; confl=d.confl||[]; if(req)req();}, setVisible:function(b){vis=!!b; if(req)req();} };
  }
  function markers(){ if(!CS) return; var mk=[]; var segs=tf?(byTf[tf]||[]):[];
    segs.forEach(function(s){
      // marker on the MIDDLE candle (C1) — pattern flagged on C0; flagged seg t0 == C1 date
      if(s.pattern==='BULL_U') mk.push({time:s.t0,position:'belowBar',color:'#3fb950',shape:'arrowUp',text:'U'+(s.confirmed?'':'?')});
      else if(s.pattern==='BEAR_INVU') mk.push({time:s.t0,position:'aboveBar',color:'#f85149',shape:'arrowDown',text:'\\u2229'+(s.confirmed?'':'?')}); });
    mk.sort(function(a,b){return a.time<b.time?-1:(a.time>b.time?1:0);}); CS.setMarkers((on&&tf)?mk:[]); }
  function render(){ if(prim) prim.setData({segs:(tf?(byTf[tf]||[]):[]), confl:conf}); markers(); }
  function setChip(){ var c=document.getElementById('cprChip'); if(c) c.style.cssText=chipCss(on); }
  function applyTf(){ tf=ivTf(); if(!on) return; if(!tf){ if(prim) prim.setVisible(false); if(CS) CS.setMarkers([]); return; } if(prim) prim.setVisible(true); render(); }
  function toggle(){ on=!on; setChip();
    if(on){ if(loaded){ applyTf(); return; } loaded=true; var sym=new URLSearchParams(location.search).get('sym')||'';
      fetch('/dash/cpr/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
        if(!d){ on=false; setChip(); return; } byTf={D:d.D||[],W:d.W||[],M:d.M||[]}; conf=d.confluence||[];
        prim=makePrim(); CS.attachPrimitive(prim); tf=ivTf(); render();
      }).catch(function(){ loaded=false; on=false; setChip(); });
    } else { if(prim) prim.setVisible(false); if(CS) CS.setMarkers([]); }
  }
  function inject(){ var host=document.getElementById('priceChart'); if(!host||document.getElementById('cprChip')) return;
    var bar=document.getElementById('stratBar');
    if(!bar){ bar=document.createElement('div'); bar.id='stratBar'; bar.style.cssText='display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:6px 0 2px;font-family:-apple-system,Segoe UI,sans-serif';
      var l=document.createElement('span'); l.textContent='Strategies'; l.style.cssText='font-size:10px;letter-spacing:.4px;text-transform:uppercase;color:#6e7681;margin-right:2px'; bar.appendChild(l);
      host.parentNode.insertBefore(bar, host.nextSibling); }
    var chip=document.createElement('span'); chip.id='cprChip'; chip.style.cssText=chipCss(on);
    chip.innerHTML='<span style="width:7px;height:7px;border-radius:50%;background:#d29922"></span>CPR';
    chip.title='Central Pivot Range \\u2014 follows the chart timeframe; narrow band = coiled (move pending)'; chip.onclick=toggle;
    bar.appendChild(chip);
  }
  function hookIv(){ document.querySelectorAll('[data-ptf]').forEach(function(b){ b.addEventListener('click', function(){ setTimeout(applyTf,0); }); }); }
  function boot(){ if(!window.__wfpc||!window.__wfcandle){ return setTimeout(boot,60); } PC=window.__wfpc; CS=window.__wfcandle; tf=ivTf(); inject(); hookIv(); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
</script>"""
