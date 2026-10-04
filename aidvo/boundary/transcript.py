"""
Transcript (log) parsing - scalar quantities only.

Allowed observation interface per the AId-VO compliance rules:

* scalar coverage percentages (e.g. the total printed by the testbench's
  report phase, or a UCDB summary report),
* UVM error / warning / fatal counts from the UVM report summary,
* simulated time from the simulator log.

This module NEVER parses covergroups, coverpoints, bins, UVM class
hierarchy, or any other coverage-model internal structure.  It only applies
config-provided regexes to whole log text and keeps the last match
(the UVM report summary / final report phase output).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TranscriptStats:
    """Scalar summary extracted from one simulation transcript."""

    coverage_pct: Optional[float] = None   # scalar total coverage [%]
    uvm_errors: Optional[int] = None       # None = summary not found
    uvm_warnings: Optional[int] = None
    uvm_fatals: Optional[int] = None
    sim_time_ns: Optional[float] = None
    report_summary_found: bool = False

    @property
    def valid(self) -> bool:
        """A run is valid when it finished with a report summary and a
        parseable scalar coverage percentage."""
        return (
            self.report_summary_found
            and self.coverage_pct is not None
            and (self.uvm_fatals or 0) == 0
        )


def _last_float(text: str, pattern: str) -> Optional[float]:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if not matches:
        return None
    try:
        return float(matches[-1])
    except (TypeError, ValueError):
        return None


def _last_int(text: str, pattern: str) -> Optional[int]:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except (TypeError, ValueError):
        return None


def parse_transcript(text: str, parse_cfg: Dict[str, str]) -> TranscriptStats:
    """Extract the allowed scalar observations from a transcript/log."""
    stats = TranscriptStats()

    cov_re = parse_cfg.get("coverage_regex")
    if cov_re:
        stats.coverage_pct = _last_float(text, cov_re)

    err_re = parse_cfg.get("uvm_error_regex")
    warn_re = parse_cfg.get("uvm_warning_regex")
    fatal_re = parse_cfg.get("uvm_fatal_regex")
    if err_re:
        stats.uvm_errors = _last_int(text, err_re)
    if warn_re:
        stats.uvm_warnings = _last_int(text, warn_re)
    if fatal_re:
        stats.uvm_fatals = _last_int(text, fatal_re)

    stats.report_summary_found = stats.uvm_errors is not None

    time_re = parse_cfg.get("sim_time_regex")
    if time_re:
        stats.sim_time_ns = _last_float(text, time_re)

    return stats


def parse_report_total(text: str, total_regex: str) -> Optional[float]:
    """Extract the scalar TOTAL coverage percentage from a vendor coverage
    report text file.  Only aggregate/total percentage lines are matched -
    per-group or per-bin structures are out of scope by design."""
    if not total_regex:
        return None
    return _last_float(text, total_regex)
