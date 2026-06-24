"""Self-contained JS snippet that overlays the (up to two) most-recent, clearest Wolfe
waves on the stock page's lightweight-charts price chart (`window.__wfpc`).

dashboard.py exposes the chart as `window.__wfpc` and drops this SNIPPET in (one token).
On tick of `#wfChk` it fetches /dash/wolfe/overlay?sym=… (wolfe.overlay_for) → up to two
waves. For each it draws the 1-2-3-4-(5) structure + numbered markers, the **1-3
confirmation rail** (point 5 only counts once price crosses it — above for a sell, below
for a buy), and the **strong Fibonacci overlap zones** — the levels where the extension
fan on leg 1-2 coincides with the fan on leg 3-4 (Ramana's targets), each labelled with
its price and the ratio pair (e.g. `1226 (2.618∩2.618)`). A "fib fans" toggle reveals the
two full extension grids. Wave 1 = solid/circle markers; wave 2 = dashed/square. Off by
default; series opt out of autoscale; best viewed in Candles mode. No imports.
"""

SNIPPET = """<script>
(function(){
  var cb=document.getElementById('wfChk'); if(!cb) return;
  var lbl=document.getElementById('wfLbl');
  var ser=[], fans=[], WAVES=null, fansOn=false;
  var NS={autoscaleInfoProvider:function(){return null;}};
  function add(opts,data,bucket){ var s=window.__wfpc.addLineSeries(Object.assign({priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},opts,NS)); s.setData(data); (bucket||ser).push(s); return s; }
  function clear(){ ser.concat(fans).forEach(function(s){try{window.__wfpc.removeSeries(s);}catch(e){}}); ser=[]; fans=[]; }
  function fan(arr,col,w){ if(!arr) return; arr.forEach(function(f){
    add({color:col,lineWidth:1,lineStyle:0,visible:fansOn},
        [{time:w.struct[0].time,value:f.value},{time:w.last_time,value:f.value}], fans); }); }
  function drawWave(w){
    var dash=w.dashed?2:0;
    var ss=add({color:w.color,lineWidth:2,lineStyle:dash},w.struct); ss.setMarkers(w.markers);   // 1-2-3-4-(5)
    add({color:'#bb8009',lineWidth:1,lineStyle:2},w.line13);                                     // 1-3 rail
    (w.zones||[]).slice(0,3).forEach(function(z,zi){                                             // Fib overlap zones
      var zl=add({color:w.color,lineWidth:zi===0?2:1,lineStyle:dash},
                 [{time:w.struct[0].time,value:z.price},{time:w.last_time,value:z.price}]);
      zl.setMarkers([{time:w.last_time,position:(zi%2?'belowBar':'aboveBar'),color:w.color,shape:'square',
                      text:z.price+' ('+z.r12+'∩'+z.r34+')'}]);
    });
    if(w.p5pred){                                                                                // 5 not printed yet
      var sp=add({color:w.color,lineWidth:1,lineStyle:2},[{time:w.p4_time,value:w.p4_value},{time:w.last_time,value:w.p5pred.value}]);
      sp.setMarkers([{time:w.last_time,position:(w.dir==='BEAR'?'aboveBar':'belowBar'),color:w.color,shape:'circle',text:'5?'}]);
    }
    fan(w.fib12,'rgba(88,166,255,0.45)',w);                                                      // leg 1-2 extension fan
    fan(w.fib34,'rgba(210,153,34,0.45)',w);                                                      // leg 3-4 extension fan
  }
  function setFans(on){ fansOn=on; fans.forEach(function(s){s.applyOptions({visible:on});}); }
  function renderLbl(){
    if(!lbl) return;
    lbl.innerHTML = WAVES.map(function(w,i){return 'W'+(i+1)+' '+w.summary;}).join('  &nbsp;·&nbsp;  ')
      + ' &middot; <span id="wfFans" style="cursor:pointer;text-decoration:underline;color:#8b949e">'+(fansOn?'hide fib fans':'fib fans')+'</span>';
    var f=document.getElementById('wfFans'); if(f) f.onclick=function(){ setFans(!fansOn); renderLbl(); };
  }
  function drawAll(){ if(!window.__wfpc||!WAVES) return; clear(); WAVES.forEach(drawWave); setFans(fansOn); renderLbl(); }
  function load(){
    if(lbl) lbl.textContent='loading…';
    var sym=new URLSearchParams(location.search).get('sym')||'';
    fetch('/dash/wolfe/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
      if(!d||!d.waves||!d.waves.length){ WAVES=null; if(lbl) lbl.textContent='no recent Wolfe wave'; return; }
      WAVES=d.waves; drawAll();
    }).catch(function(){ if(lbl) lbl.textContent='overlay error'; });
  }
  cb.addEventListener('change', function(){
    if(this.checked){ if(WAVES) drawAll(); else load(); }
    else { clear(); if(lbl) lbl.textContent=''; }
  });
})();
</script>"""
