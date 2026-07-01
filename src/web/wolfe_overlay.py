"""Self-contained JS snippet that overlays ONE Wolfe wave at a time on the stock page's
lightweight-charts price chart (`window.__wfpc`).

dashboard.py exposes the chart as `window.__wfpc`, a checkbox `#wfChk` and a label
`#wfLbl`, and drops this SNIPPET in (one token). On tick of `#wfChk` it fetches
/dash/wolfe/overlay?sym=… (wolfe.overlay_for) → {prediction, completed, bars}. The
snippet injects ALL its own controls into `#wfLbl` (so dashboard.py is never touched).
Three modes Ramana navigates:

  • Prediction — the single most-recent FORMING wave at the current right edge: its
    1-2-3-4 structure, the extended **1-3 confirmation rail**, and the predicted-5 zone
    (the Fib overlap on the correct side of point 3). NO EPA — the wave isn't complete.
  • Completed (◄ ►) — every CONFIRMED Wolfe wave (point 5 printed), newest first. The
    ◄/► arrows walk back/forward through history; each press redraws the whole
    1-2-3-4-5 marking + that wave's Fib zones + its EPA, and pans the chart to it.
  • ✎ Draw your own — the analyst clicks points 1→5 on the candle chart (each snapped to
    the nearer real bar high/low); the machine draws the structure and computes the EXACT
    standard Fib EXTENSIONS and their strong OVERLAP zones — on HIS pivots. The count is
    always his, so auto-pivot segmentation can never mis-count his wave (the recurring
    complaint that prompted commit b7ad360). The Fib math here mirrors wolfe.fib_zones
    byte-for-byte: EXTENSIONS only (1.272/1.414/1.618/2.618/3.618/4.236/4.618), each leg
    normalised to (low,high) and projected toward the overshoot, overlap tol 2%, dedupe 2%
    (verified: his 968.1/1066.75/1075.5/1133 → 2.618∩2.618 = 1226.2). Ascending wedge =
    SELL (red, zones above); descending = BUY (green, zones below). DESCRIPTIVE only —
    draws the geometry + zones, never a buy/sell verdict.

A "fib fans" link reveals the two full extension grids. Off by default; series opt out
of autoscale; best viewed in Candles mode. No imports.
"""

SNIPPET = """<script>
(function(){
  var cb=document.getElementById('wfChk'); if(!cb) return;
  var lbl=document.getElementById('wfLbl');
  var ser=[], fans=[], DATA=null, fansOn=false, mode='pred', di=0;
  var BARS=null, manual=[], manualZones=[], probe=null, clickWired=false;
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
    var zfill=bull?'rgba(63,212,134,0.16)':'rgba(255,106,122,0.16)';                              // soft GREEN (bull) / RED (bear)
    var zedge=bull?'rgba(63,212,134,0.70)':'rgba(255,106,122,0.70)';                              // bands, minimal opacity
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
  function tab(id,on,txt){ return '<span id="'+id+'" style="cursor:pointer;padding:1px 8px;border-radius:4px;'+(on?'background:#1f6feb;color:#fff;':'color:var(--ink-2);border:1px solid var(--line-2)')+'">'+txt+'</span>'; }

  // -------------------------- MANUAL "✎ draw your own" -------------------------- //
  // Mirrors wolfe.fib_zones BYTE-FOR-BYTE: EXTENSIONS only, leg normalised to (lo,hi)
  // and projected toward the overshoot; overlap tol 2%, dedupe 2%, top 6.
  var FIB_R=[1.272,1.414,1.618,2.618,3.618,4.236,4.618];
  function fibZones(p1,p2,p3,p4,bear){
    var lo12=Math.min(p1,p2),hi12=Math.max(p1,p2),lo34=Math.min(p3,p4),hi34=Math.max(p3,p4);
    var e12={},e34={};
    FIB_R.forEach(function(r){
      if(bear){ e12[r]=lo12+r*(hi12-lo12); e34[r]=lo34+r*(hi34-lo34); }     // BEAR overshoot UP
      else    { e12[r]=hi12-r*(hi12-lo12); e34[r]=hi34-r*(hi34-lo34); }     // BULL overshoot DOWN
    });
    var raw=[];
    FIB_R.forEach(function(r1){ FIB_R.forEach(function(r2){
      var v1=e12[r1], v2=e34[r2], mid=(v1+v2)/2;
      if(mid && Math.abs(v1-v2)<=0.02*Math.abs(mid))
        raw.push({price:Math.round(mid*100)/100,r12:r1,r34:r2,
                  low:Math.round(Math.min(v1,v2)*100)/100,high:Math.round(Math.max(v1,v2)*100)/100,tight:Math.abs(v1-v2)});
    });});
    raw.sort(function(a,b){return a.tight-b.tight;});
    var z=[];
    raw.forEach(function(c){
      if(z.some(function(k){return Math.abs(c.price-k.price)<=0.02*Math.abs(c.price);})) return;
      z.push({price:c.price,r12:c.r12,r34:c.r34,low:c.low,high:c.high});
    });
    return z.slice(0,6);
  }
  function ensureProbe(){
    // coordinateToPrice needs the series to carry data, but seeding with the full bar
    // history would add foreign dates to the shared time scale and push the candles
    // off-screen. Seed just 2 points at the CURRENT visible range (already on the scale)
    // — enough to make coordinateToPrice resolve, zero scale disturbance.
    if(!probe){ probe=window.__wfpc.addLineSeries(Object.assign({visible:false},NS));
      try{ var vr=window.__wfpc.timeScale().getVisibleRange();
        if(vr){ probe.setData([{time:vr.from,value:0},{time:vr.to,value:0}]); }
        else if(BARS&&BARS.length){ probe.setData([{time:BARS[0].t,value:0},{time:BARS[BARS.length-1].t,value:0}]); }
      }catch(e){}
    }
    return probe;
  }
  function normTime(t){
    if(t==null) return null;
    if(typeof t==='string') return t;
    if(typeof t==='object'&&t.year) return t.year+'-'+('0'+t.month).slice(-2)+'-'+('0'+t.day).slice(-2);
    return ''+t;
  }
  function snap(tstr,price){                                                 // snap to the nearer real bar high/low
    if(!BARS) return price;
    for(var i=0;i<BARS.length;i++){ if(BARS[i].t===tstr){ var b=BARS[i];
      return (Math.abs(price-b.h)<=Math.abs(price-b.l))? b.h : b.l; } }
    return price;
  }
  function rightTime(){ return (BARS&&BARS.length)? BARS[BARS.length-1].t : (manual.length? manual[manual.length-1].time : null); }
  function isHigh(i){ var L=manual.length;
    if(L===1) return false;
    if(i===0) return manual[0].value>manual[1].value;
    if(i===L-1) return manual[i].value>manual[i-1].value;
    return manual[i].value>=manual[i-1].value && manual[i].value>=manual[i+1].value;
  }
  function drawManual(){
    clear();
    if(manual.length<1) return;
    var asc = manual.length>=4 ? (manual[3].value>manual[1].value) : (manual[manual.length-1].value>=manual[0].value);
    var bear = asc;                                                          // ascending wedge = SELL/BEAR
    var col = bear? '#ff6a7a' : '#3fd486';
    // lightweight-charts needs ascending, unique times — sort + dedupe so an out-of-order
    // or same-bar click can't throw (markers keep their click number).
    var seen={}, lineData=[], marks=[];
    manual.map(function(p,i){return {p:p,i:i};})
      .sort(function(a,b){return a.p.time<b.p.time?-1:(a.p.time>b.p.time?1:0);})
      .forEach(function(o){ if(seen[o.p.time]) return; seen[o.p.time]=1;
        lineData.push({time:o.p.time,value:o.p.value});
        marks.push({time:o.p.time,position:(isHigh(o.i)?'aboveBar':'belowBar'),color:col,shape:'circle',text:''+(o.i+1)}); });
    var ss=add({color:col,lineWidth:2},lineData); ss.setMarkers(marks);
    manualZones=[];
    if(manual.length>=4){
      var z=fibZones(manual[0].value,manual[1].value,manual[2].value,manual[3].value,bear);
      var rt=rightTime(), p4t=manual[3].time;
      var over=z.filter(function(x){return bear? x.price>manual[3].value : x.price<manual[3].value;});
      var ordered=over.concat(z.filter(function(x){return over.indexOf(x)<0;}));   // overshoot-side first
      manualZones=ordered;
      ordered.forEach(function(x,zi){
        var s=add({color:col,lineWidth:zi===0?2:1},[{time:p4t,value:x.price},{time:rt,value:x.price}]);
        s.setMarkers([{time:rt,position:(zi%2?'belowBar':'aboveBar'),color:col,shape:'square',text:'Z'+(zi+1)+' '+x.price+' ('+x.r12+'∩'+x.r34+')'}]);
      });
    }
  }
  function onClick(param){
    if(mode!=='draw'||!param||!param.point||param.time==null) return;
    var price=ensureProbe().coordinateToPrice(param.point.y);
    if(price==null) return;
    var t=normTime(param.time);
    manual.push({time:t,value:Math.round(snap(t,price)*100)/100});
    drawManual(); controls();
  }
  function enterDraw(){
    mode='draw'; clear(); manual=[]; manualZones=[]; ensureProbe();
    if(!clickWired){ try{ window.__wfpc.subscribeClick(onClick); }catch(e){} clickWired=true; }
    controls();
  }
  function exitDraw(){
    clear(); manual=[]; manualZones=[];
    mode=(DATA&&DATA.prediction)?'pred':'done'; di=0; redraw();
  }
  function drawLink(){ return ' &nbsp;&middot; <span id="wfDraw" style="cursor:pointer;text-decoration:underline;color:#58a6ff">✎ draw your own</span>'; }
  function wireDraw(){ var e;
    if(e=document.getElementById('wfDraw')) e.onclick=function(){ enterDraw(); };
  }
  function renderDraw(){
    if(!lbl) return;
    var labels=['1','2','3','4','5 (overshoot, optional)'];
    var next = manual.length<5 ? ('click point '+labels[manual.length]) : '5 points placed';
    var placed = manual.length? (' &middot; '+manual.map(function(p,i){return (i+1)+':'+p.value;}).join('  ')) : '';
    var zs = manualZones.length? (' &nbsp;&middot; <b style="color:#d29922">zones:</b> '+
      manualZones.map(function(x,i){return 'Z'+(i+1)+' '+x.price+' ('+x.r12+'∩'+x.r34+')';}).join('  &middot; ')) : '';
    lbl.innerHTML='<b style="color:#58a6ff">✎ DRAW</b> '+next+zs+
      ' &nbsp;&middot; <span id="wfUndo" style="cursor:pointer;text-decoration:underline">undo</span>'+
      ' &middot; <span id="wfReset" style="cursor:pointer;text-decoration:underline">reset</span>'+
      ' &middot; <span id="wfAuto" style="cursor:pointer;text-decoration:underline;color:var(--ink-2)">use auto</span>'+placed;
    var e;
    if(e=document.getElementById('wfUndo')) e.onclick=function(){ manual.pop(); drawManual(); controls(); };
    if(e=document.getElementById('wfReset')) e.onclick=function(){ manual=[]; manualZones=[]; drawManual(); controls(); };
    if(e=document.getElementById('wfAuto')) e.onclick=function(){ exitDraw(); };
  }
  function controls(){
    if(!lbl) return;
    if(mode==='draw'){ renderDraw(); return; }
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
    h+=drawLink();
    lbl.innerHTML=h;
    var e;
    if(e=document.getElementById('wfTabP')) e.onclick=function(){ mode='pred'; redraw(); };
    if(e=document.getElementById('wfTabC')) e.onclick=function(){ mode='done'; redraw(); };
    if(e=document.getElementById('wfPrev')) e.onclick=function(){ di++; redraw(); };   // older
    if(e=document.getElementById('wfNext')) e.onclick=function(){ di--; redraw(); };   // newer
    if(e=document.getElementById('wfFans')) e.onclick=function(){ setFans(!fansOn); controls(); };
    wireDraw();
  }
  function redraw(){
    if(mode==='draw'){ controls(); return; }
    if(!window.__wfpc||!DATA){ controls(); return; }
    clear(); var w=curWave(); if(w){ drawWave(w); panTo(w); } controls();
  }
  function load(){
    if(lbl) lbl.textContent='loading…';
    var sym=new URLSearchParams(location.search).get('sym')||'';
    fetch('/dash/wolfe/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
      BARS=(d&&d.bars)||null;
      if(!d||(!d.prediction&&(!d.completed||!d.completed.length))){
        DATA=d||null;
        if(lbl){ lbl.innerHTML='no auto Wolfe wave'+drawLink(); wireDraw(); }   // still let him draw his own
        return;
      }
      DATA=d; mode=d.prediction?'pred':'done'; di=0; redraw();
    }).catch(function(){ if(lbl) lbl.textContent='overlay error'; });
  }
  cb.addEventListener('change', function(){
    if(this.checked){ if(DATA||BARS!==null) redraw(); else load(); }
    else { clear(); manual=[]; manualZones=[]; mode='pred'; if(lbl) lbl.textContent=''; }
  });
})();
</script>"""
