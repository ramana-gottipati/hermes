# Patearn Strategy Reference — Canonical Index

> **Class:** CANONICAL (permanent — do not archive). **Reconciled:** 2026-07-11 (S111).
> **Why this folder exists.** Our strategies are home-grown *variations* of known techniques, and
> their names had started to drift (DVPT vs DDPK vs MEP; CCI meaning two different things; "momentum"
> meaning both the RS axis and the factor engine). This folder is the **single canonical reference
> layer** — one authoritative page per strategy that fixes its **name, definition, current status,
> and terminology** so future sessions (and Ramana) always have one place to point at.

## What this layer is — and is NOT

This is a **reference index on top of** the existing material, not a replacement for it. Each page is
deliberately thin on math and heavy on *definition + current status + provenance + terminology*, and
it **links** to the deeper sources rather than duplicating them:

| Layer | Owner file(s) | This layer's relationship |
|---|---|---|
| **Canonical definition + status + terminology** | `docs/strategies/*.md` (**here**) | the anchor — start here |
| **Origin / provenance of each strategy** | [`origins.md`](origins.md) (**here**) | who created what — the 🧑 RAMANA / 🏠 HOUSE / 📚 CLASSIC map |
| Deep design-of-record | `docs/<strategy>-*-design.md` | linked from each page §10 |
| Fundability / benchmarks / **falsification ledger** | [`docs/strategy-ledger.md`](../strategy-ledger.md) | the single source for result tables — **never duplicated here** |
| Formula constants / weights | code + [`docs/calculations-and-weights.md`](../calculations-and-weights.md) | linked, never restated |
| Metric definitions | [`docs/metrics-glossary.md`](../metrics-glossary.md) | linked |
| Running project truth | [`../../PROJECT_STATE.md`](../../PROJECT_STATE.md) (Decision log / Session log) | cited by decision ID |

**Binding rule:** no page in this folder restates a formula constant or a backtest result table. If you
need the number, follow the link. This keeps the canon single-sourced (memory `calculations-weights-canonical`).

## The doctrine every page is consistent with

> **Price strength is the only gross forward-return engine.** Value, quality, credibility, delivery,
> and accumulation reads are **veto / filter / context layers — never rankers**, and **no factor here
> is a fundable net-of-cost alpha vs the index** (Nifty 500 buy-&-hold, Sharpe 0.89). The one
> participation-fundable corner is quarterly large-cap **LOWVOL_MOM** (~1.02 @₹50cr, ~₹100cr ceiling).
> **The asset is PIT rigor + under-covered primary data + the analytical selection lens — not a
> backtested alpha strategy.** (Source: [strategy-ledger.md](../strategy-ledger.md) "BLOCKING FAILURE
> MODELS" corollary; memory `failure-models-ledger`.)

Because of this doctrine, most pages carry a **DESCRIPTIVE-ONLY** honesty fence. That is not a hedge —
it is the recorded, evidence-backed status. Do not "promote" any descriptive lens to a ranked/traded
strategy without its own pre-registered, leak-free study that beats the recorded numbers.

## Status matrix (the canonical strategies)

| Strategy | Canonical name | Status | Governing decision(s) | Page |
|---|---|---|---|---|
| **DVPT** | Delivery Value per Trade ("Positioning") | **DESCRIPTIVE-ONLY** — engine live, picker thesis refuted | D62 · D28/D31/D43/D44 · D56 · D107 · D47 | [dvpt.md](dvpt.md) |
| **MEP** | signed accumulation/distribution (price-tape) | **DESCRIPTOR-ONLY** — failed the alpha gate | D62 · D65 · D61 | [mep.md](mep.md) |
| **Wolfe Wave** | 5-point reversal geometry (Patearn variation) | **DESCRIPTIVE-ONLY** · §B scoring **ratified D111** (max = `_QUALITY_MAX`, now 27) | D96 · D108 · D109 · D111 · D113 | [wolfe-wave.md](wolfe-wave.md) |
| **Relative Strength** | RS suite (RRG · RS-band · rotation · Mansfield · capture · size-index) | **DESCRIPTIVE** lens suite (deployed) | D39 · D40 · D64 · D67 | [relative-strength.md](relative-strength.md) |
| **CPR** | Central Pivot Range ("CPR Spine") | **LIVE** — descriptive charting lens | D53 · D71 | [cpr.md](cpr.md) |
| **Reversal Context** | STREAM BAND + FRACTAL FLOOR/CEILING (band-state · stretch · floor geometry) | **DESCRIPTIVE-ONLY** — every tradeable form falsified; context columns live | ledger §§ 07-13/07-14/07-14b/07-14c · S132b/c | [reversal-context.md](reversal-context.md) |
| **CCI** | **Concall Credibility Index** (≠ Commodity Channel Index) | **FAILED-AS-FACTOR → DESCRIPTIVE / VETO-ONLY** | D60 · D61 · 2026-06-25 falsification · Gate B fail | [cci.md](cci.md) |
| **Harmonic** | XABCD / PRZ patterns | **LIVE** (descriptive) · backtest-GATED | D72 · D71 | [harmonic.md](harmonic.md) |
| **Momentum / RISKADJ** | ranked-rotation factor engine (the benchmark) | **BENCHMARK** · gross selection, **not fundable net of cost** | D66 + ledger benchmarks | [momentum-riskadj.md](momentum-riskadj.md) |
| **patearn** | 14-pattern PIT fundamental-quality methodology | **DEPLOYED** analytical lens (not run as standalone alpha) | D66 · D76 · D7/D8/D24 | [patearn.md](patearn.md) |
| **Classic Screens** | famous public strategies (Magic Formula · CANSLIM · Piotroski · Coffee Can · GARP · Graham · Quality · Low-Vol) run as live rosters on our PIT data | **DESCRIPTIVE-ONLY** — 5 full + 3 proxy; value shown with its recorded failure numbers | D133 · D66 · Guardrail #8 | [classic-screens.md](classic-screens.md) |

## Terminology canon (the master anti-drift table)

The whole reason this folder exists. Use the **canonical** column; retire the **deprecated** column.

| Say this | Means | Do NOT confuse with / stop saying |
|---|---|---|
| **DVPT** | Delivery Value per Trade — a **side-blind magnitude** off NSE delivery data | **DDPK** (deprecated informal shorthand for DVPT) · **DBP** (a mis-transcription) · MEP (different strategy) |
| **MEP** | **signed** accumulation(+)/distribution(−) off the **price tape** (OHLC+VWAP+volume) | DVPT (delivery, side-blind) · "DDPK" |
| **"accumulation"** | context-dependent: DVPT-sense = the D43 delivery *character* label; MEP-sense = the signed *positive score* | using it unqualified when both DVPT and MEP are on screen |
| **RS / RS-Momentum** | relative strength vs the index (the RRG y-axis, RS-band, rotation) | the **Momentum FACTOR** (RISKADJ engine) — a different, return-tested thing |
| **Momentum (factor)** | RISKADJ ranked-rotation = 6-mo return ÷ 3-mo vol, top-25 monthly | RS-Momentum (descriptive) · "momentum is fundable" (it is **not**, net of cost) |
| **CCI** | **Concall Credibility Index** (the scored core of the "Concall Intelligence" program) | **Commodity Channel Index** (an unrelated price oscillator) |
| **CPR** | **Central Pivot Range** (Pivot + BC/TC), the "CPR Spine" charting lens | generic support/resistance · RS-band |
| **STREAM BAND** | a 13-EMA high/low band + 5-EMA HLC/3 trigger; **RECLAIM** = the buy-cross (a *caution*, an anti-signal — not an entry) | CPR (pivot band) · RS-band (relative strength) |
| **FRACTAL FLOOR / CEILING** | the latest *confirmed* Williams down/up-fractal as a support/invalidation **risk-geometry** level | Wolfe fractal *gate* (same primitive, different use) · a breakout *trigger* (falsified) |
| **Wolfe: "strength"** | the §B score — eight components (max = `_QUALITY_MAX`, now 27), ratified D111 (spring-and-reclaim C, §A9); **freshness is NOT strength** | recency/freshness · the removed D98–D102 STR/LND vocabulary · "D111 = the draw tool" (D111 is the §B rescore; the draw tool is **D113**) |
| **"C" (capital allocation)** | the modern quality composite (ROIIC, ROCE, dilution, debt-funding, growth efficiency) | the older 4-metric quality lens it **subsumes** (D66) |
| **Classic Screens** | the famous NAMED strategies run as rosters (`/dash/classics`) | **Factor League** (the raw factor *families*, `/dash/factor-league`) — related but different granularity |
| **Magic Formula (our run)** | ROC (=ROCE) + earnings yield (E/P proxy) | the true Greenblatt EBIT/EV yield (not yet computable PIT) |

## The rest of the estate (catalogued — design doc is the current reference)

These are real, discussed strategies/lenses that are **covered by their design docs** and don't yet
have a dedicated canonical page. They are listed here so nothing is orphaned; promote any of them to a
full page on request.

| Lens | Status | Reference |
|---|---|---|
| **Ignition (champion/challenger)** | built; the DVPT ×power intensity ranking + ML challenger | covered in [dvpt.md](dvpt.md) §3/§5; design [ignition-champion-challenger-design.md](../ignition-champion-challenger-design.md) |
| **MTF (multi-timeframe positioning)** | agreed; weekly/monthly rollup shipped, materialised MTF signals not | [multi-timeframe-positioning-design.md](../multi-timeframe-positioning-design.md) |
| **Explosive-move / "Launchpad"** | validated as a **screen** only — no fundable edge net of cost | [explosive-move-research.md](../explosive-move-research.md); ledger Tier-2 |
| **PEAD / Results-Reactions** | descriptive event lens — **every tradeable wrapper falsified**; the drift is real descriptively | [strategy-ledger.md](../strategy-ledger.md) "PEAD…"; `pead_surface.py`; `/dash/results-reactions` |
| **Concall Intelligence (content / growth-intent)** | descriptive candor axis — content edge **placebo-killed** (2026-07-08) | covered in [cci.md](cci.md); [concall-intelligence-design.md](../concall-intelligence-design.md) |
| **Season / event-study estate (E-02…E-14)** | armed, self-gating, **descriptive**; placebo harness kills would-be lenses | ledger "Studies 2026-07-08"; memory `season-armed-triggers-estate` |

## ⚠ Known reconciliation items (surfaced during the S109 build)

Honest gaps the doc build found. **Items 1–3 have since been RESOLVED; 4–5 remain open:**

1. **✅ RESOLVED — Wolfe draw tool merged (D113 / S112, `35a11e7`).** It is now on main together with the
   D109 lifecycle layer (the abandoned branch commit `8fc40dc` was not used; the tool was provisionally
   "D111" before the §B rescore claimed that number → renumbered **D113**). The §B freeze is lifted (the
   rescore = **D111**, `dfbe175`, S109). See [wolfe-wave.md](wolfe-wave.md) §5/§8.
2. **✅ RESOLVED — patearn code↔methodology mapping made explicit (D114).** The deliberate patterns-6–14
   computable adaptation is now mapped in [patterns.md](../../resources/patearn/patterns.md) § "Implementation
   mapping (scoring.py)", and the stale `# Pattern weights from patterns.md` comment is corrected — scoring
   output unchanged. See [patearn.md](patearn.md) §9.
3. **✅ RESOLVED — `calculations-and-weights.md` now covers DVPT / MEP / CCI / Harmonic.** Added §5e (DVPT
   two-tier trigger), §5f (MEP signed accum/distrib + phase hysteresis), §5g (CCI credibility weights),
   §5h (Harmonic XABCD ratio bands) — real constants pulled from code, matching the house style. The
   "numbers live in calculations-and-weights.md" doctrine now holds for every strategy page.
4. **RS D67 size-index backfill** — the 11 cap-segment RS history requires a one-time VPS
   `index_signals --backfill`; **not verifiable from the repo** — confirm on the box. See [relative-strength.md](relative-strength.md) §9.
5. **CPR Telegram `/cpr`** — designed (design §7) but **never shipped** (`telegram_bot.py` has no `cpr`
   ref); listed as an unbuilt aspiration, not a live surface. See [cpr.md](cpr.md) §9.

## Maintenance protocol (this is the "maintained" in "create and maintain")

1. **Update-in-the-same-commit.** When a session changes a strategy's math, status, data, or naming,
   update its page **in the same commit** as the code — same discipline as the PROJECT_STATE rule
   (CLAUDE.md 🔴 MANDATORY UPDATE RULE). The page's own §Maintenance says what to keep in sync.
2. **Status badge is load-bearing.** The `Status` line and any 🧊 FREEZE callout are what other lanes
   read before touching a strategy. Keep them current (esp. Wolfe's §B freeze).
3. **Honesty fence is non-negotiable.** A page may never soften a DESCRIPTIVE-ONLY / FAILED-AS-FACTOR
   status without a new pre-registered, leak-free study recorded in [strategy-ledger.md](../strategy-ledger.md)
   that beats the recorded numbers (skill `failure-ledger`).
4. **Adding a new strategy.** Copy the shared template (below), fill all 10 sections + Maintenance, add
   a row to the Status matrix + Terminology canon here, **serve it** (add the slug to
   `src/web/strategies_view.py` `_PAGES` → renders at `/dash/strategy-ref?p=<slug>`), and wire it into
   [DOC_INDEX.md](../DOC_INDEX.md) and `PROJECT_STATE.md` § Key file paths.
5. **Keep siblings in sync.** DVPT ↔ MEP, RS ↔ Momentum, Wolfe ↔ Harmonic cross-link each other; a
   terminology change on one must be mirrored on its sibling.
6. **Machine backstop — the continuous-docs gate.** `tests/test_strategy_docs_coverage.py` FAILS the
   suite if the artifacts drift: every served page must have a file on disk **and** a Status-matrix row,
   and every `docs/strategies/*.md` must be served. It is the enforcement behind items 1 & 4 — run it
   (or the suite) before shipping any strategy change. (It cannot catch a strategy built in code with
   *no* doc at all — that stays the CLAUDE.md new-strategy rule's job.)

### Shared template (copy for any new strategy page)

```
# <Full Name> (<ALIAS>) — Canonical Reference
> Class · Status · Governing decision(s) · Reconciled · Charter (links to design/ledger/calc)
**One-line definition:** <the terminology-anchor sentence>
## 1. What it is
## 2. Our variation vs. the standard technique
## 3. How it works (methodology)   ← link constants, never restate
## 4. Status, validation & honesty fence   ← cite ledger numbers + decision IDs
## 5. Where it lives (code · routes · DB · timers)
## 6. Data & provenance   ← primary-source status; leak fences
## 7. Terminology canon   ← canonical name · aliases · deprecated · disambiguation
## 8. Decision & session history
## 9. Open items / frozen work
## 10. Sources of truth
## Maintenance
```
