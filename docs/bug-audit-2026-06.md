# Full-codebase bug & improvement audit — 2026-06-30

**Scope:** every `*.py` under `src/` (146 files / ~59.5K LOC), `research/` (~9.2K LOC), `scripts/` (~1.4K LOC).
**Method:** 12 parallel deep-readers (Claude), one per subsystem, each reading every line of its files against the project doctrines (PIT/no-look-ahead · rupees-not-shares · descriptive-only · cheap-LLM-in-timers · secrets-in-`.env` · additive-not-replace). High-impact and all security findings spot-verified by hand (see ✓/✗ flags).
**Cross-check:** Codex (`gpt-5.5`, read-only) runs the same audit and rates these findings — see `codex-bridge/DISCUSSION-bug-audit.md` + `codex-bridge/req-10-full-codebase-bug-hunt.md`. Nothing here is implemented until Ramana approves (bridge doctrine).

**Finder legend:** `CL-*` = found by Claude. `CX-*` (added later) = found by Codex.
**Verify legend:** ✓ = Claude hand-verified the claim in source · ✗ = Claude verified it is a **false positive** · ⚠ = disputed/partial.

Counts (Claude pass): ~170 findings — 1 Critical, ~17 High, ~60 Medium, rest Low; split bugs vs improvements below.

---

## Remediation status — 2026-06-30 (branch `bugfix/audit-p1-2026-06-30`, PR #1, HEAD `c6a6b4b`)

**Codex cross-check DONE** (`codex-bridge/resp-10` + `DISCUSSION-bug-audit.md`): Codex `gpt-5.5` AGREED on all 23 headline `CL-*` and both adjudications; added `CX-01..05`. CX-01/02/03 fixed; CX-04/05 deferred (untracked dormant `code_review.py`).

- **FIXED + committed (held off `main` for review):** the 1 Critical + all High + the bulk of Medium/Low — across the P1 wave (`0ec20f5`…`df4d3af`, `a815e6c`) and the completion wave (`2eab882`, `7599477`, `937a90f`, `8b3f7e8`, `9594c6e`, `dc35453`, `d7ca005`, `fb6837f`, `c6a6b4b`). Each fix real-data-verified read-only on the VPS; chrome_gate PASS.
- **DEPLOYED live to VPS:** only the P1 security/crash set (CL-SYS-01/02, CL-CHR-1/3/4, CL-VIEW-01/03/08, the market-data recompute). All Medium/Low ride Ramana's PR merge (coordinated deploy) — prod stays at the reviewed P1 state.
- **⚠ CX-01 (Q4-vs-annual settle):** fixed in code; deploying requires a coordinated re-settle + `concall_scores`/credibility-series recompute (shifts ~1,568 verdicts; supersedes published CCI track-record numbers). Recompute not run.
- **BLOCKED — parallel session's uncommitted tree edits (untouched):** CL-CCI-01/03/04/05/10/11/13/14, CL-MDC-09, CL-RS-07.
- **DEFERRED:** untracked-file findings CL-PROV-11 (`enrich.py`), CL-SCR-10 (`pipeline_status.py`), CL-PROV-17 + CX-04/05 (`code_review.py`); plus CL-DASH-14 (1200-line dead-body removal), CL-DASH-17 (sector IN-list), CL-CHR-6 (cockpit palette) — each needs a focused/owner pass.
- **FALSE-POSITIVE / portability-only (no action, Codex-confirmed):** CL-DASH-11, CL-DASH-02 (+ the verified-clean set at the bottom of this doc).

---

## TABLE 1 — BUGS

### Critical

| ID | File:Line | Conf | Title | Why it's a problem | Suggested fix |
|---|---|---|---|---|---|
| CL-RES-01 | research/cci/common.py:104-131 | High | CCI uses latest-per-symbol credibility composite as a per-period predictor | `gather_observations` attaches `composite_score` from `MAX(last_updated)` (computed from ALL of a symbol's concalls, incl. ones *after* each observation's anchor) then `gate_residual_alpha` regresses forward return on it → forward-looking leakage; the PASS/FAIL verdict can be a false positive. The in-code "not look-ahead because return is measured after" comment is wrong — the *regressor* embeds the future. | Score credibility per-period as-of the anchor, join on (symbol, source_period); until then the gate must render "underpowered/unscored", never PASS. |

### High

| ID | File:Line | Conf | Title | Why it's a problem | Suggested fix |
|---|---|---|---|---|---|
| CL-MDC-01 | src/automation/signals.py:281-284 | High | Delivery value uses raw (unadjusted) close, violating split-invariance doctrine | `deliv_value = deliv_qty * close` uses raw close while the price-direction axis uses `adj`. The 1m/6m delivery-value ratio spans ≤180d; a split in-window puts deliv_qty and close on different scales. | Compute `deliv_value` on a split-consistent basis (`deliv_qty * adj_close` or turnover-derived), matching `accum_price_drift`. |
| CL-MDC-08 | src/automation/signal_events.py:225-235 | High | `_latest_two`/`_symbols_in` interpolate table/column/order names into SQL | `f"SELECT {cols},{order} … FROM {table} …"` — literals today, but an injection-shaped pattern one config change from being exploitable. | Whitelist identifiers / assert `^[A-Za-z_][A-Za-z0-9_ ,]*$` before interpolation. |
| CL-RS-01 | src/automation/mtf_signals.py:261 | High | Under-filled long-window baselines inflate scores for young listings | `lo=max(0,i-n_bars)` lets a 2-bar "52-week" baseline score equal to a full one, inflating `p_score`/`trigger_rank` for new listings, with no immaturity flag. | Require min fill (`len(win)>=n_bars`) or store `n_bars_used`; null the window when under-filled. |
| CL-RS-02 | src/automation/fno_oi.py:279 | High | OI-change % uses reconstructed prior OI that can be wrong-signed/zero | `prior_oi = fut_oi - fut_oi_chg` summed across expiries; on roll days `prior_oi` can go ≤0 (→FLAT) or tiny (→explosive %), mislabelling LONG/SHORT buildup. | Carry true prior-day OI from the stored prior row, or validate `prior_oi ≥` a fraction of `fut_oi`. |
| CL-SCO-01 | src/automation/ignition_backtest.py:288-292 | High | Continuity-break truncation only inspects the first break | Unconditional `break` after the first iteration; a demerger/merger *after* the signal is never truncated and the scheme gap is counted as return — violates the "Continuity" non-negotiable. | Iterate all breaks; truncate at the first `bd` whose position lands in `[entry_idx,end_idx]`; don't break on a pre-signal break. Sort breaks ascending (see CL-SCO-09). |
| CL-CCI-01 | concall_bse.py:94 vs concalls.py:97-103 | High | Two ingest paths derive different quarter/FY for the same concall | Screener path maps Apr–Jun→Q4; BSE path maps May/Jun→Q1 with `fy=y+1`. The same May/June call gets different `quarter`+`fy` into one `concalls` table; FY/quarter consumers get inconsistent semantics by capture source. | Make `concall_bse._derive_period` call `concalls._derive_period(month,year)` so both paths agree. |
| CL-CCI-03 | concall_scores.py:127-131 / cci_series.py:163 | High | `quantification_rate` snapshot is not PIT + period-label collision | `_quantification_rate` selects every guidance row (no period filter) → snapshot mixes future periods; promises keyed by `source_period` label only, so a "Aug 2025" label from BSE vs Screener collapses/duplicates promise sets. | Restrict snapshot to PIT (`made<=as_of`); disambiguate period identity by fy+quarter or transcript_url. |
| CL-CCI-06 | src/automation/cci_series.py:155 | Medium | "Newly graded" uses prior *concall* date, not the prior resolution boundary | `p["res"]>prev_ym` (prev concall ym) mis-times EARNING_TRUST/DETERIORATION tape for irregular-cadence filers (gaps >1 quarter collapse, <1 quarter miss the boundary). | Track actual max(res_ym) already emitted, or window by calendar quarter. |
| CL-PROV-01 | src/automation/fundamentals_asof.py:171 | Medium | PIT gate does lexicographic string compare against mixed-format dates | `_known()` filters `rdate <= as_of` as strings; real-BSE path slices `[:10]` but the stored-`report_date` fallback does not, so `'2024-05-10 00:00:00' <= '2024-05-10'` is False → drops a period knowable exactly on `as_of`. Core PIT product path. | Slice both sides to `[:10]` before compare; normalize `report_date` to ISO date in the frame. |
| CL-CHR-1 ✓ | src/web/shell_skin.py:426 | High | `_HSEARCH_RE` is undefined — NameError drops the entire skin | Verified: referenced at L426, defined nowhere in `src/`. When `_native_header()` raises, the fallback hits `_HSEARCH_RE.sub` → NameError → outer except returns the page **completely un-skinned**, and the logged warning is misleading. | Define `_HSEARCH_RE = re.compile(r'<form class="hsearch".*?</form>', re.S)` or drop the fallback line and just retint the legacy header. |
| CL-VIEW-01 ✓ | src/web/news_view.py:70-71 | High | News headline URL unsafe in `href` (no quote-escape, no scheme allowlist) | Verified `_esc` escapes only `& < >`, not `"`. Feed URLs (attacker-influenced via `sent_news`) go into `href="{url}"`: a `"` breaks the attribute; a `javascript:`/`data:` URL fires on click. | `html.escape(url, quote=True)` AND require scheme ∈ {http,https}; neutralize otherwise. |
| CL-SYS-01 ✓ | src/api/v1/*  (auth/resources/routes) | High | `/v1` redistribution licensing gate is never enforced | Verified `redistribution_status` is referenced nowhere under `src/api/`. VENDOR_TOS classes are *stamped* in the envelope but never *refused*; an external/data-feed key can pull non-redistributable vendor data — the doctrine's gate is absent. | In `require_scope`/`ok()`, look up `redistribution_status(cls)` per served class and 403 (or return typed `absence`) for external scope on VENDOR_TOS/news-license. |
| CL-SYS-02 ✓ | src/api/v1/keys.py:55 | High | Hardcoded predictable all-scopes dev API key | Verified `os.environ.get("HERMES_V1_DEV_KEY","pk_dev_local-0000000000000000")`; `preview_app` seeds it unconditionally at import (all scopes, rate 100000). If `preview_app` is ever exposed, the constant grants full `/v1`. | Require the env var (no constant fallback); refuse to seed if unset, or gate behind an explicit dev-only flag. Same for `seed_compliance_key`. |
| CL-SYS-03 | src/core/settings.py:18; llm.py:15 | Medium | Default model is Sonnet, contradicting "Haiku default" doctrine | `default_model="claude-sonnet-4-6"`; HTTP `/chat` defaults `fast=False`→Sonnet, so any non-Telegram caller silently runs Sonnet — spend risk vs ≤₹300/mo. | Make Haiku the default tier; require explicit opt-in for Sonnet on the user-initiated path only. |
| CL-RES-02 | research/cci/gate_residual_alpha.py:54-84 | High | Residual-alpha quality controls (ROCE/debt) read latest snapshot, not PIT | Controls come from the current `fundamentals` table, so 2021-22 forward returns are orthogonalised against 2026 fundamentals → look-ahead biases the credibility coefficient; PASS/FAIL fires on leaked data. | Use `fundamentals_history` with `report_date<=anchor` (the `latest_known` pattern already in factor_zoo); gate the verdict on PIT controls. |
| CL-RES-04 | research/explosive_moves/mine.py:91-108 | High | Univariate lift selected in-sample over a quantile×direction grid (data-snooping) | Threshold chosen by maximizing lift over 5 quantiles × 2 directions on the same positives+controls, no holdout → reported hit_ratio/lift are best-of-10 upward-biased, then fed to the writeup as honest. | Pre-register thresholds or fit/eval split (as `validate.py` does); or apply a max-statistic/multiple-comparison correction; label current numbers in-sample. |
| CL-RES-06 | research/explosive_moves/combo_test.py:34-70 | High | Survivorship reintroduced by inner-joining survivorship-aware fund_panel to ml_panel | `ml_panel` drops rows with NULL 22d-forward (delisted), so the inner join silently removes the blow-ups fund_panel kept → "does quality cut blow-ups" tested on survivors only. | Build ml_panel features without requiring a non-null forward target, or LEFT JOIN from fund_panel tolerating missing ml features. |

### Medium

| ID | File:Line | Conf | Title | Why / Fix |
|---|---|---|---|---|
| CL-MDC-02 | signals.py:549 vs 814 | High | `is_ath_dvpt` disagrees realtime (first-ever=1) vs backfill (first-ever=0) for a stock's first row. → Pick one convention; make backfill set 1 when `prior_max is None`. |
| CL-MDC-03 ✓ | index_signals.py:124-131 | High | Off-by-one: `if today_idx < window` rejects the exact-window case, delaying every index MA by one trading day. Verified. → `today_idx < window - 1`. |
| CL-MDC-04 | bhavcopy.py:260 | Medium | UDIFF `TradDt` stored verbatim, unvalidated; format drift silently corrupts `trade_date` (breaks ON CONFLICT + all window math). → Parse/normalize like the other two parsers; skip row on failure. |
| CL-MDC-06 | indexes.py:152-161 | Medium | `_store` returns attempted parse count (not rows written); `_mark_date` can overstate stored rows on silent constraint rejects. → Return `conn.total_changes` delta and validate. |
| CL-RS-03 | cpr_signals.py:333 | High | Partial (`is_partial=1`) period emitted as a normal signal with `confirmed`/`regime` against in-progress close → a confirmed BULL_U can flip pre-close. → Suppress/mark confirmed on partial rows (mirror MTF). |
| CL-RS-04 | rrg.py:155 | Medium | RS-Momentum ROC seeds first point with synthetic `0.0`, biasing `_ema`/`_normalise_100` for the first MOM_NORM_WIN points → shifts early quadrant assignment. → Drop the synthetic 0.0 / mark None. |
| CL-RS-05 | harmonic_patterns.py:218 | High | Forming-PRZ projection only ever runs on `piv[-4:]`; an in-progress pattern one pivot back is never projected. → Scan trailing 4-pivot windows. |
| CL-RS-06 | fno_oi.py:289,137 | Medium | Option-chain near-expiry chosen by `min()` on expiry *strings*; non-ISO (`DD-MMM-YYYY`) sorts lexically → wrong near-month chain. → Parse expiry to dates before min/`<`. |
| CL-SCO-03 | ignition_backtest.py:304 | Medium | Censored flag conflates "young signal" with "data-exhausted/truncated". → Censor on data-exhaustion test independent of `n_days_held`. |
| CL-SCO-07 | wolfe.py:357 | Medium | Wedge-rail touch test divides by tiny `ln` (spurious touches) and iterates 1→3 while using the 1→4 slope — code/comment disagree. → ATR-scaled abs tolerance; iterate the intended span. |
| CL-SCO-12 | wolfe.py:907-910 | High | `persist_scan` `try: conn.commit() except: pass` commits a possibly-foreign connection and hides disk-full/locked errors. → Only commit when owning the conn; let errors propagate/log. |
| CL-CCI-04 | concall_extract.py:299 | High | LLM extractor not pinned to a cheap model at the call site; cost cap is advisory; `--max-calls 0`=unlimited; worker pool can burn free-tier fast. → Pass explicit cheap model id / assert resolved model ∈ allowed set; log model used. |
| CL-CCI-05 | concall_extract.py:414 | Medium | Circuit-breaker ratio mixes process-wide `totals["FAIL"]` with batch `done`; `Future.cancel()` can't stop running Gemini calls (they still bill). → Batch-local fail count + shared stop-flag workers check. |
| CL-CCI-08 | cci_backtest.py:113 | Medium | Level terciles degenerate on tied `level` values (clustered qr-only points) → low/high overlap, double-counting ties → biased spread the veto verdict keys on. → Rank-based bucketing excluding ties; require lo/hi gap. |
| CL-CCI-12 | concall_bse.py:188-209 | Medium | A failed PDF fetch is INSERTed as a terminal `FETCH_FAIL` row whose UNIQUE key blocks all future re-capture even when BSE later serves the attachment. → Don't latch failures; re-attempt rows with `transcript_path IS NULL`. |
| CL-PROV-04 | screener.py:341-342 | High | `_read_cache` parse of `fetched_at` raises on NULL/odd format → crashes the whole fundamentals fetch instead of treating as cache-miss. → Guard None + try/except → return None. |
| CL-PROV-08 | fundamentals_filing_dates.py:257 | Medium | `date.fromisoformat(pe)` without `[:10]`; a timestamped `period_end` raises inside the comprehension, aborting matching for that announcement. → Slice `pe[:10]`. |
| CL-PROV-10 | tracker_alerts.py:264-267 | High | `ok = all(_send(d,…) for d in dests)` → on partial multi-dest failure nothing is marked notified (duplicate re-send to the dest that already got it), and `all()` short-circuits so later dests may never be tried. → Per-dest success tracking. |
| CL-PROV-11 | enrich.py:419-423 | Medium | Threaded circuit-breaker `f.cancel()` can't stop running Gemini calls; the `break` blocks on executor `__exit__` until in-flight finish → "cancel rest" defeats spend control. → `cancel_futures=True` / shared Event. |
| CL-DASH-03 | dashboard.py:4759-4765 | High | `dash_track_close` with a bad/foreign id and an uncapturable snapshot closes the position with NULL exit price; `dash_track_reopen` can resurrect it → corrupts performance math. → Only UPDATE when row exists and `ep is not None`. |
| CL-DASH-04 ✓ | dashboard.py:556-560 | High | `_pct`/`_num` render NaN as "nan%" (only `None` guarded). `_esc` confirmed not quote-safe either. → Add `v != v` / `math.isnan` guard. |
| CL-DASH-05 | dashboard.py:5917-5981 | High | Import commit silently stamps `utcnow()` when a holding's entry date is unparseable → breaks P/L-since and XIRR. → Skip/surface unresolved-date rows. |
| CL-DASH-06 | dashboard.py:5705,5900 | Medium | XLSX upload `await file.read()` with no size cap before `openpyxl.load_workbook` → zip-bomb memory exhaustion on the single VPS. → Cap upload size before parse; `read_only=True`. |
| CL-DASH-08 | dashboard.py:2714,2765 | Medium | `_mep_stock_panel` reads `m["data_points_used"]`/`m["z_pressure"]` by key with no `.get`; render block not in try → a `mep_signals` schema drift 500s the whole stock page. → `.get`/keys guard or wrap render. |
| CL-DASH-20 | dashboard.py:6353,7143 | Medium | `int(r["dvpt"])` raises `ValueError` on a NaN/inf DVPT → 500s the stock chart. → Coerce defensively (`==` self-check / wrap). |
| CL-CHR-2 | nav_links.py:193 | High | "Open in Screener" lateral link uses `?lens=` which `dash_screener` ignores (only `scope`,`limit`) → lands on the unfiltered screener; the promised filter is a no-op. → Honour `lens` or change to a supported param. |
| CL-CHR-3 | v2_surfaces.py:84 | High | `_IA_ALT = [… subnav(_alt)[0] …]` runs at import; an all-overlay altitude → `IndexError` at import → app crash (not in try). → Guard empty subnav. |
| CL-CHR-4 | shell_skin.py:407 | Medium | `uk-skin` body-class regex can strip body attributes / lose an existing class on a `<body attr>` shell. → Single substitution that preserves/merges existing class+attrs. |
| CL-VIEW-03 | strategist_view.py:173 | High | MEP top-note `f"{x['ph']:+.2f}"` raises `TypeError` if a registry-path MEP row has `ph=None` → whole card list lost (CCI branch guards None, MEP doesn't). → Guard `x['ph']`. |
| CL-VIEW-08 | participants_view.py:99-126 | Medium | Headline gauge `f"{fii_net/1e5:+.2f}"` 500s when `fii_net` is None (missing FII index OI). → Guard `is not None` (matrix `_cell` already does). |
| CL-VIEW-10 | rrg_view.py / rsband_view.py:354-371 | Medium | Manual `cm.__enter__()`/`__exit__(None,None,None)` in `finally` swallows real exception info from the contextmanager; route has no try → 500. → Use `with get_conn() as conn:`. |
| CL-VIEW-20 | strategist_view.py:430-431 | Medium | `_alerts_strip` "new" branch splices raw `</div><div>` into the `sec` body → unbalanced/nested tags, prematurely closes `sec`. → Build chips as a sibling element. |
| CL-VIEW-02 | rrg_view.py:171-175 | Medium | Tooltip `data-html` built with non-quote-escaping `_esc` then set via `innerHTML` — XSS sink if the name set ever widens to constituent symbols (L752). → Quote-escape / JSON-encode. |
| CL-SYS-06 | llm.py:23; chat.py:181; patearn.py:130,195 | Medium | `response.content[0].text` assumes a text block; empty/tool_use/refusal content raises in scheduled paths (no try in `llm.ask`). → Find first text block / safe default. |
| CL-SYS-07 | metering.py:24-41; schema.py:65 | High | `v1_ratelimit` rows accumulate one per (key,minute) forever — unbounded growth on single-file SQLite (also per-process counter only correct at workers=1). → Prune stale windows opportunistically. |
| CL-SYS-04 | db.py:950-954 | High | `_ensure_column`/`_tune` interpolate `{table}/{column}/{decl}` into ALTER/PRAGMA — internal-only today, latent injection. → Whitelist/assert; never expose to user input. |
| CL-RES-03 | explosive_moves/embase.py:211-228 | High | 200-DMA regime filter includes the same-day close (1-bar look-ahead) while entries trade at s+1 open. → Lag MA by one bar (`close[i] > ma[i-1]`). |
| CL-RES-05 | explosive_moves/metrics.py:23-42 | Medium | Equity curve compounds only over open-position days (idle days absent, not zero-return) → inflated Sharpe/CAGR, compressed drawdown duration. → Build on full calendar / annualize consistently. |
| CL-RES-09 | explosive_moves/strategies.py + run_backtests.py | Medium | "Frozen OOS" tree cuts also run on their own 2012-19 derivation window and are reported alongside as if independent. → Label in-sample windows; only the untouched window is OOS. |
| CL-SCR-01 | scripts/build_dossier_html.py:245-300 | High | Ledger fields (`l.metric`,`l.period_end`,`l.report_date`) concatenated into `innerHTML` unescaped → markup break / script injection. → JS `esc()` helper / `textContent`. |
| CL-SCR-03 | scripts/cci_drain_loop.py:56-58 | High | `subprocess.run` return code ignored; a hard crash (not the in-batch breaker) busy-spins 300× at fixed 30s, burning ~2.5h and possibly billed Gemini calls, no alert. → Check returncode; exponential backoff; abort after N. |
| CL-SCR-05 | scripts/wire_v2_surfaces.py:108-145 | Medium | `--verify` rollback isn't all-or-nothing: a failing first `copy2` leaves later files mutated. → try/finally restoring every file; or temp-file + atomic rename after import check. |
| CL-SCR-06 | scripts/wire_stock_chart.py:48-51 | High | `_backup` writes `.bak` only `if not exists` → after the first run the backup is frozen forever; a later corrupting run has only a stale pre-image and no auto-rollback. → Timestamp backups; add import-verify+rollback. |

### Low (bugs)

| ID | File:Line | Title / fix |
|---|---|---|
| CL-MDC-07 | signals.py / bhavcopy.py:740 | Scheduler detects ingestion via brittle `"rows" in msg` substring. → Return structured `(ok, count)`. |
| CL-MDC-11 | bhavcopy.py:114 | sec_bhavdata sniff reads only first 6 bytes; a BOM/whitespace prefix skips the delivery-bearing source. → Robust header sniff. |
| CL-SCO-02 | scoring.py:183-184 | `if pe`/`if pb` treats 0.0 as missing and discards negative PE (rest of file uses `is not None`). → Use `is not None`. |
| CL-SCO-08 | ignition.py:204 | COOLING uses fragile float `< 0.8×` with no NaN/zero guard → status oscillates on noise. → Epsilon band; handle prev≤0. |
| CL-SCO-10 | wolfe.py:478-481 | `_adjust` NaN-guards via `o==o` but a real 0.0 OHLC → `0*g=0` feeds zigzag/atr as a real low → fabricated swings. → Filter zero/NaN OHLC. |
| CL-SCO-15 | strategy_registry.py:146,183 | RS card `count` (rs_rank≥90) vs `top` (all rows) use different populations → count=0 yet 5 names listed; CCI `as_of` can be None with rows present. → Same population; ensure as_of set. |
| CL-CCI-02 | concall_bse.py:72 | Headline filter `A or B and C` precedence is fragile/unparenthesized. → Add parens. |
| CL-CCI-09 | cci_backtest.py:256 | `ex[int(0.05*L)]` floors to index 0 for small L → "p5" reports the single worst obs; cohorts of different n compared. → Interpolated quantile + min-n guard. |
| CL-CCI-13 | concall_scores.py:198 | Forward `direction` reads raw kept-rate `ga` even when sample is unproven → UP off a single resolved promise. → Gate direction on `proven`. |
| CL-PROV-02 ✓ | news_feed.py:366-389 | Unreachable dead code after `return success`, references undefined `chat_ids`. → Delete. |
| CL-PROV-17 | code_review.py:195 | Diff+untracked byte budget not shared → payload can be ~2× cap → larger GLM bill. → Shared running budget. |
| CL-DASH-09 | dashboard.py:2938 | F&O OI percentile uses `cur["fut_oi"]` truthiness → drops legit 0. → `is not None`. |
| CL-DASH-16 | dashboard.py:7028,6562 | Day-change/up-fraction guarded by truthiness → legit 0 close / 0 updown treated as no-data. → `is not None`. |
| CL-DASH-18 | dashboard.py:4574 | Autocomplete cache keyed on row COUNT only → a rename (same count) serves stale names. → Fingerprint (MAX(rowid)+count). |
| CL-VIEW-16 | screener_plus.py:633,679 | `data-v="{mep_ph or -99}"` makes a real 0.0 sort as missing. → `... if v is not None else -99`. |
| CL-VIEW-19 | harmonic_view.py:68 | Confirmed-pattern sort `-p.points[-1][1]` sorts by D-point *price*, comment says "newest first" → sort by date field. |
| CL-VIEW-06 | rsband_view.py:586-611 | `lane_from_series` may be called on a 1-point series → confirm n<2 tolerance or guard `len>=2`. |
| CL-PAT-04 | pat/web.py:1428 | Unquoted `class=empty` attr in a nested f-string (sym is DB-safe). → Quote + lift out. |
| CL-PAT-06 | pat/understand.py:242 | `value in (0,None)` conflates explicit 0 / False / missing. → Explicit None+type check. |
| CL-PAT-10 | pat/threads.py:112-124 | `MAX(turn)+1` then INSERT can duplicate turn under concurrency (no UNIQUE(tid,turn)). → Constraint + order by id. |
| CL-SYS-09 | telegram_bot.py:147,232 | `chat.title`/`full_name` echoed into `parse_mode="HTML"` unescaped. → HTML-escape. |
| CL-SCR-02 | scripts/chrome_gate.py:105-120 | Bare-substring chrome markers can false-green a degraded 200 that still embeds the nav scaffolding. → Anchor markers in `<body>`/`<header>` + min length. |
| CL-SCR-04 | scripts/recon_dossier.py:84-97 | Column identifiers from PRAGMA interpolated into SQL (schema-sourced, latent). → Allow-list/quote. |
| CL-SCR-07 | scripts/probe_data_reachability.py:96 | Unbounded NSE scan; any block sets `n=-1` "err" → misleading "no data that far back". → Distinguish HTTP block from empty; backoff. |
| CL-RES-11 | explosive_moves/gate_study.py:117 etc. | Forward-return fallback `i1=d2i.get(d1, min(i0+REBAL,len-1))` lacks `i1>i0` guard (factor_zoo has it) → stale/0 forward return near series end. → Add `i1>i0`. |
| CL-RES-13 | explosive_moves/factor_zoo.py:70 | PIT shares = NetProfit/EPS can flip/explode near zero EPS → noisy mcap feeds velocity/book-yield gates. → Explicit shares series / widen floor / cap. |
| CL-RES-15 | explosive_moves/ml_alpha.py:100-106 | Permutation importance measured on rows overlapping training years → partly in-sample. → Held-out rows only. |

---

## TABLE 2 — IMPROVEMENTS (correctness-adjacent / perf / hygiene)

| ID | File:Line | Title | Suggested improvement |
|---|---|---|---|
| CL-MDC-05 | signals.py:239 | `deliv_updown_ratio_3m` caps up-only at 99 but floors down-only at raw 0 → asymmetric thresholds. | Symmetric clamp (cap 99 / floor 1/99). |
| CL-MDC-09 | index_signals.py:266 | Ratio MA counts list positions while slopes use calendar days → inconsistent window semantics on gapped joins. | Document as trading-row, or make calendar-consistent. |
| CL-MDC-10 | signals.py:639 | `_hot_days_avg_close` needs exactly 22 non-None points → thin names never register a hot day. | Min-count threshold (≥15). |
| CL-MDC-12 | capture.py:54 | `_returns` substitutes 0.0 for non-positive prev → fake flat day dilutes up/down-capture. | Skip the observation. |
| CL-MDC-13 | security_master.py:210 | ISIN rename auto-confirm chains consecutive pairs only → >2 symbols/ISIN can mis-stitch. | Validate full non-overlapping chain before confirming. |
| CL-MDC-14 | signals.py:467 | Calendar windows rely on ISO-string `>=` with no guarantee (ties to CL-MDC-04). | Normalize/assert ISO at ingestion. |
| CL-MDC-15 | bhavcopy.py:376 | `store_rows` swallows per-row errors at debug → a whole day can be lost silently. | Count failures; warn if rate >1%. |
| CL-RS-07 | rsband.py:176 | 3-month momentum uses fixed 63-row offset, not calendar-aware. | Date-anchored lookback. |
| CL-RS-08 | stock_rs.py:229 | `rs_rank` blend coalesces missing 6m slope to 0 (not neutral on non-zero-mean dist). | `COALESCE(slope_6m, slope_3m)` or exclude under-history. |
| CL-RS-10 | mep_signals.py:486 | Nightly skips any symbol already having a row → stale/partial scores never refreshed. | `--force` / compare computed_at. |
| CL-RS-11 | rrg.py:107 | `compute_one` length gate doesn't cover momentum warm-up → returns None for a series that passed. | Gate on momentum warm-up too. |
| CL-RS-13 | fno_oi.py:84 | Non-200/short body all treated as "holiday" → NSE 403/429 masked as gap. | Distinguish retryable errors. |
| CL-RS-14 | stock_rs.py:190 | Per-date path rebuilds full RSI series per symbol per night (O(history)). | Incremental/cached RSI. |
| CL-SCO-04 | ignition_rankv2.py:188 | `dict(r)` built 4× per row. | Bind once. |
| CL-SCO-05 | ignition_rankv2.py:107 | Missing-intensity `-1e9` sentinel makes the intensity baseline and v2 model use different intensity values. | Filter None from baseline / document. |
| CL-SCO-11 | ignition_rankv2.py:75 | Lift uses only extreme buckets → non-monotone features mis-weighted. | Spearman/regression slope across buckets. |
| CL-SCO-13 | scoring.py:158 | Dead inner ternary; negative `sales_g` yields false-good operating leverage. | Drop ternary; guard negative sales. |
| CL-CCI-07 | cci_backtest.py:62 | Genuine >100% moves silently dropped as bad ticks → biased forward returns. | Volume/corp-action sanity check; log drops. |
| CL-CCI-10 | concall_extract.py:148 | LLM behaviour scores clamped but never validated for direction/range. | Per-row parse-confidence flag. |
| CL-CCI-11 | concalls.py:181 | Transcript text taken raw from pypdf; garbled text-layer PDFs score as valid. | NFKC normalize + alnum-ratio quality heuristic. |
| CL-CCI-14 | concall_extract.py:264 | `_set_status` (DONE) and `_persist` use separate connections → not atomic. | Set status in the same transaction. |
| CL-CCI-15 | cci_backtest.py:126 | Hardcoded `period_year BETWEEN 2010 AND 2026` silently drops post-2026 data. | `date.today().year` or drop upper bound. |
| CL-PROV-05 | screener.py:342 | `datetime.utcnow()` deprecated/naive. | `datetime.now(timezone.utc)`. |
| CL-PROV-06 | provenance.py:495 | Per-cell `stamp()` without a shared conn re-runs schema DDL + opens a conn per value. | Pass `conn`; cache schema-ensured state. |
| CL-PROV-07 | data_quality.py:153 | `chk_provenance_knowable` full-table Python scan each run. | Push to SQL (GLOB/length) or sample. |
| CL-PROV-09 | news_tagging.py:255 | `LIMIT {int(limit)}` f-string (int-cast safe but inconsistent). | Bind `LIMIT ?`. |
| CL-PROV-12 | news_feed.py:613 | `_items_block` caps summary but not title → unbounded LLM input. | Cap title length. |
| CL-PROV-15 | fundamentals_asof.py:241 | `eps_ttm` sums last 4 quarters without checking they're consecutive. | Verify ≤~370d span. |
| CL-DASH-10 | dashboard.py:4717 | Entry-price OHLC band uses fixed ±0.05 absolute (meaningless across price scales). | Relative or max(abs,rel) band. |
| CL-DASH-13 | dashboard.py:6404 | Corp-action window hard-coded `[-264:]`. | Tie to actual zone lookback. |
| CL-DASH-14 | dashboard.py:1097-1371 | ~1,200 lines of dead post-`return` legacy bodies across ~8 cockpit-delegating routes. | Delete dead bodies. |
| CL-DASH-15 | dashboard.py:4394 etc. | `snapshot_json`/`alerts_json` parsed with broad `except: {}` → corruption silently vanishes. | Log/count parse failures. |
| CL-DASH-17 | dashboard.py:892,2152 | Sector IN-lists inlined via string concat (constants, latent). | `?` placeholders. |
| CL-DASH-19 | dashboard.py:6246 | `cmp` query param unbounded into memory (heavy query is capped). | Slice at entry. |
| CL-DASH-12 | dashboard.py:8550 | PWA icon still the legacy "H" glyph under patearn branding. | Use the header mark. |
| CL-CHR-5 | nav_links.py:71 | `_qsym` doesn't encode `?`,`=`,`/`. | `urllib.parse.quote(s, safe="")`. |
| CL-CHR-6 | cockpit.py:221+ | Hardcoded legacy palette hexes bypass `body.uk-skin` retint (bleed-through). | Move to CSS classes / tokens. |
| CL-CHR-7 | shell_skin.py:333 | `_ACTIVE_HREF_RE` brittle to attr order/multi-class. | Order-tolerant regex / pass `active`. |
| CL-CHR-8 | v2_surfaces.py:247 | "More" group emits scraped href/label unescaped (only nav path that doesn't). | Escape both. |
| CL-CHR-9 | glossary.py:101 | `lookup` computes `_norm(term)` repeatedly. | Bind once. |
| CL-CHR-10 | nav_links.py:276 | `_THEME_H2_RE` very broad, shares prefix with index header. | Theme-specific marker. |
| CL-CHR-11 | cockpit.py:218 | `_esc`/`D._esc` doesn't escape `"` → a `"` in a stored URL breaks `href`. | Escape quotes (see CL-VIEW-01, CL-DASH-04). |
| CL-VIEW-05 | growth_view.py:140 | `sym=` in href HTML- but not URL-encoded (other views use `_q`). | `_q(sym)`. |
| CL-VIEW-09 | wolfe_view.py:317 / harmonic_view.py:124 | JS-string safety relies on `_q` percent-encoding — latent if swapped to `_esc`. | Comment the invariant. |
| CL-VIEW-11 | stock_chart.py:241 | Re-sorts full `tval` array on every repaint. | Cache `tvCap`. |
| CL-VIEW-13 | drawings_store.py:88 | POST `/dash/drawings` unauthenticated, keyed only by symbol (single-user OK). | Per-user key if multi-user. |
| CL-VIEW-14 | rrg_view.py:268 | Benchmark dict looked up twice in the ratio comprehension. | Bind once. |
| CL-VIEW-15 | screener_plus.py:51 | `_LIQ` hardcodes `value>1e7 AND close>20` — static rupee threshold vs the no-static-threshold doctrine. | Percentile/turnover-rank gate. |
| CL-VIEW-18 | rotation_view.py:266 | Two `get_conn()` contexts per request. | Reuse one connection. |
| CL-VIEW-07 | participants_view.py:49 | Dead `f"right:50%"` prefix. | Drop `f`. |
| CL-SYS-05 | preview_app.py:37; envelope.py:76 | Broad `except: pass` hides startup/provenance errors. | Log at WARNING. |
| CL-SYS-08 | telegram_bot.py:216+ | `asyncio.get_event_loop()` deprecated in coroutines. | `get_running_loop()`. |
| CL-SYS-10 | main.py:96 | `/chat` HTTP route unauthenticated (spends Anthropic credits). | Confirm LAN-only / add shared-secret. |
| CL-SYS-11 | auth.py:31; schema.py:39 | Scope vocab drift: `alpha` vs `data-feed`; tenant `tier=next(iter(scopes))` non-deterministic. | Align defaults; set tier deterministically. |
| CL-SYS-12 | conversations.py:15; chat.py:142 | Telegram history grows unbounded; full thread loaded each turn before slicing. | `ORDER BY id DESC LIMIT N`. |
| CL-SYS-13 | settings.py:38 | Unused `broker_api_*` secret fields (latent secret surface). | Remove until trading wired. |
| CL-PAT-01 | pat/engine.py:67 | Unbounded `_CACHE` dict (memory leak + stale after feedback change). | LRU/OrderedDict cap + feedback version stamp. |
| CL-PAT-02 | pat/engine.py:134 | User 👎 feedback text injected verbatim into the LLM system prompt (prompt-injection/poisoning). | Strip/clamp/fence as untrusted. |
| CL-PAT-03 | pat/disambiguate.py:244 | `route_index` (the "₹0 quota-proof" deterministic router) is implemented but never called. | Wire into `route()` or delete. |
| CL-PAT-05 | pat/web.py:2473 vs threads.py:252 | Divergent ticker-stopword lists between the two follow-up resolvers. | Shared constant. |
| CL-PAT-07 | pat/web.py:486 | Shared numeric formatters lack NaN/inf guard. | `math.isfinite` → `—`. |
| CL-PAT-08 | pat/flows.py:765 | `namelike="%"+token+"%"` doesn't escape `%`/`_` (bound, but changes LIKE semantics). | `ESCAPE` clause / strip. |
| CL-PAT-09 | pat/web.py:2655 | Non-intersecting refine runs `_free_text` twice (2 routes/Gemini calls). | Detect before first render / cache route. |
| CL-PAT-11 | pat/web.py:2254 | Per-answer `MAX(date)` scans not memoized. | Compute as-of once per request. |
| CL-RES-07 | explosive_moves/mega_search.py:100 | 144-config CAGR grid sorted by the test window, no multiple-testing adjustment. | Deflated/Bonferroni statistic; require both-half survival. |
| CL-RES-08 | explosive_moves/gridsearch.py:34 | Exit-param grid ranked by in-sample expectancy, then feeds `strategies.py`. | Train/test fold split. |
| CL-RES-10 | explosive_moves/results_table.py:15 | Data-derived thresholds reported with in-sample lift. | Note provenance; held-out lift. |
| CL-RES-12 | research/cci/common.py:50 | Concall anchor approximated as the 15th of month (mild look-ahead vs actual call date). | Use actual `concall_dt` / first trading day of next month. |
| CL-RES-14 | wolfe_waves/phase1_tradesim.py:175 | phase1 default universe is current-Nifty-500 (survivorship); inclusive is opt-in. | Default to inclusive; label nifty500 as biased. |
| CL-SCR-08 | scripts/probe_*.py | SQLite connections opened, never closed. | `with`/`finally close()`. |
| CL-SCR-09 | scripts/recon_dossier.py:184 | Sparkline sampling can drop the as-of/peak bars (off by ≤3 days) on a "zero look-ahead" demo. | Force-include as-of + sell index. |
| CL-SCR-10 | scripts/pipeline_status.py:11 | One missing table aborts the whole status print. | try/except per section → `n/a`. |
| CL-SCR-11 | scripts/build_dossier_html.py:70 | `json.load(open(...))` leaks the fd. | `with open(...)`. |
| CL-SCR-12 | scripts/chrome_gate.py:100 | Double `wire()` "idempotency test" asserts nothing. | Drop or assert route/wrap count unchanged. |

---

## Verified-clean / disputed (do NOT action)

| ID | Verdict | Note |
|---|---|---|
| CL-DASH-11 | ✗ FALSE POSITIVE | "Today's movers" losers slice is **correct** — within a descending sort, `[...][-5:]` takes the *most* negative five (biggest losers); `[::-1]` shows worst-first. The reader misread the sort direction. Verified by hand. |
| CL-DASH-02 | ⚠ DISPUTED | The bare-columns-with-`MAX()` GROUP BY is **safe on SQLite** (guaranteed to return the max row since SQLite 3.7.11, 2012). Only a concern if the DB engine ever changes. Low priority. |
| CL-DASH-01 / CL-DASH-07 | ✓ cleared | Stock-page RS overlay names come only from the DB allowlist and are escaped; not exploitable. |
| CL-PROV-16 | ✓ cleared | Industrialization-proxy derivation verified correct. |
| CL-VIEW-12 / CL-VIEW-17 | ✓ cleared | Trust surfaces (coverage/replay/testing) are defensively wrapped; overlay snippets preserve `__wfpc`/`__wfcandle`. |

**Pat / drawings / pat_tid:** No SQL injection from NL filters (all `?`-bound, tokens from closed dicts); `pat_tid` validated `^[0-9a-f]{8,40}$`, server-minted, httponly; conjunctive-refine correctly INTERSECTS. Clean.

---

## Next step

Codex (`gpt-5.5`, read-only) runs the same full-codebase audit, **adds its own findings** (`CX-*`) and **rates every `CL-*` row above** in `codex-bridge/DISCUSSION-bug-audit.md`. Claude then rates Codex's `CX-*` findings. Ramana approves; only approved items are implemented (one commit per fix, `PROJECT_STATE.md` updated in the same commit).
