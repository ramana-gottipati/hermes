# Theme tagging — external validation via Perplexity

**TRANSIENT helper** (one-off external enrichment; not project state). Generated 2026-06-23.

## What you have

- **`data/themes_export.csv`** — the template. **3,799 companies** (the full universe), one row each.
  - `symbol`, `company_name`, `our_sector` — what we already know.
  - `has_description` — Y/N, whether we hold a business blurb on file (FYI only; Perplexity researches independently).
  - `current_tags` — the tags **we have already approved** for this company (pipe-separated). **375** companies are tagged; **3,424** are blank.
  - `validated_tags`, `tags_to_add`, `tags_to_remove`, `one_line_business`, `sources` — **blank columns for Perplexity to fill.**

## Why only 375 were tagged (context for you, not for the prompt)

Our auto-tagger only seeds from NSE thematic-index membership (a fact) — that union is ~375 names. Everything else needs research. That's the gap this exercise fills.

## How to use

1. Paste the **PROMPT below** into Perplexity once (it contains the fixed vocabulary + rules).
2. Then paste a **batch of CSV rows** (include the header line each time). Keep batches to **~40–50 rows** so it researches and cites properly instead of guessing — quality collapses if you dump all 3,799 at once.
3. It returns CSV rows you merge back by `symbol`. Validate the already-tagged 375 too (it may correct us).
4. Open `themes_export.csv` in Excel → sort by `current_tags` blank-first, or by `our_sector`, to batch sensibly. Clustering similar businesses per batch improves consistency.

---

## THE PROMPT — paste this into Perplexity, then paste a CSV batch under it

```
You are an equity-research analyst classifying Indian-listed (NSE) companies into a FIXED
set of thematic tags for a screening database. I will give you a batch of companies as CSV
rows. For each company: VALIDATE the tags we already have and ADD any that are genuinely
missing — using ONLY the controlled vocabulary below.

============================  CONTROLLED VOCABULARY  ============================
These are the ONLY tags you may use. Spell them EXACTLY as shown. Do NOT invent new tags.

SECTORS
  Auto                  — Automobiles & auto components
  Banks                 — Scheduled commercial banks (public + private)
  Financial Services    — NBFCs, insurers, AMCs, exchanges & banks
  FMCG                  — Fast-moving consumer goods
  IT                    — IT services & software
  Media                 — Media & entertainment
  Metals                — Ferrous & non-ferrous metals & mining
  Pharma                — Pharmaceuticals
  Healthcare            — Hospitals, diagnostics & healthcare services
  Realty                — Real-estate DEVELOPERS (owns/develops property)
  Consumer Durables     — Consumer durables & electronics
  Chemicals             — Specialty & commodity chemicals
  Energy                — Power, utilities & integrated energy
  Oil & Gas             — Upstream, refining, gas & OMCs

CAPEX & INDUSTRIALS
  Infrastructure        — EPC, roads, ports, construction & capital assets
  Defence               — Defence manufacturing & PSUs
  Commodities           — BROAD commodity producers (metals, energy, cement, chem)
  Construction / EPC    — Contract construction & EPC; builds infra/buildings FOR CLIENTS
                          (NOT a real-estate developer — that is Realty)

OWNERSHIP
  PSU Banks             — Public-sector banks (banks only)
  Private Banks         — Private-sector banks (banks only)

SERVICES & CONSUMER
  Aviation              — Airlines & airports
  Travel & Tourism      — Travel, tourism, ticketing & holidays
  Hospitality           — Hotels, resorts, restaurants & QSR

CROSS-CUTTING
  Capital Goods         — Industrial machinery & equipment makers
  Industrialization-proxy — Benefits from India's capex & manufacturing build-out
                          (capital goods / defence / industrial inputs — NOT consumer/services)
  Power / Renewables    — Generation, transmission, solar/wind & the green-energy chain
  Transport / Logistics — Logistics, ports, rail, roads & mobility
  Make-in-India         — Import-substitution / domestic-manufacturing (PLI) plays
  PSU                   — Government-owned enterprises, broad (Centre/State majority owned)
================================================================================

RULES
1. Use ONLY tags from the vocabulary above, spelled EXACTLY (incl. "Construction / EPC",
   "Power / Renewables", "Oil & Gas", "Industrialization-proxy", "Travel & Tourism").
2. MULTI-LABEL is expected. Assign EVERY tag that genuinely applies. Examples:
     - An EPC road builder = Infrastructure | Construction / EPC | Industrialization-proxy
       | Transport / Logistics
     - IndiGo = Aviation | Travel & Tourism | Transport / Logistics
     - A solar EPC = Power / Renewables | Construction / EPC | Industrialization-proxy
3. Be HONEST, not generous. Assign a tag ONLY if the company's ACTUAL core business fits the
   definition. Never force a company into a bucket just to fill a cell. Respect distinctions:
     - Construction / EPC builds FOR clients on contract; a developer that owns/sells flats is Realty.
     - PSU = government-owned (majority Centre/State). Use PSU Banks / Private Banks for banks.
     - Industrialization-proxy is for capex/manufacturing suppliers — not consumer or services names.
     - Commodities = broad producer; if it's specifically metals/oil&gas/chemicals, use those.
4. VALIDATE existing tags: `current_tags` shows what we already approved. Keep each correct one
   in `validated_tags`. If one is WRONG, drop it from validated_tags and list it in
   `tags_to_remove` with a short reason in parentheses.
5. Column meanings:
     validated_tags  = the COMPLETE correct final set (correct existing + newly added)
     tags_to_add     = only the NEW tags (validated_tags minus current_tags)
     tags_to_remove  = current tags you judge incorrect, each with a parenthesised reason
6. ANTI-HALLUCINATION — this is the most important rule:
     - Base every tag on the company's REAL, verifiable business. Do NOT infer from the name alone.
     - Cite at least one authentic source URL per company in `sources`.
     - If you CANNOT verify what a company does (obscure / ambiguous / no reliable source found),
       put exactly "UNVERIFIED" in validated_tags and leave tags_to_add and one_line_business blank.
       Do NOT fabricate. Returning UNVERIFIED is CORRECT and preferred over any guess.
7. SOURCES — use authentic, primary sources, in this priority:
     1) Screener.in:  https://www.screener.in/company/<SYMBOL>/   (our primary reference)
     2) NSE https://www.nseindia.com  /  BSE https://www.bseindia.com  (company page, filings, announcements)
     3) The company's OWN website (About / Business / Investors) and latest Annual Report
     4) Reputable finance sources (Moneycontrol, Tijori, Economic Times) only to corroborate
   Do DEEP RESEARCH for names you can't classify quickly. Cite the source you actually used.
8. one_line_business = one factual sentence (<=20 words) on what the company does, from the source.

OUTPUT FORMAT — return ONLY CSV, no commentary, with EXACTLY this header and these columns:
symbol,validated_tags,tags_to_add,tags_to_remove,one_line_business,sources
  - Separate multiple tags in a cell with a pipe "|"  (e.g. Infrastructure|Construction / EPC)
  - In tags_to_remove, append the reason: Realty (it is an EPC contractor, not a developer)
  - In sources, put one or more full URLs separated by a space.
  - Wrap any cell containing a comma in double quotes.
  - Keep `symbol` EXACTLY as given so I can merge your output back.

Here is the batch (the first line is the header from my file):
<PASTE 40–50 CSV ROWS HERE, INCLUDING THE HEADER LINE>
```

---

## After Perplexity returns

Save its CSV output and we'll merge it back by `symbol` — approved adds become `source='ramana'`
tags in `company_tags`, and any `tags_to_remove` get reviewed before we drop them. Ask me to
write the merge/import step when you have a filled file back.
