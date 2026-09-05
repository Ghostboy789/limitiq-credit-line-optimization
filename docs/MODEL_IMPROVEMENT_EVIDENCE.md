# V4.2 model-improvement evidence

## Outcome

V4.2 strengthens calibration challenge, vintage-sensitivity evidence, monitoring,
experimental readiness, India data readiness and inference controls without
claiming a new production model. The checksum-bound v4 sigmoid-calibrated HGB
remains the application primary because its frozen test cannot honestly be
reused to promote a post-test calibrator.

## Calibrator decision rule

Before inspecting the paired result, the adoption rule is: adopt a new
calibrator only if the paired 95% candidate-minus-reference intervals for both
Brier score and log loss exclude zero in the candidate's favor.

## Deployed-configuration challenger evidence

All HGB candidates declare 180 maximum boosting iterations. The deployed model's
three calibrated estimators stop early at 62, 55 and 83 iterations because
`early_stopping='auto'` is active; each fold uses an internal 10% validation
split. The maximum is not effective complexity. Three-fold out-of-fold results
on the 24,000 development rows are:

| Candidate | ROC-AUC | PR-AUC | Brier | Log loss | Calibration gap | Slope |
|---|---:|---:|---:|---:|---:|---:|
| Logistic + sigmoid | 0.747257 | 0.508590 | 0.140692 | 0.448113 | 0.017725 | 1.0052 |
| HGB + sigmoid | **0.772719** | **0.547978** | **0.135689** | **0.432897** | 0.008635 | 1.0285 |
| HGB + isotonic | 0.771946 | 0.547074 | 0.135791 | 0.433069 | **0.005344** | 1.0011 |
| Monotonic HGB + sigmoid | 0.770721 | 0.542436 | 0.136226 | 0.434559 | 0.010118 | 1.0138 |

For isotonic minus sigmoid, the seeded 500-repeat paired bootstrap gives Brier
`+0.00010232` (95% interval `-0.00004410–0.00026984`) and log loss
`+0.00017265` (95% interval `-0.00030351–0.00064774`). Both cross zero, so
the adoption rule is not met. The result remains **no promotion**; even an
interval-excluding development result would require a new current-vintage or
independent holdout.

## Implemented evidence

1. **Disciplined challenger search.** The four candidates were prespecified and
   assessed through the shared frozen-split control and three-fold out-of-fold
   predictions on 24,000 development rows.
2. **Calibration diagnostics.** Every candidate reports Brier, log loss,
   expected calibration gap, calibration intercept and slope.
3. **Inference support.** Payment-to-bill ratios are capped at 5× before the
   generic model clip, preventing near-zero bills from exploding support bounds.
   Three or more breaches route a request to manual review. The shipped portfolio
   has zero routes; a labelled synthetic governance exhibit demonstrates one.
4. **Vintage and stress evidence.** The separate US installment-loan research
   track orders matured terminal labels by origination vintage and reports
   high-DTI, high-revolving-utilization and prior-delinquency segments. Because
   2013 outcomes were not observable until 2016, it is not a point-in-time
   backtest or temporal-stability evidence. It never feeds card recommendations.
5. **Monitoring stability.** Matured-outcome replays now report calibration,
   discrimination and Brier evidence across utilization and delinquency
   segments in addition to portfolio-level alerts.
6. **Observed experiment readiness.** The four-arm analyzer accepts real
   randomized inputs and reports ITT/CUPED uncertainty and delinquency harm
   intervals. The committed replay remains clearly synthetic.
7. **India forward-validation gate.** A strict account-month runner requires
   complete 12-month outcomes, four chronological partitions and account-level
   separation. No local artifact is fabricated while governed Indian outcomes
   are absent.
8. **Affordability and customer protection.** The India contract measures FOIR,
   aggregate issuer limits and aggregate-limit-to-income. Any positive offer
   requires explicit customer acceptance before activation.

## Promotion rule

No V4.2 research result changes the primary artifact. Promotion requires a new
current-vintage card holdout (ideally representative of the intended Indian
portfolio), independent validation, approved thresholds and customer-protection
review. Simulated economics require a governed randomized pilot before any
causal or business-impact claim.
