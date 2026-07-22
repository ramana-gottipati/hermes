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

  AUTO-DRAW (Ramana 2026-07-11): "auto-snap" (ON by default; toggle in the DRAW bar) pulls
  points 1/3/5 onto the local LOWS and 2/4 onto the local HIGHS of a BULL wave (reversed on a
  BEAR) — direction is read from points 1->2 — so a click near a pivot lands ON it. Two guards
  (S204) keep the magnet honest: it NEVER moves two points onto the same bar (that silently
  dropped the later point at draw — the "point 3 becomes point 1" bug), and it NEVER teleports a
  click that falls outside the snap payload to the payload edge (the exact click is kept). The
  snap payload (wolfe.overlay_for -> `bars`) covers the FULL chart history so a pivot years back
  (S204: BATAINDIA point 1 in 2021) still snaps and its bar index resolves. The EPA (1-4) target
  line is drawn AS SOON AS point 4 is in (before point 5) and extended to the right edge; the
  1-2 and 3-4 legs
  are extended too so their intersection is visible. A STRICT gate warns "The distance between
  points 1 and 2 is less than the distance between points 3 and 4." whenever leg 3-4 exceeds
  leg 1-2. Any point is editable: double-click it on the chart (or click its chip) then click
  to drop it. Still DESCRIPTIVE-only.

A "fib fans" link reveals the two full extension grids. Off by default; series opt out
of autoscale; best viewed in Candles mode. No imports.
"""

SNIPPET = """<script>
(function(){
  var cb=document.getElementById('wfChk'); if(!cb) return;
  var lbl=document.getElementById('wfLbl');
  var ser=[], fans=[], DATA=null, fansOn=false, mode='pred', di=0;
  var BARS=null, manual=[], manualZones=[], probe=null, clickWired=false, keyWired=false;
  var autosnap=true, editing=null, wfWarn='', redoStack=[], wDirty=false;      // draw: magnet ON (Ramana) — guarded; redoStack powers Ctrl+Y redo; wDirty = user drew since enter (persistence race guard)
  var NS={autoscaleInfoProvider:function(){return null;}};
  function add(opts,data){ var s=window.__wfpc.addLineSeries(Object.assign({priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},opts,NS)); s.setData(data); ser.push(s); return s; }
  function clear(){ ser.forEach(function(s){try{window.__wfpc.removeSeries(s);}catch(e){}}); ser=[]; fans=[]; }
  function setFans(on){ fansOn=on; fans.forEach(function(s){try{s.applyOptions({visible:on});}catch(e){}}); }
  function fan(arr,col,w,tag){ if(!arr) return; arr.forEach(function(f){ var s=add({color:col,lineWidth:1,lineStyle:0,visible:fansOn},[{time:w.struct[0].time,value:f.value},{time:w.last_time,value:f.value}]);
    // name every grid line (leg + ratio + price) — an unlabeled fan is unreadable
    try{ s.setMarkers([{time:w.last_time,position:'inBar',color:col,shape:'square',text:tag+'\\u00d7'+f.r+' '+f.value}]); }catch(e){}
    fans.push(s); }); }
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
    fan(w.fib12,'rgba(88,166,255,0.45)',w,'1-2 ');                                             // leg 1-2 extension fan
    fan(w.fib34,'rgba(210,153,34,0.45)',w,'3-4 ');                                             // leg 3-4 extension fan
    setFans(fansOn);
  }
  function panTo(w){ if(w&&w.pan_from&&w.pan_to){ try{ window.__wfpc.timeScale().setVisibleRange({from:w.pan_from,to:w.pan_to}); }catch(e){} } }
  // -------- badge (top of the chart): direction · points/total · rank ---------
  // Fixed at the top so it stays put while the chart stays static (Ramana: no zoom on nav).
  var badgeEl=null;
  function ensureBadge(){
    if(badgeEl) return badgeEl;
    var host=document.getElementById('priceChart'); if(!host) return null;
    if(getComputedStyle(host).position==='static') host.style.position='relative';
    badgeEl=document.createElement('div');
    badgeEl.style.cssText='position:absolute;top:8px;left:50%;transform:translateX(-50%);z-index:6;'+
      'font:600 12px -apple-system,Segoe UI,sans-serif;padding:4px 12px;border-radius:14px;'+
      'pointer-events:none;white-space:nowrap;box-shadow:0 1px 5px rgba(0,0,0,.45)';
    host.appendChild(badgeEl);
    return badgeEl;
  }
  function waveRank(w){                       // rank of w within the CURRENT section, by points
    if(mode!=='open'&&mode!=='closed') return null;
    var lst=listFor(mode); if(!lst.length) return null;
    var pts=(w.points!=null?w.points:0), better=0;
    for(var i=0;i<lst.length;i++){ if((lst[i].points!=null?lst[i].points:0)>pts) better++; }
    return {rank:better+1, total:lst.length};
  }
  function updateBadge(w){
    var b=ensureBadge(); if(!b) return;
    if(!w||mode==='draw'){ b.style.display='none'; return; }
    var bull=w.dir==='BULL', col=bull?'#3fd486':'#ff6a7a', rk=waveRank(w);
    b.style.display='block';
    b.style.background=bull?'rgba(63,212,134,0.16)':'rgba(255,106,122,0.16)';
    b.style.color=col; b.style.border='1px solid '+col;
    b.innerHTML=(bull?'\\u25b2 BULL':'\\u25bc BEAR')
      +' &nbsp;\\u00b7&nbsp; '+(w.points!=null?w.points:'?')+'/'+(w.points_max||24)+' pts'
      +(rk?' &nbsp;\\u00b7&nbsp; rank #'+rk.rank+'/'+rk.total:'');
  }
  function hideBadge(){ if(badgeEl) badgeEl.style.display='none'; }
  // Ramana's 3 sections, all from the SAME confirmed-wave list — filtered by lifecycle,
  // NOTHING hidden: open = point 5 in, EPA target not yet reached (the actionable now);
  // closed = EPA reached (reference + how neatly). Prediction = forming (no point 5).
  function listFor(m){
    var c=(DATA&&DATA.completed)||[];
    if(m==='open') return c.filter(function(w){return w.lifecycle==='open';});
    if(m==='closed') return c.filter(function(w){return w.lifecycle==='closed';});
    return c;
  }
  function defaultMode(){
    if(listFor('open').length) return 'open';       // the current live setups first
    if(DATA&&DATA.prediction) return 'pred';
    if(listFor('closed').length) return 'closed';
    return 'pred';
  }
  function curWave(){
    if(!DATA) return null;
    if(mode==='pred') return DATA.prediction;
    var c=listFor(mode); if(!c.length) return null; di=Math.max(0,Math.min(di,c.length-1)); return c[di];
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
  // ---- auto-draw helpers (Ramana, 2026-07-11): snap 1/3/5 to lows & 2/4 to highs on a BULL
  //      wave (reversed on a BEAR); direction read from points 1->2. ----
  var SNAPW=3;
  function barIx(ts){ if(!BARS) return -1; for(var i=0;i<BARS.length;i++){ if(BARS[i].t===ts) return i; } return -1; }
  function nearestBar(ts){ if(!BARS) return -1; var tv=Date.parse(ts); if(isNaN(tv)) return barIx(ts);
    var best=-1,bd=1e18; for(var i=0;i<BARS.length;i++){ var d=Math.abs(Date.parse(BARS[i].t)-tv); if(d<bd){bd=d;best=i;} } return best; }
  function snapExtreme(bar,kind){ var best=bar, bp=(kind==='low'?BARS[bar].l:BARS[bar].h);
    for(var j=Math.max(0,bar-SNAPW);j<=Math.min(BARS.length-1,bar+SNAPW);j++){ var v=(kind==='low'?BARS[j].l:BARS[j].h);
      if(kind==='low'? v<bp : v>bp){ bp=v; best=j; } } return {t:BARS[best].t, v:bp}; }
  function dirBull(){ return manual.length>=2 ? (manual[1].value>manual[0].value) : null; }
  function roleKind(i,bull){ var low=(i%2===0); return bull? (low?'low':'high') : (low?'high':'low'); }
  function occupiedBy(idx,ts){ for(var k=0;k<manual.length;k++){ if(k===idx) continue;   // is bar `ts` already held by ANOTHER placed point?
      var kb=barIx(manual[k].time); if(kb<0) kb=nearestBar(manual[k].time); if(kb>=0 && BARS[kb].t===ts) return true; } return false; }
  function resnap(){ if(!BARS||!BARS.length) return; var bull=dirBull();        // re-pin every placed point to its role extreme
    for(var i=0;i<manual.length;i++){ var p=manual[i], exact=barIx(p.time), bar=exact; if(bar<0) bar=nearestBar(p.time); if(bar<0) continue;
      // out-of-window guard: a click older than the snap payload (barIx miss + nearest real bar >5d away)
      // must NOT teleport to the window edge — keep the EXACT click (the 800-bar cap in wolfe.overlay_for).
      if(exact<0){ var dd=Math.abs(Date.parse(BARS[bar].t)-Date.parse(p.time)); if(isNaN(dd)||dd>5*864e5){ p.value=Math.round(p.value*100)/100; continue; } }
      if(autosnap && bull!==null){ var s=snapExtreme(bar,roleKind(i,bull));
        // NEVER collapse two points onto one bar — that silently drops the later point at draw
        // (the "point 3 becomes point 1" bug). On collision fall back to a gentle same-bar snap.
        if(occupiedBy(i,s.t)){ var bb=BARS[bar]; s={t:BARS[bar].t, v:(Math.abs(p.value-bb.h)<=Math.abs(p.value-bb.l))? bb.h : bb.l}; }
        p.time=s.t; p.value=s.v; }
      else { var b=BARS[bar]; p.value=(Math.abs(p.value-b.h)<=Math.abs(p.value-b.l))? b.h : b.l; }
      p.value=Math.round(p.value*100)/100; } }
  function nearestManual(ts){ var cb=barIx(ts); if(cb<0) cb=nearestBar(ts); if(cb<0) return null;
    var best=null,bd=4; for(var i=0;i<manual.length;i++){ var pb=barIx(manual[i].time); if(pb<0) pb=nearestBar(manual[i].time);
      var d=Math.abs(pb-cb); if(d<bd){ bd=d; best=i; } } return best; }
  function legLenPx(i,j){ try{ var tsc=window.__wfpc.timeScale();                // leg length as DRAWN (pixels); price-Δ fallback
      var xi=tsc.timeToCoordinate(manual[i].time), xj=tsc.timeToCoordinate(manual[j].time);
      var yi=ensureProbe().priceToCoordinate(manual[i].value), yj=ensureProbe().priceToCoordinate(manual[j].value);
      if(xi!=null&&xj!=null&&yi!=null&&yj!=null){ var dx=xj-xi,dy=yj-yi; return Math.sqrt(dx*dx+dy*dy); } }catch(e){}
    return Math.abs(manual[j].value-manual[i].value); }
  function onDbl(ev){ if(mode!=='draw'||!manual.length) return;                 // double-click a point on the chart -> edit it
    try{ var el=window.__wfpc.chartElement(); if(!el) return; var r=el.getBoundingClientRect();
      var tt=window.__wfpc.timeScale().coordinateToTime(ev.clientX-r.left); if(tt==null) return;
      var idx=nearestManual(normTime(tt)); if(idx!=null){ editing=idx; drawManual(); controls(); if(ev.preventDefault) ev.preventDefault(); } }catch(e){} }
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
    var warns=wolfeWarnings();                                                // P3/P4 directional placement checks (from point 3 on)
    if(manual.length>=4){
      var rt2=rightTime(), rb=(BARS?BARS.length-1:-1);
      var b0=barIx(manual[0].time), b1=barIx(manual[1].time), b2=barIx(manual[2].time), b3=barIx(manual[3].time);
      if(b0>=0&&b3>=0&&b3!==b0&&rb>=0){                                        // EPA = 1-4 line, drawn AT point 4 (before 5), extended right
        var epaSl=(manual[3].value-manual[0].value)/(b3-b0), epaR=Math.round((manual[0].value+epaSl*(rb-b0))*100)/100;
        var eL=add({color:'#e3a008',lineWidth:2,lineStyle:0},[{time:manual[0].time,value:manual[0].value},{time:rt2,value:epaR}]);
        try{ eL.setMarkers([{time:rt2,position:'inBar',color:'#e3a008',shape:'square',text:'EPA '+epaR}]); }catch(e){}
      }
      var extLeg=function(a,bb,ba,bx){ if(ba<0||bx<0||ba===bx||rb<0) return;   // extend the Wolfe RAILS 1-3 & 2-4 (the wedge; convergence must cross forward of pt4 — fbc6b29), NOT the 1-2/3-4 thrust legs
        var s=(manual[bb].value-manual[a].value)/(bx-ba);
        add({color:'rgba(88,166,255,0.55)',lineWidth:1,lineStyle:2},[{time:manual[a].time,value:manual[a].value},{time:rt2,value:Math.round((manual[a].value+s*(rb-ba))*100)/100}]); };
      extLeg(0,2,b0,b2); extLeg(1,3,b1,b3);                                     // rail 1-3 (pt5 forms on its extension) + rail 2-4
      if(legLenPx(2,3) > legLenPx(0,1))                                        // STRICT symmetry gate: leg 1-2 must be >= leg 3-4
        warns.push('The distance between points 1 and 2 is less than the distance between points 3 and 4.');
    }
    wfWarn=warns.join('  &middot;  ');                                         // placement notes + symmetry, all shown in the DRAW bar
  }
  function wolfeWarnings(){                                                    // directional placement checks — ACCEPT the click, just inform
    var out=[], L=manual.length; if(L<3) return out;
    var bull=dirBull(), p1=manual[0].value, p2=manual[1].value, p3=manual[2].value;   // direction = leg 1->2 (same basis the magnet/roles use)
    if(bull ? (p3>=p1) : (p3<=p1)) out.push('The placement of point 3 is incorrect.');   // bull: 3 below 1 · bear: 3 above 1
    if(L>=4){ var p4=manual[3].value;                                          // pt4 BETWEEN pt2 & pt3 in BOTH patterns — pt1 IRRELEVANT (Ramana): bull 3<4<2 · bear 2<4<3
      if(bull ? !(p3<p4 && p4<p2) : !(p3>p4 && p4>p2)) out.push('The placement of point 4 is incorrect.'); }
    return out;
  }
  // ---- persistence (Ramana): the hand-drawn wave survives reload/device via the SAME
  //      /dash/drawings store the general drawings use, under a namespaced key `<SYM>#wolfe`
  //      (its own row — never collides with the general list) + localStorage for instant restore. ----
  function wRawSym(){ return (new URLSearchParams(location.search).get('sym')||'').trim(); }
  function wKey(){ return 'wolfedraw:'+wRawSym(); }
  function wStoreSym(){ return wRawSym()+'#wolfe'; }
  var wSaveT=null;
  function saveDraw(){                                                          // localStorage now + debounced server POST (empty array clears the row)
    try{ localStorage.setItem(wKey(), JSON.stringify(manual)); }catch(e){}
    if(!wRawSym()) return;
    if(wSaveT) clearTimeout(wSaveT);
    wSaveT=setTimeout(function(){ try{ fetch('/dash/drawings?sym='+encodeURIComponent(wStoreSym()),
      {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(manual),keepalive:true}).catch(function(){}); }catch(e){} }, 600);
  }
  function loadDraw(){                                                          // restore on entering draw mode: localStorage instant, then server (source of truth)
    var got=null; try{ got=JSON.parse(localStorage.getItem(wKey())||'null'); }catch(e){ got=null; }
    if(Array.isArray(got)&&got.length){ manual=got.slice(0,5); }
    if(!wRawSym()) return;
    try{ fetch('/dash/drawings?sym='+encodeURIComponent(wStoreSym())).then(function(r){return r.json();}).then(function(d){
      if(mode!=='draw'||wDirty) return;                                        // he left draw mode / already started drawing — don't clobber
      var srv=(d&&Array.isArray(d.items))?d.items:[];
      if(srv.length){ manual=srv.slice(0,5); try{ localStorage.setItem(wKey(), JSON.stringify(manual)); }catch(e){} drawManual(); controls(); }
      else if(manual.length){ saveDraw(); }                                    // first-time migrate local -> server
    }).catch(function(){}); }catch(e){}
  }
  // ---- LEARNINGS (Ramana 2026-07-22): capture-and-preserve the hand-drawn wave as an isolated,
  //      persistent example (server table wolfe_learnings). Never touches the detector/scoring. ----
  var learnCount=0, learnPanel=null, learnOpen=false, learnItems=[], overlaySer=[], overlayOn=false, overlayDetail=false;
  function clearOverlay(){ overlaySer.forEach(function(s){try{window.__wfpc.removeSeries(s);}catch(e){}}); overlaySer=[]; }   // multi-wave overlay lives in ITS OWN series list — clear()/drawManual never touch it
  function addOverlay(opts,data){ var s=window.__wfpc.addLineSeries(Object.assign({priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false},opts,NS)); s.setData(data); overlaySer.push(s); return s; }
  function paintOverlay(){                                                      // ALL saved learnings on the chart AT ONCE — dim, so the active working wave stands out
    clearOverlay(); if(!overlayOn) return;
    (learnItems||[]).forEach(function(it){
      var col=(it.direction==='BULL')?'rgba(63,212,134,0.5)':'rgba(255,106,122,0.5)';
      var seen={}, line=[], marks=[];
      (it.points||[]).map(function(p,i){return {p:p,i:i};}).sort(function(a,b){return a.p.time<b.p.time?-1:(a.p.time>b.p.time?1:0);})
        .forEach(function(o){ if(seen[o.p.time])return; seen[o.p.time]=1; line.push({time:o.p.time,value:o.p.value});
          if(overlayDetail) marks.push({time:o.p.time,position:'inBar',color:col,shape:'circle',text:''+(o.i+1)}); });   // numbered points 1-5 (detail on)
      if(line.length<2) return;
      if(!overlayDetail) marks=[{time:line[line.length-1].time,position:'inBar',color:col,shape:'circle',text:'#'+it.id}];   // else just the #id label
      var s=addOverlay({color:col,lineWidth:1,lineStyle:0},line);
      try{ s.setMarkers(marks); }catch(e){}
      if(overlayDetail){ var t0=line[0].time, t1=line[line.length-1].time;                                                   // this wave's Fib zones as dim dashed levels, bounded to its span
        (it.zones||[]).forEach(function(z,zi){ if(z==null||z.price==null) return;
          var zs=addOverlay({color:col,lineWidth:1,lineStyle:2},[{time:t0,value:z.price},{time:t1,value:z.price}]);
          try{ zs.setMarkers([{time:t1,position:(zi%2?'belowBar':'aboveBar'),color:col,shape:'square',text:'#'+it.id+' Z'+(zi+1)+' '+z.price}]); }catch(e){}
        }); }
    });
  }
  function lSym(){ return (new URLSearchParams(location.search).get('sym')||'').trim(); }
  function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;'); }
  function refreshLCount(){ if(!lSym()) return;
    fetch('/dash/wolfe/learnings?sym='+encodeURIComponent(lSym())).then(function(r){return r.json();}).then(function(d){
      learnCount=(d&&d.items)?d.items.length:0; if(mode==='draw') controls(); }).catch(function(){}); }
  function saveLearning(){
    if(manual.length<4){ alert('Place at least points 1\\u20134 first, then save.'); return; }
    if(!confirm('Do you want me to take this as my learning for Wolfe wave?')) return;
    var dir=(manual[3].value>manual[1].value)?'BEAR':'BULL';                    // ascending wedge = SELL/BEAR (project convention)
    fetch('/dash/wolfe/learnings?sym='+encodeURIComponent(lSym()),{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({direction:dir,points:manual.slice(),zones:manualZones.slice(),note:''})})
      .then(function(r){return r.json();}).then(function(d){
        if(d&&d.ok){ learnOpen=true; renderLearn(); refreshLCount(); }
        else alert('Save failed'+(d&&d.error?': '+d.error:'')); }).catch(function(){ alert('Save failed (offline?)'); });
  }
  function ensureLPanel(){ if(learnPanel) return learnPanel;
    learnPanel=document.createElement('div');
    learnPanel.style.cssText='display:none;margin-top:6px;padding:8px 10px;border:1px solid var(--line-2);border-radius:8px;background:#0e1320;font-size:12px;max-height:280px;overflow:auto;line-height:1.5';
    if(lbl&&lbl.parentNode) lbl.parentNode.appendChild(learnPanel); return learnPanel; }
  function startDictation(inp,btn){                                            // voice note via the browser Web Speech API (Chrome); falls back to typing
    var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){ alert('Voice input is not supported in this browser \\u2014 please type the note.'); return; }
    try{ var r=new SR(); r.lang='en-IN'; r.interimResults=false; r.maxAlternatives=1; btn.textContent='\\ud83d\\udd34';
      r.onresult=function(ev){ var t=ev.results[0][0].transcript; inp.value=(inp.value?inp.value+' ':'')+t; };
      r.onerror=function(){}; r.onend=function(){ btn.textContent='\\ud83c\\udfa4'; }; r.start();
    }catch(e){ btn.textContent='\\ud83c\\udfa4'; } }
  function renderLearn(){
    var p=ensureLPanel();
    if(!learnOpen){ p.style.display='none'; return; }
    p.style.display='block'; p.innerHTML='loading\\u2026';
    fetch('/dash/wolfe/learnings?sym='+encodeURIComponent(lSym())).then(function(r){return r.json();}).then(function(d){
      var items=(d&&d.items)||[]; learnCount=items.length; learnItems=items;
      if(!items.length){ clearOverlay(); p.innerHTML='<i style="color:var(--ink-2)">No saved learnings yet for this symbol. Draw a wave, then \\u201c\\u2605 save as learning\\u201d.</i>'; return; }
      p.innerHTML='<b style="color:#d29922">Wolfe learnings \\u2014 '+esc(lSym())+' ('+items.length+')</b>'
        +' &nbsp; <span id="lShowAll" style="cursor:pointer;text-decoration:underline;color:'+(overlayOn?'#3fd486':'var(--ink-2)')+'">'+(overlayOn?'\\u25a0 hide all on chart':'\\u25a1 show all on chart')+'</span>'
        +' <span id="lDetail" style="cursor:pointer;text-decoration:underline;color:'+(overlayDetail?'#3fd486':'var(--ink-2)')+'">'+(overlayDetail?'\\u25a0 points + zones':'\\u25a1 points + zones')+'</span>'
        +items.map(function(it){
        var when=''; try{ when=new Date(it.created_at*1000).toISOString().slice(0,10); }catch(e){}
        var col=(it.direction==='BULL')?'#3fd486':'#ff6a7a', pts=(it.points||[]).map(function(q,i){return (i+1)+':'+q.value;}).join(' ');
        return '<div data-id="'+it.id+'" style="border-top:1px solid var(--bg-2);padding:6px 0">'
          +'<b>#'+it.id+'</b> \\u00b7 <b style="color:'+col+'">'+esc(it.direction||'?')+'</b> \\u00b7 '+when+' \\u00b7 '+(it.points||[]).length+'pts'
          +' &nbsp;<span class="lView" style="cursor:pointer;color:#58a6ff;text-decoration:underline">view</span>'
          +' &nbsp;<span class="lDel" style="cursor:pointer;color:#ff6a7a;text-decoration:underline">delete</span>'
          +'<div style="color:var(--ink-2);font-size:11px">'+esc(pts)+'</div>'
          +'<div style="margin-top:3px;display:flex;gap:5px;align-items:center">'
          +'<input class="lNote" value="'+esc(it.note)+'" placeholder="add a note (type or \\ud83c\\udfa4)\\u2026" style="flex:1;background:#0b0f16;border:1px solid var(--line-2);border-radius:5px;color:var(--ink);padding:3px 6px;font-size:11px">'
          +'<span class="lMic" title="dictate" style="cursor:pointer">\\ud83c\\udfa4</span>'
          +'<span class="lSave" style="cursor:pointer;color:#3fd486;text-decoration:underline;white-space:nowrap">save note</span></div></div>';
      }).join('');
      [].forEach.call(p.querySelectorAll('.lView'),function(el){ el.onclick=function(){ var id=+this.closest('[data-id]').getAttribute('data-id'); var it=items.filter(function(x){return x.id===id;})[0]; if(it){ manual=(it.points||[]).slice(0,5); wDirty=true; resnap(); drawManual(); controls(); } }; });
      [].forEach.call(p.querySelectorAll('.lDel'),function(el){ el.onclick=function(){ var id=+this.closest('[data-id]').getAttribute('data-id'); if(!confirm('Delete learning #'+id+'?')) return; fetch('/dash/wolfe/learnings/delete?id='+id,{method:'POST'}).then(function(){ renderLearn(); refreshLCount(); }); }; });
      [].forEach.call(p.querySelectorAll('.lSave'),function(el){ el.onclick=function(){ var row=this.closest('[data-id]'), id=+row.getAttribute('data-id'), note=row.querySelector('.lNote').value, b=this;
        fetch('/dash/wolfe/learnings/note?id='+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({note:note})}).then(function(r){return r.json();}).then(function(){ b.textContent='saved \\u2713'; setTimeout(function(){ b.textContent='save note'; },1200); }); }; });
      [].forEach.call(p.querySelectorAll('.lMic'),function(el){ el.onclick=function(){ startDictation(this.closest('[data-id]').querySelector('.lNote'),this); }; });
      var sa=document.getElementById('lShowAll'); if(sa) sa.onclick=function(){ overlayOn=!overlayOn; paintOverlay(); this.innerHTML=(overlayOn?'\\u25a0 hide all on chart':'\\u25a1 show all on chart'); this.style.color=overlayOn?'#3fd486':'var(--ink-2)'; };   // toggle ALL saved waves at once — in place (no re-fetch, no flash)
      var da=document.getElementById('lDetail'); if(da) da.onclick=function(){ overlayDetail=!overlayDetail; paintOverlay(); this.innerHTML=(overlayDetail?'\\u25a0 points + zones':'\\u25a1 points + zones'); this.style.color=overlayDetail?'#3fd486':'var(--ink-2)'; };   // numbered points 1-5 + Fib zones on the overlaid waves (opt-in)
      if(overlayOn) paintOverlay();                                            // keep the overlay in sync with the freshly-fetched list
    }).catch(function(){ p.innerHTML='<i style="color:#ff6a7a">could not load learnings</i>'; });
  }
  function doUndo(){ if(!manual.length) return; redoStack.push(manual.pop());  // Ctrl+Z / undo link — step back one point, remember it for redo
    if(editing!=null&&editing>=manual.length) editing=null; resnap(); drawManual(); controls(); saveDraw(); }
  function doRedo(){ if(!redoStack.length||manual.length>=5) return; manual.push(redoStack.pop()); resnap(); drawManual(); controls(); saveDraw(); }  // Ctrl+Y / redo link
  function onKey(e){                                                           // undo/redo keys — ONLY while drawing, and never while typing in a field
    if(mode!=='draw') return;
    var tg=(e.target&&e.target.tagName)||''; if(/INPUT|TEXTAREA|SELECT/.test(tg)||(e.target&&e.target.isContentEditable)) return;
    if(e.ctrlKey&&!e.shiftKey&&(e.key==='z'||e.key==='Z')){ e.preventDefault(); doUndo(); }
    else if(e.ctrlKey&&(e.key==='y'||e.key==='Y')){ e.preventDefault(); doRedo(); }
  }
  function onClick(param){
    if(mode!=='draw'||!param||!param.point||param.time==null) return;
    var price=ensureProbe().coordinateToPrice(param.point.y);
    if(price==null) return;
    var t=normTime(param.time);
    if(editing!=null){ manual[editing]={time:t,value:Math.round(price*100)/100}; editing=null; redoStack.length=0; wDirty=true; resnap(); drawManual(); controls(); saveDraw(); return; }  // drop the edited point (a new action invalidates redo)
    if(manual.length>=5) return;
    manual.push({time:t,value:Math.round(price*100)/100}); redoStack.length=0; wDirty=true; resnap(); drawManual(); controls(); saveDraw();   // a fresh point invalidates the redo stack
  }
  function enterDraw(){
    mode='draw'; hideBadge(); clear(); manual=[]; manualZones=[]; editing=null; wfWarn=''; redoStack.length=0; wDirty=false; ensureProbe();   // hide the auto-wave badge — it describes the DETECTED wave, not the one being hand-drawn
    if(!clickWired){ try{ window.__wfpc.subscribeClick(onClick); }catch(e){}
      try{ var el=window.__wfpc.chartElement&&window.__wfpc.chartElement(); if(el) el.addEventListener('dblclick',onDbl); }catch(e){}
      clickWired=true; }
    if(!keyWired){ document.addEventListener('keydown',onKey); keyWired=true; }   // Ctrl+Z / Ctrl+Y active while drawing (guarded to draw-mode)
    loadDraw(); drawManual(); refreshLCount(); controls();                       // restore the saved working wave + the learnings count for this symbol
  }
  function exitDraw(){
    clear(); manual=[]; manualZones=[]; editing=null; wfWarn=''; redoStack.length=0;
    learnOpen=false; if(learnPanel) learnPanel.style.display='none'; overlayOn=false; clearOverlay();   // hide the learnings drawer + clear the multi-wave overlay when leaving draw mode
    mode=defaultMode(); di=0; redraw();
  }
  function drawLink(){ return ' &nbsp;&middot; <span id="wfDraw" style="cursor:pointer;text-decoration:underline;color:#58a6ff">✎ draw your own</span>'; }
  function wireDraw(){ var e;
    if(e=document.getElementById('wfDraw')) e.onclick=function(){ enterDraw(); };
  }
  function renderDraw(){
    if(!lbl) return;
    var labels=['1','2','3','4','5 (overshoot, optional)'];
    var next = editing!=null ? ('editing point '+(editing+1)+' — click the chart to move it')
             : (manual.length<5 ? ('click point '+labels[manual.length]) : '5 points placed');
    var chips = manual.length? (' &nbsp;&middot;&nbsp; '+manual.map(function(p,i){                 // click a chip (or double-click the point) to edit it
        return '<span class="wfPt" data-i="'+i+'" style="cursor:pointer;padding:0 4px;border-radius:3px;'+
          (editing===i?'background:#1f6feb;color:#fff':'text-decoration:underline;color:var(--ink-2)')+'">'+(i+1)+':'+p.value+'</span>';
      }).join(' ')) : '';
    var zs = manualZones.length? (' &nbsp;&middot; <b style="color:#d29922">zones:</b> '+
      manualZones.map(function(x,i){return 'Z'+(i+1)+' '+x.price+' ('+x.r12+'∩'+x.r34+')';}).join('  &middot; ')) : '';
    var warnHtml = wfWarn? (' &nbsp;&middot; <b style="color:#ff6a7a">⚠ '+wfWarn+'</b>') : '';
    lbl.innerHTML='<b style="color:#58a6ff">✎ DRAW</b> '+next+
      ' &nbsp;&middot; <span id="wfSnap" title="auto-snap 1/3/5 to lows, 2/4 to highs (reversed on a bear)" style="cursor:pointer;text-decoration:underline;color:'+(autosnap?'#3fd486':'var(--ink-2)')+'">'+(autosnap?'auto-snap: on':'auto-snap: off')+'</span>'+
      ' &middot; <span id="wfUndo" title="undo (Ctrl+Z)" style="cursor:pointer;text-decoration:underline">undo</span>'+
      ' &middot; <span id="wfRedo" title="redo (Ctrl+Y)" style="cursor:pointer;text-decoration:underline">redo</span>'+
      ' &middot; <span id="wfReset" style="cursor:pointer;text-decoration:underline">reset</span>'+
      ' &middot; <span id="wfAuto" style="cursor:pointer;text-decoration:underline;color:var(--ink-2)">use auto</span>'+
      ' &nbsp;&middot; <span id="wfLearn" style="cursor:pointer;text-decoration:underline;color:#d29922">\\u2605 save as learning</span>'+
      ' &middot; <span id="wfLearnList" style="cursor:pointer;text-decoration:underline;color:var(--ink-2)">learnings'+(learnCount?' ('+learnCount+')':'')+'</span>'+
      chips+zs+warnHtml;
    var e;
    if(e=document.getElementById('wfSnap')) e.onclick=function(){ autosnap=!autosnap; resnap(); drawManual(); controls(); saveDraw(); };
    if(e=document.getElementById('wfUndo')) e.onclick=function(){ doUndo(); };
    if(e=document.getElementById('wfRedo')) e.onclick=function(){ doRedo(); };
    if(e=document.getElementById('wfReset')) e.onclick=function(){ if(manual.length && !confirm('Clear the current wave? This erases the '+manual.length+' point(s) placed. (Tip: “★ save as learning” first to keep it.)')) return; manual=[]; manualZones=[]; editing=null; wfWarn=''; redoStack.length=0; wDirty=true; drawManual(); controls(); saveDraw(); };   // guarded reset; saveDraw([]) deletes the stored working wave
    if(e=document.getElementById('wfAuto')) e.onclick=function(){ exitDraw(); };
    if(e=document.getElementById('wfLearn')) e.onclick=function(){ saveLearning(); };
    if(e=document.getElementById('wfLearnList')) e.onclick=function(){ learnOpen=!learnOpen; renderLearn(); };
    var pts=document.querySelectorAll('.wfPt');
    for(var k=0;k<pts.length;k++){ pts[k].onclick=function(){ editing=parseInt(this.getAttribute('data-i'),10); drawManual(); controls(); }; }
  }
  function controls(){
    if(!lbl) return;
    if(mode==='draw'){ renderDraw(); return; }
    var hasP=!!(DATA&&DATA.prediction), op=listFor('open'), cl=listFor('closed');
    var h=tab('wfTabP',mode==='pred','Prediction'+(hasP?'':' (none)'))
       +' '+tab('wfTabO',mode==='open','Open'+(op.length?' ('+op.length+')':' (none)'))
       +' '+tab('wfTabC',mode==='closed','Closed'+(cl.length?' ('+cl.length+')':' (none)'));
    var lst=listFor(mode);
    if((mode==='open'||mode==='closed')&&lst.length){
      h+=' &nbsp; <span id="wfPrev" title="previous (older) Wolfe" style="cursor:pointer;font-size:16px;padding:0 5px;color:var(--ink)">◄</span>'
       + ' <b>'+(di+1)+'/'+lst.length+'</b> '
       + '<span id="wfNext" title="next (newer) Wolfe" style="cursor:pointer;font-size:16px;padding:0 5px;color:var(--ink)">►</span>';
    }
    var w=curWave();
    h+=' &nbsp;&middot;&nbsp; '+(w?w.summary:(mode==='pred'?'no forming wave':mode==='open'?'no open wave':'no closed wave'));
    if(w) h+=' &nbsp;&middot; <span id="wfFans" style="cursor:pointer;text-decoration:underline;color:var(--ink-2)">'+(fansOn?'hide fib fans':'fib fans')+'</span>';
    h+=drawLink();
    lbl.innerHTML=h;
    var e;
    if(e=document.getElementById('wfTabP')) e.onclick=function(){ mode='pred'; di=0; redraw(); };
    if(e=document.getElementById('wfTabO')) e.onclick=function(){ mode='open'; di=0; redraw(); };
    if(e=document.getElementById('wfTabC')) e.onclick=function(){ mode='closed'; di=0; redraw(); };
    if(e=document.getElementById('wfPrev')) e.onclick=function(){ di++; redraw(); };   // older
    if(e=document.getElementById('wfNext')) e.onclick=function(){ di--; redraw(); };   // newer
    if(e=document.getElementById('wfFans')) e.onclick=function(){ setFans(!fansOn); controls(); };
    wireDraw();
  }
  function redraw(){
    if(mode==='draw'){ controls(); return; }
    if(!window.__wfpc||!DATA){ controls(); return; }
    // Ramana: the chart stays STATIC on nav — draw the selected wave, clear the one we're
    // leaving, but do NOT pan/zoom (panTo removed). Only the badge updates.
    clear(); var w=curWave(); if(w){ drawWave(w); } updateBadge(w); controls();
  }
  function restoreSaved(fallback){                                            // paint the saved hand-drawn wave if one exists for this symbol, else run fallback (the auto view)
    var s=null; try{ s=JSON.parse(localStorage.getItem(wKey())||'null'); }catch(e){}
    if(Array.isArray(s)&&s.length){ enterDraw(); return; }                    // localStorage = instant (same browser)
    if(fallback) fallback();
    if(!wRawSym()) return;
    try{ fetch('/dash/drawings?sym='+encodeURIComponent(wStoreSym())).then(function(r){return r.json();}).then(function(dd){   // server = cross-device first open
      var srv=(dd&&Array.isArray(dd.items))?dd.items:[];
      if(srv.length && mode!=='draw'){ try{ localStorage.setItem(wKey(),JSON.stringify(srv.slice(0,5))); }catch(e){} enterDraw(); }
    }).catch(function(){}); }catch(e){}
  }
  function load(){
    if(lbl) lbl.textContent='loading…';
    var sym=new URLSearchParams(location.search).get('sym')||'';
    fetch('/dash/wolfe/overlay?sym='+encodeURIComponent(sym)).then(function(r){return r.json();}).then(function(d){
      BARS=(d&&d.bars)||null;
      if(!d||(!d.prediction&&(!d.completed||!d.completed.length))){
        DATA=d||null;
        if(lbl){ lbl.innerHTML='no auto Wolfe wave'+drawLink(); wireDraw(); }   // still let him draw his own
        restoreSaved(null);                                                    // …and paint his saved hand-drawn wave if he has one
        return;
      }
      DATA=d; mode=defaultMode(); di=0;
      // AUTO-SELECT a specific wave by its point-5 date (from a Wolfe "open trades" link,
      // /dash/stock?sym=…&wolfe=YYYY-MM-DD) — so the full chart opens ON that exact wave,
      // not the newest. Falls back to the default (newest) when the param is absent/unmatched.
      var want=new URLSearchParams(location.search).get('wolfe');
      if(want&&DATA.completed){
        for(var k=0;k<DATA.completed.length;k++){
          if(DATA.completed[k].p5_time===want){
            mode=(DATA.completed[k].lifecycle==='closed')?'closed':'open';
            var lst=listFor(mode); var ix=lst.indexOf(DATA.completed[k]); if(ix>=0) di=ix;
            break;
          }
        }
      }
      if(want){ redraw(); }                                                   // an explicit ?wolfe= deep-link → show THAT auto wave, don't override
      else { restoreSaved(redraw); }                                          // else paint the saved hand-drawn wave if present, otherwise the auto wave
    }).catch(function(){ if(lbl) lbl.textContent='overlay error'; });
  }
  cb.addEventListener('change', function(){
    if(this.checked){ if(DATA||BARS!==null) redraw(); else load(); }
    else { clear(); manual=[]; manualZones=[]; mode='pred'; hideBadge(); learnOpen=false; if(learnPanel) learnPanel.style.display='none'; overlayOn=false; clearOverlay(); if(lbl) lbl.textContent=''; }
  });
  // ON OPEN (Ramana): if this symbol has a saved hand-drawn wave, auto-enable the overlay and
  // paint it the moment the chart opens — no need to tick "Wolfe wave" + click "draw your own".
  (function(){
    function activate(){ if(!cb.checked) cb.checked=true; if(DATA||BARS!==null) redraw(); else load(); }
    function ready(fn){ if(window.__wfpc){ fn(); return; } var n=0,t=setInterval(function(){ if(window.__wfpc){ clearInterval(t); fn(); } else if(++n>60){ clearInterval(t); } },100); }   // wait up to ~6s for the chart
    var s=null; try{ s=JSON.parse(localStorage.getItem(wKey())||'null'); }catch(e){}
    if(Array.isArray(s)&&s.length){ ready(activate); return; }                 // localStorage hit → open + paint immediately
    if(!wRawSym()) return;
    try{ fetch('/dash/drawings?sym='+encodeURIComponent(wStoreSym())).then(function(r){return r.json();}).then(function(dd){   // cross-device first open
      if(dd&&Array.isArray(dd.items)&&dd.items.length){ try{ localStorage.setItem(wKey(),JSON.stringify(dd.items.slice(0,5))); }catch(e){} ready(activate); }
    }).catch(function(){}); }catch(e){}
  })();
})();
</script>"""
