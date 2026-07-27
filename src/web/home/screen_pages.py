"""src/web/home/screen_pages.py — the Graphite SCREENER estate (lane W4 · milestone M8).

Two declared children of the Graphite home, on their own APIRouter:

    GET /dash/home/screen    the confluence screener  (+ `?format=csv`)
    GET /dash/home/themes    themes / baskets — non-ticker discovery, hands off to the screener

This is a REBUILD of the classic `/dash/screen2`, not a transliteration. Three recorded debts are
fixed BY DESIGN — each one is the reason a capability moved rather than being copied:

 1. PAYLOAD.  Classic rendered up to 600 rows × 43 columns in one document (~2.3 MB). Here the
    server paginates (default 50 rows) and renders only the ACTIVE column set inside a fixed-size,
    internally-scrolling frozen-pane grid. Gate: tests/test_home_screen.py asserts the default
    render is under 500 KB.
 2. EXPORT.   Classic's CSV was a client-side Blob of whatever the DOM happened to be showing.
    Here `?format=csv` is a SERVER export that honours the active scope · text filter · minimum
    confluence · reversal cut · sort · column set — the same params that produced the page.
 3. URL STATE. Classic kept scope in the URL but hid the column set, sort and filter in
    localStorage, so a screen could not be shared. Here EVERY control is a GET that round-trips
    through query params: the URL *is* the saved screen (`?cols=`/`?sort=`/`?dir=`/`?q=`/
    `?minconf=`/`?rev=`/`?page=`/`?n=`). Named views are presets over the same params.

Free / Pro (owner's binding split): Free is a COMPLETE honest screener — every one of the ~70
columns, every filter, sort, pagination and the CSV export. Columns are never paywalled (Part III
§J, ratified: "evidence is never gated"). Pro adds the REFERENCE LAYER only — where a value sits
against the current result set, and against the name's own recent tape.

Isolation: imports only sibling Graphite modules (`components`, `shell`) + the lane-owned
`screen_reads`. No classic/preview render module, no `lens_registry` edit, no nav change.
"""
from __future__ import annotations

import csv as _csv
import io as _io
from urllib.parse import quote as _q

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from src.web.home import components as C
from src.web.home import screen_reads as R
from src.web.home import shell

router = APIRouter()

# The stock page is a sibling Graphite surface (W1). Linked by ROUTE ONLY — never imported.
STOCK_ROUTE = "/dash/home/stock"


def sym_link(symbol) -> str:
    """A symbol cell that deep-links to the Graphite stock page. `?sym=` — never `?symbol=`."""
    s = C.esc(symbol)
    return '<a class="g-syma" href="' + STOCK_ROUTE + "?sym=" + s + '">' + s + "</a>"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE COLUMN POOL
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Part III §J's three-layer model, ratified 2026-07-20:
#   1. IDENTITY SPINE — frozen, never configurable: Symbol (sticky first column) · Sector · CMP.
#   2. BOOK CORE      — the 10-12 default visible columns (DEFAULT_COLS below).
#   3. EVIDENCE POOL  — ~70 configurable columns, toggled by family and individually.
# Every pooled column carries a glossary key (`term`) or an explicit '' opt-out, mirroring the
# machine-gated rule the classic screener already lives under — enforced here by
# tests/test_home_screen.py::test_every_pool_column_is_glossary_backed.
#
# `kind`:  num (right-aligned number) · pct (signed %) · txt (label) · state (label + up/down tint)
# `src` is the key in the merged row dict (base row + prefixed aux lookups).

class Col:
    __slots__ = ("key", "label", "fam", "term", "kind", "dp", "src", "unit")

    def __init__(self, key, label, fam, term, kind="num", dp=2, src=None, unit=""):
        self.key, self.label, self.fam, self.term = key, label, fam, term
        self.kind, self.dp, self.src, self.unit = kind, dp, (src or key), unit


# family key -> (label, descriptive fence shown when the family is visible)
FAMILIES: list[tuple[str, str, str]] = [
    ("conf", "Confluence", "How many independent pillars line up right now. A sorting heuristic for "
                           "building a shortlist — not a validated model, not a score to act on."),
    ("pos", "Delivery positioning", ""),
    ("mep", "Accumulation", "Descriptive only (D62) — the accumulation/distribution read describes "
                            "the tape; it never ranks and never triggers."),
    ("rs", "Relative strength", ""),
    ("cpr", "Structure", ""),
    ("cci", "Credibility", "Descriptive only — the credibility composite FAILED its leak-free "
                           "predictive gate (Gate B). It is context about disclosure quality, never a rank."),
    ("wol", "Wolfe geometry", "Descriptive only — the studied edge was in SELECTION, not in the "
                              "geometry itself. Never a target or an entry."),
    ("rev", "Reversal context", "Descriptive only — BOTH band crosses were falsified as entries "
                                "(2026-07-13). What survives is context: band state, own-history stretch, "
                                "and the confirmed fractal as a risk level."),
    ("qual", "Quality (14-pattern)", ""),
    ("ca", "Capital allocation", "Descriptive context or a blend tilt — never a veto and never a "
                                 "standalone ranker."),
    ("ctx", "Tape character", ""),
    ("key", "Key price", "The value-weighted price levels where delivery actually happened, and "
                         "today's gap to each. Raw material for your own cuts."),
    ("fno", "F&O positioning", "Descriptive only — the Phase-0 gate (2026-07-24) found the put/call "
                               "ratio selects only weakly and is forward-test-only; max-pain, basis and "
                               "OI-change did not select at all."),
]
FAM_LABEL = {k: lbl for k, lbl, _ in FAMILIES}
FAM_FENCE = {k: f for k, _, f in FAMILIES}

SPINE: list[Col] = [
    Col("sym", "Symbol", "spine", "", "txt", 0, "symbol"),
    Col("sector", "Sector", "spine", "primary_sector", "txt", 0, "primary_sector"),
    Col("cmp", "CMP", "spine", "close", "num", 1, "close"),
]

POOL: list[Col] = [
    # ── confluence ───────────────────────────────────────────────────────────────────────────
    Col("confl", "Confl", "conf", "confluence", "num", 0, "_confl"),
    # ── delivery positioning (DVPT) ──────────────────────────────────────────────────────────
    Col("dvpt", "DVPT", "pos", "DVPT", "num", 0, "delivery_value_per_trade"),
    Col("rank", "Trigger rank", "pos", "trigger_rank", "txt", 0, "trigger_rank"),
    Col("p", "P", "pos", "p_score", "num", 0, "p_score"),
    Col("r", "R", "pos", "r_score", "num", 0, "r_score"),
    Col("xpow", "×power", "pos", "×power", "num", 2, "ratio_today_vs_power_1m", "×"),
    Col("dlv", "Deliv %", "pos", "deliv_per", "num", 1, "deliv_per", "%"),
    Col("pow1m", "Power 1m", "pos", "power_dvpt_*", "num", 0, "power_dvpt_1m"),
    Col("pow3m", "Power 3m", "pos", "power_dvpt_*", "num", 0, "power_dvpt_3m"),
    Col("pow6m", "Power 6m", "pos", "power_dvpt_*", "num", 0, "power_dvpt_6m"),
    Col("pow12m", "Power 12m", "pos", "power_dvpt_*", "num", 0, "power_dvpt_12m"),
    Col("nextp", "Next P level", "pos", "next_p_above", "num", 0, "next_p_above"),
    Col("gapnextp", "Gap to next P", "pos", "next_p_above", "pct", 1, "gap_to_next_p_pct"),
    Col("ath", "All-time DVPT", "pos", "is_ath_dvpt", "txt", 0, "is_ath_dvpt"),
    # ── accumulation (MEP) ───────────────────────────────────────────────────────────────────
    Col("mep", "MEP score", "mep", "MEP phase score", "num", 2, "mep_score_smooth"),
    Col("mepst", "MEP state", "mep", "MEP daily state", "state", 0, "mep_state_smooth"),
    # ── relative strength ────────────────────────────────────────────────────────────────────
    Col("rsrank", "RS rank", "rs", "rs_rank", "num", 0, "rs_rank"),
    Col("rstrend", "RS trend", "rs", "RS vs broad", "state", 0, "rs_vs_broad_trend_state"),
    Col("rsphase", "RS phase", "rs", "rs_phase", "state", 0, "rs_phase"),
    Col("rsi", "RSI of RS", "rs", "rsi_of_rs", "num", 0, "rsi_of_rs"),
    Col("rs1w", "RS 1w", "rs", "RS vs broad", "pct", 1, "rs_vs_broad_1w"),
    Col("rs1m", "RS 1m", "rs", "RS vs broad", "pct", 1, "rs_vs_broad_slope_1m"),
    Col("rs3m", "RS 3m", "rs", "RS vs broad", "pct", 1, "rs_vs_broad_slope_3m"),
    Col("rs6m", "RS 6m", "rs", "RS vs broad", "pct", 1, "rs_vs_broad_slope_6m"),
    Col("rs12m", "RS 12m", "rs", "RS vs broad", "pct", 1, "rs_vs_broad_slope_12m"),
    Col("rs18m", "RS 18m", "rs", "RS vs broad", "pct", 1, "rs_vs_broad_slope_18m"),
    Col("rs24m", "RS 24m", "rs", "RS vs broad", "pct", 1, "rs_vs_broad_slope_24m"),
    # ── structure (CPR) ──────────────────────────────────────────────────────────────────────
    Col("cprd", "CPR · day", "cpr", "pattern", "state", 0, "cprD_pattern"),
    Col("cprw", "CPR · week", "cpr", "pattern", "state", 0, "cprW_pattern"),
    Col("cprc", "Compression", "cpr", "compression_pctile", "num", 0, "cprD_compression_pctile"),
    # ── credibility (CCI) ────────────────────────────────────────────────────────────────────
    Col("cci", "Credibility", "cci", "Credibility composite", "num", 0, "cci_composite_score"),
    Col("ccitier", "Credibility tier", "cci", "Credibility level", "txt", 0, "cci_tier"),
    Col("ccitrend", "Credibility trend", "cci", "credibility tape", "txt", 0, "cci_credibility_trend"),
    # ── Wolfe geometry (undocumented in the glossary — explicit '' opt-out, as on classic) ────
    Col("wolfe", "Wolfe", "wol", "", "state", 0, "_wolfe"),
    Col("wolfeq", "Wolfe quality", "wol", "", "num", 0, "wolfe_q"),
    # ── reversal context ─────────────────────────────────────────────────────────────────────
    Col("band", "Band state", "rev", "Band state", "state", 0, "rev_band_state"),
    Col("stretch", "Stretch", "rev", "Stretch %", "pct", 1, "rev_stretch_pct"),
    Col("stretchp", "Stretch pctile", "rev", "stretch_pctile", "num", 0, "rev_stretch_pctile"),
    Col("floor", "Floor gap", "rev", "floor_gap_pct", "pct", 1, "rev_floor_gap_pct"),
    Col("ceil", "Ceiling gap", "rev", "ceil_gap_pct", "pct", 1, "rev_ceil_gap_pct"),
    # ── quality (14-pattern) ─────────────────────────────────────────────────────────────────
    Col("ns", "Quality score", "qual", "ns_base", "num", 0, "pt14_ns_base"),
    Col("qtier", "Quality tier", "qual", "ns_base", "txt", 0, "pt14_tier"),
    # ── capital allocation ───────────────────────────────────────────────────────────────────
    Col("ca", "C score", "ca", "ca_score", "num", 0, "ca_ca_score"),
    Col("catier", "C tier", "ca", "ca_tier", "txt", 0, "ca_ca_tier"),
    # ── tape character ───────────────────────────────────────────────────────────────────────
    Col("char", "Character", "ctx", "accum_character", "state", 0, "accum_character"),
    Col("su1", "Surge 1m", "ctx", "surge 1m", "num", 2, "turnover_surge_1m", "×"),
    Col("su3", "Surge 3m", "ctx", "turnover_surge_*", "num", 2, "turnover_surge_3m", "×"),
    Col("su1y", "Surge 1y", "ctx", "turnover_surge_*", "num", 2, "turnover_surge_1y", "×"),
    Col("ticket", "Ticket ratio", "ctx", "ticket_ratio_1m_6m", "num", 2, "ticket_ratio_1m_6m", "×"),
    Col("tcr", "Trade-count ratio", "ctx", "trade_count_ratio_1m_6m", "num", 2, "trade_count_ratio_1m_6m", "×"),
    Col("updown", "Deliv up/down", "ctx", "deliv_updown_ratio_3m", "num", 2, "deliv_updown_ratio_3m", "×"),
    Col("dvr", "Deliv value ratio", "ctx", "deliv ×", "num", 2, "deliv_value_ratio_1m_6m", "×"),
    Col("dp1m", "Deliv % · 1m norm", "ctx", "delivery %", "num", 1, "avg_deliv_pct_1m", "%"),
    Col("dp6m", "Deliv % · 6m norm", "ctx", "delivery %", "num", 1, "avg_deliv_pct_6m", "%"),
    Col("drift", "Price drift 3m", "ctx", "accum_price_drift_3m", "pct", 1, "accum_price_drift_3m"),
    Col("hh", "From 52w high", "ctx", "pct_from_52w_high", "pct", 1, "pct_from_52w_high"),
    Col("turn", "Turnover", "ctx", "traded value", "num", 0, "turnover"),
    # ── key price (the family absorbed from the retired /dash/workbench) ──────────────────────
    Col("kp3", "Key price 3m", "key", "key_price_p*", "num", 1, "key_price_p3m"),
    Col("gk3", "Gap to key 3m", "key", "gap_to_key_p*", "pct", 1, "gap_to_key_p3m"),
    Col("kp6", "Key price 6m", "key", "key_price_p*", "num", 1, "key_price_p6m"),
    Col("gk6", "Gap to key 6m", "key", "gap_to_key_p*", "pct", 1, "gap_to_key_p6m"),
    Col("kp12", "Key price 12m", "key", "key_price_p*", "num", 1, "key_price_p12m"),
    Col("gk12", "Gap to key 12m", "key", "gap_to_key_p*", "pct", 1, "gap_to_key_p12m"),
    Col("ac3", "Avg close 3m", "key", "avg_price", "num", 1, "avg_close_p3m"),
    Col("atq", "Avg trade qty", "key", "avg_trade_qty", "num", 0, "avg_trade_qty"),
    Col("adq", "Deliv qty / trade", "key", "avg_deliv_qty_per_trade", "num", 0, "avg_deliv_qty_per_trade"),
    Col("dvt", "Delivered value", "key", "delivery_value_today", "num", 0, "delivery_value_today"),
    Col("tvt", "Traded value", "key", "traded value", "num", 0, "total_value_today"),
    # ── F&O positioning ──────────────────────────────────────────────────────────────────────
    Col("futoi", "Futures OI", "fno", "fut_oi", "num", 0, "fno_fut_oi"),
    Col("oichg", "Futures OI change", "fno", "fut_oi_chg_pct", "pct", 1, "fno_fut_oi_chg_pct"),
    Col("fquad", "OI quadrant", "fno", "positioning quadrant", "txt", 0, "fno_quadrant"),
    Col("pcr", "Put/call OI", "fno", "pcr", "num", 2, "fno_pcr"),
]

BY_KEY: dict[str, Col] = {c.key: c for c in POOL}
BY_KEY_ALL: dict[str, Col] = {c.key: c for c in (SPINE + POOL)}
SOFT_CAP = 20          # beyond this the frozen-pane scan breaks (Part III §J, ratified)

# ── named views (the presets). `default` is the ratified 10-12-column BOOK CORE. ──────────────
VIEWS: dict[str, tuple[str, tuple, str]] = {
    "confluence": ("Confluence read",
                   ("confl", "dvpt", "rank", "p", "xpow", "dlv", "mepst", "rsrank", "rstrend",
                    "cprd", "char", "hh"),
                   "Where independent pillars line up right now."),
    "momentum": ("Momentum read",
                 ("rsrank", "rstrend", "rsphase", "rs1m", "rs3m", "rs6m", "rs12m", "rsi", "hh",
                  "su1", "xpow"),
                 "Relative strength across horizons, with the extension context."),
    "accumulation": ("Accumulation read",
                     ("mep", "mepst", "dvpt", "xpow", "dlv", "dp1m", "dp6m", "updown", "ticket",
                      "char", "su1"),
                     "Who is doing the buying, and in what size."),
    "quality": ("Quality read",
                ("ns", "qtier", "ca", "catier", "cci", "ccitier", "ccitrend", "rsrank", "char", "dlv"),
                "The management / disclosure / allocation evidence layers."),
    "keyprice": ("Key-price read",
                 ("kp3", "gk3", "kp6", "gk6", "kp12", "gk12", "ac3", "atq", "adq", "dvt", "char"),
                 "Every key-price, gap and activity column in one table — the read the standalone "
                 "Workbench page used to serve."),
    "structure": ("Structure read",
                  ("cprd", "cprw", "cprc", "band", "stretch", "stretchp", "floor", "ceil",
                   "wolfe", "wolfeq"),
                  "Compression, bands and geometry — all descriptive."),
}
DEFAULT_VIEW = "confluence"
DEFAULT_COLS = VIEWS[DEFAULT_VIEW][1]
DEFAULT_SCOPE = "Nifty 500"
PAGE_SIZES = (25, 50, 100, 200)
DEFAULT_N = 50
CSV_CAP = 5000

# Debt #1 is bounded BY CONSTRUCTION, not by hoping the default is small. The rendered grid costs
# ~34 bytes per cell, so the page size is capped by a CELL budget rather than a row budget: a wide
# view automatically renders shorter pages. Without this, `n=200` x the full 75-column set projects
# to ~585 KB — over budget — even though the default view is ~140 KB. The reduction is DISCLOSED in
# the pager (never a silent trim), and it changes nothing about the URL state or the CSV export.
CELL_BUDGET = 4000


def effective_n(st: "State") -> int:
    """Rows actually rendered on one page: the requested size, reduced when the active view is wide."""
    n_cols = max(1, len(st.cols) + len(SPINE) + 2)      # +2 = the Pro reference columns
    return max(25, min(st.n, CELL_BUDGET // n_cols))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# STATE — every control round-trips through the query string. The URL *is* the saved screen.
# ══════════════════════════════════════════════════════════════════════════════════════════════
class State:
    __slots__ = ("scope", "view", "cols", "sort", "dir", "q", "minconf", "rev", "page", "n")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def replace(self, **kw) -> "State":
        cur = {k: getattr(self, k) for k in self.__slots__}
        cur.update(kw)
        return State(**cur)


def parse_state(params) -> State:
    """Read the full screen state out of the query string. Every field CLAMPS rather than 422s —
    a hand-typed or truncated URL must still render a screen, never an error page."""
    def one(name, default=""):
        v = params.get(name)
        return default if v is None else str(v).strip()

    view = one("view") or DEFAULT_VIEW
    if view not in VIEWS:
        view = DEFAULT_VIEW
    raw_cols = one("cols")
    if raw_cols:
        cols = tuple(dict.fromkeys(k for k in (c.strip() for c in raw_cols.split(",")) if k in BY_KEY))
        cols = cols or DEFAULT_COLS
    else:
        cols = VIEWS[view][1]

    sort = one("sort") or "confl"
    if sort not in BY_KEY_ALL:
        sort = "confl"
    direction = "asc" if one("dir").lower() == "asc" else "desc"

    try:
        minconf = max(0, min(6, int(one("minconf", "0") or 0)))
    except (TypeError, ValueError):
        minconf = 0
    try:
        page = max(1, int(one("page", "1") or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        n = int(one("n", str(DEFAULT_N)) or DEFAULT_N)
    except (TypeError, ValueError):
        n = DEFAULT_N
    if n not in PAGE_SIZES:
        n = DEFAULT_N
    rv = one("rev").lower()
    rev = "ri" if rv in ("ri", "reclaim") else ("si" if rv in ("si", "slip") else "")

    return State(scope=one("scope") or DEFAULT_SCOPE, view=view, cols=cols, sort=sort,
                 dir=direction, q=one("q")[:60], minconf=minconf, rev=rev, page=page, n=n)


def qs(st: State, **over) -> str:
    """The canonical URL for a state. Only non-default fields are emitted, so a shared link stays
    readable — and re-parsing it yields exactly this state (round-trip proven by the gate)."""
    s = st.replace(**over) if over else st
    bits = []
    if s.scope != DEFAULT_SCOPE:
        bits.append("scope=" + _q(s.scope))
    named = next((k for k, v in VIEWS.items() if tuple(v[1]) == tuple(s.cols)), None)
    if named and named != DEFAULT_VIEW:
        bits.append("view=" + named)
    elif not named:
        bits.append("cols=" + ",".join(s.cols))
    if s.sort != "confl":
        bits.append("sort=" + s.sort)
    if s.dir != "desc":
        bits.append("dir=asc")
    if s.q:
        bits.append("q=" + _q(s.q))
    if s.minconf:
        bits.append("minconf=" + str(s.minconf))
    if s.rev:
        bits.append("rev=" + s.rev)
    if s.n != DEFAULT_N:
        bits.append("n=" + str(s.n))
    if s.page > 1:
        bits.append("page=" + str(s.page))
    if over.get("format"):
        bits.append("format=" + str(over["format"]))
    return "/dash/home/screen" + ("?" + "&".join(bits) if bits else "")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE PIPELINE — read · enrich · filter · sort · paginate (all server-side)
# ══════════════════════════════════════════════════════════════════════════════════════════════
_AUX_FOR_FAM = {"cpr": ("cprD", "cprW"), "cci": ("cci",), "wol": ("wolfe",), "qual": ("pt14",),
                "ca": ("ca",), "rev": ("rev",), "fno": ("fno",)}


def _needed(st: State) -> set:
    """Only run the auxiliary lookups the ACTIVE view actually needs — a Momentum read costs four
    fewer batched queries than a Confluence read."""
    need: set = set()
    fams = {BY_KEY[k].fam for k in st.cols if k in BY_KEY}
    for fam in fams:
        need.update(_AUX_FOR_FAM.get(fam, ()))
    if "confl" in st.cols or st.minconf or st.sort == "confl":
        need.update(("cprD", "cci", "wolfe"))          # the pillars that live outside the base row
    if st.rev:
        need.add("rev")
    if st.sort in BY_KEY:
        need.update(_AUX_FOR_FAM.get(BY_KEY[st.sort].fam, ()))
    return need


_PILLARS = ("DVPT", "MEP", "RS", "CPR", "Credibility", "Wolfe")


def _enrich(rows: list, aux: dict) -> list:
    """Flatten the auxiliary lookups onto each row (prefixed keys) and compute the confluence
    count. Confluence is 0-6 booleans over independent pillars — a SORTING HEURISTIC for building
    a shortlist, never a validated model (fenced on the page)."""
    cprD, cprW = aux.get("cprD", {}), aux.get("cprW", {})
    cci, wolfe = aux.get("cci", {}), aux.get("wolfe", {})
    pt14, ca = aux.get("pt14", {}), aux.get("ca", {})
    rev, fno = aux.get("rev", {}), aux.get("fno", {})
    out = []
    for r in rows:
        s = r.get("symbol")
        rec = dict(r)
        for pre, src in (("cprD", cprD), ("cprW", cprW), ("cci", cci), ("wolfe", wolfe),
                         ("pt14", pt14), ("ca", ca), ("rev", rev), ("fno", fno)):
            for k, v in (src.get(s) or {}).items():
                rec[pre + "_" + k] = v
        w = wolfe.get(s) or {}
        rec["_wolfe"] = ((w.get("dir") or "").upper() + (" · in zone" if w.get("in_zone") else "")) or None
        rec["wolfe_q"] = w.get("q")
        pil = (1 if (rec.get("p_score") or 0) >= 4 else 0,
               1 if (rec.get("mep_state_smooth") or "") in ("ACCUM", "STRONG_ACCUM") else 0,
               1 if (rec.get("rs_rank") or 0) >= 80 else 0,
               1 if rec.get("cprD_pattern") == "BULL_U" else 0,
               1 if (rec.get("cci_tier") or "") in ("A+", "A") else 0,
               1 if ((w.get("dir") or "").lower() == "bull" and w.get("in_zone")) else 0)
        rec["_confl"] = sum(pil)
        rec["_pillars"] = pil
        rec["fno_fut_oi"] = (fno.get(s) or {}).get("fut_oi")
        out.append(rec)
    return out


_TEXT_FIELDS = ("symbol", "primary_sector", "accum_character", "mep_state_smooth",
                "rs_vs_broad_trend_state", "rs_phase", "cprD_pattern", "cci_tier", "pt14_tier",
                "ca_ca_tier", "rev_band_state", "fno_quadrant")


def _filter(rows: list, st: State) -> list:
    out = rows
    if st.q:
        needle = st.q.lower()
        out = [r for r in out
               if any(needle in str(r.get(f)).lower() for f in _TEXT_FIELDS if r.get(f) is not None)]
    if st.minconf:
        out = [r for r in out if (r.get("_confl") or 0) >= st.minconf]
    if st.rev:
        want = ("RECLAIM", "floor_alive") if st.rev == "ri" else ("SLIP", "ceil_alive")
        out = [r for r in out
               if (r.get("rev_band_state") == want[0] and (r.get(want[1]) or r.get("rev_" + want[1])))]
    return out


def _sort_value(rec, col: Col):
    v = rec.get(col.src)
    if v is None or v == "":
        return None
    if col.kind in ("num", "pct"):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    return str(v).lower()


def _sorted(rows: list, st: State) -> list:
    col = BY_KEY_ALL.get(st.sort) or BY_KEY["confl"]
    present, absent = [], []
    for r in rows:
        (present if _sort_value(r, col) is not None else absent).append(r)
    present.sort(key=lambda r: _sort_value(r, col), reverse=(st.dir == "desc"))
    return present + absent          # a missing value always sorts LAST, in both directions


def _run(conn, st: State) -> tuple:
    """(rows_all_filtered, sig_date, universe_n, truncated) — the full server-side pipeline."""
    sig_date = R.latest_date(conn)
    syms = R.scope_symbols(conn, st.scope)
    base = R.base_rows(conn, sig_date, syms)
    truncated = len(base) >= R.UNIVERSE_CAP
    need = _needed(st)
    keys = [r["symbol"] for r in base]
    aux = {}
    if keys:
        if "cprD" in need:
            aux["cprD"] = R.cpr_by_tf(conn, keys, "D")
        if "cprW" in need:
            aux["cprW"] = R.cpr_by_tf(conn, keys, "W")
        if "cci" in need:
            aux["cci"] = R.cci_by_sym(conn, keys)
        if "wolfe" in need:
            aux["wolfe"] = R.wolfe_by_sym(conn, keys)
        if "pt14" in need:
            aux["pt14"] = R.pt14_by_sym(conn, keys)
        if "ca" in need:
            aux["ca"] = R.calloc_by_sym(conn, keys)
        if "rev" in need:
            aux["rev"] = R.revctx_by_sym(conn, keys)
        if "fno" in need:
            aux["fno"] = R.fno_by_sym(conn, keys)
    rows = _sorted(_filter(_enrich(base, aux), st), st)
    return rows, sig_date, len(base), truncated


# ── demo fallback (standing correction #4: look full, but never pass demo off as live) ────────
_DEMO = [
    {"symbol": "SAMPLECO", "primary_sector": "Nifty IT", "close": 1842.5, "deliv_per": 46.2,
     "delivery_value_per_trade": 118000.0, "trigger_rank": "P1", "p_score": 5, "r_score": 4,
     "ratio_today_vs_power_1m": 2.4, "rs_rank": 91, "rs_vs_broad_trend_state": "UPTREND",
     "mep_state_smooth": "ACCUM", "mep_score_smooth": 0.42, "accum_character": "ACCUMULATION",
     "pct_from_52w_high": -3.1, "turnover_surge_1m": 2.2, "cprD_pattern": "BULL_U",
     "cci_tier": "A", "turnover": 1.8e9},
    {"symbol": "DEMOIND", "primary_sector": "Nifty Auto", "close": 624.8, "deliv_per": 38.7,
     "delivery_value_per_trade": 74000.0, "trigger_rank": "P2", "p_score": 4, "r_score": 3,
     "ratio_today_vs_power_1m": 1.6, "rs_rank": 83, "rs_vs_broad_trend_state": "IMPROVING",
     "mep_state_smooth": "ACCUM", "mep_score_smooth": 0.21, "accum_character": "ACCUMULATION",
     "pct_from_52w_high": -8.4, "turnover_surge_1m": 1.4, "cprD_pattern": "BULL_U",
     "cci_tier": "B", "turnover": 9.1e8},
    {"symbol": "EXAMPLEBK", "primary_sector": "Nifty Bank", "close": 1290.0, "deliv_per": 51.0,
     "delivery_value_per_trade": 96000.0, "trigger_rank": "P2", "p_score": 3, "r_score": 4,
     "ratio_today_vs_power_1m": 1.1, "rs_rank": 66, "rs_vs_broad_trend_state": "WEAKENING",
     "mep_state_smooth": "NEUTRAL", "mep_score_smooth": -0.05, "accum_character": "MIXED",
     "pct_from_52w_high": -14.2, "turnover_surge_1m": 0.9, "cprD_pattern": "—",
     "cci_tier": "B", "turnover": 1.2e9},
    {"symbol": "PLACEHOLD", "primary_sector": "Nifty Pharma", "close": 388.4, "deliv_per": 29.5,
     "delivery_value_per_trade": 41000.0, "trigger_rank": "P3", "p_score": 2, "r_score": 2,
     "ratio_today_vs_power_1m": 0.8, "rs_rank": 41, "rs_vs_broad_trend_state": "LAGGING",
     "mep_state_smooth": "DISTRIB", "mep_score_smooth": -0.33, "accum_character": "DISTRIBUTION",
     "pct_from_52w_high": -27.9, "turnover_surge_1m": 0.7, "cprD_pattern": "—",
     "cci_tier": "C", "turnover": 3.4e8},
]


def _demo_rows(st: State) -> list:
    return _sorted(_enrich([dict(r) for r in _DEMO], {}), st)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# RENDER
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _fmt(rec, col: Col) -> tuple[str, str]:
    """(cell_text, tone_class) — server-side formatting; the grid never interpolates markup."""
    v = rec.get(col.src)
    if v is None or v == "":
        return ("—", "mut")
    if col.kind == "pct":
        try:
            f = float(v)
        except (TypeError, ValueError):
            return (str(v), "")
        return (f"{f:+.{col.dp}f}%", "up" if f >= 0 else "dn")
    if col.kind == "num":
        txt = C._num(v, col.dp)
        return ((txt + col.unit) if txt != "—" else "—", "")
    if col.kind == "state":
        s = str(v).replace("_", " ").title()
        low = str(v).upper()
        tone = ("up" if ("ACCUM" in low or "UPTREND" in low or "LEADING" in low or "IMPROVING" in low
                         or "BULL" in low) else
                "dn" if ("DISTRIB" in low or "DOWN" in low or "LAGGING" in low or "WEAKEN" in low
                         or "BEAR" in low or "RECLAIM" in low or "SLIP" in low) else "")
        return (s, tone)
    if col.key == "ath":
        return ("yes" if v else "no", "up" if v else "")
    return (str(v), "")


def _thead(st: State, base_url_state: State) -> str:
    ths = []
    for col in SPINE + [BY_KEY[k] for k in st.cols if k in BY_KEY]:
        is_sort = st.sort == col.key
        nxt = "asc" if (is_sort and st.dir == "desc") else "desc"
        href = qs(base_url_state, sort=col.key, dir=nxt, page=1)
        arrow = (" ▼" if st.dir == "desc" else " ▲") if is_sort else ""
        cls = "g-scr-sp" if col.key == "sym" else ""
        aria = ' aria-sort="' + ("descending" if st.dir == "desc" else "ascending") + '"' if is_sort else ""
        help_link = ('<a class="g-scr-q" href="/dash/glossary" title="What does '
                     + C.esc(col.label) + ' mean? Opens the glossary.">?</a>') if col.term else ""
        ths.append('<th class="' + cls + ('" data-on="1"' if is_sort else '"') + aria + ">"
                   '<a class="g-scr-sort" href="' + C.esc(href) + '">' + C.esc(col.label)
                   + arrow + "</a>" + help_link + "</th>")
    # the Pro reference layer — extra columns, hidden in Free, revealed in Pro
    ths.append('<th class="pro-more" title="Where this row\'s sorted value sits inside THIS screen\'s '
               'result set — descriptive context, not a verdict.">Rank in screen</th>')
    ths.append('<th class="pro-more" title="Today\'s turnover against the same name\'s own 1-month '
               'average — is this move unusual FOR THIS STOCK?">vs own 1-mo</th>')
    return "<thead><tr>" + "".join(ths) + "</tr></thead>"


def _pillar_dots(pil) -> str:
    return "".join('<i class="g-scr-d' + (" on" if on else "") + '" title="' + C.esc(name) + '"></i>'
                   for name, on in zip(_PILLARS, pil or ()))


def _tbody(page_rows: list, st: State, pctl: dict) -> str:
    cols = [BY_KEY[k] for k in st.cols if k in BY_KEY]
    trs = []
    for rec in page_rows:
        tds = ['<td class="g-scr-sp">' + sym_link(rec.get("symbol")) + "</td>",
               '<td class="mut">' + C.esc(rec.get("primary_sector") or "—") + "</td>",
               '<td class="g-num">' + C._num(rec.get("close"), 1) + "</td>"]
        for col in cols:
            txt, tone = _fmt(rec, col)
            cls = ("g-num " if col.kind in ("num", "pct") else "") + tone
            extra = ""
            if col.key == "confl":
                extra = '<span class="g-scr-dots">' + _pillar_dots(rec.get("_pillars")) + "</span>"
            tds.append('<td class="' + cls.strip() + '">' + C.esc(txt) + extra + "</td>")
        p = pctl.get(id(rec))
        tds.append('<td class="pro-more g-num">' + (C._ord(p) + " pct" if p is not None else "—") + "</td>")
        su = rec.get("turnover_surge_1m")
        try:
            su_txt = ("%.1f×" % float(su)) if su is not None else "—"
            unusual = su is not None and float(su) >= 2.0
        except (TypeError, ValueError):
            su_txt, unusual = "—", False
        tds.append('<td class="pro-more g-num' + (" up" if unusual else "") + '">' + su_txt + "</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return "<tbody>" + "".join(trs) + "</tbody>"


def _percentiles(rows: list, page_rows: list, st: State) -> dict:
    """The Pro reference number: where each shown row's sorted value sits inside the CURRENT
    filtered result set. Cheap (the set is already in memory) and honestly scoped — it is a
    percentile within this screen, never a claim about the whole market."""
    col = BY_KEY_ALL.get(st.sort) or BY_KEY["confl"]
    vals = [v for v in (_sort_value(r, col) for r in rows) if isinstance(v, (int, float))]
    if len(vals) < 5:
        return {}
    vals.sort()
    out = {}
    for r in page_rows:
        v = _sort_value(r, col)
        if isinstance(v, (int, float)):
            out[id(r)] = 100.0 * sum(1 for f in vals if f <= v) / len(vals)
    return out


def _chip(label: str, href: str, on: bool, title: str = "") -> str:
    return ('<a class="g-scr-chip' + (" on" if on else "") + '" href="' + C.esc(href) + '"'
            + (' title="' + C.esc(title) + '"' if title else "") + ">" + C.esc(label) + "</a>")


def _controls(st: State, sig_date, shown: int, total: int, universe_n: int, truncated: bool) -> str:
    base = st.replace(page=1)
    scope_chips = "".join(
        _chip(nm, qs(base, scope=nm), st.scope == nm) for nm in R.broad_indices())
    scope_chips += _chip("All liquid", qs(base, scope="all"), st.scope.lower() == "all")
    scope_chips += _chip("★ My watchlist", qs(base, scope="watch"),
                         st.scope.lower() in ("watch", "watchlist"))
    if st.scope.lower().startswith("theme:"):
        scope_chips += _chip("Theme · " + st.scope.split(":", 1)[1], qs(base), True)

    sec_opts = "".join('<option value="' + C.esc(s) + '"' + (" selected" if st.scope == s else "")
                       + ">" + C.esc(s) + "</option>" for s in R.sector_indices())
    view_chips = "".join(
        _chip(VIEWS[k][0], qs(base, cols=VIEWS[k][1]), tuple(st.cols) == tuple(VIEWS[k][1]),
              VIEWS[k][2]) for k in VIEWS)

    fam_chips = ""
    active = list(st.cols)
    for fam, lbl, _f in FAMILIES:
        fam_keys = [c.key for c in POOL if c.fam == fam]
        on = any(k in active for k in fam_keys)
        nxt = [k for k in active if k not in fam_keys] if on else active + [
            k for k in fam_keys if k not in active]
        nxt = nxt or list(DEFAULT_COLS)
        fam_chips += _chip(lbl + " (" + str(len(fam_keys)) + ")", qs(base, cols=tuple(nxt)), on)

    rev_chips = (_chip("⚠ Reclaim · floor intact", qs(base, rev=("" if st.rev == "ri" else "ri")),
                       st.rev == "ri",
                       "Band reclaims whose confirmed fractal floor is UNBROKEN. A descriptive watch "
                       "cut — the reclaim cross itself tested as an anti-signal (2026-07-13).")
                 + _chip("⚠ Slip · ceiling intact", qs(base, rev=("" if st.rev == "si" else "si")),
                         st.rev == "si",
                         "The bearish mirror: the trigger slipped below the upper bank while the "
                         "confirmed up-fractal ceiling is UNBROKEN. Descriptive, not a short signal."))

    hidden = ('<input type="hidden" name="scope" value="' + C.esc(st.scope) + '">'
              '<input type="hidden" name="cols" value="' + C.esc(",".join(st.cols)) + '">'
              '<input type="hidden" name="sort" value="' + C.esc(st.sort) + '">'
              '<input type="hidden" name="dir" value="' + C.esc(st.dir) + '">'
              + ('<input type="hidden" name="rev" value="' + C.esc(st.rev) + '">' if st.rev else ""))
    conf_opts = "".join('<option value="' + str(i) + '"' + (" selected" if st.minconf == i else "")
                        + ">" + ("any" if i == 0 else str(i) + "+") + "</option>" for i in range(7))
    n_opts = "".join('<option value="' + str(i) + '"' + (" selected" if st.n == i else "")
                     + ">" + str(i) + " rows</option>" for i in PAGE_SIZES)
    filter_form = (
        '<form class="g-scr-bar" method="get" action="/dash/home/screen" role="search">' + hidden
        + '<input class="g-scr-in" type="search" name="q" value="' + C.esc(st.q)
        + '" placeholder="Filter — symbol, sector, state…" aria-label="Filter rows">'
        '<label class="g-scr-lab">Confluence <select name="minconf">' + conf_opts + "</select></label>"
        '<label class="g-scr-lab">Show <select name="n">' + n_opts + "</select></label>"
        '<button class="g-btn" type="submit">Apply</button>'
        '<a class="g-scr-chip" href="/dash/home/screen">Reset</a>'
        "</form>")

    sector_form = ('<form class="g-scr-bar" method="get" action="/dash/home/screen">'
                   '<input type="hidden" name="cols" value="' + C.esc(",".join(st.cols)) + '">'
                   '<label class="g-scr-lab">Sector <select name="scope" '
                   'onchange="this.form.submit()"><option value="">choose…</option>'
                   + sec_opts + "</select></label>"
                   '<noscript><button class="g-btn" type="submit">Go</button></noscript></form>')

    n_cols = len(st.cols) + len(SPINE)
    cap_note = ("" if len(st.cols) <= SOFT_CAP else
                '<span class="g-scr-warn">' + str(len(st.cols)) + " columns — past the "
                + str(SOFT_CAP) + "-column comfort limit; a second saved screen usually reads better.</span>")
    trunc = ("" if not truncated else
             '<span class="g-scr-warn">Universe capped at ' + f"{R.UNIVERSE_CAP:,}"
             + " names for this scope (ranked by pillar alignment before the cap).</span>")

    csv_href = qs(st, format="csv")
    meta = ('<div class="g-scr-bar g-scr-meta"><span>' + f"{shown:,}" + " of " + f"{total:,}"
            + " matching · " + f"{universe_n:,}" + " in scope · as of "
            + C.esc(str(sig_date)[:10] if sig_date else "—") + "</span>"
            '<a class="g-scr-chip" href="' + C.esc(csv_href) + '" '
            'title="Downloads exactly what this URL shows — same scope, filter, sort and columns.">'
            "⬇ CSV (this screen)</a>"
            '<span class="g-scr-lab">' + str(n_cols) + " columns shown of "
            + str(len(POOL) + len(SPINE)) + " available</span>" + cap_note + trunc + "</div>")

    return ('<div class="g-scr-bar">' + scope_chips + "</div>" + sector_form
            + '<div class="g-scr-bar"><span class="g-scr-lab">Views</span>' + view_chips + "</div>"
            '<div class="g-scr-bar"><span class="g-scr-lab">Columns</span>' + fam_chips + "</div>"
            '<div class="g-scr-bar"><span class="g-scr-lab">Cuts</span>' + rev_chips + "</div>"
            + filter_form + meta)


def _pager(st: State, total: int, eff_n: int) -> str:
    pages = max(1, (total + eff_n - 1) // eff_n)
    page = min(st.page, pages)
    lo = 0 if not total else (page - 1) * eff_n + 1
    hi = min(page * eff_n, total)
    prev = ('<a class="g-scr-chip" href="' + C.esc(qs(st, page=page - 1)) + '">← Previous</a>'
            if page > 1 else '<span class="g-scr-chip off">← Previous</span>')
    nxt = ('<a class="g-scr-chip" href="' + C.esc(qs(st, page=page + 1)) + '">Next →</a>'
           if page < pages else '<span class="g-scr-chip off">Next →</span>')
    note = ("" if eff_n >= st.n else
            '<span class="g-scr-warn">' + str(eff_n) + " rows per page (asked for " + str(st.n)
            + ") — this view is "
            + str(len(st.cols) + len(SPINE)) + " columns wide, so pages are kept shorter to stay "
            "quick to load. Narrow the columns to see more rows at once.</span>")
    return ('<div class="g-scr-bar g-scr-pager">' + prev
            + '<span class="g-scr-lab">' + f"{lo:,}–{hi:,}" + " of " + f"{total:,}"
            + " · page " + str(page) + " of " + str(pages) + "</span>" + nxt + note + "</div>")


def _active_fences(st: State) -> str:
    out = ""
    seen = set()
    for k in st.cols:
        fam = BY_KEY[k].fam if k in BY_KEY else None
        if fam and fam not in seen and FAM_FENCE.get(fam):
            seen.add(fam)
            out += C.fence(FAM_LABEL[fam] + " — " + FAM_FENCE[fam])
    return out


_HOW_TO_READ = (
    "<p>Pick a <b>scope</b> (an index, your watchlist, everything liquid, or a theme), then a "
    "<b>view</b> — a named set of columns for one question. Add or drop whole column families, "
    "sort on any column, and narrow with the filter box. Nothing is hidden behind a plan: every "
    "column, filter and export is free.</p>"
    "<p>The <b>Confluence</b> column counts how many independent pillars line up on a name today "
    "(delivery positioning · accumulation · relative strength · structure · credibility · geometry). "
    "It is a way to <i>sort a shortlist</i>, not a score to act on — the pillars were built and "
    "tested separately, and several of them are explicitly descriptive-only.</p>"
    "<p><b>The address bar is the saved screen.</b> Every choice you make is in the URL, so you can "
    "bookmark it, share it, or paste it to a colleague and they see exactly your screen. The CSV "
    "button downloads that same screen — same scope, same filter, same sort, same columns.</p>"
    "<p>Only liquid names are shown: a stock must trade at or above the 30th percentile of the "
    "day's exchange turnover. That floor re-derives from the data every day rather than sitting at "
    "a fixed rupee number.</p>")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════════════════════
@router.get("/dash/home/screen", include_in_schema=False)
def screen(request: Request):
    """The Graphite screener. `?format=csv` returns the SAME screen as a server-side CSV."""
    st = parse_state(request.query_params)
    want_csv = str(request.query_params.get("format", "")).lower() == "csv"
    rows, sig_date, universe_n, truncated, is_demo = [], None, 0, False, False
    try:
        from src.core.db import get_conn
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            rows, sig_date, universe_n, truncated = _run(conn, st)
            pat = "" if want_csv else _pat(conn)
    except Exception:  # noqa: BLE001 — a busy/edge DB must never 500 the screener
        rows, sig_date, universe_n, truncated, pat = [], None, 0, False, ""
    if not rows and not st.q and not st.minconf and not st.rev:
        rows, is_demo = _demo_rows(st), True

    if want_csv:
        return _csv_response(rows[:CSV_CAP], st, sig_date, is_demo)

    total = len(rows)
    eff_n = effective_n(st)
    pages = max(1, (total + eff_n - 1) // eff_n)
    page = min(st.page, pages)
    page_rows = rows[(page - 1) * eff_n: page * eff_n]
    pctl = _percentiles(rows, page_rows, st)

    grid = ('<div class="g-scr-box" tabindex="0" role="region" aria-label="Screen results">'
            '<table class="g-scr">' + _thead(st, st.replace(page=1))
            + _tbody(page_rows, st, pctl) + "</table></div>") if page_rows else C.empty(
        "No names match this screen. Widen the scope, lower the confluence minimum, or clear the filter.")

    teaser = C.pro_teaser(
        '<div class="g-scr-teaser">Pro adds the <b>reference layer</b>: where each row sits inside '
        'this screen&rsquo;s result set, and whether today&rsquo;s activity is unusual '
        '<i>for that stock</i> against its own recent tape.</div>'
        + C.ref_chip({"pctile": 82, "typical": 1.0, "n": 250}, unit="×", dp=1, trend="up", bare=True),
        cta_sub="Every column, filter and export stays free.", advertise=True)

    body = (C.zone(
        "Screen", "stock_signals · MEP · CPR · CCI · nightly",
        _controls(st, sig_date, total, total, universe_n, truncated)
        + teaser + grid + _pager(st, total, eff_n)
        + C.learn("Each row is one liquid stock on the latest exchange close. Every value is a stored, "
                  "precomputed number — nothing is recomputed or predicted on the fly."),
        sub="build a shortlist, share it as a link", sample=is_demo, name="Screen")
        + C.zone("How to read this screen", "docs/metrics-glossary.md",
                 C.drawer("How to read this screen", "SCREEN", "scope · views · columns · the URL",
                          _HOW_TO_READ, is_open=False)
                 + _active_fences(st)
                 + '<p class="g-scr-note">Themes and baskets are a different door onto the same data — '
                 '<a class="g-syma" href="/dash/home/themes">browse by what companies actually do →</a></p>',
                 sub="plain English", name="How to read"))
    return HTMLResponse(shell.shell("Screen", body, extra_head=_CSS, current="Stocks", pat_html=pat))


def _csv_response(rows: list, st: State, sig_date, is_demo: bool) -> Response:
    """Debt #2 fixed: the export is produced by the SERVER from the same filtered, sorted result set
    that rendered the page — not scraped out of whatever the DOM happened to be showing."""
    cols = SPINE + [BY_KEY[k] for k in st.cols if k in BY_KEY]
    buf = _io.StringIO()
    w = _csv.writer(buf, lineterminator="\n")
    w.writerow(["# patearn screen", "as of " + str(sig_date or "")[:10],
                "scope=" + st.scope, "sort=" + st.sort + " " + st.dir,
                ("filter=" + st.q) if st.q else "filter=",
                ("min confluence=" + str(st.minconf)) if st.minconf else "min confluence=any",
                ("cut=" + st.rev) if st.rev else "cut=none",
                "SAMPLE DATA — not a live read" if is_demo else "live"])
    w.writerow([c.label for c in cols])
    for rec in rows:
        w.writerow([rec.get(c.src) if rec.get(c.src) is not None else "" for c in cols])
    stem = "".join(ch if ch.isalnum() else "_" for ch in st.scope)[:32] or "screen"
    return Response(content=buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="patearn_screen_'
                                                    + stem + '.csv"',
                             "Cache-Control": "no-store"})


def _pat(conn) -> str:
    try:
        from src.web.home import pat_dock
        return pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — the dock is chrome; never fatal
        return ""


# ── themes / baskets ──────────────────────────────────────────────────────────────────────────
def _theme_board_html(board: list) -> str:
    if not board:
        return C.empty("The theme layer hasn't been seeded on this host yet.")
    out = ""
    for grp in board:
        items = ""
        for t in grp["themes"]:
            n = t["n"]
            items += ('<a class="g-scr-theme" href="/dash/home/themes?tag=' + _q(t["label"]) + '">'
                      '<span class="g-scr-tname">' + C.esc(t["label"]) + "</span>"
                      '<span class="g-scr-tn g-num">' + str(n) + "</span>"
                      '<span class="g-scr-tb">' + C.esc(t["blurb"]) + "</span>"
                      + ('<span class="g-scr-tsrc">index-seeded</span>' if t["seeded"] else "")
                      + "</a>")
        out += ('<div class="g-scr-tgroup"><h3>' + C.esc(grp["group"]) + "</h3>"
                '<div class="g-scr-tgrid">' + items + "</div></div>")
    return out


def _theme_detail_html(conn, tag: str) -> str:
    syms = R.theme_members(conn, tag)
    prov = R.theme_provenance(conn, tag)
    bits = []
    if prov.get("index"):
        bits.append(str(prov["index"]) + " seeded from an NSE thematic index (a fact)")
    if prov.get("ramana"):
        bits.append(str(prov["ramana"]) + " hand-approved")
    if prov.get("ai"):
        bits.append(str(prov["ai"]) + " AI-proposed and approved")
    prov_txt = " · ".join(bits) if bits else "no approved members yet"
    if not syms:
        return (C.empty("No approved companies carry this theme yet.")
                + '<p class="g-scr-note"><a class="g-syma" href="/dash/home/themes">← all themes</a></p>')
    sig_date = R.latest_date(conn)
    rows = R.base_rows(conn, sig_date, syms, cap=400)
    n_lead = sum(1 for r in rows if (r.get("rs_rank") or 0) >= 80)
    n_acc = sum(1 for r in rows if (r.get("mep_state_smooth") or "") in ("ACCUM", "STRONG_ACCUM"))
    tiles = ('<div class="g-scr-tiles">' + C.tile("Companies tagged", str(len(syms)), "approved tags")
             + C.tile("With signals today", str(len(rows)), "liquid + priced")
             + C.tile("Relative-strength leaders", str(n_lead), "RS rank 80+")
             + C.tile("Being accumulated", str(n_acc), "delivery accumulation state") + "</div>")
    trs = "".join(
        "<tr>" + '<td class="g-scr-sp">' + sym_link(r.get("symbol")) + "</td>"
        '<td class="mut">' + C.esc(r.get("primary_sector") or "—") + "</td>"
        '<td class="g-num">' + C._num(r.get("close"), 1) + "</td>"
        '<td class="g-num">' + (str(r.get("rs_rank")) if r.get("rs_rank") is not None else "—") + "</td>"
        '<td>' + C.esc(str(r.get("rs_vs_broad_trend_state") or "—").replace("_", " ").title()) + "</td>"
        '<td>' + C.esc(str(r.get("mep_state_smooth") or "—").replace("_", " ").title()) + "</td>"
        '<td>' + C.esc(str(r.get("accum_character") or "—").title()) + "</td>" + "</tr>"
        for r in sorted(rows, key=lambda r: (r.get("rs_rank") is None, -(r.get("rs_rank") or 0))))
    table = ('<div class="g-scr-box" tabindex="0" role="region" aria-label="Theme members">'
             '<table class="g-scr"><thead><tr><th class="g-scr-sp">Symbol</th><th>Sector</th>'
             "<th>CMP</th><th>RS rank</th><th>RS trend</th><th>Accumulation</th><th>Character</th>"
             "</tr></thead><tbody>" + trs + "</tbody></table></div>")
    return (tiles + '<p class="g-scr-note">Provenance: ' + C.esc(prov_txt) + " · "
            '<a class="g-syma" href="/dash/home/screen?scope=theme:' + _q(tag)
            + '">open these names in the screener →</a> · '
            '<a class="g-syma" href="/dash/home/themes">← all themes</a></p>' + table)


@router.get("/dash/home/themes", response_class=HTMLResponse, include_in_schema=False)
def themes(request: Request) -> HTMLResponse:
    """Themes / baskets — the non-ticker door. A company can carry several themes at once, so this
    is deliberately MULTI-LABEL: an EPC name is Infrastructure and Industrialization-proxy and
    Transport. Sector/capex themes are seeded deterministically from the NSE thematic indices (a
    fact); cross-cutting themes are filled by review. A map of the market's stories, not a ranking."""
    tag = str(request.query_params.get("tag", "") or "").strip()[:60]
    body, pat = "", ""
    try:
        from src.core.db import get_conn
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            pat = _pat(conn)
            inner = _theme_detail_html(conn, tag) if tag else _theme_board_html(R.theme_board(conn))
    except Exception:  # noqa: BLE001
        inner = C.empty("The theme layer hasn't landed on this host yet.")
    title = (tag + " · theme") if tag else "Themes & baskets"
    body = C.zone(
        title, "company_tags · NSE thematic indices", inner,
        sub=("who is in this theme" if tag else "browse by what companies actually do"),
        name="Themes") + C.zone(
        "How to read themes", "docs/metrics-glossary.md",
        C.learn("Themes are multi-label on purpose: one company can sit in several stories at once, "
                "and forcing it into a single bucket would lose information. Counts are approved tags "
                "only. Nothing here is scored or ranked — it is a way to find names you would not "
                "have typed into a search box.")
        + C.fence("Descriptive grouping only. A theme is not a recommendation, a basket you can buy, "
                  "or a claim that the companies in it will move together."),
        sub="plain English", name="How to read themes")
    return HTMLResponse(shell.shell(("Theme · " + tag) if tag else "Themes", body,
                                    extra_head=_CSS, current="Stocks", pat_html=pat))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CSS — scoped `:root[data-ui-g] .g-scr-*`, injected via the shell's extra_head so neither
# components.py nor the shared token sheet is co-edited by this lane.
# ══════════════════════════════════════════════════════════════════════════════════════════════
_CSS = """<style>/* g-screen w4 */
:root[data-ui-g] .g-scr-bar{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:0 0 8px}
:root[data-ui-g] .g-scr-lab{font:600 9.5px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);margin-right:2px}
:root[data-ui-g] .g-scr-chip{font:600 11.5px/1 var(--font);color:var(--ink-2);background:var(--bg-2);
  border:1px solid var(--line-2);border-radius:var(--r-pill);padding:6px 11px;text-decoration:none;white-space:nowrap}
:root[data-ui-g] .g-scr-chip:hover{color:var(--ink);border-color:var(--accent)}
:root[data-ui-g] .g-scr-chip.on{color:var(--on-accent);background:linear-gradient(120deg,var(--accent),var(--accent-hi));border-color:transparent}
:root[data-ui-g] .g-scr-chip.off{opacity:.4}
:root[data-ui-g] .g-scr-in,:root[data-ui-g] .g-scr-bar select{font:inherit;font-size:12.5px;
  background:var(--bg-1);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:6px 10px}
:root[data-ui-g] .g-scr-in{min-width:230px}
:root[data-ui-g] .g-scr-meta{color:var(--ink-3);font-size:11.5px;margin-top:2px}
:root[data-ui-g] .g-scr-warn{color:var(--warn,#c69316);font-size:11.5px}
/* the fixed-size, internally-scrolling grid — never a flat endless page (standing correction #3) */
:root[data-ui-g] .g-scr-box{max-height:60vh;overflow:auto;border:1px solid var(--line);
  border-radius:12px;background:var(--bg-1);scrollbar-width:thin}
:root[data-ui-g] table.g-scr{border-collapse:separate;border-spacing:0;width:100%;font-size:12.5px}
:root[data-ui-g] table.g-scr th{position:sticky;top:0;z-index:3;background:var(--bg-3);
  text-align:left;font:600 10.5px/1.3 var(--font);letter-spacing:.05em;text-transform:uppercase;
  color:var(--ink-2);padding:9px 10px;border-bottom:1px solid var(--line-2);white-space:nowrap}
:root[data-ui-g] table.g-scr th[data-on]{color:var(--accent)}
:root[data-ui-g] table.g-scr th.g-scr-sp{left:0;z-index:4}
:root[data-ui-g] table.g-scr td{padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
:root[data-ui-g] table.g-scr td.g-scr-sp{position:sticky;left:0;z-index:2;background:var(--bg-1)}
:root[data-ui-g] table.g-scr tr:hover td{background:var(--bg-2)}
:root[data-ui-g] table.g-scr tr:hover td.g-scr-sp{background:var(--bg-2)}
:root[data-ui-g] table.g-scr td.g-num{text-align:right;font-variant-numeric:tabular-nums}
:root[data-ui-g] table.g-scr td.up{color:var(--up)} :root[data-ui-g] table.g-scr td.dn{color:var(--dn,var(--down))}
:root[data-ui-g] table.g-scr td.mut{color:var(--ink-3)}
:root[data-ui-g] .g-scr-sort{color:inherit;text-decoration:none}
:root[data-ui-g] .g-scr-sort:hover{color:var(--accent)}
:root[data-ui-g] .g-scr-q{color:var(--ink-3);text-decoration:none;margin-left:5px;font-size:10px;
  border:1px solid var(--line-2);border-radius:50%;padding:0 4px}
:root[data-ui-g] .g-scr-q:hover{color:var(--accent);border-color:var(--accent)}
:root[data-ui-g] .g-scr-dots{display:inline-flex;gap:2px;margin-left:6px;vertical-align:middle}
:root[data-ui-g] .g-scr-d{width:5px;height:5px;border-radius:50%;background:var(--line-2);display:inline-block}
:root[data-ui-g] .g-scr-d.on{background:var(--accent)}
:root[data-ui-g] .g-scr-pager{justify-content:space-between;margin-top:10px}
:root[data-ui-g] .g-scr-note{font-size:12px;color:var(--ink-3);margin:10px 0 0}
:root[data-ui-g] .g-scr-teaser{font-size:12.5px;color:var(--ink-2);margin-bottom:8px}
/* themes */
:root[data-ui-g] .g-scr-tgroup{margin-bottom:18px}
:root[data-ui-g] .g-scr-tgroup h3{font:700 10.5px/1 var(--font);letter-spacing:.1em;text-transform:uppercase;
  color:var(--accent);margin:0 0 9px;border-bottom:1px solid var(--line);padding-bottom:6px}
:root[data-ui-g] .g-scr-tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:9px}
:root[data-ui-g] .g-scr-theme{display:block;padding:10px 12px;border:1px solid var(--line-2);
  border-radius:10px;background:var(--bg-2);text-decoration:none;color:var(--ink)}
:root[data-ui-g] .g-scr-theme:hover{border-color:var(--accent)}
:root[data-ui-g] .g-scr-tname{font-weight:700;font-size:13px}
:root[data-ui-g] .g-scr-tn{float:right;color:var(--accent);font-weight:700;font-size:13px}
:root[data-ui-g] .g-scr-tb{display:block;font-size:11.5px;color:var(--ink-3);margin-top:3px;line-height:1.4}
:root[data-ui-g] .g-scr-tsrc{display:inline-block;margin-top:6px;font:600 9px/1 var(--mono);
  letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
:root[data-ui-g] .g-scr-tiles{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
</style>"""
