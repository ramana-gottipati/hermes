# M6 — THE GUIDED JOURNEY (contextual, tourless) · module specification for owner review

> **Lifecycle: TRANSIENT** — retire when: M6 ships and its landing record folds into
> `docs/redesign-coordination.md` §5; then `git rm`. Fold into: `docs/redesign-coordination.md`.

**Status: SPEC v1.1 — no code. Built only on explicit owner go.** Codex pre-build review:
`VERDICT: APPROVE-WITH-CHANGES` — 2 BLOCKING accepted and fixed in this revision (the
empty-state contract enforced at the COMPONENT level across all v3 empties; the migration
inventory corrected) + 2 ADVISORY folded (structural tour-ban checks; the "track" persona exit
verified). Dispositions: `docs/redesign-coordination.md` §2.
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
3. **TEACHING EMPTY STATES (contract, not copy — Codex B1/B2 form).** A shared
   `C.empty(why, href, label)` component that REQUIRES a why-clause AND exactly one action
   (both mandatory arguments — the component itself enforces the invariant; a bare "no data"
   cannot be constructed). Migration inventory (corrected): `news_dock._empty` (all channels) ·
   the hub's real section-empty returns + the miss page + the context-rail "No context data
   yet" · Today's warm-up + what-changed empties · the chart section's no-tape empties
   (`stock_chart_v3`). NOT migrated: hub `_collapsed` (a lazy closed-section renderer with an
   "Open section" action — not an empty state). Test: source-level — every `C.empty(` call
   site passes non-empty why + href + label; render-level — no legacy bare-empty markup
   remains in v3 output.
4. **PER-PERSONA EXITS (verification only, no new UI).** The §E exits already exist (newcomer →
   reading-guide, analyst → Proof links, skeptic → validation record on every teach card,
   **tracker → the Tracker destination in the fixed bar** — Codex A4); M6's test file asserts
   all FOUR are reachable from BOTH Today and the hub in ≤1 click (the destination bar
   satisfies the track exit; asserted, not assumed).

**Non-goals:** NO multi-step tour (banned by the ratified evidence — a test asserts no
tour markers ever appear) · no Pat changes · no new data · no cut-over.

## 2. Files

| File | Contents |
|---|---|
| `src/web/journey_v3.py` (NEW) | the nudge: `assets()` (CSS + the one-shot localStorage JS) + `nudge_html(anchor_selector)`; pure presentation, zero DB |
| `src/web/ui_components_v3.py` (edit, v3-owned) | `empty(why, href, label)` — ALL arguments mandatory (the component enforces the teaching contract) |
| `src/web/shell_v3.py` (edit, v3-owned) | the "New here? How to read →" control in the fixed top-bar slot |
| `src/web/stock_hub_v3.py` (edit, v3-owned) | includes `journey_v3.assets()` + the nudge after the digest |
| v3 empty-state call sites (edits, all v3-owned) | migrate to `C.empty` per the §1.3 corrected inventory (dock channels · hub section-empties/miss/context-rail · Today warm-up + what-changed · chart no-tape) — `_collapsed` excluded |
| `tests/test_v3_journey.py` (NEW) | nudge present on hub + one-shot mechanics in markup · absent from legacy AND from Today · help control same slot on Today/hub/showcase · the C.empty contract (source-level: every call passes why+href+label; render-level: no bare empties) · **structural tour-ban (Codex A3): no backdrop/dimming element, no focus trap, no body-scroll lock, no multi-step state beyond `pv3nudge=done`, no "next" control** + the string markers (`data-tour`, `step 1 of`, `Next →`) · per-persona exits incl. Tracker reachable ≤1 click from Today + hub |

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
