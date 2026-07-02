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

# _shell's `active` arg is a NAV key, not a lens key, and pages are inconsistent — the
# momentum/rotation/flow surfaces all pass the workspace "markets" (verified: rotation/
# rrg/rsband/cycle-clock/capture-map/participants), while the strategy-detail pages pass
# their own key ("stocks"/"mep"/"conviction"), and the screener passes "screen2"/
# "screener" (NOT in dashboard._WS). So we can't key on a lens name — we normalize the
# `active` value to a logical kill-switch WORKSPACE with our OWN complete map (a superset
# of dashboard._WS; importing that private/partial map would silently drop "screen2").
_ACT_WS = {
    # markets — price / momentum / RS / rotation / flow surfaces (all pass "markets" or
    # a key that resolves here). coverage_view also passes "markets".
    "markets": "markets", "sectors": "markets", "rs": "markets", "ratio": "markets",
    "leaders": "markets", "laggards": "markets", "compare": "markets",
    "rotation": "markets", "rrg": "markets", "rsband": "markets", "cycle-clock": "markets",
    "capture": "markets", "capture-map": "markets", "participants": "markets",
    "momentum-scan": "markets",
    # strategies — stock-selection surfaces (momentum ranks + fundamentals blended)
    "strategies": "strategies", "stocks": "strategies", "scan": "strategies",
    "stock": "strategies", "conviction": "strategies", "mep": "strategies",
    "cpr": "strategies", "concalls": "strategies", "growth": "strategies",
    "workbench": "strategies", "launchpad": "strategies", "strategist": "strategies",
    # screener — fundamentals-driven columns
    "screener": "screener", "screen2": "screener",
}

# workspace -> the checks whose WARN/CRIT should surface on it. Momentum kill-switches
# (regime OFF / stale bhavcopy / universe drift) gate every price surface; fundamentals
# checks (restatement spike / impossible dates) gate the fundamentals surfaces; feed
# liveness is a pipeline-health signal worth showing on any data surface (the corporates-
# pit endpoint died silently for 4 months precisely because nothing surfaced it).
_WS_CHECKS = {
    "markets": _MOM + _FLOW,
    "strategies": _MOM + _FUND + _FLOW,
    "screener": _FUND,
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
.dqb-warn{color:var(--warn,#f6b73c);border-color:var(--warn,#f6b73c);
  background:var(--warn-dim,rgba(246,183,60,.14));}
.dqb-crit{color:var(--down,#ff6a7a);border-color:var(--down,#ff6a7a);
  background:rgba(var(--down-rgb,255,106,122),.14);}
.dqb .dqb-k{font-weight:600;white-space:nowrap;}
.dqb .dqb-at{margin-left:auto;font-size:11px;opacity:.75;white-space:nowrap;}
</style>"""


def _strip_html(active: str) -> str:
    """The strip for one page, or '' when nothing relevant fires."""
    ws = _ACT_WS.get(active)
    if ws is None:
        return ""
    scope = _WS_CHECKS.get(ws)
    if not scope:
        return ""
    run_at, bad = _fetch()
    hits = [b for b in bad if b[0] in scope]
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
    signature-transparent (inspects args, passes them through verbatim).

    Like shell_skin, this must ALSO rebind the modules that captured `_shell` by
    reference at import time (`from src.web.dashboard import _shell` in rotation_view /
    rrg_view / rsband_view / cycle_clock / participants_view / screener_plus …). Those
    resolve the bare name against their OWN globals, so patching dashboard._shell alone
    never reaches them — verified live: /dash/markets/rotation rendered 0 strips while
    /dash/stocks (dashboard-native) rendered 2. table_controls/shell_skin run before us
    and only shell_skin sweeps, so those refs point at the skin wrapper, not the
    original — hence we rebind by "is a captured shell ref in src.web", not "is orig"."""
    import sys

    from src.web import dashboard as _dash
    cur = _dash._shell
    if getattr(cur, "_dqb_installed", False):
        return False

    def _shell_dqb(*a, **k):
        try:
            act = k["active"] if "active" in k else (a[2] if len(a) > 2 else "")
            if act in _ACT_WS:
                if "body" in k and isinstance(k["body"], str):
                    k = dict(k)
                    k["body"] = _enhance(k["body"], act)
                elif len(a) > 1 and isinstance(a[1], str):
                    a = a[:1] + (_enhance(a[1], act),) + a[2:]
        except Exception:
            pass                                   # additive: never break a page
        return cur(*a, **k)

    _shell_dqb._dqb_installed = True
    _shell_dqb.__wrapped__ = cur                    # keep the chain walkable
    _dash._shell = _shell_dqb

    # Rebind import-time captures. A module-level `_shell` in the src.web.* namespace is
    # always a captured reference to some layer of the shell chain (dashboard is the only
    # definer, and we skip it), so repointing every such ref to our outermost wrapper is
    # safe: after install nothing legitimately points higher, and the next sweep finds
    # _shell_dqb and skips (idempotent). main.py imports every router before wire() runs.
    rebound = 0
    for _name, _mod in list(sys.modules.items()):
        if _mod is None or _mod is _dash or not (_name or "").startswith("src.web."):
            continue
        try:
            ref = getattr(_mod, "_shell", None)
            if callable(ref) and ref is not _shell_dqb and not getattr(ref, "_dqb_installed", False):
                _mod._shell = _shell_dqb
                rebound += 1
        except Exception:  # noqa: BLE001 — a quirky module must never break install
            continue
    return True


def _selftest() -> int:
    # synthetic battery states, no DB: patch the cache directly
    _cache.update(at=time.time(), ttl=3600, run_at="2026-07-02 06:30:01", bad=[
        ("killswitch.regime", "warn", "Nifty 50 24100 < 200DMA 24500 — momentum regime OFF"),
        ("killswitch.market_freshness", "critical", "bhavcopy stale: last trade_date 2026-06-25 (7d ago)"),
        ("killswitch.restatement_spike", "warn", "3/25 gate-passed symbols (12.0%) revised in 30d"),
    ])
    # a markets page passes active="markets" (rotation/rrg/rsband/cycle-clock/participants
    # all do) → momentum checks only, NOT the fundamentals restatement.
    out = _enhance("<h2>Rotation</h2>", "markets")
    assert _SENTINEL in out and "dqb-crit" in out, "crit strip missing on markets"
    assert "momentum regime OFF" in out and "bhavcopy stale" in out, "messages must be quoted"
    assert "restatement" not in out, "fundamentals check must not leak onto a markets page"
    assert out.index("dqb-crit") < out.index("dqb-warn"), "critical must sort first"
    assert _enhance(out, "markets") == out, "must be idempotent"
    # screener page (active="screen2", not in dashboard._WS) → fundamentals checks only.
    s2 = _enhance("<h2>Screen+</h2>", "screen2")
    assert "restatement" in s2 and "regime" not in s2, "screener gets only its checks"
    # strategies-detail (active="stocks"/"mep"/…) blends both momentum + fundamentals.
    strat = _enhance("<h2>Positioning</h2>", "stocks")
    assert "regime" in strat and "restatement" in strat, "strategies blends momentum+fundamentals"
    assert _enhance("<h2>Wire</h2>", "wire") == "<h2>Wire</h2>", "unmapped page untouched"

    # the load-bearing regression: prove install() rebinds a module that captured `_shell`
    # by reference at import time (the rotation_view/rrg_view pattern) — the bug that made
    # /dash/markets/rotation render 0 strips while the dashboard-native /dash/stocks worked.
    import sys
    import types

    import src.web.dashboard as _D
    _fake = types.ModuleType("src.web._fake_lens_for_dqb_test")
    _fake._shell = _D._shell            # as `from src.web.dashboard import _shell` would bind
    sys.modules[_fake.__name__] = _fake
    try:
        _cache.update(at=time.time(), ttl=3600, run_at="2026-07-02 06:30:01", bad=[
            ("killswitch.regime", "warn", "Nifty 50 24100 < 200DMA 24500 — momentum regime OFF")])
        assert install() is True and install() is False, "install must be idempotent"
        assert _fake._shell is _D._shell, "captured _shell ref was not rebound to the dqb wrapper"
        page = _fake._shell("Rotation · patearn", "<h2>Rotation</h2>", active="markets")
        assert _SENTINEL in page and "momentum regime OFF" in page, \
            "rebound view-module ref does not inject the kill-switch strip"
    finally:
        del sys.modules[_fake.__name__]

    _cache.update(bad=[])
    assert _enhance("<h2>Rotation</h2>", "markets") == "<h2>Rotation</h2>", "all-ok = no strip"
    print("dq_banner selftest OK — workspace-scoped strips, crit-first, idempotent, "
          "all-ok silent, import-time refs rebound")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
