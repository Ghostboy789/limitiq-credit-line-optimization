# India deployment-readiness assessment

## Current verdict

**Not ready for Indian customer decisions.** LimitIQ has no demonstrated Indian
development sample, Indian validation sample or observed Indian line-increase
outcomes. INR is the canonical demonstration currency and default display, but
currency conversion does not make foreign or undisclosed populations Indian.

This document is a gap assessment, not legal advice, regulatory approval or a
claim that the model complies with Indian law.

## Regulatory reference boundary

The Reserve Bank of India published a [draft circular on Regulatory Principles
for Management of Model Risks in Credit](https://www.rbi.org.in/scripts/bs_viewcontent.aspx?Id=4479)
on 5 August 2024. It covers lifecycle governance, model inventory, independent
validation, change control, monitoring, explainability, auditable overrides and
at-least-annual validation in its draft text.

The source is explicitly a **draft circular for comments**. LimitIQ uses it only
as an organizing reference. Before any pilot, Indian Legal and Compliance must
identify the final, current requirements applying to the institution, product,
data, customer communication and outsourcing arrangement.

The RBI [Credit Card and Debit Card — Issuance and Conduct Directions,
2022](https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12300), updated
7 March 2024, are the authoritative product-policy reference used for two
implemented safeguards: known limits from other entities enter aggregate
exposure review, and a positive eligibility offer cannot activate without the
customer's explicit acceptance. Institution-specific Legal and Compliance
approval remains mandatory.

## Data gaps

| Required evidence | Current LimitIQ evidence | Gap to close |
|---|---|---|
| Indian application population | None | Representative applications across intended product, channels and geographies |
| Credit-bureau history | No Indian bureau data | Governed bureau attributes, inquiry/trade history, delinquencies and source-quality controls |
| Affordability | Incomplete public proxies | Verified income, employment, obligations, FOIR/debt-service measures, dependants and hardship indicators under approved policy |
| Existing relationship | Synthetic behavior only | Card tenure, payments, statements, utilization, transaction and servicing history with clear lineage |
| Outcome target | One coherent Taiwan next-month target for the primary model; mixed labels in research only | One India-specific adverse event, performance window, observation point and maturity rule |
| Line treatment | No observed treatment | Randomized holdout and +10%/+20%/+30% offers with take-up and outcomes |
| Customer protection | Generic policy rules | Local overextension, vulnerable-customer, hardship, notification, dispute and adverse-action controls |
| Fairness | Limited source diagnostics | Legally reviewed groups, representativeness, error/treatment/outcome tests and remediation process |
| Macroeconomic coverage | None | Development and stress evidence across relevant Indian economic conditions |
| Data rights and privacy | Public/synthetic demonstration | Documented purpose, lawful use, consent/notice where required, retention, access, deletion and vendor controls |

## Model-development gates

1. State the intended card product, existing-customer population, decision,
   adverse event and horizon in one approved specification.
2. Build a time-indexed Indian dataset with application, behavior, bureau,
   affordability, decision, treatment and mature outcome lineage.
3. Freeze development, calibration and genuinely later validation vintages.
4. Compare a transparent scorecard/logistic benchmark with any challenger.
5. Evaluate discrimination, calibration, stability and threshold performance
   overall and for material customer, channel, geography and risk segments.
6. Add confidence intervals and stress/sensitivity evidence.
7. Validate reason codes, manual reviews and overrides against actual cases.
8. Estimate line response only from a governed experiment or credible causal
   design; never transfer the current synthetic elasticity.

## Executable readiness and validation contracts

`docs/INDIA_DATA_CONTRACT.json` now requires tokenized customer references,
timezone-aware consent and evidence timestamps, fresh bureau and verified-income
records, current and other-issuer sanctioned limits, obligations, balance,
statement history and lineage. `validate_india_contract` derives FOIR,
utilization, aggregate credit limit and aggregate-limit-to-income measures but
returns no PD or lending decision. A positive line recommendation is only an
eligibility offer; explicit customer acceptance is required before activation.

`python -m limitiq.india_validation INPUT.csv --output-dir OUTPUT` is the
governed local-outcome runner. It requires a complete 12-month default outcome,
at least four snapshot months and unique account/month pairs. It creates ordered
train, calibration, model-selection and final-test periods, excludes held-out
accounts from development, compares logistic and histogram-gradient models,
and checksums the selected artifact and report. No Indian model artifact is
committed because no representative governed Indian outcomes were supplied.

## Governance and control gates

- Board-approved model-risk and credit-line policy appropriate to materiality
- Complete inventory of model, data, policy engine, overlays and third parties
- Independent validation before deployment and after material change
- Documented approval of model, calibration, threshold, eligibility, exposure
  and customer-protection limits
- Auditable human overrides with reason, authority and outcome review
- End-to-end input/output reconciliation and immutable model/data versions
- Monitoring for data quality, drift, calibration, outcomes, fairness, overrides,
  complaints, hardship, concentration and financial performance
- Tested rollback that stops automatic increases without punitive automatic
  decreases
- Access, privacy, retention, incident, business-continuity and vendor controls
- Clear customer communication, complaint handling and remediation approved by
  Legal and Compliance

## Minimum validation package

- Conceptual-soundness review tied to the Indian use case
- Independent code and implementation verification
- Benchmark and challenger replication
- Future-vintage and, where possible, independent external validation
- Calibration and rank-order evidence with confidence intervals
- Policy cut-off, affordability and capacity challenge
- Customer-outcome and fairness analysis
- Stress and sensitivity tests for income, obligations, utilization, delinquency,
  funding, loss and response assumptions
- Pilot protocol and observed outcome analysis
- Finding ledger, approval conditions, monitoring plan and rollback test

## Readiness decision

INR display, a global research union and clean software engineering are useful
portfolio evidence, not India model evidence. India readiness remains **red**
until representative local data, an India-specific target, independent validation,
observed treatment evidence and institution-specific approvals exist. Until
then, the only permitted India use is education, research planning and
demonstration with synthetic identifiers.
