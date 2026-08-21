# SQL decision mart

`portfolio_mart.sql` creates four read-only SQLite views over the committed,
deterministic Taiwan-contract synthetic primary-model portfolio. It demonstrates portfolio
reconciliation, action aggregation, development-source analysis and risk-band
concentration without adding a runtime database or retaining uploaded data.

```bash
python -m limitiq.analytics --check
python -m limitiq.analytics --output reports/sql_portfolio_reconciliation.json
```

The SQL results are scenario evidence, not production outcomes, regulatory ECL
or an Indian customer portfolio.
