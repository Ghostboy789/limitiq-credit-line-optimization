# Deployment

## Status boundary

The URLs below are the **deployed v2 global benchmark** (`main` commit `7e4ca6e`,
tag `v2.0.0`, deployed 12 August 2026). The live `/health` endpoint reports
application `2.0.0`, model `limitiq-global-2.0.0-37a14c45a811` and dataset
`global-7-94bb4c0ad0f1`.

V2 publication proceeded per the repository owner's 12 August 2026 terms-review
decision documented in [`NOTICE.md`](../NOTICE.md). Four upstream sources (Give
Me Some Credit, FICO/HELOC, Lending Club upstream, Home Credit) remain under
review; see NOTICE for the recorded evidence and decision.

Live application: https://limitiq-credit-line-optimization.onrender.com

Health endpoint: https://limitiq-credit-line-optimization.onrender.com/health

The `limitiq-production` Blueprint deploys the Docker service from `main` on
Render's free plan with a `$0` workspace spend limit.

## Local production smoke test

```bash
docker build -t limitiq .
docker run --rm -p 8000:8000 -e PORT=8000 limitiq
curl http://localhost:8000/health
```

The image runs a non-root user, one Uvicorn worker, no debug mode, capped numeric
threads and a stdlib health check. Training and downloading never occur in the
runtime image.

## V2 release gate — completed 12 August 2026

All release-gate steps passed for commit `7e4ca6e`:

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
