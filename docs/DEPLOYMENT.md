# Deployment

## Status boundary

The public service runs verified **v4.1.0** with behavioral primary model
`limitiq-behavioral-4.0.0-21234ab33f78` and dataset
`uci-350-behavioral-6ba3a746be13`. Live `/health` reports application `4.1.0`,
the exact deployed Git revision and the primary model and dataset identifiers.
The v2 global model and v4 temporal loan study remain research evidence only;
neither drives card recommendations.

Verify the release files with
`sha256sum -c release/checksums-v4.1.0.sha256`. Text entries in the manifest
are SHA-256 of LF-normalised UTF-8 content, so the command is portable across
supported checkout platforms.

Publication proceeded under the repository owner's 14 August 2026 clearance
attestation documented in [`NOTICE.md`](../NOTICE.md). This is an owner-cleared
attestation, not an independent legal opinion. Historical source-review evidence
remains recorded in NOTICE.

Live application: https://limitiq-credit-line-optimization.onrender.com

Health endpoint: https://limitiq-credit-line-optimization.onrender.com/health

The `limitiq-production` Blueprint deploys the Docker service from `main` on
Render's free plan with a `$0` workspace spend limit.

## V4.1 release verification — 25 August 2026

1. Implementation commit `0ac35b77d7f530c2e54f1c78c2c559ddaba9b8ce`
   passed GitHub Actions
   [run 32817814174](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32817814174):
   **137 passed** tests at **72.26%** scoped statement coverage, Ruff, format,
   primary smoke, source/analytics/SBOM checks, Bandit, pip-audit, secret scan,
   Docker build, zero HIGH/CRITICAL Trivy findings, non-root container health
   and concurrency smoke.
2. Matching CodeQL
   [run 32817814172](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32817814172)
   passed for the same implementation SHA.
3. Render `/health` returned 200 with application `4.1.0`, the unchanged frozen
   behavioral primary and dataset identifiers above, and exact deployed commit
   `0ac35b77d7f530c2e54f1c78c2c559ddaba9b8ce`.
4. Eight major routes plus the robustness, India-readiness and model-improvement
   evidence downloads returned 200. The executive PDF had a valid `%PDF-`
   signature; a five-row transient batch returned the expected decision columns
   and `Cache-Control: no-store`.
5. Production decision checks returned a positive eligibility offer with an
   explicit acceptance requirement and routed an out-of-development-support
   profile to manual review with a failed support policy check.
6. Browser QA exercised overview, v4 lab, batch and reports at 1440 and 390 px.
   There was no page-level overflow or console warning/error. Local browser QA
   additionally covered 768 px and found two shared decision defects that were
   corrected before the full suite and production verification were repeated.

The v4.1 application adds development-only calibration/challenger evidence,
support-bound review routing, temporal stress cohorts, observed-pilot analysis
and a governed India forward-validation runner. It does not promote a new
primary model or claim Indian validation or observed treatment impact.

## V4 release verification — 21–24 August 2026

1. Implementation commit `621239c39ce4b32f32aa1667a6aa4af8830889e2`
   passed GitHub Actions
   [run 32483007565](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32483007565):
   127 collected tests (126 passed, 1 skipped) at 70.85% coverage, Ruff,
   format, behavioral smoke, source/analytics/SBOM checks, Bandit, pip-audit,
   secret scan, Docker build, zero HIGH/CRITICAL Trivy findings, container
   health and 50/50 concurrency smoke requests (p50 4.54 ms; p95 107.56 ms).
   These timings are point-in-time smoke evidence, not a capacity claim.
2. Matching CodeQL
   [run 32483007603](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32483007603)
   passed for the same SHA.
3. Render `/health` returned 200 with application `4.0.0`, the behavioral model
   and dataset identifiers above, and exact deployed commit `621239c`. CSP,
   HSTS, `nosniff` and strict referrer headers were present.
4. Nineteen primary HTTPS routes, operational endpoints and report/CSV/schema
   downloads returned 200. A five-row transient batch returned five decisions
   with `no-store`; a missing-column batch returned a specific safe 422; single
   prediction and the PDF `%PDF-` signature passed. A crawl checked 94 internal
   links with zero failures.
5. Production browser QA exercised overview, filtered portfolio, account
   decision, extreme simulator, batch, governance, monitoring, v4 lab and
   reports. Back/forward/refresh, search focus restoration and mobile navigation
   passed. No page-level overflow was present at 1440, 768 or 390 px, and the
   browser console had zero warning/error entries.
6. The in-app browser screenshot operation was unavailable during this pass.
   Existing README captures therefore remain honestly labelled v3; they are not
   used as v4 verification evidence.

## Historical v3 release verification — 21 August 2026

1. The v3.0.0 implementation gate used GitHub Actions
   [run 32455018502](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32455018502)
   passed Ruff, format, 112 tests at 72.82% scoped coverage, primary smoke,
   source/analytics/SBOM checks, Bandit, pip-audit, secret scanning, Docker build,
   zero HIGH/CRITICAL Trivy scanning, container health and concurrency smoke.
2. Matching v3.0.0 CodeQL
   [run 32455018503](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32455018503)
   passed.
3. Render `/health`, `/live`, `/ready` and `/ops` returned 200; `/health` proved
   the exact commit, application, primary model and dataset.
4. Twenty-one production GET/download/document routes returned 200. The stressed
   simulator, valid transient batch CSV, invalid batch rejection, valid API
   decision and out-of-scope-region rejection passed. CSP, HSTS, request ID and
   timing headers were present.
5. Fresh production browser QA covered the executive, portfolio, governance,
   monitoring, reports and committee views at 1440, 768 and 390 px. No page-level
   horizontal overflow or console warning/error was observed; the mobile menu
   expanded with accessible state.
6. The post-release audit found documentation drift only. V3.0.1 corrected the
   release boundary, interview script and current assumptions; the same CI,
   CodeQL, Render exact-commit and live smoke gates were repeated before tagging.

The runtime container uses the current official Python 3.11 slim Trixie base,
applies published OS security updates during build, removes build-only packaging
tools and runs as a non-root user.

## Historical v2.1 deployment verification — 18 August 2026

1. Every reachable commit author/committer and tagger was rewritten to
   `Ghostboy789`; the tested application commit is `c6154603`.
2. GitHub Actions run
   [32117394757](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32117394757)
   passed on rerun after a transient Docker Hub HTTP 502. Ruff, format, 92 tests
   at 69.00% coverage, Bandit, pip-audit, secret scanning, Docker build/run and
   container `/health` all passed.
3. Render `/health` proved the application, model and dataset, and exposed the
   full deployed Git revision.
4. Production HTTPS verification passed 23 checks with zero failures: 20
   GET/download checks, an extreme simulator submission, a valid batch flow and
   an invalid batch flow. CSP, HSTS, PDF signatures and report styles were clean.
5. Local rendered browser QA had already passed 27 route/viewport combinations
   at 1440/768/390 px without layout or console failures. Production visual
   browser replay was not rerun because the browser-control runtime rejected its
   trusted path; production behavior and exact commit were instead verified
   directly over HTTPS. This constraint is recorded rather than treated as a
   visual-browser pass.

The final documentation commit was tagged `v2.1.0` after repeat CI, Render
verification and the independent audit pass.

## Local production smoke test

```bash
docker build -t limitiq .
docker run --rm -p 8000:8000 -e PORT=8000 limitiq
curl http://localhost:8000/health
```

V3 adds `/live`, `/ready` and aggregate-only `/ops`; release verification checks
all four operational endpoints plus portfolio, account, simulator, committee
memo, reports and transient batch workflows.

The image runs a non-root user, one Uvicorn worker, no debug mode, capped numeric
threads and a stdlib health check. Training and downloading never occur in the
runtime image.

## Historical v2.0 release gate — completed 12 August 2026

All release-gate steps passed for the then-current commit `7e4ca6e`. That SHA is
a pre-authorship-rewrite historical identifier and is retained only as release
evidence:

1. Source decisions recorded in `NOTICE.md`; no raw file is tracked.
2. Full tests (71 passed, 75.99% coverage), lint, formatting, Bandit,
   dependency and secret scans passed locally.
3. Model/dataset/demo checksums recomputed and verified.
4. Python 3.11 production image built in GitHub Actions and passed container
   smoke/health tests (`actions/run 31568971402`).
5. Browser QA passed across overview, portfolio, account, simulator, batch,
   governance and reports at 1440/768/390 px.
6. Commit `7e4ca6e` pushed to `main`; CI passed; tagged `v2.0.0`.
7. Render `/health`, key routes, CSV/PDF downloads verified over public HTTPS
   on 12 August 2026.
8. README/docs labelled the deployed v2 and recorded the model version/commit.

## Render free web service

1. Push the public repository after tests, secret/privacy/licence checks.
2. In an authenticated Render account, create a Blueprint from `render.yaml`.
3. Confirm plan `free`, Docker runtime, health path `/health`, no secret values,
   and deploy-after-CI-checks behavior.
4. Wait through possible free-tier cold start, then verify `/health`, all seven
   areas, PDF/CSV downloads, sample batch upload, desktop/mobile layout, console
   and logs.

Render free services may spin down and have constrained memory/CPU; see current
official terms: https://render.com/docs/free. This repository uses prebuilt
artifacts and one worker to remain within those constraints.

## Release verification

Do not call a deployment successful until HTTPS, health, model startup,
simulator, account lookup, filtered CSV, PDF, sample CSV and batch output have
been exercised on the public URL and browser/server logs show no material error.

This checklist passed on 6 August 2026 for commit `4c185c6`: the health endpoint
returned model `limitiq-1.0.0-f8fe4953fac4` and dataset
`uci-350-30c6be3abd8d`; the application, downloads, stressed simulator, valid
batch scoring and invalid-schema response were exercised over public HTTPS.
