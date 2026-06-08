# VCT Role Ranker

Streamlit app for building a personal VCT player ranking by role using VLR public HTML stats.

The goal is not to produce a purely statistical ranking. The app lets you choose between two players, then updates a dynamic Elo-like ranking for the selected role.

## Core idea

1. Scrape VLR player stats from `/stats` HTML pages.
2. Extract player, team, played agents and key metrics.
3. Infer a competitive role from the observed agent pool.
4. Let the user compare two players from the same role.
5. Update a persistent ranking after each duel.

## Role inference

Valorant only has four official agent roles: Duelist, Controller, Initiator and Sentinel.
The app adds `Flex` as a competitive label.

Rule used:

- The app maps each played agent to its official Valorant role.
- If one role represents at least 60% of the player's observed agent pool, the player receives that role.
- Otherwise the player is classified as `Flex`.

This is deliberate. In pro Valorant, some teams run double duelist, double controller, no sentinel, Viper hybrid roles, or role swaps by map. A strict one-player-one-role model would be misleading.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Optional CLI scraping

```bash
python scripts/scrape_players.py --event-id 2860 --min-rounds 200
```

The scraped file is saved to:

```text
data/processed/vlr_players_processed.csv
```

Your subjective rankings are saved to:

```text
data/processed/user_rankings.json
```

## Project structure

```text
vct_role_ranker_streamlit/
├── app.py
├── requirements.txt
├── pyproject.toml
├── scripts/
│   └── scrape_players.py
├── src/vct_ranker/
│   ├── agents.py
│   ├── models.py
│   ├── ranking.py
│   ├── roles.py
│   ├── scraper.py
│   └── storage.py
├── tests/
│   └── test_roles.py
└── data/
    ├── raw/
    └── processed/
```

## Design decisions

- `requests + BeautifulSoup` instead of Selenium/Playwright for easier deployment.
- Defensive parsing because VLR's HTML can change.
- Elo ranking instead of simple vote counts, because beating a highly rated player should matter more.
- Conservative role inference to avoid overclaiming when a player has a mixed pool.

## Limitations

- VLR is a public website, not a stable API. The scraper may need updates if their HTML changes.
- The role inference is based on observed agents, not official team role announcements.
- A subjective ranking requires many duels before it becomes stable.
