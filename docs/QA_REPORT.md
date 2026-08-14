# QA report

## V2.1 release-candidate verification — 14 August 2026

- 85 tests passed with 69.05% statement coverage against the enforced 65%
  threshold; the lower percentage than the earlier v2 run reflects the new
  offline evidence module, whose long full-data paths are verified through
  versioned artifact and provenance tests.
- Ruff lint/format and Bandit passed. `pip-audit -r requirements.txt` reported
  no known vulnerabilities. Detect-secrets scanned all 94 publishable tracked
  and untracked text files with zero findings.
- Desktop (1440), tablet (768) and mobile (390) browser checks found no
  page-level horizontal overflow or console warnings/errors. Primary routes,
  mobile navigation, accessible search/focus handling, account routing, INR/EUR
  persistence, simulator extremes, valid batch download and missing-column
  feedback passed.
- Fifteen governance SVGs expose accessible titles/descriptions. Current-v2 and
  archived-v1 reports are separated. CSP no longer permits inline styles.
- Both two-page A4 executive PDFs were regenerated, rendered page by page and
  inspected for clipping/overlap; descriptive PDF metadata is present.
- The model bytes and checksum are unchanged. This is an application,
  diagnostic-evidence and governance release candidate. GitHub Actions Docker
  and Render production verification remain the release gate until recorded
  below.

## Version boundary

This report separates verified **v1 production evidence** from verified **v2
deployed evidence**. V2 passed the local automated, security and real-browser
checks below, then passed Docker, GitHub Actions CI and Render verification on
12 August 2026. V2 was committed as `7e4ca6e`, tagged `v2.0.0` and deployed;
the live `/health` reports application `2.0.0`, model
`limitiq-global-2.0.0-37a14c45a811` and dataset `global-7-94bb4c0ad0f1`.
Publication proceeded per the owner's terms decision recorded in `NOTICE.md`.

## Local v2 evidence — 11 August 2026

- 71 tests passed with 75.99% statement coverage, above the enforced 65%
  threshold.
- Ruff lint and format checks passed.
- Bandit scanned 3,893 lines with zero findings.
- `pip-audit -r requirements.txt` reported no known vulnerabilities.
- Detect-secrets returned no findings for source/configuration/documentation or
  generated HTML, JSON and synthetic CSV artifacts.
- Global artifact checks verify the model checksum, 1,869,548-row union, six
  independent training cohorts plus one reference-only source, two cohorts over
  200,000 rows, and macro/pooled/per-source metrics, chart points and the
  publication decision.

The production-shaped local app was exercised at 1440 px desktop, 768 px
tablet and 390 px mobile. There was no unexpected page-level horizontal
overflow, browser-console error or application-log error. The mobile menu,
overview, seven accessible governance SVGs, portfolio empty/filter/sort flow,
account detail, simulator extreme and native-validation paths, reports, global
executive PDF, valid five-row transient batch upload, decision CSV download,
refresh, back and forward navigation all passed. Missing-column, invalid-type,
duplicate, upload-size and other negative batch paths are covered by passing
integration tests. The two-page A4 executive PDF was separately rendered and
visually checked for clipping and overlap.

## Deployed v2 verification — 12 August 2026

- Commit `7e4ca6e` pushed to `main`; GitHub Actions run
  [31568971402](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/31568971402)
  passed every job including ruff, pytest (71 tests, 75.99% coverage), Bandit,
  pip-audit, the secret scan, the Docker image build and the container `/health`
  smoke test.
- Tag `v2.0.0` pushed. Render deployed the tagged commit.
- Public `/health` verified over HTTPS: application `2.0.0`, model
  `limitiq-global-2.0.0-37a14c45a811`, dataset `global-7-94bb4c0ad0f1`.
- Public routes verified 200 over HTTPS: overview, portfolio, account detail,
  simulator, batch, governance, reports, `/sample-input.csv`,
  `/portfolio.csv`, and downloads `global-executive-pdf`,
  `global-executive-html`, `global-model`, `global-policy-simulation`,
  `global-financial-impact` and `executive-report-pdf`.
- V1 remains available via Git history/tag `v1.0.0`; the live service now
  serves v2.


Verified 7 August 2026 against model version
`limitiq-1.0.0-284f9a7c8ca2` and dataset version
`uci-350-30c6be3abd8d-inr297`.

## Automated evidence

- 62 tests passed: 12 data/feature, 15 optimizer/financial-policy, 9 artifact and
  reproducibility, and 26 application/integration tests.
- 77.56% statement coverage, above the enforced 65% project threshold.
- Ruff format and lint, Bandit, `pip-audit` and detect-secrets passed locally.
- GitHub Actions run
  [31040997235](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/31040997235)
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
| Policy simulator | Submitted LGD 100% stress; exposure, loss, eligible count, action mix and simulated contribution changed as expected |
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

## Production HTTPS evidence

The Render deployment at
https://limitiq-credit-line-optimization.onrender.com was first exercised on 6 August
2026 against the then-current pre-INR build. `/health` returned `status=ok`,
application version `1.0.0`, model `limitiq-1.0.0-f8fe4953fac4` and dataset
`uci-350-30c6be3abd8d`.

- Overview, portfolio search, account decision, governance, reports and model
  card rendered with the expected evidence and educational disclaimer.
- A stressed 90% LGD / 100% CCF / 5% loss-ceiling scenario recalculated to zero
  increases, a higher proposed expected-loss result and zero incremental contribution.
- A two-row CSV produced a downloadable decision file with bounded PD values,
  recommendations, ECL, simulated contribution and reason codes.
- A missing-column upload returned a safe 422 page naming every absent column.
- The executive PDF and batch decision CSV downloaded successfully from the
  public application; the PDF had a valid `%PDF-` signature.
- Render reported the Docker deployment live on the free plan. The public
  service may take roughly 50 seconds to wake after inactivity.

### 7 August 2026 INR-release re-verification

Re-verified live after the INR release deployed (model
`limitiq-1.0.0-284f9a7c8ca2`, dataset `uci-350-30c6be3abd8d-inr297`, Render
deployment `dep-d9qmglbtqb8s73b2vuug` success):

- `/health` returns the INR model and dataset versions above.
- Overview shows INR figures with the documented fixed 2.97 TWD conversion note
  and the educational disclaimer; account pages carry the same boundary note.
- All 27 primary pages (9 routes × 1440/768/390 px) loaded with no horizontal
  overflow and empty console/page-error logs.
- Batch upload of the sample template returned a decision CSV; an invalid
  `ACCOUNT_ID` returned a safe 422.
- Executive PDF and portfolio CSV downloaded successfully from production.

## Independent audit

An independent read-only review repeated after remediation found no remaining
material local issues. It reconciled model, report, demo and split checksums;
verified all 30 re-optimized sensitivity scenarios; reran the 62-test suite,
Ruff and Bandit; and confirmed the INR-localized working tree builds and tests
clean before the `v1.0.0` release.
