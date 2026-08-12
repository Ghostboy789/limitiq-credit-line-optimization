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

The verified public v1 uses 30,000 Taiwan accounts. Local v2 harmonizes six
independent training cohorts totaling 1,869,548 rows; a seventh legacy Statlog
file is reference-only because it duplicates the corrected South German
population.

V2 compares calibrated logistic and histogram-gradient-boosting pipelines. The
champion records macro test ROC-AUC 0.6845, PR-AUC 0.4024, Brier 0.1390 and log
loss 0.4334 across 373,910 untouched rows. Pooled metrics—ROC-AUC 0.6699 and
Brier 0.1406—are secondary because Lending Club dominates row counts.

The source labels have different events and horizons, so the output is a
source-specific adverse-outcome probability—not a common-horizon or regulatory
PD. Random within-source splitting does not prove future-vintage, unseen-market
or Indian-population performance. Region and structural missingness may identify
source.

## Data honesty and publication control

All source files are gitignored and checksum-bound. Corrected South German uses
UCI 573 / DOI `10.24432/C5QG88`. Give Me Some Credit and Home Credit geography
and currency are undisclosed. FICO/HELOC is a cleaned OpenML mirror. Lending
Club mirror metadata declares CC0, but upstream rights are not independently
verified.

The v2 publication gate is blocked pending terms review for Give Me Some Credit,
FICO/HELOC, Lending Club and Home Credit. A downloadable file is not automatically
an open licence.

## Synthetic business scenario

The local demo uses 1,200 deterministic synthetic profiles and INR exposures.
Its base scenario recommends 18 +10%, 18 +20% and 216 +30% increases, 283
no-change actions, 619 manual reviews and 46 automatic-increase freezes. Credit
limits move from ₹567.613M to ₹608.791M and the exposure proxy from ₹500.023M to
₹530.935M; the expected-loss proxy moves from ₹75.984M to ₹77.625M. Simulated
incremental contribution is ₹6.412M at 20.74% contribution / incremental
exposure.

No source observes a line-increase treatment. These values are synthetic,
simulated, non-causal and not realized impact, IFRS 9 ECL or regulatory capital.

## Engineering and governance

One Python 3.11 FastAPI/Jinja service loads checksum-verified artifacts,
supports portfolio/account/simulator/batch/governance/report workflows, renders
CSP-safe server-side SVG, validates uploads transiently and exposes a health
endpoint. The offline pipeline records source/model versions, fixed splits,
candidate metrics, source calibration, provenance and limitations.

## Product judgment

The strongest choice was what not to claim. More rows do not make heterogeneous
labels one PD, and a mirror does not clear upstream rights. Source-macro metrics,
duplicate-population exclusion, human review and a blocked publication gate are
more credible to a model-risk reviewer than an inflated “global accuracy” claim.

## Résumé bullets

- Built a production-shaped credit-line platform and local 1.87M-row multi-source
  benchmark with six independent cohorts, checksum-bound provenance and governed
  increase/hold/refer/freeze actions.
- Selected a calibrated histogram-gradient-boosting champion against logistic
  baseline using source-macro validation; achieved 0.685 macro ROC-AUC, 0.402
  macro PR-AUC and 0.139 macro Brier on 373,910 untouched test rows.
- Designed deterministic INR exposure and contribution simulation; a 1,200-
  profile scenario produced ₹6.41M simulated—not causal or realized—incremental
  contribution with explicit terms, model-risk and human-review controls.

See the [career targeting guide](CAREER_TARGETING.md) for J.P. Morgan, UBS,
Morgan Stanley and State Street positioning without implying endorsement.
