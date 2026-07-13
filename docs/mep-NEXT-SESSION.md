# MEP — NEXT-SESSION handoff & self-prompt (2026-06-22)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the MEP follow-ups ship + fold. Registered in `docs/DOC_INDEX.md`.


> **TRANSIENT run-book** (per [[transient-doc-lifecycle]]). Retire when the OPEN ITEMS below are closed.
> Canonical design + per-step verification: **`docs/mep-strategy-design.md`**. Memory: **[[mep-strategy-built-deployed]]**.
> Terminology (Ramana's shorthand, not in code): **DDPK = DVPT**; **MEP = signed accumulation/distribution**.

---

## TL;DR — where MEP stands

MEP = a **signed** accumulation(+)/distribution(−) descriptor, computed from the OHLC+VWAP+volume tape (NOT delivery-per-trade). **Built, deployed, verified, committed** across all stock surfaces; **descriptor-only** (its predictive role FAILED a walk-forward + Deflated-Sharpe gate — D62, so it characterises/confirms, never ranks/picks). It **auto-updates every trading night** (in the `hermes-bhavcopy.service.d/10-signals.conf` chain, right after DVPT). Full history backfilled (7.56M rows, 2004→2026).

**Live surfaces:** `/dash/mep` (the dedicated BOTH-sides screen — 150 accumulators + 150 distributors, 5-state count strip, raw terms, accum/distrib filter) · home pillar "Accum/Distrib" + Net-accumulation/Distribution-watch boards · screener `accumulation·mep` column-group · stock-page "Accumulation·MEP" tab+dossier · `/dash/index` intra-index MEP board (both sides) · Conviction display-only column · Pat `mep`/`mep_state` glossary. Every MEP link → `/dash/mep`.

**★ THE CATCH — ✅ FIXED (2026-06-22, session 35).** MEP used to **flip state ~3 days out of 4** (RELIANCE 50 changes / 70 rows; TCS 54; SUZLON 41) — a daily oscillator, not a phase. Now there's a smoothed, hysteresis-banded **PHASE** (`mep_score_smooth` / `mep_state_smooth`, 15-row mean) headlined on every surface, daily kept underneath: **48.8 → 5.8 changes/70, max 8, all single-digit (8.5×).** Engine + UI committed + deployed + verified. Design+calibration in `docs/mep-strategy-design.md` §9. **Open items #1 & #2 are now closed** (below); the live items are #3 (F&O OI) and #4 (Pat routing) — both **Ramana's call**.

---

## OPEN ITEMS (priority order)

### 1. ★ MEP smoothing → make it a real PHASE — ✅ DONE (2026-06-22, session 35)
**Shipped exactly as specified.** `mep_score_smooth` = rolling mean of the daily `mep_score` over **15** trading rows (the "~10" was widened to 15 — the smallest window that makes EVERY reference stock single-digit; calibrated on the VPS). `mep_state_smooth` = the smoothed score through a **hysteresis ladder** (asymmetric enter/exit deadbands, e.g. STRONG_ACCUM enters at +0.62 / exits at +0.40). The **smoothed PHASE is now the headline** on `/dash/mep` (+ a "Today" daily column), the home boards, the pillar count, the screener, the intra-index board, conviction, and the stock dossier (+ a "held in phase" days stat); the daily score is kept underneath. Implemented in `src/automation/mep_signals.py` (`_smooth_chain` for backfill/`--resmooth`; `_smooth_date` auto-called by `compute_for_date` for the nightly — no systemd change; backfill≡incremental to float epsilon). Columns added to `db.py` SCHEMA_BASE + migrated live via `ensure_table()`. **Verified: 48.8 → 5.8 changes/70, max 8, all single-digit (8.5×).** Full write-up: `docs/mep-strategy-design.md` §9.

### 2. Document the multi-lens accumulation/distribution decode — ✅ DONE (2026-06-22, session 35)
Written into `docs/mep-strategy-design.md` **§10** (3 channels, the lens/equation table, NAP synthesis, the descriptor-only verdict + the killer line). The essence preserved (kept here too for quick reference):

**Three channels, rising information content:** (1) **bar/tape** — infer from one day's OHLC/VWAP/vol (cheap, but your data keeps refuting its *predictive* power); (2) **dynamics** — infer the footprint over time (persistence, vol-compression — where the validated Launchpad edge lives); (3) **identity** — directly observe WHO (named flows, holdings deltas, F&O OI — the only channel that names the strong hand).

**The lenses + equations (signed where possible):**
| Lens (channel) | Equation | Accum ↔ Distrib |
|---|---|---|
| Close-vs-VWAP pressure (bar) | `(close−VWAP)/VWAP` | close>VWAP on vol ↔ close<VWAP |
| Effort/Result · Amihud (bar) | `|r| / turnover` | heavy vol, price won't fall ↔ won't rise |
| Bar anatomy · Chaikin (bar) | `CLV=((C−L)−(H−C))/(H−L)`, `ΣCLV·V` | closes near high ↔ near low (⚠ REFUTED as a predictor) |
| Permanence · Kyle-λ (dynamics) | fraction of move retained k days | moves stick (informed) ↔ revert (churn) |
| Persistence (dynamics) | `VR(k)=Var(r^k)/(k·Var(r^1))` | VR>1 drift ↔ VR<1 churn (✅ validated) |
| Compression (dynamics) | `σ_short/σ_long` | coiled, non-falling near highs ↔ vol-expanding off highs (✅ validated) |
| Holdings delta (identity) | `Δ(FII%+DII%+promoter%)/float` | inst % rises QoQ ↔ falls (NOT wired) |
| Named-flow (identity) | net ₹ non-churn named buyers + FII/DII | real buyers ↔ sellers (`deals.py`, sparse) |
| F&O OI quadrant (identity) | `ΔPrice×ΔOI` | ↑P↑OI long-build ↔ ↓P↑OI short-build (NOT wired) |

**NAP synthesis (signed, within-stock z-average):** `NAP_t = Σ w_i·z_i`, `z_i=(x_i−μ_stock)/σ_stock`. MEP IS the price-tape half of this (x1/x2/x3/x5). **Verdict:** the price-tape half is DESCRIPTOR-ONLY (DSR FAIL — `close_vs_vwap` is the in-sample #1 / OOS poison); real predictive alpha must come from the **identity channel** + fundamentals/concall. The killer line: *the feature that best DESCRIBES today's accumulation is exactly the one that fails to PREDICT tomorrow.*

### 3. F&O Open-Interest feed — ✅ DONE + DEPLOYED (2026-06-23, "go for it")
The NSE F&O OI URL is **located + proven**: the UDiFF F&O bhavcopy `https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_<YYYYMMDD>_F_0000.csv.zip` (same host as the cash bhav; cols incl. `OpnIntrst`/`ChngInOpnIntrst`/`FinInstrmTp`/`UndrlygPric`). Built as its OWN module **`src/automation/fno_oi.py`** (NOT `deals.py` — that's parallel-owned): aggregates each underlying's stock-FUTURES (STF) OI across expiries, reads OI change vs the cash price change → the **price×ΔOI quadrant** (LONG_BUILDUP / SHORT_BUILDUP / LONG_UNWIND / SHORT_COVER / FLAT) + a PCR from stock options. New table `fno_oi_signals` (canonical in db.py); nightly via isolated `30-fnooi.conf`; surfaced descriptor-only on the MEP stock dossier ("F&O positioning · identity"). Verified — the quadrant confirms the tape (RELIANCE SHORT_BUILDUP↔STRONG_DISTRIB) and can lead it (INFY fresh shorts while phase still NEUTRAL). Commits `4510b3b` (module+db.py), `2047ee3` (dossier). **Descriptor-only (D62)** — must earn any predictive role through the DSR gate. **Remaining (future):** an F&O column/board on `/dash/mep` (gated on `cockpit.py` being quiet — it's currently parallel-dirty); pre-UDiFF legacy backfill (a 2nd parser, for >2024 history); fold PCR/quadrant into a future identity-NAP once DSR-tested.

### 4. Pat MEP routing — ⏳ BLOCKED on the parallel Pat session (Ramana's call on the semantics)
Pat's "accumulation" NL flow routes to **DVPT-delivery**. Adding MEP routing needs (a) Ramana's semantic call — should "accumulation" mean DVPT-delivery or MEP-signed? — and (b) the Pat files to be free: **all of `src/pat/disambiguate.py`, `flows.py`, `glossary.py`, `web.py`, `src/assistant/patearn.py` are currently parallel-dirty** with the CCI/Pat session's uncommitted work, so routing edits would clobber them. Do it once they commit. **My lean (for sign-off):** keep "accumulation" → DVPT-delivery; add "distribution" / "being distributed" / "under distribution" → MEP-signed (MEP's signed edge IS the distribution side DVPT can't see). Glossary `mep`/`mep_state` terms are already in (MEP is explainable today).

### 5. Commit the still-uncommitted bits (housekeeping)
Uncommitted in the working tree (deployed/working, but not in git → a parallel `git checkout` can revert them): `docs/dvpt-picking-strategy-design.md` (§0 DVPT reframe — mixed w/ parallel), `docs/mep-strategy-design.md` (post-commit updates — mostly mine), `src/pat/glossary.py` (MEP terms — mixed w/ parallel). Commit the clean ones surgically; glossary/dvpt-design are tangled with parallel work so verify before staging.

---

## Standing operating rules (pre-answered — do NOT re-ask)
- **Autonomous + blanket access:** `acceptEdits` + blanket allows are set. One up-front folder-access grant for the whole task; never ask per-file. Consult **read-only segment agents** when unsure, not Ramana.
- **Commit MY work IMMEDIATELY** after each verified step (`git add <explicit paths>`, never `-A`; verify `--cached`) — parallel sessions share the tree and clobber uncommitted work (the `/dash/mep` 404 + the `dashboard.py` revert this session). New files = zero collision; commit them first.
- **Additive only — never remove or reroute Ramana's existing pages** ([[build-additive-never-replace]]); `/dash/ratio`, `/dash/rrg`, `/dash/compare`, `/dash/stocks` are sacred.
- **Descriptor-only discipline:** nothing ranks/picks/sizes until it passes the **purged walk-forward + Deflated-Sharpe** gate (`research/explosive_moves/ml_alpha.py`). MEP characterises/confirms only.
- **Data-first** ([[data-first-light-ui]]): raw values beside every verdict.
- **Deploy:** scp + retry-ready restart (`for i in $(seq…); do sleep 2; curl…; done` — the app needs >3s under load); **CRLF-diff check** before scp (`diff <(tr -d '\r' local) <(tr -d '\r' vps)`); full-route 200 regression after; column-alignment check on any screener change.
- **Plan non-trivial work first; synchronize across ALL screens + processes; present for acceptance** at the end — Ramana steps away mid-task; don't block waiting.

## Key facts the next session needs
- Compute: `src/automation/mep_signals.py` (pure-stdlib sibling of `signals.py`). Score = within-stock z-avg of `pressure`(close-vwap) · `clv` · `drift_22d` · `updown_vol_22d`, z over trailing 200 rows; bands ±0.35 / ±1.0. Table `mep_signals` (own table; `ensure_table()` self-creates; canonical def in `db.py`).
- Nightly: in `10-signals.conf` after `signals`. Screen: `cockpit.render_mep` + `GET /dash/mep` (dashboard.py). Instruments `_mv_adbar` + `_mep_pill` (cockpit.py). Accent `#db61a2`.
- VPS: `ssh hermes` → `/opt/hermes`, `.venv/bin/python`, db `/opt/hermes/data/hermes.db`. Public: `https://srv1704897.hstgr.cloud/dash/mep`.

---

## ★ SELF-PROMPT — paste this to start the next session

```
Resume the MEP (signed accumulation/distribution) work. BOOT FIRST: read docs/mep-NEXT-SESSION.md, docs/mep-strategy-design.md, the mep-strategy-built-deployed memory, and PROJECT_STATE.md before touching anything. (DDPK=DVPT, MEP=signed accum/distrib — my shorthand. MEP is built+deployed+committed across all stock surfaces, descriptor-only, with a live /dash/mep both-sides screen that auto-updates nightly.)

This message is your one folder-access grant for the whole task: full read/write to D:\Hermes + Bash + ssh-deploy to the VPS. Don't ask again per-file. Consult read-only segment agents when unsure — not me.

Work autonomously, in order. Plan each non-trivial step first; build ADDITIVELY (never remove/reroute my existing pages); deploy with the CRLF-diff check + retry-ready restart + full-route 200 regression; and COMMIT my files immediately after each verified step (explicit paths, never -A) so a parallel session can't clobber them — that bit me last time.

1. ★ FIX THE MEP NOISE → make it a real PHASE. Right now the state flips ~3 days out of 4 (a daily oscillator, not a phase). Add a smoothed, persistent state: mep_score_smooth = rolling ~10-day mean of the daily score + hysteresis (asymmetric enter/exit bands), so STRONG_ACCUM/DISTRIB hold and transition slowly — accumulation → consolidation → distribution. Headline the smoothed phase on /dash/mep and everywhere; keep the daily score underneath. Full design in mep-NEXT-SESSION.md §1. Verify with the transition-count probe (target: single-digit changes per 70 days, not 50+).

2. Write the multi-lens accumulation/distribution decode (the 3 channels, the lenses + equations, NAP, the descriptor-only verdict — captured in mep-NEXT-SESSION.md §2) into the design doc so it's preserved.

Then surface — for MY decision, don't guess — #3 the F&O OI feed (the missing identity channel) and #4 Pat's "accumulation" routing (DVPT-delivery vs MEP-signed).

Descriptor-only discipline: nothing ranks/picks until it passes the DSR gate. Data-first: raw values beside every verdict. Work to completion, then present for my acceptance — I'll be away, don't wait mid-task.
```
