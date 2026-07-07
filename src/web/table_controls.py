"""Consistent table controls — `?` glossary popovers + column add/remove on strategy tables.

Ramana's ask (S72 carry-forward): strategy tables should match Screen+ — every
column header explained (`?` hover-popover sourced from docs/metrics-glossary.md)
and columns addable/removable, persisted like Screen+'s s2_hidden_v1 toggles
(localStorage, per page). /dash/stocks (Positioning) first; extend a page by
adding its `active` lens key to _PAGES.

Isolated module (parallel-sessions doctrine — no dashboard/cockpit edit):
v2_surfaces.wire() calls install(), which wraps dashboard._shell (the same seam
shell_skin uses) and enhances only registered pages. Defensive (any failure
renders the page unchanged) + idempotent (sentinels on wrapper and body).
"""
from __future__ import annotations

import re

from src.web import glossary as G

# pages to enhance: `active` lens key -> localStorage namespace
# (stealth is the same shared table rendered under its own lens key — S83c)
_PAGES = {"stocks": "tc_stocks", "stealth": "tc_stealth"}

# header text -> glossary term, where the visible label is too terse to resolve.
# Everything else resolves via G.gloss(header_text) or degrades to a plain label
# (e.g. Symbol/Close/Near-P today). Keys are lowercased header text.
_HDR_KEYS = {
    "r/p": "p_score",
    "×pow": "×Power",
    "δhot": "price_vs_hot_avg_pct",   # header shows Δhot; Δ str.lower()s to δ
    "peak rank": "Rank",
    "days fired": "p_score",
    "avg dvpt ₹": "DVPT",
    # extra (default-hidden) Positioning columns — terse labels -> glossary terms
    "rs#": "rs_rank",
    "rs·brd": "rs_vs_broad_today",
    "rs·sec": "rs_vs_sector_today",
    "52w-hi": "pct_from_52w_high",
    "drift3m": "accum_price_drift_3m",
    "up/dn3m": "deliv_updown_ratio_3m",
    "dvpt ₹": "DVPT",
    "pow3m cr": "power_dvpt_3m",
    "churn": "trade_count_ratio_1m_6m",
    "ticket": "ticket_ratio_1m_6m",
    "key3m": "key_price_p3m",
    "gap3m": "gap_to_key_p3m",
    "key6m": "key_price_p6m",
    "gap6m": "gap_to_key_p6m",
}

_SENTINEL = "tc-colbar"
_MIN_COLS = 5                      # leave small summary tables alone
_TABLE_RE = re.compile(r"<table\b[^>]*>")
_THEAD_RE = re.compile(r"<thead\b.*?</thead>", re.S)
_TH_RE = re.compile(r"<th\b([^>]*)>(.*?)</th>", re.S)


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]*>", "", s).strip()


def _gloss_th(m: re.Match) -> str:
    """Wrap a plain-text <th> label in a `?` popover; leave rich/empty ones alone."""
    attrs, inner = m.group(1), m.group(2).strip()
    if not inner or "<" in inner:
        return m.group(0)
    term = _HDR_KEYS.get(inner.lower(), inner)
    return f"<th{attrs}>{G.gloss(term, inner)}</th>"


def _picker(tidx: int, labels: list[str]) -> str:
    boxes = "".join(
        f'<label><input type="checkbox" data-c="{i}" checked> {lbl or f"col {i + 1}"}</label>'
        for i, lbl in enumerate(labels))
    return (f'<div class="{_SENTINEL}" data-tc-for="{tidx}"><details>'
            f'<summary>&#9881; Columns</summary><div class="tc-menu">{boxes}'
            f'<a href="#" class="tc-reset">reset</a></div></details></div>')


def _enhance(body: str, ns: str) -> str:
    """Popovers on qualifying tables' headers + a per-table column picker.
    Pure text -> text; returns the body unchanged on no match (or if already done)."""
    if _SENTINEL in body:
        return body
    out: list[str] = []
    pos, tidx = 0, 0
    for tm in _TABLE_RE.finditer(body):
        if tm.start() < pos:                      # nested/overlapping — skip
            continue
        end = body.find("</table>", tm.end())
        if end < 0:
            continue
        seg = body[tm.start():end]
        hm = _THEAD_RE.search(seg)
        if not hm:
            continue
        ths = _TH_RE.findall(hm.group(0))
        if len(ths) < _MIN_COLS:
            continue
        # columns the PAGE marks `<th data-tcoff>` start hidden on first visit
        # (until the user toggles them) — keeps a wide table's default view clean.
        off = [str(i) for i, (attrs, _in) in enumerate(ths) if "data-tcoff" in attrs]
        off_attr = f' data-tc-off="[{",".join(off)}]"' if off else ""
        new_head = _TH_RE.sub(_gloss_th, hm.group(0))
        new_seg = seg[:hm.start()] + new_head + seg[hm.end():]
        tag = tm.group(0)[:-1] + f' data-tc="{tidx}"{off_attr}>'   # tag table for the JS
        new_seg = tag + new_seg[len(tm.group(0)):]
        labels = [_strip_tags(t[1]) for t in ths]
        out.append(body[pos:tm.start()])
        out.append(_picker(tidx, labels))
        out.append(new_seg)
        pos = end
        tidx += 1
    if not tidx:
        return body
    out.append(body[pos:])
    return "".join(out) + G.css() + _CSS + _JS.replace("__NS__", ns)


_CSS = """<style>
.tc-colbar{display:flex;justify-content:flex-end;margin:2px 0;}
.tc-colbar details{position:relative;}
.tc-colbar summary{cursor:pointer;font-size:11px;color:var(--ink-3);list-style:none;
  border:1px solid var(--line-2);border-radius:6px;padding:2px 8px;user-select:none;}
.tc-colbar summary::-webkit-details-marker{display:none;}
.tc-menu{position:absolute;right:0;top:120%;z-index:70;background:var(--bg-2);
  border:1px solid var(--line-2);border-radius:8px;padding:8px 10px;min-width:170px;
  box-shadow:0 6px 22px rgba(0,0,0,.55);display:flex;flex-direction:column;gap:3px;}
.tc-menu label{font-size:12px;color:var(--ink);display:flex;gap:6px;align-items:center;
  cursor:pointer;white-space:nowrap;}
.tc-menu .tc-reset{font-size:11px;color:#58a6ff;margin-top:5px;}
</style>"""

# plain string (no f-string) so the JS braces stay literal.
_JS = """<script>(function(){
var NS='__NS__';
function K(i){return NS+'_'+i}
document.querySelectorAll('table[data-tc]').forEach(function(t){
  var i=t.getAttribute('data-tc'), hidden=[];
  var raw=localStorage.getItem(K(i));
  if(raw===null){try{hidden=JSON.parse(t.getAttribute('data-tc-off')||'[]')}catch(e){hidden=[]}}
  else{try{hidden=JSON.parse(raw)}catch(e){hidden=[]}}
  var bar=document.querySelector('.tc-colbar[data-tc-for="'+i+'"]');
  if(!bar)return;
  function apply(){
    var h={};hidden.forEach(function(x){h[x]=1});
    t.querySelectorAll('tr').forEach(function(r){
      for(var c=0;c<r.children.length;c++)r.children[c].style.display=h[c]?'none':'';
    });
    bar.querySelectorAll('input[data-c]').forEach(function(cb){
      cb.checked=!h[+cb.getAttribute('data-c')]});
  }
  bar.querySelectorAll('input[data-c]').forEach(function(cb){
    cb.addEventListener('change',function(){
      var c=+cb.getAttribute('data-c');
      hidden=hidden.filter(function(x){return x!==c});
      if(!cb.checked)hidden.push(c);
      try{localStorage.setItem(K(i),JSON.stringify(hidden))}catch(e){}
      apply();
    });
  });
  var rs=bar.querySelector('.tc-reset');
  if(rs)rs.addEventListener('click',function(ev){
    ev.preventDefault();hidden=[];
    try{localStorage.removeItem(K(i))}catch(e){}
    apply()});
  apply();
});
})();</script>"""


def install() -> bool:
    """Wrap dashboard._shell so registered pages get table controls. Idempotent;
    signature-transparent (inspects args, passes them through verbatim)."""
    from src.web import dashboard as _dash
    cur = _dash._shell
    if getattr(cur, "_tc_installed", False):
        return False

    def _shell_tc(*a, **k):
        try:
            act = k["active"] if "active" in k else (a[2] if len(a) > 2 else "")
            ns = _PAGES.get(act)
            if ns:
                if "body" in k and isinstance(k["body"], str):
                    k = dict(k)
                    k["body"] = _enhance(k["body"], ns)
                elif len(a) > 1 and isinstance(a[1], str):
                    a = a[:1] + (_enhance(a[1], ns),) + a[2:]
        except Exception:
            pass                                   # additive: never break a page
        return cur(*a, **k)

    _shell_tc._tc_installed = True
    _dash._shell = _shell_tc
    return True


def _selftest() -> int:
    sample = ('<h2>Positioning</h2><table id="stbl" class="dt"><thead><tr>'
              '<th class="l">Symbol</th><th>Rank</th><th>r/p</th><th>×pow</th>'
              '<th>Close</th><th>Δhot</th><th>Character</th>'
              '<th>Deliv ₹Cr</th><th>Near-P</th></tr></thead>'
              '<tbody><tr><td>RELIANCE</td><td>SS</td><td>5/5</td><td>1.6</td>'
              '<td>2901</td><td>+2%</td><td>ACCUM</td><td>412</td><td>-</td></tr>'
              '</tbody></table>')
    out = _enhance(sample, "tc_stocks")
    assert _SENTINEL in out and 'data-tc="0"' in out, "picker/table tag missing"
    pops = out.count("gl-pop")
    assert pops >= 6, f"expected >=6 header popovers, got {pops}"
    assert "price_vs_hot_avg_pct" in out, "Δhot header must resolve (Δ lowercases to δ)"
    assert '<th class="l">Symbol</th>' in out, "unmapped header must stay plain"
    assert _enhance(out, "tc_stocks") == out, "must be idempotent"
    small = "<table><thead><tr><th>A</th><th>B</th></tr></thead></table>"
    assert _enhance(small, "x") == small, "small tables must be untouched"
    assert "NS='tc_stocks'" in out and "localStorage" in out, "persistence JS missing"
    dh = _enhance('<table><thead><tr><th>A</th><th>B</th><th>C</th><th>D</th>'
                  '<th data-tcoff>E</th></tr></thead><tbody></tbody></table>', "z")
    assert 'data-tc-off="[4]"' in dh, "default-off column must seed data-tc-off on the table"
    print(f"table_controls selftest OK — {pops} popovers; picker + persisted "
          "column toggles injected once; idempotent")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
