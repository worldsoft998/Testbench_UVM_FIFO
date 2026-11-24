"""Coverage-report parser for the blackbox optimizer.

Reads QuestaSim coverage reports (plain text) and extracts per-coverpoint
coverage percentages. Operates on files only — no simulator internals.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.blackbox.report_parser")


# Line shape: "cp_wfull.full         :   0.00  (hit 0 of 1)"
_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.]+)\s+:\s*(?P<pct>[0-9.]+)\s*%\s*"
    r"(?:\(\s*hit\s*(?P<hit>[0-9]+)\s*of\s*(?P<total>[0-9]+)\s*\))?\s*$"
)
_CG_RE = re.compile(r"(?i)covergroup\s+(?P<name>[A-Za-z0-9_.]+)")


def parse_report(path: str) -> Dict[str, Any]:
    """Parse a coverage report file.

    Returns
    -------
    dict
        {
          "covergroups": { cg_name: { cp_name: {"pct": float, "hit": int, "total": int} } },
          "total_coverage": float,
          "unhit": [ "cg.cp", ... ],
        }
    """
    result: Dict[str, Any] = {
        "covergroups": {},
        "total_coverage": 0.0,
        "unhit": [],
    }
    if not path or not os.path.isfile(path):
        logger.warning("Coverage report not found: %s", path)
        return result

    current_cg: str | None = None
    cps: Dict[str, Dict[str, Any]] = {}

    def flush() -> None:
        nonlocal current_cg, cps
        if current_cg is not None:
            result["covergroups"][current_cg] = cps
        current_cg = None
        cps = {}

    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = _CG_RE.search(line)
            if m:
                flush()
                current_cg = m.group("name")
                continue
            lm = _LINE_RE.match(line)
            if lm and current_cg is not None:
                name = lm.group("name")
                pct = float(lm.group("pct"))
                hit = int(lm.group("hit")) if lm.group("hit") else None
                total = int(lm.group("total")) if lm.group("total") else None
                cps[name] = {"pct": pct, "hit": hit, "total": total}
    flush()

    # Total coverage = average of covergroup coverage.
    cg_pcts = []
    for cg_name, cg in result["covergroups"].items():
        if cg:
            cg_pcts.append(sum(cp["pct"] for cp in cg.values()) / len(cg))
        for cp_name, cp in cg.items():
            if cp["pct"] <= 0:
                result["unhit"].append(f"{cg_name}.{cp_name}")
    result["total_coverage"] = (
        sum(cg_pcts) / len(cg_pcts) if cg_pcts else 0.0
    )

    logger.info("Parsed report %s: coverage=%.2f%% unhit=%d",
                path, result["total_coverage"], len(result["unhit"]))
    return result


def unhit_coverpoints(report: Dict[str, Any]) -> List[str]:
    return list(report.get("unhit", []))


__all__ = ["parse_report", "unhit_coverpoints"]
