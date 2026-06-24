"""Moving-average overlay for the stock page's EXISTING price chart.

Mirrors `cpr_overlay.py` / `wolfe_overlay.py`: a self-contained SNIPPET (NO router —
reads the price data already on the page via `window.__wfdata`) that draws EMA
20/50/200 as a canvas primitive ON the existing candle series (`window.__wfcandle`).
Drawing it as a primitive (not a line series) means it never pollutes the chart's
shared time axis and degrades cleanly when the chart is resampled to W/M or zoomed
(off-axis points are simply skipped). Toggle chips are injected (50/200 default ON,
20 OFF). dashboard.py exposes `window.__wfdata = DATA` (one line) + drops one
`{token}` next to the others. No DB, no endpoint, no circular dep.
"""
from __future__ import annotations

# Plain string (NOT an f-string) so the JS braces survive; dashboard.py inserts it
# via its f-string template like `{_WF_SNIPPET}` / `{_CPR_SNIPPET}`.
SNIPPET = """<script>
(function(){
  var defs=[{n:20,c:'#8b949e',on:false},{n:50,c:'#58a6ff',on:true},{n:200,c:'#d29922',on:true}];
  var PC=null, CS=null, prim=null;
  function ema(S,n){ var k=2/(n+1), out=[], e=null, sum=0;
    for(var i=0;i<S.length;i++){ var c=S[i].close;
      if(i<n-1){ sum+=c; continue; }
      if(i===n-1){ sum+=c; e=sum/n; } else { e=c*k+e*(1-k); }
      out.push({time:S[i].time, value:e}); }
    return out; }
  function hexA(hex,a){ var h=hex.replace('#',''); return 'rgba('+parseInt(h.slice(0,2),16)+','+parseInt(h.slice(2,4),16)+','+parseInt(h.slice(4,6),16)+','+a+')'; }
  function makePrim(){ var series=null, req=null;
    var view={ zOrder:function(){return 'top';}, renderer:function(){ return { draw:function(tg){
      if(!series||!PC) return;
      tg.useBitmapCoordinateSpace(function(sc){
        var x=sc.context,h=sc.horizontalPixelRatio,v=sc.verticalPixelRatio,ts=PC.timeScale();
        defs.forEach(function(o){ if(!o.on||!o.pts) return;
          x.strokeStyle=o.c; x.lineWidth=1.2*v; x.beginPath(); var pen=false;
          for(var i=0;i<o.pts.length;i++){ var p=o.pts[i], cx=ts.timeToCoordinate(p.time), cy=series.priceToCoordinate(p.value);
            if(cx==null||cy==null){ pen=false; continue; }
            if(!pen){ x.moveTo(cx*h,cy*v); pen=true; } else { x.lineTo(cx*h,cy*v); } }
          x.stroke(); });
      });
    }};}};
    return { attached:function(p){series=p.series; req=p.requestUpdate;}, detached:function(){series=null;}, updateAllViews:function(){}, paneViews:function(){return [view];}, redraw:function(){ if(req) req(); } };
  }
  function chipCss(o){ return 'cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:3px 9px;border-radius:20px;'+(o.on?('background:'+hexA(o.c,0.16)+';color:'+o.c):('border:1px solid #30363d;color:#8b949e')); }
  function inject(){ var host=document.getElementById('priceChart'); if(!host||document.getElementById('maBar')) return;
    var bar=document.createElement('div'); bar.id='maBar'; bar.style.cssText='display:flex;gap:6px;align-items:center;margin:4px 0 2px;font-family:-apple-system,Segoe UI,sans-serif';
    var l=document.createElement('span'); l.textContent='Indicators'; l.style.cssText='font-size:10px;letter-spacing:.4px;text-transform:uppercase;color:#6e7681;margin-right:2px'; bar.appendChild(l);
    defs.forEach(function(o){ var c=document.createElement('span');
      function paint(){ c.style.cssText=chipCss(o); c.innerHTML='<span style="width:7px;height:7px;border-radius:50%;background:'+o.c+'"></span>MA '+o.n; }
      paint(); c.onclick=function(){ o.on=!o.on; if(prim) prim.redraw(); paint(); }; bar.appendChild(c); });
    var anchor=document.getElementById('cprBar')||host; anchor.parentNode.insertBefore(bar, anchor.nextSibling);
  }
  function boot(){ if(!window.__wfpc||!window.__wfcandle||!window.__wfdata||!window.__wfdata.series){ return setTimeout(boot,60); }
    PC=window.__wfpc; CS=window.__wfcandle; var S=window.__wfdata.series; if(!S.length) return;
    defs.forEach(function(o){ o.pts=ema(S,o.n); });
    prim=makePrim(); CS.attachPrimitive(prim); inject();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
</script>"""
