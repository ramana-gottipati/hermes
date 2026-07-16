"""ui_components.py — the native v2 component library (Lane A2).

The full institutional-grade component set built on `ui_tokens` (the shared foundation):
buttons, form fields, tabs, tooltips, skeletons, spinners, empty/error states, inline
notes, kbd, progress, tags, and a switch (the density toggle). Each is a `.uk-*` class
plus a small Python render helper, so a v2 page (or the showcase) composes them the way
`ui_kit` already composes `card`/`pill`/`stat`.

`components_css()` returns ONE `<style>` block (include once per page, after
`ui_tokens.tokens_css()`). The render helpers return HTML strings.

Isolation: imports only `ui_tokens` (for the marker convention). Additive; nothing here is
wired into a live page until a caller (the showcase, then progressively ui_kit/shell_skin)
opts in — so it cannot regress an existing surface.
"""
from __future__ import annotations

import html as _html

COMPONENTS_MARKER = "/* uk-components v1 */"


def esc(s) -> str:
    return _html.escape(str(s if s is not None else ""))


_COMPONENTS_CSS = """<style>""" + COMPONENTS_MARKER + """
/* ── button ── */
.uk-btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;font:var(--fw-semi) var(--fs-sm)/1 var(--font);
  cursor:pointer;border:1px solid var(--line-2);background:var(--bg-2);color:var(--ink-2);
  border-radius:var(--r-sm);padding:9px 14px;transition:var(--t);white-space:nowrap;text-decoration:none}
.uk-btn:hover{border-color:var(--line-3);color:var(--ink);background:var(--bg-3)}
.uk-btn:active{transform:translateY(.5px)}
.uk-btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.uk-btn.primary:hover{background:var(--accent-2);border-color:var(--accent-2)}
.uk-btn.ghost{background:transparent;border-color:transparent;color:var(--ink-2)}
.uk-btn.ghost:hover{background:var(--bg-2);color:var(--ink)}
.uk-btn.danger{color:var(--down);border-color:rgba(255,106,122,.4)}
.uk-btn.danger:hover{background:var(--down-dim);color:var(--down)}
.uk-btn.sm{padding:6px 10px;font-size:var(--fs-xs)}
.uk-btn.lg{padding:11px 18px;font-size:var(--fs-md)}
.uk-btn[disabled],.uk-btn.disabled{opacity:.45;pointer-events:none}
.uk-btn .ic{font-size:1.1em;line-height:1}

/* ── form field ── */
.uk-field{display:flex;flex-direction:column;gap:6px}
.uk-field>label,.uk-label{font:var(--fw-med) var(--fs-xs)/1 var(--font);color:var(--ink-3);
  text-transform:uppercase;letter-spacing:.5px}
.uk-input,.uk-select,.uk-textarea{font:var(--fs-md)/1.3 var(--font);color:var(--ink);background:var(--bg-1);
  border:1px solid var(--line-2);border-radius:var(--r-sm);padding:9px 11px;transition:var(--t);width:100%}
.uk-input:hover,.uk-select:hover,.uk-textarea:hover{border-color:var(--line-3)}
.uk-input:focus,.uk-select:focus,.uk-textarea:focus{outline:none;border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-dim)}
.uk-input::placeholder,.uk-textarea::placeholder{color:var(--ink-4)}
.uk-select{appearance:none;cursor:pointer;
  background-image:linear-gradient(45deg,transparent 50%,var(--ink-3) 50%),linear-gradient(135deg,var(--ink-3) 50%,transparent 50%);
  background-position:calc(100% - 16px) 17px,calc(100% - 11px) 17px;background-size:5px 5px,5px 5px;background-repeat:no-repeat;padding-right:30px}

/* ── tabs (canonical underline tabs) ── */
.uk-tabs{display:flex;gap:2px;flex-wrap:wrap;border-bottom:1px solid var(--line)}
.uk-tab{font:var(--fw-semi) var(--fs-sm)/1 var(--font);cursor:pointer;background:none;border:0;color:var(--ink-3);
  padding:10px 15px;border-bottom:2px solid transparent;margin-bottom:-1px;transition:var(--t)}
.uk-tab:hover{color:var(--ink-2)}
.uk-tab.on{color:var(--ink);border-bottom-color:var(--accent)}
.uk-pane{display:none}.uk-pane.on{display:block}

/* ── tooltip (CSS-only, [data-tip]) ── */
.uk-tip{position:relative}
.uk-tip::after{content:attr(data-tip);position:absolute;left:50%;bottom:calc(100% + 7px);transform:translateX(-50%) translateY(3px);
  background:var(--bg-4);color:var(--ink);font:var(--fw-med) var(--fs-xs)/1.35 var(--font);white-space:nowrap;
  padding:6px 9px;border-radius:var(--r-xs);border:1px solid var(--line-2);box-shadow:var(--e-2);
  opacity:0;pointer-events:none;transition:var(--t);z-index:var(--z-toast)}
.uk-tip:hover::after,.uk-tip:focus-visible::after{opacity:1;transform:translateX(-50%) translateY(0)}

/* ── skeleton + spinner (loading) ── */
.uk-skel{background:linear-gradient(100deg,var(--bg-2) 30%,var(--bg-3) 50%,var(--bg-2) 70%);
  background-size:200% 100%;animation:uk-shim 1.3s linear infinite;border-radius:var(--r-sm);height:14px}
@keyframes uk-shim{to{background-position:-200% 0}}
.uk-spin{width:18px;height:18px;border-radius:50%;border:2px solid var(--line-2);border-top-color:var(--accent);
  display:inline-block;animation:uk-rot .7s linear infinite;vertical-align:middle}
@keyframes uk-rot{to{transform:rotate(360deg)}}

/* ── empty / error states ── */
.uk-empty,.uk-error{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;
  text-align:center;padding:46px 20px;color:var(--ink-3)}
.uk-empty .ic,.uk-error .ic{font-size:30px;opacity:.7;line-height:1}
.uk-empty .ti,.uk-error .ti{font:var(--fw-semi) var(--fs-lg) var(--font);color:var(--ink-2)}
.uk-empty .hint,.uk-error .hint{font-size:var(--fs-sm);max-width:380px;line-height:1.5}
.uk-error .ti{color:var(--down)}

/* ── inline note / toast (info · warn · down · up) ── */
.uk-note{display:flex;gap:9px;align-items:flex-start;border:1px solid var(--line-2);background:var(--bg-2);
  border-radius:var(--r-sm);padding:11px 13px;font-size:var(--fs-sm);color:var(--ink-2);line-height:1.5}
.uk-note .d{width:7px;height:7px;border-radius:50%;background:var(--accent);margin-top:5px;flex:none;box-shadow:0 0 7px var(--accent)}
.uk-note.warn{border-color:rgba(246,183,60,.4)} .uk-note.warn .d{background:var(--warn);box-shadow:0 0 7px var(--warn)}
.uk-note.down{border-color:rgba(255,106,122,.4)} .uk-note.down .d{background:var(--down);box-shadow:0 0 7px var(--down)}
.uk-note.up{border-color:rgba(63,212,134,.4)} .uk-note.up .d{background:var(--up);box-shadow:0 0 7px var(--up)}

/* ── kbd · divider · progress · tag ── */
.uk-kbd{font:var(--fs-xs) var(--mono);background:var(--bg-3);border:1px solid var(--line-2);
  border-radius:var(--r-xs);padding:1px 6px;color:var(--ink-2)}
.uk-div{height:1px;background:var(--line);border:0;margin:var(--sp-4) 0}
.uk-div-v{width:1px;align-self:stretch;background:var(--line)}
.uk-prog{height:7px;background:var(--bg-1);border:1px solid var(--line);border-radius:var(--r-pill);overflow:hidden}
.uk-prog>span{display:block;height:100%;background:var(--accent);border-radius:var(--r-pill);transition:width var(--t)}
.uk-tag{display:inline-flex;align-items:center;gap:5px;font:var(--fw-med) var(--fs-xs) var(--font);
  background:var(--bg-3);color:var(--ink-2);border:1px solid var(--line-2);border-radius:var(--r-xs);padding:2px 8px}

/* ── switch (the density toggle, and any boolean) ── */
.uk-switch{display:inline-flex;align-items:center;gap:8px;cursor:pointer;font-size:var(--fs-sm);color:var(--ink-2);user-select:none}
.uk-switch .tk{width:34px;height:19px;border-radius:var(--r-pill);background:var(--bg-3);border:1px solid var(--line-2);
  position:relative;transition:var(--t);flex:none}
.uk-switch .tk::after{content:"";position:absolute;top:2px;left:2px;width:13px;height:13px;border-radius:50%;
  background:var(--ink-2);transition:var(--t)}
.uk-switch.on .tk{background:var(--accent-dim);border-color:var(--accent)}
.uk-switch.on .tk::after{transform:translateX(15px);background:var(--accent)}

/* ── responsive grid helpers ── */
.uk-cols{display:grid;gap:var(--sp-3);grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.uk-cols-2{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
</style>"""


def components_css() -> str:
    """The component-library `<style>` block. Include once per page, after tokens_css()."""
    return _COMPONENTS_CSS


# ── render helpers ────────────────────────────────────────────────────────────
def btn(label: str, *, href: str = "", variant: str = "", size: str = "",
        icon: str = "", attrs: str = "") -> str:
    cls = " ".join(c for c in ("uk-btn", variant, size) if c)
    ic = f'<span class="ic">{icon}</span>' if icon else ""
    if href:
        return f'<a class="{cls}" href="{esc(href)}" {attrs}>{ic}{esc(label)}</a>'
    return f'<button class="{cls}" type="button" {attrs}>{ic}{esc(label)}</button>'


def field(label: str, control: str) -> str:
    return f'<div class="uk-field"><label>{esc(label)}</label>{control}</div>'


def note(text: str, kind: str = "") -> str:
    return f'<div class="uk-note {esc(kind)}"><span class="d"></span><div>{text}</div></div>'


def empty(title: str, hint: str = "", icon: str = "○") -> str:
    h = f'<div class="hint">{esc(hint)}</div>' if hint else ""
    return f'<div class="uk-empty"><div class="ic">{icon}</div><div class="ti">{esc(title)}</div>{h}</div>'


def error_state(title: str, hint: str = "", icon: str = "△") -> str:
    h = f'<div class="hint">{esc(hint)}</div>' if hint else ""
    return f'<div class="uk-error"><div class="ic">{icon}</div><div class="ti">{esc(title)}</div>{h}</div>'


def skeleton(rows: int = 3) -> str:
    bars = "".join(
        f'<div class="uk-skel" style="width:{w}%;margin-bottom:9px"></div>'
        for w in ([92, 78, 85, 64, 80][:max(1, rows)]))
    return f'<div>{bars}</div>'


def spinner(label: str = "") -> str:
    lab = f'<span style="margin-left:9px;color:var(--ink-3);font-size:var(--fs-sm)">{esc(label)}</span>' if label else ""
    return f'<span class="uk-spin" role="status" aria-label="loading"></span>{lab}'


def progress(pct: float) -> str:
    p = max(0, min(100, pct))
    return f'<div class="uk-prog"><span style="width:{p}%"></span></div>'


def tag(text: str) -> str:
    return f'<span class="uk-tag">{esc(text)}</span>'


def tabs(items: list[tuple[str, str]], *, active: int = 0) -> tuple[str, str]:
    """items=[(tab_id, label),...] -> (tabbar_html, '') ; panes are authored by the caller
    as <div class="uk-pane[ on]" id="ukpane-<tab_id>">. Returns the bar + a small JS once."""
    bar = '<div class="uk-tabs" role="tablist">' + "".join(
        f'<button class="uk-tab{" on" if i == active else ""}" role="tab" data-pane="{esc(tid)}" '
        f'type="button">{esc(lbl)}</button>' for i, (tid, lbl) in enumerate(items)) + '</div>'
    return bar, _TABS_JS


_TABS_JS = ("<script>(function(){if(window.__uktabs)return;window.__uktabs=1;"
            "document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('.uk-tab');"
            "if(!b)return;var id=b.dataset.pane,box=b.closest('.uk-tabwrap')||document;"
            "box.querySelectorAll('.uk-tab').forEach(function(x){x.classList.toggle('on',x.dataset.pane===id);});"
            "box.querySelectorAll('.uk-pane').forEach(function(x){x.classList.toggle('on',x.id==='ukpane-'+id);});});"
            "})();</script>")


def _selftest() -> int:
    css = components_css()
    assert COMPONENTS_MARKER in css
    for cls in (".uk-btn", ".uk-input", ".uk-tabs", ".uk-tip", ".uk-skel", ".uk-spin",
                ".uk-empty", ".uk-note", ".uk-switch", ".uk-prog"):
        assert cls in css, f"missing component {cls}"
    assert "uk-btn primary" in btn("Go", variant="primary")
    assert "href=" in btn("Go", href="/x") and "<button" in btn("Go")
    assert "uk-note warn" in note("careful", "warn")
    assert "uk-empty" in empty("Nothing here", "try a filter")
    bar, js = tabs([("a", "A"), ("b", "B")], active=0)
    assert 'data-pane="a"' in bar and "uktabs" in js
    assert "width:42%" in progress(42)
    print("ui_components selftest OK — components + render helpers")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
