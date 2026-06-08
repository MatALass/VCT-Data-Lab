"""Centralized statistical thresholds for VLR Analytics.

Change here rather than hard-coding in marts, models, or UI code.
"""

# --- Agent meta presence ---
MIN_META_MAPS_PLAYED: int = 2          # below this → low_sample_signal
MIN_SPECIALIST_PICK_RATE: float = 0.05  # kept for backward-compat (marts shim)
MIN_SPECIALIST_MAPS_PLAYED: int = 2     # kept for backward-compat

# --- Team tactical profiles ---
MIN_TACTICAL_PROFILE_COMPOSITIONS: int = 3  # below this → low_sample_profile

# --- Team map identity ---
MIN_MAP_IDENTITY_COMPOSITIONS: int = 1  # below this → low_signal

# --- Composition patterns ---
MIN_COMP_PATTERN_USES: int = 1  # below this → low_sample_comp

# --- Agent pair patterns (synergy) ---
MIN_SYNERGY_PAIR_PICKS: int = 3
MIN_SYNERGY_TEAMS_COUNT: int = 2
