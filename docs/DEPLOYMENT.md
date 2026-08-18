# Deployment

## Status boundary

The URLs below serve the **v2.1.0 application**. Application code was
release-gated at commit `c6154603da430b0eacb2d237a469f0843784557e` on 18
August 2026. The live
`/health` endpoint reports application `2.1.0`, unchanged model
`limitiq-global-2.0.0-37a14c45a811`, dataset `global-7-94bb4c0ad0f1` and the
exact deployed Git revision. Tag `v2.1.0` identifies the final evidence release.

Publication proceeded under the repository owner's 14 August 2026 clearance
attestation documented in [`NOTICE.md`](../NOTICE.md). This is an owner-cleared
attestation, not an independent legal opinion. Historical source-review evidence
remains recorded in NOTICE.

Live application: https://limitiq-credit-line-optimization.onrender.com

Health endpoint: https://limitiq-credit-line-optimization.onrender.com/health

The `limitiq-production` Blueprint deploys the Docker service from `main` on
Render's free plan with a `$0` workspace spend limit.

## V2.1 deployment verification — 18 August 2026

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

The final documentation commit is tagged `v2.1.0` only after repeat CI, Render
verification and the independent audit pass.

## Local production smoke test

```bash
docker build -t limitiq .
docker run --rm -p 8000:8000 -e PORT=8000 limitiq
curl http://localhost:8000/health
```

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
