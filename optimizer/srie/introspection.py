"""Introspection interface: push optimized stimulus back into the simulation.

Converts an RL action (from the action space) into a command message sent to
the VPI plug-in, which applies it via VPI (vpi_put_value, re-seed, constraint
bias, ...). No HDL source is modified — the simulator drives the DUT signals.
"""

from __future__ import annotations

from typing import Any, Dict, List

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.srie.introspection")


class Introspection:
    """Applies optimizer actions to the running simulation through the VPI client."""

    def __init__(self, vpi_client) -> None:
        self.vpi = vpi_client
        self.applied_actions: List[Dict[str, Any]] = []

    def apply(self, action: Dict[str, Any]) -> bool:
        """Send an action to the VPI plug-in to steer the simulation.

        The VPI plug-in interprets keys such as:
          - winc_bias / rinc_bias     : bias write/read incidence
          - burst_length_bias         : burst length adjustment
          - clock_ratio               : write_fast / read_fast
          - reseed                    : re-seed randomizer
          - reset_pulse               : pulse reset
          - corner                    : focus corner (wfull / rempty)
        """
        ok = self.vpi.send_action(action)
        if ok:
            self.applied_actions.append(dict(action))
            logger.info("Introspection applied action: %s", action.get("action"))
        else:
            logger.warning("Introspection failed to apply action: %s", action.get("action"))
        return ok

    def apply_command(self, command: Dict[str, Any]) -> bool:
        """Apply a raw command dict (e.g. from ActionSpace.to_command)."""
        return self.apply(command)

    def history(self) -> List[Dict[str, Any]]:
        return list(self.applied_actions)

    def reset_history(self) -> None:
        self.applied_actions = []


__all__ = ["Introspection"]
