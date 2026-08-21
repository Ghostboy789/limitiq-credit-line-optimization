# Recruiter-facing case study

## The problem

Credit-line growth is asymmetric: unused capacity may suppress growth, while an
increase can amplify loss, overextension and concentration. A useful product
must turn risk into governed candidate actions and expose the evidence,
financial assumptions and human-review boundaries.

## Product decision

LimitIQ evaluates current, +10%, +20% and +30% limits, simulates EAD and an
expected-loss proxy, applies delinquency, overextension, loss, profitability and
exposure controls, and selects the best eligible simulated contribution.
Deterioration freezes automation or routes to an analyst—never an ungoverned
punitive decrease.

## Model development

V4 uses UCI Taiwan's 30,000 accounts, explicit following-month default target
and six months of repayment, billing and payment behavior. Calibrated logistic
regression is the baseline and calibrated histogram gradient boosting the
champion. On 6,000 untouched test rows, it records ROC-AUC 0.7811 (95%
bootstrap CI 0.7674–0.7961), PR-AUC 0.5679 and Brier 0.1331. On those same
accounts it improves ROC by 0.0237 and Brier by 0.0085 versus v3.

The 1,869,548-row, six-cohort v2 model is retained only as transportability
research because its source labels have different events and horizons. Random
within-source splitting in both tracks does not prove future-vintage,
unseen-market or Indian-population performance.

## Data honesty and publication control

All source files are gitignored and checksum-bound. Corrected South German uses
UCI 573 / DOI `10.24432/C5QG88`. Give Me Some Credit and Home Credit geography
and currency are undisclosed. FICO/HELOC is a cleaned OpenML mirror. Lending
Club mirror metadata declares CC0, but upstream rights are not independently
verified.

The publication gate was cleared by repository-owner attestation on 14 August
2026; the supporting documents are retained by the owner. The case study does
not represent that attestation as an independent legal opinion.

## Synthetic business scenario

The v4 demo uses 1,200 deterministic Taiwan-contract synthetic histories and
INR exposures. Its base scenario recommends 288 +30% increases, 115 no-change
actions, 455 manual reviews and 342 automatic-increase freezes. Credit limits
move from ₹478.947M to ₹513.032M and exposure proxy from ₹401.899M to
₹427.463M; loss proxy moves from ₹48.712M to ₹50.340M. Simulated incremental
contribution is ₹2.980M at 11.66% contribution / incremental exposure.

No source observes a line-increase treatment. These values are synthetic,
simulated, non-causal and not realized impact, IFRS 9 ECL or regulatory capital.

## Engineering and governance

One Python 3.11 FastAPI/Jinja service loads checksum-verified artifacts,
supports portfolio/account/simulator/batch/governance/report workflows, renders
CSP-safe server-side SVG, validates uploads transiently and exposes a health
endpoint. The offline pipeline records source/model versions, fixed splits,
candidate metrics, source calibration, provenance and limitations.

## Product judgment

The strongest choice was correcting the architecture after challenge. More rows
do not make heterogeneous labels one PD, so v3 moves the global model out of
decisioning and promotes one coherent next-month target. Preserving the global
work as restricted research is more credible than an inflated “global PD” claim.

## Résumé bullets

- Built a production-shaped credit-line platform with a coherent next-month
  primary model, a separate 1.87M-row research benchmark, checksum-bound
  provenance and governed increase/hold/refer/freeze actions.
- Selected a calibrated histogram-gradient-boosting champion against logistic
  regression; achieved 0.781 ROC-AUC (95% CI 0.767–0.796), 0.568 PR-AUC and
  0.133 Brier on 6,000 untouched test rows.
- Designed deterministic INR exposure and contribution simulation; a 1,200-
  profile scenario produced ₹2.98M simulated—not causal or realized—incremental
  contribution with explicit terms, model-risk and human-review controls.

See the [career targeting guide](CAREER_TARGETING.md) for J.P. Morgan, UBS,
Morgan Stanley and State Street positioning without implying endorsement.
