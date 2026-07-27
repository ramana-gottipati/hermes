"""Rule-lab core — closed-vocabulary rule compiler + honest gated verdicts (D134 §4-H, L4/L7).

THE GATE (pre-registered; this raw docstring is the hash target, prereg.gate_hash discipline —
hash the RAW string, never ast.get_docstring, which dedents):

  A user rule is compiled from a CLOSED vocabulary (no free text, no arithmetic composer, no
  rupee constants, no entry/exit micro-language, no single-stock verdicts) and judged by the
  existing evidence-factory gauntlet. The deterministic verdict law over the measured numbers:

    required = net_retvol, half1, half2, placebo_p95, observed, bench_net
    0. any required number missing/NaN                  -> NO-VERDICT(missing:<names>)
       (a missing stage is a refusal to rule, never a partial verdict)
    1. observed <= placebo_p95                          -> REJECTED            [descriptive-only]
    2. net_retvol <= 0                                  -> REJECTED            [descriptive-only]
    3. half1 > bench AND half2 > bench AND net > bench:
         capacity_inr stated (> 0)                      -> NEW-BENCHMARK       [fundable]
         capacity unstated                              -> CONDITIONAL(capacity-unstated)
                                                                               [flat-cost-only]
    4. net > bench, exactly one half fails              -> CONDITIONAL(H1-only|H2-only)
                                                                               [paper-only]
    5. net > bench, both halves fail                    -> CONDITIONAL(full-window-only)
                                                                               [paper-only]
    6. else                                             -> WEAKER-THAN-BENCHMARK
                                                                               [descriptive-only]

  Verdict enum = the ledger's own vocabulary, verbatim (docs/strategy-ledger.md):
  REJECTED | WEAKER-THAN-BENCHMARK | CONDITIONAL(<condition>) | NEW-BENCHMARK, plus the
  refusal NO-VERDICT(<why>). The qualifier (descriptive-only | paper-only | flat-cost-only |
  fundable) travels with the verdict forever — never a droppable footnote.

  Placebo control (pre-registered here): observed = the rule's full-window NET return/vol; the
  null = the distribution of net return/vols of N random-selection books of the same size, on the
  SAME tables / universe / TAKE / HOLD. Observed must beat the null p95 — not merely beat zero.

BLOCKING wall (binding): when a compiled rule matches a known-dead shape, the matching
"❌ BLOCKING FAILURE MODELS" row(s) of docs/strategy-ledger.md are stapled VERBATIM into the
compile result and every verdict object built from it. The rule may still run (new evidence is
Ramana's call) — but it can never run silently. The ledger file stays canonical: if the rows
embedded below ever disagree with it, the ledger wins (tests/test_rule_lab.py byte-compares).

Boundary (plan §3, SEBI RA Regulations 2014 reg. 2(1)(w)): the lab analyzes the USER'S rule and
returns statistical summaries — cohort arithmetic, never a recommendation, target price, or
single-stock verdict. Verdict labels are ledger vocabulary, never action verbs.

Module layout (stdlib-only; the numpy-side executor lives in
research/explosive_moves/rule_lab_executor.py and imports THIS module for the vocabulary,
citations and judge law — src/ never imports the research stack):
  compile_rule(text)          closed-grammar parse -> RuleSpec (canonical text + sha256 hash)
  spec_from_params(...)       structured entry point (the ?u=&rank=... URL state)
  trigger_citations(spec)     §5.1 shape -> verbatim BLOCKING rows (+ survivor note)
  judge(numbers)              the verdict law above -> (verdict, qualifier, refusal_reason)
  RuleVerdict                 the one result object; invariants enforced in __post_init__
  ledger_entry(verdict)       paste-ready ledger block (append happens AFTER human approval)

CLI:  python -m src.automation.rule_lab --selftest | --compile "RULE TEXT" | --grammar
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict

# --------------------------------------------------------------------------- benchmarks
# The bar every rule must clear: Nifty-500 buy-and-hold, net (ledger § Benchmarks).
BENCH_NET_LEDGER = 0.89

# --------------------------------------------------------------------------- vocabulary
# Every token binds 1:1 to a function that ALREADY exists and is already tested — no token
# may be added without the function existing first (docs/rule-lab-design.md §2). Bindings are
# DECLARATIVE (module + name strings): this module stays stdlib-only; the research-venv
# executor resolves them, and tests/test_rule_lab.py proves each name exists in its source.

# Universes = PIT liquidity-percentile bands over median turnover (pctrank of med_turn at each
# rebalance) — percentiles ONLY, never rupee constants (ramana-working-principles). The bands
# reuse the house gates: 0.60 = the value-relative top-40% gate (cost_realism.GATE_PCTL,
# factor_zoo), 0.80 = the large-cap top-quintile gate (cost_participation.GATE_PCTL).
UNIVERSES: dict = {
    "liquid500": {"band": (0.60, 1.00), "label": "liquid top-40% by turnover (house standard gate)"},
    "largecap":  {"band": (0.80, 1.00), "label": "top-quintile liquidity (large-cap gate)"},
    "midcap":    {"band": (0.60, 0.80), "label": "liquidity percentile 60-80 band"},
    "smallcap":  {"band": (0.30, 0.60), "label": "liquidity percentile 30-60 band"},
}

# Rank signals -> factory callables (research/explosive_moves/factory.py), one function per
# token, no exceptions. The value/quality family binds to the factor-zoo's TESTED factors
# (research/explosive_moves/factor_zoo.py keys) — expressible so the BLOCKING wall can cite
# them (§5.1), but the v1 executor leaves them unbound: compiling one auto-cites the recorded
# factor-zoo result; re-running it is an on-box factor_zoo pass, not silent new math.
SIGNALS: dict = {
    "mom6":      {"module": "research/explosive_moves/factory.py", "callable": "sig_mom6"},
    "mom12":     {"module": "research/explosive_moves/factory.py", "callable": "sig_mom12"},
    "riskadj":   {"module": "research/explosive_moves/factory.py", "callable": "sig_riskadj"},
    "accel":     {"module": "research/explosive_moves/factory.py", "callable": "sig_accel"},
    "lowvolmom": {"module": "research/explosive_moves/factory.py", "callable": "sig_lowvolmom"},
    "delivmom":  {"module": "research/explosive_moves/factory.py", "callable": "sig_delivmom"},
    "qualmom":   {"module": "research/explosive_moves/factory.py", "callable": "sig_qualmom"},
    "pullback":  {"module": "research/explosive_moves/factory.py", "callable": "sig_pullback"},
    "bookyield": {"module": "research/explosive_moves/factor_zoo.py", "callable": "BOOK_YIELD",
                  "executor_v1": "unbound (factor-zoo evidence cited; on-box factor_zoo re-run)"},
    "earnyield": {"module": "research/explosive_moves/factor_zoo.py", "callable": "EARN_YIELD",
                  "executor_v1": "unbound (factor-zoo evidence cited; on-box factor_zoo re-run)"},
    "quality":   {"module": "research/explosive_moves/factor_zoo.py", "callable": "QUALITY",
                  "executor_v1": "unbound (factor-zoo evidence cited; on-box factor_zoo re-run)"},
}

# Filters. not_extended = the *_VAL rule (excludes >200% / ~5y) -> factory.not_extended().
# min_liquidity tightens the universe's LOWER percentile edge by +0.10 (still a percentile).
# listed_on_asof asserts the PIT membership property (security_master.universe_on join, D2-F1)
# — inherent to the on-box cache build; recorded in provenance, synthetic runs say synthetic.
FILTERS: dict = {
    "not_extended":   {"module": "research/explosive_moves/factory.py", "callable": "not_extended"},
    "min_liquidity":  {"module": "src/automation/rule_lab.py", "callable": "UNIVERSES",
                       "effect": "raises universe lower percentile edge by +0.10"},
    "listed_on_asof": {"module": "src/automation/security_master.py", "callable": "universe_on"},
}

# Vetoes are FILTERS, never rankers (D66). Attempting to RANK BY any of these (or their
# family words) is a compile-time refusal that carries the matching BLOCKING citation.
VETOES: dict = {
    "cci_deterioration": {"family": "cci", "note": "credibility deterioration veto (D66)"},
    "mep_distribution":  {"family": "mep", "note": "MEP distribution-phase veto (D62/D66)"},
    "rating_downgrade":  {"family": "rating", "note": "credit-rating downgrade veto"},
}

HOLDS = ("monthly", "quarterly")          # run_strat rebalance clock: 22 / 66 trading days
TAKE_MIN, TAKE_MAX = 5, 50

# Veto-family words that must never appear as a rank signal (compile refusal + citation).
_VETO_RANK_REFUSALS = {
    "cci": "CCI_FACTOR", "cci_deterioration": "CCI_FACTOR", "credibility": "CCI_FACTOR",
    "mep": "MEP_AS_ALPHA", "mep_distribution": "MEP_AS_ALPHA", "accumulation": "MEP_AS_ALPHA",
    "rating_downgrade": None, "rating": None,     # doctrine only — no dedicated ledger row
}

# --------------------------------------------------------------------------- BLOCKING wall
# Reproduced VERBATIM from docs/strategy-ledger.md § "❌ BLOCKING FAILURE MODELS" (2026-07-02).
# ASCII-escaped JSON so the bytes survive any editor/locale; json.loads restores the exact
# Unicode of the ledger rows. tests/test_rule_lab.py re-reads the ledger and byte-compares —
# if the ledger changes, the suite fails until this block is re-synced (the ledger wins).
# D142: the ratios in these rows are return/vol (mean/sd × √periods, no risk-free rate
# subtracted). The ledger's own label was corrected 2026-07-27 and this block re-derived from
# it in the SAME commit — the only honest way to move a byte-compared pair. Never relabel a
# row here alone: the ledger is canonical, so edit THERE and re-derive (map rows by their
# name cell, which a label change leaves untouched); do not hand-edit the escaped JSON.
_BLOCKING_JSON = r"""
{
 "corollary": "The corollary (the doctrine these failures prove): **price strength is the only gross forward-return\nengine; value/quality/credibility/accumulation are veto/filter/context layers, not rankers; and no\nfactor here is a fundable net-of-cost alpha vs the index.** The asset is PIT rigor + under-covered data\n+ the analytical selection lens \u2014 not a backtested alpha strategy.",
 "rows": {
  "ACCEL_PULLBACK_DELIV": "| ACCEL / PULLBACK / DELIV_MOM (standalone) | return/vol 0.42-0.85, MaxDD \u221244%\u2026\u221270% | Short-thrust chasing / dip-buying / delivery% added no standalone edge. |",
  "BOOK_YIELD": "| **BOOK_YIELD (deep value / B-P)** | return/vol 0.61-0.63 \u00b7 **alpha \u22121.8%\u2026\u22122.2% (NEGATIVE)** \u00b7 **beta 1.54-1.56** \u00b7 **MaxDD \u221282%** \u00b7 fails BOTH halves | Negative alpha + \u221282% drawdown + high beta = a value-trap engine. **Never a production long-ranker.** The \u03b2\u22481.54 + MaxDD\u224882% alone stop us. |",
  "CBLEND_FUNDABLE": "| **C-BLEND 50/50 as a FUNDABLE book (2026-07-05c)** | Flat-cost return/vol **1.32** (recorded champion) \u2192 participation-cost **NET 0.52 @Rs25cr \u00b7 0.17 @Rs50cr \u00b7 \u22120.30 @Rs100cr**; beats the index at NO AUM; H2 (honest window) 0.70 @Rs50cr < 0.89; ann cost 22%\u219286% | The 1.32 was **flat-cost only**. Monthly rebalance \u00d7 mid-cap tilt (median capacity ~Rs38cr) makes Almgren participation impact fatal; the RISKADJ core is worse. C-BLEND stays a **descriptive/paper overlay** (D66 fence holds), never a fundable book. Only participation-fundable corner = quarterly large-cap **LOWVOL_MOM** (1.02 @Rs50cr, ~Rs100cr ceiling). Re-cost: `cblend_cost_recut.py`. |",
  "CCI_FACTOR": "| CCI credibility as a factor | Spearman \u22480; HIGH\u2212LOW excess \u221210% @12m (inverse, survivorship) | FALSIFIED as a factor \u2192 descriptive/veto only. |",
  "EARN_YIELD": "| **EARN_YIELD (cheap on P/E)** | return/vol 0.70 \u00b7 alpha +0.4% \u00b7 MaxDD \u221271% | No index-beating edge standalone; deep drawdown. |",
  "FOOTPRINT_V1": "| **Accumulation-footprint detector v1 (2026-07-05b)** | pre-registered gate **FAIL 1/4** (only trade-size cleared \u03b4\u2265+0.20 vs both controls: +0.329/+0.250); 764/947 episodes had NO pre-public window (SEBI PIT T+2); n=54 usable | \"Front-detect the insider from the tape\" is structurally near-impossible in India at filing granularity. deliv_per showed ~no case elevation (\u03b4\u2248+0.07) \u2014 consistent with MEP's alpha failure. Survivor: avg-trade-size ratio = descriptive column only. Follow-ups (campaign arcs E-04, disclosure drift E-03) require fresh pre-registration. |",
  "MEP_AS_ALPHA": "| MEP-accumulation as alpha | Deflated-Sharpe DSR 0.45\u21920.36 when added | Descriptor-only; adds nothing. Do not re-test as alpha. |",
  "MOMENTUM_BAND_RSI": "| **MOMENTUM BAND + RSI single-name swing (2026-07-22)** | Upper-band breakout entry (T=EMA5(HLC3) > EMA13(high)) + RSI/2-fractal managed exit, pre-registered `0e90bf2c`, 45,131 events / 124,832 trades 2012-26: EVENT median 22d excess **\u22120.90%**, Cliff's \u03b4 vs placebo **\u22120.012** (FAIL-null, negative both halves); BOOK net return/vol **0.53** (h1 0.19 / h2 0.87, both <0.89), raw CAGR 19.4% \u2192 **net 8.4%** (cost \u221211pp) | The \"buy strength\" edge of the STREAM BAND band is ALSO an anti-signal; RSI-as-stop churns (phase-1 hair-trigger, 94% exits, 5-bar hold) and the RSI-80 partial *hurts* (\u22120.25pp mean = profit-taker law again, 07-14e). Beats random-entry (+0.20) but nowhere near fundable. Full entry: \u00a7 Study 2026-07-22; cites 07-13/14b/14c/14d/14e. |",
  "MOMENTUM_FUNDABLE": "| **Momentum sold as a FUNDABLE strategy** | GROSS return/vol 1.29 \u2192 **NET ~0.09, CAGR negative, MaxDD \u221269%** under realistic cost (~36%/yr, ~100%/mo turnover) | The headline return/vol is a flat-cost illusion. Nothing beats Nifty-500 buy-&-hold (0.89) net of realistic cost. Momentum = a **gross selection/analytical lens**, not net alpha; any fundable form must be low-turnover (and is then defensive, not alpha). |",
  "PEAD_BOOK": "| **PEAD tradeable book (event-time, 2026-07-05)** | ALL constructions fail: trailing net return/vol **0.10**, no-delivery 0.02, **within-season 0.06** (pre-registered), HEDGED **\u22120.58**, 1.5\u00d7 cost \u22120.32 \u2014 vs bench 0.85, both halves | Event drift is REAL descriptively (A-study SUE-Q5\u00d7DELIV-T3 CAR60 +7.62%, t_cohort 1.92) but no wrapper survives real-time ranks + costs + compounding; the within-season variant (the last untested cell) also failed. Descriptive event lens only (`pead_surface.py`). Do not re-attempt any PEAD book without beating these exact numbers under the same no-leak harness. |",
  "QUALITY_STANDALONE": "| **QUALITY standalone** | return/vol 0.76 \u00b7 alpha ~0.0% \u00b7 fails halves | Quality doesn't rank returns alone; only helps *attached to momentum* (QUAL_MOM). \u2192 C is a veto/filter, not a ranker. |"
 },
 "source": "docs/strategy-ledger.md \u00a7 \"\u274c BLOCKING FAILURE MODELS\" (2026-07-02)"
}
"""

_BLOCKING = json.loads(_BLOCKING_JSON)
BLOCKING_ROWS: dict = _BLOCKING["rows"]              # key -> verbatim ledger table row
BLOCKING_CROLLARY: str = _BLOCKING["corollary"]      # the doctrine paragraph, verbatim
BLOCKING_SOURCE: str = _BLOCKING["source"]

# The one recorded survivor to state honestly when its shape appears (design §5.1):
SURVIVOR_NOTE = ("RECORDED SURVIVOR (not a blocker): quarterly large-cap LOWVOL_MOM — "
                 "participation-fundable at 1.02 @₹50cr, ceiling ~₹100cr "
                 "(docs/strategy-ledger.md, C-BLEND re-cut 2026-07-05c).")

# Ledger vocabulary — verbatim enums (docs/rule-lab-design.md §4).
VERDICTS = ("REJECTED", "WEAKER-THAN-BENCHMARK", "CONDITIONAL", "NEW-BENCHMARK", "NO-VERDICT")
QUALIFIERS = ("descriptive-only", "paper-only", "flat-cost-only", "fundable")

_REQUIRED_NUMBERS = ("net_retvol", "half1", "half2", "placebo_p95", "observed", "bench_net")


class RuleError(ValueError):
    """Compile refusal. May carry the BLOCKING citation(s) that motivated it."""

    def __init__(self, msg: str, citations: list | None = None):
        super().__init__(msg)
        self.citations = list(citations or [])


# --------------------------------------------------------------------------- the compiler
@dataclass(frozen=True)
class RuleSpec:
    """A compiled rule: canonical frozen text + its sha256 (the prereg chip)."""
    universe: str
    signal: str
    take: int
    hold: str
    filters: tuple = ()
    vetoes: tuple = ()
    text: str = ""                 # canonical spec string (grammar §2 clause order)
    rule_hash: str = ""            # sha256 of the RAW canonical text

    def to_dict(self) -> dict:
        d = asdict(self)
        d["filters"], d["vetoes"] = list(self.filters), list(self.vetoes)
        return d


def _canonical_text(universe, filters, signal, take, hold, vetoes) -> str:
    parts = [f"SELECT {universe}"]
    if filters:
        parts.append("WHERE " + " AND ".join(filters))
    parts += [f"RANK BY {signal}", f"TAKE {take}", f"HOLD {hold}"]
    if vetoes:
        parts.append("VETO " + " AND ".join(vetoes))
    return " ".join(parts)


def spec_from_params(universe: str, signal: str, take, hold: str,
                     filters=(), vetoes=()) -> RuleSpec:
    """Structured compile (the URL-state path). Validates every token; canonicalizes;
    hashes the RAW canonical string (prereg discipline — never a dedented copy)."""
    u = str(universe or "").strip().lower()
    s = str(signal or "").strip().lower()
    h = str(hold or "").strip().lower()
    fl = tuple(sorted({str(f).strip().lower() for f in filters if str(f).strip()}))
    vt = tuple(sorted({str(v).strip().lower() for v in vetoes if str(v).strip()}))

    if u not in UNIVERSES:
        raise RuleError(f"unknown universe token '{u}' (closed vocabulary: {sorted(UNIVERSES)})")
    if s in _VETO_RANK_REFUSALS or s in VETOES:
        key = _VETO_RANK_REFUSALS.get(s) or VETOES.get(s, {}).get("family")
        key = _VETO_RANK_REFUSALS.get(key, key) if key else None
        row_key = key if key in BLOCKING_ROWS else _VETO_RANK_REFUSALS.get(s)
        cites = [BLOCKING_ROWS[row_key]] if row_key in BLOCKING_ROWS else []
        raise RuleError(
            f"'{s}' is a veto/filter layer, never a ranker (D66; {BLOCKING_SOURCE}). "
            f"The doctrine: {BLOCKING_CROLLARY.splitlines()[0]}", citations=cites)
    if s not in SIGNALS:
        raise RuleError(f"unknown signal token '{s}' (closed vocabulary: {sorted(SIGNALS)})")
    try:
        n = int(take)
    except (TypeError, ValueError):
        raise RuleError(f"TAKE must be an integer {TAKE_MIN}..{TAKE_MAX}, got {take!r}")
    if not (TAKE_MIN <= n <= TAKE_MAX):
        raise RuleError(f"TAKE out of range: {n} (allowed {TAKE_MIN}..{TAKE_MAX})")
    if h not in HOLDS:
        raise RuleError(f"unknown hold token '{h}' (closed vocabulary: {HOLDS})")
    for f in fl:
        if f not in FILTERS:
            raise RuleError(f"unknown filter token '{f}' (closed vocabulary: {sorted(FILTERS)})")
    for v in vt:
        if v not in VETOES:
            raise RuleError(f"unknown veto token '{v}' (closed vocabulary: {sorted(VETOES)})")

    text = _canonical_text(u, fl, s, n, h, vt)
    return RuleSpec(universe=u, signal=s, take=n, hold=h, filters=fl, vetoes=vt,
                    text=text, rule_hash=hashlib.sha256(text.encode("utf-8")).hexdigest())


_CLAUSE_RE = re.compile(
    r"\b(SELECT|WHERE|RANK\s+BY|TAKE|HOLD|VETO)\b", re.IGNORECASE)


def compile_rule(text: str) -> RuleSpec:
    """Parse the closed grammar (clauses accepted in any order; canonicalized to §2 order):

        RULE := SELECT <universe> [WHERE <filter> [AND <filter>]*]
                RANK BY <signal> TAKE <n:5..50> HOLD <horizon>
                [VETO <veto> [AND <veto>]*]
    """
    raw = (text or "").strip()
    if not raw:
        raise RuleError("empty rule")
    hits = list(_CLAUSE_RE.finditer(raw))
    if not hits:
        raise RuleError("no grammar clauses found (expected SELECT/RANK BY/TAKE/HOLD)")
    if hits[0].start() != 0:
        raise RuleError(f"rule must start with a clause keyword, got: {raw[:hits[0].start()]!r}")
    clauses: dict = {}
    for i, m in enumerate(hits):
        kw = re.sub(r"\s+", " ", m.group(1).upper())
        val = raw[m.end(): hits[i + 1].start() if i + 1 < len(hits) else len(raw)].strip()
        if kw in clauses:
            raise RuleError(f"duplicate clause {kw}")
        clauses[kw] = val
    missing = [k for k in ("SELECT", "RANK BY", "TAKE", "HOLD") if k not in clauses]
    if missing:
        raise RuleError(f"missing required clause(s): {missing}")
    split_and = lambda v: [p for p in re.split(r"\s+AND\s+", v, flags=re.IGNORECASE) if p.strip()]
    return spec_from_params(
        universe=clauses["SELECT"], signal=clauses["RANK BY"], take=clauses["TAKE"],
        hold=clauses["HOLD"], filters=split_and(clauses.get("WHERE", "")),
        vetoes=split_and(clauses.get("VETO", "")))


# --------------------------------------------------------------------------- §5.1 trigger map
def trigger_citations(spec: RuleSpec) -> list:
    """Compiled-shape -> the matching BLOCKING rows, verbatim (may be non-empty on a PASS).

    Shape matching is on the COMPILED rule, not user wording (design §5.1). Rows whose
    trigger tokens are not yet expressible in the v1 vocabulary (PEAD event wrappers ->
    PEAD_BOOK; insider/SAST footprint ranks -> FOOTPRINT_V1) stay in BLOCKING_ROWS awaiting
    their tokens — a future event/entity token must wire its row here before it ships."""
    cites = []
    s, h, u = spec.signal, spec.hold, spec.universe
    if s in ("bookyield", "earnyield"):
        cites += [BLOCKING_ROWS["BOOK_YIELD"], BLOCKING_ROWS["EARN_YIELD"]]
    if s == "quality":
        cites.append(BLOCKING_ROWS["QUALITY_STANDALONE"])
    if s in ("mom6", "mom12") and h == "monthly":
        cites.append(BLOCKING_ROWS["MOMENTUM_FUNDABLE"])
    if s in ("accel", "pullback", "delivmom"):
        cites.append(BLOCKING_ROWS["ACCEL_PULLBACK_DELIV"])
    if s in ("riskadj", "lowvolmom", "qualmom") and h == "monthly" and u in ("midcap", "smallcap"):
        cites.append(BLOCKING_ROWS["CBLEND_FUNDABLE"])
    return cites


def survivor_note(spec: RuleSpec) -> str:
    """The recorded participation-fundable corner, stated honestly when its shape appears."""
    if spec.signal == "lowvolmom" and spec.hold == "quarterly" and spec.universe == "largecap":
        return SURVIVOR_NOTE
    return ""


# --------------------------------------------------------------------------- the verdict law
def _num(numbers: dict, key: str):
    v = numbers.get(key)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None          # NaN -> None


def judge(numbers: dict) -> tuple:
    """The deterministic verdict law (see THE GATE in the module docstring).

    Returns (verdict, qualifier, refusal_reason). verdict uses the ledger vocabulary
    verbatim; CONDITIONAL carries its condition inline: 'CONDITIONAL(H2-only)'."""
    missing = [k for k in _REQUIRED_NUMBERS if _num(numbers, k) is None]
    if missing:
        return ("NO-VERDICT(missing:%s)" % ",".join(missing), None,
                "a missing stage is a refusal to rule, never a partial verdict "
                "(docs/rule-lab-design.md §4 invariant 3)")
    net = _num(numbers, "net_retvol"); h1 = _num(numbers, "half1"); h2 = _num(numbers, "half2")
    p95 = _num(numbers, "placebo_p95"); obs = _num(numbers, "observed")
    bench = _num(numbers, "bench_net")
    cap = _num(numbers, "capacity_inr")

    if obs <= p95:
        return ("REJECTED", "descriptive-only",
                "observed does not beat the placebo p95 — the control wins")
    if net <= 0:
        return ("REJECTED", "descriptive-only", "no positive net edge at all")
    if h1 > bench and h2 > bench and net > bench:
        if cap is not None and cap > 0:
            return ("NEW-BENCHMARK", "fundable", "")
        return ("CONDITIONAL(capacity-unstated)", "flat-cost-only",
                "a rule with no stated capacity is not a result (design §3 stage 6)")
    if net > bench:
        if h1 > bench and not h2 > bench:
            return ("CONDITIONAL(H1-only)", "paper-only", "")
        if h2 > bench and not h1 > bench:
            return ("CONDITIONAL(H2-only)", "paper-only", "")
        return ("CONDITIONAL(full-window-only)", "paper-only", "")
    return ("WEAKER-THAN-BENCHMARK", "descriptive-only", "")


# --------------------------------------------------------------------------- verdict object
@dataclass
class RuleVerdict:
    """The ONE result object (design §4). Invariants are enforced, not conventions."""
    rule_text: str
    rule_hash: str
    prereg_ref: str
    verdict: str
    qualifier: str | None
    numbers: dict
    ledger_citations: list
    provenance: dict
    survivor_note: str = ""
    refusal_reason: str = ""
    roster: list = field(default_factory=list)   # the cohort the rule currently selects

    def __post_init__(self):
        base = self.verdict.split("(", 1)[0]
        if base not in VERDICTS:
            raise ValueError(f"verdict '{self.verdict}' is not ledger vocabulary {VERDICTS}")
        if base == "CONDITIONAL" and "(" not in self.verdict:
            raise ValueError("CONDITIONAL must carry its condition: CONDITIONAL(<condition>)")
        if base == "NO-VERDICT":
            if self.qualifier is not None:
                raise ValueError("NO-VERDICT carries no qualifier — nothing was concluded")
        else:
            if self.qualifier not in QUALIFIERS:
                raise ValueError(f"qualifier '{self.qualifier}' not in {QUALIFIERS} — "
                                 "the qualifier travels with the verdict forever")
        if base == "NEW-BENCHMARK":
            n = self.numbers
            ok = (_num(n, "half1") is not None and _num(n, "half2") is not None
                  and _num(n, "bench_net") is not None
                  and _num(n, "half1") > _num(n, "bench_net")
                  and _num(n, "half2") > _num(n, "bench_net")
                  and (_num(n, "capacity_inr") or 0) > 0
                  and _num(n, "observed") is not None and _num(n, "placebo_p95") is not None
                  and _num(n, "observed") > _num(n, "placebo_p95"))
            if not ok:
                raise ValueError(
                    "NEW-BENCHMARK requires net>bench in BOTH halves AND stated capacity AND "
                    "observed>placebo_p95 (design §4 invariant 1)")
        for c in self.ledger_citations:
            if not str(c).startswith("| "):
                raise ValueError("ledger_citations must be verbatim ledger table rows")

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, d: dict) -> "RuleVerdict":
        return cls(**{k: d[k] for k in (
            "rule_text", "rule_hash", "prereg_ref", "verdict", "qualifier", "numbers",
            "ledger_citations", "provenance", "survivor_note", "refusal_reason", "roster")
            if k in d})


def build_verdict(spec: RuleSpec, numbers: dict, prereg_ref: str,
                  provenance: dict, roster=()) -> RuleVerdict:
    """Assemble the result object: judge the numbers, staple the wall citations."""
    verdict, qualifier, why = judge(numbers)
    return RuleVerdict(
        rule_text=spec.text, rule_hash=spec.rule_hash, prereg_ref=prereg_ref,
        verdict=verdict, qualifier=qualifier, numbers=dict(numbers),
        ledger_citations=trigger_citations(spec), provenance=dict(provenance),
        survivor_note=survivor_note(spec), refusal_reason=why, roster=list(roster))


# --------------------------------------------------------------------------- ledger block
def ledger_entry(v: RuleVerdict, decided_on: str) -> str:
    """Paste-ready docs/strategy-ledger.md block for a DECIDED verdict. The append itself
    happens only after human approval in the Review Inbox (design §8 open question —
    inbox-first default: canon carries a human signature)."""
    n = v.numbers
    fmt = lambda k: ("n/a" if _num(n, k) is None else f"{_num(n, k):.2f}")
    lines = [
        f"## Rule-lab run {decided_on} — `{v.rule_text}` ({v.verdict})",
        "",
        f"Prereg: `{v.rule_hash[:16]}…` ({v.prereg_ref}) · qualifier **{v.qualifier or 'none'}**",
        f"NET return/vol {fmt('net_retvol')} (gross {fmt('gross_retvol')}) vs bench "
        f"{fmt('bench_net')} · halves {fmt('half1')}/{fmt('half2')} · "
        f"placebo p95 {fmt('placebo_p95')} (observed {fmt('observed')}, "
        f"emp-p {fmt('emp_p')}) · MaxDD {fmt('maxdd')} · ann cost {fmt('ann_cost_pct')}%",
    ]
    cap = _num(n, "capacity_inr")
    lines.append("Capacity: " + (f"₹{cap / 1e7:.0f}cr" if cap else "unstated"))
    if v.ledger_citations:
        lines.append("")
        lines.append("Matched BLOCKING rows (cited before the run — %s):" % BLOCKING_SOURCE)
        lines += list(v.ledger_citations)
    if v.survivor_note:
        lines.append(v.survivor_note)
    if v.refusal_reason:
        lines.append(f"Note: {v.refusal_reason}")
    prov = ", ".join(f"{k}={v.provenance[k]}" for k in sorted(v.provenance))
    lines += ["", f"Provenance: {prov}"]
    return "\n".join(lines)


# --------------------------------------------------------------------------- selftest / CLI
def _selftest() -> int:
    # grammar + hash stability
    a = compile_rule("SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly")
    b = spec_from_params("liquid500", "mom12", 25, "quarterly", filters=["not_extended"])
    assert a == b and a.rule_hash == b.rule_hash and len(a.rule_hash) == 64
    # clause order tolerated, canonicalized (the design §4 example's order)
    c = compile_rule("SELECT liquid500 RANK BY mom12 WHERE not_extended TAKE 25 HOLD quarterly")
    assert c.text == a.text and c.rule_hash == a.rule_hash
    # the BLOCKING wall on a BOOK_YIELD-shaped rule
    d = compile_rule("SELECT liquid500 RANK BY bookyield TAKE 25 HOLD monthly")
    cites = trigger_citations(d)
    assert BLOCKING_ROWS["BOOK_YIELD"] in cites and BLOCKING_ROWS["EARN_YIELD"] in cites
    # veto promoted to rank -> refusal WITH citation
    try:
        compile_rule("SELECT liquid500 RANK BY mep_distribution TAKE 25 HOLD monthly")
        raise AssertionError("veto-as-ranker must refuse")
    except RuleError as e:
        assert e.citations and e.citations[0] == BLOCKING_ROWS["MEP_AS_ALPHA"]
    # the verdict law
    base = {"net_retvol": 1.0, "half1": 1.0, "half2": 1.0, "placebo_p95": 0.5,
            "observed": 1.0, "bench_net": 0.89, "capacity_inr": 50e7}
    assert judge(base)[0] == "NEW-BENCHMARK"
    assert judge({**base, "capacity_inr": None})[0] == "CONDITIONAL(capacity-unstated)"
    assert judge({**base, "half2": 0.5})[0] == "CONDITIONAL(H1-only)"
    assert judge({**base, "placebo_p95": 1.5})[0] == "REJECTED"
    assert judge({**base, "net_retvol": None})[0].startswith("NO-VERDICT")
    # the object enforces invariant 1
    try:
        RuleVerdict(rule_text=a.text, rule_hash=a.rule_hash, prereg_ref="x", numbers={},
                    verdict="NEW-BENCHMARK", qualifier="fundable", ledger_citations=[],
                    provenance={})
        raise AssertionError("NEW-BENCHMARK without the numbers must raise")
    except ValueError:
        pass
    v = build_verdict(d, {**base, "half2": 0.5}, prereg_ref="selftest", provenance={"env": "selftest"})
    assert v.verdict == "CONDITIONAL(H1-only)" and v.qualifier == "paper-only"
    assert v.ledger_citations and RuleVerdict.from_dict(json.loads(v.to_json())).rule_hash == v.rule_hash
    assert "Rule-lab run" in ledger_entry(v, "2026-07-15")
    print("RULE_LAB selftest OK (%d vocabulary tokens, %d blocking rows)"
          % (len(SIGNALS) + len(UNIVERSES) + len(FILTERS) + len(VETOES), len(BLOCKING_ROWS)))
    return 0


def _print_grammar() -> None:
    print("RULE := SELECT <universe> [WHERE <filter> [AND <filter>]*] "
          "RANK BY <signal> TAKE <n:%d..%d> HOLD <horizon> [VETO <veto> [AND <veto>]*]"
          % (TAKE_MIN, TAKE_MAX))
    print("universe:", " | ".join(sorted(UNIVERSES)))
    print("signal:  ", " | ".join(sorted(SIGNALS)))
    print("filter:  ", " | ".join(sorted(FILTERS)))
    print("horizon: ", " | ".join(HOLDS))
    print("veto:    ", " | ".join(sorted(VETOES)))


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    elif "--grammar" in sys.argv:
        _print_grammar()
    elif "--compile" in sys.argv:
        spec = compile_rule(sys.argv[sys.argv.index("--compile") + 1])
        print(json.dumps(spec.to_dict(), indent=2))
        for cite in trigger_citations(spec):
            print("BLOCKING:", cite.encode("ascii", "backslashreplace").decode())
    else:
        print(__doc__)
