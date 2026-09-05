# QA report

## V4.2.0 verified implementation — 5 September 2026

- Frozen model scores and SHA-256 remain unchanged. The fitted calibrated HGB
  folds expose effective iteration counts **62 / 55 / 83** under the documented
  180-iteration early-stopping configuration.
- The payment-to-bill ratios are capped at **5.0** before generic feature
  clipping, and the governance page includes a synthetic out-of-support example
  with explicit support flags and manual-review routing.
- High-utilization accounts in the weakly calibrated segment are capped at a
  **+10%** increase. The candidate portfolio selects **157 +10%**, **37 +20%**,
  **0 +30%**, **204 holds**, **460 manual reviews** and **342 freezes**.
- Simulated incremental contribution is **INR 454,414.31**; gross contribution
  is **INR 1,473,970.50**, incremental expected loss is **INR 475,890.70**,
  expected loss is **32.29%** of gross contribution, contribution per eligible
  account is **INR 2,342.34**, and derived break-even response elasticity is
  **0.2421**. These are synthetic decision assumptions, not realized economics.
- The complete Windows Python 3.12 suite passes **161 tests** at **76.07%**
  scoped coverage across 3,210 statements. Honest all-`limitiq` coverage is
  **67.60%** across 3,756 statements, and deployed-model producer
  `limitiq/behavioral.py` is **70.94%** covered.
- Ruff lint/format, Bandit, pip-audit, tracked-file secret scanning, primary
  smoke training, analytics reconciliation, SBOM verification and the literal
  19-entry v4.2 checksum manifest all pass locally.
- Local Playwright QA covered **27 route/viewport combinations** across nine
  routes at 1440x1000, 768x1024 and 390x844. There was no page-level overflow;
  keyboard search/navigation, reduced motion, sticky table cells, disclosure
  behavior, the extreme simulator and valid/invalid batch flows passed. The
  only browser console error was the expected 422 response in the intentional
  invalid-batch test; a fresh overview console was clean.
- Warm GET `Server-Timing` was below the 500 ms gate on all 12 checked routes
  (worst: governance at **13.27 ms**). The 50-request `/v4-lab` benchmark
  completed 50/50 at **30.46 ms p50 / 51.50 ms p95**; the three-request,
  500-row multipart `/batch` benchmark completed 3/3 at **2.267 s p50 /
  2.391 s p95**. These are point-in-time local smoke measurements, not capacity
  claims.
- Both regenerated executive PDFs are two-page A4 documents with descriptive
  metadata and render all four pages successfully through Poppler. The Windows
  sandbox image helper failed before model-side visual inspection, so this
  section does not claim a fresh visual PDF-layout pass.
- Exact implementation commit `d369f128558a01c3550289bdfa02211606965731`
  passed GitHub Actions
  [run 33963179773](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/33963179773)
  and matching CodeQL
  [run 33963179790](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/33963179790).
  CI included the literal committed-blob manifest check, Docker/Trivy, non-root
  container health, the 500 ms route gate and both concurrency benchmarks.
- Render `/health` returned application `4.2.0`, the unchanged primary model and
  dataset identifiers, and exact deployed commit `d369f128558a01c3550289bdfa02211606965731`.
- Production HTTPS checks passed 20 routes/evidence endpoints, required security
  and request/timing headers, the `%PDF-` signature, five-row valid batch and
  specific safe 422 invalid batch. Worst measured application timing was
  governance at **175.97 ms**, below the 500 ms gate.
- Production Playwright QA passed all **27 route/viewport combinations** with
  zero page-level overflow and zero console warnings/errors. Keyboard skip and
  search focus, mobile navigation, reduced motion, sticky table cells, positive
  consent routing, extreme simulator economics, calibration/support exhibits,
  out-of-support manual review, India readiness, valid download and safe invalid
  upload all passed. The invalid 422 navigation produced the expected failed-
  resource console entry and no unexpected application error.
- A final live-document replay exposed Markdown-generated inline alignment
  styles blocked by CSP. Corrective commit
  `6a99d80c2e1eb576b60834c825efc919304f87c0` maps alignment to CSS classes,
  passes all 161 local tests, CI
  [run 33968842279](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/33968842279)
  and CodeQL
  [run 33968842278](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/33968842278),
  and is bound by Render `/health`. Fresh production checks of the three changed
  document views at 1440 and 390 px had zero inline styles, overflow or console
  warnings/errors.
- The final documentation-only release boundary is re-gated through CI, CodeQL
  and exact Render identity before tagging; implementation claims remain bound
  to the verified commit and runs above.

## Prompt 3 allocator and affordability release - 5 September 2026

- The complete Windows Python 3.12 suite passes **157 tests** at **75.61%**
  scoped coverage. Honest all-`limitiq` coverage is **67.08%** across 3,703
  statements, and the deployed `limitiq/behavioral.py` module is **70.43%**.
- The regenerated 1,200-profile deterministic simulation selects **147 +10%**,
  **47 +20%**, **0 +30%**, **204 holds**, **460 manual reviews** and
  **342 automatic-increase freezes**. New economics and affordability inputs
  are explicitly labelled synthetic assumptions, not estimates or outcomes.
- The committed optimizer stress binds the higher-risk concentration cap at
  **60 / 60 accounts**. Relaxing the integer cap by one account raises
  simulated contribution by **INR 2,815.08**; this is a finite-difference
  shadow value, not a continuous dual or realized impact.
- At least five profiles are routed to manual review with the
  customer-overextension reason; `LIQ-000292` visibly shows synthetic
  **68.0% FOIR** and manual review in the account UI.
- The 5,000-row batch measured **2.459 seconds end to end**, versus the
  pre-change **11.345 seconds**, and returned all 5,000 decisions.
- Frozen model SHA-256 remains
  `21234ab33f782a5a4d12e6e9050ccbcd812c2b1f324ae91d1a2f4bbd07648115`.
  Untouched-test ROC-AUC 0.781138, PR-AUC 0.567889, Brier 0.133149,
  log loss 0.426351 and threshold 0.173874 remain unchanged.
- Ruff lint/format, Bandit, pip-audit, analytics, SBOM, primary smoke and all
  **19** platform-stable release hashes pass. The local host has no
  `sha256sum` executable; the repository's newline-stable validator was used,
  and Linux CI remains authoritative for the literal command and Docker gates.
- Both pages of `reports/executive_report.pdf` were rendered and visually
  checked without clipping or overlap. Playwright rendered overview, portfolio,
  affordability-blocked account, simulator and governance at 1440, 768 and
  390 px without page-level overflow or browser-console errors.
## Split, policy and analysis controls — 4 September 2026

- The complete local suite passes **154 tests**.
- The default **76.00%** figure uses a scoped 3,112-statement denominator that
  excludes `limitiq/external.py` and `limitiq/multisource.py`. CI separately
  prints the honest all-`limitiq` result: **67.30%** across 3,658 statements,
  including both offline research CLIs.
- `limitiq/behavioral.py` coverage is **74.63%** across 201 statements, up from
  **36.32%** before the synthetic end-to-end training test. The test writes only
  below `tmp_path` and verifies the 180/60/60 split, champion rule and artifact
  checksums without reading the frozen 6,000-row test.
- The regenerated development-only robustness report uses 180 HGB iterations
  and paired calibration intervals; the experiment replay uses protocol 1.2
  multiplicity families. Only those two report hashes changed in the release
  manifest.
- Local Docker remains unavailable. The unchanged CI container path still
  builds the image, runs it as non-root, and requires `/health` before its
  concurrency smoke test.

## V4.1.0 verified release — 25 August 2026

- Exact implementation commit:
  `0ac35b77d7f530c2e54f1c78c2c559ddaba9b8ce`.
- The final local suite passed **137 tests** at **72.26%** scoped statement
  coverage over 2,963 statements, excluding `limitiq/external.py` and
  `limitiq/multisource.py`. Ruff lint and formatting, Bandit, SBOM and analytics checks,
  manifest validation, dependency audit and a 164-file secret scan passed.
- GitHub Actions
  [run 32817814174](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32817814174)
  independently passed the same quality gates plus Docker build, zero
  HIGH/CRITICAL Trivy findings, non-root container health and concurrency smoke.
  Matching CodeQL
  [run 32817814172](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32817814172)
  passed on the implementation SHA.
- Local rendered QA covered overview, v4 lab, batch, governance and reports at
  1440, 768 and 390 px with no page-level overflow or console warning/error.
  It found and fixed two shared causes: consent reason codes could survive a
  portfolio-level action change, and single-account API calls incorrectly used
  portfolio concentration caps.
- Render `/health` returned application `4.1.0`, the unchanged frozen behavioral
  primary, its dataset and the exact implementation commit. Eight major routes,
  the new evidence downloads, PDF signature, five-row transient batch, positive
  eligibility/consent flow and out-of-support manual-review flow passed over
  public HTTPS.
- Production browser QA covered overview, v4 lab, batch and reports at 1440 and
  390 px. No page-level overflow or browser-console warning/error was observed.
- The calibration/challenger table is development-only; the temporal evidence
  is separate US installment-loan research; the India runner remains awaiting
  governed local outcomes. None is reported as a promoted model or production
  impact.

## Editorial overview refresh — 24 August 2026

- The image-first interface pass was checked against four section-specific
  design references, then implemented as server-rendered Jinja and scoped CSS.
  Runtime figures still come from the existing source-bound application
  context; generated reference values were not copied into the product.
- Playwright 1.62.1 with installed Chrome exercised overview, portfolio,
  simulator, batch, governance, monitoring, v4 lab and reports at 1440×1000,
  768×1024 and 390×844 CSS pixels. Every route returned 200 with no page-level
  overflow or browser-console errors.
- Keyboard QA confirmed the skip link is the first tab stop. Reviewer carousel
  controls and native governance disclosures were exercised. Reduced-motion
  emulation confirmed scrubbed copy remains fully visible and stacked cards
  return to normal document flow.
- Fresh overview captures are stored as optimized WebP files under
  `docs/assets/v5-overview-*`; the complete local Python suite passes 127 tests.
  Production deployment evidence is recorded separately and is not implied by
  these local checks.

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
  research CLIs (`limitiq/external.py` and `limitiq/multisource.py`) remain
  explicitly omitted and are checked through artifact, schema and provenance
  tests; the headline is not full rebuild-path coverage.
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
