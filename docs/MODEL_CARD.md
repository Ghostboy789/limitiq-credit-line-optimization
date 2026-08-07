# Model card

## Model

- Version: `limitiq-1.0.0-284f9a7c8ca2`
- Champion: sigmoid-calibrated histogram gradient boosting
- Baseline: sigmoid-calibrated regularized logistic regression
- Target: subsequent-month default
- Seed: 42
- Split: 18,000 train / 6,000 validation / 6,000 untouched test
- Model-ready split artifacts: raw decision fields plus target, deterministic
  CSVs and SHA-256 metadata generated under `data/processed/splits/`
- Decision threshold: 0.173874, selected on validation with missed defaults
  weighted five times false positives
- Artifact SHA-256:
  `284f9a7c8ca22ea2f8091dfea814796357f81014cfdbabecf62b7aaa0de14275`

## Selection

Choose the lowest validation Brier score among candidates within 0.02 ROC-AUC
of the best. Histogram gradient boosting validation ROC-AUC was 0.7659 and Brier
0.1389 versus logistic 0.7328 and 0.1441. The champion type and threshold were
frozen before the single test read.

## Untouched-test metrics

- ROC-AUC: 0.781138
- PR-AUC: 0.567889
- Brier score: 0.133149
- Log loss: 0.426351
- Precision: 0.398640
- Recall: 0.706858
- F1: 0.509783
- Confusion matrix: TN 3,258; FP 1,415; FN 389; TP 938

These are historical test results, not production performance or business
impact. Calibration curves, risk-band results and segment diagnostics are in
the governance page and generated report.

## Intended use

Educational one-month PD estimation for candidate-line scenario comparison in
the LimitIQ demonstration. Source monetary fields are converted from TWD to INR
at the documented fixed rate before modelling. PD is held constant across
candidates and ECL varies through EAD.

## Non-use

No real lending, affordability determination, customer notice, regulatory
capital, IFRS 9 provision, punitive line decrease, or causal uplift estimation.

## Inputs and explainability

Seventeen engineered behavioral features are built inside the serialized
pipeline. Customer ID, target and all demographics are excluded. Reason codes
come from actual behavioral/policy checks. Five-repeat test-set permutation
importance uses Brier degradation; it is not causal and is not an adverse-action
explanation.

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

The governance page includes development-reference PSI indicators comparing
train-plus-validation with test. These support review but are not evidence of
live production drift.
