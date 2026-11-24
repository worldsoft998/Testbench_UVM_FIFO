"""Coverage-guided reward shaping for the verification optimizer.

The reward function encourages the RL agent to take actions that increase
functional coverage, especially hard-to-hit corner cases, while penalizing
stalls and excessive simulation time.
"""

from __future__ import annotations

from typing import Any, Dict


class RewardFunction:
    """Computes a scalar reward from before/after observations.

    Reward = w_cov * coverage_growth
           + w_new * newly_hit_coverpoints
           - w_stall * stall_penalty
           - w_time * time_penalty

    All weights are configurable. Defaults favor coverage growth and newly-hit
    coverpoints (corner-case emphasis).
    """

    def __init__(
        self,
        w_coverage: float = 10.0,
        w_new_hit: float = 5.0,
        w_stall: float = 2.0,
        w_time: float = 0.1,
        coverage_scale: float = 100.0,
    ) -> None:
        self.w_coverage = float(w_coverage)
        self.w_new_hit = float(w_new_hit)
        self.w_stall = float(w_stall)
        self.w_time = float(w_time)
        self.coverage_scale = float(coverage_scale)
        self._prev_coverage: float = 0.0
        self._prev_hit_count: int = 0

    def reset(self) -> None:
        self._prev_coverage = 0.0
        self._prev_hit_count = 0

    def compute(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
        elapsed_time: float = 0.0,
    ) -> float:
        """Return the scalar reward for the transition before -> after."""
        cov_before = float(before.get("coverage_pct", 0.0))
        cov_after = float(after.get("coverage_pct", 0.0))
        coverage_growth = (cov_after - cov_before) / self.coverage_scale

        hit_before = int(before.get("hit_coverpoints", 0))
        hit_after = int(after.get("hit_coverpoints", 0))
        newly_hit = max(0, hit_after - hit_before)

        stalled = float(after.get("stalled", 0.0))  # 0..1 fraction stalled
        stall_penalty = stalled

        reward = (
            self.w_coverage * coverage_growth
            + self.w_new_hit * float(newly_hit)
            - self.w_stall * stall_penalty
            - self.w_time * float(elapsed_time)
        )

        # Track for potential delta-based shaping in subclasses.
        self._prev_coverage = cov_after
        self._prev_hit_count = hit_after

        return float(reward)

    def coverage_reward(self, coverage_pct: float) -> float:
        """Simple reward equal to normalized coverage (useful for baselines)."""
        return float(coverage_pct) / self.coverage_scale


__all__ = ["RewardFunction"]
