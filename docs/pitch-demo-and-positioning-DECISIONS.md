# Patearn — Pitch demo & positioning DECISIONS (2026-06-29)

> **Status: DECIDED** (delegated to the builder; "treat these as your calls"). Four positioning/design
> calls for the institutional (PMS/AIF/family-office/bank) pitch. Grounded in the binding §9 red-team
> verdict in `docs/product-strategy-2026.md` ("earn the trust before you sell it"), the already-built
> trust spine (`provenance.py` + `coverage_view.py` + `/v1`, held for acceptance), the Lane A2
> institutional design foundation (`ui_tokens.py`/`ui_components.py`), and the runtime-wrap → native
> migration reality (`v2_surfaces`/`shell_skin`).
>
> Companion: `docs/product-strategy-2026.md` (strategy/§9), `docs/ui-architecture-v2.md` (IA),
> `docs/navigation-and-structure-review.md` (Scope×Lens + the registry fix), `docs/replay-the-tape.html`.
>
> These supersede nothing; they are net-new positioning calls. Fold into PROJECT_STATE § Decision log as
> **D-PITCH-1…4** at next commit (binding update rule).

---

## D-PITCH-1 — Trust-as-front-door demo path
**The demo opens on Coverage/Provenance, never on a leaderboard or any screen that implies a buy/sell edge.**
Forced by the §9 pivot: the CCI alpha wedge was falsified; the surviving wedge is *audit-grade provenance
+ descriptive credibility + multi-lens confluence*. The front door is the honesty machinery.

Path (descend, never backtrack):
1. `/dash/coverage` = demo home — coverage funnel (touched→scored→≥3→≥10), tier×n cross-tab (self-incriminates thin samples), spend-cap pause banner shown openly, survivorship policy. Volunteering limits = the credibility move.
2. Provenance basis legend — every cell as-traded/modeled/derived; "modeled-availability, not PIT" stated plainly; per-class registry (`/v1/provenance/registry`).
3. Replay the Tape (`docs/replay-the-tape.html`, ALKYLAMINE/TANLA) — scrub to a past date; zero look-ahead.
4. *Only then* descend into a single name's evidence.

Operational, not new build: deploy `coverage_view` + replay-the-tape behind a demo flag as the entry (both already built + held for acceptance).

## D-PITCH-2 — Visual restraint for banks
The Lane A2 institutional foundation **is** the restraint; suppress the Tier-2 "proprietary visuals (the
brand)" gimmickry for the bank build.
- Ink-on-paper base, one accent. Semantic color reserved for the green/red value contract only — and **fix the Rotation blue=bull/amber=bear clash** (§6 audit; one color contract site-wide).
- No decorative motion in the demo — kill animated RS comet-tails + any glow. Keep only micro-viz that *carries data* (DVPT ladder, accum/distrib bar, heat-strip) — data-first, not decoration.
- No radar "area = conviction" (§9.7 quant red-flag). If shown: 4 evidence families + composite + dispersion + dissent. Never a filled area.
- Default to the dense/light density token; tabular numerals; raw values beside every verdict.

Doctrine: *serious, not gimmicky; tables + provenance lead, signature visuals stay backstage for banks.*

## D-PITCH-3 — Native-page migration order
Migrate off the runtime-wrap (`v2_surfaces`/`shell_skin`) trust-first, risk-last:
1. **Lens/nav registry first** (nav-review patterns #1+#5) — single source for nav + links + dossier tabs + screener columns; every later native page self-places, links can't drift. Foundation before pages.
2. **Trust surfaces native** — coverage / provenance / `/v1` faces (already isolated; 1-line `main.py` include). Lowest risk, highest demo value, matches the front door.
3. **Stock dossier** — convergence hub; ship `stock_link(sym, lens)` + `#lens` deep-linking (land on the lens clicked).
4. **Markets ▸ Rotation** — rrg/rotation/rsband under one strip; de-orphan rsband.
5. **Screener last** — highest risk (virtualizer + colgroup widths); keep runtime-wrapped until all else native.
6. **Chrome cut-over last of all** — retire `shell_skin` runtime wrap → native `_shell` once `dashboard.py` frees. Only step gated on parallel sessions.

## D-PITCH-4 — Linear demo script (6 beats, no dead ends)
1. **Trust & Coverage** — "exactly what we cover and what we don't" (funnel, pause banner, survivorship).
2. **Provenance** — audit any number's basis + knowable-at date; modeled vs filed, color-coded.
3. **Replay the Tape** — hero name, scrub to a past date, zero look-ahead.
4. **One name in confluence** — dossier: Promise→Outcome credibility ledger (descriptive: hit-rate + n + strong/mixed/weak/**unproven**, *never* A+/grades) with MEP/RS/structure stacking. "No single lens claims alpha; evidence stacks."
5. **Screener as 'all lenses at once'** — *now* the buyer types their **own** ticker / filters their universe; columns are descriptive context; **must degrade gracefully + show coverage** on a buyer-chosen name (§9.1 binding).
6. **Two-buyer close** — PM gets the shortlist; compliance gets export-to-IC-memo + signed PIT dossier; end on `/v1` "one bus, four faces" as the data-feed expansion.
</content>
</invoke>
