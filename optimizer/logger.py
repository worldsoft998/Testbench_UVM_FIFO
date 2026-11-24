"""Structured logging for AId-UVO-RT.

Provides a small console logger with optional file output. All logs are local;
nothing is sent to any remote service (consistent with the Local-Only AI Policy).
"""

import logging
import os
import sys
from typing import Optional


_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: Optional[int] = None, log_file: Optional[str] = None) -> logging.Logger:
    """Return a configured logger.

    Parameters
    ----------
    name : str
        Logger name (usually __module__).
    level : int, optional
        Logging level. Defaults to LOG_LEVEL env or INFO.
    log_file : str, optional
        If given, also write logs to this file.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        # Already configured.
        return logger

    lvl_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    lvl = getattr(logging, lvl_name, logging.INFO)
    if level is not None:
        lvl = level
    logger.setLevel(lvl)
    logger.propagate = False

    fmt = logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)) or ".", exist_ok=True)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


__all__ = ["get_logger"]
