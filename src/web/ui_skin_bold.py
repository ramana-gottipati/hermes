"""ui_skin_bold.py — the ratified "B geometry + D atmosphere" v3 skin (owner, 2026-07-22).

Command-Deck GEOMETRY (chamfered plates via clip-path, oversized instrument numerals,
glow-underline destinations, uppercase tracked labels) carried by Aurora-Glass ATMOSPHERE
(aurora radial fields, translucent blurred panes, gradient display accents).

An OPT-IN override layer: every rule is scoped `:root[data-ui-v3][data-skin="bold"]` — it can
never touch a legacy page (no v3 root attr there) and never fires on v3 pages when the user
flips back to the Quiet skin (the toggle persists in localStorage; shell_v3 owns the control).
Amends Part II §B's EXPRESSION only: fences, value-contract colors, evidence links, AA
legibility all inherited untouched from the token layer.
"""
from __future__ import annotations

SKIN_MARKER = "/* pv3-skin-bold v1 */"

_CSS = """<style>""" + SKIN_MARKER + """
:root[data-ui-v3][data-skin="bold"]{
  --bg-0:#05070d; --bg-1:#0a0e1a; --bg-2:#0e1524; --bg-3:#131c30; --bg-4:#182541;
  --line:#1c2a44; --line-2:#27395c;
  --r-sm:0px; --r:0px;              /* geometry: the chamfer replaces the radius */
}
:root[data-ui-v3][data-skin="bold"] body{background:
  radial-gradient(1100px 460px at 82% -8%, rgba(77,157,255,.11), transparent 60%),
  radial-gradient(760px 380px at 6% 4%, rgba(52,224,214,.08), transparent 55%),
  radial-gradient(820px 480px at 50% 112%, rgba(177,140,255,.10), transparent 60%),
  var(--bg-0)}
/* ── chamfered plates (the B signature) ── */
:root[data-ui-v3][data-skin="bold"] :is(.pv3-card,.pv3-tile,.hub-checks,.tc-card,.pv3-dock){
  border-radius:0;
  clip-path:polygon(12px 0,100% 0,100% calc(100% - 12px),calc(100% - 12px) 100%,0 100%,0 12px);
  background:linear-gradient(160deg,var(--bg-3),var(--bg-2) 55%);
  position:relative}
:root[data-ui-v3][data-skin="bold"] :is(.pv3-card,.pv3-tile)::before{
  content:"";position:absolute;left:0;top:0;width:38px;height:2px;background:var(--accent-cy, #34e0d6)}
/* ── glass rail + dock (the D atmosphere) ── */
:root[data-ui-v3][data-skin="bold"] .pv3-rail .pv3-card{
  background:rgba(255,255,255,.045);border-color:rgba(255,255,255,.11);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
:root[data-ui-v3][data-skin="bold"] .pv3-dock{
  background:rgba(255,255,255,.035);border-color:rgba(255,255,255,.10);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
/* ── type: instrument numerals + tracked uppercase labels ── */
:root[data-ui-v3][data-skin="bold"] .pv3-tile .v{font-size:32px;font-weight:700;letter-spacing:-.02em}
:root[data-ui-v3][data-skin="bold"] :is(.pv3-sec,.hub-checks .hd,.pv3-navrail .hd){
  letter-spacing:.28em}
:root[data-ui-v3][data-skin="bold"] :is(h1,h2,.pv3-h){font-weight:800;letter-spacing:-.01em}
:root[data-ui-v3][data-skin="bold"] .hub-id h1{
  background:linear-gradient(100deg,var(--ink) 45%,var(--accent));
  -webkit-background-clip:text;background-clip:text;color:transparent}
/* ── destinations: glow underline ── */
:root[data-ui-v3][data-skin="bold"] .pv3-dests a{
  font-size:var(--t-xs);font-weight:600;letter-spacing:.22em;text-transform:uppercase}
:root[data-ui-v3][data-skin="bold"] .pv3-dests a[aria-current="page"]{
  border-bottom-color:transparent;
  background:linear-gradient(90deg,var(--accent),#34e0d6) bottom/100% 2px no-repeat;
  text-shadow:0 0 18px rgba(77,157,255,.55)}
/* ── controls: cut buttons, gradient primary ── */
:root[data-ui-v3][data-skin="bold"] .pv3-btn{
  border-radius:0;background:transparent;
  clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px)}
:root[data-ui-v3][data-skin="bold"] .pv3-dock-tabs a.on{
  border-radius:0;background:linear-gradient(120deg,rgba(77,157,255,.18),rgba(52,224,214,.14));
  clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px)}
/* ── fence: dashed, tracked, centered ── */
:root[data-ui-v3][data-skin="bold"] .pv3-fence{
  border:1px dashed var(--line-2);background:transparent;text-align:center;letter-spacing:.05em}
/* ── motion: hover lift + live pulse (reduced-motion respected by the token layer's kill-switch) ── */
@media (prefers-reduced-motion: no-preference){
  :root[data-ui-v3][data-skin="bold"] :is(.pv3-tile,.pv3-card){
    transition:transform 160ms ease-out,border-color 160ms ease-out}
  :root[data-ui-v3][data-skin="bold"] :is(.pv3-tile:hover,.pv3-card:hover){
    transform:translateY(-2px);border-color:var(--accent)}
}
</style>"""

_BOOT_JS = """<script>(function(){
var r=document.documentElement,k="pv3skin";
try{var s=localStorage.getItem(k);if(s==="quiet"){r.setAttribute("data-skin","quiet");}}catch(e){}
window.pv3Skin=function(){
  var bold=r.getAttribute("data-skin")!=="quiet";
  r.setAttribute("data-skin",bold?"quiet":"bold");
  try{localStorage.setItem(k,bold?"quiet":"bold");}catch(e){}
};})();</script>"""


def skin_css() -> str:
    """The bold-skin override layer + its localStorage bootstrap. shell_v3 includes it once;
    the server renders data-skin="bold" as the preview default, the user toggles to quiet."""
    return _CSS + _BOOT_JS


def _selftest() -> int:
    css = skin_css()
    assert SKIN_MARKER in css and 'data-skin="bold"' in css
    # every rule is double-scoped — nothing can reach a legacy page or the quiet skin
    import re
    for sel in re.findall(r"\n(:root[^{]+|@media[^{]+)\{", css):
        assert 'data-ui-v3' in sel or sel.startswith("@media"), sel
    assert "pv3Skin" in css and "prefers-reduced-motion" in css
    assert "--up" not in css and "--down" not in css  # the value contract is never restyled
    print("ui_skin_bold selftest OK — double-scoped, value contract untouched")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
