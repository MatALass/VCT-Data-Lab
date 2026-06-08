# Role Ranker Streamlit Apps

This folder contains the two historical role-ranker modes merged into the unified project.

## Recommended mode

```bash
streamlit run apps/role_ranker_streamlit/tournament_app.py
```

Tournament mode tracks wins/losses, elimination state, remaining losses and tournament score.

## Legacy Elo mode

```bash
streamlit run apps/role_ranker_streamlit/elo_app.py
```

Elo mode is preserved to avoid losing the original pairwise-ranking functionality.

## Role inference v5

The ranker now uses a more conservative business-rule layer instead of a simple "top 3 agents" heuristic:

- role scores are weighted by per-agent rounds when available;
- when VLR only exposes an agent pool, agents are weighted equally and the limitation is shown in `role_explanation`;
- Viper is treated as Sentinel-adjacent zone control when the rest of the pool is Sentinel-heavy;
- Flex requires meaningful spread across at least three roles, not a single emergency pick;
- exact five-player team groups are normalized into Duelist / Controller / Initiator / Sentinel / Flex;
- larger groups caused by roster changes are not forced into a perfect five-role structure, but duplicated roles can be reassigned to missing roles or Flex when the player pool supports it.

Useful QA columns are visible in the Streamlit expander: `raw_role`, `team_role`, `role_scores`, `flex_score`, `distinct_roles`, and `role_explanation`.
