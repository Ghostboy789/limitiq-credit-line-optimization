# V4.1 model-improvement evidence

## Outcome

V4.1 strengthens calibration challenge, temporal evidence, monitoring,
experimental readiness, India data readiness and inference controls without
claiming a new production model. The checksum-bound v4 sigmoid-calibrated HGB
remains the application primary because its frozen test cannot honestly be
reused to promote a post-test calibrator.

## Implemented evidence

1. **Disciplined challenger search.** Logistic/sigmoid, HGB/sigmoid,
   HGB/isotonic and monotonic-HGB/sigmoid were prespecified and assessed with
   three-fold out-of-fold predictions on 24,000 development rows. Isotonic HGB
   has the lowest development Brier (`0.135737`) while remaining within the
   ROC gate. This is development evidence only.
2. **Calibration diagnostics.** Every candidate reports Brier, log loss,
   expected calibration gap, calibration intercept and slope.
3. **Inference support.** Development 0.5th–99.5th percentile ranges are
   recorded for all 17 engineered features. Three or more breaches route a
   request to manual review rather than extrapolating automatically.
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
