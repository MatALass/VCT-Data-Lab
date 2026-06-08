# Architecture

```text
src/vlr_analytics/
  scraping/      # extraction VLR vers data/raw
  processing/    # nettoyage stable vers data/processed
  marts/         # tables analytiques intermédiaires
  modeling/      # scores, clusters, synergies, insights
  assets/        # registres d'images agents/équipes
  api/           # FastAPI + static assets
frontend/        # React/Vite dashboard
```

## Principe

Le dashboard ne doit jamais inventer de métriques. Chaque carte UI lit une table générée par le pipeline. Les métriques qui ressemblent à du win rate sont volontairement évitées côté équipe, car les résultats de matchs ne sont pas présents dans les données source.

## Pipeline logique

1. Scrape VLR.
2. Nettoie les colonnes et les identifiants.
3. Construit les marts : compositions, agents par équipe, cartes par équipe, synergies, tendances meta.
4. Construit les modèles descriptifs.
5. Expose les résultats via FastAPI.
6. Le front React consomme uniquement les endpoints API.
