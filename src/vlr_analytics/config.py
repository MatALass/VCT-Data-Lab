from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MARTS_DIR = DATA_DIR / "marts"
MODELS_DIR = DATA_DIR / "models"
ASSETS_DIR = DATA_DIR / "assets"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_REPORTS_DIR = DATA_DIR / "reports"
EXPECTED_AGENTS_PER_COMP = 5

EVENTS = {
    "americas_stage_1": "https://www.vlr.gg/event/agents/2860/vct-2026-americas-stage-1",
    "china_stage_1": "https://www.vlr.gg/event/agents/2864/vct-2026-china-stage-1",
    "pacific_stage_1": "https://www.vlr.gg/event/agents/2775/vct-2026-pacific-stage-1",
    "emea_stage_1": "https://www.vlr.gg/event/agents/2863/vct-2026-emea-stage-1",
}

RAW_SUMMARY = RAW_DIR / "vlr_agents_summary_raw.csv"
RAW_MATRIX = RAW_DIR / "vlr_agents_matrix_raw.csv"

PROCESSED_SUMMARY = PROCESSED_DIR / "vlr_agents_summary_processed.csv"
PROCESSED_MATRIX = PROCESSED_DIR / "vlr_agents_matrix_processed.csv"

AGENT_MAP_STATS = MARTS_DIR / "agent_map_stats.csv"
TEAM_COMPOSITIONS = MARTS_DIR / "team_compositions.csv"
TEAM_AGENT_STATS = MARTS_DIR / "team_agent_stats.csv"
TEAM_MAP_STATS = MARTS_DIR / "team_map_stats.csv"
AGENT_SYNERGY = MARTS_DIR / "agent_synergy.csv"
META_TRENDS = MARTS_DIR / "meta_trends.csv"
TEAM_SIGNATURES = MARTS_DIR / "team_signatures.csv"

TEAM_STRENGTHS = MODELS_DIR / "team_profile_scores.csv"
AGENT_TIERS = MODELS_DIR / "agent_tiers.csv"
MAP_SPECIALISTS = MODELS_DIR / "map_specialists.csv"
COMPOSITION_CLUSTERS = MODELS_DIR / "composition_clusters.csv"
COMPOSITION_ARCHETYPES = MODELS_DIR / "composition_archetypes.csv"
TEAM_MAP_IDENTITY = MODELS_DIR / "team_map_identity.csv"
INSIGHTS = MODELS_DIR / "insights.json"

# v2 model outputs
AGENT_META_PRESENCE = MODELS_DIR / "agent_meta_presence.csv"
TEAM_TACTICAL_PROFILES = MODELS_DIR / "team_tactical_profiles.csv"
COMPOSITION_PATTERNS = MODELS_DIR / "composition_patterns.csv"
AGENT_PAIR_PATTERNS = MODELS_DIR / "agent_pair_patterns.csv"
AGENT_GLOBAL_META = MODELS_DIR / "agent_global_meta.csv"
AGENT_ASSETS = ASSETS_DIR / "agents"
TEAM_ASSETS = ASSETS_DIR / "teams"
AGENT_ASSET_REGISTRY = ASSETS_DIR / "agent_assets.csv"
TEAM_ASSET_REGISTRY = ASSETS_DIR / "team_assets.csv"
INVALID_COMPOSITIONS_REPORT = DATA_REPORTS_DIR / "invalid_compositions.csv"

for directory in [RAW_DIR, PROCESSED_DIR, MARTS_DIR, MODELS_DIR, REPORTS_DIR, DATA_REPORTS_DIR, AGENT_ASSETS, TEAM_ASSETS]:
    directory.mkdir(parents=True, exist_ok=True)
