# Reversal Context — STREAM BAND + FRACTAL FLOOR — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** **DESCRIPTIVE-ONLY** (context columns are LIVE on Screen+; every *tradeable* form — timing, breakout craft, risk-geometry book at true cost, and ex-ante selection — was **falsified** under pre-registered, tamper-clean study). · **Governing decision(s):** the reversal-pair arc, ledger §§ 2026-07-13 / 07-14 / 07-14b / 07-14c (+ exit studies 07-14d / 07-14e) · S132b/S132c (the two Screen+ pills). · **Reconciled:** 2026-07-14 (S147).
> **Origin:** 🧑 RAMANA (both constructs dictated — the 13-EMA HiLo band + 5-EMA HLC/3 trigger, and the Williams-fractal floor/ceiling reversal radar) + 🏠 HOUSE honesty fences + measurement. See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference for the reversal-context columns. Falsification record (numbers live there, never restated here): [strategy-ledger.md](../strategy-ledger.md) §§ 07-13 → 07-14e. Live engine: `src/automation/reversal_context.py`. Numbers/constants live in code; this page never restates them — it links.

**One-line definition:** the two survivors of Ramana's reversal-pair research — **STREAM BAND** (a 13-EMA high/low band with a 5-EMA HLC/3 trigger) and **FRACTAL FLOOR/CEILING** (the latest confirmed Williams down/up-fractal as a support/invalidation level) — shipped **only** as descriptive context columns (band state · own-history stretch percentile · risk-geometry floor), because every tradeable form of the pair was pre-registered and **falsified** at every level.

---

## 1. What it is

Two related structures Ramana specified (2026-07-13 voice-note session) for catching reversals off a stretched, beaten-down tape:

- **STREAM BAND** — an EMA13-of-highs / EMA13-of-lows envelope with an EMA5-of-(H+L+C)/3 "trigger stream" running through it. The read is the **position** of the trigger relative to the banks (BELOW · CROSS-UP/**RECLAIM** · INSIDE · CROSS-DOWN/**SLIP** · ABOVE) plus a **STRETCH** measure: how far the trigger has deviated from the violated bank, ranked as a **percentile against the stock's own trailing history** (per-stock, percent, never a rupee threshold — Ramana's no-static-threshold rule).
- **FRACTAL FLOOR / CEILING** — the latest **confirmed** degree-10 (fallback degree-5) down-fractal low is a well-defined **support / invalidation level**; the mirror up-fractal high is the ceiling. A 10-fractal that still holds implies a ≥20-bar consolidation by construction. The useful read is **risk geometry**: how far above a confirmed floor price sits, how old the floor is, and whether it is still unbroken.

Both are pure-Python over the NSE bhav archive, ₹0, no LLM, point-in-time honest (a degree-N fractal is only used once N bars have printed after it).

## 2. Our variation vs. the standard technique

- **STREAM BAND** is in the Gann-HiLo / high-low-channel family (sane prior art). The proprietary treatment is the **STRETCH percentile vs the stock's own trailing 756-bar history** — which resolves the cap-size problem exactly (a small-cap at 8% may be p60; a large-cap at 4% may be p97, the more actionable read), where no global threshold can.
- **FRACTAL FLOOR** reuses the validated Williams-fractal primitive (`fractal_pivots` in `wolfe.py`, shared with the Wolfe lens under the D108 gate — not forked) and reframes the confirmed fractal as a **cheap, well-defined place to be wrong** rather than as an entry trigger.

## 3. How it works (methodology)

All constants (EMA lengths, the 756-bar stretch window, fractal degrees, floor lookback) live in [`src/automation/reversal_context.py`](../../src/automation/reversal_context.py) (`EMA_FAST`/`EMA_SLOW`, `STRETCH_WIN`, `DEGREES`, `FLOOR_LOOKBACK`) — **not restated here**. The module computes one latest row per symbol into the isolated `reversal_context` table (bounded snapshot; space rule; no `db.py` edit — the `signal_alerts.py` isolation pattern) and stamps every fractal's `knowable_at` implicitly by only consuming confirmed pivots.

The Screen+ **"rev" column-group** renders four/six descriptive cells per symbol (`_rev_cells` in `screener_plus.py`): **band state** (with the reclaim cross labelled a **caution**), **stretch %**, **stretch percentile**, and the **floor** (+ ceiling) level. Two filter pills — `?rev=ri` ("⚠ Reclaim · floor intact") and `?rev=si` (the bearish mirror, "⚠ Slip · ceiling intact") — surface the band event **with** its confirmed fractal context. None is an entry or an alert.

## 4. Status, validation & honesty fence

**DESCRIPTIVE-ONLY, and the falsification is the product copy.** This is a binding fence — the project keeps a falsified-approaches ledger and softening this status is a blocking error. The reversal pair was tested **pre-registered + hash-frozen + tamper-clean** and is **falsified at every level** (all numbers in [strategy-ledger.md](../strategy-ledger.md)):

- **Timing (07-13, STREAM BAND).** The BUY-cross is an **anti-signal** — it *negatively* selects; both matched placebos beat it; the book never approaches the 0.89 hurdle. An early band-reclaim after a real downtrend is a falling knife more often than a reversal → the cross **never ships as an entry/alert**; only the descriptive state + stretch-percentile survive.
- **Confirmation craft (07-14, FRACTAL FLOOR).** The up-fractal breakout confirmation adds **≈ nothing** over mere floor proximity at fixed horizons; "STRONG" (beats the first two up-fractals) is *worse*. The floor is the information; the breakout craft is not. *(The interim "PROX10 book return/vol 1.04" was a **gross-of-cost accounting defect** — see next.)*
- **Risk-geometry book at true cost (07-14b, FENCES).** The reconstruction gate caught our own defect: true flat-cost PROX10 = **0.59** (below the hurdle — the candidate was never alive). All three fences then failed — participation cost decays catastrophically with AUM, a random-entry/same-exit control reproduces the book (the entry is ~inert; the P&L was the exit geometry), and realistic fills sink it further.
- **Ex-ante selection (07-14c, RECLAIM SELECTION).** Even validated factors cannot pick the launchers in advance: the best frozen rule (low-vol + above-own-norm delivery) merely *stops the bleeding* — it matches random same-stock days (δ vs placebo ≈ 0). The right tail exists but is **not identifiable in advance** from price/volume features.
- **Exit studies (07-14d MANAGED, 07-14e EXIT LAB).** Ramana's dictated Case-A stop/re-entry stack is **not-improved** (the two-candle exit churns to −0.50); across ten exit engines the **exit law is monotonic in looseness** (slow/wide best, profit-takers worst) and the ceiling is ~0.63 OOS < 0.89 — exits shape losses, they cannot mint edge.

**What survives (as shipped):** the descriptive context columns + the two watch pills. The one reusable, **non-tradeable** nugget: among knife-bounces, **low-vol + above-own-norm-delivery** names are consistently *less bad* — context for triage, **never a rank**. Any future reversal proposal **must cite ledger §§ 07-13 / 07-14 / 07-14b / 07-14c first** (skill `failure-ledger`). This is coherent with project doctrine: *price strength is the only gross forward-return engine; reversal/band/floor reads are context, never rankers or fundable alpha.*

## 5. Where it lives (code · routes · DB · timers)

- **Compute:** [`src/automation/reversal_context.py`](../../src/automation/reversal_context.py) (pure-stdlib) → the isolated **`reversal_context`** table (one latest row per symbol; `db.py` untouched). CLI `--compute` / `--selftest`. Fractal primitive reused from `wolfe.py` (`fractal_pivots`).
- **Surfaces:** Screen+ (`/dash/screen2`) **"rev" column-group** (`_revctx_by_sym` + `_rev_cells` in [`src/web/screener_plus.py`](../../src/web/screener_plus.py), read-only) + the `?rev=ri` / `?rev=si` filter pills. Descriptive columns only — band state · stretch % · stretch percentile · floor · ceiling.
- **Timer:** nightly compute piggybacks on the existing signals chain (no new systemd unit); deploy = scp + writer-safe restart.

## 6. Data & provenance

- **Primary source only** — NSE bhav copy OHLC (split/bonus-adjusted via `src.automation.adjust`); no vendor, no Screener (Guardrail #8). Pure stdlib (prod venv has no numpy), ₹0, no LLM.
- **Point-in-time / no-look-ahead** — a degree-N fractal is only consumed once N bars have printed after it; the stretch percentile reads only trailing stored values.

## 7. Terminology canon

- **STREAM BAND** — the EMA13(high)/EMA13(low) bands + EMA5(HLC/3) trigger stream. Band states: BELOW · **RECLAIM** (cross-up, a *caution* not an entry) · INSIDE · **SLIP** (cross-down) · ABOVE.
- **STRETCH** — signed % gap between the trigger and the violated bank, **ranked as a percentile vs the stock's own trailing history** (per-stock, percent — never absolute).
- **FRACTAL FLOOR / CEILING** — the latest *confirmed* degree-10 (fallback 5) down-fractal low (support/invalidation) / up-fractal high (mirror). Read as **risk geometry** (gap %, age, alive?), never as a trigger.
- **Reclaim / Slip pills** — `?rev=ri` = reclaim with the floor still intact; `?rev=si` = the bearish slip mirror with the ceiling intact.
- ⚠ **Deprecated as *signals*** — "band-reclaim buy", "fractal breakout trigger", "PROX10 book". These are **falsified** (§4); the words survive only as descriptive state labels, never as entries.

## 8. Decision & session history

- **2026-07-13 (voice-note)** — Ramana specifies the reversal pair (STREAM BAND his stated priority + FRACTAL FLOOR); build order = descriptive screener → pre-registered study → book only if it survives.
- **07-13 → 07-14e (ledger)** — six pre-registered, hash-frozen, tamper-clean studies falsify every tradeable form (timing / craft / risk-geometry book / selection / two exit labs). Full record + numbers: [strategy-ledger.md](../strategy-ledger.md).
- **S132b / S132c** — the two Screen+ pills shipped (reclaim `?rev=ri`, slip `?rev=si`) with the honesty fence in the product copy; `reversal_context.py` is the live descriptive engine.
- **S147 (2026-07-14)** — this canonical page created (the arc's home moved out of the transient `reversal-pair-PLAN.md`, now retired); origin label 🧑 RAMANA recorded.

## 9. Open items / frozen work

- **RULED OUT (do not re-open) — the reversal pair as a signal / entry / book.** Falsified at all four levels; any re-attempt is blocked until it beats the recorded numbers, net of cost, under the same no-leak harness (skill `failure-ledger`).
- **Bear-mirror parity** — the ceiling columns exist; a full bear-side study was deferred/disclosed (non-shortable in the harness), never a live short signal.
- **Phase-3 chart overlay** (the 13/13/5 ribbon + fractal markers on `/dash/stock`) was a design aspiration in the retired PLAN doc — not built; not required (the descriptive columns are the shipped surface).

## 10. Sources of truth

- Falsification & numbers (single source): [strategy-ledger.md](../strategy-ledger.md) §§ Study 2026-07-13 / 07-14 / 07-14b / 07-14c / 07-14d / 07-14e.
- Code: [`src/automation/reversal_context.py`](../../src/automation/reversal_context.py) (engine + module docstring = the canonical prose) · [`src/web/screener_plus.py`](../../src/web/screener_plus.py) (the "rev" group + pills).
- Sibling references: [wolfe-wave.md](wolfe-wave.md) (shares the fractal primitive + the selection-not-craft doctrine) · [dvpt.md](dvpt.md) / [mep.md](mep.md) (the descriptive-only doctrine).
- Provenance: [origins.md](origins.md) (🧑 RAMANA rows: STREAM BAND · FRACTAL FLOOR/CEILING · Reversal context columns).
- Memory: `failure-models-ledger`, `record-and-remind`.

## Maintenance

When a future session changes the reversal-context engine (EMA lengths, the stretch window, fractal degrees, the floor lookback) or its Screen+ columns, update **this page + the code + the ledger** in the same commit (state-doc + strategy-docs coverage gates). **Keep the §4 falsification fence intact** — reviving any tradeable form is blocked until it beats the recorded ledger numbers net of cost. Keep the 🧑 RAMANA origin label. Keep this page and [wolfe-wave.md](wolfe-wave.md) in sync on the shared fractal primitive.
