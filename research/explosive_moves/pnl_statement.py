"""Plain-money P&L: invest Rs 10 lakh in Jan 2019, year-by-year profit/loss.

Compares the FIXED strategy (v2: risk-adj momentum + buffer + vol-target, no stop) vs the
BROKEN one (v1: with the stop-loss) vs just buying a Nifty 500 index fund. Shows whether
fixing the problems actually made more money — in rupees.
"""
import numpy as np
from explosive_moves.v2_backtest import run
from explosive_moves.metrics import index_series

START = 1_000_000   # Rs 10 lakh


def yearly(daily, dates, start=START):
    bal = start; ys = bal; cur = dates[0][:4]; rows = []; series = []
    for d, r in zip(dates, daily):
        if d[:4] != cur:
            rows.append((cur, ys, bal, bal - ys, bal / ys - 1)); ys = bal; cur = d[:4]
        bal *= (1 + r); series.append(bal)
    rows.append((cur, ys, bal, bal - ys, bal / ys - 1))
    s = np.array(series); peak = np.maximum.accumulate(s); ddr = (s / peak - 1).min()
    return rows, bal, ddr * peak[np.argmin(s / peak)]   # max drawdown in rupees (approx)


v2 = run(score="riskadj", exit_top=40, vtarget=0.25, use_sl=False)
v1 = run(score="riskadj", exit_top=25, vtarget=None, use_sl=True)
r2, fin2, dd2 = yearly(v2["daily"], v2["dates"])
r1, fin1, dd1 = yearly(v1["daily"], v1["dates"])

# Nifty 500 index fund, same dates
di, ci = index_series("Nifty 500"); mp = {d: ci[i] for i, d in enumerate(di)}
ds = [d for d in v2["dates"] if d in mp]
ix = [mp[d] for d in ds]
ixdaily = [0.0] + [ix[i] / ix[i - 1] - 1 for i in range(1, len(ix))]
ri, fini, ddi = yearly(ixdaily, ds)

print("INVEST Rs 10,00,000 (10 lakh) on 1-Jan-2019\n")
print(f"{'Year':6}{'FIXED v2 P&L':>16}{'v2 balance':>14}   |{'Index P&L':>14}{'Index balance':>15}")
ix_by_year = {r[0]: r for r in ri}
for y, ys, ye, pnl, ret in r2:
    iy = ix_by_year.get(y)
    ip = iy[3] if iy else 0; ib = iy[2] if iy else 0
    print(f"{y:6}{pnl:>+12,.0f}({ret*100:>+4.0f}%){ye:>14,.0f}   |{ip:>+10,.0f}({(iy[4] if iy else 0)*100:>+4.0f}%){ib:>15,.0f}")

print(f"\n{'='*70}")
print(f"FINAL (mid-2026):")
print(f"  FIXED v2 strategy : Rs {fin2:,.0f}   (profit Rs {fin2-START:,.0f}, {(fin2/START-1)*100:.0f}% total)")
print(f"  Nifty 500 fund    : Rs {fini:,.0f}   (profit Rs {fini-START:,.0f}, {(fini/START-1)*100:.0f}% total)")
print(f"  BROKEN v1 (w/stop): Rs {fin1:,.0f}   (profit Rs {fin1-START:,.0f}, {(fin1/START-1)*100:.0f}% total)")
print(f"\nDID FIXING IT HELP?  v1 -> v2 = Rs {fin1:,.0f} -> Rs {fin2:,.0f}  (+Rs {fin2-fin1:,.0f} more)")
worst = min(r2, key=lambda x: x[4])
print(f"\nWorst year (v2): {worst[0]} lost Rs {-worst[3]:,.0f} ({worst[4]*100:.0f}%)")
print(f"Deepest dip (v2): about Rs {-dd2:,.0f} from a peak (~-31%) before recovering")
