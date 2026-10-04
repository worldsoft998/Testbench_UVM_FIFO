"""
Campaign history records shared by the baseline (AI off) and AI campaigns.

A history is the ground truth for the side-by-side comparison report: one
record per simulation run with its scalar coverage, UVM counts, wall time and
(which the AI campaign only) the per-step reward.
"""
from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

CSV_FIELDS = [
    "run", "mode", "algo", "test", "seed", "profile", "coverage_pct", "best_pct",
    "delta_pct", "uvm_errors", "uvm_warnings", "valid", "wall_time_s",
    "sim_time_ns", "reward", "decision_time_s",
]


@dataclass
class RunRecord:
    run: int
    mode: str                              # "baseline" | "ai"
    algo: str = ""
    test: str = ""
    seed: int = 0
    profile: str = ""
    coverage_pct: Optional[float] = None
    best_pct: float = 0.0
    delta_pct: float = 0.0
    uvm_errors: Optional[int] = None
    uvm_warnings: Optional[int] = None
    valid: bool = True
    wall_time_s: float = 0.0
    sim_time_ns: Optional[float] = None
    reward: float = 0.0
    decision_time_s: float = 0.0


@dataclass
class History:
    mode: str
    algo: str = ""
    seed_base: int = 0
    goal_pct: float = 95.0
    created: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    runs: List[RunRecord] = field(default_factory=list)
    best_pct: float = 0.0

    def add(self, rec: RunRecord) -> None:
        if rec.coverage_pct is not None:
            rec.delta_pct = max(0.0, rec.coverage_pct - self.best_pct)
            self.best_pct = max(self.best_pct, rec.coverage_pct)
            rec.best_pct = self.best_pct
        else:
            rec.best_pct = self.best_pct
        self.runs.append(rec)

    # ------------------------------------------------------------------ io
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "algo": self.algo,
            "seed_base": self.seed_base,
            "goal_pct": self.goal_pct,
            "created": self.created,
            "best_pct": self.best_pct,
            "runs": [asdict(r) for r in self.runs],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "History":
        hist = cls(
            mode=data.get("mode", "unknown"),
            algo=data.get("algo", ""),
            seed_base=int(data.get("seed_base", 0)),
            goal_pct=float(data.get("goal_pct", 95.0)),
            created=data.get("created", ""),
        )
        for rd in data.get("runs", []):
            rec = RunRecord(**{k: rd.get(k) for k in CSV_FIELDS})
            hist.runs.append(rec)
        hist.best_pct = float(data.get("best_pct", 0.0))
        if not hist.best_pct and hist.runs:
            hist.best_pct = max((r.best_pct for r in hist.runs), default=0.0)
        return hist

    def save(self, out_dir: Path) -> Path:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "history.json"
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        csv_path = out_dir / "history.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for rec in self.runs:
                writer.writerow(asdict(rec))
        return json_path

    @classmethod
    def load(cls, source: Path) -> "History":
        p = Path(source)
        if p.is_dir():
            p = p / "history.json"
        if not p.is_file():
            raise FileNotFoundError("history not found: %s" % p)
        with open(p, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))
