> **Lifecycle: TRANSIENT** — the self-contained brief for the Graphite parity-fix program
> (an Opus-5 session, owner-run). Retire when the gap register is closed and folded. Registered
> in `docs/DOC_INDEX.md`.

# Graphite parity-fix program — session brief (Opus 5)

You are the **Graphite parity-fix session**. The classic→Graphite migration is DEPLOYED and
LIVE (`/dash` → `/dash/home`; classic byte-frozen at `/dash/classic`), but a per-block audit
found **464 gaps (160 MAJOR)** where the Graphite twin lacks classic capability, plus owed
improvements. Your mission: close the register, restore-don't-replace, nothing removed.

## Boot (in order, lazy-load beyond it)
1. `docs/graphite-gap-register.md` — THE work-list (660 rows, per-workspace tables, file:line
   evidence both sides). You tick rows off IN this file as they close (same commit as the fix).
2. `docs/graphite-cutover-orchestration.md` — program history, binding rules §0, deploy links.
3. `docs/graphite-home-carryforward.md` §3 (Free/Pro grammar) · §4 (standing corrections) ·
   §6 (the verified deploy recipe).
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
- **P1 — Cross-cutting (M, highest leverage, ~120 rows):** (a) ONE shared table-toolbar
  component (sort · filter box · row count · server CSV · column picker · `?` popovers) adopted
  by every Graphite table (~40); (b) the Rule-1 un-gating sweep; (c) nav residuals per register
  §0 — but re-verify against main first: W6 (`276762c`) already wired 17 pages, repointed all
  six doors, and made `nav_integrity_gate` exit 0 — cross off what it closed.
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
  carryforward §6: md5-sweep · `.bak-p<N>` backups · `tr -d '\r'` · py_compile · prod-venv
  import+hasattr sweep · `fuser` writer-safe · NEVER restart ~14:01 UTC · curl-walk with real
  data + journalctl clean · hand the owner a fresh `?v=` link per phase.
- Argue back on any register row you believe is wrong — with file:line evidence; record the
  verdict in the register rather than silently skipping.
