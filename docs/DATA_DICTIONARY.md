# Data dictionary

## Local v2 model inputs

| Field | Type / range | Interpretation and caveat |
|---|---|---|
| `delinquency_count` | numeric, ≥0, nullable | Source-specific recent late months, events, derogatory trades or historical-credit proxy |
| `utilization` | numeric, ≥0, nullable | Revolving/statement utilization proxy; values above 1 may occur |
| `debt_to_income` | numeric, normally 0–1, nullable | Total DTI, installment burden or annuity-to-income proxy depending on source |
| `credit_lines` | numeric, ≥0, nullable | Open accounts, total trades or ordinal existing-credit proxy |
| `income_inr` | numeric, ≥0, nullable | Annual income only where source currency is disclosed and converted to INR |
| `credit_age_months` | numeric, ≥0, nullable | Age of oldest credit history where reported |
| `region` | category | `asia`, `europe`, `north_america` or `undisclosed`; one-hot encoded |

`source_dataset` exists in the synthetic demo for display and source-level
diagnostics but is not a model predictor. Structural missingness and region may
still identify source.

## Local v2 synthetic decision fields

| Field | Meaning |
|---|---|
| `account_id` | Deterministic synthetic identifier `LIQ-*`; never a source ID |
| `current_limit_inr` | Synthetic current credit line in INR |
| `current_balance_inr` | Synthetic current drawn balance in INR |
| `pd` | Legacy UI field name; source-specific adverse-outcome probability, not common-horizon PD |
| `risk_band` | Low, Moderate, High or Very high educational band |
| `action` | Increase 30%, No change, Manual review or Freeze automatic increases in the base scenario |
| `proposed_limit` | Synthetic proposed INR limit after governed action |
| `current_ead`, `proposed_ead` | Synthetic exposure-at-default proxy |
| `current_expected_loss`, `proposed_expected_loss` | Educational probability×LGD×EAD proxy; not IFRS 9 ECL |
| `incremental_contribution` | Simulated revenue less expected-loss/funding/capital/servicing costs |
| `reason_codes` | Educational behavioral and policy explanations; not consumer notices |
| `policy_checks` | Deterministic constraint results |
| `missing_model_fields` | Structurally or individually absent harmonized inputs |

## Batch input

Batch CSV uses the seven v2 model-input fields plus synthetic
`current_limit_inr` and `current_balance_inr`. Inputs are strictly validated,
processed transiently and not retained. Values for undisclosed source currencies
must not be relabeled as INR; users provide already-localized synthetic scenario
amounts.

## V1 source reference

The verified public v1 pipeline uses `LIMIT_BAL`, `PAY_0`, `PAY_2`–`PAY_6`,
`BILL_AMT1`–`BILL_AMT6` and `PAY_AMT1`–`PAY_AMT6`. Monetary fields are converted
from TWD to INR at 2.97. `ID`, target and demographics are excluded from model
input; sex and age exist only in offline v1 diagnostics.
