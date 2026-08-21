# Model and decision-component inventory

Inventory date: 18 August 2026. This deliberately small register reflects the
actual v3 architecture. An institution must apply its own approved model
definition, materiality and ownership framework before any real use.

| ID | Component | Version | Current role | Status |
|---|---|---|---|---|
| MOD-001 | UCI Taiwan next-month default model | `limitiq-primary-3.0.0-89f9a2530bde` | Primary candidate for the educational synthetic decision demo | Conditional demonstration approval only |
| MOD-002 | Multi-source adverse-credit-outcome model | `limitiq-global-2.0.0-37a14c45a811` | Transportability research and governance comparison only | Explicitly prohibited from account decisioning |
| MOD-003 | Original Taiwan model | SHA starts `284f9a7c8ca2` | Archived v1 reproducibility reference | Superseded |
| CALC-001 | Candidate-limit optimizer and policy rules | v3.0.0 | +10%, +20%, +30%, hold, review and freeze simulation | Model-adjacent; high materiality if real |
| SIM-001 | Line-response and financial simulation | v3.0.0 assumptions | Synthetic EAD, loss, revenue, cost and contribution | Not causal or observed |

## MOD-001 — primary application candidate

- **Owner role:** Model Development
- **Business sponsor role:** Credit Portfolio Strategy
- **Purpose:** estimate following-month default probability for Taiwan-source-like
  inputs and drive a deterministic educational policy simulation
- **Target and horizon:** default payment in the following month; one month
- **Population:** 30,000 UCI Taiwan credit-card clients
- **Method:** histogram gradient boosting with sigmoid calibration
- **Benchmark:** calibrated regularized logistic regression
- **Split:** 18,000 train / 6,000 validation / 6,000 untouched test
- **Active inputs:** delinquency count and utilization
- **Test evidence:** ROC-AUC 0.757410 (95% CI 0.743319–0.773753), PR-AUC
  0.508729, Brier 0.141683 and log loss 0.447444
- **Prohibited use:** any real lending, India scoring, regulatory PD, IFRS 9,
  pricing, provisioning, capital or automatic customer treatment
- **Key limitations:** 2005 Taiwan source, random rather than future-vintage
  split, narrow active feature set, no Indian population and no observed line
  response
- **Rollback:** `AUTO_INCREASES_ENABLED=false` routes otherwise eligible
  increases to manual review
- **Review trigger:** any data, target, feature, calibration, threshold, policy,
  economics or intended-use change

## MOD-002 — separate research benchmark

- **Purpose:** investigate pooled and per-source ranking/calibration behavior
  across six independent public credit cohorts
- **Population:** 1,869,548 training rows; 373,910 test rows
- **Primary evidence view:** source-macro metrics; pooled metrics secondary
- **Decision boundary:** never loaded for account, batch or policy decisions in v3
- **Key limitations:** incompatible events and horizons, source dominance,
  structural missingness, weak source cohorts, no future-vintage or unseen-market
  claim
- **Validation status:** research evidence only

## Model-adjacent components

SR 26-2 excludes simple deterministic rule-based processes from its model
definition. CALC-001 still embeds material assumptions and consumes model
output, so this register treats it as controlled model-adjacent logic. SIM-001
must remain visibly simulated and cannot support production impact claims.

The RBI's [2024 draft principles](https://www.rbi.org.in/scripts/bs_viewcontent.aspx?Id=4479)
are a non-binding readiness reference only. They are not evidence of Indian
legal or regulatory compliance.
