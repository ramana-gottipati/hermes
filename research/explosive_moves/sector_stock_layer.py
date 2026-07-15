"""THE TWO-STEP ENGINE (Ramana's design, verbatim, 2026-07-15): sector selection -> stock
selection. First-pass simulation of the canon's open-item #1 (docs/strategies/sector-rotation.md
Sec.9 #1; ledger Sec.2026-07-15h/i/j; D138/D139/D141). NOT the final ~1,973-symbol PIT-safe build
-- a genuinely primary-sourced, honestly-scoped first cut. Read Sec.2026-07-15j before quoting
any number this prints.

STEP 1 (sector selection) is REUSED UNTOUCHED from the validated V24 engine
(sector_rotation_v24_final.py) -- same qualifying-sector logic, same quarterly clock, same
taper/hysteresis/recovery-accelerator/inverse-vol/own-percentile-RSIRS rules, same residual-
sleeve regime. This module execs that file's own build()/kill_on()/rebal calendar directly; it
does not re-derive or alter the sector layer in any way.

STEP 2 (stock selection) is NEW: within each qualifying sector, rank the sector's stock UNIVERSE
by RS EXCESS vs that stock's OWN SECTOR COMPOSITE (equal-weighted trailing 6m return of the
universe) -- Ramana's own discriminator, verbatim: "if a stock is performing well within its
NARROW index, we will target it." Top names per sector are selected, weighted by
sector-weight x RS-rank, capped per-name, and the WHOLE portfolio is capped at TOTAL_CAP names
(Ramana, 2026-07-15: "set a ceiling of 30 to 35 stocks for a portfolio of about 1 crore").

THE STOCK UNIVERSE -- genuine primary source, one real limitation (disclosed, not buried):
each of V24's 16 sectors' OWN current (2026-07-15) official NSE constituent list
(niftyindices.com/IndexConstituent/<slug>.csv -- the SAME access pattern already used and
approved in src/automation/membership.py), UNION'd with the Nifty-500's current "Industry" tag
wherever a clean, unambiguous match exists (widening e.g. Auto from ~15 to ~39 names) -- both
committed as a dated snapshot in nse_sector_classification_2026-07-15/ so this module is
reproducible without re-fetching. 268 distinct symbols, 16 sectors.

DISCLOSED LIMITATION -- READ BEFORE TRUSTING ANY NUMBER: this universe is CURRENT-DAY
(2026-07-15) classification, applied statically across the whole 2005-2026 backtest. This is
NOT the survivorship trap the ledger already banned (using TODAY's narrow index MEMBERSHIP as
if valid for 2011, which structurally selects names that EARNED their way in by outperforming)
-- industry/sector CLASSIFICATION is not a performance filter, so the bias is structurally much
smaller -- but it is a real, disclosed simplification, and it fails CONSERVATIVE: delisted
companies are EXCLUDED from the universe entirely (not fabricated an assumed performance for),
the opposite failure direction from the banned mistake. The canon's ultimate ~1,973-symbol
PIT-safe classification (incl. ~280 dead names, bias-bounded per its own two-sided design)
remains the owed rigor item; this is a first, honest, working simulation, not that final build.

PRE-REGISTERED BAR (ledger Sec.2026-07-15h/i, canon Sec.9 #1 -- set BEFORE this was run):
stock-level momentum is BETA not skill (t=1.99); only LOWVOL_MOM quarterly large-cap cleared
fundable (1.02 @ Rs50cr); stock legs cost MORE than index legs. MERELY MATCHING V24's
index-only book is a REJECTION, not a result -- it must beat V24 net of realistic stock costs.

Usage: python research/explosive_moves/sector_stock_layer.py [db_path] [stock_cost_bps]
  db_path        default "data/hermes.db"
  stock_cost_bps default 40  (0.40%/side; pass e.g. 15 for gross/same-as-index, 70 for stress)
"""
import sys, os, csv, json, math, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "nse_sector_classification_2026-07-15")
OUT_DIR = os.path.join(HERE, "out")
V24_MODULE = os.path.join(HERE, "sector_rotation_v24_final.py")

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
STOCK_COST = (float(sys.argv[2]) if len(sys.argv) > 2 else 40.0) / 10000.0

TOTAL_CAP = 33          # Ramana, 2026-07-15: "a ceiling of 30 to 35 stocks" -- midpoint
PER_NAME_CAP = 0.12      # no single stock > 12% of the book (retail-diversification discipline)
MAX_PER_SECTOR = 8       # canon Sec.9 spec: ~4-8 names/sector

SLUG = {
    "Nifty Auto": "ind_niftyautolist", "Nifty Bank": "ind_niftybanklist",
    "Nifty Energy": "ind_niftyenergylist", "Nifty FMCG": "ind_niftyfmcglist",
    "Nifty IT": "ind_niftyitlist", "Nifty Pharma": "ind_niftypharmalist",
    "Nifty Infrastructure": "ind_niftyinfralist", "Nifty Media": "ind_niftymedialist",
    "Nifty Metal": "ind_niftymetallist", "Nifty PSU Bank": "ind_niftypsubanklist",
    "Nifty Realty": "ind_niftyrealtylist", "Nifty Financial Services": "ind_niftyfinancelist",
    "Nifty Private Bank": "ind_nifty_privatebanklist", "Nifty Oil & Gas": "ind_niftyoilgaslist",
    "Nifty Consumer Durables": "ind_niftyconsumerdurableslist",
    "Nifty Healthcare Index": "ind_niftyhealthcarelist",
}
# widen the narrow sectoral-index pond with the Nifty-500 Industry tag ONLY where the match is
# unambiguous. Bank/PSU Bank/Private Bank/Financial Services/Infrastructure/Media/Healthcare/
# Pharma are deliberately left UNWIDENED: "Financial Services" spans all 3 bank sub-sectors,
# "Healthcare" spans both Pharma and hospitals with no finer tag in this file, and Capital
# Goods/Services/Construction don't map cleanly to any one V24 sector.
INDUSTRY_WIDEN = {
    "Nifty Auto": {"Automobile and Auto Components"}, "Nifty IT": {"Information Technology"},
    "Nifty FMCG": {"Fast Moving Consumer Goods"}, "Nifty Metal": {"Metals & Mining"},
    "Nifty Realty": {"Realty"}, "Nifty Consumer Durables": {"Consumer Durables"},
    "Nifty Oil & Gas": {"Oil Gas & Consumable Fuels"},
    "Nifty Energy": {"Power", "Oil Gas & Consumable Fuels"},
}


def _read_symbols(slug):
    with open(os.path.join(DATA_DIR, f"{slug}.csv"), newline="", encoding="utf-8-sig") as f:
        return {r["Symbol"].strip() for r in csv.DictReader(f) if r.get("Symbol")}


def build_universe():
    with open(os.path.join(DATA_DIR, "n500.csv"), newline="", encoding="utf-8-sig") as f:
        n500 = list(csv.DictReader(f))
    by_industry = {}
    for r in n500:
        by_industry.setdefault(r["Industry"].strip(), set()).add(r["Symbol"].strip())
    universe = {}
    for sector, slug in SLUG.items():
        own = _read_symbols(slug)
        widened = set()
        for tag in INDUSTRY_WIDEN.get(sector, set()):
            widened |= by_industry.get(tag, set())
        universe[sector] = sorted(own | widened)
    return universe


# ---- exec the VALIDATED V24 sector engine (UNCHANGED reuse; same trick as
# sector_rotation_significance.py) -- Step 1 is never re-derived. ------------------------
_src = open(V24_MODULE, encoding="utf-8").read().splitlines(True)
_anchor = next(i for i, l in enumerate(_src) if l.startswith("v24_rows, v24_book"))
V24 = {"__name__": "v24_engine"}
_argv = sys.argv
sys.argv = ["sector_rotation_v24_final", DB]
exec(compile("".join(_src[:_anchor]), V24_MODULE, "exec"), V24)
sys.argv = _argv
build, kill_on, rebal = V24["build"], V24["kill_on"], V24["rebal"]
NEXT50, BENCH = V24["NEXT50"], V24["BENCH"]
index_close = V24["close"]

# ---- stock prices: read-only from bhavcopy_rows for exactly the universe's symbols -----
universe = build_universe()
all_syms = sorted(set().union(*universe.values()))
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
q = ("SELECT symbol, trade_date, close FROM bhavcopy_rows WHERE series='EQ' AND close>0 "
     "AND symbol IN (%s)" % ",".join("?" * len(all_syms)))
sclose = {}
for sym, d, c in conn.execute(q, all_syms):
    sclose.setdefault(sym, {})[d] = c
conn.close()


def strailing(sym, d, lb=126):
    """trailing lb-trading-day return on the STOCK's own calendar (handles listing gaps)."""
    ser = sclose.get(sym, {})
    if d not in ser:
        return None
    dates = sorted(x for x in ser if x <= d)
    if len(dates) <= lb:
        return None
    return ser[d] / ser[dates[-1 - lb]] - 1.0


def sector_composite_trailing(sector, d, lb=126):
    vals = [v for v in (strailing(s, d, lb) for s in universe[sector]) if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def rank_stocks_in_sector(sector, d):
    """RS-EXCESS vs the sector's OWN composite (Ramana: strength within the narrow sector,
    not vs the broad benchmark). Only genuinely out-performing-own-sector names qualify."""
    comp = sector_composite_trailing(sector, d)
    if comp is None:
        return []
    out = [(s, tr - comp) for s in universe[sector]
           for tr in [strailing(s, d)] if tr is not None]
    out.sort(key=lambda x: -x[1])
    return [(s, ex) for s, ex in out if ex > 0]


def cap_weights(w, cap=PER_NAME_CAP):
    for _ in range(8):
        over = {s: w[s] for s in w if w[s] > cap + 1e-9}
        if not over:
            break
        exc = sum(w[s] - cap for s in over)
        for s in over:
            w[s] = cap
        und = [s for s in w if w[s] < cap - 1e-9]
        tu = sum(w[s] for s in und) or 1
        for s in und:
            w[s] += exc * w[s] / tu
    return w


def build_stock_book(d, sector_weights):
    """Step 2: {sector: weight} (Step 1, V24, untouched) -> {symbol: weight}."""
    picks = {}
    for sector, sw in sector_weights.items():
        top = rank_stocks_in_sector(sector, d)[:min(max(1, round(sw * TOTAL_CAP)), MAX_PER_SECTOR)]
        if not top:
            continue
        tot_ex = sum(ex for _, ex in top)
        for s, ex in top:
            picks[s] = picks.get(s, 0.0) + sw * (ex / tot_ex if tot_ex > 0 else 1.0 / len(top))
    if len(picks) > TOTAL_CAP:
        picks = dict(sorted(picks.items(), key=lambda kv: -kv[1])[:TOTAL_CAP])
    return cap_weights(picks)


def sret(sym, d, dn):
    a, b = sclose.get(sym, {}).get(d), sclose.get(sym, {}).get(dn)
    return (b / a - 1.0) if (a and b) else None


def sleeve_ret(asset, d, dn):
    a, b = index_close.get(asset, {}).get(d), index_close.get(asset, {}).get(dn)
    return (b / a - 1.0) if (a and b) else 0.0


def simulate(record_book=False):
    prev_sec, prev_stk = {}, {}
    rows, book = [], []
    for k in range(len(rebal) - 1):
        d, dn = rebal[k], rebal[k + 1]
        is_q = (k % 3 == 0)
        if is_q:
            eb = None
            on_index_d = not kill_on(d)
            if on_index_d:
                lookback = [rebal[k - j] for j in (1, 2, 3) if k - j >= 0]
                if any(kill_on(x) for x in lookback):
                    eb = 0.0
            sector_w = build(d, set(prev_sec), eb)           # STEP 1 -- V24, verbatim
            stock_w = build_stock_book(d, sector_w)           # STEP 2 -- new
            if record_book:
                inv = sum(stock_w.values())
                book.append(dict(
                    date=d, sectors={s: round(v, 4) for s, v in sector_w.items()},
                    holdings=[(s, round(x, 4)) for s, x in
                              sorted(stock_w.items(), key=lambda kv: -kv[1])],
                    sleeve_w=round(max(0.0, 1 - inv), 4),
                    regime="INDEX" if on_index_d else "CASH",
                    entered=sorted(set(stock_w) - set(prev_stk)),
                    exited=sorted(set(prev_stk) - set(stock_w)), n_stocks=len(stock_w)))
        else:
            sector_w, stock_w = prev_sec, dict(prev_stk)

        inv = sum(stock_w.values())
        on_index = not kill_on(d)
        if not stock_w:
            rp = sleeve_ret(NEXT50, d, dn) if on_index else 0.0
        else:
            rp = sum(x * (sret(s, d, dn) or 0.0) for s, x in stock_w.items())
            if inv < 1.0 and on_index:
                rp += (1.0 - inv) * sleeve_ret(NEXT50, d, dn)
        if is_q:
            allk = set(stock_w) | set(prev_stk)
            t = sum(abs(stock_w.get(s, 0) - prev_stk.get(s, 0)) for s in allk)
            rp -= t * STOCK_COST
        rows.append((dn, rp, sleeve_ret(BENCH, d, dn)))
        prev_sec, prev_stk = sector_w, stock_w
    return (rows, book) if record_book else rows


def stats(rows):
    rp = [r[1] for r in rows]
    n = len(rp)
    m = sum(rp) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in rp) / (n - 1))
    nav = pk = 1.0
    mdd = 0.0
    for x in rp:
        nav *= 1 + x
        pk = max(pk, nav)
        mdd = min(mdd, nav / pk - 1)
    half = n // 2

    def rv(xs):
        mm = sum(xs) / len(xs)
        s2 = math.sqrt(sum((x - mm) ** 2 for x in xs) / (len(xs) - 1))
        return round(mm / s2 * math.sqrt(12), 3) if s2 else 0
    return dict(ret_vol=round(m / sd * math.sqrt(12), 3) if sd else 0, h1=rv(rp[:half]),
                h2=rv(rp[half:]), cagr=round(nav ** (12 / n) - 1, 4), mdd=round(mdd, 4),
                cr=round(nav, 3))


if __name__ == "__main__":
    rows, book = simulate(record_book=True)
    st = stats(rows)
    print(f"STOCK-LAYER (two-step, cost={STOCK_COST*100:.2f}%/side): {json.dumps(st)}")
    print(f"n={len(rows)} months ({len(rows)/12:.1f}y)  "
          f"quarters-with-picks={sum(1 for b in book if b['n_stocks']>0)}/{len(book)}  "
          f"universe={len(all_syms)} symbols / {len(universe)} sectors")
    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump({"stats": st, "stock_cost": STOCK_COST, "book": book, "universe_size": len(all_syms)},
               open(os.path.join(OUT_DIR, "sector_stock_layer_result.json"), "w"), indent=1)
