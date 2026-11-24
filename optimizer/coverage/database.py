"""Coverage-database and report parsing helpers.

Reads coverage reports / covergroup CSVs exported from QuestaSim (or any
simulator). These parsers operate on files only — no simulator internals are
accessed, consistent with the blackbox non-intrusive model.
"""

from __future__ import annotations

import csv
import os
import re
from typing import Any, Dict, List, Optional

from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.coverage.database")


class CoverageDatabase:
    """In-memory representation of merged coverage data."""

    def __init__(self) -> None:
        self.covergroups: Dict[str, Dict[str, Any]] = {}
        self.total_coverage: float = 0.0

    def add_covergroup(self, name: str, coverpoints: Dict[str, float]) -> None:
        self.covergroups[name] = {
            "coverpoints": dict(coverpoints),
            "coverage": self._cg_coverage(coverpoints),
        }
        self._recompute_total()

    def _cg_coverage(self, coverpoints: Dict[str, float]) -> float:
        if not coverpoints:
            return 0.0
        hit = sum(1 for v in coverpoints.values() if v > 0)
        return 100.0 * hit / len(coverpoints)

    def _recompute_total(self) -> None:
        if not self.covergroups:
            self.total_coverage = 0.0
            return
        self.total_coverage = sum(cg["coverage"] for cg in self.covergroups.values()) / len(
            self.covergroups
        )

    def coverage_percent(self) -> float:
        return self.total_coverage

    def unhit(self) -> List[str]:
        out: List[str] = []
        for cg_name, cg in self.covergroups.items():
            for cp_name, val in cg["coverpoints"].items():
                if val <= 0:
                    out.append(f"{cg_name}.{cp_name}")
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_coverage": self.total_coverage,
            "covergroups": self.covergroups,
            "unhit": self.unhit(),
        }


def parse_coverage_report(path: str) -> CoverageDatabase:
    """Parse a text coverage report into a CoverageDatabase.

    Expected (flexible) lines look like:
        covergroup write_cg : 75.00%
          cp_winc          : 100%
          cp_wfull         : 50%
    Any line matching `name : value%` is captured.
    """
    db = CoverageDatabase()
    if not path or not os.path.isfile(path):
        logger.warning("Coverage report not found: %s", path)
        return db

    current_cg: Optional[str] = None
    cg_cps: Dict[str, float] = {}

    line_re = re.compile(r"^\s*(?P<name>[A-Za-z0-9_.]+)\s*:\s*(?P<val>[0-9.]+)\s*%?\s*$")
    cg_re = re.compile(r"(?i)covergroup\s+(?P<name>[A-Za-z0-9_.]+)\s*:\s*(?P<val>[0-9.]+)")

    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = cg_re.search(line)
            if m:
                # Flush previous covergroup.
                if current_cg is not None:
                    db.add_covergroup(current_cg, cg_cps)
                    cg_cps = {}
                current_cg = m.group("name")
                continue
            lm = line_re.match(line)
            if lm and current_cg is not None:
                name = lm.group("name")
                val = float(lm.group("val"))
                cg_cps[name] = val
    if current_cg is not None:
        db.add_covergroup(current_cg, cg_cps)

    logger.info("Parsed coverage report %s: %.2f%% coverage", path, db.coverage_percent())
    return db


def parse_coverage_csv(path: str) -> CoverageDatabase:
    """Parse a covergroup CSV (columns: covergroup,coverpoint,coverage_pct)."""
    db = CoverageDatabase()
    if not path or not os.path.isfile(path):
        logger.warning("Coverage CSV not found: %s", path)
        return db
    by_cg: Dict[str, Dict[str, float]] = {}
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cg = row.get("covergroup") or row.get("covergroup_name") or "default"
            cp = row.get("coverpoint") or row.get("name") or "cp"
            try:
                val = float(row.get("coverage_pct") or row.get("coverage") or 0.0)
            except ValueError:
                val = 0.0
            by_cg.setdefault(cg, {})[cp] = val
    for cg, cps in by_cg.items():
        db.add_covergroup(cg, cps)
    logger.info("Parsed coverage CSV %s: %.2f%% coverage", path, db.coverage_percent())
    return db


def merge_databases(*dbs: CoverageDatabase) -> CoverageDatabase:
    """Merge multiple CoverageDatabase instances (max coverage per coverpoint)."""
    merged = CoverageDatabase()
    for db in dbs:
        for cg_name, cg in db.covergroups.items():
            existing = merged.covergroups.setdefault(cg_name, {"coverpoints": {}, "coverage": 0.0})
            for cp_name, val in cg["coverpoints"].items():
                prev = existing["coverpoints"].get(cp_name, 0.0)
                existing["coverpoints"][cp_name] = max(prev, float(val))
            merged._recompute_total()
    return merged


__all__ = ["CoverageDatabase", "parse_coverage_report", "parse_coverage_csv", "merge_databases"]
