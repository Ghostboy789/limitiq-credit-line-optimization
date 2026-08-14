# Evidence-based résumé bullets

- Built and deployed (v2.0.0, live on Render, 12 Aug 2026) a production-shaped
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

- Released v2.0.0 as a tagged, checksum-verified build through GitHub Actions CI
  (71 tests at 75.99% coverage, Ruff, Bandit, pip-audit, detect-secrets, Docker
  image build and container `/health` smoke test) to Render, then verified every
  route, CSV/PDF download and the live `/health` endpoint over public HTTPS.
  Earlier v1 (0.781 test ROC-AUC, Brier 0.133) remains verifiable via tag
  `v1.0.0`.

Use “multi-source adverse-credit-outcome benchmark,” not common-horizon/global
regulatory PD. The live URL serves v2.0.0 until the v2.1 release is verified.
The four-source publication gate was cleared by the repository owner's dated
14 August 2026 attestation, not by an independent legal opinion; the historical
review and resolution basis are recorded in NOTICE.md.
