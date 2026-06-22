# MEP — Accumulation/Distribution strategy: data + UI rollout plan (design v0.1)

> **Status:** ✅ **ROLLOUT COMPLETE + DEPLOYED + VERIFIED (2026-06-22)** — all 5 build steps live on the VPS; descriptor-only (the predictive step was ruled out by the DSR gate). **UNCOMMITTED — awaiting Ramana's acceptance** (deployed + reversible, per the accept-at-end workflow). Per-step detail + verification in § 7.
> **Doc type:** TRANSIENT design/handoff (per [[transient-doc-lifecycle]]). Canonical decisions fold into `PROJECT_STATE.md` via the normal rule only **when shipped** — this doc is parallel-safe scratch until then (PROJECT_STATE is parallel-owned; see [[autonomous-blanket-access-multisession]]).
> **Naming (provisional, confirm at acceptance):** **DDPK = the DVPT strategy** (the built delivery/"Positioning" picking engine). **MEP = this new signed accumulation/distribution strategy.** If MEP expands to something narrower, the integration shape below is unchanged — only the column/score internals shift.

---

## 0. The directive (what Ramana asked for)

- **DVPT (DDPK) is currently the main strategy** — built across (nearly) every screen: home/dashboard, screener, stock pages. NOT on index-detail/dedicated pages. The DVPT compute is live.
- **Gradually shift emphasis → MEP.** MEP becomes the rising flagship. **Gradual + non-destructive:** DVPT stays fully functional throughout, now correctly scoped as a confirmation/character layer (D62).
- **Plan the complete UI first, synchronize across all screens AND processes, then build.** Identify exactly which DVPT details must be **maintained** and **how**. Change UI/UX **without hampering existing elements.**
- **Standing autonomy:** work self-driven under blanket access; pre-answer agents' questions in their prompts; don't return for per-step permission. Produce the plan, wait for acceptance.

---

## 1. What MEP IS (the signal)

The **signed Net Accumulation Pressure** — a within-stock, side-aware composite of orthogonal price-tape channels (NONE delivery-per-trade — we are explicitly NOT reskinning DVPT):

```
MEP_t = Σ_i w_i · z_i        (signed: + = accumulation, − = distribution)
z_i   = (x_i,t − μ_stock(x_i)) / σ_stock(x_i)     ← standardized vs the stock's OWN trailing window

  x1 Pressure    = (close − avg_price[VWAP]) / avg_price
  x2 Effort/Res  = |ret| / turnover           (Amihud, trailing 22d)
  x3 Permanence  = lag-1 return autocorr (66d) (does the move stick?)
  x4 Persistence = variance ratio VR(k) − 1    (drift vs churn)
  x5 Compression = −(σ_short / σ_long)         (the coiled spring)
  [later, gated] x6 Identity (named flow/FII-DII/holdings Δ), x7 F&O OI quadrant
```

**The upgrade over DVPT, provable without a backtest:** MEP is **signed** (distinguishes buying from selling) where DVPT is **side-blind** (a magnitude only). That is why MEP can power a *distribution-warning* surface that DVPT structurally cannot.

**Descriptor-only — CONFIRMED 2026-06-22.** MEP ships as a *character/confirmation* read. Any **predictive / ranking / position-sizing** role was GATED on a walk-forward + Deflated-Sharpe test — **which FAILED.** Wiring x1/x2/x3 through the real `ml_panel`/`embase` harness (not `features.py` — that only feeds `ml_probe`) *lowered* OOS Sharpe 0.76→0.68 and DSR 0.45→0.36; it does not clear Nifty500 (0.86), let alone DSR≥0.95. So MEP is **locked descriptor-only; no predictive/ranking/sizing role.** Predictive alpha must come from the new-data channels (identity / fundamentals / concall), each through its own DSR gate. Evidence consistent with the prior finding: x4/x5 were already inside the failed library; x1/x2/x3 are the same data class. See §8, `docs/explosive-move-research.md` (D56), and D62.

---

## 2. Governance (binding for this build)

1. **Additive only.** Nothing DVPT is removed, disabled, or down-weighted. MEP is *added alongside*. (§5 is the contract.)
2. **Proof before promotion.** MEP ranks/sizes/sorts-by-default only after passing the DSR gate. Until then it is a descriptor/overlay. A descriptor needs no gate.
3. **Gradual & reversible.** Emphasis shifts by ordering/config (§6), each phase reversible; no DVPT capability deleted at any phase.
4. **Parallel-safe build doctrine** (from [[autonomous-blanket-access-multisession]]):
   - Build in **NEW self-contained modules** — `src/automation/mep_signals.py` (new), MEP rendering added in `src/web/cockpit.py` (the full-bleed layer), `dashboard.py` gets **thin wrappers only** (never edit its legacy bodies).
   - **Agents PLAN (read-only Explore); I BUILD (sole editor).** Agents never write the shared tree.
   - New DB table `mep_signals` — do **not** ALTER the 2.35M-row hot `stock_signals`.
   - Commit my files explicitly (`git add <paths>`, never `-A`; verify `--cached`); co-author trailer.
   - Deploy with the **CRLF-aware diff-check** before `scp`; keep parallel VPS work intact.
   - Keep this work-stream's state in THIS doc, not PROJECT_STATE.

---

## 3. Data + process layer (synchronize across processes)

Mirrors the DVPT pipeline (mapped: `signals.py` → `stock_signals`; nightly `hermes-bhavcopy.timer`; signals run via backfill/orchestration).

| Piece | DVPT (existing) | MEP (new) |
|---|---|---|
| Compute module | `src/automation/signals.py` · `compute_signals_for_symbol_date()` | **`src/automation/mep_signals.py`** · `compute_mep_for_symbol_date()` — same per-stock loop, same 372-day fetch from `bhavcopy_rows`, reads `open/high/low/close/prev_close/avg_price/volume/num_trades/value` (all present, EQ). NO `deliv_*`. |
| Store | `stock_signals` (PK symbol,trade_date) | **new table `mep_signals`** (PK symbol,trade_date) — raw terms (x1..x5) + their within-stock z-scores + signed `mep_score` + `mep_state` (STRONG_ACCUM/ACCUM/NEUTRAL/DISTRIB/STRONG_DISTRIB) + `data_points_used`. Indexes: (trade_date), (trade_date, mep_state), (trade_date, mep_score DESC). |
| Schema home | `src/core/db.py` SCHEMA_BASE | add `mep_signals` CREATE TABLE to SCHEMA_BASE (no ALTER on hot table). |
| Schedule | `hermes-bhavcopy.timer` (14:00 UTC) → the `hermes-bhavcopy.service.d/10-signals.conf` chain (signals→indexes→…→cpr) | **DONE** — added `mep_signals` to that same chain, right after `signals` (both read the fresh bhav). The chain is VPS-managed (like `cpr_signals`, it's not in `setup-news.sh`); backed up before edit + `daemon-reload`ed. |
| Backfill / recompute | `scripts/full-backfill.sh` step 3 | add `python -m src.automation.mep_signals --backfill`. **Full-history recompute required** — within-stock z-scores need the stock's history (same doctrine as DVPT's ATH/first-ever). |
| "The query" | the DVPT picking/ranking query | a daily MEP ranked query (descriptor-mode until DSR-gated). |

**Synchronization point:** MEP writes the SAME `trade_date` snapshots as `stock_signals`, so the UI can `LEFT JOIN mep_signals ON (symbol, trade_date)` and show DVPT + MEP side by side on any screen.

---

## 4. UI rollout — screen by screen (mirror the DVPT footprint)

DVPT lives on: **home, screener, stock page** (+ partial on **index-detail** constituents, + a term inside **conviction**). MEP mirrors exactly that footprint. Everything routes through the existing `STRATEGY_REGISTRY` + `_mv_*` instrument language + `_ck_*`/`_board` helpers (mapped in cockpit.py).

**Registry (the spine).** Add an MEP entry to `STRATEGY_REGISTRY` (cockpit.py ~L346): `{key:"MEP", label:"Accumulation", accent:"#bc8cff" (purple — distinct from DVPT #58a6ff / CCI #39c5cf; swappable), href:"/dash/mep", cta:"net accumulators today", thesis:"Signed accumulation vs distribution — who's being absorbed.", count: λ → #STRONG_ACCUM today}`. This **auto-appears** on the home count-strip and `/dash/strategies` (registry-driven). DVPT's POS entry is **untouched**.

| Screen | DVPT today | MEP adds | Emphasis shift |
|---|---|---|---|
| **Home** (`render_home`) | "⚡ Top triggers" + "🕵 Stealth accumulation" boards; POS count tile | a "📈 Net accumulation" board AND a "📉 Distribution watch" board (the signed win DVPT can't do); MEP count tile (auto via registry) | Phase A: MEP boards below DVPT. Phase B: above. |
| **Screener** (`render_screener`, dashboard.py thead ~L2097) | `positioning · dvpt` column-group (9 cols: DVPT-vs-power ladder, p, r, ×Pow, surges, Deliv%, Val₹) | NEW group `accumulation · mep`: signed `_mv_adbar` (bipolar −/+ bar), `mep_score`, `state`, x1..x5 sub-scores. Extend the `TOG` localStorage toggle with `['mep','Accumulation']`. | Phase A: appended after g-pos. Phase B: offer MEP as default sort. |
| **Stock page** (`render_stock`) | "Positioning · DVPT" tab (inertia + character + zones + key-price blocks) | NEW tab "Accumulation · MEP" (`data-tab="mep"`): signed verdict + x1..x5 term breakdown + **DVPT shown as a confirmation sub-row** (D62 role) | Phase A: tab after DVPT. Phase C: MEP tab before DVPT; DVPT folds in as overlay. |
| **Index-detail** (`render_index_detail`, partial) | "⚡ Intra-index DVPT" constituent board | "📈 Intra-index accumulation" constituent board beside it | co-equal |
| **Conviction** (`render_conviction`) | uses `p_score` in the cross-pillar synthesis | add signed `mep_score` as an additive synthesis term | co-equal |
| **Pat** (`src/pat/`) | dvpt/r_tier/p_tier glossary + DVPT routing | glossary (mep + terms) + routing (accumulation-leaders / distribution-avoid), mirroring DVPT flows | co-equal |
| **markets / leaders / sectors / rs / concalls** | no DVPT (orthogonal) | **no MEP** (same rationale) | — |

**New instrument:** `_mv_adbar(mep_score)` — a bipolar SVG bar, zero-centred, green to the right (accumulation) / red to the left (distribution), marker at the signed z. Follows the existing `_mv_*` micro-viz pattern; added, not modifying any existing helper.

---

## 5. Non-regression contract — the details we MUST maintain, and HOW (Ramana's explicit ask)

Every DVPT surface and the exact preservation mechanism:

| DVPT detail to maintain | HOW it is preserved |
|---|---|
| `STRATEGY_REGISTRY` POS entry | **Untouched.** MEP is a NEW entry appended; registry iteration already handles N pillars. |
| Home "Top triggers" / "Stealth accumulation" boards | **Untouched.** MEP boards are *added*; ordering only changes board *sequence* (Phase A below them), never their content. |
| Screener `g-pos` column-group (9 cols) + sort/filter | **Untouched.** New `g-mep` group is *appended*; **all column-group colspans recomputed** (the known footgun — session-31 noted colspan alignment); header/colgroup/body cell counts re-balanced and asserted equal. |
| Screener saved views | **localStorage key NOT renamed** (`patearn_scr_hidden`); `TOG` array *extended* with `mep` → users' existing saved show/hide views survive; MEP defaults to shown. |
| Screener row virtualizer (`SCREENER_VIRT_JS`) | New cells render inside the existing row template; no per-row re-measure; the `cpr-only` gate logic untouched. |
| Stock page "Positioning · DVPT" tab + its 4 blocks (inertia/character/zones/key-price) | **Untouched.** New tab *added*; sticky tab-bar JS reveal extended for one more tab. |
| Stock page 4-pane price-chart sync graph | **Byte-untouched** (session-31 lesson: keep all panes in the DOM; MEP pane is show/hide like the others). |
| `_mv_ladder` / `_mv_keyband` / `_mv_triglyph` / `_char_pill` / `_pos_cells` / `_intensity` / `_rupee` helpers | **Reused, not modified.** MEP gets its own `_mv_adbar`. |
| Pat DVPT glossary + routing | **Untouched.** MEP terms/flows added; "stocks to avoid" routing collision checked (DVPT distribution vs MEP distribution vs CCI avoid — disambiguate explicitly). |
| `stock_signals` table (2.35M rows) + indexes | **Untouched.** MEP lives in its own `mep_signals` table — zero ALTER risk to the hot path. |
| `hermes-bhavcopy` / signals / mtf / stock_rs jobs | **Untouched.** `hermes-mep` is a new timer, `After=` bhavcopy. |
| Deploy safety | CRLF-aware diff-check before every `scp`; only `cockpit.py` + new modules shipped; `dashboard.py` thin wrappers; 20-route regression must return 200; home/markets/screener unaffected. |

---

## 6. Gradual emphasis-shift mechanism (DVPT → MEP), reversible

- **Phase A — Introduce (co-equal).** MEP appears everywhere DVPT is, same visual weight, DVPT defaults unchanged. **Pure addition.** (Safe the moment the DSR question is settled — descriptor needs no gate.)
- **Phase B — Elevate.** MEP boards move above DVPT on home; screener offers MEP as the default sort; MEP tab ordered before DVPT on the stock page. DVPT remains fully present.
- **Phase C — Synthesis.** A combined view where **MEP leads** and **DVPT renders as the confirmation/character overlay within it** (exactly DVPT's surviving role per D62). DVPT's standalone surfaces stay available, de-emphasized.
- Each phase = an ordering/config change (registry order, default-sort flag, tab order, board sequence) — **reversible**, no capability removed.

---

## 7. Build order (after acceptance) — each step: new module/cockpit.py → py_compile → CRLF diff-check → deploy → 200-route regression → explicit commit

1. **Data — ✅ DONE + DEPLOYED (2026-06-22).** `src/automation/mep_signals.py` (compute / store / per-symbol full-history backfill / CLI — pure-stdlib, sibling of `signals.py`); `mep_signals` table (self-ensuring `ensure_table()` + canonical def in `db.py` SCHEMA_BASE, kept LOCAL-only since `db.py` is parallel-modified — deployed ONLY the new file). Validated locally (synthetic walk: 160 scored rows, scores centred ~0, all 5 states) AND on real VPS data (RELIANCE STRONG_DISTRIB, TCS ACCUM, etc.). Wired into the nightly `10-signals.conf` chain after DVPT. **Full-history backfill COMPLETE — 7,558,088 rows, 4,138 symbols, 2004-09-17 → 2026-06-19.**
2. **Registry pillar + home boards — ✅ DONE + DEPLOYED (2026-06-22).** MEP pillar in `STRATEGY_REGISTRY` (accent **`#db61a2`** pink — `#bc8cff` was already CPR's) → auto-appears on the home count-strip; two new boards **"Net accumulation"** + **"Distribution watch"** (the signed win — a distribution board DVPT can't do); new `_mv_adbar` signed mini-bar + `_mep_pill` instruments (both in `cockpit.py`, parallel-safe). CRLF-diff clean (0 VPS-only lines); 12-route regression all 200; home renders 7 strong accumulators + 6 strong distributors on real data.
3. **Screener `g-mep` column-group — ✅ DONE + DEPLOYED (2026-06-22).** 3 cols (Accum bar · Score · State) right after Positioning; the SELECT LEFT-JOINs `mep_signals` (NULL-safe). **Verified ALIGNED — group-header colspans = sub-header `<th>` = body `<td>` = 47/47/47** (the charts-incident class of bug, checked explicitly). `TOG` extended with `['mep','Accumulation']`; the `patearn_scr_hidden` localStorage key is unchanged → users' saved views survive; the `<colgroup>` auto-builds `cg-mep` from the body cells. Baseline CRLF-diff 0 before editing → my diff was provably only MEP lines; 13-route regression all 200. (Lesson: under backfill load the app needs >3 s to warm up — use a retry, not a fixed `sleep 3`, before regressing.)
4. **Stock-page MEP tab + dossier — ✅ DONE + DEPLOYED (2026-06-22).** New "Accumulation · MEP" tab (after Positioning) + `_mep_stock_panel`: signed verdict chips (score · state · adbar · history-days) + the 4 signed terms each with within-stock z + raw value (data-first) + context terms + **DVPT character as a confirmation sub-row** (D62). PURE static HTML/SVG — no chart, no width-measuring JS → renders correctly while hidden, sidestepping the charts-incident class; the **4-pane price-chart graph is byte-untouched**; the generic tab-JS auto-handles the pane (no JS edit). Verified on RELIANCE (STRONG_DISTRIB tab + dossier render); 10-route regression all 200; CRLF-diff clean (1 `>` = my own `_tabs` original).
5a. **Index-detail board + conviction column — ✅ DONE + DEPLOYED (2026-06-22).** "📈 Intra-index accumulation" board on `/dash/index` beside the DVPT board (separate constituent query; member fetch untouched; verified on Nifty Bank — both render). Conviction: MEP state as a **display-only confirmation column** (D62 — NOT a ranking input; `conviction_shortlist` untouched), table re-aligned **9/9 thead/body**. 11-route regression all 200.

5b. **Pat (NL) glossary — ✅ DONE + DEPLOYED (2026-06-22).** Added `mep` + `mep_state` glossary terms (explainable via the explain-flow AND NL aliases — "what is mep" / "explain signed accumulation" both resolve). **Routing deliberately NOT changed:** Pat's existing "accumulation" flow is DVPT/delivery — hijacking the word for MEP would break it (the flagged collision). Verified MEP explainable + the DVPT accumulation flow byte-unaffected. **DEFERRED (a product decision for Ramana, not a guess):** dedicated MEP NL routing / a distribution-watch screen — needs a deliberate call on whether "accumulation" means DVPT-delivery or MEP-signed.
6. ~~(GATED) predictive/ranking promotion~~ — **RULED OUT (DSR FAIL, 2026-06-22).** MEP stays descriptor-only; the emphasis shift is a character/confirmation reframing (still a real upgrade — signed > side-blind). Predictive alpha must come from the new-data channels (identity / fundamentals / concall), each through its own DSR gate.

---

## 8. Open items / the single confirm

- **Confirm MEP = the signed accumulation/distribution score** described in §1 (vs a narrower meaning), and the **accent colour** (proposed `#bc8cff`).
- **DSR test — DONE, verdict FAIL (2026-06-22).** Top-20 monthly, net of cost, walk-forward + Deflated Sharpe:

  | Config | OOS Sharpe | DSR | CAGR |
  |---|---|---|---|
  | Baseline (26 feat) | 0.76 | 0.45 | 23.0% |
  | + x1/x2/x3 (29 feat) | **0.68** | **0.36** | 18.7% |
  | (Nifty500 benchmark) | 0.86 | — | — |

  The three price features *lowered* risk-adjusted performance. **The poison is `close_vs_vwap_s`** — ranks #1 in in-sample importance yet *destroys* out-of-sample (a textbook overfit-attractor; it's informative about *today's* tape but doesn't generalize forward; worsened by 37% missing pre-2020). Amihud + return-autocorr alone are faintly additive in a clean ablation (0.88→1.00 Sharpe) but still far below the DSR≥0.95 bar — not tradeable. **The neat encapsulation: the feature that best *describes* today's accumulation is exactly the one that fails to *predict* tomorrow — which is why MEP is a descriptor, not a predictor.** Harness fact: `ml_alpha` reads the `ml_panel` table (built by `panel_build` from `stock_signals` + `embase.compute_entry_features`), not `features.py`. Test left no trace (VPS files restored, scratch dropped, nothing committed).

**Implication for "MEP as the main strategy":** MEP can be the main **character/confirmation lens** you read every stock through (signed, side-aware — a genuine upgrade over DVPT in that role). It is **not** a stock-*picker* — no price-tape signal here is. The *picking* edge still has to come from the new-data strategies (CCI/concall, fundamentals, identity flows). Worth deciding consciously at acceptance.
