# Merge notes

This project was built by merging four source projects into one unified repository:

- `vlr_refactored`: kept as the architectural base.
- `vlr-analytics-pro`: preserved as legacy 2026 VLR agent scraping/transformation/aggregation notebooks and scripts.
- `vct_role_ranker_streamlit_tournament`: integrated as the canonical Streamlit role-ranker mode and `vct_ranker` package.
- `vct_role_ranker_streamlit`: preserved as the legacy Elo mode through `vct_ranker_elo` and `apps/role_ranker_streamlit/elo_app.py`.

No functional branch was intentionally discarded. Generated caches, bytecode, `node_modules`, test caches and build artifacts were removed.
