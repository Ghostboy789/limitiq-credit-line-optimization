# Deployment

## Status boundary

The public service runs the verified **v3.0.0 application** with primary
model `limitiq-primary-3.0.0-89f9a2530bde` and dataset
`uci-350-next-month-dc05bd56186a`. Application code was release-gated at commit
`1dc6257f96617b3618527446203c96d55ae75568` on 21 August 2026. Live `/health`
reports application `3.0.0`, that exact Git revision and the primary model and
dataset identifiers. The v2 global model remains a research benchmark only.

Publication proceeded under the repository owner's 14 August 2026 clearance
attestation documented in [`NOTICE.md`](../NOTICE.md). This is an owner-cleared
attestation, not an independent legal opinion. Historical source-review evidence
remains recorded in NOTICE.

Live application: https://limitiq-credit-line-optimization.onrender.com

Health endpoint: https://limitiq-credit-line-optimization.onrender.com/health

The `limitiq-production` Blueprint deploys the Docker service from `main` on
Render's free plan with a `$0` workspace spend limit.

## V3.0 deployment verification — 21 August 2026

1. GitHub Actions
   [run 32455018502](https://github.com/Ghostboy789/limitiq-credit-line-optimization/actions/runs/32455018502)
   passed Ruff, format, 112 tests at 72.82% scoped coverage, primary smoke,
   source/analytics/SBOM checks, Bandit, pip-audit, secret scanning, Docker build,
   zero HIGH/CRITICAL Trivy scanning, container health and concurrency smoke.
2. Matching CodeQL
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
