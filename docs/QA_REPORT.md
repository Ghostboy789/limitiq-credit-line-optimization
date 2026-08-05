# QA report

Verified 5 August 2026 against model version
`limitiq-1.0.0-f8fe4953fac4` and dataset version
`uci-350-30c6be3abd8d`.

## Automated evidence

- 61 tests passed: 12 data/feature, 15 optimizer/financial-policy, 9 artifact and
  reproducibility, and 25 application/integration tests.
- 77.60% statement coverage, above the enforced 65% project threshold.
- Ruff format and lint, Bandit, `pip-audit` and detect-secrets passed locally.
- GitHub Actions run
  [31038484167](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/31038484167)
  independently passed the same checks, built the Docker image, ran it as a
  container and reached its `/health` endpoint.

## Real-browser end-to-end evidence

The local production-shaped Uvicorn application was exercised with the Codex
in-app browser controller, not only an HTTP client.

| Area | Verified behavior |
|---|---|
| Executive overview | Loaded exact model/dataset evidence, KPI cards, action/risk distributions and disclaimer |
| Portfolio explorer | Search, sort, Moderate-risk filter (3,178 rows), pagination and filtered CSV download |
| Account decision | Synthetic account route, six-period histories, reasons and six policy checks |
| Policy simulator | Submitted LGD 100% stress; results changed to TWD 1.060B proposed exposure, TWD 159.66M ECL, 961 increases and TWD 5.73M simulated contribution |
| Batch decisioning | Uploaded a valid CSV and downloaded decisions; missing `PAY_6` produced a specific validation error |
| Governance and reports | Exact metrics/model version rendered; executive PDF and document links downloaded/opened |
| Navigation and state | Refresh, back and forward behavior passed; no dead primary navigation items |

Responsive checks were performed at 1440 px desktop, 768 px tablet and 390 px
mobile. The mobile governance table scrolls within its panel without page-level
overflow. Keyboard-reachable native links, forms and controls were checked.
Browser warning/error logs were empty after the final local pass. Valid,
invalid, empty/missing-column and extreme-policy paths are also covered by the
automated application tests.

## Security and privacy checks

- Upload limit: 5 MB and 5,000 rows; strict column, numeric-range, duplicate and
  unknown-column validation.
- Uploaded bytes are processed in memory and not retained.
- Formula-safe CSV, allowlisted sorts/routes, Jinja autoescape and model checksum
  verification were exercised by tests.
- CSP, frame denial, `nosniff`, referrer, permissions and opener headers were
  observed on the running app.
- The secret scan reported zero findings. The dependency audit reported zero
  known vulnerabilities.
- The public artifact uses synthetic account IDs and excludes source IDs and
  demographic fields. The official raw workbook and cleaned full duplicate are
  gitignored.

Production HTTPS checks remain separate from this local report and are not
claimed until the deployed URL is exercised.
