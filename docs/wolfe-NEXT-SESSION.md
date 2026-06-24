# Wolfe Wave — session wrap-up + AUTONOMOUS run-book (2026-06-23)

> **TRANSIENT** ([[transient-doc-lifecycle]]). Retire once the Fib-extension / wave-selection issue is
> resolved and the feature is committed. Fold the durable parts into `docs/wolfe-wave-design.md` +
> PROJECT_STATE, then `git rm` this file.
>
> **Read order for a fresh session:** CLAUDE.md → PROJECT_STATE.md → `docs/wolfe-wave-design.md` (the full
> design, correct convention in §2) → **this file** → memory `[[wolfe-wave-strategy]]`.

---

## ⭐ 0. DEFINITIVE STATE + RESUME (2026-06-24 wrap — READ THIS FIRST; supersedes the §7* correction history below, which is kept only as archaeology)

> Ramana ended the session saying **"there seem to be a lot of misunderstandings — let's address this properly"** and asked to persist the knowledge. So: the implementation below is LIVE and reflects everything he corrected this session, **but treat the METHODOLOGY as not-yet-fully-pinned** — next session, RE-GROUND it with him cleanly before changing code. Do **not** assume the current build is the final truth.

### Brand (binding)
The product is **patearn** (lowercase). **"Hermes" = the Nous agent ONLY** — never call the product/VPS services Hermes. See memory [[patearn-brand-and-dvpt-direction]].

### The methodology as understood so far (hard-won across this session; corrections in priority order)
1. **CONVENTION — do NOT rewrite (he corrected this 2–3×; I broke it once by "improving" it and had to revert):**
   - **BEAR / sell = ASCENDING structure**, pivots in time **H,L,H,L** (point 1 = a HIGH); 1·3 ascending highs (3>1), 2·4 ascending lows. Point 5 = a HIGH that overshoots the 1-3 line; price then reverses DOWN. *(PARAS daily: 1=1066.75 H 06-10, 2=968.1 L 06-11, 3=1133 H 06-15, 4=1075.5 L 06-16, 5=1443 06-19.)*
   - **BULL / buy = DESCENDING structure**, pivots **L,H,L,H** (point 1 = a LOW); descending lows (3<1). Point 5 = a LOW overshooting the 1-3 line; reverses UP.
2. **POINT 5 (his explicit rule):** a candidate is **NOT point 5 until price crosses the EXTENDED 1-3 line** — *above* for a bear, *below* for a bull — and **it may keep extending**. Impl: scan bars after point 4 (within ~1.5× the 1-4 span) for the extreme that crossed the 1-3 rail.
3. **PIVOTS:** he marks pivots with Fyers **Fractals (2) and (10)**. patearn uses an **ATR-zigzag** on **DAILY** bars, grid **ks=(1.0, 1.5, 2.5)** — coarse 2.5 surfaces the bigger/monthly wave, fine 1.0/1.5 the recent tight one. (Daily *fractals* are too sparse in a trend to give 5 clean points, so zigzag is the proxy; `fractal_pivots()` exists but is unused.) His exact pivots are sometimes **75-minute** or discretionary and can't be reproduced on daily — that's a data-resolution wall, NOT a bug (he declined intraday data).
4. **TWO WAVES:** the overlay shows the **two most-recent** clearest waves (recency leads, WolfeRank breaks ties); they can be **nested** (different degree, sharing point 5).
5. **FIB ratios:** two standard **EXTENSION fans**, one per thrust leg (1→2 and 3→4), each anchored at the leg's **low** and projected **toward the overshoot** (up for a sell). **EXTENSION ratios ONLY (>1.0): 1.272, 1.414, 1.618, 2.618, 3.618, 4.236, 4.618.** *(0.236–1.0 are RETRACEMENTS — inside the leg — and must NOT enter the overlap test; he caught this.)* Where a leg-1-2 extension coincides with a leg-3-4 extension (within ~0.4 %) = a **strong target zone**. Validated to the decimal: PARAS legs 968.1→1066.75 & 1075.5→1133 → **2.618∩2.618 = 1226.2**.
6. **CANDLES ONLY:** these overlays must render on **candlesticks**, never a close-line (a line hides the intraday spikes the pivots sit on). `/dash/wolfe` draws candles; `/dash/stock` overlay must be viewed in Candles mode.

### Surfaces (LIVE on the VPS, patearn)
- **`/dash/stock?sym=…` → tick "Wolfe wave"** (Candles): candle overlay drawing the 2 most-recent waves — structure 1-2-3-4-(5) + numbered markers, the **1-3 confirmation rail**, the strong overlap zones labelled `price (r12∩r34)`, and a **"fib fans"** toggle for the full extension grids. (Wave 1 solid/circle, wave 2 dashed/square.)
- **`/dash/wolfe?sym=…`**: ranked SVG page — lists every setup best-first (click to draw), candlesticks, the two extension fans (faint, ratio-labelled at the right gutter) + bold overlap zones.

### OPEN / unresolved (he flagged "a lot of misunderstandings" — resolve these by re-grounding with him, don't guess)
- **The 3 calibration points he was about to answer:** (a) include the **2.0** extension? (his Fyers fans seem to jump 1.618→2.618); (b) **overlap tolerance** — 0.4 % now, but his A-4.236(≈1319) vs B-3.618(≈1325) sit ~0.45 % apart, just outside; loosen to ~0.5–0.6 %?; (c) keep **retracement levels** drawn faintly on the fans for context, or extensions-only? (They stay out of the overlap test either way.)
- **EPA / downstream target for a BEAR**: the 1-4 line projects up and reads oddly as a sell target — unresolved; he trades the Fib *zone*, not the EPA. Revisit whether to draw EPA at all for sells.
- **Auto-pivots vs his eye:** the zigzag can't always reproduce his exact discretionary/75-min pivots. A fractal-pivot reader or a manual "draw your own swings" mode are options he hasn't chosen.
- **Edge backtest NEVER run** (Phase 0). A naive probe looked great but was repaint look-ahead; a PIT-honest entry-at-confirmation probe showed **no edge**. So the lens stays **DESCRIPTIVE-ONLY — no buy/sell verdict** until a proper survivorship-aware backtest earns one.
- **Whole-method re-confirmation:** he senses residual misunderstandings — next session, walk the method end-to-end with him on 1–2 examples BEFORE touching code.

### Files (isolated — commit ONLY these; parallel session owns dashboard.py/main.py/PROJECT_STATE.md)
`src/automation/wolfe.py` (detector + `fib_zones`+`overlay_for`+`analyze`+`fractal_pivots`(unused)) · `src/web/wolfe_view.py` (`/dash/wolfe` SVG, candlesticks) · `src/web/wolfe_overlay.py` (the `/dash/stock` snippet, 2-wave + fib fans toggle) · `research/wolfe_waves/selftest.py` (GREEN: bull L,H,L,H / bear H,L,H,L / PARAS 1226.2 pin / noise-reject) · `docs/wolfe-*.md`.

### Commit trail this session (all on `main`, deployed to VPS by scp+restart, LF)
`f1a8741` revert the bad convention-rewrite + fix Fib **direction** (up not down) · `70d5703` back to zigzag pivots (the version that drew 1-2-3-4-5) · `f028fdd` two nested waves + point-5=cross-1-3-line rule + ks 2.5 · `b747cf7` recency-first selection · `35bf825` `/dash/wolfe` candlesticks · `f9fc5e8` draw the Fib fans + labelled overlap zones · **`707fcb1` (HEAD) Fib EXTENSIONS only (drop retracements from overlap)**. (Earlier `4804200`/`b7ad360`/`45d4d92` were the convention-rewrite / draw-mode / fractal experiments — all reverted.)

### Deploy recipe (unchanged): `sed 's/\r$//' <f> | ssh hermes 'cat > /opt/hermes/<f>'` for each wolfe file, then `ssh hermes 'systemctl restart hermes-api'` + wait ~7s + verify `/health`=200. Backups on VPS: `*.bak-0624fix`. NEVER scp dashboard.py/main.py (parallel session).

### ▶ RESUME PROMPT (paste into the next session)
```
You are continuing patearn's "Wolfe Wave" lens (patearn — NOT Hermes; Hermes = the Nous
agent only). Boot: read CLAUDE.md, PROJECT_STATE.md, docs/wolfe-wave-design.md,
docs/wolfe-NEXT-SESSION.md §0 (the DEFINITIVE STATE — read it fully), and memory
[[wolfe-wave-strategy]] before touching code.

The lens is LIVE on the VPS (candle overlay on /dash/stock + ranked /dash/wolfe page) and
implements: H,L,H,L bear / L,H,L,H bull convention; point 5 = the post-point-4 extreme
that crosses the extended 1-3 line (above bear / below bull, may extend); ATR-zigzag
pivots ks=(1.0,1.5,2.5) on DAILY; two nested waves shown; Fib EXTENSION fans per leg
(1.272,1.414,1.618,2.618,3.618,4.236,4.618 — extensions only, no retracements) with the
extension∩extension overlap (~0.4%) as the target zone (PARAS 2.618∩2.618=1226.2); all on
candlesticks. Selftest green.

⚠️ Ramana says there are STILL misunderstandings in the method. Do NOT assume the build is
correct. START by walking the methodology end-to-end with him on 1–2 concrete examples and
let HIM correct it — especially: (a) the exact extension ratio set (include 2.0?), (b) the
overlap tolerance (0.4% misses his ~0.45% 1319/1325 pair — loosen?), (c) whether
retracement levels should be drawn (display only, never in the overlap test), (d) the
EPA/target for a bear, (e) whether to match his exact Fyers Fractals(2/10) pivots (fractal
reader / manual swing input) since the daily zigzag can't always reproduce his pivots.
The Fib FORMULA is validated (1226.2); the CONVENTION (H,L,H,L bear) is his and must NOT be
rewritten (I broke it once by "improving" it — reverted).

Work additively in the isolated wolfe files only (wolfe.py, wolfe_view.py,
wolfe_overlay.py, research/wolfe_waves/, docs/wolfe-*.md); never touch dashboard.py /
main.py / PROJECT_STATE.md (parallel session owns them). Deploy via the in-place scp+restart
recipe in §0. Verify changes LIVE in the browser on CANDLES (the line chart hides the
spikes). Commit only the isolated wolfe files. Keep it DESCRIPTIVE-ONLY until the edge
backtest (still un-run) earns a verdict. Minimise churn — confirm the method with Ramana
before each change; I burned tokens this session by guessing instead of asking.
```

---

## 0. One-paragraph state

The Wolfe Wave lens is **built and LIVE on the VPS**, end to end: a pure-stdlib detector
(`src/automation/wolfe.py`), a JSON overlay endpoint + standalone ranked page (`src/web/wolfe_view.py`),
and — the surface Ramana actually uses — a **"Wolfe wave" checkbox on the real stock candlestick chart**
(`/dash/stock`) that overlays the most-recent setup on the live lightweight-charts candles
(`src/web/wolfe_overlay.py` + 4 in-place patches to `dashboard.py`). Detection enforces the real rules
(1·3·5 structure, symmetry, 4-in-channel, **4-not-breached**), predicts/marks point 5, and now draws the
**standard Fib extensions** `level(r)=a+r·(b−a)` on swings 1→2 & 3→4 with their **strong overlap zones**.
The Fib FORMULA was validated against Ramana's Fyers screenshot to the decimal (the 1226 zone). **The
remaining defect: the detector frequently selects a different wave / different pivots than the one Ramana
draws by eye** — so the (correct) extensions get computed on the wrong swings and the zones look "wrong."
Nothing is committed to git; the edge backtest was never run (it's descriptive-only).

---

## 1. THE method — ground truth (from Ramana across the session)

Encode this exactly; do not re-derive.

**Structure (correct convention — he made me rebuild to this):**
- **Bullish:** 1·3·5 = descending **LOWS**, 2·4 = highs. 3<1; point 5 overshoots the **1-3 line**; reverses **up**.
- **Bearish:** mirror — 1·3·5 = ascending **HIGHS**, 2·4 = lows.
- Valid wave: **leg 1-2 ≈ leg 3-4** (symmetry) · point 4 **inside the 1-2 channel** (bull 4≤2, bear 4≥2) ·
  point 4 **NOT breached before 5** (bull: no higher high above 4; bear: no lower low below 4) — a breach
  means it broke out, not a Wolfe.
- **EPA target = the 1-4 line** (bull slopes up, bear down). After 5, price plays back to EPA.

**Point 5 / the Fib method (the part still not matching his eye):**
- Draw **standard Fibonacci extensions** on **swing 1→2** and **swing 3→4**: `level(r) = a + r·(b−a)`,
  0 at the swing start, 1.0 at its end. Ratio set `{0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.414,
  1.618, 2.0, 2.618, 3.618, 4.236, (4.618)}`.
- Where a **1-2 level overlaps a 3-4 level = a STRONG ZONE.** There are usually **several** (he found two).
  These zones are the high-probability reversal/target levels; point 5 sits in one.
- **VERIFIED against Fyers (intraday 75-min PARAS):** swings 968.1→1066.75 and 1075.5→1133 → both 2.618 ≈
  **1226** → strong zone 1226.2 (his exact zone). `wolfe.fib_zones()` reproduces this. **The formula is right.**
- Earlier he also said the overlap "tends to land ~0.5" and the broken-band → next-band / reverse-on-return
  logic — keep those as refinements once the wave/pivots match.

---

## 2. What's BUILT (files · routes · deploy)

| Piece | File | Notes |
|---|---|---|
| Detector | `src/automation/wolfe.py` | zigzag→1-4 (all rules)→p5→WolfeRank(6-dim)→R:R · `fib_zones()` · `overlay_for()` · `analyze()` |
| Overlay JSON + ranked page | `src/web/wolfe_view.py` | `/dash/wolfe` (ranked SVG, `&w=` selects) · `/dash/wolfe/overlay` (JSON for the stock chart) |
| Stock-chart overlay JS | `src/web/wolfe_overlay.py` | self-contained SNIPPET, **no imports**; draws on `window.__wfpc` |
| Stock-page integration | `dashboard.py` (4 in-place patches) | import `_WF_SNIPPET`; checkbox by Candles/Line; `window.__wfpc=pc;`; `{_WF_SNIPPET}` token |
| Mount | `src/main.py` | `include_router(wolfe_router)` |
| Research sandbox | `research/wolfe_waves/` | `selftest.py` GREEN (tests prod `wolfe.py`); `detect.py`/`point5.py`/`backtest.py` are STALE (old convention) |
| Design doc | `docs/wolfe-wave-design.md` | rich; §2 has the corrected convention |

**LIVE at** `http://187.127.173.149:8000/dash/stock?sym=<TICKER>` → tick **Wolfe wave**. Also `/dash/wolfe?sym=`.

**Selftest:** `.venv/Scripts/python.exe research/wolfe_waves/selftest.py` → ALL PASS (bull+bear geometry,
EPA slope signs, point-5 confirm, breach, trend-rejection).

**Deploy recipe (VPS tree is dirty w/ a parallel session — NEVER scp shared files over theirs):**
- New/mine (`wolfe.py`, `wolfe_view.py`, `wolfe_overlay.py`): `sed 's/\r$//' <f> | ssh hermes 'cat > /opt/hermes/<f>'`.
- `dashboard.py` / `main.py`: apply the additive edits **in place** via an idempotent, anchored Python patch
  over SSH (all chart-area anchors matched the VPS — its chart section == local; only nav/subnav diverges).
- Then `ssh hermes 'systemctl restart hermes-api'` + verify `/health` and the route. LF endings always.
- `python-multipart` was installed in the LOCAL `.venv` (the app needs it; was missing locally).

---

## 3. THE OPEN DEFECT (start here) + the rest

**#1 — Wave / pivot selection mismatch (the "fibs are wrong again" cause).** The Fib formula is correct, but
the detector's ATR-zigzag 1-4 ≠ the swing Ramana draws by eye. On PARAS he drew the **rising** wave (zones
~1226/1386, *up*); the detector showed a **bear** wave (zone ~807, *down*). So extensions land on the wrong
swings. **Fix paths (pick via the agent panel, §5):** (a) a **prev/next selector** on the chart to cycle the
N setups; (b) bias selection to the wave **nearest current price / the active structure**; (c) match his
pivot-picking (he uses fractals — note the Fyers "Fractals (2)/(10)" — consider a fractal pivot detector to
mirror his eye instead of/alongside ATR-zigzag); (d) let him **click two swings** and compute extensions on
those. Verify any change by reproducing his Fyers zones on the *same* swings.

**#2 — Overlay clutter.** Full grids = ~26 faint lines; if busy, draw only the zones + each zone's two
contributing levels.

**#3 — Tighten setups** (symmetry/quality) so a name shows 1-2 clean setups, not 4-8.

**#4 — Edge backtest never run** (Phase 0 gate). Port `research/wolfe_waves/backtest.py` to the rebuilt
`wolfe.py` API and run PIT on the VPS archive: does the setup reverse better than chance? Until then it is
**descriptive-only** — no buy/sell verdict.

**#5 — Not committed to git; PROJECT_STATE not updated.** Tree is dirty with a parallel session's work, so
commit **only the isolated wolfe files** (`src/automation/wolfe.py`, `src/web/wolfe_view.py`,
`src/web/wolfe_overlay.py`, `docs/wolfe-*.md`, `research/wolfe_waves/`) — do **not** add `dashboard.py` /
`main.py` / `PROJECT_STATE.md` (they carry others' uncommitted edits). Use the `safe-git-add-new` discipline.

**#6 — Universe scanner** (rank every name in a setup) needs a nightly `wolfe_signals` table (Phase 4).

---

## 4. Architecture guardrails (unchanged)

Isolate in NEW modules; never reroute the sacred pages; pure-Python/no-LLM/₹0 in the detector; point-in-time
safe; descriptive-only until the backtest earns a verdict; update PROJECT_STATE + `[[wolfe-wave-strategy]]`
memory when a phase ships.

---

## 5. THE AUTONOMOUS PROMPT (paste into a fresh session)

> Copy everything in the block below to start the next session. It runs autonomously, resolves its own
> questions through an expert-agent panel, minimises pings, and surfaces only a final review.

```
You are continuing the Hermes "Wolfe Wave" strategy. Work AUTONOMOUSLY and minimise interruptions to
Ramana (the financial analyst). Boot: read CLAUDE.md, PROJECT_STATE.md, docs/wolfe-wave-design.md,
docs/wolfe-NEXT-SESSION.md, and memory [[wolfe-wave-strategy]] before touching code.

GOAL: make the on-chart Wolfe overlay match how Ramana draws it in Fyers — correct pivots, correct Fib
extensions (level(r)=a+r·(b−a) on swings 1→2 & 3→4), and the STRONG OVERLAP ZONES (several, not one). The
Fib formula is already correct (validated vs his Fyers 1226 zone); the live defect is WAVE/PIVOT SELECTION
(detector picks a different wave than he draws — see docs/wolfe-NEXT-SESSION.md §3 #1). Fix that first,
then clutter (#2), tighten (#3), and run the edge backtest (#4).

AUTONOMY RULE — do NOT ask Ramana questions. Whenever a decision or ambiguity arises, convene a panel of
expert agents (use the Agent tool, or a Workflow if it's multi-step) and decide from their perspectives,
then proceed:
  • Wolfe/Fib QUANT — owns the geometry, the standard Fib-extension method, fractal vs ATR pivot detection,
    which swings/ratios/zones are correct. Must reproduce Ramana's Fyers numbers exactly on the same swings.
  • CHARTING/VIZ — owns the lightweight-charts overlay: readability, clutter, what to draw vs hide.
  • SKEPTIC/QA — adversarially verifies every claim: does it match Fyers? does the wave obey ALL rules
    (1·3·5, symmetry, 4-in-channel, 4-not-breached)? does it survive point-in-time? Default to "not proven."
  • RAMANA-PROXY — the domain authority: "what would a Fyers-using analyst who draws these by hand expect
    here?" Resolve UI/interpretation calls from this seat.
Synthesise the panel, record the decision + rationale in docs/wolfe-NEXT-SESSION.md, and act. Only surface
to Ramana a single end-of-run REVIEW: what changed, screenshots/zone numbers vs Fyers, what's still open.

VERIFY everything against the Fyers reference in §1 (swings 968.1→1066.75 & 1075.5→1133 → strong zone
~1226.2). Deploy with the in-place VPS recipe in §2 (never clobber the parallel session's dashboard.py /
main.py). Keep the detector pure-Python, descriptive-only until the backtest earns a verdict. Commit only
the isolated wolfe files when done (§3 #5) and update PROJECT_STATE + the memory. Reduce disturbances:
batch work, no per-step pings, one clean review at the end.
```

---

## 6. Quick verification commands

```
# selftest (geometry rules)
.venv/Scripts/python.exe research/wolfe_waves/selftest.py
# fib_zones vs Fyers
.venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');from src.automation import wolfe;print(wolfe.fib_zones(968.1,1066.75,1075.5,1133)[2])"
# live overlay for a name
ssh hermes 'curl -s "http://localhost:8000/dash/wolfe/overlay?sym=PARAS" | python3 -m json.tool | head -40'
```

---

## 7d. TWO nested waves + point-5 = 1-3-line-cross rule (2026-06-24, latest — WORKING)

Ramana confirmed the points are correct and gave the spec: (1) show the **two** most-recent/clearest waves;
(2) his bigger wave = Mar-9 H / Mar-23 L / May-8 H / May-18 L / Jun-19 H (shares point 5 with the first —
nested); (3) **point 5 is not point 5 until price crosses the EXTENDED 1-3 line** (above for bear / below for
bull) — "this point may keep extending."

Done + verified on PARAS: `detect_waves` grid now **`ks=(1.0,1.5,2.5)`** — the coarse 2.5 surfaces the
monthly Mar-Jun wave (validated: it reproduces his exact pivots), fine 1.0/1.5 the May-Jun wave. **Point-5
rule rewritten** to his definition: scan bars after point 4 (within ~1.5× the 1-4 span, so a tiny old wave
can't claim a far-future high) for the extreme that has **crossed the 1-3 rail** → that's point 5, CONFIRMED,
may extend. `overlay_for` now returns the **two** clearest recent waves (most-recent by last pivot, ties by
WolfeRank, structurally distinct), and the snippet draws both (W1 solid/circle markers, W2 dashed/square) each
with its **1-3 confirmation rail** + strong zones. Live result: W1 = his Mar-Jun wave, W2 = the May-Jun wave,
both 5 = Jun-19 1443. Selftest green. (Fib zones per wave come from its own legs — W2's are ~1005/1128, W1's
~887/958; the 75-min-only 1226 is a different, finer wave not present on daily.)

NOTE: zigzag is back as the pivot source (fractals on daily are too sparse — see §7c); `fractal_pivots` kept
but unused.

---

## 7c. Pivot mechanism switched to WILLIAMS FRACTALS on daily (2026-06-24) — REVERTED (see §7d, zigzag won)

Ramana: *"Why feed 75-minute data? … Do it for the daily chart … replicate the same mechanism on the
daily timeframe. The concept is something you need to look at."* The **concept = his Fyers Fractals 2 & 10**
(top-left of both his charts) — that's how he marks pivots, NOT an ATR-zigzag.

**Done:** new `fractal_pivots(high, low, periods=(2,10))` (strict, unique Williams fractals → alternating
H/L) now feeds `detect_waves` instead of the zigzag (`zigzag()` kept but unused). `analyze`/selftest use
`periods=`. Added a **freshness gate** in `overlay_for`: if the latest setup's last pivot is >90 bars old,
return None (don't show a year-old wave). Selftest green; deployed; `/health` 200.

**Result:** the mechanism is now his, on daily. Works cleanly where a daily Wolfe exists — RELIANCE BEAR
(zones 1325.9…), KEI BEAR forming (5159/5656). **PARAS shows nothing — and that is CORRECT:** on daily its
June move is one near-vertical leg with NO intermediate daily fractals (06-02 low → 06-19 high), so there's
no daily Wolfe; his 968/1066/1133/1075 pivots are 75-min-only (06-10's high isn't a daily local max — 06-12
is higher). Proven 3 ways. PARAS's pattern genuinely lives at 75-min; daily can't show it without intraday
data (which he declined). The mechanism is right; PARAS is simply post-breakout on the daily scale.

**⚠️ REVERTED the fractal switch (Ramana, same day): "You already identified 1-2-3-4-5 before — reach that
place AGAIN first, then fibs."** The fractal switch made PARAS show *nothing* — a regression vs the zigzag,
which DID plot the five points. So `detect_waves` is back on the **ATR-zigzag** (the version that surfaces a
clean 1-2-3-4-5 on daily); `fractal_pivots()` stays defined but unused. PARAS now plots
**1(881.95 05-26·H) · 2(805.7 06-02·L) · 3(1066.75 06-10·H) · 4(968.1 06-11·L) · 5(1443 06-19·H)** — a valid
ascending bear, zones (up-projected) 1005.55/1128.21. **LESSON: stop changing the pivot mechanism; the
zigzag is the "version that worked." Get his sign-off on the 5 points BEFORE touching the Fib ratios.**
NOTE: this daily wave is *bigger* than his 75-min one (shares 1066.75/968.1 but not 1133/1075.5); whether it
IS the pattern he remembers, or he wants the tighter consolidation swings (→ a finer zigzag k), is the next
question for him — do NOT guess it.

---

## 7b. CORRECTION — the convention rewrite was WRONG; REVERTED (2026-06-24, later)

⚠️ **The whole §7 convention rewrite below was a mistake and has been REVERTED.** Ramana clarified
(with his 75-min + daily Fyers screenshots): an earlier version **already plotted points 1-2-3-4-5
correctly** — his structure is **H,L,H,L** (point 1 = a HIGH; 1·3 ascending highs, the ORIGINAL bear
convention). He only ever asked to fix the **Fibonacci ratios**. Rewriting `_classify` to L,H,L,H + dropping
H,L,H,L **spoiled the points that were already right** (the skeptic seat had warned exactly this; it was
overridden — the skeptic was correct).

**What was actually wrong = the Fib DIRECTION only.** `overlay_for` called `fib_zones(P1,P2,P3,P4)` with the
bear's points in detector order (P1 = high), so `p1 + r·(p2−p1)` projected **down** → the bogus ~807 zone.

**Fix applied (surgical):** restored the original detector verbatim (H,L,H,L bear, L,H,L,H bull, original
point-5 / breach / `point5_zone` / single-most-recent `overlay_for` + the original simple snippet). Changed
ONLY `fib_zones`: it now normalises each leg to (low, high) and projects toward the **overshoot** — UP for a
BEAR/sell (zone above), DOWN for a BULL/buy — reproducing his exact zones (his legs → 2.618∩2.618 = 1226.2,
verified on his detector-order points 1066.75/968.1/1133/1075.5). `overlay_for` passes `direction=`.

**Remaining (honest, data-proven):** the auto-detector finds his *type* of wave and now projects fibs the
right way, but it can't reproduce his *exact* 1226 wave — his 4 pivots are **non-consecutive, hand-picked
fractal pivots** (he uses Fyers **Fractals 2 & 10**) on a **75-minute** chart; the daily zigzag can't surface
them at any scale (tested 0.4–1.5). True match needs intraday 75-min data + a fractal pivot reader, OR a
manual swing-input. That's a data/feature decision for Ramana, not a convention bug.

**BRANDING (binding):** the product is **patearn**, NOT Hermes. "Hermes" = the Nous agent ONLY. Stop calling
the product Hermes.

---

## 7. PANEL DECISION — wave/pivot selection fix (2026-06-24) — ⚠️ SUPERSEDED, SEE §7b ABOVE

Convened the 4-seat panel (Wolfe-quant · charting/viz · skeptic-QA · Ramana-proxy) per the autonomy
rule. The split: QUANT said the direction convention is inverted and wanted a full relabel; SKEPTIC
vetoed (a relabel resurrects the exact "1 high·2 low·3 lower-high·4 lower-low" = H,L,H,L-descending-as-BULL
shape Ramana retracted on 2026-06-23, whose 1-4 EPA slopes the wrong way). RAMANA-PROXY (domain
authority) broke the tie. **Empirical probe (`/tmp/wolfe_paras_probe.py`) was decisive:** the current
`_classify` returns `None` on Ramana's exact PARAS pivots **even with symmetry widened to 0.5** — so this
is NOT merely a selection/tolerance problem (SKEPTIC's lighter fix is insufficient); a new detection
branch is genuinely required, AND the symmetry floor must move.

### The agreed convention (the anchor)
The two thrust legs **1→2 and 3→4 point toward point 5** — their standard Fib extensions
`level(r)=a+r·(b−a)` converge at the point-5 zone (this is literally Ramana's method, and it reproduces
the PARAS 1226.2 zone = 2.618∩2.618 to the decimal). Applying it:

- **BEAR / SELL (validated on PARAS, the fix shipped this session):** ASCENDING wedge. Pivots **L,H,L,H**,
  lows ascend (3>1), highs ascend (4>2), legs 1→2 & 3→4 **UP**. Point 5 = a HIGH that breaks **above point
  4** and overshoots the **2-4 (upper) rail** → the upper Fib-confluence zone (PARAS ≈ **1226**). Reverses
  **DOWN**. Colour **RED**. EPA = 1-4 line (secondary; he trades the zone, not the EPA).
- **BULL / BUY — UNCHANGED + DEFERRED.** Keep the existing L,H,L,H descending-lows convention exactly
  (respects Ramana's 2026-06-23 correction; SKEPTIC's veto). It has a *latent* Fib-method inconsistency
  (legs up but point 5 below) — do NOT touch it until a real buy-side drawing of his is available to
  validate. Logged as open item #B1 below.
- **H,L,H,L decompositions — DROPPED.** They put the Fib confluence on the wrong side of point 5 (legs
  point away from 5) — this was the source of the bogus downward ~807 zone the detector showed on PARAS.
- **Symmetry tolerance widened 0.6 → 0.5** (PARAS legs = 57.5/98.65 = 0.583 was being rejected).
- **Point-5 zone unified on the Fib confluence** (strongest zone on the overshoot side), with the old
  symmetry projection as a fallback — so `/dash/wolfe` (SVG) and the candle overlay agree on the number.

### Viz / selection (VIZ seat)
- Default candle overlay: structure 1-2-3-4-(5) + numbered markers + EPA + **only the strongest zone**.
  Hide the two ~13-line Fib grids, the 1-3 reference line, and the weaker zones behind a **secondary
  toggle**. Zones as right-anchored bands with gutter labels (`Z₁ price (r12∩r34)`), graded by tightness.
- Selection: `overlay_for` returns **all** waves best-first; default = top WolfeRank (not most-recent);
  add **‹ prev / next ›** + a **↧ nearest-price** control. **All controls injected by the snippet itself**
  (next to `#wfLbl`) so `dashboard.py` / `main.py` are NOT touched (parallel session safe).

### Blast-radius handled in lockstep (SKEPTIC's condition)
`_classify` (new BEAR branch + drop H,L,H,L), `_build` (+`line24_slope`), `detect_waves` (bear point-5 =
high>p4 overshooting 2-4; bear breach = low below p3), `point5_zone`/new `line24_at`, `analyze` (Fib-zone
unification + RR/stop already direction-keyed), `overlay_for` (all-waves payload), the snippet, and the
**selftest** (rewritten: bull=descending-lows L,H,L,H reverse-up; bear=ascending L,H,L,H reverse-down +
a PARAS numeric pin). PIT-safety preserved (point-5 reads only printed pivots/bars ≤ as-of).

### ADDENDUM (2026-06-24, same session) — Ramana rejected the auto wave-count → built MANUAL draw mode
Ramana looked at the live PARAS overlay and said the auto wave count was wrong ("pathetic / horrible"): the
detector put **point 4 on the peak with no point 5** and anchored **point 1 too early**, so the whole count
slid by one. **Root cause (confirmed):** his hand-drawn pivots are *discretionary* — they aren't strict
alternating zigzag pivots (his PARAS point 3 = 1075.5 sits **above** point 2 = 1066.75; the rally 920→1500 is
one clean zigzag leg so the auto-detector can't insert the intermediate point-4 he sees). No ATR-zigzag /
fractal auto-tune will reliably match his eye. **Decision (overrides the VIZ seat's earlier "skip manual"):**
give him **direct pivot control** — the durable fix, since the machine's value is computing the *exact* Fib
zones on *his* count, not guessing the count.

Built the **"✎ draw your own" mode** in `wolfe_overlay.py` (self-contained; dashboard.py still untouched):
he clicks points 1→5 on the candle chart, each **snapped to the nearer real bar high/low**, the snippet draws
the structure + computes the **standard Fib extensions + strong overlap zones on his pivots** (a JS
`fibZones` that mirrors `wolfe.fib_zones` byte-for-byte — verified `968.1/1066.75/1075.5/1133 → 1226.2`).
Zone prices also print in the label (so they're readable even when a steep wedge's zone sits off the visible
scale). `overlay_for` now also returns compact `bars` (date/high/low) for snapping. **Verified LIVE in Chrome
(computer-use):** auto overlay reads ascending-wedge BEAR with upward zones + ‹ ›/near selector; draw mode
enters, places snapped pivots (confirmed against the bar OHLC readout), structure renders, **candles stay
intact, zero console errors**.

Two bugs were caught + fixed only because of the live browser test: (1) seeding the coordinate-probe series
with the full 800-bar history **expanded the time scale and pushed the candles off-screen** → fixed by
seeding the probe with just 2 points at the candle's current visible times; (2) added sort/dedupe of pivot
times so an out-of-order or same-bar click can't throw. Redeployed each fix (LF + restart, `/health` 200).

### Still open after this session
- **#B1** — reconcile the BUY/descending Wolfe with the Fib-method anchor against a real Ramana buy
  drawing (currently deferred, left untouched).
- **#4** — the edge backtest still un-run as a full survivorship-aware study (the PIT-honest probe showed no
  mechanical edge at confirmation → descriptive-only).
- **auto wave-count** still won't match his discretionary eye on every name (inherent — his pivots aren't
  zigzag pivots). Manual draw mode is the answer; a fractal-pivot auto-detector could *narrow* the gap later.
