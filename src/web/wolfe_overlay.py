"""Self-contained JS snippet that overlays the (up to two) most-recent, clearest Wolfe
waves on the stock page's lightweight-charts price chart (`window.__wfpc`).

dashboard.py exposes the chart as `window.__wfpc` and drops this SNIPPET in (one token).
On tick of `#wfChk` it fetches /dash/wolfe/overlay?sym=… (wolfe_view.py → wolfe.overlay_for),
which returns up to two waves (a recent tight one + a bigger one of higher degree, e.g.
PARAS's May-Jun and Mar-Jun waves both ending at the Jun-19 high). For each wave it draws
the 1-2-3-4-(5) structure + numbered markers, the **1-3 confirmation rail** (point 5 only
counts once price crosses it — above for a sell, below for a buy), and the strong Fib
overlap zones. Wave 1 = solid + circle markers; wave 2 = dashed + square markers, so the
two are easy to tell apart. Off by default; series opt out of autoscale. No imports.
"""

SNIPPET = """<script>
(function(){
  var cb=document.getElementById('wfChk'); if(!cb) return;
  var lbl=document.getElementById('wfLbl');
  var ser=[], WAVES=null;
  var NS={autoscaleInfoProvider:function(){return null;}};
  function add(opts,data){ var s=window.__wfpc.addLineSeries(Object.assign({priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},opts,NS)); s.setData(data); ser.push(s); return s; }
  function clear(){ ser.forEach(function(s){try{window.__wfpc.removeSeries(s);}catch(e){}}); ser=[]; }
  function drawWave(w){
    var dash = w.dashed ? 2 : 0;
    var ss=add({color:w.color,lineWidth:2,lineStyle:dash},w.struct); ss.setMarkers(w.markers);
    add({color:'#bb8009',lineWidth:1,lineStyle:2},w.line13);                 // 1-3 confirmation rail
    (w.zones||[]).slice(0,2).forEach(function(z,zi){
      var zl=add({color:w.color,lineWidth:zi===0?2:1,lineStyle:dash},
                 [{time:w.struct[0].time,value:z.price},{time:w.last_time,value:z.price}]);
      zl.setMarkers([{time:w.last_time,position:(zi%2?'belowBar':'aboveBar'),color:w.color,shape:'square',text:'Z '+z.price}]);
    });
    if(w.p5pred){                                                            // 5 not printed yet
      var sp=add({color:w.color,lineWidth:1,lineStyle:2},[{time:w.p4_time,value:w.p4_value},{time:w.last_time,value:w.p5pred.value}]);
      sp.setMarkers([{time:w.last_time,position:(w.dir==='BEAR'?'aboveBar':'belowBar'),color:w.color,shape:'circle',text:'5?'}]);
    }
  }
  function drawAll(){
    if(!window.__wfpc||!WAVES) return;
    clear(); WAVES.forEach(drawWave);
    if(lbl) lbl.innerHTML = WAVES.map(function(w,i){return 'W'+(i+1)+' '+w.summary;}).join('  &nbsp;·&nbsp;  ');
  }
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
