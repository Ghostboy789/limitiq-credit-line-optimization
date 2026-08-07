# Career targeting guide — India

## Recruiter-safe positioning

**One-line project pitch:** Built and deployed an end-to-end credit-risk
decision-support platform that converts calibrated default probability into
governed credit-line actions, with expected-loss economics, early warnings,
model governance and transient batch decisioning.

**Evidence boundary:** The PD model uses the public UCI Default of Credit Card
Clients dataset. Source monetary fields are converted to INR for presentation.
Line response and financial outcomes are deterministic simulations—not observed,
causal, production or India-market results.

This project demonstrates product judgment, credit-risk modelling, ML
engineering, decision policy, governance, security and deployment. It does not
demonstrate legal approval, production underwriting, realized profit or
fair-lending compliance.

## Best-fit roles

Prioritize roles in this order:

1. Credit Risk Analytics / Consumer Risk Strategy
2. Model Development, Model Validation or Model Risk Management
3. Risk Data Science / Decision Science
4. Risk Technology / Analytics Engineering
5. Credit Portfolio Management or Risk Product Management

Search with combinations of `credit risk`, `consumer risk`, `risk analytics`,
`model validation`, `quantitative risk`, `portfolio risk`, `decision science`,
`data scientist`, `risk technology`, `early warning`, `stress testing` and
`product manager risk`. Verify each opening's city, level and live status before
applying.

## Employer-specific angle

| Institution | Lead with | Useful search terms | What to show first |
|---|---|---|---|
| J.P. Morgan | Governed consumer-credit decisions, calibrated PD, controls and portfolio trade-offs | Consumer Risk, Credit Risk, Model Development, Model Validation, Quantitative Risk, Risk Analytics | Simulator → Governance → Account reasons |
| UBS | Risk Control, deterioration signals, stress testing, model performance and engineering discipline | Risk Control, Quantitative Risk Modelling, Credit Risk, Portfolio Risk, C&ORC, Data Scientist | Governance → early-warning accounts → monitoring/rollback |
| Morgan Stanley | Risk-adjusted returns, quantitative risk, scalable risk calculations and resilient risk technology | Risk Technology, Risk Analytics, Credit Risk, Quantitative Risk, Analytics & Data Technology | Architecture → simulator → batch decisioning |
| State Street | Model-risk governance, data/analytics, platform controls and financial-software product delivery | Model Risk Management, Quantitative Risk, Data Analytics, Enterprise Risk, Financial Software, Product Management | Governance → security/transient processing → reports |

The State Street fit is strongest as a governed analytics platform and model-risk
case study; do not imply its core business is retail credit-card line management.

Official career context:

- J.P. Morgan Risk & Compliance programs:
  https://careers.jpmorgan.com/us/en/students/programs/risk-compliance-program
- UBS India careers and locations:
  https://www.ubs.com/global/en/careers/about-us/locations/india.html
- Morgan Stanley technology careers in India:
  https://www.morganstanley.com/articles/tech-career-development-morgan-stanley-india/
- State Street India careers:
  https://careers.statestreet.com/global/en/jobs-in-india
- State Street data/research/trading roles:
  https://careers.statestreet.com/global/en/c/data-research-and-trading-jobs/

## Résumé package

**Project title:** LimitIQ — Credit Risk Decisioning & Exposure Optimization

**Technology line:** Python, FastAPI, scikit-learn, pandas, Jinja, Docker, GitHub
Actions, Render, pytest

Use these bullets:

- Built and deployed a Dockerized credit-line decisioning platform over 30,000
  CC BY 4.0 UCI accounts, translating calibrated PD into governed +10/+20/+30,
  no-change, manual-review and early-warning freeze actions across seven web
  workflows.
- Developed calibrated logistic and histogram-gradient-boosting pipelines with
  fixed 60/20/20 splits; selected on validation and achieved 0.781 ROC-AUC,
  0.568 PR-AUC and 0.133 Brier score on a 6,000-account untouched test set.
- Implemented deterministic PD×LGD×EAD and contribution optimization with
  adjustable loss, exposure, profitability and customer-protection controls;
  the default INR scenario selected 1,904 increases and ₹41.34M simulated—not
  causal or realized—annual incremental contribution.

## LinkedIn/GitHub summary

LimitIQ is a deployed banking decision-support case study that joins model
development to product policy. It trains and calibrates a real public-data PD
model, evaluates governed candidate limits, optimizes transparent simulated
economics and exposes portfolio, account, simulator, batch and model-governance
workflows. I built it to show how risk analytics becomes a controlled product,
including evidence boundaries, fairness diagnostics, monitoring and rollback.

## 30-second interview answer

“Many credit-risk projects end at a prediction. I built LimitIQ to answer the
operating decision: for an existing account, should the bank offer a 10, 20 or
30 percent increase, hold, refer or freeze? A calibrated public-data PD model
feeds a constrained optimizer using PD×LGD×EAD and transparent simulated
economics. I then productized it as a secure Dockerized app with portfolio,
account, scenario, batch and governance workflows. The main judgment was keeping
observed, estimated and simulated evidence separate—so I can defend both the
model and what it cannot claim.”

## Evidence to discuss by interviewer

- **Risk manager:** eligibility rules, early-warning logic, exposure cap,
  portfolio growth cap, reason codes, manual review and no punitive auto-decrease.
- **Model validator:** fixed partitions, unified preprocessing, calibration,
  Brier-led selection, frozen threshold, untouched test, segment diagnostics,
  drift indicators, checksum and rollback.
- **Data scientist:** engineered payment/utilization/delinquency signals,
  logistic baseline, gradient-boosting challenger and probability-quality
  metrics rather than accuracy-only selection.
- **Product manager:** six personas, candidate-action framing, simulator,
  human override, limitations and phased path from shadow mode to monitored pilot.
- **Engineer:** single-service architecture, deterministic rebuild, strict CSV
  validation, transient processing, security headers, CI, Docker health check and
  verified public deployment.

## Application checklist

1. Put the live URL and GitHub URL beside the project title.
2. Match the first bullet to the job family: risk decisioning for credit roles,
   model governance for validation roles, platform controls for technology roles.
3. Keep exact metrics and label every financial result “simulated.”
4. Add only keywords that also appear in the target job description and that
   you can defend from the repository.
5. Attach the executive PDF for portfolio/risk roles; link the model card for
   data science/model risk; link the architecture for engineering roles.
6. Rehearse the five-minute walkthrough and one limitation-first answer.
7. Never state that J.P. Morgan, UBS, Morgan Stanley or State Street uses,
   reviewed or endorsed this project.

## High-value next learning

For India roles, learn RBI card/credit-risk guidance and IFRS 9/Ind AS 109
staging at interview depth, then discuss how Indian bureau, income/obligation
and affordability data would replace the demo's documented gaps. Do not bolt
those claims into the product without current authoritative data and legal/model
risk review.
