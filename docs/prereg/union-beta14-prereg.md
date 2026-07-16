# PRE-REGISTRATION — UNION + per-name beta cap 1.4 at selection ("union-β14"), forward test

> **Class:** PRE-REGISTERED forward-test spec, SIBLING to the sealed union registration
> (`union-prereg.md`, seal `a9a14058…`, which is UNTOUCHED). Hashed and committed before any
> forward-window data exists. Editing this file after the forward window opens voids it.
> **Registered:** 2026-07-16 (same day as the union's own registration; ledger 2026-07-16Y).
> **Origin:** 🧑 RAMANA (the standing directive to push the union's CAGR higher; the RS theses) +
> 🏠 HOUSE (the beta-cap selection lever, falsification, this registration).

## Why this exists

The union's one weak regime (2012–17, mid-cycle bull) was proven unreachable by sizing levers
(throttle 16W, inverse-vol 16X). This session attacked SELECTION instead: 14 candidates
(`union_lab.py`), each the sealed union + one change. Exactly one survived every pre-declared
kill condition: **exclude qualifiers whose trailing 250-day beta vs Nifty 500 exceeds 1.4 at
selection time.** In-sample it beats the union on CAGR, MaxDD, beta AND alpha together, and flips
2012–17 alpha positive — surviving threshold-plateau, beta-window, dead-cash-decomposition and
missing-data checks (ledger 2026-07-16Y).

**It carries the union's own epistemic status: an IN-SAMPLE-SELECTED LEAD** (picked from a
multi-config battery on the same 2005–2026 window — Codex 15R applies in full). The only honest
conversion is the same one the union got: freeze the spec, judge on data not used to build it.

## THE FROZEN SPEC (any change voids the registration)

Identical to the sealed union spec (`union-prereg.md`: EQ+BE+BZ CA-adjusted, split-ratio
quarantine, prior-month ADV ≥ ₹5cr, PIT 500d excess-correlation sector assignment, the two
signals — trend: price-RSI(14) > its 50-SMA AND ≥70% trailing-quarter consistency vs own sector;
turn 6b: RSI(14)-of-RS < 30 → ≥ 30 in trailing ~60d — union by OR, fixed 1/60 slots, top-60 in
engine qualifier order, idle → Nifty Next 50 while Nifty 500 ≥ 200DMA else cash, trailing stop
−20% from peak close @1% slip, 0.15%/side, quarterly), **plus exactly one additional rule:**

> **At each rebalance, a qualifier is EXCLUDED if its trailing 250-trading-day beta vs Nifty 500
> (computed from daily closes, minimum 150 paired observations) exceeds 1.4. A qualifier with
> insufficient data to compute beta is KEPT (absence of evidence is not a risk flag).**

Repro: `research/explosive_moves/union_lab.py` (`s_beta_cap_1.4` row — the first-declared
candidate; the cap value and window were NOT chosen from the sweep, which ran after as a
stability check only).

## IN-SAMPLE RESULT (2006–2026, for the record — NOT the test)

CAGR 18.1% · MaxDD −24.7% · ₹1 Cr → ₹28.84 Cr · beta 0.74 · alpha +8.4% · ~69% avg invested
(vs the union's 17.5% / −30.5% / 26.04× / 0.87 / +6.8% / 82%).
Walk-forward alpha: 2006–11 +9.3% (union +9.8%) · **2012–17 +3.4% (union −4.6%)** ·
2018–26 +9.2% (union +8.3%). Selection-driven: in dead-cash mode 2012–17 is still +1.7% vs the
union's −5.6%. Give-back disclosed: 2006–11 CAGR 17.4% vs the union's 19.0% (fewer low-beta
qualifiers → more sleeve time in that window).

## PASS / FAIL — frozen criteria, judged ONLY on data after the registration date

Same window and cadence as the sealed union's forward test (every new quarter from 2026-07 on,
≥ 8 forward quarters), same four criteria judged independently of the union's:

1. **CAGR > Nifty Next 50 buy-and-hold net of the modelled costs.**
2. **Alpha > 0 with forward beta reported** (excess purely from beta > 1.1 = FAIL).
3. **MaxDD not worse than Nifty Next 50's over the same window.**
4. **No single quarter > 60% of the total excess.**

**Sibling adjudication (frozen now):** if BOTH this and the sealed union pass their own criteria
over the same forward window, the one with the higher forward ALPHA graduates and the other is
retired to reference status. If only one passes, it graduates. Miss 1–3 → DESCRIPTIVE-ONLY,
never deployed. Criterion 4 → inconclusive, extend.

## What is NOT claimed

- Not that 18.1%/+8.4% recurs — in-sample selection inflates it by an unknown amount.
- Not that the 2012–17 fix is proven — there is no second mid-cycle-bull regime in any honest
  hold-out; the forward window is the only judge.
- Not personalized advice. Descriptive research on a paper portfolio; price-index benchmark
  (TRI re-cut owed estate-wide).

## Canon

Ledger: 2026-07-16Y (the candidate battery + diagnostics, every number) · 2026-07-16Z (the
rejected candidates) · union baseline §§ 2026-07-16U→X. Ruleset prose: `docs/strategies/union.md`
(candidate ladder section). Repro: `research/explosive_moves/union_lab.py` + `union_lab2.py`.
SHA-256 of this file is recorded in the landing commit and the ledger 16Y entry — any edit after
the forward window opens is detectable and voids the registration.
