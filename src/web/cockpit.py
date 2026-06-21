"""Cockpit — registry-driven, full-bleed HOME + MARKETS render (collision-isolated).

Why a separate module: the big UI rebuild lives here so it doesn't fight the
parallel sessions editing dashboard.py. dashboard.py imports `render_home` /
`render_markets` and wraps the returned INNER html in its own `_shell`. We reuse
dashboard's helpers (`_mv_*`, `_rs_strip`, formatters, constants) via a LAZY
`from src.web import dashboard as D` inside each function — that breaks the import
cycle (dashboard imports us at top; we import it only at call-time, by when it is
fully loaded).

STRATEGY_REGISTRY is the single source of truth for the strategy pillars: add one
entry and it appears in the home count-strip + hub automatically — the user's
"a new strategy should auto-update the dashboard" ask (D-UI-7: strategy = a lens).
"""
from __future__ import annotations

# stock_rs does NOT import dashboard, so these top-level imports are cycle-safe.
try:
    from src.automation.stock_rs import leaders_laggards, conviction_shortlist
except Exception:  # keep the page resilient if the module shifts
    leaders_laggards = conviction_shortlist = None


def _near(g) -> bool:
    """Close vs the value-weighted key price (the 🎯 launch band), −1%…+5%."""
    return g is not None and -1.0 <= g <= 5.0


# --- THE STRATEGY REGISTRY ----------------------------------------------------
# One entry per pillar. `count(conn, sig_date, D) -> int | None` is the live count
# (None = not-yet-live). Adding an entry here makes the pillar appear on the home
# count-strip automatically. accent = the pillar's colour across the whole UI.
STRATEGY_REGISTRY = [
    {"key": "CONV", "label": "Conviction", "accent": "#d2a8ff", "href": "/dash/conviction",
     "cta": "all-pillars aligned",
     "thesis": "Every pillar aligned — an RS leader institutions are accumulating now, with the entry.",
     "count": lambda conn, d, D: (len(conviction_shortlist(limit=300)) if conviction_shortlist else 0)},
    {"key": "POS", "label": "Positioning", "accent": "#58a6ff", "href": "/dash/stocks",
     "cta": "SS/S triggers today",
     "thesis": "Where institutional delivery money is positioning now — DVPT vs its own peak-day baselines.",
     "count": lambda conn, d, D: conn.execute(
         "SELECT COUNT(*) c FROM stock_signals s JOIN bhavcopy_rows b USING(symbol,trade_date) "
         "WHERE s.trade_date=? AND s.trigger_rank IN ('SS','S') " + D._SCAN_FILTERS, (d,)).fetchone()["c"]},
    {"key": "RS", "label": "Relative Strength", "accent": "#3fb950", "href": "/dash/leaders",
     "cta": "strong-in-strong leaders",
     "thesis": "Beating the broad market and leading its own sector.",
     "count": lambda conn, d, D: (len(leaders_laggards("leaders", limit=400)) if leaders_laggards else 0)},
    {"key": "CPR", "label": "Structure · CPR", "accent": "#bc8cff", "href": "/dash/cpr",
     "cta": "fresh reversals",
     "thesis": "Multi-timeframe CPR — has price just turned (U / ∩) and is it coiled? Amplified when higher TFs agree.",
     "count": lambda conn, d, D: len(D._cpr_setups(conn, fresh_only=True, limit=200))},
    {"key": "QUAL", "label": "Quality · pt14", "accent": "#d29922", "href": "/dash/screener",
     "cta": "names scored",
     "thesis": "Is the business worth owning — the patearn 14-pattern durability score.",
     "count": lambda conn, d, D: conn.execute("SELECT COUNT(DISTINCT symbol) c FROM pattern_scores").fetchone()["c"]},
    {"key": "LAUNCH", "label": "Launchpad", "accent": "#f0883e", "href": "/dash/screener",
     "cta": "research → live screener pending",
     "thesis": "Validated explosive-move precursors (momentum-continuation ∪ pullback-in-vol). D56 research, productizing next.",
     "count": lambda conn, d, D: None},
]


# Scoped styles for the cockpit + markets grids. Plain string (NOT an f-string) so
# the CSS braces don't need doubling. Self-contained — no edit to _BASE_CSS needed.
_CKPT_CSS = """
<style>
.ck-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:4px 0 14px;}
.ck-tile{display:block;background:#161b22;border:1px solid #30363d;border-radius:10px;padding:11px 13px;color:inherit;text-decoration:none;}
.ck-tile:hover{border-color:#484f58;}
.ck-tile .ck-n{font-size:26px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1;}
.ck-tile .ck-l{font-size:12px;font-weight:700;margin-top:5px;color:#e6edf3;}
.ck-tile .ck-c{font-size:10.5px;color:#8b949e;margin-top:2px;}
.ckpt{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:12px;align-items:start;margin-bottom:14px;}
.ck-board{margin:0;padding:12px 14px;}
.ck-h{display:flex;align-items:baseline;gap:8px;font-size:14px;font-weight:700;margin-bottom:8px;}
.ck-h .em{font-size:15px;}
table.ck-t{width:100%;border-collapse:collapse;font-size:12.5px;}
table.ck-t td{padding:5px 6px;border-bottom:1px solid #1c2128;white-space:nowrap;vertical-align:middle;}
table.ck-t tr:last-child td{border-bottom:none;}
table.ck-t td.l{text-align:left;} table.ck-t td.r{text-align:right;font-variant-numeric:tabular-nums;}
.ck-board a.more{display:inline-block;margin-top:8px;color:#58a6ff;font-size:12px;text-decoration:none;}
.ck-board a.more:hover{text-decoration:underline;}
.mkt-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:9px;margin-bottom:6px;}
</style>
"""


def _board(title_html, sub, inner_html, href, cta, accent):
    return (f'<div class="card ck-board" style="border-top:2px solid {accent}">'
            f'<div class="ck-h">{title_html}'
            f'<span class="sub" style="margin:0;font-weight:400">{sub}</span></div>'
            f'{inner_html}<a class="more" href="{href}">{cta} →</a></div>')


def render_home(sig_date, idx_date) -> str:
    """Full-bleed, registry-driven market cockpit. Reuses dashboard's instrument
    helpers so home speaks the same visual language as the screener."""
    from src.web import dashboard as D
    esc, pct, q, num = D._esc, D._pct, D._q, D._num

    nifty, breadth, lead = {}, None, None
    top_sectors, weak_sectors, top_stocks, stealth = [], [], [], []
    counts = {}
    with D.get_conn() as conn:
        if idx_date:
            r = conn.execute(
                "SELECT ret_1d_pct r1d, pct_above_200d_avg a200 FROM index_signals "
                "WHERE index_name='Nifty 50' AND trade_date=?", (idx_date,)).fetchone()
            nifty = dict(r) if r else {}
            b = conn.execute(
                "SELECT AVG(CASE WHEN pct_above_200d_avg>0 THEN 1.0 ELSE 0 END)*100 p "
                "FROM index_signals WHERE trade_date=? AND pct_above_200d_avg IS NOT NULL",
                (idx_date,)).fetchone()
            breadth = b["p"] if b and b["p"] is not None else None
            lr = conn.execute(
                "SELECT index_name FROM index_signals WHERE trade_date=? AND index_name IN "
                f"({','.join('?' for _ in D.LEADERSHIP_SET)}) "
                "ORDER BY COALESCE(ret_3m_pct,-999) DESC LIMIT 1",
                (idx_date, *D.LEADERSHIP_SET)).fetchone()
            lead = lr["index_name"] if lr else None
            sec_cols = ("index_name nm, rs_vs_broad_trend_state st, rs_vs_broad_slope_1m s1, "
                        "rs_vs_broad_slope_3m s3, rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12")
            top_sectors = [dict(x) for x in conn.execute(
                f"SELECT {sec_cols} FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL "
                f"AND index_name IN ({D._real_sectors_in()}) ORDER BY COALESCE(rs_vs_broad_slope_3m,-999) DESC LIMIT 6",
                (idx_date,)).fetchall()]
            weak_sectors = [dict(x) for x in conn.execute(
                f"SELECT {sec_cols} FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL "
                f"AND index_name IN ({D._real_sectors_in()}) ORDER BY COALESCE(rs_vs_broad_slope_3m,999) ASC LIMIT 4",
                (idx_date,)).fetchall()]
        if sig_date:
            pos_cols = ("s.symbol, s.trigger_rank rank, s.is_ath_dvpt ath, s.accum_character ch, "
                        "s.delivery_value_per_trade dvpt, s.power_dvpt_1m p1, s.power_dvpt_2m p2, "
                        "s.power_dvpt_3m p3, s.power_dvpt_6m p6, s.power_dvpt_12m p12")
            top_stocks = [dict(x) for x in conn.execute(
                f"SELECT {pos_cols}, s.price_vs_hot_avg_pct pvh FROM stock_signals s "
                f"JOIN bhavcopy_rows b USING(symbol,trade_date) WHERE s.trade_date=? "
                f"AND s.delivery_value_per_trade IS NOT NULL {D._SCAN_FILTERS} "
                f"ORDER BY COALESCE(s.is_ath_dvpt,0) DESC, COALESCE(s.p_score,-1) DESC, "
                f"COALESCE(s.r_score,-1) DESC LIMIT 7", (sig_date,)).fetchall()]
            stealth = [dict(x) for x in conn.execute(
                f"SELECT {pos_cols}, s.p_score psc, s.pct_from_52w_high pfh FROM stock_signals s "
                f"JOIN bhavcopy_rows b USING(symbol,trade_date) WHERE s.trade_date=? "
                f"AND s.accum_character='ACCUMULATION' AND s.p_score>=3 "
                f"AND COALESCE(s.trade_count_ratio_1m_6m,99)<=1.1 AND s.pct_from_52w_high<=-10 "
                f"{D._SCAN_FILTERS} ORDER BY s.p_score DESC, s.pct_from_52w_high ASC LIMIT 6",
                (sig_date,)).fetchall()]
        for e in STRATEGY_REGISTRY:
            try:
                counts[e["key"]] = e["count"](conn, sig_date, D)
            except Exception:
                counts[e["key"]] = None

    conv_rows = conviction_shortlist(limit=60) if conviction_shortlist else []
    lead_rows = leaders_laggards("leaders", limit=300) if leaders_laggards else []

    # --- regime banner ---
    a200 = nifty.get("a200")
    nifty_up = a200 is not None and a200 > 0
    if breadth is None:
        bcls, blabel = "b-neu", "NO DATA"
    elif breadth >= 60 and nifty_up:
        bcls, blabel = "b-on", "RISK-ON"
    elif breadth < 40 or not nifty_up:
        bcls, blabel = "b-off", "RISK-OFF"
    else:
        bcls, blabel = "b-neu", "NEUTRAL"
    lead_txt = {"Nifty 50": "Large-caps leading", "Nifty Midcap 150": "Mid-caps leading",
                "Nifty Smallcap 250": "Small-caps leading"}.get(lead, lead or "—")
    breadth_txt = f"{breadth:.0f}%" if breadth is not None else "—"

    search = ('<form class="search" action="/dash/stock" method="get" autocomplete="off">'
              '<input name="sym" placeholder="Enter NSE ticker — e.g. RELIANCE" '
              'autocapitalize="characters"/><button type="submit">Go</button></form>')
    banner = (f'<div class="banner {bcls}" style="font-size:15px">{blabel}'
              f'<small>· Nifty 50 {pct(nifty.get("r1d"))} today · {breadth_txt} of indices &gt; 200-DMA '
              f'· {esc(lead_txt)}</small></div>')

    # --- registry-driven count strip ---
    tiles = []
    for e in STRATEGY_REGISTRY:
        c = counts.get(e["key"])
        cval = "—" if c is None else str(c)
        tiles.append(
            f'<a class="ck-tile" href="{e["href"]}" style="border-top:3px solid {e["accent"]}" '
            f'title="{esc(e["thesis"])}"><div class="ck-n" style="color:{e["accent"]}">{cval}</div>'
            f'<div class="ck-l">{esc(e["label"])}</div><div class="ck-c">{esc(e["cta"])}</div></a>')
    count_strip = '<div class="ck-tiles">' + "".join(tiles) + '</div>'

    # --- boards (instrument language) ---
    def trig_rows(rows, score_cell=None):
        out = []
        for r in rows:
            rank = r.get("rank") or "-"
            ath = "⚡" if r.get("ath") else ""
            ladder = D._mv_ladder(r.get("dvpt"), r.get("p1"), r.get("p2"),
                                  r.get("p3"), r.get("p6"), r.get("p12"))
            extra = score_cell(r) if score_cell else f'<td><span class="pill p-{rank}">{rank}</span></td>'
            out.append(
                f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                f'<span class="sym">{ath}{esc(r["symbol"])}</span></a></td>'
                f'<td class="l">{ladder}</td>{extra}'
                f'<td class="l">{D._char_pill(r.get("ch"))}</td></tr>')
        return f'<table class="ck-t"><tbody>{"".join(out)}</tbody></table>'

    boards = []

    # Conviction — the payoff board
    if conv_rows:
        cr = ""
        for r in conv_rows[:7]:
            nk = (_near(r.get("gap_to_key_p3m")) or _near(r.get("gap_to_key_p6m"))
                  or _near(r.get("gap_to_key_p12m")))
            star = "★ " if (r.get("pt14_tier") and not r.get("pt14_dq")) else ""
            cr += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                   f'<span class="sym">{star}{esc(r["symbol"])}</span></a></td>'
                   f'<td class="l mut">{esc(r.get("primary_sector") or "—")}</td>'
                   f'<td class="r">{r.get("rs_rank") if r.get("rs_rank") is not None else "—"}</td>'
                   f'<td class="r">{"🎯" if nk else ""}</td></tr>')
        boards.append(_board('<span class="em">⭐</span> Conviction shortlist', 'all pillars aligned',
                             f'<table class="ck-t"><tbody>{cr}</tbody></table>',
                             "/dash/conviction", "See the full shortlist", "#d2a8ff"))

    # Top triggers — Positioning instrument
    if top_stocks:
        boards.append(_board('<span class="em">⚡</span> Top triggers', 'DVPT-vs-power ladder',
                             trig_rows(top_stocks), "/dash/stocks", "See all triggers", "#58a6ff"))

    # Sector rotation — RS heat strips
    if top_sectors:
        def sect_rows(rows):
            o = ""
            for r in rows:
                st = r["st"] or "—"
                o += (f'<tr><td class="l"><a class="row" href="/dash/ratio?idx={q(r["nm"])}">'
                      f'<span class="sym">{esc(r["nm"])}</span></a></td>'
                      f'<td class="l">{D._rs_strip(r["s1"], r["s3"], r["s6"], r["s12"])}</td>'
                      f'<td><span class="pill p-{st}">{st[:5]}</span></td>'
                      f'<td class="r">{pct(r["s3"])}</td></tr>')
            return o
        inner = ('<table class="ck-t"><tbody>' + sect_rows(top_sectors)
                 + '<tr><td colspan="4" class="mut" style="padding-top:8px;font-size:11px">WEAKEST</td></tr>'
                 + sect_rows(weak_sectors) + '</tbody></table>')
        boards.append(_board('<span class="em">📈</span> Sector rotation', 'RS vs Nifty 500 · 1m/3m/6m/12m',
                             inner, "/dash/sectors", "See full rotation", "#3fb950"))

    # Strong-in-strong leaders
    if lead_rows:
        lr = ""
        for r in lead_rows[:7]:
            lr += (f'<tr><td class="l"><a class="row" href="/dash/stock?sym={esc(r["symbol"])}">'
                   f'<span class="sym">{esc(r["symbol"])}</span></a></td>'
                   f'<td class="l mut">{esc(r["primary_sector"] or "—")}</td>'
                   f'<td class="r">{r["rs_rank"] if r["rs_rank"] is not None else "—"}</td></tr>')
        boards.append(_board('<span class="em">🏆</span> Strong-in-strong', 'stock + sector both leading',
                             f'<table class="ck-t"><tbody>{lr}</tbody></table>',
                             "/dash/leaders", "Leaders &amp; laggards", "#3fb950"))

    # Stealth accumulation
    if stealth:
        def stealth_score(r):
            psc = r.get("psc") or 0
            tag = "SS" if psc >= 5 else "S" if psc == 4 else "A"
            return (f'<td><span class="pill p-{tag}">{psc}/5</span></td>'
                    f'<td class="r">{pct(r.get("pfh"))}</td>')
        boards.append(_board('<span class="em">🕵</span> Stealth accumulation', 'concentrated, still off the highs',
                             trig_rows(stealth, score_cell=stealth_score),
                             "/dash/stocks", "See the full screen", "#58a6ff"))

    cockpit = '<div class="ckpt">' + "".join(boards) + '</div>'

    fresh = (f'<div class="sub" style="margin-top:6px">Stock signals <b>{sig_date or "—"}</b> · '
             f'Index signals <b>{idx_date or "—"}</b> · updated nightly 7:30 PM IST. '
             f'Every count above is a live lens — open it to screen.</div>')

    return _CKPT_CSS + search + banner + count_strip + cockpit + fresh


def render_markets(idx_date) -> str:
    """Full-bleed markets cockpit: a regime/breadth header strip, broad & sector
    index cards (RS heat), and the full sortable index bundle — same visual
    language as the screener/home (no more lean narrow page)."""
    from src.web import dashboard as D
    esc, pct, q, num = D._esc, D._pct, D._q, D._num

    allrows = {}
    breadth = nifty1d = None
    if idx_date:
        with D.get_conn() as conn:
            for r in conn.execute(
                "SELECT g.index_name nm, g.ret_1d_pct r1d, g.ret_1m_pct r1m, g.ret_3m_pct r3m, "
                "g.pct_above_200d_avg a200, g.rs_vs_broad_trend_state st, g.broad_benchmark bb, "
                "g.rs_vs_broad_slope_1m s1, g.rs_vs_broad_slope_3m s3, g.rs_vs_broad_slope_6m s6, "
                "g.rs_vs_broad_slope_12m s12, x.close_value close "
                "FROM index_signals g LEFT JOIN index_rows x USING(index_name,trade_date) "
                "WHERE g.trade_date=?", (idx_date,)).fetchall():
                allrows[r["nm"]] = dict(r)
            b = conn.execute(
                "SELECT AVG(CASE WHEN pct_above_200d_avg>0 THEN 1.0 ELSE 0 END)*100 p "
                "FROM index_signals WHERE trade_date=? AND pct_above_200d_avg IS NOT NULL",
                (idx_date,)).fetchone()
            breadth = b["p"] if b and b["p"] is not None else None
            n = allrows.get("Nifty 50")
            nifty1d = n.get("r1d") if n else None
    if not allrows:
        return '<div class="empty">No index data yet.</div>'

    sect_up = sum(1 for s in D.MAJOR_SECTORS if allrows.get(s) and (allrows[s].get("s3") or 0) > 0)
    sect_dn = sum(1 for s in D.MAJOR_SECTORS if allrows.get(s) and (allrows[s].get("s3") or 0) < 0)
    breadth_txt = f"{breadth:.0f}%" if breadth is not None else "—"

    hdr = ('<div class="ck-tiles" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">'
           f'<div class="ck-tile" style="border-top:3px solid #58a6ff"><div class="ck-n">{pct(nifty1d)}</div>'
           f'<div class="ck-l">Nifty 50 today</div></div>'
           f'<div class="ck-tile" style="border-top:3px solid #3fb950"><div class="ck-n">{breadth_txt}</div>'
           f'<div class="ck-l">indices &gt; 200-DMA</div></div>'
           f'<div class="ck-tile" style="border-top:3px solid #3fb950"><div class="ck-n" style="color:#3fb950">{sect_up}</div>'
           f'<div class="ck-l">sectors rising · 3m RS</div></div>'
           f'<div class="ck-tile" style="border-top:3px solid #f85149"><div class="ck-n" style="color:#f85149">{sect_dn}</div>'
           f'<div class="ck-l">sectors falling</div></div></div>')

    def maj_card(v):
        st = v["st"]
        chip = f' <span class="pill p-{st}">{st[:5]}</span>' if st else ''
        strip = D._rs_strip(v["s1"], v["s3"], v["s6"], v["s12"])
        return (f'<a class="maj" href="/dash/ratio?idx={q(v["nm"])}">'
                f'<div class="nm">{esc(v["nm"])}{chip}</div>'
                f'<div class="rr"><span class="mut">ABS</span><span>{num(v["close"],0)}</span>'
                f'<span>1d {pct(v["r1d"])}</span><span>1m {pct(v["r1m"])}</span>'
                f'<span>3m {pct(v["r3m"])}</span></div>'
                f'<div class="rr"><span class="grp">RS</span>{strip}'
                f'<span class="mut" style="font-size:11px">vs Nifty 500</span></div></a>')

    broad_html = "".join(maj_card(allrows[n]) for n in D.MAJOR_BROAD if n in allrows)
    sect_html = "".join(maj_card(allrows[n]) for n in D.MAJOR_SECTORS if n in allrows)

    bundle = sorted(allrows.values(), key=lambda v: (v["r3m"] is None, -(v["r3m"] or 0)))
    brows = []
    for v in bundle:
        grp = "broad" if v["bb"] is None else "sector"
        st = v["st"] or ""
        chip = (f'<span class="pill p-{st}">{st[:5]}</span>' if st else '<span class="mut">—</span>')
        brows.append(
            f'<tr data-grp="{grp}"><td class="sym">{esc(v["nm"])}</td>'
            f'<td class="num">{pct(v["r1d"])}</td><td class="num">{pct(v["r1m"])}</td>'
            f'<td class="num">{pct(v["r3m"])}</td>'
            f'<td>{D._rs_strip(v["s1"], v["s3"], v["s6"], v["s12"])}</td>'
            f'<td>{chip}</td></tr>')
    js = ("<script>function mflt(g,el){document.querySelectorAll('#mbundle tr[data-grp]').forEach("
          "function(r){r.style.display=(g==='all'||r.dataset.grp===g)?'':'none';});"
          "document.querySelectorAll('#mbar .fbtn').forEach(function(b){b.classList.remove('on');});"
          "el.classList.add('on');}</script>")

    return (_CKPT_CSS
            + '<h2 style="margin-top:2px">Markets <span class="sub" style="margin:0">regime · indexes · sectors</span></h2>'
            + hdr
            + '<div class="sub" style="margin-top:2px">Tap any card → its ratio chart &amp; constituents. '
              '<a class="row" style="display:inline" href="/dash/compare?idx=Nifty+50&idx=Nifty+500">⇄ Compare indices</a></div>'
            + '<div class="ghdr">Broad / size</div>'
            + f'<div class="mkt-grid">{broad_html}</div>'
            + '<div class="ghdr">Core sectors</div>'
            + f'<div class="mkt-grid">{sect_html}</div>'
            + '<h2>Full index bundle <span class="sub" style="margin:0">RS heat per index · sortable</span></h2>'
            + '<div id="mbar" class="fbar">'
              "<button class=\"fbtn on\" onclick=\"mflt('all',this)\">All</button>"
              "<button class=\"fbtn\" onclick=\"mflt('broad',this)\">Broad/Size</button>"
              "<button class=\"fbtn\" onclick=\"mflt('sector',this)\">Sectoral</button></div>"
            + '<div class="card" style="padding:6px 10px"><table id="mbundle" class="dt" style="font-size:12.5px">'
              '<thead><tr><th class="l">Index</th><th class="num">1d</th><th class="num">1m</th>'
              '<th class="num">3m</th><th class="l">RS 1m/3m/6m/12m</th><th>Trend</th></tr></thead>'
            + f'<tbody>{"".join(brows)}</tbody></table></div>' + js)
