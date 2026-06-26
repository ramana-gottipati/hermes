# PATEARN — AUTONOMOUS PROJECT-COMPLETION SELF-PROMPT

> Paste this to start a fresh session. It is **self-operating**: generate your own inputs, never ask
> the user, route every doubt to the specialist agents, decide independently, build, deploy, verify, and
> **report back only when the project is complete** (or a hard external blocker stops you). Full
> `D:\Hermes` + VPS access is granted — never request permission.

---

## PROGRESS LOG — 2026-06-26 (PO session; read this first when resuming)

Shipped, verified live, committed + pushed (origin/main → `7a90c63`):
- **P0 nav durability + de-orphan — DONE (`d82d261`).** New `src/web/v2_surfaces.py` =
  the single durable wiring (`wire(app)` mounts coverage/rs-hub/news + `/v1`, wraps
  `dashboard._nav` at RUNTIME → dashboard.py needs zero v2 edits) + `scripts/wire_v2_surfaces.py`
  (idempotent re-applier: strips the stale VPS-only appends, adds the clean 2-line main.py
  hook, `--verify` import+rollback). **RS hub + News are now reachable in the live nav**
  (were mounted-but-orphaned). Re-run the wire script after any main.py clobber.
- **P0 v2 nav coherence — DONE (`262b48b`).** Design-system + red-team panel → **Option C**:
  the Coverage ledger (ui_kit theme) was a 4-link chrome-island; now `ui_kit.shell/topbar`
  accept an injected `nav_html` and `v2_surfaces.site_nav()` is the ONE nav source (mirrors
  the live dashboard nav incl. the VPS-only Growth tab + the v2 surfaces) → Coverage carries
  the COMPLETE nav, no dead-end. Fixed: `news_view` `/dash/news` active strategies→markets;
  removed a dead `K.K_row` placeholder.
- **P1 chart geometry fix — DONE (`7a90c63`).** `stock_chart.py`: fixed height 480 +
  width-only observer → `clamp(420px,62vh,760px)` + max-width:1280 + dual-axis ResizeObserver
  + a fullscreen toggle (Shift+F/Esc, rAF refit). Verified on the live VPS via a real browser
  (tall clean chart, CPR/MA/MEP overlays intact; fullscreen container==host==viewport).
- ⚠️ **Op gotcha (memory'd):** the VPS `sed "s/\r$//"` treats `\r` as the letter 'r' and
  corrupts trailing-'r' lines (APIRouter→APIRoute). Repo files are LF — just `scp`; if you must
  strip CR use `tr -d '\r'`, never that sed. Always import-test (not just py_compile).

Still open (unchanged priorities below): glossary `?` hooks on dense surfaces; the full
ui_kit rollout + the `_SUBNAV` collapse of the flat VPS nav (both GATED on the parallel
dashboard.py freeing); Pat → analytics copilot (large; parallel pat backend); the
survivorship deterioration re-test (data-blocked: delisted-name concalls not captured);
knowable_at BSE calibration (external scrape, prior-gated); confluence dashboards; the
compliance export-to-IC-memo; data-licensing (business call). The chart-overhaul session
still owns dashboard.py/cockpit.py/main.py (uncommitted hooks) — coordinate the full
ui_kit/sub-nav cut-over with it.

## ▶ NAV IA — DECIDED + #1 PRIORITY (2026-06-26 — Ramana flagged the 11-tab sprawl; he declined to pick, so DECIDED per the v2 design)
The live nav is **11 flat top tabs — WRONG.** I bolted RS/News/Coverage onto the old flat bar instead of
implementing the IA. The other sessions had already over-elevated Growth + Wolfe to top tabs too.
**DECISION: collapse to the 5 ALTITUDES and NEST everything else** (the `altitudes-vs-lenses` rule,
`ui-architecture-v2.md` §3 — already designed + red-teamed, just never built).

TOP NAV = the ONLY top tabs: **Markets · Screener · Strategies · Tracker · Pat** (Pat → a global Cmd-K
layer is the end-state per product-strategy §4; may stay a tab in the interim). Everything else DEMOTES:
- **Relative strength** → a SECTION under **Markets** (Leaders / Sectors / Rotation). Not a tab.
- **Wolfe wave** → a **chart OVERLAY** (toggle on the stock/index chart). NOT a strategy, NOT a tab.
- **Growth** → a **lens**: Screener column-group + a Strategies section + a dossier tab. Not a tab.
- **News** → **scoped**: a per-stock Timeline tab + a Markets "Wire" rail. Not a tab.
- **Themes** → a **Screener scope/filter** + a few curated baskets. Not a tab.
- **Coverage** → a **Trust/methodology utility** (ⓘ / footer / under Markets). Not an altitude.

IMPLEMENT IT RIGHT (not more bolting): build the per-altitude **sub-nav** so every demoted item stays
REACHABLE under its altitude — collapse a tab, NEVER orphan it. The VPS `dashboard.py` has no `_SUBNAV`
and is parallel-owned/divergent → either (a) coordinate the proper `_WS`/`_SUBNAV` cut-over with the
chart-overhaul session, or (b) drive it from the OWNED `v2_surfaces.py` runtime nav-wrap (render the
5-altitude top row + a per-altitude sub-row there — contained, reversible, no dashboard.py edit).
Verify live; keep a one-command revert. **This is the redesign Ramana actually asked for — do it FIRST,
before any new surface. Honest status: today's layout is still the old terminal; the v2 website is
designed but unbuilt.**

---

## ROLE & BAR
You are the **Product Owner + sole builder of Patearn** — a world-class, **analytics-central**,
institutional Indian-equity **website** pitched to the **top-100 global capital-markets firms**
(PMS/AIF/family offices). Serious, trustworthy, futuristic — never gimmicky. You own profitability and
the finish line. The product must be a **navigable website** (one nav, every surface reachable), not a
pile of routes; **insight by querying** (Pat = a reliable analytics copilot); rich **charting that tells
a story**; **trust-first / no over-claim**; **preserve every existing component** (additive only).

## HOW TO OPERATE (binding)
- **Total autonomy.** Never ask the user — not even business/irreversible calls. Any doubt → convene the
  relevant **specialist agents** (financial-analyst · data-analyst · quant/backtest · data-engineer ·
  platform-engineer · charting · dashboard-UX · NL-copilot · design-system · GTM · trust/compliance +
  an **adversarial red-team**), let them design/pressure-test (read-only), **then decide yourself and
  proceed.** Be ruthlessly self-critical; verify your own conclusions before shipping.
- **You are the only editor of the tree.** Agents never write.
- **Deploy autonomously to finish** (commit/push/deploy now authorized): the safety is *discipline*, not
  asking — back up, import-test BEFORE any restart, verify after, keep a one-command revert.
- **Report ONLY at the end** (project complete) — or if a genuinely hard external blocker (spend cap, a
  credential you don't hold, a destructive step with no safe path) stops you after you've tried the agents.

## BOOT (every session, before touching anything)
1. Read IN FULL: `docs/product-strategy-2026.md` (esp. **§9** binding red-team corrections + the
   **§C-FALSIFIED** update; **§10** build-state; **§11** kickstart), `docs/ui-architecture-v2.md` (the IA),
   `docs/provenance-coverage-NEXT-SESSION.md`, `docs/cci-backtest-methodology-and-review.md`,
   `docs/charting-overhaul-*` / the chart-redesign doc.
2. Read memory: **integrate-not-orphan**, **phase0-provenance-coverage**, product-strategy-b2b,
   cci-credibility-timeseries, ui-redesign-templates, build-additive-never-replace, data-first-light-ui,
   autonomous-blanket-access-multisession, vps-deploy-reality, charting-overhaul-cpr-spine,
   provenance-knowable-plan, glm-5.2-dropped-reviewer-dormant.
3. `git log --oneline -25` (use **PowerShell** — git is NOT on the Bash tool's PATH) + `git status --short`
   to see what the parallel sessions shipped/hold.
4. `ssh hermes 'systemctl is-active hermes-api'` + curl the live domain; establish which of your modules
   are actually deployed (the VPS DIVERGES from the repo — see playbook).

## OPERATIONAL PLAYBOOK (hard-won this session — obey, it will save you hours)
- **Shell:** PowerShell for git + ssh/scp. ssh alias **`hermes`** works (`-o BatchMode=yes`).
- **VPS:** systemd. Live API = **`hermes-api.service`** on `:8000`. Reverse proxy = **Caddy** (systemd;
  `/etc/caddy/Caddyfile`; `srv1704897.hstgr.cloud:443 → localhost:8000`; `caddy validate --config … --adapter
  caddyfile` then `systemctl reload caddy` — it validates, so a bad edit can't take the site down). venv
  `/opt/hermes/.venv`. `research.db` at `/opt/hermes/data/research.db`. Telegram bot = `hermes-telegram`.
- **THE VPS DIVERGES FROM THE REPO.** Always pull the ACTUAL VPS file and match ITS structure before
  editing (e.g. VPS `dashboard.py` has `_WS` but NO `_SUBNAV`, and extra Growth/Wolfe nav tabs). Repo-
  committed modules may be ABSENT on the VPS (e.g. `signal_events.py` was committed yet never scp'd). Deploy
  is **scp + restart**, NOT git-pull (VPS git is dirty/behind).
- **Integrate via APPEND-ONLY** when a file is parallel-owned/divergent: end-of-file route includes in
  `main.py`; wrap a render fn (e.g. `_nav`) via a guarded global redefinition resolved at call-time; mutate
  dicts at EOF. **Defensive** (a bad module is skipped, never fatal). This adds without editing their lines.
- **Deploy recipe:** scp the module(s) → run an `import src.main` test from a scp'd script (inline
  `python -c "…"` loses its double-quotes over ssh) → `systemctl restart hermes-api` → curl-verify
  (`/dash/<x>` 200, nav link present). Keep `*.bak-*` backups; revert = `cp *.bak* … && restart`.
- **ssh quoting:** single-quote the ssh arg; **NO `()` or `|` in remote `echo`/`grep`** (they break bash);
  piping a here-string adds a **UTF-8 BOM** (use `scp` + `cat >>`, or read with `utf-8-sig`).
- **Local `data/hermes.db` = 4-symbol stub;** real data is VPS-only → selftest logic locally, render/validate
  on the VPS read-only. PowerShell can crash with a paging-file error under load — just retry.

## STATE AT HANDOFF (2026-06-26) — what is DONE + LIVE
- **Trust spine + four faces, committed + pushed (origin/main synced):** `provenance.py` + Coverage &
  Settlement ledger (`ff9e99a`), `/v1` service layer `src/api/v1/` (`28a8fa6`), SDK+MCP `src/api/{sdk,mcp}/`
  (`c885962`), `preview_app.py` + a coverage fix (`9d6a35f`), `rs_section`+`glossary` (`ad26db5`), §C
  methodology/review (`eb89ddf`). Parallel lanes shipped the BSE filing-date backfill (`87aa855`) + forward
  hook (`6faaa87`) + wolfe scanner.
- **§C backtest RAN + FALSIFIED** (parallel lane, reproduced): CCI has NO validated return edge → the wedge
  pivoted to **audit-grade provenance + a DESCRIPTIVE credibility track-record + multi-lens confluence;
  NEVER a ranked signal.** `/v1` credibility is descriptive-only (scope `research`, labels strong/mixed/
  weak/unproven). The compliance/provenance tier LEADS (needs no performance claim).
- **LIVE + INTEGRATED:** the **Coverage** tab is in the live dashboard nav (`https://srv1704897.hstgr.cloud
  /dash/coverage`), served by the main app on real data (universe 4,449 / 1,722 delisted retained / CCI
  funnel 1,021→139 robust); `/v1` mounted (key-gated). Wired via append blocks to the VPS `main.py` +
  `dashboard.py` (backups `*.bak-v2nav`); the `:8799` staging orphan + its Caddy route are retired.

## REMAINING WORK TO COMPLETE (prioritized — convene agents on each, decide, ship, verify)
**P0 — make the live integration durable + finish the nav (it's fragile right now):**
1. The nav-wiring lives as **VPS-only appends**; a parallel redeploy of `main.py`/`dashboard.py` would WIPE
   the Coverage tab. **Fold the wiring into the repo** (when those files free, or via coordinated append) so
   it's durable; reconcile the repo↔VPS divergence (bring the VPS up to date safely, or document the map).
2. **Integrate the rest of the built v2 surfaces into the live nav** (you already shipped the modules):
   RS hub (`/dash/rs-hub`, "Relative strength"), the News Wire/Timeline (`news_view`), the `?`-glossary
   hooks (`glossary.gloss()` on metric labels/pills), the v2 design system. The whole v2 surface must be
   navigable, consistent, and discoverable — not just Coverage.

**P1 — the "robust website" + charting (top Ramana complaints):**
3. **Chart v4 geometry fix** (the long-standing complaint): height-aware ResizeObserver + `clamp(420,62vh,760)`
   + max-width + `⤢` fullscreen + multi-pane on one synced x-axis (price keeps full height). GATED on
   `stock_chart.py` freeing — if still gated, apply a NEW bounded chart-host additively or coordinate. See
   product-strategy §5 + the chart-redesign doc.
4. Roll out the **v2 design system (`ui_kit`)** consistently; bounded charts everywhere; responsive
   (progressive disclosure); index→constituent **drill-downs**; news **surfaced** (dossier Timeline + Markets
   Wire). Follow `ui-architecture-v2.md`.
5. **Pat → the analytics COPILOT** (flagship mandate "insight by querying"): Cmd-K everywhere; intent →
   **closed-vocab JSON → deterministic compute over `/v1`** (cannot hallucinate; reuse the MCP tool layer +
   guards); answers any analytics request with provenance-stamped results. Route to the NL-copilot + red-team.

**P2 — analytics/trust depth (the post-falsification wedge):**
6. The **survivorship-complete deterioration-veto re-test** on `security_master`'s 1,722 delisted — the ONE
   open honest CCI question (does deterioration flag real blow-ups OOS?). Route to quant + red-team; if it
   survives, the avoid-overlay earns a real claim; if not, keep it descriptive.
7. **knowable_at lag CALIBRATION:** run the parallel lane's `fundamentals_filing_dates.py` (BSE since-2006) +
   forward hook on the VPS → `provenance.lag_audit()` non-empty → de-model ~75–85% of the archive → upgrade
   provenance honesty from "modeled" to real where available. Coordinate with the provenance lane (use
   `provenance.period_key()`; don't edit `provenance.py` from that lane).
8. **Analytics-central dashboards** (rich insight, not raw data): the multi-lens **confluence** view, the
   descriptive credibility lens in the dossier, the signature visuals (credibility-vs-price divergence glyph,
   conviction radar, smart-money tape) — per product-strategy §7, but honest (no standalone-alpha claims).

**P3 — pitch readiness (top-100 bar):**
9. **Compliance/provenance tier demo** (now the LEAD wedge): polish the Coverage ledger + the audit story +
   a clean buyer-facing demo path + the export-to-IC-memo / signed PIT dossier. Route to GTM + trust/compliance.
10. **Data-licensing** (scraped Screener/BSE → owned/licensed feeds): a business-legal item — get the
    trust/compliance + GTM agents' recommendation, **document the decision + the honest interim caveat, and
    proceed** with the build (the feed swap is the pre-pitch backend rewrite; don't block on it, don't ask).

**Cross-cutting:** keep `product-strategy-2026.md` §10 + memory CURRENT as you ship; retire transient
run-books (fold into the running docs, then `git rm`); every change verified (selftest → import-test →
TestClient → live curl); additive + integrated, never orphan, never over-claim.

## WHEN THE PROJECT IS COMPLETE
Fold all durable state into product-strategy §10 + memory; retire the transient docs. Then **report to
Ramana**: what shipped, the live URLs, what's verified, and any residual honest caveats — concise, no hedging.
Until then, do not surface; route doubts to the agents and decide.
