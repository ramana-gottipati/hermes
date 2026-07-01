# Review brief 08 — the full 4-lane parallel arc (`cd98445..HEAD`)

**From:** Claude Code (lead) · **To:** Codex (`gpt-5.5`, reviewer) · **Mode:** READ-ONLY
**Date:** 2026-06-29 · Closes the continuous-review mandate (req-05) over the converged arc.

Review READ-ONLY; output review text only → `resp-08-4lane-arc-review.md`. Cite files/commits; if you
can't verify, say so. **49 commits** since the anchor; both gates PASS; PROJECT_STATE **Session 54** is the
record. Scope below — flag correctness bugs, over-claims, and regressions; don't re-litigate decided IA.

## Read first
1. `git log --oneline cd98445..HEAD` + `PROJECT_STATE.md` Session 54 (the map).
2. `bash scripts/regression_sweep.sh` (or `python scripts/chrome_gate.py`) — confirm green.

## Per-lane focus (the highest-value independent checks)
- **L1 / orchestrator** — `rrg_view.py` (`05cdeae`): is the timeframe-native resampling + animated `_RRG_PLAY_JS`
  sound (no RAF leak, graceful on no-data)? `dashboard.py` (`c736f3a`): the `pat_tid` cookie call-site —
  any session-fixation / forged-cookie risk (`threads._valid`)? leaders→Markets fully correct?
  `mini_rrg.py` (`b926f7a`) — confirm no OTHER tracked→untracked import landmine remains
  (`git grep "import.*mini_rrg"`; scan for similar). `coverage_view.py` (`274ee3e`) — does
  `_section_provenance_story` faithfully render `provenance_narrative()` without over-claiming (descriptive,
  no edge)?
- **L2** — `shell_skin.py` (16 commits): the `body.uk-skin .uk-*` re-asserts — any specificity/!important
  regression or NEW bleed-through? WCAG-AA `--ink-3` lift (#7e90a8) — recompute a couple of contrast ratios.
- **L3** — `stock_chart.py`/`drawings_store.py` (`6e3b22d`,`7b49e4e`,`76d465f`): the lower-pane time-sync
  (master→follower) — can it desync or busy-loop? RSI/MACD/Bollinger/ATR math correct? `drawings_store`
  caps/never-500? `/dash/compare/series` read-only + bounded?
- **L4** — `src/pat/threads.py`/`web.py` (`1ef085a`,`d3362ee`): multi-turn thread store — any injection via
  the thread, unbounded growth, or pronoun-resolution mis-binding? `provenance.py` `lag_headline`/
  `lag_samples`/`provenance_narrative` — are the leak numbers (1.42% effective, 8.4× cut, 29,176 pairs)
  defensible from the code, or is anything overstated? Descriptive-only / SEBI boundary intact?

## Output format
```
## Verdict — is the arc safe + are the claims honest?
## Correctness bugs found  (lane | file:line | severity | why)
## Over-claims / descriptive-only violations
## Regressions / clean-checkout or security risks
## Anything missed
```

## Note
Auto-dispatch from Claude Code hits the Windows sandbox block (`windows sandbox: spawn setup refresh`) —
Ramana runs this manually: `codex exec --sandbox read-only -C "D:\Hermes" -m gpt-5.5 -o
"codex-bridge\resp-08-4lane-arc-review.md" "Read codex-bridge\req-08-4lane-arc-review.md and follow it exactly."`
