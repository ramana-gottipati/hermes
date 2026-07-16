"""niftyindices.com HISTORY FETCHER — the committed recipe (S174; closes the "S120 recipe was
never committed as a tool" gap; primary source, Guardrail #8-clean).

THE CRACK (2026-07-16, ledger 16AI): the modern site serves history from `/BackPage/...` (NOT the
legacy `Backpage.aspx/...`), and the payload is a JSON body whose `cinfo` value is a STRING of
SINGLE-QUOTED JS-style JSON, exactly as the site's own live code builds it
(`IISLComponet.js`: `"{'name':'<TRADING_NAME_UPPERCASED>','startDate':'dd-MMM-yyyy','endDate':
'dd-MMM-yyyy','indexName':'<long name>'}"`). Content-Type application/json. Ranges are capped at
~1 year server-side — chunk yearly. `name` = Trading_Index_Name (IndexMapping.json, uppercased),
`indexName` = the long name.

Endpoints:
  PR OHLC  : POST /BackPage/getHistoricaldatatabletoString  -> [{HistoricalDate, OPEN..CLOSE}]
  TR       : POST /BackPage/getTotalReturnIndexString       -> [{Date, TotalReturnsIndex, NTR_Value}]

Usage (from /opt/hermes, .venv-research python):
  python research/explosive_moves/niftyindices_hist.py --name "NIFTY 500" --long "Nifty 500" \
      --kind tr --from 2005-01-01 --to 2026-07-16 --out research/data/niftyindices/nifty500_tr.csv

Writes CSV `date,value[,ntr]` ascending, deduped. Empty chunks are recorded to stderr (an index's
pre-base-date era returns []). Polite: 1.0s sleep between chunks, 3 retries with backoff.
Research-side files ONLY — the prod `index_rows` ingestion is the feed lane's job (manifest,
licence gate, timer), deliberately not done here.
"""
import argparse, csv, datetime as dt, json, sys, time, urllib.request

BASE = "https://www.niftyindices.com"
HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json; charset=utf-8",
    "Referer": BASE + "/reports/historical-data",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE,
}
EP = {"pr": "/BackPage/getHistoricaldatatabletoString", "tr": "/BackPage/getTotalReturnIndexString"}

def _fmt(d): return d.strftime("%d-%b-%Y")

def fetch_chunk(kind, name, long_name, d0, d1, retries=3):
    cinfo = "{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}" % (
        name.upper().strip(), _fmt(d0), _fmt(d1), long_name)
    body = json.dumps({"cinfo": cinfo}).encode()
    for att in range(retries):
        try:
            req = urllib.request.Request(BASE + EP[kind], data=body, headers=HDRS)
            raw = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
            if raw.strip().startswith("<"):
                raise RuntimeError("HTML page returned (WAF?)")
            data = json.loads(raw)
            if isinstance(data, str):
                data = json.loads(data)
            return data or []
        except Exception as e:
            if att == retries - 1:
                raise
            time.sleep(2.0 * (att + 1))
    return []

def parse_rows(kind, data):
    out = {}
    for r in data:
        if kind == "tr":
            ds, v = r.get("Date"), r.get("TotalReturnsIndex")
            ntr = r.get("NTR_Value")
        else:
            ds, v = r.get("HistoricalDate"), r.get("CLOSE")
            ntr = None
        if not ds or v in (None, "", "0"):
            continue
        try:
            d = dt.datetime.strptime(ds.strip(), "%d %b %Y").date()
        except ValueError:
            continue
        try:
            ntr_f = float(ntr) if ntr not in (None, "", "-") else None
        except ValueError:
            ntr_f = None
        try:
            out[d.isoformat()] = (float(v), ntr_f)
        except ValueError:
            continue
    return out

def backfill(kind, name, long_name, d_from, d_to, sleep=1.0):
    rows = {}
    cur = d_from
    while cur <= d_to:
        end = min(dt.date(cur.year, 12, 31), d_to)
        try:
            chunk = fetch_chunk(kind, name, long_name, cur, end)
        except Exception as e:
            print(f"[{name}] {cur}..{end}: FAILED {e}", file=sys.stderr, flush=True)
            chunk = []
        got = parse_rows(kind, chunk)
        print(f"[{name}] {cur}..{end}: {len(got)} rows", file=sys.stderr, flush=True)
        rows.update(got)
        cur = dt.date(cur.year + 1, 1, 1)
        time.sleep(sleep)
    return rows

def ingest(db_path, index_name, csv_path):
    """One-shot ADDITIVE ingestion of a fetched CSV into prod index_rows (S175, ledger 16AK).
    Only close_value is populated (the TRI/G-sec endpoints publish closes); rows whose
    (index_name, trade_date) already exist are left untouched — re-runs are idempotent.
    Guarded: refuses to run while another writer holds the DB (busy_timeout + immediate tx)."""
    import sqlite3
    rows = []
    with open(csv_path) as f:
        rd = csv.reader(f); next(rd, None)
        for r in rd:
            try:
                rows.append((index_name, r[0], float(r[1])))
            except (ValueError, IndexError):
                continue
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    before = cur.execute("SELECT count(*) FROM index_rows WHERE index_name=?", (index_name,)).fetchone()[0]
    cur.executemany(
        "INSERT INTO index_rows(index_name, trade_date, close_value) "
        "SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM index_rows WHERE index_name=?1 AND trade_date=?2)",
        rows)
    conn.commit()
    after = cur.execute("SELECT count(*) FROM index_rows WHERE index_name=?", (index_name,)).fetchone()[0]
    lo, hi = cur.execute("SELECT min(trade_date), max(trade_date) FROM index_rows WHERE index_name=?",
                         (index_name,)).fetchone()
    conn.close()
    print(f"INGESTED '{index_name}': +{after-before} rows (had {before}, now {after}; {lo}..{hi})", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Trading_Index_Name (IndexMapping.json)")
    ap.add_argument("--long", required=True, help="Index_long_name")
    ap.add_argument("--kind", choices=("tr", "pr"), default="tr")
    ap.add_argument("--from", dest="dfrom", required=True)
    ap.add_argument("--to", dest="dto", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ingest-db", help="ALSO ingest the written CSV into this DB's index_rows")
    ap.add_argument("--ingest-name", help="index_name for ingestion")
    a = ap.parse_args()
    d0 = dt.date.fromisoformat(a.dfrom); d1 = dt.date.fromisoformat(a.dto)
    rows = backfill(a.kind, a.name, a.long, d0, d1)
    import os
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value", "ntr"] if a.kind == "tr" else ["date", "close"])
        for d in sorted(rows):
            v, ntr = rows[d]
            w.writerow([d, v, ntr] if a.kind == "tr" else [d, v])
    print(f"WROTE {a.out}: {len(rows)} rows "
          f"({min(rows) if rows else '-'} .. {max(rows) if rows else '-'})", flush=True)
    if a.ingest_db and a.ingest_name:
        ingest(a.ingest_db, a.ingest_name, a.out)

if __name__ == "__main__":
    main()
