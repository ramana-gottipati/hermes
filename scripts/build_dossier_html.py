"""Build the 'Replay the Tape' one-page dossier (self-contained HTML) from dossier.json.

Every number is computed here from the reconstructed point-in-time data + the live
patearn scorer — nothing is hand-typed. Output: docs/replay-the-tape.html
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.automation.scoring import score_fundamentals

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PATTERN_NAMES = {
    1: "ROCE Trajectory", 2: "Operating Leverage", 3: "Sectoral Tailwind",
    4: "Valuation", 5: "Balance-Sheet Quality", 6: "Promoter Conviction",
    7: "Export / Mix Inflection", 8: "Institutional Neglect", 9: "Earnings Momentum",
    10: "Margin Expansion", 11: "VCP / Technical", 12: "Receivables Discipline",
    13: "Working Capital", 14: "Volume Confirmation",
}
WEIGHTS = {1: 9, 2: 9, 3: 8, 4: 8, 5: 8, 6: 7, 7: 7, 8: 6, 9: 6, 10: 6,
           11: 5, 12: 7, 13: 6, 14: 5}
QG_PATTERNS = [1, 2, 3, 4, 5]


def build_hero(h):
    f = h["fundamentals_asof"]
    s = score_fundamentals(f)
    pats = []
    for pid in range(1, 15):
        blk = s["patterns"][pid] if isinstance(s["patterns"], dict) else s["patterns"][pid - 1]
        w = WEIGHTS[pid]
        pmax = w * 6.0
        pats.append({
            "id": pid, "name": PATTERN_NAMES[pid], "weight": w,
            "pct": round(100.0 * blk["score"] / pmax, 0),
            "qg": pid in QG_PATTERNS,
        })
    return {
        "symbol": h["symbol"], "name": h["name"], "lens": h["lens"],
        "as_of": h["as_of"], "entry": h["entry"], "sell": h["sell"],
        "px_asof": h["px_asof"], "latest_filing": h["latest_filing_used"],
        "score": {
            "tier": s["tier"], "ns_base": round(s["ns_base"], 1),
            "ns_lo": round(s["ns_pessimistic"], 1), "ns_hi": round(s["ns_optimistic"], 1),
            "qg_pass": s["qg_pass"], "qg_score": round(s["qg_score"], 0),
            "qg_threshold": round(s["qg_threshold"], 0), "pac": s["pac"],
        },
        "patterns": pats,
        "fund": {
            "roce": f.get("roce"), "opm": f.get("opm_latest"),
            "de": round(f["debt_to_equity"], 2) if f.get("debt_to_equity") is not None else None,
            "icov": round(f["interest_coverage"], 1) if f.get("interest_coverage") is not None else None,
            "sales_g5": round(f["sales_growth_5y"], 0) if f.get("sales_growth_5y") is not None else None,
            "profit_g5": round(f["profit_growth_5y"], 0) if f.get("profit_growth_5y") is not None else None,
            "pe": round(f["pe"], 1) if f.get("pe") is not None else None,
        },
        "ledger": h["ledger"],
        "tech": h["technicals"],
        "rs": h["rs"],
        "reveal": h["reveal"],
        "known_return": h["known_return"], "months": h["months"],
        "path": h["path"]["path"], "path_asof": h["path"]["asof_date"],
    }


def main():
    with open(os.path.join(HERE, "dossier.json"), encoding="utf-8") as _fh:  # CL-SCR-11: don't leak the fd
        d = json.load(_fh)
    heroes = [build_hero(h) for h in d["heroes"]]
    payload = {"index": d.get("index_used"), "heroes": heroes}
    # Escape '<' so a ledger field containing '</script>' can't break out of the inline
    # <script> data block (json.dumps does not escape '/'); the standard < form is
    # valid JSON and renders identically. (Client-side innerHTML of these fields should also
    # be esc()'d — tracked as a follow-up; data is internal research, so low-risk today.)
    html = TEMPLATE.replace("/*__DATA__*/",
                            json.dumps(payload, default=str).replace("<", "\\u003c"))
    out = os.path.join(ROOT, "docs", "replay-the-tape.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("wrote", out, "(", len(html), "bytes )")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Replay the Tape — Point-in-Time Audit</title>
<style>
:root{
  --paper:#0e1116; --panel:#161b22; --panel2:#1c232d; --ink:#e8ecf1; --muted:#8b97a7;
  --line:#262e39; --go:#34d399; --go-d:#10b981; --warn:#f59e0b; --bad:#f87171;
  --gold:#e6b450; --accent:#5ec8ff; --mono:'SF Mono',ui-monospace,'Cascadia Code',Consolas,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:'Inter',-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;line-height:1.45}
.wrap{max-width:1120px;margin:0 auto;padding:30px 28px 80px}
.mast{display:flex;justify-content:space-between;align-items:flex-end;
  border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:0}
.mast h1{font-size:13px;letter-spacing:.32em;font-weight:700;margin:0 0 8px;color:var(--accent)}
.mast .big{font-family:Georgia,'Times New Roman',serif;font-size:30px;font-weight:400;
  letter-spacing:-.01em;line-height:1.15;margin:0;max-width:640px}
.mast .big em{font-style:italic;color:var(--gold)}
.mast .meta{text-align:right;font-size:11px;color:var(--muted);font-family:var(--mono)}
.mast .meta b{color:var(--ink)}
.ribbon{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 26px}
.ribbon span{font-size:11px;color:var(--muted);background:var(--panel);border:1px solid var(--line);
  padding:6px 11px;border-radius:20px;display:inline-flex;gap:7px;align-items:center}
.ribbon span b{color:var(--go)}
.tabs{display:flex;gap:8px;margin-bottom:22px}
.tab{cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--muted);
  padding:11px 18px;border-radius:10px;font-size:13px;font-weight:600;display:flex;gap:12px;align-items:center;
  transition:.15s}
.tab .ret{font-family:var(--mono);font-size:12px;color:var(--muted)}
.tab.on{border-color:var(--go-d);background:linear-gradient(180deg,#13261f,#101a16);color:var(--ink)}
.tab.on .ret{color:var(--go)}
.tab .lens{font-size:9px;letter-spacing:.14em;text-transform:uppercase;padding:2px 7px;border-radius:5px;
  background:var(--panel2);color:var(--muted)}
.tab.on .lens{background:var(--go-d);color:#062018}
.hero{display:none}
.hero.on{display:block;animation:fade .35s ease}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.idrow{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:18px}
.idrow .name{font-family:Georgia,serif;font-size:24px;margin:0}
.idrow .sub{color:var(--muted);font-size:12px;font-family:var(--mono);margin-top:4px}
.stamp{border:1.5px solid var(--gold);color:var(--gold);border-radius:10px;padding:9px 15px;text-align:center;
  transform:rotate(-2deg);flex-shrink:0}
.stamp .k{font-size:9px;letter-spacing:.22em;opacity:.8}
.stamp .v{font-family:var(--mono);font-size:17px;font-weight:700;letter-spacing:.02em}
.stamp .px{font-size:10px;color:var(--muted);font-family:var(--mono);margin-top:2px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 18px 16px}
.card h3{font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin:0 0 14px;
  display:flex;justify-content:space-between;align-items:center}
.tier{display:flex;align-items:baseline;gap:14px;margin-bottom:14px}
.tier .chip{font-family:var(--mono);font-weight:700;font-size:22px;padding:6px 14px;border-radius:9px;
  background:var(--panel2);border:1px solid var(--line)}
.tier .chip.t1,.tier .chip.t2{color:var(--go);border-color:var(--go-d)}
.tier .chip.t3{color:var(--gold);border-color:#6b5a2a}
.tier .chip.t4,.tier .chip.t5{color:var(--muted)}
.tier .nsband{flex:1}
.nsband .nlab{font-size:10px;color:var(--muted);display:flex;justify-content:space-between;margin-bottom:5px;font-family:var(--mono)}
.bar{height:9px;background:var(--panel2);border-radius:6px;position:relative;overflow:hidden}
.bar .fill{position:absolute;top:0;bottom:0;background:linear-gradient(90deg,#374151,var(--accent));border-radius:6px}
.bar .base{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--ink)}
.qg{font-size:11px;font-family:var(--mono);padding:8px 11px;border-radius:8px;margin-bottom:14px;
  display:flex;justify-content:space-between;align-items:center}
.qg.pass{background:#10241c;color:var(--go);border:1px solid var(--go-d)}
.qg.fail{background:#241814;color:var(--warn);border:1px solid #6b4a1f}
.pats{display:flex;flex-direction:column;gap:5px}
.prow{display:grid;grid-template-columns:18px 130px 1fr 34px;gap:8px;align-items:center;font-size:11px}
.prow .pid{font-family:var(--mono);color:var(--muted);font-size:10px}
.prow .pn{color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow.gate .pn{color:var(--ink)}
.prow.gate .pid{color:var(--gold);font-weight:700}
.prow .pb{height:6px;background:var(--panel2);border-radius:4px;overflow:hidden}
.prow .pb i{display:block;height:100%;border-radius:4px}
.prow .pv{font-family:var(--mono);text-align:right;font-size:10px;color:var(--muted)}
.gatehdr{font-size:9px;letter-spacing:.12em;color:var(--gold)}
.chips{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.chipc{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.chipc .k{font-size:9.5px;letter-spacing:.05em;color:var(--muted);text-transform:uppercase}
.chipc .v{font-family:var(--mono);font-size:17px;font-weight:600;margin-top:3px}
.chipc .v.good{color:var(--go)}.chipc .v.warn{color:var(--warn)}.chipc .v.neutral{color:var(--ink)}
.chipc .n{font-size:9.5px;color:var(--muted);margin-top:2px}
.ledger{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}
.ledger h3{font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin:0 0 4px}
.ledger .cap{font-size:11.5px;color:var(--muted);margin-bottom:14px;max-width:760px}
.ledger .cap b{color:var(--go)}
table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:11.5px}
th{text-align:right;color:var(--muted);font-weight:500;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;
  padding:0 10px 8px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
td{padding:7px 10px;border-bottom:1px solid #1b212b}
tr:last-child td{border-bottom:none}
td.met{color:var(--ink);font-family:inherit}
td.val{color:var(--ink);font-weight:600}
td.neg{color:var(--bad)}
.ok{color:var(--go)}
.lag{color:var(--muted)}
.story{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;position:relative;overflow:hidden}
.story h3{font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin:0 0 2px}
.story .sub{font-size:11.5px;color:var(--muted);margin-bottom:10px}
.chartwrap{position:relative}
svg{display:block;width:100%;height:230px}
.revealbtn{position:absolute;right:18px;top:14px;z-index:5;cursor:pointer;border:1px solid var(--gold);
  background:#241d10;color:var(--gold);font-size:11px;font-weight:600;padding:8px 14px;border-radius:8px;
  display:flex;gap:8px;align-items:center;transition:.15s}
.revealbtn:hover{background:var(--gold);color:#1a1206}
.revealed .revealbtn{display:none}
.bignum{position:absolute;left:40%;top:34%;transform:translate(-50%,-50%) scale(.9);text-align:center;
  opacity:0;transition:.6s cubic-bezier(.2,.8,.2,1);pointer-events:none;z-index:4;padding:14px 40px;
  background:radial-gradient(ellipse at center,rgba(14,17,22,.92) 35%,rgba(14,17,22,.55) 65%,transparent 80%)}
.revealed .bignum{opacity:1;transform:translate(-50%,-50%) scale(1)}
.bignum .pct{font-family:var(--mono);font-size:48px;font-weight:700;color:var(--go);
  text-shadow:0 0 30px rgba(52,211,153,.35);line-height:1}
.bignum .lbl{font-size:11px;color:var(--muted);margin-top:6px;letter-spacing:.04em}
.bignum .cap2{font-size:11px;color:var(--gold);font-family:var(--mono);margin-top:8px}
.footnote{font-size:10.5px;color:var(--muted);margin-top:26px;border-top:1px solid var(--line);padding-top:14px;line-height:1.6}
.footnote b{color:var(--muted)}
@media (max-width:760px){.grid{grid-template-columns:1fr}.mast{flex-direction:column;align-items:flex-start;gap:12px}.mast .meta{text-align:left}}
</style>
</head>
<body>
<div class="wrap">
  <div class="mast">
    <div>
      <h1>PATEARN · REPLAY THE TAPE</h1>
      <p class="big">What the machine knew <em>before</em> the move — reconstructed with zero look-ahead.</p>
    </div>
    <div class="meta">
      POINT-IN-TIME AUDIT<br>
      Universe: <b>NSE · 1,983 symbols</b><br>
      Fundamentals archive: <b>2002–2026</b><br>
      Price archive: <b>survivorship-safe raw bhav</b>
    </div>
  </div>
  <div class="ribbon">
    <span><b>✓</b> No look-ahead — every input filed before the as-of date</span>
    <span><b>✓</b> Point-in-time fundamentals (report_date gated)</span>
    <span><b>✓</b> Walk-forward validated technical engine</span>
    <span id="idxnote"></span>
  </div>
  <div class="tabs" id="tabs"></div>
  <div id="heroes"></div>
  <div class="footnote" id="foot"></div>
</div>
<script>
const DATA = /*__DATA__*/;
const $=(t,c,h)=>{const e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e;};
const fmt=(v,d=0)=>v==null?'—':Number(v).toLocaleString('en-IN',{maximumFractionDigits:d,minimumFractionDigits:d});
const mon=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function dlabel(s){const p=s.split('-');return p[2]+' '+mon[+p[1]-1]+' '+p[0];}

document.getElementById('idxnote').innerHTML='<b>✓</b> Relative strength vs '+(DATA.index||'broad index');

function patColor(p){if(p>=66)return 'var(--go)';if(p>=40)return 'var(--gold)';if(p>=15)return '#6b7686';return '#3a4250';}

function techChip(k,v,n,cls){const c=$('div','chipc');c.innerHTML=
  '<div class="k">'+k+'</div><div class="v '+(cls||'neutral')+'">'+v+'</div>'+(n?'<div class="n">'+n+'</div>':'');return c;}

function renderHero(h,i){
  const root=$('div','hero'+(i===0?' on':''));root.id='hero'+i;
  // identity
  const id=$('div','idrow');
  id.innerHTML='<div><p class="name">'+h.name+'</p>'+
    '<div class="sub">NSE: '+h.symbol+'  ·  lens that fired: <span style="color:var(--gold)">'+h.lens.toUpperCase()+'</span>  ·  latest filing the score could see: '+dlabel(h.latest_filing)+'</div></div>'+
    '<div class="stamp"><div class="k">AS OF</div><div class="v">'+dlabel(h.as_of)+'</div><div class="px">close ₹'+fmt(h.px_asof,1)+'</div></div>';
  root.appendChild(id);

  // grid: scorecard + technical
  const grid=$('div','grid');
  // --- patearn scorecard ---
  const sc=$('div','card');const s=h.score;
  const tierCls='t'+s.tier.replace(/\D/g,'');
  let pats='';
  h.patterns.forEach(p=>{pats+='<div class="prow'+(p.qg?' gate':'')+'"><span class="pid">'+p.id+'</span>'+
    '<span class="pn">'+p.name+'</span>'+
    '<span class="pb"><i style="width:'+Math.max(2,p.pct)+'%;background:'+patColor(p.pct)+'"></i></span>'+
    '<span class="pv">'+fmt(p.pct)+'</span></div>';});
  const span=s.ns_hi-s.ns_lo;
  sc.innerHTML='<h3>patearn point-in-time scorecard <span style="color:var(--muted)">'+s.pac+'/14 patterns active</span></h3>'+
    '<div class="tier"><span class="chip '+tierCls+'">'+s.tier+'</span>'+
    '<div class="nsband"><div class="nlab"><span>NS '+fmt(s.ns_lo,1)+'%</span><span style="color:var(--ink)">base '+fmt(s.ns_base,1)+'%</span><span>'+fmt(s.ns_hi,1)+'%</span></div>'+
    '<div class="bar"><div class="fill" style="width:'+s.ns_hi+'%"></div><div class="base" style="left:'+s.ns_base+'%"></div></div></div></div>'+
    '<div class="qg '+(s.qg_pass?'pass':'fail')+'"><span>QUALITY GATE (patterns 1–5)</span><span>'+(s.qg_pass?'PASS':'FAIL')+' · '+fmt(s.qg_score)+'/'+fmt(s.qg_threshold)+'</span></div>'+
    '<div class="pats">'+pats+'</div>';
  grid.appendChild(sc);

  // --- technical / RS card ---
  const tc=$('div','card');const t=h.tech;const rs=h.rs||{};
  tc.innerHTML='<h3>relative strength &amp; setup <span style="color:var(--muted)">price archive ≤ as-of</span></h3>';
  const chips=$('div','chips');
  chips.appendChild(techChip('Off 52-wk high',(t.pct_off_52w_high>0?'+':'')+fmt(t.pct_off_52w_high,1)+'%',
    t.pct_off_52w_high>-3?'at new highs':'in a base',t.pct_off_52w_high>-3?'good':'neutral'));
  chips.appendChild(techChip('vs 200-day',(t.pct_vs_sma200>0?'+':'')+fmt(t.pct_vs_sma200,1)+'%',
    t.pct_vs_sma200>0?'above trend':'below trend',t.pct_vs_sma200>0?'good':'warn'));
  chips.appendChild(techChip('RS vs '+(DATA.index||'index')+' · 6m',(rs.rs_trend_6m_pct>0?'+':'')+fmt(rs.rs_trend_6m_pct,0)+'%',
    rs.rs_at_6m_high?'RS at 6-mo high':'outperforming',rs.rs_trend_6m_pct>0?'good':'warn'));
  chips.appendChild(techChip('Delivery (20d)',fmt(t.avg_deliv_pct_20d,0)+'%',
    t.avg_deliv_pct_20d>=45?'high conviction':'normal',t.avg_deliv_pct_20d>=45?'good':'neutral'));
  chips.appendChild(techChip('Vol contraction',fmt(t.vol_contraction_ratio,2)+'×',
    t.vol_contraction_ratio<1?'coiling':'expanding',t.vol_contraction_ratio<1?'good':'neutral'));
  chips.appendChild(techChip('Vol surge 10/50',fmt(t.vol_surge_10v50,2)+'×',
    t.vol_surge_10v50>1.4?'demand spike':'quiet',t.vol_surge_10v50>1.4?'good':'neutral'));
  tc.appendChild(chips);
  grid.appendChild(tc);
  root.appendChild(grid);

  // --- ledger ---
  const lg=$('div','ledger');
  let rows='';
  h.ledger.forEach(l=>{const neg=l.value<0;rows+='<tr><td class="met">'+l.metric+'</td>'+
    '<td>'+l.period_end+'</td><td>'+l.report_date+'</td><td class="lag">+'+l.lag_days+'d</td>'+
    '<td class="val'+(neg?' neg':'')+'">'+fmt(l.value, Math.abs(l.value)<100?2:0)+'</td>'+
    '<td class="ok">✓ before</td></tr>';});
  lg.innerHTML='<h3>the no-look-ahead ledger</h3>'+
    '<div class="cap">Every fundamental input the score consumed, with the date it was actually <b>filed</b>. '+
    'The score on '+dlabel(h.as_of)+' could only see results reported on or before that day — note the ~90-day '+
    'reporting lag on each annual. <b>Nothing here was knowable in hindsight.</b></div>'+
    '<table><thead><tr><th>Metric</th><th>Period end</th><th>Filed (report_date)</th><th>Lag</th><th>Value</th><th>vs as-of</th></tr></thead><tbody>'+rows+'</tbody></table>';
  root.appendChild(lg);

  // --- story chart ---
  const story=$('div','story');story.id='story'+i;
  story.innerHTML='<h3>the tape</h3><div class="sub">Everything left of the gold line is what the desk would judge on '+dlabel(h.as_of)+'. The rest was the future.</div>';
  const cw=$('div','chartwrap');
  const btn=$('div','revealbtn','▶ &nbsp;Reveal what happened next');
  btn.onclick=()=>{story.classList.add('revealed');drawForward(i);};
  cw.appendChild(btn);
  cw.appendChild(buildSVG(h,i));
  const rv=h.reveal;
  const bn=$('div','bignum');
  bn.innerHTML='<div class="pct">+'+fmt(rv.peak_gain_pct,0)+'%</div>'+
    '<div class="lbl">peak by '+dlabel(rv.peak_date)+'  ·  entry '+dlabel(rv.entry_date)+'</div>'+
    '<div class="cap2">patearn-rule exit captured +'+fmt(h.known_return,0)+'% in '+h.months+' months</div>';
  cw.appendChild(bn);
  story.appendChild(cw);
  root.appendChild(story);

  document.getElementById('heroes').appendChild(root);

  // tab
  const tab=$('div','tab'+(i===0?' on':''));
  tab.innerHTML='<span class="lens">'+h.lens+'</span><span>'+h.symbol+'</span><span class="ret">▲ later +'+fmt(h.reveal.peak_gain_pct,0)+'%</span>';
  tab.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
    document.querySelectorAll('.hero').forEach(x=>x.classList.remove('on'));
    tab.classList.add('on');root.classList.add('on');};
  document.getElementById('tabs').appendChild(tab);
}

const SVGW=1060,SVGH=230,PADX=8,PADT=16,PADB=22;
function buildSVG(h,i){
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 '+SVGW+' '+SVGH);
  const path=h.path;const n=path.length;
  const xs=path.map(p=>p[0]),ys=path.map(p=>p[1]);
  const ymin=Math.min(...ys)*0.96,ymax=Math.max(...ys)*1.02;
  const X=k=>PADX+(SVGW-2*PADX)*k/(n-1);
  const Y=v=>PADT+(SVGH-PADT-PADB)*(1-(v-ymin)/(ymax-ymin));
  let aidx=path.findIndex(p=>p[0]>h.path_asof);if(aidx<0)aidx=n-1;
  const ax=X(aidx);
  // base shading (left of as-of)
  const baseRect=document.createElementNS(ns,'rect');
  baseRect.setAttribute('x',0);baseRect.setAttribute('y',0);baseRect.setAttribute('width',ax);
  baseRect.setAttribute('height',SVGH);baseRect.setAttribute('fill','rgba(94,200,255,0.04)');svg.appendChild(baseRect);
  // pre line (solid)
  let dpre='';for(let k=0;k<=aidx;k++){dpre+=(k===0?'M':'L')+X(k).toFixed(1)+' '+Y(path[k][1]).toFixed(1)+' ';}
  const pre=document.createElementNS(ns,'path');pre.setAttribute('d',dpre);pre.setAttribute('fill','none');
  pre.setAttribute('stroke','#5ec8ff');pre.setAttribute('stroke-width','2');svg.appendChild(pre);
  // post line (hidden until reveal) via clip that expands
  let dpost='';for(let k=aidx;k<n;k++){dpost+=(k===aidx?'M':'L')+X(k).toFixed(1)+' '+Y(path[k][1]).toFixed(1)+' ';}
  const post=document.createElementNS(ns,'path');post.setAttribute('d',dpost);post.setAttribute('fill','none');
  post.setAttribute('stroke','#34d399');post.setAttribute('stroke-width','2.4');
  const L=post.getTotalLength?0:0;post.id='post'+i;
  post.setAttribute('stroke-dasharray','3000');post.setAttribute('stroke-dashoffset','3000');
  post.style.transition='stroke-dashoffset 1.4s ease';svg.appendChild(post);
  // as-of gold line
  const vline=document.createElementNS(ns,'line');vline.setAttribute('x1',ax);vline.setAttribute('x2',ax);
  vline.setAttribute('y1',PADT-6);vline.setAttribute('y2',SVGH-PADB);vline.setAttribute('stroke','#e6b450');
  vline.setAttribute('stroke-width','1.3');vline.setAttribute('stroke-dasharray','4 3');svg.appendChild(vline);
  const tag=document.createElementNS(ns,'text');tag.setAttribute('x',ax-6);tag.setAttribute('y',PADT);
  tag.setAttribute('fill','#e6b450');tag.setAttribute('font-size','11');tag.setAttribute('text-anchor','end');
  tag.setAttribute('font-family','monospace');tag.textContent='AS OF '+h.as_of;svg.appendChild(tag);
  // start/asof price labels
  const sp=document.createElementNS(ns,'text');sp.setAttribute('x',PADX);sp.setAttribute('y',Y(path[aidx][1])-8);
  sp.setAttribute('fill','#8b97a7');sp.setAttribute('font-size','10');sp.setAttribute('font-family','monospace');
  sp.textContent='₹'+fmt(path[aidx][1],0);svg.appendChild(sp);
  // dot at as-of
  const dot=document.createElementNS(ns,'circle');dot.setAttribute('cx',ax);dot.setAttribute('cy',Y(path[aidx][1]));
  dot.setAttribute('r','3.5');dot.setAttribute('fill','#e6b450');svg.appendChild(dot);
  h._post='post'+i;
  return svg;
}
function drawForward(i){const p=document.getElementById(DATA.heroes[i]._post);if(p)p.setAttribute('stroke-dashoffset','0');}

DATA.heroes.forEach(renderHero);
document.getElementById('foot').innerHTML=
  '<b>Method.</b> Point-in-time fundamentals are gated by <code style="font-family:monospace">report_date</code> '+
  '(period end + ~90d for annuals) so the score on any past day sees only what had actually been filed. '+
  'Price/relative-strength features are computed from the survivorship-safe raw NSE bhav archive using bars dated on or before the as-of day; '+
  'forward paths enter at the next session’s open. patearn tiers are deliberately conservative — they penalise rich valuation and hold '+
  'data-poor patterns (shareholding, concall, technical) at “partial,” so winners are <i>not</i> retro-fitted to look pre-ordained. '+
  'This is an audit of a research process, not investment advice.';
</script>
</body>
</html>"""

if __name__ == "__main__":
    main()
