"""Live functional-coverage tracker for the optimizer.

Observes covergroup/coverpoint samples (delivered by the SRIE VPI client or
blackbox parser) and tracks which coverpoints have been hit, coverage %, and
which coverpoints are stalled (not improving).
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.coverage.tracker")


class CoverageTracker:
    """Tracks functional coverage over time.

    Each coverpoint is identified by a string name (e.g. "cp_wfull.full").
    A coverpoint is considered "hit" once it has been sampled with a non-zero
    count at least once. "Stalled" means it has not improved in the last
    `stall_window` updates.
    """

    def __init__(self, stall_window: int = 10) -> None:
        self.stall_window = int(stall_window)
        self.coverpoints: Dict[str, Dict[str, Any]] = {}
        self._update_counter = 0
        self.history: List[Dict[str, Any]] = []

    def sample(self, coverpoint: str, value: float, bin_hit: bool = True) -> None:
        """Record a sample for a coverpoint.

        Parameters
        ----------
        coverpoint : str
            Coverpoint name (hierarchical, e.g. "write_cg.cp_wfull.full").
        value : float
            Sampled value / count.
        bin_hit : bool
            Whether this sample represents a bin being hit.
        """
        self._update_counter += 1
        cp = self.coverpoints.setdefault(
            coverpoint,
            {
                "name": coverpoint,
                "hit": False,
                "max_value": 0.0,
                "last_value": 0.0,
                "samples": 0,
                "last_update": 0,
                "best_update": 0,
            },
        )
        cp["samples"] += 1
        cp["last_value"] = float(value)
        cp["last_update"] = self._update_counter
        if float(value) > cp["max_value"]:
            cp["max_value"] = float(value)
            cp["best_update"] = self._update_counter
        if bin_hit and float(value) > 0:
            cp["hit"] = True

    def batch_sample(self, samples: Dict[str, float]) -> None:
        for name, val in samples.items():
            self.sample(name, val, bin_hit=(val > 0))

    def coverage_percent(self) -> float:
        if not self.coverpoints:
            return 0.0
        hit = sum(1 for cp in self.coverpoints.values() if cp["hit"])
        return 100.0 * hit / len(self.coverpoints)

    def hit_coverpoints(self) -> List[str]:
        return sorted([n for n, c in self.coverpoints.items() if c["hit"]])

    def unhit_coverpoints(self) -> List[str]:
        return sorted([n for n, c in self.coverpoints.items() if not c["hit"]])

    def stalled_coverpoints(self) -> List[str]:
        """Coverpoints hit but not improving within the stall window."""
        stalled = []
        for name, cp in self.coverpoints.items():
            if not cp["hit"]:
                continue
            age = self._update_counter - cp["best_update"]
            if age >= self.stall_window:
                stalled.append(name)
        return sorted(stalled)

    def stalled_fraction(self) -> float:
        hit = self.hit_coverpoints()
        if not hit:
            return 0.0
        stalled = set(self.stalled_coverpoints()) & set(hit)
        return len(stalled) / len(hit)

    def observation(self) -> Dict[str, Any]:
        """Return a dict suitable for the RL state encoder."""
        return {
            "coverage_pct": self.coverage_percent(),
            "hit_coverpoints": len(self.hit_coverpoints()),
            "total_coverpoints": len(self.coverpoints),
            "hit_ratio": (len(self.hit_coverpoints()) / len(self.coverpoints)) if self.coverpoints else 0.0,
            "stalled_coverpoints": self.stalled_fraction(),
            "stalled": self.stalled_fraction(),
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            "coverage_pct": self.coverage_percent(),
            "update_counter": self._update_counter,
            "coverpoints": {n: dict(c) for n, c in self.coverpoints.items()},
        }


__all__ = ["CoverageTracker"]
