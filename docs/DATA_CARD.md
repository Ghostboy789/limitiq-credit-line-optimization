# Data card

## Identity and provenance

Default of Credit Card Clients, I-Cheng Yeh / UCI Machine Learning Repository,
DOI https://doi.org/10.24432/C55S3H, CC BY 4.0. Version in this build:
`uci-350-30c6be3abd8d`; source SHA-256
`30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.

## Population and time

30,000 Taiwan card customers. Six months of repayment, billing and payment
behavior from April–September 2005, with a subsequent-month default indicator.
UCI reports no missing values. The observed default rate is 22.12%.

## Preparation

The pipeline validates required names, numeric conversion, positive limits,
binary target, repayment status range -2 to 9, non-negative payment amounts,
missingness and duplicate IDs. It removes invalid/duplicate-ID rows, uses fixed
stratified 60/20/20 splits and records lineage/checksums. The committed demo has
6,000 untouched-test accounts with deterministic synthetic IDs; original IDs and
all demographics are removed.

## Decision and audit fields

Decision inputs: current limit plus six repayment statuses, six bill amounts and
six payment amounts. Audit-only: sex and age on the untouched test. Excluded:
ID, target, education and marital status. Target is never a feature.

## Appropriate use

Educational PD modelling, feature engineering, calibration, portfolio scenario
design and governance demonstration. It may support reproducible research.

## Inappropriate use

Real lending, production line assignment, causal response claims, income or
ability-to-pay inference, current-market performance claims, legal compliance
claims, or population-general fairness conclusions.

## Gaps and risks

Old single-market cross-section; no income, assets, external debt, affordability,
macro scenarios, outcome timing beyond one month, LGD, EAD-at-default, line
change, acceptance, spend uplift or profit. Demographic coding is limited and
cannot establish legally relevant groups across jurisdictions.

## Maintenance

The download URL and CC BY 4.0 metadata are recorded. A rebuild computes the raw
checksum; unexpected checksum/schema changes require review before retraining.

