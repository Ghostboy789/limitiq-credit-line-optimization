# Data card

## Version boundary

- **V1, verified public deployment:** UCI Default of Credit Card Clients only;
  dataset version `uci-350-30c6be3abd8d-inr297`.
- **V2, deployed 12 August 2026:** six independent training cohorts plus one
  duplicate-population reference file; dataset version
  `global-7-94bb4c0ad0f1` and provenance checksum
  `94bb4c0ad0f13d7677b9afe00a4943850ea890df5be3450592be69b1b14340dd`.

V2 is a multi-source adverse-credit-outcome benchmark. It is not a
common-horizon regulatory PD dataset.

## Training population

| Source | Role | Raw / harmonized rows | Geography and period | Label / horizon | Currency |
|---|---|---:|---|---|---|
| Taiwan Credit | train | 30,000 / 30,000 | Taiwan; behavior Apr–Sep 2005 | Subsequent-month default / one month | TWD |
| South German Credit | train | 1,000 / 1,000 | South Germany; 1973–1975 | Contract good/bad / undisclosed | DEM |
| Statlog German | reference only | 1,000 / excluded | Same underlying South German population | Legacy good/bad coding | DEM |
| Give Me Some Credit | train | 150,000 / 150,000 | Geography and collection period undisclosed | Serious delinquency / two years | Undisclosed |
| FICO/HELOC cleaned mirror | train | 10,459 upstream / 9,871 | Geography and period undisclosed | `RiskPerformance=Bad` / undisclosed | Not applicable |
| Lending Club | train | 2,260,701 / 1,371,166 | US; accepted loans 2007–2018Q4 | Status at extract / variable | USD |
| Home Credit | train | 307,511 / 307,511 | Geography and period undisclosed | Payment difficulty / X and Y undisclosed | Undisclosed |

Total independent training rows: **1,869,548**. Lending Club supplies 73.3% of
the union, so pooled evaluation is row-weighted and source-macro evaluation is
primary.

Statlog German and corrected South German are not independent cohorts. UCI
describes South German as a corrected representation of the same population;
Statlog is kept for reference and excluded from model fitting and row budgets.

## Harmonized fields

| Field | Source-dependent meaning |
|---|---|
| `delinquency_count` | Recent delayed months, delinquency events, derogatory trades or a binary historical-credit proxy |
| `utilization` | Statement/limit, unsecured revolving utilization or net revolving burden |
| `debt_to_income` | Total DTI, installment burden or annuity-to-income proxy |
| `credit_lines` | Open lines/loans, total trades or an ordinal existing-credit proxy |
| `income_inr` | Annual income converted only where source currency is disclosed |
| `credit_age_months` | Oldest-trade age where available |
| `region` | One-hot categorical context: Asia, Europe, North America or undisclosed |

These mappings are deliberately narrow but not semantically identical. Entire
fields are structurally missing for some sources. Region and missingness may
identify source and allow the model to learn source base rates.

## Currency treatment

Only source-disclosed currencies are localized to INR at fixed, documented
rates: TWD 2.97 and USD 83. Home Credit and Give Me Some Credit currency is
undisclosed, so their monetary values are not represented as INR. FX conversion
is a reproducible presentation transform, not Indian borrower evidence or proof
of cross-market economic comparability.

## Preparation and split

Each harmonizer enforces the common schema, numeric coercion, binary labels,
bounded source-specific transformations and missing-value handling. Every raw
file receives a SHA-256 checksum. HELOC negative special values become missing;
Give Me Some Credit 96/98 delinquency placeholders become missing; Lending Club
excludes Current/In Grace and other uncategorized statuses; and legacy Statlog is
excluded from training.

The fixed seed is 42. A seeded random 60/20/20 split is created within each
source and then combined, producing 1,121,728 train, 373,910 validation and
373,910 untouched-test rows. This is interpolation within represented sources,
not out-of-time or unseen-country validation.

## Synthetic demonstration

The app uses 1,200 deterministic synthetic profiles with `LIQ-*` identifiers and
synthetic INR limit/balance fields. The profiles are shaped for demonstration;
they are not source rows, customers or production outcomes. Published economics
and recommendations are deterministic scenario outputs.

## Appropriate use

- educational harmonization and model-governance study;
- within-source discrimination and calibration comparison;
- source-macro versus pooled metric analysis;
- governed synthetic portfolio and policy simulation;
- demonstrating provenance, checksums, reason codes and human-review controls.

## Inappropriate use

- real lending, customer eligibility or line assignment;
- common-horizon, IFRS 9 or regulatory PD claims;
- unseen-market or Indian-population performance claims;
- causal response, realized profit or production-impact claims;
- cross-jurisdiction fairness or legal-compliance conclusions;
- public redistribution of blocked v2 artifacts before terms review.

## Terms and publication status

UCI Taiwan, corrected South German and legacy Statlog German are CC BY 4.0.
Give Me Some Credit, FICO/HELOC, Lending Club upstream and Home Credit required
manual terms review; the owner documented the evidence and directed publication
on 12 August 2026. See [`NOTICE.md`](../NOTICE.md) for origin, mirror, revision,
checksum, review log and decision details.

## Maintenance

On rebuild, compare every raw hash, row count, risk rate, missingness profile and
schema with versioned evidence. Any source revision, new source or terms change
requires review. Future validation should include leave-one-source-out,
out-of-time and source-balanced sensitivity analyses before portability claims.
