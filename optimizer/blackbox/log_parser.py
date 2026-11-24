"""Simulator log parser for the blackbox optimizer.

Extracts simulation metadata, error/warning counts, runtime, and coverage
hints from a QuestaSim `sim.log`. Operates on files only.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.blackbox.log_parser")


_ERROR_RE = re.compile(r"(?i)\bUVM_ERROR\b|\bERROR\b")
_FATAL_RE = re.compile(r"(?i)\bUVM_FATAL\b|\bFATAL\b")
_WARNING_RE = re.compile(r"(?i)\bUVM_WARNING\b|\bWARNING\b")
_COV_RE = re.compile(r"(?i)coverage\s*[:=]\s*([0-9.]+)\s*%?")
_TIME_RE = re.compile(r"(?i)(?:simulation\s+time|elapsed)\s*[:=]\s*([0-9.]+)\s*(ns|us|ms|s)?")


def parse_log(path: str) -> Dict[str, Any]:
    """Parse a simulator log file.

    Returns
    -------
    dict
        {
          "errors": int,
          "fatals": int,
          "warnings": int,
          "coverage_pct": float or None,
          "sim_time": float or None,
          "clean": bool,
        }
    """
    result: Dict[str, Any] = {
        "errors": 0,
        "fatals": 0,
        "warnings": 0,
        "coverage_pct": None,
        "sim_time": None,
        "clean": True,
    }
    if not path or not os.path.isfile(path):
        logger.warning("Sim log not found: %s", path)
        return result

    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if _FATAL_RE.search(line):
                result["fatals"] += 1
                result["clean"] = False
            if _ERROR_RE.search(line):
                result["errors"] += 1
                result["clean"] = False
            if _WARNING_RE.search(line):
                result["warnings"] += 1
            m = _COV_RE.search(line)
            if m:
                try:
                    result["coverage_pct"] = float(m.group(1))
                except ValueError:
                    pass
            m = _TIME_RE.search(line)
            if m:
                try:
                    result["sim_time"] = float(m.group(1))
                except ValueError:
                    pass

    if result["fatals"] > 0 or result["errors"] > 0:
        result["clean"] = False
    logger.info("Parsed log %s: errors=%d fatals=%d warnings=%d clean=%s",
                path, result["errors"], result["fatals"], result["warnings"], result["clean"])
    return result


__all__ = ["parse_log"]
