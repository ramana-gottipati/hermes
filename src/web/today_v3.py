"""today_v3.py — the M5 orientation home (spec v1.1, owner go 2026-07-22). ADDITIVE, v3-only.

Renders the Today focus body + Context rail for `/dash/preview` (v3_preview delegates here;
no new route). Anatomy per spec §2: mood via the ONE regime vocabulary (the exact cockpit
call-chain) · the adopted count-tile band (every count a live lens, subtitle always visible) ·
the humanized what-changed board · the flagship band with provenance chips · start-here.
Zero new tables/timers; every read bounded and honest-empty (§3, Codex-pinned signatures).
"""
from __future__ import annotations

import html as _html
import urllib.parse as _uq

from src.core.db import get_conn
from src.web import ui_components_v3 as C


def _e(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _mood_html() -> str:
    """The spec §3 chain: index_signals latest → market_mood(breadth, a200) → mood_banner."""
    try:
        from src.web.market_mood import market_mood, mood_banner
        with get_conn() as conn:
            d = conn.execute("SELECT MAX(trade_date) m FROM index_signals").fetchone()
            idx_date = d["m"] if d else None
            if not idx_date:
                return ""
            b = conn.execute(
                "SELECT AVG(CASE WHEN pct_above_200d_avg>0 THEN 1.0 ELSE 0 END)*100 p "
                "FROM index_signals WHERE trade_date=? AND pct_above_200d_avg IS NOT NULL",
                (idx_date,)).fetchone()
            breadth = b["p"] if b and b["p"] is not None else None
            n = conn.execute(
                "SELECT pct_above_200d_avg a FROM index_signals "
                "WHERE index_name='Nifty 50' AND trade_date=?", (idx_date,)).fetchone()
            a200 = None if (n is None or n["a"] is None) else (n["a"] > 0)
        mood = market_mood(breadth, a200)
        extra = ("as of " + str(idx_date)[:10]
                 + (" · " + format(breadth, ".0f") + "% of indices above their 200-day line"
                    if breadth is not None else ""))
        return mood_banner(mood, extra)
    except Exception:
        return ""


def _counts() -> list[tuple[str, str, str, str]]:
    """[(count, severity-suffix, subtitle, href)] — every read table-guarded → honest zeros
    are RENDERED as empty-state tiles, never faked."""
    out: list[tuple[str, str, str, str]] = []
    with get_conn() as conn:
        try:
            from src.automation.signal_alerts import active_count
            ac = active_count(conn, within_days=7)
            crit = (ac.get("by_severity") or {}).get("critical", 0)
            out.append((str(ac.get("total", 0)), (str(crit) + " critical") if crit else "",
                        "state-changes on the signal bus this week", "/dash/attention"))
        except Exception:
            pass
        try:
            r = conn.execute("SELECT pct_advancing p, n_traded n FROM market_internals_daily "
                             "ORDER BY trade_date DESC LIMIT 1").fetchone()
            if r and r["p"] is not None:
                out.append((format(r["p"], ".0f") + "%", "",
                            "of " + format(r["n"] or 0, ",") + " stocks advanced today",
                            "/dash/market-internals"))
        except Exception:
            pass
        try:
            from src.automation.results_calendar import upcoming_results
            k = len(upcoming_results(days=7))
            out.append((str(k), "", "results meetings in the next 7 days",
                        "/dash/preview?ch=results"))
        except Exception:
            pass
        try:
            from src.automation import corp_actions as CA
            rows, _asof = CA.flagged_symbols(conn)
            out.append((str(len(rows)), "", "corporate actions going ex this fortnight",
                        "/dash/preview?ch=actions"))
        except Exception:
            pass
        try:
            has = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND "
                               "name IN ('news_symbol_tags','sent_news')").fetchall()
            if len(has) == 2:
                r = conn.execute(
                    "SELECT COUNT(DISTINCT t.news_url) c FROM news_symbol_tags t "
                    "JOIN sent_news n ON n.url=t.news_url "
                    "WHERE n.sent_at >= datetime('now','-1 day')").fetchone()
                out.append((str(r["c"] if r else 0), "",
                            "stock-tagged headlines in 24 hours", "/dash/preview?ch=wire"))
        except Exception:
            pass
    return out


def _count_band() -> str:
    tiles = _counts()
    if not tiles:
        return '<div class="pv3-dock-empty">Counts warm up as the day\'s feeds land.</div>'
    out = []
    for v, sev, sub, href in tiles:
        sevh = ('<span class="t3-sev">' + _e(sev) + "</span>") if sev else ""
        out.append('<div class="pv3-tile t3-count"><span class="v pv3-num">' + _e(v) + sevh
                   + '</span><span class="s">' + _e(sub) + ' · <a href="' + _e(href)
                   + '">open the lens →</a></span></div>')
    return '<div class="pv3-tiles">' + "".join(out) + "</div>"


_HUMAN = {"_": " "}


def _what_changed() -> str:
    rows = []
    try:
        from src.automation.signal_alerts import active_alerts
        with get_conn() as conn:
            rows = active_alerts(conn, within_days=7, limit=8)
    except Exception:
        rows = []
    if not rows:
        return C.card("What changed", '<div class="pv3-dock-empty">No state-changes on the '
                      "signal bus this week.</div>")
    out = []
    for r in rows:
        sym = str(r.get("symbol") or "")
        mid = (str(r.get("severity", "")) + " · " + str(r.get("lens", "")).replace("_", " ")
               + ": " + str(r.get("from_state", "")).replace("_", " ").lower()
               + " → " + str(r.get("to_state", "")).replace("_", " ").lower())
        out.append('<li><span class="t">' + _e(str(r.get("as_of") or "")[:10]) + "</span>"
                   '<span class="s"><a href="/dash/preview/stock?sym=' + _uq.quote(sym) + '">'
                   + _e(sym) + '</a></span><span class="m">' + _e(mid) + "</span></li>")
    return C.card("What changed", '<ul class="t3-feed">' + "".join(out) + "</ul>")


def _flagship() -> str:
    cards = [
        ("POINT-IN-TIME", "any date since 2003",
         "Replay the tape: only what was knowable that day — with the exact API call to reproduce it.",
         "/dash/replay-any-date", "Replay a date"),
        ("22 YEARS · ONE METHOD", "5,000+ sessions",
         "Market internals — breadth, delivery and effort measured the same way across two decades.",
         "/dash/market-internals", "The long tape"),
        ("PLACEBO-GATED", "most cells grey",
         "Calendar habits render only past two placebo tests. Grey IS the finding.",
         "/dash/seasonal-tape", "Seasonal tape"),
        ("NOTHING HIDDEN", "failures published",
         "Every strategy we tested — the survivors and the casualties, with their numbers.",
         "/dash/testing", "The validation record"),
    ]
    out = []
    for prov, k, body, href, label in cards:
        out.append('<div class="pv3-tile t3-moat"><span class="t3-prov">' + _e(prov)
                   + '</span><span class="v">' + _e(k) + '</span><span class="s">' + _e(body)
                   + ' <a href="' + _e(href) + '">' + _e(label) + " →</a></span></div>")
    return '<div class="pv3-tiles">' + "".join(out) + "</div>"


def _start_here() -> str:
    try:
        from src.web.symbol_search import TYPEAHEAD_JS
        ta = TYPEAHEAD_JS
    except Exception:
        ta = ""
    return C.card("Start here",
                  '<form method="get" action="/dash/preview/stock" class="t3-search">'
                  '<input id="t3sym" name="sym" placeholder="Type a company name — try '
                  '&quot;tata consultancy&quot;" autocomplete="off" '
                  'style="text-transform:uppercase;width:70%">'
                  ' <button class="pv3-btn" type="submit">Open</button></form>'
                  '<p class="t3-help">New here? <a href="/dash/reading-guide">How to read these '
                  'pages →</a> · or <a href="/dash/pat">Ask Pat</a>, the built-in explainer.</p>'
                  + ta)


_CSS = """<style>
.t3-count .v{font-size:30px;font-weight:700}
.t3-sev{font-size:11px;font-weight:600;color:var(--down);margin-left:8px;letter-spacing:.08em}
.t3-feed{list-style:none;margin:0;padding:0}
.t3-feed li{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid var(--line);
  font-size:var(--t-sm);align-items:baseline;flex-wrap:wrap}
.t3-feed li:last-child{border-bottom:0}
.t3-feed .t{color:var(--ink-3);font-family:var(--mono);font-size:var(--t-xs);flex:none;width:78px}
.t3-feed .s a{font-family:var(--mono);font-weight:700}
.t3-feed .m{color:var(--ink-2);min-width:0}
.t3-moat .t3-prov{display:block;font-size:9.5px;font-weight:700;letter-spacing:.22em;
  color:var(--accent);text-transform:uppercase;margin-bottom:4px}
.t3-moat .v{font-size:19px;font-weight:700}
.t3-idline{color:var(--ink-2);font-size:var(--t-md);margin:12px 2px 4px;max-width:74ch}
.t3-help{color:var(--ink-3);font-size:var(--t-sm);margin:10px 0 0}
</style>"""


def body() -> str:
    """The Today focus column (spec §2.1–§2.5)."""
    from src.web import infographics as ifx
    return (_CSS
            + _mood_html()
            + '<p class="t3-idline">Patearn describes what Indian-market data is doing, in '
              "plain English, and shows you the proof — never what to buy.</p>"
            + ifx.demo_framing()
            + C.section("Right now — every count is a live lens") + _count_band()
            + C.section("What changed") + _what_changed()
            + C.section("Why this is different") + _flagship()
            + C.section("Start here") + _start_here())


def rail() -> str:
    """The Context rail (spec §2.6) — the M0 toggle card is composed by v3_preview itself."""
    return (C.card("The proof", "<p>" + C.evidence_link("/dash/testing", "Validation record")
                   + "<br>" + C.evidence_link("/dash/spec-sheets", "Spec sheets (pre-registered)")
                   + "<br>" + C.evidence_link("/dash/coverage", "Coverage & honesty") + "</p>")
            + C.card("In this preview", "<p>Today · the stock hub (search above) · the design "
                     "system. Everything opt-in; the classic site is untouched.</p>"
                     "<p>" + C.evidence_link("/dash", "Back to the classic site") + "</p>"))


def _selftest() -> int:
    b = body()  # dev DB may be sparse — structure must hold regardless
    assert "t3-idline" in b and "never what to buy" in b
    assert "Start here" in b and "/dash/reading-guide" in b and "/dash/pat" in b
    assert "Why this is different" in b and b.count('<span class="t3-prov"') == 4
    assert "?symbol=" not in b
    low = b.lower()
    import re
    for verb in ("buy", "sell", "avoid", "ride", "fade"):
        hits = [m for m in re.finditer(r"\b" + verb + r"\b", low)]
        # "never what to buy" is the fence itself — the only sanctioned occurrence
        assert all(low[max(0, m.start() - 14):m.start()].endswith("what to ") for m in hits), verb
    assert rail().count("pv3-card") == 2
    print("today_v3 selftest OK — anatomy, links, fence discipline")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
