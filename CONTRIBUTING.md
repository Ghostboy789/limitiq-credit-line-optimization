# Contributing

LimitIQ accepts narrowly scoped changes that preserve the boundary between
observed source data, model estimates and simulated decisions.

1. Create a branch from `main`.
2. Do not commit raw datasets, customer information, credentials or local caches.
3. Keep public-source terms, target definitions and checksums explicit.
4. Run `python -m pytest`, `ruff check .`, `ruff format --check .` and
   `python -m limitiq.analytics --check`.
5. Explain any changed model, policy, financial or governance claim in the pull
   request and update its versioned evidence.

Real lending integrations, paid services and new data sources require a separate
documented security, privacy, legal and model-risk decision.
