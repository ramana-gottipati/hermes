"""Pat — the dashboard tab body (server-rendered, theme-matched to dashboard.py).

``render_pat(flow, explain, q)`` returns the INNER HTML for ``/dash/pat``; the
route in ``dashboard.py`` wraps it in the shared ``_shell``. This module is
self-contained — it imports only the glossary, never dashboard.py (one-way
dependency), and the avatar SVGs use explicit hex (no Tabler / CSS-var deps) so
they render on the dark dashboard chrome.

Phase-1 scope (DB-free): the persona + 6-avatar picker, and the fully working
"Explain a metric" flow driven by the glossary. The three data-backed flows
(accumulation / RS / fundamentals) are present but announce themselves as next —
they need the SQL templates, which land with the engine.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from src.pat.glossary import GLOSSARY, FAMILIES, get, find, family
from src.pat.flows import (
    ACC_STRENGTH, ACC_ENTRY, RS_STRENGTH, RS_ALIGN,
    build_accumulation_query, build_accumulation_sectors_query,
    build_rs_query, build_rs_sectors_query,
)


def _esc(s) -> str:
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- avatars ---------------------------------------------------------------
# Flat, self-contained SVGs (viewBox only; sized by CSS). Indianised market
# archetypes — see the design conversation. data-av slug is the persistence key.

_AV_SETH = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Seth Pat">'
    '<circle cx="50" cy="50" r="48" fill="#E0911E"/>'
    '<rect x="29" y="35" width="42" height="44" rx="13" fill="#fff"/>'
    '<path d="M27 37 Q50 22 73 37 Q50 31 27 37 Z" fill="#fff"/>'
    '<circle cx="41" cy="52" r="7.6" fill="#fff" stroke="#20242B" stroke-width="2.6"/>'
    '<circle cx="59" cy="52" r="7.6" fill="#fff" stroke="#20242B" stroke-width="2.6"/>'
    '<line x1="48.6" y1="52" x2="51.4" y2="52" stroke="#20242B" stroke-width="2.6"/>'
    '<circle cx="41" cy="52" r="2.2" fill="#20242B"/><circle cx="59" cy="52" r="2.2" fill="#20242B"/>'
    '<path d="M33 65 C36 61 41 62 44 65 C47 67 53 67 56 65 C59 62 64 61 67 65 '
    'C63 66 59 65 56 67 C52 69 48 69 44 67 C41 65 37 66 33 65 Z" fill="#20242B"/>'
    '</svg>'
)
_AV_RAO = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Rao Pat">'
    '<circle cx="50" cy="50" r="48" fill="#D85A30"/>'
    '<rect x="29" y="36" width="42" height="43" rx="13" fill="#fff"/>'
    '<path d="M27 39 Q27 23 50 23 Q73 23 73 39 Q61 31 50 32 Q39 31 27 39 Z" fill="#20242B"/>'
    '<path d="M32 48 Q32 59 41 58 Q47 57 46 48 Q39 46 32 48 Z" fill="#20242B"/>'
    '<path d="M68 48 Q68 59 59 58 Q53 57 54 48 Q61 46 68 48 Z" fill="#20242B"/>'
    '<line x1="46" y1="49" x2="54" y2="49" stroke="#20242B" stroke-width="2.4"/>'
    '<circle cx="37" cy="51" r="1.6" fill="#fff"/><circle cx="63" cy="51" r="1.6" fill="#fff"/>'
    '<path d="M37 64 Q50 71 63 64 Q57 67 50 66 Q43 67 37 64 Z" fill="#20242B"/>'
    '</svg>'
)
_AV_SINGH = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Singh Pat">'
    '<circle cx="50" cy="50" r="48" fill="#2F7FD6"/>'
    '<rect x="30" y="38" width="40" height="41" rx="13" fill="#fff"/>'
    '<path d="M31 58 Q31 83 50 85 Q69 83 69 58 Q61 72 50 72 Q39 72 31 58 Z" fill="#20242B"/>'
    '<path d="M26 43 Q24 20 50 19 Q76 20 74 43 Q50 34 26 43 Z" fill="#EE9A22"/>'
    '<path d="M26 43 Q50 34 74 43" fill="none" stroke="#C77A12" stroke-width="1.5"/>'
    '<path d="M46 33 Q50 27 54 33 Q50 31 46 33 Z" fill="#EE9A22" stroke="#C77A12" stroke-width="0.8"/>'
    '<circle cx="42" cy="53" r="2.3" fill="#20242B"/><circle cx="58" cy="53" r="2.3" fill="#20242B"/>'
    '<path d="M40 61 Q50 65 60 61 Q54 63 50 62 Q46 63 40 61 Z" fill="#20242B"/>'
    '</svg>'
)
_AV_CHAI = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Chai Pat">'
    '<circle cx="50" cy="50" r="48" fill="#1AA079"/>'
    '<path d="M23 49 Q23 25 50 25 Q77 25 77 49" fill="none" stroke="#20242B" stroke-width="4.5"/>'
    '<rect x="19" y="46" width="9" height="15" rx="4" fill="#20242B"/>'
    '<rect x="72" y="46" width="9" height="15" rx="4" fill="#20242B"/>'
    '<rect x="30" y="34" width="40" height="43" rx="13" fill="#fff"/>'
    '<rect x="33" y="46" width="13" height="11" rx="3" fill="#fff" stroke="#20242B" stroke-width="2.4"/>'
    '<rect x="54" y="46" width="13" height="11" rx="3" fill="#fff" stroke="#20242B" stroke-width="2.4"/>'
    '<line x1="46" y1="51" x2="54" y2="51" stroke="#20242B" stroke-width="2.4"/>'
    '<circle cx="39.5" cy="51" r="2" fill="#20242B"/><circle cx="60.5" cy="51" r="2" fill="#20242B"/>'
    '<path d="M40 64 Q50 68 60 64" fill="none" stroke="#20242B" stroke-width="2" stroke-linecap="round"/>'
    '<path d="M59 71 L73 71 L71 80 Q66 82 61 80 Z" fill="#9C5B2A"/>'
    '<path d="M63 68 Q61 65 63 62 M69 68 Q71 65 69 62" fill="none" stroke="#fff" stroke-width="1.4"/>'
    '</svg>'
)
_AV_LAKSHMI = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Lakshmi Pat">'
    '<circle cx="50" cy="50" r="48" fill="#C84C84"/>'
    '<circle cx="50" cy="22" r="6" fill="#20242B"/>'
    '<path d="M27 46 Q25 22 50 21 Q75 22 73 46 Q68 31 50 31 Q32 31 27 46 Z" fill="#20242B"/>'
    '<rect x="31" y="33" width="38" height="44" rx="13" fill="#fff"/>'
    '<path d="M31 41 Q31 33 36 33 L36 61 Q31 54 31 41 Z" fill="#20242B"/>'
    '<path d="M69 41 Q69 33 64 33 L64 61 Q69 54 69 41 Z" fill="#20242B"/>'
    '<circle cx="50" cy="39" r="2.6" fill="#C0143C"/>'
    '<path d="M34 51 Q40 48 46 51 Q45 56 39 56 Q34 55 34 51 Z" fill="#fff" stroke="#20242B" stroke-width="2.2"/>'
    '<path d="M66 51 Q60 48 54 51 Q55 56 61 56 Q66 55 66 51 Z" fill="#fff" stroke="#20242B" stroke-width="2.2"/>'
    '<line x1="46" y1="51.5" x2="54" y2="51.5" stroke="#20242B" stroke-width="2.2"/>'
    '<circle cx="40" cy="52" r="1.8" fill="#20242B"/><circle cx="60" cy="52" r="1.8" fill="#20242B"/>'
    '<circle cx="30" cy="61" r="2" fill="#E6B23A"/><path d="M27 63 Q30 69 33 63 Z" fill="#E6B23A"/>'
    '<circle cx="70" cy="61" r="2" fill="#E6B23A"/><path d="M67 63 Q70 69 73 63 Z" fill="#E6B23A"/>'
    '<path d="M44 65 Q50 69 56 65" fill="none" stroke="#20242B" stroke-width="2" stroke-linecap="round"/>'
    '</svg>'
)
_AV_NANDI = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Nandi Pat">'
    '<circle cx="50" cy="50" r="48" fill="#7A6FD6"/>'
    '<path d="M33 33 Q22 26 24 15 Q33 21 39 31 Z" fill="#fff"/>'
    '<path d="M67 33 Q78 26 76 15 Q67 21 61 31 Z" fill="#fff"/>'
    '<ellipse cx="28" cy="47" rx="5" ry="3.6" fill="#fff"/>'
    '<ellipse cx="72" cy="47" rx="5" ry="3.6" fill="#fff"/>'
    '<rect x="31" y="34" width="38" height="40" rx="14" fill="#fff"/>'
    '<ellipse cx="50" cy="66" rx="13" ry="9" fill="#E7E2F7"/>'
    '<path d="M47 40 L47 47 M53 40 L53 47" stroke="#EE9A22" stroke-width="2.2" stroke-linecap="round"/>'
    '<path d="M47 47 Q50 50 53 47" fill="none" stroke="#EE9A22" stroke-width="2.2"/>'
    '<path d="M50 40 L50 46" stroke="#C0143C" stroke-width="1.6" stroke-linecap="round"/>'
    '<circle cx="43" cy="51" r="2.4" fill="#20242B"/><circle cx="57" cy="51" r="2.4" fill="#20242B"/>'
    '<circle cx="50" cy="70" r="4" fill="none" stroke="#E6B23A" stroke-width="2"/>'
    '</svg>'
)

AVATARS: dict[str, dict] = {
    "seth":    {"name": "Seth Pat",    "tag": "old-school bania wisdom",  "svg": _AV_SETH},
    "rao":     {"name": "Rao Pat",     "tag": "Tollywood mass swagger",   "svg": _AV_RAO},
    "singh":   {"name": "Singh Pat",   "tag": "the steady, confident ace", "svg": _AV_SINGH},
    "chai":    {"name": "Chai Pat",    "tag": "cutting-chai quant",       "svg": _AV_CHAI},
    "lakshmi": {"name": "Lakshmi Pat", "tag": "goddess of wealth",        "svg": _AV_LAKSHMI},
    "nandi":   {"name": "Nandi Pat",   "tag": "bull-market energy",       "svg": _AV_NANDI},
}
_DEFAULT_AV = "seth"


# The three data-backed flows — announced now, built with the engine. Each names
# the metric behind it so the user can still learn it today via the glossary.
_DATA_FLOWS: dict[str, dict] = {
    "fundamentals": {
        "label": "Screen by fundamentals",
        "blurb": "I'll filter on valuation, returns, growth and balance-sheet "
                 "health from the cached Screener snapshot.",
        "behind": "fundamentals",
    },
}


_PAT_CSS = """
<style>
.patHero{display:flex;align-items:center;gap:12px;margin:4px 0 12px;}
.patHeroAv{width:64px;height:64px;flex:none;border-radius:50%;overflow:hidden;background:#161b22;}
.patHeroAv svg{width:64px;height:64px;display:block;}
.patHeroName{font-weight:800;font-size:17px;}
.patHeroTag{color:#8b949e;font-size:12px;margin-top:1px;}
.patPicks{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px;}
.patPick{background:#161b22;border:1px solid #30363d;border-radius:50%;padding:0;
         width:42px;height:42px;cursor:pointer;overflow:hidden;line-height:0;}
.patPick svg{width:40px;height:40px;display:block;}
.patPick.on{border-color:#3fb950;box-shadow:0 0 0 2px rgba(63,185,80,.33);}
.patQ{background:#161b22;border:1px solid #30363d;border-radius:12px;
      border-top-left-radius:3px;padding:11px 14px;font-size:14px;line-height:1.5;
      margin:0 0 12px;max-width:92%;}
.patChips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 6px;}
.patChip{background:#1b2230;border:1px solid #2b3a52;color:#cdd9e5;border-radius:9px;
         padding:8px 12px;font-size:13px;text-decoration:none;display:inline-block;}
.patChip:hover{border-color:#1f6feb;}
.patChip .ar{color:#58a6ff;font-weight:700;}
.patAnsTerm{font-weight:800;font-size:16px;margin-bottom:4px;}
.patAnsPlain{color:#9fb0c3;font-size:13px;font-style:italic;margin-bottom:8px;}
.patAnsDetail{font-size:14px;line-height:1.65;margin:0 0 10px;}
.patMeta{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:#8b949e;
         font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
         border-top:1px solid #21262d;padding-top:8px;margin-top:2px;}
.patBack{display:inline-block;margin:0 0 12px;color:#8b949e;font-size:12px;text-decoration:none;}
.patBack:hover{color:#cdd9e5;}
.patChip.on{border-color:#3fb950;color:#fff;background:#16341f;}
.patTable{overflow-x:auto;margin-top:2px;}
.patTable table{min-width:660px;font-variant-numeric:tabular-nums;}
.patTable table.dt .dttool{margin:0 0 8px;}
</style>
"""


def _avatar_picker() -> str:
    """The persona hero + the 6-avatar picker. JS persists the pick in
    localStorage and re-skins the hero on load — server renders the default."""
    d = AVATARS[_DEFAULT_AV]
    picks = []
    for slug, a in AVATARS.items():
        on = " on" if slug == _DEFAULT_AV else ""
        picks.append(
            f'<button class="patPick{on}" data-av="{slug}" title="{_esc(a["name"])}" '
            f'onclick="patPick(\'{slug}\')" aria-label="{_esc(a["name"])}">{a["svg"]}</button>'
        )
    jsmap = "{" + ",".join(
        f'"{s}":{{"n":"{_esc(a["name"])}","t":"{_esc(a["tag"])}"}}' for s, a in AVATARS.items()
    ) + "}"
    script = (
        "<script>(function(){var M=" + jsmap + ";"
        "function pick(s){try{localStorage.setItem('patAvatar',s);}catch(e){}"
        "var src=document.querySelector('.patPick[data-av=\"'+s+'\"]');"
        "var h=document.getElementById('patHeroAv');if(src&&h){h.innerHTML=src.innerHTML;}"
        "var m=M[s];if(m){var n=document.getElementById('patHeroName'),t=document.getElementById('patHeroTag');"
        "if(n)n.textContent=m.n;if(t)t.textContent=m.t;}"
        "var ps=document.querySelectorAll('.patPick');for(var i=0;i<ps.length;i++){"
        "ps[i].classList.toggle('on',ps[i].getAttribute('data-av')===s);}}"
        "window.patPick=pick;var sv=null;try{sv=localStorage.getItem('patAvatar');}catch(e){}"
        "if(sv&&M[sv])pick(sv);})();</script>"
    )
    return (
        '<div class="patHero">'
        f'<div class="patHeroAv" id="patHeroAv">{d["svg"]}</div>'
        f'<div><div class="patHeroName" id="patHeroName">{_esc(d["name"])}</div>'
        f'<div class="patHeroTag" id="patHeroTag">{_esc(d["tag"])}</div></div>'
        '</div>'
        f'<div class="patPicks">{"".join(picks)}</div>'
        f'{script}'
    )


def _chip(href: str, label: str, arrow: bool = False) -> str:
    ar = ' <span class="ar">→</span>' if arrow else ""
    return f'<a class="patChip" href="{href}">{_esc(label)}{ar}</a>'


def _q_bubble(text: str) -> str:
    return f'<div class="patQ">{_esc(text)}</div>'


def _metric_directory() -> str:
    """All explainable terms, grouped by family — chips that link to the answer."""
    out = []
    for fam_key, fam_label in FAMILIES.items():
        ents = family(fam_key)
        if not ents:
            continue
        out.append(f'<div class="ghdr">{_esc(fam_label)}</div>')
        chips = [
            _chip(f"/dash/pat?flow=explain&explain={slug}", e["term"])
            for slug, e in ents
        ]
        out.append(f'<div class="patChips">{"".join(chips)}</div>')
    return "".join(out)


def _answer(slug: str, e: dict) -> str:
    related = []
    for r in e.get("related", []):
        re_ = get(r)
        if re_:
            related.append(_chip(f"/dash/pat?flow=explain&explain={r}", re_["term"]))
    rel_html = (
        f'<div class="ghdr">Related</div><div class="patChips">{"".join(related)}</div>'
        if related else ""
    )
    return (
        '<a class="patBack" href="/dash/pat?flow=explain">← explain another metric</a>'
        '<div class="card">'
        f'<div class="patAnsTerm">{_esc(e["term"])}</div>'
        f'<div class="patAnsPlain">{_esc(e["plain"])}</div>'
        f'<p class="patAnsDetail">{_esc(e["detail"])}</p>'
        f'<div class="patMeta"><span>unit: {_esc(e["unit"])}</span>'
        f'<span>source: {_esc(e["source"])}</span></div>'
        f'{rel_html}'
        '</div>'
    )


def _explain_flow(explain: str, q: str) -> str:
    # A specific term was chosen → answer it.
    if explain and get(explain):
        e = get(explain)
        return _q_bubble(f"Here's {e['term']} —") + _answer(explain, e)

    search = (
        '<form class="search" action="/dash/pat" method="get" autocomplete="off">'
        '<input type="hidden" name="flow" value="explain"/>'
        f'<input name="q" value="{_esc(q)}" placeholder="ask about any metric — p_score, accumulation, key price…"/>'
        '<button>Ask</button></form>'
    )

    # A free-text query → rank matches with the deterministic fallback.
    if q:
        hits = find(q, limit=8)
        if hits:
            bubble = _q_bubble(f"Closest matches for “{q}”. Tap one:")
            chips = [_chip(f"/dash/pat?flow=explain&explain={s}", e["term"]) for s, e in hits]
            return bubble + search + f'<div class="patChips">{"".join(chips)}</div>'
        return (
            _q_bubble(f"I don't have “{q}” yet — here's everything I can explain:")
            + search + _metric_directory()
        )

    # Entry point for the flow → search + full directory.
    return (
        _q_bubble("Which term should I explain? Tap one, or search.")
        + search + _metric_directory()
    )


def _data_flow(flow: str) -> str:
    f = _DATA_FLOWS[flow]
    behind = get(f["behind"])
    bridge = (
        _chip(f"/dash/pat?flow=explain&explain={f['behind']}",
              f"Explain {behind['term']}", arrow=True)
        if behind else ""
    )
    return (
        '<a class="patBack" href="/dash/pat">← back</a>'
        + _q_bubble(f["blurb"])
        + _q_bubble("This data-backed flow lands next — for now I can explain any "
                    "metric behind it.")
        + f'<div class="patChips">{bridge}'
        + _chip("/dash/pat?flow=explain", "Explain a metric")
        + '</div>'
    )


# ── data flow: accumulation setups (live, read-only over stock_signals) ──────

def _u(s) -> str:
    return quote_plus(str(s) if s is not None else "")


def _int(v) -> str:
    return str(int(v)) if v is not None else '<span class="mut">—</span>'


def _n(v, d=2) -> str:
    return f"{v:,.{d}f}" if v is not None else '<span class="mut">—</span>'


def _sgn(v, d=1) -> str:
    if v is None:
        return '<span class="mut">—</span>'
    cls = "pos" if v > 0 else ("neg" if v < 0 else "mut")
    return f'<span class="{cls}">{v:+.{d}f}%</span>'


def _cr(v) -> str:
    return f"{v / 1e7:,.1f}" if v is not None else '<span class="mut">—</span>'


def _rank_pill(rank) -> str:
    if not rank:
        return '<span class="mut">—</span>'
    return f'<span class="pill p-{_esc(rank)}">{_esc(rank)}</span>'


def _char_pill(c) -> str:
    short = {"ACCUMULATION": ("ACC", "ca-acc"), "DISTRIBUTION": ("DIST", "ca-dist"),
             "CONSOLIDATION": ("CONS", "ca-cons"), "NEUTRAL": ("NEU", "ca-neu")}
    lbl, cls = short.get(c or "", (c or "—", "ca-neu"))
    return f'<span class="pill {cls}">{_esc(lbl)}</span>'


def _chip_sel(href: str, label: str, active: bool) -> str:
    return f'<a class="{"patChip on" if active else "patChip"}" href="{href}">{_esc(label)}</a>'


def _acc_url(sector: str, strength: str, entry: str) -> str:
    qs = ["flow=accumulation"]
    if sector:
        qs.append("sector=" + _u(sector))
    if strength:
        qs.append("strength=" + _u(strength))
    if entry:
        qs.append("entry=" + _u(entry))
    return "/dash/pat?" + "&".join(qs)


def _acc_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>CMP</th><th>Rank</th><th>p/r</th><th>Character</th>'
            '<th>Δ hot%</th><th>key gap%</th><th>52w%</th><th>RS</th>'
            '<th>Sector</th><th>Deliv ₹Cr</th></tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            f'<td>{_rank_pill(r["trigger_rank"])}</td>'
            f'<td>{_int(r["p_score"])}/{_int(r["r_score"])}</td>'
            f'<td>{_char_pill(r["accum_character"])}</td>'
            f'<td>{_sgn(r["price_vs_hot_avg_pct"])}</td>'
            f'<td>{_sgn(r["gap_to_key_p3m"])}</td>'
            f'<td>{_sgn(r["pct_from_52w_high"])}</td>'
            f'<td>{_int(r["rs_rank"])}</td>'
            f'<td class="mut">{_esc(r["primary_sector"] or "—")}</td>'
            f'<td>{_cr(r["delivery_value_today"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _accumulation_flow(conn, sector: str, strength: str, entry: str) -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("Accumulation setups — a strong hand active AND the character "
                  "reading accumulation. Take it as-is, or narrow it:"),
        '<div class="ghdr">Strength</div><div class="patChips">',
    ]
    for key, (lbl, _p) in ACC_STRENGTH.items():
        out.append(_chip_sel(_acc_url(sector, key, entry), lbl, key == strength))
    out.append('</div><div class="ghdr">Entry</div><div class="patChips">')
    for key, lbl in ACC_ENTRY.items():
        out.append(_chip_sel(_acc_url(sector, strength, key), lbl, key == entry))
    out.append('</div>')

    sectors = []
    if conn is not None:
        try:
            sectors = list(conn.execute(build_accumulation_sectors_query()))
        except Exception:
            sectors = []
    out.append('<div class="ghdr">Sector</div><div class="patChips">')
    out.append(_chip_sel(_acc_url("", strength, entry), "All sectors", sector == ""))
    for r in sectors:
        out.append(_chip_sel(_acc_url(r["sector"], strength, entry),
                             f'{r["sector"]} ({r["c"]})', sector == r["sector"]))
    out.append('</div>')

    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_accumulation_query(sector, strength, entry)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    tag = f' · {_esc(sector)}' if sector else ''
    out.append(f'<div class="ghdr">Matches{tag} ({len(rows)})</div>')
    out.append(_acc_table(rows) if rows
               else '<div class="empty">No accumulation setups match — loosen the filters.</div>')
    return "".join(out)


# ── data flow: RS leaders (live, read-only over stock_signals) ───────────────

def _yn(v) -> str:
    return '<span class="pos">✓</span>' if v else '<span class="mut">·</span>'


def _txt(v) -> str:
    return f'<span class="mut">{_esc(v)}</span>' if v else '<span class="mut">—</span>'


def _rs_url(sector: str, strength: str, align: str) -> str:
    qs = ["flow=rs"]
    if sector:
        qs.append("sector=" + _u(sector))
    if strength:
        qs.append("strength=" + _u(strength))
    if align:
        qs.append("align=" + _u(align))
    return "/dash/pat?" + "&".join(qs)


def _rs_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>CMP</th><th>RS</th><th>RS 3m</th><th>vs broad</th>'
            '<th>vs sector</th><th>SiS</th><th>Sector</th><th>Pos</th><th>Character</th>'
            '</tr></thead><tbody>')
    rws = []
    for r in rows:
        sis = r["rs_vs_broad_above_200ma"] and r["rs_vs_sector_above_200ma"]
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            f'<td>{_int(r["rs_rank"])}</td>'
            f'<td>{_sgn(r["rs_vs_broad_slope_3m"])}</td>'
            f'<td>{_txt(r["rs_vs_broad_trend_state"])}</td>'
            f'<td>{_txt(r["rs_vs_sector_trend_state"])}</td>'
            f'<td>{_yn(sis)}</td>'
            f'<td class="mut">{_esc(r["primary_sector"] or "—")}</td>'
            f'<td>{_rank_pill(r["trigger_rank"])}</td>'
            f'<td>{_char_pill(r["accum_character"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _rs_flow(conn, sector: str, strength: str, align: str) -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("RS leaders — the names the market is voting for. Filter by strength, "
                  "sector, or 'strong in strong' (beating BOTH the market and its sector):"),
        '<div class="ghdr">Strength</div><div class="patChips">',
    ]
    for key, (lbl, _r) in RS_STRENGTH.items():
        out.append(_chip_sel(_rs_url(sector, key, align), lbl, key == strength))
    out.append('</div><div class="ghdr">Alignment</div><div class="patChips">')
    for key, lbl in RS_ALIGN.items():
        out.append(_chip_sel(_rs_url(sector, strength, key), lbl, key == align))
    out.append('</div>')

    sectors = []
    if conn is not None:
        try:
            sectors = list(conn.execute(build_rs_sectors_query()))
        except Exception:
            sectors = []
    out.append('<div class="ghdr">Sector</div><div class="patChips">')
    out.append(_chip_sel(_rs_url("", strength, align), "All sectors", sector == ""))
    for r in sectors:
        out.append(_chip_sel(_rs_url(r["sector"], strength, align),
                             f'{r["sector"]} ({r["c"]})', sector == r["sector"]))
    out.append('</div>')

    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_rs_query(sector, strength, align)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    tag = f' · {_esc(sector)}' if sector else ''
    out.append(f'<div class="ghdr">Leaders{tag} ({len(rows)})</div>')
    out.append(_rs_table(rows) if rows
               else '<div class="empty">No RS leaders match — loosen the filters.</div>')
    return "".join(out)


def _home() -> str:
    chips = [
        _chip("/dash/pat?flow=explain", "Explain a metric", arrow=True),
        _chip("/dash/pat?flow=accumulation", "Accumulation setups", arrow=True),
        _chip("/dash/pat?flow=rs", "RS leaders by sector", arrow=True),
        _chip("/dash/pat?flow=fundamentals", "Screen by fundamentals", arrow=True),
    ]
    return (
        _q_bubble("What are you looking for today?")
        + f'<div class="patChips">{"".join(chips)}</div>'
    )


def render_pat(flow: str = "", explain: str = "", q: str = "",
               sector: str = "", strength: str = "", entry: str = "", align: str = "",
               conn=None) -> str:
    """Build the inner HTML for /dash/pat from the chip params (+ optional DB conn)."""
    flow = (flow or "").strip().lower()
    explain = (explain or "").strip()
    q = (q or "").strip()
    sector = (sector or "").strip()
    strength = (strength or "").strip().lower()

    if explain and get(explain):
        body = _explain_flow(explain, q)
    elif flow == "explain":
        body = _explain_flow(explain, q)
    elif flow == "accumulation":
        body = _accumulation_flow(conn, sector, strength, (entry or "").strip().lower())
    elif flow == "rs":
        body = _rs_flow(conn, sector, strength, (align or "").strip().lower())
    elif flow in _DATA_FLOWS:
        body = _data_flow(flow)
    else:
        body = _home()

    return _PAT_CSS + _avatar_picker() + body
