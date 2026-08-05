# Data dictionary

## Observed UCI fields

- `ID`: source row identifier; excluded and never published.
- `LIMIT_BAL`: existing credit limit in TWD.
- `PAY_0`, `PAY_2` … `PAY_6`: recent-to-old repayment status. Positive values
  denote months delayed; -1 means paid duly and -2/0 are no-use/revolving states
  documented in common source coding.
- `BILL_AMT1` … `BILL_AMT6`: recent-to-old statement amounts in TWD.
- `PAY_AMT1` … `PAY_AMT6`: recent-to-old prior payment amounts in TWD.
- `SEX`, `EDUCATION`, `MARRIAGE`, `AGE`: source demographics; excluded from
  decisioning. Sex and age are used only for offline audit diagnostics.
- `default_next_month`: binary model target; never an input.

## Engineered model fields

- `limit_bal`: current line.
- `current_utilization`, `average_utilization`, `maximum_utilization`: positive
  bill divided by line.
- `utilization_trend`: recent less oldest utilization.
- `recent_payment_ratio`, `average_payment_ratio`: payment divided by positive bill.
- `payment_consistency`: share of months with positive payments.
- `delinquent_month_count`, `maximum_delinquency_severity`: delay history.
- `recent_payment_deterioration`: recent status less older-status mean.
- `revolving_balance_proxy`: positive recent bill less recent payment, divided by line.
- `limit_headroom`: positive line less recent bill, divided by line.
- `balance_volatility`, `payment_volatility`: six-month standard deviation over line.
- `recent_balance_growth`: recent less three-month-prior bill over line.
- `inactive_month_count`: months with zero bill.

## Model-estimated fields

- `pd`: calibrated subsequent-month probability of default, [0, 1].
- `risk_band`: Low (<5%), Moderate (5–15%), High (15–30%), Very high (≥30%).

## Synthetic and simulated fields

- `account_id`: deterministic `LIQ-` synthetic identifier; not reversible to ID.
- `action`: selected increase/no-change/review/freeze label.
- `increase_pct`, `proposed_limit`: simulated policy result.
- `current_ead`, `proposed_ead`: drawn + CCF × positive undrawn line.
- `current_expected_loss`, `proposed_expected_loss`: PD × LGD × EAD.
- `incremental_contribution`: simulated revenue less loss/funding/capital/servicing.
- `risk_adjusted_return`: contribution divided by incremental EAD.
- `reason_codes`: pipe-separated actual policy/behavior reasons.
- `policy_checks`: JSON booleans for the selected candidate.

## Batch schema

Exactly `ACCOUNT_ID`, `LIMIT_BAL`, six `PAY_*`, six `BILL_AMT*` and six
`PAY_AMT*` columns. IDs must be unique 3–40 character letters, numbers,
underscores or hyphens. Numeric blanks, non-positive/excessive limits, payment
statuses outside -2…9 and negative payment amounts are rejected.

