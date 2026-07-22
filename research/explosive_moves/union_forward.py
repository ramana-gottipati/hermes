"""UNION FORWARD — the forward-test-day runner for the union sibling family (S181).

WHAT THIS IS. One command that makes the 2026-10-03+ forward-test day mechanical. It
exec-loads `union_ladder_val.py`'s engine byte-for-byte (the S176 sealed-validation
implementation whose reproduction gate ran 5/5 to the digit, ledger 16AL) — everything
above that module's print battery — and adds ONLY reporting: no new selection logic, no
new levers, no spec change. Sealed files untouched.

Run (box, read-only):
    /opt/hermes/.venv-research/bin/python union_forward.py /opt/hermes/data/hermes.db
    ... union_forward.py /opt/hermes/data/hermes.db --asof 2026-10-03
(plain python works too — the engine is stdlib-only). Before an official checkpoint,
refresh the TRI/G-sec CSVs via `niftyindices_hist.py` (manifest `indexes_tri`,
pull-on-demand) — this runner warns if they look stale but does not fetch.

WHAT IT PRINTS, in order:
  1. REPRODUCTION GATE (mandatory): all SIX ladder rows re-run and gated TO THE DIGIT on
     the 16AS drift-proof anchors — computed over legs ending <= GATE_END (2026-04-01),
     the input-closed prefix that data arrival cannot move (isdead()'s 60-session forward
     window past the 2026-07-01 boundary leg stays open until ~late Sep 2026). The
     seal-time full-period headlines (16AL gate + lab4's A1) are printed BESIDE with the
     known drift disclosed (the 16AQ corporate-actions repair moved the adjusted archive;
     16AR). Any anchor miss -> STOP: legs in the gate window only move if the engine or
     the archive was EDITED. Recorded-repair loop: --derive-anchors -> ledger entry ->
     embed same-commit (S183 policy, ledger 16AS).
  2. THE FORWARD WINDOW: every completed engine leg from the 2026-07 quarter onward
     (see BOUNDARY below), per-leg returns for each book beside Nifty 500 PR, Next 50 PR,
     and the TRI twins; cumulative + annualized when >=4 legs; alpha/beta vs N500 PR and
     vs N500 TRI (>=6 legs); MaxDD (quarterly marks, same convention both sides);
     inv%; and the two prints this runner owes the estate:
       - MEDIAN PICK-ADV per forward rebalance + overall (owed since 16AJ; run5 never
         computed it — recomputed here from the same QUAL/hook/topn selection line).
       - A2-COMPOSITE CLEAN-TR (full-period tr=True run — union-ladder.md §5 carries
         "not separately run" until this prints; K30's tr=True run beside it must
         reproduce the recorded 27.3%/16AF as the same-code-path cross-check).
  3. THE FOUR FROZEN CRITERIA per SEALED spec (verbatim from the four preregs, all four
     specs carry the same criteria; A1/A2 are RECORDED leads, reported beside but
     excluded from adjudication):
       C1 forward CAGR > Nifty Next 50 buy-and-hold (PR, as frozen; TRI printed beside),
       C2 forward alpha > 0 (vs Nifty 500, quarterly regression x4; beta reported;
          excess that is purely beta > 1.1 = FAIL),
       C3 forward MaxDD not worse than Next 50's over the same window,
       C4 no single quarter > 60% of the total excess (fail -> INCONCLUSIVE, extend).
     With < 8 completed forward quarters the verdict line is INTERIM (n/8) — the preregs
     judge only at >= 8. At >= 8 the FAMILY ADJUDICATION fires mechanically: among sealed
     passers the highest forward ALPHA graduates, the rest retire; none pass -> all
     DESCRIPTIVE-ONLY. Seals: union a9a14058 / b14 08b46199 / c40ra 0715a0d9 /
     composite30 07ef2ef9 (docs/prereg/*.md).
  4. THE PORTFOLIO DIAL on the forward window (16AN fold): K30 and A2 mixed with the
     long G-sec leg at 100/0 / 90/10 / 80/20 / 70/30, quarterly-rebalanced fixed weights
     — the measured CAGR<->survivability dial rides into every checkpoint until Ramana
     picks the policy point (docs/portfolio-layer-design.md).

BOUNDARY (encoded once so no future session re-derives it). All four preregs freeze
"every NEW quarter from 2026-07 onward", registered 2026-07-16. The engine's own
rebalance calendar defines the quarters. Two cuts are printed:
  - PREREG CUT (the judged one): legs starting at the LAST rebalance <= 2026-07-16 —
    that leg IS the 2026-07 quarter; its picks were fixed by the frozen rule before the
    seal, its return accrues almost entirely after it.
  - STRICT CUT (audit twin): legs starting at the FIRST rebalance AFTER 2026-07-16 —
    zero pre-seal overlap of any kind. Printed beside so nobody has to argue about the
    few pre-seal days inside the boundary leg.
Criteria are judged on the PREREG cut per the preregs' own wording.

CAVEATS THAT RIDE INTO THE JUDGMENT (printed with the rows):
  - era-floor flag (16AL C2b): the floor rung failed the <=2018 re-derivation
    (P_train 0.268 vs sealed 0.450) — the family's highest window-fit risk; first
    suspect if A1/A2/K30 forward rows disappoint.
  - deflated forward expectations (16AL C3, Bailey-LdP deflation at N_trials=69):
    U 15.7 / B14 16.6 / C40 18.1 / A2 21.0 / K30 21.6 — the honest priors, printed
    beside every headline until the forward window speaks.
  - sealed criteria stay PR-vs-PR as frozen; TRI columns are measurement beside them
    (16AJ). Book TR accrual is a LOWER bound (16AD: ~34% pre-2012 dividend parse).
Descriptive research on paper portfolios; not advice; nothing here deploys anything.
"""
import os as _os, sys

# ---- CLI: [DB] [--asof YYYY-MM-DD] [--derive-anchors]; strip flags before the engine reads sys.argv ----
ASOF = None
DERIVE = False
_argv = [sys.argv[0]]
_it = iter(sys.argv[1:])
for _a in _it:
    if _a == "--asof":
        ASOF = next(_it, None)
    elif _a.startswith("--asof="):
        ASOF = _a.split("=", 1)[1]
    elif _a == "--derive-anchors":
        DERIVE = True
    else:
        _argv.append(_a)
sys.argv = _argv

# ---- exec-load the sealed-validation engine (everything above its print battery) ----
_src = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "union_ladder_val.py")
_c = open(_src, encoding="utf-8").read()
_head = _c[:_c.index('\nprint("=" * 118)')]
# --- additive toggles for the 3 sealed HOLD/DEEP siblings (16BD/16BE/16BF). With HOLD_BAND=0 and
#     TURN_LO=30 (the defaults) the SIX ladder rows run BYTE-IDENTICAL, so the reproduction gate is
#     unchanged. The sealed engine file union_ladder_val.py is NOT edited — only this runner's exec. ---
_head = _head.replace("def rsi_of_rs_recovery(s, sec, i):", "TURN_LO = 30\ndef rsi_of_rs_recovery(s, sec, i):", 1)
_head = _head.replace("r = prev < 30 and now >= 30", "r = prev < TURN_LO and now >= 30", 1)
_head = _head.replace("sel = (hook or sel_a2c)(QUAL[fmode][d], d, i, topn)[:topn]",
                      "sel = _sib_sel(hook, QUAL[fmode][d], d, i, topn, held)", 1)
HOLD_BAND = 0
def _sib_sel(hook, q, d, i, topn, held):
    ranked = (hook or sel_a2c)(q, d, i, topn)
    if not HOLD_BAND:
        return ranked[:topn]                       # HOLD_BAND=0 -> identical to the sealed selection
    band = set(ranked[:HOLD_BAND]); pos = {s: p for p, s in enumerate(ranked)}
    keep = sorted([s for s in held if s in band], key=lambda s: pos[s])
    out = keep[:topn]
    for s in ranked:
        if len(out) >= topn: break
        if s not in out: out.append(s)
    return out[:topn]
exec(compile(_head, _src, "exec"), globals())
# --- run the 3 sealed HOLD/DEEP siblings once (K30-HOLD 16BD e6994c19 · A2-HOLD 16BD 17e0dd1a ·
#     K30-DEEP-HOLD 16BF b705f770). QUAL["pf1"] is rebuilt+cached per TURN_LO and restored to 30 after. ---
_qcache = {30: QUAL["pf1"]}
def _set_turn(tl):
    global TURN_LO
    if tl not in _qcache:
        TURN_LO = tl; globals()["_turn_memo"] = {}
        _qcache[tl] = {d: qualify(d, "pf1") for d in rebal_all}
    QUAL["pf1"] = _qcache[tl]
SIBS = [  # (name, base cfg, TURN_LO, HOLD_BAND top-2N, seal8, recorded in-sample flat CAGR)
    ("K30-HOLD",      dict(fmode="pf1", topn=30, rf_cash=True, weights="drift"), 30, 60, "e6994c19", 27.2),
    ("A2-HOLD",       dict(fmode="pf1", topn=40, rf_cash=True),                  30, 80, "17e0dd1a", 26.6),
    ("K30-DEEP-HOLD", dict(fmode="pf1", topn=30, rf_cash=True, weights="drift"), 20, 60, "b705f770", 27.5),
]
SIB_RUNS = {}
for _sn, _sc, _stl, _shb, _ssl, _sisf in SIBS:
    _set_turn(_stl); HOLD_BAND = _shb
    SIB_RUNS[_sn] = run5(**_sc)
_set_turn(30); HOLD_BAND = 0                        # restore defaults for the 6-row gate + all downstream code
# in scope now: run5/stat/stat_vs/bench_cagr_series/hook_union/hook_b14/sel_a2c/QUAL/adv/
# pym/ci/cal/N/rebal_all/iclose/BENCH/SLEEVE/TRI500/TRIN50/GSEC/gsec_q/BOOKS/GATE

REG = "2026-07-16"          # all four registrations sealed this day
MIN_Q = 8                    # preregs: judged only at >= 8 forward quarters
SEALS = {"U": "a9a14058", "B14": "08b46199", "C40": "0715a0d9", "K30": "07ef2ef9"}
DEFLATED = {"U": 15.7, "B14": 16.6, "C40": 18.1, "A2": 21.0, "K30": 21.6}   # 16AL C3
ERA_FLOOR_ROWS = ("A1", "A2", "K30")

# the sixth ladder row (union-ladder.md §4; recorded 16AE, unregistered)
BOOKS = dict(BOOKS)
BOOKS["A1"] = dict(fmode="pf", topn=40, rf_cash=True)
ORDER = ["U", "B14", "C40", "A1", "A2", "K30"]

# ---- anchors & gate policy (S183, ledger 16AS) ----
# GATE_SEAL = the SEAL-TIME archive's full-period numbers (ledger 16U..16AH; A1 from lab4 via
# union-ladder.md §4). The 16AQ corporate-actions repair (14 gold-ETF unit subdivisions
# backfilled — the sealed universe SELECTS gold ETFs, 16AR, owner task task_7a70ad77) plus
# normal data arrival legitimately moved the adjusted archive, so these seal-time values are
# PRINTED as provenance with the drift disclosed — never hard-gated.
# GATE = the drift-proof anchors (ledger 16AS): re-derived on the repaired archive over legs
# ending <= GATE_END. GATE_END sits one leg EARLIER than the seal boundary because isdead()
# reads 60 sessions past a leg's end — the (2026-04-01 -> 2026-07-01) boundary leg's dead-name
# window stays open until ~late Sep 2026 and can move with data arrival until then; legs
# through 2026-04-01 are input-closed and can only move if the archive itself is EDITED —
# exactly what a hard gate exists to catch. Re-derivation loop for any future RECORDED archive
# repair: run --derive-anchors, record a new ledger entry, embed the values here same-commit.
GATE_END = "2026-04-01"
GATE_SEAL = dict(GATE)
GATE_SEAL["A1"] = (25.6, 100.43)
# The gate compares the Rs1Cr MULTIPLE only: it is window-exact and convention-free (CAGR
# annualization conventions differ across the estate's printers), and at ~100x a 0.006
# tolerance is basis-point-of-terminal-wealth sensitivity. CAGR prints informationally in
# stat()'s convention.
# ANCHOR HISTORY (each set = a recorded archive repair; the re-derivation loop in action):
#   16AS (2026-07-17, post-16AQ gold-ETF splits): U 20.15 B14 26.01 C40 41.26 A1 87.70
#     A2 86.59 K30 101.06 — base books' seal-window mults reproduced EXACTLY then.
#   16AU (2026-07-17, post the 117-event orphan-cliff heal, audit_orphan_cliffs.py): the
#     un-quarantined names shift selections — base books dilute ~2% of terminal wealth
#     (U/B14/C40 down), K30 +2.6%; ladder order unchanged; seal-time records untouched.
#   16AW (2026-07-17, post the S187 official-archive resolution of the 64 AMBIGUOUS — 44
#     healed incl. ITC F=15/RUCHINFRA F=40): K30's headline lands back at 115.66x vs the
#     seal-time 115.69x (the 16AU drift and the S187 heals nearly cancel); PM_ANCHORS in
#     portfolio_mix.py cross-check EQUAL for K30/A2 (independent engine lineage).
#   16BG (2026-07-22, ETF-class CA drift): the S185-S189 mf-feed/orphan-cliff backfill ingested
#     174 ETF-class historical SPLITs (ex_date <= 2026-04-01) AFTER the 16AW anchors were set.
#     The era-floor books SELECT ETFs (16AR: NIFTYBEES etc.), so their input-closed legs
#     re-adjusted: A1 87.75->88.30 (+0.6%) A2 86.59->86.52 K30 100.73->100.19. The BASE books
#     (U/B14/C40, ETF-free) reproduce EXACTLY (unchanged). Legitimate recorded-class repair, not
#     corruption — every drifted CA is an ETF split. FIX: re-anchor the 3 era-floor books + give
#     them a tolerance BAND (they drift with each ETF-CA nightly; base books stay tight = the real
#     tamper-evidence). Investigated 2026-07-22 before re-anchoring (the gate demands it).
GATE = {"U": 19.62, "B14": 25.14, "C40": 39.75, "A1": 88.30, "A2": 86.52, "K30": 100.19}  # base unchanged; era-floor re-anchored 16BG
# sealed-era TR records (informational §5 anchors): K30 16AF / A2 16AO, seal-time archive
TR_REC = {"K30": (27.3, 131.80), "A2": (26.3, 113.65)}

if ASOF is None:
    ASOF = cal[-1]

print("=" * 118)
print("UNION FORWARD — checkpoint as of %s (registrations sealed %s; judgment at >= %d forward quarters)"
      % (ASOF, REG, MIN_Q))
print("=" * 118)

# ---- data freshness (warn, never fetch) ----
def _gap_days(d1, d2):
    from datetime import date
    a = date(*map(int, d1.split("-"))); b = date(*map(int, d2.split("-")))
    return (b - a).days

if _gap_days(cal[-1], ASOF) > 7:
    print("!! index_rows (PR benches) end %s — %d days before asof; check the nightly bhavcopy ingest"
          % (cal[-1], _gap_days(cal[-1], ASOF)), flush=True)
for _nm, _sd in (("TRI500", TRI500), ("TRIN50", TRIN50), ("GSEC", GSEC)):
    if _sd and _gap_days(max(_sd), ASOF) > 10:
        print("!! %s CSV ends %s — refresh via niftyindices_hist.py before an official checkpoint"
              % (_nm, max(_sd)), flush=True)
    elif not _sd:
        print("!! %s CSV missing — TRI columns will be blank" % _nm, flush=True)

# ---- 1. reproduction gate (sliced anchors; to the digit on the 16AS set, else STOP) ----
print("")
print("### 1. REPRODUCTION GATE (legs <= %s vs the 16AS drift-proof anchors; seal-time headline printed as provenance)" % GATE_END)
rb_all = list(rebal_all)
j_gate = max(i for i in range(len(rb_all) - 1) if rb_all[i + 1] <= GATE_END)
j_head = max(i for i in range(len(rb_all) - 1) if rb_all[i + 1] <= REG)

def slice_cm(navs, j):
    """CAGR/mult over legs 0..j — the exact prefix of the run (legs are prefix-deterministic).
    CAGR uses stat()'s convention (y = (len(navs)-1)/4 = j/4) so prints compare to the ledger."""
    mult = navs[j]
    y = j / 4.0
    return ((mult ** (1 / y) - 1) * 100 if j else 0.0), mult

RUNS = {}
for k in ORDER:
    o = run5(**BOOKS[k])
    RUNS[k] = o
    gc, gm = slice_cm(o["navs"], j_gate)
    hc, hm = slice_cm(o["navs"], j_head)
    if DERIVE:
        print("  derive %-4s gate(<=%s) CAGR %6.2f%%  mult %8.2fx   | headline(<=%s) %6.2f%% / %8.2fx"
              % (k, GATE_END, gc, gm, REG, hc, hm), flush=True)
        continue
    g_m = GATE[k]
    # base books (ETF-free) reproduce to the basis-point → tight; era-floor books legitimately drift
    # with the owner-ratified ETF-in-universe CA feed (16AR/16BG) → a 2% band, still catches real
    # engine/archive corruption (any engine bug hits the tight base books too).
    _tol = 0.02 * g_m if k in ERA_FLOOR_ROWS else 0.006
    ok = abs(gm - g_m) < _tol
    s_c, s_m = GATE_SEAL[k]
    print("  gate %-4s <=%s mult %8.2fx (anchor %.2f — see ANCHOR HISTORY above; latest ledger entry governs)  %s  [CAGR %5.2f%%] | seal-time headline %.1f/%.2f -> now %.1f/%.2f (drift disclosed: recorded archive repairs)"
          % (k, GATE_END, gm, g_m, "OK" if ok else "FAIL", gc, s_c, s_m, hc, hm), flush=True)
    if not ok:
        print("REPRODUCTION GATE FAILED — STOP. Legs through %s are input-closed: a miss means the ENGINE"
              " or the ARCHIVE was edited. If the edit is a RECORDED repair (16AQ-class), re-derive via"
              " --derive-anchors + a new ledger entry; otherwise investigate before reading any forward number." % GATE_END)
        sys.exit(1)
print("  universe note (16AR): the sealed universe (all EQ/BE/BZ series) selects ETFs, not just gold —")
print("  any-ETF 34/82(K30)/38/82(A2) rebals (NIFTYBEES x13-15 biggest, gold 9/10); DECIDED 2026-07-17")
print("  (task_7a70ad77): RATIFY seals + document (option b) — the frozen rule runs AS SEALED here, so a")
print("  forward selection MAY be an ETF; any ETF pick is flagged below. Exclusion effect <0.5pp (design")
print("  §7d(repro)); a clean-universe book, if ever wanted, is a NEW pre-registered sibling, not a seal edit.")

# ---- 1b. sibling reproduction (the 3 sealed HOLD/DEEP variants; forward-judged, no mult-anchor) ----
print("")
print("### 1b. SIBLING REPRODUCTION (16BD/16BF HOLD/DEEP variants; soft check vs recorded in-sample flat CAGR — forward-judged, not mult-anchored)")
for _sn, _sc, _stl, _shb, _ssl, _sisf in SIBS:
    _o = SIB_RUNS[_sn]
    _fc, _fm = slice_cm(_o["navs"], len(_o["navs"]) - 1)
    print("  %-14s seal %s  full-period flat CAGR %5.1f%% (recorded %.1f%%, %s)  [turn<%d, hold-band top-%d]"
          % (_sn, _ssl, _fc, _sisf, "OK" if abs(_fc - _sisf) < 1.2 else "drift-check", _stl, _shb))

if DERIVE:
    print("")
    print("### derive: sealed-era TR pair (end=%s)" % REG)
    for k in ("K30", "A2"):
        o = run5(tr=True, end=REG, **BOOKS[k])
        s = stat(o["navs"], o["bnavs"])
        print("  derive %-4s TR CAGR %6.2f%%  mult %8.2fx  div %d  MaxDD %6.2f%%  aPR %+6.2f/bPR %5.3f"
              % (k, s["cagr"] * 100, s["mult"], o["ndiv"], s["dd"] * 100, s["alpha"] * 100, s["beta"]), flush=True)
    print("")
    print("derivation complete — embed GATE (and refresh the §5 TR print's current-archive context) with a ledger entry, same commit.")
    sys.exit(0)

# ---- the boundary ----
rb = list(rebal_all)
j_pre = max(i for i, d in enumerate(rb) if d <= REG)            # prereg cut: last rebalance <= REG
j_strict = j_pre + 1                                            # strict cut: first rebalance after REG
legs_end = [i for i in range(len(rb) - 1) if rb[i + 1] <= ASOF] # completed legs by asof
fwd_pre = [i for i in legs_end if i >= j_pre]
fwd_strict = [i for i in legs_end if i >= j_strict]
print("")
print("### 2. THE FORWARD WINDOW")
print("  engine rebalances around the seal: ... %s | %s(=boundary) | %s"
      % (rb[j_pre - 1], rb[j_pre], rb[j_strict] if j_strict < len(rb) else "(next: not yet in data)"))
print("  PREREG cut (judged): legs from %s   -> %d completed forward quarter(s) by %s"
      % (rb[j_pre], len(fwd_pre), ASOF))
print("  STRICT cut (audit) : legs from %s -> %d completed forward quarter(s)"
      % (rb[j_strict] if j_strict < len(rb) else "(pending)", len(fwd_strict)))
if not fwd_pre:
    nxt = rb[j_pre + 1] if j_pre + 1 < len(rb) else None
    if nxt:
        print("  boundary leg IN PROGRESS: started %s, completes at the next rebalance %s" % (rb[j_pre], nxt))
    else:
        elapsed = ci.get(ASOF, N - 1) - ci[rb[j_pre]] if ASOF in ci else (N - 1) - ci[rb[j_pre]]
        print("  boundary leg IN PROGRESS: started %s, ~%d of %d trading days elapsed — first checkpoint lands when the engine's next rebalance enters the data (~%d more sessions)"
              % (rb[j_pre], elapsed, QTR, max(0, QTR - elapsed)))

# ---- ETF-in-selection flag (16AR finding; owner-DECIDED 2026-07-17 ratify+document, task_7a70ad77) ----
# The frozen rule runs AS SEALED, so a live selection MAY include an ETF (a fund, not a stock). Surface it
# every checkpoint so the forward-test day never silently holds an index/commodity/liquid ETF. Reporting
# only — reuses the frozen selection line, adds NO selection logic. Identification: nse_etf_list + verified
# historical gold-ETF orphans (design §7d(repro)).
import sqlite3 as _sq
_qc = _sq.connect("file:%s?mode=ro" % DB, uri=True)
_ETF = {s: (a or "") for s, a in _qc.execute("SELECT symbol, assets FROM nse_etf_list")}
_qc.close()
_GOLD_ORPHAN = {"KOTAKGOLD", "HDFCMFGETF", "ICICIGOLD", "RELGOLD", "SBIGETS"}
def _is_etf(s):
    return (s in _ETF) or (s in _GOLD_ORPHAN)
def _etf_kind(s):
    a = (_ETF.get(s) or "").lower()
    if ("gold" in a and "silver" not in a) or s in _GOLD_ORPHAN: return "gold"
    if "silver" in a: return "silver"
    if "government" in a or s.startswith("LIQUID"): return "liquid/gilt"
    return "equity-index/other"
def _is_gold(s):
    a = (_ETF.get(s) or "").lower()
    return ("gold" in a and "silver" not in a) or s in _GOLD_ORPHAN
def _sel_nogold(qq, d, i, topn):   # rank as sealed, then drop gold ETFs (backfilled by run5's [:topn])
    return [s for s in sel_a2c(qq, d, i, topn) if not _is_gold(s)]
def _sel_noetf(qq, d, i, topn):    # rank as sealed, then drop ALL ETFs
    return [s for s in sel_a2c(qq, d, i, topn) if not _is_etf(s)]
_jlive = max(i for i in range(len(rb)) if rb[i] <= ASOF)
_dlive = rb[_jlive]
print("  ETF-in-selection check @ latest rebalance %s (frozen rule as-sealed; ratify+document):" % _dlive)
_any_etf = False
for _k in ORDER:
    _cfg = BOOKS[_k]
    _hook = _cfg.get("hook") or sel_a2c
    _sel = _hook(QUAL[_cfg["fmode"]][_dlive], _dlive, ci[_dlive], _cfg["topn"])[:_cfg["topn"]]
    _etfs = [(s, _etf_kind(s)) for s in _sel if _is_etf(s)]
    if _etfs:
        _any_etf = True
        print("    !! %-4s holds %d ETF(s): %s"
              % (_k, len(_etfs), ", ".join("%s[%s]" % (s, kd) for s, kd in _etfs)))
if not _any_etf:
    print("    OK — no ETF in any book's latest selection.")

def _near(sd, d):
    return series_near(sd, d) if sd else None

def _inear(nm, d):
    v = iclose[nm].get(d)
    return v if v else _idx_near(nm, d)

def med_pick_adv(k, d):
    """median ADV (Rs) of the book's selection at rebalance d — the same selection line run5 uses."""
    cfg = BOOKS[k]
    i = ci[d]
    hook = cfg.get("hook") or sel_a2c
    sel = hook(QUAL[cfg["fmode"]][d], d, i, cfg["topn"])[:cfg["topn"]]
    pm = pym(d)
    a = sorted(adv.get(s, {}).get(pm, 0) for s in sel)
    return (a[len(a) // 2] if a else None), len(sel)

def leg_rets(navs, idxs):
    out = []
    for i in idxs:
        prev = navs[i - 1] if i > 0 else 1.0
        out.append(navs[i] / prev - 1.0)
    return out

def dd_of(rets):
    nav, pk, mx = 1.0, 1.0, 0.0
    for r in rets:
        nav *= (1 + r); pk = max(pk, nav); mx = min(mx, nav / pk - 1)
    return mx

def ab(r, br):
    n = min(len(r), len(br))
    if n < 2: return None, None
    r, br = r[:n], br[:n]
    m, mb = sum(r) / n, sum(br) / n
    vb = sum((x - mb) ** 2 for x in br) / (n - 1)
    cov = sum((r[i] - m) * (br[i] - mb) for i in range(n)) / (n - 1)
    b = cov / vb if vb else 0.0
    return (m - b * mb) * 4, b

def idx_leg(nm, i):
    a, b = _inear(nm, rb[i]), _inear(nm, rb[i + 1])
    return b / a - 1.0 if (a and b) else 0.0

def tri_leg(sd, i):
    a, b = _near(sd, rb[i]), _near(sd, rb[i + 1])
    return b / a - 1.0 if (a and b) else None

def cum(rets):
    nav = 1.0
    for r in rets: nav *= (1 + r)
    return nav - 1.0

def annualize(rets):
    nav = 1.0
    for r in rets: nav *= (1 + r)
    y = len(rets) / 4.0
    return nav ** (1 / y) - 1 if y > 0 and nav > 0 else float("nan")

if fwd_pre:
    n500 = [idx_leg(BENCH, i) for i in fwd_pre]
    n50 = [idx_leg(SLEEVE, i) for i in fwd_pre]
    tri5 = [tri_leg(TRI500, i) for i in fwd_pre]
    trin = [tri_leg(TRIN50, i) for i in fwd_pre]
    print("")
    print("  per-quarter (PREREG cut): leg end | N500 PR | N50 PR | N500 TRI | N50 TRI | " + " | ".join(ORDER))
    for row_i, i in enumerate(fwd_pre):
        cols = " | ".join("%+6.1f%%" % (leg_rets(RUNS[k]["navs"], [i])[0] * 100) for k in ORDER)
        print("    %s | %+6.1f%% | %+6.1f%% | %s | %s | %s"
              % (rb[i + 1], n500[row_i] * 100, n50[row_i] * 100,
                 ("%+6.1f%%" % (tri5[row_i] * 100)) if tri5[row_i] is not None else "   n/a ",
                 ("%+6.1f%%" % (trin[row_i] * 100)) if trin[row_i] is not None else "   n/a ",
                 cols), flush=True)

    print("")
    print("  book summaries (PREREG cut, %d quarter(s)):" % len(fwd_pre))
    SUMM = {}
    for k in ORDER:
        r = leg_rets(RUNS[k]["navs"], fwd_pre)
        c = cum(r)
        a_pr, b_pr = ab(r, n500)
        tri_ok = all(x is not None for x in tri5)
        a_tri, b_tri = ab(r, [x for x in tri5]) if tri_ok else (None, None)
        madv = [med_pick_adv(k, rb[i]) for i in fwd_pre]
        mm = sorted(v for v, _n in madv if v is not None)
        med = mm[len(mm) // 2] / 1e7 if mm else 0.0
        inv = RUNS[k]["inv"]
        inv_f = sum(inv[i] for i in fwd_pre) / len(fwd_pre)
        SUMM[k] = dict(rets=r, cum=c, alpha=a_pr, beta=b_pr, dd=dd_of(r))
        tag = "SEALED %s" % SEALS[k] if k in SEALS else "recorded lead (unregistered)"
        line = "    %-4s cum %+7.2f%%" % (k, c * 100)
        if len(r) >= 4:
            line += "  ann %5.1f%%" % (annualize(r) * 100)
        if a_pr is not None and len(r) >= 6:
            line += "  aPR %+5.1f/bPR %4.2f" % (a_pr * 100, b_pr)
            if a_tri is not None:
                line += "  aTRI %+5.1f/bTRI %4.2f" % (a_tri * 100, b_tri)
        elif a_pr is not None:
            line += "  (a/b at <6 legs: unstable, not printed)"
        line += "  MaxDD %5.1f%%  inv %3.0f%%  medADV %5.1fcr   [%s]" % (SUMM[k]["dd"] * 100, inv_f * 100, med, tag)
        print(line, flush=True)
        if k in DEFLATED:
            print("           deflated prior (16AL C3): ~%.1f%%/yr expected forward" % DEFLATED[k])
    print("    N50 PR  cum %+7.2f%%  MaxDD %5.1f%%   (criterion benches; N50 TRI cum %s)"
          % (cum(n50) * 100, dd_of(n50) * 100,
             ("%+.2f%%" % (cum([x for x in trin]) * 100)) if all(x is not None for x in trin) else "n/a"))
    if fwd_strict:
        print("  STRICT-cut cums: " + "  ".join(
            "%s %+.2f%%" % (k, cum(leg_rets(RUNS[k]["navs"], fwd_strict)) * 100) for k in ORDER))

    # ---- 3. frozen criteria per sealed spec ----
    print("")
    print("### 3. FROZEN CRITERIA (sealed specs only; %d/%d forward quarters -> %s)"
          % (len(fwd_pre), MIN_Q, "JUDGMENT" if len(fwd_pre) >= MIN_Q else "INTERIM — no verdict before %d" % MIN_Q))
    passers = []
    for k in [x for x in ORDER if x in SEALS]:
        r = SUMM[k]["rets"]
        exc = [r[i] - n50[i] for i in range(len(r))]
        tot = sum(exc)
        c1 = cum(r) > cum(n50)
        c2 = SUMM[k]["alpha"] is not None and SUMM[k]["alpha"] > 0
        c3 = SUMM[k]["dd"] >= dd_of(n50)
        c4ok = not (tot > 0 and max(exc) / tot > 0.60)
        beta_note = ""
        if SUMM[k]["beta"] is not None and SUMM[k]["beta"] > 1.1 and c1 and not c2:
            beta_note = "  << excess is beta, not alpha (prereg: FAIL)"
        verdict = "PASS" if (c1 and c2 and c3) else "FAIL"
        if c1 and c2 and c3 and not c4ok:
            verdict = "INCONCLUSIVE (C4) — extend window"
        if len(fwd_pre) < MIN_Q:
            alpha_moot = SUMM[k]["alpha"] is None      # < 2 legs: alpha not computable yet
            verdict = "on track" if (c1 and c3 and (c2 or alpha_moot)) else "behind"
        print("  %-4s C1 beat-N50 %-5s  C2 alpha>0 %-5s  C3 dd-not-worse %-5s  C4 concentration %-5s  -> %s%s"
              % (k, c1, ("n/a" if SUMM[k]["alpha"] is None else bool(c2)), c3, c4ok, verdict, beta_note))
        if len(fwd_pre) >= MIN_Q and verdict == "PASS":
            passers.append((SUMM[k]["alpha"] or -9, k))
    # the 3 sealed HOLD/DEEP siblings under the SAME four criteria (self-contained; they join adjudication)
    print("  --- HOLD/DEEP siblings (16BD/16BF; same 4 criteria; near-identical to K30/A2, shared levers disclosed) ---")
    for _sn, _sc, _stl, _shb, _ssl, _sisf in SIBS:
        _r = leg_rets(SIB_RUNS[_sn]["navs"], fwd_pre)
        _cc = cum(_r); _apr, _bpr = ab(_r, n500); _dd = dd_of(_r)
        _exc = [_r[i] - n50[i] for i in range(len(_r))]; _tot = sum(_exc)
        _c1 = _cc > cum(n50); _c2 = _apr is not None and _apr > 0; _c3 = _dd >= dd_of(n50)
        _c4 = not (_tot > 0 and max(_exc) / _tot > 0.60)
        if len(fwd_pre) >= MIN_Q:
            _v = "PASS" if (_c1 and _c2 and _c3 and _c4) else ("INCONCLUSIVE (C4)" if (_c1 and _c2 and _c3) else "FAIL")
        else:
            _v = "on track" if (_c1 and _c3 and (_c2 or _apr is None)) else "behind"
        _ln = "  %-14s cum %+7.2f%%" % (_sn, _cc * 100)
        if len(_r) >= 4: _ln += "  ann %5.1f%%" % (annualize(_r) * 100)
        if _apr is not None and len(_r) >= 6: _ln += "  aPR %+5.1f/bPR %4.2f" % (_apr * 100, _bpr)
        _ln += "  MaxDD %5.1f%%  C1%s C2%s C3%s C4%s -> %s  [seal %s; turn<%d/hold%d]" % (
            _dd * 100, "+" if _c1 else "-", ("?" if _apr is None else ("+" if _c2 else "-")),
            "+" if _c3 else "-", "+" if _c4 else "-", _v, _ssl, _stl, _shb)
        print(_ln, flush=True)
        if len(fwd_pre) >= MIN_Q and _v == "PASS":
            passers.append((_apr or -9, _sn))
    if len(fwd_pre) >= MIN_Q:
        if passers:
            passers.sort(reverse=True)
            print("  FAMILY ADJUDICATION (frozen): GRADUATE = %s (highest forward alpha among passers); the rest retire to reference."
                  % passers[0][1])
        else:
            print("  FAMILY ADJUDICATION (frozen): no sealed spec passed — ALL DESCRIPTIVE-ONLY, never deployed.")
    print("  era-floor flag rides in (16AL C2b): P_train 0.268 vs sealed 0.450 — %s carry the family's highest window-fit risk."
          % "/".join(ERA_FLOOR_ROWS))

    # ---- 4. the portfolio dial on the forward window (16AN fold) ----
    print("")
    print("### 4. PORTFOLIO DIAL (forward window; fixed mix, quarterly rebalance; G-sec leg = gsec_q)")
    gs = [gsec_q(rb[i], rb[i + 1]) for i in fwd_pre]
    for k in ("K30", "A2"):
        for w in (1.0, 0.9, 0.8, 0.7):
            mix = [w * SUMM[k]["rets"][i] + (1 - w) * gs[i] for i in range(len(gs))]
            line = "  %s %3.0f/%2.0f  cum %+7.2f%%  MaxDD %5.1f%%" % (k, w * 100, (1 - w) * 100, cum(mix) * 100, dd_of(mix) * 100)
            if len(mix) >= 4:
                m = sum(mix) / len(mix)
                sd = (sum((x - m) ** 2 for x in mix) / (len(mix) - 1)) ** 0.5
                line += "  ann %5.1f%%  ret/vol %4.2f" % (annualize(mix) * 100, (m / sd * 2 if sd else 0))
            print(line, flush=True)
    print("  (policy point = Ramana's pick on the measured 16AN curve; design default 80/20 per"
          " docs/portfolio-layer-design.md §4; the sealed specs themselves stay 100/0)")

# ---- 5. the TR prints (sealed era, end=REG; recorded values printed beside, informational) ----
print("")
print("### 5. TOTAL-RETURN prints (16AD accrual, lower bound; sealed era end=%s; records = seal-time archive)" % REG)
for k in ("K30", "A2"):
    o = run5(tr=True, end=REG, **BOOKS[k])
    s = stat(o["navs"], o["bnavs"])
    r_c, r_m = TR_REC[k]
    print("  %s TR %5.1f%% (Rs1Cr->%7.2fx, div %d, MaxDD %5.1f%%, aPR %+5.1f/bPR %4.2f)  [recorded %s: %.1f/%.2f on the seal-time archive; delta = 16AQ repair + boundary-leg dead-window, disclosed]"
          % (k, s["cagr"] * 100, s["mult"], o["ndiv"], s["dd"] * 100, s["alpha"] * 100, s["beta"],
             "16AF" if k == "K30" else "16AO", r_c, r_m), flush=True)
    # ETF-excluded companions on the SAME TR basis (universe-hygiene; DECIDED ratify+document,
    # task_7a70ad77; sealed rows above are unchanged; effect <0.5pp, no verdict move; design §7d(repro))
    for _hlab, _hk in (("gold-ETF-excl", _sel_nogold), ("all-ETF-excl", _sel_noetf)):
        _oc = run5(tr=True, end=REG, hook=_hk, **BOOKS[k])
        _sc = stat(_oc["navs"], _oc["bnavs"])
        print("       %-4s companion %-13s TR %5.1f%% (Rs1Cr->%7.2fx, MaxDD %5.1f%%)  [hygiene; descriptive; sealed row unchanged]"
              % (k, _hlab, _sc["cagr"] * 100, _sc["mult"], _sc["dd"] * 100), flush=True)

# ---- 6. full-period median pick-ADV (the other owed print; per book, all rebalances) ----
print("")
print("### 6. MEDIAN PICK-ADV (full period + last-4-rebalance recent view; Rs cr)")
for k in ORDER:
    vals = []
    for d in rb[:-1]:
        v, _n = med_pick_adv(k, d)
        if v is not None: vals.append(v)
    if not vals:
        print("  %-4s no selections" % k); continue
    med_all = sorted(vals)[len(vals) // 2] / 1e7
    recent = sorted(vals[-4:])[len(vals[-4:]) // 2] / 1e7
    print("  %-4s full-period median %6.1fcr   recent(4 rebals) %6.1fcr" % (k, med_all, recent), flush=True)

print("")
print("done. (descriptive research; sealed criteria judged only per the preregs; nothing here deploys anything)")
