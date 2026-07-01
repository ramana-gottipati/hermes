# Codex review 02 — navigation & page-structure (captured from Ramana's manual run)

> NOTE: Claude's automated `codex exec` dispatch was sandbox-blocked
> (`windows sandbox: spawn setup refresh`, same failure as resp-01). The review below was produced by
> Codex on Ramana's machine and pasted back; captured here verbatim for the audit trail.

## Findings

**P0 — Repo deploy would drop the institutional chrome and trust surfaces.**
PROJECT_STATE.md says the v2 IA/nav/skin is durable and live, but `src/main.py` (line 34) does not call
`v2_surfaces.wire(app)`. In a TestClient sweep from the current checkout, `/dash/coverage`, `/dash/_ui`,
`/dash/rs-hub`, and `/dash/wire` returned 404; legacy pages also rendered the old search/chrome. The
intended durable hook exists in `scripts/wire_v2_surfaces.py` (line 40); calling `v2_surfaces.wire(app)`
in-memory mounted those routes and produced the v2 markers. Impact: for institutional demos this is the
biggest red flag — "trust ledger exists" is not enough; it must survive redeploy from repo.

**P0 — Live IA depends on runtime monkeypatching, so it needs a hard acceptance test.**
Nav is centralized in `src/web/v2_surfaces.py` (line 41) — Coverage, RS hub, News/Wire, UI showcase, four
altitudes, contextual sub-nav, Trust utility — but because it wraps `dashboard._nav`/`._shell` at runtime,
the release gate must assert rendered HTML, not just route status. After `wire()`, `/dash/markets`,
`/dash/screener`, `/dash/stock?sym=RELIANCE`, `/dash/rs-hub`, `/dash/wire` all showed uk-skin, v2bar,
Trust, Wire, RS hub, and no old `.hsearch`. Required demo gate: "all investor-facing routes 200 + v2
chrome markers present + no old search form."

**P1 — The trust/provenance surface is the lead wedge, not a utility afterthought.** `/dash/coverage`
should front the demo: survivorship-aware coverage, modeled-vs-ingested disclosure, no-lookahead, source
provenance, reproducibility. Keep "Trust" in top chrome; start the demo there, then Markets → Screener → Stock.

**P1 — Navigation model is directionally right: altitudes over lenses.** The four-altitude IA
(`v2_surfaces.py` line 57) reads like an institutional terminal. Risk: incomplete route truth — `growth`
and `testing` are in the v2 nav map but 404'd even after `wire()`. Do not advertise unavailable surfaces.

**P1 — Visual language credible but slightly too "product neon."** Tokens in `ui_kit.py` (line 78) are
good (dark instrument palette, tabular numerics, restrained cyan/blue, dense tables, bounded charts).
Watch "futuristic"/glowing dots/aurora — should read "audit-grade analytical workstation," not "crypto terminal."

**P1 — Stock chart direction is strong and demo-worthy.** `stock_chart.py` (line 63): one bounded chart,
height clamp, max-width, fullscreen, ResizeObserver, four-family controls, overlays — a serious workstation.

**P2 — Legacy shell remains a fragility layer.** `shell_skin.py` (line 197) runtime skin is a clever bridge
but the long-term target is native v2 pages for the highest-traffic route (Coverage → Markets → RS hub →
Screener → Stock dossier). Runtime skin = migration infra, not final architecture.

**P2 — Demo narrative must be brutally linear:** Coverage ledger → Markets → RS hub → Screener/Screen+ →
Stock dossier → Tracker → Pat Cmd-K.

## Verification Codex ran
- WITHOUT `v2_surfaces.wire(app)`: 30 OK, 6 missing (`/dash/growth`, `/dash/testing`, `/dash/coverage`,
  `/dash/_ui`, `/dash/rs-hub`, `/dash/wire`); legacy chrome markers present.
- WITH `v2_surfaces.wire(app)` in-memory: 34 OK, 2 missing (`/dash/growth`, `/dash/testing`); v2 chrome/skin present.

## Verdict
Can meet a serious investment-bank audience, but only after fixing the repo wiring gap and making the
trust/provenance path the front door. The edge is auditable Indian-market intelligence with point-in-time
discipline — make that unmistakable and the UI reads as a credible institutional terminal.
