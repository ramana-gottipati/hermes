"""src/web/home/tokens.py — the Graphite identity token layer (spec §3).

FRESH from scratch: none of the legacy/preview palette is reused (no `#4d9dff` UI accent, no legacy
green/red signed hues). Scoped `:root[data-ui-g]` + component prefix `.g-*` so it is isolated from
BOTH `ui_kit`/`.uk`/`:root{}` AND the existing preview's `data-ui-v3`/`.pv3-*` (both directions
gate-tested). Two themes ship day one, AA-verified (tests/test_home_tokens_aa.py imports DARK/LIGHT).

The palette values are Python dicts so the AA gate can compute WCAG contrast on the exact values the
CSS emits — the numbers can never drift from the stylesheet.
"""
from __future__ import annotations

TOKENS_G_MARKER = "/* g-tokens graphite */"

# ── the palette (both themes, AA-verified: scratchpad/aa_check.py + candle_aa.py) ──
DARK = {
    "bg-0": "#080b11", "bg-1": "#0f151c", "bg-2": "#141c25", "bg-3": "#1b2530", "bg-4": "#243040",
    "line": "#223040", "line-2": "#2c3d4f",
    "ink": "#e8eef4", "ink-2": "#9fb0c0", "ink-3": "#6f8394",
    "accent": "#17b0aa", "accent-hi": "#2fe6da", "on-accent": "#04211f",
    "up": "#3ad17f", "down": "#f2617f", "warn": "#f4b740",
    "candle-up": "#4d9dff", "candle-dn": "#8496ad",
    "candle-up-line": "#a9d0ff", "candle-dn-line": "#c6d1e2",
}
LIGHT = {
    "bg-0": "#eef2f5", "bg-1": "#ffffff", "bg-2": "#f7fafb", "bg-3": "#e9eef2", "bg-4": "#dde5ec",
    "line": "#dbe3ea", "line-2": "#c4d0da",
    "ink": "#101a22", "ink-2": "#45586a", "ink-3": "#667a8b",
    "accent": "#096b65", "accent-hi": "#0f857f", "on-accent": "#ffffff",
    "up": "#0e8a57", "down": "#c93a52", "warn": "#96660a",
    # candle-down corrected for AA on the near-white light panel (#93a2b8 2.59:1 -> #6f8096 3.85:1;
    # outline #b6c1cd 1.74 -> #455468 7.4) — keeps the owner's blue-up/grey-down/crisp-outline directive.
    "candle-up": "#1668cc", "candle-dn": "#6f8096",
    "candle-up-line": "#5b93da", "candle-dn-line": "#455468",
}

_STATIC = (
    "--acc-dim:rgba(23,176,170,.14);--glow:rgba(23,176,170,.55);"
    "--font:system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
    "--mono:ui-monospace,'SF Mono','Cascadia Code','Consolas','Liberation Mono',monospace;"
    "--r:14px;--r-sm:10px;--r-pill:999px;"
)
_LIGHT_STATIC = "--acc-dim:rgba(9,107,101,.10);--glow:rgba(9,107,101,.30);"


def _vars(d: dict) -> str:
    return "".join(f"--{k}:{v};" for k, v in d.items())


def tokens_css() -> str:
    """The Graphite <style> block. Include ONCE per home page (shell does this)."""
    return (
        "<style>" + TOKENS_G_MARKER + "\n"
        ":root[data-ui-g]{" + _vars(DARK) + _STATIC + "}\n"
        ":root[data-ui-g][data-theme=\"light\"]{" + _vars(LIGHT) + _LIGHT_STATIC + "}\n"
        ":root[data-ui-g] body{margin:0;background:var(--bg-0);color:var(--ink);"
        "font:400 15px/1.55 var(--font);-webkit-font-smoothing:antialiased;"
        "text-rendering:optimizeLegibility;min-height:100vh}\n"
        ":root[data-ui-g] *{box-sizing:border-box}\n"
        ":root[data-ui-g] a{color:var(--accent);text-decoration:none}\n"
        ":root[data-ui-g] a:hover{text-decoration:underline}\n"
        ":root[data-ui-g] .g-num{font-family:var(--mono);font-variant-numeric:tabular-nums}\n"
        ":root[data-ui-g] :where(a,button,input,select,summary,[tabindex]):focus-visible{"
        "outline:2px solid var(--accent-hi);outline-offset:2px;border-radius:6px}\n"
        "@media(prefers-reduced-motion:reduce){:root[data-ui-g] *,:root[data-ui-g] *::before,"
        ":root[data-ui-g] *::after{animation:none!important;transition:none!important}}\n"
        ":root[data-ui-g] img,:root[data-ui-g] svg{max-width:100%}\n"
        "</style>"
    )


def _selftest() -> int:
    css = tokens_css()
    assert TOKENS_G_MARKER in css and "data-ui-g" in css and 'data-theme="light"' in css
    # isolation: nothing may target bare :root, the legacy scope, or the preview scope
    assert ":root{" not in css and ".uk" not in css and "pv3" not in css and "data-ui-v3" not in css
    # the corrected light candle-down is present verbatim
    assert "--candle-dn:#6f8096" in css and "--candle-dn-line:#455468" in css
    # dark keeps the invariant candle identity
    assert "--candle-up:#4d9dff" in css and "--candle-dn:#8496ad" in css
    assert set(DARK) == set(LIGHT), "themes must define the same token set"
    print("home/tokens selftest OK — Graphite, scoped, two themes, candle-AA fix present")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
