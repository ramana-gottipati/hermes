# Lane L4 — Demo Readiness & Edge-Case Hardening (pre-pitch)

> **Session 2026-06-29 (L4 FINAL wave).** A skeptical-prospect walkthrough of every L4 surface +
> an adversarial edge-case probe. Verdict: **the L4 surface is demo-ready** — every path 200s,
> no 500s, the wedge (provenance + Pat-as-analyst) is airtight and descriptive. Two demo rough
> edges found and fixed (`740cd66`). Surfaces: Pat (`/dash/pat`), Strategist (`/dash/strategist`),
> Screen+ (`/dash/screen2`), Provenance evidence (`provenance.{lag_headline,lag_samples,narrative}`).

## 1. Demo dry-run — the prospect walkthrough (in-browser, live VPS)

**A full Pat multi-turn conversation** (the `pat_tid` cookie is live):
1. "tell me about TITAN" → the single-name dossier (delivery / RS / fundamentals).
2. "what about its credibility?" → resolves "its" → TITAN → "TITAN reads CREDIBLE composite 67/100
   tier B, 23 promises 91.3% kept" + the receipts + provenance footer.
3. "is it being accumulated?" → resolves → TITAN → **the per-name MEP read** ("TITAN is in
   CONSOLIDATION — delivery character NEUTRAL · positioning p/r 0/0") — NOT the generic screen
   (this was the rough edge; fixed).
4. "top 5 credible managements" → exactly 5 ranked rows ("CREDIBILITY LEADERS — TOP 5") + footer.
5. "start over" (`?new=1`) → the thread clears, back to the fresh home.

Every turn carries: the "THIS CONVERSATION" trail, the pronoun-resolution note, raw values beside
the verdict, a provenance footer, "Ask next ↳" lens chips, and the 👍/👎 + save-board affordances.

**Strategist board:** the at-a-glance strip (10 strategies · universe · bhav/MEP as-of), the
confluence-alerts strip, **What changed** (▲new/▽dropped per strategy, or "No membership changes"
honestly), the **Credibility RRG · divergence** tile (806 names, descriptive map), and 10 strategy
cards (count · freshness · top names · deep-link). Toggles persist. CSV exports.

**Screen+:** the confluence superset (DVPT×MEP×RS×CPR×CCI×Wolfe, 0-6) + Quality·pt14, group toggles,
saved screens, CSV, Pat bridge; `/dash/screen2?parity=1` proves promotability (8/8 families) + the
promotion checklist (9/10; the 10th is the orchestrator's nav flip).

**Provenance evidence (the lead wedge):** `provenance_narrative()` →
> "Effective look-ahead leak **1.42%** (vs 11.9% on the naive +90/+50d model — an **8.4× cut**), over
> 29,176 matched periods." + the 3-beat story (what we model · how we de-model · the proof) + the
> worst-case receipt (ATLASCYCLE +659d would-leak) + a conservative receipt (FINPIPE −398d).

## 2. Edge-case probe — NO 500s (39 adversarial cases, all 200)

Ran an adversarial probe against the live VPS. **Result: 39/39 → 200, zero non-200, zero 500s.**
Every path degrades gracefully to an intentional empty/error/boundary state:

| Category | Cases | Result |
|---|---|---|
| Empty / whitespace / nonsense queries | 3 | graceful (home / glossary nudge) |
| Unknown symbol / no-data name (card/why/trend) | 4 | "couldn't resolve" / "no series yet" |
| Absurd / negative / zero top-N | 3 | clamped (1..200) |
| SQL injection / XSS in query | 2 | bound params + `_esc` (closed-vocab, can't escape) |
| OOD advisory / buy ("should i buy", "target price") | 2 | SEBI boundary redirect, never a screen |
| Follow-up with no thread / forged·oversized `pat_tid` | + | inert (regex-validated, rejected) |
| Concurrent threads | + | isolated (no bleed) |
| Unknown flow / scope / explain term | 3 | graceful default |
| Strategist bad `fmt` · 0-name strategy | 2 | CSV ignores · card shows "Open the lens" |
| Screen+ bad / out-of-range `limit` | 3 | **clamped** (was a raw 422 → fixed `740cd66`) |
| Screen+ injection scope · empty saved-screen | 2 | empty result, no SQL error |

**Two fixes shipped** (`740cd66`):
- **Single-name accumulation/RS follow-up** routed to the generic screen, not the name → now the
  per-name `why` evidence ("why is X being accumulated" → `why(metric=accumulation)`).
- **`/dash/screen2?limit=…`** out-of-range returned a raw 422 → `limit` is now a clamped str
  param (50..2000, bad → 600) so the screener always renders.

**Forged-tid security:** `threads._TID_OK` (`^[0-9a-f]{8,40}$`) rejects path-traversal, SQL, XSS,
and oversized tids → `last_symbol`/`history` return empty, render stays inert. No injection surface
(the tid is server-minted uuid4, never reflected unescaped, SQL-bound).

## 3. SEBI / advisory safety (descriptive-only, airtight)

- **7/7 OOD asks redirect** to a boundary clarify (should-i-buy · target-price · will-go-up ·
  recommend-portfolio · stock-tip · good-investment · will-double) — e.g. "should i buy RELIANCE" →
  *"I don't give buy/sell advice — I'm a screening tool, not a SEBI-registered adviser. I can show
  you the data to decide for yourself"* + descriptive alternatives.
- **Every credibility answer carries the provenance + descriptive footer** ("source: concall
  track-record · descriptive evidence · not a recommendation"; leaders "inform but never rank").
- **Zero buy/sell/target verbs** in any rendered answer (grep + live probe both clean).
- **§C falsification + the 1/806-delisted survivorship limit stand** — credibility is framed as a
  research map / descriptive track record, never a ranked alpha signal.

## 4. Verification matrix

| Surface | In-browser | Research / data | Gates |
|---|---|---|---|
| Pat multi-turn (single→its-credibility→accumulation→top-5→reset) | ✓ screenshots | eval 31/31 · route 63/64 · TREND 15/15 | ✓ |
| Pat SEBI boundary (should-i-buy) | ✓ screenshot | OOD 7/7 redirect · HALLUC 8/8 | ✓ |
| Strategist board (strip · what-changed · CCI tile · cards) | ✓ screenshot | — | ✓ |
| Screen+ parity + promotion checklist | ✓ (W2/W3) | parity 8/8 families | ✓ |
| Provenance evidence (headline · receipts · narrative) | — (orchestrator coverage 1-liner) | `lag_audit` 29,176 · effective 1.42% · `narrative` live | ✓ |
| Edge cases (39 adversarial) | — | **39/39 → 200, zero 500s** | ✓ |
| VPS research selftests | — | provenance · cci_rrg · threads all OK | ✓ |

`regression_sweep.sh` + `chrome_gate.py` PASS before every commit (31 routes + 5 overlays 200).
VPS eval incl. **ACCURACY 10/10** against real data.

## 5. Final-wave commits
| Commit | What |
|---|---|
| `740cd66` | demo hardening — single-name follow-ups → per-name evidence + clamp screen2 limit |
| `741cf5f` | `provenance_narrative()` — the tight, CFA-auditable zero-look-ahead story |

## 6. Residual (orchestrator-owned, not L4)
- Render `provenance_narrative()`/`lag_headline`/`lag_samples` on the Coverage page (1-liner in the
  non-owned `coverage_view.py`; data + helpers shipped in `provenance.py`).
- Promote Screen+ to the default Screener (the `lens_registry` nav slot; readiness proven 9/10).

**Verdict: L4 is demo-ready and bulletproof.** No further hardening needed; the wedge is airtight.
