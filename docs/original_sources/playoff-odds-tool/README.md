# Playoff Odds Tool — V3.0

A simulation-first playoff analytics project with a modular Python engine, a React frontend, persisted match updates from the console, and a reproducible JSON contract between backend and UI.

## What this project now does well

- runs a **Monte Carlo qualification simulation**
- applies **official tie-break ordering**
- exposes **match leverage** and **scenario extremes**
- exports a **single frontend-ready JSON dataset**
- lets you **persist a real match result from the console** and immediately regenerate the dataset

## Architecture

```text
simulation/config.sample.json
    ↓
simulation/core/*
    ├─ config validation
    ├─ state building
    ├─ ranking / tie-break logic
    ├─ simulation / conditional analysis
    └─ JSON export
    ↓
data/vct-emea-2026.json
    ↓
React frontend (src/*)
```

## Project structure

```text
playoff-odds-tool/
├─ data/
├─ simulation/
│  ├─ core/
│  ├─ tests/
│  ├─ cli.py
│  ├─ run_simulation.py
│  ├─ run_what_if.py
│  └─ config.sample.json
├─ src/
├─ package.json
└─ pyproject.toml
```

## Honest model note

Two analytical approximations remain and are documented explicitly:

- **Scenario extremes** are best / worst cases observed inside the Monte Carlo sample.
- **Exact winner-only bounds** enumerate winner combinations but use a deterministic proxy scoreline for tie-break-sensitive map / round metrics.

## Python setup

```bash
pip install -r simulation/requirements.txt
```

or:

```bash
pip install -e .[dev]
```

## Main simulation

```bash
python -m simulation.run_simulation   --config simulation/config.sample.json   --output-json data/vct-emea-2026.json   --output-dir simulation/output   --show-progress
```

## Deterministic what-if snapshot

```bash
python -m simulation.run_what_if   --config simulation/config.sample.json   --output-json data/vct-emea-2026-whatif.json   --force "GX vs EF=GX"   --force "BBL vs VIT=BBL"
```

## Persist a real match result from the console

### Interactive mode

```bash
python -m simulation.cli set-match-result   --config simulation/config.sample.json   --dataset data/vct-emea-2026.json
```

### Direct command mode

```bash
python -m simulation.cli set-match-result   --config simulation/config.sample.json   --dataset data/vct-emea-2026.json   --match "NAVI vs TL"   --winner TL   --score 2-1
```

### List remaining matches

```bash
python -m simulation.cli list-remaining-matches --config simulation/config.sample.json
```

The console workflow now updates:

- `standings`
- `remaining_matches`
- `played_matches`
- the frontend dataset JSON after regeneration

## Frontend

```bash
npm install
npm run build
```

## Tests

```bash
python -m unittest discover -s simulation/tests -v
```

## Versioning policy

Version is aligned across:

- `pyproject.toml` → `3.0.0`
- `package.json` → `3.0.0`
- README → `V3.0`
