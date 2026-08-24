# LimitIQ v4 decision-science workbench

## Status and evidence boundary

V4 is the verified application release. The behavioral model has replaced v3
inside the application after paired improvement and inference-contract migration;
CI, container and live production checks bind the deployed implementation
commit. No result below is production impact. Taiwan outcomes are
observed; candidate scores are model estimates; portfolio, monitoring and experiment
outcomes are deterministic simulations.

## 1. Rich behavioral primary

The candidate keeps the UCI Taiwan following-month target and the frozen 18,000 /
6,000 / 6,000 split, but restores six months of repayment status, bills and payments.
The shared `FeatureBuilder` derives 17 behavioral measures; demographic attributes and
customer ID remain excluded.

| Same untouched 6,000 accounts | V4 behavioral | V3 two-feature | V4 minus v3, paired 95% interval |
|---|---:|---:|---:|
| ROC-AUC | 0.781138 | 0.757410 | +0.023728 [0.017680, 0.030144] |
| PR-AUC | 0.567889 | 0.508729 | +0.059160 [0.044466, 0.075197] |
| Brier score | 0.133149 | 0.141683 | -0.008533 [-0.010342, -0.006640] |
| Log loss | 0.426351 | 0.447444 | -0.021093 [-0.025538, -0.016470] |

Intervals use 500 seeded paired bootstrap samples. This is a credible within-source
improvement, not temporal or India validation. Candidate artifact:
`limitiq-behavioral-4.0.0-21234ab33f78`.

## 2. Separate temporal track

The Lending Club track uses only application-time features and terminal 36-month loans.
Training vintages end in 2013, 2014 is reserved for calibration and 2015 is evaluated
once. The deterministic proportional sample contains 69,912 training, 65,702 validation
and 114,385 test loans. The 2015 result is ROC-AUC 0.647084, PR-AUC 0.229972,
Brier 0.122924 and log loss 0.404746.

This is US installment-loan temporal evidence, not a card next-month PD. Status timing
inside the contractual term is unavailable. It never feeds LimitIQ recommendations.

## 3. Portfolio-wide optimization

`recommend_portfolio` now solves a binary multiple-choice allocation rather than
removing low-value recommendations greedily. It selects one candidate per account while
respecting portfolio exposure growth, loss growth, capital budget and higher-risk
concentration limits. The existing account eligibility and customer-protection rules
remain hard constraints.

## 4. Monitoring replay

`python -m limitiq.monitoring_ops --demo` produces a checksum-bound stable and degraded
month. The frozen-baseline replay is green (score PSI 0.006335); the degraded replay is
red (PSI 8.539213, Brier deterioration 0.067020) and requires disabling automatic
increases plus rollback review. For approved real outcomes, `--input` returns exit code
2 on red.

## 5. Randomized experiment plumbing

`python -m limitiq.experiment` executes deterministic assignment, ITT comparison, CUPED
adjustment, guardrail summaries and a two-proportion power calculation across control,
+10%, +20% and +30% arms. The included synthetic replay verifies analysis code only.
At a 10% baseline event rate, 1 percentage-point absolute MDE, 80% power and 5% alpha,
the illustrative requirement is 14,751 accounts per arm.

## 6. Model-linked explanations

`limitiq.explain` changes repayment, bill/utilization, payment and balance-trend groups
one at a time and measures the behavioral candidate's score response. These local
sensitivities are shown separately from policy checks and business reason codes. They
are not causal customer counterfactuals.

## 7. Maker-checker workflow

The process-local review ledger accepts synthetic `LIQ-######` accounts only, restricts
decisions and reasons to governed values, requires a different checker and chains every
event cryptographically. It stores no uploaded or real customer data and intentionally
resets with the process.

## 8. India readiness contract

[`INDIA_DATA_CONTRACT.json`](INDIA_DATA_CONTRACT.json) specifies consent, bureau and
income freshness, DPD, obligations, verified income, statement history, exposure and
lineage fields. The executable validator rejects direct identifiers including PAN and
Aadhaar and returns readiness diagnostics only—never a PD or lending decision.

## Reproduce the evidence

```powershell
python -m limitiq.behavioral --bootstrap-repeats 500
python -m limitiq.temporal --max-rows 250000
python -m limitiq.monitoring_ops --demo
python -m limitiq.experiment --rows 20000
python -m pytest tests/test_behavioral.py tests/test_temporal.py tests/test_optimizer.py tests/test_monitoring_ops.py tests/test_experiment.py tests/test_explain_review.py tests/test_india.py tests/test_web.py
```

## Release gate status

Completed and release-verified: rich-history portfolio rebuild; strict batch/API migration;
mixed-integer policy allocation; monitoring, experiment, explanation, review and
India workbenches; executive report; checksum manifest; model/data cards and
validation-style review; 127 collected tests (126 passed, 1 skipped) at 70.85% coverage; Ruff/format, Bandit,
dependency and secret scans; SQL/SBOM/artifact checks; and two-page PDF render
inspection. Container/Trivy, CI/CodeQL, responsive browser and production HTTPS
gates passed for implementation commit `621239c`.
