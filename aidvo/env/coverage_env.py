"""
Gymnasium environment: the AId-VO RL problem definition.

One environment step == one boundary simulation:

    action  -> decode boundary knobs (seed bucket, test selection, clock
               profile, ...) into simulator run options
    step    -> run the simulator as a black box, parse ONLY scalar coverage
               percentages + UVM report-summary counts from the transcript
    reward  -> positive for coverage increments and valid runs, negative for
               UVM errors/warnings, stagnation and (small) wall-clock cost

Observation is a fixed-size vector of normalized scalars - no coverage-model
structure, no testbench internals, no DUT signals are ever observed.

The AI decision happens between simulations: its latency is accounted
separately (decision_time) and adds ZERO delay inside simulated time.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from ..boundary.runner import SimResult, SimRunner
from ..config import Config

OBS_DIM = 10


class AidvoCoverageEnv(gym.Env):
    """Black-box coverage-closure environment for any boundary-steerable TB."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        cfg: Config,
        mode: str = "train",
        worker_id: int = 0,
        run_root: Optional[Path] = None,
    ):
        super().__init__()
        self.cfg = cfg
        self.mode = mode
        self.worker_id = worker_id
        self.runner = SimRunner(cfg)

        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBS_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(cfg.n_actions)

        root = Path(run_root) if run_root else (
            cfg.repo_root / "results" / "runs" / mode
        )
        self.run_root = Path(root)

        self.max_steps = int(cfg.env_cfg.get("max_steps_per_episode", 24))
        self.stag_window = max(1, int(cfg.env_cfg.get("stagnation_window", 4)))
        self.time_ref = max(1e-6, float(cfg.env_cfg.get("time_reference_s", 60.0)))
        self.reward_cfg = cfg.reward_cfg
        self.goal_pct = cfg.goal_pct

        # Knob slots exposed in the observation (non-seed knobs, up to two).
        self._obs_knobs = [k for k in cfg.knobs if k["kind"] != "seed"][:2]

        # Episode state
        self._episode = 0
        self._steps = 0
        self._best = 0.0
        self._last_cov = 0.0
        self._delta = 0.0
        self._stagnation = 0
        self._last_obs_knob_idx = [0.0, 0.0]
        self._episode_dir: Path = Path(".")
        self._merged_ucdb: Optional[Path] = None
        self._last_result: Optional[SimResult] = None
        self._last_errors = 0
        self._last_warnings = 0
        self._last_wall = 0.0
        self._last_valid = True

    # ------------------------------------------------------------------ utils
    def _zero_obs(self) -> np.ndarray:
        return np.zeros(OBS_DIM, dtype=np.float32)

    def _obs(self) -> np.ndarray:
        vec = np.zeros(OBS_DIM, dtype=np.float32)
        vec[0] = min(self._best / 100.0, 1.0)
        vec[1] = min(self._last_cov / 100.0, 1.0)
        vec[2] = min(self._delta / 100.0, 1.0)
        vec[3] = min(self._stagnation, self.stag_window) / float(self.stag_window)
        vec[4] = min(self._last_errors, 20) / 20.0
        vec[5] = min(self._last_warnings, 50) / 50.0
        vec[6] = min(self._last_wall, self.time_ref) / self.time_ref
        vec[7] = self._last_obs_knob_idx[0]
        vec[8] = self._last_obs_knob_idx[1]
        vec[9] = min(self._steps, self.max_steps) / float(self.max_steps)
        return vec

    def _knob_idx_norm(self, decoded: Dict[str, Dict[str, Any]]) -> list:
        out = [0.0, 0.0]
        for i, knob in enumerate(self._obs_knobs[:2]):
            sel = decoded.get(knob["name"])
            if sel is None:
                continue
            card = self.cfg._cardinality(knob)
            out[i] = float(sel["index"]) / float(card - 1) if card > 1 else 0.0
        return out

    def _label(self, resolved: Dict[str, Any], decoded: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
        test = "-"
        for name, sel in decoded.items():
            if sel["knob"]["kind"] == "uvm_test":
                test = str(sel["value"])
        labels = resolved.get("labels", {})
        profile = labels.get("clock_profile") or ",".join(
            v for k, v in labels.items() if k != "test"
        )
        return test, profile

    # ------------------------------------------------------------ ucdb merge
    def _update_merged_coverage(self, run_dir: Path) -> Optional[float]:
        run_ucdb = run_dir / "aidvo_last_run.ucdb"
        if not run_ucdb.is_file():
            return None
        if self._merged_ucdb is None:
            first = self._episode_dir / "merged.ucdb"
            shutil.copyfile(run_ucdb, first)
            self._merged_ucdb = first
        else:
            tmp = self._episode_dir / "merged_tmp.ucdb"
            if not self.runner.merge_ucdb(tmp, [self._merged_ucdb, run_ucdb]):
                return None
            tmp.replace(self._merged_ucdb)
        return self.runner.report_total(self._merged_ucdb, self._episode_dir / "cov_report.txt")

    # ---------------------------------------------------------------- gym api
    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        super().reset(seed=seed)
        options = options or {}
        self._episode += 1
        self._steps = 0
        self._best = 0.0
        self._last_cov = 0.0
        self._delta = 0.0
        self._stagnation = 0
        self._last_obs_knob_idx = [0.0, 0.0]
        self._last_errors = 0
        self._last_warnings = 0
        self._last_wall = 0.0
        self._last_valid = True
        self._merged_ucdb = None
        self._last_result = None
        if "max_steps" in options:
            self.max_steps = int(options["max_steps"])

        stamp = time.strftime("%Y%m%d_%H%M%S")
        self._episode_dir = (
            self.run_root / ("%s_w%02d" % (stamp, self.worker_id)) / ("ep_%03d" % self._episode)
        )
        self._episode_dir.mkdir(parents=True, exist_ok=True)
        return self._zero_obs(), {"goal_pct": self.goal_pct}

    def step(self, action: int):
        self._steps += 1
        rc = self.reward_cfg
        decoded = self.cfg.decode_action(int(action))
        resolved = self.cfg.resolve_run(decoded, episode_index=self._episode)
        test, profile = self._label(resolved, decoded)

        run_dir = self._episode_dir / ("run_%03d" % self._steps)
        result = self.runner.run(
            run_dir,
            seed=int(resolved["seed"]),
            plusargs=resolved["plusargs"],
            extra=resolved["extra"],
        )
        self._last_result = result

        # ---- resolve the scalar coverage for this step (transcript or ucdb)
        cov: Optional[float]
        if self.cfg.coverage_mode == "ucdb":
            cov = self._update_merged_coverage(run_dir)
            if cov is None:
                cov = result.stats.coverage_pct
        else:
            cov = result.stats.coverage_pct

        errors = result.stats.uvm_errors
        warnings = result.stats.uvm_warnings
        fatals = result.stats.uvm_fatals or 0
        valid = result.valid and cov is not None

        # ---- coverage bookkeeping (monotone best-so-far)
        prev_best = self._best
        if cov is not None:
            self._last_cov = float(cov)
            self._best = max(self._best, float(cov))
        delta = max(0.0, self._best - prev_best)
        self._delta = delta
        self._stagnation = 0 if delta > 1e-9 else self._stagnation + 1

        # ---- reward: positive for coverage gains & valid runs
        reward = float(rc.get("coverage_gain_weight", 1.0)) * delta
        reward -= float(rc.get("error_penalty", 2.0)) * int(errors or 0)
        reward -= float(rc.get("warning_penalty", 0.05)) * int(warnings or 0)
        reward -= float(rc.get("fatal_penalty", 10.0)) * fatals
        reward -= float(rc.get("time_penalty", 0.2)) * min(
            result.wall_time_s / self.time_ref, 1.0
        )
        if valid:
            reward += float(rc.get("valid_bonus", 0.1))
        else:
            reward -= float(rc.get("invalid_penalty", 5.0))
        if self._stagnation > 0:
            reward -= float(rc.get("stagnation_penalty", 0.3))

        # ---- episode termination
        terminated = self._best >= self.goal_pct
        if terminated:
            reward += float(rc.get("goal_bonus", 30.0))
        truncated = (not terminated) and self._steps >= self.max_steps

        # ---- state for the next observation
        self._last_errors = int(errors or 0) + 5 * fatals
        self._last_warnings = int(warnings or 0)
        self._last_wall = result.wall_time_s
        self._last_valid = valid
        self._last_obs_knob_idx = self._knob_idx_norm(decoded)

        info = {
            "run": self._steps,
            "test": test,
            "profile": profile,
            "seed": resolved["seed"],
            "coverage_pct": cov,
            "best_pct": self._best,
            "delta_pct": delta,
            "uvm_errors": errors,
            "uvm_warnings": warnings,
            "valid": valid,
            "wall_time_s": result.wall_time_s,
            "sim_time_ns": result.stats.sim_time_ns,
            "reward": float(reward),
            "run_dir": str(run_dir),
        }
        return self._obs(), float(reward), bool(terminated), bool(truncated), info

    def close(self):
        return None
