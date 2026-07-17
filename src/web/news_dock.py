"""news_dock.py — the persistent News/Flow dock (redesign M3). ADDITIVE, v3-preview-only.

Six channels over feeds that ALL exist today with timers — zero new compute, zero new tables:
Wire · Filings · Results · Corp actions · Deals/FII · Alerts. Renders as one server-side
component inside `shell_v3`'s dock slot; channel + symbol filter are URL query params
(SURFACE-PLAYBOOK 8b — a shared URL reproduces the view; no client-only state).

REUSE THE READS, never re-query (the S144 rule) — every channel calls the existing bounded,
empty-safe read mapped for it:
  wire     news_view._recent_market_news · news_tagging.news_for_symbol
  filings  direct bounded reads over insider_events / credit_rating_events (the view tables);
           per-symbol = pat filings_flow.filings_for
  results  results_calendar.upcoming_results (board_meetings, lazily created)
  actions  corp_actions.upcoming (forward ex-dates + as_of)
  deals    bulk_block_deals direct (deals.py exposes no read helper — the one mapped gap)
           + participants_flow.fii_stance for the FII positioning line (NOTE: that helper is
           empty-safe but not SQL-bounded — it scans participant_oi; acceptable as an
           existing-read reuse, flagged by the M3 Codex pass)
  alerts   signal_alerts.active_alerts (severity-gated bus rail; strings humanized — S-A debt)

Copyright discipline: wire rows are title + source + link ONLY (the /dash/wire treatment).
Every symbol links `/dash/stock?sym=` (playbook #9 — `sym`, never `symbol`).
Every read is table-guarded / try-excepted → an honest per-channel empty state, never a 500.
"""
from __future__ import annotations

import html as _html
import urllib.parse as _uq

from src.core.db import get_conn

CHANNELS = [
    ("wire", "Wire"),
    ("filings", "Filings"),
    ("results", "Results"),
    ("actions", "Corp actions"),
    ("deals", "Deals / FII"),
    ("alerts", "Alerts"),
]
_CH_KEYS = {k for k, _ in CHANNELS}

_CSS = """<style>
.pv3-dock{background:var(--bg-1);border:1px solid var(--line);border-radius:var(--r)}
.pv3-dock-tabs{display:flex;gap:2px;flex-wrap:wrap;padding:8px 10px;border-bottom:1px solid var(--line);align-items:center}
.pv3-dock-tabs a{padding:5px 11px;border-radius:var(--r-pill);font-size:var(--t-sm);color:var(--ink-2)}
.pv3-dock-tabs a.on{background:var(--accent-dim);color:var(--accent);font-weight:600}
.pv3-dock-sym{margin-left:auto;display:flex;gap:6px;align-items:center}
.pv3-dock-sym input{background:var(--bg-2);border:1px solid var(--line-2);color:var(--ink);
  border-radius:var(--r-sm);padding:4px 8px;font:400 var(--t-sm) var(--mono);width:92px;text-transform:uppercase}
.pv3-dock-rows{list-style:none;margin:0;padding:4px 0;max-height:340px;overflow-y:auto}
.pv3-dock-rows li{display:flex;gap:10px;padding:7px 14px;border-bottom:1px solid var(--line);
  font-size:var(--t-sm);align-items:baseline;flex-wrap:wrap}
.pv3-dock-rows li:last-child{border-bottom:0}
.pv3-dock-rows .t{color:var(--ink-3);font-family:var(--mono);font-size:var(--t-xs);flex:none;min-width:82px}
.pv3-dock-rows .s a{font-family:var(--mono);font-weight:600}
.pv3-dock-rows .m{color:var(--ink-2);min-width:0}
.pv3-dock-rows .src{color:var(--ink-3);font-size:var(--t-xs);flex:none}
.pv3-dock-empty{padding:16px;color:var(--ink-3);font-size:var(--t-sm)}
.pv3-dock-foot{padding:6px 14px;border-top:1px solid var(--line);color:var(--ink-3);font-size:var(--t-xs)}
</style>"""


def css() -> str:
    return _CSS


def _e(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _sym_link(sym: str) -> str:
    return '<span class="s"><a href="/dash/stock?sym=' + _uq.quote(str(sym)) + '">' + _e(sym) + "</a></span>"


def _row(when: str, mid_html: str, sym: str = "", src: str = "") -> str:
    parts = ['<li><span class="t">' + _e(when) + "</span>"]
    if sym:
        parts.append(_sym_link(sym))
    parts.append('<span class="m">' + mid_html + "</span>")
    if src:
        parts.append('<span class="src">' + _e(src) + "</span>")
    parts.append("</li>")
    return "".join(parts)


def _empty(msg: str) -> str:
    return '<div class="pv3-dock-empty">' + _e(msg) + "</div>"


def _human(s) -> str:
    """Machine states → plain words (the S-A humanize debt): DISTRIB→STRONG_DISTRIB reads as
    'distrib → strong distrib'."""
    return _e(str(s or "").replace("_", " ").lower())


# ── channel renderers — each: bounded read → <li> rows, or the honest empty state ──────────

def _ch_wire(conn, sym: str) -> str:
    try:
        if sym:
            from src.automation import news_tagging as NT
            rows = NT.news_for_symbol(conn, sym, limit=15)
        else:
            from src.web.news_view import _recent_market_news
            rows = _recent_market_news(conn, limit=15)
    except Exception:
        rows = []
    if not rows:
        return _empty("No tagged headlines in the window" + ((" for " + sym) if sym else "") + ".")
    from src.web.news_view import _safe_url  # http(s)-only href guard (Codex M3 B1) — feed
    out = []                                 # URLs are attacker-influenced external data
    for r in rows:
        title = ('<a href="' + _safe_url(r.get("url") or "") + '" rel="noopener">'
                 + _e(r.get("title")) + "</a>")
        out.append(_row(str(r.get("sent_at") or "")[:16], title, src=str(r.get("source") or "")))
    return '<ul class="pv3-dock-rows">' + "".join(out) + "</ul>"


def _ch_filings(conn, sym: str) -> str:
    try:
        if sym:
            from src.pat import filings_flow as FF
            b = FF.filings_for(conn, sym)
            if not FF.has_any(b):
                return _empty("No recent filings for " + sym + ".")
            out = []
            for r in (b.get("insider") or []):
                out.append(_row(str(r.get("disclosure_dt") or "")[:10],
                                _human(r.get("category")) + " · " + _human(r.get("txn_class"))
                                + " · ₹" + _e(r.get("value_rs")), sym=sym))
            for r in (b.get("ratings") or []):
                out.append(_row(str(r.get("t0") or "")[:10],
                                _e(r.get("agency")) + " · " + _human(r.get("action_class"))
                                + " · " + _e(r.get("rating_raw")), sym=sym))
            # SAST + holdings render too, so has_any(bundle) always matches what shows
            # (Codex M3 B2 — a SAST-only or holdings-only symbol must never read as empty)
            if b.get("sast"):
                out.append(_row("", 'pledge / stake activity on record — '
                                '<a href="/dash/sast">Stake · Pledge lens</a>', sym=sym))
            hold = b.get("holdings") or {}
            for h in (hold.get("rows") or [])[:3]:
                out.append(_row(str(hold.get("as_of") or "")[:10],
                                "holdings · " + _e(h.get("metric")) + " " + _e(h.get("value"))
                                + "% (QoQ " + _e(h.get("delta")) + ")", sym=sym))
            return ('<ul class="pv3-dock-rows">' + "".join(out) + "</ul>") if out \
                else _empty("No recent filings for " + sym + ".")
        out = []
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='insider_events'").fetchone():
            for r in conn.execute(
                    "SELECT disclosure_dt, symbol, category, txn_class, value_rs FROM insider_events "
                    "WHERE amendment_flag=0 ORDER BY disclosure_dt DESC LIMIT 8"):
                out.append(_row(str(r["disclosure_dt"] or "")[:10],
                                "insider · " + _human(r["category"]) + " · " + _human(r["txn_class"]),
                                sym=r["symbol"]))
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='credit_rating_events'").fetchone():
            for r in conn.execute(
                    "SELECT COALESCE(broadcast_dt, rating_date) AS t0, symbol, agency, action_class, "
                    "rating_raw FROM credit_rating_events ORDER BY t0 DESC LIMIT 8"):
                out.append(_row(str(r["t0"] or "")[:10],
                                "rating · " + _e(r["agency"]) + " · " + _human(r["action_class"]),
                                sym=r["symbol"]))
        return ('<ul class="pv3-dock-rows">' + "".join(out) + "</ul>") if out \
            else _empty("No filings events yet.")
    except Exception:
        return _empty("No filings events yet.")


def _ch_results(conn, sym: str) -> str:
    try:
        from src.automation.results_calendar import upcoming_results
        rows = upcoming_results(days=21)
    except Exception:
        rows = []
    if sym:
        rows = [r for r in rows if str(r["symbol"]).upper() == sym]
    if not rows:
        return _empty("No results meetings in the next 21 days"
                      + ((" for " + sym) if sym else "") + ".")
    out = [_row(str(r["meeting_date"] or "")[:10], _e(r["company"] or r["purpose"]),
                sym=r["symbol"]) for r in rows[:15]]
    return '<ul class="pv3-dock-rows">' + "".join(out) + "</ul>"


def _ch_actions(conn, sym: str) -> str:
    try:
        from src.automation import corp_actions as CA
        rows, as_of = CA.upcoming(conn, days=30)
    except Exception:
        rows, as_of = [], None
    if sym:
        rows = [r for r in rows if str(r.get("symbol", "")).upper() == sym]
    if not rows:
        return _empty("No corporate actions going ex in the next 30 days"
                      + ((" for " + sym) if sym else "") + ".")
    out = [_row("ex " + str(r.get("ex_date") or "")[:10],
                _human(r.get("action_type")) + " · " + _e(r.get("details") or ""),
                sym=r.get("symbol", "")) for r in rows[:15]]
    note = ('<div class="pv3-dock-foot">feed as of ' + _e(as_of) + "</div>") if as_of else ""
    return '<ul class="pv3-dock-rows">' + "".join(out) + "</ul>" + note


def _ch_deals(conn, sym: str) -> str:
    out, stance = [], ""
    try:
        from src.pat.participants_flow import fii_stance
        st = fii_stance(conn)
        if st:
            stance = ('<div class="pv3-dock-foot">FII index-futures stance: '
                      + _e(st.get("stance")) + " (as of " + _e(st.get("as_of")) + ")</div>")
    except Exception:
        pass
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='bulk_block_deals'").fetchone():
            q = ("SELECT trade_date, symbol, deal_type, client_name, side, qty, price "
                 "FROM bulk_block_deals ")
            args: tuple = ()
            if sym:
                q += "WHERE symbol=? "
                args = (sym,)
            q += "ORDER BY trade_date DESC LIMIT 12"
            for r in conn.execute(q, args):
                out.append(_row(str(r["trade_date"] or "")[:10],
                                _e(r["deal_type"]) + " · " + _e(r["client_name"]) + " · "
                                + _e(r["side"]) + " " + _e(r["qty"]) + " @ ₹" + _e(r["price"]),
                                sym=r["symbol"]))
    except Exception:
        pass
    if not out and not stance:
        return _empty("No named-flow deals in the window" + ((" for " + sym) if sym else "") + ".")
    body = ('<ul class="pv3-dock-rows">' + "".join(out) + "</ul>") if out \
        else _empty("No named-flow deals in the window" + ((" for " + sym) if sym else "") + ".")
    return body + stance


def _ch_alerts(conn, sym: str) -> str:
    try:
        if sym:
            from src.pat.whatchanged_flow import changes
            rows = changes(conn, sym, within_days=7, limit=12)
        else:
            from src.automation.signal_alerts import active_alerts
            rows = active_alerts(conn, within_days=7, limit=12)
    except Exception:
        rows = []
    if not rows:
        return _empty("No state-changes on the signal bus this week"
                      + ((" for " + sym) if sym else "") + ".")
    out = []
    for r in rows:
        mid = (_e(r.get("severity", "")) + " · " + _human(r.get("lens"))
               + ": " + _human(r.get("from_state")) + " → " + _human(r.get("to_state")))
        out.append(_row(str(r.get("as_of") or "")[:10], mid, sym=r.get("symbol", "")))
    return '<ul class="pv3-dock-rows">' + "".join(out) + "</ul>"


_RENDER = {"wire": _ch_wire, "filings": _ch_filings, "results": _ch_results,
           "actions": _ch_actions, "deals": _ch_deals, "alerts": _ch_alerts}


def dock_html(ch: str = "wire", sym: str = "", base: str = "/dash/preview") -> str:
    """The full dock: channel tabs (URL-state links on `base`) + the active channel's rows +
    the context fence. Any read failure degrades to the channel's honest empty state."""
    ch = ch if ch in _CH_KEYS else "wire"
    sym = str(sym or "").strip().upper()[:20]
    tabs = []
    for key, label in CHANNELS:
        qs = "?ch=" + key + (("&sym=" + _uq.quote(sym)) if sym else "")
        cls = ' class="on"' if key == ch else ""
        tabs.append("<a" + cls + ' href="' + base + qs + '">' + _e(label) + "</a>")
    symbox = ('<form class="pv3-dock-sym" method="get" action="' + base + '">'
              '<input type="hidden" name="ch" value="' + ch + '">'
              '<input name="sym" value="' + _e(sym) + '" placeholder="filter: SYM" '
              'aria-label="Filter by symbol"><button class="pv3-btn" type="submit">Go</button>'
              + ('<a class="pv3-btn" href="' + base + "?ch=" + ch + '">All</a>' if sym else "")
              + "</form>")
    try:
        with get_conn() as conn:
            body = _RENDER[ch](conn, sym)
    except Exception:
        body = _empty("Data unavailable right now.")
    from src.web import infographics as _ifx
    foot = ('<div class="pv3-dock-foot">' + _e(_ifx.fence("context", cap=True))
            + " · primary-source exchange feeds, bounded reads</div>")
    return ('<div class="pv3-dock"><nav class="pv3-dock-tabs" aria-label="Flow channels">'
            + "".join(tabs) + symbox + "</nav>" + body + foot + "</div>")


def _selftest() -> int:
    h = dock_html("wire")
    assert "pv3-dock-tabs" in h and 'class="on"' in h and "Context, not a signal" in h
    for key, _label in CHANNELS:
        hh = dock_html(key, sym="TCS")
        assert "?ch=" + key in hh and "sym=TCS" in hh, key
        assert "?symbol=" not in hh, key + " emits ?symbol= (the P0-1 bug class)"
    assert dock_html("nonsense").count('class="on"') == 1  # unknown channel → wire
    print("news_dock selftest OK — 6 channels render, URL state carried, sym= discipline")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
