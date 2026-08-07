# Dataset attribution

LimitIQ uses **Default of Credit Card Clients**, created by I-Cheng Yeh and
distributed by the UCI Machine Learning Repository:

- Source: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients
- DOI: https://doi.org/10.24432/C55S3H
- Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Citation: Yeh, I. (2009). *Default of Credit Card Clients* [Dataset]. UCI
  Machine Learning Repository.

The repository does not redistribute the raw XLS source. The build pipeline
downloads it from UCI and records its SHA-256 checksum. The committed
demonstration artifact contains behavioral fields and deterministic synthetic
account identifiers; original IDs and demographic attributes are excluded.

## External validation datasets

The external-validation report re-runs the same modelling methodology on two
additional credit datasets also distributed by the UCI Machine Learning
Repository under CC BY 4.0:

- **Statlog (German Credit Data)**
  - Source: https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data
  - DOI: https://doi.org/10.24432/C5NC77
- **Statlog (Australian Credit Approval)**
  - Source: https://archive.ics.uci.edu/dataset/143/statlog+australian+credit+approval
  - DOI: https://doi.org/10.24432/C59012

The build script `python -m limitiq.external` downloads each ZIP from UCI,
record its SHA-256 checksum, and writes `reports/external_validation.json` and
`reports/external_validation_report.html`.

