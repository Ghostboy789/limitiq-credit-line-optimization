# Public dataset review

Research updated 11 August 2026. “Downloadable” is not treated as synonymous
with “openly licensed.” V2 publication remains blocked wherever upstream,
competition or derived-artifact rights are unresolved.

## Training and reference sources

### 1. Default of Credit Card Clients — training; verified terms

- Publisher/source: I-Cheng Yeh; UCI Machine Learning Repository
- Official page: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients
- DOI/licence: `10.24432/C55S3H`; CC BY 4.0
- Rows/features: 30,000; 23 predictors plus ID and binary target
- Target: subsequent-month default
- Geography/time/currency: Taiwan; Apr–Sep 2005 behavior; TWD
- Strength: revolving limit and behavioral history with a defined future label
- Limitation: old single-market snapshot; no line treatment, income, external
  obligations, response, LGD, EAD or economics

### 2. South German Credit — training; verified terms

- Publisher/source: UCI correction based on Open Data LMU/German sources
- Official page: https://archive.ics.uci.edu/dataset/573/south+german+credit+update
- DOI/licence: `10.24432/C5QG88`; CC BY 4.0
- Rows/features: 1,000 contracts; 20 predictors; 700 good / 300 bad
- Target: contract complied with or not; horizon undisclosed
- Geography/time/currency: South Germany; 1973–1975; DEM
- Limitation: tiny, old, bad credits oversampled and not revolving-card behavior

### 3. Statlog German Credit — reference only; verified terms

- Official page: https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data
- DOI/licence: `10.24432/C5NC77`; CC BY 4.0
- Rows: 1,000
- Decision: excluded from training because corrected South German is a corrected
  representation of the same underlying population. Including both would create
  duplicate-population leakage and a false seventh independent cohort.

### 4. Give Me Some Credit — local training; terms unresolved

- Origin: Kaggle Give Me Some Credit competition
- Immediate source: OpenML 45577 / file 22116561
- Metadata: https://www.openml.org/api/v1/json/data/45577
- Rows: 150,000 training records
- Target: serious delinquency within two years
- Geography/currency/collection period: undisclosed
- Mirror licence field: `Public`, not a standard open licence; original
  competition terms apply
- Strength: useful scale and delinquency/utilization/debt features
- Limitation: geography/currency unknown, missing income and unresolved terms

### 5. FICO Explainable ML / HELOC — local training; terms unresolved

- Origin: FICO Explainable Machine Learning Challenge
- Immediate source: cleaned OpenML 45554 / file 22116522
- Metadata: https://www.openml.org/api/v1/json/data/45554
- Rows: 10,459 upstream; 9,871 after mirror cleaning
- Target: `RiskPerformance=Bad`; exact horizon undisclosed by mirror
- Geography/time: undisclosed; currency not applicable to used features
- Licence: OpenML says `Unknown (Kaggle) / Custom (FICO website)`
- Strength: real HELOC credit-file behavior and explainability provenance
- Limitation: small, cleaned through an intermediary and custom/unknown terms

### 6. Lending Club accepted loans — local training; terms unresolved

- Immediate source:
  https://huggingface.co/datasets/codesignal/lending-club-loan-accepted
- File: `accepted_2007_to_2018Q4.csv`
- Rows: 2,260,701 raw; 1,371,166 harmonized
- Geography/time/currency: US; 2007–2018Q4 originations; USD
- Target used: Fully Paid versus Charged Off, Default or Late at extract; other
  statuses excluded; variable horizon
- Mirror licence: CC0-1.0; upstream Lending Club rights not independently verified
- Strength: largest cohort with utilization, DTI, income, credit lines and age
- Limitations: row dominance, status/censoring selection, variable horizons,
  vintage drift and unresolved upstream rights

### 7. Home Credit application data — local training; terms unresolved

- Origin: Home Credit Default Risk competition
- Immediate unofficial mirror:
  https://huggingface.co/cantalapiedra/poc_scoring_fair/blob/main/application_train.csv
- Rows: 307,511
- Target: payment difficulty; X-day delinquency within Y days, with X/Y and
  horizon undisclosed
- Geography/currency/collection period: undisclosed
- Licence: no compatible mirror licence established; original competition terms
  require review
- Strength: second cohort above 200,000 rows
- Limitations: geography, currency and target parameters undisclosed; only narrow
  application proxies harmonize; terms unresolved

## V1 external-validation sources

### Statlog Australian Credit Approval

- Official page: https://archive.ics.uci.edu/dataset/143/statlog+australian+credit+approval
- DOI/licence: `10.24432/C59012`; CC BY 4.0
- Rows/features: 690 applications; 14 anonymized predictors
- Target: approval class, not documented future default
- Use: preprocessing/methodology benchmark only; never a PD source

## Additional-dataset search

### SBA loan-level data — separate validation roadmap

U.S. Small Business Administration loan-performance data can support a governed
business-lending validation study. It is not merged into the consumer union:
borrower unit, guarantee structure, underwriting policy and default/charge-off
outcomes differ materially. Confirm the exact SBA release, data dictionary,
licence and reporting lag before use.

### Polish Companies Bankruptcy — separate validation roadmap

- Official page:
  https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data
- DOI/licence: `10.24432/C5F600`; CC BY 4.0
- Population: Polish companies; five cohorts; 64 financial ratios
- Target: bankruptcy one to five years after financial statement
- Decision: useful corporate-credit stability/transfer study, but not merged with
  consumer accounts merely to claim more global rows.

### PAKDD 2009 — rejected for public union

Potential consumer-credit relevance does not overcome the absence of a dependable
credential-free authoritative source and verified redistribution/derived-artifact
terms. Do not use an unofficial copy to satisfy a row or geography target.

### Freddie Mac and Fannie Mae — rejected for public union

Their mortgage-performance datasets have valuable time-series outcomes but come
with access agreements, product-specific schemas and attribution/use obligations.
Mortgage servicing performance is not interchangeable with revolving or
unsecured consumer outcomes. Consider only as a separately governed mortgage
study after reviewing the then-current terms; do not add them to this public union.

## Selection decision

The local research benchmark uses six independent cohorts totaling 1,869,548
rows and retains legacy Statlog only as reference. This satisfies scale but not a
common PD definition or global representativeness. Source-macro metrics are
primary because Lending Club dominates raw rows. Public v2 distribution is
blocked until all unresolved terms are cleared; if they cannot be cleared, the
deployable model must be retrained on compatible sources.
