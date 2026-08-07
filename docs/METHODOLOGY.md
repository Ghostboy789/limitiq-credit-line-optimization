# LimitIQ methodology

## Decision objective

For each existing account, LimitIQ asks which governed action—current line,
+10%, +20% or +30%—maximizes simulated risk-adjusted contribution while meeting
loss, exposure, payment-history, customer-protection and profitability controls.
Early-warning accounts are frozen or referred. No automatic punitive decrease
is recommended.

## Evidence layers

- Observed: 30,000 UCI accounts, contractual line, six monthly repayment-status,
  bill and payment fields, and subsequent-default target.
- Model-estimated: calibrated probability of default and risk bands.
- Simulated: response, spend, EAD, LGD, revenue, cost, expected loss, candidate
  contribution and proposed line.

These labels are preserved in the website and reports. Simulated values are
scenario mechanics, not causal estimates or realized production outcomes.

## Data and features

The fixed seed is 42. Stratified partitions are 60% train, 20% validation and
20% untouched test. Model-ready decision fields plus target are saved with
per-file checksums under `data/processed/splits/` during a rebuild. Customer
ID, target, sex, education, marital status and age
are excluded from the decision pipeline. Sex and age are retained only for
offline test diagnostics. Behavioral engineering occurs inside the sklearn
pipeline so training and inference share one transformation: utilization
levels/trend, payment-to-bill ratios and consistency, delinquency count/severity,
recent deterioration, revolving proxy, headroom, volatility, balance growth and
inactive months.

## Models, calibration and selection

The baseline is regularized logistic regression. The challenger is histogram
gradient boosting. Both are sigmoid-calibrated with three-fold training data.
Candidate selection uses validation data: choose the lowest Brier score among
models within 0.02 ROC-AUC of the best. The classification threshold minimizes
a transparent validation cost in which a missed default weighs five times a
false positive. The selected type and threshold are frozen, the champion is
refit on train + validation, and the untouched test is read once.

The champion is histogram gradient boosting. Untouched-test results: ROC-AUC
0.7811, PR-AUC 0.5679, Brier 0.1331, log loss 0.4264, precision 0.3986, recall
0.7069 and F1 0.5098 at threshold 0.1739. These are historical test results, not
production performance.

## Financial logic

Management expected loss is:

`ECL = PD × LGD × EAD`

EAD is current drawn balance (capped at line) plus CCF times positive undrawn
line. Baseline PD is held constant across line candidates because the source has
no line-increase treatment. Substituting a higher line into the observational
model would manufacture an unsupported causal risk benefit.

Incremental contribution is:

`interchange + interest − incremental ECL − funding − capital − servicing`

Monthly incremental spend is simulated as incremental line × response
elasticity × observed current utilization, annualized over 12 periods. Interest
uses the revolving-rate and APR assumptions. Funding and capital costs apply to
incremental EAD. Every assumption is visible and editable. The generated policy
report fully re-optimizes low/base/high one-at-a-time scenarios for the ten
decision-critical assumptions; the interactive page also shows fast
fixed-action LGD and response-elasticity contribution sensitivities.

Model feature importance is five-repeat permutation importance on the untouched
test set using Brier-score degradation. PSI indicators compare engineered
feature distributions in train-plus-validation with the test split. Both are
descriptive development diagnostics, not causal explanations, adverse-action
reasons or substitutes for production drift monitoring.

All source monetary fields are converted before modelling at a fixed 2.97
INR/TWD, derived from official July 2026 USD reference rates. This is a
reproducible unit/presentation transform, not Indian borrower evidence or a
live-FX promise.

## Policy order

1. Detect severe/repeated delinquency, recent deterioration, rapidly rising
   revolving balance or customer-overextension signals.
2. Route severe warnings to freeze and ambiguous cases to manual review.
3. Evaluate only candidates permitted by maximum increase.
4. Reject candidates breaching account exposure, expected-loss ceiling,
   payment-history or overextension controls.
5. Reject candidates below the profitability hurdle.
6. Select maximum eligible contribution; deterministic tie-breaks prefer the
   smaller increase.
7. Enforce the portfolio growth cap by reverting the lowest-contribution
   increases first, with a reason code.

## Governance interpretation and authoritative sources

Basel CRE35 states IRB expected-loss rate as PD × LGD and amount as rate × EAD;
CRE36 defines EAD as expected gross exposure at default and requires it not be
below current drawn on-balance-sheet exposure. LimitIQ uses these components for
transparent scenario comparison, not regulatory capital:
https://www.bis.org/basel_framework/chapter/CRE/35.htm and
https://www.bis.org/basel_framework/chapter/CRE/36.htm

IFRS 9 ECL is probability-weighted discounted cash shortfall with staging,
significant-increase-in-credit-risk assessment and reasonable/supportable
forward-looking information. LimitIQ's one-period management ECL is not an IFRS
9 provision: https://www.ifrs.org/content/dam/ifrs/project/fi-impairment/ifrs-standard/published-documents/project-summary-july-2014.pdf

Current U.S. interagency model-risk guidance is Federal Reserve SR 26-2 / OCC
2026-13, which superseded SR 11-7 on 17 April 2026. It supports proportionate
development evidence, independent validation, outcome monitoring, clear
limitations, inventory, exceptions and remediation:
https://www.federalreserve.gov/supervisionreg/srletters/SR2602.pdf and
https://www.occ.treas.gov/news-issuances/bulletins/2026/bulletin-2026-13.html

U.S. Regulation Z §1026.51 requires ability-to-pay consideration before a card
line increase, including income/assets and current obligations. UCI lacks these
inputs; behavioral PD cannot substitute for a production ATP assessment:
https://www.consumerfinance.gov/rules-policy/regulations/1026/51/

Regulation B constrains prohibited-basis use and requires specific, accurate
principal reasons where adverse-action duties apply. Demographics are audit-only
and demo reason codes are not consumer notices:
https://www.consumerfinance.gov/rules-policy/regulations/1002/6/ and
https://www.consumerfinance.gov/rules-policy/regulations/1002/9/

Basel, IFRS, Federal Reserve/OCC and CFPB materials operate under different
purposes and jurisdictions. Citing them informs design; it does not establish
compliance. Local counsel, policy owners and independent validators must approve
a production use.
