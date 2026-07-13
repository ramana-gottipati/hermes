# Screener consolidation — merge plan (Screen → Screen+)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the Screen+ merge ships + the dedup lands. Registered in `docs/DOC_INDEX.md`.


> **Created 2026-06-29.** SCREENER-CONSOLIDATION lane. Owner directive: make **Screen+**
> (`/dash/screen2`) the canonical screener — keep its cleaner confluence layout + saved-screens
> + CSV + group toggles, but give it the **pictorial richness** of the original **Screen**
> (`/dash/screener`), fix its **off-green**, and **de-dup** the "Screen+" entry that reads as a
> peer card under Strategies. Studied IN-BROWSER side-by-side (computed styles + screenshots),
> not from HTML.
>
> Owned files: `src/web/screener_plus.py`, `src/web/strategist_view.py` (+ `ui_tokens.py` only if a
> shared token, which it is NOT — see §3). **Do NOT touch `dashboard.py`/`cockpit.py`** — read-only
> to learn the graphics; the orchestrator is fixing Screen's "Near-P" column in parallel.

---

## 1. What the original Screen (`/dash/screener`) does BETTER — the visual character

Studied live at `localhost:8000/dash/screener` (tunnel). The defining difference is **"the
instrument"** (dashboard.py §"D54 Phase 2, D-UI-16"): every column-group **leads with a
self-contained inline SVG / glyph micro-viz** that turns the buried numbers into a *scannable
shape*, with the raw sortable values kept beside it (data-first). In-browser I counted **156
`svg.mv` instruments + the heat strip** on Screen; Screen+ rendered **0 SVGs, 0 heat strips**
(`svg_count:0, mv_count:0, has_hstrip:false`). That gap IS the "superior pictorial presentation".

The instrument vocabulary (all in `dashboard.py`, except `_mv_adbar`/`_mep_pill` in `cockpit.py`):

| Instrument | Fn | Group | What the shape encodes |
|---|---|---|---|
| **DVPT-vs-power ladder** | `_mv_ladder(dvpt,p1,p2,p3,p6,p12)` | Positioning · DVPT | track + 5 notches (P1M…P12M; green notch = beaten by today's DVPT) + green fill to today + ▲ marker. "how hard it crossed its own power baselines" as one bar. |
| **Launch-band gauge** | `_mv_keyband(gap)` | Key price | ±15% axis with the **−1…+5% launch band shaded green** + a coloured marker (green in-band / amber extended / blue discount) at gap-to-key-3m. |
| **Character triglyph** | `_mv_triglyph(tcr,duo,hh)` | Character | 3 diverging micro-bars: WHO (trade-count concentration) · WAY (delivery up/down skew) · CTX (distance from 52w high). Right/green = the accumulation lean. |
| **RS spark** | `_mv_rsspark(b1,b3,b6,b12)` | Relative strength | tiny polyline of the rs-vs-broad slope trajectory 12m→1m; green rising / red falling. |
| **MEP accum/distrib bar** | `_mv_adbar(score)` | Accumulation · MEP | centre=0; green-right = accumulation, red-left = distribution; clamped ±2. |
| **Multi-TF heat strip** | `_rs_strip(s1,s3,s6,s12,s18,s24)` | RS / Structure | coloured cells `1m 3m 6m 12m [18m 24m]` with ▲/▬/▼ glyphs; green up-bands, amber flat, red down-bands. |

Other Screen strengths Screen+ already matches or can keep light: grouped header band
(group → columns, two-row thead), colored verdict pills (MEP phase pill, trend pill), frozen
header + frozen Symbol column, per-cell value tints (`h-pos*`/`h-neg*`).

**Verdict:** Screen+ has the better *structure* (confluence lead column, group show/hide chips,
saved screens, CSV, Pat bridge). Screen has the better *texture* (the six instruments). Merge =
Screen+'s structure + Screen's instruments, retinted to the institutional value palette.

## 2. The GREEN problem — root cause (computed-colour proof, in-browser)

Owner: Screen+'s green "looks different and less appealing." Probed the live computed styles:

| Element (Screen+) | Computed colour | Token |
|---|---|---|
| Confluence count `td.confl.c4/c5/c6` text | `rgb(52,224,214)` | `--accent-cy` **#34e0d6 (CYAN)** |
| Confluence dots `.cd.on` background | `rgb(52,224,214)` + cyan glow `box-shadow` | `--accent-cy` **#34e0d6 (CYAN)** |
| (reference) up-pills, value-positive everywhere | `rgb(63,212,134)` | `--up` **#3fd486 (value green)** |

On Coverage, **`--accent-cy` is used as text colour exactly 0 times** — the cyan is a
confluence-only stylistic outlier. The institutional positive tint sitewide is `--up #3fd486`.
The bright aqua `#34e0d6` on the lead column is what reads as the "off, less appealing" green.

**Fix (within screen2's OWN `_CSS`, NOT a global token change):** repoint the confluence count
text (`.c3/.c4/.c5/.c6`) and the active dots (`.cd.on`) from `var(--accent-cy)` → `var(--up)`,
and soften the neon glow to a subtle value-tint. The ported instruments are authored in
`var(--up)`/`var(--down)` from the start (not the legacy GitHub `#2ea043`/`#3fb950`), so the
whole surface speaks ONE green. `ui_tokens.py` is left untouched — this is not a shared-token bug,
it's a local misuse of `--accent-cy`. (Brief rule: prefer fixing within screen2's CSS; flag, don't
risk, a global change.)

## 3. De-dup the Strategist board

`strategist_view.py._sub()` listed **"Screen+" → /dash/screen2** as a peer item in the *Strategies*
sub-nav (and the old sub-nav also duplicated several Markets/legacy labels). Screen+'s home is the
**Screener** altitude (per `lens_registry`: `Lens("screen2","Screen+",scope="screen",altitude="screener")`).
Listing it under Strategies makes it read as a second screener living in the wrong place.

**Fix:** rewrite `_sub()` to match the **registry's Strategies altitude** (Strategist · Conviction ·
Accumulation{Positioning,MEP} · Structure · Credibility · Growth · Launchpad) and **drop the
"Screen+" peer entry**. Screen+ is reachable from its own Screener sub-nav. (No cross-link card is
needed; if one is ever wanted it must read "open in Screen+ →", never a peer.) Done via the
registry helper so it cannot drift again.

## 4. Promotion-readiness

Screen+ already proves family-parity at `/dash/screen2?parity=1` (8/8 legacy analytic families +
confluence/Wolfe/pt14 cross-lens; checklist 9/10, the 10th = the nav flip). After this lane it ALSO
matches Screen's pictorial richness and speaks the institutional palette — so it is the strictly
better, complete surface. **The nav flip (making `/dash/screen2` the default Screener) stays the
orchestrator's call via `lens_registry`** — this lane does NOT reroute the sacred `/dash/screener`.

## 5. Non-negotiables honoured

- IN-BROWSER verify (computed styles + screenshot, dedicated tab) before claiming done.
- `regression_sweep.sh` + `chrome_gate.py` PASS before every commit; revert from `*.bak-screener` on red.
- Deploy: safety-diff → backup `*.bak-screener` → scp LF (CR=0) → VPS py3.10 import-test → restart
  hermes-api → health 200 + curl `/dash/screen2`,`/dash/strategist` → in-browser verify.
- Commit ONLY owned paths (`git diff --cached --name-only` == exactly my files); never `git add -A`;
  never stage dashboard.py/cockpit.py. A foreign path is a HARD STOP.
- Descriptive-only; data-first (raw values stay beside every instrument).
- VPS is py3.10 → **no backslash inside f-string expressions** (lane-a2 gotcha).

## 6. Implementation order

1. Port the six instruments into `screener_plus.py` as **self-contained local fns** authored in
   `--up`/`--down` (no import from dashboard/cockpit — keeps the parallel-ownership wall intact).
   Add an instrument cell at the head of each relevant group; keep every existing numeric column.
2. Fix the green in screen2's `_CSS` (confluence count + dots → `--up`).
3. De-dup `strategist_view._sub()` against the registry.
4. Gates → deploy → in-browser verify (screenshots + computed-colour proof) → commit owned-only.
