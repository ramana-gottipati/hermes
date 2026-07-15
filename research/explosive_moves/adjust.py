"""Corporate-action price adjustment — the fix for the bug that voided 15j/15k/15L/15M.

Raw bhavcopy `close` is NOT adjusted for splits/bonuses. A 1:2 bonus reads as -50%; a 10:1 split
reads as -90%. 973 of the 1,489 EQ one-day drops worse than -40% (65%) sit within 3 days of a
corporate action. Index levels ARE adjusted, so every stock-vs-index comparison today was rigged
against the stock. This violated the project's own Guardrail #5 ("Value > quantity ... eliminates
corporate-action adjustment bugs").

CONVENTION (verified against the data, 2026-07-15):
  SPLIT  ratio_from=10, ratio_to=1  -> "Face Value Split From Rs 10/- to Rs 1/-" -> 10:1
         factor = ratio_from / ratio_to
  BONUS  ratio_from=5, ratio_to=1   -> "Bonus 5:1" = 5 new per 1 held -> shares x6
         factor = (ratio_from + ratio_to) / ratio_to
Prices BEFORE an ex_date are divided by the cumulative factor of all later ex_dates.

DIVIDENDS ARE DELIBERATELY NOT ADJUSTED: the benchmark is a PRICE index (Nifty 500 price, not TRI),
so leaving dividends out of both sides keeps the comparison like-for-like. RIGHTS (368) are not
handled -- disclosed, not hidden.
"""
from collections import defaultdict


def load_factors(conn):
    """symbol -> sorted list of (ex_date, factor). Factor > 1 means the price stepped DOWN."""
    fac = defaultdict(list)
    q = """SELECT symbol, action_type, ex_date, ratio_from, ratio_to
           FROM corporate_actions
           WHERE action_type IN ('SPLIT','BONUS')
             AND ratio_from > 0 AND ratio_to > 0 AND ex_date IS NOT NULL"""
    for sym, typ, ex, rf, rt in conn.execute(q):
        if typ == 'SPLIT':
            f = rf / rt
        else:                                   # BONUS: rf new shares per rt held
            f = (rf + rt) / rt
        if f and f > 1.0001:                    # ignore no-ops / malformed
            fac[sym].append((ex, f))
    for s in fac:
        fac[s].sort()
    return fac


def adjust_closes(closes, factors):
    """closes: {date: raw_close} -> {date: adjusted_close}. Divide each price by the product of
    every factor whose ex_date is AFTER it, so the series is continuous across the action."""
    if not factors:
        return closes
    out = {}
    for d, px in closes.items():
        adj = 1.0
        for ex, f in factors:
            if ex > d:
                adj *= f
        out[d] = px / adj
    return out


def adjust_all(sclose, fac):
    n = 0
    for s in list(sclose):
        f = fac.get(s)
        if f:
            sclose[s] = adjust_closes(sclose[s], f)
            n += 1
    return n
