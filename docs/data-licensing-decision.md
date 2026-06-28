# Data licensing — decision & migration plan

> **Status: DECIDED — proceed, do not block.** Lane H, 2026-06-28. Formalises the standing call
> (Ramana, recorded in [[product-strategy-b2b]] / `docs/product-strategy-2026.md` §9 #9 and the
> 06-26 line: *"owned/properly-licensed Indian feeds at the pre-pitch backend rewrite — keep
> building the foundation now"*). This doc turns that one-liner into a per-data-class map + the
> triggers, so a future session (or a compliance reviewer) has the complete picture.
> Owner of the linkage: `provenance.py` (its `PROVENANCE` registry already stamps `source` per
> class, so the migration is an auditable per-class source swap, not a rewrite).

---

## 1. The decision (TL;DR)

1. **Build now on the current (largely scraped) sources.** They are fit for **internal research +
   foundation-building**, and every value is already **provenance-stamped** (`provenance.py`) with
   its source and a modeled/real availability basis. Development does **not** block on licensing.
2. **Do not redistribute scraped third-party data externally.** The risk is **distribution to
   institutions**, not internal computation. Today there is **no external B2B distribution**, so we
   are inside the safe envelope.
3. **Migrate the redistribution-sensitive feeds to owned/properly-licensed sources BEFORE the first
   external pitch / pilot** (the "pre-pitch backend rewrite"). This is a per-data-class swap, not a
   re-architecture — the `/v1` "one bus, four faces" layer + the provenance registry are designed
   exactly so the source can change underneath without touching consumers.
4. **What we own regardless of feed:** all **derived analytics** (CCI credibility, MEP/flow, RS,
   Wolfe, and the **provenance / `knowable_at` calibration itself**) are **our IP**, computed from
   inputs. The provenance layer is not a cost centre — it is the **compliance asset** that makes the
   audit/PIT-honesty tier sellable.

---

## 2. The honest interim caveat (carry it on every surface)

> The current research dataset is assembled in part from **publicly-scraped sources (Screener.in,
> exchange websites)** under their respective terms of use. It is **safe for internal research and
> product development**. **External distribution to clients (B2B) requires licensed/owned feeds and
> a compliance review** — and is gated until the Phase-1 migration below is complete.

This mirrors the SEBI-RA / defamation line already in `docs/concall-intelligence-design.md` §15
("internal-research-safe; B2B distribution needs a compliance review"). Because `provenance.py`
embeds the `source` and basis **inside** every stamp's display string (the red-team's
no-silent-strip rule), a downstream SDK/MCP/LLM consumer **cannot** quietly drop the caveat.

---

## 3. Per-data-class map (current source → redistribution status → target licensed source)

Redistribution status: **PUBLIC-RECORD** = an exchange disclosure / official file (lowest risk —
resale still needs the exchange's data-redistribution licence but it is *our* compiled use of a
public record); **VENDOR-TOS** = scraped from a vendor whose ToS restricts redistribution (the real
gap); **OWNED** = computed by us (our IP).

| data_class (provenance) | Current source | Status | Target licensed/owned source (Phase 1+) |
|---|---|---|---|
| `bhav_eq`, `index`, `fno`, `participant_oi`, `fii_dii_flows` | NSE/BSE bhav copy + participant files | PUBLIC-RECORD | **NSE Data Services / BSE data feed** redistribution licence (paid) |
| `fundamentals_history` | **Screener.in scrape** | **VENDOR-TOS** | Exchange **XBRL financials** (own the parse) **or** a licensed vendor (CMIE Prowess / Accord Fintech / Trendlyne / Tickertape API / Refinitiv-LSEG) |
| `shareholding_history` | **Screener.in scrape** | **VENDOR-TOS** → underlying is PUBLIC-RECORD | Exchange **shareholding-pattern (SHP)** filings direct (public) |
| `knowable_at` filing dates | **BSE corporate announcements** (`AnnSubCategoryGetData`) | **PUBLIC-RECORD** (exchange disclosure) | Same — BSE/NSE announcements are official disclosures; **safest class, no change needed** |
| concall transcripts → `concall_*`, `cci_*` | BSE/issuer-IR PDFs; **index via Screener** | PDFs PUBLIC-RECORD; **index VENDOR-TOS** | Discover filings directly via **BSE/NSE announcements** (the BSE-announcements adapter, already scoped in [[cci-credibility-timeseries]]) or a licensed transcript vendor (AlphaSense/Trendlyne). Extraction is OWNED. |
| `news_*` | RSS / news sites | per-source ToS | Licensed news API (e.g. NewsAPI/× vendor) for any redistributed headline |
| CCI / MEP / RS / Wolfe / provenance / calibration | computed by us | **OWNED** | unchanged — our IP |

**Key insight from the knowable_at work (Lane D/H):** the single most compliance-sensitive PIT
claim — *"as of when was this number knowable?"* — is now sourced from **BSE's official corporate
announcements (public record)**, not a vendor compilation. So the **provenance backbone is already
on the safest possible footing**; the migration burden is concentrated on `fundamentals_history`
and the concall **index** (the transcript PDFs and filing dates are exchange public record).

---

## 4. Phased plan + triggers

**Phase 0 — NOW (internal foundation). Active.**
- Scraped sources permitted for internal research + building. No external redistribution.
- Mandatory: every value provenance-stamped; the §2 caveat on any research artefact that could
  leave the building (decks, dossiers, exports).
- Polite scraping only (paced, UA-identified) — already the house pattern.

**Phase 1 — PRE-PITCH (first external pilot / paid seat). Trigger: any data leaves to a client.**
- Swap the **VENDOR-TOS** rows above to a licensed/owned equivalent, **class by class** (the
  provenance registry's `source` field is the checklist). Priority order:
  1. `fundamentals_history` → licensed vendor or exchange XBRL (highest exposure, highest value).
  2. concall **index** → the BSE/NSE-announcements adapter (de-Screener the discovery path; the
     PDFs + extraction are already ours/public).
  3. `shareholding_history` → exchange SHP filings.
- Prices/F&O: obtain the **NSE/BSE redistribution licence** before any feed/API tier ships.
- Add the **licence/redistribution status to each `ProvenanceDescriptor`** (a one-field extension)
  so `/v1` can refuse to serve a not-yet-licensed class to an external scope. (Hook, not built yet —
  recorded as the Phase-1 provenance task.)

**Phase 2 — SCALE (SaaS / data-feed / white-label). Trigger: multi-client GA.**
- Full licensed stack + the operational gates from §9 #9: **SLA, HA/DR (today: single-node, no HA —
  disclosed in the coverage freshness panel), SOC 2**. These gate the *sale*, not the build.

---

## 5. Why this is safe to proceed on now

- **No external distribution exists yet** → we are inside the internal-use envelope of every source.
- **The architecture was built for the swap:** `/v1` (strangler-fig over `resources.py`) + the
  provenance registry mean Phase-1 is a **source substitution behind a stable contract**, with the
  per-class `source` stamp as the migration ledger — not a rewrite, not a blocker.
- **The crown-jewel PIT data (filing dates) is already exchange-public-record**, and the analytics
  are **owned IP**. The licensing exposure is a **known, bounded, per-class** list (§3), each with a
  concrete target — exactly the state a compliance reviewer or an institutional buyer's diligence
  wants to see.

**Therefore: keep building the foundation. Do not block. Migrate the §3 VENDOR-TOS rows at the
pre-pitch trigger.**

Related: [[product-strategy-b2b]], [[provenance-knowable-plan]], [[phase0-provenance-coverage]],
[[cci-credibility-timeseries]]; the per-class source truth lives in `provenance.py` `PROVENANCE`.
