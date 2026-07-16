# §7 owner-decisions brief — plan decisions reserved for Ramana (2026-07-16, S169)

> **TRANSIENT** — retire when: all three of plan §7 items 2/7/8 are ratified (or reversed) and the calls are folded into `docs/patearn-analytics-company-plan.md` §7 + the PROJECT_STATE Decision log. Fold into: `docs/patearn-analytics-company-plan.md` §7.

Decision-ready briefs for the three plan-§7 items the carry-forward has been carrying as open ("Ramana's plan decisions §7.2 / §7.7 / §7.8"). Each was put to two institutional-panel lenses — **Risk / Model-Governance** (SR 11-7 caliber) and **Data-Product / Commercial** (MSCI/Bloomberg-QIS caliber) — per `docs/institutional-panel-assessment.md`. **A machine must not ratify these; this brief only makes them decision-ready.** Nothing in the codebase was changed to produce it.

## TL;DR — the ask

| # | Decision | Panel | Recommendation | Ratify by |
|---|---|---|---|---|
| §7.2 | Auto-analyst (E) monthly LLM cap | both → agree | **₹200/mo** (the default) | one word: "ratify ₹200" (or a different ₹ value) |
| §7.7 | 6 vendor-ToS feeds: 5th licence class vs. keep out | **split** | **B — keep out of FEEDS**, strengthened (see below) | "B" / "A" / "B + the 3 guards" |
| §7.8 | Rule-lab NEW-BENCHMARK → auto-append vs. inbox-first | both → agree | **Ratify inbox-first** (already implemented) | "ratify §7.8" |

---

## §7.2 — E's monthly LLM token cap

**The decision.** E = the auto-analyst that AI-drafts event briefs (grounded only in our own tables, labeled "AI-drafted, human-reviewed", inbox-reviewed before publish). Every LLM component ships a hard monthly cap logged to `cost_ledger` (`cap_status` → OK / AMBER@85% / RED); **at the cap E degrades to deterministic template-text** — no hard failure, no silent stop. Classifier work already moved to Gemini Flash (~13× cheaper than Haiku). Proposed range ₹100–300/mo, default ₹200.

**Panel — both lenses converge on ₹200/mo:**
- *Risk-gov:* with graceful degradation already engineered, the cap is a spend-governance control, not an availability risk; ₹200 gives working headroom over the Gemini-Flash cost base without materially raising exposure. ₹100 risks routine premature degradation for no real saving (the absolute rupees are trivial); ₹300 buys negligible extra coverage for double the ceiling.
- *Data-product:* the LLM brief is a convenience layer over the asset, not the asset; ₹200 funds enough drafting to accelerate human curation throughput (what actually compounds provenance quality) while degradation makes any overshoot a non-event.

**→ RECOMMENDATION: ratify ₹200/mo.** **Guard to attach:** route `cap_status` AMBER@85% and RED to the owner inbox, and revisit the value only after two full months of actuals — the cap stays a *monitored* control, never a silent throttle.

---

## §7.7 — the 6 vendor-ToS legacy feeds

**The decision.** `screener · fundamentals_history · shareholding_history · concalls · news_feed · enrich` are all VENDOR-TOS sources (Screener.in scrapes / vendor compilations / per-source-ToS RSS) that violate Guardrail #8 (primary-sources-only). They sit in `UNCLASSIFIED_FEEDS`, held **out** of the `FEEDS` manifest (a test pins them out); the licence gate keeps RESTRICTED classes `{licensed, personal-broker}` off every public `src/web` surface by construction. Guardrail-#8 remediation is **active**: `fundamentals_xbrl` replaces the fundamentals/screener scrapes, an XBRL path replaces `shareholding_history`, and a BSE-announcement primary-source path replaces the concalls discovery.
- **Option A** — add a 5th licence class `vendor-tos-remediating`, gated off public surfaces like the restricted classes → brings these feeds **into** the manifest (provenance, DQ, auto-docs) while staying off public surfaces.
- **Option B** — keep them **out** of FEEDS until the XBRL/BSE migrations retire them (status quo).

**Panel — genuine split:**
- *Risk-gov → A:* SR 11-7 demands a complete inventory — any source that still touches the system, including in-remediation ones, must sit under provenance/lineage/DQ governance. Under B the six feeds keep operating with no provenance record and only a "pinned-out" test as a fragile negative control; a leak would be undetectable because there is no lineage to trace. *Conditions:* per-feed hard retirement date + a positive CI assertion that no such feed reaches any public surface.
- *Data-product → B:* the manifest is the system-of-record for the buyable asset, and a hard "zero vendor-ToS lineage in the manifest, by construction" invariant is a strictly simpler, more diligence-proof provenance claim to a data buyer than a gated fifth class that normalizes vendor data as a tenant inside the asset. A `vendor-tos-remediating` class quietly becomes permanent, dilutes the clean-by-construction test, and forces provenance/DQ machinery onto exactly the feeds we are about to kill. *Condition:* bring the NSE/BSE/XBRL **replacements** into the manifest with full DQ so remediation stays measurable in-manifest — without importing the vendor originals.

**→ RECOMMENDATION: Option B, strengthened** — keep the vendor originals out of the manifest (the cleaner, diligence-proof provenance story, which is the panel's #1 convergent doctrine: the data IS the product), AND adopt the risk-governance guards so B is not a blind spot. This captures both lenses because both independently agreed on the same replacement handling. **The three guards to attach:**
1. Keep the pinned-out test **and add a positive CI assertion**: no `UNCLASSIFIED_FEEDS` key is referenced by any public `src/web` surface (a positive invariant, not only the negative pin-out).
2. Record a **per-feed hard retirement date** in each `UNCLASSIFIED_FEEDS` note, tied to its XBRL/BSE replacement.
3. Bring the **primary replacements** into `FEEDS` with full DQ coverage, so remediation progress is measurable in-manifest — without importing the vendor originals.

*If you weight complete-inventory over clean-by-construction, choose A instead — the residual risk of B is that the still-running vendor fetchers carry no in-manifest lineage until the guards land.*

---

## §7.8 — rule-lab ledger append

**The decision.** When the rule-lab produces a `NEW-BENCHMARK` verdict, should it **auto-append** to the canonical `docs/strategy-ledger.md`, or land in the Review Inbox for **human approval first**? S157-b already **implemented inbox-first** (canon carries a human signature; `rule_lab_inbox` ships a paste-ready ledger block in the payload; nothing auto-appends), and it was exercised in S163 (the first verdict human-signed into canon). Ratify or reverse.

**Panel — both lenses converge on ratify inbox-first:**
- *Risk-gov:* auto-appending a model's own verdict to canon collapses the segregation between model output and attested record; inbox-first preserves the auditable human signature on the ledger that gates all downstream strategy decisions — exactly the control SR 11-7 requires over self-certifying model loops.
- *Data-product:* the ledger's value is that it carries a human signature; auto-append destroys the human-reviewed provenance guarantee that makes the honesty/rigor story credible to this tier, and a single spurious verdict would silently contaminate the one ledger the whole "sold as data, human-verified" doctrine rests on.

**→ RECOMMENDATION: ratify inbox-first** (no code change — it's already the implemented default). **Guard to attach:** keep it non-blocking — the paste-ready block already makes approval one action; add a review-inbox staleness/SLA alert so an unreviewed verdict is flagged rather than silently backlogged (canon stays current without auto-canonizing).

---

*Provenance: the two panel verdicts were produced this session by independent agents primed with the plan-§7 facts and the panel's convergent DATA-is-the-product doctrine; the recommendations above are the synthesis. Every fact cited is from `docs/patearn-analytics-company-plan.md` §7, `src/automation/feed_manifest.py`, and `src/automation/cost_ledger.py`.*
