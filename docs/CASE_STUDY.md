# Recruiter-facing case study

## The problem

Card portfolios face an asymmetric decision: unused capacity can suppress
growth, but an increase can amplify loss, overextension and concentration.
Typical model demos stop at default prediction; real product work must turn PD
into governed, explainable candidate actions and show the financial trade-off.

## Product decision

LimitIQ evaluates current, +10%, +20% and +30% limits. It calculates EAD and
expected loss, simulates transparent annual revenue/cost, applies delinquency,
payment, overextension, loss, profitability and exposure controls, and chooses
the best eligible contribution. Deterioration freezes automation or routes to an
analyst—never an ungoverned punitive decrease.

## Data honesty

The public UCI source supports PD but contains no observed customer response to
a line increase. LimitIQ therefore separates observed data, model estimates and
simulations in code, UI and reports. Baseline PD is held constant across
candidates; all response/economics assumptions are adjustable. No uplift or
profit is called causal or realized.

## Evidence

The calibrated histogram-gradient-boosting champion was selected on validation
and evaluated once on 6,000 untouched accounts: ROC-AUC 0.7811, PR-AUC 0.5679,
Brier 0.1331, log loss 0.4264 and recall 0.7069 at the frozen 0.1739 threshold.
With documented default assumptions, the 6,000-account scenario recommends
1,904 increases, raises proposed lines from ₹3.005016B to ₹3.255868B and
produces ₹41.343M simulated annual incremental contribution at 21.93%
simulated contribution/incremental-EAD. These are scenario outputs only.

## Engineering and governance

One Dockerized FastAPI/Jinja service loads checksum-verified artifacts, supports
responsive portfolio/account/simulator/batch/governance/report workflows, uses
strict transient upload validation, emits safe exports/security headers and has
a health endpoint. The offline pipeline records data/model versions, fixed
splits, candidate metrics, calibration, segment diagnostics and reports.

Governance explicitly covers current SR 26-2/OCC 2026-13, Basel component
interpretation, IFRS 9 non-equivalence, Regulation B reason accuracy and the
critical Regulation Z ability-to-pay gap.

## Product judgment

The biggest design choice was what not to claim. A more impressive-looking
"optimal limit" regression would be scientifically false without treatment and
response data. A constrained candidate optimizer is safer, more explainable and
operationally testable. The production roadmap begins with ability-to-pay and
causal experimentation—not more model complexity.

## Three evidence-based résumé bullets

- Built a Dockerized credit-line optimization product over 30,000 CC BY 4.0 UCI
  accounts, translating calibrated PD into governed +10/+20/+30/no-change,
  manual-review and early-warning freeze actions across seven working web areas.
- Trained and calibrated logistic and gradient-boosting models with fixed
  60/20/20 splits; selected the champion on validation and achieved 0.781 ROC-AUC,
  0.568 PR-AUC and 0.133 Brier score on a 6,000-account untouched test set.
- Designed a deterministic ECL/EAD and contribution optimizer with transparent
  policy assumptions; the default scenario selected 1,904 increases and ₹41.34M
  simulated—not causal or realized—annual incremental contribution.

For India-based applications, use the companion
[career targeting guide](CAREER_TARGETING.md) to map this evidence to credit
risk, model risk, risk analytics and risk-technology roles without presenting
the Taiwan source population or simulated economics as Indian production data.
