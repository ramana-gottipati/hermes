"""sideways_parity — the migration-parity ledger: guarantee nothing in the classic estate
is silently missed as the modern app ("Sideways") is rebuilt from scratch.

The problem
-----------
Sideways is a from-scratch rebuild (redesign M0-M8; identity mid-reselection). A from-scratch
rebuild is exactly where a 73-surface / 257-metric / 17-strategy estate loses things — not
maliciously, just silently. "Be careful" does not scale. This module is the machine-enforced
answer, same DNA as the gates that already keep the classic site honest (`test_dash_route_registry`
= no orphan routes, `test_pat_coverage` = every lens known to Pat): a DERIVED inventory of the
whole product estate, a DISPOSITION for every element, and a gate (`tests/test_sideways_parity.py`)
that fails the build on any integrity violation.

The inventory is DERIVED, never hand-typed
------------------------------------------
Everything we shipped already lives in single-sources-of-truth, so a new lens/metric/strategy
appears here the day it ships (it can never drift):
  * SURFACES   — `lens_registry.LENSES` (routed) — the screens a user would notice missing.
  * METRICS    — `docs/metrics-glossary.md` bullets — must stay explainable in Sideways.
  * STRATEGIES — `docs/strategies/*.md` — must stay represented (with their honesty verdict).

Every element carries a DISPOSITION
------------------------------------
    PORTED   — built in Sideways AND verified at a real route (the `target` is that /dash route).
    DEFERRED — planned; `target` is the Sideways milestone (M6/M7/M8) or UNSCOPED (no milestone
               covers it yet — the visible planning gap, e.g. the Markets analytical estate).
    DROPPED  — deliberately not carried, WITH a rationale (the ONLY way something legitimately
               doesn't make it).
    NA       — structurally doesn't apply to the new app, WITH a rationale.

A surface with no explicit disposition falls to a deterministic per-workspace DEFERRED default,
so it is always ACCOUNTED (it shows on the board's backlog) — never invisible. Explicit entries
capture the real decisions (what is ported / dropped / re-scoped). The gate enforces integrity
(no stale keys · PORTED has a route · DROPPED/NA have a reason) and completeness (a milestone
marked DONE cannot still have un-ported surfaces assigned to it).

This is v1: surface/metric/strategy parity + the visible backlog. Honesty-status carry (each
item's descriptive-only / fundable / falsified verdict travels with it) is a v2 tightening.

Internal governance board: /dash/sideways-parity (INTERNAL_DEV route — deliberately unlinked,
an owner/ops dashboard, not a customer lens). Read-only, descriptive.
"""
from __future__ import annotations

import glob
import os
import re

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.web import lens_registry as LR
from src.web.dashboard import _shell, _esc

router = APIRouter()

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── the Sideways milestones (redesign M0-M8; docs/redesign-coordination.md §5) ───────
# status: DONE (deployed) · PLANNED (spec/approved, not built) · OPEN (no milestone).
MILESTONES: dict[str, tuple[str, str]] = {
    "M3":       ("News / flow dock", "DONE"),
    "M4":       ("Stock hub (dossier)", "DONE"),
    "M5":       ("Today / orientation home", "DONE"),
    "M6":       ("Journey / guided + help layer", "PLANNED"),
    "M7":       ("Clusters & portfolios (Strategies + Tracker)", "PLANNED"),
    "M8":       ("Screener", "PLANNED"),
    # Added 2026-07-24 (owner) to close the gap the parity ledger surfaced: the M6-M8 plan
    # scoped journey/clusters/screener but not the Markets analytical estate. M-Markets carries it.
    "M-Markets": ("Markets analytical estate (internals · anatomy · self-history · rotation · RS · "
                  "seasonal · events · patterns · participants · compare · …)", "PLANNED"),
    "UNSCOPED": ("Not yet assigned to any Sideways milestone", "OPEN"),
}

# per-workspace DEFAULT milestone for a surface with no explicit disposition. The Markets
# analytical estate maps to M-Markets — the milestone the owner added 2026-07-24 to close the
# gap the ledger surfaced (M6-M8 had scoped journey/clusters/screener but not the Markets estate).
_WS_MILESTONE: dict[str, str] = {
    "markets": "M-Markets", "screener": "M8", "strategies": "M7", "tracker": "M7", "trust": "M6",
}

# ── EXPLICIT dispositions — the human decisions. (status, target, note) ───────────────
#   PORTED  : target = the live Sideways /dash route; note = what it maps to.
#   DEFERRED: target = a MILESTONES key; note optional.
#   DROPPED : target = ""; note = REQUIRED rationale.
#   NA      : target = ""; note = REQUIRED rationale.
# Everything not listed here takes the per-workspace DEFERRED default above.
SURFACE_PARITY: dict[str, tuple[str, str, str]] = {
    "markets": ("PORTED", "/dash/preview",
                "M5 Today IS the migrated markets overview / orientation home"),
    "wire":    ("PORTED", "/dash/preview",
                "M3 news/flow dock (?ch=news) is the migrated News/Wire"),

    # ── M-Markets · lane W2-A (2026-07-27): eleven classic Markets lenses consolidated into FOUR
    # Graphite pages. Consolidation, not transliteration — each page answers ONE question with its
    # evidence stacked under it. Every note below states what travelled AND what deliberately did
    # not, so a "PORTED" here can never over-claim (the classic lens stays live either way).
    "market-internals": ("PORTED", "/dash/home/internals",
                         "Graphite Market internals: the five vital signs with Pro percentile "
                         "references vs the full 2004-> history, the price-breadth-vs-tape hero, the "
                         "delivery/dispersion/coil regimes, the crisis-fingerprint anchors and a "
                         "session drill. NOT carried: the 1200-cell daily heat ribbon (the drill is "
                         "reached from a 20-session strip instead) — classic keeps it"),
    "divergence": ("PORTED", "/dash/home/internals",
                   "the RSI-of-RS divergence watch (bullish/bearish columns + the momentum-extremes "
                   "strip) is the Divergence-watch zone of the Graphite internals page; the home's "
                   "own breadth-vs-delivery two-gauge stays the Today-level seed"),
    "participants": ("PORTED", "/dash/home/flows",
                     "Graphite Flows & positioning: the FII index-futures stance with its own-history "
                     "percentile, the FII-vs-retail mirror, the four-participant matrix (index fut "
                     "net · long:short · stock fut net · index option lean) and the recent-session "
                     "history (Pro). Sits beside the home's existing FII/DII cash reads rather than "
                     "duplicating them"),
    "fno": ("PORTED", "/dash/home/flows",
            "the own-history F&O board (OI · PCR · max-pain percentiles + build-up streak) with the "
            "auto reality-check callouts and a server CSV; the Phase-0 fence travels ON the block "
            "(PCR selects weakly, forward-test-only; max-pain/basis/OI-change failed)"),
    "actions": ("PORTED", "/dash/home/events",
                "the forward corporate-actions calendar grouped by ex-date with type counts, the "
                "recent-past + security-events context (Pro) and a server CSV; reuses the home's "
                "reads.upcoming_ca (same corp_actions.upcoming single source). E-11/E-12 logistics "
                "fence carried"),
    "results-reactions": ("PORTED", "/dash/home/events",
                          "the results-reaction board (surprise · delivery multiple · realized 22/60-"
                          "day abnormal move) + who-reports-next, with the falsification fence stated "
                          "ABOVE the table (tradeable book net ret/vol 0.10 vs bench 0.85). NOT "
                          "carried: the CAR fan SVG and the published-brief cards — classic keeps them"),
    "event-cadence": ("PORTED", "/dash/home/events",
                      "overdue-vs-own-rhythm + expected-by-cadence tables with the event-type filter "
                      "and the dormant count, off the same bounded seasonal_events snapshot; TIME-only "
                      "fence carried verbatim. Index-membership filter not carried (event-type only)"),
    "buyback-calc": ("PORTED", "/dash/home/events",
                     "the tender-quota calculator (accepted · tender P&L · residual · net · breakeven "
                     "exit) with the live ₹2L small-shareholder eligibility read-out, anchored by the "
                     "buyback rows on the corporate-actions feed; the acceptance-ratio-is-YOUR-"
                     "assumption fence carried"),
    "surveillance": ("PORTED", "/dash/home/events",
                     "the ASM/GSM/price-band transition tape + current-state counts, single-sourced "
                     "through surveillance.transitions/current_state so page == card == pillar; "
                     "'context, never a gate' fence carried"),
    "band-locks": ("PORTED", "/dash/home/events",
                   "the close-at-band streak board single-sourced through band_lock.active_streaks, "
                   "with the honest-window note (bands reconstructable only back to the feed's first "
                   "captured day) and the no-study-exists fence"),
    "attention": ("PORTED", "/dash/home/attention",
                  "the full magnitude-ranked queue with lens filters, per-batch counts, ?as_of= "
                  "last-batch-on-or-before replay and the curated alert rail; the depth behind the "
                  "home's 'What changed today' band (which keeps owning severity_counts/what_changed). "
                  "NOT carried: the acknowledge WRITE and the cookie 'since you last looked' brief — "
                  "owner actions that stay on the classic page"),
}

_VALID_STATUS = {"PORTED", "DEFERRED", "DROPPED", "NA"}


def surfaces() -> list:
    """Derived: every routed lens (the screens). (key, label, altitude, route)."""
    return [(ln.key, ln.label, ln.altitude, ln.route) for ln in LR.LENSES if ln.route]


def metrics() -> list:
    """Derived: metric/term names from docs/metrics-glossary.md bullets (best-effort)."""
    p = os.path.join(_ROOT, "docs", "metrics-glossary.md")
    try:
        txt = open(p, encoding="utf-8").read()
    except OSError:
        return []
    # a metric bullet: "- **Term ....**  definition"
    return [m.strip() for m in re.findall(r"^-\s+\*\*(.+?)\*\*", txt, re.M)]


def strategies() -> list:
    """Derived: strategy pages (docs/strategies/*.md, excluding the index/README)."""
    out = []
    for f in sorted(glob.glob(os.path.join(_ROOT, "docs", "strategies", "*.md"))):
        base = os.path.basename(f).lower()
        if base in ("readme.md", "index.md", "_index.md"):
            continue
        out.append(os.path.basename(f)[:-3])
    return out


def disposition(key: str, altitude: str) -> tuple[str, str, str]:
    """The effective disposition for a surface: explicit entry, else the workspace default."""
    if key in SURFACE_PARITY:
        return SURFACE_PARITY[key]
    return ("DEFERRED", _WS_MILESTONE.get(altitude, "UNSCOPED"), "")


def summary() -> dict:
    """Counts for the board + the gate's non-degenerate sanity."""
    srf = surfaces()
    by_status: dict[str, int] = {"PORTED": 0, "DEFERRED": 0, "DROPPED": 0, "NA": 0}
    unscoped = 0
    for key, _label, alt, _route in srf:
        st, tgt, _n = disposition(key, alt)
        by_status[st] = by_status.get(st, 0) + 1
        if st == "DEFERRED" and tgt == "UNSCOPED":
            unscoped += 1
    return {
        "surfaces": len(srf), "metrics": len(metrics()), "strategies": len(strategies()),
        "by_status": by_status, "unscoped": unscoped,
    }


# ── the board (INTERNAL_DEV route) ────────────────────────────────────────────────────
_CSS = """
<style>
.sp-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 14px;max-width:1120px;}
.sp-note b{color:var(--ink);}
.sp-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 16px;}
.sp-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:11px;padding:11px 13px;}
.sp-tile .n{font-size:25px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.05;}
.sp-tile .l{font-size:11px;color:var(--ink-2);margin-top:5px;}
.sp-h{font-size:15px;font-weight:700;margin:18px 0 6px;color:var(--ink);}
table.sp{border-collapse:collapse;width:100%;font-size:12px;margin:0 0 8px;}
table.sp th{color:var(--ink-3);font-weight:600;text-align:left;padding:4px 8px;border-bottom:1px solid var(--line-2);}
table.sp td{padding:3px 8px;border-bottom:1px solid var(--line);vertical-align:top;}
table.sp td.k a{color:var(--accent);text-decoration:none;font-weight:600;}
.sp-pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:10.5px;font-weight:700;}
.sp-PORTED{background:rgba(35,160,90,.16);color:#1f9e5a;}
.sp-DEFERRED{background:rgba(200,150,20,.16);color:#c69316;}
.sp-UNSCOPED{background:rgba(210,70,70,.16);color:#d24646;}
.sp-DROPPED{background:var(--bg-3);color:var(--ink-3);}
.sp-NA{background:var(--bg-3);color:var(--ink-3);}
.sp-ms{color:var(--ink-3);font-size:11px;}
</style>
"""

_WS_ORDER = ("markets", "screener", "strategies", "tracker", "trust")
_WS_LABEL = {"markets": "Markets", "screener": "Screener", "strategies": "Strategies",
             "tracker": "Tracker", "trust": "Trust"}


def _pill(status: str, target: str) -> str:
    kind = "UNSCOPED" if (status == "DEFERRED" and target == "UNSCOPED") else status
    label = "UNSCOPED" if kind == "UNSCOPED" else status
    return f'<span class="sp-pill sp-{kind}">{label}</span>'


def _render() -> str:
    s = summary()
    body = [_CSS, '<h2 style="margin:0 0 2px">Sideways migration parity '
            '<small style="color:var(--ink-3);font-size:12px;font-weight:400">'
            'every classic element accounted for in the modern app · derived + gate-enforced</small></h2>']
    body.append(
        '<div class="sp-note">Guarantees nothing in the classic estate is <b>silently</b> missed as '
        'Sideways is rebuilt. The inventory is <b>derived</b> from the single-sources-of-truth '
        '(lens registry · metrics glossary · strategy docs), so a new element appears here the day it '
        'ships. Every surface carries a disposition; a gate (<code>tests/test_sideways_parity.py</code>) '
        'fails the build on any integrity violation (a dropped surface with no reason, a "done" '
        'milestone with un-ported surfaces). <b>UNSCOPED</b> = accounted but not yet assigned to any '
        'Sideways milestone — the visible planning gap. Descriptive; internal.</div>')

    bs = s["by_status"]
    tiles = [
        ("n", s["surfaces"], "surfaces (routed lenses)"),
        ("PORTED", bs["PORTED"], "ported + live"),
        ("DEFERRED", bs["DEFERRED"], "deferred / planned"),
        ("UNSCOPED", s["unscoped"], "UNSCOPED — no milestone yet"),
        ("n", s["metrics"], "metrics accounted"),
        ("n", s["strategies"], "strategies accounted"),
    ]
    thtml = ""
    for kind, n, lab in tiles:
        col = ({"PORTED": "#1f9e5a", "DEFERRED": "#c69316", "UNSCOPED": "#d24646"}
               .get(kind, "var(--ink)"))
        thtml += f'<div class="sp-tile"><div class="n" style="color:{col}">{n}</div><div class="l">{_esc(lab)}</div></div>'
    body.append(f'<div class="sp-tiles">{thtml}</div>')

    # milestones
    body.append('<div class="sp-h">Sideways milestones</div>')
    ms = '<table class="sp"><thead><tr><th>Milestone</th><th>Scope</th><th>Status</th></tr></thead><tbody>'
    for k, (lab, st) in MILESTONES.items():
        stp = 'sp-PORTED' if st == "DONE" else ('sp-DEFERRED' if st == "PLANNED" else 'sp-UNSCOPED')
        ms += f'<tr><td><b>{_esc(k)}</b></td><td>{_esc(lab)}</td><td><span class="sp-pill {stp}">{_esc(st)}</span></td></tr>'
    body.append(ms + '</tbody></table>')

    # surfaces by workspace
    srf = surfaces()
    for ws in _WS_ORDER:
        rows = [(k, lab, alt, rt) for (k, lab, alt, rt) in srf if alt == ws]
        if not rows:
            continue
        body.append(f'<div class="sp-h">{_esc(_WS_LABEL[ws])} <span class="sp-ms">· {len(rows)} surfaces</span></div>')
        t = ('<table class="sp"><thead><tr><th>Lens</th><th>Classic route</th><th>Disposition</th>'
             '<th>Target</th><th>Note</th></tr></thead><tbody>')
        for k, lab, alt, rt in rows:
            st, tgt, note = disposition(k, alt)
            tgt_txt = (f'<a href="{_esc(tgt)}" style="color:var(--accent);text-decoration:none">{_esc(tgt)}</a>'
                       if st == "PORTED" and tgt.startswith("/dash") else _esc(tgt or "—"))
            t += (f'<tr><td class="k"><a href="{_esc(rt)}">{_esc(lab)}</a> '
                  f'<span class="sp-ms">{_esc(k)}</span></td><td class="sp-ms">{_esc(rt)}</td>'
                  f'<td>{_pill(st, tgt)}</td><td class="sp-ms">{tgt_txt}</td>'
                  f'<td class="sp-ms">{_esc(note)}</td></tr>')
        body.append(t + '</tbody></table>')

    body.append(f'<div class="sp-note" style="margin-top:14px;color:var(--ink-3);font-size:11.5px">'
                f'Also accounted (port with their surfaces): <b>{s["metrics"]}</b> metrics '
                f'(<code>docs/metrics-glossary.md</code>) · <b>{s["strategies"]}</b> strategies '
                f'(<code>docs/strategies/</code>). v2 tightening: each item\'s honesty verdict '
                f'(descriptive-only / fundable / falsified) travels with the port. '
                f'<a href="/dash/sideways-parity?format=csv" style="color:var(--accent)">CSV</a></div>')
    return "".join(body)


def _csv() -> str:
    out = ["kind,key,label,workspace,classic_route,status,target,note"]
    for k, lab, alt, rt in surfaces():
        st, tgt, note = disposition(k, alt)
        note = note.replace(",", ";").replace("\n", " ")
        out.append(f'surface,{k},"{lab}",{alt},{rt},{st},{tgt},"{note}"')
    for m in metrics():
        out.append(f'metric,"{m.replace(chr(34), "")}",,,,DEFERRED,ports-with-surface,')
    for st in strategies():
        out.append(f'strategy,{st},,,,DEFERRED,M7,')
    return "\n".join(out) + "\n"


@router.get("/dash/sideways-parity", response_class=HTMLResponse)
def dash_sideways_parity(format: str = "") -> HTMLResponse:
    if format == "csv":
        return PlainTextResponse(_csv(), media_type="text/csv",
                                 headers={"Content-Disposition": 'attachment; filename="sideways-parity.csv"'})
    try:
        html = _render()
    except Exception as e:  # noqa: BLE001 — never 500 an internal board
        html = (f'<h2>Sideways migration parity</h2><div class="sp-note">The parity ledger could not '
                f'render on this host ({_esc(str(e))}). It derives from lens_registry + '
                f'docs/metrics-glossary.md + docs/strategies/.</div>')
    return HTMLResponse(_shell("Sideways parity · patearn", _CSS + html, "", "", wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/sideways-parity" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    srf = surfaces()
    assert len(srf) >= 50, ("too few surfaces derived", len(srf))
    # every surface resolves to a valid disposition
    for k, _lab, alt, _rt in srf:
        st, tgt, note = disposition(k, alt)
        assert st in _VALID_STATUS, (k, st)
        if st == "PORTED":
            assert tgt.startswith("/dash"), (k, "PORTED needs a route", tgt)
        if st in ("DROPPED", "NA"):
            assert note.strip(), (k, st, "needs a rationale")
        if st == "DEFERRED":
            assert tgt in MILESTONES, (k, "bad milestone", tgt)
    s = summary()
    assert s["metrics"] > 100 and s["strategies"] > 5, s
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    assert c.get("/dash/sideways-parity").status_code == 200
    assert "migration parity" in c.get("/dash/sideways-parity").text
    assert c.get("/dash/sideways-parity?format=csv").status_code == 200
    print("sideways_parity selftest OK — %d surfaces · %d metrics · %d strategies · %d UNSCOPED · board 200"
          % (s["surfaces"], s["metrics"], s["strategies"], s["unscoped"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
