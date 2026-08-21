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

V3 uses UCI Taiwan's 30,000 accounts and explicit following-month default target
for the decision candidate. Calibrated logistic regression is the baseline and
calibrated histogram gradient boosting the champion. On 6,000 untouched test
rows, the champion records ROC-AUC 0.7574 (95% bootstrap CI 0.7433–0.7738),
PR-AUC 0.5087 and Brier 0.1417.

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

The v3 demo uses 1,200 deterministic Taiwan-contract synthetic profiles and INR
exposures. Its base scenario recommends 2 +20% and 268 +30% increases, 551
no-change actions, 323 manual reviews and 56 automatic-increase freezes. Credit
limits move from ₹514.951M to ₹566.423M and exposure proxy from ₹461.467M to
₹500.086M; loss proxy moves from ₹53.140M to ₹55.904M. Simulated incremental
contribution is ₹9.100M at 23.56% contribution / incremental exposure.

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
  regression; achieved 0.757 ROC-AUC (95% CI 0.743–0.774), 0.509 PR-AUC and
  0.142 Brier on 6,000 untouched test rows.
- Designed deterministic INR exposure and contribution simulation; a 1,200-
  profile scenario produced ₹9.10M simulated—not causal or realized—incremental
  contribution with explicit terms, model-risk and human-review controls.

See the [career targeting guide](CAREER_TARGETING.md) for J.P. Morgan, UBS,
Morgan Stanley and State Street positioning without implying endorsement.
