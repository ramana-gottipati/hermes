"""home/demo.py — representative preview data (owner directive, 2026-07-23).

When a live read is empty, the zones fall back to this representative data so the PREVIEW shows the
full, tile-dense experience instead of empty panels — "if the plan can't be realised for limited
availability, generate the data." This is illustrative preview content ONLY; the real product
renders live data whenever it exists (each zone uses `live_read() or demo.X`), and the fence marks
the surface as a preview.
"""
from __future__ import annotations

GLOBAL = [
    {"name": "DOW", "value": "44,120", "chg": 0.35},
    {"name": "NASDAQ", "value": "20,540", "chg": 0.62},
    {"name": "USD/INR", "value": "83.42", "chg": -0.08},
    {"name": "GOLD", "value": "71,850", "chg": 0.44},
    {"name": "CRUDE", "value": "$81.2", "chg": -0.55},
]
INDEX = [
    {"index_name": "NIFTY 50", "close_value": 24218.4, "ret_1d_pct": 0.71},
    {"index_name": "SENSEX", "close_value": 79486.3, "ret_1d_pct": 0.63},
    {"index_name": "NIFTY BANK", "close_value": 52140.0, "ret_1d_pct": 0.28},
    {"index_name": "NIFTY 500", "close_value": 22910.5, "ret_1d_pct": 0.55},
]
SERIES = [38, 40, 39, 42, 45, 44, 47, 49, 48, 52, 55, 54, 58, 61, 60, 63]
MOOD_INPUTS = (64.0, True)                       # breadth 64% · Nifty above its 200-DMA
BREADTH = {"d": "2026-07-23", "adv": 1187, "dec": 824, "pct_adv": 59.0}
FII_DII = [
    {"trade_date": "2026-07-23", "category": "FII/FPI", "net_value": -1240.0},
    {"trade_date": "2026-07-23", "category": "DII", "net_value": 860.0},
]
SEVERITY = {"critical": 3, "high": 7, "opportunity": 11, "risk": 5, "total": 26}
WHATCHANGED = [
    {"symbol": "TATASTEEL", "lens": "dvpt", "from_state": "NORMAL", "to_state": "ABOVE_BAND", "as_of": "2026-07-23"},
    {"symbol": "INFY", "lens": "rs", "from_state": "INSIDE", "to_state": "LEADING", "as_of": "2026-07-23"},
    {"symbol": "LT", "lens": "quality", "from_state": "WATCH", "to_state": "PASS", "as_of": "2026-07-22"},
    {"symbol": "MARUTI", "lens": "mep", "from_state": "NEUTRAL", "to_state": "ACCUM", "as_of": "2026-07-22"},
]
CA = [
    {"symbol": "TCS", "action_type": "Dividend", "ex_date": "2026-07-25", "ratio_from": None, "ratio_to": None, "details": "Rs 27"},
    {"symbol": "INFY", "action_type": "Dividend", "ex_date": "2026-07-28", "ratio_from": None, "ratio_to": None, "details": "Rs 18"},
    {"symbol": "RELIANCE", "action_type": "Bonus", "ex_date": "2026-08-02", "ratio_from": "1", "ratio_to": "1", "details": ""},
    {"symbol": "VBL", "action_type": "Split", "ex_date": "2026-08-05", "ratio_from": "1", "ratio_to": "2", "details": ""},
]
RESULTS = [
    {"symbol": "HDFCBANK", "company": "HDFC Bank", "meeting_date": "2026-07-24", "purpose": "Q1 results + board meeting"},
    {"symbol": "ITC", "company": "ITC", "meeting_date": "2026-07-26", "purpose": "Q1 results"},
    {"symbol": "BAJFINANCE", "company": "Bajaj Finance", "meeting_date": "2026-07-29", "purpose": "Q1 results"},
    {"symbol": "SUNPHARMA", "company": "Sun Pharma", "meeting_date": "2026-07-31", "purpose": "Board meeting - dividend"},
]
NEWS = [
    {"source": "Business Standard", "url": "https://www.business-standard.com",
     "title": "Tata Steel Q1 delivery volumes rise as European operations stabilise", "sent_at": "2026-07-23 11:20"},
    {"source": "Mint", "url": "https://www.livemint.com",
     "title": "RBI keeps repo rate unchanged; stance stays neutral", "sent_at": "2026-07-23 09:05"},
    {"source": "ET Markets", "url": "https://economictimes.indiatimes.com",
     "title": "Reliance board to consider bonus issue at July meeting", "sent_at": "2026-07-23 07:40"},
]
DELIVERY = [
    {"symbol": "RELIANCE", "power_dvpt_3m": 3.4},
    {"symbol": "TATASTEEL", "power_dvpt_3m": 2.8},
    {"symbol": "INFY", "power_dvpt_3m": 2.1},
    {"symbol": "HDFCBANK", "power_dvpt_3m": 1.6},
]

# ── the market-pulse instrument deck ──────────────────────────────────────────────
# ~30 sessions of internals for the trend sparklines (breadth · delivery% · MEP · dispersion)
INTERNALS = [
    {"pct_adv": p, "avg_dp": d, "mep_net": m, "disp": s}
    for p, d, m, s in [
        (44, 52, 9.1, 2.10), (62, 53, 11.0, 2.20), (58, 55, 10.2, 2.15), (41, 54, 12.8, 2.30),
        (55, 56, 14.6, 2.25), (67, 55, 13.9, 2.20), (74, 57, 15.7, 2.26), (71, 56, 16.6, 2.20),
        (66, 54, 16.1, 2.28), (70, 55, 16.9, 2.25), (79, 56, 17.2, 2.24), (74, 56, 16.9, 2.26),
    ]
]
NEW_HIGHS = {"highs": 84, "near": 213}
SECTOR_HEAT = [
    {"sector": "Nifty IT", "rs": 1.2}, {"sector": "Nifty Auto", "rs": 0.9},
    {"sector": "Nifty Metal", "rs": 0.6}, {"sector": "Nifty Energy", "rs": 0.3},
    {"sector": "Nifty FMCG", "rs": -0.2}, {"sector": "Nifty Pharma", "rs": -0.5},
    {"sector": "Nifty Realty", "rs": -1.1},
]

# ── featured card: watchlist · portfolio · movers ────────────────────────────────
WATCHLIST = [
    {"symbol": "RELIANCE", "pct": 1.24, "trend": "LEADING", "rank": 88, "deliv": 61},
    {"symbol": "TATASTEEL", "pct": 2.03, "trend": "IMPROVING", "rank": 74, "deliv": 58},
    {"symbol": "INFY", "pct": -0.42, "trend": "INSIDE", "rank": 52, "deliv": 47},
    {"symbol": "HDFCBANK", "pct": 0.38, "trend": "INSIDE", "rank": 55, "deliv": 49},
    {"symbol": "MARUTI", "pct": -0.91, "trend": "WEAKENING", "rank": 33, "deliv": 44},
]
PORTFOLIO = {
    "rows": [
        {"symbol": "RELIANCE", "pct": 1.24, "weight": 18.0, "since": 24.0},
        {"symbol": "HDFCBANK", "pct": 0.38, "weight": 14.0, "since": 11.0},
        {"symbol": "INFY", "pct": -0.42, "weight": 11.0, "since": -3.0},
        {"symbol": "TCS", "pct": 0.22, "weight": 9.0, "since": 31.0},
    ],
    "invested": 23_400_000.0, "day_pnl": 142_000.0, "day_pct": 0.61, "n": 14,
}
MOVERS = {
    "gainers": [{"symbol": "HUDCO", "pct": 9.2}, {"symbol": "IDEA", "pct": 7.1},
                {"symbol": "YESBANK", "pct": 5.4}, {"symbol": "IRFC", "pct": 4.6}],
    "losers": [{"symbol": "PAYTM", "pct": -5.3}, {"symbol": "ZOMATO", "pct": -4.1},
               {"symbol": "IDFCFIRSTB", "pct": -3.8}, {"symbol": "BANDHANBNK", "pct": -3.1}],
}
