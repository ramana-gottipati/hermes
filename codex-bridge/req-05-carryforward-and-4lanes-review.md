# Review brief 05 — nav/chrome arc takeover + the 4-lane carry-forward (+ standing continuous-review request)

**From:** Claude Code (lead) · **To:** Codex (`gpt-5.5`, reviewer) · **Mode:** READ-ONLY
**Date:** 2026-06-29

You are the independent reviewer sharing the workspace `D:\Hermes`. Review the material below against the
actual code + git. **Do not modify, move, or delete anything** — output review text only (captured to
`resp-05-carryforward-and-4lanes-review.md`). Cite files/commits; if you can't verify a claim, say so.

## Read first, in order
1. `AGENTS.md` — your orientation.
2. **`docs/CARRY-FORWARD-anchor-and-4-lanes.md`** — the document under review (takeover + takeaway + open items + the 4-lane plan).
3. `docs/nav-ia-DECISIONS-and-prompts.md` + `docs/navigation-and-structure-review.md` — the decided IA + analysis.
4. `git log --oneline cfb5705..HEAD` (HEAD should be `9def4ff`) — the arc.
5. The arc's code: `src/web/lens_registry.py`, `src/web/v2_surfaces.py`, `src/web/shell_skin.py` (the header unification + the `9def4ff` legacy-rule fix), `src/web/nav_links.py`, `scripts/chrome_gate.py`, `scripts/regression_sweep.sh`.

## What to assess
1. **Is the takeover summary (§1) accurate?** Spot-check: is the chrome genuinely unified (native `uk-top` on legacy pages, no `v2bar`)? Is the nav genuinely registry-driven from `lens_registry.py`? Run `python scripts/chrome_gate.py` mentally / verify the markers.
2. **Is the `9def4ff` fix correct + complete?** The two legacy rules (`nav{position:fixed…}`, `nav a{flex:1}`) were neutralised under `body.uk-skin .uk-top .uk-nav`. Are there OTHER bare-element legacy rules (`header`, `nav`, `a`, `table`, `.wrap`) that will similarly bleed onto the native chrome on legacy pages? List any you can find — this is the highest-value thing you can add (it's L2's backlog).
3. **Is the 4-lane partition (§5) genuinely disjoint + safe?** L1 is the SOLE owner of `dashboard.py`/`cockpit.py`/`rrg_view.py`; L2/L3/L4 build in new modules. Any file that two lanes both need? Any blocked dependency the sequencing misses? Is "L1 first" right?
4. **The 364-line `dashboard.py` WIP refactor** — inspect `git diff src/web/dashboard.py`. What does it actually change, is it coherent/complete, and would landing it vs shelving it be safer? (This is L1's first decision; your read informs it.)
5. **Open-items completeness (§4):** anything material the arc left open that the doc doesn't list? Any item mis-classified UI-vs-not?
6. **Risks (§6):** the dirty WIP, the `8}]` junk file, `regression_sweep.sh` modified — anything else that could be lost or break a clean-checkout deploy?

## Output format (markdown)
```
## Verdict
<is the takeover accurate? is the 4-lane plan safe to hand to 4 sessions?>
## Accuracy check (§1–§2)
<list: claim | confirmed/refuted | citation>
## Legacy-rule bleed-through I found (the L2 backlog)
<list each: selector | property | which pages it would hit | citation>
## Lane-partition verdict (§5)
<is it disjoint? dependency/sequencing issues? per file>
## dashboard.py WIP refactor — land or shelve?
<what it changes + recommendation + evidence>
## Anything missed / mis-classified
<free text>
```

## STANDING REQUEST — continuous review (Ramana's instruction)
Beyond this brief: **continuously review each of the 4 lanes' commits and improvements** as they land on
`main`. After a lane ships, a follow-up `req-NN` will point you at its commit range; review it for
correctness, regressions, chrome bleed-through, and over-claim, same contract as this brief. The goal is a
running quality gate across the parallel work, not a one-shot review.
