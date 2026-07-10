"""/dash/buyback-calc — the E-10 buyback tender-quota calculator (personal-scale tool).

WHY THIS EXISTS (charter §2.4): tender-offer buybacks reserve 15% of the offer for the
SMALL-SHAREHOLDER category (holdings ≤ ₹2,00,000 by market value on the record date —
SEBI Buyback Regulations). That reservation gives small holders a structurally higher
acceptance ratio than the general category — an anomaly that persists BECAUSE it is
capped at ₹2L per person: institutions cannot touch it. Personal-scale arithmetic,
never a fund pitch.

WHAT IT IS: a client-side calculator (vanilla JS, zero deps) over the tender math —
  accepted   = shares × A                (A = acceptance ratio, YOUR assumption)
  tender P&L = accepted × (buyback − cost)
  residual   = (shares − accepted) × (exit − cost)
  breakeven exit (net = 0, A<1): exit = cost − A·(buyback − cost)/(1 − A)
— plus the recent/upcoming BUYBACK rows from the corporate_actions feed to anchor it.

HONESTY FENCES (also stated on-page):
  * The acceptance ratio is an ASSUMPTION YOU set. Historical accepted-vs-tendered
    ratios are company-published post-offer and are NOT in our data — we refuse to
    fabricate a prior; the sensitivity row exists instead.
  * Eligibility is holdings ≤ ₹2L by value ON THE RECORD DATE — size with a buffer;
    a price rally into record date can push you over the category line.
  * Arithmetic, not advice; annualization is simple (× 365/days), stated as such.

House pattern: isolated pure-stdlib APIRouter (like results_reactions), mounted via
one v2_surfaces._ROUTER_SPECS line + a Markets Lens beside the corp-actions calendar.
"""
from __future__ import annotations

import html
import re
import sqlite3

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

HERMES_DB = "/opt/hermes/data/hermes.db"
router = APIRouter()


def _shell_fallback(title, body, active="", latest_date="", wide=False):
    return ("<!doctype html><meta charset='utf-8'><title>" + title + "</title>"
            "<body style='background:var(--bg-1);color:var(--ink);font-family:system-ui;"
            "max-width:1100px;margin:0 auto;padding:24px'>" + body + "</body>")


try:
    from src.web.dashboard import _shell
except Exception:                                   # pragma: no cover
    _shell = _shell_fallback


def _esc(s):
    return html.escape(str(s), quote=True)


_PRICE = re.compile(r"R[se]\.?\s*([0-9][0-9,]*(?:\.[0-9]+)?)", re.I)


def parse_bb_price(details: str) -> float | None:
    """Best-effort ₹ price from the details text ('Buyback ... Rs 1650 Per Share...')."""
    m = _PRICE.search(details or "")
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", ""))
        return v if 1 <= v <= 200000 else None
    except ValueError:
        return None


def recent_buybacks(limit: int = 30) -> list[dict]:
    try:
        con = sqlite3.connect(f"file:{HERMES_DB}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error:
        return []
    try:
        rows = con.execute(
            "SELECT symbol, ex_date, record_date, details FROM corporate_actions "
            "WHERE action_type='BUYBACK' ORDER BY COALESCE(ex_date, record_date) DESC "
            "LIMIT ?", (limit,)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    return [{"sym": r[0], "ex": str(r[1] or "")[:10], "rec": str(r[2] or "")[:10],
             "details": r[3] or "", "px": parse_bb_price(r[3])} for r in rows]


_CSS = """
<style>
.bb{max-width:1060px}
.bb .lead{color:var(--ink-2);font-size:13px;line-height:1.65;max-width:880px;margin:2px 0 14px}
.bb .fence{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;
           padding:10px 14px;margin:0 0 16px;font-size:12.5px;line-height:1.6}
.bb .fence b{color:#b18cff}
.bb .calc{border:1px solid var(--line-2);border-radius:12px;background:var(--bg-1);
          padding:14px 18px;margin:0 0 16px}
.bb .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px 16px}
.bb label{display:block;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
          color:var(--ink-3);margin:0 0 3px}
.bb input{width:100%;background:var(--bg-2);border:1px solid var(--line-2);border-radius:8px;
          color:var(--ink);padding:7px 10px;font-size:14px;font-variant-numeric:tabular-nums}
.bb .out{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-top:14px}
.bb .kpi{border:1px solid var(--line-2);border-radius:10px;padding:8px 12px;background:var(--bg-2)}
.bb .kpi .n{font-size:19px;font-weight:800;font-variant-numeric:tabular-nums}
.bb .kpi .l{font-size:10px;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-2)}
.bb table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:12px}
.bb th,.bb td{padding:5px 9px;border-bottom:1px solid var(--bg-3);text-align:right;white-space:nowrap}
.bb th:first-child,.bb td:first-child{text-align:left}
.bb thead th{color:var(--ink-2);font-weight:600;font-size:10px;letter-spacing:.05em;
             text-transform:uppercase}
.bb .pos{color:#3fd486}.bb .neg{color:#ff6a7a}
.bb .note{color:var(--ink-2);font-size:11px;margin-top:14px;border-top:1px solid var(--line-2);
          padding-top:10px;line-height:1.6;max-width:880px}
.bb .dt{font-size:12px;color:var(--ink-3)}
</style>"""

_JS = """
<script>
function bbfmt(x, dp){ if(!isFinite(x)) return '—';
  return x.toLocaleString('en-IN', {minimumFractionDigits: dp===undefined?0:dp,
                                    maximumFractionDigits: dp===undefined?0:dp}); }
function bbcalc(){
  var bb = parseFloat(document.getElementById('bb_px').value);
  var cmp = parseFloat(document.getElementById('bb_cmp').value);
  var inv = parseFloat(document.getElementById('bb_inv').value);
  var A = parseFloat(document.getElementById('bb_acc').value)/100.0;
  var ex = parseFloat(document.getElementById('bb_exit').value);
  var days = parseFloat(document.getElementById('bb_days').value)||75;
  var out = document.getElementById('bb_out'), sens = document.getElementById('bb_sens');
  if(!(bb>0&&cmp>0&&inv>0&&A>0&&A<=1)){ out.innerHTML=''; sens.innerHTML=''; return; }
  if(isNaN(ex)) ex = cmp;
  var capw = document.getElementById('bb_capwarn');
  capw.style.display = inv>200000 ? '' : 'none';
  function legs(a){
    var sh = Math.floor(inv/cmp), acc = Math.floor(sh*a), ret = sh-acc;
    var t = acc*(bb-cmp), r = ret*(ex-cmp), net = t+r, base = sh*cmp;
    return {sh:sh, acc:acc, ret:ret, t:t, r:r, net:net,
            pct: base>0 ? 100*net/base : 0/0,
            ann: base>0 ? (100*net/base)*(365/days) : 0/0};
  }
  var m = legs(A);
  var be = A<1 ? cmp - A*(bb-cmp)/(1-A) : 0/0;
  function kpi(n,l,cls){ return '<div class="kpi"><div class="n '+(cls||'')+'">'+n+
                                '</div><div class="l">'+l+'</div></div>'; }
  out.innerHTML =
    kpi(bbfmt(m.sh), 'shares bought @ CMP') +
    kpi(bbfmt(m.acc)+' / '+bbfmt(m.ret), 'accepted / returned') +
    kpi('₹'+bbfmt(m.t), 'tender leg P&L', m.t>=0?'pos':'neg') +
    kpi('₹'+bbfmt(m.r), 'residual leg P&L', m.r>=0?'pos':'neg') +
    kpi('₹'+bbfmt(m.net)+' ('+bbfmt(m.pct,1)+'%)', 'net', m.net>=0?'pos':'neg') +
    kpi(bbfmt(m.ann,1)+'%', 'annualized (simple, '+days+'d)', m.ann>=0?'pos':'neg') +
    kpi(isFinite(be)?('₹'+bbfmt(be,2)):'n/a (A=100%)', 'breakeven exit price');
  var rows='';
  [0.20,0.33,0.50,0.66,1.00].forEach(function(a){
    var s=legs(a);
    rows += '<tr><td>'+Math.round(a*100)+'%</td><td>'+bbfmt(s.acc)+'</td>'+
      '<td class="'+(s.net>=0?'pos':'neg')+'">₹'+bbfmt(s.net)+'</td>'+
      '<td class="'+(s.pct>=0?'pos':'neg')+'">'+bbfmt(s.pct,1)+'%</td>'+
      '<td class="'+(s.ann>=0?'pos':'neg')+'">'+bbfmt(s.ann,1)+'%</td></tr>';
  });
  sens.innerHTML = '<table><thead><tr><th>acceptance</th><th>accepted</th><th>net ₹</th>'+
    '<th>net %</th><th>annualized</th></tr></thead><tbody>'+rows+'</tbody></table>';
}
function bbfill(px){ if(px>0){ document.getElementById('bb_px').value = px; bbcalc(); } }
document.addEventListener('DOMContentLoaded', function(){
  ['bb_px','bb_cmp','bb_inv','bb_acc','bb_exit','bb_days'].forEach(function(id){
    document.getElementById(id).addEventListener('input', bbcalc); });
  bbcalc();
});
</script>"""


@router.get("/dash/buyback-calc", response_class=HTMLResponse)
def buyback_calc():
    bbs = recent_buybacks()
    tr = []
    for b in bbs:
        px = f'<a href="#" onclick="bbfill({b["px"]});return false" class="pos">₹{b["px"]:,.0f}</a>' \
            if b["px"] else '—'
        tr.append(f'<tr><td><a class="row" href="/dash/stock?sym={_esc(b["sym"])}" '
                  f'style="color:var(--ink);text-decoration:none"><b>{_esc(b["sym"])}</b></a></td>'
                  f'<td class="dt">{_esc(b["ex"] or "—")}</td><td class="dt">{_esc(b["rec"] or "—")}</td>'
                  f'<td>{px}</td>'
                  f'<td style="text-align:left;color:var(--ink-2);white-space:normal">'
                  f'{_esc(b["details"][:110])}</td></tr>')
    body = [_CSS, '<div class="bb">',
            '<h2>Buyback tender-quota calculator</h2>',
            '<div class="lead">Tender-offer buybacks reserve <b>15% for the small-shareholder '
            'category</b> (holdings ≤ ₹2,00,000 by market value on the record date — SEBI Buyback '
            'Regulations). That cap is the moat: the acceptance ratio in the small category is '
            'structurally higher precisely because no large pocket can crowd in. This page is the '
            'arithmetic of that trade — nothing more.</div>',
            '<div class="fence">⚖️ <b>What this is not:</b> the acceptance ratio below is '
            '<b>your assumption</b> — realized ratios are company-published after each offer and '
            'are not in our data, so we refuse to fabricate a prior (the sensitivity table exists '
            'instead). Eligibility is measured <b>on the record date</b> — a rally can push a '
            '₹2L position over the category line, so size with a buffer. Simple annualization, '
            'stated as such. Arithmetic, not advice.</div>',
            '<div class="calc"><div class="grid">',
            '<div><label>Buyback price ₹</label><input id="bb_px" type="number" value="1000"></div>',
            '<div><label>Current price (your cost) ₹</label><input id="bb_cmp" type="number" value="850"></div>',
            '<div><label>Investment ₹ (small-shareholder cap 2,00,000)</label>'
            '<input id="bb_inv" type="number" value="195000"></div>',
            '<div><label>Assumed acceptance ratio %</label><input id="bb_acc" type="number" '
            'value="33" min="1" max="100"></div>',
            '<div><label>Post-tender exit price ₹ (default = cost)</label>'
            '<input id="bb_exit" type="number" placeholder="= current"></div>',
            '<div><label>Days locked (record→payout)</label><input id="bb_days" type="number" value="75"></div>',
            '</div>',
            '<div id="bb_capwarn" class="fence" style="display:none;border-color:#f6b73c;margin-top:10px">'
            '⚠ Above ₹2,00,000 you are OUT of the small-shareholder category — the general-category '
            'acceptance ratio is typically far lower.</div>',
            '<div class="out" id="bb_out"></div>',
            '<div id="bb_sens"></div></div>',
            '<h3 style="margin:18px 0 6px">Buybacks on the corporate-actions tape</h3>',
            '<div class="lead" style="margin-bottom:8px">From the nightly primary-source feed '
            f'({len(bbs)} most recent; the archive holds 344 back to 2012). Click a parsed price '
            'to load it into the calculator; details text is shown raw — parse quality varies.</div>',
            '<table><thead><tr><th>Symbol</th><th>Ex-date</th><th>Record</th><th>Px (parsed)</th>'
            '<th style="text-align:left">Details</th></tr></thead><tbody>',
            "".join(tr) or '<tr><td colspan="5" style="color:var(--ink-2)">no buyback rows '
                           '(corporate_actions absent on this checkout)</td></tr>',
            '</tbody></table>',
            '<div class="note">Mechanism: SEBI Buyback Regulations reserve 15% of a tender offer '
            'for small shareholders; entitlement is pro-rata within the category and companies '
            'publish the final acceptance ratio with the offer results. The residual leg (unaccepted '
            'shares) carries the market risk — the breakeven exit price above is the honest way to '
            'see it. Personal-scale by construction (charter §2.4): this is a capacity-moat anomaly, '
            'not a fund strategy. E-10; a drift/event STUDY on buyback announcements would need its '
            'own pre-registration.</div>',
            '</div>', _JS]
    return HTMLResponse(_shell("Buyback calculator", "".join(body),
                               active="buyback-calc", wide=True))
