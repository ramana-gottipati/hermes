"""High-conviction mode: few strong signals, not a 25-stock basket.
(A) Honest backtest of concentration (top 3/5/10) — return vs drawdown.
(B) TODAY's high-conviction shortlist: the strongest names by 12-month momentum AND
    risk-adjusted momentum; the OVERLAP = highest conviction; flag valuation + any genuine
    institutional buyer from the deals feed.
"""
import os, pickle, importlib.util
import numpy as np
from explosive_moves.embase import load_symbol_cache
from explosive_moves.strategies import CR
from explosive_moves.common import main_conn

CPS = 0.005
cache = load_symbol_cache()

# ---------- (A) concentration backtest ----------
TBL = pickle.load(open("/opt/hermes/data/search_tbl.pkl", "rb"))


def bt(sig, topn, lo, hi):
    rets, prev = [], set()
    for t in TBL:
        if not (lo <= t["d0"] <= hi):
            continue
        m6, vol, mom12, fwd, mt = t["mom6"], t["vol"], t["mom12"], t["fwd"], t["mt"]
        sc = (m6 / (vol + 1e-6)) if sig == "riskadj" else mom12
        sc = np.where(mt >= 5 * CR, sc, np.nan)
        valid = ~np.isnan(sc) & ~np.isnan(fwd); idx = np.where(valid)[0]
        if len(idx) < topn:
            rets.append(0.0); continue
        top = idx[np.argsort(sc[idx])[::-1]][:topn]; picks = set(t["sym"][i] for i in top)
        g = float(np.mean(fwd[top])); turn = (len(picks - prev) + len(prev - picks)) / max(len(picks), 1)
        rets.append(g - CPS * turn); prev = picks
    rets = np.array(rets); eq = np.cumprod(1 + rets); pk = np.maximum.accumulate(eq)
    dd = (eq / pk - 1).min(); cagr = eq[-1] ** (1 / (len(eq) / 12)) - 1
    return cagr, dd

print("(A) HOW FEW NAMES TRADES OFF — concentration (monthly, net of cost, 2019-26):")
print(f"   {'names':6}{'signal':9}{'CAGR':>8}{'MaxDD':>8}")
for topn in (3, 5, 10):
    for sig in ("mom12", "riskadj"):
        c, d = bt(sig, topn, "2019-01-01", "2026-12-31")
        print(f"   top-{topn:<3}{sig:9}{c*100:>7.1f}%{d*100:>7.1f}%")

# ---------- (B) today's high-conviction shortlist ----------
# latest date
latest = max(A["date"][-1] for A in cache.values())
rowsR, rowsM = [], []
for s, A in cache.items():
    d2i = {d: i for i, d in enumerate(A["date"])}
    i = d2i.get(latest)
    if i is None or i < 260 or not (A["med_turn"][i] >= 5 * CR):
        continue
    ac = A["adj_close"]; v = A["feats"]["vol_66"][i]
    if v != v or v <= 0:
        continue
    mom6 = ac[i] / ac[i - 126] - 1 if i >= 126 else np.nan
    mom12 = ac[i] / ac[i - 252] - 1 if i >= 252 else np.nan
    ext5y = ac[i] / ac[i - 1250] - 1 if i >= 1250 else np.nan
    if mom6 == mom6:
        rowsR.append((mom6 / v, s, mom6, mom12, ext5y, A["med_turn"][i]))
    if mom12 == mom12:
        rowsM.append((mom12, s, mom6, mom12, ext5y, A["med_turn"][i]))
rowsR.sort(reverse=True); rowsM.sort(reverse=True)
topR = {r[1] for r in rowsR[:15]}; topM = {r[1] for r in rowsM[:15]}
overlap = topR & topM

# institutional buyers today
mc = main_conn()
spec = importlib.util.spec_from_file_location("cc", "/opt/hermes/src/automation/client_classify.py")
cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)
Td = mc.execute("SELECT MAX(trade_date) FROM bulk_block_deals").fetchone()[0]
buyrows = mc.execute("SELECT symbol, client_name, side, SUM(qty) q FROM bulk_block_deals WHERE trade_date=? GROUP BY symbol,client_name,side", (Td,)).fetchall()
agg = {}
for r in buyrows:
    a = agg.setdefault((r[0], r[1]), {"BUY": 0, "SELL": 0}); a[r[2]] = a.get(r[2], 0) + (r[3] or 0)
genu = set()
for (sym, cl), a in agg.items():
    b, sl = a.get("BUY", 0), a.get("SELL", 0); tot = b + sl
    if tot > 0 and cc.classify_client(cl) not in cc.CHURN and (b - sl) > 0 and abs(b - sl) / tot >= 0.6:
        genu.add(sym)
mc.close()

print(f"\n(B) TODAY'S HIGH-CONVICTION SHORTLIST (as of {latest}, >=Rs 5cr/day)")
print(f"\n*** HIGHEST CONVICTION — strong on BOTH 12-mo momentum AND risk-adjusted ({len(overlap)}): ***")
info = {r[1]: r for r in rowsM}
for s in sorted(overlap, key=lambda x: -info[x][3]):
    _, _, m6, m12, ext, mt = info[s]
    inst = "  +INSTITUTION BUYING" if s in genu else ""
    print(f"   {s:12} 12mo {m12*100:+.0f}%  6mo {m6*100:+.0f}%  5yr {('%.0f%%'%(ext*100)) if ext==ext else 'n/a':>6}  Rs{mt/1e7:.0f}cr{inst}")
print(f"\nStrong on 12-month momentum (top 10):")
for sc, s, m6, m12, ext, mt in rowsM[:10]:
    print(f"   {s:12} 12mo {m12*100:+.0f}%  Rs{mt/1e7:.0f}cr{'  +INST' if s in genu else ''}")
