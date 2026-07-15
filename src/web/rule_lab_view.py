"""/dash/rule-lab — render layer for the Rule-lab (D134 §4-H build step 4; UNMOUNTED this round).

PURE RENDER FUNCTIONS ONLY: (verdict dict, query params) -> HTML/CSV strings. No FastAPI, no
router, no DB access — stdlib + the shared readability scaffold (infographics, glossary). The
LANE-H build constraint bans web-surface mounting and edits to lens_registry/v2_surfaces, so
mounting is the integration lane's step. This module is deliberately scanned by
tests/test_compliance_language_gate.py (it lives in src/web) — the SEBI lexicon covers every
string here by construction.

INTEGRATION CHECKLIST (docs/rule-lab-design.md §7, all 12 rows — status from THIS lane):
   1  Registry entry      -> INTEGRATION: Lens("rule-lab","Rule lab","stock","trust","/dash/rule-lab")
                             (lens_registry is FORKED on the box - anchored insert, never scp)
   2  Durable mount       -> INTEGRATION: anchored insert in v2_surfaces._ROUTER_SPECS; the route
                             wraps render_page/render_csv; POST /dash/rule-lab/run queues the
                             gauntlet (Review-Inbox pattern, design §7 run-cost note); owner-gate
                             via the tracker_gate middleware pattern (anonymous = demo verdict)
   3  Education minimum   -> BUILT here: bottom_line + plain + how_to_read_link + gloss on metrics
   4  Honesty fence       -> BUILT here: infographics.fence("not_reco"); verdict labels are ledger
                             vocabulary only (REJECTED / WEAKER-THAN-BENCHMARK / CONDITIONAL /
                             NEW-BENCHMARK / NO-VERDICT) - never action verbs
   5  Glossary keys       -> INTEGRATION: append to docs/metrics-glossary.md (auto-folds into Pat);
                             paste-ready block at the bottom of this docstring
   6  Pat registration    -> BUILT: src/pat/rulelab_flow.py (logic); INTEGRATION: engine.route()
                             lazy-import line + web.py render + PAT_DATA entry in
                             tests/test_pat_coverage.py
   7  Strategy doc        -> INTEGRATION (deviation, documented): docs/strategies/rule-lab.md +
                             strategies_view._PAGES row + README matrix + Origin: HOUSE must land
                             in the SAME commit, and _PAGES lives in an existing file this lane
                             may not edit - test_strategy_docs_coverage fails on a doc without
                             its _PAGES row, so BOTH go to the integration commit together
   8  Export              -> BUILT here: render_csv (server-side format=csv - roster + numbers)
   8b URL state           -> BUILT here: spec_from_query/query_from_spec; the querystring IS the
                             canonical rule (and its text IS the prereg target)
   9  Symbol links        -> BUILT here: roster cells -> /dash/stock?sym= (sym, never symbol)
  10  Home exposure       -> deliberately NOT on home at v1 (owner-only; design §7 row 10)
  11  Writes are POST     -> BUILT here: the run form is method=post (running writes prereg +
                             inbox rows); GET only ever renders
  12  State doc           -> INTEGRATION: PROJECT_STATE key-paths + decision-log in the merge
                             commit (state:skip debt, precedent b5e9e6d)

Glossary paste-block for docs/metrics-glossary.md (words-first names - the S153 D/E lesson):
  - **Placebo p95.** The 95th percentile of the null distribution: the same book rebuilt N
    times with RANDOM picks (same universe, same size, same costs). A rule must beat this,
    not merely beat zero - luck has a high bar. *Source:* evlib placebo machinery.
  - **Capacity breakpoint.** The AUM (Rs cr) at which participation-cost impact kills the
    edge - the largest AUM whose net Sharpe still beats the benchmark. A rule with no stated
    capacity is not a result. *Source:* cost_participation grid scan.
  - **Both halves.** Walk-forward split 2012-18 vs 2019-26: a rule must beat the benchmark in
    BOTH halves or it is noise. *Source:* factory.slice_stats.
  - **Prereg gate hash.** sha256 of the frozen rule text, recorded BEFORE the run; first
    registration wins. Tamper-evident: re-deriving the hash must match. *Source:* prereg
    discipline (rule_lab_prereg).
  - **Flat cost only.** A qualifier warning that a result survives only under flat per-trade
    cost assumptions, not participation-real impact (the C-BLEND lesson: 1.32 flat became
    0.17 at Rs50cr). Travels with the verdict forever.
"""
from __future__ import annotations

import csv
import io
import json
from html import escape as _esc

from src.web import infographics as ifx
from src.web.glossary import gloss
from src.automation.rule_lab import (
    UNIVERSES, SIGNALS, FILTERS, VETOES, HOLDS, TAKE_MIN, TAKE_MAX,
    BLOCKING_SOURCE, RuleError, RuleSpec, compile_rule, spec_from_params,
)

BOTTOM_LINE = ("Write a rule; we run it through the same gauntlet as our own studies "
               "and tell you honestly if it works.")

_NUM_ORDER = (  # net FIRST — gross is a footnote (design §3 stage 5)
    ("net_sharpe", "net Sharpe"), ("gross_sharpe", "gross Sharpe"),
    ("flat_sharpe", "flat-cost Sharpe"), ("alpha", "alpha (ann.)"), ("beta", "beta"),
    ("maxdd", "max drawdown"), ("half1", "half 1 (2012-18)"), ("half2", "half 2 (2019-26)"),
    ("placebo_p95", "placebo p95"), ("observed", "observed"), ("emp_p", "empirical p"),
    ("ann_cost_pct", "annual cost %"), ("turnover", "turnover/rebalance"),
    ("bench_net", "benchmark (Nifty-500 net)"),
)


# ------------------------------------------------------------------ URL state (row 8b)
def query_from_spec(spec: RuleSpec) -> dict:
    """The whole rule as URL params — a shared URL reproduces the verdict exactly."""
    q = {"u": spec.universe, "rank": spec.signal, "n": str(spec.take), "hold": spec.hold}
    if spec.filters:
        q["where"] = ",".join(spec.filters)
    if spec.vetoes:
        q["veto"] = ",".join(spec.vetoes)
    return q


def spec_from_query(params: dict) -> RuleSpec:
    """?u=liquid500&rank=mom12&where=not_extended&n=25&hold=quarterly[&veto=...] -> RuleSpec.
    Raises RuleError on any token outside the closed vocabulary."""
    split = lambda v: [p for p in str(v or "").split(",") if p.strip()]
    return spec_from_params(
        universe=params.get("u", ""), signal=params.get("rank", ""),
        take=params.get("n", ""), hold=params.get("hold", ""),
        filters=split(params.get("where")), vetoes=split(params.get("veto")))


# ------------------------------------------------------------------ CSV export (row 8)
def render_csv(verdict: dict) -> tuple:
    """(filename, csv_text): the verdict numbers + verbatim citations + the roster."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["field", "value"])
    w.writerow(["rule_text", verdict.get("rule_text", "")])
    w.writerow(["rule_hash", verdict.get("rule_hash", "")])
    w.writerow(["prereg_ref", verdict.get("prereg_ref", "")])
    w.writerow(["verdict", verdict.get("verdict", "")])
    w.writerow(["qualifier", verdict.get("qualifier") or ""])
    nums = verdict.get("numbers") or {}
    for key, label in _NUM_ORDER:
        if key in nums:
            w.writerow([label, "" if nums[key] is None else nums[key]])
    if nums.get("capacity_inr") is not None:
        w.writerow(["capacity (Rs cr)", float(nums["capacity_inr"]) / 1e7])
    for c in verdict.get("ledger_citations") or []:
        w.writerow(["blocking_citation", c])
    if verdict.get("survivor_note"):
        w.writerow(["survivor_note", verdict["survivor_note"]])
    w.writerow([])
    w.writerow(["roster_symbol"])
    for s in verdict.get("roster") or []:
        w.writerow([s])
    h = (verdict.get("rule_hash") or "rule")[:12]
    return f"rule-lab-{h}.csv", buf.getvalue()


# ------------------------------------------------------------------ HTML pieces
def _fmt(v, pct=False) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _esc(str(v))
    if f != f:
        return "—"
    return f"{f * 100:.1f}%" if pct else f"{f:.2f}"


def _numbers_table(nums: dict) -> str:
    rows = []
    for key, label in _NUM_ORDER:
        if key not in nums:
            continue
        pct = key in ("maxdd", "alpha")
        lab = gloss(label, label)
        rows.append(f"<tr><td>{lab}</td><td style='text-align:right'>"
                    f"{_fmt(nums.get(key), pct=pct)}</td></tr>")
    cap = nums.get("capacity_inr")
    cap_txt = "unstated" if not cap else f"₹{float(cap) / 1e7:.0f}cr"
    rows.append(f"<tr><td>{gloss('capacity breakpoint', 'capacity breakpoint')}</td>"
                f"<td style='text-align:right'>{_esc(cap_txt)}</td></tr>")
    return ("<table class='rl-nums' style='border-collapse:collapse;min-width:320px'>"
            + "".join(rows) + "</table>")


def _citations_block(cites: list, survivor: str) -> str:
    if not cites and not survivor:
        return ""
    parts = ["<div class='rl-wall' style='margin:12px 0;padding:10px;border-left:3px solid "
             "#d29922'>",
             f"<b>Known-dead shapes this rule matches</b> <small>(cited before the run, "
             f"verbatim from {_esc(BLOCKING_SOURCE)} — the ledger stays canonical)</small>"]
    for c in cites:
        parts.append(f"<pre style='white-space:pre-wrap;margin:6px 0'>{_esc(c)}</pre>")
    if survivor:
        parts.append(f"<p style='margin:6px 0'><small>{_esc(survivor)}</small></p>")
    parts.append("</div>")
    return "".join(parts)


def _roster_block(roster: list) -> str:
    if not roster:
        return ""
    links = ", ".join(
        f"<a href='/dash/stock?sym={_esc(s)}'>{_esc(s)}</a>" for s in roster)
    return (f"<div class='rl-roster' style='margin:10px 0'><b>Current cohort "
            f"({len(roster)})</b> <small>— the names the rule selects at the latest "
            f"rebalance; a cohort statistic, never a single-stock verdict</small>"
            f"<div>{links}</div></div>")


def render_verdict_card(verdict: dict, csv_href: str = "") -> str:
    """The honest-verdict card: ledger-vocabulary verdict + qualifier + numbers (net first)
    + the BLOCKING wall citations verbatim + the prereg hash chip + the roster."""
    v = verdict.get("verdict", "")
    q = verdict.get("qualifier")
    refusal = verdict.get("refusal_reason") or ""
    nums = verdict.get("numbers") or {}
    chip = (f"<code title='prereg gate hash — sha256 of the frozen rule text, recorded "
            f"before the run'>{_esc((verdict.get('rule_hash') or '')[:16])}…</code>")
    parts = [
        "<div class='rl-card' style='border:1px solid var(--ink-3,#444);border-radius:8px;"
        "padding:14px;margin:12px 0'>",
        f"<div><small>rule</small> <code>{_esc(verdict.get('rule_text', ''))}</code></div>",
        f"<div style='font-size:1.3em;margin:8px 0'><b>{_esc(v)}</b>"
        + (f" <span class='rl-qual' style='padding:2px 8px;border-radius:10px;"
           f"border:1px solid var(--ink-3,#444)'>{_esc(q)}</span>" if q else "")
        + "</div>",
    ]
    if refusal:
        parts.append(f"<p><small>{_esc(refusal)}</small></p>")
    parts.append(_numbers_table(nums))
    parts.append(_citations_block(verdict.get("ledger_citations") or [],
                                  verdict.get("survivor_note") or ""))
    parts.append(_roster_block(verdict.get("roster") or []))
    parts.append(f"<div style='margin-top:8px'><small>prereg {chip} · "
                 f"{_esc(verdict.get('prereg_ref', ''))}</small>"
                 + (f" · <a href='{_esc(csv_href)}'>CSV</a>" if csv_href else "") + "</div>")
    parts.append(ifx.plain(
        "Plain read: the verdict is the gauntlet's arithmetic on YOUR rule — walk-forward "
        "halves, a random-pick placebo, realistic costs, a capacity read — judged against "
        "Nifty-500 buy-and-hold. It is a statistical summary of the rule, not advice about "
        "any stock."))
    parts.append("</div>")
    return "".join(parts)


def _form(params: dict) -> str:
    """The rule composer — POST because running WRITES (prereg + inbox; row 11)."""
    sel = lambda name, options, cur: (
        f"<select name='{name}'>" + "".join(
            f"<option value='{_esc(o)}'{' selected' if o == cur else ''}>{_esc(o)}</option>"
            for o in options) + "</select>")
    p = params or {}
    filt_boxes = "".join(
        f"<label style='margin-right:10px'><input type='checkbox' name='where' "
        f"value='{_esc(f)}'{' checked' if f in str(p.get('where', '')) else ''}> "
        f"{_esc(f)}</label>" for f in sorted(FILTERS))
    veto_boxes = "".join(
        f"<label style='margin-right:10px'><input type='checkbox' name='veto' "
        f"value='{_esc(v)}'{' checked' if v in str(p.get('veto', '')) else ''}> "
        f"{_esc(v)}</label>" for v in sorted(VETOES))
    return f"""
<form method="post" action="/dash/rule-lab/run" class="rl-form" style="margin:12px 0">
  <div>SELECT {sel('u', sorted(UNIVERSES), p.get('u', 'liquid500'))}
       RANK BY {sel('rank', sorted(SIGNALS), p.get('rank', 'mom12'))}
       TAKE <input type="number" name="n" min="{TAKE_MIN}" max="{TAKE_MAX}"
            value="{_esc(str(p.get('n', '25')))}" style="width:4em">
       HOLD {sel('hold', HOLDS, p.get('hold', 'quarterly'))}</div>
  <div style="margin:6px 0">WHERE {filt_boxes}</div>
  <div style="margin:6px 0">VETO {veto_boxes} <small>(vetoes filter; they never rank — D66)</small></div>
  <button type="submit">Run the gauntlet</button>
  <small>runs queue to the Review Inbox; the verdict lands here when done</small>
</form>"""


def render_page(verdict: dict | None = None, params: dict | None = None,
                demo_note: str = "") -> str:
    """The full page BODY (the mount wraps it in the site shell). Anonymous visitors get a
    read-only demo verdict via `demo_note` (the tracker demo-book precedent, D-P0-6)."""
    fence_line = ifx.fence("not_reco", "rule-lab verdicts are gauntlet arithmetic", cap=True)
    csv_href = ""
    if verdict:
        from urllib.parse import urlencode
        try:
            csv_href = "/dash/rule-lab?" + urlencode(
                {**query_from_spec(compile_rule(verdict.get("rule_text", ""))),
                 "format": "csv"})
        except RuleError:
            csv_href = ""
    parts = [
        f"<h1>Rule lab <small>{fence_line}</small></h1>",
        ifx.bottom_line(BOTTOM_LINE),
        (f"<p><small>{_esc(demo_note)}</small></p>" if demo_note else ""),
        _form(params or (query_from_spec(compile_rule(verdict["rule_text"]))
                         if verdict and verdict.get("rule_text") else {})),
        render_verdict_card(verdict, csv_href) if verdict else
        "<p>No verdict yet — compose a rule above. Every run is pre-registered "
        "(the frozen rule text is hashed before anything executes) and judged by the same "
        "gauntlet our own studies pass: walk-forward halves, a placebo control, realistic "
        "costs, a capacity read.</p>",
        "<h2>How the gauntlet judges</h2>",
        "<ul>",
        f"<li>{gloss('both halves', 'Both halves')}: beat the Nifty-500 net benchmark in "
        "2012-18 AND 2019-26, or it is noise.</li>",
        f"<li>{gloss('placebo p95', 'Placebo p95')}: beat the 95th percentile of "
        "random-selection books on the same tables — not merely beat zero.</li>",
        f"<li>{gloss('capacity breakpoint', 'Capacity breakpoint')}: the AUM where "
        "participation impact kills the edge; no stated capacity, no result.</li>",
        f"<li>{gloss('prereg gate hash', 'Prereg gate hash')}: the rule text is frozen and "
        "hashed before the run; first registration wins.</li>",
        "<li>Known-dead shapes are cited verbatim from the strategy ledger BEFORE any run — "
        "a dead idea can be re-tested, never re-walked silently.</li>",
        "</ul>",
        ifx.how_to_read_link(),
    ]
    return "".join(p for p in parts if p)


# ------------------------------------------------------------------ selftest
def _selftest() -> int:
    from src.automation.rule_lab import build_verdict
    spec = compile_rule("SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly")
    q = query_from_spec(spec)
    assert spec_from_query(q) == spec                     # URL round-trip (row 8b)
    nums = {"net_sharpe": 0.61, "gross_sharpe": 1.02, "half1": 0.55, "half2": 0.66,
            "placebo_p95": 0.40, "observed": 0.61, "emp_p": 0.02, "bench_net": 0.89,
            "capacity_inr": None, "maxdd": -0.41, "ann_cost_pct": 6.0}
    v = build_verdict(spec, nums, "selftest", {"env": "selftest"},
                      roster=["AAA", "BBB"]).to_dict()
    page = render_page(v, demo_note="read-only demo rule")
    assert "descriptive, not a recommendation" in page    # the fence (row 4)
    assert BOTTOM_LINE in page
    assert "/dash/stock?sym=AAA" in page                  # sym links (row 9)
    assert 'method="post"' in page                        # writes are POST (row 11)
    assert "WEAKER-THAN-BENCHMARK" in page
    name, text = render_csv(v)
    assert name.startswith("rule-lab-") and "net Sharpe" in text and "AAA" in text
    # dead-shape page carries the verbatim wall
    dead = compile_rule("SELECT liquid500 RANK BY bookyield TAKE 25 HOLD monthly")
    dv = build_verdict(dead, {}, "selftest", {"env": "selftest"}).to_dict()
    dpage = render_page(dv)
    assert "BOOK_YIELD" in dpage and "Known-dead shapes" in dpage
    print("RULE_LAB_VIEW selftest OK")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else print(__doc__) or 0)
