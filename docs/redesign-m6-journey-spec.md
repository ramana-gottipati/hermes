# M6 — THE GUIDED JOURNEY (contextual, tourless) · module specification for owner review

> **Lifecycle: TRANSIENT** — retire when: M6 ships and its landing record folds into
> `docs/redesign-coordination.md` §5; then `git rm`. Fold into: `docs/redesign-coordination.md`.

**Status: SPEC v1.0 — no code. Built only on explicit owner go, after the Codex review loop.**
Inputs: Part II §E as RATIFIED — the evidence there is one-sided (NN/g n=70: upfront tours made
apps feel HARDER; skippers rated them easier) — so Part I's original "coach-mark journey"
was already revised to: **one one-shot nudge · contextual pull-help · teaching empty states ·
a persistent help affordance**. M6 builds exactly that, nothing more. The five-step arc
(understand → search → learn → form your view → track) is delivered by STRUCTURE (M5's Today +
M4's hub already carry steps 1–2 and 4–5); M6 adds the "learn" trigger and the standing help.
**Zero new tables, zero new routes, zero new timers; ~zero payload.**

## 1. Scope — four small pieces

1. **THE ONE-SHOT NUDGE (the "learn" trigger).** On a visitor's FIRST-ever view of the stock
   hub, one small dismissible callout anchored to the first term chip in the digest:
   *"Every dotted term explains itself — tap one."* Rules (all evidence-backed):
   - ONE nudge, ONE time, EVER (`localStorage pv3nudge=done` set on dismiss or on any chip tap).
   - Never blocks anything: no overlay, no dimming, no "next" — a single floating tip with ×.
   - Dismissed by: the ×, Esc, tapping any chip, or scrolling past the digest.
   - Renders only when chips exist on the page; never on legacy pages; never a second step.
   - `prefers-reduced-motion` honored (no pulse animation for those users).
2. **THE PERSISTENT HELP AFFORDANCE.** One "New here? How to read →" control in the SAME
   position on every v3 page (the shell top bar, before Skin/Theme), linking
   `/dash/reading-guide`. Same label, same slot, site-wide — position consistency IS the
   feature (NN/g: help must be dismissible and retrievable later, in a standing place).
3. **TEACHING EMPTY STATES (contract, not copy).** A shared `C.empty(message, href, label)`
   component: every v3 empty state must explain WHY it's empty and offer ONE next action.
   Migrate the existing v3 empty states (dock channels · hub sections · Today tiles warm-up ·
   miss page) to it. Test: every `pv3-dock-empty` in v3 output carries either a link or a
   why-clause — a bare "no data" becomes a build failure.
4. **PER-PERSONA EXITS (verification only, no new UI).** The §E exits already exist (newcomer →
   reading-guide, analyst → Proof links, skeptic → validation record on every teach card);
   M6's test file asserts they are reachable from BOTH Today and the hub in ≤1 click.

**Non-goals:** NO multi-step tour (banned by the ratified evidence — a test asserts no
tour markers ever appear) · no Pat changes · no new data · no cut-over.

## 2. Files

| File | Contents |
|---|---|
| `src/web/journey_v3.py` (NEW) | the nudge: `assets()` (CSS + the one-shot localStorage JS) + `nudge_html(anchor_selector)`; pure presentation, zero DB |
| `src/web/ui_components_v3.py` (edit, v3-owned) | `empty(message, href="", label="")` — the teaching-empty-state component |
| `src/web/shell_v3.py` (edit, v3-owned) | the "New here? How to read →" control in the fixed top-bar slot |
| `src/web/stock_hub_v3.py` (edit, v3-owned) | includes `journey_v3.assets()` + the nudge after the digest |
| v3 empty-state call sites (edits, all v3-owned) | migrate to `C.empty` (dock channels · hub `_collapsed`/miss · Today warm-up) |
| `tests/test_v3_journey.py` (NEW) | nudge present on hub + one-shot mechanics in markup · absent from legacy AND from Today (it belongs where chips live) · help control same slot on Today/hub/showcase · every v3 empty state teaches (link or why-clause) · NO tour markers (`data-tour`, `step 1 of`, `Next →`) anywhere in v3 output · per-persona exits reachable ≤1 click from Today + hub |

## 3. Verification

Suite + the M6 file → local walk (cold-profile check: nudge appears once, never again) →
Codex post-build loop → deploy (writer-safe recipe) → box walk: nudge markup on the hub ·
help control on all v3 pages · empty-state sweep (force one empty channel via a nonsense
`?sym=`) · 0 legacy leak · public 200.

## 4. Owner decisions at review (defaults ship)

1. Nudge copy (*"Every dotted term explains itself — tap one."*).
2. Help label (*"New here? How to read →"*) and its top-bar slot.
3. Whether the nudge ALSO appears on Today's first visit (default: NO — it belongs beside the
   chips, and Today already orients; one nudge in one place, per the evidence).
