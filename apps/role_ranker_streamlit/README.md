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
