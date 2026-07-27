> **Lifecycle: TRANSIENT** — the self-contained brief for the Graphite parity-fix program
> (an Opus-5 session, owner-run). Retire when the gap register is closed and folded. Registered
> in `docs/DOC_INDEX.md`.

# Graphite parity-fix program — session brief (Opus 5)

You are the **Graphite parity-fix session**. The classic→Graphite migration is DEPLOYED and
LIVE (`/dash` → `/dash/home`; classic byte-frozen at `/dash/classic`), but a per-block audit
found **464 gaps (160 MAJOR)** where the Graphite twin lacks classic capability, plus owed
improvements. Your mission: close the register, restore-don't-replace, nothing removed.

## Boot (in order, lazy-load beyond it)
1. `docs/graphite-gap-register.md` — THE work-list (§1–§11: 464 rows + the 29-row §11
   information-contract audit; per-workspace tables, file:line evidence both sides). You tick rows
   off IN this file as they close (same commit as the fix).
2. **Appendix A of this brief** — the binding lane rules, the standing owner corrections, the
   Free/Pro grammar and the verified deploy recipe. (It absorbed
   `docs/graphite-cutover-orchestration.md` + `docs/graphite-home-carryforward.md`, both retired
   2026-07-28 per their Lifecycle banners.)
3. `PROJECT_STATE.md` § Session log → **"Graphite cutover mega-orchestration — 2026-07-27/28"** for
   the program history + every commit/deploy anchor (W0→W7, D148/D149/D150).
4. `CLAUDE.md` (repo guardrails — primary sources, cost discipline, state-doc same-commit gate).

## Binding policy rulings (parent-session ratified; owner may override in-session)
1. **Free-in-classic stays FREE in Graphite.** Classic had zero tier machinery; ~40
   register rows show classic-free content behind Pro teasers (F&O 12-of-200, rotation 12M/24M
   horizons, leaders' thesis columns, …). UN-GATE every such row. Pro gates only NEW reference
   depth (percentile chips, deeper history) that classic never showed.
2. **Nothing is removed, ever.** A Graphite page replaces a classic one only at full per-block
   parity; until then the register row stays open. Classic remains byte-frozen at
   `/dash/classic` throughout.
3. **Owner asks folded in:** rotation horizons become **3 / 6 / 12 / 18 / 24** months (3 restores
   classic; **18 is NEW** — owner-requested); the RRG **Play apparatus** returns in full
   (playback · slow/med/fast · draggable scrubber + month badge · hover-to-trace · tapered
   tails · cadence smoothing — classic reference: `src/web/rrg_view.py` ~L372-580).
4. Two XS correctness defects (band-locks `"UP"` case · seasonal `iso_week` axis) are being
   fixed by the parent session — `git pull` first and kickstart-pick-verify before touching.
   **DONE by `lane/parity-truth` (2026-07-28): parity downgrades (34 keys PORTED→DEFERRED, board
   now 22/45/5/2) + both XS defects (pinned by `tests/test_graphite_parity_defects.py`) + the 7
   false SURFACE_PARITY notes + M6/M7/M8 re-opened to PLANNED — do not redo; see register §10.**

## Work order (by leverage; one phase = one worktree lane = one deploy)
- **P1 — Cross-cutting (M, highest leverage, ~150 rows):** (a) ONE shared table-toolbar
  component (sort · filter box · row count · server CSV · column picker · `?` popovers) adopted
  by every Graphite table (~40); (b) the Rule-1 un-gating sweep; (c) nav residuals per register
  §0 — but re-verify against main first: W6 (`276762c`) already wired 17 pages, repointed all
  six doors, and made `nav_integrity_gate` exit 0 — cross off what it closed; (d) **the
  INFORMATION CONTRACT (register §11, owner-priority):** ONE shared `components.chart_frame`
  (x-endpoints · y-ticks · last-value pill · reference band · mandatory read-line · provenance —
  `components.breadth_gauges` is the model that already passes all six points) adopted by the 6
  structurally-identical hand-rolled renderers, then MACHINE-ENFORCED via a new
  `tests/test_info_contract.py` (the Pat-gate pattern); close all 12 MAJOR §11 rows. Parent
  rulings pending owner override: the Regimes strip renders VISIBLE on Free (blur only the
  deeper drill — a blurred core regime read violates Rule 1 + the info contract) · charts carry
  a minimal FREE reference (baseline/typical line as chart furniture); the FULL reference layer
  (percentile chips, streaks, history) stays Pro. Also fix the §11 DATA defect: the home DVPT
  drawer normalises against liquid-ETF artefacts (CASHIETF 4.19M×) — exclude the liquid/ETF
  class from leader scaling, pin it.
- **P2 — Rotation (L):** Play apparatus + 3/6/12/**18**/24 + the RS-depth table (RSI-of-RS ·
  Mansfield · capture · 7 turn-flag pills) + the stock-grain half (`?phase=` selector,
  300-row member table incl. 18m/24m, "see all", leverage pills). Reuse classic's engine
  params (`_SECTOR_TAIL_SESSIONS`, `_TAIL_CADENCE`, JdK smoothing) — port, don't reinvent.
- **P3 — Strength + Sectors (L):** capture-map scatter (the lens IS the scatter) · rsband lane
  chart · the Breathe clock · thesis columns free · benchmark control · horizon sets 6→6.
- **P4 — Internals / Flows / Events / Attention (L):** regime charts un-blurred · participants
  mirror charts + the 40-day regression · attention 200-row queue + rail filters ·
  results-reactions stale-tape banner · buyback sensitivity table · surveillance membership.
- **P5 — Stock chart workstation (L):** D/W/M/Q intervals · chart types · lower panes
  (Vol/RSI/MACD) · VWAP/Bollinger/ATR · compare overlay · RS pane — extend
  `src/web/home/stock_chart_g.py` ONLY (isolation gate bans legacy chart imports). 🔴 CANDLE
  COLORS ARE OWNER-IN-SELECTION (parent session, sample lineup) — do NOT touch candle tokens;
  the 4 computed-contrast gates stay whatever treatment wins.
- **P6 — Seasonal / Patterns / Anatomy / Compare (L):** the recorded OUTSTANDING notes in
  `SURFACE_PARITY` + register rows (consolidation panels, Strength-t, §B Wolfe quality cols…).
- **P7 — Tracker (M) · Strategies (M) · Trust (M) · Screener+Themes (S-M):** per register
  tables (alerts/ready-to-act · attribution · ownership-hub controls · Pat's ~15 guided flows ·
  coverage memo · rule-lab verdict card · screen2 instrument visuals + Pat bridge · themes cols).

## Session schedule + REQUIRED LEARNING (owner directive, 2026-07-28)

Run the program as SCHEDULED Opus-5 sessions, one per phase (S-P1…S-P7; split a phase across
two sessions only if its lane report says it overran). **Capability lives in the brief, not the
model tier** (`docs/FABLE-PROTOCOL.md` doctrine): every session MUST read this section before
building and its wrap report MUST answer "which of these lessons did this session's work
exercise, and where."

**The lessons — every one is a scar this program actually earned; violating one is a regression:**
1. **Fixture blindness:** the local DB is a 4-row fixture; a green render proves STRUCTURE only.
   Any claim about data shape/coverage/perf is unproven until walked on the box. (The 756-session
   truncation and two dead-render defects all passed green suites.)
2. **One-domain rule:** multi-pane/multi-series views share ONE canonical session-date domain,
   equal array lengths, synced visible ranges, equalized axis gutters — pinned by test.
3. **Default-window rule:** the default view must show what the owner owns (the deep tape);
   payload budgets are proven FIRST, then the full data ships — visible range ≠ loaded range.
4. **Per-block parity:** a page "reads well" ≠ ported. Every classic control/column/interaction
   is carried, or its absence is a written register row. Never mark PORTED past an open MAJOR row.
5. **Free-never-gated:** anything classic showed free stays free; Pro gates only NEW depth.
6. **S158 ship-together:** a caller never deploys without its callee; import+hasattr sweep under
   the PROD venv before any restart; captions must never assert what the data on the box isn't.
7. **Verify by content:** pushes (`diff origin.. --stat` empty), deploys (md5), claims (re-run
   the command). Exit codes and green checkmarks lie; bytes don't.
8. **Pinning test per fix:** a fixed bug without a RED-then-GREEN test doesn't count as fixed.
9. **Argue back with evidence:** contest any register row or brief instruction you can falsify
   with file:line proof; record the verdict where the next session will find it.
10. **Sample-first for identity/pixel choices:** owner-visible visual changes are presented as
    labeled 100%-scale samples for the owner's pick BEFORE shipping; verification crops are
    never presented as the viewing experience.
11. **A 200 is not a verification:** every Graphite page serves a placeholder behind HTTP 200
    when its body raises, so post-deploy walks must assert CONTENT (zone count ≠ 0, zero
    "hasn't landed" markers) — see Appendix A.5 for the incident + recipe. Journal evidence
    is only meaningful from `9290ba7` forward (fallbacks now log tracebacks).

## Non-negotiable mechanics (every phase)
- Worktree per lane off current `origin/main`; branch `fix/p<N>-<name>`; NEVER edit the shared
  checkout `D:\patearn` directly; atomic add→commit; src/-touching commits carry PROJECT_STATE
  in the SAME commit (machine gate).
- Suite: plain `python -m pytest -q` (NEVER the repo `.venv` — stale py3.13). 0 failures, every
  fixed row gains a pinning test. `python scripts/doc_hygiene_gate.py` +
  `python scripts/nav_integrity_gate.py` + `python -m src.web.sideways_parity` all clean.
- Parity honesty: flip a key DEFERRED→PORTED only when its register rows are ALL closed; note
  evidence. Fences travel (D138 above-headline · CCI/MEP descriptive · ret/vol labels ·
  0-certified seasonal · PEAD net-fail).
- Push branch, verify BY CONTENT, merge to main serially (one lane at a time), then deploy per
  **Appendix A.3**: md5-sweep · `.bak-p<N>` backups · `tr -d '\r'` · py_compile · prod-venv
  import+hasattr sweep · `fuser` writer-safe · NEVER restart ~14:01 UTC · curl-walk with real
  data + journalctl clean · hand the owner a fresh `?v=` link per phase.
- Argue back on any register row you believe is wrong — with file:line evidence; record the
  verdict in the register rather than silently skipping.

---

# Appendix A — grafted from the retired cutover docs (BINDING; do not re-derive)

> Absorbed 2026-07-28 (lane `lane/w7-close`) from `docs/graphite-cutover-orchestration.md` §0 and
> `docs/graphite-home-carryforward.md` §2/§3/§4/§6 when both were `git rm`'d per their Lifecycle
> banners. This appendix, plus the `PROJECT_STATE.md` session-log entry named in Boot §3, is the
> complete surviving record. Nothing here is optional.

## A.1 — Binding rules for EVERY lane (cutover charter §0)

Classic site byte-FROZEN · additive + isolated (`.g-*`, no legacy/`*_v3`/preview imports) ·
fixed-size internally-scrolling boxes, never a flat endless page · demo/sample honesty (generate a
demo when a live read is empty, but the real-vs-demo line stays HONEST via the sample badge) ·
descriptive-only fences + evidence links travel with the data · **Free is never crippled** ·
primary sources only (Guardrail #8) · worktree isolation, atomic `add`→`commit`, stage only your
own hunks · **verify pushes by CONTENT, never exit code** · deploys serialized by the parent per
A.3 (writer-safe, never ~14:01 UTC) · argue back and record the verdict on genuine forks.

Environment facts that cost a session each to rediscover: the in-repo `.venv` is a **stale py3.13
env with no numpy — NEVER use it** (plain `python` = the hermes-agent venv); the local
`data/hermes.db` is a small fixture, so structure is verifiable locally and **data only on the
box**; the in-app Browser pane is DOWN — verify HTML/gates/data on the box and hand the owner a
`?v=N` link for pixels.

## A.2 — Standing owner corrections (carry-forward §4) — violate none

1. **Classic site FROZEN (byte-identical).** The new experience is FROM SCRATCH — no legacy
   palette; carry only doctrine + the blue-up/grey-down candle identity. [[ramana-working-principles]]
2. **Plan-first; study reference products; present; build on go.** On a genuine fork, run the
   counter-option and give the VERDICT before building — especially on "any better way?".
3. **Fixed-size boxes that scroll INTERNALLY** — never a flat endless page.
4. **Generate demo when a live read is empty, but keep the real-vs-demo line HONEST** (sample badge).
5. **Crisp by default; detail on demand;** calibrate format to the question.
6. **Plain-English, clickable symbols, every number links to its source, descriptive-only fences.**
7. **Argue back, no sycophancy** — the owner wants the spine and the honest verdict.
8. **A number in isolation is useless — the reference point is the premium.** Free gives the number;
   Pro says whether it MATTERS (normal/unusual, which way, better/worse than before).
9. **Verify on the box** (HTML/gates/data); pixels via the owner (`?v=N` link).

**The Free/Pro grammar (carry-forward §2/§3), which Rule 1 of this brief constrains:** FREE = a
complete, honest glance — every number, the map, the watchlist, today's reads; never a teaser. PRO =
the REFERENCE LAYER + depth, expressed as ONE chip grammar everywhere — `components.ref_chip`,
`Npct · band · typ X · ↑/↓` — plus drill-downs, full history/universe, portfolio-aware analytics.
PRO-ADS = `components.pro_teaser`, the third `.g-proad` state: a blurred real Pro block + an
"Unlock with Pro" CTA shown to Free users. **A reference chip is only ever rendered where an honest
reference EXISTS** (no stored history → no fabricated percentile; a 24-point store is a "range
position", not a percentile) — the precedent that keeps Rule 1's un-gating sweep honest.

## A.3 — The deploy recipe (verified across the whole cutover; see [[vps-deploy-reality]])

`scp src/web/home/*.py hermes:/opt/hermes/src/web/home/` (NEW modules — a full scp is fine; a
CO-EDITED file such as `v2_surfaces.py` is **anchored-insert patched, NEVER full-scp'd**) → on box
`tr -d '\r'` each (NEVER `sed`) → `.venv/bin/python -m py_compile src/web/home/*.py` →
**import + `hasattr` check of every new CALLEE under the prod venv** (S158: patch-deploying a caller
without its callee is silent, because the imports are lazy) → **writer-safe restart**
(`fuser /opt/hermes/data/hermes.db` must show no FOREIGN writer; hermes-api startup is read-only;
**never restart ~14:01 UTC**, the bhavcopy window) `systemctl restart hermes-api` → `curl …/dash/home`
200 + structure grep + a REAL-DATA walk (the verify-curl also warms the conviction cache) →
`journalctl` clean → hand the owner a fresh `?v=N` link. Keep a `.bak-<phase>` set on the box: the
rollback is restoring those files (+ the four `_ROUTER_SPECS` tuples) and restarting. Chat/Telegram
prompt changes live in `src/assistant/chat.py` → restart `hermes-api` AND `hermes-telegram`.

**Live estate as handed over:** `/dash` **302s** to `/dash/home` (D148, middleware
`src/web/home/cutover.py`); classic is byte-frozen and preserved at `/dash/classic`; the old preview
302s into Graphite (D149, `src/web/home/preview_retired.py`). Owner links:
`https://srv1704897.hstgr.cloud/dash/home?v=w7` · `…/dash/home/stock?sym=TCS&v=w7`.

## A.4 — Open chips inherited from the ledger (not cutover work; do not lose them)

- The classic `strategies_view._public` sanitizer **LEAKS on live `/dash/strategy-ref`** today
  (`S164BB` / `S155-e` / `S1234` escape the regex). Classic is byte-frozen → RECORDED, not patched;
  the Graphite port widens it and adds a line-drop backstop.
- `rule_lab.BLOCKING_ROWS` mirrors the failure ledger **byte-verbatim under a machine gate** — the
  ledger and its mirror must move in the SAME commit, or the pair desyncs.
- Box `scripts/nav_integrity_gate.py` is stale and NOT-IN-HISTORY (dev-only, never imported by the
  app) — left untouched by doctrine; run the gate from the repo, not the box.
- `hub_sections_v3.load_core` queried `wolfe_signals` by `symbol` while the table keys on `sym`, so
  that badge NEVER fired — recorded so the module's retirement is not mistaken for a lost feature.

## Appendix A.5 — the 200-is-not-verification incident (grafted from the retired carryforward, 2026-07-28)
🔴 **A 200 IS NOT A VERIFICATION** (2026-07-27 incident, `9290ba7`). Every Graphite page wraps its
body in a broad `except Exception` that serves a "…hasn't landed on this host yet" placeholder, so a
CODE defect renders an EMPTY page behind HTTP 200 — `/dash/home/events` shipped that way through a
whole deploy range and a 38/38-green status sweep. The post-deploy walk must therefore assert
CONTENT, per route:

```
curl -s -o /tmp/p.html -w '%{http_code}\n' http://127.0.0.1:8000<route>
grep -o '<section class="g-zone"' /tmp/p.html | wc -l     # expected zone count, NOT zero
grep -c "hasn't landed on this host yet" /tmp/p.html       # MUST be 0
```

Since `9290ba7` those fallbacks `log.warning(..., exc_info=True)`, so `journalctl -u hermes-api` shows
a traceback when one fires — box-verified that uvicorn leaves the root logger handler-less, so
Python's last-resort handler puts WARNING+ on stderr and journald captures it. A clean journal is only
meaningful evidence from that commit forward; before it, the page was broken AND the journal was clean.
Note the fixture DB used by local gates has no `board_meetings` rows, so the defect's code path never
ran locally either — data-shaped fixtures (see `test_home_markets_pages.py` §7) are what close that gap.
