# Model card

## Version boundary

This card describes the **deployed v2 model**. V2 was committed as `7e4ca6e`,
passed GitHub Actions CI (including Docker container health check), was tagged
`v2.0.0` and deployed to Render on 12 August 2026. The live `/health` endpoint
reports application `2.0.0`, model `limitiq-global-2.0.0-37a14c45a811` and
dataset `global-7-94bb4c0ad0f1`.

## Model identity

- Classification: multi-source adverse-credit-outcome benchmark
- Version: `limitiq-global-2.0.0-37a14c45a811`
- Champion: sigmoid-calibrated histogram gradient boosting
- Baseline: sigmoid-calibrated regularized logistic regression
- Artifact SHA-256:
  `37a14c45a8118d8684e3e7bf7fdad45fe167844a4e7700b1833e15b78a25df72`
- Dataset version: `global-7-94bb4c0ad0f1`
- Seed: 42
- Split: 1,121,728 train / 373,910 validation / 373,910 untouched test
- Threshold: `0.16891891891891891`

The suffix `global-7` records six independent training sources plus one legacy
reference file; it does not mean seven markets.

## Target interpretation

Source labels differ in event and horizon: next-month default, two-year serious
delinquency, historical good/bad performance, status at extract and payment
difficulty. The calibrated output is an educational probability of the relevant
source-specific adverse outcome. It is **not** a common-horizon contractual,
IFRS 9 or regulatory PD and is not comparable across sources as a single legal
default definition.

## Selection

Both candidates use unified imputation/preprocessing and three-fold sigmoid
calibration. Selection chooses the lowest source-macro validation Brier score
among candidates within 0.02 macro ROC-AUC of the best. Validation evidence:

| Candidate | Macro ROC-AUC | Macro Brier | Pooled ROC-AUC | Pooled Brier |
|---|---:|---:|---:|---:|
| Regularized logistic regression | 0.609702 | 0.180764 | 0.642906 | 0.143872 |
| Histogram gradient boosting | 0.678085 | 0.141845 | 0.669017 | 0.140721 |

The threshold is selected on validation with false negatives weighted five
times false positives. The champion is then refit on train plus validation and
the untouched test is read once.

## Untouched-test evidence

Source-macro evidence is primary; pooled evidence is secondary because Lending
Club dominates the row count.

| Metric | Macro | Pooled row-weighted |
|---|---:|---:|
| ROC-AUC | 0.6845295228 | 0.6698913281 |
| PR-AUC | 0.4023697231 | 0.3049645893 |
| Brier score | 0.1389681610 | 0.1406294588 |
| Log loss | 0.4333847612 | 0.4448560373 |
| Mean absolute calibration-bin gap | 0.0269678270 | Versioned in metadata |

At the selected threshold, pooled precision is 0.243562, recall 0.777521 and F1
0.370929; confusion matrix: TN 140,794, FP 164,849, FN 15,188, TP 53,079.

Per-source ROC-AUC ranges from 0.5175 for Home Credit to 0.8529 for Give Me Some
Credit. Small-cohort metrics—especially the 200-row South German test and
1,974-row HELOC test—are descriptive and uncertain, not league tables.

## Evaluation scope

The seeded split is random within each source. It measures interpolation for
represented source cohorts and does not evaluate:

- an unseen country or institution;
- future vintages or macroeconomic drift;
- leave-one-source-out transfer;
- Indian borrower performance;
- causal response to a credit-line change.

The one-hot region context and structural missingness may reveal source identity
and base rate. Histogram gradient boosting does not enforce common effect
directions. Pooled metrics may benefit from between-source differences and must
not be called like-for-like cross-market ranking.

## Intended use

Educational benchmarking, calibration/governance review and deterministic
synthetic portfolio scenario comparison. The app demonstrates how a model,
policy controls, reason codes, human review and rollback can be joined in a
production-shaped workflow.

## Non-use

No real lending, affordability decision, consumer notice, regulatory capital,
IFRS 9 provision, punitive line decrease, causal uplift estimate, realized
business impact, fair-lending certification or public v2 deployment before the
terms gate passes.

## Inputs and explanation

Six heterogeneous harmonized proxies plus one-hot region context enter the
pipeline. No source identifier, customer ID, target or demographic attribute is
an explicit input. However, region and missingness can act as source proxies.
Reason codes come from behavior/policy checks and are educational; they are not
consumer adverse-action reasons or causal feature explanations.

## Fairness and responsible lending

Comparable protected attributes are not available across sources, so v2 cannot
perform a defensible cross-jurisdiction fairness audit. Region is not a protected-
class substitute and its use would require legal and model-risk review in any
real system. The synthetic policy layer cannot replace verified income,
obligations or ability-to-pay assessment.

## Monitoring and rollback

Monitor source/schema version, missingness, source mix, feature and score drift,
per-source calibration/discrimination, risk-band outcomes, overrides and policy
breaches. Material deterioration or an unknown source routes to human review and
disables automatic increases. Rollback restores the prior checksum-verified v1
artifact or freezes automation.

## Publication gate

Status: **blocked**. Give Me Some Credit, FICO/HELOC, Lending Club upstream and
Home Credit terms require manual review before publishing the v2 model or
source-derived demonstration. See [`NOTICE.md`](../NOTICE.md).

## Verified deployed v1 reference

V1 remains sigmoid-calibrated histogram gradient boosting on 30,000 Taiwan
accounts: test ROC-AUC 0.781138, PR-AUC 0.567889, Brier 0.133149 and threshold
0.173874. Those numbers must not be mixed with v2 evidence.
