"""Self-contained JS snippet that overlays a Wolfe wave on the stock page's existing
lightweight-charts price chart (`window.__wfpc`).

Two modes, both injected by this snippet (so dashboard.py / main.py stay untouched —
it only needs the `#wfChk` checkbox, the `#wfLbl` span, and `window.__wfpc`):

  • AUTO — fetches /dash/wolfe/overlay?sym=… (all detected waves, best-first by
    WolfeRank), draws ONE at a time (structure + EPA + the single strongest zone by
    default; Fib grids / 1-3 rail / weaker zones behind a "grid" toggle), with a
    ‹ ›/near setup selector.
  • DRAW — "draw your own": the analyst clicks points 1→5 on the chart (each snapped
    to the nearer real bar high/low); the machine draws the structure and computes the
    EXACT standard Fib extensions level(r)=a+r·(b−a) on swings 1→2 & 3→4 and their
    STRONG overlap zones — on HIS pivots. The count is always his, so the auto-pivot
    segmentation can never mis-count his wave again (the recurring complaint). The Fib
    math here mirrors wolfe.fib_zones byte-for-byte (verified: his 968.1/1066.75/
    1075.5/1133 → 1226.2).

Convention (2026-06-24): ascending wedge (lows & highs rising) = SELL, red, zones
above; descending = BUY, green, zones below. Overlay series opt out of autoscale so a
far zone never squishes the candles. No imports → no circular dep.
"""

SNIPPET = """<script>
(function(){
  var cb=document.getElementById('wfChk'); if(!cb) return;
  var lbl=document.getElementById('wfLbl');
  var WAVES=null, NEAR=0, wi=0, gridOn=false, mode='auto';
  var main=[], grid=[], draw=[], manual=[], manualZones=[];
  var BARS=null, probe=null, clickWired=false;
  var NS={autoscaleInfoProvider:function(){return null;}};
  var RATIOS=[0.236,0.382,0.5,0.618,0.786,1.0,1.272,1.414,1.618,2.0,2.618,3.618,4.236];
  function C(){ return window.__wfpc; }
  function mk(bucket,opts,data){
    var s=C().addLineSeries(Object.assign({priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},opts,NS));
    s.setData(data); bucket.push(s); return s;
  }
  function wipe(b){ b.forEach(function(s){try{C().removeSeries(s);}catch(e){}}); b.length=0; }
  function clearAll(){ wipe(main); wipe(grid); wipe(draw); }

  // ----------------------------- AUTO overlay ----------------------------- //
  function W(){ return WAVES[wi]; }
  function gridLines(arr,col){ if(!arr) return; var w=W();
    arr.forEach(function(f){ mk(grid,{color:col,lineWidth:1},[{time:w.p4_time,value:f.value},{time:w.last_time,value:f.value}]); }); }
  function drawAuto(){
    if(!C()||!WAVES) return;
    wipe(main); wipe(grid); var w=W();
    var ss=mk(main,{color:w.color,lineWidth:2},w.struct); ss.setMarkers(w.markers);
    mk(main,{color:w.color,lineWidth:1,lineStyle:2},w.epa);
    if(w.p5pred){
      var sp=mk(main,{color:w.color,lineWidth:1,lineStyle:2},[{time:w.p4_time,value:w.p4_value},{time:w.last_time,value:w.p5pred.value}]);
      sp.setMarkers([{time:w.last_time,position:(w.dir==='BEAR'?'aboveBar':'belowBar'),color:w.color,shape:'circle',text:'5?'}]);
    }
    (w.zones||[]).forEach(function(z,zi){
      var s=mk(zi===0?main:grid,{color:w.color,lineWidth:zi===0?2:1},[{time:w.p4_time,value:z.price},{time:w.last_time,value:z.price}]);
      s.setMarkers([{time:w.last_time,position:(zi%2?'belowBar':'aboveBar'),color:w.color,shape:'square',text:'Z'+(zi+1)+' '+z.price+' ('+z.r12+'x'+z.r34+')'}]);
    });
    gridLines(w.fib12,'rgba(88,166,255,0.22)'); gridLines(w.fib34,'rgba(210,153,34,0.22)');
    mk(grid,{color:'#bb8009',lineWidth:1,lineStyle:2},w.line13);
    grid.forEach(function(s){s.applyOptions({visible:gridOn});});
  }

  // ----------------------------- MANUAL draw ------------------------------ //
  function fibZones(p1,p2,p3,p4){
    var e12=RATIOS.map(function(r){return {r:r,v:p1+r*(p2-p1)};});
    var e34=RATIOS.map(function(r){return {r:r,v:p3+r*(p4-p3)};});
    var raw=[];
    e12.forEach(function(a){ e34.forEach(function(b){
      var mid=(a.v+b.v)/2;
      if(mid && Math.abs(a.v-b.v)<=0.004*Math.abs(mid))
        raw.push({price:Math.round(mid*100)/100,r12:a.r,r34:b.r,
                  low:Math.round(Math.min(a.v,b.v)*100)/100,high:Math.round(Math.max(a.v,b.v)*100)/100,tight:Math.abs(a.v-b.v)});
    });});
    raw.sort(function(x,y){return x.tight-y.tight;});
    var z=[];
    raw.forEach(function(c){
      if(z.some(function(k){return Math.abs(c.price-k.price)<=0.004*Math.abs(c.price);})) return;
      z.push({price:c.price,r12:c.r12,r34:c.r34,low:c.low,high:c.high});
    });
    return z.slice(0,4);
  }
  function ensureProbe(){
    // coordinateToPrice needs the series to carry data, but seeding with the full bar
    // history would add foreign dates to the shared time scale and push the candles
    // off-screen. Seed just 2 points at the candle's CURRENT visible times (already on
    // the scale) — enough to make coordinateToPrice resolve, zero scale disturbance.
    if(!probe){ probe=C().addLineSeries(Object.assign({visible:false},NS));
      try{ var vr=C().timeScale().getVisibleRange();
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
  function snap(tstr,price){
    if(!BARS) return price;
    for(var i=0;i<BARS.length;i++){ if(BARS[i].t===tstr){ var b=BARS[i];
      return (Math.abs(price-b.h)<=Math.abs(price-b.l))? b.h : b.l; } }
    return price;
  }
  function rightTime(){ return (BARS&&BARS.length)? BARS[BARS.length-1].t : (manual.length? manual[manual.length-1].time : null); }
  function isHigh(p,i){ var L=manual.length;
    if(L===1) return false;
    if(i===0) return manual[0].value>manual[1].value;
    if(i===L-1) return manual[i].value>manual[i-1].value;
    return manual[i].value>=manual[i-1].value && manual[i].value>=manual[i+1].value;
  }
  function drawManual(){
    wipe(draw);
    if(manual.length<1) return;
    var asc = manual.length>=4 ? (manual[3].value>manual[1].value) : (manual[manual.length-1].value>=manual[0].value);
    var col = asc? '#f85149' : '#3fb950';   // ascending wedge = SELL(red) / descending = BUY(green)
    // lightweight-charts needs ascending, unique times — sort + dedupe so an
    // out-of-order or same-bar click can't throw (markers keep their click number).
    var seen={}, lineData=[], marks=[];
    manual.map(function(p,i){return {p:p,i:i};})
      .sort(function(a,b){return a.p.time<b.p.time?-1:(a.p.time>b.p.time?1:0);})
      .forEach(function(o){ if(seen[o.p.time]) return; seen[o.p.time]=1;
        lineData.push({time:o.p.time,value:o.p.value});
        marks.push({time:o.p.time,position:(isHigh(o.p,o.i)?'aboveBar':'belowBar'),color:col,shape:'circle',text:''+(o.i+1)}); });
    var ss=mk(draw,{color:col,lineWidth:2},lineData); ss.setMarkers(marks);
    manualZones=[];
    if(manual.length>=4){
      var z=fibZones(manual[0].value,manual[1].value,manual[2].value,manual[3].value);
      var rt=rightTime(), p4t=manual[3].time;
      var over=z.filter(function(x){return asc? x.price>manual[3].value : x.price<manual[3].value;});
      var ordered=over.concat(z.filter(function(x){return over.indexOf(x)<0;}));
      manualZones=ordered;
      ordered.forEach(function(x,zi){
        var s=mk(draw,{color:col,lineWidth:zi===0?2:1},[{time:p4t,value:x.price},{time:rt,value:x.price}]);
        s.setMarkers([{time:rt,position:(zi%2?'belowBar':'aboveBar'),color:col,shape:'square',text:'Z'+(zi+1)+' '+x.price+' ('+x.r12+'x'+x.r34+')'}]);
      });
    }
  }
  function onClick(param){
    if(mode!=='draw'||!param||!param.point||param.time==null) return;
    var price=ensureProbe().coordinateToPrice(param.point.y);
    if(price==null) return;
    var t=normTime(param.time);
    manual.push({time:t,value:Math.round(snap(t,price)*100)/100});
    drawManual(); renderDraw();
  }

  // ----------------------------- label / UI ------------------------------- //
  function wire(){
    if(!lbl) return;
    lbl.querySelectorAll('[data-wf]').forEach(function(el){
      el.onclick=function(){
        var a=el.getAttribute('data-wf'), n=WAVES?WAVES.length:0;
        if(a==='prev'){ wi=(wi-1+n)%n; drawAuto(); renderAuto(); }
        else if(a==='next'){ wi=(wi+1)%n; drawAuto(); renderAuto(); }
        else if(a==='near'){ wi=NEAR; drawAuto(); renderAuto(); }
        else if(a==='grid'){ gridOn=!gridOn; grid.forEach(function(s){s.applyOptions({visible:gridOn});}); renderAuto(); }
        else if(a==='draw'){ enterDraw(); }
        else if(a==='undo'){ manual.pop(); drawManual(); renderDraw(); }
        else if(a==='reset'){ manual=[]; drawManual(); renderDraw(); }
        else if(a==='auto'){ exitDraw(); }
      };
    });
  }
  var DRAWLINK=' &middot; <span data-wf="draw" style="cursor:pointer;text-decoration:underline;color:#58a6ff">✎ draw your own</span>';
  function renderAuto(){
    if(!lbl) return; var n=WAVES.length, w=W();
    var nav = n>1 ? ('<span data-wf="prev" style="cursor:pointer">&#8249;</span> '+(wi+1)+'/'+n+
                     ' <span data-wf="next" style="cursor:pointer">&#8250;</span>'+
                     ' <span data-wf="near" style="cursor:pointer;color:#8b949e">near</span> &middot; ') : '';
    lbl.innerHTML = nav + w.summary +
      ' &middot; <span data-wf="grid" style="cursor:pointer;text-decoration:underline;color:#8b949e">'+(gridOn?'hide grid':'grid')+'</span>'+DRAWLINK;
    wire();
  }
  function renderDraw(){
    if(!lbl) return;
    var labels=['1 (low)','2 (high)','3 (low)','4 (high)','5 (overshoot, optional)'];
    var next = manual.length<5 ? ('click point '+labels[manual.length]) : '5 points placed';
    var placed = manual.length? (' &middot; '+manual.map(function(p,i){return (i+1)+':'+p.value;}).join('  ')) : '';
    var zs = manualZones.length? (' &middot; <b style="color:#d29922">zones:</b> '+
      manualZones.map(function(x,i){return 'Z'+(i+1)+' '+x.price+' ('+x.r12+'x'+x.r34+')';}).join('  &middot; ')) : '';
    lbl.innerHTML = '<b style="color:#58a6ff">DRAW</b> '+next+zs+
      ' &middot; <span data-wf="undo" style="cursor:pointer;text-decoration:underline">undo</span>'+
      ' &middot; <span data-wf="reset" style="cursor:pointer;text-decoration:underline">reset</span>'+
      ' &middot; <span data-wf="auto" style="cursor:pointer;text-decoration:underline;color:#8b949e">use auto</span>'+placed;
    wire();
  }
  function enterDraw(){
    mode='draw'; wipe(main); wipe(grid); manual=[]; wipe(draw); ensureProbe();
    if(!clickWired){ C().subscribeClick(onClick); clickWired=true; }
    renderDraw();
  }
  function exitDraw(){
    mode='auto'; wipe(draw); manual=[];
    if(WAVES){ drawAuto(); renderAuto(); }
    else if(lbl){ lbl.innerHTML='no auto setup'+DRAWLINK; wire(); }
  }

  function load(){
    if(lbl) lbl.textContent='loading…';
    var sym=new URLSearchParams(location.search).get('sym')||'';
    fetch('/dash/wolfe/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
      BARS=(d&&d.bars)||null;
      if(!d||!d.waves||!d.waves.length){ WAVES=null; if(lbl){ lbl.innerHTML='no auto setup'+DRAWLINK; wire(); } return; }
      WAVES=d.waves; NEAR=d.nearest||0; wi=d.default||0; mode='auto'; drawAuto(); renderAuto();
    }).catch(function(){ if(lbl) lbl.textContent='overlay error'; });
  }
  cb.addEventListener('change', function(){
    if(this.checked){ if(WAVES){ mode='auto'; drawAuto(); renderAuto(); } else load(); }
    else { clearAll(); mode='auto'; manual=[]; if(lbl) lbl.textContent=''; }
  });
})();
</script>"""
