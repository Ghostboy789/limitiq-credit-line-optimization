# LimitIQ methodology

## Decision objective

For each synthetic account, LimitIQ asks which governed action—current line,
+10%, +20% or +30%—maximizes simulated risk-adjusted contribution while meeting
loss, exposure, payment-history, overextension and profitability controls.
Early-warning profiles are frozen or referred. No automatic punitive decrease
is recommended.

## Evidence layers

- **Observed:** UCI Taiwan behavior and following-month default for the primary
  model; heterogeneous public outcomes for the separate research benchmark.
- **Model-estimated:** calibrated following-month default probability for the
  primary track; source-specific adverse-outcome score for research only.
- **Synthetic:** 1,200 demonstration profiles, limit/balance fields, response,
  EAD, LGD, revenue, cost, expected-loss proxy, contribution and action.

The v3 decision model has one event and one-month horizon. The v2 research labels
have different events and horizons and do not form a common-horizon regulatory
PD. Synthetic values are transparent scenario mechanics, not causal estimates,
forecasts or realized outcomes.

## Primary source selection and provenance

The application candidate uses UCI Default of Credit Card Clients: 30,000
Taiwan accounts with April–September 2005 behavior and following-month default,
CC BY 4.0. The source is checksum-bound and monetary fields are deterministically
converted from TWD to INR for scenario presentation. Only delinquency count and
current utilization have semantically direct harmonized mappings; other contract
fields remain explicitly missing.

## Research source selection and provenance

V2 uses six independent training cohorts totaling 1,869,548 rows. Corrected
South German replaces legacy Statlog German in training because both represent
the same 1,000-credit population; Statlog is reference-only. Each raw file is
checksummed, gitignored and linked to its origin and immediate mirror.

The public-page review did not independently establish upstream/competition
terms for four non-UCI sources. The owner supplied a resolution attestation on
14 August 2026 and cleared the project publication gate (see
[`NOTICE.md`](../NOTICE.md)). Full provenance and the historical review remain
there; this is not an independent legal opinion.

## Harmonization

Each source emits six narrow proxies: delinquency count, utilization, debt
burden, credit lines, disclosed-currency annual income and credit age. A one-hot
region context is added. Source fields are numeric-coerced, infinities become
missing and source-specific sentinels are removed.

The shared names do not create identical semantics. For example, delinquency may
mean late months, events, derogatory trades or a credit-history category; debt
burden may mean total DTI, installment percentage or annuity/income. Entire
fields are structurally missing for some sources. Region and missingness can
identify source and allow source-base-rate learning.

Only source-disclosed TWD and USD amounts are converted to INR at fixed rates.
Give Me Some Credit and Home Credit currency is undisclosed, so their monetary
fields are not converted or shown as INR. FX conversion is presentation
localization, not Indian borrower evidence or economic comparability.

## Primary split, model and selection

With seed 42, the primary population receives a stratified 60/20/20 split:
18,000 train, 6,000 validation and 6,000 untouched test. Calibrated regularized
logistic regression is the baseline and calibrated histogram gradient boosting
the challenger. Selection minimizes validation Brier among candidates within
0.02 ROC-AUC of the best. The threshold minimizes validation cost with missed
defaults weighted five times false positives. Champion and threshold are frozen
before the single test read.

The primary champion is `limitiq-primary-3.0.0-89f9a2530bde`, threshold
0.1639639640. Test ROC-AUC is 0.757410 (95% bootstrap CI 0.743319–0.773753),
PR-AUC 0.508729, Brier 0.141683 and log loss 0.447444. The split does not
establish future-vintage or geographic portability.

## Research split, model and selection

With seed 42, each training source receives a stratified random 60/20/20 split;
the parts are combined into 1,121,728 train, 373,910 validation and 373,910
untouched test rows. This design tests within-source interpolation, not
out-of-time or unseen-market generalization.

The baseline is regularized logistic regression. The challenger is histogram
gradient boosting. Both use common preprocessing and three-fold sigmoid
calibration. Candidate selection minimizes source-macro validation Brier among
models within 0.02 macro ROC-AUC of the best. The threshold minimizes validation
cost with missed adverse outcomes weighted five times false positives. Model
type and threshold are frozen before the untouched test read.

The champion is calibrated histogram gradient boosting, version
`limitiq-global-2.0.0-37a14c45a811`, threshold 0.1689189189. Test evidence:

| Metric | Source-macro | Pooled row-weighted |
|---|---:|---:|
| ROC-AUC | 0.684530 | 0.669891 |
| PR-AUC | 0.402370 | 0.304965 |
| Brier | 0.138968 | 0.140629 |
| Log loss | 0.433385 | 0.444856 |

Macro evidence is primary because Lending Club supplies 73.3% of the rows.
Histogram gradient boosting does not enforce shared effect directions. No
like-for-like cross-source ranking or new-market generalization is claimed.

## Financial logic

The educational expected-loss proxy is:

`Expected-loss proxy = primary next-month default score × LGD × EAD`

The score is not a production or regulatory PD and the result is not IFRS 9 ECL
or regulatory capital. EAD is simulated current drawn balance, capped at line, plus
CCF times positive undrawn line. Probability is held constant across candidate
limits because no source observes a randomized limit increase.

Incremental contribution is:

`interchange + interest − incremental expected loss − funding − capital − servicing`

Monthly incremental spend is simulated from incremental line, response
elasticity and current utilization, then annualized. Interest uses simulated
revolving-rate and APR assumptions. Funding and capital costs apply to
incremental EAD. All assumptions are visible, editable and deterministic.

The v3 1,200-profile base scenario produces ₹514.951M current and ₹566.423M
proposed credit limits, ₹461.467M current and ₹500.086M proposed exposure proxy,
₹53.140M current and ₹55.904M proposed expected-loss proxy, ₹9.100M simulated
incremental contribution and 23.56% contribution / incremental exposure. These
are not causal forecasts or production impact.

## Policy order

1. Detect delinquency, recent deterioration, high utilization and missing-history
   signals.
2. Route severe warnings to freeze and ambiguous/insufficient cases to manual
   review.
3. Evaluate only candidates permitted by maximum increase.
4. Reject candidates breaching account exposure, expected-loss ceiling,
   payment-history or overextension controls.
5. Reject candidates below the profitability hurdle.
6. Select maximum eligible simulated contribution; ties prefer the smaller
   increase.
7. Enforce the portfolio growth cap by reverting the lowest-contribution
   increases first.

## Governance interpretation

The benchmark demonstrates reproducibility, calibration, provenance, challenger
comparison, source-level monitoring, human review and rollback. It does not
establish compliance in any jurisdiction. Comparable protected attributes are
not available across sources, so no global fairness conclusion is possible.

Basel PD/LGD/EAD concepts inform the simulated decomposition, but LimitIQ does
not calculate regulatory capital:
https://www.bis.org/basel_framework/chapter/CRE/35.htm and
https://www.bis.org/basel_framework/chapter/CRE/36.htm

IFRS 9 requires probability-weighted discounted cash shortfalls, staging,
forward-looking information and significant-increase-in-credit-risk assessment;
the LimitIQ proxy is not an IFRS 9 provision:
https://www.ifrs.org/content/dam/ifrs/project/fi-impairment/ifrs-standard/published-documents/project-summary-july-2014.pdf

U.S. Regulation Z ability-to-pay and Regulation B adverse-action requirements
cannot be satisfied by this public-data demonstration:
https://www.consumerfinance.gov/rules-policy/regulations/1026/51/ and
https://www.consumerfinance.gov/rules-policy/regulations/1002/9/

Local counsel, policy owners, data-rights reviewers and independent model
validators must approve any real use.

## Validation roadmap

Required before portability claims: leave-one-source-out evaluation, fixed-
horizon temporally seasoned validation, source-balanced sensitivity, confidence intervals for
small cohorts, current terms-cleared populations and independent validation.

The additive Lending Club vintage split is a status-at-extract robustness check,
not fixed-horizon out-of-time PD validation. Source-context ablation removes only
explicit region; structural missingness remains. Permutation importance shuffles
within source cohorts, and fitted effect curves use deterministic, source-capped
samples only where a field is observed.
SBA loan data and Polish Companies Bankruptcy belong in separate product/domain
validation studies. PAKDD and Freddie/Fannie are not accepted into this public
union under current source/access/terms constraints.
