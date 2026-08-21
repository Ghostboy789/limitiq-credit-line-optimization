# LimitIQ recruiter brief

## The product in one sentence

LimitIQ is a production-shaped credit-line decision-support demonstration that
connects a coherent next-month default model to governed +10%, +20%, +30%, hold,
review and early-warning-freeze actions.

- **Live application:** https://limitiq-credit-line-optimization.onrender.com
- **Repository:** https://github.com/Ghostboy789/limitiq-credit-line-optimization
- **Release state:** v4.0.0 release candidate; verify the live `/health` payload before claiming deployment

## Evidence at a glance

| Evidence | Verified result |
|---|---:|
| Primary source | UCI Taiwan; 30,000 rows; next-month default |
| Split | 18,000 train / 6,000 validation / 6,000 untouched test |
| Champion | Sigmoid-calibrated histogram gradient boosting |
| Test ROC-AUC | 0.781138 (95% CI 0.767398–0.796055) |
| Test PR-AUC / Brier | 0.567889 / 0.133149 |
| Exact gain vs v3 | +0.023728 ROC; -0.008533 Brier; paired intervals exclude zero |
| Research union | 1,869,548 rows; six independent cohorts; governance only |
| Temporal study | 249,999 seasoned US loans; 2015 test ROC-AUC 0.647084; research only |
| Synthetic portfolio | 1,200 histories; ₹2.980M simulated contribution |

The behavioral primary has one event and one horizon. The global model remains a
separate transportability benchmark because its labels are heterogeneous. The
financial result is deterministic simulation, not observed, causal or realized
impact.

## What makes the project senior

- Corrected the architecture when model-risk review showed that one pooled
  heterogeneous score should not drive decisions.
- Preserved the 1.87M-row work as research evidence rather than hiding or
  overstating it.
- Froze champion and threshold before untouched-test evaluation and added 500
  deterministic bootstrap samples.
- Evaluated constrained actions instead of predicting an unrestricted limit.
- Replaced greedy portfolio pruning with one-candidate-per-account mixed-integer
  allocation under exposure, loss, capital and concentration caps.
- Separated source observations, model estimates and simulated economics.
- Implemented manual review, early-warning freeze, exposure/loss/profitability
  controls and an automatic-increase kill switch.
- Bound models, data and demo artifacts with provenance and checksums.
- Added validation review, issue ledger, model inventory, pilot design, India
  readiness contract, executable monitoring/experiment replays, maker-checker,
  SBOM, CodeQL, Trivy, operational probes and SQL reconciliation.

## What to inspect in five minutes

1. **Overview:** portfolio posture and the evidence boundary.
2. **Account:** score, candidate limit, reason codes, synthetic history and policy checks.
3. **Simulator:** stress loss, funding and response assumptions.
4. **Governance:** primary test evidence first; transportability research second.
5. **Committee memo:** conditional-use verdict and production conditions.

## Résumé-ready bullets

- Built a deployed, production-shaped credit-line decision platform that joins
  a calibrated next-month default model to constrained +10%/+20%/+30%, hold,
  review and freeze actions with transparent loss, exposure and profitability
  controls.
- Selected a sigmoid-calibrated histogram-gradient-boosting champion against a
  regularized-logistic baseline; achieved 0.781 ROC-AUC (95% CI 0.767–0.796),
  0.568 PR-AUC and 0.133 Brier on a 6,000-row untouched test set, with paired
  improvement over the frozen v3 model.
- Separated a 1.87M-row heterogeneous transportability benchmark from the
  decision model, then shipped checksum-bound artifacts, transient batch
  inference, policy simulation, governance evidence, Docker CI and security
  gates; kept ₹2.98M scenario value explicitly simulated.

Do not claim that ₹2.98M is production impact or that any employer reviewed,
endorsed or uses LimitIQ.

## Best-fit roles and interview angle

| Role family | Lead with |
|---|---|
| Consumer / Credit Risk Analytics | coherent target, calibration, threshold, actions and portfolio controls |
| Model Development / Validation / MRM | challenge finding, model separation, intervals, limitations and issue ledger |
| Decision Science | candidate-action optimization, guardrails and randomized pilot design |
| Risk Technology / Analytics Engineering | FastAPI service, provenance, CI, SBOM, security and observability |
| Credit Portfolio / Risk Product | committee memo, simulator, overrides, rollback and customer protection |

For J.P. Morgan, emphasize consumer-risk decision strategy and controls. For
UBS, lead with independent challenge and risk control. For Morgan Stanley, lead
with risk technology and reproducible analytics. For State Street, position the
work as model-risk and governed analytics engineering rather than retail-card
domain expertise.

## Limitation-first interview answer

“The hardest part was not improving a dashboard. Review showed that my large
multi-source model combined different adverse events and horizons. I corrected
the architecture: a source-coherent next-month Taiwan model now drives only a
synthetic educational portfolio, while the 1.87-million-row model is research
evidence only. The primary test ROC-AUC is 0.781 with a 0.767–0.796 bootstrap
interval after adding six-month behavioral history. It is still not production-ready because the data are historical,
Taiwan-only, not future-vintage, and line-response economics are simulated. The
next real step is local data, independent validation and a randomized pilot.”

## Related evidence

- [Independent validation-style review](INDEPENDENT_VALIDATION.md)
- [Validation issues](VALIDATION_ISSUES.md)
- [Model inventory](MODEL_INVENTORY.md)
- [Experiment design](EXPERIMENT_DESIGN.md)
- [India readiness](INDIA_READINESS.md)
- [Career targeting guide](CAREER_TARGETING.md)
