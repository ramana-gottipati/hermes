"""Self-contained JS snippet that overlays a Wolfe wave on the stock page's existing
lightweight-charts price chart (`window.__wfpc`).

dashboard.py exposes the chart as `window.__wfpc` (one line) and drops this SNIPPET
into the page (one `{token}`). It wires the `#wfChk` checkbox: on tick it fetches
/dash/wolfe/overlay?sym=… (wolfe_view.py → wolfe.overlay_for) which returns ALL
detected waves best-first by WolfeRank, then draws ONE at a time.

Convention (2026-06-24): BEAR = ascending wedge → sell at the upper Fib-confluence
zone (red); BULL = descending wedge → buy at the lower zone (green). The point-5 zone
is the strongest Fib overlap on the overshoot side; when 5 hasn't printed it is drawn
as the predicted point 5 (dashed projection + "5?").

De-cluttered by default — only the 1-2-3-4-(5) structure, pivot markers, the EPA
target, and the SINGLE strongest zone are shown. The two raw Fib grids (~13 lines
each), the 1-3 reference rail, and the weaker overlap zones are hidden behind a "grid"
toggle. A ‹ / › selector (and a "near" shortcut to the wave nearest current price)
cycles the detected setups. ALL controls are injected by this snippet into `#wfLbl`,
so dashboard.py / main.py are never touched. Overlay series opt out of autoscale so a
far zone never squishes the candles. No imports → no circular dep.
"""

SNIPPET = """<script>
(function(){
  var cb=document.getElementById('wfChk'); if(!cb) return;
  var lbl=document.getElementById('wfLbl');
  var WAVES=null, NEAR=0, wi=0, gridOn=false, main=[], grid=[];
  var NS={autoscaleInfoProvider:function(){return null;}};
  function mk(opts,data,bucket){
    var s=window.__wfpc.addLineSeries(Object.assign(
      {priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},opts,NS));
    s.setData(data); (bucket||main).push(s); return s;
  }
  function clear(){
    main.concat(grid).forEach(function(s){try{window.__wfpc.removeSeries(s);}catch(e){}});
    main=[]; grid=[];
  }
  function W(){ return WAVES[wi]; }
  function gridLines(arr,col){ if(!arr) return; var w=W();
    arr.forEach(function(f){ mk({color:col,lineWidth:1},
      [{time:w.p4_time,value:f.value},{time:w.last_time,value:f.value}], grid); }); }
  function drawWave(){
    if(!window.__wfpc||!WAVES) return;
    clear(); var w=W();
    // --- main (always shown while the overlay is on) -------------------------- //
    var ss=mk({color:w.color,lineWidth:2},w.struct); ss.setMarkers(w.markers);   // 1-2-3-4-(5)
    mk({color:w.color,lineWidth:1,lineStyle:2},w.epa);                            // EPA target
    if(w.p5pred){                                                                 // predicted 5 (FORMING)
      var sp=mk({color:w.color,lineWidth:1,lineStyle:2},
                [{time:w.p4_time,value:w.p4_value},{time:w.last_time,value:w.p5pred.value}]);
      sp.setMarkers([{time:w.last_time,position:(w.dir==='BEAR'?'aboveBar':'belowBar'),
                      color:w.color,shape:'circle',text:'5?'}]);
    }
    // strongest overlap zone -> main; weaker overlaps -> grid (secondary toggle)
    (w.zones||[]).forEach(function(z,zi){
      var s=mk({color:w.color,lineWidth:zi===0?2:1},
               [{time:w.p4_time,value:z.price},{time:w.last_time,value:z.price}], zi===0?main:grid);
      s.setMarkers([{time:w.last_time,position:(zi%2?'belowBar':'aboveBar'),color:w.color,
                     shape:'square',text:'Z'+(zi+1)+' '+z.price+' ('+z.r12+'x'+z.r34+')'}]);
    });
    // --- grid (hidden until the 'grid' toggle) -------------------------------- //
    gridLines(w.fib12,'rgba(88,166,255,0.22)');
    gridLines(w.fib34,'rgba(210,153,34,0.22)');
    mk({color:'#bb8009',lineWidth:1,lineStyle:2},w.line13,grid);                  // 1-3 reference rail
    grid.forEach(function(s){s.applyOptions({visible:gridOn});});
  }
  function setGrid(on){ gridOn=on; grid.forEach(function(s){s.applyOptions({visible:on});}); }
  function render(){
    if(!lbl) return; var n=WAVES.length, w=W();
    var nav = n>1 ? ('<span data-wf="prev" style="cursor:pointer">&#8249;</span> '+(wi+1)+'/'+n+
                     ' <span data-wf="next" style="cursor:pointer">&#8250;</span>'+
                     ' <span data-wf="near" style="cursor:pointer;color:#8b949e">near</span> &middot; ') : '';
    lbl.innerHTML = nav + w.summary +
                    ' &middot; <span data-wf="grid" style="cursor:pointer;text-decoration:underline;color:#8b949e">'+
                    (gridOn?'hide grid':'grid')+'</span>';
    lbl.querySelectorAll('[data-wf]').forEach(function(el){
      el.onclick=function(){
        var a=el.getAttribute('data-wf');
        if(a==='prev'){ wi=(wi-1+n)%n; drawWave(); render(); }
        else if(a==='next'){ wi=(wi+1)%n; drawWave(); render(); }
        else if(a==='near'){ wi=NEAR; drawWave(); render(); }
        else if(a==='grid'){ setGrid(!gridOn); render(); }
      };
    });
  }
  function load(){
    if(lbl) lbl.textContent='loading…';
    var sym=new URLSearchParams(location.search).get('sym')||'';
    fetch('/dash/wolfe/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
      if(!d||!d.waves||!d.waves.length){ WAVES=null; if(lbl) lbl.textContent='no Wolfe setup detected'; return; }
      WAVES=d.waves; NEAR=d.nearest||0; wi=d.default||0; drawWave(); render();
    }).catch(function(){ if(lbl) lbl.textContent='overlay error'; });
  }
  cb.addEventListener('change', function(){
    if(this.checked){ if(WAVES){ drawWave(); render(); } else load(); }
    else { clear(); if(lbl) lbl.textContent=''; }
  });
})();
</script>"""
