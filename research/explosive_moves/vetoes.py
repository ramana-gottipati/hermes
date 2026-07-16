"""TWO VETO LAYERS — BE-surveillance and fundamentals red-flags. Both PIT, both optional.

Ramana, 2026-07-16: approved both, with the condition "I also want to track the picks without
fundamentals also, because at times financials speak late." => EVERY config runs twice, with and
without the fundamentals veto, so its cost and benefit are visible rather than baked in.

VETO 1 — BE SURVEILLANCE (free, no new data, fully backfilled 2004-2026: 173-766 symbols/yr).
  Ledger 15L found strong-RS stocks get moved to NSE's BE (trade-to-trade) surveillance series MORE
  often than average -- the regulator independently flagging exactly the kind of move a top-decile
  RS filter is drawn to. 15P found the top decile's problem is VOLATILITY (sd 26.63%/qtr, a 3.55%
  variance toll against a 1.97% edge). HYPOTHESIS: a meaningful share of that excess volatility is
  surveillance-flagged speculative names, so vetoing BE shrinks the toll WITHOUT touching the signal.
  PIT: uses only the series a stock traded in ON/BEFORE the rebalance date.

VETO 2 — FUNDAMENTALS RED FLAGS (veto-only, never a ranker).
  Grounded in this project's OWN standing result: "Momentum [is the] only surviving factor -- but
  it's BETA not skill (t=1.99); C/A/B stay veto-only." So: NOT "rank by ROE" -- disqualify red flags.
  PIT: only uses filings whose report_date <= the rebalance date (no look-ahead into results not yet
  published).
  RED FLAGS (each a hard disqualify, all from real columns in fundamentals_history):
    - Net Profit < 0 in the most recent reported year        (loss-making)
    - Reserves < 0                                            (negative net worth)
    - Interest > Operating Profit                             (debt servicing exceeds earnings)
    - OPM % < 0                                               (operating loss)
  DISCLOSURE (Guardrail #8): fundamentals_history is the SCREENER-sourced table flagged as the known
  exception being remediated. This uses it READ-ONLY for a veto test -- not an extension, but it is
  NOT a primary source and any result depending on it inherits that caveat. The BE veto has no such
  problem (NSE bhavcopy = primary).
"""
from collections import defaultdict


def load_be_history(conn):
    """symbol -> sorted list of (yyyy-mm, True) months where it traded in BE.
    PIT-safe: we only ever ask 'was it BE on or before date d'."""
    be = defaultdict(set)
    for s, ym in conn.execute("""SELECT DISTINCT symbol, substr(trade_date,1,7)
                                 FROM bhavcopy_rows WHERE series='BE'"""):
        be[s].add(ym)
    return be


def be_flagged(be, sym, d, lookback_months=6):
    """Was this symbol in BE surveillance at any point in the lookback window ending at d?
    Uses ONLY months <= d. lookback_months=0 means 'BE in the current month only'."""
    months = be.get(sym)
    if not months:
        return False
    y, m = int(d[:4]), int(d[5:7])
    for k in range(lookback_months + 1):
        yy, mm = y, m - k
        while mm <= 0:
            mm += 12; yy -= 1
        if "%04d-%02d" % (yy, mm) in months:
            return True
    return False


def load_fundamentals(rconn):
    """symbol -> sorted [(report_date, {metric: value})]. PIT via report_date, NOT period_end:
    a FY2011 result published in 2011-08 must not be visible in 2011-04."""
    rows = defaultdict(lambda: defaultdict(dict))
    q = """SELECT symbol, report_date, metric, value FROM fundamentals_history
           WHERE report_date IS NOT NULL AND value IS NOT NULL
             AND metric IN ('Net Profit','Reserves','Interest','Operating Profit','OPM %','Sales')"""
    for sym, rd, metric, val in rconn.execute(q):
        try:
            rows[sym][rd][metric] = float(val)
        except (TypeError, ValueError):
            continue
    out = {}
    for sym, byrd in rows.items():
        out[sym] = sorted(byrd.items())
    return out


def fundamentals_veto(fund, sym, d):
    """True = DISQUALIFY. Only looks at filings with report_date <= d.
    Returns False (allow) when we have no data -- absence of evidence is not a red flag; that keeps
    the veto from silently becoming a coverage filter."""
    hist = fund.get(sym)
    if not hist:
        return False
    latest = None
    for rd, metrics in hist:
        if rd <= d:
            latest = metrics
        else:
            break
    if not latest:
        return False
    np_ = latest.get("Net Profit")
    res = latest.get("Reserves")
    inte = latest.get("Interest")
    op = latest.get("Operating Profit")
    opm = latest.get("OPM %")
    if np_ is not None and np_ < 0:
        return True
    if res is not None and res < 0:
        return True
    if opm is not None and opm < 0:
        return True
    if inte is not None and op is not None and op > 0 and inte > op:
        return True
    return False


def veto_stats(be, fund, symbols, d):
    """diagnostic: how many of `symbols` each veto would remove at date d"""
    nbe = sum(1 for s in symbols if be_flagged(be, s, d))
    nfu = sum(1 for s in symbols if fundamentals_veto(fund, s, d))
    return nbe, nfu
