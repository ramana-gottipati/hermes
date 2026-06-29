# Lane M1 — Native chrome unification (single-row topbar on legacy pages)

> Make every legacy `dashboard._shell` page render the SAME top chrome as the native
> `ui_kit` pages: ONE single-row nav bar (`uk-top`: logo + altitude tabs + Trust inline +
> Ask-Pat ⌘K) + the contextual sub-nav (`uk-sub`), replacing the legacy two-row
> `hrow1`/`hrow2` header. Goal: `/dash`, `/dash/markets` and `/dash/strategist` are
> visually indistinguishable in the header.

## The problem (verified live, 2026-06-29)

Legacy pages (`/dash`, `/dash/markets`, every strategy lens) render through
`dashboard._shell` + `shell_skin.reskin`, which emits a **two-row header**:
- `hrow1` = green-"e" `pat·e·arn` brand + a `uk-trustlink` Trust chip + an Ask-Pat hint
- `hrow2` = `.v2bar` (the `_wrapped_nav` output): a justified `.wsnav` of altitude tabs + a
  `.v2util` cluster (Ask Pat; Trust de-duped out)
- `hrow3` = the `.v2subnav`

Native pages (`/dash/strategist`, `/dash/coverage`) render through `ui_kit.shell` with a
clean **single-row** `uk-top`: cyan-dot `patearn` logo + `uk-nav` tabs **with Trust as the
last inline tab** + a single `uk-cmdk` hint, then `uk-sub`.

Result: two different products — different tab alignment, Trust in a different place
(top-row chip vs inline tab), green-e vs cyan-dot logo, justified vs left tabs.

## The fix (converge on ONE renderer)

In `shell_skin.reskin(html, active)` — thread `active` from the wrapped `_shell` call —
detect the legacy `<header>…</header>` block and REPLACE it with the native header,
produced by reusing the native renderers so the two paths converge on ONE header:

```
ui_kit.topbar(alt, nav_html=ui_kit.nav_links(v2_surfaces.site_nav(active)))   # uk-top
+ v2_surfaces.native_subnav(active)                                            # uk-sub
+ ui_kit.cmdk_overlay()                                                        # ⌘K (re-inject)
```

`site_nav(active)` already returns Trust as the **last inline nav item** (exactly the
native behaviour) → Trust appears inline with the tabs, exactly once. The new
`native_subnav(active)` renders the registry-driven `_IA_SUB` for the page's altitude as
`uk-sub` markup (markets → its lenses, etc.) — the SAME source the native sub-nav reads.

Inject `ui_kit.css()` into the legacy `<head>` so the `.uk-top/.uk-nav/.uk-sub` rules
(all top-level selectors, not `.uk`-scoped) style the header identically even though the
legacy body is not wrapped in `.uk`. The body retint (`uk-skin` + skin CSS) is unchanged —
cards/tables/data keep the v2 palette.

Removing the whole `<header>` drops the old `_V2NAV_CSS` (`.v2bar`/`.wsnav`/`.v2subnav`)
and the `uk-trustlink`/`v2util` Trust duplication WITH it — killing the justified-tabs
anomaly and the double-Trust in one move. The back button (`hback`) is dropped too:
native pages have no back affordance, so dropping it is required for true parity.

Properties (unchanged house rules): DEFENSIVE (any failure → original html, never 500) ·
IDEMPOTENT (the `uk-skin v1` marker) · NO-LOSS (body + data + sacred routes intact;
every nav destination preserved via `site_nav` + `_IA_SUB`) · ADDITIVE + REVERSIBLE
(restore `*.bak-m1`, restart).

## Backlog (self-driven)

1. **Emit the native `uk-top` topbar on legacy pages** — replace `hrow1`/`hrow2` with
   `ui_kit.topbar(alt, nav_html=site_nav(active))`. Thread `active` through `reskin`. ✅
2. **Render the contextual `uk-sub` sub-nav on legacy pages** — new
   `v2_surfaces.native_subnav(active)` from the lens registry (`_IA_SUB`), so markets
   shows its lenses exactly like native. ✅
3. **Correct altitude highlight per page** — reuse `_altitude_of(active)` for the tab +
   `_SUB_ALIAS` for the sub-nav item; dossier (`active="stock"`) claims nothing. ✅
4. **Single inline Trust** — Trust is the last `uk-nav` item (from `site_nav`); the
   top-row `uk-trustlink` and the `v2util` Trust both vanish with the old header. ✅
5. **Responsive / hamburger parity** — the native `uk-top`/`uk-nav`/`uk-sub` @media
   rules (≤640px: scrolling nav, compacted cmdk) now apply to legacy pages too, since
   they render the same markup + `ui_kit.css()`. ✅
6. **Sweep EVERY nav route** — chrome_gate (updated marker: `uk-top` is the new single-row
   nav marker, replacing `v2bar`) + regression_sweep BOTH PASS; header identical across
   `/dash`, `/dash/markets`, `/dash/strategist`; page body + data intact; zero regression. ✅

## Gate-contract note (necessary, flagged)

`scripts/chrome_gate.py` asserted `class="v2bar"` as the "v2 nav rendered" marker on
legacy pages. This lane deliberately replaces `v2bar` with the native `uk-top` on legacy
pages, so that marker is updated to `class="uk-top"` (the new single-row nav marker). The
gate stays fully meaningful — it still catches a silent revert to legacy chrome
(`uk-skin` body retint, `no .hsearch` search-swap, `Trust`/`Wire` nav completeness all
unchanged) and now additionally asserts true header unification. This is the one edit
outside the M1-owned set (`shell_skin.py`/`ui_kit.py`/`v2_surfaces.py`); it is required
because a gate that asserts the very anomaly M1 removes would block the fix. Flagged in
the wrap report.

## DO-NO-HARM (every change)

safety-diff → backup `*.bak-m1` → scp (LF) → VPS import-test → restart hermes-api →
`bash scripts/regression_sweep.sh` AND `python scripts/chrome_gate.py` BOTH PASS → verify
live that `/dash`, `/dash/markets`, `/dash/strategist` share an identical header (curl +
grep the header markup is the same shape) → commit ONLY owned files. Gate FAIL → revert
from `*.bak-m1`, re-verify green, STOP + report. Sacred routes
(`/dash/ratio`,`/dash/rrg`,`/dash/compare`) intact.
