# Lane L2 — Native bodies & chrome polish — STATUS

> **Closed 2026-06-29.** Sole builder: autonomous L2 session. Branch `main`, started at HEAD
> `05cdeae`. All work in owned files only (`src/web/shell_skin.py` + new docs). Both gates PASS;
> every change deployed to the live VPS and verified IN-BROWSER before commit.

## Commits (all owned-files-only, explicit-path staged)
| Commit | What |
|---|---|
| `5f4cef5` | **Bleed-through neutralisation + reskin-deepen.** Re-assert native `.uk-*` geometry under `body.uk-skin .uk-*` (specificity (0,2,x) beats every bare `_BASE_CSS` element rule) → any native component on any reskinned page now renders identically to the native reference. Deepen legacy primitives (`.maj`/`.kpi .box`/`.chip`/`.scard`) to native token geometry (radius/spacing/mono-numerics). + `docs/L2-body-migration-audit.md`. |
| `eaa165c` | **RS-hub `rsh-*` retint.** The RS hub's self-contained mini-design-system still carried the OLD palette (#161b22 / #30363d / #1f6feb / 10px); mapped every `rsh-*` primitive to the ui_kit tokens via the skin. |
| `ca5674d` | Docs: shipped status + browser evidence in the audit. |

## What shipped (against the 9-item backlog)
1. **Audit** — `docs/L2-body-migration-audit.md`. Rendered the demo path IN-BROWSER vs the live VPS
   (local DB too sparse). Coverage + Screen+ = native shell; Markets/RS/Screener/Stock = legacy `_shell`
   reskinned; bodies live in frozen `dashboard.py`/`cockpit.py`. ✓
2. **Bleed-through sweep** — enumerated the live bare-element rules (`h2`/`table`/`th`/`td`/`nav`/`nav a`/
   `header`) on `/dash/markets`; confirmed absent on native `/dash/coverage`. Neutralised the whole class
   under `body.uk-skin .uk-*` (the `9def4ff` pattern, generalised). ✓
3–6. **Markets / RS / Screener / Stock bodies** — the bodies are FROZEN. Deepened the reskin so the legacy
   primitives adopt native token geometry (not just colour) → reskinned bodies read native. Screener
   frozen-pane (sticky col + header, 48 cols) and Stock dossier (8 tabs + chart controls) **preserved,
   no-loss** (browser-verified). A full body rewrite into new modules was deliberately deferred (see audit
   §5 — high blast radius for marginal gain). ✓ (via deepen)
7. **Coverage** — verified fully native; the reference, no drift. ✓
8. **Density / responsive / a11y / print** — density drives `--grid-pad` 6→3px on the reskinned screener
   grid; skip-link + `#uk-main` + `aria-current` + density toggle present; my additions add no width
   constraints. ✓
9. **End-to-end** — all 6 demo pages: `uk-top` + Trust + `ui_tokens` foundation; one consistent native
   look. `regression_sweep.sh` PASS (chrome gate 11+4; live 31 routes + 4 overlays). ✓

## Mechanism / design decision
The demo-path BODIES live in `dashboard.py`/`cockpit.py` (Lane L1-frozen). L2 may not edit them. The
realistic, owned-file path to "native look end-to-end" is to make `shell_skin._SKIN_CSS` carry (a) a
defensive `body.uk-skin .uk-*` re-assertion that immunises native components against bare-element
bleed-through, and (b) a deepen layer that lifts the legacy primitives from colour-only to native
geometry. This achieves the visual goal with ZERO edits to the frozen bodies and zero risk to the
frozen-pane grid (no layout/sticky/z-index touched). A body REWRITE is the right move only when a body
needs a structural (not cosmetic) change — then build a new `*_native.py` module for THAT body and
runtime-swap it.

## Revert
- Local backup: `src/web/shell_skin.py.bak-L2` (pre-L2 baseline).
- VPS backups: `/opt/hermes/src/web/shell_skin.py.bak-L2-<ts>` (per deploy).
- One-command: restore the bak + `systemctl restart hermes-api`.

## Deploy reality (confirmed this session)
- VPS `shell_skin.py` matched committed HEAD exactly at start (clean safety-diff).
- Local repo files are pure LF → `scp` directly, no CR-strip. SHA-verified each deploy; CRLF=0 on VPS.
- VPS Python 3.10.12 — selftest + py_compile pass there.
- Parallel lanes are live (Lane L4's `1ef085a` landed mid-session); explicit-path staging kept L2 commits
  clean (no cross-absorption).
