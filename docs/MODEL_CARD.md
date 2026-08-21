# Model card — LimitIQ v4 behavioral primary

## Current model identity and use boundary

- **Version:** `limitiq-behavioral-4.0.0-21234ab33f78`
- **Role:** source-coherent behavioral primary for synthetic educational decisions
- **Source:** UCI Default of Credit Card Clients, Taiwan, 30,000 rows, CC BY 4.0
- **Target / horizon:** default payment in the following month / one month
- **Champion:** three-fold sigmoid-calibrated histogram gradient boosting
- **Raw contract:** current limit plus six repayment-status, bill and payment periods
- **Engineered contract:** 17 behavioral features; customer ID and protected attributes excluded
- **Model SHA-256:** `21234ab33f782a5a4d12e6e9050ccbcd812c2b1f324ae91d1a2f4bbd07648115`
- **Dataset version:** `uci-350-behavioral-6ba3a746be13`
- **Split:** 18,000 train / 6,000 validation / 6,000 untouched test; fixed seed 42
- **Selected threshold:** `0.173874`, selected on validation before the single test read

| Untouched-test metric | V4 result | Seeded 95% bootstrap interval |
|---|---:|---:|
| ROC-AUC | 0.781138 | 0.767398–0.796055 |
| PR-AUC | 0.567889 | 0.540125–0.599004 |
| Brier score | 0.133149 | 0.127508–0.138953 |
| Log loss | 0.426351 | 0.412325–0.441232 |

At the frozen threshold: precision 0.398640, recall 0.706858 and F1 0.509783;
confusion matrix TN 3,258, FP 1,415, FN 389, TP 938.

The exact paired 500-repeat bootstrap on the same test accounts shows v4 minus
v3 ROC-AUC `+0.023728` (`0.017680–0.030144`), PR-AUC `+0.059160`
(`0.044466–0.075197`), Brier `-0.008533` (`-0.010342–-0.006640`) and
log loss `-0.021093` (`-0.025538–-0.016470`). This supports application-level
promotion for the educational demo; it does not establish India, temporal,
regulatory or production suitability.

## Current limitations and controls

- random within-source interpolation on Taiwan 2005 behavior, not out-of-time validation;
- no Indian borrowers, verified affordability, external obligations or current-vintage evidence;
- no observed response to a line increase and no causal profit or customer-outcome evidence;
- management expected-loss and economics are simulated, not Ind AS 109/IFRS 9 allowances;
- fairness diagnostics cannot establish jurisdiction-specific compliance;
- automatic increases can be disabled with `AUTO_INCREASES_ENABLED=false`;
- monitoring and experiment outputs are executable deterministic replays, not live results.

The separate 2015 US installment-loan vintage study and heterogeneous 1.87M-row
global benchmark never feed card recommendations.

---

## Archived v3 model record

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
- **Release state:** model/runtime 3.0.0 served by release v3.0.1, verified live on 21 August 2026

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
