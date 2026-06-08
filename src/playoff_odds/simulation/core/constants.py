from __future__ import annotations
import numpy as np
REALISTIC_WINNING_MAP_SCORES = [(13, 5), (13, 6), (13, 7), (13, 8), (13, 9), (13, 10), (13, 11), (14, 12), (15, 13)]
REALISTIC_WINNING_MAP_WEIGHTS = np.array([0.08, 0.10, 0.14, 0.18, 0.18, 0.14, 0.10, 0.05, 0.03], dtype=float)
REALISTIC_WINNING_MAP_WEIGHTS /= REALISTIC_WINNING_MAP_WEIGHTS.sum()
