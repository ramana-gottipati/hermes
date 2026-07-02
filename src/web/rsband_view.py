"""/dash/rsband — RS support & resistance band (the mean-reversion / LEVEL lens).

The read surface for the RS-band foundation (``rsband.py``). ISOLATED on purpose:
a self-contained APIRouter in its OWN module, mounted via one line in main.py
WITHOUT editing the (parallel-session-held) dashboard.py. It reuses the shared
page shell (``_shell``) and dark CSS for chrome consistency.

The hero is the **lane dossier**: every curated sector on its OWN horizontal lane
along a shared 0–100 support→resistance axis. Per lane — a hollow dot where it sat
N months ago → a bar (the journey) → the filled dot today; a ◆ fair-value magnet
(POC); a left dot for regime (mean-reverting vs trending); and a fused verdict.
Orthogonal to /dash/rrg (trend/momentum): this is *level* — cheap vs rich vs its
own history, with the trend-regime gate so a re-rating (Defence) is never mistaken
for fade-able richness.

Data: ``rsband.band_lane`` (current metrics + the point-in-time band_pct journey),
fused with ``capture`` for the down-capture 'falls-less' veto. Pure read, ₹0, no LLM.
"""

from __future__ import annotations

import html
import json
from contextlib import nullcontext
from urllib.parse import quote_plus

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.automation import adjust, capture, rsband
from src.core.db import get_conn
from src.web.dashboard import _shell

try:
    from src.web.dashboard import REAL_SECTORS as _REAL_SECTORS
except Exception:
    _REAL_SECTORS = None

router = APIRouter()

BENCHMARKS = ("Nifty 500", "Nifty 50")


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _n(v, dp: int = 1) -> str:
    return "—" if v is None else f"{v:.{dp}f}"


# ── data ──────────────────────────────────────────────────────────────────────
def _lane_data(den: str, conn) -> list[dict]:
    """Per-sector lane payload: band_lane metrics + journey + the capture-fused
    verdict, ordered cheapest-first. One row per curated sector that has data."""
    falls: dict = {}
    try:
        caps = capture.latest_all(den, conn=conn) or capture.current_all(
            den, conn=conn, only=_REAL_SECTORS)
        for c in caps:
            dc = c.get("down_capture_63")
            falls[c["numerator"]] = (dc is not None and dc < 1.0)
    except Exception:
        falls = {}

    if _REAL_SECTORS:
        names = list(_REAL_SECTORS)
    else:
        names = [r["numerator"] for r in rsband.latest_all(den, conn=conn)]

    out = []
    for nm in names:
        if nm == den:
            continue
        try:
            lane = rsband.band_lane(nm, den, conn=conn)
        except Exception:
            lane = None
        if not lane or lane.get("rs_band_pct") is None:
            continue
        v, why = rsband.band_verdict(
            lane["rs_band_pct"], lane["rs_regime"], lane["slope_3m_pct"],
            lane["rs_band_state"], falls_less=falls.get(nm),
            trend_drift=lane["rs_trend_drift"])
        out.append({
            "k": nm.replace("Nifty ", "").replace(" Index", ""),
            "n": nm,
            "band": lane["rs_band_pct"],
            "path": lane["band_path"],
            "poc": lane["rs_poc_pct"],
            "regime": lane["rs_regime"],
            "state": lane["rs_band_state"],
            "tr2": lane["rs_trend_r2"],
            "verdict": v,
            "why": why,
            "href": f"/dash/rsband?idx={quote_plus(nm)}",
            "asof": lane.get("trade_date"),
        })
    out.sort(key=lambda d: d["band"] if d["band"] is not None else 1e9)
    return out


# ── the lane chart (SVG built client-side from injected data) ─────────────────
_MONTHS_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _month_labels(asof: str, n: int = 25) -> list:
    """['Jul '26', 'Jun '26', ...] - the calendar month `m` months before `asof`
    (m=0..n-1), for the band-lane scrubber badge. Pure int math (no datetime)."""
    y, m = int(asof[:4]), int(asof[5:7])
    out = []
    for k in range(n):
        yy, mm = y, m - k
        while mm <= 0:
            mm += 12
            yy -= 1
        out.append("%s '%02d" % (_MONTHS_ABBR[mm - 1], yy % 100))
    return out


_LANE_JS = r"""
(function(){
var P={ink:'#e6edf3',mut:'#8b949e',grid:'#30363d',track:'#21262d',val:'#3fd486',valF:'rgba(63,212,134,0.10)',rich:'#d29922',richF:'rgba(210,153,34,0.10)',cap:'rgba(255,106,122,0.13)',up:'#3fd486',down:'#ff6a7a',flat:'#8b949e',ghost:'#6e7681',mr:'#39c5bb',poc:'#bc8cff',hollow:'#0d1117'};
var KM=[0,3,6,12,18,24],SEC=__SEC__,H=12;
if(!SEC.length)return;
function knots(p){var k=[];for(var i=0;i<KM.length;i++){if(p[i]!=null)k.push([KM[i],p[i]]);}return k;}
function pibAt(p,m){var ks=knots(p);if(!ks.length)return null;if(m<=ks[0][0])return ks[0][1];for(var i=0;i<ks.length-1;i++){if(m>=ks[i][0]&&m<=ks[i+1][0]){var t=(m-ks[i][0])/(ks[i+1][0]-ks[i][0]);return ks[i][1]+(ks[i+1][1]-ks[i][1])*t;}}return ks[ks.length-1][1];}
var AX0=150,AX100=512;
function xOf(p){if(p==null)return null;if(p<0)return Math.max(AX0-26,AX0+p*1.4);if(p>100)return Math.min(AX100+26,AX100+(p-100)*1.4);return AX0+p/100*(AX100-AX0);}
function colNet(n){return n>3?P.up:n<-3?P.down:P.flat;}
function zc(p){return p>100||p<0?P.down:p<=20?P.val:p>=80?P.rich:'#58a6ff';}
function vcol(v){return (v=='Accumulate'||v=='Add'||v=='Ride')?P.up:(v=='Avoid'||v=='Fade')?P.down:(v=='Hold')?P.flat:P.rich;}
var top=44,rowH=23,svg=document.getElementById('rbsvg'),tip=document.getElementById('rbtip');
var scEl=document.getElementById('rbscrub'),mbEl=document.getElementById('rbmonth'),MLBL=__MLBL__||[];
function zones(n){var s='',bot=top+n*rowH;
 s+='<rect x="'+(AX0-26)+'" y="'+top+'" width="26" height="'+(bot-top)+'" fill="'+P.cap+'"/><rect x="'+AX100+'" y="'+top+'" width="26" height="'+(bot-top)+'" fill="'+P.cap+'"/>';
 s+='<rect x="'+AX0+'" y="'+top+'" width="'+(xOf(25)-AX0)+'" height="'+(bot-top)+'" fill="'+P.valF+'"/><rect x="'+xOf(75)+'" y="'+top+'" width="'+(AX100-xOf(75))+'" height="'+(bot-top)+'" fill="'+P.richF+'"/>';
 [0,25,50,75,100].forEach(function(g){var x=xOf(g);s+='<line x1="'+x+'" y1="'+top+'" x2="'+x+'" y2="'+bot+'" stroke="'+P.grid+'" stroke-width="1" stroke-dasharray="'+(g==50?'1 5':'3 4')+'"/>';});
 s+='<text x="'+AX0+'" y="'+(top-7)+'" fill="'+P.val+'" font-size="10">support · cheap</text>';
 s+='<text x="'+AX100+'" y="'+(top-7)+'" fill="'+P.rich+'" font-size="10" text-anchor="end">rich · resistance</text>';
 s+='<text x="558" y="'+(top-7)+'" fill="'+P.mut+'" font-size="10">verdict</text>';
 return s;}
function laneStr(s,i,head,trail){
 var y=top+i*rowH+rowH/2,now=s.path[0],start=pibAt(s.path,H),net=(start==null||now==null)?0:now-start,c=colNet(net);
 var str='<g class="rblane" data-k="'+encodeURIComponent(s.k)+'" style="cursor:pointer">';
 if(s.verdict=='Accumulate')str+='<rect x="0" y="'+(y-rowH/2+1)+'" width="680" height="'+(rowH-2)+'" fill="rgba(63,212,134,0.08)"/>';
 str+='<circle cx="10" cy="'+y+'" r="3.4" fill="'+(s.regime=='TRENDING'?P.rich:P.mr)+'"/>';
 str+='<text x="138" y="'+(y+4)+'" fill="'+P.ink+'" font-size="11" text-anchor="end">'+s.k+'</text>';
 str+='<line x1="'+AX0+'" y1="'+y+'" x2="'+AX100+'" y2="'+y+'" stroke="'+P.track+'" stroke-width="1"/>';
 if(s.poc!=null){var px=xOf(s.poc);str+='<path d="M'+px.toFixed(1)+','+(y-4)+' L'+(px+4).toFixed(1)+','+y+' L'+px.toFixed(1)+','+(y+4)+' L'+(px-4).toFixed(1)+','+y+' Z" fill="none" stroke="'+P.poc+'" stroke-width="1.2"/>';}
 if(trail){trail.forEach(function(tx,j){var a=(j/trail.length)*0.45;str+='<circle cx="'+tx.toFixed(1)+'" cy="'+y+'" r="3" fill="'+c+'" fill-opacity="'+a.toFixed(2)+'"/>';});if(head!=null)str+='<circle cx="'+xOf(head).toFixed(1)+'" cy="'+y+'" r="6" fill="'+c+'" stroke="'+P.ink+'" stroke-width="1.2"/>';}
 else{
  var ks=knots(s.path).filter(function(kk){return kk[0]<=H;});
  if(ks.length>1){var pts='';ks.forEach(function(kk){pts+=xOf(kk[1]).toFixed(1)+','+y+' ';});str+='<polyline points="'+pts+'" fill="none" stroke="'+c+'" stroke-width="2" stroke-opacity="0.6"/>';var st=ks[ks.length-1];str+='<circle cx="'+xOf(st[1]).toFixed(1)+'" cy="'+y+'" r="4.2" fill="'+P.hollow+'" stroke="'+P.ghost+'" stroke-width="1.4"/>';}
  if(now!=null)str+='<circle cx="'+xOf(now).toFixed(1)+'" cy="'+y+'" r="6" fill="'+c+'" stroke="'+P.ink+'" stroke-width="1.2"/>';
  str+='<text x="540" y="'+(y+4)+'" fill="'+zc(now==null?50:now)+'" font-size="11" text-anchor="end">'+(now==null?'—':Math.round(now))+'</text>';
  str+='<text x="558" y="'+(y+4)+'" fill="'+vcol(s.verdict)+'" font-size="11">'+s.verdict+'</text>';
 }
 str+='</g>';return str;}
var ORD=SEC.map(function(s,i){return i;}).sort(function(a,b){var pa=SEC[a].path[0],pb=SEC[b].path[0];return (pa==null?999:pa)-(pb==null?999:pb);});
function render(){var s=zones(SEC.length);ORD.forEach(function(idx,i){s+=laneStr(SEC[idx],i,null,null);});svg.setAttribute('viewBox','0 0 680 '+(top+SEC.length*rowH+14));svg.innerHTML=s;wire();}
function wire(){Array.prototype.forEach.call(svg.querySelectorAll('.rblane'),function(g){
 g.addEventListener('mouseenter',function(){var k=decodeURIComponent(g.getAttribute('data-k')),s=null;for(var i=0;i<SEC.length;i++){if(SEC[i].k===k){s=SEC[i];break;}}if(!s)return;
  var now=s.path[0],start=pibAt(s.path,H),net=(start==null||now==null)?null:now-start;
  var lab=now==null?'n/a':now>=85?'at resistance':now>=65?'upper band':now>=35?'mid-band':now>=15?'lower band':'at support';
  var h='<b>'+s.n+'</b><br>'+(now==null?'n/a':Math.round(now)+'/100')+' · '+lab+' · '+(s.regime=='TRENDING'?'trending':'mean-reverting');
  if(net!=null)h+='<br>'+H+'m: '+Math.round(start)+' &rarr; '+Math.round(now)+' ('+(net>=0?'+':'')+Math.round(net)+')';
  if(s.poc!=null)h+='<br>magnet '+Math.round(s.poc);
  h+='<br><span style="color:'+vcol(s.verdict)+'">'+s.verdict+'</span> — '+s.why;
  tip.innerHTML=h;tip.style.display='block';
  var w=document.getElementById('rbwrap').getBoundingClientRect(),gb=g.getBoundingClientRect();
  tip.style.left=Math.min(gb.left-w.left+40,w.width-250)+'px';var ty=gb.top-w.top-tip.offsetHeight-6;tip.style.top=(ty<0?gb.top-w.top+gb.height+6:ty)+'px';});
 g.addEventListener('mouseleave',function(){tip.style.display='none';});
 g.addEventListener('click',function(){var k=decodeURIComponent(g.getAttribute('data-k'));for(var i=0;i<SEC.length;i++){if(SEC[i].k===k){if(SEC[i].href)window.location.href=SEC[i].href;return;}}});});}
function play(){if(window._rbraf)cancelAnimationFrame(window._rbraf);tip.style.display='none';var trails={};ORD.forEach(function(idx){trails[idx]=[];});var t0=null,dur=700+H*120;
 function step(ts){if(!t0)t0=ts;var k=Math.min(1,(ts-t0)/dur),mk=H*(1-k),s=zones(SEC.length);
  ORD.forEach(function(idx,i){var sec=SEC[idx],pib=pibAt(sec.path,mk),tr=trails[idx];if(pib!=null){tr.push(xOf(pib));if(tr.length>16)tr.shift();}s+=laneStr(sec,i,pib,tr.slice());});
  svg.innerHTML=s;if(mbEl)mbEl.textContent=MLBL[Math.round(mk)]||'\u2014';if(scEl)scEl.value=Math.round((H-mk)*10);
  if(k<1)window._rbraf=requestAnimationFrame(step);else{render();if(mbEl)mbEl.textContent=MLBL[0]||'\u2014';if(scEl)scEl.value=H*10;}}
 window._rbraf=requestAnimationFrame(step);}
// -- manual scrubber: travel the lookback window; each lane's marker moves to that month --
function scrubTo(mk){if(window._rbraf){cancelAnimationFrame(window._rbraf);window._rbraf=null;}tip.style.display='none';
 var s=zones(SEC.length);
 ORD.forEach(function(idx,i){var sec=SEC[idx],pib=pibAt(sec.path,mk),tr=[];
  for(var mm=H;mm>mk;mm-=Math.max(0.5,H/14)){var xp=xOf(pibAt(sec.path,mm));if(xp!=null)tr.push(xp);}
  s+=laneStr(sec,i,pib,tr);});
 svg.setAttribute('viewBox','0 0 680 '+(top+SEC.length*rowH+14));svg.innerHTML=s;
 if(mbEl)mbEl.textContent=MLBL[Math.round(mk)]||'\u2014';
 if(scEl&&document.activeElement!==scEl)scEl.value=Math.round((H-mk)*10);}
if(scEl)scEl.addEventListener('input',function(){var mk=H-(+scEl.value)/10;if(mk<0)mk=0;if(mk>H)mk=H;scrubTo(mk);});
function movers(){var arr=SEC.map(function(s){var st=pibAt(s.path,H);return {k:s.k,net:(st==null||s.path[0]==null)?0:s.path[0]-st};});
 var up=arr.slice().sort(function(a,b){return b.net-a.net;}).slice(0,3),dn=arr.slice().sort(function(a,b){return a.net-b.net;}).slice(0,3);
 function f(x){return x.k+' '+(x.net>=0?'+':'')+Math.round(x.net);}
 document.getElementById('rbmov').innerHTML='<span style="color:'+P.up+'">&#9650; '+up.map(f).join(' · ')+'</span>&nbsp;&nbsp;<span style="color:'+P.down+'">&#9660; '+dn.map(f).join(' · ')+'</span>';}
function setH(h){H=h;Array.prototype.forEach.call(document.querySelectorAll('#rbh button'),function(b){var on=+b.getAttribute('data-h')===h;b.style.background=on?'#1f6feb':'transparent';b.style.color=on?'#fff':'#8b949e';b.style.borderColor=on?'#1f6feb':'#30363d';});if(scEl){scEl.max=H*10;scEl.value=H*10;}if(mbEl)mbEl.textContent=MLBL[0]||'\u2014';movers();render();}
document.getElementById('rbh').addEventListener('click',function(e){var b=e.target.closest('button');if(b)setH(+b.getAttribute('data-h'));});
document.getElementById('rbplay').addEventListener('click',play);
setH(12);
})();
"""


def _segbtn(m: int) -> str:
    return (f'<button data-h="{m}" style="background:transparent;color:var(--ink-2);border:0;'
            f'border-right:1px solid var(--line-2);padding:5px 13px;font-size:13px;cursor:pointer">{m}m</button>')


def _chart_block(data: list[dict]) -> str:
    asof = next((d.get("asof") for d in data if d.get("asof")), None)
    mlbl = _month_labels(asof) if asof else []
    js = (_LANE_JS.replace("__SEC__", json.dumps(data))
          .replace("__MLBL__", json.dumps(mlbl)))
    return (
        '<div class="card" style="padding:10px 12px">'
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px">'
        '<span class="sub" style="margin:0">look back</span>'
        f'<span id="rbh" style="display:inline-flex;border:1px solid var(--line-2);border-radius:6px;overflow:hidden">{_segbtn(6)}{_segbtn(12)}{_segbtn(24)}</span>'
        '<button id="rbplay" style="background:transparent;color:var(--ink);border:1px solid var(--line-2);'
        'border-radius:6px;padding:4px 11px;font-size:13px;cursor:pointer">&#9658; Play</button>'
        '<span class="sub" id="rbmov" style="margin:0 0 0 auto"></span></div>'
        '<div id="rbwrap" style="position:relative">'
        '<svg id="rbsvg" viewBox="0 0 680 520" width="100%" xmlns="http://www.w3.org/2000/svg"></svg>'
        '<div id="rbtip" style="position:absolute;display:none;pointer-events:none;background:var(--bg-2);'
        'border:1px solid var(--line-2);border-radius:6px;padding:6px 9px;font-size:12px;color:var(--ink);'
        'max-width:280px;line-height:1.45;z-index:5"></div></div>'
        '<div style="margin:8px 2px 2px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
        '<span class="pill" id="rbmonth" style="min-width:76px;text-align:center;font-weight:700;'
        'background:#1f6feb;border-color:#1f6feb;color:#fff">&mdash;</span>'
        '<input id="rbscrub" type="range" min="0" max="120" value="120" step="1" '
        'style="flex:1;min-width:220px;accent-color:#1f6feb;cursor:pointer" '
        'aria-label="band timeline - drag to travel the look-back window"></div>'
        '<div class="sub" style="margin-top:6px">'
        '<span style="color:#39c5bb">&#9679;</span> mean-reverting · '
        '<span style="color:#d29922">&#9679;</span> trending &nbsp;|&nbsp; '
        '<span style="color:#bc8cff">&#9670;</span> fair-value magnet · hollow = start · filled = today · '
        'green row = accumulate. Hover a lane for the read.</div>'
        f'</div><script>{js}</script>')


_CLOCK_JS = r"""
(function(){
var P={ink:'#e6edf3',mut:'#8b949e',val:'#3fd486',rich:'#d29922',flat:'#8b949e',up:'#3fd486',down:'#ff6a7a',brk:'#ff6a7a'};
var SEC=__SEC__;if(!SEC.length)return;
SEC=SEC.slice().sort(function(a,b){return (a.band==null?999:a.band)-(b.band==null?999:b.band);});
var cx=280,cy=240,rIn=26,rOut=195,N=SEC.length,svg=document.getElementById('csvg');
var scEl=document.getElementById('cbscrub'),mbEl=document.getElementById('cbmonth'),MLBL=__MLBL__||[];
var KM=[0,3,6,12,18,24];
function knots(p){var k=[];for(var i=0;i<KM.length;i++){if(p&&p[i]!=null)k.push([KM[i],p[i]]);}return k;}
function pibAt(p,m){var ks=knots(p);if(!ks.length)return null;if(m<=ks[0][0])return ks[0][1];for(var i=0;i<ks.length-1;i++){if(m>=ks[i][0]&&m<=ks[i+1][0]){var t=(m-ks[i][0])/(ks[i+1][0]-ks[i][0]);return ks[i][1]+(ks[i+1][1]-ks[i][1])*t;}}return ks[ks.length-1][1];}
function rad(p){if(p==null)p=50;return rIn+(Math.max(-12,Math.min(115,p))/100)*(rOut-rIn);}
function ang(i){return -Math.PI/2+i/N*Math.PI*2;}
var HIDX={6:2,12:3,24:5},HZ=6;
function pH(s){var i=HIDX[HZ];return (s.path&&s.path[i]!=null)?s.path[i]:s.band;}
function col(s){var d=(s.band==null||pH(s)==null)?0:s.band-pH(s);return d>3?P.up:d<-3?P.down:P.flat;}
function zc(p){return (p>100||p<0)?P.brk:p<=20?P.val:p>=80?P.rich:'#58a6ff';}
function rings(){var s='';
 [[rIn,P.val,'2 6'],[rad(50),P.mut,'2 6'],[rOut,P.rich,'4 4']].forEach(function(g){s+='<circle cx="'+cx+'" cy="'+cy+'" r="'+g[0].toFixed(1)+'" fill="none" stroke="'+g[1]+'" stroke-width="1" stroke-dasharray="'+g[2]+'" stroke-opacity="0.6"/>';});
 s+='<text x="'+cx+'" y="'+(cy-rOut-8)+'" fill="'+P.rich+'" font-size="11" text-anchor="middle">resistance (rim)</text>';
 s+='<text x="'+cx+'" y="'+(cy+rIn+14)+'" fill="'+P.val+'" font-size="10" text-anchor="middle">support</text>';
 s+='<text id="ctxt" x="'+cx+'" y="'+(cy-3)+'" fill="'+P.mut+'" font-size="12" text-anchor="middle">hover a spoke</text>';
 s+='<text id="ctxt2" x="'+cx+'" y="'+(cy+15)+'" fill="'+P.ink+'" font-size="13" text-anchor="middle"></text>';
 return s;}
function spokes(rads){var s='';
 SEC.forEach(function(sec,i){var a=ang(i),r=rads[i],ex=cx+Math.cos(a)*r,ey=cy+Math.sin(a)*r,c=col(sec),brk=sec.band>100||sec.band<0;
  var lx=cx+Math.cos(a)*(rOut+15),ly=cy+Math.sin(a)*(rOut+15);
  s+='<g class="cspk" data-i="'+i+'" style="cursor:pointer">';
  s+='<line x1="'+cx+'" y1="'+cy+'" x2="'+ex.toFixed(1)+'" y2="'+ey.toFixed(1)+'" stroke="'+c+'" stroke-width="2" stroke-opacity="0.55"/>';
  if(brk)s+='<circle cx="'+ex.toFixed(1)+'" cy="'+ey.toFixed(1)+'" r="8" fill="none" stroke="'+P.brk+'" stroke-width="2"/>';
  s+='<circle cx="'+ex.toFixed(1)+'" cy="'+ey.toFixed(1)+'" r="5" fill="'+c+'"/>';
  s+='<text x="'+lx.toFixed(1)+'" y="'+(ly+3).toFixed(1)+'" fill="'+P.ink+'" font-size="10" text-anchor="middle">'+sec.k+'</text>';
  s+='</g>';});
 return s;}
function draw(rads){svg.innerHTML=rings()+spokes(rads);
 Array.prototype.forEach.call(svg.querySelectorAll('.cspk'),function(g){var sec=SEC[+g.getAttribute('data-i')];
  g.addEventListener('mouseenter',function(){var t1=document.getElementById('ctxt'),t2=document.getElementById('ctxt2');t1.textContent=(sec.band==null?'n/a':Math.round(sec.band)+'/100 in band');t1.setAttribute('fill',zc(sec.band));t2.textContent=sec.n;});
  g.addEventListener('click',function(){if(sec.href)window.location.href=sec.href;});});}
function curr(){return SEC.map(function(s){return rad(s.band);});}
function bandAt(s,mk){var v=pibAt(s.path,mk);return v==null?s.band:v;}
function hud(mk){var p=Math.round(mk);if(mbEl)mbEl.textContent=MLBL[p]||'\u2014';if(scEl&&document.activeElement!==scEl)scEl.value=Math.round((HZ-mk)*10);}
function drawAt(mk){draw(SEC.map(function(s){return rad(bandAt(s,mk));}));hud(mk);}
draw(curr());
var raf=null;
function breathe(){if(raf)cancelAnimationFrame(raf);
 var from=SEC.map(function(s){return rad(pH(s));}),to=curr(),t0=null;
 function step(ts){if(!t0)t0=ts;var k=Math.min(1,(ts-t0)/2400),e=1-Math.pow(1-k,3);draw(from.map(function(f,i){return f+(to[i]-f)*e;}));hud(HZ*(1-e));if(k<1)raf=requestAnimationFrame(step);else hud(0);}
 raf=requestAnimationFrame(step);}
function setHZ(h){HZ=h;Array.prototype.forEach.call(document.querySelectorAll('#cbh button'),function(b){var on=+b.getAttribute('data-h')===h;b.style.background=on?'#1f6feb':'transparent';b.style.color=on?'#fff':'#8b949e';});if(raf)cancelAnimationFrame(raf);if(scEl){scEl.max=HZ*10;scEl.value=HZ*10;}hud(0);draw(curr());}
document.getElementById('cbh').addEventListener('click',function(e){var b=e.target.closest('button');if(b)setHZ(+b.getAttribute('data-h'));});
document.getElementById('cbreathe').addEventListener('click',breathe);
if(scEl)scEl.addEventListener('input',function(){if(raf){cancelAnimationFrame(raf);raf=null;}var mk=HZ-(+scEl.value)/10;if(mk<0)mk=0;if(mk>HZ)mk=HZ;drawAt(mk);});
setHZ(6);
})();
"""


def _cbtn(m: int) -> str:
    return (f'<button data-h="{m}" style="background:transparent;color:var(--ink-2);border:0;'
            f'border-right:1px solid var(--line-2);padding:5px 13px;font-size:13px;cursor:pointer">{m}m</button>')


def _clock_block(data: list[dict]) -> str:
    asof = next((d.get("asof") for d in data if d.get("asof")), None)
    mlbl = _month_labels(asof) if asof else []
    js = (_CLOCK_JS.replace("__SEC__", json.dumps(data))
          .replace("__MLBL__", json.dumps(mlbl)))
    return (
        '<div class="card" style="padding:10px 12px">'
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px">'
        '<button id="cbreathe" style="background:transparent;color:var(--ink);border:1px solid var(--line-2);'
        'border-radius:6px;padding:5px 14px;font-size:13px;cursor:pointer">&#9658; Breathe</button>'
        '<span class="sub" style="margin:0">over</span>'
        '<span id="cbh" style="display:inline-flex;border:1px solid var(--line-2);border-radius:6px;overflow:hidden">'
        f'{_cbtn(6)}{_cbtn(12)}{_cbtn(24)}</span>'
        '<span class="sub" style="margin:0">centre = support · rim = resistance · past the rim = breakout · '
        'colour = direction over the chosen window · click a spoke to drill</span></div>'
        '<svg id="csvg" viewBox="0 0 560 500" width="100%" style="max-width:560px;display:block;margin:0 auto" '
        'xmlns="http://www.w3.org/2000/svg"></svg>'
        '<div style="margin:6px auto 2px;max-width:560px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
        '<span class="pill" id="cbmonth" style="min-width:76px;text-align:center;font-weight:700;'
        'background:#1f6feb;border-color:#1f6feb;color:#fff">&mdash;</span>'
        '<input id="cbscrub" type="range" min="0" max="60" value="60" step="1" '
        'style="flex:1;min-width:200px;accent-color:#1f6feb;cursor:pointer" '
        'aria-label="clock timeline - drag to travel the look-back window"></div></div>'
        '<script>' + js + '</script>')


def _table(data: list[dict], den: str, link_fn=None) -> str:
    head = ("<thead><tr><th>Sector</th><th>Band</th><th>Regime</th><th>Trend-R²</th>"
            "<th>State</th><th>Verdict</th></tr></thead>")
    vc = {"Accumulate": "var(--up)", "Add": "var(--up)", "Ride": "var(--up)",
          "Avoid": "var(--down)", "Fade": "var(--down)", "Hold": "var(--ink-2)"}
    # directional verdict → token rgba tint (var()+hex-alpha is invalid CSS).
    vbg = {"Accumulate": "rgba(var(--up-rgb),.13)", "Add": "rgba(var(--up-rgb),.13)",
           "Ride": "rgba(var(--up-rgb),.13)", "Avoid": "rgba(var(--down-rgb),.13)",
           "Fade": "rgba(var(--down-rgb),.13)", "Hold": "#8b949e22"}
    body = []
    for d in data:
        nm = d["n"]
        col = vc.get(d["verdict"], "#d29922")
        bg = vbg.get(d["verdict"], "#d2992222")
        bcol = ("var(--up)" if (d["band"] is not None and d["band"] <= 20)
                else "#d29922" if (d["band"] is not None and d["band"] >= 80) else "var(--ink)")
        rcol = "#d29922" if d["regime"] == "TRENDING" else "#39c5bb"
        link = link_fn(nm) if link_fn else f'/dash/rsband?idx={quote_plus(nm)}&den={quote_plus(den)}'
        body.append(
            f'<tr><td><a href="{link}" style="color:#58a6ff;text-decoration:none">{_esc(nm)}</a></td>'
            f'<td style="color:{bcol}">{_n(d["band"])}</td>'
            f'<td style="color:{rcol}">{_esc(d["regime"].replace("_", "-").lower())}</td>'
            f'<td>{_n(d["tr2"], 2)}</td>'
            f'<td class="sub" style="margin:0">{_esc(d["state"])}</td>'
            f'<td><span style="background:{bg};color:{col};padding:2px 9px;border-radius:10px;'
            f'font-size:12px;font-weight:500">{_esc(d["verdict"])}</span> '
            f'<span class="sub" style="margin:0">{_esc(d["why"])}</span></td></tr>')
    return f'<table class="dt">{head}<tbody>{"".join(body)}</tbody></table>'


# Per-view one-liner under the page title (the TAB BAR is the primary switch now).
_VIEW_BLURB = {
    "lanes": ("Where each sector's relative strength sits inside its OWN 3-year band vs {den} "
              "— 0 = at historical RS support (cheap vs its own history), 100 = RS resistance "
              "(rich). The <i>level</i> lens, orthogonal to the rotation map; a trend-regime gate "
              "flags structural re-raters so a re-rating is never mistaken for fade-able richness."),
    "clock": ("The same band levels as a radial bloom vs {den} — centre = support, rim = "
              "resistance, past the rim = a breakout. Hit <b>Breathe</b> to watch the last "
              "6 / 12 / 24 months of rotation play out. Still the <i>level</i> lens."),
    "rrg":   ("The rotation map vs {den} — JdK RS-Ratio × RS-Momentum, the <i>direction &amp; "
              "momentum</i> lens (the derivative of relative strength): improving → leading → "
              "weakening → lagging, clockwise. Pair it with Lanes (level) to size decisions."),
}


def _tabbar(den: str, view: str) -> str:
    """The PRIMARY view switch — a prominent browser-tab strip right under the page
    title, styled deliberately UNLIKE the round benchmark pills below the explainer so
    it can't be missed (Ramana's #1 ask: UI visibility). [Lanes][Clock][RRG]. NOT
    sticky: the shell header is already `position:sticky;top:0` (dashboard.py) — a
    second sticky strip at top:0 collided with it on scroll, so this stays in flow."""
    def tab(v: str, label: str) -> str:
        if v == view:
            st = ("background:var(--bg-2);color:#58a6ff;border:1px solid var(--line-2);"
                  "border-bottom:3px solid #58a6ff;")
        else:
            st = ("background:transparent;color:var(--ink-2);border:1px solid transparent;"
                  "border-bottom:3px solid transparent;")
        return (f'<a href="/dash/rsband?den={quote_plus(den)}&view={v}" '
                f'style="display:inline-block;padding:9px 26px;font-size:15px;font-weight:600;'
                f'letter-spacing:.2px;text-decoration:none;border-radius:8px 8px 0 0;'
                f'margin-right:3px;{st}">{label}</a>')
    return ('<div style="display:flex;align-items:flex-end;margin:8px 0 14px;'
            'border-bottom:1px solid var(--line-2)">'
            + tab("lanes", "Lanes") + tab("clock", "Clock") + tab("rrg", "RRG")
            + '</div>')


def _controls(den: str, view: str = "lanes") -> str:
    def pill(b: str) -> str:
        on = "background:#1f6feb;border-color:#1f6feb;color:#fff;" if b == den else ""
        return (f'<a href="/dash/rsband?den={quote_plus(b)}&view={view}" class="pill" '
                f'style="text-decoration:none;margin-right:6px;{on}">vs {_esc(b)}</a>')
    blurb = _VIEW_BLURB.get(view, _VIEW_BLURB["lanes"]).format(den=_esc(den))
    return (
        '<h2 style="margin-bottom:4px">RS support &amp; resistance — sectors</h2>'
        + _tabbar(den, view)
        + f'<div class="sub">{blurb}</div>'
        + f'<div style="margin:10px 0 12px">{"".join(pill(b) for b in BENCHMARKS)}</div>')


def _empty() -> str:
    return ('<h2>RS support &amp; resistance — sectors</h2>'
            '<div class="card"><div class="sub">No band data yet — needs <code>ratio_rows</code>. '
            'Run <code>python -m src.automation.rsband</code> after the signal chain.</div></div>')


def render_band_lanes(den: str = "Nifty 500", view: str = "lanes", conn=None,
                      tail: str = "12") -> str:
    # CL-VIEW-10: `with` (own → get_conn(); passed-in → nullcontext) — real exceptions
    # propagate instead of being masked by __exit__(None,None,None); an early return
    # inside still closes the owned conn correctly.
    own = conn is None
    with (get_conn() if own else nullcontext(conn)) as conn:
        den = den if den in BENCHMARKS else "Nifty 500"
        if view == "rrg":                  # 3rd tab: the sector rotation RRG (reused)
            from src.web.rrg_view import render_sectors_map
            months = tail if tail in ("3", "6", "12", "24") else "12"
            rrg_block = render_sectors_map(den, conn=conn, months=months,
                                           tail_base="/dash/rsband", tail_view="rrg")
            return (_controls(den, "rrg") + (rrg_block or
                    '<div class="card"><div class="sub">No rotation data yet — '
                    'run the nightly RRG job.</div></div>'))
        data = _lane_data(den, conn)
    if not data:
        return _empty()
    block = _clock_block(data) if view == "clock" else _chart_block(data)
    return _controls(den, view) + block + _table(data, den)


# ── single-sector Channel (the band chart — drill from a lane) ────────────────
def _ratio_series(conn, num: str, den: str) -> list[tuple]:
    rows = conn.execute(
        "SELECT trade_date, ratio FROM ratio_rows WHERE numerator=? AND denominator=? "
        "AND ratio IS NOT NULL ORDER BY trade_date ASC", (num, den)).fetchall()
    return [(r["trade_date"], r["ratio"]) for r in rows]


def _back() -> str:
    return ('<a class="row" style="display:inline;color:#58a6ff;text-decoration:none" '
            'href="/dash/rsband">&larr; Back to the band</a>')


_CH_HOVER_JS = r"""
(function(){
var D=__CH__,svg=document.getElementById('chsvg'),tip=document.getElementById('chtip'),wrap=document.getElementById('chwrap'),xl=document.getElementById('chx'),dot=document.getElementById('chd');
if(!svg||!wrap||!D.pts.length)return;
var pts=D.pts,sup=D.sup,res=D.res;
function near(vx){var b=pts[0],bd=1e9;for(var i=0;i<pts.length;i++){var d=Math.abs(pts[i].x-vx);if(d<bd){bd=d;b=pts[i];}}return b;}
svg.addEventListener('mousemove',function(e){
 var r=svg.getBoundingClientRect(),vx=(e.clientX-r.left)/r.width*900,p=near(vx);
 xl.setAttribute('x1',p.x);xl.setAttribute('x2',p.x);xl.style.display='block';
 dot.setAttribute('cx',p.x);dot.setAttribute('cy',p.y);dot.style.display='block';
 var bp=(sup!=null&&res!=null&&res>sup)?Math.max(0,Math.min(100,(p.v-sup)/(res-sup)*100)):null;
 tip.innerHTML='<b>'+p.d+'</b><br>RS '+p.v+(bp!=null?' &middot; ~'+Math.round(bp)+'/100 '+(bp<=20?'cheap':bp>=80?'rich':'mid'):'');
 tip.style.display='block';
 var w=wrap.getBoundingClientRect();
 tip.style.left=Math.min(e.clientX-w.left+12,w.width-150)+'px';tip.style.top=(e.clientY-w.top-42)+'px';
 if(window.__tailMark)window.__tailMark(p.d);          // link: light the same moment on the rotation tail
});
svg.addEventListener('mouseleave',function(){xl.style.display='none';dot.style.display='none';tip.style.display='none';if(window.__tailMark)window.__tailMark(null);});
// exposed so the rotation tail can drive THIS crosshair to a given date (shared cursor)
function dn(s){return (+s.slice(0,4))*372+(+s.slice(5,7))*31+(+s.slice(8,10));}
window.__chGoto=function(d){if(!d)return;var b=pts[0],bk=1e18;for(var i=0;i<pts.length;i++){var k=Math.abs(dn(pts[i].d)-dn(d));if(k<bk){bk=k;b=pts[i];}}
 xl.setAttribute('x1',b.x);xl.setAttribute('x2',b.x);xl.style.display='block';dot.setAttribute('cx',b.x);dot.setAttribute('cy',b.y);dot.style.display='block';
 var bp2=(sup!=null&&res!=null&&res>sup)?Math.max(0,Math.min(100,(b.v-sup)/(res-sup)*100)):null;
 tip.innerHTML='<b>'+b.d+'</b><br>RS '+b.v+(bp2!=null?' &middot; ~'+Math.round(bp2)+'/100 '+(bp2<=20?'cheap':bp2>=80?'rich':'mid'):'');tip.style.display='block';tip.style.left='12px';tip.style.top='4px';};
})();
"""


# ── linked single-sector rotation tail (RS-Ratio × RS-Momentum), date-synced to the
#    channel above via one shared cursor: hover the channel → the same moment lights here,
#    hover a dot here → the channel crosshair jumps to that date. Level + rotation, one moment.
_LINK_TAIL_JS = r"""
(function(){
var T=__TAIL__;if(!T.length)return;
var mk=document.getElementById('rtmark'),rl=document.getElementById('rtread');
function dn(s){return (+s.slice(0,4))*372+(+s.slice(5,7))*31+(+s.slice(8,10));}
function q(r,m){return r>=100?(m>=100?'leading':'weakening'):(m>=100?'improving':'lagging');}
function nearD(d){var b=T[0],bk=1e18;for(var i=0;i<T.length;i++){var k=Math.abs(dn(T[i].d)-dn(d));if(k<bk){bk=k;b=T[i];}}return b;}
window.__tailMark=function(d){if(!d){if(mk)mk.style.display='none';return;}var p=nearD(d);if(!p||!mk)return;
 mk.setAttribute('cx',p.x);mk.setAttribute('cy',p.y);mk.style.display='block';
 if(rl)rl.innerHTML='rotation @ <b>'+p.d+'</b> &middot; '+q(p.r,p.m)+' &middot; RS-ratio '+p.r+' &middot; RS-mom '+p.m;};
Array.prototype.forEach.call(document.querySelectorAll('.rtdot'),function(c){c.style.cursor='pointer';
 c.addEventListener('mouseenter',function(){var d=c.getAttribute('data-d');window.__tailMark(d);if(window.__chGoto)window.__chGoto(d);});});
})();
"""


def _rot_tail_svg(tail: list) -> str:
    """Compact single-sector RRG tail (JdK RS-Ratio × RS-Momentum over the window),
    every period-dot date-tagged so the shared cursor can light the SAME moment the
    channel is showing. Returns '' if the tail is too short."""
    pts = [(p["rs_ratio"], p["rs_momentum"], p["date"]) for p in (tail or [])
           if p.get("rs_ratio") is not None and p.get("rs_momentum") is not None and p.get("date")]
    if len(pts) < 2:
        return ""
    devs = [abs(v - 100) for (a, b, _) in pts for v in (a, b)]
    half = max(6.0, min(34.0, (max(devs) if devs else 6.0) * 1.15))
    lo, hi = 100 - half, 100 + half
    L, R, T, B = 40, 400, 16, 300

    def X(v):
        return max(L + 2, min(R - 2, L + (v - lo) / (hi - lo) * (R - L)))

    def Y(v):
        return max(T + 2, min(B - 2, B - (v - lo) / (hi - lo) * (B - T)))

    cx, cy = X(100), Y(100)
    s = ['<svg id="rtsvg" viewBox="0 0 420 320" width="100%" style="max-width:420px" '
         'xmlns="http://www.w3.org/2000/svg">']
    s.append(f'<rect x="{L}" y="{T}" width="{cx-L:.0f}" height="{cy-T:.0f}" style="fill:var(--accent)" fill-opacity="0.05"/>')
    s.append(f'<rect x="{cx:.0f}" y="{T}" width="{R-cx:.0f}" height="{cy-T:.0f}" style="fill:var(--up)" fill-opacity="0.05"/>')
    s.append(f'<rect x="{cx:.0f}" y="{cy:.0f}" width="{R-cx:.0f}" height="{B-cy:.0f}" style="fill:var(--warn)" fill-opacity="0.05"/>')
    s.append(f'<rect x="{L}" y="{cy:.0f}" width="{cx-L:.0f}" height="{B-cy:.0f}" style="fill:var(--down)" fill-opacity="0.05"/>')
    s.append(f'<rect x="{L}" y="{T}" width="{R-L}" height="{B-T}" fill="none" style="stroke:var(--line-2)"/>')
    s.append(f'<line x1="{cx:.0f}" y1="{T}" x2="{cx:.0f}" y2="{B}" style="stroke:var(--line-2)" stroke-dasharray="3 3"/>')
    s.append(f'<line x1="{L}" y1="{cy:.0f}" x2="{R}" y2="{cy:.0f}" style="stroke:var(--line-2)" stroke-dasharray="3 3"/>')
    s.append(f'<text x="{L+5}" y="{T+12}" style="fill:var(--ink-3)" font-size="9">improving</text>')
    s.append(f'<text x="{R-5}" y="{T+12}" style="fill:var(--ink-3)" font-size="9" text-anchor="end">leading</text>')
    s.append(f'<text x="{R-5}" y="{B-5}" style="fill:var(--ink-3)" font-size="9" text-anchor="end">weakening</text>')
    s.append(f'<text x="{L+5}" y="{B-5}" style="fill:var(--ink-3)" font-size="9">lagging</text>')
    n = len(pts)
    # comet tail: per-segment lines + dots that fade IN toward now (oldest lightest,
    # most-recent strongest) so recency reads at a glance — not a flat, uniform web
    for i in range(n - 1):
        (a0, b0, _d0), (a1, b1, _d1) = pts[i], pts[i + 1]
        f = (i + 1) / n
        s.append(f'<line x1="{X(a0):.1f}" y1="{Y(b0):.1f}" x2="{X(a1):.1f}" y2="{Y(b1):.1f}" '
                 f'stroke="#58a6ff" stroke-opacity="{0.10 + 0.5 * f:.2f}" '
                 f'stroke-width="{0.8 + 1.4 * f:.1f}" stroke-linecap="round"/>')
    for i, (a, b, d) in enumerate(pts):
        f = (i + 1) / n
        s.append(f'<circle class="rtdot" data-d="{d}" cx="{X(a):.1f}" cy="{Y(b):.1f}" '
                 f'r="{2.2 + 1.8 * f:.1f}" style="fill:var(--ink-2)" fill-opacity="{0.2 + 0.7 * f:.2f}"/>')
    na, nb, _nd = pts[-1]
    s.append(f'<circle cx="{X(na):.1f}" cy="{Y(nb):.1f}" r="6" fill="#58a6ff" style="stroke:var(--ink)" stroke-width="1.5"/>')
    s.append('<circle id="rtmark" r="7.5" fill="none" stroke="#f0c000" stroke-width="2" style="display:none"/>')
    s.append('</svg>')
    tdata = json.dumps([{"x": round(X(a), 1), "y": round(Y(b), 1), "d": d,
                         "r": round(a, 1), "m": round(b, 1)} for (a, b, d) in pts])
    return ('<div id="rtwrap" style="position:relative">' + "".join(s) + '</div>'
            '<div class="sub" id="rtread" style="margin-top:4px;min-height:16px">'
            'hover the channel above (or a dot) to sync level ↔ rotation</div>'
            + '<script>' + _LINK_TAIL_JS.replace("__TAIL__", tdata) + '</script>')


def _channel_svg(series: list[tuple], m: dict) -> str:
    """The RS line over its full history inside its current support/resistance band
    (flat 3y-window rails) + median + POC + the all-time envelope + the now-dot,
    with a hover crosshair (date · RS value · ~position in the current band)."""
    step = max(1, len(series) // 400)
    pts = series[::step]
    if pts[-1] != series[-1]:
        pts.append(series[-1])
    dates = [p[0] for p in pts]
    vals = [p[1] for p in pts]
    sup, res, mid = m.get("rs_band_low"), m.get("rs_band_high"), m.get("rs_band_mid")
    poc, ath, atl = m.get("rs_poc"), m.get("rs_alltime_high"), m.get("rs_alltime_low")
    allv = vals + [x for x in (sup, res, mid, poc, ath, atl) if x is not None]
    vmin, vmax = min(allv) * 0.98, max(allv) * 1.02
    L, R, T, B = 58, 862, 22, 300
    n = len(vals)

    def X(i):
        return L + (i / (n - 1)) * (R - L) if n > 1 else L

    def Y(v):
        return B - (v - vmin) / (vmax - vmin) * (B - T) if vmax > vmin else (T + B) / 2

    dotc = "var(--up)" if (m.get("slope_3m_pct") or 0) > 0 else "var(--down)"
    s = ['<svg id="chsvg" viewBox="0 0 900 322" width="100%" xmlns="http://www.w3.org/2000/svg">']
    if sup is not None and res is not None:
        s.append(f'<rect x="{L}" y="{Y(res):.1f}" width="{R-L}" height="{Y(sup)-Y(res):.1f}" '
                 f'fill="#58a6ff" fill-opacity="0.07"/>')
    for lv in (ath, atl):
        if lv is not None:
            s.append(f'<line x1="{L}" y1="{Y(lv):.1f}" x2="{R}" y2="{Y(lv):.1f}" style="stroke:var(--ink-3)" '
                     f'stroke-width="1" stroke-dasharray="1 4" stroke-opacity="0.6"/>')
    if res is not None:
        s.append(f'<line x1="{L}" y1="{Y(res):.1f}" x2="{R}" y2="{Y(res):.1f}" stroke="#d29922" stroke-width="1.3"/>')
        s.append(f'<text x="{R+4}" y="{Y(res)+3:.1f}" fill="#d29922" font-size="10">res</text>')
    if sup is not None:
        s.append(f'<line x1="{L}" y1="{Y(sup):.1f}" x2="{R}" y2="{Y(sup):.1f}" style="stroke:var(--up)" stroke-width="1.3"/>')
        s.append(f'<text x="{R+4}" y="{Y(sup)+3:.1f}" style="fill:var(--up)" font-size="10">sup</text>')
    if mid is not None:
        s.append(f'<line x1="{L}" y1="{Y(mid):.1f}" x2="{R}" y2="{Y(mid):.1f}" style="stroke:var(--ink-2)" '
                 f'stroke-width="1" stroke-dasharray="4 4"/>')
    if poc is not None:
        s.append(f'<line x1="{L}" y1="{Y(poc):.1f}" x2="{R}" y2="{Y(poc):.1f}" stroke="#bc8cff" '
                 f'stroke-width="1" stroke-dasharray="2 3"/>')
        s.append(f'<text x="{R+4}" y="{Y(poc)+3:.1f}" fill="#bc8cff" font-size="10">POC</text>')
    poly = " ".join(f"{X(i):.1f},{Y(vals[i]):.1f}" for i in range(n))
    s.append(f'<polyline points="{poly}" fill="none" stroke="#58a6ff" stroke-width="1.5" stroke-opacity="0.9"/>')
    if res is not None:
        s.append(f'<line x1="{X(n-1):.1f}" y1="{Y(res):.1f}" x2="{X(n-1):.1f}" y2="{Y(vals[-1]):.1f}" '
                 f'style="stroke:{dotc}" stroke-width="1.5" stroke-dasharray="2 3"/>')
    s.append(f'<circle cx="{X(n-1):.1f}" cy="{Y(vals[-1]):.1f}" r="7" style="fill:{dotc};stroke:var(--ink)" stroke-width="2"/>')
    for i in (0, n // 3, 2 * n // 3, n - 1):
        s.append(f'<text x="{X(i):.1f}" y="{B+15}" style="fill:var(--ink-2)" font-size="9" text-anchor="middle">{_esc(dates[i][:4])}</text>')
    s.append(f'<line id="chx" x1="0" y1="{T}" x2="0" y2="{B}" stroke-width="1" stroke-dasharray="3 3" style="display:none;stroke:var(--ink-2)"/>')
    s.append('<circle id="chd" r="4" stroke-width="1.4" style="display:none;fill:var(--ink);stroke:var(--bg-1)"/>')
    s.append('</svg>')
    pdata = json.dumps({"pts": [{"x": round(X(i), 1), "y": round(Y(vals[i]), 1),
                                 "d": dates[i], "v": round(vals[i], 4)} for i in range(n)],
                        "sup": sup, "res": res})
    return ('<div id="chwrap" style="position:relative">' + "".join(s)
            + '<div id="chtip" style="position:absolute;display:none;pointer-events:none;background:var(--bg-2);'
            'border:1px solid var(--line-2);border-radius:6px;padding:5px 8px;font-size:12px;color:var(--ink);'
            'z-index:5;white-space:nowrap"></div></div>'
            + '<div class="sub" style="margin-top:4px">'
            '<span style="color:#d29922">&mdash;</span> resistance &nbsp; '
            '<span style="color:var(--up)">&mdash;</span> support &nbsp; '
            '<span style="color:#bc8cff">&middot;&middot;&middot;</span> POC (magnet) &nbsp; '
            '<span style="color:var(--ink-2)">&ndash;&ndash;</span> median &nbsp; '
            '<span style="color:var(--ink-3)">&middot;&middot;</span> all-time hi/lo &nbsp;·&nbsp; hover to scrub</div>'
            + '<script>' + _CH_HOVER_JS.replace("__CH__", pdata) + '</script>')


def _mc(label: str, value: str, color: str = "var(--ink)") -> str:
    return (f'<div style="background:var(--bg-2);border-radius:6px;padding:8px 12px;min-width:118px">'
            f'<div class="sub" style="margin:0;font-size:11px">{label}</div>'
            f'<div style="font-size:18px;color:{color}">{value}</div></div>')


def _channel_readout(m: dict, verdict: str, why: str, to_res, to_sup) -> str:
    bp = m["rs_band_pct"]
    lab = ("at RS support" if bp <= 15 else "lower band" if bp < 35 else "mid-band"
           if bp < 65 else "upper band" if bp < 85 else "at RS resistance")
    vc = {"Accumulate": "var(--up)", "Add": "var(--up)", "Ride": "var(--up)",
          "Avoid": "var(--down)", "Fade": "var(--down)", "Hold": "var(--ink-2)"}.get(verdict, "#d29922")
    bpcol = ("var(--up)" if bp <= 20 else "#d29922" if bp >= 80 else "var(--ink)")
    cards = (
        _mc("band position", f'{_n(bp)} <span class="sub" style="margin:0;font-size:11px">{lab}</span>', bpcol)
        + _mc("regime", _esc(m["rs_regime"].replace("_", "-").lower()),
              "#d29922" if m["rs_regime"] == "TRENDING" else "#39c5bb")
        + _mc("to resistance", "—" if to_res is None else f"+{to_res:.0f}%")
        + _mc("to support", "—" if to_sup is None else f"&minus;{abs(to_sup):.0f}%")
        + _mc("trend-R²", _n(m["rs_trend_r2"], 2))
        + _mc("state", _esc(m["rs_band_state"]))
    )
    return ('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:10px;margin-top:12px">' + cards + '</div>'
            f'<div style="margin-top:10px;font-size:15px"><span style="color:{vc};font-weight:500">{_esc(verdict)}</span> '
            f'<span class="sub" style="margin:0">— {_esc(why)}</span></div>')


def _channel_page(label_html: str, den: str, series, m, fl, back_href: str,
                  back_label: str, extra: str = "", tail=None) -> str:
    head = (f'<a class="row" style="display:inline;color:#58a6ff;text-decoration:none" '
            f'href="{back_href}">{back_label}</a>{extra}')
    if not m or m.get("rs_band_pct") is None or len(series) < 60:
        return (head + f'<h2 style="margin-top:6px">{label_html} — RS band</h2>'
                '<div class="card"><div class="sub">Not enough RS history for a band chart yet.</div></div>')
    v, why = rsband.band_verdict(m["rs_band_pct"], m["rs_regime"], m["slope_3m_pct"],
                                 m["rs_band_state"], falls_less=fl, trend_drift=m["rs_trend_drift"])
    last = series[-1][1]
    res, sup = m["rs_band_high"], m["rs_band_low"]
    to_res = ((res - last) / last * 100.0) if (res and last) else None
    to_sup = ((last - sup) / last * 100.0) if (sup and last) else None
    rot = ""
    rt = _rot_tail_svg(tail) if tail else ""
    if rt:
        rot = ('<div class="card" style="padding:10px 12px;margin-top:10px">'
               '<div class="sub" style="margin:0 0 6px"><b>Rotation path</b> — the same window in '
               'RS-Ratio × RS-Momentum. Hover the channel above (or a dot) and the matching moment '
               'lights in both: <b>level</b> (band) ↔ <b>rotation</b> (quadrant).</div>' + rt + '</div>')
    return (head
            + f'<h2 style="margin-top:6px">{label_html} — RS band '
              f'<span class="sub" style="margin:0">vs {_esc(den)} · where it sits in its own history</span></h2>'
            + '<div class="card" style="padding:10px 12px">' + _channel_svg(series, m) + '</div>'
            + rot
            + _channel_readout(m, v, why, to_res, to_sup))


def render_band_channel(num: str, den: str = "Nifty 500", conn=None) -> str:
    own = conn is None                      # CL-VIEW-10: `with`, not manual enter/exit
    with (get_conn() if own else nullcontext(conn)) as conn:
        den = den if den in BENCHMARKS else "Nifty 500"
        m = rsband.band_one(num, den, conn=conn)
        series = _ratio_series(conn, num, den)
        fl = None
        try:
            for c in (capture.latest_all(den, conn=conn) or []):
                if c["numerator"] == num:
                    dc = c.get("down_capture_63")
                    fl = (dc is not None and dc < 1.0)
                    break
        except Exception:
            pass
        tail = None
        try:                                  # single-sector rotation tail → the linked cursor
            from src.web.rrg_view import _sector_tail
            tail = _sector_tail(num, den, "12", conn)
        except Exception:
            tail = None
    return _channel_page(_esc(num), den, series, m, fl, "/dash/rsband",
                         "&larr; Back to the band", tail=tail)


def _stock_ratio_series(conn, sym: str, den: str) -> list[tuple]:
    """A stock's RS series = split-adjusted bhavcopy close ÷ benchmark close, aligned."""
    brows = conn.execute("SELECT trade_date, close_value FROM index_rows WHERE index_name=? "
                         "AND close_value>0 ORDER BY trade_date ASC", (den,)).fetchall()
    ben = {r["trade_date"]: r["close_value"] for r in brows}
    if not ben:
        return []
    braw = conn.execute("SELECT trade_date, close, prev_close FROM bhavcopy_rows WHERE symbol=? "
                        "AND series='EQ' AND (segment='CM' OR segment IS NULL) ORDER BY trade_date ASC",
                        (sym,)).fetchall()
    if not braw:
        return []
    braw = [dict(r) for r in braw]
    adj = adjust.adjusted_closes(braw)
    out = []
    for r, a in zip(braw, adj):
        b = ben.get(r["trade_date"])
        if a and a > 0 and b and b > 0:
            out.append((r["trade_date"], a / b))
    return out


def render_stock_channel(sym: str, den: str = "Nifty 500", back_idx: str = "", conn=None) -> str:
    own = conn is None                      # CL-VIEW-10: `with`, not manual enter/exit
    with (get_conn() if own else nullcontext(conn)) as conn:
        den = den if den in BENCHMARKS else "Nifty 500"
        series = _stock_ratio_series(conn, sym, den)
        # CL-VIEW-06: lane_from_series tolerates a thin/1-point series — compute_one()
        # returns None below MIN_HISTORY (504 pts), so `if series` + that floor is enough.
        m = rsband.lane_from_series([v for _, v in series], series[-1][0]) if series else None
    back_href = f'/dash/rsband?idx={quote_plus(back_idx)}' if back_idx else "/dash/rsband"
    back_label = ("&larr; Back to " + _esc(back_idx)) if back_idx else "&larr; Back to the band"
    extra = (f'<a class="row" style="display:inline;color:#58a6ff;text-decoration:none;margin-left:14px" '
             f'href="/dash/rrg?sym={quote_plus(sym)}">rotation (RRG) &rarr;</a>'
             f'<a class="row" style="display:inline;color:#58a6ff;text-decoration:none;margin-left:14px" '
             f'href="/dash/stock?sym={quote_plus(sym)}">full stock page &rarr;</a>')
    return _channel_page(_esc(sym), den, series, m, None, back_href, back_label, extra=extra)


def band_section(num: str = "", sym: str = "", den: str = "Nifty 500", conn=None) -> str:
    """A compact, embeddable RS-band section (chart + readout + 'open full →' link),
    for the index-detail / stock pages. Pass num (an index) OR sym (a stock). Returns
    '' when there isn't enough RS history — so it embeds cleanly on any page."""
    own = conn is None                      # CL-VIEW-10: `with`, not manual enter/exit
    with (get_conn() if own else nullcontext(conn)) as conn:
        den = den if den in BENCHMARKS else "Nifty 500"
        fl = None
        if sym:
            series = _stock_ratio_series(conn, sym, den)
            m = rsband.lane_from_series([v for _, v in series], series[-1][0]) if series else None
            label, full = sym, f"/dash/rsband?sym={quote_plus(sym)}"
        else:
            m = rsband.band_one(num, den, conn=conn)
            series = _ratio_series(conn, num, den)
            label, full = num, f"/dash/rsband?idx={quote_plus(num)}"
            try:
                for c in (capture.latest_all(den, conn=conn) or []):
                    if c["numerator"] == num:
                        dc = c.get("down_capture_63")
                        fl = (dc is not None and dc < 1.0)
                        break
            except Exception:
                pass
    if not m or m.get("rs_band_pct") is None or len(series) < 60:
        return ""
    v, why = rsband.band_verdict(m["rs_band_pct"], m["rs_regime"], m["slope_3m_pct"],
                                 m["rs_band_state"], falls_less=fl, trend_drift=m["rs_trend_drift"])
    last = series[-1][1]
    res, sup = m["rs_band_high"], m["rs_band_low"]
    to_res = ((res - last) / last * 100.0) if (res and last) else None
    to_sup = ((last - sup) / last * 100.0) if (sup and last) else None
    return ('<h2 style="margin-top:14px">RS support &amp; resistance '
            f'<span class="sub" style="margin:0">where {_esc(label)} sits in its own band vs {_esc(den)} · '
            f'<a class="row" style="display:inline" href="{full}">open full →</a></span></h2>'
            '<div class="card" style="padding:10px 12px">' + _channel_svg(series, m) + '</div>'
            + _channel_readout(m, v, why, to_res, to_sup))


def band_home_inner(den: str = "Nifty 500", conn=None) -> str:
    """Compact Home-board inner: cheapest (near support) + richest (near resistance)
    + any band breakouts, from the STORED rsband_signals (fast — no on-read recompute).
    Returns '' if the band table isn't populated yet."""
    own = conn is None                      # CL-VIEW-10: `with`, not manual enter/exit
    with (get_conn() if own else nullcontext(conn)) as conn:
        den = den if den in BENCHMARKS else "Nifty 500"
        rows = rsband.latest_all(den, conn=conn)
        falls = {}
        try:
            for c in (capture.latest_all(den, conn=conn) or []):
                dc = c.get("down_capture_63")
                falls[c["numerator"]] = (dc is not None and dc < 1.0)
        except Exception:
            pass
    keep = set(_REAL_SECTORS) if _REAL_SECTORS else None
    data = []
    for r in rows:
        if (keep is not None and r["numerator"] not in keep) or r["rs_band_pct"] is None:
            continue
        v, _why = rsband.band_verdict(r["rs_band_pct"], r["rs_regime"], r["slope_3m_pct"],
                                      r["rs_band_state"], falls_less=falls.get(r["numerator"]),
                                      trend_drift=r["rs_trend_drift"])
        data.append({"k": r["numerator"].replace("Nifty ", "").replace(" Index", ""),
                     "n": r["numerator"], "band": r["rs_band_pct"], "verdict": v,
                     "state": r["rs_band_state"]})
    if not data:
        return ""
    data.sort(key=lambda d: d["band"])
    vc = {"Accumulate": "var(--up)", "Add": "var(--up)", "Ride": "var(--up)",
          "Avoid": "var(--down)", "Fade": "var(--down)", "Hold": "var(--ink-2)"}

    def row(d):
        bcol = "var(--up)" if d["band"] <= 20 else "#d29922" if d["band"] >= 80 else "var(--ink)"
        c = vc.get(d["verdict"], "#d29922")
        return (f'<tr><td class="l"><a class="row" href="/dash/rsband?idx={quote_plus(d["n"])}">'
                f'<span class="sym">{_esc(d["k"])}</span></a></td>'
                f'<td class="r" style="color:{bcol}">{_n(d["band"])}</td>'
                f'<td class="r"><span style="color:{c};font-size:11px">{_esc(d["verdict"])}</span></td></tr>')

    breaks = [d for d in data if d["state"] in ("BREAKOUT_UP", "BREAKDOWN_DN")
              or d["band"] > 100 or d["band"] < 0]
    out = ['<table class="ck-t"><tbody>',
           '<tr><td colspan="3" class="mut" style="font-size:11px">CHEAP · near support</td></tr>']
    out += [row(d) for d in data[:4]]
    out.append('<tr><td colspan="3" class="mut" style="padding-top:8px;font-size:11px">RICH · near resistance</td></tr>')
    out += [row(d) for d in reversed(data[-4:])]
    if breaks:
        out.append('<tr><td colspan="3" class="mut" style="padding-top:8px;font-size:11px">&#9889; breaking the band</td></tr>')
        out += [row(d) for d in breaks[:3]]
    out.append('</tbody></table>')
    return "".join(out)


# ── constituent drilldown: the STOCKS inside one index, each on a band lane ────
_CONSTITUENT_CAP = 16          # bound the on-read compute
_CONSTITUENT_MIN = 520         # ≥ ~2y of stock history for a band (rsband.MIN_HISTORY)


def _members(index_name: str, conn) -> list[str]:
    rows = conn.execute(
        "SELECT m.symbol FROM stock_index_membership m WHERE UPPER(m.index_name)=UPPER(?) "
        "AND m.snapshot_date=(SELECT MAX(snapshot_date) FROM stock_index_membership "
        "WHERE UPPER(index_name)=UPPER(?))", (index_name, index_name)).fetchall()
    return [r["symbol"] for r in rows]


def _constituent_data(index_name: str, conn, vs: str = "broad") -> list[dict]:
    """Each member stock's RS band vs the chosen benchmark, built on-read from
    split-adjusted bhavcopy closes ÷ the benchmark close. vs='sector' = vs the index
    itself (who's cheap/rich WITHIN the sector); vs='broad' = vs Nifty 500."""
    ben = index_name if vs == "sector" else "Nifty 500"
    brows = conn.execute("SELECT trade_date, close_value FROM index_rows WHERE index_name=? "
                         "AND close_value>0 ORDER BY trade_date ASC", (ben,)).fetchall()
    ben_map = {r["trade_date"]: r["close_value"] for r in brows}
    if not ben_map:
        return []
    out = []
    for sym in _members(index_name, conn)[:_CONSTITUENT_CAP]:
        braw = conn.execute(
            "SELECT trade_date, close, prev_close FROM bhavcopy_rows WHERE symbol=? "
            "AND series='EQ' AND (segment='CM' OR segment IS NULL) ORDER BY trade_date ASC",
            (sym,)).fetchall()
        if len(braw) < _CONSTITUENT_MIN:
            continue
        braw = [dict(r) for r in braw]
        adj = adjust.adjusted_closes(braw)
        rs, last = [], None
        for r, a in zip(braw, adj):
            b = ben_map.get(r["trade_date"])
            if a and a > 0 and b and b > 0:
                rs.append(a / b)
                last = r["trade_date"]
        if len(rs) < _CONSTITUENT_MIN:
            continue
        lane = rsband.lane_from_series(rs, last)
        if not lane or lane.get("rs_band_pct") is None:
            continue
        v, why = rsband.band_verdict(lane["rs_band_pct"], lane["rs_regime"], lane["slope_3m_pct"],
                                     lane["rs_band_state"], trend_drift=lane["rs_trend_drift"])
        out.append({"k": sym, "n": sym, "band": lane["rs_band_pct"], "path": lane["band_path"],
                    "poc": lane["rs_poc_pct"], "regime": lane["rs_regime"], "state": lane["rs_band_state"],
                    "tr2": lane["rs_trend_r2"], "verdict": v, "why": why,
                    "href": f"/dash/rsband?sym={quote_plus(sym)}&idx={quote_plus(index_name)}"})
    out.sort(key=lambda d: d["band"] if d["band"] is not None else 1e9)
    return out


def _vs_pills(index_name: str, vs: str) -> str:
    def pill(v, label):
        on = "background:#1f6feb;border-color:#1f6feb;color:#fff;" if v == vs else ""
        return (f'<a href="/dash/rsband?idx={quote_plus(index_name)}&vs={v}" class="pill" '
                f'style="text-decoration:none;margin-right:6px;{on}">{label}</a>')
    return pill("broad", "vs Nifty 500") + pill("sector", "vs " + _esc(index_name))


def render_constituents(index_name: str, conn, vs: str = "broad") -> str:
    ben_label = _esc(index_name) if vs == "sector" else "Nifty 500"
    head = (f'<h2 style="margin-top:16px">Constituents '
            f'<span class="sub" style="margin:0">{_esc(index_name)} stocks · band vs {ben_label} · '
            f'click a stock for its page</span></h2>'
            f'<div style="margin:6px 0">{_vs_pills(index_name, vs)}</div>')
    data = _constituent_data(index_name, conn, vs)
    if not data:
        return (head + '<div class="card"><div class="sub">No constituent band data — membership '
                'or price history is missing for this index.</div></div>')
    return (head + _chart_block(data)
            + _table(data, ben_label,
                     link_fn=lambda nm: f'/dash/rsband?sym={quote_plus(nm)}&idx={quote_plus(index_name)}'))


@router.get("/dash/rsband", response_class=HTMLResponse)
def rsband_page(den: str = Query("Nifty 500", max_length=40),
                idx: str = Query("", max_length=60),
                vs: str = Query("broad", max_length=8),
                sym: str = Query("", max_length=30),
                view: str = Query("lanes", max_length=6),
                tail: str = Query("12", max_length=2)) -> HTMLResponse:
    den = den if den in BENCHMARKS else "Nifty 500"
    if sym:                                # DEEPEST DRILL: one stock's band Channel
        with get_conn() as conn:
            body = render_stock_channel(sym, den, idx, conn=conn)
        return HTMLResponse(_shell(f"{sym} — RS band", body, active="markets", wide=True))
    if idx:                                # DRILL: one sector's Channel + its constituents
        vs = vs if vs in ("broad", "sector") else "broad"
        with get_conn() as conn:
            body = render_band_channel(idx, den, conn=conn) + render_constituents(idx, conn, vs)
        return HTMLResponse(_shell(f"{idx} — RS band", body, active="markets", wide=True))
    view = view if view in ("lanes", "clock", "rrg") else "lanes"
    return HTMLResponse(_shell("RS support & resistance", render_band_lanes(den, view, tail=tail),
                               active="markets", wide=True))
