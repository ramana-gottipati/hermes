"""Self-contained JS snippet that overlays the most-recent Wolfe wave on the stock
page's existing lightweight-charts price chart (`window.__wfpc`).

dashboard.py exposes the chart as `window.__wfpc` (one line) and drops this SNIPPET
into the page (one `{token}`). The snippet wires the `#wfChk` checkbox: on tick it
fetches /dash/wolfe/overlay?sym=… (wolfe_view.py) and draws the structure (1-5),
the 1-3 line, the EPA target, pivot markers, the two Fib-extension grids and the
strong overlap zones (now projected toward the overshoot — above for a sell). Off by
default. Overlay series opt out of autoscale so a far level never squishes the
candles. No imports → no circular dep.
"""

SNIPPET = """<script>
(function(){
  var cb=document.getElementById('wfChk'); if(!cb) return;
  var lbl=document.getElementById('wfLbl');
  var ser=[], ss=null, sp=null, loaded=false, WF=null;
  var NS={autoscaleInfoProvider:function(){return null;}};
  function add(opts,data){ var s=window.__wfpc.addLineSeries(Object.assign(opts,NS)); s.setData(data); ser.push(s); return s; }
  function p5mk(){ return [{time:WF.last_time,position:(WF.dir==='BEAR'?'aboveBar':'belowBar'),color:WF.color,shape:'circle',text:'5?'}]; }
  function draw(){
    if(!window.__wfpc||!WF) return;
    ss=add({color:WF.color,lineWidth:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},WF.struct);
    ss.setMarkers(WF.markers);
    add({color:'#bb8009',lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},WF.line13);
    add({color:WF.color,lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},WF.epa);
    if(WF.p5pred){
      sp=add({color:WF.color,lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},
             [{time:WF.p4_time,value:WF.p4_value},{time:WF.last_time,value:WF.p5pred.value}]);
      sp.setMarkers(p5mk());
    }
    function grid(arr,col){ if(!arr) return; arr.forEach(function(f){
      add({color:col,lineWidth:1,lineStyle:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},
          [{time:WF.p4_time,value:f.value},{time:WF.last_time,value:f.value}]);
    }); }
    grid(WF.fib12,'rgba(88,166,255,0.30)');
    grid(WF.fib34,'rgba(210,153,34,0.30)');
    if(WF.zones) WF.zones.forEach(function(z){
      var zl=add({color:WF.color,lineWidth:2,lineStyle:0,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},
                 [{time:WF.struct[0].time,value:z.price},{time:WF.last_time,value:z.price}]);
      zl.setMarkers([{time:WF.last_time,position:'inBar',color:WF.color,shape:'square',text:('Z '+z.price)}]);
    });
  }
  function show(on){
    ser.forEach(function(s){s.applyOptions({visible:on});});
    if(ss) ss.setMarkers(on?WF.markers:[]);
    if(sp) sp.setMarkers(on?p5mk():[]);
  }
  cb.addEventListener('change', function(){
    if(this.checked){
      if(loaded){ if(WF) show(true); else if(lbl) lbl.textContent='no Wolfe setup detected'; return; }
      loaded=true; if(lbl) lbl.textContent='loading…';
      var sym=new URLSearchParams(location.search).get('sym')||'';
      fetch('/dash/wolfe/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
        WF=d;
        if(!WF||!WF.struct){ if(lbl) lbl.textContent='no Wolfe setup detected'; return; }
        draw(); if(lbl) lbl.textContent=WF.summary;
      }).catch(function(){ loaded=false; if(lbl) lbl.textContent='overlay error'; });
    } else { show(false); if(lbl) lbl.textContent=''; }
  });
})();
</script>"""
