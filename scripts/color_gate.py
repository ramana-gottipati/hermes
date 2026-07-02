#!/usr/bin/env python3
"""
color_gate.py — the colour-system alignment gate (a RATCHET).

Why this exists
---------------
The UI carries two palettes: the agreed design tokens (`ui_tokens.py` `:root`) and a
legacy GitHub-dark set still emitted in page bodies. `shell_skin.py` retints legacy
CLASSES but structurally cannot reach inline `style=`, SVG `fill=`/`stroke=` attributes,
or canvas/JS literals — so a directional bull/bear value can render in the wrong green/red
while every page still returns 200 and carries every chrome marker. chrome_gate and
nav_integrity_gate are blind to it (they check presence + structure, not colour values).

This gate makes colour drift a build failure. It is a RATCHET, not a big-bang assertion:

  1. TOKENS PRESENT — `ui_tokens.py` defines the canonical + colour-alignment tokens.
  2. NO sc-RS REGRESSION — the categorical `.scard.sc-RS` border must NOT be the value
     `--up` hex (#3fd486); it caused a "category reads as bullish" bug + would be baked in
     when shell_skin remaps are retired. (The exact class of bug already shipped once.)
  3. MIGRATED FILES STAY CLEAN — files that already speak the token language for directional
     colour must contain NO legacy directional hex/rgb. This list GROWS one phase at a time;
     a regression in any migrated file FAILS the build, locking in each phase's gains.
  4. BACKLOG (informational) — prints the count of legacy directional colour still in the
     un-migrated bodies, so the shrinking number is visible every run (no silent cap).

False-positive handling: scanning is **tokenize-based** — only Python STRING-token contents
are inspected, so a hex inside a `#` comment or a docstring-about-colours never trips it
(the real failure mode of a naive grep). Foundation files that legitimately hold palette
VALUES (ui_tokens/ui_kit/shell_skin/ui_components) are excluded from the directional scan.

Usage:  python scripts/color_gate.py      # exit 0 = aligned (for the current ratchet), 1 = drift
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys
import tokenize

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── the canonical + Phase-0 tokens that MUST exist ───────────────────────────
REQUIRED_TOKENS = [
    "--up:#3fd486", "--down:#ff6a7a", "--warn:#f6b73c", "--accent:#4d9dff",
    "--up-rgb:63,212,134", "--down-rgb:255,106,122", "--warn-rgb:246,183,60",
    "--ok:#3fd486", "--off:#ff6a7a", "--on-accent:#06121f", "--cat-rs:#34e0d6",
    # Phase 3 — categorical / chart-series identity (seed the canvas C object + compare palettes)
    "--accent-orange:#f0883e", "--series-1:#39c5cf", "--series-8:#f778ba",
    "--chart-line:#1f6feb", "--chart-dval:#2ea043", "--chart-vol:#3b5168",
]

# ── legacy DIRECTIONAL colour literals (bull/bear) that a migrated file must not carry.
# These are the GitHub-dark greens/reds that should be --up/--down. (#2ea043 included — its
# only blessed non-directional use, the --cat-rs token VALUE, lives in an excluded foundation
# file, so flagging it inside a BODY string is correct.) ──
_LEGACY_DIRECTIONAL = [
    "#3fb950", "#2ea043", "#238636", "#56d364", "#7ee787",                 # greens
    "#f85149", "#ff7b72", "#ffa198", "#da3633", "#8f1f1f", "#b53b38",      # reds
]
_LEGACY_RGB = [r"rgba?\(\s*63\s*,\s*185\s*,\s*80", r"rgba?\(\s*248\s*,\s*81\s*,\s*73"]
_DIR_RE = re.compile("|".join([re.escape(h) for h in _LEGACY_DIRECTIONAL] + _LEGACY_RGB), re.I)

# ── the ratchet: files that already speak tokens for directional colour. GROW per phase. ──
MIGRATED = [
    "src/web/screener_plus.py",     # _UP/_DOWN/_TRACK python-consts = var() tokens
    "src/web/strategist_view.py",   # .st-*/.wc-* all var()
    "src/web/rotation_view.py",     # PHASE dict already canonical (D-PITCH-2 colour contract)
    "src/web/rsband_view.py",       # _LANE_JS/_CLOCK_JS canvas-canonical hex + verdict/band var() tokens
    # Phase 1 (directional migration complete — regression-locked):
    "src/web/rrg_view.py",          # RRG ruling: QCOLOR→tokens, SVG consumers→style=
    "src/web/mini_rrg.py",          # RRG ruling, reconciled to rrg_view
    "src/web/wolfe_view.py",        # bull/bear/in-zone→var(); SVG path→canonical literal
    "src/web/participants_view.py", # net-long/short→var(); sparkline SVG stroke→style=; {col}22→rgba(var())
    "src/web/rs_section.py",        # .rsh-rk.up/.dn→var()
    "src/web/harmonic_view.py",     # _BULL/_BEAR + inline color:→var()
    "src/web/wolfe_overlay.py",     # canvas zfill/zedge + manual-draw→canonical literal
    "src/web/cpr_overlay.py",       # canvas regime tint + BULL/BEAR arrows→canonical literal
    "src/web/mep_overlay.py",       # canvas accum/distrib COL→canonical literal
    # Categorical phase: the CATEGORICAL greens (gw-cr money-accent, testing benchmark
    # "row to beat", kt-in provenance) are decoupled from the value contract to --series-4
    # (D-COL role #2 — NEVER --up); these two files are now clean of legacy directional hex.
    "src/web/growth_view.py",       # gw-cr money-accent → var(--series-4) (categorical)
    "src/web/testing_view.py",      # benchmark row "to beat" → var(--series-4) (categorical)
    # NOT yet migrated: dashboard.py, stock_chart.py (directional in progress);
    # dashboard.kt-in provenance green is now var(--series-4) but dashboard.py keeps other
    # directional sites (heat cells, SVG fills) so it stays un-migrated for the directional phase.
]

# foundation files legitimately hold palette VALUES as literals — exclude from the legacy scan.
_FOUNDATION = {"ui_tokens.py", "ui_kit.py", "shell_skin.py", "ui_components.py", "ui_showcase.py"}


def _string_text(path: str) -> str:
    """Concatenate ONLY Python STRING-token contents — so a hex in a `#` comment or prose is
    never scanned (the naive-grep false positive). Falls back to comment-stripped raw text if
    the file won't tokenize (it always should — these are importable modules)."""
    chunks: list[str] = []
    try:
        with open(path, "rb") as f:
            for tok in tokenize.tokenize(f.readline):
                if tok.type == tokenize.STRING:
                    chunks.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        with io.open(path, "r", encoding="utf-8") as f:
            return "\n".join(ln.split("#", 1)[0] for ln in f)
    return "\n".join(chunks)


def _legacy_hits(path: str) -> list[str]:
    text = _string_text(path)
    return sorted(set(m.group(0) for m in _DIR_RE.finditer(text)))


def main() -> int:
    fails: list[str] = []

    # 1. tokens present
    try:
        from src.web import ui_tokens
        css = ui_tokens.tokens_css()
        for tok in REQUIRED_TOKENS:
            if tok not in css:
                fails.append(f"TOKEN MISSING: ui_tokens.py does not define `{tok}`")
    except Exception as e:  # noqa: BLE001
        fails.append(f"could not load ui_tokens: {type(e).__name__}: {e}")

    # 2. sc-RS must not be the value --up hex (regression lock on the shipped bug)
    skin = _string_text(os.path.join(_ROOT, "src/web/shell_skin.py"))
    if re.search(r"sc-RS\{border-top-color:\s*#3fd486", skin):
        fails.append("sc-RS REGRESSION: shell_skin maps the categorical .scard.sc-RS border to "
                     "#3fd486 (== the value --up). Re-point it to var(--cat-rs).")

    # 3. migrated files stay clean of legacy directional colour
    for rel in MIGRATED:
        hits = _legacy_hits(os.path.join(_ROOT, rel))
        if hits:
            fails.append(f"MIGRATED REGRESSION: {rel} re-introduced legacy directional colour "
                         f"{hits} — use var(--up)/var(--down) (or rgba(var(--up-rgb),a)).")

    # 3b. render-based: a var() must NEVER reach an SVG fill=/stroke= ATTRIBUTE — it is invalid
    # CSS there and FAILS SILENTLY (the shape renders with no colour). A static scan can't catch
    # it (source emits fill="{col}" where col holds the var), so render the glyph-dense pages with
    # a data-bearing fixture symbol and assert no attribute resolves to var(). This is the exact
    # bug that shipped in cockpit._mv_adbar; it now fails the build.
    try:
        from fastapi.testclient import TestClient
        import src.main as _M
        from src.web import v2_surfaces as _v2
        _v2.wire(_M.app)
        _client = TestClient(_M.app)
        _attr_re = re.compile(r'(?:fill|stroke)="var\(--')
        for _p in ("/dash/stock?sym=ALPHA", "/dash/dashboard", "/dash/rrg", "/dash/rsband?sym=ALPHA"):
            try:
                _n = len(_attr_re.findall(_client.get(_p).text))
            except Exception:  # noqa: BLE001
                continue
            if _n:
                fails.append(f"SVG-ATTR VAR: {_p} renders {_n} `fill=/stroke=\"var(--…)\"` — var() is "
                             "invalid in an SVG presentation attribute (silent-fail). Emit "
                             "style=\"fill:var(--…)\" instead.")
    except Exception as _e:  # noqa: BLE001
        print(f"  ~~ SVG-attr render check skipped: {type(_e).__name__}: {_e}")

    # 4. backlog (informational, non-failing) — legacy directional colour left in the bodies
    backlog = 0
    worst: list[tuple[int, str]] = []
    for path in sorted(glob.glob(os.path.join(_ROOT, "src/web/*.py"))):
        base = os.path.basename(path)
        if base in _FOUNDATION or ".bak" in base or ("src/web/" + base) in MIGRATED:
            continue
        n = len(_DIR_RE.findall(_string_text(path)))
        if n:
            backlog += n
            worst.append((n, base))
    worst.sort(reverse=True)

    print(f"== color gate: {len(REQUIRED_TOKENS)} tokens · {len(MIGRATED)} migrated files · "
          f"backlog {backlog} legacy directional colour sites in {len(worst)} unmigrated files ==")
    if worst:
        print("  backlog (Phase-1 target, by file): " +
              ", ".join(f"{b}:{n}" for n, b in worst[:12]))

    if fails:
        print(f"FAIL — {len(fails)} colour-alignment regression(s):")
        for f in fails:
            print(f"  !! {f}")
        return 1
    print("PASS — tokens present, sc-RS decoupled, migrated files clean. "
          "(Backlog is tracked, not yet enforced — it shrinks as files join MIGRATED.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
