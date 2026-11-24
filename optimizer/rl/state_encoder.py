"""State encoder: maps live simulator state to a fixed RL state vector.

The encoder consumes observations produced by the SRIE VPI client or the
blackbox log/report parsers and produces a normalized numeric vector that the
RL agent can consume. No RTL source is read — only simulator-exposed values.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.rl.state_encoder")


class StateEncoder:
    """Encodes simulator state into a fixed-length RL state vector.

    Features (order is fixed and documented):
      0  coverage_pct          — accumulated functional coverage [0, 1]
      1  coverage_growth_rate  — delta coverage per event/run (clipped)
      2  stalled_coverpoints   — fraction of coverpoints not improving [0, 1]
      3  hit_ratio             — fraction of coverpoints hit at least once [0, 1]
      4  flag_wfull           — write-full flag observed (0/1)
      5  flag_rempty          — read-empty flag observed (0/1)
      6  recent_transitions    — count of recent state transitions (normalized)
      7  time_budget_remaining — fraction of sim time budget left [0, 1]
    """

    def __init__(self, state_dim: int = 8) -> None:
        self.state_dim = int(state_dim)
        self._prev_coverage: float = 0.0

    def reset(self) -> None:
        self._prev_coverage = 0.0

    def encode(self, observation: Dict[str, Any]) -> np.ndarray:
        """Encode a raw observation dict into a normalized state vector.

        Missing keys are treated as zeros. All outputs are clipped to [0, 1]
        except coverage_growth_rate which is clipped to [-1, 1] then shifted.
        """
        vec = np.zeros(self.state_dim, dtype=np.float32)

        coverage = float(observation.get("coverage_pct", 0.0)) / 100.0
        coverage = float(np.clip(coverage, 0.0, 1.0))

        growth = float(observation.get("coverage_growth_rate", 0.0))
        growth = float(np.clip(growth, -1.0, 1.0))
        # Track growth relative to previous coverage for signal.
        growth = growth if abs(growth) > 1e-6 else (coverage - self._prev_coverage)
        growth = float(np.clip(growth, -1.0, 1.0))
        self._prev_coverage = coverage

        stalled = float(observation.get("stalled_coverpoints", 0.0))
        stalled = float(np.clip(stalled, 0.0, 1.0))

        hit_ratio = float(observation.get("hit_ratio", 0.0))
        hit_ratio = float(np.clip(hit_ratio, 0.0, 1.0))

        wfull = float(observation.get("wfull", 0.0))
        rempty = float(observation.get("rempty", 0.0))

        transitions = float(observation.get("recent_transitions", 0.0))
        transitions = float(np.clip(transitions / 100.0, 0.0, 1.0))

        time_left = float(observation.get("time_budget_remaining", 1.0))
        time_left = float(np.clip(time_left, 0.0, 1.0))

        vec[0] = coverage
        vec[1] = (growth + 1.0) / 2.0  # shift [-1,1] -> [0,1]
        vec[2] = stalled
        vec[3] = hit_ratio
        vec[4] = wfull
        vec[5] = rempty
        vec[6] = transitions
        vec[7] = time_left

        return vec

    def decode_action(self, action: int) -> Dict[str, Any]:
        """Placeholder: action decoding is handled by ActionSpace."""
        return {"action": int(action)}


__all__ = ["StateEncoder"]
