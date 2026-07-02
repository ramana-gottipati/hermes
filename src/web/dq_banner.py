"""Kill-switch WARN/CRIT surfacing — data-first: show, don't hide (validation memo §5).

Maps each affected page (its lens `active` key) to the data-quality checks that gate what
that page shows, and injects a compact strip above the body whenever the LATEST nightly
`data_quality` run has one of those checks at warn/critical. The strip quotes the check's
own message (they are written for humans) + the run date, so a stale scan, a regime-OFF
market or a restatement spike is visible ON the surface it affects, not buried in a log.

Isolated module (parallel-sessions doctrine — no dashboard/cockpit edit): v2_surfaces.wire()
calls install(), which wraps dashboard._shell (the same seam shell_skin / table_controls
use). Defensive (any failure renders the page unchanged), idempotent (sentinel on wrapper
and body), and cached (one DB read per _TTL seconds per process — the battery only writes
nightly, and a reader must never stall a page behind a busy writer).
"""
from __future__ import annotations

import html
import time

# check groups (names as persisted in data_quality_runs.report_json)
_MOM = ("killswitch.market_freshness", "killswitch.regime", "killswitch.universe_drift")
_FLOW = ("killswitch.feed_freshness",)
_FUND = ("killswitch.restatement_spike", "fundamentals_history.dates")

# lens `active` key -> checks that gate the page; () = every check (the trust home).
_PAGES = {
    "momentum-scan": _MOM, "rrg": _MOM, "rotation": _MOM, "rsband": _MOM,
    "cycle-clock": _MOM, "leaders": _MOM, "stocks": _MOM,
    "capture-map": _MOM + _FLOW, "participants": _FLOW, "mep": _FLOW,
    "screen2": _FUND, "screener": _FUND, "strategist": _FUND,
    "growth": _FUND, "conviction": _FUND,
    "coverage": (),
}

_SENTINEL = "dqb-strip"
_TTL = 600            # battery writes nightly; refresh at most every 10 min
_TTL_ERR = 120        # after a failed read (e.g. writer holds the lock) retry sooner
_MAX_LINES = 3

_cache: dict = {"at": 0.0, "ttl": 0, "run_at": None, "bad": []}


def _fetch() -> tuple:
    """(run_at, [(check, severity, message), ...]) for warn/critical checks of the most
    recent persisted run. Cached; never raises."""
    now = time.time()
    if now - _cache["at"] < _cache["ttl"]:
        return _cache["run_at"], _cache["bad"]
    run_at, bad, ttl = None, [], _TTL
    try:
        from src.automation import data_quality as DQ
        lr = DQ.last_run()
        if lr:
            run_at = lr.get("run_at")
            for k in ((lr.get("report") or {}).get("checks") or []):
                if k.get("severity") in (DQ.SEV_WARN, DQ.SEV_CRIT):
                    bad.append((k.get("check", ""), k["severity"], k.get("message", "")))
    except Exception:  # noqa: BLE001 — a busy/absent DB must never break a page
        ttl = _TTL_ERR
    _cache.update(at=now, ttl=ttl, run_at=run_at, bad=bad)
    return run_at, bad


_CSS = """<style>
.dqb-strip{display:flex;flex-direction:column;gap:3px;margin:0 0 8px;}
.dqb{display:flex;align-items:baseline;gap:8px;font-size:12px;line-height:1.45;
  border:1px solid;border-radius:8px;padding:5px 10px;}
.dqb-warn{color:var(--warn);border-color:var(--warn);background:var(--warn-dim);}
.dqb-crit{color:var(--down);border-color:var(--down);background:rgba(var(--down-rgb),.14);}
.dqb .dqb-k{font-weight:600;white-space:nowrap;}
.dqb .dqb-at{margin-left:auto;font-size:11px;opacity:.75;white-space:nowrap;}
</style>"""


def _strip_html(active: str) -> str:
    """The strip for one page, or '' when nothing relevant fires."""
    scope = _PAGES.get(active)
    if scope is None:
        return ""
    run_at, bad = _fetch()
    hits = [b for b in bad if not scope or b[0] in scope]
    if not hits:
        return ""
    hits.sort(key=lambda b: (b[1] != "critical", b[0]))
    lines = []
    for check, sev, msg in hits[:_MAX_LINES]:
        cls = "dqb-crit" if sev == "critical" else "dqb-warn"
        icon = "&#9888;" if sev == "critical" else "&#9650;"
        lines.append(
            f'<div class="dqb {cls}">{icon} <span class="dqb-k">{html.escape(check)}</span> '
            f'{html.escape(msg)} <span class="dqb-at">data-quality {html.escape(str(run_at or "")[:16])}</span></div>')
    if len(hits) > _MAX_LINES:
        lines.append(f'<div class="dqb dqb-warn">+{len(hits) - _MAX_LINES} more — see /dash/coverage</div>')
    return f'<div class="{_SENTINEL}">' + "".join(lines) + "</div>" + _CSS


def _enhance(body: str, active: str) -> str:
    if _SENTINEL in body:
        return body
    strip = _strip_html(active)
    return (strip + body) if strip else body


def install() -> bool:
    """Wrap dashboard._shell so affected pages get the kill-switch strip. Idempotent;
    signature-transparent (inspects args, passes them through verbatim)."""
    from src.web import dashboard as _dash
    cur = _dash._shell
    if getattr(cur, "_dqb_installed", False):
        return False

    def _shell_dqb(*a, **k):
        try:
            act = k["active"] if "active" in k else (a[2] if len(a) > 2 else "")
            if act in _PAGES:
                if "body" in k and isinstance(k["body"], str):
                    k = dict(k)
                    k["body"] = _enhance(k["body"], act)
                elif len(a) > 1 and isinstance(a[1], str):
                    a = a[:1] + (_enhance(a[1], act),) + a[2:]
        except Exception:
            pass                                   # additive: never break a page
        return cur(*a, **k)

    _shell_dqb._dqb_installed = True
    _dash._shell = _shell_dqb
    return True


def _selftest() -> int:
    # synthetic battery states, no DB: patch the cache directly
    _cache.update(at=time.time(), ttl=3600, run_at="2026-07-02 06:30:01", bad=[
        ("killswitch.regime", "warn", "Nifty 50 24100 < 200DMA 24500 — momentum regime OFF"),
        ("killswitch.market_freshness", "critical", "bhavcopy stale: last trade_date 2026-06-25 (7d ago)"),
        ("killswitch.restatement_spike", "warn", "3/25 gate-passed symbols (12.0%) revised in 30d"),
    ])
    out = _enhance("<h2>Rotation</h2>", "rotation")
    assert _SENTINEL in out and "dqb-crit" in out, "crit strip missing"
    assert "momentum regime OFF" in out and "bhavcopy stale" in out, "messages must be quoted"
    assert "restatement" not in out, "fundamentals check must not leak onto a momentum page"
    assert out.index("dqb-crit") < out.index("dqb-warn"), "critical must sort first"
    assert _enhance(out, "rotation") == out, "must be idempotent"
    s2 = _enhance("<h2>Screen+</h2>", "screen2")
    assert "restatement" in s2 and "regime" not in s2, "fundamentals page gets only its checks"
    cov = _enhance("<h2>Coverage</h2>", "coverage")
    assert all(w in cov for w in ("regime", "bhavcopy", "restatement")), "coverage shows all"
    assert _enhance("<h2>Wire</h2>", "wire") == "<h2>Wire</h2>", "unmapped page untouched"
    _cache.update(bad=[])
    assert _enhance("<h2>Rotation</h2>", "rotation") == "<h2>Rotation</h2>", "all-ok = no strip"
    print("dq_banner selftest OK — scoped strips, crit-first, idempotent, all-ok silent")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
