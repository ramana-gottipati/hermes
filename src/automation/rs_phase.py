"""Unified RS rotation *phase* — the weather/quadrant label shared by stocks and
sectors — plus the additive-column guard for the whole rotation feature.

Part of the RS-rotation build (session 25; design in
``docs/rs-rotation-design.md``). The four-phase rotation:

    🌤 Tailwind     strong & strengthening   (= strong-in-strong)
    🌅 Recovery     deep base turning up      (= the "improving" turn)
    ⛅ Rolling-over  a leader cracking         (= the reverse of recovery)
    🌧 Headwind     weak & weakening          (= weak-in-weak)
    ☁ Neutral      consolidating / undefined

Self-contained (the ``rrg.py`` / ``capture.py`` / ``oscillators.py`` pattern):
this module OWNS the additive rotation columns and ensures them at runtime via
``db._ensure_column`` — it NEVER edits ``db.py`` (which a parallel session holds
uncommitted). All additive: existing columns/tables are untouched. Pure
arithmetic, no LLM.

The classifier ``rs_weather()`` is PORTED VERBATIM from ``src/web/cockpit.py``
``sector_weather()`` so the rotation label is byte-identical to the sector-weather
badge the UI already ships (Ramana's "weather, project-native" choice). The two
copies are kept in sync by ``_selftest`` pinning the contract; a future cleanup
can unify them once ``db.py`` / ``cockpit.py`` are free of the parallel hold.
"""

from __future__ import annotations

import argparse
import logging

log = logging.getLogger("hermes.rs_phase")

# Display labels (the emoji-name only; colors stay in cockpit._WEATHER for the
# web layer). Lets the non-web surfaces (Telegram) render a phase without a
# backward web import.
WEATHER_LABEL = {
    "TAILWIND":     "🌤 Tailwind",
    "RECOVERY":     "🌅 Recovery",
    "HEADWIND":     "🌧 Headwind",
    "ROLLING-OVER": "⛅ Rolling over",
    "NEUTRAL":      "☁ Neutral",
}
WEATHER_KEYS = tuple(WEATHER_LABEL.keys())


def rs_weather(s1, s3, s6, s12, st, breadth=None, accum_skew=None):
    """Classify an RS series' weather from its 1m/3m/6m/12m slopes + trend_state
    (+ optional constituent breadth / accumulation skew). First-match-wins.
    Returns ``(key, reasons[])``. Generic over numerator: a sector's RS-vs-broad
    OR a stock's RS-vs-broad both classify here.

    PORTED VERBATIM from src/web/cockpit.py ``sector_weather`` — keep in sync
    (``_selftest`` pins it)."""
    a1, a3, a6, a12 = (s1 or 0.0), (s3 or 0.0), (s6 or 0.0), (s12 or 0.0)
    up = st in ("UPTREND", "BREAKOUT")
    down = st in ("DOWNTREND", "BREAKDOWN")
    R = []
    if (up and a3 > 1 and a1 > 0
            and (breadth is None or breadth >= 55)
            and (accum_skew is None or accum_skew >= 0)):
        R = [f"RS {(st or '').lower()}", f"3m slope {a3:+.1f}", f"1m {a1:+.1f}"]
        if breadth is not None:
            R.append(f"{breadth:.0f}% members RS-up")
        return "TAILWIND", R
    if ((a6 < 0 or a12 < 0) and a1 > 1 and a3 > a6
            and (breadth is None or breadth > 40)):
        R = ["longer-horizon RS still negative", f"1m slope {a1:+.1f} turning up",
             f"3m {a3:+.1f} > 6m {a6:+.1f}"]
        return "RECOVERY", R
    if (down and a3 < -1
            and (breadth is None or breadth < 45)
            and (accum_skew is None or accum_skew <= 0)):
        R = [f"RS {(st or '').lower()}", f"3m slope {a3:+.1f}"]
        if breadth is not None:
            R.append(f"only {breadth:.0f}% members RS-up")
        return "HEADWIND", R
    if up and a1 < 0 and a12 > 0:
        R = [f"12m slope {a12:+.1f} positive", f"1m {a1:+.1f} rolling over"]
        return "ROLLING-OVER", R
    return "NEUTRAL", [f"3m slope {a3:+.1f}"]


def phase_key(s1, s3, s6, s12, st) -> str:
    """Just the weather KEY (no reasons) — what we store in ``rs_phase``."""
    return rs_weather(s1, s3, s6, s12, st)[0]


# ── additive-column guard (owns its schema; never edits db.py) ────────────────
# {table: [(column, decl), ...]}. ratio_signals/index_signals/stock_signals are
# EXISTING tables — we only ADD nullable columns. Idempotent.
_ROTATION_COLUMNS = {
    "ratio_signals": [
        ("slope_18m_pct", "REAL"),
        ("slope_24m_pct", "REAL"),
    ],
    "index_signals": [
        ("rs_vs_broad_slope_18m", "REAL"),
        ("rs_vs_broad_slope_24m", "REAL"),
        ("rs_phase", "TEXT"),
    ],
    "stock_signals": [
        ("rs_vs_broad_slope_18m",  "REAL"),
        ("rs_vs_broad_slope_24m",  "REAL"),
        ("rs_vs_sector_slope_18m", "REAL"),
        ("rs_vs_sector_slope_24m", "REAL"),
        ("rs_phase",  "TEXT"),
        ("rsi_of_rs", "REAL"),
    ],
}

_ensured = False


def ensure_columns(conn) -> None:
    """Idempotently add the rotation columns to the existing signal tables, using
    db._ensure_column (imported lazily to avoid any import cycle). Guarded so the
    PRAGMA work runs once per process — safe to call from every write path. A
    missing table (e.g. on a fresh stub DB) is skipped, never fatal."""
    global _ensured
    if _ensured:
        return
    from src.core.db import _ensure_column
    existing = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for table, cols in _ROTATION_COLUMNS.items():
        if table not in existing:
            continue
        for col, decl in cols:
            _ensure_column(conn, table, col, decl)
    # Rotation read index (idempotent). The phase filter (phase_members/shortlist)
    # and the movers prior-day lookup both hit rs_phase; without this they
    # full-scan the multi-million-row stock_signals history — the /dash/rotation
    # slowness (movers was ~8s). One composite index fixes both.
    if "stock_signals" in existing:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_phase "
                     "ON stock_signals(rs_phase, trade_date)")
    _ensured = True


# ── self-check (no DB) — pins the ported classifier to its contract ───────────
def _selftest() -> None:
    cases = [
        # (s1, s3, s6, s12, trend_state) -> expected key
        ((2.0, 2.0, 1.0, 1.0, "UPTREND"),       "TAILWIND"),
        ((2.0, 0.5, -1.0, -2.0, "CONSOLIDATING"), "RECOVERY"),
        ((-1.0, -2.0, -1.0, -1.0, "DOWNTREND"),  "HEADWIND"),
        ((-0.5, 0.5, 1.0, 2.0, "UPTREND"),       "ROLLING-OVER"),
        ((0.0, 0.0, 0.0, 0.0, "CONSOLIDATING"),  "NEUTRAL"),
        ((None, None, None, None, None),         "NEUTRAL"),  # all-None never crashes
    ]
    for args, expected in cases:
        got = phase_key(*args)
        assert got == expected, f"rs_weather{args} = {got}, expected {expected}"
    assert set(WEATHER_LABEL) == set(WEATHER_KEYS)
    print("rs_phase selftest: OK")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.selftest:
        _selftest()
        return
    print("rs_phase: classifier module; run with --selftest")


if __name__ == "__main__":
    main()
