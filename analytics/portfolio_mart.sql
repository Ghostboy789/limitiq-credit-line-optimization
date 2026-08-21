-- Read-only recruiter evidence: a minimal decision mart over synthetic profiles.
-- The application remains stateless; this SQL is for reproducible reconciliation.

CREATE VIEW portfolio_reconciliation AS
SELECT
    COUNT(*) AS accounts,
    ROUND(SUM(current_limit_inr), 2) AS current_limit,
    ROUND(SUM(proposed_limit), 2) AS proposed_limit,
    ROUND(SUM(current_ead), 2) AS current_ead,
    ROUND(SUM(proposed_ead), 2) AS proposed_ead,
    ROUND(SUM(current_expected_loss), 2) AS current_expected_loss,
    ROUND(SUM(proposed_expected_loss), 2) AS proposed_expected_loss,
    ROUND(SUM(incremental_contribution), 2) AS incremental_contribution,
    SUM(CASE WHEN increase_pct > 0 THEN 1 ELSE 0 END) AS eligible_increases
FROM decisions;

CREATE VIEW action_summary AS
SELECT
    action,
    COUNT(*) AS accounts,
    ROUND(SUM(proposed_limit - current_limit_inr), 2) AS incremental_limit,
    ROUND(SUM(incremental_contribution), 2) AS simulated_contribution
FROM decisions
GROUP BY action;

CREATE VIEW source_risk_summary AS
SELECT
    source_dataset,
    COUNT(*) AS accounts,
    ROUND(AVG(pd), 6) AS mean_score,
    ROUND(AVG(utilization), 6) AS mean_utilization,
    ROUND(SUM(proposed_ead), 2) AS proposed_ead,
    ROUND(SUM(proposed_expected_loss), 2) AS proposed_loss_proxy
FROM decisions
GROUP BY source_dataset;

CREATE VIEW risk_band_summary AS
SELECT
    risk_band,
    COUNT(*) AS accounts,
    ROUND(SUM(proposed_ead), 2) AS proposed_ead,
    ROUND(SUM(proposed_expected_loss), 2) AS proposed_loss_proxy
FROM decisions
GROUP BY risk_band;
