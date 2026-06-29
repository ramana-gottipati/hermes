# Lane L4 — Pat copilot + research wedge — STATUS

> **Session 2026-06-29.** Sole autonomous builder of Lane L4 (Pat copilot + the research/provenance
> wedge). HEAD at boot `05cdeae`. Both gates (`regression_sweep.sh` + `chrome_gate.py`) PASS.
> Owned: `src/pat/*`, `src/web/{strategist_view,screener_plus,provenance}.py`, `src/automation/cci_*`,
> the research.db lane. Frozen for me: `dashboard.py`/`cockpit.py`/`rrg_view.py` (L1), `ui_kit`/
> `shell_skin`/`v2_surfaces` (L2), `chart_view`/`stock_chart`/`wolfe*`/`harmonic_*` (L3).

## Commits (this lane, this session)
| Commit | What | Files |
|---|---|---|
| `1ef085a` | **Pat true multi-turn thread store + single-name credibility intent** | `src/pat/{threads.py(new),web.py,understand.py,eval_set.py}` |
| `f7fdbe1` | **Wire single-name credibility into the LIVE ₹0 pre-router** (`1ef085a` had only the `parse_fallback` path; the live VPS with Gemini up would not route it deterministically) | `src/pat/disambiguate.py`, `docs/pat-design-and-improvements.md` |
| `e80bfc5` | Commit the L4 CCI research machinery (byte-identical to VPS) | `src/automation/{cci_backtest,cci_deep_actuals,concall_direction}.py` |

Each commit staged EXACTLY its owned paths (`git diff --cached --name-only` verified); never `git add -A`;
no frozen file touched. Backups on the VPS: `src/pat/.bak-L4-<ts>/`.

## Backlog coverage (the ≥8 items)

### 1. Pat saved-boards polish — VERIFIED ROBUST (no change needed)
`boards.py` already handles every edge: empty name → `None`; name sanitised (`My <Board>! 2026` →
`My Board 2026`); upsert by `(name, kind)`; `delete` of a missing board → `False` (no raise); `get` of a
missing board → `None`; all reads degrade to `[]`/`None`. The manager (`flow=boards`) renders an explicit
empty state. Left as-is — gold-plating it would add risk for no gain.

### 2. Richer Pat intents — SHIPPED (`1ef085a`)
NEW `understand.detect_single_credibility`: **"is X credible" / "how credible is X" / "confluence on X" /
"X credibility" / "can I trust X management"** now route to the `why`-flow single-name EVIDENCE read
(composite + sub-scores + promises-resolved + the verbatim receipts + provenance footer), instead of
returning `None` (a dead-end) as they did at boot. Guarded both ways: the plural metric ask
("most credible managements") stays the leaders board; the definition ask ("what is credibility") stays the
glossary explain. Wired on **both** paths so it fires identically whether or not Gemini is up: a ₹0
deterministic pre-route in `disambiguate.route_extra` (`f7fdbe1` — placed after compare/strategy/trend/why,
before the generic single-stock card) **and** in `understand.parse_fallback` (`1ef085a`). Verified live on
the VPS: "is TCS credible" → why/credibility; "most credible managements" → leaders; "what is credibility"
→ explain; "TCS vs INFY" → compare. (The credibility-trend, confluence, planner, compare, why, strategy
intents already existed from F2/F-rounds.)

### 3. Ranked top-N — ALREADY SATISFIED for the core; explicit-N cap is the documented F2-7 deferral
Every list flow is **already ranked + sorted + capped and shows the raw value beside the verdict**
(RS rank, credibility composite + met% + n, etc. — data-first). The remaining piece — honouring an
explicit "top 5/top 10" N — requires threading a LIMIT through every `build_*` query + the param-smuggling
contract through the frozen `dashboard.py` generics; that is exactly the **F2-7 deferral** recorded in
`docs/pat-design-and-improvements.md` (deferred on cost-discipline, lists already capped). Not reopened
this session — the risk/reward against a frozen call-site is wrong.

### 4. Multi-turn thread store — ✅ CLOSED + LIVE ON PROD (L1 landed the call-site `c736f3a`)
NEW `src/pat/threads.py` — server-side conversation memory keyed by an optional `tid` (own `pat_threads`
table, `boards.py` pattern; rolling 12-turn window; server-minted uuid4 `tid`, regex-validated, SQL-bound;
nothing raises to the caller). `web.render_pat()` now **accepts optional `tid` / `new`**:
- with a `tid`: renders a compact **"This conversation" trail** above the answer (prior turns as
  click-back chips, oldest→newest) + a **"start over ⟲"** link (`?new=1` clears the thread) + records each
  concrete answer as a turn.
- with the **default `tid=""`: completely INERT** (zero behaviour change) — proven in-browser + by smoke.

**⇒ CALL-SITE CONTRACT — NOW CLOSED.** L1 landed the cookie plumb in `dashboard.py:1449`
(`dash_pat`: reads/validates/mints the `pat_tid` cookie, forwards `tid`+`new` into `render_pat`, sets the
cookie `httponly + samesite=lax`, 30d) in commit **`c736f3a`** AND deployed it to the VPS
(`grep -c pat_tid /opt/hermes/src/web/dashboard.py` → 3). My `render_pat(tid=)` signature having landed
(`1ef085a`) was the unblock.

**VERIFIED LIVE END-TO-END on the prod VPS** (cookie-jar curl): turn 1 →
`set-cookie: pat_tid=…; HttpOnly; Max-Age=2592000; SameSite=lax`; turn 2 (same jar) → the
**"This conversation" trail renders**; `?new=1` → trail cleared (start-over works). Default `tid=""`
stays inert. Multi-turn is now fully live with no further L4 change needed.

### 5. RESEARCH — knowable_at leak → 0 — VERIFIED LIVE (Lane D/H work; confirmed, not rebuilt)
`provenance.lag_audit()` is **non-empty** on the VPS (29,176 pairs): baseline +90/+50 modelled leak
**11.9%** → calibrated p95 (A=113d / Q=59d) **4.6%** → **effective (real-preferred) blended 1.42%**
(real-BSE-dated periods leak 0%; the calibrated synthetic covers the rest). De-model rate **69.2%**.
`provenance --selftest` OK (35 classes). `provenance_knowable`=29,176, `provenance_lag_calibration`=2.
The forward scheduler (`hermes-fundamentals-provenance.timer`, Tue+Sat) is armed. Nothing to build —
the gate is cleared; I verified it.

### 6. RESEARCH — CCI Phase 3 (descriptive RRG + divergence + backtest) — VERIFIED LIVE
- **RRG/divergence** (`cci_rrg.py`): `credibility_rrg` = **806 rows**, 9 quadrants populated (155
  proven-improving / 296 unproven-improving / 49 low-deteriorating / …). Divergence (TEXT label, correctly
  queried): **331 POSITIVE_DIVERGENCE / 247 CONFIRMING / 180 NONE / 48 NEGATIVE_DIVERGENCE**. `--selftest`
  OK; `build()`+`summary()` round-trip OK. Correctly framed **DESCRIPTIVE** (the "positive divergence =
  alpha" premise is undercut by the falsified momentum result → surfaced as an observation, never a signal).
- **Backtest** (`cci_backtest.py`, FREE/no-LLM): the recorded benchmark stands — **CCI has NO validated
  long/short/risk return edge** (high-cred UNDERperforms, survivorship-fragile, momentum weak,
  deterioration-veto structurally blind). Negative result kept as a benchmark (`docs/strategy-ledger.md`),
  never discarded (ramana-working-principles). Did NOT re-run the heavy backtest to re-derive a known
  verdict.

### 7. RESEARCH — survivorship deterioration re-test — STRUCTURALLY BLOCKED (now QUANTIFIED)
Confirmed with a direct VPS query: of the **806–809 names with a credibility score, exactly 1 is
not-currently-listed and 0 are status='delisted'**; only **33 delisted names have any concall row at all**
(mostly recent M&A, not distress blow-ups). The distress cohort the veto is meant to flag has ~0 concall /
credibility data because the **BSE transcript mandate (~2021+) post-dates the 2010s distress cohort**. The
re-test **cannot be run** — this is a genuine structural data gap, not a capture/spend-fixable one. The
deterioration veto **stays DESCRIPTIVE** (the §C falsification stands). This is the sharpest statement of
the block yet (1-of-806 is a number, not a hand-wave).

### 8. RESEARCH — data-licensing migration status — VERIFIED
- `provenance.redistribution_status(data_class)` + `licensing_digest()` live: 18 owned / 10 public-record /
  6 vendor-tos / 1 news-license. **Fail-closed**: unknown class → `vendor-tos` (most restrictive) — correct
  for the `/v1` external-scope gate. NSE/BSE/exchange → public-record; computed/Gemini/rule → owned;
  Screener → vendor-tos.
- **6 vendor-tos migration targets** (the remaining Screener.in dependency): `fundamentals_live`,
  `fundamentals_history`, `shareholding_history`, `company_about`, `concall_corpus`, `concall_results`.
- **De-Screener concall discovery EXISTS** (`concall_bse.py`, BSE announcements →
  `SUBCATNAME='Earnings Call Transcript'`): `--selftest` OK (filter + period + attachment-url + capture
  round-trip, idempotent). The concall LANE is migratable off Screener; the fundamentals classes are the
  pre-pitch swap targets per `docs/data-licensing-decision.md`.

### 9. Provenance-stamp every new Pat answer / research output — DONE
The new single-name credibility answer routes to `why`, which already carries the full provenance footer
("credibility as-of · rank N of the pilot · K concalls scored · source: concall track-record (CCI pilot) ·
descriptive evidence · not a recommendation") — screenshot-confirmed in-browser. The multi-turn trail is
session metadata (not a data claim). All research reads are stamped (`as_of_period` / `knowable_at` /
`effective_as_of` / divergence-as-observation).

## Verification evidence
- **Pat UI in-browser** (non-negotiable #1): screenshot of `/dash/pat?q=is+TCS+credible` on the live VPS —
  "TCS reads MIXED" with composite 26/100 tier D, the receipts, the provenance footer, refine box +
  save-board + feedback bar, unified chrome. Default page renders clean.
- **Multi-turn** verified on the live VPS stack (3-turn trail, default tid inert, ordered history).
- **Research** verified on the VPS (real data; local hermes.db is a 4-symbol stub): `lag_audit` non-empty,
  `cci_rrg`/`provenance`/`concall_bse` selftests OK, survivorship block quantified, licensing digest read.
- **Eval** (VPS real data): compiler 31/31, route 60/61 (TREND 12/12; the one fail is the pre-existing
  "cheap stocks under PE 15"), EXPLAIN 493/495 (2 pre-existing), HALLUCINATION 8/8, **ACCURACY 10/10**.
- **Harness**: `regression_sweep.sh` PASS (31 routes + 4 overlays 200 + chrome gate) + `chrome_gate.py`
  PASS, before each commit.

## Deviations / notes (Wave 1)
- Items 5–8 were **verified, not rebuilt** — they shipped in Lanes D/H/H2 and are live on the VPS; the L4
  task was to confirm + commit the machinery + state the gaps honestly (kickstart-pick-verify discipline).
  I committed the three untracked owned research modules so the repo inherits them.
- The repo↔VPS `engine.py` divergence noted in memory is **not relevant** to this lane — I did not touch
  `engine.py`.
- `PROJECT_STATE.md` deliberately NOT edited (per the lane brief — rides the wrap reconciliation).

---

## WAVE 2 — screener unification + strategist depth + provenance durability

Multi-turn went **end-to-end live** between waves: L1 landed the `pat_tid` cookie call-site (`c736f3a`,
deployed + browser-verified) — the thread trail is now live (confirmed in the W2 top-N screenshot:
"THIS CONVERSATION: most credible managements › top 5 …").

### W2 commits (owned paths only; staged set verified == my paths each time)
| Commit | What | Files |
|---|---|---|
| `361c95e` | **Screen+ confluence SUPERSET (Wolfe + pt14) + column-parity check** | `src/web/screener_plus.py` |
| `b8ec3f8` | **Credibility RRG + divergence tile (CCI P3) on the strategist workbench** | `src/web/strategist_view.py` |
| `a07208d` | **Pat explicit "top N" cap on the ranked list flows (F2-7)** | `src/pat/{web,flows,understand,engine,disambiguate,eval_set}.py` |
| `313e02f` | **provenance.lag_headline() — surface the EFFECTIVE leak, not buried** | `src/automation/provenance.py` |

### Backlog coverage (W2 items)
1. **SCREEN+ → DEFAULT-GRADE** (`361c95e`) — added the brief's 5th pillar **Wolfe** (was absent; READ-ONLY
   `wolfe_signals`) → confluence is now 0-6; added **Quality·pt14** columns (READ-ONLY `pattern_scores`).
   NEW `parity_report()` + `/dash/screen2?parity=1` page proves **8/8 legacy analytic families covered +
   3 new lenses (MEP, Confluence, Wolfe) → PROMOTABLE** (parity by family — legacy carries deeper
   p1-p12/b1-b24 ladders Screen+ summarises; both read the SAME precomputed tables). Saved screens / group
   toggles / CSV intact. **Promotion to default = a `lens_registry` nav slot → L1/orchestrator's call**
   (NOT a hand-edit of frozen nav). Documented in the in-app parity page + this note.
2. **STRATEGIST DEPTH** (`b8ec3f8`) — NEW Credibility RRG·divergence tile from `cci_rrg.summary()` (806
   names): 155 proven-improving / 37 slipping / 72 low-deteriorating / 331 +divergence / 48 −divergence,
   each deep-linking to credibility leaders / deterioration tape / coverage. Framed **"a research map, NOT
   a ranked signal (no validated return edge — §C falsified; survivorship-limited)"**. The existing cards
   already carry count/freshness/top-names/health from `strategy_registry.summary()` + deep-link to each
   lens. NEW "Credibility" toolbar toggle. Browser-verified (806 names, real numbers).
3. **PAT EXPLICIT-N** (`a07208d`) — closes the deferred F2-7. "top 5 credible X" / "top 10 RS leaders" /
   "best 3 accumulation" cap the list to the **N strongest already-ranked** rows (ranking unchanged, raw
   values beside the verdict). Wired through ALL routing paths (parse_fallback stamp · engine inject ·
   route_extra ₹0 pre-route · `_VALID` "int" kind, fail-closed). **Live row counts EXACT** (top 5 → 5,
   top 10 → 10, bare → 80 safety-cap); browser-verified ("CREDIBILITY LEADERS — TOP 5 (5)").
   eval TREND 15/15, route 63/64, HALLUC 8/8, ACCURACY 10/10.
4. **PROVENANCE DURABILITY** (`313e02f`) — `hermes-fundamentals-provenance.timer` **ENABLED + armed**
   (next Tue 2026-06-30 21:00 UTC); `--demo-capture` proves the forward hook (captured 1, real
   `knowable_at` stamped, cleaned up, `ok:true`); `lag_audit()` stays non-empty after `--calibrate`
   (29,176 pairs). NEW **`lag_headline()`** surfaces the effective leak flat: **baseline 11.9% → calibrated
   4.6% → effective 1.42% · de-model 69.2% · 8.4× cut**, now in `coverage_snapshot()` so the Coverage read
   + `/v1` can lead with it. **HAND-OFF:** `coverage_view._section_modeled` reads the OLD flat lag_audit
   shape → a 1-line render of `snap['lag_headline']` by the coverage_view owner makes it visible on the
   page (the data is now there).
5. **PAT↔RESEARCH BRIDGE** — verified, no gap: every credibility receipt cites provenance consistently
   (why = composite+sub-scores+receipts+as-of+source; leaders/deterioration = freshness bar; confluence =
   dual-lens as-of badge; trend = period-range). The "why credible" drill is already deep.
6. **CCI DESCRIPTIVE SURFACE** — the credibility RRG (806) is now reachable + readable via the W2
   strategist tile, clearly DESCRIPTIVE (§C falsification + the 1/806-delisted survivorship limit stated),
   provenance-stamped (n + as-of). Plus the existing NL credibility/deterioration flows + `/dash/coverage`.

### W2 deviations / hand-offs
- **Screen+ → default promotion** needs a `lens_registry` nav slot (L1/orchestrator owns nav) — I proved
  promotability + built the page; the nav swap is theirs.
- **Coverage page lag_headline render** — a 1-line update in the (non-owned) `coverage_view.py` to read
  `snap['lag_headline']`; the data + helper are shipped in `provenance.py`.
- **CRLF gotcha hit + handled:** git's autocrlf converted some working-tree `.py` to CRLF; I CR-stripped
  (`tr -d '\r'`) before every scp (verified CR=0 on the VPS each time) — repo stays LF.
- **Cross-absorption caught:** a parallel L2 session staged `shell_skin.py` into the shared index between
  my `git add` and commit; I unstaged it (their work landed in `75442fd`, not lost) and committed only my
  file. Thereafter staged+committed **atomically in one call** with an explicit staged-set assertion.
- Gemini is **503 (high demand)** on the VPS → the live router rides the ₹0 deterministic path
  (route_extra → parse_fallback); never-Claude holds. All explicit-N + intents verified on that path.
