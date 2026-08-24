# QA report

## V4 release-media and uptime polish — 24 August 2026

- Fresh v4 captures cover the executive overview, portfolio explorer, account
  decision, policy simulator, governance verdict and a true 390 CSS-pixel mobile
  viewport. They are committed under `docs/assets/v4-*` and the README
  walkthrough is generated only from those inspected frames.
- The 390 px capture exposed a presentation edge at narrow widths. The shared
  mobile hero sizing and top-bar spacing were tightened; the recaptured layout
  contains the brand, menu, search, INR selector, hero copy, both calls to action
  and the eligibility callout without clipping.
- `.github/workflows/uptime.yml` checks the public `/health` response daily and
  on manual dispatch. It tolerates free-tier cold starts, requires HTTP success,
  and validates status, application version and behavioral model version without
  credentials or a paid monitoring service.

## V4.0.0 verified release — 21–24 August 2026

- Exact implementation commit:
  `621239c39ce4b32f32aa1667a6aa4af8830889e2`.
- GitHub Actions
  [run 32483007565](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32483007565):
  **127 collected, 126 passed, 1 skipped**, **70.85%** scoped statement
  coverage (65% required). Ruff, format, primary smoke, source/analytics/SBOM
  checks, Bandit, pip-audit and secret scan passed.
- Docker build, zero HIGH/CRITICAL Trivy scan, non-root container health and the
  50-request/5-concurrency smoke passed 50/50 (p50 4.54 ms, p95 107.56 ms).
  This is point-in-time smoke evidence, not a capacity claim.
- Matching CodeQL
  [run 32483007603](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32483007603)
  passed on the same commit.
- Render `/health` returned application `4.0.0`, model
  `limitiq-behavioral-4.0.0-21234ab33f78`, dataset
  `uci-350-behavioral-6ba3a746be13` and the exact deployed SHA. CSP, HSTS,
  `nosniff` and strict referrer headers were present.
- Public HTTPS QA passed 19 primary routes/endpoints/downloads, five-row
  transient batch scoring, specific invalid-schema rejection, single-account
  prediction, PDF signature validation and 94/94 discovered internal links.
- Production browser QA covered overview, portfolio filter, account detail,
  extreme simulator, batch, governance, monitoring, v4 lab and reports.
  Refresh/back/forward, search focus return and responsive navigation passed;
  1440/768/390 px had no page-level overflow and console warning/error logs
  were empty.
- The original in-app screenshot operation was unavailable. Fresh v4 captures
  were subsequently produced from the same rendered application with explicit
  desktop and mobile viewports and visually inspected before publication.
- The v4 behavioral primary, global research benchmark and temporal loan study
  remain separately labelled; only the source-coherent behavioral model drives
  the deterministic synthetic card demonstration.

## Historical V3.0.1 verified release — 21 August 2026

The working tree contains a coherent UCI Taiwan next-month primary model,
Taiwan-contract synthetic demo, two-track governance, operational endpoints,
committee memo, source manifest, SQL reconciliation, SBOM, CodeQL and container
scan gates.

- Full suite: **112 passed**, **72.82%** scoped statement coverage (65% required).
- Ruff lint and format: pass. Bandit: no findings. Pip-audit: no known
  vulnerabilities in pinned runtime dependencies.
- Secret scan: 131 publishable source/config/document files, zero findings;
  generated reports/data and binary artifacts were separately provenance-bound
  and excluded from entropy scanning.
- Primary smoke training, SQL reconciliation, SBOM check and source-manifest
  rendering: pass.
- Local runtime: 16 routes/downloads returned 200 with unique request IDs;
  50-request/5-concurrency health smoke completed 50/50 with p50 7.70 ms and p95
  256.56 ms. This is point-in-time smoke evidence, not a capacity claim.
- Fresh v3 browser QA on 21 August covered the overview, portfolio, governance
  and monitoring routes at 1440, 768 and 390 px. No page-level horizontal
  overflow or browser warning/error was observed; the favicon defect found in
  server logs was fixed. Current screenshots are committed under `docs/assets/`.
- The coverage headline applies to the primary/runtime package. Large offline
  research CLIs remain explicitly omitted and are checked through artifact,
  schema and provenance tests; the headline is not full rebuild-path coverage.
- Local Docker is unavailable; GitHub Actions supplied the container evidence.
- The v3.0.0 implementation CI [run 32455018502](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32455018502)
  passed Docker build, zero HIGH/CRITICAL Trivy scanning, non-root container
  health and a 50-request/5-concurrency benchmark. CodeQL
  [run 32455018503](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32455018503)
  passed on the same commit.
- V3.0.1 corrected documentation drift found by the post-release audit without
  changing code, model, evidence or simulation. The full CI, CodeQL, Render
  exact-commit and production smoke gates were repeated before its tag.
- Render `/health` reports application `3.0.0`, model
  `limitiq-primary-3.0.0-89f9a2530bde`, dataset
  `uci-350-next-month-dc05bd56186a` and the exact deployed commit; the immutable
  release tag identifies the source.
- Production HTTPS QA passed 21 GET/download/document routes, stressed simulator,
  valid/invalid batch, valid/out-of-scope prediction and security/observability
  header checks.
- Fresh production browser QA covered executive, portfolio, governance,
  monitoring, reports and committee views across 1440/768/390 px. Mobile
  navigation, overflow and console checks passed with zero warning/error.

## V2.1 application verification — 18 August 2026

- Release-gated application-code commit:
  `c6154603da430b0eacb2d237a469f0843784557e`. Every reachable Git commit
  author/committer and tagger was rewritten to `Ghostboy789`.
- GitHub Actions run
  [32117394757](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32117394757)
  succeeded on rerun after a transient Docker Hub HTTP 502. Ruff, format, 92
  tests at 69.00% statement coverage (above the enforced 65%), Bandit,
  `pip-audit`, secret scanning, Docker build/run and container `/health` passed.
- Live `/health` reports application `2.1.0`, unchanged model
  `limitiq-global-2.0.0-37a14c45a811`, dataset `global-7-94bb4c0ad0f1` and the
  exact deployed Git revision.
- Production HTTPS QA passed 23 checks with zero failures: 20 GET/download
  checks, an extreme simulator submission, a valid batch flow and an invalid
  batch flow. CSP, HSTS, PDF signatures and report styles were clean.
- Local rendered browser QA covered 27 route/viewport combinations at 1440,
  768 and 390 px with no layout or browser-console failures. Primary routes,
  mobile navigation, accessible search/focus handling, account routing,
  currency persistence, simulator extremes, valid batch download and
  missing-column feedback passed.
- Production visual browser replay was not rerun because the browser-control
  runtime rejected its trusted path. This is not presented as a production
  visual-browser pass; the exact deployment commit and production workflows
  were verified directly over HTTPS.
- Fifteen governance SVGs expose accessible titles/descriptions. Current-v2 and
  archived-v1 reports are separated. CSP disallows inline styles and HSTS is
  present.
- Both two-page A4 executive PDFs were regenerated, rendered page by page and
  inspected for clipping/overlap; descriptive PDF metadata is present.
- The model bytes, checksum and `2.0.0` model identifier are unchanged. Tag
  `v2.1.0` identifies the final evidence release after repeat gates pass.

## Version boundary

This report separates current **v4 application evidence** from historical
**v3, v2.1, v2.0 and v1 release evidence**. V4 uses the 17-feature coherent
behavioral primary model for the educational demo while the v2 global model and
v4 temporal loan study remain research only. Pre-rewrite
commit `7e4ca6e`, v2.0 tag and 12 August results below are
retained as historical evidence; current identity is the rewritten
`Ghostboy789` history. Publication proceeds under the owner's 14 August 2026
clearance attestation recorded in `NOTICE.md`, not an independent legal opinion.

## Historical local v2.0 evidence — 11 August 2026

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

## Historical deployed v2.0 verification — 12 August 2026

- The then-current pre-rewrite commit `7e4ca6e` was pushed to `main`; GitHub Actions run
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
- The complete request is bounded before multipart parsing; uploaded bytes are
  processed transiently, may use framework-managed temporary spooling and are
  closed without application retention.
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
