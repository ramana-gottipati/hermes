# PROPOSALS-02 — Claude's filtered evaluation of Codex review 02

**From the bridge protocol:** Codex reviews → Claude evaluates vs project direction → Ramana approves →
Claude implements approved-only. This is the filtered set. **Nothing is implemented yet — awaiting Ramana's go.**

## Verification I (Claude) ran independently (not taking Codex on faith)
- ✅ **Confirmed:** repo `src/main.py` does NOT call `v2_surfaces.wire(app)` (grep: not found). The hook is
  only applied by *running* `scripts/wire_v2_surfaces.py`. So a clean repo deploy serves legacy chrome +
  404s Coverage/RS-hub/Wire/_ui.
- ✅ **Confirmed:** `src/web/growth_view.py` is **untracked** (`??`) → not in the repo at all. `testing_view.py`
  is tracked but its router is not mounted in repo main.py → `/dash/testing` 404 in a clean checkout.
- ✅ **Root of my blind spot:** `regression_sweep.sh` curls the **live VPS** (already wired) — it cannot
  catch a repo-checkout gap. Codex tested a clean checkout via TestClient. Its acceptance-gate point is correct.

## Proposal set
| # | Source | Proposal | Risk | Priority | Claude's call |
|---|---|---|---|---|---|
| **1** | P0a | **Make the repo self-sufficient.** Add the 2-line `v2_surfaces.wire(app)` hook to committed `main.py` (defensive try/except); fold the redundant Lane-B block into `_ROUTER_SPECS`; commit `growth_view.py`; mount `testing_view`. Net: a clean `git clone` + deploy renders the full v2 site + trust surfaces. | Low — additive, reversible, idempotent (wire is sentinel-guarded). `main.py` is shared but lanes are idle; EOF hook only. | **P0** | **Recommend now** |
| **2** | P0b | **Upgrade the release gate.** Extend `scripts/regression_sweep.sh` (or a new gate) to run a **clean-checkout TestClient sweep** AND assert HTML chrome markers (`uk-skin`, `v2bar`, `Trust`, `Wire`, RS-hub, **no `.hsearch`**) — not just live-VPS 200s. | Low — test tooling only. | **P0** | **Recommend now** |
| **3** | P1 (route truth) | **Nav truth.** No nav entry may point to a route that 404s in a clean checkout. Fixed as a side-effect of #1 (growth/testing); add a gate assertion that every `_IA_SUB` href resolves. | Low. | **P1** | **Recommend now** |
| **4** | P1 (lead wedge) | **Trust-as-front-door** — keep "Trust" in top chrome (already there) and make Coverage the demo's first beat. | None (positioning). | P1 | **Ramana's call** (GTM) |
| **5** | P1 (visual) | **Visual discipline for banks** — restrain "futuristic"/glow/aurora; read as audit-grade workstation. | Low (design taste). | P1 | **Ramana's call** (design) |
| **6** | P2 (legacy shell) | **Native-page migration order** for the top demo route (Coverage → Markets → RS hub → Screener → Stock), retiring runtime-skin there. Aligns with Lane A2. | Medium (real build). | P2 | **Defer / schedule** |
| **7** | P2 (demo) | **Linear demo script** — Coverage → Markets → RS hub → Screener/Screen+ → Stock → Tracker → Pat ⌘K. | None. | P2 | **Ramana's call** (GTM) |

## Recommendation
Greenlight **#1, #2, #3** now — they are the credibility-critical, low-risk reproducibility fixes (a
bank-facing demo must survive a redeploy from repo, and the gate must prove it). Treat **#4, #5, #7** as
Ramana's positioning/design decisions. **#6** is a real build → schedule as a lane, not a quick fix.

## Honest note
Codex caught a genuine durability/reproducibility gap that my earlier "durability done" status and my
VPS-only harness both missed. The fix is small and the gate upgrade prevents a recurrence.
