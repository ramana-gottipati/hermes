"""Name→ticker search — the S-D "search & entry" primitive (UX audit §8).

Beginners know company names, not NSE codes ("TATA CONSULTANCY" → dead-end was the
audit's canonical miss). This module is the ONE shared lookup every entry surface
uses:

  · `GET /dash/api/symbol-search?q=` — the JSON typeahead feed (⌘K palette + the
    home search box fetch it as-you-type),
  · `search()` — the ranked lookup itself (injectable conn → hermetically testable),
  · `did_you_mean_html()` — the stock-miss page's "Did you mean" strip (dashboard.py
    calls this so the fuzzy logic lives HERE, testable, not in the D80-forked file),
  · `TYPEAHEAD_JS` — the one idempotent JS attach function both boxes share.

Data: `security_master` (symbol · company_name · currently_listed · n_days — the
canonical PIT universe table), falling back to `nse_equity_list` when the master
hasn't been computed (fresh local checkouts). Read-only; every path degrades to
"no suggestions" on ANY error — a suggestion box must never 500 an entry surface.
"""
from __future__ import annotations

import html
import re
from urllib.parse import quote_plus

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.core.db import get_conn

router = APIRouter()

_MAX_Q = 60          # sanity cap on query length
_LIKE_ESC = "\\"     # ESCAPE char for LIKE special chars in user input


def _like(frag: str) -> str:
    """Escape LIKE wildcards in a user fragment (we add our own %)."""
    return (frag.replace(_LIKE_ESC, _LIKE_ESC + _LIKE_ESC)
                .replace("%", _LIKE_ESC + "%")
                .replace("_", _LIKE_ESC + "_"))


def _candidate_rows(q: str, conn) -> list[dict]:
    """Raw substring hits from security_master (fallback: nse_equity_list)."""
    pat = f"%{_like(q)}%"
    try:
        rows = conn.execute(
            "SELECT symbol, COALESCE(company_name,'') AS name, "
            "       COALESCE(currently_listed,0) AS listed, COALESCE(n_days,0) AS depth "
            "FROM security_master "
            "WHERE symbol LIKE ? ESCAPE '\\' OR company_name LIKE ? ESCAPE '\\' "
            "LIMIT 400", (pat, pat)).fetchall()
        if rows:
            return [dict(r) for r in rows]
    except Exception:
        pass
    try:  # fresh checkout / partial local DB — the equity list still has names
        rows = conn.execute(
            "SELECT symbol, COALESCE(company_name,'') AS name, 1 AS listed, 0 AS depth "
            "FROM nse_equity_list "
            "WHERE symbol LIKE ? ESCAPE '\\' OR company_name LIKE ? ESCAPE '\\' "
            "LIMIT 400", (pat, pat)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _rank(q: str, row: dict) -> tuple:
    """Sort key: match quality first, then listed > depth > symbol (stable)."""
    qu = q.upper()
    sym = (row.get("symbol") or "").upper()
    name = (row.get("name") or "").upper()
    if sym == qu:
        quality = 0
    elif sym.startswith(qu):
        quality = 1
    elif name.startswith(qu):
        quality = 2
    elif re.search(r"(^|[^A-Z0-9])" + re.escape(qu), name):
        quality = 3          # word-boundary hit in the name ("consultancy")
    else:
        quality = 4          # plain substring
    # Demote DELISTED rows a full tier so a current listing wins even when a delisted ticker
    # prefix-matches (typing "infosys" → INFY, not the delisted INFOSYSTCH whose ticker starts
    # with it). A delisted exact-ticker hit still surfaces — just under a live alternative.
    if not row.get("listed"):
        quality += 2
    return (quality, -int(row.get("listed") or 0), -int(row.get("depth") or 0), sym)


def search(q: str, limit: int = 8, conn=None) -> list[dict]:
    """Ranked name→ticker lookup. Returns [{symbol, name, listed}], best first.

    Never raises — any DB problem returns []. `conn` is injectable for tests;
    the default opens the app DB read-path via get_conn().
    """
    q = (q or "").strip()[:_MAX_Q]
    if not q:
        return []
    try:
        if conn is not None:
            rows = _candidate_rows(q, conn)
        else:
            with get_conn() as c:
                rows = _candidate_rows(q, c)
    except Exception:
        return []
    rows.sort(key=lambda r: _rank(q, r))
    out, seen = [], set()
    for r in rows:
        sym = r.get("symbol")
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append({"symbol": sym, "name": r.get("name") or "",
                    "listed": bool(r.get("listed"))})
        if len(out) >= limit:
            break
    return out


def search_indices(q: str, limit: int = 5, conn=None) -> list[dict]:
    """Ranked index-name lookup from ``index_rows`` (distinct names). Returns
    [{symbol, name, kind:'index'}] — `symbol` is the index name itself (that's what
    /dash/compare/series matches on). Never raises; [] on any error / missing table.
    Used by the compare typeahead so a user can add "Nifty 50" / "Nifty Bank" by name."""
    q = (q or "").strip()[:_MAX_Q]
    if not q:
        return []
    pat = f"%{_like(q)}%"

    def _run(c):
        return c.execute(
            "SELECT DISTINCT index_name FROM index_rows "
            "WHERE index_name LIKE ? ESCAPE '\\' ORDER BY index_name LIMIT 60",
            (pat,)).fetchall()
    try:
        rows = _run(conn) if conn is not None else None
        if rows is None:
            with get_conn() as c:
                rows = _run(c)
    except Exception:
        return []
    names = [r[0] for r in rows if r and r[0]]
    qu = q.upper()

    def _rk(n: str) -> tuple:
        nu = n.upper()
        if nu == qu:
            k = 0
        elif nu.startswith(qu):
            k = 1
        elif re.search(r"(^|[^A-Z0-9])" + re.escape(qu), nu):
            k = 2
        else:
            k = 3
        return (k, len(n), n)
    names.sort(key=_rk)
    return [{"symbol": n, "name": "index", "kind": "index"} for n in names[:limit]]


@router.get("/dash/api/symbol-search")
def symbol_search_api(q: str = "", indices: str = "") -> JSONResponse:
    """Typeahead feed: {q, results:[{symbol,name,status}]}. Always 200. When
    ``indices`` is truthy, matching INDICES are appended (status='index') — the
    compare boxes pass it so a user can add an index by name; ⌘K / the home box
    omit it, so their stock-only behaviour is unchanged."""
    results = [{"symbol": r["symbol"], "name": r["name"],
                "status": "" if r["listed"] else "delisted"}
               for r in search(q)]
    if indices:
        results += [{"symbol": r["symbol"], "name": "", "status": "index"}
                    for r in search_indices(q)]
    return JSONResponse({"q": (q or "").strip()[:_MAX_Q], "results": results})


@router.get("/dash/api/peers")
def peers_api(sym: str = "") -> JSONResponse:
    """Same-sector peer tickers for the stock-chart "related companies" quick-add:
    {sym, peers:[{symbol,name}]}. Always 200; [] on any error / no sector. The compare box
    adds a peer via /dash/compare/series, so this only needs symbol+name."""
    sym = (sym or "").strip().upper()[:24]
    if not sym:
        return JSONResponse({"sym": "", "peers": []})
    peers: list[dict] = []
    try:
        # lazy import → avoids the dashboard↔symbol_search import cycle (dashboard is loaded by
        # request time). Reuses the SAME sector logic the RS-tab peer rail uses.
        from src.web.dashboard import _narrow_sector, _sector_symbols
        with get_conn() as c:
            sec = _narrow_sector(c, sym)
            syms = [s for s in _sector_symbols(c, sec) if s and s != sym][:10] if sec else []
            names: dict = {}
            if syms:
                ph = ",".join("?" * len(syms))
                for r in c.execute(
                        "SELECT symbol, COALESCE(company_name,'') FROM security_master "
                        "WHERE symbol IN (%s)" % ph, syms).fetchall():
                    names[r[0]] = r[1]
            peers = [{"symbol": s, "name": names.get(s, "")} for s in syms]
    except Exception:
        peers = []
    return JSONResponse({"sym": sym, "peers": peers})


def did_you_mean_html(sym: str, limit: int = 5, conn=None) -> str:
    """The stock-miss page's "Did you mean" strip ('' when nothing matches).

    Links straight to /dash/stock?sym= — the audit bar is name→stock in ≤2
    actions, so the miss page must offer the jump itself, not another search.
    """
    hits = search(sym, limit=limit, conn=conn)
    if not hits:
        return ""
    links = " · ".join(
        f'<a href="/dash/stock?sym={quote_plus(h["symbol"])}"><b>{html.escape(h["symbol"])}</b></a>'
        + (f' <span style="color:#7e90a8">({html.escape(h["name"])}'
           + ("" if h["listed"] else " — delisted") + ")</span>" if h["name"] else "")
        for h in hits)
    return (f'<div style="margin-top:8px;font-size:13px">Did you mean: {links}?</div>')


# ── the one shared typeahead attach function (idempotent; both boxes use it) ──────
# window.__symTA(inputEl, suggestEl, {pages: {key:href}|null})
#   · fetches /dash/api/symbol-search as-you-type (160ms debounce, stale-guarded)
#   · optional `pages` map is filtered locally (the ⌘K palette passes the registry map)
#   · ArrowUp/Down + Enter pick; Enter with no pick falls through to the host's own
#     handler (form submit / the palette's route()) — stopPropagation only when picking.
TYPEAHEAD_JS = (
    '<script>(function(){if(window.__symTA)return;'
    'window.__symTA=function(inp,sug,opts){opts=opts||{};var t=null,items=[],hi=-1;'
    'function esc(s){return String(s).replace(/[&<>"\']/g,function(c){'
    'return{"&":"&amp;","<":"&lt;",">":"&gt;",\'"\':"&quot;","\'":"&#39;"}[c];});}'
    'function rows(){sug.innerHTML=items.map(function(it,i){'
    'return \'<div class="sym-sug-row" data-i="\'+i+\'" style="padding:7px 16px;cursor:pointer;'
    'font-size:13.5px;color:#c9d7e8;\'+(i===hi?"background:#1b2735;":"")+\'">\''
    '+\'<b style="color:#eaf1f9">\'+esc(it.t)+"</b>"'
    '+(it.s?\' <span style="color:#7e90a8">— \'+esc(it.s)+"</span>":"")'
    '+(it.k?\' <span style="float:right;color:#5b708c;font-size:11px">\'+esc(it.k)+"</span>":"")'
    '+"</div>";}).join("");'
    'sug.style.display=items.length?"block":"none";}'
    'function go(it){if(!it)return;if(opts.onPick){opts.onPick(it);}else{location.href=it.h;}}'
    'function refresh(q){var loc=[];'
    'if(opts.pages){var k,ql=q.toLowerCase(),hit=[];'
    'for(k in opts.pages){if(k.indexOf(ql)===0)hit.push(k);}'
    'for(k in opts.pages){if(k.indexOf(ql)>0&&hit.indexOf(k)<0)hit.push(k);}'
    'hit.slice(0,4).forEach(function(k){loc.push({t:k,h:opts.pages[k],k:"page"});});}'
    'if(q.length<2){items=loc;hi=-1;rows();return;}'
    'fetch("/dash/api/symbol-search?q="+encodeURIComponent(q)+(opts.indices?"&indices=1":""))'
    '.then(function(r){return r.json();}).then(function(j){'
    'if(inp.value.trim()!==q)return;'
    'items=loc.concat((j.results||[]).map(function(r){'
    'return{t:r.symbol,s:r.name,h:"/dash/stock?sym="+encodeURIComponent(r.symbol),k:r.status||""};}));'
    'hi=-1;rows();}).catch(function(){items=loc;hi=-1;rows();});}'
    'inp.addEventListener("input",function(){var q=inp.value.trim();clearTimeout(t);'
    'if(!q){items=[];hi=-1;rows();return;}t=setTimeout(function(){refresh(q);},160);});'
    'inp.addEventListener("keydown",function(e){'
    'if(e.key==="ArrowDown"&&items.length){e.preventDefault();hi=(hi+1)%items.length;rows();}'
    'else if(e.key==="ArrowUp"&&items.length){e.preventDefault();hi=(hi-1+items.length)%items.length;rows();}'
    'else if(e.key==="Enter"&&hi>=0&&items[hi]){e.preventDefault();e.stopPropagation();go(items[hi]);}'
    'else if(e.key==="Escape"&&items.length){items=[];hi=-1;rows();}});'
    'sug.addEventListener("mousedown",function(e){'
    'var r=e.target.closest?e.target.closest(".sym-sug-row"):null;'
    'if(r){e.preventDefault();go(items[+r.getAttribute("data-i")]);}});'
    '};})();</script>'
)


def _selftest() -> None:  # pragma: no cover — quick local sanity: python -m src.web.symbol_search
    import sqlite3
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE security_master (symbol TEXT PRIMARY KEY, company_name TEXT,"
              " currently_listed INTEGER, n_days INTEGER)")
    c.executemany("INSERT INTO security_master VALUES (?,?,?,?)", [
        ("TCS", "Tata Consultancy Services Limited", 1, 5000),
        ("TATACONSUM", "Tata Consumer Products Limited", 1, 3000),
        ("TATAMOTORS", "Tata Motors Limited", 1, 5200),
        ("OLDCO", "Old Tata Venture", 0, 900),
    ])
    hits = search("tata consultancy", conn=c)
    assert hits and hits[0]["symbol"] == "TCS", hits
    assert search("TCS", conn=c)[0]["symbol"] == "TCS"
    dym = did_you_mean_html("tata consultancy", conn=c)
    assert 'sym=TCS"' in dym, dym
    tata = search("tata", conn=c)          # broad fragment: listed first, then delisted
    assert [h["symbol"] for h in tata][:3] == ["TATAMOTORS", "TATACONSUM", "TCS"] or \
           {"TCS", "TATAMOTORS", "TATACONSUM"} <= {h["symbol"] for h in tata}, tata
    assert tata[-1]["symbol"] == "OLDCO" and tata[-1]["listed"] is False, tata
    assert search("", conn=c) == [] and search("zz_nohit_zz", conn=c) == []
    # index search (compare typeahead): name match, ranked, capped; empty on no table/hit.
    c.execute("CREATE TABLE index_rows (index_name TEXT, trade_date TEXT, close_value REAL)")
    c.executemany("INSERT INTO index_rows VALUES (?,?,?)", [
        ("Nifty 50", "2026-01-01", 100.0), ("Nifty 50", "2026-01-02", 101.0),
        ("Nifty Bank", "2026-01-01", 200.0), ("Nifty 500", "2026-01-01", 90.0)])
    idx = search_indices("nifty", conn=c)
    assert {r["symbol"] for r in idx} == {"Nifty 50", "Nifty Bank", "Nifty 500"}, idx
    assert all(r["kind"] == "index" for r in idx)
    assert search_indices("bank", conn=c)[0]["symbol"] == "Nifty Bank"
    assert search_indices("", conn=c) == []
    # delisted demotion: a LIVE name-match beats a DELISTED ticker-prefix hit (INFY over INFOSYSTCH).
    c.execute("INSERT INTO security_master VALUES ('INFY','Infosys Limited',1,3700)")
    c.execute("INSERT INTO security_master VALUES ('INFOSYSTCH',NULL,0,1700)")
    inf = search("infosys", conn=c)
    assert inf and inf[0]["symbol"] == "INFY", inf
    print("symbol_search selftest OK")


if __name__ == "__main__":  # pragma: no cover
    _selftest()
