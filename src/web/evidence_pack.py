"""/dash/evidence-pack — the procurement evidence artifact, assembled live (charter P-04).

ONE print-ready document a diligence/procurement reader can be handed as a PDF: the
P-03 detection spec-sheets (verbatim — imported from spec_sheets, failures included),
the coverage/provenance boundary of every dataset (the two anchor sections + the
boundary statements imported from coverage_view), the live season service record
(filing→surface MTTR + the M-02 placebo readout), and the Replay-the-Tape pointer.
"PDF assembly" is deliberately the browser's own print engine (zero dependencies):
the site-wide ``@media print`` block in ui_tokens already flips the palette light,
strips the chrome, paginates tables and stamps the disclaimer footer — this module
only adds document-level page breaks and a screen-only print toolbar.

Honesty contract (D91 spirit): this page never invents a number. Every block is either
imported from the surface that owns it (spec_sheets._SHEETS / M05_BOX / NOTE_HTML,
coverage_view.COPY_* + section renderers over provenance.coverage_snapshot) or is a
pointer to the live route where the reader can re-derive it. The replay section
describes the demonstrator's mechanics and its two worked cases — it quotes no
returns (a trust artifact makes no performance claim).

House pattern: pure isolated APIRouter, one route, imports nothing mutable, mounted
by one line in v2_surfaces._ROUTER_SPECS + a Trust Lens record. Defensive throughout:
a missing DB, snapshot or sibling module degrades a section to its pointer — a trust
surface must never error.

Route: GET /dash/evidence-pack
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web import spec_sheets as SS

router = APIRouter()


def _shell_fallback(title, body, active="", latest_date="", wide=False):
    return ("<!doctype html><meta charset='utf-8'><title>" + title + "</title>"
            "<body style='background:var(--bg-1);color:var(--ink);font-family:system-ui;"
            "max-width:1100px;margin:0 auto;padding:24px'>" + body + "</body>")


try:
    from src.web.dashboard import _shell
except Exception:                                   # pragma: no cover
    _shell = _shell_fallback


def _esc(s):
    return html.escape(str(s), quote=True)


_CSS = """
<style>
.ep .ep-bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;border:1px solid var(--line-2);
  border-radius:10px;background:var(--bg-2);padding:10px 14px;margin:0 0 18px;font-size:12px;
  color:var(--ink-2);line-height:1.5}
.ep .ep-bar button{border:1px solid var(--accent);background:var(--accent-dim);color:var(--ink);
  border-radius:8px;padding:8px 15px;font-size:13px;font-weight:600;cursor:pointer}
.ep .ep-meta{font-size:12px;color:var(--ink-3);margin:2px 0 14px}
.ep .ep-sec{margin:26px 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--ink-2);border-bottom:1px solid var(--line-2);padding-bottom:5px}
.ep .vtable{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0 14px;max-width:880px}
.ep .vtable td{padding:5px 10px 5px 0;border-top:1px solid var(--bg-3);vertical-align:top;line-height:1.55}
.ep .vtable td:first-child{white-space:nowrap;font-family:var(--mono,monospace);font-size:12px}
.ep .bnd{max-width:880px;margin:0 0 12px;font-size:12.5px;line-height:1.65;color:var(--ink-2)}
.ep .bnd b.lbl{display:block;color:var(--ink);font-size:11px;text-transform:uppercase;
  letter-spacing:.06em;margin-bottom:2px}
.ep .muted-block{border-left:2px solid var(--line-2);padding:2px 0 2px 12px;margin:0 0 12px;
  color:var(--ink-3);font-size:12px;line-height:1.6;max-width:880px}
@media print{
  .ep .ep-bar{display:none!important}
  .ep .brk{break-before:page}
  .ep .sheet,.ep .live,.ep .bnd,.ep .muted-block{break-inside:avoid}
}
</style>"""


def _coverage_sections():
    """The two anchor sections + boundary prose from coverage_view; degrades to a pointer."""
    try:
        from src.web import coverage_view as CV
    except Exception:                               # noqa: BLE001
        return ('<div class="muted-block">The live coverage ledger is not available in this '
                'environment — the boundary of every dataset is stated at '
                '<a href="/dash/coverage">/dash/coverage</a> and its print memo '
                '<a href="/dash/coverage/memo">/dash/coverage/memo</a>.</div>')

    def _safe(fn, *a):
        try:
            return fn(*a)
        except Exception as e:                      # noqa: BLE001
            return f'<div class="muted-block">section unavailable: {_esc(e)}</div>'

    try:
        snap = CV.P.coverage_snapshot(None)
    except Exception:                               # noqa: BLE001
        snap = {}

    prose = "".join(
        f'<div class="bnd"><b class="lbl">{_esc(lbl)}</b>{_esc(txt)}</div>'
        for lbl, txt in [
            ("Availability dating", CV.COPY_MODELED),
            ("Universe & survivorship", CV.COPY_SURVIVORSHIP),
            ("Concall credibility", CV.COPY_CCI),
            ("Coverage selection (missing-not-at-random)", CV.COPY_MNAR),
            ("Sourcing", CV.COPY_SOURCE),
            ("Validation discipline", CV.COPY_VALIDATION),
        ])
    return (CV._COV_CSS
            + _safe(CV._section_glance, snap)
            + _safe(CV._section_matrix, snap)
            + prose
            + '<div class="muted-block">The full Coverage &amp; Provenance Memo — universe '
              'funnel, per-class coverage, CCI settlement, modeled-vs-filed dating, the '
              'provenance registry — is its own print artifact at '
              '<a href="/dash/coverage/memo">/dash/coverage/memo</a>; the live ledger is '
              '<a href="/dash/coverage">/dash/coverage</a>.</div>')


def _infra_copy():
    try:
        from src.web import coverage_view as CV
        return f'<div class="muted-block">{_esc(CV.COPY_INFRA)}</div>'
    except Exception:                               # noqa: BLE001
        return ""


def _framing_copy():
    """SEBI + no-performance-claim framing, verbatim from the coverage ledger."""
    try:
        from src.web import coverage_view as CV
        return (f'<div class="muted-block">{_esc(CV.COPY_NOALPHA)}</div>'
                f'<div class="muted-block">{_esc(CV.COPY_SEBI)}</div>')
    except Exception:                               # noqa: BLE001
        return ('<div class="muted-block">Descriptive research record, point-in-time; '
                'not investment advice or a recommendation.</div>')


_VERIFY_ROUTES = [
    ("/dash/spec-sheets", "the live detection spec-sheets — every pre-registered study, "
                          "gate hashes attached, failures included"),
    ("/dash/coverage", "the live coverage &amp; settlement ledger — the boundary of every "
                       "dataset, stated in writing (print memo: /dash/coverage/memo)"),
    ("/dash/testing", "strategy validation — every backtest net of realistic cost, the "
                      "failures kept as visible as the wins"),
    ("/dash/replay", "the zero-look-ahead demonstrator — scrub to a past date, see only "
                     "what was knowable, then reveal what followed"),
    ("/dash/glossary", "every custom metric and term on the site, defined"),
]


@router.get("/dash/evidence-pack", response_class=HTMLResponse)
def evidence_pack():
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    verify_rows = "".join(
        f'<tr><td><a href="{r}">{r}</a></td><td>{d}</td></tr>' for r, d in _VERIFY_ROUTES)

    body = [
        SS._CSS, _CSS, '<div class="sp ep">',

        # ── cover ──
        '<div class="ep-bar"><button onclick="window.print()">🖨 Print / save as PDF</button>'
        '<span>This page is the procurement artifact — your browser&#39;s print dialog '
        'produces the PDF (the palette flips light, the chrome is stripped and the pages '
        'are stamped automatically). Assembled live at request time; nothing is '
        'hand-curated for export.</span></div>',
        '<h2>patearn — Evidence Pack</h2>',
        f'<div class="ep-meta">generated <b class="num">{_esc(gen)}</b> · scope: NSE-listed '
        'Indian equities (EQ/BE/BZ; SME excluded) · descriptive evidence, point-in-time · '
        'not investment advice</div>',
        '<div class="lead">This pack assembles patearn&#39;s trust surfaces into one '
        'document: the <b>pre-registered detection spec-sheets</b> (failures published on '
        'purpose), the <b>coverage and provenance boundary</b> of every dataset behind the '
        'product, the <b>live season service record</b>, and the <b>point-in-time replay '
        'demonstrator</b>. Every number here is generated from the running system and can '
        'be re-derived at the routes below — the pack is a snapshot of pages that exist, '
        'not a brochure.</div>',
        '<table class="vtable">' + verify_rows + '</table>',
        '<div class="lead" style="font-size:12px;color:var(--ink-3)">Tamper evidence '
        '(M-04): each study&#39;s hypothesis and pass/fail gate are hashed at '
        'registration, before the run; the sha256 chips on the sheets below come from '
        'that registry, and <code>prereg --verify</code> flags any post-hoc edit.</div>',
        _framing_copy(),

        # ── §1 method & standing caveats ──
        '<div class="ep-sec">1 · Method &amp; standing caveats</div>',
        SS._placebo_box(),
        SS.M05_BOX,

        # ── §2 the spec-sheets (P-03, the core evidence) ──
        '<div class="ep-sec brk">2 · Detection spec-sheets — every completed study, '
        'failures included</div>',
        "".join(SS._sheet_html(s, SS._prereg_hashes()) for s in SS._SHEETS),

        # ── §3 coverage & limits ──
        '<div class="ep-sec brk">3 · Coverage &amp; limits — the boundary, in writing</div>',
        _coverage_sections(),

        # ── §4 season service record (live) ──
        '<div class="ep-sec brk">4 · Season service record (live)</div>',
        SS._mttr_box(),
        _infra_copy(),

        # ── §5 replay the tape ──
        '<div class="ep-sec">5 · Replay the Tape — the zero-look-ahead demonstrator</div>',
        '<div class="bnd">The replay artifact answers the diligence question every scored '
        'surface invites: <i>what exactly did the system know, and when?</i> It replays two '
        'fully worked historical cases — ALKYLAMINE (fundamental lens, 2020) and TANLA '
        '(technical lens, 2020) — where the reader scrubs to a past date and sees only '
        'what was knowable that day (prices as-traded, the latest filing then public, the '
        'score as it stood), then reveals what followed. Every number is date-stamped; '
        'no return is quoted here because the demonstration is the audit trail, not a '
        'performance claim. It is interactive by nature and therefore lives outside this '
        'printed pack: <a href="/dash/replay">/dash/replay</a>.</div>',

        # ── close ──
        SS.NOTE_HTML,
        '</div>']
    return HTMLResponse(_shell("Evidence pack", "".join(body),
                               active="evidence-pack", wide=True))
