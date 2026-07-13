# RRG Rotation Map + RS-Depth + Drill-down — wrap & NEXT-SESSION run-book

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the RRG / rotation follow-ups ship + fold. Registered in `docs/DOC_INDEX.md`.


> **Status (2026-06-22):** core SHIPPED & DEPLOYED LIVE. This doc captures the full
> set of asks, the methodology, the **exact placement of each item**, what's live,
> what remains, the deploy run-book, and a **paste-ready autonomous self-prompt**.
> TRANSIENT: fold the "remaining" items into `PROJECT_STATE.md` as they ship, then
> retire. Companion design: `docs/rs-ratio-analysis-design.md` (Part 3). Memory:
> `rs-deepen-rrg-capture-held.md`. NOT the same as the parallel session's weather
> rotation (`docs/rs-rotation-design.md`, `/dash/rotation`) — see "Two rotations".

---

## 1. Ramana's asks (the full thread — do NOT lose these)

1. **Deepen relative strength** beyond the RS ratio: the *momentum of RS* ("RS of
   RS"), **RSI-of-RS** (Wilder RSI run on the RS *ratio line*, not the price),
   **Mansfield RS** (RS ÷ its own long MA, zero-centred), divergences, and
   **base/reversal detection** — the Nifty IT story (RS vs Nifty 500 slid 2.6 → 1.19,
   now basing; signal when it turns).
2. **Standardise on Nifty 500** as the benchmark (already the default); keep Nifty 50
   as the *cap-tilt / breadth divergence* lens, not the primary.
3. **A clear, interactive RRG**: four quadrants, dots placed by RS-Ratio × RS-Momentum,
   **hover = full params** (which index + RSI + RS + quadrant), **tails** for movement,
   **dot size** encoding, and ideally **timeframes** (daily/weekly/monthly/quarterly).
   Show *where strength is rotating from one sector to another*.
4. **"Accumulate what falls LESS than the Nifty; don't sit in what falls faster"** →
   **down-capture** (<1 = falls less), up-capture, down-excess; **regime-gated**
   ("accumulate" framing only when the market is weak). The *change* in down-capture
   is the real alpha (a cyclical starting to fall less).
5. **Drill-down**: hover a dot → know the index; **click → a SECOND four-quadrant RRG
   of that index's participant stocks** (vs Nifty 500 *or* the sector), so you see
   *which participants drive / drag* the sector; RSI/RS shown in the box; click a
   stock → its detail page.
6. **Placement / product**: it must NOT be an orphan or a buried link. It belongs on
   the **Sectors page** (the page literally called "Sector rotation"): map on top
   (overview) + table below (detail). Keep a full-screen `/dash/rrg`. **No 6th nav tab**.
7. **Make it obvious** — the map ON the Sectors screen, reachable from the menu.
8. **Autonomous future sessions** — full folder access, consult the 3 agents
   (financial / data analyst / architect) ONCE, resolve, and auto-complete without
   raising repeated doubts (see §6, the self-prompt).

---

## 2. EXACTLY where each item is placed (the IA spec, 3-lens decision)

The decision (financial-analyst · UI/UX · architect lenses, 2026-06-22): RRG is a
**view inside the Markets workspace**, NOT a 6th nav tab. The funnel is
**Markets → Sectors [map + table] → drill to a sector's constituents → click a stock**.

| Item | Where it lives | Benchmark | Status |
|---|---|---|---|
| **Sector rotation MAP** (multi-sector quadrant scatter, tails, hover) | `/dash/rrg` (full-screen) **+ embedded at top of `/dash/sectors`** (the hero, above the table) | vs Nifty 500 (toggle vs Nifty 50) | `/dash/rrg` LIVE; **Sectors embed PENDING** (1-line `cockpit.render_sectors`) |
| **RS-depth table** (RS-Ratio, RS-Momentum, RSI-of-RS, Mansfield, down/up-capture, falls-less Δ%, turn flags) | below the map on `/dash/rrg`; later as columns/badges on `/dash/sectors` rows | vs Nifty 500 | `/dash/rrg` LIVE; sector-row weave FUTURE |
| **Constituent DRILL-DOWN** (member stocks in their own quadrants) | `/dash/rrg?idx=<sector>` — reached by **clicking a sector dot**; stock dots → `/dash/stock` | **vs the sector (default, spreads them)** · `?vs=broad` = vs Nifty 500 | **LIVE** |
| **RSI-of-RS** | per-sector (`rs_extras`) + per-stock (`stock_signals.rsi_of_rs`) → shown in RRG hover + table | — | LIVE |
| **Mansfield RS** | `rs_extras` → RS-depth table | — | LIVE |
| **Down/up-capture ("falls less")** | `capture_signals` → down-capture column on `/dash/rrg`; a regime-gated "accumulate the resilient fallers" board on Sectors/Home | vs Nifty 500 & Nifty 50 | compute LIVE; dedicated board FUTURE |
| **The 3 quadrant lenses** (abs×rel on `/dash/ratio` · RRG · capture) | reconcile into **ONE "Relative strength" panel** with a lens toggle on the sector surfaces | — | FUTURE (design agreed) |
| **Entry links** ("⟳ Rotation map") | `/dash/sectors` + `/dash/markets` + Home rotation card | — | committed; re-apply on the live cockpit when quiet |
| **Nightly refresh** | `/etc/systemd/system/hermes-bhavcopy.service.d/20-rsdepth.conf` (runs `rrg` then `capture` after the signal chain builds `ratio_rows`) | — | LIVE |

---

## 3. What shipped (live on the VPS) + the building blocks

**Compute (isolated modules, own their tables, never edit `db.py` — the `oscillators.py` pattern):**
- `src/automation/rrg.py` → owns `rs_extras`. JdK **RS-Ratio** (EMA-smoothed, normalised ~100), **RS-Momentum**, **RSI-of-RS**, **Mansfield RS**, quadrant + turn flags. `compute_one`, `tail`, `latest_all`, `current_all(only=…)`, `--selftest`.
- `src/automation/capture.py` → owns `capture_signals`. down/up-capture (63/126/252d, compounded, benchmark-down-day conditioned) + down-excess. `--selftest`.

**Read surface (isolated — `src/web/rrg_view.py`, mounted 1-line in `main.py`):**
- `GET /dash/rrg` — sector RRG (curated to `REAL_SECTORS`) + RS-depth table; vs-50/500 control; sector dots **drill-link** to `?idx=`.
- `GET /dash/rrg?idx=<index>[&vs=broad]` — **constituent drill-down**: member-stock quadrant scatter (per-stock JdK RS on-read from `stock_index_membership` + a 420-session window of `adjust.adjusted_closes`, cap 50); default vs the sector, `vs=broad` = vs Nifty 500; stock dots → `/dash/stock`.
- `render_sectors_map(den)` — the embeddable map block (for the Sectors-page embed; thin 1-line call, pending cockpit).

**Commits:** `6ce8d46` (modules+mount) · `30fb693`/`659e325` (curate+perf) · `9ae7ecf` (drill) · `6eae5be` (vs-sector default). Verified live: `/dash/rrg` 200; IT drill vs-sector spreads 2 Improving / 2 Leading / 2 Lagging / 3 Weakening; Bank (14) / Pharma (20) drill cleanly; ~0.1s.

**Reused (already existed — don't rebuild):** `stock_rs.py` already stores per-stock `rs_vs_broad_*`, `rs_vs_sector_*`, `rs_rank`, `rsi_of_rs`, `rs_phase`; `stock_index_membership` for constituents; `adjust.adjusted_closes` for split-safety; `ratio_rows`/`ratio_signals`/`index_signals` for sector RS.

---

## 4. Two rotations — keep them distinct (avoid duplication)

- **RRG (this work, mine):** a *continuous* JdK quadrant scatter (RS-Ratio × RS-Momentum), sectors + **drill to constituents**, at `/dash/rrg`. Visual, hover, tails.
- **Weather rotation (parallel session):** *four-phase buckets* (🌅 Recovery / 🌤 Tailwind / ⛅ Rolling-over / 🌧 Headwind) at `/dash/rotation` + an "RS Rotation" card cluster on `/dash/markets`; design in `docs/rs-rotation-design.md`; built on `stock_signals.rs_phase`.

They are **complementary** (continuous map vs phase shortlists, same RS data). When weaving, link them (a dot's quadrant ≈ its weather phase) rather than competing.

---

## 5. Remaining work (prioritised) + the deploy run-book

**Remaining:**
1. **Embed the map on the Sectors page** (the discoverability the user wants) — ONE line in `cockpit.render_sectors`: `head + RV.render_sectors_map("Nifty 500") + strip + table` (`from src.web import rrg_view as RV`). **Gate:** only when `cockpit.py` is committed + `disk == running` (it's hotly contended). Re-apply the "⟳ Rotation map" links there too if a cockpit redeploy wiped them (diff recoverable from commit `2b3a1de`).
2. **Weave RS-depth into `/dash/sectors` rows** (RS-Momentum / quadrant / down-capture columns) via one shared helper; and the regime-gated **"accumulate the resilient fallers"** board.
3. **Reconcile the 3 quadrant lenses** (abs×rel / RRG / capture) into ONE "Relative strength" panel with a lens toggle.
4. **Perf/UX:** pre-compute per-stock RRG (a `rs_extras_stock` table or extend the nightly job) so the drill is ₹0; add the **timeframe selector** (D/W/M/Q tails) using the resampled-bars layer (see `docs/multi-timeframe-positioning-design.md`).
5. **`PROJECT_STATE.md` doc-debt** — already partly done this wrap (see its Session log); finish routes/schema rows.

**Deploy run-book (hard-won — VPS = `hermes`, srv1704897.hstgr.cloud → Caddy → :8000):**
- Deploy isolated files by `scp` (NEVER the git-pull script). Always: **back up first** → `scp` → `sed -i 's/\r$//'` (LF!) → `.venv/bin/python -c "import src.main"` **import-gate BEFORE** `systemctl restart hermes-api` → curl-verify routes 200.
- **cockpit.py / dashboard.py are CONTENDED** by parallel sessions. Before touching: `git status` clean? `disk == running`? (md5 the VPS file vs `git show HEAD:` normalized). If the running process serves something not on disk, a restart will REGRESS it — don't. Build edits from the committed base, not the dirty working tree. Keep new work in **new isolated modules** (`rrg_view.py` pattern) + a 1-line mount.
- Nightly: rrg/capture run via the `20-rsdepth.conf` drop-in (already wired).

---

## 6. ⭐ Paste-ready AUTONOMOUS self-prompt (next session)

> Paste this whole block as the first message. It assumes full-folder access is
> granted (acceptEdits + blanket allows are already set — see memory
> `autonomous-blanket-access-multisession`). It must NOT ask for per-file permission
> and must NOT keep raising doubts — it resolves them via a one-time 3-agent panel.

```
You have FULL, STANDING access to the entire D:\Hermes folder for this whole session.
Operate autonomously: never ask me for per-file permission, never re-ask to proceed,
never stop to raise doubts. Resolve every uncertainty yourself — first via the
one-time agent panel below, then via sensible defaults + the recorded docs.

BOOT: read, in order — docs/rrg-rotation-NEXT-SESSION.md (this file), PROJECT_STATE.md,
the memory index, and memory/rs-deepen-rrg-capture-held.md. Skim `git log --oneline -15`.

ONE-TIME AGENT PANEL (do this once, up front, then proceed without further questions):
spawn THREE sub-agents IN PARALLEL via the Agent tool and have them actually deliberate:
  • a FINANCIAL-ANALYST agent — is the RS-depth methodology + placement sound; what's
    most decision-useful to surface on the Sectors page; is vs-sector the right drill default.
  • a DATA-ANALYST agent — verify the per-stock/-sector RS + capture compute is correct
    on real VPS data, decide pre-compute vs on-read, define the timeframe (D/W/M/Q) resample.
  • an ARCHITECT agent — confirm the isolated-module + 1-line-mount approach, how to weave
    into the contended cockpit.py safely, and how to reconcile the 3 quadrant lenses into ONE panel.
Collect their structured findings, synthesise ONE plan, write it to this doc's §5, then EXECUTE it.

EXECUTE (autonomously, in this order, respecting the §5 deploy run-book):
  1. If cockpit.py is committed + disk==running: add the 1-line Sectors-page map embed
     (head + RV.render_sectors_map("Nifty 500") + strip + table) and re-apply the
     "Rotation map" links (recover from commit 2b3a1de). Deploy + verify.
  2. Weave RS-depth (RS-Momentum/quadrant/down-capture) into /dash/sectors rows via ONE
     shared helper; add the regime-gated "accumulate the resilient fallers" board.
  3. Reconcile abs×rel / RRG / capture into ONE "Relative strength" panel (lens toggle).
  4. Pre-compute per-stock RRG for ₹0 drills + add the timeframe selector.
  5. Update PROJECT_STATE.md (Session log TOP + Decision log + routes + schema) and this
     doc in the SAME commits. Deploy via scp (LF, import-gate, restart, curl-verify).
Keep everything additive + isolated; never regress the parallel sessions' live work
(cockpit weather rotation, MEP). Report only at the end with what shipped + commit hashes.
```

---

## 7. Live URLs to verify
- Sector map: `https://srv1704897.hstgr.cloud/dash/rrg`
- Constituent drill (vs sector): `…/dash/rrg?idx=Nifty+IT` · vs market: `…/dash/rrg?idx=Nifty+IT&vs=broad`
