# CCI falsification gates (P6 — THE DECISION)

Offline, **read-only** kill-or-save tests for the Concall-Intelligence strategy
(debate rank #2, `docs/concall-intelligence-design.md` §13, `…-debate.md`). They
decide whether CCI ships as a **standalone ranked book** or is **merged into pt14**
as an avoid-tape / quality overlay. The honest stance (design §10): CCI is carried
as a **screen/overlay** until these gates — and the §P8 backtest — clear it.

## The two gates

| Gate | Script | Question | Decision rule |
|---|---|---|---|
| **A** | `gate_guidance_return.py` | Does guidance **direction** (net UP vs DOWN promises in a call) predict the **forward return** (enter T+2, hold ~3m, net of cost, survivorship-safe)? | FAIL/WEAK → CCI is **not** a return engine; keep it an avoid-tape/overlay. |
| **B** | `gate_residual_alpha.py` | Does the credibility composite carry **incremental** alpha after orthogonalising vs **quality (ROCE/debt) + size + 12-1 momentum + PEAD** (Newey-West HAC)? | credibility coef **not** significant → **MERGE into pt14, do NOT ship standalone**. |

Both rank/test **measurable signals only** (D61): guidance direction, the credibility
composite, quantification — never the 0-100 behaviour axes.

## How to run (VPS, isolated research venv)

```bash
ssh hermes
cd /opt/hermes
# gate A needs only numpy (already in .venv-research from the explosive-move work):
.venv-research/bin/python -m research.cci.gate_guidance_return
# gate B additionally needs statsmodels:
.venv-research/bin/pip install statsmodels
.venv-research/bin/python -m research.cci.gate_residual_alpha
```

## ⏳ Status: BUILT, AWAITING DATA

The gates are complete and run today, but the **verdict needs ≥ ~40 extracted
concalls across the golden set** (`resources/cci/golden_set.csv`). On thin data they
print `INSUFFICIENT DATA` and a smoke-check of the wiring, and exit cleanly — they do
**not** fabricate a verdict. The Gemini free tier (20 req/day) means the historical
backfill accrues over time: **`hermes-concalls.timer` drains ~18 concalls/day
oldest-first**, so re-run the gates after ~2 weeks (or accelerate the backfill via
claude.ai-paste / paid Gemini — Ramana's routing call). `MIN_OBS` in `common.py` is
the refuse-to-render threshold.

## Known limitations (documented, not hidden)
- **Concall date** is approximated as the 15th of the concall month (the precise
  `concall_dt` three-clock model is deferred — debate #4). Forward returns enter T+2
  to stay clear of the immediate reaction regardless.
- **ROCE/debt** are the latest fundamentals snapshot, not point-in-time (no
  point-in-time fundamentals history yet). Size/momentum/PEAD **are** point-in-time
  from the bhav archive.
- **Credibility** in gate B is the per-symbol composite; per-period credibility
  scoring is a later refinement.
- Blowup pre-collapse calls (2017-2019) have **no matching `concall_results`** (the
  Screener quarterly table only reaches ~FY2023), so they contribute to gate A
  (forward return is from the bhav archive, which reaches 2012) but their guidance
  does not *settle*. Discrimination of a single pre-collapse call also needs ≥2
  consecutive extracted calls for the deterioration diff to fire.
