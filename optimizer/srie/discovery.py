"""Hierarchical discovery & reflection for SRIE.

When a coverage-relevant event fires, the SRIE agent reflects on what changed
inside the running testbench by querying the simulator hierarchy through the
VPI plug-in. No RTL source code is read — only simulator-exposed signal
values and hierarchy are inspected.
"""

from __future__ import annotations

from typing import Any, Dict, List

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.srie.discovery")


class Discovery:
    """Performs hierarchical discovery and reflection over simulator state.

    The VPI client exposes methods to traverse hierarchy and read signal
    values. This class assembles those into a structured reflection report
    that the RL state encoder consumes.
    """

    def __init__(self, vpi_client) -> None:
        self.vpi = vpi_client

    def reflect(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Build a reflection report for a simulation event.

        Parameters
        ----------
        event : dict
            Event from the VPI plug-in (type, path, value, timestamp, ...).

        Returns
        -------
        dict
            Reflection report with changed signals, hierarchy path, and
            derived observations for the RL agent.
        """
        report: Dict[str, Any] = {
            "event": event,
            "changed_signals": [],
            "hierarchy_path": event.get("path", ""),
            "timestamp": event.get("ts"),
            "observations": {},
        }

        # Discover what changed at the event path.
        path = event.get("path")
        if path:
            try:
                value = self.vpi.send({"type": "read_signal", "path": path})
                # send() returns bool; the VPI plug-in would stream the value
                # back via a separate recv() in a full implementation. Here we
                # keep a safe fallback using the event's embedded value.
                report["changed_signals"].append({
                    "path": path,
                    "value": event.get("value"),
                })
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Discovery read failed for %s: %s", path, exc)

        # Derive observations used by the state encoder.
        report["observations"] = self._derive_observations(event, report)
        logger.debug("Discovery reflection: %s", report)
        return report

    def _derive_observations(self, event: Dict[str, Any],
                             report: Dict[str, Any]) -> Dict[str, Any]:
        obs: Dict[str, Any] = {}
        etype = event.get("type", "")
        if etype == "coverage_sample":
            obs["coverage_event"] = True
            obs["coverpoint"] = event.get("coverpoint", "")
            obs["coverage_delta"] = event.get("coverage_delta", 0.0)
        elif etype == "value_change":
            obs["signal_transition"] = True
            obs["signal"] = event.get("path", "")
        elif etype == "stall":
            obs["coverage_stall"] = True
        return obs

    def walk_hierarchy(self, root: str = "uvm_top") -> List[str]:
        """Return a list of hierarchical paths under root (discovery only)."""
        paths: List[str] = []
        try:
            msg = {"type": "walk", "root": root}
            if self.vpi.send(msg):
                resp = self.vpi.recv()
                if resp and isinstance(resp, dict):
                    paths = resp.get("paths", [])
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Hierarchy walk failed: %s", exc)
        return paths


__all__ = ["Discovery"]
