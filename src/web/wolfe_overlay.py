"""Self-contained JS snippet that overlays ONE Wolfe wave at a time on the stock page's
lightweight-charts price chart (`window.__wfpc`).

dashboard.py exposes the chart as `window.__wfpc`, a checkbox `#wfChk` and a label
`#wfLbl`, and drops this SNIPPET in (one token). On tick of `#wfChk` it fetches
/dash/wolfe/overlay?sym=… (wolfe.overlay_for) → {prediction, completed}. The snippet
injects ALL its own controls into `#wfLbl` (so dashboard.py is never touched) — two
sections Ramana navigates:

  • Prediction — the single most-recent FORMING wave at the current right edge: its
    1-2-3-4 structure, the extended **1-3 confirmation rail**, and the predicted-5 zone
    (the Fib overlap on the correct side of point 3). NO EPA — the wave isn't complete.
  • Completed (◄ ►) — every CONFIRMED Wolfe wave (point 5 printed), newest first. The
    ◄/► arrows walk back/forward through history; each press redraws the whole
    1-2-3-4-5 marking + that wave's Fib zones + its EPA, and pans the chart to it.

A "fib fans" link reveals the two full extension grids. Off by default; series opt out
of autoscale; best viewed in Candles mode. No imports.
"""

SNIPPET = """<script>
(function(){
  var cb=document.getElementById('wfChk'); if(!cb) return;
  var lbl=document.getElementById('wfLbl');
  var ser=[], fans=[], DATA=null, fansOn=false, mode='pred', di=0;
  var NS={autoscaleInfoProvider:function(){return null;}};
  function add(opts,data){ var s=window.__wfpc.addLineSeries(Object.assign({priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},opts,NS)); s.setData(data); ser.push(s); return s; }
  function clear(){ ser.forEach(function(s){try{window.__wfpc.removeSeries(s);}catch(e){}}); ser=[]; fans=[]; }
  function setFans(on){ fansOn=on; fans.forEach(function(s){try{s.applyOptions({visible:on});}catch(e){}}); }
  function fan(arr,col,w){ if(!arr) return; arr.forEach(function(f){ var s=add({color:col,lineWidth:1,lineStyle:0,visible:fansOn},[{time:w.struct[0].time,value:f.value},{time:w.last_time,value:f.value}]); fans.push(s); }); }
  function drawWave(w){
    var done = w.state==='CONFIRMED';
    var ss=add({color:w.color,lineWidth:2,lineStyle:0},w.struct); ss.setMarkers(w.markers);   // 1-2-3-4-(5)
    add({color:'#bb8009',lineWidth:1,lineStyle:2},w.line13);                                   // extended 1-3 rail
    if(done && w.epa){ add({color:w.color,lineWidth:1,lineStyle:0},w.epa); }                   // EPA — only after 5
    var bull=w.dir==='BULL';                                                                   // ALL Fib overlap zones, as
    var zfill=bull?'rgba(63,185,80,0.16)':'rgba(248,81,73,0.16)';                              // soft GREEN (bull) / RED (bear)
    var zedge=bull?'rgba(63,185,80,0.70)':'rgba(248,81,73,0.70)';                              // bands, minimal opacity
    var sv=w.struct.map(function(p){return p.value;});                                         // keep zones near the structure
    var sLo=Math.min.apply(null,sv), sHi=Math.max.apply(null,sv), sR=Math.max(sHi-sLo,sHi*0.02);
    (w.zones||[]).filter(function(z){return z.price>=sLo-sR && z.price<=sHi+sR;}).forEach(function(z,zi){
      var half=Math.max(Math.abs((z.high||z.price)-(z.low||z.price))/2, z.price*0.002);        // min visible band ~0.4%
      var lo=z.price-half, hi=z.price+half;
      var ai={autoscaleInfoProvider:function(){return {priceRange:{minValue:lo,maxValue:hi}};}};// pull the scale to include the band
      var s;
      try{
        s=window.__wfpc.addBaselineSeries(Object.assign({baseValue:{type:'price',price:lo},
          topFillColor1:zfill,topFillColor2:zfill,topLineColor:zedge,
          bottomFillColor1:'rgba(0,0,0,0)',bottomFillColor2:'rgba(0,0,0,0)',bottomLineColor:'rgba(0,0,0,0)',
          lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},ai));
        s.setData([{time:w.struct[0].time,value:hi},{time:w.last_time,value:hi}]);
      }catch(e){                                                                               // fallback if no baseline series
        s=window.__wfpc.addLineSeries(Object.assign({color:zedge,lineWidth:3,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},ai));
        s.setData([{time:w.struct[0].time,value:z.price},{time:w.last_time,value:z.price}]);
      }
      try{s.setMarkers([{time:w.last_time,position:(zi%2?'belowBar':'aboveBar'),color:zedge,shape:'square',text:z.price+' ('+z.r12+'∩'+z.r34+')'}]);}catch(e){}
      ser.push(s);
    });
    if(!done && w.p5pred){                                                                     // predicted 5 (forming)
      var sp=add({color:w.color,lineWidth:1,lineStyle:2},[{time:w.p4_time,value:w.p4_value},{time:w.last_time,value:w.p5pred.value}]);
      sp.setMarkers([{time:w.last_time,position:(w.dir==='BEAR'?'aboveBar':'belowBar'),color:w.color,shape:'circle',text:'5?'}]);
    }
    fan(w.fib12,'rgba(88,166,255,0.45)',w);                                                    // leg 1-2 extension fan
    fan(w.fib34,'rgba(210,153,34,0.45)',w);                                                    // leg 3-4 extension fan
    setFans(fansOn);
  }
  function panTo(w){ if(w&&w.pan_from&&w.pan_to){ try{ window.__wfpc.timeScale().setVisibleRange({from:w.pan_from,to:w.pan_to}); }catch(e){} } }
  function curWave(){
    if(!DATA) return null;
    if(mode==='pred') return DATA.prediction;
    var c=DATA.completed||[]; if(!c.length) return null; di=Math.max(0,Math.min(di,c.length-1)); return c[di];
  }
  function tab(id,on,txt){ return '<span id="'+id+'" style="cursor:pointer;padding:1px 8px;border-radius:4px;'+(on?'background:#1f6feb;color:#fff;':'color:#8b949e;border:1px solid #30363d')+'">'+txt+'</span>'; }
  function controls(){
    if(!lbl) return;
    var hasP=!!(DATA&&DATA.prediction), c=(DATA&&DATA.completed)||[];
    var h=tab('wfTabP',mode==='pred','Prediction'+(hasP?'':' (none)'))+' '+tab('wfTabC',mode==='done','Completed'+(c.length?' ('+c.length+')':' (none)'));
    if(mode==='done'&&c.length){
      h+=' &nbsp; <span id="wfPrev" title="previous (older) Wolfe" style="cursor:pointer;font-size:16px;padding:0 5px;color:#e6edf3">◄</span>'
       + ' <b>'+(di+1)+'/'+c.length+'</b> '
       + '<span id="wfNext" title="next (newer) Wolfe" style="cursor:pointer;font-size:16px;padding:0 5px;color:#e6edf3">►</span>';
    }
    var w=curWave();
    h+=' &nbsp;&middot;&nbsp; '+(w?w.summary:(mode==='pred'?'no forming wave':'no completed wave'));
    if(w) h+=' &nbsp;&middot; <span id="wfFans" style="cursor:pointer;text-decoration:underline;color:#8b949e">'+(fansOn?'hide fib fans':'fib fans')+'</span>';
    lbl.innerHTML=h;
    var e;
    if(e=document.getElementById('wfTabP')) e.onclick=function(){ mode='pred'; redraw(); };
    if(e=document.getElementById('wfTabC')) e.onclick=function(){ mode='done'; redraw(); };
    if(e=document.getElementById('wfPrev')) e.onclick=function(){ di++; redraw(); };   // older
    if(e=document.getElementById('wfNext')) e.onclick=function(){ di--; redraw(); };   // newer
    if(e=document.getElementById('wfFans')) e.onclick=function(){ setFans(!fansOn); controls(); };
  }
  function redraw(){ if(!window.__wfpc||!DATA) return; clear(); var w=curWave(); if(w){ drawWave(w); panTo(w); } controls(); }
  function load(){
    if(lbl) lbl.textContent='loading…';
    var sym=new URLSearchParams(location.search).get('sym')||'';
    fetch('/dash/wolfe/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
      if(!d||(!d.prediction&&(!d.completed||!d.completed.length))){ DATA=null; if(lbl) lbl.textContent='no Wolfe wave'; return; }
      DATA=d; mode=d.prediction?'pred':'done'; di=0; redraw();
    }).catch(function(){ if(lbl) lbl.textContent='overlay error'; });
  }
  cb.addEventListener('change', function(){
    if(this.checked){ if(DATA) redraw(); else load(); }
    else { clear(); if(lbl) lbl.textContent=''; }
  });
})();
</script>"""
