"""Re-export structured logger (kept in optimizer.logger)."""

from optimizer.logger import get_logger  # noqa: F401

__all__ = ["get_logger"]
