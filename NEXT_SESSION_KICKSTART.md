HERMES — NEXT SESSION KICKSTART (session 17)
═══════════════════════════════════════════════════════════════
Project root:  D:\Hermes\
Boot doc:      D:\Hermes\PROJECT_STATE.md  (mandatory full read)
Repo:          github.com/ramana-gottipati/hermes
Local HEAD:    0adcf5d  (== origin/main == VPS /opt/hermes; all clean, nothing unpushed)
Git identity:  Ramana Gottipati <gottipati.ramana@gmail.com>  (repo-local; FIXED in s16 — no CirqleLife footprint)

BOOT PROCEDURE (in order)
  1. Read D:\Hermes\CLAUDE.md
  2. Read D:\Hermes\PROJECT_STATE.md FULLY — especially:
       - the ⚠ Session-16 WRAP banner (very top)
       - § Session log → "Session 16 — WRAP" (the index) + the per-phase entries below it
       - Decisions D37 (RS spec), D38, D39, D40, and the D33a notes
       - § What's NOT yet built → open items (D33b/c, B5, B6)
       - docs/rs-ratio-analysis-design.md (the RS design — Part 1 = D39, Part 2 = D40)
  3. git log --oneline -12
  4. Quick sanity: ssh hermes 'cd /opt/hermes && git rev-parse --short HEAD && systemctl is-active hermes-api'
       (expect 0adcf5d + active)
  5. Only then start work.

✅ NO OPERATIONAL MESS THIS TIME (unlike s16's kickstart)
  Git identity fixed · everything pushed · VPS reconciled & clean at 0adcf5d · dashboard live ·
  D32 sectors populated · D33a stock RS backfilled (2.37M rows). Just boot-read and build.
  🔴 The ONLY uncommitted thing is the long-dormant src/assistant/patearn.py diff (stage1_screen +
     use_sonnet — contradicts doctrine D7/D22). NEVER stage it. Always `git add <explicit paths>`,
     never `git add -A` / `git add .`.

🎯 PRIMARY BUILD — D33b then D33c (finish the third pillar; spec = D37 + the design doc)
  D33a (DONE, s16) = stock-vs-BROAD (Nifty 500) RS + 1–99 percentile rank, live on every stock page.

  D33b — stock-vs-SECTOR RS:
    - Assign each stock a PRIMARY sector = the NARROWEST sectoral index it belongs to, from the
      populated `stock_index_membership` (21 indices). A stock in both Nifty Bank and Nifty
      Financial Services → pick the narrower sector. EXCLUDE the broad/size indices
      (Nifty 50/500/Midcap 150/Smallcap 250) as "sector" — they're benchmarks, not sectors.
    - rs_vs_sector = adjusted_close(stock) / close(primary_sector_index). REUSE `adjust.py` +
      the `stock_rs.py` pipeline pattern + `index_signals.compute_ratio_signal` for slopes/trend.
    - Store denormalized rs_vs_sector_* columns on stock_signals (mirror the rs_vs_broad_* set).
      Per-symbol backfill (~D33a cost). ~500 stocks have a sector; the rest are broad-only.
    - Dashboard: add a "vs sector" row to the stock-page RS reconciliation table + a sector strip.

  D33c — composite "strong-in-strong" + surfaces:
    - Leader = stock rs_vs_sector ∈ {UPTREND,BREAKOUT} AND stock rs_vs_broad ∈ {UPTREND,BREAKOUT}
      AND its sector's rs_vs_broad (D32 index_signals) ∈ {UPTREND,BREAKOUT}. Laggard = all down.
    - Add a dashboard "Leaders" board (triple-confirm, rank by RS) + /rs TICKER, /leaders,
      /laggards Telegram commands (bot is network-blocked, but add them so they work when it recovers).

🔧 SECONDARY / OPEN (after D33b/c, or if asked)
  - B5 (half done in s16): unify the dashboard's INLINE D36 adjustment (in dash_stock) to call the
    new `adjust.py`; recompute the institutional price ZONES (avg_close_*) in signals.py on ADJUSTED
    prices (still raw → the ⚠ "zone overlay approximate" warning when an action is in-window).
  - B6: pt14 fundamentals caching for the dashboard (Quality section is on-demand/empty).
  - Data-grid: CSV export is live; if Ramana wants TRUE .xlsx (sheets/formatting), add SheetJS (CDN).
  - RS tuning knobs (cheap): rank blend `0.6·3m + 0.4·6m`; heat-strip thresholds (±1% flat / ±3% strong).
    Adjust only if Ramana's read of the rank disagrees with reality.
  - Telegram bot: api.telegram.org throttled from the Mumbai VPS — wait / proxy / Hostinger ticket.

🔴 OPERATIONAL RULES IN FORCE
  - Deploy = git commit + push + reconcile on the VPS:
      ssh hermes 'cd /opt/hermes && git fetch origin -q && git stash push -u -m s &&
        git merge --ff-only origin/main &&
        ([ -z "$(git diff --ignore-cr-at-eol stash@{0} HEAD)" ] && git stash drop || echo CHECK) &&
        systemctl restart hermes-api'
    (Windows working tree is CRLF, committed blobs are LF → scp'd/working files ALWAYS show a
     CRLF-only diff vs committed; the --ignore-cr-at-eol check confirms content-identical → safe drop.)
    Fast iteration: scp a single file + `systemctl restart hermes-api`, THEN reconcile git afterward.
  - 🔴 SSH discipline: ONE `ssh hermes` attempt; on timeout WAIT or restart the home router for a
    fresh IP — rapid retries trip a port-22 IP ban (timeout while 443/the dashboard stays up).
  - Long backfills: `nohup .venv/bin/python -m ... < /dev/null > /var/log/xx.log 2>&1 &`, capture PID,
    then a background watcher `ssh hermes 'while kill -0 <PID>; do sleep 30; done; echo DONE; <stats>'`
    (run_in_background) to be auto-notified. VERIFY correctness on a KNOWN case (e.g. a split stock
    like PARAS for the adjustment) BEFORE committing to a full multi-million-row backfill.
  - 🔴 NO Sonnet via API. Classifier→Gemini, chat→Haiku, deterministic→no LLM, deep→claude.ai.
    Everything built in s16 is pure SQL / vanilla JS, ₹0 — keep it that way.
  - 🔴 Value>quantity DVPT metrics stay split-invariant; RS + price CHARTS use ADJUSTED prices (adjust.py).
  - 🔴 Update PROJECT_STATE.md in the SAME commit as code (binding rule). End session → append a
    Session-log entry + commit hashes.

🌐 KEY ACCESS
  VPS shell:        ssh hermes   (passwordless; root@187.127.173.149 / srv1704897.hstgr.cloud)
  Dashboard (PWA):  https://srv1704897.hstgr.cloud/dash   (hard-refresh after deploys — service-worker cache)
    Routes: /dash · /dash/markets · /dash/sectors · /dash/stocks · /dash/stock?sym=X
            · /dash/ratio?idx=X · /dash/rs · /dash/compare?idx=A&idx=B
  DB:               /opt/hermes/data/hermes.db   (SQLite; gitignored)
  Nous agent (separate product, NOT ours): https://srv1704897.hstgr.cloud:9443

📈 RS RECONCILIATION (if Ramana questions correctness)
  Stock page → "Relative strength" → the per-window table (stock return | Nifty 500 | RS) reconciles
  on-page. Identity: RS slope = ((1+stock_ret)/(1+nifty500_ret) − 1)×100 (verified exact in s16).

WHAT SHIPPED IN SESSION 16 (brief)
  P0 reconciliation (identity/push/VPS/D32 title-case fix) · D38 macro→micro dashboard + index
  membership · D39 RS ratio analysis (heat strip, /dash/ratio, /dash/rs) · D40 /dash/compare rebase
  chart + chart range-switch perf fix · D33a stock-vs-broad RS + 1–99 rank (2.37M rows) · on-page RS
  reconciliation table · chart hover crosshair readouts · data-grid toolbar (sort/filter/Excel-CSV
  export/count/sticky). All at HEAD 0adcf5d — clean, pushed, VPS-reconciled.

WHEN TO COME BACK TO RAMANA
  - After D33b/c is usable: do the "strong-in-strong" leaders match your judgement?
  - If you want true .xlsx export, the Telegram proxy fix, or RS rank-weighting changes.
  - NOT for threshold tweaks — SSH-edit / scp on the VPS.
═══════════════════════════════════════════════════════════════
go.
═══════════════════════════════════════════════════════════════
