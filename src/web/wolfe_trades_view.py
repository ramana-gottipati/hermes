"""/dash/wolfe/trades — the Wolfe "Open trades — remaining ROI" filterable view.

A NEW additive surface (docs/wolfe-open-trades-PLAN.md, 2026-07-12). The fresh
scanner (/dash/wolfe/scan) is age-capped at ≤15 bars, so it shows only the just-
printed calls. This view surfaces EVERY OPEN winner-profile trade — point 5 printed,
EPA (1-4) target not yet reached, ANY age — ranked by REMAINING ROI from the current
price (run% / risk% / R:R), with 9 top-of-page filters that the persist/script honor
too (filtering is a server-side WHERE over the nightly snapshot, never front-end only).

Descriptive-only. Wolfe carries no buy/sell signal. The validated +edge is measured on
FRESH ≤15d winner-profile entries; older open trades have run left but no validated
entry-edge → they are BADGED ("open · judge the run"), never hidden. Q = structural
strength; ✓edge = the tradeable filter — they differ on purpose.

Additive: this module never touches detection, §A geometry, §B scoring, winner_scan,
the crossing rule, or point-4. Its router is included onto wolfe_view's already-mounted
router (durable-include pattern) so it needs no v2_surfaces / lens_registry edit.
"""
from __future__ import annotations

import csv
import hashlib
import io
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.core.db import get_conn
from src.automation import wolfe

# STICKY FILTERS (Ramana 2026-07-13): "I dive into a result, do a study, and return —
# the filters I set are gone." The analyst's filtered shortlist must survive navigating
# away (to a wave chart) and back. We remember the active filter+sort set in a cookie; a
# bare return visit to the view restores it (redirect to the saved querystring). Same
# client-cookie, no-server-state pattern as D110's "since you last looked".
_FILTER_COOKIE = "wolfe_open_filters"
# per-param default/empty values that count as "not set" (so we only remember real filters)
_STATE_DEFAULTS = {"universe": ("nifty500",), "size": ("", "all"), "sector": ("", "all"),
                   "dir": ("", "all"), "maxage": ("", "all"), "minq": ("", "any"),
                   "minroom": ("", "any"), "status": ("", "all"), "minliq": ("", "any"),
                   "minrr": ("", "any"), "minprox": ("", "any"), "minrs": ("", "any"),
                   "sort": ("", "run")}


def _active_state(params):
    """The subset of filter/sort params that differ from their defaults (the state worth
    remembering / that means 'the user has filtered')."""
    return {k: v for k, v in params.items() if v and v not in _STATE_DEFAULTS.get(k, ())}


def _sticky(resp, active, clear):
    """Set (or clear) the remembered-filters cookie on the outgoing response."""
    if clear:
        resp.delete_cookie(_FILTER_COOKIE, path="/dash/wolfe/trades")
    elif active:
        resp.set_cookie(_FILTER_COOKIE, urlencode(active), max_age=2592000,   # 30 days
                        path="/dash/wolfe/trades", samesite="lax", httponly=True)
    return resp

try:
    from src.web.dashboard import _shell, _esc, _q
except Exception:  # pragma: no cover
    from urllib.parse import quote_plus

    def _esc(s):
        return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _q(s):
        return quote_plus(str(s) if s is not None else "")

    def _shell(title, body, active, latest_date="", wide=False):
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>{title}</title></head><body>{body}</body></html>")

router = APIRouter()

_UP, _DN = "var(--up)", "var(--down)"

# (value, label) option lists for the 9 filter dropdowns. `value` = the query param.
_SIZE_OPTS = [("all", "All sizes"), ("N50", "Nifty 50"), ("Next50", "Next 50"),
              ("Mid150", "Midcap 150"), ("Small250", "Smallcap 250"),
              ("Micro250", "Microcap 250")]
_DIR_OPTS = [("all", "Both sides"), ("bull", "Bull only"), ("bear", "Bear only")]
_AGE_OPTS = [("all", "Any age"), ("15", "≤ 15d (✓ validated)"), ("30", "≤ 30d"),
             ("60", "≤ 60d"), ("120", "≤ 120d")]
_Q_OPTS = [("any", "Any strength"), ("15", "Q ≥ 15"), ("18", "Q ≥ 18"),
           ("21", "Q ≥ 21"), ("top20", "Top 20 only")]
_ROOM_OPTS = [("any", "Any room"), ("10", "≥ 10% left"), ("20", "≥ 20%"),
              ("30", "≥ 30%"), ("50", "≥ 50%")]
_STATUS_OPTS = [("all", "In zone + watching"), ("in", "Actionable now (in zone)"),
                ("watch", "Watching")]
_LIQ_OPTS = [("any", "Any liquidity"), ("1", "≥ ₹1 cr traded"), ("5", "≥ ₹5 cr"),
             ("25", "≥ ₹25 cr"), ("100", "≥ ₹100 cr")]
_RR_OPTS = [("any", "Any R:R"), ("1.5", "R:R ≥ 1.5"), ("2", "R:R ≥ 2"), ("3", "R:R ≥ 3")]
_PROX_OPTS = [("any", "Any distance"), ("2", "≤ 2% from zone"), ("5", "≤ 5%"), ("10", "≤ 10%")]

_FILTER_KEYS = ("size", "sector", "dir", "maxage", "minq", "minroom",
                "status", "minliq", "minrr")


def wolfe_view_toggle(active):
    """The Fresh setups ⇄ Open trades switch shown at the top of BOTH Wolfe views.
    They live under ONE 'Patterns · Wolfe' nav tab (Ramana 2026-07-13) — this segmented
    control is the mode switch between them. `active` = 'fresh' | 'open'."""
    def _it(key, href, label, sub):
        on = " on" if active == key else ""
        return (f'<a class="wtg{on}" href="{href}"><b>{label}</b>'
                f'<span>{_esc(sub)}</span></a>')
    return (
        '<div class="wtgbar" role="tablist">'
        + _it("fresh", "/dash/wolfe/scan", "Fresh setups", "≤15d · validated edge")
        + _it("open", "/dash/wolfe/trades", "Open trades", "any age · remaining ROI, filterable")
        + '</div>'
        '<style>.wtgbar{display:inline-flex;gap:3px;background:#0e141c;border:1px solid #1c2937;'
        'border-radius:11px;padding:3px;margin:4px 0 12px}.wtg{display:flex;flex-direction:column;'
        'gap:1px;padding:6px 15px;border-radius:8px;text-decoration:none;color:#9bb0c6;line-height:1.25}'
        '.wtg b{font-size:13.5px;font-weight:600}.wtg span{font-size:10.5px;color:#5f7488;letter-spacing:.02em}'
        '.wtg:hover{color:#eaf1f9}.wtg.on{background:#1c2937;color:#eaf1f9}'
        '.wtg.on span{color:#8ba3ba}</style>')


def _sector_opts(conn):
    """Sector dropdown = the live company_tags vocabulary (multi-label, approved)."""
    opts = [("all", "All sectors")]
    try:
        for tag, c in conn.execute(
                "SELECT tag, COUNT(DISTINCT symbol) c FROM company_tags "
                "WHERE approved=1 GROUP BY tag ORDER BY tag").fetchall():
            opts.append((tag, f"{tag} ({c})"))
    except Exception:
        pass
    return opts


def _sel(name, opts, cur, extra=""):
    """A GET <select> that auto-submits its form on change."""
    cur = (cur or opts[0][0])
    body = "".join(
        f'<option value="{_esc(v)}"{" selected" if str(v) == str(cur) else ""}>{_esc(lbl)}</option>'
        for v, lbl in opts)
    return (f'<label class="wtf"><span>{_esc(extra)}</span>'
            f'<select name="{name}" onchange="this.form.submit()">{body}</select></label>')


def _qs(params, **override):
    """Build a querystring from the current filter params + overrides (for sort/cross links)."""
    p = dict(params)
    p.update(override)
    keep = [(k, v) for k, v in p.items() if v not in (None, "")]
    return "&amp;".join(f"{k}={_q(v)}" for k, v in keep)


def _num(v):
    return f"{v:,.1f}" if (isinstance(v, (int, float)) and abs(v) >= 100) else (
        f"{v:.2f}" if isinstance(v, (int, float)) else "—")


def _liq_cell(r):
    tv, dp = r.get("tv_cr"), r.get("deliv_pct")
    if tv is None:
        return '<span style="color:var(--ink-3)" title="no liquidity data">—</span>'
    thin = tv < 5.0                                    # the systematized TIRUPATIFL lesson
    col = "var(--down)" if thin else "var(--ink-2)"
    dps = f' · {dp:.0f}%del' if dp is not None else ""
    warn = ' ⚠' if thin else ""
    return (f'<span style="color:{col}" title="traded value today (₹ crore) · delivery %'
            f'{" — thin/illiquid, gap-prone" if thin else ""}">₹{tv:,.1f} cr{dps}{warn}</span>')


def _status_word(r):
    if r.get("invalid"):
        return "below_stop"
    return "in_zone" if r.get("in_zone") else "watch"


# ── growth helpers (backlog #4-#12) — all descriptive, all from fields on the row ──
_MIN_RS_OPTS = [("any", "Any RS"), ("50", "RS ≥ 50"), ("70", "RS ≥ 70"), ("85", "RS ≥ 85 (leaders)")]
_SEEN_COOKIE = "wolfe_open_seen"


def _run_t1(r):
    """#4 conservative run% — to T1 (the 0.618∩0.618 near target), not the far EPA."""
    cmp_, t1 = r.get("cmp"), r.get("t1")
    if not cmp_ or not t1:
        return None
    return round(((t1 - cmp_) if r["dir"] == "BULL" else (cmp_ - t1)) / cmp_ * 100, 1)


def _age_mute(age):
    """#5 the EPA extrapolates further (less trustworthy) the older the wave — return a
    (css, prefix) that progressively mutes the EPA/run cells."""
    if age is None or age <= 30:
        return "", ""
    if age <= 90:
        return "color:var(--ink-2);", ""
    return "color:var(--ink-3);", "~"          # far past formation → muted + a '~'


def _risk_cell(r):
    """#6 risk% with ATR context + a razor-stop flag (stop tighter than ~0.8 normal days)."""
    risk, atr = r.get("risk"), r.get("atr_pct")
    if risk is None:
        return '<span style="color:var(--ink-3)">—</span>'
    base = f'{risk:.1f}%'
    if atr and atr > 0 and risk > 0:
        x = risk / atr
        extra = (f' · {x:.1f}×ATR' + (' <span style="color:#d29922" title="stop is inside ~one '
                 'normal day\'s range — easily whipsawed">⚠ razor</span>' if x < 0.8 else ''))
        return f'{base}<span style="color:var(--ink-3);font-size:11px">{extra}</span>'
    return base


def _comp_title(r):
    """#7 the §B component breakdown as a hover string (parity with the fresh scanner)."""
    c = r.get("comp") or {}
    if not c:
        return "§B breakdown unavailable"
    return ("§B  A(pt-1 fractal)=%s · B(pts 2/3/4)=%s · C(pt-5)=%s · F(zone)=%s · "
            "G(extension)=%s · H(EPA touch)=%s · I(RSI div)=%s · D(upside)=%s"
            % tuple(c.get(k, 0) for k in ("p1", "B", "C", "F", "G", "H", "I", "D")))


def _rs_cell(r):
    """#8 RS rank + a with-trend / counter-trend label (leaders vs laggards)."""
    rs = r.get("rs")
    if not isinstance(rs, (int, float)):
        return '<span style="color:var(--ink-3)">—</span>'
    bull = r["dir"] == "BULL"
    tag, col = "", "var(--ink-2)"
    if bull:
        if rs >= 60:
            tag, col = "leader", "var(--up)"
        elif rs <= 40:
            tag, col = "counter-trend", "#d29922"
    else:
        if rs <= 40:
            tag, col = "weak (with trend)", "var(--up)"
        elif rs >= 60:
            tag, col = "counter-trend", "#d29922"
    lab = (f'<br><span style="font-size:10px;color:{col}">{tag}</span>' if tag else '')
    return f'<span style="color:{col}">{rs:.0f}</span>{lab}'


def _ladder(r):
    """#11 a compact inline SVG: SL · zone band · CMP (colored by status) · T1 · EPA on a
    normalized price axis — the trade's shape at a glance."""
    cmp_, sl, zlo, zhi, t1, epa = (r.get(k) for k in ("cmp", "sl", "zlo", "zhi", "t1", "epa"))
    pts = [x for x in (sl, zlo, zhi, cmp_, t1, epa) if x is not None]
    if cmp_ is None or len(pts) < 2:
        return '<span style="color:var(--ink-3)">—</span>'
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1.0
    W, H = 118, 16

    def X(v):
        return 3 + (v - lo) / rng * (W - 6)
    S = [f'<svg width="{W}" height="{H}" style="vertical-align:middle" '
         f'aria-label="stop {sl} · zone {zlo}-{zhi} · CMP {cmp_} · T1 {t1} · EPA {epa}">']
    if zlo is not None and zhi is not None:
        x0, x1 = X(min(zlo, zhi)), X(max(zlo, zhi))
        S.append(f'<rect x="{x0:.0f}" y="3" width="{max(2, x1 - x0):.0f}" height="{H - 6}" fill="#1f6feb" opacity="0.35"/>')
    S.append(f'<line x1="3" y1="{H // 2}" x2="{W - 3}" y2="{H // 2}" stroke="#30363d"/>')
    if sl is not None:
        S.append(f'<line x1="{X(sl):.0f}" y1="2" x2="{X(sl):.0f}" y2="{H - 2}" stroke="#ff6a7a" stroke-width="1.5"/>')
    if epa is not None:
        S.append(f'<line x1="{X(epa):.0f}" y1="2" x2="{X(epa):.0f}" y2="{H - 2}" stroke="#3fb950" stroke-width="1.5"/>')
    if t1 is not None:
        S.append(f'<line x1="{X(t1):.0f}" y1="3.5" x2="{X(t1):.0f}" y2="{H - 3.5}" stroke="#d29922"/>')
    col = "#3fd486" if r.get("in_zone") else "#ff6a7a" if r.get("invalid") else "#c9d1d9"
    S.append(f'<circle cx="{X(cmp_):.0f}" cy="{H // 2}" r="3" fill="{col}" stroke="#0d1117"/>')
    S.append('</svg>')
    return "".join(S)


def _statuskey(r):
    return "X" if r.get("invalid") else ("I" if r.get("in_zone") else "W")


def _parse_seen(cookie):
    d = {}
    for part in (cookie or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            d[k] = v
    return d


def _seen_key(r):
    """A short, STABLE token for a wave (sym+p5date). Hashed so the #12 cookie stays well
    under the ~4KB browser limit even at the row cap (a raw 'sym|p5date' fingerprint over
    ~170+ rows crossed 4KB and browsers then silently dropped the whole cookie, turning the
    diff off exactly when the list was largest — review finding, 2026-07-13). 8 hex chars →
    ~11 B/row → 200 rows ≈ 2.2KB. Collision prob at 200 rows ≈ 5e-6 → at worst a missed
    badge, never wrong data."""
    return hashlib.blake2s(f'{r.get("sym","")}|{r.get("p5date","")}'.encode(), digest_size=4).hexdigest()


def _seen_str(rows):
    """Compact fingerprint of the ranked set for the 'what changed' diff (cap 200)."""
    return ";".join(f'{_seen_key(r)}={_statuskey(r)}' for r in rows[:200])


def _staleness_banner(scan_date, latest_data):
    """#10 warn when the ranked snapshot lags the latest available data (nightly missed)."""
    if not scan_date or not latest_data or str(scan_date) >= str(latest_data):
        return ""
    return (f'<div class="wtstale">⚠ Snapshot is stale — ranked as-of <b>{_esc(scan_date)}</b>, but the '
            f'latest data is <b>{_esc(latest_data)}</b>. The nightly <code>--persist-open</code> run may '
            'have missed; prices, status and run% may be out of date.</div>')


def _breadth(rows):
    """#9 a compute-on-read concentration read of the CURRENTLY FILTERED set — direction
    split, size mix, top sectors, and the median trade — so crowding is visible."""
    from collections import Counter
    if not rows:
        return ""
    nb = sum(1 for r in rows if r["dir"] == "BULL")
    ne = len(rows) - nb
    sizes = Counter(r.get("size") or "—" for r in rows)
    tags = Counter(t for r in rows for t in (r.get("tags") or []))

    def _med(key):
        vals = sorted(r[key] for r in rows if r.get(key) is not None)
        return vals[len(vals) // 2] if vals else None
    top_sec = " · ".join(f"{_esc(t)} ×{c}" for t, c in tags.most_common(3))
    size_mix = " · ".join(f"{_esc(k)} {v}" for k, v in sizes.most_common())
    mr, mrisk, mrr = _med("run"), _med("risk"), _med("rr")
    parts = [f'<b style="color:var(--up)">{nb}</b> bull · <b style="color:var(--down)">{ne}</b> bear']
    if size_mix:
        parts.append("sizes: " + size_mix)
    if top_sec:
        parts.append("top sectors: " + top_sec)
    if mr is not None:
        med = f"median run {mr:+.0f}%"
        if mrisk is not None:
            med += f" · risk {mrisk:.0f}%"
        if mrr is not None:
            med += f" · R:R {mrr:.1f}"
        parts.append(med)
    return '<div class="wtbreadth">' + ' &nbsp;|&nbsp; '.join(parts) + '</div>'


def _whatsnew_badge(r):
    """#12 what-changed-since-you-last-looked badge (set by the diff in the handler)."""
    if r.get("_new"):
        return ('<br><span style="background:#1f6feb;color:#fff;font-size:9px;padding:0 4px;'
                'border-radius:3px" title="new to the ranked list since you last looked">NEW</span>')
    if r.get("_flip"):
        now = _statuskey(r)
        if now == "I":
            return '<br><span style="color:var(--up);font-size:10px" title="entered the entry zone since you last looked">→ in zone</span>'
        if now == "X":
            return '<br><span style="color:var(--down);font-size:10px" title="fell below the stop since you last looked">→ stopped</span>'
        return '<br><span style="color:var(--ink-3);font-size:10px" title="left the entry zone since you last looked">→ watch</span>'
    return ''


def _csv_response(rows, scan_date):
    """Server-side CSV of the filtered + sorted rows (the plain, flat, analyst-friendly
    shape). Honors the exact same filter/sort the page shows — a download, not a signal."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["symbol", "direction", "sector_tags", "size", "cmp", "zone_low",
                "zone_high", "stop", "t1", "epa", "run_pct", "run_t1_pct", "risk_pct",
                "atr_pct", "rr", "q", "rs", "gap_to_zone_pct", "traded_cr", "delivery_pct",
                "age_bars", "setup_p5_date", "status", "edge", "as_of"])
    for r in rows:
        edge = "edge" if (r.get("age") is not None and r["age"] <= 15) else "open"
        rt1 = _run_t1(r)
        w.writerow([
            r.get("sym"), r.get("dir"), "|".join(r.get("tags") or []), r.get("size") or "",
            r.get("cmp"), r.get("zlo"), r.get("zhi"), r.get("sl"), r.get("t1") or "",
            r.get("epa"), r.get("run"), (rt1 if rt1 is not None else ""), r.get("risk"),
            (r.get("atr_pct") if r.get("atr_pct") is not None else ""),
            (r.get("rr") if r.get("rr") is not None else ""), r.get("Q"),
            (r.get("rs") if r.get("rs") is not None else ""), wolfe.zone_gap_pct(r),
            (r.get("tv_cr") if r.get("tv_cr") is not None else ""),
            (r.get("deliv_pct") if r.get("deliv_pct") is not None else ""),
            r.get("age"), r.get("p5date") or "", _status_word(r), edge, scan_date])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="wolfe-open-trades.csv"'})


# Standout-pick guards (panel wf_dd906a08): the headline must be a TRADEABLE
# representative, not a near-zero-risk / thin-stock outlier.
_STANDOUT_MIN_RISK = 2.0        # risk% floor — R:R is denominator noise below this
_STANDOUT_MIN_LIQ = 5.0         # ₹cr traded — the thin-stock (TIRUPATIFL) lesson


def _rr_disp(rr):
    """Display R:R, capped at the sane ceiling (">10" above it — an honest reward:risk
    above ~10 is almost always a stop-too-tight artifact)."""
    if rr is None:
        return "—"
    return f"&gt;{wolfe._RR_DISPLAY_CAP:.0f}" if rr > wolfe._RR_DISPLAY_CAP else f"{rr:.2f}"


def _bottom_line(rows, total_open, held_out=0):
    """Bottom-line-FIRST band (readability doctrine): surface the answer — how many are
    actionable + the standout trades by R:R and by room — before the analyst scans the
    table. Standout picks are GUARDED (min risk% floor + min liquidity) so the headline
    is a tradeable representative, not a razor-stop or microcap outlier (panel
    wf_dd906a08). Computed over the CURRENTLY FILTERED set."""
    n = len(rows)
    hnote = (f' <span style="color:var(--ink-3)">({held_out} older/out-of-domain waves held out '
             'of the ranked view — their 1-4 target extrapolates too far past formation to '
             'compare to today\'s price; still detected + drawn on each stock\'s chart)</span>') if held_out else ''
    if not n:
        return ('<div class="wtbl"><b>Bottom line:</b> no open trades match these filters '
                f'— of {total_open} ranked open, none pass. Loosen a dropdown.{hnote}</div>')
    n_act = sum(1 for r in rows if r.get("in_zone") and not r.get("invalid"))
    n_edge = sum(1 for r in rows if (r.get("age") is not None and r["age"] <= 15))
    n_blown = sum(1 for r in rows if r.get("invalid"))
    # eligible standouts: not blown, liquid enough (the thin-stock lesson)
    elig = [r for r in rows if not r.get("invalid") and (r.get("tv_cr") or 0) >= _STANDOUT_MIN_LIQ]
    rr_cands = [r for r in elig if r.get("rr") is not None and (r.get("risk") or 0) >= _STANDOUT_MIN_RISK]
    best_rr = max(rr_cands, key=lambda r: r["rr"]) if rr_cands else None
    room_cands = [r for r in elig if r.get("run") is not None]
    most_room = max(room_cands, key=lambda r: r["run"]) if room_cands else None

    def _name(r, extra):
        col = _UP if r["dir"] == "BULL" else _DN
        return (f'<a href="/dash/wolfe?sym={_q(r["sym"])}&p5={_q(r.get("p5date") or "")}&p4={_q(r.get("p4date") or "")}" '
                f'style="color:{col};font-weight:600;text-decoration:none">{_esc(r["sym"])}</a> {extra}')
    parts = [f'<b>Bottom line:</b> <b>{n}</b> ranked open trade{"s" if n != 1 else ""} '
             f'{"match these filters" if n != total_open else "in view"} — '
             f'<b style="color:var(--up)">{n_act}</b> actionable now, {n_edge} fresh (★edge)'
             + (f', {n_blown} below stop (shown last)' if n_blown else '') + '.']
    if best_rr:
        parts.append('Best risk-adjusted: ' + _name(best_rr,
                     f'<span style="color:var(--ink-2)">R:R {_rr_disp(best_rr["rr"])}, {best_rr["run"]:+.0f}% room</span>') + '.')
    if most_room and (not best_rr or most_room["sym"] != best_rr["sym"]):
        parts.append('Most room left: ' + _name(most_room,
                     f'<span style="color:var(--ink-2)">{most_room["run"]:+.0f}%, R:R {_rr_disp(most_room.get("rr"))}</span>') + '.')
    return '<div class="wtbl">' + " ".join(parts) + hnote + '</div>'


@router.get("/dash/wolfe/trades", response_class=HTMLResponse)
def wolfe_trades(request: Request,
                 universe: str = Query("nifty500", max_length=24),
                 size: str = Query("", max_length=12),
                 sector: str = Query("", max_length=40),
                 dir: str = Query("", max_length=8),
                 maxage: str = Query("", max_length=6),
                 minq: str = Query("", max_length=8),
                 minroom: str = Query("", max_length=6),
                 status: str = Query("", max_length=8),
                 minliq: str = Query("", max_length=8),
                 minrr: str = Query("", max_length=6),
                 minprox: str = Query("", max_length=6),
                 minrs: str = Query("", max_length=6),
                 sort: str = Query("run", max_length=6),
                 format: str = Query("", max_length=6),
                 clear: int = Query(0, ge=0, le=1)):
    """Open winner-profile trades, ranked by remaining ROI, with 9 server-side filters.
    Reads the nightly wolfe_open_signals snapshot (instant); a live open_scan over the
    universe is minutes-long, so when the snapshot is absent we show a build notice."""
    uni = universe or "nifty500"
    params = {"universe": uni, "size": size, "sector": sector, "dir": dir,
              "maxage": maxage, "minq": minq, "minroom": minroom, "status": status,
              "minliq": minliq, "minrr": minrr, "minprox": minprox, "minrs": minrs, "sort": sort}
    active = _active_state(params)
    # STICKY FILTERS: a bare return visit (no filter params) restores the last-used set
    # so the analyst comes back to their shortlist, not the full list. The redirected
    # request carries the params → renders normally (no loop). `clear=1` skips this.
    if not active and not clear and format.lower() != "csv":
        saved = request.cookies.get(_FILTER_COOKIE)
        if saved:
            return RedirectResponse(f"/dash/wolfe/trades?{saved}", status_code=307)
    with get_conn() as conn:
        snap = wolfe.latest_open_scan(conn, universe=uni)
        sector_opts = _sector_opts(conn)
        latest_data = wolfe._scan_as_of(conn)   # #10 for the staleness check

    if not snap:
        note = ('<h2>Wolfe <span style="color:var(--ink-2);font-size:15px;font-weight:400">— open trades, remaining ROI</span></h2>'
                + wolfe_view_toggle("open") +
                '<div class="sub" style="margin:10px 0">The nightly open-trades snapshot '
                'has not been built yet for this universe. It rides the '
                '<code>hermes-wolfe-scan</code> timer (<code>python -m src.automation.wolfe '
                '--persist-open</code>) — check back after the next nightly run, or open the '
                '<a href="/dash/wolfe/scan" style="color:#58a6ff">fresh winner-profile scanner ›</a> '
                'in the meantime.</div>')
        return _sticky(HTMLResponse(_shell("Open trades — Wolfe", note, "wolfe", wide=True)), active, clear)

    all_rows = snap["rows"]
    total_open = len(all_rows)
    # #12 "what changed since you last looked" — diff the FULL ranked set vs the seen-cookie
    # (over all_rows so filtering never fabricates 'new'). First-ever visit marks nothing.
    _prior = _parse_seen(request.cookies.get(_SEEN_COOKIE))
    for _r in all_rows:
        _was = _prior.get(_seen_key(_r))
        _r["_new"] = bool(_prior) and _was is None
        _r["_flip"] = _was is not None and _was != _statuskey(_r)
    rows = wolfe.filter_open_rows(
        all_rows, size=size, sector=sector, direction=dir, maxage=maxage,
        minq=minq, minroom=minroom, status=status, minliq=minliq, minrr=minrr,
        minprox=minprox, minrs=minrs)
    rows = wolfe.sort_open_rows(rows, sort)

    # CSV export — the SAME filtered + sorted rows drive the download (the plan's
    # "same params drive the view, the sort, AND any export"). Server-side, honest.
    if format.lower() == "csv":
        return _csv_response(rows, snap.get("scan_date") or "")

    nin = sum(1 for r in rows if r.get("in_zone") and not r.get("invalid"))  # actionable = in zone, not blown

    # ── filter bar (one GET form; each select auto-submits) ──────────────────
    fbar = (
        f'<form method="get" action="/dash/wolfe/trades" class="wtbar">'
        f'<input type="hidden" name="universe" value="{_esc(uni)}"/>'
        f'<input type="hidden" name="sort" value="{_esc(sort)}"/>'
        + _sel("size", _SIZE_OPTS, size, "Size")
        + _sel("sector", sector_opts, sector, "Sector")
        + _sel("dir", _DIR_OPTS, dir, "Direction")
        + _sel("maxage", _AGE_OPTS, maxage, "Max age")
        + _sel("minq", _Q_OPTS, minq, "Strength")
        + _sel("minroom", _ROOM_OPTS, minroom, "Room to EPA")
        + _sel("status", _STATUS_OPTS, status, "Status")
        + _sel("minliq", _LIQ_OPTS, minliq, "Min liquidity")
        + _sel("minrr", _RR_OPTS, minrr, "Min R:R")
        + _sel("minprox", _PROX_OPTS, minprox, "Distance to zone")
        + _sel("minrs", _MIN_RS_OPTS, minrs, "Min RS")
        + f'<a class="wtclear" href="/dash/wolfe/trades?universe={_q(uni)}&amp;clear=1" '
          'title="clear all filters + forget them">clear</a>'
        + '</form>')

    # ── sort links (carry the current filters) ───────────────────────────────
    def _slink(key, label):
        on = ' style="color:#eaf1f9;font-weight:600"' if sort == key else ' style="color:#58a6ff"'
        return f'<a href="/dash/wolfe/trades?{_qs(params, sort=key)}"{on}>{label}</a>'
    sortbar = ('<b>Sort:</b> ' + _slink("run", "most room (run%)") + ' · '
               + _slink("rr", "best R:R") + ' · ' + _slink("q", "strongest (Q)")
               + ' · ' + _slink("age", "freshest"))

    # ── rows ─────────────────────────────────────────────────────────────────
    trs = []
    for r in rows:
        bull = r["dir"] == "BULL"
        col = _UP if bull else _DN
        edge = (r.get("age") is not None and r["age"] <= 15)
        badge = ('<span style="background:#1f6feb;color:#fff;font-size:10px;padding:0 5px;'
                 'border-radius:4px" title="fresh ≤15d — the OOS-validated winner-profile entry-edge">★ edge</span>'
                 if edge else
                 '<span style="color:var(--ink-3);font-size:10.5px" title="older open trade — run '
                 'still left, but no validated entry-edge; judge the run">open</span>')
        if r.get("invalid"):
            status_cell = '<span style="color:var(--down)" title="price has fallen through the stop — setup broken">✗ stop</span>'
        elif r.get("in_zone"):
            status_cell = '<span style="color:var(--up);font-weight:700" title="price in the entry zone now">● IN</span>'
        else:
            gap = wolfe.zone_gap_pct(r)
            if gap >= 0:      # ran past the entry — working, wait for a pullback/bounce
                status_cell = (f'<span style="color:var(--ink-3)" title="price ran past the entry zone '
                               f'({"above" if bull else "below"} it) — the setup is working; wait for a '
                               f'pullback to enter">watch · +{gap:.1f}% to zone</span>')
            else:             # on the stop side of the zone — drifting toward the stop
                status_cell = (f'<span style="color:#d29922" title="price is on the stop side of the entry '
                               f'zone, drifting toward the stop — deteriorating">watch · {gap:.1f}% (toward stop)</span>')
        tags = ", ".join(r.get("tags") or []) or (r.get("psector") or "—")
        tags_short = tags if len(tags) <= 26 else tags[:24] + "…"
        rr = r.get("rr")
        rr_s = (f'<b style="color:{col}" title="reward:risk if you enter now (capped display &gt;{wolfe._RR_DISPLAY_CAP:.0f})">{_rr_disp(rr)}</b>' if rr is not None
                else '<span style="color:var(--ink-3)">—</span>')
        # #5 the EPA extrapolates further (less trustworthy) the older the wave → mute it,
        # and #4 show the conservative run→T1 beside the aggressive run→EPA.
        emute_css, emute_pre = _age_mute(r.get("age"))
        if r.get("run") is not None:
            rt1 = _run_t1(r)
            t1sub = (f'<br><span style="color:var(--ink-3);font-size:10.5px" '
                     f'title="conservative run — to T1 (the near 0.618∩0.618 target), a realistic floor '
                     f'vs the far EPA">T1 {rt1:+.0f}%</span>' if rt1 is not None else '')
            run_s = (f'<span style="{emute_css or ("color:%s;" % _UP)}font-weight:600" '
                     f'title="run to the EPA target from CMP'
                     f'{" — extrapolated far past formation; treat as directional, not precise" if emute_pre else ""}">'
                     f'{emute_pre}{r["run"]:+.1f}%</span>{t1sub}')
        else:
            run_s = '<span style="color:var(--ink-3)">—</span>'
        epa_s = f'<span style="{emute_css or "color:var(--up);"}">{emute_pre}{_num(r["epa"])}</span>'
        dim = ' opacity:0.6;' if r.get("invalid") else ''
        # the wave URL — shared by the whole-row click AND the symbol anchor (so the
        # symbol supports Ctrl/middle-click "open in a new tab"). stopPropagation keeps a
        # plain click on the anchor from ALSO firing the row's onclick.
        wave_href = (f'/dash/wolfe?sym={_q(r["sym"])}&p5={_q(r.get("p5date") or "")}'
                     f'&p4={_q(r.get("p4date") or "")}')
        trs.append(
            # _q percent-encodes the symbol → safe inside the single-quoted JS string.
            f'<tr class="wtrow" onclick="location.href=\'{wave_href}\'" '
            f'style="cursor:pointer;border-top:1px solid var(--line-2);{dim}">'
            f'<td style="padding:6px 10px"><a href="{wave_href}" onclick="event.stopPropagation()" '
            f'style="color:{col};font-weight:700;text-decoration:none" '
            f'title="draw this exact wave — Ctrl/middle-click to open in a new tab">{_esc(r["sym"])}</a></td>'
            f'<td style="color:{col};font-weight:600">{r["dir"]}</td>'
            f'<td style="color:var(--ink-2)" title="{_esc(tags)}">{_esc(tags_short)}</td>'
            f'<td style="color:var(--ink-3)">{_esc(r.get("size") or "—")}</td>'
            f'<td>{_liq_cell(r)}</td>'
            f'<td>{status_cell}</td>'
            f'<td title="stop · entry zone · CMP · T1 · EPA at a glance">{_ladder(r)}</td>'
            f'<td>{_num(r["cmp"])}</td>'
            f'<td style="color:var(--ink-2)">{_num(r["zlo"])}–{_num(r["zhi"])}</td>'
            f'<td style="color:var(--down)">{_num(r["sl"])}</td>'
            f'<td>{_num(r["t1"]) if r.get("t1") else "—"}</td>'
            f'<td>{epa_s}</td>'
            f'<td style="white-space:nowrap">{run_s}</td>'
            f'<td style="color:var(--ink-2);white-space:nowrap">{_risk_cell(r)}</td>'
            f'<td style="text-align:center">{rr_s}</td>'
            f'<td style="text-align:center" title="{_esc(_comp_title(r))}"><b style="color:{col}">{_num_q(r.get("Q"))}</b></td>'
            f'<td style="text-align:center">{_rs_cell(r)}</td>'
            f'<td style="color:var(--ink-3);white-space:nowrap" title="point-5 (setup) date · click the row to draw this exact wave">{r.get("age")}d '
            f'<span style="font-size:11px;color:var(--ink-2)">{_esc(r.get("p5date") or "")}</span></td>'
            f'<td style="text-align:center">{badge}{_whatsnew_badge(r)}</td></tr>')
    if not rows:
        trs = ['<tr><td colspan="19" style="padding:14px;color:var(--ink-2)">No open trades match '
               'these filters — loosen a dropdown or <a href="/dash/wolfe/trades?universe='
               + _q(uni) + '&amp;clear=1" style="color:#58a6ff">clear all</a>.</td></tr>']

    head = ("symbol", "dir", "sector", "size", "liquidity / deliv", "status", "trade", "CMP",
            "entry zone", "stop", "T1", "EPA", "run %", "risk %", "R:R",
            f"Q/{wolfe._QUALITY_MAX}", "RS", "age", "")

    sd = _esc(snap.get("scan_date") or "—")
    ca = _esc((snap.get("computed_at") or "")[:16])
    body = (
        _CSS
        + '<h2>Wolfe <span style="color:var(--ink-2);font-size:15px;font-weight:400">— open trades, remaining ROI</span></h2>'
        + wolfe_view_toggle("open")
        + _staleness_banner(snap.get("scan_date"), latest_data)
        + '<div class="sub" style="margin-bottom:8px">Every <b>OPEN</b> winner-profile Wolfe setup — '
        'point 5 printed, the EPA (1-4) target <b>not yet reached</b>, so run is still left — at <b>any age</b>, '
        'ranked by how much room is left from the current price. '
        '<b style="color:var(--up)">run%</b> = move to the EPA target from CMP · '
        '<b>risk%</b> = distance to the stop · <b>R:R</b> = reward:risk if you enter now. '
        '<span style="color:#1f6feb;font-weight:600">★ edge</span> = fresh ≤15d (the OOS-validated entry-edge); '
        '<span style="color:var(--ink-3)">open</span> = older, run left but <i>no validated entry-edge — judge the run</i>. '
        'Q = structural strength (the ★edge filter differs on purpose). '
        '<i>Descriptive — not a buy/sell signal.</i></div>'
        f'<div class="sub" style="margin-bottom:8px;font-size:12px">{sortbar}</div>'
        + fbar
        + _bottom_line(rows, total_open, snap.get("held_out", 0))
        + _breadth(rows)
        + f'<div style="color:var(--ink-2);font-size:13px;margin:8px 0 10px">{_esc(uni)} · '
          f'as-of <b>{sd}</b> <span style="color:var(--ink-3)">(nightly snapshot'
          f'{(" · computed " + ca) if ca else ""})</span> · '
          f'<b>{len(rows)} of {total_open} ranked open trades</b> · {nin} actionable now'
          f' &nbsp;|&nbsp; <a href="/dash/wolfe/trades?{_qs(params, format="csv")}" style="color:#3fb950" '
          'title="download the filtered + sorted rows as CSV">⬇ CSV</a>'
          ' &nbsp;|&nbsp; <a href="/dash/wolfe/scan?universe=' + _q(uni) + '" style="color:#58a6ff">fresh scanner ›</a>'
          '</div>'
        '<div class="wtwrap"><table class="wttab" style="width:100%;border-collapse:collapse;font-size:13px">'
        '<thead><tr style="color:var(--ink-2);text-align:left">'
        + "".join(f'<th style="padding:6px 10px;white-space:nowrap">{h}</th>' for h in head)
        + '</tr></thead><tbody>' + "".join(trs) + '</tbody></table></div>')
    resp = _sticky(HTMLResponse(_shell("Open trades — Wolfe", body, "wolfe", wide=True)), active, clear)
    resp.set_cookie(_SEEN_COOKIE, _seen_str(all_rows), max_age=2592000,   # remember for the next-look diff
                    path="/dash/wolfe/trades", samesite="lax", httponly=True)
    return resp


def _num_q(v):
    """Q may be a float (§B total) — show a clean integer-ish value."""
    if v is None:
        return ""
    try:
        return f"{float(v):g}"
    except Exception:
        return _esc(v)


_CSS = """<style>
.wtbar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:flex-end;margin:6px 0 2px;
  padding:10px;background:#0e141c;border:1px solid #1c2937;border-radius:8px}
.wtf{display:flex;flex-direction:column;gap:3px;font-size:11px;color:#7d93a8}
.wtf span{letter-spacing:.03em}
.wtf select{font:inherit;font-size:12.5px;background:#0b0f17;color:#cdd9e5;
  border:1px solid #27384a;border-radius:6px;padding:5px 7px;min-width:120px}
.wtf select:hover{border-color:#4d9dff}
.wtclear{align-self:flex-end;font-size:12px;color:#7d93a8;text-decoration:none;
  padding:6px 8px;border:1px solid #27384a;border-radius:6px}
.wtclear:hover{color:#eaf1f9;border-color:#4d9dff}
.wtbl{font-size:13.5px;line-height:1.5;margin:8px 0 4px;padding:10px 12px;
  background:#0e1a14;border:1px solid #1c3a2a;border-left:3px solid #3fb950;border-radius:8px;color:#c7d5e0}
@media (prefers-color-scheme:light){.wtbl{background:#f0f8f2;border-color:#cce8d5;color:#243b30}}
/* sticky symbol column + header so the wide table stays readable while scrolling */
.wtwrap{max-height:78vh;overflow:auto;border:1px solid #1c2937;border-radius:8px}
.wttab thead th{position:sticky;top:0;z-index:2;background:#0e141c}
.wttab tbody td:first-child{position:sticky;left:0;z-index:1;background:var(--bg-1,#0d1117)}
.wttab thead th:first-child{position:sticky;left:0;top:0;z-index:3;background:#0e141c}
.wttab tbody tr.wtrow:hover td{background:#1c2430}
.wtbreadth{font-size:12.5px;color:#9bb0c6;margin:4px 0 2px;padding:7px 12px;background:#0e141c;
  border:1px solid #1c2937;border-radius:8px}
.wtstale{font-size:13px;margin:8px 0;padding:9px 12px;background:#2a1e0e;border:1px solid #5c4415;
  border-left:3px solid #d29922;border-radius:8px;color:#e8d3a3}
</style>"""
