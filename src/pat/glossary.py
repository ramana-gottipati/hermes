"""Pat's data glossary — the grounding layer for the natural-language search tab.

WHAT THIS IS
    A plain-English dictionary of every metric, column and value a user can ask
    Pat about. It is the asset behind two features:
      1. "Explain a metric" — Pat answers "what does p_score mean?" from here.
      2. Free-text understanding — these descriptions are the context Gemini
         Flash reads to map a typed question onto the right data.

HOW IT IS CONSUMED
    - ``plain``  -> chip labels, column-header hover, one-line tooltips.
    - ``detail`` -> the full "explain this" answer, already in Pat's voice.
    - ``source`` -> the real ``table.column`` (or "derived on read"), so Pat can
                    point at where the number actually lives.
    Nothing here holds live numbers — those always come fresh from hermes.db.
    This file is data + meaning ONLY.

VOICE
    Pat talks like a sharp desk analyst who respects your time: plain, concrete,
    Indian-market-native, never hand-wavy. Short sentences. Always tells you how
    to READ the number, not just its formula.

ENTRY SHAPE
    term     - display label
    family   - grouping key (see FAMILIES)
    unit     - human-readable unit
    source   - real table.column, or "derived on read"
    plain    - one sentence (chips / tooltips)
    detail   - the "explain this" answer
    aliases  - extra natural-language hooks for matching
    related  - related slugs ([[ ]]-style cross-links)
"""

from __future__ import annotations

# Display order + human labels for the families.
FAMILIES: dict[str, str] = {
    "basics": "Price & delivery basics",
    "positioning": "Positioning — the strong-hand footprint (DVPT)",
    "character": "Character — accumulation vs distribution",
    "rs": "Relative strength",
    "structure": "Structure — CPR",
    "quality": "Quality — pt14 & fundamentals",
    "credibility": "Management credibility — CCI (concalls)",
    "concepts": "How to read Patearn",
}


GLOSSARY: dict[str, dict] = {

    # ───────────────────────── basics ─────────────────────────
    "close": {
        "term": "Close",
        "family": "basics",
        "unit": "₹",
        "source": "prices_eq.close (raw); adj_close for split/bonus-adjusted",
        "plain": "The day's closing price — raw, as printed by the exchange.",
        "detail": (
            "The last traded price of the session. This is the RAW close — it is "
            "not adjusted for splits or bonuses. When Pat compares prices across "
            "time (a cost line from a year ago vs today) it uses the ADJUSTED "
            "close instead, so a 1:1 bonus doesn't look like a 50% crash."
        ),
        "aliases": ["closing price", "ltp", "cmp", "current price", "price"],
        "related": ["avg_price", "value_not_quantity"],
    },
    "avg_price": {
        "term": "Average price (VWAP)",
        "family": "basics",
        "unit": "₹",
        "source": "prices_eq.avg_price",
        "plain": "The volume-weighted average price for the day — the real 'where it traded'.",
        "detail": (
            "NSE's daily volume-weighted average price. More honest than the close "
            "for 'where did this actually change hands today', because it weights "
            "every trade by size instead of just taking the last tick. Pat uses it "
            "as the day's price when it builds value-weighted cost lines."
        ),
        "aliases": ["vwap", "average traded price", "avg traded price"],
        "related": ["close", "key_price"],
    },
    "deliv_qty": {
        "term": "Delivery quantity",
        "family": "basics",
        "unit": "shares",
        "source": "prices_eq.deliv_qty",
        "plain": "Shares that were actually delivered — bought to keep, not flipped intraday.",
        "detail": (
            "Of all shares traded, how many were taken to demat (delivered) rather "
            "than squared off the same day. Delivery is the footprint of people "
            "buying for keeps. Pat almost never uses raw quantity though — it uses "
            "delivery VALUE (qty × price) so corporate actions can't distort it. "
            "See why under 'value, not quantity'."
        ),
        "aliases": ["delivery quantity", "delivered shares", "delivery volume"],
        "related": ["deliv_per", "delivery_value", "value_not_quantity"],
    },
    "deliv_per": {
        "term": "Delivery %",
        "family": "basics",
        "unit": "%",
        "source": "prices_eq.deliv_per",
        "plain": "What share of the day's volume was delivered — conviction of the day's trade.",
        "detail": (
            "Delivered quantity as a percent of total traded quantity. High "
            "delivery % means the day's buyers mostly intend to hold; low means it "
            "was mostly intraday churn. A price move on high delivery % carries "
            "more weight than the same move on thin delivery."
        ),
        "aliases": ["delivery percentage", "delivery percent", "deliv pct"],
        "related": ["deliv_qty", "trade_count_ratio"],
    },
    "value": {
        "term": "Traded value (turnover)",
        "family": "basics",
        "unit": "₹",
        "source": "prices_eq.value",
        "plain": "Total rupees that changed hands in the stock that day.",
        "detail": (
            "The day's turnover — every trade, delivered or not, in rupees. Pat "
            "separates this from delivery value: turnover is total activity, "
            "delivery value is the part that stuck."
        ),
        "aliases": ["turnover", "traded value", "total value"],
        "related": ["delivery_value", "turnover_surge"],
    },
    "num_trades": {
        "term": "Number of trades",
        "family": "basics",
        "unit": "count",
        "source": "prices_eq.num_trades",
        "plain": "How many separate trades printed — the 'how many hands' read.",
        "detail": (
            "Count of executed trades for the day. Pat reads it for BREADTH: the "
            "same delivery value split across many small trades (broadening retail) "
            "reads very differently from a few large ones (concentrated, "
            "institutional). It's the denominator of DVPT."
        ),
        "aliases": ["trades", "trade count", "number of trades"],
        "related": ["dvpt", "trade_count_ratio", "ticket_size"],
    },
    "delivery_value": {
        "term": "Delivery value",
        "family": "basics",
        "unit": "₹",
        "source": "stock_signals.delivery_value_today",
        "plain": "Rupee value delivered that day = delivered shares × price.",
        "detail": (
            "The rupee size of the to-keep buying: delivery quantity × price. This "
            "is Patearn's canonical 'how much real money showed up' number, and the "
            "building block of DVPT and the accumulation read."
        ),
        "aliases": ["delivery value", "deliv value", "delivered value"],
        "related": ["dvpt", "deliv_qty", "value_not_quantity"],
    },

    # ─────────────────────── positioning / DVPT ───────────────────────
    "dvpt": {
        "term": "DVPT — delivery value per trade",
        "family": "positioning",
        "unit": "₹",
        "source": "stock_signals.delivery_value_per_trade",
        "plain": "The average rupee size of a delivered trade — how big the to-keep hands were.",
        "detail": (
            "DVPT = delivery value ÷ number of trades. It asks: when someone bought "
            "to hold today, how big was the average ticket? Big DVPT = large, "
            "concentrated hands (the 'strong hand'); small DVPT = lots of little "
            "buyers. It's the spine of the whole Positioning pillar — but on its "
            "own it's side-blind (it can't tell buying from selling), which is why "
            "Pat reads it together with character."
        ),
        "aliases": ["delivery value per trade", "dvpt", "strong hand", "ticket size signal"],
        "related": ["p_score", "r_score", "p_tier", "accum_character"],
    },
    "mep": {
        "term": "MEP — signed accumulation / distribution",
        "family": "positioning",
        "unit": "z-score",
        "source": "mep_signals.mep_score / mep_state",
        "plain": "A SIGNED read of accumulation (+) vs distribution (−) — the side DVPT can't tell.",
        "detail": (
            "MEP is the within-stock z-average of four SIGNED price-tape terms — "
            "close-vs-VWAP pressure, close-location, 22-day drift, and up/down volume "
            "skew — so + means net accumulation and − means net distribution, each "
            "judged against the stock's OWN trailing history. It is the signed "
            "complement to DVPT (which is side-blind). DESCRIPTOR ONLY: it "
            "characterises / confirms, it does NOT rank or pick stocks — its "
            "predictive role failed a Deflated-Sharpe gate (D62). Read it beside DVPT, "
            "not instead of it."
        ),
        "aliases": ["mep", "signed accumulation", "accumulation score", "mep score",
                    "net accumulation pressure", "accumulation distribution score"],
        "related": ["mep_state", "dvpt", "accum_character"],
    },
    "mep_state": {
        "term": "MEP state",
        "family": "positioning",
        "unit": "label",
        "source": "mep_signals.mep_state",
        "plain": "The banded MEP verdict: STRONG_ACCUM / ACCUM / NEUTRAL / DISTRIB / STRONG_DISTRIB.",
        "detail": (
            "The signed MEP score bucketed into five bands — strong accumulation, "
            "accumulation, neutral, distribution, strong distribution. A quick "
            "character / confirmation read; it does not rank stocks (descriptor only, D62)."
        ),
        "aliases": ["mep state", "accumulation state"],
        "related": ["mep", "accum_character"],
    },
    "r_tier": {
        "term": "R-tier baselines (the normal-day bars)",
        "family": "positioning",
        "unit": "₹",
        "source": "stock_signals.avg_dvpt_1m / _2m / _3m / _6m / _12m",
        "plain": "Today's DVPT vs the stock's ordinary day, over 1–12 months.",
        "detail": (
            "Soft bars. Each is the FLAT average DVPT over a trailing window "
            "(roughly 1, 2, 3, 6 and 12 months of trading days). They answer 'is "
            "today busier than a normal day for this stock?' Clearing more of them "
            "lifts the r_score and shows building intensity before a true "
            "institutional peak prints."
        ),
        "aliases": ["r tier", "rolling average dvpt", "avg dvpt", "normal day bar"],
        "related": ["r_score", "p_tier", "dvpt"],
    },
    "p_tier": {
        "term": "P-tier baselines (the peak-day bars)",
        "family": "positioning",
        "unit": "₹",
        "source": "stock_signals.power_dvpt_1m / _2m / _3m / _6m / _12m",
        "plain": "Today's DVPT vs the stock's heaviest institutional days, over 1–12 months.",
        "detail": (
            "Hard bars. Each is the average DVPT of only the HEAVIEST-delivery days "
            "in the window — the institutional peak days, not the average day. "
            "Clearing a P-bar means today rivalled the days the big hands last "
            "showed up in size. This is a much higher wall than the R-tier, and it "
            "drives p_score and the rank."
        ),
        "aliases": ["p tier", "power delivery", "power dvpt", "peak day bar", "institutional bar"],
        "related": ["p_score", "r_tier", "next_p_above", "trigger_rank"],
    },
    "r_score": {
        "term": "r_score",
        "family": "positioning",
        "unit": "score 0–5",
        "source": "stock_signals.r_score",
        "plain": "How many of the 5 normal-day (R) bars today's DVPT cleared.",
        "detail": (
            "A count from 0 to 5 of how many R-tier baselines today's DVPT beats. "
            "It's the 'building intensity' meter — a stock quietly waking up will "
            "light up r_score before it ever clears a P-bar. A high r_score with a "
            "low p_score is the classic 'something's stirring, not yet a peak day' "
            "setup."
        ),
        "aliases": ["r score", "rolling score"],
        "related": ["p_score", "r_tier", "trigger_rank"],
    },
    "p_score": {
        "term": "p_score",
        "family": "positioning",
        "unit": "score 0–5",
        "source": "stock_signals.p_score",
        "plain": "How many institutional 'power' walls today's delivery flow cleared (0–5).",
        "detail": (
            "A count from 0 to 5 of how many P-tier (peak-day) baselines today's "
            "DVPT beats. This is the headline strength number. p_score = 5 means "
            "today out-delivered the big-hand peak days across every horizon — a "
            "rare, loud signal. The rank (SS/S/A/B/C) is just a label on this count."
        ),
        "aliases": ["p score", "power score", "strength score"],
        "related": ["trigger_rank", "p_tier", "is_ath_dvpt", "next_p_above"],
    },
    "trigger_rank": {
        "term": "Trigger rank (SS / S / A / B / C)",
        "family": "positioning",
        "unit": "label",
        "source": "stock_signals.trigger_rank",
        "plain": "A letter grade for today's delivery strength, straight from p_score.",
        "detail": (
            "A plain label on p_score so you don't have to remember the number: "
            "SS = 5 (cleared every wall), S = 4, A = 3, B = 2, C = 1, and '–' = 0. "
            "There is NO hidden ordering — it's a pure count, so a 3-of-5 hit is an "
            "A no matter which windows it cleared. /triggers defaults to A-or-better."
        ),
        "aliases": ["rank", "trigger rank", "ss", "grade"],
        "related": ["p_score", "next_p_above"],
    },
    "is_ath_dvpt": {
        "term": "All-time-high DVPT",
        "family": "positioning",
        "unit": "flag",
        "source": "stock_signals.is_ath_dvpt",
        "plain": "Today's delivery-per-trade is the biggest in the stock's whole history.",
        "detail": (
            "A flag that fires when today's DVPT beats every day in the stock's "
            "entire database history — the single loudest to-keep buying footprint "
            "it has ever shown. It's the top sort key on /scan because an ATH-DVPT "
            "day is often the day a new strong hand declares itself."
        ),
        "aliases": ["ath dvpt", "all time high delivery", "record delivery", "ath"],
        "related": ["dvpt", "p_score"],
    },
    "next_p_above": {
        "term": "Near-break pointer (next_p_above / gap)",
        "family": "positioning",
        "unit": "label + %",
        "source": "stock_signals.next_p_above, stock_signals.gap_to_next_p_pct",
        "plain": "The closest P-wall still above today, and how far under it you are.",
        "detail": (
            "next_p_above names the smallest P-baseline today did NOT clear — the "
            "nearest wall overhead. gap_to_next_p_pct is how far below it you are "
            "(negative = under). When a stock is within about −10% of that wall AND "
            "r_score is already ≥ 4, it's 'kissing the wall' — the breakout-imminent "
            "row that /triggers near surfaces."
        ),
        "aliases": ["near break", "next p above", "gap to next", "wall above"],
        "related": ["p_tier", "p_score", "trigger_rank"],
    },
    "hot_days": {
        "term": "Hot-day cost line (discount / at-cost / above-cost)",
        "family": "positioning",
        "unit": "₹ + %",
        "source": "stock_signals.hot_days_avg_price, stock_signals.price_vs_hot_avg_pct",
        "plain": "Where the big-delivery days transacted, and whether you're cheap vs them today.",
        "detail": (
            "hot_days_avg_price is the average price on the stock's heavy-delivery "
            "days — roughly where the strong hand paid. price_vs_hot_avg_pct is "
            "today's close vs that line. Pat reads it as a tag: 🟢 discount (>3% "
            "below the strong hand's cost), 🟡 at-cost (±3%), 🔴 above-cost (>3% "
            "over). Buying at or below where the big money paid is the edge."
        ),
        "aliases": ["hot day price", "cost line", "discount entry", "at cost", "above cost"],
        "related": ["key_price", "price_zones"],
    },
    "price_zones": {
        "term": "Institutional price zones (avg_close_r* / avg_close_p*)",
        "family": "positioning",
        "unit": "₹",
        "source": "stock_signals.avg_close_r1m…r12m, avg_close_p1m…p12m",
        "plain": "The price levels where the normal-day and peak-day deliveries happened, per horizon.",
        "detail": (
            "For every R and P baseline, Pat also stores the average close on the "
            "days that fed it. So you can read not just 'how intense' but 'at what "
            "price' the activity sat — a ladder of institutional zones from 1 month "
            "to 12. /dvpt renders these as the 'Institutional price zones' section."
        ),
        "aliases": ["price zones", "institutional zones", "avg close", "where they bought"],
        "related": ["hot_days", "key_price"],
    },
    "key_price": {
        "term": "Key price + entry gap (value-weighted cost)",
        "family": "positioning",
        "unit": "₹ + %",
        "source": "stock_signals.key_price_p1m…p12m, gap_to_key_p1m…p12m",
        "plain": "The big day's true cost line — value-weighted, so the heaviest day dominates.",
        "detail": (
            "Where the institutional price zones equal-weight every peak day, the "
            "key price VALUE-weights them: Σ(price × delivery value) ÷ Σ(delivery "
            "value) over the same peak days. The single biggest day pulls the line "
            "toward where the real money actually sat. gap_to_key_p* is today's "
            "close vs that key (− below cost = a gift, + above = chasing). "
            "'Near-key' is flagged when you're sitting right on it."
        ),
        "aliases": ["key price", "value weighted cost", "entry gap", "gap to key"],
        "related": ["hot_days", "price_zones", "avg_price"],
    },
    "ticket_size": {
        "term": "Ticket size (avg_trade_qty / avg_deliv_qty_per_trade)",
        "family": "positioning",
        "unit": "shares",
        "source": "stock_signals.avg_trade_qty, stock_signals.avg_deliv_qty_per_trade",
        "plain": "How big the average trade — and average delivered trade — was today.",
        "detail": (
            "Two reads on 'how chunky were today's trades': average shares per "
            "trade, and average DELIVERED shares per trade. Rising ticket size "
            "alongside rising delivery value is the fingerprint of fewer, bigger "
            "buyers stepping in."
        ),
        "aliases": ["ticket size", "avg trade qty", "trade size"],
        "related": ["dvpt", "num_trades"],
    },
    "turnover_surge": {
        "term": "Turnover surge (1m / 3m / 1y)",
        "family": "positioning",
        "unit": "×",
        "source": "stock_signals.turnover_surge_1m / _3m / _1y",
        "plain": "Today's traded value vs its own recent average — an activity-spike multiple.",
        "detail": (
            "Today's turnover divided by its rolling average over 1 month, 3 months "
            "and 1 year. A 3× surge says today drew three times the usual money. "
            "Pair a turnover surge with a high p_score and you have both unusual "
            "activity AND unusual to-keep buying on the same day."
        ),
        "aliases": ["turnover surge", "volume spike", "activity surge", "x power"],
        "related": ["value", "p_score"],
    },

    # ───────────────────────── character ─────────────────────────
    "accum_character": {
        "term": "Character (accumulation / distribution / consolidation / neutral)",
        "family": "character",
        "unit": "label",
        "source": "stock_signals.accum_character",
        "plain": "Which SIDE the strong hand is on — the warning DVPT alone can't give you.",
        "detail": (
            "Delivery data is side-blind: every delivered share was both bought and "
            "sold, so a loud p_score is equally consistent with a big hand BUYING "
            "or DISTRIBUTING into a retail bid. Character is the label that breaks "
            "the tie — ACCUMULATION, DISTRIBUTION, CONSOLIDATION or NEUTRAL — "
            "derived from three independent axes (who / which-way / context). A "
            "high-rank trigger reading DISTRIBUTION is a WARNING, not a buy."
        ),
        "aliases": ["character", "accumulation", "distribution", "accum", "side"],
        "related": ["deliv_updown_ratio", "trade_count_ratio", "pct_from_52w_high", "dvpt"],
    },
    "trade_count_ratio": {
        "term": "WHO — breadth & conviction",
        "family": "character",
        "unit": "ratio / %",
        "source": "stock_signals.trade_count_ratio_1m_6m, deliv_value_ratio_1m_6m, avg_deliv_pct_1m/_6m",
        "plain": "Is the buying broadening into a crowd or staying concentrated — and is delivery ₹ picking up?",
        "detail": (
            "The 'who' axis of character. trade_count_ratio_1m_6m compares recent "
            "trade-count to the longer base (a jump = a broadening crowd, often "
            "retail piling in). deliv_value_ratio_1m_6m asks if delivery rupees are "
            "accelerating. avg_deliv_pct_1m vs _6m asks if conviction (delivery %) "
            "is holding. Concentrated + rising delivery ₹ leans strong-hand; "
            "broadening crowd leans retail."
        ),
        "aliases": ["who axis", "breadth", "trade count ratio", "conviction"],
        "related": ["accum_character", "num_trades", "deliv_per"],
    },
    "deliv_updown_ratio": {
        "term": "WHICH WAY — the direction read",
        "family": "character",
        "unit": "ratio / %",
        "source": "stock_signals.deliv_updown_ratio_3m, accum_price_drift_3m",
        "plain": "Is delivery landing more on up-days or down-days — the only true side-revealer.",
        "detail": (
            "The 'which way' axis — the closest delivery data gets to showing a "
            "side. deliv_updown_ratio_3m is the value-weighted skew of delivery on "
            "up-days vs down-days (on adjusted closes); more on up-days leans "
            "accumulation. accum_price_drift_3m is the price drift over the same "
            "window. Together they say whether the heavy delivery is being "
            "absorbed on strength or dumped on weakness."
        ),
        "aliases": ["which way", "up down ratio", "direction", "price drift"],
        "related": ["accum_character", "trade_count_ratio"],
    },
    "pct_from_52w_high": {
        "term": "CONTEXT — distance from the 52-week high",
        "family": "character",
        "unit": "%",
        "source": "stock_signals.pct_from_52w_high",
        "plain": "Near the highs or down in a base — same delivery means different things at each.",
        "detail": (
            "The 'context' axis. Heavy delivery right under fresh highs reads very "
            "differently from the same delivery deep in a base. Distance from the "
            "52-week high frames the other two axes: distribution near highs is the "
            "dangerous kind; accumulation in a base is the patient kind."
        ),
        "aliases": ["distance from high", "52w high", "pct from high", "context"],
        "related": ["accum_character", "rs_vs_broad"],
    },

    # ───────────────────────── relative strength ─────────────────────────
    "rs_rank": {
        "term": "RS rank (1–99)",
        "family": "rs",
        "unit": "rank 1–99",
        "source": "stock_signals.rs_rank",
        "plain": "Where this stock's momentum sits vs every other liquid stock — 99 = strongest.",
        "detail": (
            "A cross-stock percentile of blended relative-strength momentum across "
            "the liquid universe. 99 means almost nothing is outrunning it; 50 is "
            "middle of the pack. It's the fastest one-number read of 'is the market "
            "voting for this name', and the spine of the leaders board."
        ),
        "aliases": ["rs rank", "relative strength rank", "momentum rank", "percentile"],
        "related": ["rs_vs_broad", "rs_vs_sector", "rs_leader"],
    },
    "rs_vs_broad": {
        "term": "RS vs the broad market",
        "family": "rs",
        "unit": "ratio + slopes",
        "source": "stock_signals.rs_vs_broad_today, _slope_1m/3m/6m/12m, _above_50ma/_200ma, _new_52w_high, _trend_state",
        "plain": "The stock's price divided by Nifty 500 — rising = beating the market.",
        "detail": (
            "rs_vs_broad_today = the stock's adjusted price ÷ Nifty 500. A rising "
            "RS line means the stock is outperforming the market regardless of "
            "direction. The slopes (1–12m), the 50/200-day MA flags, a new RS "
            "52-week high, and the trend_state label all describe whether that "
            "outperformance is accelerating, holding, or rolling over."
        ),
        "aliases": ["rs vs broad", "vs market", "vs nifty 500", "relative strength"],
        "related": ["rs_rank", "rs_vs_sector"],
    },
    "rs_vs_sector": {
        "term": "RS vs the stock's sector",
        "family": "rs",
        "unit": "ratio + slopes",
        "source": "stock_signals.primary_sector, rs_vs_sector_today, _slope_*, _above_*ma, _new_52w_high, _trend_state",
        "plain": "The stock vs its own sector index — is it a leader inside its group?",
        "detail": (
            "Same vocabulary as RS-vs-broad, but measured against the stock's "
            "primary sector index (the narrowest NSE sectoral index it belongs to). "
            "This separates 'the whole sector is hot' from 'this name is the leader "
            "OF a hot sector'. The strongest setups are strong-stock-in-strong-"
            "sector — high on both reads."
        ),
        "aliases": ["rs vs sector", "vs sector", "sector relative strength"],
        "related": ["primary_sector", "rs_vs_broad", "rs_leader"],
    },
    "primary_sector": {
        "term": "Primary sector",
        "family": "rs",
        "unit": "label",
        "source": "stock_signals.primary_sector",
        "plain": "The narrowest NSE sector index the stock belongs to — its home group.",
        "detail": (
            "Assigned from index membership as the SMALLEST-membership NSE sectoral "
            "index a stock sits in (size and broad indices excluded), so 'sector' "
            "means its tightest real peer group. It's null for stocks in no NSE "
            "sectoral index. This is what the sector RS and the leaders/laggards "
            "boards group by."
        ),
        "aliases": ["sector", "primary sector", "industry", "peer group"],
        "related": ["rs_vs_sector", "rs_leader"],
    },
    "rs_leader": {
        "term": "Leaders & laggards",
        "family": "rs",
        "unit": "derived board",
        "source": "derived on read (rs_rank + sector trend + RS trend_state)",
        "plain": "Strong stocks inside strong sectors (leaders) vs weak-in-weak (laggards).",
        "detail": (
            "Not a single column — a synthesis. Leaders are names ranking high on "
            "both market and sector RS while their sector itself is trending up "
            "('strong in strong'); laggards are the mirror. It's the board you open "
            "to ask 'where is the market actually putting its money right now'."
        ),
        "aliases": ["leaders", "laggards", "strong in strong", "rs leaders"],
        "related": ["rs_rank", "rs_vs_sector", "primary_sector"],
    },

    # ───────────────────────── structure / CPR ─────────────────────────
    "cpr": {
        "term": "CPR (Central Pivot Range)",
        "family": "structure",
        "unit": "₹ (3 lines)",
        "source": "cpr_signals.p, cpr_signals.bc, cpr_signals.tc, cpr_signals.timeframe",
        "plain": "Three pivot lines from the prior period's range — read at Daily, Weekly, Monthly.",
        "detail": (
            "A 3-line range projected from the PRIOR completed period's high/low/"
            "close: Pivot P = (H+L+C)/3, BC = (H+L)/2, and TC = 2P − BC. Pat builds "
            "it identically at three degrees — Daily, Weekly, Monthly (the "
            "timeframe field). Price sitting above or below the range, and how the "
            "ranges stack across timeframes, is the Structure pillar."
        ),
        "aliases": ["cpr", "central pivot range", "pivot", "structure"],
        "related": ["cpr_width", "cpr_pattern", "cpr_regime"],
    },
    "cpr_width": {
        "term": "CPR width & compression",
        "family": "structure",
        "unit": "% + percentile",
        "source": "cpr_signals.width_pct, cpr_signals.compression_pctile",
        "plain": "How narrow the pivot range is — a tight CPR often precedes a big move.",
        "detail": (
            "width_pct = (TC − BC) ÷ P × 100 — a narrow range signals balance and "
            "often precedes expansion. But 'narrow' is relative, so compression_"
            "pctile ranks today's width against this stock's OWN history (high "
            "percentile = unusually coiled FOR THIS STOCK). That own-history read "
            "is the truer 'unusual' than a flat percentage."
        ),
        "aliases": ["cpr width", "compression", "narrow cpr", "coiled"],
        "related": ["cpr", "cpr_pattern"],
    },
    "cpr_pattern": {
        "term": "CPR reversal pattern (BULL_U / BEAR_INVU)",
        "family": "structure",
        "unit": "label",
        "source": "cpr_signals.pattern, cpr_signals.confirmed, cpr_signals.days_since_pattern",
        "plain": "A clean two-step turn in the pivot ranges — U-shape up, inverted-U down.",
        "detail": (
            "BULL_U is a clean down-then-up step in successive CPRs (a valley "
            "reversal); BEAR_INVU is the inverted top. 'confirmed' means price "
            "actually closed beyond the range in the pattern's direction; "
            "days_since_pattern = 0 means it formed on this very bar (fresh). Larger "
            "timeframes carry more weight when they line up."
        ),
        "aliases": ["bull u", "bear invu", "cpr pattern", "reversal", "u shape"],
        "related": ["cpr", "cpr_regime"],
    },
    "cpr_regime": {
        "term": "CPR regime",
        "family": "structure",
        "unit": "+1 / −1 / 0",
        "source": "cpr_signals.regime",
        "plain": "Simply: is price above the pivot (+1), below (−1) or on it (0).",
        "detail": (
            "The sign of (adjusted close − pivot). It's the higher-timeframe trend "
            "context Pat uses to amplify lower-timeframe signals — a daily bull "
            "setup inside a +1 weekly and monthly regime is worth more than the "
            "same setup fighting the bigger trend."
        ),
        "aliases": ["regime", "above pivot", "below pivot", "trend context"],
        "related": ["cpr", "cpr_pattern"],
    },

    # ───────────────────────── quality / pt14 ─────────────────────────
    "pt14": {
        "term": "pt14 — the 14-pattern quality score",
        "family": "quality",
        "unit": "0–100 + tier",
        "source": "pattern_scores (pws · ns_base/_pessimistic/_optimistic · pac · qg_pass · hard_disqualified · tier)",
        "plain": "A rule-based read of business quality across the 14 Patearn patterns.",
        "detail": (
            "Pure-Python, no-LLM scoring of a company against the 14 Patearn "
            "patterns (ROCE trajectory, operating leverage, balance sheet, promoter "
            "conviction, and so on) from Screener.in fundamentals. The headline is "
            "ns_base — a 0–100 Normalized Score (the raw pattern-weighted score "
            "pws as a percent of the max). ns_pessimistic / ns_optimistic bracket "
            "it as a confidence band (recomputed if every soft 'Yes' is marked "
            "down to 'Partial', or every 'Partial' up to 'Yes'). pac counts how "
            "many of the 14 patterns are actively contributing. A Quality Gate "
            "(qg_pass) checks a core subset of must-have patterns clears a bar, "
            "and a hard-disqualify flag knocks out fatal cases outright. These "
            "roll up to a tier: DISQUALIFIED overrides all; else T1 (ns ≥ 72 AND "
            "QG pass), T2 (ns ≥ 55), T3 (ns ≥ 40), T4 below. Scored on demand for "
            "surfaced names, not in bulk (honors the build-over-time doctrine)."
        ),
        "aliases": ["pt14", "pattern score", "quality score", "14 patterns", "patearn score",
                    "ns_base", "tier", "quality gate", "t1"],
        "related": ["fundamentals", "financials_adaptation", "pillars"],
    },
    "fundamentals": {
        "term": "Fundamentals (Screener.in)",
        "family": "quality",
        "unit": "mixed",
        "source": "fundamentals.* (pe, pb, roce, roe, debt_to_equity, promoter_holding, growth, opm, …)",
        "plain": "The cached fundamental snapshot — valuation, returns, growth, balance sheet, holding.",
        "detail": (
            "A periodically-cached pull from Screener.in: valuation (PE, PB, book "
            "value, dividend yield), returns (ROCE, ROE and their 3-year averages), "
            "growth (sales & profit over 5y / 3y / TTM), margins (OPM), balance "
            "sheet (debt-to-equity, debt, cash, interest coverage) and ownership "
            "(promoter holding & pledge, FII / DII). These feed pt14 and the "
            "'screen by fundamentals' flow."
        ),
        "aliases": ["fundamentals", "pe", "roce", "roe", "promoter holding", "valuation", "screener"],
        "related": ["pt14", "financials_adaptation"],
    },

    # ───────────────────────── concepts / doctrine ─────────────────────────
    "pillars": {
        "term": "The four Patearn pillars",
        "family": "concepts",
        "unit": "—",
        "source": "derived (synthesis across signals)",
        "plain": "Positioning, Relative strength, Quality and Structure — the four lenses.",
        "detail": (
            "Patearn reads a stock through four independent lenses: POSITIONING "
            "(DVPT — is a strong hand active?), RELATIVE STRENGTH (is the market "
            "voting for it?), QUALITY (pt14 — is the business any good?) and "
            "STRUCTURE (CPR — is the chart set up?). No single pillar is a verdict; "
            "conviction is when several line up on the same name."
        ),
        "aliases": ["pillars", "four pillars", "strategy", "framework"],
        "related": ["dvpt", "rs_rank", "pt14", "cpr", "conviction"],
    },
    "conviction": {
        "term": "Conviction shortlist",
        "family": "concepts",
        "unit": "derived board",
        "source": "derived on read (RS leader + accumulating + near-entry + pt14 quality)",
        "plain": "The rare names where all four pillars agree at once.",
        "detail": (
            "The synthesis board: a name that is an RS leader, reads as "
            "accumulating in character, sits near a strong-hand entry zone, AND "
            "passes pt14 quality. Few stocks clear all four on any given day — "
            "that's the point. It's where Pat points when you ask 'what's the best "
            "setup right now', not just 'what's loud'."
        ),
        "aliases": ["conviction", "shortlist", "best setups", "all pillars align"],
        "related": ["pillars", "rs_leader", "accum_character", "pt14"],
    },
    "value_not_quantity": {
        "term": "Why value, not share quantity",
        "family": "concepts",
        "unit": "—",
        "source": "doctrine (Patearn data layer)",
        "plain": "Every cross-time metric is in rupees, so splits and bonuses can't lie to you.",
        "detail": (
            "Share counts break across corporate actions — a 1:1 bonus doubles "
            "quantity overnight with no new money in. So Patearn's canonical metric "
            "is delivery VALUE (delivered shares × price), and every cross-time "
            "comparison is in rupees. It makes the numbers corporate-action-"
            "invariant: a 'record delivery day' is record MONEY, not a split "
            "artefact."
        ),
        "aliases": ["value not quantity", "why value", "rupees not shares", "corporate action"],
        "related": ["delivery_value", "dvpt"],
    },
    "financials_adaptation": {
        "term": "Sector-adapted thresholds for financials",
        "family": "concepts",
        "unit": "—",
        "source": "doctrine (pt14 scoring for HFCs / NBFCs / banks)",
        "plain": "Banks and NBFCs are scored on bank metrics, not the standard pattern thresholds.",
        "detail": (
            "The 14 patterns were built for non-financial companies, so applying "
            "them raw makes banks and NBFCs score misleadingly low (their D/E is 6–8× "
            "by design, ROCE is suppressed by leverage). For financials Pat reads "
            "ROE/ROA, NII growth, GNPA, CAR and ALM discipline instead. Any "
            "financial-sector score is tagged as using sector-adapted thresholds."
        ),
        "aliases": ["financials", "banks", "nbfc", "hfc", "sector adapted", "doctrine d"],
        "related": ["pt14", "fundamentals"],
    },

    # ──────────────────── management credibility (CCI) ────────────────────
    "cci_credibility": {
        "term": "Management credibility (CCI)",
        "family": "credibility",
        "unit": "tier A+…D + 0–100 composite",
        "source": "concall_scores (from earnings-concall transcripts)",
        "plain": "How much a management's words have proven true over time — a "
                 "credibility tier built from its earnings-call promises vs what landed.",
        "detail": (
            "CCI (Concall Intelligence) reads a company's earnings-call transcripts, "
            "captures every forward promise, and grades it against what actually "
            "happened. The score ranks on MEASURABLE items only (D61): kept-promise "
            "accuracy + how falsifiable the guidance is + a forensic veto + deterministic "
            "deterioration. The behaviour reads (tone, courage…) are shown for context but "
            "NEVER ranked — credibility can't be scored from the suspect's own testimony. "
            "A name with no settled promises is 'unproven' (capped below A). Pilot."
        ),
        "aliases": ["credibility", "management credibility", "credible management",
                    "concall", "concall intelligence", "trustworthy management"],
        "related": ["guidance_accuracy", "cci_deterioration", "cci_veto"],
    },
    "guidance_accuracy": {
        "term": "Guidance accuracy",
        "family": "credibility",
        "unit": "%",
        "source": "concall_scores.guidance_accuracy_score (settled promises)",
        "plain": "The hit-rate of a management's RESOLVED promises — what share of the "
                 "guidance it gave actually came true.",
        "detail": (
            "Every quantified or directional promise on a concall is settled once its "
            "horizon's result is reported (no look-ahead): MET / MISSED / PARTIAL vs the "
            "actual. Guidance accuracy is the kept-promise hit-rate across all settled "
            "promises — the slow, earned, hard-to-fake core of credibility. 'Unproven' "
            "until enough promises resolve."
        ),
        "aliases": ["guidance accuracy", "kept promises", "promise hit rate",
                    "promise ledger", "follow-through"],
        "related": ["cci_credibility", "quantification_rate"],
    },
    "quantification_rate": {
        "term": "Quantification rate",
        "family": "credibility",
        "unit": "%",
        "source": "concall_scores.quantification_rate",
        "plain": "What share of a management's forward statements are falsifiable NUMBERS "
                 "rather than vague talk — the honest, deterministic 'transparency'.",
        "detail": (
            "Computed deterministically from each promise's text: a HARD/SOFT number "
            "(₹5,000cr, 15% margin) counts; a directional/aspirational vagueness does "
            "not. It replaces an LLM 'transparency' score with a reproducible measure — and "
            "it is non-monotonic in spirit: serial round-number promoter targets are a "
            "value-trap tell, not a virtue, so it is read alongside the track record."
        ),
        "aliases": ["quantification", "quantification rate", "transparency", "falsifiable guidance"],
        "related": ["guidance_accuracy", "cci_credibility"],
    },
    "cci_deterioration": {
        "term": "Credibility deterioration (avoid tape)",
        "family": "credibility",
        "unit": "count of flags",
        "source": "concall_redflags (deterministic diff) → concall_scores.deterioration_score",
        "plain": "Objective signs a management's story is decaying — a promise walked back, "
                 "quietly dropped, or a metric it stopped disclosing.",
        "detail": (
            "A deterministic diff of consecutive transcripts emits FACT-based flags: a "
            "quantified target LOWERED (guidance walk-back), a prior capex/revenue/margin "
            "promise not reaffirmed (quietly dropped), or a metric that vanished "
            "(stopped disclosing). These drive the avoid tape and CAN move the rank "
            "(unlike the soft LLM red-flags, which only inform). The sell-side won't "
            "publish credibility decay on its banking/IPO clients — that conflict is the edge."
        ),
        "aliases": ["deterioration", "avoid tape", "guidance walkback", "walked back",
                    "quietly dropped", "stopped disclosing", "credibility decay"],
        "related": ["cci_credibility", "cci_veto"],
    },
    "cci_veto": {
        "term": "Forensic veto (CCI)",
        "family": "credibility",
        "unit": "boolean ⛔",
        "source": "concall_scores.veto_active (pledge / auditor-exit / pt14 disqualifiers)",
        "plain": "An exogenous integrity gate IN FRONT of credibility: a promoter-pledge "
                 "spike or an auditor exit forces the worst tier no matter how good the call sounded.",
        "detail": (
            "Glib frauds run smooth, confident, numeric calls right up to collapse "
            "(Manpasand, Vakrangee, DHFL, Yes Bank, Coffee Day…), so credibility can't be "
            "scored from the call alone. The veto wires the un-spinnable signals — promoter "
            "pledge ≥20%, auditor resignation/qualification, and pt14's hard "
            "disqualifiers — to force tier D. Cash-flow/leverage vetoes are suppressed for "
            "lenders and heavy-capex cyclicals (structural, not fraud)."
        ),
        "aliases": ["veto", "forensic veto", "pledge veto", "auditor exit", "integrity gate"],
        "related": ["cci_credibility", "cci_deterioration", "disqualified"],
    },
}


# ─────────────────────────── retrieval helpers ───────────────────────────
# These are how the engine will pull entries: a direct slug lookup, a simple
# keyword search over term/aliases/plain/detail, and a family filter. Kept tiny
# and dependency-free so both the web tab and the Gemini prompt-builder can use
# them.

def get(slug: str) -> dict | None:
    """Return one entry by slug, or None."""
    return GLOSSARY.get(slug)


def family(name: str) -> list[tuple[str, dict]]:
    """Return all (slug, entry) pairs in a family, in declaration order."""
    return [(s, e) for s, e in GLOSSARY.items() if e["family"] == name]


def find(query: str, limit: int = 5) -> list[tuple[str, dict]]:
    """Cheap keyword ranking over term + aliases + plain + detail.

    Not a substitute for the Gemini free-text mapper — this is the deterministic
    fallback / autocomplete behind the 'explain a metric' picker.
    """
    q = query.lower().strip()
    if not q:
        return []
    words = [w for w in q.replace("?", " ").split() if w]
    scored: list[tuple[int, str, dict]] = []
    for slug, e in GLOSSARY.items():
        hay = " ".join(
            [slug, e["term"], e["plain"], e["detail"], " ".join(e.get("aliases", []))]
        ).lower()
        score = 0
        if q in hay:
            score += 5
        single_aliases = {a.lower() for a in e.get("aliases", [])}
        for w in words:
            if w in hay:
                score += 1
            if w == slug:
                score += 6
            elif w in single_aliases:
                score += 4
        # exact whole-query alias / slug hit ranks hardest
        if q == slug or q in single_aliases:
            score += 10
        if score:
            scored.append((score, slug, e))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [(slug, e) for _, slug, e in scored[:limit]]
