# Independent validation-style review

## Decision

**Conditional approval for educational research and synthetic policy
demonstration only.** LimitIQ v3.0.0-rc is not approved for lending decisions,
regulatory probability of default (PD), pricing, provisioning, capital,
customer treatment, Indian-customer decisions or automated credit-line changes.

V3 materially improves conceptual soundness by using one UCI Taiwan next-month
default target for the application candidate and moving the heterogeneous
multi-source score to a research-only track. Production interpretation remains
blocked because the source is old and Taiwan-only, validation is random rather
than out-of-time, active features are narrow, and all line-response and
financial outcomes are simulated.

This is an independent-validation **style** review written for a portfolio
project. It is not organizationally independent model validation: no separate
bank validation function, legal team, compliance function or credit committee
approved it.

## Scope and evidence

Review date: 18 August 2026.

| Item | Reviewed evidence |
|---|---|
| Primary model | `limitiq-primary-3.0.0-89f9a2530bde` |
| Primary dataset | UCI 350 next-month default; 30,000 rows |
| Research benchmark | `limitiq-global-2.0.0-37a14c45a811`; 1,869,548 rows |
| Implementation | v3.0.0 release candidate; not yet live at review time |
| Development evidence | `reports/primary_model.json`, `reports/global_model.json`, calibration, source diagnostics and checksum metadata |
| Controls | policy constraints, reason codes, manual review, early-warning freeze, `AUTO_INCREASES_ENABLED` rollback |
| Verification | 112 local tests passed at 72.82% scoped coverage; Ruff/format/Bandit/pip-audit/provenance/runtime smoke passed. CI, container and live v3 gates remain pending |
| Documentation | methodology, data card, model card, assumptions, provenance notice and monitoring baseline |

The review follows the risk-based themes in the US interagency [Revised
Guidance on Model Risk Management, SR 26-2](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm):
effective challenge, conceptual soundness, outcomes analysis, ongoing
monitoring and controls appropriate to intended use. SR 26-2 superseded SR
11-7 on 17 April 2026. The RBI's [5 August 2024 draft credit-model-risk
principles](https://www.rbi.org.in/scripts/bs_viewcontent.aspx?Id=4479) are used
only as a non-binding India-readiness reference; the document is explicitly a
draft, not a claim of current legal compliance.

## Intended and prohibited use

### Conditionally permitted

- Demonstrate source-aware credit-risk research.
- Compare a calibrated logistic baseline with a calibrated tree challenger.
- Explore deterministic candidate-limit policy under disclosed assumptions.
- Train interviewers and portfolio users on model-risk questions.
- Exercise synthetic batch, account, simulator and governance workflows.

### Prohibited

- Score, approve, decline, price, freeze or change any real customer's credit.
- Interpret the output as a common-horizon, through-the-cycle, point-in-time,
  Basel, IFRS 9 or Ind AS 109 PD.
- infer causal response to a credit-line increase or claim realized profit.
- Apply the score to India or any unseen population without local development,
  validation, governance and legal review.
- Use pooled metrics alone to claim cross-market performance or fairness.
- Treat owner attestation about source publication rights as legal advice.

## Effective challenge summary

### Conceptual soundness — not acceptable for production use

The candidate-action design is sound for a management simulation: it evaluates
only +10%, +20%, +30% and no-change candidates, then applies exposure, expected
loss, profitability, payment-history, overextension and review constraints.
The system does not automatically prescribe punitive limit decreases.

The v3 decision construct uses one explicit target—default payment in the
following month—and one source. This closes the v2 target-coherence finding for
the current educational scope. It does not make the model a production PD: the
source is Taiwan-only and historical, only two harmonized fields are active,
and the split is not a future vintage.

The six-cohort global score remains separate research. Its targets include
next-month default, two-year serious delinquency, historical good/bad credit,
status at extract and payment difficulty. Pooling those labels does not create a
shared PD event or horizon; region and structural missingness can identify
sources and base rates. V3 never loads that artifact for account decisions.

### Primary development evidence — adequate for demonstration

The primary calibrated histogram-gradient-boosting champion was selected
against a calibrated regularized-logistic baseline using validation
discrimination and Brier score. On 6,000 untouched test rows it records:

| Metric | Result | Seeded 95% bootstrap interval |
|---|---:|---:|
| ROC-AUC | 0.757410 | 0.743319–0.773753 |
| PR-AUC | 0.508729 | 0.480370–0.542755 |
| Brier score | 0.141683 | 0.136133–0.146975 |
| Log loss | 0.447444 | 0.433312–0.460640 |

The 500-repeat intervals quantify sampling uncertainty on this test population;
they do not cover temporal, geographic or model-selection uncertainty.

### Multi-source benchmark evidence — adequate for research only

The champion is sigmoid-calibrated histogram gradient boosting. Selection uses
source-macro validation evidence rather than accuracy alone. On the untouched
test split it records:

| Metric | Source macro | Pooled, row weighted |
|---|---:|---:|
| ROC-AUC | 0.684530 | 0.669891 |
| PR-AUC | 0.402370 | 0.304965 |
| Brier score | 0.138968 | 0.140629 |
| Log loss | 0.433385 | 0.444856 |

The regularized-logistic benchmark has validation macro ROC-AUC 0.609702 and
macro Brier 0.180764; the histogram challenger has 0.678085 and 0.141845. This
supports challenger selection for the defined research exercise.

Evidence is uneven. Source test ROC-AUC ranges from 0.517499 for Home Credit to
0.852894 for Give Me Some Credit. Lending Club contributes 274,234 of 373,910
test rows and records ROC-AUC 0.601517, so pooled evidence must remain secondary.
The South German test cohort has only 200 rows. Per-source confidence intervals
have not been produced.

### Calibration and threshold — adequate for demonstration

The primary model uses sigmoid calibration and a threshold of 0.163964 frozen
on validation data using a five-to-one false-negative cost preference. That is a
documented research preference, not an institution-approved risk appetite or
customer-treatment boundary. For the research model, the pooled mean absolute
calibration-bin gap is 0.001161 and source-macro gap is 0.026968; the difference
shows why pooled calibration cannot substitute for source review.

The production candidate should choose thresholds from explicit business costs,
capacity and customer-protection limits, then validate them on the intended
population. Threshold changes should be independently approved and versioned.

### Outcome analysis — incomplete

The primary untouched test supports within-Taiwan-source interpolation evidence.
It does not establish future-vintage, unseen-country or Indian performance. The
research model's Lending Club vintage split is a status-at-extract robustness
study with unequal seasoning, not fixed-horizon out-of-time PD validation.

No source observes customer response to a credit-line increase. Expected loss,
EAD, revenue, cost and incremental contribution in the application are
deterministic simulations. They cannot back-test a real credit-line policy. A
controlled pilot is specified in [EXPERIMENT_DESIGN.md](EXPERIMENT_DESIGN.md).

### Monitoring and controls — designed, not operational

The project records a test-split monitoring baseline and illustrative triggers
for score PSI, calibration, source mix, risk rate and missingness. It also has a
rollback control that disables automatic increases and sends otherwise eligible
cases to manual review.

There is no live production scoring feed, realized-outcome join, alerting job or
approved monitoring committee. Accordingly, the thresholds are governance
proposals, not validated alert limits. Production approval would require a
dated population baseline, outcome availability map, owners, service levels,
escalation evidence and regular performance reporting.

### Fairness and customer protection — incomplete

Demographic variables are excluded from decision features and used only where
available for limited offline diagnostics. Neither the Taiwan primary source
nor the heterogeneous research sources can establish Indian fair-lending,
affordability or customer-protection compliance. Protected-class coverage,
representativeness, label quality and decision-outcome analysis are insufficient
for a legal fairness conclusion.

Positive controls include explicit eligibility constraints, early-warning
freeze, manual review, reason codes and no automatic punitive decrease. These
controls reduce risk but do not replace local fairness and customer-outcome
testing.

### Implementation verification — satisfactory for current scope

Training and inference share serialized preprocessing. Dataset and model
checksums, source provenance, fixed seeds, bootstrap evidence and artifact
consistency checks are recorded. Strict upload validation, transient processing,
security headers, safe production errors, liveness/readiness and aggregate-only
operations telemetry are implemented. The full local suite passed 112 tests at
72.82% scoped coverage with clean lint, format, Bandit and dependency audit. CI,
container and live deployment evidence remains a release gate. These controls
support the educational scope and do not certify a bank production environment.

## Validation findings

The authoritative finding status is maintained in
[VALIDATION_ISSUES.md](VALIDATION_ISSUES.md). Approval cannot expand beyond the
educational scope while any high-severity production blocker remains open.

## Approval conditions for a production candidate

1. Confirm one intended product and population while retaining the coherent
   adverse event and horizon established by the primary track.
2. Develop and validate on representative, legally usable data from that
   population, including a true future-vintage holdout.
3. Produce confidence intervals, benchmark and sensitivity evidence at the
   model, threshold, risk-band and material-segment levels.
4. Validate affordability, fairness, reason codes and overrides under applicable
   law and policy.
5. Estimate line response through a governed randomized pilot, not the current
   synthetic layer.
6. Establish independent validation, model inventory, change control, monitoring
   ownership, outcome joins and rollback testing.
7. Obtain data-rights, legal, compliance, credit-policy and risk-committee
   approval before any real decision use.

## Validator conclusion

LimitIQ shows strong model-risk awareness precisely because it does not hide its
limitations. The coherent primary track is suitable for an educational
portfolio, and the heterogeneous model is properly restricted to research.
Historical Taiwan data, lack of local/out-of-time validation and simulated
treatment economics remain decisive production blockers. The appropriate
verdict is **conditional approval for demonstration only; reject all real-credit
use**.
