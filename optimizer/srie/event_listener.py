"""Event-driven listener loop for the SRIE agent.

Blocks on the VPI client socket, receiving simulation events as they fire
(instantly, mid-simulation), and dispatches them to the SRIE agent for
RL-based steering. This is the "runtime/instantaneous" trigger path.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.srie.event_listener")


class EventListener:
    """Listens for VPI plug-in events on a background thread."""

    def __init__(self, vpi_client, on_event: Callable[[Dict[str, Any]], None]) -> None:
        self.vpi = vpi_client
        self.on_event = on_event
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.logger = get_logger("optimizer.srie.event_listener")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="srie-listener")
        self._thread.start()
        self.logger.info("Event listener started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self.logger.info("Event listener stopped")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self.vpi.recv()
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning("Listener recv error: %s", exc)
                break
            if event is None:
                # Connection closed; try to reconnect.
                if not self._stop.is_set():
                    self.logger.warning("VPI connection closed; reconnecting...")
                    self.vpi.connect()
                continue
            try:
                self.on_event(event)
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.exception("Event handler raised: %s", exc)


__all__ = ["EventListener"]
