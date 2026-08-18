# Evidence-based résumé bullets

- Built and deployed (v2.1 application, live on Render, verified 18 Aug 2026) a production-shaped
  credit-line decision-support platform over a 1.87M-row multi-source
  adverse-credit-outcome benchmark, harmonizing six independent cohorts with
  checksum-bound provenance and governed increase/hold/refer/freeze actions.
- Compared calibrated logistic and histogram-gradient-boosting pipelines using
  source-macro validation; the champion achieved 0.685 macro ROC-AUC, 0.402
  macro PR-AUC and 0.139 macro Brier on 373,910 untouched test rows.
- Implemented deterministic INR exposure optimization with loss, profitability,
  early-warning and human-review controls; the 1,200-profile synthetic scenario
  produced ₹6.41M simulated—not causal or realized—incremental contribution.

Deployment-focused alternative:

- Deployed checksum-verified application `2.1.0` through GitHub Actions CI (92
  tests at 69.00% coverage, Ruff, Bandit, pip-audit, secret scan, Docker
  build/run and container `/health`) to Render, then passed 23 production HTTPS
  route/download/simulator/batch checks with zero failures. Earlier v1 (0.781
  test ROC-AUC, Brier 0.133) remains verifiable via tag `v1.0.0`; the current
  evidence release is tagged `v2.1.0`.

Use “multi-source adverse-credit-outcome benchmark,” not common-horizon/global
regulatory PD. The model identifier remains
`limitiq-global-2.0.0-37a14c45a811` because v2.1 did not retrain it. The
four-source publication gate was owner-cleared by dated 14 August 2026
attestation, not an independent legal opinion; the historical review and
resolution basis are recorded in NOTICE.md.
