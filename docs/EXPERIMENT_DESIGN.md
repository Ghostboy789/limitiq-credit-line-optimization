# Credit-line pilot and experiment design

## Why a pilot is required

LimitIQ's public data contain adverse-credit outcomes but no randomized
credit-line changes. The current response elasticity, EAD and financial layer is
a deterministic simulation. It cannot identify what would happen because a
customer received a larger line.

This document specifies the minimum controlled experiment needed to replace
simulated uplift with observed evidence. It is a design, not an executed pilot,
approval or claim of causal impact.

## Objective and estimands

Among customers who pass approved eligibility and customer-protection rules,
estimate the intention-to-treat effect of offering each line action relative to
holdout:

- hold current line (control)
- offer +10%
- offer +20%
- offer +30%

The primary estimand for each treatment is the 12-month difference in observed
risk-adjusted contribution per randomized account:

`interchange + interest - credit loss - funding - capital - servicing cost`

Report component outcomes as well as the aggregate. Treat take-up as an outcome;
do not remove non-users from the primary intention-to-treat analysis. A
secondary treatment-on-the-treated estimate may use random assignment as an
instrument only if its assumptions and method are pre-specified.

## Population

Randomize only after deterministic policy eligibility is applied. Exclude or
route to human review any account with insufficient history, repeated or recent
delinquency, hardship, fraud/identity concerns, material payment deterioration,
overextension indicators, policy exposure breach or applicable legal/consent
restriction.

Freeze the eligibility query, data timestamp and reason codes before assignment.
Record all exclusions to measure selection effects. Do not apply this design in
India until the gaps in [INDIA_READINESS.md](INDIA_READINESS.md) are closed.

## Randomization

- Allocate equally across the four arms unless power or risk capacity justifies
  a documented alternative.
- Stratify on pre-treatment risk band, utilization band, current-limit band and
  material customer segment; randomize within stratum.
- Use a reproducible, access-controlled assignment seed and immutable assignment
  table.
- Keep a persistent holdout; never reassign based on post-treatment behavior.
- Blind outcome analysts to arm labels until data-quality checks are signed off.
- Analyze every account in its assigned arm.

The PD model may define pre-treatment strata or eligibility, but it must not use
post-assignment data. Reusing a model for a new population or purpose requires
specific validation.

## Power and minimum detectable effect

Set sample size from portfolio data before launch; LimitIQ has no empirical
variance for the intended population and therefore does not invent a number.

For a continuous primary outcome with variance `sigma^2`, two-sided type-I error
`alpha`, power `1-beta`, treatment size `n_t` and control size `n_c`, the
approximate minimum detectable difference is:

`MDE = (z_(1-alpha/2) + z_(1-beta)) * sigma * sqrt(1/n_t + 1/n_c)`

For equal treatment and control sizes `n`:

`n per arm = 2 * (z_(1-alpha/2) + z_(1-beta))^2 * sigma^2 / MDE^2`

For a binary guardrail near rate `p`, use the corresponding two-proportion power
calculation rather than treating the outcome as continuous. Inflate sample size
for non-take-up, attrition, delayed outcome maturity, stratification and planned
cluster effects. Control the three treatment-versus-control comparisons with a
pre-specified family-wise procedure such as Holm; do not choose the best arm
after unadjusted repeated testing.

Before launch, publish the baseline rate/variance window, alpha, power, target
MDE, multiplicity method and resulting sample by arm. If a guardrail requires a
larger sample than the profit endpoint, the guardrail determines the sample.

## Outcomes and guardrails

| Class | Measures |
|---|---|
| Primary | Observed 12-month risk-adjusted contribution per randomized account |
| Growth | Spend, purchase volume, revolving balance, interest and line utilization |
| Credit | 30+/60+/90+ delinquency, charge-off/default, loss, balance growth and overlimit events |
| Customer | Hardship, complaints, opt-out, minimum-payment stress and adverse servicing contacts |
| Operations | Offer delivery, acceptance, override, data completeness and reconciliation failures |
| Equity | Eligibility, assignment, take-up, benefit and adverse outcomes across approved review groups |

Define each event, observation window and data source before assignment. Report
absolute rates and confidence intervals, not only percentage changes.

## Stop and escalation rules

The credit committee, Model Risk, Compliance and Customer Protection functions
must approve numerical boundaries before launch. Stop new treatments and
preserve the holdout when any of these occurs:

- a pre-specified serious-delinquency, loss, hardship or complaint boundary is
  crossed
- material adverse disparity appears in a protected or vulnerable group
- assignment, consent, offer delivery or outcome reconciliation is unreliable
- policy limits or portfolio concentration are breached
- security, privacy or regulatory requirements cannot be met

An independent monitoring group should review coded arm summaries on a fixed
cadence. Investigators should not repeatedly inspect unblinded profit results.
Any early efficacy decision needs a pre-specified sequential-testing boundary;
customer-harm stops always take precedence.

## Phased execution

1. **Offline readiness:** finalize definitions, legal basis, data lineage,
   reconciliation, power, protocol and approvals.
2. **Shadow mode:** produce assignments and decisions without customer action;
   verify eligibility, overrides, capacity and monitoring.
3. **Limited pilot:** cap exposure, retain holdout, use the smallest approved
   treatments and apply independent harm monitoring.
4. **Full experiment:** expand only after the limited pilot passes predefined
   operational and customer-protection gates.
5. **Outcome maturity:** wait for the full horizon, lock analysis data and run
   the pre-registered analysis.
6. **Decision:** approve, modify or reject each arm; archive code, data receipt,
   deviations, results and committee decision.

## Promotion rule

No arm is promoted merely because simulated contribution is positive or a
point estimate beats control. Promotion requires multiplicity-adjusted evidence
on the primary endpoint, every customer-protection guardrail within its approved
boundary, stable material-segment results, operational reconciliation and formal
Credit Risk, Model Risk, Compliance and Legal approval.
