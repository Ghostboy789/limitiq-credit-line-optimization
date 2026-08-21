# Product requirements document

## Version status

V3 is the verified source-coherent release: a UCI Taiwan next-month default
model drives the educational synthetic decision portfolio. The v2 1,869,548-row
multi-source model remains transportability research only because it is not a
common-horizon regulatory PD. CI, container security, exact-commit Render and
production-browser gates passed on 21 August 2026. The source-terms attestation
in `NOTICE.md` is not a legal opinion.

## Product

LimitIQ is a dynamic credit-line management and exposure-optimization platform
for an existing card portfolio. It translates a calibrated next-month score, behavior, simulated
economics and policy into explainable +10%, +20%, +30%, no-change, manual-review
or freeze recommendations.

Internal APIs retain the field name `pd`, but v3 product copy calls it a
next-month default score. It is not a production, regulatory or Indian-market PD.

## Users and jobs

- Portfolio manager: allocate exposure within risk and concentration limits.
- Credit-risk analyst: inspect PD, ECL, calibration, bands and warnings.
- Card product manager: test profitable-growth assumptions and action mix.
- Underwriter: review account history, checks and specific reason codes.
- Model-risk/compliance reviewer: challenge data, model, fairness, governance and
  legal-use boundaries.
- Executive: understand exposure, risk, simulated return and limitations quickly.

## Functional requirements

1. Executive overview separates observed, modelled and simulated evidence.
2. Explorer supports search, filters, sorting, pagination and safe CSV export.
3. Account view shows synthetic ID, decision, PD/ECL/value, history and checks.
4. Simulator validates adjustable economics/policy assumptions and recomputes
   aggregate exposure, loss, return, eligibility and action distribution.
5. Batch flow validates strict CSV schema/size/ranges, scores transiently and
   returns a safe decision CSV; no upload retention.
6. Governance leads with primary candidate/test evidence and separately shows
   multi-source research calibration, diagnostics, monitoring and rollback.
7. Reports expose executive HTML/PDF, quality/EDA/model/policy/financial reports,
   product documentation and recruiter materials.

## Decision requirements

- Candidate set is current line and permitted 10% increments through 30%.
- ECL = PD × LGD × EAD; contribution deducts ECL, funding, capital and servicing.
- Severe deterioration freezes automatic increases; ambiguous or overextended
  accounts route to review. There is no automatic decrease.
- Every action has deterministic reason codes and explicit check outcomes.
- Aggregate proposals remain within a portfolio-growth cap; per-account proposals
  remain within maximum exposure.

## Non-functional requirements

Responsive at 1440/768/390 px, keyboard-usable, restrained navy/teal design,
local assets, safe production errors, strict upload limits, trusted-checksum
model loading, no secrets/debug, security headers, health endpoint, one-process
Docker image, reproducible pipeline, automated tests and public documentation.

## Success measures for this educational build

- Rebuild produces the documented dataset/model versions and reports.
- Core financial/policy calculations and all routes pass automated checks.
- Browser workflows work at target viewports with no console or server errors.
- Every simulated result is labelled; no personal or original customer ID is
  published; limitations and ability-to-pay gap are prominent.

## Explicit exclusions

Production lending, customer communications, authentication/roles, persistent
overrides, real-time bureau/core integration, regulatory capital/IFRS 9 engines,
causal uplift, a production database, LLMs and automated line decreases.
