# Evidence-based résumé bullets

- Built a production-shaped credit-line decision-support platform that joins a
  calibrated next-month default model to constrained +10%/+20%/+30%, hold,
  manual-review and early-warning-freeze actions with explicit exposure, loss,
  profitability and customer-protection controls.
- Selected a sigmoid-calibrated histogram-gradient-boosting champion against a
  regularized-logistic baseline; achieved 0.781 ROC-AUC (95% bootstrap CI
  0.767–0.796), 0.568 PR-AUC and 0.133 Brier on a 6,000-row untouched test set;
  paired improvement over the frozen v3 benchmark was +0.024 ROC and -0.009 Brier.
- Separated a 1.87M-row heterogeneous transportability benchmark from the
  decision model, then shipped checksum-bound artifacts, transient batch
  inference, policy simulation, validation evidence, Docker CI and security
  gates; kept ₹2.98M scenario contribution explicitly simulated.

Deployment-focused alternative—use only after the v4 commit is verified live:

- Deployed a non-root Dockerized FastAPI risk application through GitHub Actions
  gates covering tests/coverage, Ruff, Bandit, dependency/secret scans, CodeQL,
  SBOM, Trivy image scan, container health and concurrency smoke; verified
  portfolio, simulator, batch, report and operational endpoints over HTTPS.

Never claim that ₹2.98M is observed or realized impact, that the primary model
is validated for India, or that any employer reviewed or endorsed the project.
