"""Pat — the dashboard tab body (server-rendered, theme-matched to dashboard.py).

``render_pat(flow, explain, q)`` returns the INNER HTML for ``/dash/pat``; the
route in ``dashboard.py`` wraps it in the shared ``_shell``. This module is
self-contained — it imports only the glossary, never dashboard.py (one-way
dependency), and the avatar SVGs use explicit hex (no Tabler / CSS-var deps) so
they render on the dark dashboard chrome.

Phase-1 scope (DB-free): the persona + 6-avatar picker, and the fully working
"Explain a metric" flow driven by the glossary. The three data-backed flows
(accumulation / RS / fundamentals) are present but announce themselves as next —
they need the SQL templates, which land with the engine.
"""

from __future__ import annotations

import json
from urllib.parse import quote_plus

from src.pat.glossary import GLOSSARY, FAMILIES, get, find, family
from src.pat.flows import (
    ACC_STRENGTH, ACC_ENTRY, ACC_WINDOW, ACC_CHARACTER,
    RS_STRENGTH, RS_ALIGN, RS_WINDOW, RS_DIRECTION, RS_LAG_STRENGTH,
    FUND_VAL, FUND_QUAL, FUND_GROW, FUND_BS, FUND_OWN, FUND_SECTOR, NAMED_SCREENS,
    MOVERS_DIR, MOVERS_LIQ, MOVERS_WINDOW,
    INDEX_WINDOW, INDEX_DIRECTION, INDEX_TURNING, PT14_TIER,
    build_accumulation_query, build_accumulation_sectors_query,
    build_rs_query, build_rs_sectors_query, build_fundamentals_query, build_movers_query,
    build_index_query, build_pt14_query, build_disqualified_query,
    build_symbol_resolve_query, build_stock_card_query, build_stock_pattern_query,
    build_credibility_query, build_deterioration_query, build_confluence_query,
    build_confluence_plan_query, PLAN_PILLARS, PLAN_CAPBAND,
    build_credibility_detail_query, build_credibility_trend_query,
    build_credibility_evidence_query,
)


def _esc(s) -> str:
    # Escapes & < > and " so the same helper is safe in both HTML text and
    # double-quoted attributes (P1 hardening from the pre-deploy review).
    return (str(s) if s is not None else "").replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# --- avatars ---------------------------------------------------------------
# Flat, self-contained SVGs (viewBox only; sized by CSS). Indianised market
# archetypes — see the design conversation. data-av slug is the persistence key.

_AV_SETH = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Seth Pat">'
    '<circle cx="50" cy="50" r="48" fill="#E0911E"/>'
    '<rect x="29" y="35" width="42" height="44" rx="13" fill="#fff"/>'
    '<path d="M27 37 Q50 22 73 37 Q50 31 27 37 Z" fill="#fff"/>'
    '<circle cx="41" cy="52" r="7.6" fill="#fff" stroke="#20242B" stroke-width="2.6"/>'
    '<circle cx="59" cy="52" r="7.6" fill="#fff" stroke="#20242B" stroke-width="2.6"/>'
    '<line x1="48.6" y1="52" x2="51.4" y2="52" stroke="#20242B" stroke-width="2.6"/>'
    '<circle cx="41" cy="52" r="2.2" fill="#20242B"/><circle cx="59" cy="52" r="2.2" fill="#20242B"/>'
    '<path d="M33 65 C36 61 41 62 44 65 C47 67 53 67 56 65 C59 62 64 61 67 65 '
    'C63 66 59 65 56 67 C52 69 48 69 44 67 C41 65 37 66 33 65 Z" fill="#20242B"/>'
    '</svg>'
)
_AV_RAO = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Rao Pat">'
    '<circle cx="50" cy="50" r="48" fill="#D85A30"/>'
    '<rect x="29" y="36" width="42" height="43" rx="13" fill="#fff"/>'
    '<path d="M27 39 Q27 23 50 23 Q73 23 73 39 Q61 31 50 32 Q39 31 27 39 Z" fill="#20242B"/>'
    '<path d="M32 48 Q32 59 41 58 Q47 57 46 48 Q39 46 32 48 Z" fill="#20242B"/>'
    '<path d="M68 48 Q68 59 59 58 Q53 57 54 48 Q61 46 68 48 Z" fill="#20242B"/>'
    '<line x1="46" y1="49" x2="54" y2="49" stroke="#20242B" stroke-width="2.4"/>'
    '<circle cx="37" cy="51" r="1.6" fill="#fff"/><circle cx="63" cy="51" r="1.6" fill="#fff"/>'
    '<path d="M37 64 Q50 71 63 64 Q57 67 50 66 Q43 67 37 64 Z" fill="#20242B"/>'
    '</svg>'
)
_AV_SINGH = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Singh Pat">'
    '<circle cx="50" cy="50" r="48" fill="#2F7FD6"/>'
    '<rect x="30" y="38" width="40" height="41" rx="13" fill="#fff"/>'
    '<path d="M31 58 Q31 83 50 85 Q69 83 69 58 Q61 72 50 72 Q39 72 31 58 Z" fill="#20242B"/>'
    '<path d="M26 43 Q24 20 50 19 Q76 20 74 43 Q50 34 26 43 Z" fill="#EE9A22"/>'
    '<path d="M26 43 Q50 34 74 43" fill="none" stroke="#C77A12" stroke-width="1.5"/>'
    '<path d="M46 33 Q50 27 54 33 Q50 31 46 33 Z" fill="#EE9A22" stroke="#C77A12" stroke-width="0.8"/>'
    '<circle cx="42" cy="53" r="2.3" fill="#20242B"/><circle cx="58" cy="53" r="2.3" fill="#20242B"/>'
    '<path d="M40 61 Q50 65 60 61 Q54 63 50 62 Q46 63 40 61 Z" fill="#20242B"/>'
    '</svg>'
)
_AV_CHAI = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Chai Pat">'
    '<circle cx="50" cy="50" r="48" fill="#1AA079"/>'
    '<path d="M23 49 Q23 25 50 25 Q77 25 77 49" fill="none" stroke="#20242B" stroke-width="4.5"/>'
    '<rect x="19" y="46" width="9" height="15" rx="4" fill="#20242B"/>'
    '<rect x="72" y="46" width="9" height="15" rx="4" fill="#20242B"/>'
    '<rect x="30" y="34" width="40" height="43" rx="13" fill="#fff"/>'
    '<rect x="33" y="46" width="13" height="11" rx="3" fill="#fff" stroke="#20242B" stroke-width="2.4"/>'
    '<rect x="54" y="46" width="13" height="11" rx="3" fill="#fff" stroke="#20242B" stroke-width="2.4"/>'
    '<line x1="46" y1="51" x2="54" y2="51" stroke="#20242B" stroke-width="2.4"/>'
    '<circle cx="39.5" cy="51" r="2" fill="#20242B"/><circle cx="60.5" cy="51" r="2" fill="#20242B"/>'
    '<path d="M40 64 Q50 68 60 64" fill="none" stroke="#20242B" stroke-width="2" stroke-linecap="round"/>'
    '<path d="M59 71 L73 71 L71 80 Q66 82 61 80 Z" fill="#9C5B2A"/>'
    '<path d="M63 68 Q61 65 63 62 M69 68 Q71 65 69 62" fill="none" stroke="#fff" stroke-width="1.4"/>'
    '</svg>'
)
_AV_LAKSHMI = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Lakshmi Pat">'
    '<circle cx="50" cy="50" r="48" fill="#C84C84"/>'
    '<circle cx="50" cy="22" r="6" fill="#20242B"/>'
    '<path d="M27 46 Q25 22 50 21 Q75 22 73 46 Q68 31 50 31 Q32 31 27 46 Z" fill="#20242B"/>'
    '<rect x="31" y="33" width="38" height="44" rx="13" fill="#fff"/>'
    '<path d="M31 41 Q31 33 36 33 L36 61 Q31 54 31 41 Z" fill="#20242B"/>'
    '<path d="M69 41 Q69 33 64 33 L64 61 Q69 54 69 41 Z" fill="#20242B"/>'
    '<circle cx="50" cy="39" r="2.6" fill="#C0143C"/>'
    '<path d="M34 51 Q40 48 46 51 Q45 56 39 56 Q34 55 34 51 Z" fill="#fff" stroke="#20242B" stroke-width="2.2"/>'
    '<path d="M66 51 Q60 48 54 51 Q55 56 61 56 Q66 55 66 51 Z" fill="#fff" stroke="#20242B" stroke-width="2.2"/>'
    '<line x1="46" y1="51.5" x2="54" y2="51.5" stroke="#20242B" stroke-width="2.2"/>'
    '<circle cx="40" cy="52" r="1.8" fill="#20242B"/><circle cx="60" cy="52" r="1.8" fill="#20242B"/>'
    '<circle cx="30" cy="61" r="2" fill="#E6B23A"/><path d="M27 63 Q30 69 33 63 Z" fill="#E6B23A"/>'
    '<circle cx="70" cy="61" r="2" fill="#E6B23A"/><path d="M67 63 Q70 69 73 63 Z" fill="#E6B23A"/>'
    '<path d="M44 65 Q50 69 56 65" fill="none" stroke="#20242B" stroke-width="2" stroke-linecap="round"/>'
    '</svg>'
)
_AV_NANDI = (
    '<svg viewBox="0 0 100 100" role="img" aria-label="Nandi Pat">'
    '<circle cx="50" cy="50" r="48" fill="#7A6FD6"/>'
    '<path d="M33 33 Q22 26 24 15 Q33 21 39 31 Z" fill="#fff"/>'
    '<path d="M67 33 Q78 26 76 15 Q67 21 61 31 Z" fill="#fff"/>'
    '<ellipse cx="28" cy="47" rx="5" ry="3.6" fill="#fff"/>'
    '<ellipse cx="72" cy="47" rx="5" ry="3.6" fill="#fff"/>'
    '<rect x="31" y="34" width="38" height="40" rx="14" fill="#fff"/>'
    '<ellipse cx="50" cy="66" rx="13" ry="9" fill="#E7E2F7"/>'
    '<path d="M47 40 L47 47 M53 40 L53 47" stroke="#EE9A22" stroke-width="2.2" stroke-linecap="round"/>'
    '<path d="M47 47 Q50 50 53 47" fill="none" stroke="#EE9A22" stroke-width="2.2"/>'
    '<path d="M50 40 L50 46" stroke="#C0143C" stroke-width="1.6" stroke-linecap="round"/>'
    '<circle cx="43" cy="51" r="2.4" fill="#20242B"/><circle cx="57" cy="51" r="2.4" fill="#20242B"/>'
    '<circle cx="50" cy="70" r="4" fill="none" stroke="#E6B23A" stroke-width="2"/>'
    '</svg>'
)

AVATARS: dict[str, dict] = {
    "seth":    {"name": "Seth Pat",    "tag": "old-school bania wisdom",  "svg": _AV_SETH},
    "rao":     {"name": "Rao Pat",     "tag": "Tollywood mass swagger",   "svg": _AV_RAO},
    "singh":   {"name": "Singh Pat",   "tag": "the steady, confident ace", "svg": _AV_SINGH},
    "chai":    {"name": "Chai Pat",    "tag": "cutting-chai quant",       "svg": _AV_CHAI},
    "lakshmi": {"name": "Lakshmi Pat", "tag": "goddess of wealth",        "svg": _AV_LAKSHMI},
    "nandi":   {"name": "Nandi Pat",   "tag": "bull-market energy",       "svg": _AV_NANDI},
}
_DEFAULT_AV = "seth"


# (All four flows — explain · accumulation · RS · fundamentals — are live below.)


_PAT_CSS = """
<style>
.patHero{display:flex;align-items:center;gap:10px;margin:4px 0 14px;}
.patHeroAv{width:44px;height:44px;flex:none;border-radius:50%;overflow:hidden;background:#161b22;}
.patHeroAv svg{width:44px;height:44px;display:block;}
.patHeroName{font-weight:700;font-size:15px;}
.patHeroTag{color:#8b949e;font-size:12px;margin-top:1px;}
.patFaceToggle{color:#58a6ff;text-decoration:none;cursor:pointer;}
.patFaceToggle:hover{text-decoration:underline;}
.patPicks{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 16px;}
.patPick{background:#161b22;border:1px solid #30363d;border-radius:50%;padding:0;
         width:64px;height:64px;cursor:pointer;overflow:hidden;line-height:0;}
.patPick svg{width:62px;height:62px;display:block;}
.patPick.on{border-color:#3fb950;box-shadow:0 0 0 2px rgba(63,185,80,.33);}
.patQ{background:#161b22;border:1px solid #30363d;border-radius:12px;
      border-top-left-radius:3px;padding:11px 14px;font-size:14px;line-height:1.5;
      margin:0 0 12px;max-width:92%;}
.patChips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 6px;}
.patChip{background:#1b2230;border:1px solid #2b3a52;color:#cdd9e5;border-radius:9px;
         padding:8px 12px;font-size:13px;text-decoration:none;display:inline-block;}
.patChip:hover{border-color:#1f6feb;}
.patChip .ar{color:#58a6ff;font-weight:700;}
.patAnsTerm{font-weight:800;font-size:16px;margin-bottom:4px;}
.patAnsPlain{color:#9fb0c3;font-size:13px;font-style:italic;margin-bottom:8px;}
.patAnsDetail{font-size:14px;line-height:1.65;margin:0 0 10px;}
.patMeta{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:#8b949e;
         font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
         border-top:1px solid #21262d;padding-top:8px;margin-top:2px;}
.patBack{display:inline-block;margin:0 0 12px;color:#8b949e;font-size:12px;text-decoration:none;}
.patBack:hover{color:#cdd9e5;}
.patChip.on{border-color:#3fb950;color:#fff;background:#16341f;}
.patTable{overflow-x:auto;margin-top:2px;}
.patTable table{min-width:660px;font-variant-numeric:tabular-nums;}
.patTable table.dt .dttool{margin:0 0 8px;}
.patFb{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:14px 0 4px;
       padding-top:10px;border-top:1px solid #21262d;font-size:12px;color:#8b949e;}
.patFbBtn{background:#161b22;border:1px solid #30363d;border-radius:8px;cursor:pointer;
          padding:4px 10px;font-size:14px;line-height:1;}
.patFbBtn:hover{border-color:#1f6feb;}
.patFbThx{color:#3fb950;}
.patFbWrong{display:flex;gap:6px;flex-wrap:wrap;align-items:center;flex:1;min-width:220px;}
.patFbInput{flex:1;min-width:160px;background:#0d1117;border:1px solid #30363d;
            color:#e6edf3;border-radius:8px;padding:5px 9px;font-size:13px;}
.patFbInput:focus{outline:none;border-color:#1f6feb;}
.patFbSend{background:#1f6feb;border:none;color:#fff;border-radius:8px;cursor:pointer;
           padding:5px 12px;font-size:13px;}
.patCardHd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:10px;}
.pcSym{font-weight:800;font-size:18px;}
.pcSec{color:#8b949e;font-size:12px;}
.pcCmp{margin-left:auto;font-weight:700;font-variant-numeric:tabular-nums;}
.patFacts{display:grid;grid-template-columns:repeat(auto-fill,minmax(124px,1fr));gap:6px 14px;}
.patFact{display:flex;justify-content:space-between;gap:8px;font-size:13px;
         border-bottom:1px solid #21262d;padding:3px 0;}
.patFact .fl{color:#8b949e;}
.patFact .fv{font-variant-numeric:tabular-nums;}
.patFlag{margin-top:12px;border-radius:10px;padding:8px 12px;font-size:13px;}
.patFlag ul{margin:4px 0 0;padding-left:18px;}
.patFlag b{font-size:11px;text-transform:uppercase;letter-spacing:.4px;}
.patFlagBad{background:#2a1416;border:1px solid #5c2a2f;color:#f0c0c4;}
.patFlagOk{background:#0f2417;border:1px solid #2a5c3a;color:#bfe6c9;}
/* multi-condition planner pills + strategy board + compare (Lane F) */
.patPill{display:inline-block;background:#172554;border:1px solid #2b3a6a;color:#9db7ff;
         border-radius:20px;padding:3px 10px;font-size:11.5px;font-weight:600;}
.patPillOk{display:inline-block;background:#0f2417;border:1px solid #2a5c3a;color:#3fb950;
           border-radius:20px;padding:2px 9px;font-size:11px;font-weight:600;}
.patPillWarn{display:inline-block;background:#2a2410;border:1px solid #5c4a1f;color:#e3b341;
             border-radius:20px;padding:2px 9px;font-size:11px;font-weight:600;}
.patStratWrap{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin:2px 0 6px;}
.patStrat{background:#161b22;border:1px solid #30363d;border-radius:11px;padding:12px 13px;}
.psHd{display:flex;align-items:center;gap:9px;margin-bottom:7px;}
.psTitle{font-weight:700;font-size:14px;color:#e6edf3;text-decoration:none;}
.psTitle:hover{color:#58a6ff;}
.psCount{font-weight:700;font-variant-numeric:tabular-nums;font-size:18px;margin-left:auto;}
.psNames{font-size:12.5px;line-height:1.7;}
.psNames a{color:#cdd9e5;text-decoration:none;}
.psNames a:hover{color:#58a6ff;}
.psMeta{font-size:11px;margin-top:7px;}
.psMeta a{color:#58a6ff;text-decoration:none;}
.patCmp{display:flex;gap:12px;flex-wrap:wrap;}
.patCmpCol{flex:1;min-width:260px;background:#161b22;border:1px solid #30363d;border-radius:11px;padding:12px 13px;}
.patWhyHd{font-weight:700;font-size:15px;margin:4px 0 8px;}
.patWhy{margin:0 0 12px;padding-left:20px;font-size:13.5px;line-height:1.7;}
.patWhy li{margin:2px 0;}
.patWhy b{color:#e6edf3;}
.patFupWrap{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:12px 0 4px;
            padding-top:10px;border-top:1px solid #21262d;}
.patFupLbl{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#8b949e;}
.patFup{background:#10243a;border-color:#1f4e79;color:#9ad1ff;}
.patFup:hover{border-color:#58a6ff;}
.patTrail{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 14px;
          padding:8px 11px;background:#0d1117;border:1px solid #21262d;border-radius:9px;}
.patTrailLbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;color:#8b949e;
          white-space:nowrap;}
.patTrailItems{display:flex;align-items:center;gap:6px;flex-wrap:wrap;flex:1;min-width:0;}
.patTrailItem{font-size:12px;color:#9ad1ff;text-decoration:none;background:#10243a;
          border:1px solid #1f4e79;border-radius:7px;padding:3px 9px;max-width:260px;
          white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.patTrailItem:hover{border-color:#58a6ff;}
.patTrailSep{color:#586069;font-size:12px;}
.patTrailNew{font-size:11.5px;color:#8b949e;text-decoration:none;white-space:nowrap;
          border:1px solid #30363d;border-radius:7px;padding:3px 9px;}
.patTrailNew:hover{border-color:#8b949e;color:#e6edf3;}
.patRefine{display:flex;gap:7px;margin:8px 0 2px;}
.patRefine input[name=add]{flex:1;min-width:180px;background:#0d1117;border:1px solid #30363d;
            color:#e6edf3;border-radius:8px;padding:7px 11px;font-size:13px;}
.patRefine input[name=add]:focus{outline:none;border-color:#1f6feb;}
.patRefine button{background:#1f6feb;border:none;color:#fff;border-radius:8px;cursor:pointer;
            padding:7px 14px;font-size:13px;}
.patSaveRow{margin:8px 0 2px;}
.patBoardBtn{background:#161b22;border:1px solid #30363d;color:#e3b341;border-radius:8px;
            cursor:pointer;padding:5px 11px;font-size:12.5px;}
.patBoardBtn:hover{border-color:#e3b341;}
.patBoardBtn:disabled{opacity:.7;cursor:default;color:#3fb950;border-color:#2a5c3a;}
.patBoardList{display:flex;flex-direction:column;gap:6px;margin:10px 0;}
.patBoardRow{display:flex;align-items:center;gap:8px;background:#0d1117;
            border:1px solid #21262d;border-radius:9px;padding:8px 10px;}
.patBoardRow:hover{border-color:#30363d;}
.patBoardOpen{flex:1;display:flex;flex-direction:column;gap:2px;text-decoration:none;
            color:#e3b341;font-size:13px;min-width:0;}
.patBoardSub{color:#8b949e;font-size:11.5px;white-space:nowrap;overflow:hidden;
            text-overflow:ellipsis;}
.patBoardDel{background:transparent;border:1px solid #30363d;color:#8b949e;border-radius:7px;
            cursor:pointer;padding:4px 9px;font-size:11.5px;flex:none;}
.patBoardDel:hover{border-color:#da3633;color:#f85149;}
</style>
"""


_PAT_TAGLINE = "your pattern guide"


def _avatar_picker() -> str:
    """The slim Pat header: the CHOSEN face + the name 'Pat' + a link to the
    face-picker page. The face is pure decoration — picked once on
    /dash/pat?flow=face, persisted in localStorage. The other faces are NOT shown
    here (only your current one), so nothing implies the choice is functional."""
    d = AVATARS[_DEFAULT_AV]
    # Hidden store of every face SVG so the load-time JS can swap in the chosen one.
    faces = "".join(f'<i data-av="{slug}">{a["svg"]}</i>' for slug, a in AVATARS.items())
    script = (
        "<script>(function(){var src={};"
        "document.querySelectorAll('#patFaces > i').forEach(function(e){src[e.getAttribute('data-av')]=e.innerHTML;});"
        "var sv=null;try{sv=localStorage.getItem('patAvatar');}catch(e){}"
        "var h=document.getElementById('patHeroAv');if(h&&sv&&src[sv]){h.innerHTML=src[sv];}"
        "})();</script>"
    )
    return (
        f'<div id="patFaces" style="display:none">{faces}</div>'
        '<div class="patHero">'
        f'<div class="patHeroAv" id="patHeroAv">{d["svg"]}</div>'
        '<div><div class="patHeroName">Pat</div>'
        f'<div class="patHeroTag">{_PAT_TAGLINE} · '
        '<a class="patFaceToggle" href="/dash/pat?flow=face">change face</a></div></div>'
        '</div>'
        + script
    )


def _face_picker() -> str:
    """The dedicated 'profile picture' page — visited only to change Pat's face.
    Pure decoration: tap one, it persists (localStorage), and you return to Pat."""
    picks = "".join(
        f'<button class="patPick" data-av="{slug}" onclick="patPickFace(\'{slug}\')" '
        f'aria-label="Pat face style">{a["svg"]}</button>'
        for slug, a in AVATARS.items()
    )
    script = (
        "<script>window.patPickFace=function(s){try{localStorage.setItem('patAvatar',s);}"
        "catch(e){}location.href='/dash/pat';};"
        "(function(){var sv='seth';try{sv=localStorage.getItem('patAvatar')||'seth';}catch(e){}"
        "var ps=document.querySelectorAll('.patPick');for(var i=0;i<ps.length;i++){"
        "ps[i].classList.toggle('on',ps[i].getAttribute('data-av')===sv);}})();</script>"
    )
    return (
        '<a class="patBack" href="/dash/pat">← back to Pat</a>'
        + _q_bubble("Pick Pat's look — it's just a face, only you see it. Tap one and it stays.")
        + f'<div class="patPicks">{picks}</div>'
        + script
    )


def _chip(href: str, label: str, arrow: bool = False) -> str:
    ar = ' <span class="ar">→</span>' if arrow else ""
    return f'<a class="patChip" href="{href}">{_esc(label)}{ar}</a>'


def _q_bubble(text: str) -> str:
    return f'<div class="patQ">{_esc(text)}</div>'


# ── feedback bar (👍/👎 + "what did you expect?") — the learning loop's UI ─────
# The bar carries the answer's CONTEXT (the typed query, the routed flow + chip
# params) as data-attributes; the JS POSTs that context to /pat/feedback so a
# 👍 becomes a confirmed routing example and a 👎 + expected-text becomes a
# correction (see src/pat/feedback.py + routes.py). Decoupled from dashboard.py.

def _feedback_bar(query: str = "", flow: str = "", params: dict | None = None,
                  source: str = "") -> str:
    pj = _esc(json.dumps(params or {}, separators=(",", ":")))
    return (
        '<div class="patFb" data-q="' + _esc(query) + '" data-flow="' + _esc(flow) + '"'
        ' data-params="' + pj + '" data-src="' + _esc(source) + '">'
        '<span class="patFbAsk">Did this answer what you asked?</span>'
        '<button type="button" class="patFbBtn" data-v="up" title="Yes, this is right">👍</button>'
        '<button type="button" class="patFbBtn" data-v="down" title="No, not what I wanted">👎</button>'
        '<span class="patFbThx" hidden>Thanks — Pat will learn from this. ✓</span>'
        '<span class="patFbWrong" hidden>'
        '<input class="patFbInput" type="text" maxlength="200"'
        ' placeholder="What did you expect instead? (the most useful thing you can tell Pat)"/>'
        '<button type="button" class="patFbSend">Send</button></span>'
        '</div>'
    )


# Idempotent: binds each .patFb once (data-bound guard), so it is safe to include
# more than once per page. A 👎 records immediately (the negative is never lost),
# then reveals the "what did you expect?" box which enriches the SAME row.
_FB_JS = (
    "<script>(function(){"
    "function post(u,d){return fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify(d)}).then(function(r){return r&&r.ok?r.json():null;}).catch(function(){return null;});}"
    "document.querySelectorAll('.patFb').forEach(function(bar){"
    "if(bar.dataset.bound)return;bar.dataset.bound='1';"
    "var q=bar.dataset.q||'',flow=bar.dataset.flow||'',src=bar.dataset.src||'';"
    "var params={};try{params=JSON.parse(bar.dataset.params||'{}');}catch(e){}"
    "var ask=bar.querySelector('.patFbAsk'),thx=bar.querySelector('.patFbThx'),"
    "wrong=bar.querySelector('.patFbWrong');var lastId=null;"
    "bar.querySelectorAll('.patFbBtn').forEach(function(btn){btn.addEventListener('click',function(){"
    "var v=btn.dataset.v;bar.querySelectorAll('.patFbBtn').forEach(function(b){b.disabled=true;b.style.opacity=.4;});"
    "post('/pat/feedback',{verdict:v,query:q,flow:flow,params:params,source:src})"
    ".then(function(j){if(j&&j.id)lastId=j.id;});"
    "if(v==='down'){if(wrong)wrong.hidden=false;var i=bar.querySelector('.patFbInput');if(i)i.focus();}"
    "else{if(ask)ask.hidden=true;if(thx)thx.hidden=false;}});});"
    "var send=bar.querySelector('.patFbSend');if(send)send.addEventListener('click',function(){"
    "var inp=bar.querySelector('.patFbInput');var txt=inp?inp.value.trim():'';"
    "post('/pat/feedback/correct',{id:lastId,expected:txt,query:q,flow:flow,params:params,src:src});"
    "if(wrong)wrong.hidden=true;if(ask)ask.hidden=true;if(thx)thx.hidden=false;});"
    "});})();</script>"
)


def _metric_directory() -> str:
    """All explainable terms, grouped by family — chips that link to the answer."""
    out = []
    for fam_key, fam_label in FAMILIES.items():
        ents = family(fam_key)
        if not ents:
            continue
        out.append(f'<div class="ghdr">{_esc(fam_label)}</div>')
        chips = [
            _chip(f"/dash/pat?flow=explain&explain={slug}", e["term"])
            for slug, e in ents
        ]
        out.append(f'<div class="patChips">{"".join(chips)}</div>')
    return "".join(out)


def _answer(slug: str, e: dict) -> str:
    related = []
    for r in e.get("related", []):
        re_ = get(r)
        if re_:
            related.append(_chip(f"/dash/pat?flow=explain&explain={r}", re_["term"]))
    rel_html = (
        f'<div class="ghdr">Related</div><div class="patChips">{"".join(related)}</div>'
        if related else ""
    )
    return (
        '<a class="patBack" href="/dash/pat?flow=explain">← explain another metric</a>'
        '<div class="card">'
        f'<div class="patAnsTerm">{_esc(e["term"])}</div>'
        f'<div class="patAnsPlain">{_esc(e["plain"])}</div>'
        f'<p class="patAnsDetail">{_esc(e["detail"])}</p>'
        f'<div class="patMeta"><span>unit: {_esc(e["unit"])}</span>'
        f'<span>source: {_esc(e["source"])}</span></div>'
        f'{rel_html}'
        '</div>'
    )


def _explain_flow(explain: str, q: str) -> str:
    # A specific term was chosen → answer it.
    if explain and get(explain):
        e = get(explain)
        return _q_bubble(f"Here's {e['term']} —") + _answer(explain, e)

    search = (
        '<form class="search" action="/dash/pat" method="get" autocomplete="off">'
        '<input type="hidden" name="flow" value="explain"/>'
        f'<input name="q" value="{_esc(q)}" placeholder="ask about any metric — p_score, accumulation, key price…"/>'
        '<button>Ask</button></form>'
    )

    # A free-text query → rank matches with the deterministic fallback.
    if q:
        hits = find(q, limit=8)
        if hits:
            bubble = _q_bubble(f"Closest matches for “{q}”. Tap one:")
            chips = [_chip(f"/dash/pat?flow=explain&explain={s}", e["term"]) for s, e in hits]
            return bubble + search + f'<div class="patChips">{"".join(chips)}</div>'
        return (
            _q_bubble(f"I don't have “{q}” yet — here's everything I can explain:")
            + search + _metric_directory()
        )

    # Entry point for the flow → search + full directory.
    return (
        _q_bubble("Which term should I explain? Tap one, or search.")
        + search + _metric_directory()
    )


# ── data flow: accumulation setups (live, read-only over stock_signals) ──────

def _u(s) -> str:
    return quote_plus(str(s) if s is not None else "")


def _int(v) -> str:
    return str(int(v)) if v is not None else '<span class="mut">—</span>'


def _n(v, d=2) -> str:
    return f"{v:,.{d}f}" if v is not None else '<span class="mut">—</span>'


def _sgn(v, d=1) -> str:
    if v is None:
        return '<span class="mut">—</span>'
    cls = "pos" if v > 0 else ("neg" if v < 0 else "mut")
    return f'<span class="{cls}">{v:+.{d}f}%</span>'


def _cr(v) -> str:
    return f"{v / 1e7:,.1f}" if v is not None else '<span class="mut">—</span>'


def _rank_pill(rank) -> str:
    if not rank:
        return '<span class="mut">—</span>'
    return f'<span class="pill p-{_esc(rank)}">{_esc(rank)}</span>'


def _char_pill(c) -> str:
    short = {"ACCUMULATION": ("ACC", "ca-acc"), "DISTRIBUTION": ("DIST", "ca-dist"),
             "CONSOLIDATION": ("CONS", "ca-cons"), "NEUTRAL": ("NEU", "ca-neu")}
    lbl, cls = short.get(c or "", (c or "—", "ca-neu"))
    return f'<span class="pill {cls}">{_esc(lbl)}</span>'


def _chip_sel(href: str, label: str, active: bool) -> str:
    return f'<a class="{"patChip on" if active else "patChip"}" href="{href}">{_esc(label)}</a>'


# character key -> the flow NAME that carries it (so distribution/consolidation reuse
# the whole accumulation view + params without needing a new route param).
_ACC_FLOW = {"": "accumulation", "distribution": "distribution", "consolidation": "consolidation"}


def _acc_url(sector: str, strength: str, entry: str, window: str = "", character: str = "") -> str:
    qs = ["flow=" + _ACC_FLOW.get(character, "accumulation")]
    if sector:
        qs.append("sector=" + _u(sector))
    if strength:
        qs.append("strength=" + _u(strength))
    if entry:
        qs.append("entry=" + _u(entry))
    if window:
        qs.append("align=" + _u(window))   # reuse the captured `align` route param for the accumulation window
    return "/dash/pat?" + "&".join(qs)


def _acc_table(rows, win_label: str = "") -> str:
    # When a window is asked, LEAD with that DVPT ratio column (reporting follows
    # the question / "right not more"); otherwise keep the standard layout.
    lead = f'<th>{_esc(win_label)}</th>' if win_label else ''
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>CMP</th>' + lead + '<th>Rank</th><th>p/r</th><th>Character</th>'
            '<th>Δ hot%</th><th>key gap%</th><th>52w%</th><th>RS</th>'
            '<th>Sector</th><th>Deliv ₹Cr</th></tr></thead><tbody>')
    rws = []
    for r in rows:
        lead_td = f'<td>{_n(r["win_ratio"])}×</td>' if win_label else ''
        if win_label and r["win_ratio"] is None:
            lead_td = f'<td>{_n(None)}</td>'
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            + lead_td +
            f'<td>{_rank_pill(r["trigger_rank"])}</td>'
            f'<td>{_int(r["p_score"])}/{_int(r["r_score"])}</td>'
            f'<td>{_char_pill(r["accum_character"])}</td>'
            f'<td>{_sgn(r["price_vs_hot_avg_pct"])}</td>'
            f'<td>{_sgn(r["gap_to_key_p3m"])}</td>'
            f'<td>{_sgn(r["pct_from_52w_high"])}</td>'
            f'<td>{_int(r["rs_rank"])}</td>'
            f'<td class="mut">{_esc(r["primary_sector"] or "—")}</td>'
            f'<td>{_cr(r["delivery_value_today"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


# character -> the intro line. Distribution is the strong-hand-EXITING mirror; the
# copy makes the "warning, not a buy" reading explicit (answer philosophy §3.3).
_ACC_BUBBLE = {
    "": ("Accumulation setups — a strong hand active AND the character reading "
         "accumulation. The window ranks + leads by that delivery read; also narrow "
         "by strength, entry, or sector:"),
    "distribution": ("Distribution — the mirror of accumulation: a strong hand active "
                     "but the character reading DISTRIBUTION (smart money EXITING, often "
                     "into strength near the highs). A warning, not a buy:"),
    "consolidation": ("Consolidation — an active hand with the character coiling "
                      "(neither clearly accumulating nor distributing yet):"),
}


def _accumulation_flow(conn, sector: str, strength: str, entry: str, window: str = "",
                       character: str = "", top_n=None) -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble(_ACC_BUBBLE.get(character, _ACC_BUBBLE[""])),
        '<div class="ghdr">Character</div><div class="patChips">',
    ]
    for ckey, (clbl, _cv) in ACC_CHARACTER.items():
        out.append(_chip_sel(_acc_url(sector, strength, entry, window, ckey), clbl, ckey == character))
    out.append('</div><div class="ghdr">Window</div><div class="patChips">')
    for key, (lbl, _c) in ACC_WINDOW.items():
        out.append(_chip_sel(_acc_url(sector, strength, entry, key, character), lbl, key == window))
    out.append('</div><div class="ghdr">Strength</div><div class="patChips">')
    for key, (lbl, _p) in ACC_STRENGTH.items():
        out.append(_chip_sel(_acc_url(sector, key, entry, window, character), lbl, key == strength))
    out.append('</div><div class="ghdr">Entry</div><div class="patChips">')
    for key, lbl in ACC_ENTRY.items():
        out.append(_chip_sel(_acc_url(sector, strength, key, window, character), lbl, key == entry))
    out.append('</div>')

    sectors = []
    if conn is not None:
        try:
            ssql, sparams = build_accumulation_sectors_query(character)
            sectors = list(conn.execute(ssql, sparams))
        except Exception:
            sectors = []
    out.append('<div class="ghdr">Sector</div><div class="patChips">')
    out.append(_chip_sel(_acc_url("", strength, entry, window, character), "All sectors", sector == ""))
    for r in sectors:
        out.append(_chip_sel(_acc_url(r["sector"], strength, entry, window, character),
                             f'{r["sector"]} ({r["c"]})', sector == r["sector"]))
    out.append('</div>')

    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_accumulation_query(sector, strength, entry, window, character, top_n=top_n)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    win_label = ACC_WINDOW.get(window, ACC_WINDOW[""])[0] if window else ""
    wtag = f' · {_esc(win_label)}' if win_label else ''
    tag = f' · {_esc(sector)}' if sector else ''
    cap = f'top {int(top_n)} · ' if top_n else ''
    clabel = ACC_CHARACTER.get(character, ACC_CHARACTER[""])[0]
    out.append(f'<div class="ghdr">{cap}{_esc(clabel)}{wtag}{tag} ({len(rows)})</div>')
    out.append(_acc_table(rows, win_label) if rows
               else '<div class="empty">Nothing matches — loosen the filters.</div>')
    return "".join(out)


# ── data flow: RS leaders (live, read-only over stock_signals) ───────────────

def _yn(v) -> str:
    return '<span class="pos">✓</span>' if v else '<span class="mut">·</span>'


def _txt(v) -> str:
    return f'<span class="mut">{_esc(v)}</span>' if v else '<span class="mut">—</span>'


def _rs_url(sector: str, strength: str, align: str, window: str = "") -> str:
    qs = ["flow=rs"]
    if sector:
        qs.append("sector=" + _u(sector))
    if strength:
        qs.append("strength=" + _u(strength))
    if align:
        qs.append("align=" + _u(align))
    if window:
        qs.append("entry=" + _u(window))   # reuse the captured `entry` route param for the RS window
    return "/dash/pat?" + "&".join(qs)


def _rs_table(rows, win_label: str = "RS 3M") -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>CMP</th><th>RS</th><th>' + _esc(win_label) + '</th><th>vs broad</th>'
            '<th>vs sector</th><th>SiS</th><th>Sector</th><th>Pos</th><th>Character</th>'
            '</tr></thead><tbody>')
    rws = []
    for r in rows:
        sis = r["rs_vs_broad_above_200ma"] and r["rs_vs_sector_above_200ma"]
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            f'<td>{_int(r["rs_rank"])}</td>'
            f'<td>{_sgn(r["rs_slope"])}</td>'
            f'<td>{_txt(r["rs_vs_broad_trend_state"])}</td>'
            f'<td>{_txt(r["rs_vs_sector_trend_state"])}</td>'
            f'<td>{_yn(sis)}</td>'
            f'<td class="mut">{_esc(r["primary_sector"] or "—")}</td>'
            f'<td>{_rank_pill(r["trigger_rank"])}</td>'
            f'<td>{_char_pill(r["accum_character"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _rs_flow(conn, sector: str, strength: str, align: str, window: str = "", top_n=None) -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("RS leaders — the names the market is voting for. The window ranks + "
                  "shows that timeframe; also filter by strength, sector, or strong-in-strong:"),
        '<div class="ghdr">Window</div><div class="patChips">',
    ]
    for key, (lbl, _s) in RS_WINDOW.items():
        out.append(_chip_sel(_rs_url(sector, strength, align, key), lbl, key == window))
    out.append('</div><div class="ghdr">Strength</div><div class="patChips">')
    for key, (lbl, _r) in RS_STRENGTH.items():
        out.append(_chip_sel(_rs_url(sector, key, align, window), lbl, key == strength))
    out.append('</div><div class="ghdr">Alignment</div><div class="patChips">')
    for key, lbl in RS_ALIGN.items():
        out.append(_chip_sel(_rs_url(sector, strength, key, window), lbl, key == align))
    out.append('</div>')

    sectors = []
    if conn is not None:
        try:
            sectors = list(conn.execute(build_rs_sectors_query()))
        except Exception:
            sectors = []
    out.append('<div class="ghdr">Sector</div><div class="patChips">')
    out.append(_chip_sel(_rs_url("", strength, align, window), "All sectors", sector == ""))
    for r in sectors:
        out.append(_chip_sel(_rs_url(r["sector"], strength, align, window),
                             f'{r["sector"]} ({r["c"]})', sector == r["sector"]))
    out.append('</div>')

    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_rs_query(sector, strength, align, window, top_n=top_n)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    win_label = RS_WINDOW.get(window, RS_WINDOW[""])[0]
    tag = f' · {_esc(sector)}' if sector else ''
    cap = f'top {int(top_n)} · ' if top_n else ''
    out.append(f'<div class="ghdr">Leaders · {cap}{_esc(win_label)}{tag} ({len(rows)})</div>')
    out.append(_rs_table(rows, win_label) if rows
               else '<div class="empty">No RS leaders match — loosen the filters.</div>')
    return "".join(out)


# ── data flow: fundamentals screen (live, read-only over `fundamentals`) ─────

def _pc(v, d=1) -> str:
    return f"{v:,.{d}f}%" if v is not None else '<span class="mut">—</span>'


def _fund_url(val="", qual="", grow="", bs="", sector="", own="") -> str:
    qs = ["flow=fundamentals"]
    for k, v in (("val", val), ("qual", qual), ("grow", grow), ("bs", bs),
                 ("sector", sector), ("own", own)):
        if v:
            qs.append(f"{k}={_u(v)}")
    return "/dash/pat?" + "&".join(qs)


def _fund_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>CMP</th><th>MCap ₹Cr</th><th>P/E</th><th>ROCE</th>'
            '<th>ROE</th><th>Profit 5Y</th><th>D/E</th><th>Promoter</th><th>Pledge</th>'
            '</tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            f'<td>{_n(r["market_cap_cr"], 0)}</td>'
            f'<td>{_n(r["pe"], 1)}</td>'
            f'<td>{_pc(r["roce"])}</td>'
            f'<td>{_pc(r["roe"])}</td>'
            f'<td>{_pc(r["profit_growth_5y"])}</td>'
            f'<td>{_n(r["debt_to_equity"], 2)}</td>'
            f'<td>{_pc(r["promoter_holding"])}</td>'
            f'<td>{_pc(r["promoter_pledge"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _fundamentals_flow(conn, val, qual, grow, bs, sector, own) -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("Screen by fundamentals — from the cached Screener snapshot (the "
                  "surfaced set, not the whole market). Best of it, ranked by ROCE:"),
        '<div class="ghdr">Presets</div><div class="patChips">',
    ]
    for _key, (label, params) in NAMED_SCREENS.items():
        out.append(_chip(_fund_url(**params), label, arrow=True))
    out.append('</div>')

    cur = {"val": val, "qual": qual, "grow": grow, "bs": bs, "sector": sector, "own": own}
    groups = [("Valuation", FUND_VAL, "val", val), ("Quality", FUND_QUAL, "qual", qual),
              ("Growth", FUND_GROW, "grow", grow), ("Balance sheet", FUND_BS, "bs", bs),
              ("Ownership", FUND_OWN, "own", own)]
    for glabel, grp, pkey, pval in groups:
        out.append(f'<div class="ghdr">{glabel}</div><div class="patChips">')
        for key, tup in grp.items():
            params = dict(cur)
            params[pkey] = key
            out.append(_chip_sel(_fund_url(**params), tup[0], key == pval))
        out.append('</div>')
    out.append('<div class="ghdr">Sector</div><div class="patChips">')
    for key, lbl in FUND_SECTOR.items():
        params = dict(cur)
        params["sector"] = key
        out.append(_chip_sel(_fund_url(**params), lbl, key == sector))
    out.append('</div>')

    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, qp = build_fundamentals_query(val, qual, grow, bs, sector, own)
        rows = list(conn.execute(sql, qp))
    except Exception:
        rows = []
    out.append(f'<div class="ghdr">Matches ({len(rows)})</div>')
    out.append(_fund_table(rows) if rows
               else '<div class="empty">No names match — loosen the filters (the cached set is small).</div>')
    return "".join(out)


# ── movers flow (live, read-only over prices_eq / the bhav copy) ─────────────

def _movers_url(direction="", liq="", window=""):
    # Reuse the already-captured route params so the dashboard route needs no
    # change: for movers, strength = direction, entry = liquidity, align = window.
    qs = ["flow=movers"]
    if direction:
        qs.append("strength=" + _u(direction))
    if liq:
        qs.append("entry=" + _u(liq))
    if window:
        qs.append("align=" + _u(window))
    return "/dash/pat?" + "&".join(qs)


def _movers_table(rows, pct_label: str = "% chg", ref_label: str = "Prev") -> str:
    # Lead the move column with the asked window's label (today vs this-week).
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            f'<th>Symbol</th><th>CMP</th><th>{_esc(pct_label)}</th><th>{_esc(ref_label)}</th>'
            '<th>Turnover ₹Cr</th><th>Deliv%</th><th>Volume</th>'
            '</tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            f'<td>{_sgn(r["pct"])}</td>'
            f'<td>{_n(r["ref_close"])}</td>'
            f'<td>{_cr(r["turnover"])}</td>'
            f'<td>{_pc(r["deliv_per"])}</td>'
            f'<td>{_n(r["volume"], 0)}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _movers_flow(conn, direction, liq, window: str = "") -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("Biggest movers — % change for the asked window (today vs this "
                  "week). Pick a window and a direction:"),
        '<div class="ghdr">Window</div><div class="patChips">',
    ]
    for key, (lbl, _h, _m) in MOVERS_WINDOW.items():
        out.append(_chip_sel(_movers_url(direction, liq, key), lbl, key == window))
    out.append('</div><div class="ghdr">Direction</div><div class="patChips">')
    for key, (lbl, _o) in MOVERS_DIR.items():
        out.append(_chip_sel(_movers_url(key, liq, window), lbl, key == direction))
    out.append('</div><div class="ghdr">Liquidity</div><div class="patChips">')
    for key, (lbl, _f) in MOVERS_LIQ.items():
        out.append(_chip_sel(_movers_url(direction, key, window), lbl, key == liq))
    out.append('</div>')
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_movers_query(direction, liq, window)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    dlabel = MOVERS_DIR.get(direction, MOVERS_DIR[""])[0]
    wlabel, pct_label, _mod = MOVERS_WINDOW.get(window, MOVERS_WINDOW[""])
    ref_label = "Wk-ago" if window == "1w" else "Prev"
    out.append(f'<div class="ghdr">{_esc(dlabel)} · {_esc(wlabel)} ({len(rows)})</div>')
    out.append(_movers_table(rows, pct_label, ref_label) if rows
               else '<div class="empty">No movers — try All liquidity, or the session data may not be in yet.</div>')
    return "".join(out)


# ── index flow (live, read-only over index_signals) ──────────────────────────
# The index universe Pat was missing — sectoral + thematic NSE indices, best or
# WORST over a window, with a "turning up" reversal lens. Built after a real miss
# ("worst performing index that started turning up" → 0 stock RS-leaders).

def _index_url(window="", direction="", turning=""):
    # Reuse captured route params: entry = window, strength = direction, align = turning.
    qs = ["flow=index"]
    if window:
        qs.append("entry=" + _u(window))
    if direction:
        qs.append("strength=" + _u(direction))
    if turning:
        qs.append("align=" + _u(turning))
    return "/dash/pat?" + "&".join(qs)


def _index_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Index</th><th>Close</th>'
            '<th>1M</th><th>3M</th><th>6M</th><th>1Y</th>'
            '<th>RS 1M slope</th><th>Trend</th><th>% off 52wH</th>'
            '</tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym">{_esc(r["index_name"])}</td>'
            f'<td>{_n(r["close_value"])}</td>'
            f'<td>{_sgn(r["ret_1m_pct"])}</td>'
            f'<td>{_sgn(r["ret_3m_pct"])}</td>'
            f'<td>{_sgn(r["ret_6m_pct"])}</td>'
            f'<td>{_sgn(r["ret_12m_pct"])}</td>'
            f'<td>{_n(r["rs_vs_broad_slope_1m"], 2)}</td>'
            f'<td>{_txt(r["rs_vs_broad_trend_state"])}</td>'
            f'<td>{_sgn(r["pct_off_52w_high"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _index_flow(conn, window="", direction="", turning="") -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("Index performance — NSE sectoral & thematic indices, ranked by the "
                  "asked window. Flip to Laggards for the worst, and 'Turning up' for "
                  "the ones that started rising in the last month:"),
        '<div class="ghdr">Window</div><div class="patChips">',
    ]
    for key, (lbl, _c) in INDEX_WINDOW.items():
        out.append(_chip_sel(_index_url(key, direction, turning), lbl, key == window))
    out.append('</div><div class="ghdr">Direction</div><div class="patChips">')
    for key, (lbl, _s) in INDEX_DIRECTION.items():
        out.append(_chip_sel(_index_url(window, key, turning), lbl, key == direction))
    out.append('</div><div class="ghdr">Turning</div><div class="patChips">')
    for key, lbl in INDEX_TURNING.items():
        out.append(_chip_sel(_index_url(window, direction, key), lbl, key == turning))
    out.append('</div>')
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_index_query(window, direction, turning)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    wlabel = INDEX_WINDOW.get(window, INDEX_WINDOW[""])[0]
    dlabel = INDEX_DIRECTION.get(direction, INDEX_DIRECTION[""])[0]
    ttag = " · turning up (1M)" if turning == "turn" else ""
    out.append(f'<div class="ghdr">{_esc(dlabel)} · over {_esc(wlabel)}{_esc(ttag)} ({len(rows)})</div>')
    out.append(_index_table(rows) if rows
               else '<div class="empty">No indices match — try a different window, or turn off the turning filter.</div>')
    return "".join(out)


# ── RS laggards / weak stocks (the worst-side mirror, reuses _rs_table) ───────

def _rslag_url(sector: str = "", strength: str = "", window: str = "") -> str:
    qs = ["flow=rslag"]
    if sector:
        qs.append("sector=" + _u(sector))
    if strength:
        qs.append("strength=" + _u(strength))
    if window:
        qs.append("entry=" + _u(window))     # reuse entry=window, like the RS flow
    return "/dash/pat?" + "&".join(qs)


def _rslag_flow(conn, sector: str = "", strength: str = "", window: str = "") -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("Weak / laggard stocks — the bottom of relative strength (the worst "
                  "side Pat used to redirect away from). Ranked weakest-first by the "
                  "window's RS slope; pick how weak, and the window:"),
        '<div class="ghdr">Window</div><div class="patChips">',
    ]
    for key, (lbl, _s) in RS_WINDOW.items():
        out.append(_chip_sel(_rslag_url(sector, strength, key), lbl, key == window))
    out.append('</div><div class="ghdr">Weakness</div><div class="patChips">')
    for key, (lbl, _c) in RS_LAG_STRENGTH.items():
        out.append(_chip_sel(_rslag_url(sector, key, window), lbl, key == strength))
    out.append('</div><div class="patChips">'
               + _chip("/dash/pat?flow=rs", "↔ switch to RS leaders") + '</div>')
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_rs_query(sector, strength, "", window, direction="laggards")
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    win_label = RS_WINDOW.get(window, RS_WINDOW[""])[0]
    tag = f' · {_esc(sector)}' if sector else ''
    out.append(f'<div class="ghdr">Laggards · {_esc(win_label)}{tag} ({len(rows)})</div>')
    out.append(_rs_table(rows, win_label) if rows
               else '<div class="empty">No laggards match — loosen the filters.</div>')
    return "".join(out)


# ── pt14 quality-tier screen + the hard-disqualifier kill-list ────────────────

def _pt14_url(tier: str = "") -> str:
    qs = ["flow=pt14"]
    if tier:
        qs.append("strength=" + _u(tier))    # reuse strength param for the tier chip
    return "/dash/pat?" + "&".join(qs)


def _pt14_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>Tier</th><th>Score</th><th>Band</th>'
            '<th>Active patterns</th><th>Quality gate</th>'
            '</tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_esc(r["tier"] or "—")}</td>'
            f'<td>{_n(r["ns_base"], 0)}</td>'
            f'<td class="mut">{_n(r["ns_pessimistic"], 0)}–{_n(r["ns_optimistic"], 0)}</td>'
            f'<td>{_int(r["pac"])}</td>'
            f'<td>{_yn(r["qg_pass"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _pt14_flow(conn, tier: str = "") -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("pt14 quality — the 14-pattern business-quality score (0-100), highest "
                  "first, with hard-disqualified names excluded. Filter by tier:"),
        '<div class="ghdr">Tier</div><div class="patChips">',
    ]
    for key, (lbl, _t) in PT14_TIER.items():
        out.append(_chip_sel(_pt14_url(key), lbl, key == tier))
    out.append('</div><div class="patChips">'
               + _chip("/dash/pat?flow=redflags", "⚑ see the kill-list (disqualified)") + '</div>')
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_pt14_query(tier)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    out.append(f'<div class="ghdr">pt14 quality ({len(rows)})</div>')
    out.append(_pt14_table(rows) if rows
               else '<div class="empty">No scored names yet — pt14 is scored on demand for surfaced stocks.</div>')
    return "".join(out)


def _disqualified_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>Tier</th><th>Score</th><th>Why disqualified</th>'
            '</tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_esc(r["tier"] or "—")}</td>'
            f'<td>{_n(r["ns_base"], 0)}</td>'
            f'<td class="mut">{_esc(r["disqualifier_reasons"] or "—")}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _disqualified_flow(conn) -> str:
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("The kill-list — names the 14-pattern framework HARD-disqualified (a "
                  "fatal red flag), with the reason. This is Patearn's own 'avoid' "
                  "verdict, not a market screen:"),
    ]
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_disqualified_query()
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    out.append(f'<div class="ghdr">Hard-disqualified ({len(rows)})</div>')
    out.append(_disqualified_table(rows) if rows
               else '<div class="empty">No disqualified names recorded yet (pt14 scores on demand).</div>')
    return "".join(out)


# ── CCI: Management Credibility (concall intelligence, P5) ────────────────────

def _cci_fwd_html(v) -> str:
    v = (v or "FLAT").upper()
    if v == "UP":
        return '<span style="color:#3fb950">UP ↑</span>'
    if v in ("DOWN", "AVOID"):
        return f'<span style="color:#f85149">{_esc(v)} ↓</span>'
    return '<span style="color:#8b949e">FLAT</span>'


def _cci_tier_html(t) -> str:
    t = t or "—"
    col = "#3fb950" if t in ("A+", "A") else ("#f85149" if t == "D" else "#8b949e")
    return f'<span style="color:{col};font-weight:600">{_esc(t)}</span>'


def _cci_table(rows, avoid: bool = False) -> str:
    cols = ["Symbol", "Tier", "Score", "Forward", "Guid acc", "Quantif%", "Deter"]
    if avoid:
        cols.append("Veto")
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            + "".join(f"<th>{c}</th>" for c in cols) + "</tr></thead><tbody>")
    rws = []
    for r in rows:
        ga = r["guidance_accuracy_score"]
        ga_txt = (f'{ga:.0f}% ({r["n_promises_resolved"] or 0})' if ga is not None
                  else '<span style="color:#8b949e">unproven</span>')
        det = r["deterioration_score"] or 0
        det_txt = f'<span style="color:#f85149">{int(det)}</span>' if det else "0"
        cells = [
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>',
            f'<td>{_cci_tier_html(r["tier"])}</td>',
            f'<td>{_n(r["composite_score"], 0)}</td>',
            f'<td>{_cci_fwd_html(r["forward_direction"])}</td>',
            f'<td>{ga_txt}</td>',
            f'<td>{_n(r["quantification_rate"], 0)}</td>',
            f'<td>{det_txt}</td>',
        ]
        if avoid:
            veto = (f'<span style="color:#f85149" title="{_esc(r["veto_reason"] or "")}">⛔</span>'
                    if r["veto_active"] else "—")
            cells.append(f"<td>{veto}</td>")
        rws.append("<tr>" + "".join(cells) + "</tr>")
    return head + "".join(rws) + "</tbody></table></div>"


def _credibility_flow(conn, top_n=None) -> str:
    out = ['<a class="patBack" href="/dash/pat">← back</a>',
           _q_bubble("Credibility leaders — managements ranked by the MEASURABLE concall signal "
                     "(D61): kept-promise accuracy + how falsifiable their guidance is, "
                     "veto-excluded. The behaviour reads inform but never rank. Pilot:")]
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_credibility_query(top_n=top_n)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    cap = f"top {int(top_n)} " if top_n else ""
    out.append(f'<div class="ghdr">Credibility leaders — {cap}({len(rows)})</div>')
    out.append(_cci_table(rows) if rows
               else '<div class="empty">No scored concalls yet — the pilot is still extracting.</div>')
    out.append('<div class="patChips">'
               + _chip("/dash/pat?flow=deterioration", "⚠ deterioration / avoid tape")
               + _chip("/dash/concalls", "full CCI board →") + "</div>")
    return "".join(out)


def _deterioration_flow(conn) -> str:
    out = ['<a class="patBack" href="/dash/pat">← back</a>',
           _q_bubble("The avoid tape — names carrying a ⛔ veto (pledge / auditor-exit / pt14) or a "
                     "deterministic deterioration flag (a walked-back or quietly-dropped promise). "
                     "The credibility-decay tape the sell-side won't publish:")]
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_deterioration_query()
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    out.append(f'<div class="ghdr">Deterioration / avoid ({len(rows)})</div>')
    out.append(_cci_table(rows, avoid=True) if rows
               else '<div class="empty">No deterioration flags or vetoes yet (pilot still extracting).</div>')
    out.append('<div class="patChips">'
               + _chip("/dash/pat?flow=credibility", "★ credibility leaders")
               + _chip("/dash/concalls", "full CCI board →") + "</div>")
    return "".join(out)


# ── CCI x MEP confluence (the §9.8 "one fusion") — credible AND being accumulated ─

def _confluence_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>CMP</th><th>Character</th><th>p/r</th><th>RS</th>'
            '<th>Tier</th><th>Cred score</th><th>Guid acc</th><th>n</th>'
            '<th>Sector</th><th>Deliv ₹Cr</th></tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            f'<td>{_char_pill(r["accum_character"])}</td>'
            f'<td>{_int(r["p_score"])}/{_int(r["r_score"])}</td>'
            f'<td>{_int(r["rs_rank"])}</td>'
            f'<td>{_esc(r["tier"] or "—")}</td>'
            f'<td>{_n(r["composite_score"], 0)}</td>'
            f'<td>{_pc(r["guidance_accuracy_score"])}</td>'
            f'<td>{_int(r["n_promises_resolved"])}</td>'
            f'<td class="mut">{_esc(r["primary_sector"] or "—")}</td>'
            f'<td>{_cr(r["delivery_value_today"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _confluence_flow(conn) -> str:
    out = ['<a class="patBack" href="/dash/pat">← back</a>',
           _q_bubble("Credibility × accumulation — the CONFLUENCE: names a strong hand is "
                     "accumulating now (the MEP delivery lens) AND whose management is credible "
                     "on its concall track record (veto-excluded, ≥3 resolved promises). Two "
                     "INDEPENDENT lenses agreeing is the highest-evidence read — but it is "
                     "evidence, never a buy call, and the reads are at different grains "
                     "(daily delivery × quarterly credibility):")]
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_confluence_query()
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    # the as-of join contract (§9.8): disclose BOTH lenses' freshness, since they differ.
    asof_cred = rows[0]["as_of_period"] if rows else None
    try:
        asof_acc = conn.execute("SELECT MAX(trade_date) FROM stock_signals").fetchone()[0]
    except Exception:
        asof_acc = None
    out.append(f'<div class="ghdr">Credibility × accumulation ({len(rows)})</div>')
    out.append(_confluence_table(rows) if rows else
               '<div class="empty">No names are in BOTH lenses right now — that scarcity is '
               'itself the read (genuine confluence is rare). Try each lens alone below.</div>')
    out.append('<div class="patMeta">'
               f'<span>credibility as-of: {_esc(asof_cred or "—")}</span>'
               f'<span>accumulation as-of: {_esc(asof_acc or "—")}</span>'
               '<span>both lenses must agree · descriptive, not a signal</span></div>')
    out.append('<div class="patChips">'
               + _chip("/dash/pat?flow=credibility", "★ credibility leaders")
               + _chip("/dash/pat?flow=accumulation", "↗ accumulation setups")
               + _chip("/dash/concalls", "full CCI board →") + "</div>")
    return "".join(out)


# ── the GENERAL multi-condition CONFLUENCE PLANNER (N pillars + scope) ─────────
# Carries its params on the flow= path through dashboard.py's ALREADY-forwarded
# generic params (no dashboard.py edit needed): pillars→strength, capband→entry.
def _plan_url(pillars: str, sector: str = "", capband: str = "") -> str:
    qs = ["flow=confluence_plan", "strength=" + _u(pillars)]
    if sector:
        qs.append("sector=" + _u(sector))
    if capband:
        qs.append("entry=" + _u(capband))
    return "/dash/pat?" + "&".join(qs)


def _plan_pill(label: str) -> str:
    return f'<span class="patPill">{_esc(label)}</span>'


def _confluence_plan_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>CMP</th><th>Character</th><th>p/r</th><th>RS</th>'
            '<th>Tier</th><th>Cred</th><th>CPR</th><th>P/E</th><th>ROCE</th>'
            '<th>Sector</th></tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            f'<td>{_char_pill(r["accum_character"])}</td>'
            f'<td>{_int(r["p_score"])}/{_int(r["r_score"])}</td>'
            f'<td>{_int(r["rs_rank"])}</td>'
            f'<td>{_esc(r["tier"] or "—")}</td>'
            f'<td>{_n(r["composite_score"], 0)}</td>'
            f'<td>{_esc((r["cpr_pat"] or "—").replace("BULL_U", "bull-U").replace("BEAR_INVU", "bear-∩"))}</td>'
            f'<td>{_n(r["pe"], 1)}</td>'
            f'<td>{_pc(r["roce"])}</td>'
            f'<td class="mut">{_esc(r["primary_sector"] or "—")}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _confluence_plan_flow(conn, pillars: str = "", sector: str = "", capband: str = "") -> str:
    """The general planner: intersect ≥2 strategy pillars over the precomputed tables.
    Pillars come comma-separated (closed set); sector / cap-band narrow the universe."""
    plist = [p.strip() for p in (pillars or "").split(",") if p.strip() in PLAN_PILLARS]
    cap_lbl = PLAN_CAPBAND.get(capband, (capband.title() if capband else "", None))[0]
    scope_bits = " · ".join([b for b in (cap_lbl, (sector or "")) if b]) or "all NSE equities"
    named = ", ".join(PLAN_PILLARS[p].split(" — ")[0] for p in plist) or "—"
    out = ['<a class="patBack" href="/dash/pat">← back</a>',
           _q_bubble("Multi-condition CONFLUENCE — names where ALL of these hold at once, "
                     f"intersected over the precomputed tables: <b>{_esc(named)}</b> "
                     f"({_esc(scope_bits)}). Independent lenses agreeing is the highest-"
                     "evidence read — but it is EVIDENCE, never a buy call, and the lenses "
                     "sit at different grains (daily delivery/RS × quarterly credibility × "
                     "period CPR), shown by the as-of footer.")]
    out.append('<div class="patChips">'
               + "".join(_plan_pill(PLAN_PILLARS[p].split(" — ")[0]) for p in plist)
               + (_plan_pill(cap_lbl) if cap_lbl else "")
               + (_plan_pill(sector) if sector else "") + '</div>')
    # ≥1 pillar is enough when scoped to a cap-band/sector (e.g. "RS leaders, small-caps");
    # otherwise a confluence needs ≥2 conditions to be meaningful.
    if not plist or (len(plist) < 2 and not capband and not sector):
        out.append('<div class="empty">A confluence needs at least two conditions (or one '
                   'plus a cap-band/sector). Try “credible companies being accumulated, RS-leading”.</div>')
        return "".join(out)
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_confluence_plan_query(plist, sector=sector, capband=capband)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    asof_cred = next((r["as_of_period"] for r in rows if r["as_of_period"]), None)
    try:
        asof_acc = conn.execute("SELECT MAX(trade_date) FROM stock_signals").fetchone()[0]
    except Exception:
        asof_acc = None
    out.append(f'<div class="ghdr">{_esc(named)} · {_esc(scope_bits)} ({len(rows)})</div>')
    out.append(_confluence_plan_table(rows) if rows else
               '<div class="empty">No names satisfy ALL of these conditions right now — '
               'that scarcity is itself the read (true multi-lens confluence is rare). '
               'Drop a condition or widen the cap-band.</div>')
    out.append('<div class="patMeta">'
               f'<span>delivery / RS as-of: {_esc(asof_acc or "—")}</span>'
               + (f'<span>credibility as-of: {_esc(asof_cred)}</span>' if "credibility" in plist and asof_cred else "")
               + '<span>all lenses must agree · descriptive evidence, not a signal</span></div>')
    out.append('<div class="patChips">'
               + _chip("/dash/screen2", "open the wide screener →")
               + _chip("/dash/strategist", "strategist board →") + "</div>")
    return "".join(out)


# ── strategy_registry board read ("what's the MEP/CPR/Wolfe strategy showing") ─
def _strategy_url(key: str) -> str:
    return "/dash/pat?flow=strategy" + (("&strength=" + _u(key)) if key and key != "all" else "")


def _strategy_card(row: dict) -> str:
    count = row.get("count")
    cnt = f'{count:,}' if isinstance(count, int) else "—"
    health = (row.get("health") or "").lower()
    hpill = {"ok": ("fresh", "patPillOk"), "stale": ("stale", "patPillWarn"),
             "empty": ("no data", "patPill"), "link": ("live page", "patPill")}.get(
                 health, ("—", "patPill"))
    tops = [t for t in (row.get("top") or [])
            if (t.get("symbol") or "").strip() not in ("", "—", "-")]
    names = " · ".join(
        f'<a class="row" href="/dash/stock?sym={_u(t["symbol"])}">{_esc(t["symbol"])}</a>'
        f'<span class="mut"> {_esc(t.get("note", ""))}</span>' for t in tops[:5]) or \
        '<span class="mut">open the lens for live names</span>'
    asof = row.get("as_of")
    return (
        '<div class="patStrat">'
        f'<div class="psHd"><a class="psTitle" href="{_esc(row.get("route") or "#")}">'
        f'{_esc(row.get("label") or row.get("key"))}</a>'
        f'<span class="psCount">{cnt}</span>'
        f'<span class="{hpill[1]}">{hpill[0]}</span></div>'
        f'<div class="psNames">{names}</div>'
        f'<div class="psMeta mut">as of {_esc(str(asof)[:10] if asof else "—")} · '
        f'<a class="row" href="{_esc(row.get("route") or "#")}">open →</a></div>'
        '</div>')


def _strategy_flow(conn, key: str = "all") -> str:
    key = (key or "all").strip().lower()
    out = ['<a class="patBack" href="/dash/pat">← back</a>']
    try:
        from src.automation import strategy_registry as REG
        rows = REG.summary(conn) if conn is not None else []
    except Exception:
        rows = []
    if not rows:
        out.append(_q_bubble("The strategy board reads each strategy's current state from the "
                             "precomputed tables."))
        out.append('<div class="empty">No strategy data available on this host yet.</div>')
        return "".join(out)
    if key != "all":
        sel = [r for r in rows if (r.get("key") or "").lower() == key
               or (r.get("route") or "").rstrip("/").endswith("/" + key)]
        if sel:
            lbl = sel[0].get("label") or key
            out.append(_q_bubble(f"<b>{_esc(lbl)}</b> — its current read from the strategy "
                                 "registry (count, freshness, top names). Descriptive; open "
                                 "the deep page for the full board."))
            out.append('<div class="patStratWrap">' + "".join(_strategy_card(r) for r in sel) + '</div>')
            return "".join(out)
        out.append(_q_bubble(f'I don\'t have a “{_esc(key)}” strategy — here is the whole board:'))
    else:
        out.append(_q_bubble("The STRATEGIST board — every strategy's current read at a glance "
                             "(count · freshness · top names). Descriptive; click any to open "
                             "its deep page."))
    out.append('<div class="patStratWrap">' + "".join(_strategy_card(r) for r in rows) + '</div>')
    out.append('<div class="patChips">' + _chip("/dash/strategist", "full strategist board →") + "</div>")
    return "".join(out)


# ── compare two stocks side by side (A vs B) ──────────────────────────────────
def _compare_flow(conn, syms: str = "") -> str:
    toks = [t.strip() for t in (syms or "").replace(" ", ",").split(",") if t.strip()][:3]
    out = ['<a class="patBack" href="/dash/pat">← back</a>']
    if len(toks) < 2:
        out.append(_q_bubble("Name two stocks to compare, e.g. “compare INFY and TCS”."))
        return "".join(out)
    if conn is None:
        out.append(_q_bubble("Connect to data to compare."))
        return "".join(out)
    resolved = []
    for tok in toks:
        try:
            rsql, rparams = build_symbol_resolve_query(tok)
            hit = conn.execute(rsql, rparams).fetchone()
        except Exception:
            hit = None
        if hit:
            resolved.append(hit["symbol"])
    resolved = list(dict.fromkeys(resolved))   # dedupe, keep order
    if len(resolved) < 2:
        out.append(_q_bubble(f'I could resolve {len(resolved)} of those tickers. '
                             'Check the symbols and try again.'))
        return "".join(out)
    out.append(_q_bubble("Side by side — latest signals, relative strength, character and "
                         "fundamentals for each. Descriptive facts, not a recommendation:"))
    cards = []
    for sym in resolved:
        try:
            csql, cparams = build_stock_card_query(sym)
            row = conn.execute(csql, cparams).fetchone()
            psql, pparams = build_stock_pattern_query(sym)
            prow = conn.execute(psql, pparams).fetchone()
        except Exception:
            row, prow = None, None
        inner = _stock_card(row, prow) if row else f'<div class="empty">No data for {_esc(sym)}.</div>'
        cards.append(f'<div class="patCmpCol">{inner}</div>')
    out.append('<div class="patCmp">' + "".join(cards) + '</div>')
    return "".join(out)


# ── "why is X <metric>?" — drill into the evidence + provenance behind a read ──
def _why_url(sym: str, metric: str = "credibility") -> str:
    return f"/dash/pat?flow=why&sym={_u(sym)}" + (f"&strength={_u(metric)}" if metric else "")


def _prov(*bits) -> str:
    """A provenance footer: as-of + source, never fabricated."""
    return ('<div class="patMeta">' + "".join(f'<span>{_esc(b)}</span>' for b in bits if b)
            + '<span>descriptive evidence · not a recommendation</span></div>')


def _why_credibility(conn, sym: str) -> str:
    try:
        sql, params = build_credibility_detail_query(sym)
        r = conn.execute(sql, params).fetchone()
    except Exception:
        r = None
    if not r:
        return ('<div class="empty">No concall-credibility record for ' + _esc(sym) +
                ' — it may be outside the concall pilot (hundreds of names, not the full '
                'universe). Credibility is a DESCRIPTIVE track-record, not a buy signal.</div>'
                + _prov("coverage: concall pilot"))
    reasons = []
    cs = r["composite_score"]
    if cs is not None:
        reasons.append(f'composite credibility <b>{_n(cs,0)}/100</b>' +
                       (f' (tier {_esc(r["tier"])})' if r["tier"] else ''))
    if r["n_promises_resolved"] is not None:
        reasons.append(f'<b>{_int(r["n_promises_resolved"])}</b> guidance promises resolved'
                       + (f', {_pc(r["guidance_accuracy_score"])} kept' if r["guidance_accuracy_score"] is not None else ''))
    if r["quantification_rate"] is not None:
        reasons.append(f'guidance is {_pc(r["quantification_rate"])} quantified (falsifiable)')
    if r["credibility_trend"]:
        reasons.append(f'trend <b>{_esc((r["credibility_trend"] or "").title())}</b>')
    veto = bool(r["veto_active"])
    if veto:
        reasons.append(f'⛔ VETO active — {_esc(r["veto_reason"] or "a disqualifying flag")}')
    elif (r["deterioration_score"] or 0) > 0:
        reasons.append(f'⚠ deterioration flag ({_n(r["deterioration_score"],1)})')
    else:
        reasons.append('no veto / deterioration flag')
    facts = "".join([
        _fact("Composite", _n(cs, 0)),
        _fact("Credibility", _n(r["credibility_score"], 0)),
        _fact("Guidance acc", _pc(r["guidance_accuracy_score"])),
        _fact("Transparency", _n(r["transparency_score"], 0)),
        _fact("Quantified", _pc(r["quantification_rate"])),
        _fact("Promises n", _int(r["n_promises_resolved"])),
        _fact("Tier", _esc(r["tier"] or "—")),
        _fact("Trend", _esc((r["credibility_trend"] or "—").title())),
        _fact("Veto", "⛔ " + _esc(r["veto_reason"] or "active") if veto else "none"),
    ])
    # peer-relative context (concall_scores.peer_median) — value beside verdict
    pm = r["peer_median"] if "peer_median" in r.keys() else None
    if pm is not None and cs is not None:
        rel = "above" if cs > pm else ("below" if cs < pm else "at")
        reasons.append(f'{rel} the peer median ({_n(pm,0)}) on composite')
    verdict = ("reads CREDIBLE" if (not veto and (cs or 0) >= 55) else
               "reads WEAK / vetoed" if veto else "reads MIXED")
    body = (f'<div class="patWhyHd">{_esc(sym)} {verdict} — because:</div>'
            f'<ul class="patWhy">' + "".join(f"<li>{x}</li>" for x in reasons) + '</ul>'
            f'<div class="patFacts">{facts}</div>')
    # F3-4: drill into the UNDERLYING promise-vs-delivery rows (the receipts under the score)
    body += _why_credibility_evidence(conn, sym)
    return body + _prov(f"credibility as-of: {r['as_of_period'] or '—'}",
                        f"rank {_int(r['rank'])} of the pilot · {_int(r['n_concalls'])} concalls scored"
                        if ("rank" in r.keys()) else None,
                        "source: concall track-record (CCI pilot)")


_CLASS_CLS = {"BEAT": "pos", "IN_LINE": "mut", "UNDERSTATED": "pos",
              "MISS": "neg", "OVERSTATED": "neg", "CONCEALED": "neg"}
_CLASS_LBL = {"BEAT": "BEAT guidance", "IN_LINE": "in line", "UNDERSTATED": "under-promised",
              "MISS": "MISSED", "OVERSTATED": "over-promised", "CONCEALED": "concealed"}


def _why_credibility_evidence(conn, sym: str) -> str:
    """The actual promise-vs-delivery rows behind the guidance-accuracy score — the
    'drill into the underlying rows' the explanation should expose (F3-4). Descriptive."""
    try:
        sql, params = build_credibility_evidence_query(sym, 6)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    if not rows:
        return ""
    items = []
    for r in rows:
        cl = (r["classification"] or "").upper()
        cls = _CLASS_CLS.get(cl, "mut")
        lbl = _CLASS_LBL.get(cl, cl.title())
        what = (r["mgmt_expectation"] or "").strip() or (r["evidence"] or "").strip()
        what = what[:90] + ("…" if len(what) > 90 else "")
        metric = (r["metric"] or "").strip()
        items.append(
            '<li><span class="' + cls + '">' + _esc(lbl) + '</span> '
            + (f'<b>{_esc(metric)}</b> · ' if metric else '')
            + f'<span class="mut">{_esc(r["period_label"])}</span>'
            + (f' — {_esc(what)}' if what else '') + '</li>')
    return ('<div class="patWhyHd" style="margin-top:10px">The receipts — recent guidance '
            'vs. what actually happened:</div>'
            '<ul class="patWhy">' + "".join(items) + '</ul>')


def _why_from_card(conn, sym: str, metric: str) -> str:
    try:
        csql, cparams = build_stock_card_query(sym)
        r = conn.execute(csql, cparams).fetchone()
    except Exception:
        r = None
    if not r:
        return '<div class="empty">No signal row for ' + _esc(sym) + ' on the latest date.</div>'
    reasons, facts = [], ""
    if metric == "accumulation":
        ch = r["accum_character"] or "—"
        reasons.append(f'delivery character <b>{_esc(ch)}</b>')
        reasons.append(f'positioning p/r <b>{_int(r["p_score"])}/{_int(r["r_score"])}</b>'
                       + (' (active strong hand)' if (r["p_score"] or 0) > 0 else ''))
        if r["price_vs_hot_avg_pct"] is not None:
            reasons.append(f'price vs strong-hand cost: {_sgn(r["price_vs_hot_avg_pct"])}')
        facts = "".join([_fact("Character", _char_pill(r["accum_character"])),
                         _fact("p/r", f'{_int(r["p_score"])}/{_int(r["r_score"])}'),
                         _fact("Trigger", _rank_pill(r["trigger_rank"])),
                         _fact("Δ hot cost", _sgn(r["price_vs_hot_avg_pct"])),
                         _fact("Deliv ₹Cr", _cr(r["delivery_value_today"]))])
        verdict = ("is being ACCUMULATED" if (r["accum_character"] == "ACCUMULATION")
                   else "is under DISTRIBUTION" if (r["accum_character"] == "DISTRIBUTION")
                   else "is in CONSOLIDATION")
    elif metric == "rs":
        reasons.append(f'RS rank <b>{_int(r["rs_rank"])}/99</b> vs the broad market')
        if r["rs_vs_broad_trend_state"]:
            reasons.append(f'broad-RS trend <b>{_esc(r["rs_vs_broad_trend_state"])}</b>')
        if r["rs_vs_sector_trend_state"]:
            reasons.append(f'sector-RS trend <b>{_esc(r["rs_vs_sector_trend_state"])}</b>')
        if r["pct_from_52w_high"] is not None:
            reasons.append(f'{_sgn(r["pct_from_52w_high"])} from its 52-week high')
        facts = "".join([_fact("RS rank", _int(r["rs_rank"])),
                         _fact("Broad trend", _esc(r["rs_vs_broad_trend_state"] or "—")),
                         _fact("Sector trend", _esc(r["rs_vs_sector_trend_state"] or "—")),
                         _fact("% off 52wH", _sgn(r["pct_from_52w_high"]))])
        verdict = ("is an RS LEADER" if (r["rs_rank"] or 0) >= 80
                   else "is an RS LAGGARD" if (r["rs_rank"] or 99) <= 20 else "is MID-PACK on RS")
    else:  # valuation / quality
        reasons.append(f'P/E <b>{_n(r["pe"],1)}</b>, ROCE <b>{_pc(r["roce"])}</b>, ROE <b>{_pc(r["roe"])}</b>')
        if r["debt_to_equity"] is not None:
            reasons.append(f'D/E {_n(r["debt_to_equity"],2)}')
        if r["promoter_pledge"] is not None and r["promoter_pledge"] > 0:
            reasons.append(f'promoter pledge {_pc(r["promoter_pledge"])}')
        facts = "".join([_fact("P/E", _n(r["pe"], 1)), _fact("ROCE", _pc(r["roce"])),
                         _fact("ROE", _pc(r["roe"])), _fact("D/E", _n(r["debt_to_equity"], 2)),
                         _fact("Promoter", _pc(r["promoter_holding"])),
                         _fact("Mcap ₹Cr", _n(r["market_cap_cr"], 0))])
        if metric == "valuation":
            verdict = ("looks EXPENSIVE" if (r["pe"] or 0) > 40 else
                       "looks CHEAP" if (r["pe"] or 1e9) < 18 else "is FAIRLY VALUED")
        else:
            verdict = ("is HIGH quality" if (r["roce"] or 0) >= 18 else "is MODEST quality")
    body = (f'<div class="patWhyHd">{_esc(sym)} {verdict} — because:</div>'
            f'<ul class="patWhy">' + "".join(f"<li>{x}</li>" for x in reasons) + '</ul>'
            f'<div class="patFacts">{facts}</div>')
    src = ("source: cached Screener fundamentals" if metric in ("valuation", "quality")
           else "source: NSE daily delivery / RS signals")
    asof = "" if metric in ("valuation", "quality") else f"signals as-of: {_max_date(conn,'stock_signals','trade_date') or '—'}"
    return body + _prov(asof, src)


_WHY_LABEL = {"credibility": "credible", "accumulation": "being accumulated",
              "rs": "a market leader", "valuation": "cheap or expensive", "quality": "high-quality"}


def _why_flow(conn, sym: str, metric: str = "credibility") -> str:
    from src.pat.understand import WHY_METRICS
    metric = (metric or "credibility").strip().lower()
    if metric not in WHY_METRICS:
        metric = "credibility"
    out = ['<a class="patBack" href="/dash/pat">← back</a>']
    if not sym:
        out.append(_q_bubble("Name a stock — e.g. “why is INFY credible?”"))
        return "".join(out)
    if conn is None:
        out.append(_q_bubble("Connect to data to explain."))
        return "".join(out)
    try:
        rsql, rparams = build_symbol_resolve_query(sym)
        hit = conn.execute(rsql, rparams).fetchone()
    except Exception:
        hit = None
    if not hit:
        out.append(_q_bubble(f'I couldn\'t resolve “{_esc(sym)}”. Check the symbol.'))
        return "".join(out)
    sym = hit["symbol"]
    out.append(_q_bubble(f'Why {_esc(sym)} reads {_WHY_LABEL.get(metric, metric)} — the EVIDENCE '
                         'behind the read, drilled to the underlying rows + provenance. '
                         'Switch lens:'))
    out.append('<div class="patChips">' + "".join(
        _chip_sel(_why_url(sym, m), m.title(), m == metric) for m in
        ("credibility", "accumulation", "rs", "valuation", "quality")) + '</div>')
    out.append(_why_credibility(conn, sym) if metric == "credibility"
               else _why_from_card(conn, sym, metric))
    out.append('<div class="patChips">'
               + _chip(f"/dash/stock?sym={_u(sym)}", f"full {sym} dossier →")
               + (_chip(f"/dash/pat?flow=trend&sym={_u(sym)}", "credibility trend →")
                  if metric == "credibility" else "")
               + _chip(_why_url(sym, "credibility"), "why credible?") + "</div>")
    return "".join(out)


# ── credibility TIME-SERIES ("credibility trend for X") over credibility_series ─
# A descriptive PIT series: level + momentum + trend-state + tape, period by period.
# Never a buy signal (the §C falsification stands) — it shows HOW a management's
# credibility moved, with the as-of period range + n as provenance.
_TREND_STATE_CLS = {"IMPROVING": "pos", "DETERIORATING": "neg", "STABLE": "mut", "NEW": "mut"}


def _trend_state(s) -> str:
    s = (s or "").strip().upper()
    cls = _TREND_STATE_CLS.get(s, "mut")
    return f'<span class="{cls}">{_esc(s.title() or "—")}</span>' if s else '<span class="mut">—</span>'


def _trend_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Period</th><th>Credibility</th><th>Guid. acc.</th><th>Momentum</th>'
            '<th>3-period</th><th>Trend</th><th>Tier</th><th>Tape</th><th>n resolved</th>'
            '</tr></thead><tbody>')
    rws = []
    for r in rows:
        tape = (r["tape"] or "").replace("_", " ").title()
        tnote = r["tape_note"]
        tape_cell = (f'<span title="{_esc(tnote or "")}">{_esc(tape)}</span>'
                     if tape else '<span class="mut">—</span>')
        rws.append(
            '<tr>'
            f'<td class="sym">{_esc(r["period_label"])}</td>'
            f'<td>{_n(r["level"], 1)}</td>'
            f'<td>{_n(r["ga"], 1)}</td>'
            f'<td>{_sgnp(r["momentum"], 1)}</td>'
            f'<td>{_sgnp(r["momentum_3p"], 1)}</td>'
            f'<td>{_trend_state(r["trend"])}</td>'
            f'<td>{_esc(r["tier"] or "—")}</td>'
            f'<td class="mut">{tape_cell}</td>'
            f'<td>{_int(r["n_resolved"])}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _sgnp(v, d=1) -> str:
    """Signed value WITHOUT a percent sign (momentum is a points move, not a %)."""
    if v is None:
        return '<span class="mut">—</span>'
    cls = "pos" if v > 0 else ("neg" if v < 0 else "mut")
    return f'<span class="{cls}">{v:+.{d}f}</span>'


def _trend_flow(conn, sym: str) -> str:
    """The credibility TIME-SERIES for one name — level/momentum/trend over the PIT
    periods (credibility_series). Descriptive; carries its own period-range provenance."""
    out = ['<a class="patBack" href="/dash/pat">← back</a>']
    if not sym:
        out.append(_q_bubble("Name a stock — e.g. “credibility trend for NAVINFLUOR”."))
        return "".join(out)
    if conn is None:
        out.append(_q_bubble("Connect to data to chart the trend."))
        return "".join(out)
    try:
        rsql, rparams = build_symbol_resolve_query(sym)
        hit = conn.execute(rsql, rparams).fetchone()
    except Exception:
        hit = None
    if not hit:
        out.append(_q_bubble(f'I couldn\'t resolve “{_esc(sym)}”. Check the symbol.'))
        return "".join(out)
    sym = hit["symbol"]
    try:
        sql, params = build_credibility_trend_query(sym, 24)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    if not rows:
        out.append(_q_bubble(
            f'No credibility series for {_esc(sym)} yet — the concall pilot covers a few '
            'hundred names, not the whole market.'))
        out.append('<div class="patChips">'
                   + _chip("/dash/pat?flow=credibility", "credibility leaders →")
                   + _chip(f"/dash/stock?sym={_u(sym)}", f"{sym} dossier →") + "</div>")
        return "".join(out)
    latest, oldest = rows[0], rows[-1]
    out.append(_q_bubble(
        f'Credibility TREND for {_esc(sym)} — how the management\'s credibility has moved, '
        'period by period. The latest read is the top row; this is a descriptive series '
        '(evidence of consistency over time), not a buy signal.'))
    # the headline read of the move
    lat_trend = (latest["trend"] or "").title()
    out.append(
        f'<div class="ghdr">Latest: {_n(latest["level"], 1)} '
        f'(tier {_esc(latest["tier"] or "—")}, {_trend_state(latest["trend"])}) '
        f'— {len(rows)} periods, {_esc(oldest["period_label"])} → {_esc(latest["period_label"])}</div>')
    out.append(_trend_table(rows))
    # provenance footer (this flow carries its OWN as-of, not via _FRESH)
    out.append(
        '<div class="patMeta">'
        f'<span>as-of period: {_esc(latest["period_label"])}</span>'
        f'<span>series: {len(rows)} concall periods</span>'
        '<span>coverage: concall pilot · credibility_series · NOT the full universe</span>'
        '</div>')
    out.append('<div class="patChips">'
               + _chip(_why_url(sym, "credibility"), "why credible? (evidence) →")
               + _chip(f"/dash/stock?sym={_u(sym)}", f"full {sym} dossier →") + "</div>")
    return "".join(out)


# ── momentum oscillators (RSI / MACD over stock_oscillators, computed nightly) ─

def _osc_url(screen: str = "") -> str:
    # reuse the captured `strength` route param to carry the screen key.
    qs = ["flow=oscillators"]
    if screen:
        qs.append("strength=" + _u(screen))
    return "/dash/pat?" + "&".join(qs)


def _osc_table(rows) -> str:
    head = ('<div class="patTable"><table class="dt"><thead><tr>'
            '<th>Symbol</th><th>CMP</th><th>RSI 14</th><th>MACD</th><th>Signal</th>'
            '<th>Hist</th><th>RS</th><th>Sector</th></tr></thead><tbody>')
    rws = []
    for r in rows:
        rws.append(
            '<tr>'
            f'<td class="sym"><a class="row" href="/dash/stock?sym={_u(r["symbol"])}">{_esc(r["symbol"])}</a></td>'
            f'<td>{_n(r["cmp"])}</td>'
            f'<td>{_n(r["rsi_14"], 1)}</td>'
            f'<td>{_n(r["macd"], 2)}</td>'
            f'<td>{_n(r["macd_signal"], 2)}</td>'
            f'<td>{_sgn(r["macd_hist"], 2)}</td>'
            f'<td>{_int(r["rs_rank"])}</td>'
            f'<td class="mut">{_esc(r["primary_sector"] or "—")}</td>'
            '</tr>'
        )
    return head + "".join(rws) + '</tbody></table></div>'


def _oscillators_flow(conn, screen: str = "") -> str:
    from src.automation.oscillators import OSC_SCREEN, build_oscillators_query
    screen = (screen or "").strip().lower()
    if screen not in OSC_SCREEN:
        screen = "rsi_oversold"
    out = [
        '<a class="patBack" href="/dash/pat">← back</a>',
        _q_bubble("Momentum oscillators — RSI(14) + MACD(12,26,9), computed nightly off the "
                  "price archive. Pick a screen:"),
        '<div class="ghdr">Screen</div><div class="patChips">',
    ]
    for key, (lbl, _w, _o) in OSC_SCREEN.items():
        out.append(_chip_sel(_osc_url(key), lbl, key == screen))
    out.append('</div>')
    if conn is None:
        out.append('<div class="empty">Connect to data to see matches.</div>')
        return "".join(out)
    try:
        sql, params = build_oscillators_query(screen)
        rows = list(conn.execute(sql, params))
    except Exception:
        rows = []
    lbl = OSC_SCREEN.get(screen, OSC_SCREEN["rsi_oversold"])[0]
    out.append(f'<div class="ghdr">{_esc(lbl)} ({len(rows)})</div>')
    out.append(_osc_table(rows) if rows
               else '<div class="empty">No names match this screen right now.</div>')
    return "".join(out)


# ── single-stock snapshot / red-flag card (a different shape: one symbol) ─────

def _fact(label: str, value: str) -> str:
    return f'<div class="patFact"><span class="fl">{_esc(label)}</span><span class="fv">{value}</span></div>'


def _stock_card(row, prow) -> str:
    sym = row["symbol"]
    # Red-flag synthesis — the "what's wrong with X" read, value beside verdict.
    flags = []
    if (row["accum_character"] or "") == "DISTRIBUTION":
        flags.append("Under distribution — the strong hand looks to be EXITING.")
    rsr = row["rs_rank"]
    if rsr is not None and rsr <= 20:
        flags.append(f"Weak relative strength (RS {int(rsr)}/99) — lagging the market.")
    de = row["debt_to_equity"]
    if de is not None and de > 1.5:
        flags.append(f"High leverage (D/E {de:.2f}).")
    pl = row["promoter_pledge"]
    if pl is not None and pl > 5:
        flags.append(f"Promoter pledge {pl:.0f}%.")
    if prow and prow["hard_disqualified"]:
        flags.append("pt14 HARD-DISQUALIFIED: " + _esc(prow["disqualifier_reasons"] or "a fatal pattern") + ".")
    # Positives — the "reads well" side.
    good = []
    if (row["accum_character"] or "") == "ACCUMULATION":
        good.append("Reading accumulation (strong-hand buying).")
    if rsr is not None and rsr >= 80:
        good.append(f"RS leader (RS {int(rsr)}/99).")
    rc = row["roce"]
    if rc is not None and rc >= 18:
        good.append(f"High ROCE ({rc:.0f}%).")

    head = (f'<div class="patCardHd"><span class="pcSym">{_esc(sym)}</span>'
            f'<span class="pcSec">{_esc(row["primary_sector"] or "—")}</span>'
            f'<span class="pcCmp">₹{_n(row["cmp"])}</span></div>')
    tier = prow["tier"] if prow else None
    facts = "".join([
        _fact("RS rank", _int(rsr)),
        _fact("Character", _char_pill(row["accum_character"])),
        _fact("Trigger", _rank_pill(row["trigger_rank"])),
        _fact("p/r", f'{_int(row["p_score"])}/{_int(row["r_score"])}'),
        _fact("pt14 tier", _esc(tier or "—")),
        _fact("% off 52wH", _sgn(row["pct_from_52w_high"])),
        _fact("Δ hot cost", _sgn(row["price_vs_hot_avg_pct"])),
        _fact("P/E", _n(row["pe"], 1)),
        _fact("ROCE", _pc(row["roce"])),
        _fact("ROE", _pc(row["roe"])),
        _fact("D/E", _n(row["debt_to_equity"], 2)),
        _fact("Promoter", _pc(row["promoter_holding"])),
        _fact("Pledge", _pc(row["promoter_pledge"])),
        _fact("Profit 5Y", _pc(row["profit_growth_5y"])),
        _fact("Div yield", _pc(row["dividend_yield"])),
        _fact("MCap ₹Cr", _n(row["market_cap_cr"], 0)),
    ])
    flag_html = ''
    if flags:
        flag_html = ('<div class="patFlag patFlagBad"><b>Red flags</b><ul>'
                     + "".join(f'<li>{f}</li>' for f in flags) + '</ul></div>')
    good_html = ''
    if good:
        good_html = ('<div class="patFlag patFlagOk"><b>Reads well</b><ul>'
                     + "".join(f'<li>{_esc(g)}</li>' for g in good) + '</ul></div>')
    more = (f'<div class="patChips"><a class="patChip" href="/dash/stock?sym={_u(sym)}">'
            'Full stock page <span class="ar">→</span></a></div>')
    return ('<div class="card">' + head + '<div class="patFacts">' + facts + '</div>'
            + flag_html + good_html + more + '</div>')


def _stock_flow(conn, sym: str) -> str:
    token = (sym or "").strip()
    out = ['<a class="patBack" href="/dash/pat">← back</a>']
    if not token:
        out.append(_q_bubble("Which stock? Type a name or symbol — e.g. RELIANCE, INFY."))
        return "".join(out)
    if conn is None:
        out.append('<div class="empty">Connect to data to see the stock.</div>')
        return "".join(out)
    try:
        rsql, rparams = build_symbol_resolve_query(token)
        cands = list(conn.execute(rsql, rparams))
    except Exception:
        cands = []
    if not cands:
        out.append(_q_bubble(f'No NSE stock matches "{token}". Try the exact symbol (e.g. RELIANCE, INFY).'))
        return "".join(out)
    exact = [c for c in cands if (c["symbol"] or "").upper() == token.upper()]
    if len(cands) > 1 and not exact:
        out.append(_q_bubble("Did you mean one of these?"))
        out.append('<div class="patChips">')
        for c in cands:
            lbl = f'{c["symbol"]} — {c["company_name"] or ""}'.strip(" —")
            out.append(_chip(f"/dash/pat?flow=stock&sym={_u(c['symbol'])}", lbl))
        out.append('</div>')
        return "".join(out)
    symbol = (exact[0] if exact else cands[0])["symbol"]
    try:
        csql, cparams = build_stock_card_query(symbol)
        crow = conn.execute(csql, cparams).fetchone()
    except Exception:
        crow = None
    if crow is None:
        out.append(_q_bubble(f'{_esc(symbol)} is listed but has no recent signals row yet.'))
        return "".join(out)
    try:
        psql, pparams = build_stock_pattern_query(symbol)
        prow = conn.execute(psql, pparams).fetchone()
    except Exception:
        prow = None
    out.append(_q_bubble(f'{_esc(symbol)} — snapshot & red-flag read (value beside verdict):'))
    out.append(_stock_card(crow, prow))
    return "".join(out)


# Strategy-organized example questions — the "clues" that teach what Pat can be
# asked. Each is real free-text routed through the engine, so tapping one both
# answers AND shows the user the shape of question that works.
_EXAMPLES = [
    ("Today's market", [
        "biggest movers today", "top losers today", "most active stocks today"]),
    ("Momentum — relative strength", [
        "strongest stocks in the market over the last month",
        "RS leaders in IT", "strong-in-strong names this year"]),
    ("Indices & sectors", [
        "worst performing index over the last year that started turning up",
        "best performing sectoral index this month",
        "which sectors are leading over 3 months"]),
    ("Strong-hand delivery (DVPT)", [
        "stocks being accumulated now", "SS-rank names near a discount entry",
        "is the strong hand distributing near the highs"]),
    ("Quality & value", [
        "quality compounders", "cheap stocks with ROCE above 20",
        "debt-free names growing over 20%", "quality banks ranked by ROE"]),
    ("Management credibility (concalls)", [
        "credible managements", "why is NAVINFLUOR credible",
        "credibility trend for NAVINFLUOR", "managements with deteriorating credibility"]),
    ("Learn the metrics", [
        "what is p_score", "explain DVPT", "what does RS rank mean"]),
]


def _boards_home() -> str:
    """Saved boards as quick-load chips (server-rendered) — the multi-turn/workbench
    bridge: a pinned NL query reloads its answer. Empty → nothing rendered."""
    try:
        from src.pat import boards as B
        items = B.list_boards(kind="pat", limit=24)
    except Exception:
        items = []
    if not items:
        return ""
    chips = []
    for b in items:
        href = ("/dash/pat?q=" + _u(b["query"])) if b.get("query") else \
               ("/dash/pat?flow=" + _u(b.get("flow") or ""))
        chips.append(_chip(href, "★ " + b["name"]))
    return ('<div class="ghdr">Your saved boards</div><div class="patChips">'
            + "".join(chips) + '<a class="patChip" href="/dash/pat?flow=boards">manage boards →</a>'
            + '<a class="patChip" href="/dash/strategist">open workbench →</a></div>')


def _board_href(b: dict) -> str:
    """Where a saved board reopens to: its NL query (preferred), else flow + params."""
    if b.get("query"):
        return "/dash/pat?q=" + _u(b["query"])
    flow = b.get("flow") or ""
    if not flow:
        return "/dash/pat"
    qs = ["flow=" + _u(flow)]
    # carry the saved params back through the same generic route params the answer used
    p = b.get("params") or {}
    for k in ("sym", "strength", "entry", "align", "val", "sector"):
        if p.get(k):
            qs.append(f"{k}=" + _u(p[k]))
    return "/dash/pat?" + "&".join(qs)


def _boards_flow() -> str:
    """The dedicated saved-boards MANAGER (flow=boards): list every pinned NL board,
    one-click reopen, one-click delete. The list/reopen surface the Home chips only
    teased. Server-rendered; delete is a fetch POST to /pat/board/delete."""
    try:
        from src.pat import boards as B
        items = B.list_boards(kind="pat", limit=120)
    except Exception:
        items = []
    out = ['<a class="patBack" href="/dash/pat">← back</a>',
           _q_bubble("Your saved boards — every NL question you pinned. Reopen reruns the "
                     "same answer (always against the latest data); delete removes the pin.")]
    if not items:
        out.append('<div class="empty">No saved boards yet. Run any question, then '
                   '“★ Save as board” on the answer to pin it here.</div>')
        return "".join(out)
    rows = []
    for b in items:
        href = _board_href(b)
        flow_lbl = _FLOW_LABEL.get(b.get("flow") or "", b.get("flow") or "—")
        sub = _esc(b.get("query") or flow_lbl)
        rows.append(
            '<div class="patBoardRow">'
            f'<a class="patBoardOpen" href="{_esc(href)}">★ {_esc(b["name"])}'
            f'<span class="patBoardSub">{sub}</span></a>'
            f'<button type="button" class="patBoardDel" data-name="{_esc(b["name"])}" '
            'onclick="patDelBoard(this)">delete</button>'
            '</div>')
    out.append('<div class="patBoardList">' + "".join(rows) + '</div>')
    out.append(
        '<script>if(!window.patDelBoard){window.patDelBoard=function(b){'
        'var n=b.getAttribute("data-name");if(!n)return;'
        'if(!confirm("Delete board: "+n+"?"))return;'
        'fetch("/pat/board/delete",{method:"POST",headers:{"Content-Type":"application/json"},'
        'body:JSON.stringify({name:n,kind:"pat"})})'
        '.then(function(r){return r.json();}).then(function(j){'
        'if(j.ok){var row=b.closest(".patBoardRow");if(row)row.remove();}'
        'else{b.textContent="failed";}})'
        '.catch(function(){b.textContent="failed";});};}</script>')
    out.append('<div class="patChips"><a class="patChip" href="/dash/strategist">'
               'open the workbench →</a></div>')
    return "".join(out)


def _home() -> str:
    out = [
        '<form class="search" action="/dash/pat" method="get" autocomplete="off">'
        '<input name="q" placeholder="ask anything — e.g. strongest IT stocks over the last month"/>'
        '<button>Ask</button></form>',
        _q_bubble("Ask me anything in plain English. Not sure what to ask? Tap an "
                  "example — these are the kinds of questions I can answer:"),
        _boards_home(),
    ]
    for grp, qs in _EXAMPLES:
        out.append(f'<div class="ghdr">{grp}</div><div class="patChips">')
        for q in qs:
            out.append(_chip("/dash/pat?q=" + _u(q), q))
        out.append('</div>')
    out.append('<div class="ghdr">Or open a screen directly</div><div class="patChips">')
    for href, lbl in [("/dash/pat?flow=movers", "Today's movers"),
                      ("/dash/pat?flow=accumulation", "Accumulation"),
                      ("/dash/pat?flow=distribution", "Distribution"),
                      ("/dash/pat?flow=rs", "RS leaders"),
                      ("/dash/pat?flow=rslag", "Weak / laggards"),
                      ("/dash/pat?flow=index", "Index performance"),
                      ("/dash/pat?flow=fundamentals", "Fundamentals"),
                      ("/dash/pat?flow=pt14", "pt14 quality"),
                      ("/dash/pat?flow=redflags", "Kill-list"),
                      ("/dash/pat?flow=explain", "Explain a metric")]:
        out.append(_chip(href, lbl, arrow=True))
    out.append('</div>')
    return "".join(out)


# ── multi-turn conversation: context-aware follow-up chips + a refine box ──────
# A refinement is expressed as a self-contained COMBINED query the planner already
# intersects (no server thread state, no dashboard.py token plumbing): each chip /
# the refine box navigates to /dash/pat?q=<context + added-condition>. The chain of
# combined queries IS the conversation.
# flow -> a base NL phrase that re-states the current read (for the flow= path,
# where there's no original q to carry forward).
_FLOW_BASE_Q = {
    "rs": "RS leaders", "rslag": "weak laggard stocks",
    "accumulation": "stocks being accumulated", "fundamentals": "quality value stocks",
    "credibility": "credible companies", "deterioration": "managements with deteriorating credibility",
    "confluence": "credible companies being accumulated", "movers": "biggest movers today",
    "index": "best performing sectoral indices", "oscillators": "oversold stocks",
    "pt14": "pt14 quality tier stocks", "confluence_plan": "",
}
# flow -> the refinement chips to offer (label, the phrase to APPEND to the context).
_FOLLOWUPS = {
    "rs": [("↳ being accumulated", "that are being accumulated"),
           ("↳ credible ones", "with credible management"),
           ("↳ small-caps", "small caps")],
    "accumulation": [("↳ RS-leading", "that are RS-leading"),
                     ("↳ credible ones", "with credible management"),
                     ("↳ small-caps", "small caps")],
    "credibility": [("↳ being accumulated", "being accumulated"),
                    ("↳ RS-leading", "that are RS-leading"),
                    ("↳ small-caps", "small caps")],
    "fundamentals": [("↳ being accumulated", "being accumulated"),
                     ("↳ RS-leading", "that are RS-leading")],
    "confluence": [("↳ small-caps", "small caps"),
                   ("↳ mid-caps", "mid caps")],
    "confluence_plan": [("↳ small-caps", "small caps"),
                        ("↳ large-caps", "large caps")],
    "movers": [("↳ this week", "this week")],
}


def _followups(flow: str, q: str = "") -> str:
    """Context-aware refinement chips (the multi-turn UX): each is a one-click combined
    query that ADDS a condition to the current read — the planner intersects it."""
    specs = _FOLLOWUPS.get(flow)
    if not specs:
        return ""
    base = (q or "").strip() or _FLOW_BASE_Q.get(flow, "")
    if not base:
        return ""
    chips = []
    for label, add in specs:
        combined = f"{base} {add}".strip()
        chips.append(f'<a class="patChip patFup" href="/dash/pat?q={_u(combined)}">{_esc(label)}</a>')
    return ('<div class="patFupWrap"><span class="patFupLbl">Refine ↳</span>'
            '<div class="patChips">' + "".join(chips) + '</div></div>')


def _refine_box(ctx: str) -> str:
    """A free-text follow-up box: combines the typed refinement with the current
    context client-side, then asks Pat. ctx travels in the DOM (no server state)."""
    cattr = _esc(ctx or "")
    return (
        '<form class="patRefine" onsubmit="return patRefineGo(this)">'
        f'<input type="hidden" name="ctx" value="{cattr}"/>'
        '<input name="add" autocomplete="off" placeholder="…refine — e.g. only small-caps, in IT, that are credible"/>'
        '<button>Ask ↳</button></form>'
        '<script>if(!window.patRefineGo){window.patRefineGo=function(f){'
        'var ctx=(f.ctx.value||"").trim(),add=(f.add.value||"").trim();if(!add)return false;'
        'var q=ctx?(ctx+" "+add):add;location.href="/dash/pat?q="+encodeURIComponent(q);return false;};}</script>')


def _save_board_btn(q: str, flow: str, params: dict | None = None) -> str:
    """A '★ Save as board' button — prompts a name, POSTs to /pat/board/save (fetch).
    Stores the NL query + flow + params so the board reloads the same answer."""
    import json as _json
    pj = ""
    try:
        pj = _esc(_json.dumps(params or {}, separators=(",", ":"), ensure_ascii=False))
    except Exception:
        pj = "{}"
    return (
        f'<button type="button" class="patBoardBtn" data-q="{_esc(q)}" data-flow="{_esc(flow)}" '
        f'data-params="{pj}" onclick="patSaveBoard(this)">★ Save as board</button>'
        '<script>if(!window.patSaveBoard){window.patSaveBoard=function(b){'
        'var n=prompt("Name this board:");if(!n)return;'
        'var p={};try{p=JSON.parse(b.getAttribute("data-params")||"{}");}catch(e){}'
        'fetch("/pat/board/save",{method:"POST",headers:{"Content-Type":"application/json"},'
        'body:JSON.stringify({name:n,query:b.getAttribute("data-q")||"",'
        'flow:b.getAttribute("data-flow")||"",params:p,kind:"pat"})})'
        '.then(function(r){return r.json();}).then(function(j){'
        'b.textContent=j.ok?("★ Saved: "+n):"save failed";b.disabled=!!j.ok;})'
        '.catch(function(){b.textContent="save failed";});};}</script>')


# For a SINGLE-NAME answer (card / why / trend), the natural next questions are the
# OTHER lenses on the same name — proactive analyst follow-ups. With multi-turn live
# these are one click; even without a thread they carry the name explicitly.
_SUBJECT_NEXT = {
    "card":  [("↳ is it credible?", "is {S} credible"),
              ("↳ being accumulated?", "why is {S} being accumulated"),
              ("↳ RS / leadership", "why is {S} a leader"),
              ("↳ credibility trend", "credibility trend for {S}")],
    "why":   [("↳ credibility trend", "credibility trend for {S}"),
              ("↳ being accumulated?", "why is {S} being accumulated"),
              ("↳ full dossier", "tell me about {S}")],
    "trend": [("↳ why credible? (evidence)", "why is {S} credible"),
              ("↳ being accumulated?", "why is {S} being accumulated"),
              ("↳ full dossier", "tell me about {S}")],
}


def _subject_followups(flow: str, sym: str) -> str:
    """Proactive 'next question' chips for a single-name answer — the other lenses on
    the same name. '' if the flow has no subject map or no symbol."""
    specs = _SUBJECT_NEXT.get(flow)
    if not specs or not sym:
        return ""
    chips = []
    for label, tmpl in specs:
        nxt = tmpl.format(S=sym)
        chips.append(f'<a class="patChip patFup" href="/dash/pat?q={_u(nxt)}">{_esc(label)}</a>')
    return ('<div class="patFupWrap"><span class="patFupLbl">Ask next ↳</span>'
            '<div class="patChips">' + "".join(chips) + '</div></div>')


def _convo_tail(flow: str, q: str = "", ctx: str = "", params: dict | None = None,
                sym: str = "") -> str:
    """The conversation tail on a data answer: refine chips + refine box + save-board.
    For single-name flows, lead with proactive 'ask next' lens chips on the name."""
    sf = _subject_followups(flow, sym) if sym else ""
    fu = _followups(flow, q)
    rb = _refine_box(ctx or q or _FLOW_BASE_Q.get(flow, ""))
    sb = ('<div class="patSaveRow">'
          + _save_board_btn(q or _FLOW_BASE_Q.get(flow, ""), flow, params) + '</div>')
    return sf + fu + rb + sb


_FLOW_LABEL = {"accumulation": "Accumulation setups", "rs": "RS leaders",
               "fundamentals": "Screen by fundamentals", "movers": "Today's movers",
               "index": "Index performance", "distribution": "Distribution (strong hand exiting)",
               "consolidation": "Consolidation", "rslag": "Weak / laggard stocks",
               "pt14": "pt14 quality tiers", "redflags": "The kill-list (disqualified)",
               "stock": "Stock snapshot",
               # canonical contract aliases (route_extra/eval_set names → same views)
               "disqualified": "The kill-list (disqualified)", "card": "Stock snapshot",
               "oscillators": "Momentum (RSI / MACD)",
               "credibility": "Credibility leaders (CCI)",
               "deterioration": "Deterioration / avoid tape (CCI)",
               "confluence": "Credibility × accumulation",
               "confluence_plan": "Multi-condition confluence",
               "strategy": "Strategy board", "compare": "Compare stocks",
               "why": "Why — the evidence", "trend": "Credibility trend (time-series)"}


def _clarify_view(q: str, sel: dict) -> str:
    """Render a clarify-before-guess turn: the question + suggested-answer chips
    (each a concrete deterministic re-run) + a rephrase box. No feedback bar — this
    is a question, not an answer yet. Honors §4.5: ask ONE thing, don't guess."""
    chips = []
    for c in (sel.get("chips") or []):
        href, label = c.get("href"), c.get("label")
        if href and label:
            chips.append(f'<a class="patChip" href="{_esc(href)}">{_esc(label)}'
                         ' <span class="ar">→</span></a>')
    search = (
        '<form class="search" action="/dash/pat" method="get" autocomplete="off">'
        f'<input name="q" value="{_esc(q)}" placeholder="…or just rephrase your question"/>'
        '<button>Ask</button></form>'
    )
    question = sel.get("question") or "Could you clarify what you mean?"
    return (_q_bubble(question)
            + (f'<div class="patChips">{"".join(chips)}</div>' if chips else "")
            + search)


# ── §9.8 freshness + coverage header (on every data answer) ──────────────────
# Each data flow discloses its as-of date + the universe/coverage scope, so an
# answer never implies more freshness or breadth than it has (the trust contract:
# "render with caveat"). Table names are hardcoded (no user input → no injection).
# (flow -> (table | None, date_col | None, coverage note))
_FRESH = {
    "rs":            ("stock_signals", "trade_date", "NSE equities · daily relative-strength signals"),
    "rslag":         ("stock_signals", "trade_date", "NSE equities · daily relative-strength signals"),
    "accumulation":  ("stock_signals", "trade_date", "NSE equities · daily delivery / DVPT"),
    "distribution":  ("stock_signals", "trade_date", "NSE equities · daily delivery / DVPT"),
    "consolidation": ("stock_signals", "trade_date", "NSE equities · daily delivery / DVPT"),
    "card":          ("stock_signals", "trade_date", "single name · latest daily signals"),
    "movers":        ("bhavcopy_rows", "trade_date", "NSE cash · latest session"),
    "index":         ("index_signals", "trade_date", "NSE sectoral & thematic indices · daily"),
    "credibility":   ("concall_scores", "last_updated", "concall pilot · hundreds of names, NOT the full universe"),
    "deterioration": ("concall_scores", "last_updated", "concall pilot · veto + deterioration flags"),
    "fundamentals":  (None, None, "cached Screener snapshot · the surfaced set, not the whole market"),
    "pt14":          (None, None, "pt14 scored on demand for surfaced names"),
    "disqualified":  (None, None, "the hard-disqualifier kill-list"),
    "redflags":      (None, None, "the hard-disqualifier kill-list"),
    "oscillators":   (None, None, "RSI / MACD · computed nightly"),
    "compare":       ("stock_signals", "trade_date", "two names · latest daily signals + cached fundamentals"),
}


def _max_date(conn, table, col):
    try:
        return conn.execute(f"SELECT MAX({col}) FROM {table}").fetchone()[0]  # noqa: S608 (hardcoded names)
    except Exception:
        return None


def _freshness_bar(conn, flow: str) -> str:
    """The as-of + coverage badge for a flow. Confluence/planner/strategy carry their
    own as-of meta; explain/clarify/home have nothing to date → empty (never fabricated)."""
    if conn is None or flow in ("confluence", "confluence_plan", "strategy", "why", "trend"):
        return ""
    spec = _FRESH.get(flow)
    if not spec:
        return ""
    table, col, note = spec
    d = _max_date(conn, table, col) if table else None
    asof = f'<span>data as-of: {_esc(d)}</span>' if d else ''
    return f'<div class="patMeta">{asof}<span>coverage: {_esc(note)}</span></div>'


def _free_text(conn, q: str):
    """A typed question with no explicit flow → routed to a flow + chip params (via
    src.pat.engine); falls back to the deterministic glossary search if the engine
    declines or is unavailable.

    Returns ``(html, fb_ctx)`` where ``fb_ctx`` is the feedback context for a
    concrete answer (``{query, flow, params, source}``) or ``None`` when the view
    is a chooser/question (clarify, glossary search) that has nothing to rate yet.
    """
    sel = None
    try:
        from src.pat.engine import route as _route
        sel = _route(q, conn)
    except Exception:
        sel = None
    if sel and sel.get("flow"):
        f = sel["flow"]
        if f == "clarify":
            # Ambiguous ask → ONE short question + suggested-answer chips, no guess.
            return _clarify_view(q, sel), None
        if f == "explain" and sel.get("explain") and get(sel["explain"]):
            e = get(sel["explain"])
            html = (_q_bubble(f'I read "{q}" as →explain {e["term"]}.')
                    + _answer(sel["explain"], e))
            return html, {"query": q, "flow": "explain",
                          "params": {"explain": sel["explain"]}, "source": "free_text"}
        p = sel.get("params", {})
        body = None
        # Canonical contract (shared with eval_set.py): distribution/consolidation are
        # a `character` param on accumulation; laggards a `direction` param on rs;
        # the kill-list is `disqualified`; the single-stock view is `card`.
        if f == "accumulation":
            body = _accumulation_flow(conn, p.get("sector", ""), p.get("strength", ""),
                                      p.get("entry", ""), p.get("window", ""),
                                      character=p.get("character", ""), top_n=p.get("top_n"))
        elif f == "rs":
            if p.get("direction") == "laggards":
                body = _rslag_flow(conn, p.get("sector", ""), p.get("strength", ""), p.get("window", ""))
            else:
                body = _rs_flow(conn, p.get("sector", ""), p.get("strength", ""), p.get("align", ""),
                                p.get("window", ""), top_n=p.get("top_n"))
        elif f == "fundamentals":
            body = _fundamentals_flow(conn, p.get("val", ""), p.get("qual", ""), p.get("grow", ""),
                                      p.get("bs", ""), p.get("sector", ""), p.get("own", ""))
        elif f == "movers":
            body = _movers_flow(conn, p.get("direction", ""), p.get("liq", ""), p.get("window", ""))
        elif f == "index":
            body = _index_flow(conn, p.get("window", ""), p.get("direction", ""), p.get("turning", ""))
        elif f == "pt14":
            body = _pt14_flow(conn, p.get("tier", ""))
        elif f == "disqualified":
            body = _disqualified_flow(conn)
        elif f == "card":
            body = _stock_flow(conn, p.get("sym", ""))
        elif f == "oscillators":
            body = _oscillators_flow(conn, p.get("screen", ""))
        elif f == "credibility":
            body = _credibility_flow(conn, top_n=p.get("top_n"))
        elif f == "deterioration":
            body = _deterioration_flow(conn)
        elif f == "confluence":
            body = _confluence_flow(conn)
        elif f == "confluence_plan":
            body = _confluence_plan_flow(conn, p.get("pillars", ""), p.get("sector", ""),
                                         p.get("capband", ""))
        elif f == "strategy":
            body = _strategy_flow(conn, p.get("key", "all"))
        elif f == "compare":
            body = _compare_flow(conn, p.get("syms", ""))
        elif f == "why":
            body = _why_flow(conn, p.get("sym", ""), p.get("metric", "credibility"))
        if body is not None:
            body = body + _freshness_bar(conn, f)   # §9.8 freshness + coverage footer
            # single-name flows get proactive 'ask next' lens chips on the same name
            _sym = (p.get("sym") or "").strip() if f in ("card", "why", "trend") else ""
            body = body + _convo_tail(f, q=q, ctx=q, params=p, sym=_sym)
            note = _q_bubble(f'I read "{q}" as →{_FLOW_LABEL.get(f, f)}. Adjust with the chips below.')
            return note + body, {"query": q, "flow": f, "params": p, "source": "free_text"}
    # fallback — deterministic glossary keyword search (today's behavior). A chooser,
    # so no feedback bar (nothing concrete to rate); but offer a clarify nudge.
    return _explain_flow("", q), None


# ── true multi-turn: server-side thread trail (keyed by an optional `tid`) ─────
# The thread store (src.pat.threads) remembers the recent turns for a browser
# session. It is INERT unless the page route forwards a `tid` cookie into
# render_pat (the call-site plumb is the orchestrator's — see threads.py). When
# present, we (a) render a compact conversation trail above the answer so the
# analyst can see + jump back through the thread, and (b) record each concrete
# answer as a turn. The URL-combined refinement chips stay the primary path; the
# thread store is additive memory + a visible trail, never a behaviour change for
# tid="" (the default).

def _thread_trail(tid: str, current_flow: str = "") -> str:
    """A compact 'this conversation' strip from the thread history. '' if the
    thread has 0/1 turns (nothing to show) or threads are unavailable."""
    if not tid:
        return ""
    try:
        from src.pat import threads as _T
        hist = _T.history(tid)
    except Exception:
        hist = []
    # only worth showing once there's prior context (>=1 earlier turn besides now)
    if len(hist) < 2:
        return ""
    chips = []
    for h in hist:
        q = (h.get("query") or "").strip()
        flow = (h.get("flow") or "").strip()
        if q:
            href = "/dash/pat?q=" + _u(q)
            label = q if len(q) <= 48 else (q[:46] + "…")
        elif flow:
            href = "/dash/pat?flow=" + _u(flow)
            label = _FLOW_LABEL.get(flow, flow)
        else:
            continue
        chips.append(f'<a class="patTrailItem" href="{_esc(href)}">{_esc(label)}</a>')
    if len(chips) < 2:
        return ""
    return (
        '<div class="patTrail"><span class="patTrailLbl">This conversation</span>'
        '<div class="patTrailItems">' + '<span class="patTrailSep">›</span>'.join(chips) + '</div>'
        '<a class="patTrailNew" href="/dash/pat?new=1" title="Start a fresh conversation">'
        'start over ⟲</a></div>')


def _thread_record(tid: str, fb_ctx: dict | None) -> None:
    """Append the just-rendered concrete answer to the thread. No-op for tid='' or
    a non-answer (chooser/home). Never raises."""
    if not tid or not fb_ctx:
        return
    flow = fb_ctx.get("flow") or ""
    # don't record meta/chooser flows as conversation turns
    if flow in ("explain", "boards", "face", ""):
        if not (fb_ctx.get("query") or "").strip():
            return
    try:
        from src.pat import threads as _T
        _T.record(tid, query=fb_ctx.get("query") or "", flow=flow,
                  params=fb_ctx.get("params") or {})
    except Exception:
        pass


# ── in-thread CONTEXT resolution (Pat-as-analyst follow-ups) ──────────────────
# After "tell me about TITAN", a follow-up like "what about its credibility?" /
# "and the rotation?" / "is it being accumulated?" resolves the pronoun to TITAN
# from the thread and rewrites to an explicit query the router already serves. This
# is what turns single-shot answers into a conversation. INERT for tid="" (no
# thread) and for a query that already names a subject (no pronoun to bind).
import re as _re_wf

# a follow-up CONTINUATION: a bare/pronoun lens ask that only makes sense against a
# prior subject. (label-phrase regex, the explicit-query template). The {S} slot is
# filled with the resolved symbol. Order matters — first match wins.
_FOLLOWUP_LENS = [
    # trend (credibility OVER TIME) is more specific than a point credibility ask → first
    (_re_wf.compile(r"\b(credibility (trend|history|over time|trajectory)|"
                    r"trend (of|in) (its )?credib|over time)", _re_wf.I),
     "credibility trend for {S}"),
    (_re_wf.compile(r"\b(credib|trustworth|promise|guidance|concall track)", _re_wf.I),
     "is {S} credible"),
    # accumulation / RS / fundamentals about ONE name → the per-name WHY evidence
    # ("why is X being accumulated" routes to why(metric=accumulation)), NOT the
    # generic screen — so a single-name follow-up answers about THAT name.
    (_re_wf.compile(r"\b(being accumulat|accumulation|strong hand|smart money|delivery)", _re_wf.I),
     "why is {S} being accumulated"),
    (_re_wf.compile(r"\b(relative strength|\brs\b|leading|leader|momentum|outperform)", _re_wf.I),
     "why is {S} a leader"),
    (_re_wf.compile(r"\b(why)\b", _re_wf.I), "why is {S} credible"),
    (_re_wf.compile(r"\b(fundamental|valuation|cheap|expensive|quality|compounder)", _re_wf.I),
     "tell me about {S}"),
    (_re_wf.compile(r"\b(dossier|snapshot|overview|tell me|pull up|full picture)", _re_wf.I),
     "tell me about {S}"),
]
# the query must LOOK like a follow-up: a leading continuation ("what about", "and",
# "how about", "what's its") OR an explicit pronoun ("it"/"its"/"that company").
_FOLLOWUP_LEAD = _re_wf.compile(
    r"^\s*(what about|how about|and |what'?s its|whats its|what is its|"
    r"and its|& |also |then )", _re_wf.I)
_FOLLOWUP_PRONOUN = _re_wf.compile(
    r"\b(it|its|it'?s|that company|this company|that name|this one|the company|the stock)\b",
    _re_wf.I)
# guard: if the query already names a ticker-shaped token, it's not a pronoun ask.
_HAS_EXPLICIT_SYM = _re_wf.compile(r"\b[A-Z][A-Z0-9&.\-]{2,15}\b")


def _resolve_followup(q: str, tid: str):
    """If q is a context-dependent follow-up and the thread has a subject, return
    (rewritten_q, resolved_symbol); else (q, '') unchanged. ₹0, never raises."""
    if not tid or not q:
        return q, ""
    is_lead = bool(_FOLLOWUP_LEAD.search(q))
    has_pronoun = bool(_FOLLOWUP_PRONOUN.search(q))
    if not (is_lead or has_pronoun):
        return q, ""
    # if the analyst already typed a symbol, don't override it with the thread subject
    # (unless the only "uppercase token" is a stopword like RS — handled by len/guard).
    explicit = [m for m in _HAS_EXPLICIT_SYM.findall(q)
                if m not in ("RS", "MACD", "RSI", "CCI", "MEP", "CPR", "DVPT", "PE", "P", "Q")]
    if explicit:
        return q, ""
    try:
        from src.pat import threads as _T
        sym = _T.last_symbol(tid)
    except Exception:
        sym = ""
    if not sym:
        return q, ""
    for rx, tmpl in _FOLLOWUP_LENS:
        if rx.search(q):
            return tmpl.format(S=sym), sym
    # a bare "what about it?" with no lens → the dossier (the most informative default)
    if is_lead or has_pronoun:
        return f"tell me about {sym}", sym
    return q, ""


def render_pat(flow: str = "", explain: str = "", q: str = "",
               sector: str = "", strength: str = "", entry: str = "", align: str = "",
               val: str = "", qual: str = "", grow: str = "", bs: str = "", own: str = "",
               sym: str = "", conn=None, tid: str = "", new: str = "") -> str:
    """Build the inner HTML for /dash/pat from the chip params (+ optional DB conn).

    ``tid`` (optional) keys a server-side conversation thread for TRUE multi-turn —
    a trail of prior turns above the answer + per-answer memory. It is INERT until
    the page route forwards a `pat_tid` cookie (the orchestrator's one-line call-site
    plumb); render_pat is unchanged for the default tid="". ``new=1`` clears the
    thread (the 'start over' affordance) before rendering."""
    flow = (flow or "").strip().lower()
    explain = (explain or "").strip()
    q = (q or "").strip()
    sector = (sector or "").strip()
    strength = (strength or "").strip().lower()
    sym = (sym or "").strip()
    tid = (tid or "").strip().lower()

    # 'start over' — forget the thread before rendering (then carry on as a fresh page).
    if tid and str(new or "").strip() in ("1", "true", "yes"):
        try:
            from src.pat import threads as _T
            _T.clear(tid)
        except Exception:
            pass

    if flow == "face":                       # the dedicated face-picker page
        return _PAT_CSS + _face_picker()
    if flow == "boards":                     # the saved-boards manager (list/reopen/delete)
        return _PAT_CSS + _avatar_picker() + _boards_flow()

    # fb_ctx = the answer's context for the 👍/👎 bar, or None for non-answers
    # (home / face / metric chooser). Set per branch so the bar can log exactly
    # what was shown (the typed query, the routed flow, the chip params).
    fb_ctx = None
    if explain and get(explain):
        body = _explain_flow(explain, q)
        fb_ctx = {"query": q, "flow": "explain", "params": {"explain": explain}, "source": "explain"}
    elif flow == "explain":
        body = _explain_flow(explain, q)
    elif flow == "accumulation":
        entry = (entry or "").strip().lower()
        window = (align or "").strip().lower()   # accumulation window rides the `align` param
        body = _accumulation_flow(conn, sector, strength, entry, window)
        fb_ctx = {"query": "", "flow": "accumulation",
                  "params": {"sector": sector, "strength": strength, "entry": entry, "window": window},
                  "source": "flow"}
    elif flow == "rs":
        align = (align or "").strip().lower()
        window = (entry or "").strip().lower()
        body = _rs_flow(conn, sector, strength, align, window)
        fb_ctx = {"query": "", "flow": "rs",
                  "params": {"sector": sector, "strength": strength, "align": align, "window": window},
                  "source": "flow"}
    elif flow == "fundamentals":
        fp = {"val": (val or "").strip().lower(), "qual": (qual or "").strip().lower(),
              "grow": (grow or "").strip().lower(), "bs": (bs or "").strip().lower(),
              "sector": sector, "own": (own or "").strip().lower()}
        body = _fundamentals_flow(conn, fp["val"], fp["qual"], fp["grow"], fp["bs"], fp["sector"], fp["own"])
        fb_ctx = {"query": "", "flow": "fundamentals", "params": fp, "source": "flow"}
    elif flow == "movers":
        entry = (entry or "").strip().lower()
        window = (align or "").strip().lower()   # movers window rides the `align` param
        body = _movers_flow(conn, strength, entry, window)
        fb_ctx = {"query": "", "flow": "movers",
                  "params": {"direction": strength, "liq": entry, "window": window}, "source": "flow"}
    elif flow == "index":
        window = (entry or "").strip().lower()       # index params reuse: entry=window,
        direction = strength                          # strength=direction,
        turning = (align or "").strip().lower()       # align=turning
        body = _index_flow(conn, window, direction, turning)
        fb_ctx = {"query": "", "flow": "index",
                  "params": {"window": window, "direction": direction, "turning": turning},
                  "source": "flow"}
    elif flow in ("distribution", "consolidation"):
        entry = (entry or "").strip().lower()
        window = (align or "").strip().lower()       # character window also rides `align`
        body = _accumulation_flow(conn, sector, strength, entry, window, character=flow)
        fb_ctx = {"query": "", "flow": flow,
                  "params": {"sector": sector, "strength": strength, "entry": entry,
                             "window": window, "character": flow}, "source": "flow"}
    elif flow == "rslag":
        window = (entry or "").strip().lower()       # laggard window rides `entry` (like RS)
        body = _rslag_flow(conn, sector, strength, window)
        fb_ctx = {"query": "", "flow": "rslag",
                  "params": {"sector": sector, "strength": strength, "window": window},
                  "source": "flow"}
    elif flow == "pt14":
        body = _pt14_flow(conn, strength)            # the tier chip rides `strength`
        fb_ctx = {"query": "", "flow": "pt14", "params": {"tier": strength}, "source": "flow"}
    elif flow == "redflags":
        body = _disqualified_flow(conn)
        fb_ctx = {"query": "", "flow": "redflags", "params": {}, "source": "flow"}
    elif flow == "stock":
        body = _stock_flow(conn, sym)
        fb_ctx = {"query": "", "flow": "stock", "params": {"sym": sym}, "source": "flow"}
    elif flow == "oscillators":
        body = _oscillators_flow(conn, strength)     # the screen chip rides `strength`
        fb_ctx = {"query": "", "flow": "oscillators", "params": {"screen": strength}, "source": "flow"}
    elif flow == "credibility":
        body = _credibility_flow(conn)
        fb_ctx = {"query": "", "flow": "credibility", "params": {}, "source": "flow"}
    elif flow == "deterioration":
        body = _deterioration_flow(conn)
        fb_ctx = {"query": "", "flow": "deterioration", "params": {}, "source": "flow"}
    elif flow == "confluence":
        body = _confluence_flow(conn)
        fb_ctx = {"query": "", "flow": "confluence", "params": {}, "source": "flow"}
    elif flow == "confluence_plan":
        # planner params smuggled through forwarded generics: pillars=strength, capband=entry
        pillars = strength
        capband = (entry or "").strip().lower()
        body = _confluence_plan_flow(conn, pillars, sector, capband)
        fb_ctx = {"query": "", "flow": "confluence_plan",
                  "params": {"pillars": pillars, "sector": sector, "capband": capband},
                  "source": "flow"}
    elif flow == "strategy":
        body = _strategy_flow(conn, strength or "all")    # key rides `strength`
        fb_ctx = {"query": "", "flow": "strategy", "params": {"key": strength or "all"}, "source": "flow"}
    elif flow == "compare":
        body = _compare_flow(conn, sym)                   # "A,B" rides `sym`
        fb_ctx = {"query": "", "flow": "compare", "params": {"syms": sym}, "source": "flow"}
    elif flow == "why":
        body = _why_flow(conn, sym, strength or "credibility")   # metric rides `strength`
        fb_ctx = {"query": "", "flow": "why", "params": {"sym": sym, "metric": strength or "credibility"},
                  "source": "flow"}
    elif flow == "trend":
        body = _trend_flow(conn, sym)                     # credibility series; sym rides `sym`
        fb_ctx = {"query": "", "flow": "trend", "params": {"sym": sym}, "source": "flow"}
    elif q:
        # in-thread follow-up resolution (inert for tid=""). TWO kinds, in priority:
        #   (1) CONJUNCTIVE refine of a prior LIST ("…with credible management" after
        #       "strongest stocks") → rebuild the COMBINED query so the planner
        #       INTERSECTS the new pillar with the prior set (AND, not replace). This
        #       is the QA-round2 #5 fix.
        #   (2) PRONOUN follow-up on a single name ("its credibility") → bind to the
        #       thread subject and rewrite to an explicit query.
        resolved_sym = ""
        refined_combined = ""
        q2 = q
        if tid:
            try:
                from src.pat import threads as _Tr
                refined_combined = _Tr.refine_base(tid, q)
            except Exception:
                refined_combined = ""
            if refined_combined:
                q2 = refined_combined
            else:
                q2, resolved_sym = _resolve_followup(q, tid)
        body, fb_ctx = _free_text(conn, q2)
        # The refine must INTERSECT (AND), never silently replace the base set. If the
        # rebuilt combined query genuinely routed to a multi-pillar flow (the planner /
        # confluence), the intersection happened → show the "refining" bubble. If it did
        # NOT (the router collapsed it to a single pillar — see the deferred
        # disambiguate.route_extra / understand.validate_intent multi-pillar bug), DON'T
        # claim a refinement that didn't occur: fall back to the analyst's original bare
        # query so behaviour is exactly the prior status quo (no misleading bubble). This
        # call-site guard auto-activates the full intersection once that router fix lands.
        _refined_flow = (fb_ctx or {}).get("flow", "") if refined_combined else ""
        _did_intersect = _refined_flow in ("confluence_plan", "confluence")
        if refined_combined and q2 != q and _did_intersect:
            # the follow-up REFINED the running list (genuine pillar intersection); keep the
            # ORIGINAL phrasing in the thread record so the trail reads naturally.
            body = (_q_bubble(f'↳ refining your previous list — read as → "{q2}".') + body)
            if fb_ctx:
                fb_ctx["query"] = q
        elif refined_combined and q2 != q and not _did_intersect:
            # router did not intersect → re-route the analyst's ORIGINAL query, unmodified,
            # so we don't show a false "refining" claim over a replaced (non-AND) result.
            body, fb_ctx = _free_text(conn, q)
        elif resolved_sym and q2 != q:
            # show the analyst that the pronoun bound to the thread subject, and keep
            # the ORIGINAL phrasing in the thread record (so the trail reads naturally).
            body = (_q_bubble(f'↳ in this thread, I read "{q}" as → {resolved_sym}.') + body)
            if fb_ctx:
                fb_ctx["query"] = q
    else:
        body = _home()

    # §9.8 freshness + coverage footer on a direct flow= answer (the free-text path
    # adds its own inside _free_text; confluence/explain/clarify/home add nothing).
    if fb_ctx and fb_ctx.get("source") == "flow":
        _ff = fb_ctx.get("flow", "")
        body = body + _freshness_bar(conn, _ff)
        if _ff in _FOLLOWUPS:                       # multi-turn refine on flow= answers too
            body = body + _convo_tail(_ff, ctx=_FLOW_BASE_Q.get(_ff, ""),
                                      params=fb_ctx.get("params"))

    # true multi-turn: record this concrete answer as a thread turn, then prepend
    # the conversation trail (both no-ops for tid=""). Record BEFORE building the
    # trail so the current turn is part of the shown history.
    trail = ""
    if tid:
        _thread_record(tid, fb_ctx)
        trail = _thread_trail(tid, current_flow=(fb_ctx or {}).get("flow", ""))

    out = _PAT_CSS + _avatar_picker() + trail + body
    if fb_ctx is not None:
        out += _feedback_bar(**fb_ctx) + _FB_JS
    return out
