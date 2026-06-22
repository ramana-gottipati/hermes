"""Daily cross-check: Launchpad setup ∩ genuine institutional net buyer.

For the latest trading day:
  1. From bulk_block_deals, aggregate each client's net in each stock; classify
     (client_classify). A GENUINE NET BUYER = non-churn category, one-sided
     (|net|/(buy+sell) >= 0.6), net > 0.
  2. For each such stock, compute the validated Launchpad flags from bhavcopy:
       MOM_CONT  : ret_22d>7% AND volume-not-expanding(vol_ratio_22_66<=1.48) AND range_tight_22>0.096
       PULLBACK  : ret_22d<=7% AND vol_66>2.4% AND ret_1d<=-2.2%
       COILED    : vol contracting (vol_22/vol_66<1) AND ret_22d>=10%
  3. ⭐ = a stock that is BOTH set up AND has a genuine net buyer today.

Read-only over hermes.db. Runs in the research venv.
"""
from __future__ import annotations
import importlib.util
import numpy as np
from .common import main_conn, load_series, LIQ_FLOOR

_CC = "/opt/hermes/src/automation/client_classify.py"


def _load_cc():
    spec = importlib.util.spec_from_file_location("client_classify", _CC)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


cc = _load_cc()


def genuine_net_buyers(con, date):
    rows = con.execute(
        "SELECT symbol, client_name, side, SUM(qty) q FROM bulk_block_deals "
        "WHERE trade_date=? GROUP BY symbol, client_name, side", (date,)).fetchall()
    agg = {}
    for r in rows:
        a = agg.setdefault((r["symbol"], r["client_name"]), {"BUY": 0, "SELL": 0})
        a[r["side"]] = a.get(r["side"], 0) + (r["q"] or 0)
    bysym, cats = {}, {}
    for (sym, client), a in agg.items():
        b, s = a.get("BUY", 0), a.get("SELL", 0)
        tot = b + s
        if tot <= 0:
            continue
        cat = cc.classify_client(client)
        cats[cat] = cats.get(cat, 0) + 1
        net = b - s
        if cat not in cc.CHURN and net > 0 and abs(net) / tot >= 0.6:
            bysym.setdefault(sym, []).append((client, cat, net))
    return bysym, cats


def launchpad_flags(ss, s):
    ac, v = ss.adj_close, ss.volume
    def ret(k):
        j = s - k
        return ac[s] / ac[j] - 1.0 if j >= 0 and ac[j] > 0 else np.nan
    ret_1, ret_22 = ret(1), ret(22)
    lr = np.diff(np.log(np.clip(ac[max(0, s - 66):s + 1], 1e-9, None)))
    vol66 = float(np.nanstd(lr)) if len(lr) >= 30 else np.nan
    vol22 = float(np.nanstd(lr[-22:])) if len(lr) >= 22 else np.nan
    vratio = vol22 / vol66 if vol66 else np.nan
    seg = ac[max(0, s - 21):s + 1]
    rng = (np.nanmax(seg) - np.nanmin(seg)) / np.nanmean(seg) if len(seg) else np.nan
    vr_vol = (np.nanmean(v[max(0, s - 21):s + 1]) / np.nanmean(v[max(0, s - 65):s + 1])
              if np.nanmean(v[max(0, s - 65):s + 1]) else np.nan)
    flags = []
    if ret_22 == ret_22:
        if ret_22 > 0.07 and vr_vol <= 1.48 and rng > 0.096:
            flags.append("MOM_CONT")
        if ret_22 <= 0.07 and vol66 > 0.024 and ret_1 <= -0.022:
            flags.append("PULLBACK")
        if vratio == vratio and vratio < 1 and ret_22 >= 0.10:
            flags.append("COILED")
    return flags, {"ret22": ret_22, "vol66": vol66, "vratio": vratio,
                   "med_turn": float(ss.med_turn[s]) if s < len(ss.med_turn) else np.nan}


def main():
    mc = main_conn()
    T = mc.execute("SELECT MAX(trade_date) FROM bhavcopy_rows WHERE series='EQ'").fetchone()[0]
    Td = mc.execute("SELECT MAX(trade_date) FROM bulk_block_deals").fetchone()[0]
    ndeals = mc.execute("SELECT COUNT(*) FROM bulk_block_deals WHERE trade_date=?", (Td,)).fetchone()[0]
    print(f"Latest bhav day: {T} | latest deals day: {Td} ({ndeals} deals)\n")

    bysym, cats = genuine_net_buyers(mc, Td)
    churn = sum(n for c, n in cats.items() if c in cc.CHURN)
    genu = sum(n for c, n in cats.items() if c not in cc.CHURN)
    print("Client-category breakdown of the day's deals (client·stock pairs):")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        tag = "  <- CHURN" if c in cc.CHURN else ""
        print(f"   {c:12s} {n}{tag}")
    print(f"   => churn {churn} vs genuine {genu}")
    print(f"\n{len(bysym)} stocks with a GENUINE one-sided NET BUYER today.\n")

    star, other = [], []
    for sym, buyers in bysym.items():
        ss = load_series(mc, sym)
        if ss is None:
            continue
        s = {d: i for i, d in enumerate(ss.date)}.get(T, ss.n - 1)
        flags, m = launchpad_flags(ss, s)
        liquid = m["med_turn"] >= LIQ_FLOOR
        rec = (sym, flags, m, buyers, liquid)
        (star if (flags and liquid) else other).append(rec)

    print("=" * 70)
    print("⭐ LAUNCHPAD ∩ GENUINE NET BUYER (the high-conviction intersection):")
    if not star:
        print("   (none today — expected on a single day; this is the daily product)")
    for sym, flags, m, buyers, liquid in sorted(star, key=lambda x: -x[2]["med_turn"]):
        print(f"  {sym:12s} [{','.join(flags)}] ret22={m['ret22']:+.0%} volρ={m['vratio']:.2f} "
              f"₹{m['med_turn']/1e7:.1f}cr")
        for cl, cat, net in buyers:
            print(f"        + {cat:8s} {cl[:40]} net {net:,}")
    print("\n— genuine net buyers today WITHOUT a liquid Launchpad setup (watch):")
    for sym, flags, m, buyers, liquid in other:
        nm = "; ".join(f"{cat}:{cl[:22]}" for cl, cat, net in buyers)
        note = ("[" + ",".join(flags) + (" but <₹1cr]" if not liquid else "]")) if flags else ""
        print(f"  {sym:12s} ret22={m['ret22']:+.0%} {note} — {nm}")
    mc.close()


if __name__ == "__main__":
    main()
