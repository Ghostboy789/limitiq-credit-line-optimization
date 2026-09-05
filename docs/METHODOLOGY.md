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

The v4 behavioral decision model has one event and one-month horizon. The v2 research labels
have different events and horizons and do not form a common-horizon regulatory
PD. Synthetic values are transparent scenario mechanics, not causal estimates,
forecasts or realized outcomes.

## Primary source selection and provenance

The application primary uses UCI Default of Credit Card Clients: 30,000
Taiwan accounts with April–September 2005 behavior and following-month default,
CC BY 4.0. The source is checksum-bound and monetary fields are deterministically
converted from TWD to INR for scenario presentation. V4 uses 17 engineered
features from the six-month repayment-status, bill and payment history. Customer
ID and demographic attributes remain excluded from inference.

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

The primary champion is `limitiq-behavioral-4.0.0-21234ab33f78`, threshold
0.1738738739. Test ROC-AUC is 0.781138 (95% bootstrap CI 0.767398–0.796055),
PR-AUC 0.567889, Brier 0.133149 and log loss 0.426351. Against the frozen v3
model on identical test rows, paired intervals show material improvement in
all four metrics. The split does not
establish future-vintage or geographic portability.

## Separate temporal study

A US Lending Club research track uses only application-time features and
terminal 36-month loans. Training vintages end in 2013, 2014 is calibration and
2015 is an untouched test. The deterministic 400,000-row sample records test
ROC-AUC 0.649217, PR-AUC 0.232211, Brier 0.123224 and log loss 0.405290.
Expanding-window tests cover every feasible vintage and the report separately
measures high revolving utilization, high DTI and prior delinquency cohorts.
This is installment-loan temporal evidence with unavailable within-term event
timing; it never feeds card decisions or claims India portability.

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
or regulatory capital. EAD is simulated current drawn balance, capped at line,
plus effective CCF times positive undrawn line. Effective CCF is the explicit
assumption `min(base CCF + risk-CCF sensitivity × score, 100%)`. Probability is
held constant across candidates because no source observes a randomized increase.

Incremental contribution is:

`interchange + interest − incremental expected loss − funding − capital − servicing`

Monthly incremental spend is simulated from incremental line, response
elasticity and current utilization, multiplied by
`exp(-response_decay_kappa × increase_pct)`, then annualized. Interest uses
simulated revolving-rate and APR assumptions. Funding and capital costs apply
to incremental EAD. All parameters are visible deterministic assumptions.

The v4 1,200-profile base scenario produces 147 +10% and 47 +20% actions.
It has ₹478.947M current and ₹488.379M proposed credit limits, ₹428.861M current
and ₹436.414M proposed exposure proxy, ₹53.247M current and ₹53.746M proposed
expected-loss proxy, ₹0.460M simulated incremental contribution and 6.10%
contribution / incremental exposure. These
are not causal forecasts or production impact.

## Policy order

1. Detect delinquency, recent deterioration, high utilization and missing-history
   signals.
2. Route severe warnings to freeze and ambiguous/insufficient cases to manual
   review.
3. Evaluate only candidates permitted by maximum increase.
4. Reject candidates breaching account exposure, expected-loss-rate ceiling,
   payment-history or overextension controls.
5. Reject candidates below the profitability hurdle.
6. Select maximum eligible simulated contribution. The MILP objective normalizes
   contribution before applying a bounded dimensionless index tie-break, so
   deterministic ordering does not depend on INR scale.
7. Solve one candidate per account jointly with a mixed-integer program under
   portfolio growth, loss-growth, capital-budget and higher-risk concentration
   caps. If the solver cannot return a feasible allocation, fail closed rather
   than silently weakening a constraint.

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
