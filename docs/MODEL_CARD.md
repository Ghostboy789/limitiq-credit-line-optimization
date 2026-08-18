# Model card

## Version boundary

This card describes the **deployed v2 model**, unchanged in the v2.1 application
release. The live `/health` endpoint was verified 18 August 2026 and reports
application `2.1.0`, model `limitiq-global-2.0.0-37a14c45a811`, dataset
`global-7-94bb4c0ad0f1`; the endpoint also exposes the exact deployed Git
revision. Application code was release-gated at
`c6154603da430b0eacb2d237a469f0843784557e`. Keeping the model identifier at
`2.0.0` is deliberate: v2.1 changes application and governance evidence, not
trained model bytes. Tag `v2.1.0` identifies the final evidence release.

The original v2.0 application release was tagged `v2.0.0` and verified on
Render on 12 August 2026. Its pre-authorship-rewrite commit references are
historical only.

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
evaluated on the held-out test only after model and threshold selection. Later
diagnostics use those frozen test rows post-selection and never alter model bytes.

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
business impact or fair-lending certification. Public demonstration does not
make the model production-ready or replace independent legal, model-risk and
responsible-lending review.

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

Status: **owner-cleared by attestation on 14 August 2026**. The supporting
documents are retained by the owner. This is not an independent legal opinion
or legal validation by the project. Historical findings remain in
[`NOTICE.md`](../NOTICE.md).

## Application-release verification

GitHub Actions run
[32117394757](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32117394757)
passed Ruff, format, 92 tests at 69.00% coverage, Bandit, pip-audit, secret
scanning, Docker build/run and container health after a transient Docker Hub 502
was resolved by rerun. Production HTTPS QA passed 23 checks with zero failures;
the model version and checksum remained unchanged.

## Additive robustness evidence

The Lending Club vintage split produces ROC-AUC 0.6000 and Brier 0.2023 on the
latest 20% of issues, versus 0.6015 and roughly 0.165 on the random reference.
Because labels are status at extract with unequal seasoning, this is not a
fixed-horizon PD backtest. Explicit-region ablation does not isolate structural
missingness. Feature importance therefore uses source-preserving shuffles and
effect curves use only cohorts reporting the field.

## Verified deployed v1 reference

V1 remains sigmoid-calibrated histogram gradient boosting on 30,000 Taiwan
accounts: test ROC-AUC 0.781138, PR-AUC 0.567889, Brier 0.133149 and threshold
0.173874. Those numbers must not be mixed with v2 evidence.
