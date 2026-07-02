# MVIO — Dataset A (insider / promoter / pledge): institutional proof points

**Status:** proof-of-concept, diligence-standard. **Written:** 2026-07-02.
**Scope:** the three proof-point artifacts commissioned in
`docs/institutional-panel-assessment.md` → "Minimum viable institutional offering".
**Grounding:** `docs/institutional-panel-assessment.md` (product section) +
`docs/DATASET-RESEARCH-BRIEF.md` §5. **Data:** live table `insider_events` in
`/opt/hermes/data/hermes.db`, ingested from NSE corporates-PIT; taxonomy in
`src/automation/insider_events.py` (`classify_txn`, `signal_class`, `aggregate`).

---

## 0. What this asset is (and what it is NOT)

The buyable asset is **PIT-provenanced, taxonomized, exchange-sourced event data on
the under-covered Indian mid/small/micro-cap tail** — delivered as data with a
verifiable disclosure-date clock and a transaction taxonomy the buyer would
otherwise pay analysts to build.

**Honest framing (binding):** this document makes **no alpha, no Sharpe, no "predicts",
no "front-runs re-ratings", no "promoter bought = bullish"** claim. Every signal word
below (`conviction`, `caution`, `pledge_risk`) is a **descriptive taxonomy label**, not
a forecast. The value is **data + provenance + taxonomy**, per the panel verdict.

### Snapshot of the current cut (exact, as pulled 2026-07-02)

| Metric | Value |
|---|--:|
| Events ingested | **4,841** |
| Distinct symbols | **574** |
| Disclosure-date window | **2025-11-01 → 2026-02-28** (~4 months) |
| Transaction-date range (older txns disclosed in-window) | 2022-11-04 → 2026-02-27 |
| Distinct disclosing persons (hashed) | 1,930 |
| Median transaction→disclosure lag | **2 calendar days** (p90 = 6 days) |

The ~4-month window is the honest limit and is **disclosed, not hidden** (see §2). The
tight 2-day median lag is itself a PIT-integrity fact: the disclosure clock is precise
and reconstructable.

---

## 1. Proof point 1 — PIT "replay-the-tape" (disclosure-date clock)

**Claim demonstrated:** as-of any date **T**, the aggregate verdict is computed from
**only** disclosures with `disclosure_dt ≤ T`. Nothing that became public *after* T can
leak into the T-snapshot. The clock is the exchange **disclosure/broadcast date**, never
the transaction date (`aggregate()` filters on `disclosure_dt`, `insider_events.py:241`).

### The name: **AFFLE** (Affle India)

AFFLE was chosen because its verdict genuinely **changes as disclosures arrive** — it is
not a static label. It carries ESOP plumbing (noise), a promoter/insider pledge-creation
sequence (distress), and a later open-market Director buying cluster (conviction) — all
in one stream, so the replay shows real state transitions, not a flat line.

The snapshots below are the **actual output of `aggregate(events, as_of=T)`** run on the
live VPS data — not hand-computed.

| As-of **T** | Events known (`disclosure_dt ≤ T`) | 90d net promoter open-mkt cashflow | Pledge-adverse events (90d) | Promoter cluster buyers (30d) | **Verdict** |
|---|--:|--:|--:|--:|:--|
| **2025-12-16** | 17 | ₹0 | 0 | 0 | `neutral` |
| **2025-12-20** | 21 | ₹0 | 1 | 0 | **`pledge_risk`** |
| **2026-01-15** | 32 | ₹0 | 3 | 0 | `pledge_risk` |
| **2026-02-20** | 38 | ₹14.33 cr | 3 | 3 | `pledge_risk`* |
| **2026-02-28** | 39 | ₹14.33 cr | 3 | 3 | `pledge_risk`* |

**What the replay proves:**

1. **Nothing leaks.** On **2025-12-16** the verdict is `neutral` — the first pledge
   creation (disclosed 2025-12-17) is **invisible** because it was not yet public. One
   day later (**2025-12-20**, after the 12-17 disclosure), the verdict correctly flips to
   `pledge_risk`. The T-clock is doing exactly what a committee needs: the record as it
   *would have looked* on that morning, no hindsight.
2. **The event count is monotonic in T** (17 → 21 → 32 → 38 → 39): each later snapshot is
   a strict superset — the tape only *reveals*, never *rewrites*.
3. **\*Taxonomy priority is auditable.** By 2026-02-20 a genuine Director open-market
   buying cluster is public (₹14.33 cr / 3 buyers over 30d — a `conviction` sub-signal).
   The symbol verdict nonetheless stays `pledge_risk` because the module's documented
   precedence is **distress dominates net-flow** (`insider_events.py:283`). The buy
   cluster is not hidden — it is exposed as `promoter_cluster_buy_30d = 3` and
   `open_market_buy_value_90d = ₹14.33 cr` beside the verdict, so the buyer sees both
   facts and the rule that combined them. Provenance means the *inputs are visible*, not
   just the label.

> **Restatement note.** In this cut there are **0 amendment/restatement rows**
> (`amendment_flag = 1` count = 0), so the replay is clean by construction. The schema
> already carries `amendment_flag` and the upsert is keyed on the exchange-native
> disclosure id (`uid = "NSE:"+did`), so a future restatement updates in place and is
> logged — the replay harness will surface it. We state the zero honestly rather than
> implying a restatement log was exercised.

### How to reproduce (read-only)

```bash
ssh hermes
# single as-of snapshot via the module CLI:
/opt/hermes/.venv/bin/python -m src.automation.insider_events --agg AFFLE --as-of 2025-12-20
# full replay across dates:
/opt/hermes/.venv/bin/python - <<'PY'
import sqlite3, sys; sys.path.insert(0,"/opt/hermes")
from src.automation.insider_events import aggregate
c=sqlite3.connect("/opt/hermes/data/hermes.db"); c.row_factory=sqlite3.Row
ev=[dict(r) for r in c.execute("SELECT * FROM insider_events WHERE symbol='AFFLE' ORDER BY disclosure_dt")]
for T in ("2025-12-16","2025-12-20","2026-01-15","2026-02-20","2026-02-28"):
    a=aggregate(ev,T)
    print(T, a["n_events_known"], a["insider_signal_class"],
          "net90=%.2fcr"%(a["net_promoter_cashflow_90d"]/1e7),
          "pledge_ev=%d"%a["pledge_adverse_events_90d"],
          "cluster=%d"%a["promoter_cluster_buy_30d"])
PY
```

---

## 2. Proof point 2 — Coverage-of-the-tail ledger (honest funnel)

**Claim demonstrated:** the value concentrates exactly where a Bloomberg/terminal
barely reaches — the under-covered tail — and we **disclose the limits** rather than
oversell coverage. A coverage ledger IS the credibility.

### The funnel (exact counts, joined to `stock_index_membership`)

| Layer | Distinct symbols | Note |
|---|--:|---|
| Symbols with ≥1 event | **574** | the raw universe of this cut |
| …in the current NSE equity list (`nse_equity_list`, n=2,380) | 463 | rest are recent/SME/renamed |
| …in **any** tracked NSE index | **173** (30%) | the "covered" head |
| …**outside all tracked indices — THE TAIL** | **401** (**70%**) | where terminals are thin |
| …in Nifty 50 | 12 | the mega-caps barely feature |
| …in Nifty 500 | 111 | |
| …in Nifty Midcap 150 | 32 | |
| …in Nifty Smallcap 250 | 59 | |
| …in Nifty Microcap 250 | 61 | |

**Event volume splits the same way:** 2,453 of 4,841 events (**51%**) are on tail names
outside every tracked index; 2,388 are on index names. **Half the disclosure flow is on
names the buyer's terminal does not index.**

### Event mix by transaction class (`txn_class`) — the full, honest distribution

| txn_class | Events | Gross value (₹ cr) | Meaning |
|---|--:|--:|---|
| OPEN_MARKET_BUY | 1,728 | 5,161 | on-market acquisition |
| OPEN_MARKET_SELL | 1,212 | 20,448 | on-market disposal |
| ESOP | 735 | 1,036 | option exercise / allotment (**plumbing**) |
| OFF_MARKET | 263 | 51,208 | off-market, unclassified |
| UNKNOWN | 257 | 13,068 | blank/"Others" mode — **NOT** treated as conviction |
| PLEDGE_CREATE | 177 | 9,351 | pledge/encumbrance created (distress) |
| GIFT | 129 | 177 | plumbing |
| INTER_SE | 116 | 24,112 | promoter↔promoter transfer (**plumbing**) |
| ALLOTMENT | 78 | 2,611 | preferential/rights/QIP (plumbing) |
| SCHEME | 47 | 48 | merger/demerger (plumbing) |
| PLEDGE_RELEASE | 45 | 4,071 | pledge revoked (**not auto-bullish**) |
| CONVERSION | 41 | 467 | warrant/convertible (plumbing) |
| PLEDGE_INVOKE | 13 | 55 | lender sold pledged shares (strong distress) |

### Event mix by descriptive `signal_class`

| signal_class | Events |
|---|--:|
| conviction (principal open-market buy) | 1,471 |
| plumbing (inter-se / ESOP / gift / allotment / …) | 1,409 |
| sell_other (non-principal sell) | 825 |
| caution (principal open-market sell) | 387 |
| ignore (UNKNOWN mode) | 257 |
| buy_other (non-principal buy) | 257 |
| pledge_risk (create / invoke) | 190 |
| pledge_relief (release) | 45 |

### The honest limits (volunteered, per the "NEVER oversell coverage" rule)

- **Depth:** only ~**4 months** of disclosure history in this cut (2025-11-01 →
  2026-02-28). This is a POC cut, not the multi-year archive the full feed would carry.
  Backfill is a bounded ingestion job (`insider_events.ingest_range`), not a
  methodology change.
- **Category tagging is exchange-supplied and imperfect.** Some pledge/off-market rows
  arrive with `category = "-"` (unattributed) — the taxonomy still classes them by
  `txn_class` (pledge context wins) but cannot always assert *promoter-vs-other* when the
  exchange field is blank. This is disclosed per-row, not smoothed over.
- **Value fields:** pledge rows frequently carry ₹0 / 0% holding-change (a pledge does
  not transfer ownership), so the distress signal fires on **event existence/count**, not
  a rupee delta (`pledge_adverse_events_90d`, `insider_events.py:274`). Rupee columns are
  descriptive where present, absent where the exchange did not report them.
- **Source scope:** this cut is NSE corporates-PIT only; BSE/SME is a documented
  additional pipe (same pattern as `concall_bse.py`), not yet merged into this table.

---

## 3. Proof point 3 — Worked taxonomy example (why the taxonomy IS the value)

**Claim demonstrated:** a raw "promoter transacted ₹X cr" headline is **misleading**;
the decomposition is the product. Two worked names.

### 3a. CHOICEIN (Choice International) — the taxonomy-value poster child

All promoter/insider events in the cut, decomposed by class:

| txn_class | Events | Value (₹ cr) | Category | Honest reading |
|---|--:|--:|---|---|
| UNKNOWN | 4 | 201.20 | Promoter Group | mode blank/"-" → **not** interpretable as buy/sell |
| **PLEDGE_CREATE** | 2 | **153.34** | **Promoters / Promoter Group** | promoter **pledge created** — distress/leverage, NOT buying |
| CONVERSION | 4 | 93.63 | Promoter Group | warrant/security conversion — **plumbing**, not open-market conviction |
| OPEN_MARKET_SELL | 1 | 1.91 | (unattributed) | on-market disposal |
| **OPEN_MARKET_BUY** | 1 | **0.30** | Other (non-principal) | the **only** genuine open-market purchase |
| INTER_SE | 4 | 0.00 | Promoter/Group | promoter↔promoter reshuffle — **plumbing** |

**Why the taxonomy is the value:**

> A naive "promoter/insider activity" tape for CHOICEIN would surface **~₹450 cr** of
> promoter-tagged transaction value and could be spun as "promoters are active / buying."
> The taxonomy shows the truth: the two largest promoter events (**₹153 cr**) are
> **pledge creation** — the promoter *borrowing against* the stake, a **distress/leverage
> signal, the opposite of conviction**. The genuine open-market *buy* is a **single
> ₹0.30 cr** ticket, and it wasn't even a principal (category "Other"). Conversions and
> inter-se transfers (another ~₹94 cr) are **plumbing** that move shares without any
> open-market conviction. Raw "promoter bought" would have inverted the story.

**Liquidity sanity check (does the biggest event dwarf traded liquidity?).** The first
pledge (₹47.03 cr notional, disclosed 2025-11-18, txn 2025-11-14) sits against a stock
that traded **~₹610 cr over the 20 sessions ending 2025-11-14** (avg **₹44 cr/day**
total traded value, ₹15 cr/day delivery, from `stock_signals`). So the pledge notional is
~1 day of turnover — economically material to the promoter's own stake but **not** a
liquidity event that would move the tape; it is a *balance-sheet* signal, correctly
classed as `pledge_risk` rather than as flow. The check guards against reading a large
notional as though it were market pressure.

### 3b. NCLIND (NCL Industries) — inter-se plumbing vs real conviction

NCLIND is the densest name in the cut (55 events). A naive rupee sum is dominated by
plumbing:

| View | Value (₹ cr) |
|---|--:|
| Naive "total promoter transaction value" | **54.06** |
| …of which **INTER_SE (plumbing)** | **50.41** (93%) |
| …of which **real OPEN_MARKET_BUY** | **1.30** |

**93% of the headline rupees are inter-se transfers** — promoter-family reshuffles that
change *who inside the group holds what*, with **zero open-market conviction**. The
taxonomy strips them to `plumbing`, leaving the real signal: a genuine, sustained
promoter open-market buying cluster of small tickets. Replaying `aggregate()` on the
disclosure clock shows the verdict correctly evolving **`caution` (as-of 2026-01-03,
net −₹0.07 cr) → `conviction` (as-of 2026-02-27, net +₹0.32 cr)** as more small
open-market buys become public — a state the naive ₹54 cr headline could never express.

### How to reproduce (read-only)

```bash
ssh hermes
/opt/hermes/.venv/bin/python - <<'PY'
import sqlite3
c=sqlite3.connect("/opt/hermes/data/hermes.db"); c.row_factory=sqlite3.Row
for sym in ("CHOICEIN","NCLIND"):
    print("==", sym)
    for r in c.execute("""SELECT txn_class, COUNT(*) n, ROUND(SUM(value_rs)/1e7,2) cr
                          FROM insider_events WHERE symbol=? GROUP BY txn_class ORDER BY cr DESC""",(sym,)):
        print("  ", dict(r))
PY
```

---

## 4. What to say in the room (and what never to say)

**Say:** "PIT-clean, disclosure-date-timestamped, taxonomized event data on the
under-covered Indian tail — 70% of our names sit outside every tracked NSE index. Here is
the same name replayed as-of three dates with nothing leaking, and here is why a raw
'promoter bought' number would have misled you." (data + provenance + taxonomy)

**Never say** (per `docs/institutional-panel-assessment.md` "NEVER claim" list):
alpha / Sharpe / edge · a backtest as a track record · "promoter bought = bullish" ·
"fully PIT" for anything modeled · survivorship-free · and **never gloss the
data-licensing / redistribution question** — settle that before pricing.

---

## 5. Provenance of the numbers in this doc

Every figure was pulled read-only from `insider_events` (and `stock_signals` for
liquidity) on the live VPS on 2026-07-02, using `aggregate()` from
`src/automation/insider_events.py` for the replay snapshots. No code or shared file was
modified; no data was written. Reproduction snippets are inline in §§1–3.
