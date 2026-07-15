"""Best-available strategies — the decision menu, CLEAN universe.

Universe = current Nifty 500 constituents (real, listed equities — no delisted ghosts,
no liquid/ETF funds) that are still trading as of the cache's latest date. For each
surviving candidate, print its current top-25 holdings so a human can choose from real
portfolios. Honest metrics live in docs/strategy-ledger.md. Read-only.

METRIC BASIS (D142): every ratio quoted here is mean/sd annualised with NO risk-free rate
subtracted — a return/vol ratio, not a Sharpe; it reads high against a textbook Sharpe. The
Nifty 500 0.89 bar is on the SAME basis, so the "none beats the index" verdict is unaffected.
"""
import sqlite3
import sys
import numpy as np
sys.path.insert(0, "/opt/hermes/research")
from explosive_moves.embase import load_symbol_cache
from explosive_moves.factory import pctrank

HDB = "/opt/hermes/data/hermes.db"
TOPN = 25


def nifty500_set():
    c = sqlite3.connect(HDB)
    try:
        snap = c.execute("SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name='Nifty 500'").fetchone()[0]
        rows = c.execute("SELECT DISTINCT symbol FROM stock_index_membership WHERE index_name='Nifty 500' AND snapshot_date=?", (snap,)).fetchall()
        return {r[0] for r in rows}, snap
    finally:
        c.close()


def main():
    cache = load_symbol_cache()
    universe, snap = nifty500_set()
    # global latest trading date across the cache
    maxd = max(A["date"][-1] for A in cache.values())
    rec = []
    for s, A in cache.items():
        if s not in universe:
            continue
        ac, mt, F, dates = A["adj_close"], A["med_turn"], A["feats"], A["date"]
        if dates[-1] < maxd[:8] + "01":          # last bar must be in the latest month -> still trading
            continue
        i0 = len(ac) - 1
        if i0 < 260 or not (ac[i0] > 0):
            continue
        mom6 = ac[i0] / ac[i0 - 126] - 1.0
        vol = float(F["vol_66"][i0])
        if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0):
            continue
        rec.append({"s": s, "date": dates[i0], "mom6": mom6, "vol": vol,
                    "riskadj": mom6 / (vol + 1e-6), "lowvol": -vol})
    g = rec
    m6 = pctrank(np.array([x["mom6"] for x in g])); lv = pctrank(np.array([x["lowvol"] for x in g]))
    for k, x in enumerate(g):
        x["lowvolmom"] = 0.5 * lv[k] + 0.5 * m6[k]
        x["lowvol_sc"] = lv[k]; x["riskadj_sc"] = x["riskadj"]

    def top(score):
        return [x["s"] for x in sorted(g, key=lambda z: -z[score])[:TOPN]]

    print(f"Universe = Nifty 500 (snapshot {snap}), still-trading: {len(g)} names | as of {max(x['date'] for x in g)}\n")
    menu = [
        ("A. DEFENSIVE — Low-Vol + Momentum (best cost survivor)", "lowvolmom",
         "return/vol 0.79 / CAGR 13.3% / MaxDD -25% / cost 8.3% / cap Rs190cr"),
        ("B. SMOOTHEST — pure Low-Vol", "lowvol_sc",
         "return/vol 0.78 / CAGR 9.6% / MaxDD -23% / cost 5.4% / cap Rs168cr"),
        ("C. HIGHEST-MOMENTUM — Risk-Adjusted (aggressive, higher cost)", "riskadj_sc",
         "return/vol 0.51 / CAGR 10.2% / MaxDD -43% / cost 15.1% / cap Rs97cr"),
    ]
    board = []
    for name, key, metrics in menu:
        print("=" * 92)
        print(name + "\n  " + metrics)
        names = top(key)
        for i in range(0, TOPN, 5):
            print("   " + "  ".join(f"{n:<13}" for n in names[i:i + 5]))
        print()
        board.append({"name": name, "metrics": metrics, "holdings": names})
    print("=" * 92)
    print("BASELINE the above must beat: Nifty 500 buy & hold = return/vol 0.89 / CAGR 15.3% / MaxDD -29%")
    asof = max(x["date"] for x in g)
    write_html(board, snap, asof, len(g))
    # persist holdings into the registry so they stop hiding in a static file
    try:
        import sqlite3
        from explosive_moves import strategy_store as ss
        con = sqlite3.connect(ss.RDB); ss.ensure_schema(con)
        for b in board:
            ss.set_holdings(con, b["name"].split(" —")[0].strip(), asof, b["holdings"])
        con.commit(); con.close()
        print("holdings persisted -> research.db strategy_holdings")
    except Exception as e:
        print("holdings persist skipped:", e)


def write_html(board, snap, asof, n):
    import os
    cards = ""
    palette = ["#34d399", "#5ec8ff", "#e6b450"]
    for i, s in enumerate(board):
        chips = "".join(f"<span class='chip'>{h}</span>" for h in s["holdings"])
        cards += (f"<div class='card' style='border-top:3px solid {palette[i]}'>"
                  f"<div class='cn'>{s['name']}</div><div class='cm'>{s['metrics']}</div>"
                  f"<div class='chips'>{chips}</div></div>")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Strategy Board</title>
<style>
body{{background:#0e1116;color:#e8ecf1;font-family:'Inter',-apple-system,Segoe UI,Arial,sans-serif;margin:0;padding:26px}}
h1{{font-size:13px;letter-spacing:.3em;color:#5ec8ff;margin:0 0 4px}}
.sub{{color:#8b97a7;font-size:12px;font-family:monospace;margin-bottom:6px}}
.bar{{background:#161b22;border:1px solid #262e39;border-radius:10px;padding:12px 16px;margin:14px 0;font-size:13px}}
.bar b{{color:#e8ecf1}} .bar .idx{{color:#34d399;font-family:monospace}}
.card{{background:#161b22;border:1px solid #262e39;border-radius:14px;padding:16px 18px;margin:14px 0}}
.cn{{font-size:16px;font-weight:700;margin-bottom:4px}} .cm{{color:#8b97a7;font-family:monospace;font-size:12px;margin-bottom:12px}}
.chips{{display:flex;flex-wrap:wrap;gap:7px}}
.chip{{background:#1c232d;border:1px solid #262e39;border-radius:7px;padding:5px 9px;font-size:11.5px;font-family:monospace;color:#cdd6e0}}
.note{{color:#8b97a7;font-size:11px;margin-top:18px;border-top:1px solid #262e39;padding-top:12px;line-height:1.6}}
</style></head><body>
<h1>HERMES · STRATEGY BOARD</h1>
<div class="sub">Best-available strategies — current top-25 holdings · universe Nifty 500 (snapshot {snap}, {n} live names) · as of {asof}</div>
<div class="bar">⚖️ <b>The bar these must beat:</b> <span class="idx">Nifty 500 buy &amp; hold — return/vol 0.89 / CAGR 15.3% / MaxDD −29%</span>. None below beats it on return/vol — so this is a <b>risk-profile choice, not alpha</b>. Human decides.</div>
{cards}
<div class="note"><b>Honest notes.</b> Metrics are net of realistic per-name cost (tier spread + 0.5×ATR slippage), walk-forward 2012–26. Holdings regenerate from <code>strategy_menu.py</code>. Universe filtered to live Nifty 500 constituents (no delisted tickers, no liquid/cash ETFs). This is a research artifact, not investment advice.</div>
</body></html>"""
    out = os.path.join(os.path.dirname(__file__), "out", "strategy_board.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"\nHTML board -> out/strategy_board.html ({len(html)} bytes)")


if __name__ == "__main__":
    main()
