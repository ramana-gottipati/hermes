"""/dash/cpr/overlay — the CPR Spine on the stock page's EXISTING price chart.

Mirrors `wolfe_overlay.py`: a JSON endpoint (CPR segments from cpr_signals) + a
self-contained SNIPPET that draws the CPR Spine as a primitive on the existing candle
series (`window.__wfcandle`). Reuses `chart_view` for the cpr_signals→segments transform.

Ramana's model (2026-06-24):
  * Default OFF — a proprietary strategy you call up. Lives in a "Strategies" chip group.
  * **Ladder — the CPR is ONE degree HIGHER than the chart** (higher-TF S/R for the TF you
    trade): daily chart → **Weekly** CPR, weekly → **Monthly**, monthly → **Half-yearly**,
    quarterly → Half-yearly. Hooks the existing D/W/M/Q interval buttons.
  * The U/∩ marker sits on the **middle candle** (C1, the valley/peak): the pattern is
    flagged on C0 in cpr_signals, and the flagged segment's `t0` IS C1's date → marker uses `s.t0`.
  * Bands/markers are **snapped onto the current chart's bars** so e.g. a monthly band lands
    on the weekly axis even though month-ends aren't week-ends.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.core.db import get_conn
from src.web import chart_view

router = APIRouter()

_TFS = ("D", "W", "M", "H")
_COLS = "period_end_date,p,bc,tc,width_pct,pattern,regime,confirmed"


@router.get("/dash/cpr/overlay")
def cpr_overlay(sym: str = Query("", max_length=24)):
    """JSON: {D,W,M,H:[seg], confluence:[...]} for the stock-page Spine (the ladder)."""
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


# Plain string (NOT an f-string) so the JS braces survive; dashboard.py inserts it.
SNIPPET = """<script>
(function(){
  var PC=null, CS=null, prim=null, byTf={}, conf=[], tf='W', on=false, loaded=false;
  function ivOf(){ var b=document.querySelector('[data-ptf].on'); return b?b.dataset.ptf:'d'; }
  // CPR degree = ONE step higher than the chart (Ramana's ladder).
  function ivTf(){ var p=ivOf(); return p==='d'?'W':(p==='w'?'M':(p==='m'?'H':(p==='q'?'H':'W'))); }
  function chipCss(a){ return 'cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:3px 9px;border-radius:20px;'+(a?'background:rgba(210,153,34,0.18);color:#e3b341':'border:1px solid #30363d;color:#8b949e'); }
  // --- snap CPR period-boundary dates onto the CURRENT chart bars ---
  function isoWk(s){ var d=new Date(s+'T00:00:00Z'),jd=(d.getUTCDay()+6)%7; d.setUTCDate(d.getUTCDate()-jd+3); var iy=d.getUTCFullYear(),j4=new Date(Date.UTC(iy,0,4)),j4d=(j4.getUTCDay()+6)%7; j4.setUTCDate(j4.getUTCDate()-j4d+3); return iy+'-W'+('0'+(1+Math.round((d-j4)/(7*864e5)))).slice(-2); }
  function pkey(s,iv){ if(iv==='w') return isoWk(s); if(iv==='m') return s.slice(0,7); if(iv==='q'){var y=s.slice(0,4),mo=parseInt(s.slice(5,7),10); return y+'-Q'+(Math.floor((mo-1)/3)+1);} return s; }
  function chartBars(){ var iv=ivOf(), S=(window.__wfdata&&window.__wfdata.series)||[], out=[], k=null; for(var i=0;i<S.length;i++){ var kk=pkey(S[i].time,iv); if(kk!==k){k=kk; out.push(S[i].time);} else out[out.length-1]=S[i].time; } return out; }
  function snapDate(bars,t){ var lo=0,hi=bars.length-1,a=-1; while(lo<=hi){var m=(lo+hi)>>1; if(bars[m]<=t){a=m;lo=m+1;}else hi=m-1;} return a<0?null:bars[a]; }
  function makePrim(){
    var segs=[], confl=[], bars=[], series=null, req=null, vis=true;
    var view={ zOrder:function(){return 'bottom';}, renderer:function(){ return { draw:function(tg){
      if(!vis||!series||!PC) return;
      tg.useBitmapCoordinateSpace(function(sc){
        var x=sc.context,h=sc.horizontalPixelRatio,v=sc.verticalPixelRatio,W=sc.mediaSize.width,ts=PC.timeScale();
        function sx(t){ var dt=snapDate(bars,t); return dt==null?null:ts.timeToCoordinate(dt); }
        confl.forEach(function(z){ var yh=series.priceToCoordinate(z.hi),yl=series.priceToCoordinate(z.lo); if(yh==null||yl==null) return;
          x.fillStyle='rgba(227,179,65,'+(z.degrees>=3?0.26:0.15)+')'; x.fillRect(0,Math.min(yh,yl)*v,W*h,Math.abs(yl-yh)*v);
          x.fillStyle='#e3b341'; x.font=(10*v)+'px sans-serif'; x.fillText('D\\u00B7W\\u00B7M',6*h,(Math.min(yh,yl)-3)*v); });
        segs.forEach(function(s){ var rx0=sx(s.t0), rx1=sx(s.t1);
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
    return { attached:function(p){series=p.series; req=p.requestUpdate;}, detached:function(){series=null;}, updateAllViews:function(){}, paneViews:function(){return [view];}, setData:function(d){segs=d.segs||[]; confl=d.confl||[]; bars=d.bars||[]; if(req)req();}, setVisible:function(b){vis=!!b; if(req)req();} };
  }
  function markers(){ if(!CS) return; var bars=chartBars(); var mk=[]; var segs=tf?(byTf[tf]||[]):[];
    segs.forEach(function(s){ if(s.pattern!=='BULL_U'&&s.pattern!=='BEAR_INVU') return; var t=snapDate(bars,s.t0); if(t==null) return;
      // marker on the MIDDLE candle (C1) — flagged seg t0 == C1 date, snapped to the chart bar
      if(s.pattern==='BULL_U') mk.push({time:t,position:'belowBar',color:'#3fb950',shape:'arrowUp',text:'U'+(s.confirmed?'':'?')});
      else mk.push({time:t,position:'aboveBar',color:'#f85149',shape:'arrowDown',text:'\\u2229'+(s.confirmed?'':'?')}); });
    mk.sort(function(a,b){return a.time<b.time?-1:(a.time>b.time?1:0);});
    var seen={}, uniq=[]; for(var i=0;i<mk.length;i++){ if(!seen[mk[i].time]){ seen[mk[i].time]=1; uniq.push(mk[i]); } }
    CS.setMarkers((on&&tf)?uniq:[]); }
  function render(){ if(prim) prim.setData({segs:(tf?(byTf[tf]||[]):[]), confl:conf, bars:chartBars()}); markers(); }
  function setChip(){ var c=document.getElementById('cprChip'); if(c) c.style.cssText=chipCss(on); }
  function applyTf(){ tf=ivTf(); if(!on) return; if(!tf){ if(prim) prim.setVisible(false); if(CS) CS.setMarkers([]); return; } if(prim) prim.setVisible(true); render(); }
  function toggle(){ on=!on; setChip();
    if(on){ if(loaded){ applyTf(); return; } loaded=true; var sym=new URLSearchParams(location.search).get('sym')||'';
      fetch('/dash/cpr/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
        if(!d){ on=false; setChip(); return; } byTf={D:d.D||[],W:d.W||[],M:d.M||[],H:d.H||[]}; conf=d.confluence||[];
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
    chip.title='Central Pivot Range \\u2014 one degree higher than the chart (daily\\u2192weekly, weekly\\u2192monthly, monthly\\u2192half-yearly)'; chip.onclick=toggle;
    bar.appendChild(chip);
  }
  function hookIv(){ document.querySelectorAll('[data-ptf]').forEach(function(b){ b.addEventListener('click', function(){ setTimeout(applyTf,0); }); }); }
  function boot(){ if(!window.__wfpc||!window.__wfcandle){ return setTimeout(boot,60); } PC=window.__wfpc; CS=window.__wfcandle; tf=ivTf(); inject(); hookIv(); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
</script>"""
