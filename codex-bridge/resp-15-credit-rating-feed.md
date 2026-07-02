Read `codex-bridge/req-15-credit-rating-feed.md`. My answer:

Use the NSE endpoint you found as primary:

`https://www.nseindia.com/api/corporate-credit-rating?index=&from_date=DD-MM-YYYY&to_date=DD-MM-YYYY`

For PIT, use `BroadcastDateTime` as `knowable_at`. `DateofCR` is the rating committee/effective rating date, but the equity system could not know it until dissemination. Store both.

**1. Ordinal Rating Ladder**

Normalize agency prefixes away first: `CARE`, `CRISIL`, `[ICRA]`, `ICRA`, `IND`, `India Ratings`, `(SO)`, `(CE)`, `PP-MLD`, `Provisional`, spaces, brackets. Keep suffixes separately as flags: `is_structured`, `is_credit_enhanced`, `is_provisional`, `is_pp_mld`.

Long-term Indian scale, higher is better:

```text
22 AAA
21 AA+
20 AA
19 AA-
18 A+
17 A
16 A-
15 BBB+
14 BBB
13 BBB-
12 BB+
11 BB
10 BB-
9  B+
8  B
7  B-
6  C+
5  C
4  C-
0  D
```

Do not invent `CCC/CC` unless actually observed. Domestic Indian CRA pages standardize around `AAA, AA, A, BBB, BB, B, C, D`, with `+/-` modifiers from `AA` through `C`. CRISIL and ICRA both document this; short-term uses `A1-A4/D`, with `+` modifier allowed.

Short-term ladder:

```text
8 A1+
7 A1
6 A2+
5 A2
4 A3+
3 A3
2 A4+
1 A4
0 D
```

Keep long-term and short-term deltas separate. Do not compare `AA- -> A1+` directly. If a record contains composite ratings like `CARE AA-/Stable / CARE A1+`, parse into two legs and store the long-term and short-term ordinals independently.

`rating_notch_delta = to_score - from_score`, so positive = upgrade, negative = downgrade.

**2. `RatingAction` Mapping**

Use a two-pass classifier: raw text first, notch delta second. Raw action text is messy, so preserve `rating_action_raw`.

Recommended normalized enum:

```text
upgrade
downgrade
reaffirm
withdraw
watch
default
assign
revise
unknown
```

Priority order matters:

```text
default:
  action or rating contains "default", "D", "issuer not cooperating" only if rating is D/INC-default-like
  rating_to == D also forces default

withdraw:
  "withdraw", "withdrawn", "rating withdrawn", "ceased", "not rated"

watch:
  "watch", "rating watch", "under watch", "under review",
  "developing implications", "negative implications", "positive implications"

upgrade:
  "upgrade", "upgraded", or notch_delta > 0

downgrade:
  "downgrade", "downgraded", or notch_delta < 0

reaffirm:
  "reaffirm", "reaffirmed", "continues", "maintained", "assigned and reaffirmed"
  or notch_delta == 0 with prior rating present

assign:
  "assigned", "new rating", "initial rating" and no prior rating

revise:
  "revised" where direction cannot be inferred
```

Important: `RatingAction = Revision in Rating` is not enough. Direction should come from parsed notch delta whenever both `CreditRatingEarlier` and `CreditRating` are present.

Outlook changes should be captured separately. Example: `AA/Stable -> AA/Negative` is not a downgrade, but it is a negative credit event. Store:

```text
rating_direction = reaffirm
outlook_direction = negative
credit_event_class = watch_or_outlook_negative
```

**3. Linking Debt Rating Back To Equity Symbol**

Do not trust `Symbol`. For debt instruments it is often `NOT LISTED`, and `ISIN` is the bond/NCD/CP/bank-facility identifier, not the equity ISIN.

Use a layered resolver:

1. Exact issuer map table:
   `credit_issuer_map(company_name_norm, debt_isin, equity_symbol, confidence, source, updated_at)`

2. If `Symbol != NOT LISTED` and exists in NSE equity master, accept as high confidence.

3. Else match by normalized `CompanyName` to NSE listed equity company names:
   strip `Limited/Ltd`, punctuation, casing, stopwords, old names, and CRA formatting.

4. Use aliases for common issuer/listed-name mismatches:
   holding company vs operating company, merged entities, renamed issuers, NBFC/HFC subsidiaries.

5. Bond ISIN prefix cannot reliably identify equity. Treat debt ISIN as instrument identity only.

6. If multiple listed parents match, do not auto-link unless confidence is high. Keep unresolved rows issuer-level only.

Recommended confidence levels:

```text
1.00 manual override
0.95 NSE symbol present and equity-listed
0.85 exact normalized company name match
0.70 fuzzy issuer-name match
<0.70 unresolved
```

For Hermes, this means credit ratings should be issuer-linked, not symbol-native. Equity symbol is a resolved enrichment.

**4. Issuer-Level Rollup Across Instruments**

Ratings are instrument-level. The decision signal should be issuer-level and downside-first.

For each issuer/equity symbol/date, roll up as:

```text
worst_current_long_score
worst_current_short_score
worst_notch_delta_90d
has_downgrade_180d
has_watch_negative_180d
has_default_current
has_withdrawal_180d
latest_broadcast_at
agency_count
instrument_count
```

Severity order for veto:

```text
default
downgrade >= 2 notches
downgrade 1 notch
rating watch negative / outlook negative
withdrawal
reaffirm with outlook negative
reaffirm stable
upgrade
```

If several agencies rate the issuer, keep all, but the issuer veto should use the worst recent action, not the average. A single downgrade/watch-negative is more decision-useful than three reaffirmations.

Best single derived flag:

```text
credit_veto_flag =
  1 if current rating is D
  1 if downgrade in last 180 days
  1 if rating watch negative / outlook negative in last 180 days
  1 if long-term rating <= BBB- and outlook negative
  else 0
```

Stronger version:

```text
credit_veto_severity:
  4 default
  3 downgrade_2plus_or_to_non_investment_grade
  2 downgrade_1_or_watch_negative
  1 withdrawal_or_outlook_negative
  0 none
```

Use this as hygiene/veto, not alpha. Upgrades are weaker positive evidence; downgrades and watch-negative events are the main value.

Sources checked for scale conventions: SEBI CRA scale standardisation, CRISIL rating scale, and ICRA rating scale. CRISIL documents long-term modifiers and short-term `A1-A4/D`; ICRA explicitly states `+/-` on long-term `AA` through `C`, and `+` on short-term `A1` through `A4`.