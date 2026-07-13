# Next-session run-book — UI cockpit rebuild (autonomous)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the cockpit follow-ups ship + fold. Registered in `docs/DOC_INDEX.md`.


> **What this is.** A self-prompting, self-contained run-book to continue the Patearn UI rebuild **autonomously**. The design is decided (agent-panel approved); this is a BUILD. Decide, build, verify, deploy, report — pause only at the checkpoints below.
>
> **TRANSIENT doc** — fold the durable bits into `PROJECT_STATE.md` once the parallel sessions quiesce, then `git rm` this. Until then, **this is the UI work-stream's source of truth** (PROJECT_STATE.md is owned/edited by the parallel Pat/concall/deals sessions — do NOT fight them on it).

**To start the next session, paste:**
> *"Read `docs/ui-cockpit-NEXT-SESSION.md` and continue the UI cockpit rebuild autonomously — roll the full-bleed instrument language + the strategy registry across the remaining screens. Follow its operating mode + deploy recipe; blanket access is already set, don't ask per-file."*

---

## 0. Operating mode (binding — the user was emphatic)

- **Fully autonomous / self-prompting.** Work end-to-end. Decide, build, verify, deploy, report. Don't stop for per-step approval.
- **Blanket access is already configured** in `.claude/settings.local.json` (`defaultMode: acceptEdits` + blanket `Bash`/`Edit`/`Write`/`Read`/…). **Do NOT ask the user for file/git/shell permission** — it frustrates him. If something still prompts, it's a one-off; proceed.
- **Use agents to think, you build.** For any non-trivial design/perf question, spawn a **read-only Explore panel** (4–6 agents), take the call where the majority logically converges. **You are the single builder** — never let agents write to the shared tree (that caused repeated cross-absorption this session).
- **Pause ONLY for:** (1) a genuine **visual-taste fork** (AskUserQuestion w/ a recommended option, or a `show_widget` mockup first — the log-scale incident proved visuals need his eye); (2) a **deploy eyeball** (post the URL, he looks — this is *welcome* feedback, distinct from the permission prompts he hates); (3) **`git push`** (his call; many commits unpushed).
- **Cost discipline (CLAUDE.md):** bundle; verify with `py_compile` + a TestClient sweep; a VPS 200 + his eyeball is the ladder. Don't blind-iterate on visuals.

---

## 1. ⚠ CONCURRENCY REALITY (read first — this dominates everything)

**Multiple autonomous sessions run in parallel on this ONE working tree**, actively building Pat (oscillators/guardrails/engine/flows), concall-intelligence (`concalls.py`, `concall_extract/scores.py`, `client_classify.py`), `deals.py` (bulk/block + FII/DII), and editing `PROJECT_STATE.md` + `dashboard.py` continuously. HEAD moves every few minutes.

**The survival pattern (proven this session — use it):**
1. **Build in NEW self-contained modules**, not in `dashboard.py`. The UI rebuild lives in **`src/web/cockpit.py`** (one-way: it does `from src.web import dashboard as D` *lazily inside each function* to reuse helpers; `dashboard.py` only gains 4-line wrappers). New files = zero collision. Mirror this for everything new.
2. **Keep `dashboard.py` edits tiny** — a thin wrapper that early-returns into a cockpit/module function; leave the old route body as unreachable dead code (avoids matching/deleting 200+ lines under a moving file).
3. **Commit your files explicitly + fast** (`git add <paths>` — NEVER `-A`; confirm `git diff --cached --name-only`). `dashboard.py` is usually clean-at-HEAD between parallel commits, so a quick `add`+`commit` of your delta is clean. The co-author trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
4. **Deploy is CRLF-diff-checked** (recipe in §4) so an `scp` never reverts parallel VPS work.
5. **Do NOT edit `PROJECT_STATE.md`** (parallel-owned, perpetually `M`). This doc carries the UI state.

---

## 2. What shipped THIS session (all live on the VPS, committed, NOT pushed)

| Commit | What |
|---|---|
| `354a04e` | **Screener lag fix.** `table.scr{table-layout:fixed}` + a JS-built `<colgroup class="cg">` (per-column widths from the first body row's cell type — `fz`116/`inst`136/`num`76/other 112 — each `<col>` tagged `cg-{group}`) + `table.scr.hide-X col.cg-X{width:0}` to collapse hidden groups. **Root cause:** auto table-layout re-solved all 498 rows' widths on every strategy-toggle (the Nifty-500 browser hang). Kept `content-visibility:auto` + the frozen-Symbol pin. |
| `a7a5e48` | **Home → full-bleed cockpit** (`src/web/cockpit.py` NEW). `STRATEGY_REGISTRY` drives a live count-strip; instrument-rich boards (Conviction / Top-triggers w/ `_mv_ladder` / Sector-rotation w/ RS heat / Strong-in-strong / Stealth). `dash_home` = thin wrapper, `wide=True`. |
| `1024708` | **Markets → full-bleed** (`cockpit.render_markets`). Regime/breadth header tiles (Nifty 1d · % >200-DMA · sectors rising/falling) + RS-heat index cards + sortable bundle. `dash_markets` = thin wrapper. |

**Also:** blanket permissions written to `.claude/settings.local.json`.

**UPDATE (session 29 — the CCI work-stream, on Ramana's "strategies/credible screen still old UI" feedback):**
- **§3.A.1 DONE** — `/dash/strategies` is now **registry-driven cockpit** (`cockpit.render_strategies`: count-strip + a `ck-board` per pillar; old `.scard` body left as dead code after an early `return`). `dash_strategies` = thin wrapper, `wide=True`.
- **`STRATEGY_REGISTRY` extended** with a **`CCI` pillar** (accent `#39c5cf`, href `/dash/concalls`, count = scored concall symbols) → auto-appears on the home count-strip AND the new strategies hub. (This is the §3.B "registry drives new strategies" spirit for the strip; the screener column-group for CCI was added manually in `_SCREENER_JS`'s `TOG` — a full registry-driven screener refactor per §3.B is still open.)
- **`cockpit.render_concalls`** — the CCI board `/dash/concalls` is now **full-bleed** (`wide=True`) with a `.ck-tiles` strip + the data-first measurable table. `dash_concalls` = thin wrapper.
- Deployed cockpit.py + dashboard.py together (CRLF/parallel-diff-checked, py_compile-guarded).
- **§3.A.2 DONE (same session):** `/dash/conviction`, `/dash/leaders`, `/dash/sectors`, `/dash/rs` all migrated to full-bleed cockpit — new `cockpit.render_conviction/render_leaders/render_sectors/render_rs` (each = `_CKPT_CSS` + a `.ck-tiles` count-strip + the SAME data-first table[s]/instruments the old handler used: `_rs_strip`, `_char_pill`, the percentile `.bar`, the conviction filter bar). `dash_*` are thin `wide=True` wrappers (old bodies dead). Shared `_ck_tile`/`_ck_strip` helpers added to cockpit.py. Verified: all 4 → 200, `ck-tiles` + `wrap wide` present, real rows (leaders 140 RS pills, sectors/rs 19 strips/bars); home/markets/strategies/concalls/screener/stock all still 200. **Now the ENTIRE Strategies section is full-bleed cockpit.** Still open per this run-book: §3.B (full registry-driven screener), §3.C (Launchpad productization).

**`src/web/cockpit.py` is the new home.** `STRATEGY_REGISTRY` (list of `{key,label,accent,href,cta,thesis,count(conn,sig_date,D)->int|None}`) is the **single source of truth** for the pillars — POS · RS · QUAL · CPR · CONV · **LAUNCH** (already present, "research→live pending", so D56's Launchpad auto-appears once productized). Add an entry → it shows on the home strip automatically (the user's "new strategy auto-updates the dashboard" ask, D-UI-7).

---

## 3. WHAT'S NEXT (priority order — just build it)

**A. Consistency pass — the remaining narrow/outdated screens.** Same treatment as home/markets: full-bleed (`wide=True`) + the instrument language (reuse `D._mv_*`, `D._rs_strip`, the `.ck-*` kit in cockpit), via new `cockpit.render_*` functions + thin `dashboard.py` wrappers. Targets, in order:
   1. `/dash/strategies` — **make it registry-driven** (iterate `STRATEGY_REGISTRY`, render a card per pillar w/ its live count + top names). This is the headline "auto-update" win.
   2. `/dash/conviction`, `/dash/leaders`, `/dash/sectors`, `/dash/rs` — full-bleed + instrument rows/heat. They're currently narrow `.wrap` + plain tables (the "moving between screens looks broken — one narrow, one wide" complaint).
   3. `/dash/stock` can stay readable-width (it's the one prose/detail page) — but unify its card/pill styling.

**B. Extend the registry to the SCREENER.** Drive the screener column-group toggle list (`_SCREENER_JS`'s `TOG`) + the group headers from `STRATEGY_REGISTRY` so a new strategy's columns + toggle appear automatically. Agent-C spec is in the session transcript (registry → call-site refactor map). Keep additive/no-regression.

**C. Strategic (from the full re-read — surface to the user, don't silently build):**
   - **DVPT ↔ D56 reconciliation + productize the "Launchpad."** The D56 explosive-move research found (reading raw data) that a *delivery surge does NOT precede moves* — momentum/volatility/trend do; the validated "Launchpad" (M1∪M2+S1) hits ~63% / 5.7× lift OOS, 43% become ≥50% winners. The DVPT founding thesis is *delivery = leading signal*. **Unreconciled.** The `LAUNCH` registry entry is the hook — wiring M1∪M2+S1 into a live daily screener (`/dash/screener?scope=Launchpad` or a board) makes the data-validated edge real + auto-surfaces it on the cockpit. High value.

**D. Verify + reconcile docs.** Once the parallel sessions quiesce: fold this session's work into `PROJECT_STATE.md` (Decision log + Session log + routes/schema), retire transient docs, and decide `git push`.

---

## 4. Deploy recipe (CRLF-safe — never reverts parallel work)

```bash
# 1. build in cockpit.py / new module; tiny dashboard.py wrapper. Verify:
python -m py_compile src/web/dashboard.py src/web/cockpit.py
# TestClient sweep: all /dash* routes 200 (local synthetic DB lacks index data,
#   so index-only pages show the empty-state locally — that's expected; real data on VPS).

# 2. commit YOUR files only:
git add src/web/cockpit.py src/web/dashboard.py
git diff --cached --name-only          # must be exactly yours
git commit -q -m "...  ↵↵Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"

# 3. CRLF-AWARE safety check vs the VPS (catches real parallel divergence;
#    a raw diff shows ~15k lines of pure CRLF-vs-LF noise — strip \r first):
git show <prev-HEAD>:src/web/dashboard.py > /tmp/pre.py
scp -o BatchMode=yes hermes:/opt/hermes/src/web/dashboard.py /tmp/vps.py
ND=$(diff <(tr -d '\r' < /tmp/pre.py) <(tr -d '\r' < /tmp/vps.py) | grep -c '^[<>]')
# ND<=4  -> VPS == your pre-commit (line-endings only) -> safe to scp.
# ND big -> parallel session redeployed -> patch only your changes into the VPS file instead.

# 4. if safe: backup + scp cockpit.py AND dashboard.py together (dashboard imports
#    cockpit), py_compile-guard on the box (auto-restore the .bak on fail), restart, verify:
ssh hermes 'cp /opt/hermes/src/web/dashboard.py /opt/hermes/src/web/dashboard.py.bak.$(date +%Y%m%d-%H%M%S)'
scp src/web/cockpit.py src/web/dashboard.py hermes:/opt/hermes/src/web/
ssh hermes 'cd /opt/hermes && python3 -m py_compile src/web/dashboard.py src/web/cockpit.py && systemctl restart hermes-api && sleep 4 && systemctl is-active hermes-api'
# curl localhost:8000/dash* for 200 + grep your markers.
```

**Refs:** VPS `ssh hermes` → `/opt/hermes`; SQLite `/opt/hermes/data/hermes.db`; public `https://srv1704897.hstgr.cloud/dash`; service `hermes-api`. SSH rate-limit discipline: one attempt, don't hammer (port-22 ban).

---

## 5. Open items pending the user's eye/call

- **Lag-fix verdict** — he must toggle strategies on Nifty 500 at `…/dash/screener`. If still laggy: next lever = JS row-virtualization (render visible window, recycle), or last-resort default scope → Nifty 50 (he prefers keeping Nifty 500). The agent panel's full ranked fix plan is in the transcript.
- **Cockpit direction** — if he wants the count-strip/board style tweaked, apply it ONCE in `cockpit.py`'s `_CKPT_CSS` + helpers and it propagates to every screen built on the pattern.
- **`git push`** — many commits ahead of origin; his call.

---

## 6. Key pointers
- `src/web/cockpit.py` — `STRATEGY_REGISTRY`, `render_home`, `render_markets`, `_CKPT_CSS`, `_board()`. Lazy `D` import is the reuse + anti-cycle mechanism.
- `src/web/dashboard.py` — `_mv_ladder/_mv_keyband/_mv_triglyph/_mv_rsspark` (the instrument kit), `_rs_strip`, `_char_pill`, `_pos_cells`, `_cpr_setups`, `_SCAN_FILTERS`, `_real_sectors_in`, `MAJOR_BROAD/MAJOR_SECTORS`, `LEADERSHIP_SET`, `_shell(... wide=True)`. Screener lag-fix CSS ~L190/208, colgroup JS in `_SCREENER_JS`.
- Strategic context (the DVPT↔D56 tension, Pat, concalls, the full system map) — captured in the prior session's 7-agent re-read (transcript) + `docs/explosive-move-research.md`.
