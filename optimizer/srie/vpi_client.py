"""TCP client that bridges the Python SRIE agent and the QuestaSim VPI plug-in.

The VPI plug-in (srie_vpi.dll) runs inside the simulator and exposes a TCP
server on localhost:<port>. This client connects to it, receives simulation
events/state, and sends back optimizer actions (stimulus/seed/constraint
adjustments) which the plug-in applies via VPI (vpi_put_value, re-seed, ...).

All communication is local (loopback). No external network or AI API is used.
"""

from __future__ import annotations

import json
import socket
import time
from typing import Any, Dict, Optional

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.srie.vpi_client")


class VPIClient:
    """JSON-over-TCP client to the VPI plug-in."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5555,
                 timeout: float = 5.0, reconnect: bool = True) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)
        self.reconnect = reconnect
        self._sock: Optional[socket.socket] = None
        self.connected = False
        self.logger = get_logger("optimizer.srie.vpi_client")

    def connect(self) -> bool:
        self.disconnect()
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            sock.settimeout(self.timeout)
            self._sock = sock
            self.connected = True
            self.logger.info("Connected to VPI plug-in at %s:%d", self.host, self.port)
            return True
        except OSError as exc:
            self.connected = False
            self._sock = None
            self.logger.warning("Cannot connect to VPI plug-in %s:%d: %s", self.host, self.port, exc)
            return False

    def disconnect(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self.connected = False

    def _ensure(self) -> bool:
        if self.connected and self._sock is not None:
            return True
        if not self.reconnect:
            return False
        return self.connect()

    def send(self, message: Dict[str, Any]) -> bool:
        """Send a JSON command message to the VPI plug-in."""
        if not self._ensure():
            return False
        try:
            payload = (json.dumps(message) + "\n").encode("utf-8")
            assert self._sock is not None
            self._sock.sendall(payload)
            return True
        except OSError as exc:
            self.logger.warning("Send to VPI plug-in failed: %s", exc)
            self.disconnect()
            if self.reconnect:
                return self.connect() and self.send(message)
            return False

    def recv(self) -> Optional[Dict[str, Any]]:
        """Receive one JSON event message from the VPI plug-in (blocking)."""
        if not self._ensure():
            return None
        assert self._sock is not None
        try:
            buf = b""
            while b"\n" not in buf:
                chunk = self._sock.recv(4096)
                if not chunk:
                    self.disconnect()
                    return None
                buf += chunk
            line, _, _ = buf.partition(b"\n")
            return json.loads(line.decode("utf-8"))
        except (OSError, ValueError) as exc:
            self.logger.warning("Recv from VPI plug-in failed: %s", exc)
            self.disconnect()
            return None

    def send_action(self, action: Dict[str, Any]) -> bool:
        """Send an optimizer action (stimulus/seed/constraint command)."""
        msg = {"type": "action", "ts": time.time(), "action": action}
        return self.send(msg)

    def heartbeat(self) -> bool:
        return self.send({"type": "heartbeat", "ts": time.time()})

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()


__all__ = ["VPIClient"]
