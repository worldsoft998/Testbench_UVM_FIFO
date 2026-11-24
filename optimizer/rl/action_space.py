"""Action space for the verification optimizer.

An action encodes a stimulus/seed/constraint adjustment that the optimizer can
apply to the simulator. Actions are discrete so tabular Q-learning and DQN can
operate on them directly.

Action layout (fixed, documented):
  0  no_op                              — keep current stimulus
  1  increase_write_incidence           — bias write requests up
  2  decrease_write_incidence           — bias write requests down
  3  increase_read_incidence            — bias read requests up
  4  decrease_read_incidence            — bias read requests down
  5  increase_burst_length              — longer bursts (stress FIFO depth)
  6  decrease_burst_length              — shorter bursts
  7  bias_clock_ratio_write_fast        — write clock faster than read
  8  bias_clock_ratio_read_fast         — read clock faster than write
  9  reseed_randomizer                  — change simulation seed
  10 assert_reset_pulse                  — pulse reset to exercise reset paths
  11 focus_write_full_corner             — drive toward wfull corner cases
  12 focus_read_empty_corner             — drive toward rempty corner cases
"""

from __future__ import annotations

from typing import Any, Dict, List

ACTION_NAMES: List[str] = [
    "no_op",
    "increase_write_incidence",
    "decrease_write_incidence",
    "increase_read_incidence",
    "decrease_read_incidence",
    "increase_burst_length",
    "decrease_burst_length",
    "bias_clock_ratio_write_fast",
    "bias_clock_ratio_read_fast",
    "reseed_randomizer",
    "assert_reset_pulse",
    "focus_write_full_corner",
    "focus_read_empty_corner",
]

NUM_ACTIONS = len(ACTION_NAMES)

# Default magnitude applied when an action is selected (tunable).
DEFAULT_MAGNITUDE = 0.2


class ActionSpace:
    """Maps a discrete action index to a concrete stimulus command dict."""

    def __init__(self, num_actions: int = NUM_ACTIONS) -> None:
        self.num_actions = int(num_actions)

    def contains(self, action: int) -> bool:
        return 0 <= int(action) < self.num_actions

    def name(self, action: int) -> str:
        idx = int(action)
        if 0 <= idx < self.num_actions:
            return ACTION_NAMES[idx]
        return f"unknown({idx})"

    def to_command(self, action: int, magnitude: float = DEFAULT_MAGNITUDE) -> Dict[str, Any]:
        """Convert a discrete action into a command dict applied by the
        SRIE introspection interface or the blackbox seed manager."""
        idx = int(action)
        if not self.contains(idx):
            raise ValueError(f"Action {idx} out of range [0, {self.num_actions})")

        name = ACTION_NAMES[idx]
        cmd: Dict[str, Any] = {"action": name, "action_index": idx, "magnitude": float(magnitude)}

        if name == "no_op":
            cmd.update({})
        elif name == "increase_write_incidence":
            cmd.update({"winc_bias": +magnitude, "constraint": "write_incidence"})
        elif name == "decrease_write_incidence":
            cmd.update({"winc_bias": -magnitude, "constraint": "write_incidence"})
        elif name == "increase_read_incidence":
            cmd.update({"rinc_bias": +magnitude, "constraint": "read_incidence"})
        elif name == "decrease_read_incidence":
            cmd.update({"rinc_bias": -magnitude, "constraint": "read_incidence"})
        elif name == "increase_burst_length":
            cmd.update({"burst_length_bias": +magnitude})
        elif name == "decrease_burst_length":
            cmd.update({"burst_length_bias": -magnitude})
        elif name == "bias_clock_ratio_write_fast":
            cmd.update({"clock_ratio": "write_fast"})
        elif name == "bias_clock_ratio_read_fast":
            cmd.update({"clock_ratio": "read_fast"})
        elif name == "reseed_randomizer":
            cmd.update({"reseed": True})
        elif name == "assert_reset_pulse":
            cmd.update({"reset_pulse": True})
        elif name == "focus_write_full_corner":
            cmd.update({"corner": "wfull", "winc_bias": +magnitude})
        elif name == "focus_read_empty_corner":
            cmd.update({"corner": "rempty", "rinc_bias": -magnitude})
        return cmd

    def all_actions(self) -> List[int]:
        return list(range(self.num_actions))


__all__ = ["ActionSpace", "ACTION_NAMES", "NUM_ACTIONS", "DEFAULT_MAGNITUDE"]
