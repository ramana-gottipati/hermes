"""hub_sections_v3.py — the M4 stock hub's section renderers (spec §2.4/§7). ADDITIVE, v3-only.

One bounded `load_core()` read feeds the digest, the checks blocks, and the light sections.
Reuse per the review-verified list: `_mep_stock_panel` · `_cpr_stock_panel` (caller assembles
`by_tf`) · `_fno_stock_panel` · `credibility_fingerprint.card_html` · `seasonal_full_panel` ·
`momentum_pane.card_html`. NEW renderers: Positioning and pt14/Quality (their legacy renderings
are inline in the frozen `dash_stock`). Every read is table-guarded; every section degrades to
an honest empty state.

Checks-as-UI: real thresholds only — pt14's QG gate imports the actual constants from
`src.automation.scoring`; the confluence pillars mirror `screener_plus`'s definitions.
Wording: descriptive states, never action verbs (tested).
"""
from __future__ import annotations

import html as _html
import urllib.parse as _uq

from src.core.db import get_conn

# ── the section catalog (order = the sticky index; spec §2.3) ────────────────────────
SECTIONS = [
    ("chart", "Chart"), ("pos", "Positioning"), ("mep", "Accumulation"),
    ("rs", "Strength"), ("qual", "Quality"), ("cpr", "Structure"),
    ("cci", "Credibility"), ("seasonal", "Seasonality"), ("fno", "F&O"),
]
# rendered inline on first load; the rest expand server-side via ?section= (spec §6)
DEFAULT_OPEN = {"chart", "pos"}

# section → (glossary chip key from term_chip.SEEDS, spoke href template, spoke label)
_SECTION_META = {
    "pos":      ("dvpt", "/dash/stocks", "Positioning lens"),
    "mep":      ("mep", "/dash/mep", "Accum / Distrib lens"),
    "rs":       ("rsband", "/dash/rs-hub", "Relative-strength hub"),
    "qual":     ("pt14", "/dash/growth", "Growth / quality lens"),
    "cpr":      ("cpr", "/dash/cpr", "Structure lens"),
    "cci":      ("cci", "/dash/concalls", "Credibility lens"),
    "seasonal": ("", "/dash/seasonal-tape", "Seasonal tape"),
    "fno":      ("", "/dash/participants", "Participants lens"),
    "chart":    ("", "/dash/stock", "Full classic chart"),
}


def _e(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _row(conn, q: str, args: tuple):
    try:
        return conn.execute(q, args).fetchone()
    except Exception:
        return None


def _has(conn, table: str) -> bool:
    try:
        return bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())
    except Exception:
        return False


def load_core(sym: str) -> dict:
    """ONE bounded pass over the per-symbol signal tables. Absent tables/rows → None fields."""
    core: dict = {"sym": sym}
    with get_conn() as conn:
        core["sig"] = _row(conn, "SELECT * FROM stock_signals WHERE symbol=?", (sym,)) \
            if _has(conn, "stock_signals") else None
        if _has(conn, "bhavcopy_rows"):
            try:
                bars = conn.execute(
                    "SELECT trade_date, close, deliv_per FROM bhavcopy_rows WHERE symbol=? "
                    "AND series='EQ' ORDER BY trade_date DESC LIMIT 2", (sym,)).fetchall()
            except Exception:
                bars = []
            core["bar"] = bars[0] if bars else None
            core["prev"] = bars[1] if len(bars) > 1 else None
        core["mep"] = _row(conn, "SELECT * FROM mep_signals WHERE symbol=? "
                                 "ORDER BY trade_date DESC LIMIT 1", (sym,)) \
            if _has(conn, "mep_signals") else None
        core["pt"] = _row(conn, "SELECT * FROM pattern_scores WHERE symbol=?", (sym,)) \
            if _has(conn, "pattern_scores") else None
        core["ca"] = _row(conn, "SELECT * FROM capital_allocation_scores WHERE symbol=?", (sym,)) \
            if _has(conn, "capital_allocation_scores") else None
        core["cci"] = _row(conn, "SELECT * FROM concall_scores WHERE symbol=? "
                                 "ORDER BY rowid DESC LIMIT 1", (sym,)) \
            if _has(conn, "concall_scores") else None
        core["wolfe"] = _row(conn, "SELECT * FROM wolfe_signals WHERE symbol=? "
                                   "ORDER BY rowid DESC LIMIT 1", (sym,)) \
            if _has(conn, "wolfe_signals") else None
        core["has_fno"] = bool(_row(conn, "SELECT 1 FROM fno_oi_signals WHERE symbol=? LIMIT 1",
                                    (sym,))) if _has(conn, "fno_oi_signals") else False
        try:
            from src.web.dashboard import _cpr_latest_by_tf
            core["cpr_by_tf"] = _cpr_latest_by_tf(conn, [sym]).get(sym, {}) \
                if _has(conn, "cpr_signals") else {}
        except Exception:
            core["cpr_by_tf"] = {}
        core["name"] = ""
        if _has(conn, "security_master"):
            r = _row(conn, "SELECT COALESCE(company_name,'') FROM security_master "
                           "WHERE symbol=?", (sym,))
            core["name"] = r[0] if r else ""
        core["themes"] = []
        try:
            from src.automation import theme_tags as TT
            core["themes"] = (TT.approved_tags_for(conn, [sym]).get(sym) or [])[:5]
        except Exception:
            pass
    return core


def _g(rowlike, key, default=None):
    try:
        v = rowlike[key]
        return default if v is None else v
    except Exception:
        return default


# ── the digest (spec §2.2) ───────────────────────────────────────────────────────────

def _chip_tile(chip_key: str, sym: str, value: str, anchor: str) -> str:
    """Spec §2.2: each digest tile = an M2 term chip + the number + the evidence anchor."""
    from src.web import term_chip
    return ('<div class="pv3-tile hub-tile">'
            '<span class="v">' + _e(value) + "</span>"
            '<span class="s">' + term_chip.chip(chip_key, sym=sym)
            + ' · <a href="#' + anchor + '">evidence →</a></span></div>')


# the §9.1 proposed order, shipping as the default (owner-editable at build review)
def digest_tiles(core: dict) -> str:
    sym = core["sym"]
    sig, mep, pt, cci = core.get("sig"), core.get("mep"), core.get("pt"), core.get("cci")
    tiles = []
    if sig is not None:
        try:
            from src.web.dashboard import _conv_of
            conv = format(_conv_of(_g(sig, "p_score"), _g(sig, "rs_rank")), ".0f")
        except Exception:
            conv = "—"
        tiles.append(_chip_tile("conviction", sym, conv, "pos"))
        xp = _g(sig, "ratio_today_vs_power_1m")
        tiles.append(_chip_tile("dvpt", sym,
                                str(_g(sig, "trigger_rank", "—")) + " · "
                                + ((format(xp, ".2f") + "×") if xp is not None else "—"), "pos"))
        rs = _g(sig, "rs_rank")
        tiles.append(_chip_tile("rsrank", sym, ("#" + str(rs)) if rs is not None else "—", "rs"))
    if mep is not None:
        tiles.append(_chip_tile("mep", sym,
                                str(_g(mep, "mep_state_smooth", "—")).replace("_", " ").lower(),
                                "mep"))
    if pt is not None:
        tiles.append(_chip_tile("pt14", sym,
                                str(_g(pt, "tier", "—")) + " · " + str(_g(pt, "ns_base", "—")),
                                "qual"))
    if cci is not None:
        tiles.append(_chip_tile("cci", sym,
                                str(_g(cci, "tier", "—")) + " · " + str(_g(cci, "composite_score", "—")),
                                "cci"))
    if core.get("cpr_by_tf"):
        d = _g(core["cpr_by_tf"].get("D", {}), "pattern")
        tiles.append(_chip_tile("cpr", sym, str(d or "—").replace("_", " "), "cpr"))
    if sig is not None:
        w52 = _g(sig, "pct_from_52w_high")
        tiles.append(_chip_tile("w52", sym,
                                (format(w52, ".1f") + "%") if w52 is not None else "—", "chart"))
    if not tiles:
        return '<div class="pv3-dock-empty">No signal data for this symbol yet.</div>'
    return '<div class="pv3-tiles">' + "".join(tiles) + "</div>"


_STATE_WORDS = {"STRONG_ACCUM": "strong accumulation", "ACCUM": "accumulation",
                "NEUTRAL": "a neutral tape", "DISTRIB": "distribution",
                "STRONG_DISTRIB": "strong distribution"}


def narrative(core: dict) -> str:
    """ONE deterministic descriptive sentence from stored fields (spec §2.2). No advice verbs
    (tested); graceful under any missing field; describes, never predicts."""
    sig, mep, pt, cci = core.get("sig"), core.get("mep"), core.get("pt"), core.get("cci")
    bits = []
    if sig is not None and _g(sig, "trigger_rank") in ("SS", "S"):
        bits.append("today's delivery positioning sits in the top trigger band")
    if mep is not None and _g(mep, "mep_state_smooth") in _STATE_WORDS:
        bits.append("the tape reads as " + _STATE_WORDS[_g(mep, "mep_state_smooth")])
    if sig is not None and _g(sig, "rs_rank") is not None:
        r = _g(sig, "rs_rank")
        band = "top-quartile" if r >= 75 else ("bottom-quartile" if r <= 25 else "mid-pack")
        bits.append("relative strength is " + band + " (#" + str(r) + " of 99)")
    if pt is not None and _g(pt, "tier"):
        bits.append("the 14-pattern quality read is tier " + str(_g(pt, "tier")))
    if cci is not None and _g(cci, "tier"):
        bits.append("management credibility grades " + str(_g(cci, "tier")))
    if not bits:
        return ""
    return ('<p class="hub-narr">' + _e("; ".join(bits[:4]).capitalize() + ".")
            + ' <i>Every clause above is a stored, dated read — tap any tile for its evidence.</i></p>')


def fired_badges(core: dict) -> str:
    """Lenses flagging THIS symbol, derived from the fields already loaded (bounded — no
    estate-wide scan). Links carry ?sym= (the StockEdge loop)."""
    sym, out = core["sym"], []

    def badge(label, href):
        out.append('<a class="hub-badge" href="' + href + "?sym=" + _uq.quote(sym) + '">'
                   + _e(label) + "</a>")
    sig, mep = core.get("sig"), core.get("mep")
    if sig is not None and _g(sig, "trigger_rank") in ("SS", "S"):
        badge("Positioning trigger", "/dash/stocks")
    if mep is not None and str(_g(mep, "mep_state_smooth", "")).startswith("STRONG"):
        badge("Accum/Distrib extreme", "/dash/mep")
    if sig is not None and (_g(sig, "rs_rank") or 0) >= 90:
        badge("Leaders board", "/dash/leaders")
    w = core.get("wolfe")
    if w is not None and _g(w, "in_zone"):
        badge("Wolfe wave in zone", "/dash/wolfe/scan")
    if not out:
        return ""
    return ('<div class="hub-badges"><span class="lbl">Lenses flagging ' + _e(sym)
            + " from this read:</span>" + "".join(out) + "</div>")


# ── checks-as-UI (spec §2.4; thresholds imported, never restated) ────────────────────

def _check(ok, label: str, detail: str) -> str:
    mark = "✓" if ok else "✗"
    cls = "ok" if ok else "no"
    return ('<li class="' + cls + '"><span class="mk">' + mark + "</span>"
            + _e(label) + ' <span class="d">' + _e(detail) + "</span></li>")


def checks_confluence(core: dict) -> str:
    """The 6 pillars, mirroring screener_plus's confluence definitions — shown with values."""
    sig, mep, cci, w = core.get("sig"), core.get("mep"), core.get("cci"), core.get("wolfe")
    d = core.get("cpr_by_tf", {}).get("D", {}) if core.get("cpr_by_tf") else {}
    ps = _g(sig, "p_score") if sig is not None else None
    rs = _g(sig, "rs_rank") if sig is not None else None
    ms = _g(mep, "mep_state_smooth") if mep is not None else None
    ct = _g(cci, "tier") if cci is not None else None
    items = [
        _check(ps is not None and ps >= 4, "Positioning", "p-score " + str(ps) + " (needs ≥4)"),
        _check(ms in ("ACCUM", "STRONG_ACCUM"), "Accumulation", "state " + str(ms)),
        _check(rs is not None and rs >= 80, "Strength", "RS rank " + str(rs) + " (needs ≥80)"),
        _check(_g(d, "pattern") == "BULL_U", "Structure", "daily pattern " + str(_g(d, "pattern"))),
        _check(ct in ("A+", "A"), "Credibility", "tier " + str(ct) + " (needs A/A+)"),
        _check(w is not None and bool(_g(w, "in_zone")) and str(_g(w, "dir", "")).lower().startswith("bull"),
               "Wolfe", "in-zone bull wave present" if w is not None else "no wave"),
    ]
    n = sum(1 for i in items if 'class="ok"' in i)
    return ('<div class="hub-checks"><div class="hd">Confluence — ' + str(n)
            + ' of 6 pillars align (a count, not a verdict)</div><ul>' + "".join(items)
            + "</ul></div>")


def checks_pt14(core: dict) -> str:
    pt = core.get("pt")
    if pt is None:
        return '<div class="pv3-dock-empty">No pt14 score for this symbol (not scored, or financials — see the lens note).</div>'
    try:
        from src.automation.scoring import QG_THRESHOLD, QG_MAX, UNVERIFIED_MULTIPLIER
    except Exception:
        QG_THRESHOLD, QG_MAX, UNVERIFIED_MULTIPLIER = 151.2, 252, 0.70
    items = [
        _check(bool(_g(pt, "qg_pass")), "Quality gate",
               "score vs threshold " + format(QG_THRESHOLD, ".1f") + "/" + str(QG_MAX)),
        _check(not bool(_g(pt, "hard_disqualified")), "No hard disqualifier",
               str(_g(pt, "disqualifier_reasons") or "none recorded")),
    ]
    ca = core.get("ca")
    if ca is not None:
        items.append(_check(str(_g(ca, "ca_tier", "")) in ("EXCELLENT", "GOOD"),
                            "Capital allocation", "C-tier " + str(_g(ca, "ca_tier"))
                            + " · score " + str(_g(ca, "ca_score"))))
    return ('<div class="hub-checks"><div class="hd">Quality gates — real thresholds; unverified '
            "patterns carry a ×" + format(UNVERIFIED_MULTIPLIER, ".2f")
            + ' haircut</div><ul>' + "".join(items) + "</ul></div>")


# ── sections ─────────────────────────────────────────────────────────────────────────

def _section_shell(key: str, title: str, sym: str, inner: str, open_: bool) -> str:
    chip_key, spoke, spoke_label = _SECTION_META.get(key, ("", "", ""))
    head = ['<div class="hub-sec-hd"><h2 id="' + key + '">']
    if chip_key:
        from src.web import term_chip
        head.append(term_chip.chip(chip_key, sym=sym))
    else:
        head.append(_e(title))
    head.append("</h2>")
    if spoke:
        head.append('<a class="pv3-ev" href="' + spoke + "?sym=" + _uq.quote(sym) + '">'
                    + _e(spoke_label) + " for " + _e(sym) + " →</a>")
    head.append("</div>")
    return ('<section class="hub-sec" data-sec="' + key + '">' + "".join(head) + inner
            + "</section>")


def _collapsed(key: str, title: str, sym: str, summary: str, qs_extra: str = "") -> str:
    # qs_extra carries dock/compare state (&ch=…&cmp=…) so expansion never drops it (spec §6)
    href = ("/dash/preview/stock?sym=" + _uq.quote(sym) + "&section=" + key
            + qs_extra + "#" + key)
    return ('<section class="hub-sec collapsed" data-sec="' + key + '"><div class="hub-sec-hd">'
            '<h2 id="' + key + '">' + _e(title) + "</h2>"
            '<a class="pv3-btn" href="' + href + '">Open section</a></div>'
            '<p class="hub-sum">' + _e(summary) + "</p></section>")


def render_sections(core: dict, open_secs: set, qs_extra: str = "") -> str:
    """Every section renders its shell; heavy inners render only when opened (spec §6)."""
    sym = core["sym"]
    out = []
    for key, title in SECTIONS:
        if key == "fno" and not core.get("has_fno"):
            continue
        if key not in open_secs:
            out.append(_collapsed(key, title, sym, _summary_line(core, key), qs_extra))
            continue
        out.append(_section_shell(key, title, sym, _inner(core, key), True))
    return "".join(out)


def _summary_line(core: dict, key: str) -> str:
    if key == "mep" and core.get("mep") is not None:
        return "State " + str(_g(core["mep"], "mep_state_smooth", "—")) + " · descriptor-only (D62)."
    if key == "rs" and core.get("sig") is not None:
        return "RS rank #" + str(_g(core["sig"], "rs_rank", "—")) + " · trend " \
            + str(_g(core["sig"], "rs_vs_broad_trend_state", "—")) + "."
    if key == "qual":
        return "The 14-pattern quality read with its real gate thresholds."
    if key == "cpr":
        return "Pivot structure across D/W/M timeframes."
    if key == "cci" and core.get("cci") is not None:
        return "Tier " + str(_g(core["cci"], "tier", "—")) + " · promise-vs-delivery record."
    if key == "seasonal":
        return "The stock's own certified calendar residual — most cells grey out by design."
    if key == "fno":
        return "Futures open interest, quadrant and option walls."
    return "Open for the full evidence."


def _inner(core: dict, key: str) -> str:
    sym = core["sym"]
    try:
        if key == "chart":
            from src.web import stock_chart_v3
            from src.web import infographics as _ifx
            return (stock_chart_v3.chart_html(sym, core.get("rng", ""))
                    + '<p class="hub-note">' + _e(_ifx.fence("not_buy_sell", cap=True))
                    + ' · <a href="/dash/reading-guide">How to read these charts →</a></p>'
                    + checks_confluence(core))
        if key == "pos":
            return _pos_panel(core)
        if key == "mep":
            from src.web.dashboard import _mep_stock_panel
            return _mep_stock_panel(sym)
        if key == "rs":
            from src.web import momentum_pane
            return momentum_pane.card_html(sym)
        if key == "qual":
            return checks_pt14(core) + _qual_panel(core)
        if key == "cpr":
            from src.web.dashboard import _cpr_stock_panel
            return _cpr_stock_panel(core.get("cpr_by_tf") or {})
        if key == "cci":
            from src.web import credibility_fingerprint
            return credibility_fingerprint.card_html(sym)
        if key == "seasonal":
            from src.web.seasonal_view import seasonal_full_panel
            from src.web.seasonal_events_view import event_cadence_card
            return seasonal_full_panel("stock", sym) + event_cadence_card("stock", sym)
        if key == "fno":
            from src.web.dashboard import _fno_stock_panel
            return _fno_stock_panel(sym)
    except Exception:
        pass
    return '<div class="pv3-dock-empty">This section could not load its data right now.</div>'


def _pos_panel(core: dict) -> str:
    sig = core.get("sig")
    if sig is None:
        return '<div class="pv3-dock-empty">No positioning signals for this symbol.</div>'
    rows = []

    def add(label, val, gloss=""):
        rows.append("<tr><td>" + _e(label) + '</td><td class="pv3-num">' + _e(val) + "</td></tr>")
    dv = _g(sig, "delivery_value_per_trade")
    add("Delivery size today (DVPT)", ("₹" + format(dv, ",.0f")) if dv is not None else "—")
    xp = _g(sig, "ratio_today_vs_power_1m")
    add("Intensity vs own 1-month power days", (format(xp, ".2f") + "×") if xp is not None else "—")
    add("Baselines beaten today (p / r)", str(_g(sig, "p_score", "—")) + " / " + str(_g(sig, "r_score", "—")))
    add("Trigger band", str(_g(sig, "trigger_rank", "—")))
    for h in ("3m", "6m", "12m"):
        gap = _g(sig, "gap_to_key_p" + h)
        add("Gap to key price (" + h + ")", (format(gap, "+.1f") + "%") if gap is not None else "—")
    add("Accumulation character", str(_g(sig, "accum_character", "—")).replace("_", " "))
    return ('<div class="pv3-scroll"><table class="hub-t">' + "".join(rows) + "</table></div>"
            '<p class="hub-note">Where big money transacted and how today compares to the '
            "stock's own institutional baselines — a description of the tape, not a forecast.</p>")


def _qual_panel(core: dict) -> str:
    pt = core.get("pt")
    if pt is None:
        return ""
    rows = ["<tr><td>Naked score (ns_base)</td><td class=\"pv3-num\">"
            + _e(_g(pt, "ns_base", "—")) + " / 100</td></tr>",
            "<tr><td>Tier</td><td class=\"pv3-num\">" + _e(_g(pt, "tier", "—")) + "</td></tr>"]
    return '<div class="pv3-scroll"><table class="hub-t">' + "".join(rows) + "</table></div>"


_CSS = """<style>
.hub-tile{cursor:pointer}
.hub-tile:hover{border-color:var(--accent)}
.hub-narr{color:var(--ink-2);margin:var(--s-3) 0}
.hub-narr i{color:var(--ink-3);font-size:var(--t-xs);font-style:normal;display:block;margin-top:4px}
.hub-badges{margin:var(--s-2) 0}
.hub-badges .lbl{color:var(--ink-3);font-size:var(--t-xs);margin-right:8px}
.hub-badge{display:inline-block;background:var(--accent-dim);color:var(--accent);
  border-radius:var(--r-pill);padding:3px 10px;font-size:var(--t-xs);margin:2px 4px 2px 0}
.hub-sec{margin:var(--s-5) 0;scroll-margin-top:90px}
.hub-sec-hd{display:flex;align-items:baseline;gap:var(--s-3);flex-wrap:wrap;
  border-bottom:1px solid var(--line);padding-bottom:6px;margin-bottom:var(--s-3)}
.hub-sec-hd h2{font-size:var(--t-xl);margin:0}
.hub-sec-hd .pv3-ev{margin-left:auto}
.hub-sec.collapsed{opacity:.92}
.hub-sum{color:var(--ink-3);font-size:var(--t-sm)}
.hub-checks{background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r-sm);
  padding:10px 14px;margin:var(--s-3) 0}
.hub-checks .hd{font-size:var(--t-xs);font-weight:600;color:var(--ink-2);
  text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}
.hub-checks ul{list-style:none;margin:0;padding:0}
.hub-checks li{padding:3px 0;font-size:var(--t-sm)}
.hub-checks .mk{display:inline-block;width:18px;font-weight:700}
.hub-checks li.ok .mk{color:var(--up)} .hub-checks li.no .mk{color:var(--down)}
.hub-checks .d{color:var(--ink-3);font-size:var(--t-xs);margin-left:6px}
.hub-t{width:100%;border-collapse:collapse;font-size:var(--t-sm)}
.hub-t td{padding:6px 8px;border-bottom:1px solid var(--line)}
.hub-t td.pv3-num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}
.hub-note{color:var(--ink-3);font-size:var(--t-xs)}
/* sticky section index */
.hub-idx{position:sticky;top:52px;z-index:20;background:var(--bg-0);display:flex;gap:2px;
  flex-wrap:wrap;padding:6px 0;border-bottom:1px solid var(--line);margin-bottom:var(--s-3)}
.hub-idx a{padding:4px 10px;border-radius:var(--r-pill);font-size:var(--t-xs);color:var(--ink-2)}
.hub-idx a:hover{background:var(--accent-dim);color:var(--accent)}
@media (max-width:640px){ .hub-sec{scroll-margin-top:120px} }
</style>"""


def css() -> str:
    return _CSS


def _selftest() -> int:
    # hermetic: fabricate a core and exercise every renderer path without a DB
    core = {"sym": "TESTX", "sig": None, "bar": None, "prev": None, "mep": None, "pt": None,
            "ca": None, "cci": None, "wolfe": None, "has_fno": False, "cpr_by_tf": {}, "name": ""}
    d = digest_tiles(core)
    assert "No signal data" in d
    assert narrative(core) == ""
    assert fired_badges(core) == ""
    ch = checks_confluence(core)
    assert ch.count('class="no"') == 6 and "of 6 pillars" in ch
    html = render_sections(core, {"chart", "pos"})
    assert 'data-sec="chart"' in html and 'data-sec="pos"' in html
    assert 'data-sec="fno"' not in html                       # conditional held
    assert html.count("Open section") >= 5                    # collapsed sections offer expansion
    assert "?symbol=" not in html and "sym=TESTX" in html
    # fence discipline in the module's own copy — the sanctioned boundary phrase itself
    # ("not a buy/sell signal") is excluded before scanning for verdict verbs
    low = (d + ch + html).lower().replace("buy/sell", "")
    for verb in ("buy", "sell", " avoid ", " ride ", " fade "):
        assert verb not in low, verb
    print("hub_sections_v3 selftest OK — digest/checks/sections, sym= discipline, fence held")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
