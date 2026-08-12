# Five-minute interview walkthrough

## 0:00–0:40 — Frame the decision and status

State that the public link is verified v1 and the multi-source v2 is local with
a blocked publication gate. Open Executive Overview and explain the governed
increase/hold/refer/freeze decision. Point to the boundary: source facts
observed, adverse-outcome probability modelled, economics simulated.

## 0:40–1:25 — Explain the multi-source evidence

Open Governance. Show 1,869,548 rows across six independent cohorts and explain
why legacy Statlog German is reference-only. Lead with macro ROC-AUC 0.6845,
PR-AUC 0.4024 and Brier 0.1390; then explain why pooled metrics are secondary and
Lending Club dominated. State that labels/horizons differ, the split is random
within source, and missingness plus one-hot region may identify source.

## 1:25–2:10 — Show the portfolio and account

Filter to `Freeze automatic increases`, search, sort and open one synthetic
`LIQ-*` profile. Walk through source context, missing fields, risk, expected-loss
proxy, reason codes and policy checks. Emphasize that the 1,200 profiles, limits
and balances are synthetic INR scenarios with no original identifiers.

## 2:10–2:55 — Stress the policy

Raise LGD/CCF or the profitability hurdle. Compare exposure, expected-loss
proxy, eligible count, action mix and simulated return. Risk is held constant
across candidate limits because no source observes randomized line treatment.
The proxy is not IFRS 9 ECL or regulatory capital.

## 2:55–3:30 — Exercise batch controls

Download the sample CSV, upload it and retrieve the decision CSV. Explain the
size/row/schema/range/duplicate limits, in-memory no-retention handling and
spreadsheet-formula-safe export.

## 3:30–4:20 — Defend governance

Show calibration, per-source metrics, provenance checksums and limitations.
Explain the terms gate: Give Me Some Credit, FICO/HELOC, Lending Club upstream
and Home Credit require review before v2 publication. Comparable protected
attributes are unavailable, so no global fairness claim is made.

## 4:20–5:00 — Close with roadmap and employer fit

Roadmap: terms clearance, leave-one-source-out and out-of-time testing,
source-balanced sensitivity, India-specific affordability/bureau data, causal
line experiments, independent validation, shadow mode and monitored pilot.

Close on consumer-risk controls for J.P. Morgan, Risk Control/monitoring for UBS,
risk technology for Morgan Stanley, or model-governance/platform controls for
State Street. Never imply that any institution reviewed or endorsed LimitIQ.
