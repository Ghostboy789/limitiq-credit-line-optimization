# Public dataset review

Research date: 5 August 2026. Sources below are credential-free official UCI
pages. Observation counts and licences were checked against those pages.

## 1. Default of Credit Card Clients — selected

- Publisher/source: I-Cheng Yeh; UCI Machine Learning Repository
- Official page: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients
- Direct download: https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip
- DOI: https://doi.org/10.24432/C55S3H
- Licence: CC BY 4.0
- Observations/features: 30,000 accounts; 23 predictors plus ID and binary target
- Target: default payment in the subsequent month (1 = yes, 0 = no)
- Geography/time: Taiwan; repayment, bill and payment behavior covers April–September 2005
- Features: current credit limit; six repayment-status fields; six bill amounts;
  six payment amounts; sex, education, marital status and age
- Strengths: only reviewed source with existing revolving limits, six-month
  behavior, a subsequent-default label, useful scale, explicit open licence,
  stable DOI and direct download
- Limitations: old single-market snapshot; no observed line-increase treatment,
  response, income, external obligations or economics; limited demographics
- Suitability: strongest PD-development source for an existing-card portfolio.
  ID is excluded. Demographics are audit-only. Limit response and economics are
  deterministic simulations, never represented as causal or observed.

## 2. South German Credit

- Publisher/source: UCI correction based on Open Data LMU and German sources
- Official page: https://archive.ics.uci.edu/dataset/573/south+german+credit+update
- Direct download: https://archive.ics.uci.edu/static/public/573/south%2Bgerman%2Bcredit%2Bupdate.zip
- DOI: https://doi.org/10.24432/C5QG88
- Licence: CC BY 4.0
- Observations/features: 1,000 contracts (700 good, 300 bad); 20 predictors
- Target: whether the credit contract was complied with (good/bad)
- Geography/time: South Germany, 1973–1975
- Features: checking/savings status, duration, history, purpose, amount,
  employment, installment burden, property, housing, prior credits and job
- Strengths: corrected, documented version of the widely used German data;
  real contracts and cost-sensitive framing
- Limitations: tiny, old, bad credits oversampled, installment rather than
  revolving credit, no monthly bills/payments or current line, proxy attributes
- Suitability: historical robustness comparator, not a LimitIQ primary source

## 3. Statlog Australian Credit Approval

- Publisher/source: Ross Quinlan; UCI Machine Learning Repository
- Official page: https://archive.ics.uci.edu/dataset/143/statlog+australian+credit+approval
- Direct download: https://archive.ics.uci.edu/static/public/143/statlog%2Baustralian%2Bcredit%2Bapproval.zip
- DOI: https://doi.org/10.24432/C59012
- Licence: CC BY 4.0
- Observations/features: 690 applications; 14 predictors; some missing values
- Target: positive/negative application class, recoded 1/2 by UCI
- Geography/time: Australia implied by title; period undisclosed; cited 1987
- Features: six numeric and eight categorical fields with deliberately removed
  names and values
- Strengths: small, reproducible, mixed-type credit application benchmark
- Limitations: target is not documented as subsequent default, semantics erased,
  no current line or behavior, very small and period unknown
- Suitability: preprocessing benchmark only; not defensible for PD or line action

## 4. Polish Companies Bankruptcy

- Publisher/source: Sebastian Tomczak; UCI; financials collected from EMIS
- Official page: https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data
- Direct download: https://archive.ics.uci.edu/static/public/365/polish%2Bcompanies%2Bbankruptcy%2Bdata.zip
- DOI: https://doi.org/10.24432/C5F600
- Licence: CC BY 4.0
- Observations/features: five cohorts of 7,027 / 10,173 / 10,503 / 9,792 /
  5,910 statements; 64 ratios; missing values
- Target: bankruptcy one to five years after the financial statement, by cohort
- Geography/time: Polish companies; bankrupt 2000–2012, operating 2007–2013
- Strengths: rich financial ratios, multiple horizons, useful imbalance/stability
  challenge
- Limitations: corporate insolvency, not consumer revolving credit; different
  unit, horizon and features; no line/payment behavior
- Suitability: broad credit-risk comparison only. It must not be merged with the
  selected source simply to claim more data.

## Selection decision

Default of Credit Card Clients uniquely matches the unit of decision (an
existing card account), exposes the current line and recent repayment behavior,
and provides a future-default label at meaningful scale under CC BY 4.0. It is
used only for observed descriptive statistics and PD modelling. The repository
does not infer or fabricate causal line-response evidence.

