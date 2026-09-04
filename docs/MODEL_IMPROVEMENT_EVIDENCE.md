# V4.1 model-improvement evidence

## Outcome

V4.1 strengthens calibration challenge, temporal evidence, monitoring,
experimental readiness, India data readiness and inference controls without
claiming a new production model. The checksum-bound v4 sigmoid-calibrated HGB
remains the application primary because its frozen test cannot honestly be
reused to promote a post-test calibrator.

## Calibrator decision rule

Before inspecting the paired result, the adoption rule is: adopt a new
calibrator only if the paired 95% candidate-minus-reference intervals for both
Brier score and log loss exclude zero in the candidate's favor.

## Deployed-configuration challenger evidence

All HGB candidates used 180 maximum boosting iterations, matching the deployed
behavioral model configuration. Three-fold out-of-fold results on the 24,000
development rows are:

| Candidate | ROC-AUC | PR-AUC | Brier | Log loss | Calibration gap | Slope |
|---|---:|---:|---:|---:|---:|---:|
| Logistic + sigmoid | 0.747223 | 0.508847 | 0.140594 | 0.447859 | 0.018915 | 1.0066 |
| HGB + sigmoid | **0.772346** | 0.546790 | 0.135778 | 0.433135 | 0.008446 | 1.0303 |
| HGB + isotonic | 0.772185 | **0.547072** | **0.135737** | **0.432868** | **0.005497** | 1.0055 |
| Monotonic HGB + sigmoid | 0.771038 | 0.542365 | 0.136188 | 0.434412 | 0.009182 | 1.0159 |

For isotonic minus sigmoid, the seeded 500-repeat paired bootstrap gives Brier
`-0.00004135` (95% interval `-0.00019490–0.00010568`) and log loss
`-0.00026774` (95% interval `-0.00076437–0.00020020`). Both cross zero, so
the adoption rule is not met. The result remains **no promotion**; even an
interval-excluding development result would require a new current-vintage or
independent holdout.

## Implemented evidence

1. **Disciplined challenger search.** The four candidates were prespecified and
   assessed through the shared frozen-split control and three-fold out-of-fold
   predictions on 24,000 development rows.
2. **Calibration diagnostics.** Every candidate reports Brier, log loss,
   expected calibration gap, calibration intercept and slope.
3. **Inference support.** Development 0.5th–99.5th percentile ranges are
   recorded for all 17 pre-clip engineered features while estimator inputs
   remain clipped. Three or more breaches route a request to manual review
   rather than extrapolating automatically.
4. **Temporal and stress evidence.** The separate US installment-loan research
   track uses expanding train/calibration/test vintages and reports high-DTI,
   high-revolving-utilization and prior-delinquency segments. It never feeds
   card recommendations.
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

No V4.1 research result changes the primary artifact. Promotion requires a new
current-vintage card holdout (ideally representative of the intended Indian
portfolio), independent validation, approved thresholds and customer-protection
review. Simulated economics require a governed randomized pilot before any
causal or business-impact claim.
