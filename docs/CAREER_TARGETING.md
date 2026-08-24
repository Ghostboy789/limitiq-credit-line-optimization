# Career targeting guide — India

## Recruiter-safe positioning

**One-line pitch:** Built a production-shaped credit-line decision product with
a calibrated next-month default model, constrained actions, model-risk controls
and a separately governed 1.87M-row transportability benchmark.

Be precise about version status: v4 is verified live and `/health` exposes the
exact deployed commit, model and dataset. It uses one Taiwan next-month target
for account decisions and never uses the heterogeneous global or US
loan-vintage models for individual recommendations.

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
  https://www.jpmorganchase.com/careers/explore-opportunities/programs/risk-compliance-program
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

- Built a production-shaped credit-line decision-support platform that joins a
  coherent UCI Taiwan next-month default model to governed candidate actions,
  with a separate 1.87M-row research benchmark for transportability evidence.
- Selected a calibrated histogram-gradient-boosting champion against logistic
  regression; achieved 0.781 ROC-AUC (95% CI 0.767–0.796), 0.568 PR-AUC and
  0.133 Brier on a 6,000-row untouched test set.
- Implemented a deterministic INR exposure optimizer with loss, profitability,
  overextension, early-warning and human-review controls; the 1,200-profile
  synthetic scenario produced ₹2.98M simulated—not causal or realized—
  incremental contribution, with a USD/INR/EUR display toggle over the
  INR-canonical portfolio.

If the role values deployment more than multi-source modelling, substitute:

- Engineered a Dockerized decision-support application with portfolio, account,
  simulator, transient batch, governance and report workflows; added SBOM,
  CodeQL, container scanning, liveness/readiness and privacy-safe operations
  telemetry.

## LinkedIn/GitHub summary

LimitIQ shows how risk modelling becomes a governed product. V4 joins a rich
source-coherent calibrated next-month model to candidate-line policy,
portfolio/account views, transient batch scoring and synthetic INR economics.
The heterogeneous 1.87M-row model remains visible as transportability research,
not account decisioning. Source observations, model estimates and simulated
business outputs stay separate.

## 30-second interview answer

“Many credit-risk projects end at a score. I built LimitIQ to connect risk to a
governed action: increase, hold, refer or freeze. Model-risk review showed that
my 1.87-million-row benchmark combined different adverse events and horizons,
so I changed the architecture. A calibrated next-month Taiwan model now drives
only the synthetic decision demo; the global model is research evidence only.
The primary test ROC-AUC is 0.781 with a 0.767–0.796 bootstrap interval, and the
economics remain explicitly simulated.”

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
  CSP-safe charts, strict transient CSV handling, CI, Docker, SBOM, container
  scanning and operational probes.

## Application checklist

1. Label the link “educational live demo” and confirm its `/health` version.
2. Match the first bullet to the job family.
3. Lead with primary 0.781 ROC-AUC, its paired improvement over v3, and explain why the other model tracks are research only.
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
