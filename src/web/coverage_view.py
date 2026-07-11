"""Coverage & Settlement ledger — the trust-first artifact (Phase 0).

The single page a quant-diligence + compliance team is sent *before* they ask the
hard questions. Its job is not to impress — it is to STATE THE BOUNDARY of every
dataset, so that when a PM trusts a Patearn read they are trusting a number whose
limits were declared in writing. Volunteering the limit is the product.

Governing rule (every line obeys it): *no characterisation, only counts and dates.*
Where a word could read as a judgment — of a company, a management, or our own edge
— it is replaced by the number behind it.

Built on the adversarial red-team's binding corrections:
  * leads with the CCI **robust-core funnel** (touched -> scored -> >=1 -> >=3 -> >=10
    resolved), never the flattering "symbols touched" breadth number;
  * a **tier x n_resolved** cross-tab that self-incriminates thin-sample A+ ;
  * fundamentals are labelled **modeled-availability**, never "point-in-time";
  * survivorship is stated WITH its archive floor + asymmetry + SME exclusion;
  * freshness shows **cadence + staleness + a visible pause/incident banner** and a
    one-line single-node / no-HA-DR honesty statement;
  * no performance claim anywhere — "percentile rank-gap", never alpha/Sharpe/sigma.

Isolation (the rs_section.py / news_view.py house pattern): a brand-new module that
imports ONLY the v2 design system (`ui_kit`) + the data layer (`provenance`). It adds
one route, touches no existing route, deletes nothing. Inert until a 1-line
`include_router` in main.py (gated on the parallel web-layer sessions freeing).

Route: GET /dash/coverage
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web import ui_kit as K
from src.web import ui_tokens as T
from src.automation import provenance as P

router = APIRouter()


# ── disclosure copy (rendered close to verbatim; institutional, factual tone) ──
COPY_PAGE = ("This page documents the coverage and known limits of every dataset behind Patearn. "
             "Each figure below is a count or a date reproducible from our own tables as of the "
             "stamped date. We publish the boundary of each dataset deliberately: a Patearn read "
             "should be trusted only to the extent its inputs are, and those inputs are stated here.")

COPY_MODELED = ("Fundamental history is assigned an availability date using a uniform modelled lag — "
                "90 days after period-end for annual results, 50 days for quarterly — applied "
                "identically to every company. This is a modelled approximation of when results "
                "became public, not an observed filing date. A company that filed late will appear "
                "knowable earlier than it was; one that filed early will appear unknown when it was "
                "already public. Accordingly these surfaces are labelled “modeled-availability” "
                "and must not be read as point-in-time. A true first-seen date is captured only going "
                "forward (it does not exist for historical periods).")

COPY_CCI = ("Concall Credibility (CCI) measures a management's stated guidance against the results "
            "that subsequently landed — a measurement of delivery-versus-guidance, not a judgment of "
            "management integrity. A company's credibility level becomes meaningful only once its "
            "guidance has resolved. Until then the level is held at a fixed ceiling and reflects only "
            "the quantification rate — how specific and falsifiable the guidance was — which is a "
            "disclosure metric, not evidence of delivery. Roughly one-third of scored names currently "
            "have no resolved promises, and many high bands rest on fewer than three. We therefore "
            "define a robust core of names with at least ten graded promises, and report credibility "
            "tiers for that core only. Momentum is undefined for the first period and stabilises after "
            "about four. Every figure carries its as-of call date and its resolved-promise count; "
            "verify each against the original transcript.")

COPY_SURVIVORSHIP = ("Our security universe is built from the raw daily bhav-copy archive, not a "
                     "current-constituents list. Delisted, suspended and surveillance-series names are "
                     "kept, so historical analysis can see companies that later disappeared rather than "
                     "only today's survivors. A company is followed across a symbol rename as one "
                     "continuous security where an ISIN handover confirms it; demergers, mergers and "
                     "schemes of arrangement are recorded as continuity-break events so a structural gap "
                     "is never mistaken for a price move. One asymmetry we state plainly: the "
                     "price/survivorship spine retains delisted names, while the fundamental history "
                     "covers the names listed today — the two universes are not identical.")

COPY_NOALPHA = ("Patearn's rankings express a percentile rank-gap — where a name sits on a given factor "
                "relative to its peers — not a forecast of returns. No claim of investment performance "
                "is made or implied anywhere in this product. The lead-time study that would test "
                "whether any of these signals precede price is not yet built; until it is, every score "
                "is a descriptor of present, point-in-time evidence, and should be treated as "
                "decision-support, not a prediction.")

COPY_SOURCE = ("Fundamental and concall data are presently obtained from public web sources (including "
               "Screener.in and BSE filings); price and delivery data derive from NSE's published "
               "bhav-copy archive. These sources are public and each figure links to its origin, but the "
               "present collection method is scraped, not a licensed feed. Migration to owned or licensed "
               "data sources is planned as part of a backend rebuild ahead of production distribution.")

COPY_SEBI = ("Patearn is an analytical decision-support tool that supports SEBI Research Analyst "
             "Regulations workflows (evidence, as-of dating, source linkage). It is informational only, "
             "is not investment advice or a recommendation, and is not a substitute for the registrations "
             "or reviews that distribution of research to others may require.")

COPY_INFRA = ("Single-node deployment; no high-availability / disaster-recovery today. Data-delivery SLA, "
              "freshness monitoring with alerting, and a SOC 2 / security path are on the procurement "
              "roadmap, not yet in place.")

COPY_MNAR = ("Concall coverage is missing-not-at-random: India's transcript mandate is phased by company "
             "size and era, so small-cap and earlier-period absence is systematic. A study restricted to "
             "names with concalls is implicitly tilted toward larger, more recent companies — read "
             "coverage with that selection in mind.")

COPY_VALIDATION = ("We test our own strategies and publish what fails. Every strategy we have backtested is "
                   "recorded with its results net of realistic cost (tier spread + slippage), walk-forward "
                   "2012–26, no look-ahead — the failures kept as visible as the wins. The honest verdict so "
                   "far: nothing we have built beats a Nifty 500 buy-and-hold net of cost. We state that "
                   "plainly rather than bury it, because a research process is only trustworthy if its "
                   "negative results are on the record. No performance claim follows from this surface — it is "
                   "the rigor evidence behind the product, not a strategy lens or a return promise.")

# the diligence checklist the screen pre-empts
PRINCIPLES = [
    ("Survivorship addressed first", "Universe built from the raw archive with delisted names retained; a survivorship-correct universe-as-of-date exists."),
    ("Point-in-time honesty is graduated", "Fundamentals are labelled modeled-availability with the exact lag disclosed; CCI is genuinely PIT by construction. We never call modelled data point-in-time."),
    ("Sample size travels with every score", "No tier or credibility read appears without its resolved-promise count and as-of date; a robust core is defined and tiers reported only within it."),
    ("No performance claim without a backtest", "The product speaks in percentile rank-gaps; the lead-time study is openly marked not-built."),
    ("Grain is never overstated", "Market-level data (participant OI, FII/DII flow) is labelled market-level; we do not claim per-name participant flow."),
    ("Absence is a first-class value", "Coverage gaps return coverage + n, never a fabricated number; “not covered”, “zero” and “not in source” are distinct states."),
    ("Every figure is sourced and reproducible", "Each count maps to a named table/column; each company-level claim links to its origin."),
    ("Characterisation is banned", "Copy states stated-vs-actual facts, never judgments of people."),
    ("Data provenance is declared", "Scraped-today vs licensed-later is stated as a known item, not buried."),
    ("The as-of clock is global and visible", "The whole page renders from one stamped moment; freshness is shown per class."),
]


# ── small render helpers ──────────────────────────────────────────────────────
def _n(v, dash="—"):
    """Thousands-separated int, or an em-dash for None/missing."""
    if v is None:
        return dash
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return K.esc(v)


def _days(a, b):
    """Calendar days between two ISO date strings (b - a), or None."""
    try:
        return (date.fromisoformat(str(b)[:10]) - date.fromisoformat(str(a)[:10])).days
    except (TypeError, ValueError):
        return None


def _staleness_pill(latest, as_of, cadence):
    """A freshness verdict pill from the gap between a class's latest date and the page as-of."""
    if not latest:
        return K.pill("no data", "neutral")
    d = _days(latest, as_of)
    if d is None:
        return K.pill(K.esc(str(latest)[:10]), "neutral")
    daily = "daily" in (cadence or "")
    if daily:
        kind = "up" if d <= 5 else "warn" if d <= 20 else "down"
    else:
        kind = "up" if d <= 120 else "warn" if d <= 400 else "down"
    lab = "current" if d <= (5 if daily else 120) else (f"{d}d old")
    return K.pill(lab, kind)


def _bar(label, value, total, kind="acc"):
    """A labelled proportional bar for the n_resolved distribution."""
    pct = round(100.0 * value / total, 1) if (value and total) else 0
    colour = {"acc": "var(--accent)", "up": "var(--up)", "warn": "var(--warn)",
              "down": "var(--down)", "cred": "var(--cred)"}.get(kind, "var(--accent)")
    return (f'<div class="cov-bar"><div class="cov-bar-l">{K.esc(label)}</div>'
            f'<div class="cov-bar-t"><div class="cov-bar-f" style="width:{pct}%;background:{colour}"></div></div>'
            f'<div class="cov-bar-v num">{_n(value)} <span class="mut">({pct}%)</span></div></div>')


_COV_CSS = """<style>
.cov-funnel{display:flex;gap:8px;align-items:stretch;flex-wrap:wrap}
.cov-step{flex:1;min-width:120px;background:var(--bg-1);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px 14px;position:relative}
.cov-step.core{border-color:var(--accent);background:var(--accent-dim)}
.cov-step .cs-n{font-size:22px;font-weight:600;font-family:var(--mono);font-variant-numeric:tabular-nums;line-height:1}
.cov-step .cs-l{font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink-3);margin-top:6px}
.cov-step .cs-arrow{position:absolute;right:-12px;top:50%;transform:translateY(-50%);color:var(--ink-3);z-index:1;font-size:13px}
.cov-bar{display:grid;grid-template-columns:130px 1fr 120px;gap:10px;align-items:center;margin:7px 0;font-size:12.5px}
.cov-bar-t{height:9px;background:var(--bg-1);border-radius:6px;overflow:hidden;border:1px solid var(--line)}
.cov-bar-f{height:100%;border-radius:6px}
.cov-bar-v{text-align:right;color:var(--ink-2)}
.cov-note{font-size:12.5px;color:var(--ink-2);line-height:1.6}
.cov-banner{border:1px solid var(--warn);background:rgba(246,183,60,.10);border-radius:var(--r-sm);padding:11px 14px;color:var(--ink);font-size:12.5px;display:flex;gap:9px;align-items:flex-start}
.cov-banner .d{width:7px;height:7px;border-radius:50%;background:var(--warn);box-shadow:0 0 7px var(--warn);margin-top:5px;flex:none}
.cov-x{display:grid;gap:2px}
.cov-x table{border-collapse:collapse;font-size:12px}
.cov-x th,.cov-x td{padding:6px 11px;text-align:right;border-bottom:1px solid var(--line)}
.cov-x th:first-child,.cov-x td:first-child{text-align:left}
</style>"""


# ── sections ──────────────────────────────────────────────────────────────────
def _funnel_step(value, label, core=False, arrow=True):
    cls = "cov-step core" if core else "cov-step"
    ar = '<div class="cs-arrow">→</div>' if arrow else ""
    return f'<div class="{cls}"><div class="cs-n">{_n(value)}</div><div class="cs-l">{K.esc(label)}</div>{ar}</div>'


def _section_glance(snap):
    cci = snap.get("cci", {})
    fn = cci.get("funnel", {})
    uni = snap.get("universe", {}) or {}
    core = fn.get("robust_core_ge10")
    # robust-core HEADLINE (red-team: the number a buyer should anchor on comes first)
    head = (
        '<div class="uk-row" style="margin-bottom:14px">'
        f'<div class="uk-card accent lift" style="flex:1.4;min-width:260px">'
        f'<div class="uk-eyebrow">CCI robust core {K.badge("the only delivery-graded set")}</div>'
        f'<div class="uk-stat"><div class="val cred">{_n(core)}</div>'
        f'<div class="dl mut">names with ≥10 graded promises — credibility here means tested '
        f'delivery, not disclosure</div></div></div>'
        f'<div class="uk-card" style="flex:1;min-width:200px">'
        f'<div class="uk-eyebrow">Universe (survivorship-correct)</div>'
        f'<div class="uk-stat"><div class="val">{_n(uni.get("total_securities"))}</div>'
        f'<div class="dl mut">securities ever observed · {_n(uni.get("active"))} active · '
        f'{_n(uni.get("delisted_or_inactive"))} delisted/inactive (retained)</div></div></div>'
        f'<div class="uk-card" style="flex:1;min-width:200px">'
        f'<div class="uk-eyebrow">Fundamentals availability</div>'
        f'<div class="uk-stat"><div class="val warn">modeled</div>'
        f'<div class="dl mut">annual +90d / quarterly +50d synthetic lag — not point-in-time (§6)</div>'
        f'</div></div></div>'
    )
    # the shrinking funnel (breadth is here, clearly downstream of the headline)
    steps = (
        _funnel_step(fn.get("touched"), "concall symbols touched") +
        _funnel_step(fn.get("scored"), "scored") +
        _funnel_step(fn.get("resolved_ge1"), "≥1 promise resolved") +
        _funnel_step(fn.get("resolved_ge3"), "≥3 resolved") +
        _funnel_step(fn.get("robust_core_ge10"), "robust core ≥10", core=True, arrow=False)
    )
    # Reconcile the funnel's "scored" with the resolved-promise distribution below it: the
    # two headline counts differ because "scored" is the LLM credibility *snapshot* set,
    # while the distribution/tier-matrix count the (slightly smaller) PIT credibility
    # *series* set (a series needs ≥1 settled period). Stating the gap inline pre-empts the
    # "why doesn't scored equal the distribution total?" question on the trust page.
    _buckets = (cci.get("n_resolved_buckets") or {})
    _series_n = sum(v for v in _buckets.values() if v) or None
    _scored = fn.get("scored")
    _recon = ""
    if isinstance(_scored, int) and isinstance(_series_n, int) and _scored != _series_n:
        _gap = _scored - _series_n
        _recon = (f' <b class="num">{_n(_scored)}</b> carry an LLM credibility snapshot; '
                  f'the resolved-promise distribution and tier matrix below count the '
                  f'<b class="num">{_n(_series_n)}</b> with a full point-in-time series '
                  f'(level + momentum), so they total {_n(_series_n)}, not {_n(_scored)} '
                  f'(the {_n(abs(_gap))}-name gap is names scored but without a settled series yet).')
    funnel = K.card(f'<div class="cov-funnel">{steps}</div>'
                    '<div class="cov-note mut" style="margin-top:11px">The headline is the robust core, '
                    'not the breadth: “symbols touched” counts every name with a concall on file, '
                    'most of which have few or no resolved promises yet. Coverage shrinks left-to-right; '
                    f'each step is a stricter, more honest count.{_recon}</div>',
                    eyebrow="CCI settlement funnel — honest, monotone, denominator-first")
    return f'<div style="margin-bottom:6px">{head}</div>{funnel}'


def _section_universe(snap):
    u = snap.get("universe", {}) or {}
    if u.get("status") == "security_master_empty":
        body = ('<div class="cov-note">' + K.esc(u.get("policy", "")) +
                ' <span class="mut">(survivorship spine not built in this database — counts unavailable here)</span></div>')
        return K.card(body, eyebrow="Universe construction & survivorship policy")
    breaks = u.get("continuity_breaks", {}) or {}
    ren = u.get("renames", {}) or {}
    rows = "".join(
        f'<tr><td class="sym">{K.esc(k)}</td><td class="num">{_n(v)}</td></tr>'
        for k, v in [
            ("Total securities ever observed", u.get("total_securities")),
            ("Currently listed & active", u.get("active")),
            ("Delisted / inactive (retained)", u.get("delisted_or_inactive")),
            ("Left-censored at archive floor", u.get("left_censored_at_floor")),
            ("Continuity-break events", sum(breaks.values()) if breaks else None),
            ("Renames confirmed (ISIN handover)", ren.get("confirmed")),
            ("Rename candidates (unconfirmed)", ren.get("candidates")),
        ])
    tbl = f'<div class="uk-tw" style="max-height:none"><table class="uk-t"><thead><tr><th>Metric</th><th>Count</th></tr></thead><tbody>{rows}</tbody></table></div>'
    floor = u.get("archive_floor")
    ceil_ = u.get("archive_ceiling")
    discl = "".join(f'<li>{K.esc(d)}</li>' for d in u.get("disclosures", []))
    meta = (f'<div class="cov-note" style="margin:10px 0 6px"><b>Archive span:</b> '
            f'<span class="num">{K.esc(floor)}</span> → <span class="num">{K.esc(ceil_)}</span>. '
            f'<b>As-of mechanism:</b> <span class="mut">{K.esc(u.get("as_of_mechanism",""))}</span></div>'
            f'<ul class="cov-note" style="margin:8px 0 0;padding-left:18px">{discl}</ul>')
    note = f'<div class="cov-note" style="margin-top:12px">{COPY_SURVIVORSHIP}</div>'
    return K.card(f'<div class="uk-row"><div style="flex:1;min-width:280px">{tbl}</div>'
                  f'<div style="flex:1.1;min-width:280px">{meta}</div></div>{note}',
                  eyebrow="Universe construction & survivorship policy", cls="lift")


def _section_matrix(snap):
    classes = snap.get("classes", []) or []
    head = ("<tr><th>Dataset</th><th>Source</th><th>Coverage</th><th>Grain</th>"
            "<th>Basis</th><th>Latest</th><th>Freshness</th></tr>")
    basis_kind = {"AS_TRADED": "up", "INGESTED": "acc", "EVENT": "acc",
                  "DERIVED": "neutral", "MODELED": "warn"}
    rows = ""
    as_of = snap.get("as_of")
    for cl in classes:
        nunit = cl.get("n_unit", "symbols")
        cov = f'{_n(cl.get("n"))} <span class="mut">{K.esc(nunit)}</span>'
        pa = cl.get("pct_active")
        if pa is not None:
            # The denominator is *today's active* set; a survivorship-inclusive archive
            # (delisted names retained — see Universe) legitimately exceeds it. Label such
            # cells "of all-time" so >100% reads as the intended breadth, not a bug, while
            # the exact count + ratio stay visible (no number is hidden).
            if pa > 100:
                cov += (f' <span class="mut">· {pa}% of all-time set</span>'
                        '<span class="uk-badge" title="Count spans every symbol ever observed, '
                        'including delisted/renamed series the archive retains, so it exceeds '
                        'today&#39;s active universe by design.">all-time</span>')
            else:
                cov += f' <span class="mut">· {pa}% of active</span>'
        bp = K.pill(cl.get("basis", "?").replace("_", " ").lower(), basis_kind.get(cl.get("basis"), "neutral"))
        note = f'<div class="mut" style="font-size:10.5px">{K.esc(cl["note"])}</div>' if cl.get("note") else ""
        mv = ' <span class="uk-badge" title="rows carry method/model version">vers</span>' if cl.get("method_versioned") else ""
        rows += (f'<tr><td class="sym">{K.esc(cl.get("label"))}{mv}{note}</td>'
                 f'<td style="text-align:left">{K.esc(cl.get("source",""))}</td>'
                 f'<td class="num">{cov}</td>'
                 f'<td style="text-align:left">{K.esc(cl.get("grain",""))}</td>'
                 f'<td style="text-align:right">{bp}</td>'
                 f'<td class="num">{K.esc(str(cl.get("latest") or "—")[:10])}</td>'
                 f'<td style="text-align:right">{_staleness_pill(cl.get("latest"), as_of, cl.get("cadence"))}</td></tr>')
    tbl = f'<div class="uk-tw"><table class="uk-t"><thead>{head}</thead><tbody>{rows}</tbody></table></div>'
    legend = ('<div class="cov-note mut" style="margin-top:10px">Basis — '
              '<b>as traded</b>: a real NSE exchange date · <b>ingested</b>: a real first-seen/fetch time · '
              '<b>event</b>: a real event date · <b>derived</b>: computed from a real-dated source · '
              '<b>modeled</b>: a synthetic uniform lag (see §6). “days” coverage = distinct '
              'trading days for market-level/index classes (which have no per-stock split). '
              'A coverage shown <b>“of all-time set”</b> counts every symbol the archive has ever '
              'observed (delisted/renamed series are retained — see Universe), so it exceeds '
              'today’s active universe by design; the active-set ratio is shown only where the '
              'dataset is a subset of currently-active names.</div>')
    return K.card(tbl + legend, eyebrow="Per-data-class coverage matrix")


def _section_cci(snap):
    cci = snap.get("cci", {}) or {}
    buckets = cci.get("n_resolved_buckets", {}) or {}
    total_named = sum(buckets.values()) if buckets else 0
    dist = (_bar("0 resolved", buckets.get("0"), total_named, "down") +
            _bar("1–2 resolved", buckets.get("1-2"), total_named, "warn") +
            _bar("3–9 resolved", buckets.get("3-9"), total_named, "acc") +
            _bar("≥10 (robust core)", buckets.get(">=10"), total_named, "up"))
    unproven = cci.get("unproven_ceiling")
    momr = cci.get("momentum_ready")
    mom4 = cci.get("momentum4_ready")
    tape = cci.get("tape", {}) or {}
    # tier x n_resolved cross-tab (self-incriminates thin-sample A+)
    cross = cci.get("tier_x_nresolved", {}) or {}
    order = ["A+", "A", "B", "C", "D"]
    cols = ["0", "1-2", "3-9", ">=10"]
    xrows = ""
    for tier in [t for t in order if t in cross] + [t for t in cross if t not in order]:
        cells = "".join(f'<td class="num">{_n(cross[tier].get(c, 0))}</td>' for c in cols)
        xrows += f'<tr><td class="sym">{K.esc(tier)}</td>{cells}</tr>'
    xtab = ("" if not cross else
            '<div class="cov-x" style="margin-top:6px"><table><thead><tr><th>Tier</th>'
            '<th>0</th><th>1–2</th><th>3–9</th><th>≥10</th></tr></thead>'
            f'<tbody>{xrows}</tbody></table></div>'
            '<div class="cov-note mut" style="margin-top:6px">Tier × resolved-promise count. '
            'A high tier in a low-resolved column is a thin-sample read, shown here on purpose — a tier is '
            'only as strong as the count beside it.</div>')
    left = K.card(
        '<div class="uk-eyebrow">Resolved-promise distribution (the honesty bar)</div>' + dist +
        f'<div class="cov-note" style="margin-top:12px">{COPY_CCI}</div>',
        cls="lift")
    right = K.card(
        '<div class="uk-eyebrow">Robustness</div>'
        f'<div class="cov-note">Unproven-ceiling names (no resolved guidance — level capped, not earned): '
        f'<b class="num">{_n(unproven)}</b></div>'
        f'<div class="cov-note">Momentum-ready (≥2 periods): <b class="num">{_n(momr)}</b> · '
        f'stable slope (≥4): <b class="num">{_n(mom4)}</b></div>'
        f'<div class="cov-note">Tape: <span class="up">{_n(tape.get("EARNING_TRUST"))} earning-trust</span> · '
        f'<span class="down">{_n(tape.get("DETERIORATION"))} deterioration</span></div>'
        '<div class="uk-eyebrow" style="margin-top:14px">Tier × resolved count</div>' + (xtab or '<div class="mut cov-note">no scored names in this database</div>'))
    banner = (f'<div class="cov-banner"><span class="d"></span><div>{K.esc(cci.get("paused_note",""))}</div></div>')
    return (f'<div style="margin-bottom:12px">{banner}</div>'
            f'<div class="uk-row" style="align-items:flex-start"><div style="flex:1.3;min-width:320px">{left}</div>'
            f'<div style="flex:1;min-width:280px">{right}</div></div>')


def _section_modeled(snap):
    la = snap.get("lag_audit", {}) or {}
    fh = la.get("fundamentals_history", {}) if isinstance(la, dict) else {}
    status = fh.get("status") if isinstance(fh, dict) else None
    if status == "ok":
        audit = (f'<div class="cov-note">Measured modelled-lag error (real first-seen − modelled date): '
                 f'median <b class="num">{fh.get("median")}d</b>, p10 {fh.get("p10")}d / p90 {fh.get("p90")}d, '
                 f'over <b class="num">{_n(fh.get("n"))}</b> matched periods. '
                 f'Look-ahead-injecting cases (modelled date earlier than real): '
                 f'<b class="num">{_n(fh.get("n_leaks"))}</b>.</div>')
    else:
        audit = ('<div class="cov-note mut">Lag-accuracy audit: not yet measurable — real first-seen dates '
                 'accrue only going forward (no historical periods to compare against). This will report a '
                 'measured error distribution once forward captures and a filing-date backfill exist.</div>')
    formula = ('<div class="cov-note"><b>The rule:</b> '
               '<code>report_date = period_end + 90d (annual) / 50d (quarterly)</code> — a uniform synthetic '
               'lag applied to every company identically. <b>Two failure modes:</b> late filers leak '
               '(treated as knowable earlier than they were); early filers are wrongly greyed (treated as '
               'unknown when already public).</div>')
    return K.card(formula + f'<div class="cov-note" style="margin-top:10px">{COPY_MODELED}</div>'
                  f'<div style="margin-top:10px">{audit}</div>',
                  eyebrow="Modeled-vs-filed disclosure")


def _section_provenance_story(conn=None):
    """Replay-the-Tape EVIDENCE on the Coverage page: the *effective* look-ahead leak
    headline + the 3-beat narrative + the worst/safe per-period receipts a skeptical
    allocator can audit. Renders provenance.provenance_narrative() so every surface tells
    the SAME story (L4 W3 helper). Descriptive, NO edge claim; degrades to a note before
    real BSE filing dates accrue (forward-only). Never 500s (a trust page must not)."""
    try:
        nar = P.provenance_narrative(conn)
    except Exception:  # noqa: BLE001
        nar = None
    if not isinstance(nar, dict) or nar.get("status") != "ok":
        msg = (isinstance(nar, dict) and nar.get("headline")) or (
            "Zero-look-ahead receipts accrue going forward — real BSE filing dates are "
            "captured prospectively, then compared against the modelled date.")
        return K.card(f'<div class="cov-note mut">{K.esc(str(msg))}</div>',
                      eyebrow="Replay the Tape — zero look-ahead receipts")

    def _receipt(r, kind, tone):
        if not isinstance(r, dict):
            return ""
        ed = r.get("err_days")
        ed_txt = f'{ed:+d}d' if isinstance(ed, int) else K.esc(str(ed))
        pt = (" " + K.esc(str(r.get("period_type")))) if r.get("period_type") else ""
        return (f'<div class="cov-note" style="margin-top:8px"><span class="{tone}">{K.esc(kind)}</span> — '
                f'<b>{K.esc(str(r.get("symbol", "")))}</b> {K.esc(str(r.get("period", "")))}{pt}: '
                f'modelled <span class="num">{K.esc(str(r.get("modeled", "")))}</span> vs '
                f'real <span class="num">{K.esc(str(r.get("real", "")))}</span> '
                f'(<span class="num">{ed_txt}</span>)</div>')

    head = f'<div class="cov-banner"><div><b>{K.esc(str(nar.get("headline", "")))}</b></div></div>'
    paras = "".join(f'<div class="cov-note" style="margin-top:9px">{K.esc(str(p))}</div>'
                    for p in (nar.get("paragraphs") or []))
    receipts = (_receipt(nar.get("worst"), "Worst would-have-leaked", "warn")
                + _receipt(nar.get("conservative"), "Representative conservative", "mut"))
    rcap = ('<div class="cov-note mut" style="margin-top:10px">Receipts — the real BSE filing date vs the '
            'modelled report date, per period. Positive = modelled earlier than real (a backtest would have '
            'seen it early); negative = conservative (greyed while already public).</div>') if receipts else ""
    return K.card(head + paras + receipts + rcap,
                  eyebrow="Replay the Tape — zero look-ahead receipts")


def _section_methodology():
    blocks = [
        ("No proven performance", COPY_NOALPHA),
        ("Coverage is missing-not-at-random", COPY_MNAR),
        ("Data source & licensing", COPY_SOURCE),
        ("Infrastructure & SLA", COPY_INFRA),
        ("Regulatory posture", COPY_SEBI),
    ]
    body = "".join(f'<div style="margin-bottom:13px"><div class="uk-eyebrow">{K.esc(t)}</div>'
                   f'<div class="cov-note">{c}</div></div>' for t, c in blocks)
    return K.card(body, eyebrow="Methodology & limitations")


def _section_degradation():
    contract = ('<div class="cov-note">When you query a name we do not cover for a given dataset, Patearn '
                'shows the coverage status and the sample size — never a fabricated value. Absence is '
                'reported as absence. Three states are kept distinct: <b>not covered</b> (outside the '
                'dataset), <b>zero</b> (a real measured zero), and <b>not in source</b> (the field does not '
                'exist in the upstream feed).</div>')
    examples = (
        '<div class="cov-note" style="margin-top:10px">'
        '<b>RELIANCE</b> — Prices ✓ (daily) · Fundamentals ✓ <span class="warn">modeled-availability</span> · '
        'CCI ✓ robust core (n_resolved ≥10) · Participant flow: <span class="mut">market-level only, no per-stock split</span>.'
        '<br><b>A thin micro-cap</b> — Prices ✓ · Fundamentals: <span class="mut">not covered (outside the listed-today set)</span> · '
        'CCI: <span class="mut">quantification-rate only, n_resolved = 0 (unproven)</span> · F&amp;O: <span class="mut">not an F&amp;O underlying</span>.</div>')
    return K.card(contract + examples, eyebrow="Graceful degradation — what an uncovered ticker shows")


def _section_principles():
    items = "".join(
        f'<div style="margin-bottom:11px"><div style="display:flex;gap:8px;align-items:center">'
        f'{K.pill(str(i+1), "acc")}<b>{K.esc(t)}</b></div>'
        f'<div class="cov-note mut" style="margin-top:3px">{K.esc(d)}</div></div>'
        for i, (t, d) in enumerate(PRINCIPLES))
    return K.card(items, eyebrow="Trust-design principles — the diligence checklist this page pre-empts")


def _section_validation():
    """The strategy-validation story: the honest-backtest rigor evidence, surfaced as a
    Trust artifact with a link to the full /dash/testing record. Descriptive-only; the
    §C falsification stands — we present validation, never a return promise."""
    verdict = (
        '<div class="cov-banner"><span class="d" style="background:var(--down);box-shadow:0 0 7px var(--down)"></span>'
        '<div><b>Headline verdict:</b> across every strategy we have backtested, '
        '<b>none beats a Nifty&nbsp;500 buy-and-hold net of cost</b> '
        '(the bar: Sharpe&nbsp;0.89 / CAGR&nbsp;15.3% / MaxDD&nbsp;&minus;29%). '
        'We report that rather than bury it.</div></div>')
    link = ('<div style="margin-top:14px"><a href="/dash/testing" '
            'style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line-2);'
            'background:var(--bg-2);color:var(--ink-2);border-radius:9px;padding:8px 14px;'
            'text-decoration:none;font-size:13px">Open the full validation record (every backtest + holdings) &rarr;</a></div>')
    return K.card(f'<div style="margin-bottom:12px">{verdict}</div>'
                  f'<div class="cov-note">{COPY_VALIDATION}</div>{link}',
                  eyebrow="Strategy validation — we test our strategies and report what fails")


# ── progressive-disclosure tabs (the best-in-class data-coverage shape: a lead
# trust band + tabbed drill-down, never one long wall — Daloopa/CRSP pattern) ──
_COV_TAB_CSS = """<style>
.cov-tabs{display:flex;gap:2px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin:20px 0 16px}
.cov-tab{font:inherit;font-size:13px;cursor:pointer;background:none;border:0;color:var(--ink-3);
  padding:9px 15px;border-bottom:2px solid transparent;margin-bottom:-1px}
.cov-tab:hover{color:var(--ink-2)}
.cov-tab.on{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
.cov-pane{display:none}.cov-pane.on{display:block}
</style>"""
_COV_TAB_JS = ("<script>(function(){var t=document.querySelectorAll('.cov-tab'),"
               "p=document.querySelectorAll('.cov-pane');"
               "t.forEach(function(b){b.addEventListener('click',function(){var id=b.dataset.pane;"
               "t.forEach(function(x){x.classList.toggle('on',x.dataset.pane===id);});"
               "p.forEach(function(x){x.classList.toggle('on',x.id==='covpane-'+id);});});});"
               "})();</script>")


# ── assembly ──────────────────────────────────────────────────────────────────
def render_coverage(conn=None) -> str:
    """Build the full ledger body. Defensive per-section: one failing section degrades
    to a small note, never blanks the page."""
    try:
        snap = P.coverage_snapshot(conn)
    except Exception as e:  # noqa: BLE001 — a trust page must never 500
        return (_COV_CSS + K.card(
            f'<div class="cov-note">The coverage snapshot could not be built in this environment '
            f'(<span class="mut">{K.esc(e)}</span>). On the analytics host this renders live counts.</div>',
            eyebrow="Coverage & Settlement ledger"))

    as_of = snap.get("as_of")
    build = snap.get("build_at")
    header = (
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px">'
        f'<h1 class="uk-h1">Coverage &amp; Settlement ledger</h1>'
        f'{K.badge("the limits, stated in writing")}</div>'
        '<div class="sec" style="margin-bottom:6px"><a class="row" style="display:inline" '
        'href="/dash/glossary">📖 Glossary &amp; methodology →</a> — every custom metric on this site, defined. '
        '&nbsp;<a class="row" style="display:inline" href="/dash/spec-sheets">🧪 Detection spec-sheets →</a> '
        '— every pre-registered study, failures included.</div>'
        f'<div class="sec" style="margin-bottom:6px">Page as of <span class="num">{K.esc(str(as_of) or "—")}</span> '
        f'· built <span class="num">{K.esc(str(build) or "")}</span> · scope: NSE-listed Indian equities '
        f'(EQ/BE/BZ; SME excluded)</div>'
        f'<div class="cov-note" style="max-width:880px;margin-bottom:10px">{COPY_PAGE}</div>'
        # Trails off the trust front-door. Replay the Tape leads (the D-PITCH-1/4 lead wedge):
        # a PROMINENT accent chip, descriptive framing only ("scrub to a past date; zero
        # look-ahead") — never a leaderboard/return/edge claim. The print memo follows as the
        # secondary, muted action.
        '<div style="display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:0 0 18px">'
        '<a href="/dash/replay" '
        'style="display:inline-flex;align-items:center;gap:8px;border:1px solid var(--accent);'
        'background:var(--accent-dim);color:var(--ink);border-radius:9px;padding:9px 15px;'
        'text-decoration:none;font-size:13px;font-weight:600">'
        '<span aria-hidden="true">&#9654;</span> Replay the Tape'
        '<span class="mut" style="font-weight:400">&nbsp;— scrub to a past date, zero look-ahead</span>'
        ' &rarr;</a>'
        '<a href="/dash/coverage/memo" '
        'style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line-2);'
        'background:var(--bg-2);color:var(--ink-2);border-radius:9px;padding:8px 14px;'
        'text-decoration:none;font-size:13px">Export coverage &amp; provenance memo &rarr;</a>'
        # Evidence pack (P-04): the one-document procurement assembly (spec-sheets +
        # this ledger's boundary + season SLA + replay pointer), print-CSS → PDF.
        '<a href="/dash/evidence-pack" '
        'style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line-2);'
        'background:var(--bg-2);color:var(--ink-2);border-radius:9px;padding:8px 14px;'
        'text-decoration:none;font-size:13px">Evidence pack (print) &rarr;</a>'
        # Replay any date (P-05): the LIVE counterpart of Replay-the-Tape — any symbol,
        # any date, through the entitled /v1 API, knowable clock stamped (D104).
        '<a href="/dash/replay-any-date" '
        'style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line-2);'
        'background:var(--bg-2);color:var(--ink-2);border-radius:9px;padding:8px 14px;'
        'text-decoration:none;font-size:13px">Replay any date (live API) &rarr;</a>'
        # Move anatomy (deep-data sprint): the features event panel as a descriptive fingerprint —
        # what precedes a big move (momentum/RS elevated, delivery suppressed) + the MFE/MAE envelope.
        '<a href="/dash/move-anatomy" '
        'style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line-2);'
        'background:var(--bg-2);color:var(--ink-2);border-radius:9px;padding:8px 14px;'
        'text-decoration:none;font-size:13px">Move anatomy (what precedes a move) &rarr;</a>'
        # How to read the charts (deep-data sprint): the beginner's visual reading guide — the
        # companion to the Glossary, teaching the site's chart shapes in plain words.
        '<a href="/dash/reading-guide" '
        'style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line-2);'
        'background:var(--bg-2);color:var(--ink-2);border-radius:9px;padding:8px 14px;'
        'text-decoration:none;font-size:13px">How to read the charts &rarr;</a>'
        '</div>'
    )

    def _safe(fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001
            return K.card(f'<div class="cov-note mut">section unavailable: {K.esc(e)}</div>')

    # Lead trust band (always visible) = the anchor facts; the 9 former sections fold
    # into 5 progressive-disclosure tabs so the page reads summary-first, not a wall.
    _tabs = [
        ("universe", "Universe & survivorship",
         [(_section_universe, snap), (_section_matrix, snap), (_section_cci, snap)]),
        ("freshness", "Freshness", [(_section_modeled, snap)]),
        ("provenance", "Provenance & lineage", [(_section_provenance_story, conn), (_section_registry,)]),
        ("validation", "Strategy validation", [(_section_validation,)]),
        ("methodology", "Methodology", [(_section_methodology,), (_section_degradation,)]),
        ("limits", "Limits", [(_section_principles,)]),
    ]
    tabbar = '<div class="cov-tabs">' + "".join(
        f'<button class="cov-tab{" on" if i == 0 else ""}" data-pane="{tid}" type="button">{K.esc(lbl)}</button>'
        for i, (tid, lbl, _f) in enumerate(_tabs)) + '</div>'
    panes = "".join(
        f'<div class="cov-pane{" on" if i == 0 else ""}" id="covpane-{tid}">'
        + "".join(_safe(*spec) for spec in fns) + '</div>'
        for i, (tid, _lbl, fns) in enumerate(_tabs))
    body = (_COV_CSS + _COV_TAB_CSS + header
            + _safe(_section_glance, snap)      # the lead trust band
            + tabbar + panes + _COV_TAB_JS)
    return body


# ── the export artifact: a print-ready, dated, sourced Coverage & Provenance memo ──
# The compliance/provenance tier made tangible (the LEAD wedge post-§C-falsification):
# a buyer's diligence/compliance desk prints this to PDF as a dated, sourced audit
# record. Reuses the live ledger sections + adds the per-data-class provenance registry
# (the audit fingerprint) and a sourced footer. @media print flips ui_kit to a light
# document theme via its CSS variables.

def _section_registry():
    """The provenance registry — every data class, its source, cadence + timestamp
    basis. The audit fingerprint: exactly what is behind every number, and which
    dates are MODELED vs real."""
    try:
        rows = P.provenance_registry_digest()
    except Exception as e:  # noqa: BLE001
        return K.card(f'<div class="cov-note mut">registry unavailable: {K.esc(e)}</div>')
    rows = sorted(rows, key=lambda r: (str(r.get("source") or ""), str(r.get("key") or "")))
    out = ""
    for r in rows:
        basis = str(r.get("basis") or "")
        bcls = "warn" if basis == "MODELED" else ("acc" if basis in ("AS_TRADED", "INGESTED") else "neutral")
        out += (f'<tr><td class="sym">{K.esc(r.get("key"))}</td>'
                f'<td style="text-align:left">{K.esc(r.get("label") or "")}</td>'
                f'<td style="text-align:left">{K.esc(r.get("source") or "")}</td>'
                f'<td style="text-align:left">{K.esc(r.get("cadence") or "")}</td>'
                f'<td style="text-align:right">{K.pill(basis or "—", bcls)}</td></tr>')
    head = ('<tr><th style="text-align:left">Key</th><th style="text-align:left">Dataset</th>'
            '<th style="text-align:left">Source</th><th style="text-align:left">Cadence</th>'
            '<th>Timestamp basis</th></tr>')
    note = (f'<div class="cov-note" style="margin-bottom:8px">Every dataset behind Patearn, its origin, '
            f'refresh cadence and timestamp basis. <b>MODELED</b> = an availability date we estimate '
            f'(period-end + a uniform lag) until a real exchange filing date is captured; everything else '
            f'carries an as-traded or ingested timestamp. {len(rows)} data classes.</div>')
    return f'{note}<div class="uk-tw"><table class="uk-t"><thead>{head}</thead><tbody>{out}</tbody></table></div>'


_MEMO_PRINT_CSS = """<style>
.memo-actions{display:flex;gap:8px;margin:0 0 18px;flex-wrap:wrap}
.memo-actions a,.memo-actions button{font:inherit;font-size:13px;cursor:pointer;border:1px solid var(--line-2);
  background:var(--bg-2);color:var(--ink-2);border-radius:9px;padding:8px 14px;text-decoration:none}
.memo-actions a:hover,.memo-actions button:hover{border-color:var(--accent);color:var(--ink)}
.memo-foot{margin-top:26px;padding-top:14px;border-top:1px solid var(--line);font-size:11.5px;
  color:var(--ink-3);line-height:1.55;max-width:880px}
@media print{
  .uk{--bg-0:#fff;--bg-1:#fff;--bg-2:#fff;--bg-3:#f4f6f9;--line:#d0d7de;--line-2:#b8c2cc;
      --ink:#0b0f17;--ink-2:#39424e;--ink-3:#5d6b7a;--shadow:none;--glass:none;background:#fff!important}
  .memo-actions{display:none!important}
  .uk-card,.uk-tw{box-shadow:none!important;break-inside:avoid}
  .uk-page{max-width:none!important;padding:0!important}
  a{color:#0b0f17!important}
  thead{display:table-header-group}
  /* the memo keeps its own single .memo-foot — suppress the shared foundation's print footer
     (ui_tokens body::after) so the printed memo output is unchanged after Phase-4 de-dup. */
  body::after{content:none!important}
}
</style>"""


def render_coverage_memo(conn=None) -> str:
    """The print-ready memo body (document, not a dashboard page)."""
    try:
        snap = P.coverage_snapshot(conn)
    except Exception:  # noqa: BLE001
        snap = {}
    as_of = snap.get("as_of")
    build = snap.get("build_at")

    def _safe(fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001
            return K.card(f'<div class="cov-note mut">section unavailable: {K.esc(e)}</div>')

    def _h(t):
        return f'<div class="uk-eyebrow" style="margin:22px 0 10px;font-size:12px;color:var(--ink-2)">{K.esc(t)}</div>'

    header = (
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:2px">'
        '<h1 class="uk-h1">Patearn &mdash; Coverage &amp; Provenance Memo</h1></div>'
        f'<div class="sec" style="margin-bottom:14px">Data as of <span class="num">{K.esc(str(as_of) or "—")}</span> '
        f'· generated <span class="num">{K.esc(str(build) or "—")}</span> · scope: NSE-listed Indian equities '
        f'(EQ/BE/BZ; SME excluded)</div>'
        '<div class="memo-actions">'
        '<button onclick="window.print()">Print / save as PDF</button>'
        '<a href="/dash/coverage">Back to the live ledger</a></div>'
        f'<div class="cov-note" style="max-width:880px;margin-bottom:8px">{COPY_PAGE}</div>'
    )
    foot = (
        '<div class="memo-foot">'
        "Every figure above is a count or date reproducible from Patearn's own tables as of the stated date. "
        'Sources: NSE bhav-copy (as-traded prices &amp; volumes); Screener.in and BSE corporate filings '
        '(fundamentals, concall transcripts); NSE/BSE corporate announcements (events). Concall credibility is a '
        '<b>descriptive</b> diligence lens &mdash; an independent point-in-time backtest found no validated long/short/'
        'risk edge, so it is never presented as a ranked buy/sell signal. &ldquo;MODELED&rdquo; availability dates are '
        'a uniform-lag estimate (period-end + a fixed lag) pending capture of the real exchange filing date. '
        'This document is intended to support SEBI (Research Analysts) record-keeping practice; it does not by itself '
        'satisfy any regulatory obligation. Not investment advice. &copy; Patearn.'
        '</div>'
    )
    return (
        _COV_CSS + _MEMO_PRINT_CSS + header +
        _safe(_section_glance, snap) +
        _h("Universe construction & survivorship") + _safe(_section_universe, snap) +
        _h("Per-data-class coverage") + _safe(_section_matrix, snap) +
        _h("Concall credibility — settlement & robustness") + _safe(_section_cci, snap) +
        _h("Modeled-vs-filed availability") + _safe(_section_modeled, snap) +
        _h("Data provenance registry") + _safe(_section_registry) +
        _h("Methodology & limitations") + _safe(_section_methodology) +
        foot
    )


def _memo_shell(body: str) -> str:
    # Colour-alignment Phase 4: ui_kit no longer re-hardcodes the tokens in its `.uk` scope,
    # so this standalone memo (the one K.css() consumer that is NOT built via K.shell) must
    # itself carry the `:root` source of truth. Prepend the shared foundation. The memo keeps
    # its own `.uk`-scoped print flip (_MEMO_PRINT_CSS), which also neutralises the foundation's
    # print footer so the printed memo output is unchanged.
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Coverage &amp; Provenance Memo · patearn</title>'
            f'{T.tokens_css()}{K.css()}</head><body style="margin:0"><div class="uk">'
            f'<div class="uk-page" style="max-width:940px">{body}</div></div></body></html>')


@router.get("/dash/coverage/memo", response_class=HTMLResponse)
def coverage_memo() -> HTMLResponse:
    return HTMLResponse(_memo_shell(render_coverage_memo()))


@router.get("/dash/coverage", response_class=HTMLResponse)
def coverage_page() -> HTMLResponse:
    # The v2 chrome carries the COMPLETE site nav (one nav contract, no dead-end) —
    # sourced from v2_surfaces.site_nav so it mirrors the live dashboard nav + the
    # v2 surfaces. Imported lazily to avoid any import-order coupling.
    from src.web import v2_surfaces as V
    nav = K.nav_links(V.site_nav("coverage"))
    sub = K.subnav([("Coverage & Settlement", "/dash/coverage", True)])
    return HTMLResponse(K.shell("Coverage & Settlement · patearn", render_coverage(),
                                active="markets", sub=sub, nav_html=nav))
