# Validation issue ledger

Status date: 18 August 2026. Severity describes the consequence **if the system
were proposed for real credit use**; it does not imply current customer impact,
because LimitIQ is an educational demonstration.

| ID | Severity | Finding | Required remediation | Owner role | Status |
|---|---|---|---|---|---|
| VAL-01 | High | V2 used heterogeneous events and horizons for the application score. | V3 now uses one next-month Taiwan target for the decision demo and restricts the global model to research. Retain that separation. | Model Development | Closed for current educational scope; global benchmark remains prohibited for decisions |
| VAL-02 | High | No representative Indian development or validation population exists. INR is only presentation/canonical demo currency. | Obtain governed Indian application, bureau, affordability and outcome data; redevelop and independently validate. | India Credit Risk | Open; India-use blocker |
| VAL-03 | High | The split mainly tests seeded within-source interpolation, not a true future vintage or unseen population. | Freeze a sufficiently seasoned future-vintage test and perform external/transportability validation. | Model Validation | Open; production blocker |
| VAL-04 | High | No source observes response to credit-line treatment; value and expected-loss changes are simulated. | Run an approved randomized pilot with holdout, customer guardrails and observed outcome reconciliation. | Credit Strategy | Open; automation blocker |
| VAL-05 | High | Research-benchmark performance is heterogeneous: Home Credit test ROC-AUC is 0.517499 and Lending Club is 0.601517; Lending Club dominates pooled rows. | Keep the benchmark out of decisioning; establish source/product acceptance floors before any expanded research use. | Model Development | Risk avoided for decisions; open research limitation |
| VAL-06 | Medium | Region and structural missingness can identify sources and base rates. | Test source-balanced, source-held-out and missingness-restricted alternatives; document permitted context features. | Model Development | Open |
| VAL-07 | Medium | The primary model now has 500-repeat seeded bootstrap intervals, but research-cohort intervals remain absent and South German has only 200 test rows. | Add source-stratified intervals before comparative research claims; never use underpowered cohort estimates for decisions. | Model Validation | Partially remediated; open for research benchmark |
| VAL-08 | High | Fairness evidence is limited and cannot establish legal compliance or customer-outcome equity. | Define applicable groups and outcomes with Legal/Compliance; test selection, error, calibration, treatment and override outcomes. | Fair Lending / Compliance | Open; production blocker |
| VAL-09 | High | Monitoring thresholds are illustrative; no live outcomes, alerts, committee cadence or service levels exist. | Build source-to-outcome monitoring, approve thresholds, assign escalation owners and evidence rollback drills. | Model Operations | Open; production blocker |
| VAL-10 | Medium | Four-source publication clearance relies on repository-owner attestation, not independent legal opinion. | Retain supporting terms evidence and obtain legal approval for any institutional reuse or redistribution. | Data Governance / Legal | Risk accepted for public demo only |
| VAL-11 | Medium | The threshold embeds a 5:1 false-negative cost preference without an approved institutional risk appetite. | Re-estimate costs and capacity on the intended portfolio; independently approve and version the operating threshold. | Credit Policy | Open |
| VAL-12 | Low | CI and artifact controls are strong for a demonstration but do not evidence bank production access, resilience or operational controls. | Complete institution-specific security, resilience, access, audit, change and incident reviews. | Technology Risk | Open before production |

## Closure rules

- A development claim is not evidence of closure until an independent reviewer
  reproduces the result from checksum-bound inputs.
- A finding may be closed only with an owner, dated evidence, validation
  conclusion and approval authority appropriate to the proposed use.
- Workarounds restrict use; they do not close the underlying issue.
- Any material change to population, target, features, calibration, threshold,
  economics or policy reopens the affected findings.
