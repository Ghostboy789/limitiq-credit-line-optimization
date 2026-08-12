# Career targeting guide — India

## Recruiter-safe positioning

**One-line pitch:** Built a deployed credit-line decision-support product and a
local 1.87M-row multi-source adverse-credit-outcome benchmark, combining
calibrated risk, provenance, source-level validation, policy controls and a
deterministic synthetic INR exposure simulator.

Be precise about version status: the public link is verified Taiwan-only v1.
The multi-source v2 model is local and its publication gate is blocked pending
terms review. V2 labels have different events/horizons, so never call its score a
common-horizon or regulatory PD.

The project demonstrates credit-risk modelling, model governance, ML
engineering, decision policy, security and product delivery. It does not
demonstrate legal approval, production underwriting, Indian borrower
performance, realized profit or fair-lending compliance.

## Best-fit roles

1. Credit Risk Analytics / Consumer Risk Strategy
2. Model Development, Model Validation or Model Risk Management
3. Risk Data Science / Decision Science
4. Risk Technology / Analytics Engineering
5. Credit Portfolio Management or Risk Product Management

Search combinations of `credit risk`, `consumer risk`, `risk analytics`,
`model validation`, `quantitative risk`, `portfolio risk`, `decision science`,
`data scientist`, `risk technology`, `early warning`, `stress testing` and
`product manager risk`. Verify every opening's city, level and status.

## Employer-specific angle

| Institution | Lead with | Useful search terms | What to show first |
|---|---|---|---|
| J.P. Morgan | Governed consumer-credit decisions, calibration, challenger comparison, controls and portfolio trade-offs | Consumer Risk, Credit Risk, Model Development, Model Validation, Quantitative Risk, Risk Analytics | Simulator → Governance → account reasons |
| UBS | Risk Control, source/portfolio deterioration, stress testing, model performance and disciplined limitations | Risk Control, Quantitative Risk Modelling, Credit Risk, Portfolio Risk, C&ORC, Data Scientist | Governance → source comparison → monitoring/rollback |
| Morgan Stanley | Risk-adjusted decisions, scalable calculations, model evidence and resilient risk technology | Risk Technology, Risk Analytics, Credit Risk, Quantitative Risk, Analytics & Data Technology | Architecture → multi-source evidence → batch workflow |
| State Street | Model-risk governance, data provenance, platform controls and financial-software product delivery | Model Risk Management, Quantitative Risk, Data Analytics, Enterprise Risk, Financial Software, Product Management | Governance → source ledger → security/reports |

State Street fit is strongest as governed analytics/model-risk technology; do
not imply its core business is retail card-line management.

Official career context:

- J.P. Morgan Risk & Compliance:
  https://careers.jpmorgan.com/us/en/students/programs/risk-compliance-program
- UBS India:
  https://www.ubs.com/global/en/careers/about-us/locations/india.html
- Morgan Stanley technology careers in India:
  https://www.morganstanley.com/articles/tech-career-development-morgan-stanley-india/
- State Street India:
  https://careers.statestreet.com/global/en/jobs-in-india
- State Street data/research/trading:
  https://careers.statestreet.com/global/en/c/data-research-and-trading-jobs/

## Résumé package

**Project title:** LimitIQ — Credit Risk Decisioning, Model Governance & Exposure Optimization

**Technology:** Python 3.11, FastAPI, scikit-learn, pandas, Jinja, server-side
SVG, Docker, GitHub Actions, Render, pytest

Use these bullets:

- Built a production-shaped credit-line decision-support platform and local
  1.87M-row multi-source adverse-credit-outcome benchmark, harmonizing six independent
  cohorts with checksum-bound provenance and source-level evaluation.
- Compared calibrated logistic and histogram-gradient-boosting pipelines using
  source-macro validation; the champion recorded 0.685 macro ROC-AUC, 0.402
  macro PR-AUC and 0.139 macro Brier on 373,910 untouched test rows while
  explicitly separating row-weighted pooled evidence.
- Implemented a deterministic INR exposure optimizer with loss, profitability,
  overextension, early-warning and human-review controls; the 1,200-profile
  synthetic scenario produced ₹6.41M simulated—not causal or realized—
  incremental contribution, with a USD/INR/EUR display toggle over the
  INR-canonical portfolio.

If the role values deployment more than multi-source modelling, substitute:

- Deployed a Dockerized v1 decision-support app over 30,000 CC BY 4.0 UCI
  accounts with portfolio, account, simulator, batch, governance and report
  workflows; v1 test ROC-AUC 0.781 and Brier 0.133.

## LinkedIn/GitHub summary

LimitIQ shows how risk modelling becomes a governed product. The verified public
v1 joins a calibrated model to candidate-line policy, portfolio/account views,
batch scoring and transparent synthetic INR economics. Local v2 expands the
research workflow to 1.87M harmonized rows, source-macro calibration evidence,
provenance and publication controls. I kept source observations, model estimates
and simulated business outputs separate and documented why heterogeneous labels
are not a common regulatory PD.

## 30-second interview answer

“Many credit-risk projects end at a score. I built LimitIQ to connect risk to a
governed operating decision: increase, hold, refer or freeze. I first deployed a
Taiwan-data v1, then built a local 1.87-million-row multi-source benchmark with a
calibrated logistic baseline, gradient-boosting champion, source-macro selection
and checksum-bound provenance. The app uses a deterministic synthetic INR
portfolio to demonstrate exposure and policy trade-offs. The important judgment
was documenting that source labels differ, pooled metrics are Lending-Club-
dominated and v2 cannot be published until dataset terms are cleared.”

## Evidence to discuss by interviewer

- **Risk manager:** early warnings, exposure/loss caps, portfolio growth cap,
  manual review and no punitive automatic decrease.
- **Model validator:** duplicate-population exclusion, unified preprocessing,
  macro selection, calibration, frozen threshold, source-level metrics,
  limitations, checksums and rollback.
- **Data scientist:** 1.87M rows, missingness/source effects, logistic baseline,
  gradient-boosting challenger, PR/Brier evidence and future leave-one-source-out
  or out-of-time validation.
- **Product manager:** six personas, candidate-action framing, simulator, human
  override, data-rights gate and phased shadow/pilot roadmap.
- **Engineer:** single-service architecture, deterministic rebuild, server-side
  CSP-safe charts, strict transient CSV handling, CI, Docker and v1 deployment.

## Application checklist

1. Label the link “verified v1 live demo”; never present it as v2.
2. Match the first bullet to the job family.
3. Use macro v2 metrics and explain why pooled metrics are secondary.
4. Label every financial result “synthetic and simulated.”
5. Link the model/data cards for validation roles and architecture for technology
   roles.
6. Rehearse the five-minute walkthrough and a limitation-first answer.
7. Never state that J.P. Morgan, UBS, Morgan Stanley or State Street uses,
   reviewed or endorsed the project.

## India-specific learning roadmap

Learn current RBI credit-card/consumer-credit guidance and Ind AS 109/IFRS 9 at
interview depth. Explain that real Indian deployment needs India-specific bureau,
income, obligations, affordability, outcomes, consent and governance. INR
presentation is not Indian model evidence.
