# VLR Analytics Pro

Unified Valorant/VLR analytics project merging the previous VLR analytics pipeline, legacy VLR agent scraper notebooks, and both VCT role-ranker apps.

## What is included

### 1. VLR analytics pipeline

- Scrape VLR agent data.
- Clean raw tables into stable processed datasets.
- Build analytical marts.
- Build descriptive modeling outputs.
- Serve outputs through FastAPI.
- Display outputs in a React frontend.

### 2. Legacy 2026 agent scraper and notebooks

The original exploratory scripts and notebooks are preserved under:

```text
src/vlr_analytics/legacy_agent_scraper/
notebooks/
data/legacy_2026_agents/
```

They are kept because they contain the original scraping/transformation/aggregation path and exploratory analysis.

### 3. VCT role ranker

Two modes are preserved:

```bash
streamlit run apps/role_ranker_streamlit/tournament_app.py
streamlit run apps/role_ranker_streamlit/elo_app.py
```

Tournament mode is the recommended mode. Elo mode is retained for backward compatibility.

## Install

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .[dev]
```

For scraping with Playwright:

```bash
playwright install chromium
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

## Main commands

```bash
vlr scrape
vlr process
vlr build-marts
vlr model
vlr assets
vlr full-run --skip-scrape
vlr api
vlr ranker-paths
```

## Tests

```bash
pytest
```

## Data policy

Generated caches and build artifacts were removed. Sample and preserved datasets remain under `data/` so the project can be inspected without rerunning every scraper.

## Methodological warning

The modeling layer measures presence, stability, composition structure and descriptive tactical patterns. It does **not** claim to estimate team strength, true win probability, or player skill.

## API smoke test

After running:

```bash
vlr api
```

Open:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

Expected results:

- `/` returns project metadata and useful endpoint links.
- `/health` returns `{"status": "ok"}`.
- `/docs` opens the interactive FastAPI documentation.

## Data-quality reports

`vlr process` validates team compositions after processing the raw VLR matrix.
A valid Valorant composition should contain exactly five unique agents for one team on one map.

If anomalies are detected, the pipeline remains non-blocking and writes:

```text
data/reports/invalid_compositions.csv
```

This file contains:

```text
event,map,match_id,team,opponent,agents_count,expected_agents_count,agents,reason
```

Use this report to inspect scraping/data-quality edge cases instead of ignoring the warning printed by the CLI.
