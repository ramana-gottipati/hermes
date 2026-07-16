"""TEMPORARY, RUNTIME-ONLY quarantine of stocks whose split/bonus data cannot be trusted.

Ramana, 2026-07-16: "Whatever stocks you think have issues with a stock split should be avoided
for now... mark those stocks temporarily, but do not make any permanent markings, and allow us to
correct them later... If an entry is correct, we can proceed with the split; if it is incorrect,
we should exclude it from our sampling."

WHAT THIS IS NOT: it does NOT write to the database. It does NOT modify corporate_actions. It is a
list computed at runtime, every run, from evidence. Delete this file and nothing is lost.

THE TEST (evidence-based, no inference, no memory):
  corporate_actions is COMPLETE and CURRENT — verified against NSE across 2006/2010/2014/2018/
  2022/2025 (56/56, 117/117, 46/46, 55/55, 110/110, 108/108) and fresh to 2026-07-15.
  The ADJUSTMENT works: across all 1,121 recorded SPLIT/BONUS events the median jump across the
  ex-date goes -51.4% (raw) -> +1.9% (adjusted); events dropping <-30% go 88.4% -> 2.6%.
  THE RESIDUAL 2.6% (~29 events) are events NSE CONFIRMS happened but whose stored RATIO is wrong
  (e.g. MMTC 2010-07-29 BONUS: raw -93.9% -> adjusted -87.8%; the true factor is ~16x, ~1.5x was
  applied). Those stocks would be read as an 80-90% loss they never took.

WHY QUARANTINE INSTEAD OF INFERRING THE RATIO: inference was tried once today and produced 522
phantom splits, because ~20% of random crashes land on a round ratio by chance (ledger 15S). NSE
confirming the EVENT would make ratio-inference far safer here -- but a stock CAN genuinely crash
on a bonus ex-date, and after eight retractions the cheaper error is to drop 2.6% of the data.
The quarantined names are listed so they can be repaired properly later.
"""
from collections import defaultdict


def _jump(book, sym, ex):
    ds = sorted(book.get(sym, {}))
    prev = [d for d in ds if d < ex]
    post = [d for d in ds if d >= ex]
    if not prev or not post:
        return None
    a, b = book[sym][prev[-1]], book[sym][post[0]]
    return (b / a - 1.0) if a > 0 else None


def build(conn, raw_closes, adj_closes, threshold=-0.30):
    """Return (quarantined_symbols, detail_rows).

    A symbol is quarantined if ANY corporate action NSE recorded for it still shows a jump worse
    than `threshold` AFTER adjustment -- i.e. we hold the event but the ratio cannot be trusted.
    """
    evs = list(conn.execute("""
        SELECT symbol, ex_date, action_type FROM corporate_actions
        WHERE action_type IN ('SPLIT','BONUS') AND ex_date IS NOT NULL"""))
    bad, detail = set(), []
    for sym, ex, at in evs:
        a_ = _jump(adj_closes, sym, ex)
        if a_ is None:
            continue
        if a_ < threshold:
            r_ = _jump(raw_closes, sym, ex)
            bad.add(sym)
            detail.append((sym, ex, at, r_, a_))
    detail.sort(key=lambda t: t[4])
    return bad, detail


def report(bad, detail, universe_size=None):
    print(f"[quarantine] {len(bad)} symbols TEMPORARILY excluded "
          f"({len(detail)} untrustworthy split/bonus events)")
    if universe_size:
        print(f"[quarantine] that is {len(bad)/universe_size*100:.2f}% of the symbol universe")
    for sym, ex, at, r_, a_ in detail[:10]:
        rs = f"{r_*100:+.1f}%" if r_ is not None else "  n/a"
        print(f"   {sym:<12} {ex}  {at:<6} raw {rs:>8} -> adj {a_*100:+7.1f}%")
    if len(detail) > 10:
        print(f"   ... and {len(detail)-10} more")
    print("[quarantine] RUNTIME ONLY — nothing written to the DB; repair the ratios later and this "
          "list shrinks by itself")
