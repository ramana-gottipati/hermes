# Codex review — v3 experience prototype (2026-07-23)

Reviewer: Codex (gpt-5.5, `codex exec --dangerously-bypass-approvals-and-sandbox`, review-only).
Subject: `scratchpad/v3-experience-prototype.html` — the from-scratch v3 EXPERIENCE prototype
(Graphite palette · Beginner⇄Pro personas · living floating Pat · animated field + ticker).
Pre-build, standalone HTML (not wired into `src/`). Full raw output (1.2MB with reasoning trace)
in the session tool-results; this file is the distilled verdict + findings + dispositions.

## `VERDICT: OBJECT` — 8 BLOCKING + 2 ADVISORY

| # | Sev | Finding (Codex) | Disposition |
|---|---|---|---|
| 1 | BLOCKING | Colour doctrine violated — `--up`/green reused for non-signed states: `.chip.up` "DVPT fired"; RRG leading/lagging dots + quadrant fills use `--up`/`--down`/`--warn`. | **ACCEPTED — FIXED in prototype.** State/rank chips → neutral (accent dot); RRG dots + quadrant tints → accent (present) / `--ink3` (muted), position carries leading↔lagging. `--up/--down` now only signed deltas. Binding for the build. |
| 2 | BLOCKING | Fence too weak/late + action/hype copy ("want to peek?", "Strongest today", "sound enough to look closer"). | **ACCEPTED — FIXED in prototype.** Above-the-fold `.fence-top` added before the first cluster; Pat bubbles → past-tense observations; "Strongest today"→"Highest composite rank today"; quality copy → "says nothing about price or timing". |
| 3 | BLOCKING | Beginner/Pro mechanic superficial — CSS visibility + canned suggestions only; beginner still sees raw RS/DVPT/pt14/CONVICTION/leading; Pro = one static table, fake `href="#"`, no sort/filter/export/evidence. | **ACCEPTED as BUILD REQUIREMENT.** Beginner = plain-label-first everywhere + glossary chips on every code + a first-read path; Pro = real dense controls (sort/filter/export), evidence links, explicit ranking basis, keyboard-complete. The prototype demonstrates the *switch*; the real module implements the depth. |
| 4 | BLOCKING | Pat dialog not accessible — `role="dialog"` without `aria-modal`/labelling/focus handoff/Escape/return/trap; closed state CSS-only so descendants stay tabbable. | **ACCEPTED as BUILD REQUIREMENT.** Real Pat: focus input on open, return to FAB on close, Escape, `inert`/`aria-hidden` when closed, `aria-modal` + labelled-by. |
| 5 | BLOCKING | Keyboard semantics incomplete — persona `role="tab"` w/o arrow-keys/`aria-controls`; range buttons no state; nav anchors no `href`. | **ACCEPTED as BUILD REQUIREMENT.** Persona → segmented `button`+`aria-pressed`; real routes on nav; real state on range controls (these are live in the actual modules, not a mock). |
| 6 | BLOCKING | Duplicate SVG `id="pg"` injected twice. | **ACCEPTED — FIXED in prototype.** `avatar(n)` mints `pg0`/`pg1`. |
| 7 | BLOCKING | Unsafe `innerHTML` string assembly — injection risk once wired to live data. | **ACCEPTED as BUILD REQUIREMENT.** Real modules build DOM with `textContent` for data + escape/whitelist; SVG behind trusted static helpers (mirrors the existing `news_view._safe_url` discipline). |
| 8 | BLOCKING | Reduced-motion still draws the ambient canvas once (implied-movement cues). | **ACCEPTED — FIXED in prototype.** RM now renders no ambient field at all. |
| 9 | ADVISORY | Light candle-down `#93a2b8` on white ≈ 2.59:1 — below AA for graphical meaning. | **FLAGGED TO OWNER.** This is the owner's light-theme candle directive (2026-07-22). Options: darken the light candle-down, or add a darker outline for the ≥3:1 graphical-contrast floor. Owner decision. |
| 10 | ADVISORY | Much liveliness is decorative, not comprehension-bearing (ambient blobs, bob/blink, bubbles, hover lift). | **PRINCIPLE ACCEPTED — tension noted.** The owner explicitly asked for "intensely futuristic & lively"; Codex (doctrine) says motion must be earned. Resolution for the build: KEEP energy but BIND it to data — freshness pulses, provenance reveals, drill-expansion motion, live-update flashes — and quiet motion that only signals "futuristic". Surfaced to the owner. |

## Notes
- Findings 1/2/6/8 fixed in the prototype same-session (republished, same artifact URL).
- Findings 3/4/5/7 are genuine BUILD requirements — they need live routes, real data, and real
  focus management that a static direction-sample can't carry; they become acceptance criteria in
  the identity/experience module spec.
- Finding 9 is an owner-directive-vs-AA conflict (not a session-side fix).
- Finding 10 is the core owner-ask (lively) vs doctrine (earned) tension — resolution recorded above.
