# Five-minute interview walkthrough

## 0:00–0:40 — Frame the decision and status

State that v3 uses one UCI Taiwan following-month default target for the decision
demo and keeps the 1.87M-row heterogeneous model as research only. Until final
release, say the live site is verified v2.1 and v3 is the repository candidate.
Open Executive Overview and explain increase/hold/refer/freeze plus the boundary:
source facts observed, risk modelled, profiles and economics simulated.

## 0:40–1:25 — Explain primary and research evidence

Open Governance. Lead with primary ROC-AUC 0.7574 (95% CI 0.7433–0.7738),
PR-AUC 0.5087 and Brier 0.1417 on 6,000 untouched rows. Then show the
1,869,548-row research benchmark and explain why its labels/horizons differ,
macro metrics are preferred, pooled metrics are Lending-Club-dominated and the
benchmark never drives decisions.

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
Explain the preserved terms-review history for Give Me Some Credit, FICO/HELOC,
Lending Club upstream and Home Credit, and the owner attestation that cleared the
gate. Comparable protected attributes are unavailable, so no global fairness
claim is made.

## 4:20–5:00 — Close with roadmap and employer fit

Roadmap: independent terms validation, fixed-horizon/out-of-time validation,
source-balanced sensitivity, India-specific affordability/bureau data, causal
line experiments, independent validation, shadow mode and monitored pilot.

Close on consumer-risk controls for J.P. Morgan, Risk Control/monitoring for UBS,
risk technology for Morgan Stanley, or model-governance/platform controls for
State Street. Never imply that any institution reviewed or endorsed LimitIQ.
