# Model card

## Model

- Version: `limitiq-1.0.0-4a84b86c3f7f`
- Champion: sigmoid-calibrated histogram gradient boosting
- Baseline: sigmoid-calibrated regularized logistic regression
- Target: subsequent-month default
- Seed: 42
- Split: 18,000 train / 6,000 validation / 6,000 untouched test
- Decision threshold: 0.149099, selected on validation with missed defaults
  weighted five times false positives
- Artifact SHA-256:
  `4a84b86c3f7f0fa4cc74a9e1a9140192313719712d3df5ee865e1dfd2eacff96`

## Selection

Choose the lowest validation Brier score among candidates within 0.02 ROC-AUC
of the best. Histogram gradient boosting validation ROC-AUC was 0.7658 and Brier
0.1389 versus logistic 0.7329 and 0.1441. The champion type and threshold were
frozen before the single test read.

## Untouched-test metrics

- ROC-AUC: 0.781082
- PR-AUC: 0.568754
- Brier score: 0.133120
- Log loss: 0.426325
- Precision: 0.360506
- Recall: 0.773173
- F1: 0.491733
- Confusion matrix: TN 2,853; FP 1,820; FN 301; TP 1,026

These are historical test results, not production performance or business
impact. Calibration curves, risk-band results and segment diagnostics are in
the governance page and generated report.

## Intended use

Educational one-month PD estimation for candidate-line scenario comparison in
the LimitIQ demonstration. PD is held constant across candidates and ECL varies
through EAD.

## Non-use

No real lending, affordability determination, customer notice, regulatory
capital, IFRS 9 provision, punitive line decrease, or causal uplift estimation.

## Inputs and explainability

Seventeen engineered behavioral features are built inside the serialized
pipeline. Customer ID, target and all demographics are excluded. Reason codes
come from actual behavioral/policy checks; the displayed association ranking is
not causal and is not an adverse-action explanation.

## Fairness

Sex and age are retained only for offline test diagnostics. Segment ROC-AUC,
mean PD, TPR and FPR are reported with sample sizes. The small 60+ sample and
limited categories create uncertainty. The analysis is a governance diagnostic,
not proof of fair-lending compliance.

## Monitoring and rollback

Monitor schema/ranges, missingness, feature/PD drift, calibration, discrimination,
risk-band default, action/override rates, policy breaches and segment gaps.
Material deterioration triggers review/recalibration. Rollback disables automatic
increases and restores the prior checksum-verified artifact; freeze/manual-review
routing remains available.

