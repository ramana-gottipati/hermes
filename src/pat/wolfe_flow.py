"""Pat 'wolfe' data-flow — currently-open Wolfe setups answered inline (UX audit S-E Ph2).

Answers "any wolfe setups / open wolfe trades / show me the wolfe waves" with the currently-OPEN
Wolfe waves (point-5 printed, EPA target not yet reached) — the nightly snapshot behind
/dash/wolfe/trades. Reuses `wolfe.latest_open_scan()` (snapshot-instant; no live compute).

CONTRACT (mirrors internals_flow.py / rotation_flow.py):
  * PURE logic here — `parse_wolfe()` (a ₹0 pre-pass in engine.route) and `open_trades()` (a
    bounded read over the `wolfe_open_signals` snapshot). Render = web.py:_wolfe_flow.
  * CONSERVATIVE: needs a wolfe cue + an open/setup/trade cue, and runs AFTER nav so "where do I
    see the wolfe scanner" stays a navigate. A miss yields None.
  * DESCRIPTIVE / SEBI-safe: Wolfe carries NO buy/sell signal — its only validated edge is
    SELECTION (which name / direction / when), on FRESH <=15d winner-profile entries; older open
    trades have run left but no validated entry-edge (badged "open · judge the run"). Never advice.
"""
from __future__ import annotations

import re

# a wolfe cue AND an open/setup/trade cue (so "where do I see wolfe" — a nav ask — is not us)
_WOLFE_RE = re.compile(r"\bwolfe(?:\s*waves?)?\b")
_OPEN_RE = re.compile(r"\b(setups?|open|trades?|waves?|any|show|list|running|live|current)\b")

_ON_RE = re.compile(r"\b(?:on|for|in|of)\s+([A-Za-z][A-Za-z0-9&.\-]{1,14})\b")
_NOT_TICKER = {"WOLFE", "ANY", "THE", "OPEN", "SETUP", "SETUPS", "TRADE", "TRADES", "WAVE", "WAVES"}


def parse_wolfe(query: str) -> dict | None:
    """"any wolfe setups / open wolfe trades / wolfe setup on TCS" ->
    {flow:"wolfe", params:{symbol}} | None. Needs a wolfe cue + an open/setup/trade cue; a bare
    "wolfe" alone (or a nav 'where is wolfe' ask, handled earlier) yields."""
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    if not _WOLFE_RE.search(ql) or not _OPEN_RE.search(ql):
        return None
    sym = ""
    m = _ON_RE.search(q)
    if m and m.group(1).upper() not in _NOT_TICKER:
        sym = m.group(1).upper()
    return {"flow": "wolfe", "params": {"symbol": sym}}


def open_trades(conn, *, symbol: str = "", limit: int = 8) -> dict | None:
    """The currently-open Wolfe setups from the nightly snapshot (reuses wolfe.latest_open_scan).
    Returns {as_of, rows:[...], n_total, held_out} or None when the snapshot isn't built.
    Coherent rows only (drops price-through-stop `invalid`); optional single-symbol filter.
    Read-only; the row shape is wolfe's own (sym, dir, cmp, zlo, zhi, sl, t1, run, rr, Q, age…)."""
    if conn is None:
        return None
    try:
        from src.automation import wolfe as _W
        snap = _W.latest_open_scan(conn)
    except Exception:
        return None
    if not snap or not snap.get("rows"):
        return None
    rows = [r for r in snap["rows"] if not r.get("invalid")]
    if symbol:
        rows = [r for r in rows if str(r.get("sym", "")).upper() == symbol.upper()]
    # sort by remaining run to target, desc (wolfe's own default ranking)
    rows.sort(key=lambda r: (r.get("run") if isinstance(r.get("run"), (int, float)) else -1e9),
              reverse=True)
    return {"as_of": snap.get("scan_date") or snap.get("computed_at") or "",
            "rows": rows[: max(1, int(limit))], "n_total": len(rows),
            "held_out": snap.get("held_out") or 0}


def is_fresh(row: dict, fresh_days: int = 15) -> bool:
    """A FRESH <=15d winner-profile entry carries the validated selection edge (★ edge); an older
    open trade has run left but no validated entry-edge ("open · judge the run")."""
    age = row.get("age")
    return isinstance(age, (int, float)) and age <= fresh_days


def _selftest() -> int:
    import sqlite3
    # recognition — wolfe cue + open/setup/trade cue
    assert parse_wolfe("any wolfe setups")["flow"] == "wolfe"
    assert parse_wolfe("open wolfe trades")["params"]["symbol"] == ""
    assert parse_wolfe("show me the wolfe waves")["flow"] == "wolfe"
    assert parse_wolfe("wolfe setup on TCS")["params"]["symbol"] == "TCS"
    assert parse_wolfe("are there any wolfe waves running")["flow"] == "wolfe"
    # yields — no open/setup cue, or no wolfe word
    assert parse_wolfe("wolfe") is None, "bare 'wolfe' → nav/other, not us"
    assert parse_wolfe("harmonic setups") is None, "not wolfe"
    assert parse_wolfe("what changed today") is None
    assert parse_wolfe("") is None
    # read degrades to None when the snapshot table is absent (no crash)
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    assert open_trades(c) is None
    assert open_trades(None) is None
    # freshness helper
    assert is_fresh({"age": 3}) and not is_fresh({"age": 40}) and not is_fresh({"age": None})
    c.close()
    print("wolfe_flow selftest OK — recognition (wolfe + open/setup/trade cue; yields on bare "
          "'wolfe'/non-wolfe) + snapshot read degrades to None when unbuilt + fresh<=15d badge.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
