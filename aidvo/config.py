"""
Configuration loading and boundary action-space decoding for AId-VO.

All project-specific knowledge (tests, boundary knobs, command templates,
observation regexes, reward weights) comes from the YAML config file.  The
Python code here never opens any HDL/HVL source file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConfigError(RuntimeError):
    """Raised when the AId-VO configuration is missing or inconsistent."""


class Config:
    """Thin typed wrapper around ``config/aidvo_config.yaml``."""

    def __init__(self, data: Dict[str, Any], repo_root: Path, path: Optional[Path] = None):
        if not isinstance(data, dict):
            raise ConfigError("configuration root must be a mapping")
        self.data = data
        self.repo_root = Path(repo_root).resolve()
        self.path = path
        if "knobs" not in data or not data["knobs"]:
            raise ConfigError("configuration must define a non-empty 'knobs' list")
        for knob in data["knobs"]:
            if "name" not in knob or "kind" not in knob:
                raise ConfigError("every knob needs 'name' and 'kind'")
            if knob["kind"] not in ("seed", "uvm_test", "plusargs", "extra"):
                raise ConfigError(
                    "knob %r has unknown kind %r (expected seed|uvm_test|plusargs|extra)"
                    % (knob["name"], knob["kind"])
                )
            if knob["kind"] == "seed" and "buckets" not in knob:
                raise ConfigError("seed knob %r needs 'buckets'" % knob["name"])
            if knob["kind"] != "seed" and "values" not in knob:
                raise ConfigError("knob %r needs 'values'" % knob["name"])

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, path: str, repo_root: Optional[str] = None) -> "Config":
        p = Path(path).resolve()
        if not p.is_file():
            raise ConfigError("configuration file not found: %s" % p)
        with open(p, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        root = Path(repo_root).resolve() if repo_root else p.parent.parent
        return cls(data, root, p)

    # ----------------------------------------------------------- basic access
    @property
    def project(self) -> Dict[str, Any]:
        return self.data.get("project", {})

    @property
    def commands(self) -> Dict[str, Any]:
        return self.data.get("commands", {})

    @property
    def log_parse(self) -> Dict[str, str]:
        return self.data.get("log_parse", {})

    @property
    def coverage(self) -> Dict[str, Any]:
        return self.data.get("coverage", {})

    @property
    def coverage_mode(self) -> str:
        return str(self.coverage.get("mode", "transcript"))

    @property
    def goal_pct(self) -> float:
        return float(self.coverage.get("goal_pct", 95.0))

    def set_goal_pct(self, goal: float) -> None:
        self.data.setdefault("coverage", {})["goal_pct"] = float(goal)

    @property
    def env_cfg(self) -> Dict[str, Any]:
        return self.data.get("env", {})

    @property
    def reward_cfg(self) -> Dict[str, float]:
        return dict(self.env_cfg.get("reward", {}))

    @property
    def baseline_cfg(self) -> Dict[str, Any]:
        return self.data.get("baseline", {})

    @property
    def train_cfg(self) -> Dict[str, Any]:
        return self.data.get("train", {})

    @property
    def knobs(self) -> List[Dict[str, Any]]:
        return list(self.data["knobs"])

    @property
    def top(self) -> str:
        return str(self.project.get("top", "fifo_tb"))

    @property
    def testbench_root(self) -> Path:
        rel = str(self.project.get("testbench_root", "."))
        return (self.repo_root / rel).resolve()

    # ----------------------------------------------------------- action space
    def _cardinality(self, knob: Dict[str, Any]) -> int:
        if knob["kind"] == "seed":
            return int(knob["buckets"])
        return len(knob["values"])

    @property
    def knob_cardinalities(self) -> List[int]:
        return [self._cardinality(k) for k in self.knobs]

    @property
    def n_actions(self) -> int:
        n = 1
        for c in self.knob_cardinalities:
            n *= c
        return n

    def decode_action(self, index: int) -> Dict[str, Dict[str, Any]]:
        """Flat discrete action index -> per-knob {knob, index, value}."""
        index = int(index)
        if index < 0 or index >= self.n_actions:
            raise ValueError("action %d outside [0, %d)" % (index, self.n_actions))
        rem = index
        decoded: Dict[str, Dict[str, Any]] = {}
        for knob in self.knobs:
            card = self._cardinality(knob)
            k = rem % card
            rem //= card
            value = k if knob["kind"] == "seed" else knob["values"][k]
            decoded[knob["name"]] = {"knob": knob, "index": k, "value": value}
        return decoded

    # -------------------------------------------------- decoded action -> run
    def resolve_run(
        self, decoded: Dict[str, Dict[str, Any]], episode_index: int = 0
    ) -> Dict[str, Any]:
        """Translate decoded knob selections into simulation-boundary inputs.

        Returns dict with:
          seed        - simulator seed (int) or None when no seed knob exists
          plusargs    - list of ``+KEY=VALUE`` boundary plusargs
          extra       - list of raw extra run-option tokens
          labels      - human-readable labels per knob (for history records)
        """
        seed: Optional[int] = None
        plusargs: List[str] = []
        extra: List[str] = []
        labels: Dict[str, str] = {}

        for name, sel in decoded.items():
            knob = sel["knob"]
            kind = knob["kind"]
            if kind == "seed":
                base = int(knob.get("base", 0))
                stride = int(knob.get("stride", 1))
                offset = 0
                if knob.get("vary_by_episode", False):
                    offset = int(episode_index) * int(knob.get("episode_stride", 100000))
                seed = base + int(sel["value"]) * stride + offset
                labels[name] = str(seed)
            elif kind == "uvm_test":
                plusarg_name = str(knob.get("plusarg", "UVM_TESTNAME"))
                plusargs.append("+%s=%s" % (plusarg_name, sel["value"]))
                labels[name] = str(sel["value"])
            elif kind == "plusargs":
                for key, val in dict(sel["value"]).items():
                    plusargs.append("+%s=%s" % (key, val))
                labels[name] = ",".join("%s=%s" % kv for kv in dict(sel["value"]).items())
            elif kind == "extra":
                tokens = list(sel["value"])
                extra.extend(str(t) for t in tokens)
                labels[name] = " ".join(str(t) for t in tokens)

        if seed is None:
            seed = int(self.baseline_cfg.get("seed_base", 1)) + int(episode_index)
        return {"seed": seed, "plusargs": plusargs, "extra": extra, "labels": labels}

    # ----------------------------------------------------------- sanity check
    def describe(self) -> str:
        lines = [
            "AId-VO configuration summary",
            "  repository root : %s" % self.repo_root,
            "  testbench root  : %s" % self.testbench_root,
            "  top module      : %s" % self.top,
            "  coverage mode   : %s" % self.coverage_mode,
            "  coverage goal   : %.1f%%" % self.goal_pct,
            "  action space    : Discrete(%d)" % self.n_actions,
        ]
        for knob, card in zip(self.knobs, self.knob_cardinalities):
            lines.append("    - %-14s kind=%-9s cardinality=%d"
                         % (knob["name"], knob["kind"], card))
        tb_ok = self.testbench_root.is_dir()
        lines.append("  testbench dir exists: %s" % ("yes" if tb_ok else "NO"))
        lines.append("  coverage report regex: %s" % self.coverage.get("report_total_regex", ""))
        lines.append("  transcript coverage regex: %s" % self.log_parse.get("coverage_regex", ""))
        return "\n".join(lines)
