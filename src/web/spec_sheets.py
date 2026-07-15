"""/dash/spec-sheets — the pre-registration ledger as a Trust surface (charter P-03).

One sheet per completed study: the hypothesis as pre-registered, the pass/fail gate as
written BEFORE the run, the exact recorded numbers, and the verdict — including, on
purpose, the failures. The charter's thesis is that the evidence machine IS the product;
a spec-sheet page that only showed wins would be marketing. Fulfils the §9 KPI
("spec-sheets published: 3 by end-Aug").

Live boxes: season filing→surface MTTR from research.db `reaction_mttr` (honest about the
day-1 baseline seeding), and the M-02 placebo readout from
research/explosive_moves/out/placebo_pead.json once the harness has run.

House pattern: pure-stdlib isolated APIRouter (like results_reactions), mounted by one
line in v2_surfaces._ROUTER_SPECS + a Trust Lens record. Numbers are hand-carried FROM
docs/strategy-ledger.md and cite it; the ledger stays canonical (D91 spirit: this page
never invents a number).
"""
from __future__ import annotations

import html
import json
import sqlite3
from datetime import date, datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

RESEARCH_DB = "/opt/hermes/data/research.db"
PLACEBO_JSON = "/opt/hermes/research/explosive_moves/out/placebo_pead.json"
MTTR_SEED_CUTOFF = "2026-07-07 02:00"     # rows stamped before this = the baseline seed run

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


_CSS = """
<style>
.sp{max-width:1080px}
.sp .lead{color:var(--ink-2);font-size:13px;line-height:1.65;max-width:880px;margin:2px 0 16px}
.sp .sheet{border:1px solid var(--line-2);border-radius:12px;background:var(--bg-1);
           padding:14px 18px;margin:0 0 16px}
.sp .sheet h3{margin:0 0 2px;font-size:15px}
.sp .meta{font-size:11px;color:var(--ink-3);margin:0 0 10px}
.sp .verdict{display:inline-block;font-size:10px;font-weight:800;letter-spacing:.06em;
             padding:2px 9px;border-radius:9px;text-transform:uppercase;margin-left:8px}
.sp .v-desc{background:rgba(127,230,176,.12);color:#7fe6b0;border:1px solid rgba(127,230,176,.35)}
.sp .v-fail{background:rgba(255,106,122,.10);color:#ff6a7a;border:1px solid rgba(255,106,122,.35)}
.sp .row{display:grid;grid-template-columns:150px 1fr;gap:4px 14px;font-size:12.5px;
         line-height:1.6;padding:3px 0;border-top:1px solid var(--bg-3)}
.sp .row .k{color:var(--ink-3);font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding-top:2px}
.sp .num{font-variant-numeric:tabular-nums}
.sp .live{border:1px solid var(--line-2);border-radius:10px;padding:10px 14px;margin:0 0 14px;
          background:var(--bg-2);font-size:12.5px;line-height:1.6}
.sp .live b{color:#b18cff}
.sp .note{color:var(--ink-2);font-size:11px;margin-top:14px;border-top:1px solid var(--line-2);
          padding-top:10px;line-height:1.6;max-width:880px}
.sp .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:860px){.sp .grid2{grid-template-columns:1fr}}
</style>"""


# ── the sheets (numbers hand-carried from docs/strategy-ledger.md — cited per sheet) ──

_SHEETS = [
    {
        "title": "PEAD on real BSE result dates, delivery-confirmed",
        "verdict": ("descriptive lens CONFIRMED", "v-desc", "book FALSIFIED", "v-fail"),
        "pre_reg": "2026-07-05 (A-study) · within-season variant pre-registered 2026-07-05b",
        "hypothesis": "A high Net-Profit surprise (SUE, no analysts) CONFIRMED by abnormal "
                      "delivered value drifts upward over the next ~60 sessions — on REAL "
                      "announcement dates (provenance_knowable), zero look-ahead.",
        "gate": "Descriptive: cohort t ≥ ~2 on leak-free dates. Book: net return/vol > 0.89 "
                "(Nifty-500 B&H) in BOTH walk-forward halves under tiered+ATR costs.",
        "result": "Descriptive: SUE-Q5 × DELIV-T3 mean CAR60 <b class='num'>+7.62%</b> "
                  "(n=235, t_cohort 1.92); same surprise on thin delivery only +3.7% "
                  "(n=200); population +3.5%. Bad news did not drift. "
                  "Book: EVERY wrapper failed — trailing net return/vol <b class='num'>0.10</b> · "
                  "no-delivery 0.02 · 1.5× cost −0.32 · hedged <b class='num'>−0.58</b> · "
                  "within-season (the pre-registered last cell) <b class='num'>0.06</b> — "
                  "vs benchmark 0.85.",
        "ships": "The results-reaction war room (who just reported + delivery confirmation + "
                 "realized drift, base-rates labelled). No ranking, no trigger, no book — "
                 "the tradeable version is recorded dead in the failure ledger.",
        "source": "docs/strategy-ledger.md § Experiment 2026-07-05 · research/explosive_moves/pead.py",
    },
    {
        "title": "Accumulation-footprint detector (front-detect the insider from the tape)",
        "verdict": ("gate FAIL — published", "v-fail", None, None),
        "pre_reg": "2026-07-05b — gate written in the module docstring before the run",
        "hypothesis": "Insider/SAST accumulation episodes leave a detectable tape footprint "
                      "BEFORE the filing becomes public (delivery %, trade size, volume, "
                      "price character vs self- and cross-sectional controls).",
        "gate": "≥2 of 4 features clear Cliff's δ ≥ +0.20 vs BOTH control sets.",
        "result": "FAIL <b class='num'>1/4</b> — only avg-trade-size cleared "
                  "(δ <b class='num'>+0.329 / +0.250</b>). Structural finding: "
                  "<b class='num'>764 of 947</b> episodes had NO pre-public window at all — "
                  "SEBI PIT T+2 disclosure means the tape you can trade is already public. "
                  "Usable n=54. delivery-% showed ~no case elevation (δ ≈ +0.07), consistent "
                  "with MEP's earlier alpha failure.",
        "ships": "The trade-size ratio as a DESCRIPTIVE column (Ticket, on Screen+ / "
                 "Positioning / dossier) — a characterization, never a detector. Detection "
                 "pivots to post-public designs (disclosure-drift E-03, campaign arcs E-04), "
                 "each requiring fresh pre-registration.",
        "source": "docs/strategy-ledger.md § Study 2026-07-05b · research/explosive_moves/footprint.py",
    },
    {
        "title": "Insider disclosure drift (E-03, post-public)",
        "verdict": ("gate FAIL — placebo caught it", "v-fail", None, None),
        "pre_reg": "2026-07-07 (module docstring before the run)",
        "hypothesis": "Conviction promoter-buy clusters drift up after their first public "
                      "disclosure (the pre-public window is structurally dead — SEBI T+2).",
        "gate": "Top-value-quartile CAR60 t_cohort ≥ 2 AND observed clears the shuffled-date "
                "placebo p95 (n=200, seed 42).",
        "result": "The trap this page exists for: value-Q4 CAR60 <b class='num'>+8.26%</b> "
                  "(n=66, plain t 2.87) — looks like a product. The placebo null's p95 is "
                  "<b class='num'>+9.52%</b>: random windows of the same names drift just as "
                  "hard (the 2025-26 tape). Inflation 0.87×, empirical p 0.085; cohort t is "
                  "NaN because the feed is only ~10 months deep. NULL published.",
        "ships": "Nothing. Re-attempt condition on record: ≥8 quarterly cohorts of feed depth "
                 "and a placebo-clearing mean.",
        "source": "docs/strategy-ledger.md § Studies 2026-07-08 · research/explosive_moves/insider_drift.py",
    },
    {
        "title": "Filing-latency tell (late vs own norm)",
        "verdict": ("gate FAIL — null published", "v-fail", None, None),
        "pre_reg": "2026-07-07",
        "hypothesis": "Filing later than one's own historical norm is a tell — lateness "
                      "predicts bad surprises and negative drift.",
        "gate": "|t_cohort(Q5−Q1 CAR60)| ≥ 2 AND |gap| > label-permutation p95 (500 perms).",
        "result": "Half the folk story is real: the latest filers carry the weakest surprises "
                  "(mean SUE <b class='num'>0.77</b> vs <b class='num'>1.04</b> for the "
                  "earliest). But it does not price: CAR60 gap <b class='num'>−0.81%</b> "
                  "(t_cohort −0.84), inside the ±2.51% permutation band. Lateness predicts "
                  "surprise MIX, not tradeable drift.",
        "ships": "Nothing — no war-room flag. The surprise-mix fact may inform reading, "
                 "never a signal.",
        "source": "docs/strategy-ledger.md § Studies 2026-07-08 · research/explosive_moves/filing_latency.py",
    },
    {
        "title": "Concall growth-intent walk-forward (real call dates)",
        "verdict": ("gate FAIL — covered-name beta", "v-fail", None, None),
        "pre_reg": "2026-07-07; design correction recorded before the run (condition on "
                   "statement PRESENCE at the call, not settlement)",
        "hypothesis": "Calls pushing specific guidance content (debt reduction, capex, volume…) "
                      "drift differently over the next 60 sessions — the old month-granular "
                      "panel showed +2.8%/+2.3%/+1.5% tilts.",
        "gate": "Per type (n≥100): t_cohort ≥ 2 AND same-sign halves AND the largest passing "
                "type clears the date-shuffle placebo.",
        "result": "9,461 real-dated events. Six types pass t+halves (debt_reduction "
                  "<b class='num'>+3.52%</b> t 2.43; capex +3.07% t 2.70) — and the placebo "
                  "unmasks all of it: random windows of the SAME covered names drift "
                  "<b class='num'>+2.75%</b> (p95 <b class='num'>+3.66%</b>); the observed "
                  "means sit inside the null band (inflation 0.52×, emp-p 0.925). The old "
                  "panel tilts are recorded NOT reproducible on real dates.",
        "ships": "Nothing as an edge. Guidance remains a candor / kept-promise DESCRIPTIVE "
                 "axis (Gate B fence unchanged).",
        "source": "docs/strategy-ledger.md § Studies 2026-07-08 · research/explosive_moves/concall_intent.py",
    },
    {
        "title": "Dividend-surprise drift (E-11, post-ex)",
        "verdict": ("gate FAIL — payer beta", "v-fail", None, None),
        "pre_reg": "2026-07-07 · the first gate HASHED before its run (M-04 registry)",
        "hypothesis": "A dividend far above a name's own norm marks strength that drifts "
                      "over the following 60 sessions (post-ex, the conservative clock).",
        "gate": "Surprise-Q5 CAR60 t_cohort ≥ 2 AND the date-shuffle placebo clears "
                "(n=200, seed 42).",
        "result": "22 years, 9,166 usable events. Q5 drifts +1.61% (t 2.60) — and so does "
                  "everything else: CUTS drift <b class='num'>+1.99%</b>, hikes +1.61%, the "
                  "LOWEST-surprise quintile +2.28% (55 cohorts). The placebo seals it: "
                  "post-ex windows (+2.13%) drift LESS than random windows of the same "
                  "payers (null mean <b class='num'>+2.48%</b>, p95 +3.58%). The 'surprise' "
                  "has no direction — it is dividend-payer beta.",
        "ships": "Nothing. Class rule generalized: covered-name / payer-universe drift is "
                 "the null every event claim must beat.",
        "source": "docs/strategy-ledger.md § Studies 2026-07-08 (S83g) · research/explosive_moves/dividend_drift.py",
    },
    {
        "title": "Rebrand pump (E-12, stitched rename series)",
        "verdict": ("gate FAIL — no pump exists", "v-fail", None, None),
        "pre_reg": "2026-07-07 · gate hashed before the run",
        "hypothesis": "A symbol rename pumps on the new identity, then fades.",
        "gate": "CAR22 t_cohort ≥ 2 AND placebo clears (pump); mean(CAR60−CAR22) < 0 with "
                "|t| ≥ 2 (fade). Wolfe power rule: 111 usable events = full-power claim.",
        "result": "The folk story is simply dead: CAR22 <b class='num'>−0.41%</b> (below "
                  "even the placebo null of +0.47%), CAR60 +0.12%. No pump, and the fade "
                  "leg earns no claim (pooled t 0.23; the cohort means run negative — "
                  "outlier-carried, recorded as nuance). Method dividend: renames are "
                  "unmeasurable on naive per-symbol series — this study shipped the "
                  "reusable STITCHED old→new loader.",
        "ships": "Nothing tradeable; the stitched loader joins the harness for every "
                 "future boundary-crossing study.",
        "source": "docs/strategy-ledger.md § Studies 2026-07-08 (S83g) · research/explosive_moves/rebrand_pump.py",
    },
    {
        "title": "Wolfe waves — geometry as a selection lens",
        "verdict": ("descriptive selection edge (BULL only)", "v-desc", "trade book FALSIFIED", "v-fail"),
        "pre_reg": "§A locked 2026-06-24 (rules), §C trade-mechanics tested 2026-06-25",
        "hypothesis": "Completed Wolfe geometries mark exhaustion points whose resolutions "
                      "beat matched baselines (entry pt-5 zone, SL zone-edge ±0.3%, T1/T2).",
        "gate": "Per-trade net edge vs matched non-pattern baselines; side-split honesty.",
        "result": "The EDGE IS SELECTION, not mechanics: BULL completions carry "
                  "<b class='num'>+1.37%</b> abnormal (median +2.14%) — but the mechanical "
                  "trade book is dead: median <b class='num'>−2%/trade net</b>, the top 1% "
                  "of trades carries 58% of profit. BEAR side is tail-only: regime-stripped "
                  "<b class='num'>−0.19%</b>, decaying to −0.94% in 2021-26.",
        "ships": "The Wolfe scanner + chart overlay as a descriptive lens (BULL-weighted, "
                 "side split shown); never a mechanical trigger. Harmonic (XABCD) ships "
                 "under the same fence.",
        "source": "docs/strategy-ledger.md Tier-2/§C · docs/wolfe-rules.md · src/automation/wolfe.py",
    },
    {
        "title": "Rigorous calendar seasonality on the PIT idiosyncratic residual",
        "verdict": ("descriptive estate LIVE", "v-desc", "tradeable calendar edge FALSIFIED", "v-fail"),
        "pre_reg": "2026-07-12 — 3 hypothesis families sha256-hashed BEFORE any compute "
                   "(2882ccbc · cb32d1b9 · e566904c), frozen in research.db.prereg_registry; the "
                   "engine docstring is part of the hash, so the gate cannot move.",
        "hypothesis": "Do Indian indices / sectors / stocks run systematically hot or cold on the "
                      "calendar (month · ISO-week · weekday) AFTER the market move is stripped out — "
                      "a tradeable idiosyncratic-residual seasonality?",
        "gate": "A cell CERTIFIES only if it clears BOTH placebo nulls (circular-block + cyclic-"
                "rotation, p&lt;0.05), family-wide BH-Yekutieli FDR, ≥15 scored years, out-of-sample "
                "sign-stability, AND a pre-pledged India mechanism — the year-label shuffle is banned "
                "(zero-width). Nothing is graded on the same data it was found in.",
        "result": "<b class='num'>0</b> cells certified — across index + sector, all "
                  "~<b class='num'>2,427</b> EQ stocks, and the broad Nifty 50/100/200/500 deepened "
                  "to 2004 (~20 scored years, N-gate PASSES). The single strongest broad cell "
                  "(Nifty 500 February) clears one placebo (p=<b class='num'>0.0498</b>) but dies "
                  "under FDR. Individual names look overwhelming — MARUTI September up "
                  "<b class='num'>89%</b> of 18 years — yet clear the single-calendar placebo only "
                  "to die under the multiple-months correction. Deeper data did not rescue it: the "
                  "greying is on merits, not thin history.",
        "ships": "The Seasonal Tape estate — /dash/seasonal-tape + screen + divergence + the "
                 "event-cadence lens + the /dash/stock embed — kept strictly DESCRIPTIVE. Every "
                 "drilled cell shows its year-by-year dispersion and a placebo &lsquo;why-grey&rsquo; "
                 "read; nothing is ranked, triggered, or tradeable. The greying IS the finding.",
        "source": "PROJECT_STATE §Session 120/130 · docs/strategies/ · src/automation/seasonal_tape.py "
                  "(frozen families in research.db.prereg_registry)",
    },
]


def _mttr_box():
    """Season filing→surface MTTR from reaction_mttr — honest about the baseline seed."""
    try:
        con = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error:
        return ""
    try:
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                           "AND name='reaction_mttr'").fetchone():
            return ""
        rows = con.execute(
            "SELECT t0, first_seen_utc FROM reaction_mttr WHERE first_seen_utc > ?",
            (MTTR_SEED_CUTOFF,)).fetchall()
    except sqlite3.Error:
        return ""
    finally:
        con.close()
    if not rows:
        return ('<div class="live">⏱ <b>Filing→surface MTTR (charter §9 KPI)</b> — measuring '
                'from the first fresh filing on. The ledger was baseline-seeded 2026-07-07 '
                '(1,570 historical events; seeding is excluded here); season filings land '
                '~Jul-09 and each one gets a first-seen stamp the evening it reaches the '
                'war room.</div>')
    lags = []
    for t0, seen in rows:
        try:
            lags.append((datetime.strptime(str(seen)[:10], "%Y-%m-%d").date()
                         - date.fromisoformat(str(t0)[:10])).days)
        except ValueError:
            continue
    if not lags:
        return ""
    lags.sort()
    med = lags[len(lags) // 2]
    same_evening = sum(1 for x in lags if x <= 1)
    return (f'<div class="live">⏱ <b>Filing→surface MTTR (charter §9 KPI, live)</b> — '
            f'<b class="num">{len(lags)}</b> fresh results events since Jul-07: median '
            f'<b class="num">{med}d</b> filing→board; <b class="num">{same_evening}</b> '
            f'surfaced by the next evening. Day-level (real BSE date → first-seen date); '
            f'the baseline seed run is excluded.</div>')


def _placebo_box():
    """M-02 readout once research/explosive_moves/out/placebo_pead.json exists."""
    try:
        with open(PLACEBO_JSON, encoding="utf-8") as f:
            p = json.load(f)
    except (OSError, ValueError):
        return ('<div class="live">🎲 <b>Placebo harness (M-02)</b> — every study on this '
                'page re-runs on shuffled event dates through the SAME pipeline; the '
                'observed effect must clear the null band. First published number (PEAD '
                'confirmed cell) lands here when the run completes.</div>')
    if not p.get("n_null"):
        return ""
    infl = p.get("inflation_x")
    return (f'<div class="live">🎲 <b>Placebo (M-02), {_esc(p.get("study", ""))}</b> — '
            f'observed <b class="num">{p["observed"]*100:+.2f}%</b> vs null mean '
            f'<b class="num">{p["null_mean"]*100:+.2f}%</b> / null p95 '
            f'<b class="num">{p["null_p95"]*100:+.2f}%</b> over '
            f'<b class="num">{p["n_null"]}</b> shuffles (seed {p.get("seed")}). '
            f'Observed / null-p95 = <b class="num">{infl:.1f}×</b>; empirical one-sided '
            f'p = <b class="num">{p["emp_p_one_sided"]:.3f}</b>. '
            f'<span style="color:var(--ink-3)">Generated {_esc(p.get("generated_at", ""))} — '
            f'a real effect must sit OUTSIDE the shuffled-date band; this one does'
            f'{"" if (infl or 0) > 1 else " NOT"}.</span></div>')


def _prereg_hashes():
    """module -> gate sha256 from the M-04 registry (research.db). {} when absent."""
    try:
        con = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=10)
        out = dict(con.execute("SELECT module, gate_sha256 FROM prereg_registry"))
        con.close()
        return out
    except sqlite3.Error:
        return {}


# Hoisted so the evidence pack (P-04, evidence_pack.py) assembles the SAME strings —
# these two blocks live here once; the pack imports them, never restates them.
M05_BOX = (
    '<div class="live">📏 <b>Standing caveats (M-05)</b> — printed beside every claim, '
    'not buried: <b class="num">44.1%</b> of the 22-year tape mass is unjoinable to '
    'fundamentals (the delistings live exactly there); <b class="num">1,706 / 1,722</b> '
    'delisted names are fundamentally dark; the price archive is left-censored at '
    '<b class="num">2004-07-23</b> (773 names). Every fundamentals-conditioned lift is '
    'therefore survivor-tilted — the survivor-vs-terminal re-cut (attribution.py §5) '
    'measures the direction of that bias, and the Deflated-Sharpe / PBO stages (M-03) '
    'are one import away in <code>evlib</code> for every study; factory auto-wiring '
    'lands with the next factory run.</div>')

NOTE_HTML = (
    '<div class="note">Numbers are hand-carried from '
    '<code>docs/strategy-ledger.md</code> (the canonical record) and the machine '
    'ledger in <code>research.db.strategy_runs</code>; the standing corollary those '
    'failures prove: price strength is the only gross forward-return engine we have '
    'found, value/quality/credibility/accumulation are context layers not rankers, '
    'and no factor here is a fundable net-of-cost alpha vs the index at AUM. '
    'Every return/vol on this page is mean return ÷ volatility, annualised — NOT a '
    'Sharpe ratio: no risk-free rate is subtracted, so it reads higher than a textbook '
    'Sharpe would. '
    'Descriptive research record, not investment advice.</div>')


def _sheet_html(s, hashes=None):
    v1, c1, v2, c2 = s["verdict"]
    badges = f'<span class="verdict {c1}">{_esc(v1)}</span>'
    if v2:
        badges += f'<span class="verdict {c2}">{_esc(v2)}</span>'
    hchip = ""
    if hashes:
        import re as _re
        m = _re.search(r"explosive_moves/(\w+)\.py", s.get("source", ""))
        h = hashes.get(m.group(1)) if m else None
        if h:
            hchip = (f' · gate sha256 <span class="num" title="M-04 registry: the study '
                     f'docstring (hypothesis + gate) hashed at registration; --verify '
                     f'flags any post-hoc edit">{_esc(h[:12])}…</span>')
    return (
        f'<div class="sheet"><h3>{_esc(s["title"])}{badges}</h3>'
        f'<div class="meta">pre-registered: {_esc(s["pre_reg"])}{hchip}</div>'
        f'<div class="row"><div class="k">Hypothesis</div><div>{s["hypothesis"]}</div></div>'
        f'<div class="row"><div class="k">Gate (before the run)</div><div>{s["gate"]}</div></div>'
        f'<div class="row"><div class="k">Recorded result</div><div>{s["result"]}</div></div>'
        f'<div class="row"><div class="k">What ships</div><div>{s["ships"]}</div></div>'
        f'<div class="row"><div class="k">Source of truth</div>'
        f'<div style="color:var(--ink-3)">{_esc(s["source"])}</div></div></div>')


@router.get("/dash/spec-sheets", response_class=HTMLResponse)
def spec_sheets():
    from src.web.infographics import bottom_line, demo_framing, how_to_read_link, readability_css
    body = [_CSS, readability_css(), '<div class="sp">',
            '<h2>Detection spec-sheets</h2>',
            bottom_line(
                'Every completed study on one page: the hypothesis, the <b>pass/fail gate written '
                'before the run</b>, the recorded numbers, and the verdict — <b>failures published '
                'on purpose</b>. The evidence machine, not a highlight reel.'),
            how_to_read_link(),
            demo_framing(),
            '<div class="lead">Every claim on this site enters through a <b>pre-registered '
            'gate</b>: the hypothesis and its pass/fail threshold are written before the run, '
            'and the result goes to the ledger — win or lose. These are the completed studies, '
            '<b>failures included on purpose</b>: a page that only showed wins would be '
            'marketing, and the discipline is the product. Nothing here is a signal, a '
            'ranking, or a return promise. These sheets — with the coverage boundary and '
            'the live season record — are assembled into the print-ready '
            '<a href="/dash/evidence-pack">evidence pack</a>.</div>',
            _mttr_box(),
            _placebo_box(),
            M05_BOX,
            "".join(_sheet_html(s, _prereg_hashes()) for s in _SHEETS),
            NOTE_HTML,
            '</div>']
    return HTMLResponse(_shell("Detection spec-sheets", "".join(body),
                               active="spec-sheets", wide=True))
