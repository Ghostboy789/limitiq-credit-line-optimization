# Five-minute interview walkthrough

## 0:00–0:40 — Frame the banking decision

Open Executive Overview. Explain that the product chooses among governed line
candidates, balancing growth, expected loss, overextension and exposure. Point
to the evidence boundary: source facts observed, PD modelled, economics simulated.

## 0:40–1:30 — Show the portfolio

Open Portfolio Explorer. Filter to `Freeze automatic increases`, sort/search and
download the filtered CSV. Open one synthetic account. Walk through repayment,
bill/utilization history, PD/ECL, actual reason codes and pass/fail policy checks.
Emphasize no personal/original identifier or demographic input.

## 1:30–2:20 — Stress the policy

Open Simulator. Raise LGD/CCF or the profitability hurdle and run the scenario.
Compare exposure, expected loss, eligible count, action mix and simulated return
with baseline. State that PD is held constant across candidates because causal
line-response data do not exist.

## 2:20–3:00 — Exercise batch operations

Download the sample CSV, upload it, and receive the decision CSV. Explain the 5
MB / 5,000-row caps, exact schema/range/duplicate checks, in-memory processing,
no retention and spreadsheet-formula-safe export.

## 3:00–4:05 — Defend the model

Open Governance. Compare calibrated logistic vs histogram boosting; show frozen
threshold, untouched-test metrics, calibration, confusion matrix, risk bands,
behavioral signal ranking and audit-only segments. Explain why accuracy was not
the selection criterion and why segment metrics do not prove compliance.

## 4:05–5:00 — Close with governance and roadmap

Open Reports and the executive PDF/model/data cards. Call out Regulation Z
ability-to-pay as the production blocker, SR 26-2 validation/monitoring, controlled
overrides and rollback to no automatic increases. Roadmap: current multi-market
behavior, verified ATP data, randomized line experiments, causal elasticity/LGD/
CCF estimation, independent validation and limited monitored pilot.

