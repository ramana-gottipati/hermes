# Strategy Origins — who created what (canonical provenance map)

> **Class:** CANONICAL (permanent — do not archive). **Created:** 2026-07-14 (S132j, Ramana's
> directive: *"I need to be able to tell whether a strategy is one I created, a proprietary
> strategy, or a standard (regular) strategy — the distinction should be clear."*
>
> **The three origin classes (BINDING vocabulary):**
> - 🧑 **RAMANA** — Ramana's own concept, dictated by him (the house implemented and tested it).
> - 🏠 **HOUSE** — proprietary, patearn-built: designed inside this project, not public knowledge.
> - 📚 **CLASSIC** — standard/"bookish": public-domain families from the literature, admitted
>   only after re-proving themselves on our own data.
> Mixed lineage is stated explicitly (e.g. "classic base + Ramana layer") — never blurred.
>
> **Labeling rule (BINDING):** every page in `docs/strategies/` declares `**Origin:**` in its
> header; every surface that shows a strategy's output states the origin class in its fence
> line. New strategies may not ship without the label.

## The map

| Strategy / construct | Origin | Where it lives | Status |
|---|---|---|---|
| **DVPT positioning** (delivery-value-per-trade, power baselines, key price, ×power) | 🧑 RAMANA (concept) + 🏠 implementation | /dash/stocks · screener "pos" group | live, descriptive |
| **MEP** (signed accumulation/distribution) | 🧑 RAMANA doctrine + 🏠 model | /dash/mep | live; descriptor-only (D62) |
| **Wolfe waves** | 📚 CLASSIC base (Bill Wolfe) + 🧑 RAMANA §B strength rebalance & fractal gate | /dash/wolfe/scan + trades | live; BULL selection edge OOS-validated; book rejected |
| **CPR structure pillar** | 📚 CLASSIC base (pivot-range school) + 🏠 multi-TF amplification | /dash/cpr | live, descriptive |
| **Relative Strength suite** (RRG · RS-band · rotation · Mansfield · capture · size-index) | 📚 CLASSIC families (RRG — de Kempenaer · Mansfield/Weinstein RS · rotation) + 🏠 measurement | /dash/rrg · rotation · rsband · capture-map | live, descriptive |
| **Harmonic** (XABCD / PRZ) | 📚 CLASSIC (Gartley/Carney) + 🏠 PIT detector | /dash/harmonic | live, descriptive · backtest-gated |
| **STREAM BAND** (13-EMA banks + 5-EMA trigger) | 🧑 RAMANA | Screen+ "rev" group (band state · stretch pctile) | falsified as signal (ledger 07-13); live as context |
| **FRACTAL FLOOR / CEILING** | 🧑 RAMANA | Screen+ "rev" group + reclaim/slip pills | falsified as entry (07-14…14c); live as risk-geometry context |
| **Buyback tender quota play** | 🧑 RAMANA (charter §2.4) | /dash/buyback-calc | live, personal-scale |
| **The Union** (RS turn ∪ RS trend, stock-level) | 🧑 RAMANA (both signal theses — oversold-RS turn + persistent RS; cash-out sizing) + 🏠 HOUSE (union construction, PIT harness, falsification + pre-registration) | `docs/strategies/union.md` (no live surface by design) | RESEARCH — pre-registered lead, SEALED, not deployed |
| **pt14 quality** (14-pattern durability) | 🏠 HOUSE | /dash/stocks · screener "qual" | live; filter/veto, not a ranker |
| **CCI credibility** (concall guidance-accuracy) | 🏠 HOUSE | /dash/concalls · screener "cci" | live; factor falsified → descriptive/veto |
| **C capital-allocation** | 🏠 HOUSE | screener "ca" · /dash/momentum-scan C-blend | live; blend/veto (D66), never a ranker |
| **Conviction shortlist** (cross-pillar synthesis) | 🏠 HOUSE | /dash/conviction | live |
| **Launchpad** (momentum + contracting vol screen) | 🏠 HOUSE | /dash/launchpad | validated screen; no fundable edge net |
| **Seasonal tape** (certification-gated calendar residuals) | 🏠 HOUSE (framework) | /dash/seasonal-tape | live; 0-certified IS the finding |
| **Reversal context columns** (implementation) | 🧑 RAMANA concepts + 🏠 honesty fences | Screen+ | live, descriptive |
| **Sector Rotation** (V8 champion · V17 defensive-fill candidate) | 🧑 RAMANA (concept + every lever) + 🏠 implementation/harness | research modules (`sector_rotation*`); page [sector-rotation.md](sector-rotation.md) | research, CONDITIONAL; long-only |
| **SPRINTER-25** (MOM12) | 📚 CLASSIC (Jegadeesh-Titman 12-mo momentum) | /dash/model-portfolios | model portfolio since 2012 |
| **PACER-25** (RISKADJ) | 📚 CLASSIC (vol-adjusted momentum school) | /dash/model-portfolios | model portfolio since 2012 |
| **CRAFTSMAN-25** (QUAL_MOM) | 📚 CLASSIC blend, 🏠 delivery-leg formulation | /dash/model-portfolios | model portfolio since 2012 |
| **STEADY-25** (LOWVOL_MOM quarterly) | 📚 CLASSIC (low-vol + momentum, "conservative formula") | /dash/model-portfolios + /dash/momentum-scan/slow | model portfolio; NET champion |
| **Momentum / RISKADJ engine** (the benchmark ranker) | 📚 CLASSIC (Jegadeesh-Titman · vol-adjusted momentum) + 🏠 measurement | /dash/momentum-scan | live; gross benchmark, not fundable net of cost |
| **Factor league** (families ranked incl. failures) | 📚 CLASSIC content, 🏠 measurement | /dash/factor-league | live |
| **Value / deep value / quality-standalone / deliv-mom rows** | 📚 CLASSIC | factor league (verdict rows) | FAILED/REJECTED on our data — shown with numbers |
| **Classic screens catalog** (in flight, sibling lane) | 📚 CLASSIC | /dash/classics (when it lands) | building |

## External sources — the standing policy

**Methodology from outside is welcome; data from outside is not.** Encoding a public, "bookish"
strategy from books/papers is exactly how the CLASSIC class grows — but every such strategy must
(1) be implemented from primary-source NSE/BSE data only (CLAUDE.md guardrail #8 — no vendor
feeds), (2) pass the standard exam (walk-forward vs the 0.89 hurdle + cost realism) before any
portfolio treatment, and (3) carry its 📚 label and its measured verdict — including failures
(value's negative alpha stays on the league page precisely because it is a classic).

## Documentation loop (Ramana's directive, BINDING)

Every strategy discussion — wins, failures, refinements, dictated rules — lands in that
strategy's `docs/strategies/` page (or the ledger for results) in the SAME session it happens.
Nothing lives only in chat. The loop: **discuss → document → implement per the doc → test →
record the verdict in the ledger → update the page's status.** This file is the provenance
index over that loop.
