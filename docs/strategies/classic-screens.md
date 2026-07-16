# Classic Screens — Canonical Reference

> **Class:** CANONICAL · **Status:** DESCRIPTIVE-ONLY — public strategies run faithfully on our PIT
> data; proxies labeled, value shown with its recorded failure numbers · **Governing decision(s):**
> D133 · D66 (factor doctrine) · Guardrail #8 (primary sources) · **Reconciled:** 2026-07-14 (S145) ·
> **Origin:** 📚 CLASSIC (famous public strategies — Magic Formula · CANSLIM · Piotroski · Coffee Can · GARP · Graham · Quality · Low-Vol — re-proven on our PIT data). See [origins.md](origins.md).
> **Charter:** [strategy-ledger.md](../strategy-ledger.md) · [factor-league sibling](momentum-riskadj.md)
>
> **One-line definition:** The famous, name-brand equity strategies (Magic Formula, CANSLIM,
> Piotroski, Coffee Can, GARP, Graham, Quality, Low-Vol) catalogued and run as live top-25 rosters
> over the NSE universe — descriptive research shortlists, never buy lists.

## 1. What it is

A menu of the **public, citable stock-selection strategies** the professional world respects, each
made concrete as a screen the analyst can actually run and inspect at **`/dash/classics`**. It is the
sibling of the **Factor League** (`/dash/factor-league`): the Factor League ranks the raw factor
*families* (momentum, value, quality, low-vol) by the return/vol + alpha **we measured** on 14 years of NSE
data; Classic Screens implements the named, multi-signal *strategies* built on those factors and
surfaces their **current participants**.

Every strategy is expressed as our closest faithful reading of the original rule, run point-in-time so
a roster contains only what was knowable on the scan date.

## 2. Our variation vs. the standard technique

We run each rule **as published where our data allows, and say so plainly where it does not**. The
canon splits by what our primary-source data can compute point-in-time:

| Strategy (author) | The rule | How we run it | Fidelity |
|---|---|---|---|
| **Low-Volatility** (Haugen) | lowest realised vol | 25 lowest 66-day vol among liquid names | full |
| **Quality / QMJ** (AQR) | profitable, growing, safe | ROCE + margin + low-leverage percentile blend | full |
| **Coffee Can** (Mukherjea) | ROCE ≥15% & revenue growth ≥10%, long hold | 3-yr-avg ROCE ≥15 **and** 5-yr sales CAGR ≥10 | full (3y/5y proxy for the 10-yr every-year test) |
| **CANSLIM** (O'Neil) | earnings + new-high + leadership | profit acceleration + near-52w-high + RS rank | full |
| **GARP** (Lynch) | growth at a reasonable price | lowest PEG (P/E ÷ 3-yr earnings growth), quality-gated | full |
| **Magic Formula** (Greenblatt) | rank ROC + earnings yield | ROC = ROCE; **earnings yield = E/P** (see §6) | **proxy** — no PIT enterprise value |
| **Piotroski F-Score** (Piotroski) | 9 accounting signals | **5 of 9** computable today | **proxy** — cash-flow trio pending |
| **Graham Deep Value** (Graham) | low P/E, low P/B, current ratio | low P/E **and** low P/B | **proxy** — current-ratio leg missing |
| **Acquirer's Multiple** (Carlisle) | cheapest EV/EBIT | — | **not runnable** — needs PIT enterprise value |

The doctrine constraint (README §"doctrine") is enforced here: **price strength is the only gross
forward-return engine on our data; value and quality are context, not fundable rankers.** So the value
strategies are presented *with* their recorded results, not as recommendations.

## 3. How it works (methodology)

Nightly, `famous_strategies.refresh()` takes the liquid universe from the latest `momentum_scan`
(turnover ≥ ₹5cr), joins each name's point-in-time fundamentals via
[`fundamentals_asof.as_of_fundamentals`](../../src/automation/fundamentals_asof.py) (with the latest
bhav close as price), and applies each strategy's gate + ranking. Composite strategies rank by
cross-sectional percentile blends (the `pctrank` helper); single-axis strategies rank by their one
metric. Each produces a top-25 roster written to the isolated `classic_roster` table. The exact
thresholds live in the code, not here (calculations-and-weights doctrine — do not restate constants).

## 4. Status, validation & honesty fence

**DESCRIPTIVE-ONLY.** These rosters are research shortlists, not signals or advice. No claim is made
that any of them beats Nifty-500 buy-and-hold **net of realistic cost** — our own testing found the
opposite for most, and the value family worst of all:

- **Deep value / book-yield is HARD-REJECTED** on our data (negative alpha, beta ≈ 1.54, MaxDD ≈ −82%
  — the exact numbers are in [strategy-ledger.md](../strategy-ledger.md) § BLOCKING FAILURE MODELS).
  The Graham roster and the Magic Formula value leg are shown **as a caution**, next to that record.
- **Momentum/RS leadership** (CANSLIM's engine) is a real *gross* selection lens but its edge is a
  known risk-premium **beta**, not skill, and it dies on cost at scale (ledger § cost realism).
- **Quality** ranks nothing on its own (α ≈ 0); it earns its place as a filter (D66).

The one participation-fundable corner remains quarterly large-cap LOWVOL_MOM — see the Factor League
and [momentum-riskadj.md](momentum-riskadj.md). This page may not soften any of the above without a new
pre-registered, leak-free study recorded in the ledger (skill `failure-ledger`).

## 5. Where it lives (code · routes · DB · timers)

- **Compute:** [`src/automation/famous_strategies.py`](../../src/automation/famous_strategies.py) —
  pure scorers + `refresh()`; owns `classic_roster`. CLI `--refresh` / `--selftest`.
- **View:** [`src/web/classics_view.py`](../../src/web/classics_view.py) → **`/dash/classics`**
  (roster: `?s=<strategy>`; CSV: `?s=<strategy>&fmt=csv`).
- **Registry:** `lens_registry.py` key `classics` (altitude `strategies`); durable mount in
  `v2_surfaces._ROUTER_SPECS`.
- **DB:** isolated `classic_roster` in hermes.db (no `db.py` edit). **Timer:** wired alongside the
  nightly `momentum_scan` / `factor_league` refresh (after `momentum_scan` lands).
- **Tests:** [`tests/test_famous_strategies.py`](../../tests/test_famous_strategies.py); the route is
  covered by the no-orphan `test_dash_route_registry.py` and this doc by
  `test_strategy_docs_coverage.py`.

## 6. Data & provenance

**🔴 Source disclosure (Guardrail #8 — "disclose it where shown").** Split the claim in two, because
they are not the same:

| Layer | Source | Status |
|---|---|---|
| Price · momentum · volatility · turnover · universe · Nifty-500 benchmark | **NSE** (bhav copy 2004→, EQUITY_L, index feed) | **100% primary** |
| **Fundamentals** — ROCE · P/E · P/B · margins · growth (i.e. every non-price number on the page) | **Screener.in ≈90.9%** / NSE-XBRL ≈9.1% | **the remediating vendor exception** |

Measured 2026-07-15: 789,838 rows in `fundamentals_history` — 717,895 Screener-sourced (`source IS
NULL`), 66,686 `NSE-XBRL-CONSO`, 5,257 `NSE-XBRL-SA`. This estate **adds no new Screener dependency**
(it reads the existing archive; it never calls `screener.py`), but it does *rest* on one, and saying
"read point-in-time through `fundamentals_asof` (real BSE/NSE filing date…)" describes only the
**timing** gate — it must not be allowed to imply a primary **origin**. The `/dash/classics` page
carries the same disclosure (`_PROVENANCE`), dated on purpose: the split shifts as XBRL lands, and an
undated "91%" would itself go stale into an untruth.

**This makes phase 2 a remediation, not just a feature:** the annual-XBRL tags below are the route
*off* the 91% vendor dependency (forward from 2026-04), not merely the unlock for Acquirer's Multiple.

All fundamentals are read point-in-time through `fundamentals_asof` (real BSE/NSE filing date where
captured, else a conservative calibrated lag — no look-ahead). Price is the latest NSE bhav close
(primary). **Two known data gaps (Guardrail #8-clean to close via XBRL, not Screener):**

1. **No point-in-time enterprise value** (needs PIT cash + clean share count) → blocks true Magic
   Formula (EBIT/EV yield → we substitute E/P) and **all of** Acquirer's Multiple (EV/EBIT).
2. **No cash-flow statement / current-asset split** → blocks Piotroski's cash-flow trio (we ship an
   F5-of-9) and Graham's current-ratio leg.

Closing both is the **phase-2** task: add cash-flow + enterprise-value + current-asset tags to
`fundamentals_xbrl.extract_for` and backfill — then Magic Formula, Piotroski, Graham and Acquirer's
Multiple upgrade to full fidelity. This must NOT be done by extending `screener.py` (Guardrail #8).

**✅ Feasibility SETTLED by a live probe (S146) — the ANNUAL NSE XBRL filing carries all of it.**
A quarterly instance is P&L-only (65 tags; SEBI LODR requires the balance sheet + cash-flow
statement **annually**, not quarterly). An annual instance has **232 tags** including
`CashAndCashEquivalents` (→ enterprise value → true EBIT/EV **and** Acquirer's Multiple),
`CashFlowsFromUsedInOperatingActivities` (→ Piotroski's missing CFO trio → the full 9), and
`CurrentAssets`/`CurrentLiabilities` (→ Graham's current-ratio leg). Annual is the correct cadence —
Greenblatt, Piotroski and Graham are all annual rules. **Caveat:** XBRL is forward-only (2026-04→),
so this unblocks the RULES going forward; it does **not** deepen history (see §2 note on the ~2015
breadth cliff, which is a separate, unsolved data problem).

### Reconstructed portfolios (S146)
Each rule also runs as a NAMED, BACKDATABLE model portfolio via
[`classic_portfolios.py`](../../src/automation/classic_portfolios.py) — an additive sibling of the
`auto_portfolios` engine (reusing its clock/gate/band/cost/NAV math verbatim; the classics are NOT
admitted into that estate because they do not clear its "superior Sharpe + beats Nifty" bar). The
missing piece it adds is a **point-in-time fundamentals panel**. Books are charted only with **5+
years** of history (gate on YEARS, never rebalance count — 20 rebalances is 5y quarterly but 1.7y
monthly). Adoptable from `/dash/tracker/model-books` with **today** as entry — a reconstruction is
never written into a real book.

## 7. Terminology canon

| Say this | Means | Do NOT confuse with |
|---|---|---|
| **Classic Screens** | the named public strategies run as rosters (`/dash/classics`) | **Factor League** (the raw factor *families*, `/dash/factor-league`) |
| **Magic Formula (proxy)** | ROC (=ROCE) + **earnings yield (E/P)** rank | the true Greenblatt EBIT/EV yield (not yet computable PIT) |
| **F5** | our 5-of-9 Piotroski sub-score | the full 9-point Piotroski F-Score |
| **Coffee Can (our run)** | 3y-ROCE ≥15 & 5y-sales ≥10 | the strict 10-yr-every-year Marcellus construction |

## 8. Decision & session history

- **D133 / S145 (2026-07-14):** built the Classic Screens catalog + `/dash/classics` runnable lens
  (5 full + 3 proxy rosters), this canonical page, and the phase-1/phase-2 split. Sequencing chosen by
  Ramana: ship the computable strategies now, close the XBRL EV + cash-flow gap next.

## 9. Open items / frozen work

- **Phase 2 (data):** XBRL cash-flow + enterprise-value + current-asset tags → upgrades Magic Formula,
  Piotroski, Graham; unlocks Acquirer's Multiple (currently reference-only).
- **Home-exposure:** deliberately **not** a home tile in phase 1 (descriptive catalog; revisit once
  full-fidelity value screens land).
- Optional: a churn feed (roster entries/exits) like the Factor League's, if the rosters prove useful.

## 10. Sources of truth

- Result numbers / failure record: [strategy-ledger.md](../strategy-ledger.md) (never duplicated here).
- Factor doctrine: [momentum-riskadj.md](momentum-riskadj.md) · README §doctrine.
- Metric definitions: [metrics-glossary.md](../metrics-glossary.md).
- Running truth: [PROJECT_STATE.md](../../PROJECT_STATE.md) (D133 / S145).

## Maintenance

- When a strategy's rule, gate, or computability changes, update §2/§6 **in the same commit** as the
  code, and keep the `/dash/classics` card note (`_NOTE` in `classics_view.py`) in sync.
- When phase 2 lands, move the upgraded strategies from **proxy/none** to **full** in §2 and flip the
  card status; add Acquirer's Multiple to the runnable set.
- Never soften the DESCRIPTIVE-ONLY fence or the deep-value caution without a new ledger-recorded study.
