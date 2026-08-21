# Model card — LimitIQ v3 primary candidate

## Identity and use boundary

- **Version:** `limitiq-primary-3.0.0-89f9a2530bde`
- **Role:** source-coherent primary candidate for an educational synthetic demo
- **Source:** UCI Default of Credit Card Clients, Taiwan, 30,000 rows
- **Target:** default payment in the following month
- **Horizon:** one month
- **Champion:** sigmoid-calibrated histogram gradient boosting
- **Baseline:** sigmoid-calibrated regularized logistic regression
- **Model SHA-256:** `89f9a2530bde4fbae25974255d5de5963b1ae8ec392042287dad17356c98df33`
- **Dataset version:** `uci-350-next-month-dc05bd56186a`
- **Seed:** 42; bootstrap seed 3042
- **Release state:** v3.0.0 application verified live on 21 August 2026

The model may demonstrate policy mechanics only. It is prohibited for real
lending, Indian customer decisions, pricing, affordability, regulatory PD,
IFRS 9/Ind AS 109, provisioning, capital or automatic customer treatment.

## Model contract

The full harmonized input contract accepts delinquency count, utilization, debt
to income, credit lines, income, credit age and region. Only **delinquency count**
and **utilization** are observed and active for this primary source; region is
constant `asia` and the remaining fields are explicitly unavailable. Customer
ID and demographic attributes are excluded from inference.

## Development and selection

The fixed stratified split is 18,000 train / 6,000 validation / 6,000 untouched
test. Both candidates use serialized preprocessing and three-fold sigmoid
calibration. Selection chooses the lowest validation Brier score among models
within 0.02 ROC-AUC of the best. The selected threshold minimizes a documented
validation cost with false negatives weighted five times false positives.

| Validation candidate | ROC-AUC | PR-AUC | Brier | Log loss |
|---|---:|---:|---:|---:|
| Regularized logistic regression | 0.704729 | 0.460870 | 0.149363 | 0.469577 |
| **Histogram gradient boosting** | **0.743372** | **0.474880** | **0.146294** | **0.458581** |

The champion type and threshold `0.163964` were frozen before refitting on train
plus validation and reading the untouched test set once.

## Untouched-test evidence

| Metric | Result | Seeded 95% bootstrap interval |
|---|---:|---:|
| ROC-AUC | 0.757410 | 0.743319–0.773753 |
| PR-AUC | 0.508729 | 0.480370–0.542755 |
| Brier score | 0.141683 | 0.136133–0.146975 |
| Log loss | 0.447444 | 0.433312–0.460640 |

At the selected threshold: precision 0.379188, recall 0.724943 and F1 0.497930.
The confusion matrix is TN 3,098, FP 1,575, FN 365, TP 962.

The 500-repeat nonparametric percentile intervals quantify test-population
sampling uncertainty. They do not cover time, geography, model selection,
policy or economic uncertainty.

## Explanation and policy use

The score feeds a deterministic optimizer that evaluates current line and
+10%, +20%, +30% candidates. Reason codes are generated from behavior and policy
checks—not presented as causal feature attribution or consumer adverse-action
reasons. Guardrails cover delinquency, expected loss, exposure, profitability,
overextension, portfolio growth, manual review and early-warning freeze.

## Fairness and customer protection

Protected attributes are excluded from inference. The public Taiwan source and
limited audit fields cannot establish fair-lending, affordability or
customer-outcome compliance in India or any other jurisdiction. No automatic
punitive line decrease is recommended. Positive controls do not replace local
fairness analysis or legal review.

## Monitoring and rollback

Production monitoring is not claimed. A real implementation would track schema
and range failures, score drift, calibration, risk bands, outcomes, actions,
overrides and customer-protection guardrails against a dated local baseline.
`AUTO_INCREASES_ENABLED=false` demonstrates a kill switch that routes otherwise
eligible increases to manual review.

## Limitations

- Taiwan source from 2005; no Indian or current-vintage validation
- random within-source split, not out-of-time testing
- only two active harmonized features
- no observed treatment response or causal profit evidence
- no verified affordability or comparable fairness population
- threshold cost ratio is a research assumption, not approved risk appetite

## Separate research benchmark

`limitiq-global-2.0.0-37a14c45a811` remains available for transportability
research across 1,869,548 rows. Its six cohorts have different events and
horizons, so v3 never loads it for account or batch decisions. Source-macro test
ROC-AUC is 0.684530 and pooled ROC-AUC is 0.669891; those numbers must not be
mixed with primary evidence.

## Validation status

The [validation-style review](INDEPENDENT_VALIDATION.md) gives conditional
approval for educational demonstration only. It is not organizationally
independent bank validation. See the [issue ledger](VALIDATION_ISSUES.md) and
[model inventory](MODEL_INVENTORY.md).
