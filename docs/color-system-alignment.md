# Colour-system alignment — DECISIONS & plan

**Status:** Phases 0–4 SHIPPED. Phase 4 (S65) = de-triplicate `ui_kit`/`shell_skin` → reference
`:root` (D-COL-10); categorical remainder → `--series-4` (D-COL-8/9). Remaining is the
informational directional backlog in `dashboard.py`/`stock_chart.py` (Phase-1 tail) + the
deliberately-hex canvas/categorical leaves; retirement of redundant `shell_skin` remaps deferred.
**Owner doc.** Scrutinised by a 6-lens red-team + a 435-site context-aware inventory (2026-07-01).
Decisions here are deliberate — surface conflicts before overwriting.

---

## 1. The problem (verified, not asserted)

The UI carries **two palettes**. The agreed tokens live on `:root` in `src/web/ui_tokens.py`
(`--up #3fd486`, `--down #ff6a7a`, `--warn #f6b73c`, `--accent #4d9dff`, surfaces/lines/ink).
A legacy **GitHub-dark** set (green `#3fb950`/`#2ea043`, red `#f85149`, amber `#d29922`,
bg `#0d1117`/`#161b22`, blue `#58a6ff`/`#1f6feb`…) is still emitted directly in page bodies.

`shell_skin.py` retints legacy **classes** at runtime, but **structurally cannot reach**:
- **inline `style="color:#…"`** (inline wins the cascade) — 134 sites
- **SVG `fill=`/`stroke=` attributes** (`var()` is invalid in a presentation attribute, fails silently) — 37 sites
- **canvas / lightweight-charts JS literals** (CSS vars never apply to canvas) — 44 sites

**Inventory (435 colour sites):** 93 directional (75 up + 18 down) · 58 categorical · 49 bg ·
44 accent · 37 line · 77 ink · 28 warn · 8 cred · 6 status · 2 brand · 2 gradient.
**By file (top):** dashboard 83 · rsband_view 66 · rrg_view 36 · cockpit 35 · wolfe_view 24 ·
stock_chart 21 · testing_view 18 · growth_view 16.

**Deeper root cause:** the palette has **no single referenced source of truth** — it is copied
as raw hex in three foundation files (`ui_tokens.py :root`, `ui_kit.py .uk` scope, `shell_skin.py`)
and re-emitted ad-hoc in ~17 body files. They agree only by manual discipline.

**Exemplars already exist:** `screener_plus.py` (`_UP`/`_DOWN` = `var()` consts) and
`strategist_view.py` (`.st-*`/`.wc-*` all `var()`) are the target pattern the other files lack.

---

## 2. The mapping rule — by SEMANTIC ROLE, never by hue

A naive "every green→--up, every red→--down" is **wrong** (verified): it would miscolour brand,
categorical, status, and gradient greens/reds. Colour is chosen by the site's **role in context**:

| # | Role | Token | Hard rule |
|---|------|-------|-----------|
| 1 | **DIRECTIONAL / value** — gain/loss, +/−, bull/bear, accum/distrib, `.cp-bull/.cp-bear`, candle up/down, directional border/bg | `--up`/`--down` (tints via `rgba(var(--up-rgb),a)`) | The value contract. **Phase 1.** |
| 2 | **CATEGORICAL** — multi-series palettes (`_COMPARE_PALETTE`, 21-colour `_RRG_PALETTE` sector identity), scorecard category (`.sc-*`) | `--cat-*` / `--series-*` | **NEVER** `--up`/`--down`, even when the legacy hex is green/red. |
| 3 | **BRAND** — wordmark "e", PWA icon | `--accent`/brand | Never `--up`. |
| 4 | **GRADIENT / threshold ramp** (e.g. the P1M…P12M amber ramp) | deliberate ramp | Documented; endpoints may reuse value tokens. |
| 5 | **STATUS / HEALTH** — present/absent/enabled (`.b-on/.b-off/.b-neu`, CCI freshness) | `--ok`/`--off`/`--neu` | Aliased to value hues but NAMED apart so the gate never treats a status pill as a verdict. |

**Verified carve-outs (block any hue-keyed swap):** `_COMPARE_PALETTE[2]/[3]` (categorical),
`.scard.sc-RS` (was the live bug — see §4), `.b-on/.b-off`, RRG quadrant, `#f0883e` orange
(DISTRIB/Launchpad — categorical, not `--down`).

---

## 3. RRG quadrant ruling (was the open blocker)

**DECIDED: directional.** Leading=`--up`, Lagging=`--down`, Improving=`--accent`, Weakening=`--warn`.
The two transition quadrants get distinct non-value hues (blue/amber), preserving the cyclical
read (Lagging→Improving flips red→blue). The codebase contradicted itself — `rotation_view.py`
already does exactly this with canonical tokens, while `rrg_view.QCOLOR` + `mini_rrg._QCOLOR`
(byte-identical duplicates) use legacy hex. **Reconcile `rrg_view`/`mini_rrg` to `rotation_view`.**
No new `--q-*` tokens. (Quadrant fills are fill-only directional → keep the existing text labels
as the colour-blind redundancy.)

---

## 4. Tokens added (Phase 0)

| Token | Value | Why |
|---|---|---|
| `--up-rgb` / `--down-rgb` / `--warn-rgb` | `63,212,134` / `255,106,122` / `246,183,60` | Build any-alpha tints from ONE source: `rgba(var(--up-rgb),.08)`. Kills the heat-cell / zone-fill / canvas rgba drift. |
| `--ok` / `--off` / `--neu` | `#3fd486`/`#ff6a7a`/`#f6b73c` | STATUS role, named apart from the value contract. |
| `--on-accent` | `#06121f` | Foreground on `--accent` fills (was an orphan literal, 6+ uses). |
| `--cat-rs` | `#34e0d6` (cyan) | Scorecard RS category — a hue distinct from the value green, so the card border can't read "bullish". |

Deferred to later phases: `--series-1..N` (categorical chart palette), `--accent-orange`
(`#f0883e` DISTRIB/Launchpad), per-state rotation badge tints.

---

## 5. Mechanism caveats (the part `var()` alone doesn't solve)

| Mechanism | Approach |
|---|---|
| CSS class + inline `style=` | rewrite the emit site to `var(--token)` |
| **SVG `fill=`/`stroke=`** | emit `style="fill:var(--up)"` (the attribute form fails silently) |
| **canvas / lightweight-charts** | seed the WHOLE `C` colour object once from `getComputedStyle` — never a partial 2-of-25 migration |
| **rgba tints** | `rgba(var(--up-rgb),a)` |
| **print** | `ui_tokens` print block re-pins `.pos/.up→#137a43`, `.neg/.down→#b22433`; any new directional class needs a print rule |
| **standalone exports** (`replay-the-tape`, dossier, PWA icon, offline page, `cmdk_overlay`) | self-contained by design — hand-align hex to token VALUES + allowlist; do not tokenize |

---

## 6. Phasing

- **Phase 0 — foundation (SHIPPED):** add the §4 tokens; fix the live `sc-RS` bug; build
  `scripts/color_gate.py` (ratchet) + wire into `regression_sweep.sh`. Nothing visual changes
  except the one `sc-RS` border (green→cyan).
- **Phase 1 — directional (the user's pain):** migrate the **93 directional sites** in the
  un-migrated files to `var(--up)`/`--down` (incl. rgba tints, SVG→`style=`, box-shadows, the
  2 canvas candle keys), matching the exemplars. Reconcile RRG to `rotation_view`. Add each file
  to the gate's `MIGRATED` list as it lands (the ratchet).
- **Phase 2 — surfaces:** backgrounds + hairlines → `--bg-*`/`--line-*`.
- **Phase 3 — rest:** accent/ink/amber/cyan/purple; the full canvas `C` object; categorical
  `--series-*`; status `--ok/--off/--neu`.
- **Phase 4 — de-duplicate + retire:** make `ui_kit`/`shell_skin` REFERENCE the tokens instead
  of re-hardcoding; retire now-redundant shell_skin remaps (audit each — a retired `.sc-RS`
  must restore `--cat-rs`, not `--up`; migrate shell_skin's residual `#1f6f3a`/`#8f1f1f` first).

---

## 7. The gate (`scripts/color_gate.py`)

A **ratchet**, run in `regression_sweep.sh` (Gate 1c), clean-checkout/in-process:
1. **tokens present** — canonical + Phase-0 tokens defined in `ui_tokens.py`.
2. **sc-RS regression lock** — `.scard.sc-RS` must not be the value `--up` hex.
3. **migrated files clean** — files in `MIGRATED` carry NO legacy directional hex/rgb; the list
   GROWS each phase, locking in gains.
4. **backlog (informational)** — prints the legacy-directional count left in un-migrated bodies
   (Phase-0 baseline: **213** across 14 files) so the shrinking number is always visible.

False-positive handling: scanning is **tokenize-based** (only Python STRING-token contents), so
a hex in a `#` comment / docstring never trips it; foundation files (which hold palette values)
are excluded from the directional scan.

---

## 8. Decisions log
- **D-COL-1** Map by semantic role, never by hue (§2). Five roles incl. a new STATUS role.
- **D-COL-2** RRG quadrant = **directional** (§3); reconcile to `rotation_view`; no `--q-*` tokens.
- **D-COL-3** `sc-RS` → `--cat-rs` cyan (decouples category from the value green).
- **D-COL-4** Canvas: seed the whole `C` object from `getComputedStyle`; no partial migration.
- **D-COL-5** `--veto-bg` etc. derive from `rgba(var(--down-rgb),a)`; no separate pinned token.
- **D-COL-6** Standalone exports stay self-contained (hand-aligned + allowlisted), not tokenized.
- **D-COL-7** Colour-blind safety = preserve existing sign/arrow redundancy; forbid NEW fill-only
  directional surfaces without a non-colour channel.
- **D-COL-8** (Session 65) The **categorical greens** `gw-cr` / testing-benchmark / `kt-in` →
  `var(--series-4)` (the ramp green), never `--up` (role #2). `shell_skin .gw-cr` split out of the
  `.gw-pos` directional group for the same reason.
- **D-COL-9** (Session 65) **`_COMPARE_PALETTE` (dashboard) is LEFT as curated canvas hex**, same
  ruling as the 21-colour `_RRG_PALETTE` (§2). Both feed **lightweight-charts (canvas)** where
  `var()` fails silently, and neither `/dash/compare` nor the RS-overlay is covered by the gate's
  4-route render check — so a `getComputedStyle` var-resolver would add silent-fail risk to two
  live hot paths for a LOW-value recolour. Likewise **`_fq/_qc` F&O state dicts** (alpha-suffix
  concatenation `{c}55` / `{c}14` — no `--*-rgb` token, breaks under `var()`) and the non-directional
  **`.sc-POS/.sc-QUAL/.sc-CPR`** borders (blue/amber/purple — not backlog, already `--cat-rs` for RS)
  stay hex. These remain categorical false-positives in the informational backlog by design.
- **D-COL-10** (Session 65, Phase 4) **De-triplication = make `ui_kit` + `shell_skin` REFERENCE
  `:root`, NOT delete runtime remaps.** `ui_kit`'s `.uk` local token block was a byte-identical
  (but UNGUARDED — the selftest never asserted it) shadow copy of `:root` → deleted (self-ref
  `var()` would cycle); the one standalone consumer `coverage_view._memo_shell` (which included
  `ui_kit.css()` WITHOUT `:root`) now prepends the foundation, with a `body::after{content:none}`
  print rule so the memo PDF is byte-unchanged. `shell_skin`'s exact-match hexes → `var()`
  (colour-identical; `:root` always injected on skinned pages via `skin_css`); no-exact-token
  nuances (theme-chip blues, 2 surface tints, aurora/header rgbas) stay hex. **Retiring** remaps
  (removing a rule so `_BASE_CSS` wins) is deliberately **NOT done** — it depends on dashboard.py's
  per-class migration being deployed, fragile against the known VPS `dashboard.py` drift (S64),
  and would silently regress colours a 200 hides. The one critical retire-hazard (`.sc-RS`→`--up`,
  D-COL-3) is already safe: `.sc-RS`=`--cat-rs` in both `_BASE_CSS` and `shell_skin`.
