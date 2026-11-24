"""Loop controller for the blackbox optimizer.

Runs repeated QuestaSim simulations, parses their logs/reports, and feeds the
results back to the SeedManager to adjust seeds/constraints for the next loop.

Simulation launching is via subprocess (vsim). This code is NOT executed during
repository creation — it runs only when the user invokes the batch files / CLI.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, List, Optional

from optimizer.config import CFG
from optimizer.utils.logger import get_logger
from optimizer.utils.io import write_csv, ensure_dir
from optimizer.blackbox.seed_manager import SeedManager
from optimizer.blackbox.log_parser import parse_log
from optimizer.blackbox.report_parser import parse_report, unhit_coverpoints

logger = get_logger("optimizer.blackbox.loop_controller")


class LoopController:
    """Controls the blackbox optimization loop."""

    def __init__(
        self,
        rl_algorithm: str = "dqn",
        ai_on: bool = True,
        coverage_goal: float = 100.0,
        max_runs: int = 10,
        output_dir: str = "results/blackbox",
        vlog_cmd: str = "vlog",
        vsim_cmd: str = "vsim",
        compile_do: str = "sim/Questa/do_files/compile.do",
        run_do: str = "sim/Questa/do_files/run_blackbox.do",
        sim_log: str = "sim.log",
        coverage_report: str = "coverage_report.txt",
        coverage_db: str = "coverage.ucdb",
        top_level: str = "work.tb_top_blackbox",
    ) -> None:
        self.rl_algorithm = rl_algorithm
        self.ai_on = ai_on
        self.coverage_goal = float(coverage_goal)
        self.max_runs = int(max_runs)
        self.output_dir = output_dir
        self.vlog_cmd = vlog_cmd
        self.vsim_cmd = vsim_cmd
        self.compile_do = compile_do
        self.run_do = run_do
        self.sim_log = sim_log
        self.coverage_report = coverage_report
        self.coverage_db = coverage_db

        self.seed_manager = SeedManager(
            rl_algorithm=rl_algorithm,
            coverage_goal=coverage_goal,
            seed=CFG.fixed_seed,
        )
        self.loop_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Compile once
    # ------------------------------------------------------------------ #
    def compile(self) -> bool:
        logger.info("Compiling RTL + TB via %s", self.compile_do)
        if not os.path.isfile(self.compile_do):
            logger.warning("compile.do not found: %s (skipping compile)", self.compile_do)
            return True
        cmd = [self.vlog_cmd, "-f", self.compile_do]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if res.returncode != 0:
                logger.error("Compile failed:\n%s", res.stderr[-2000:])
                return False
            logger.info("Compile OK")
            return True
        except Exception as exc:
            logger.error("Compile exception: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    # Single run
    # ------------------------------------------------------------------ #
    def run_once(self, plusargs: List[str], work_dir: str) -> Dict[str, Any]:
        """Run one QuestaSim simulation with the given plusargs."""
        cmd = [self.vsim_cmd, "-c", "-do", self.run_do] + plusargs
        logger.info("Launching: %s", " ".join(cmd))
        start = time.time()
        try:
            res = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True,
                                 timeout=600)
        except subprocess.TimeoutExpired:
            logger.error("Simulation timed out")
            return {"clean": False, "errors": 1, "fatals": 1, "coverage_pct": 0.0,
                    "wall_time_s": 600.0, "plusargs": plusargs}
        wall = time.time() - start

        # Parse artifacts (relative to work_dir).
        log = parse_log(os.path.join(work_dir, self.sim_log))
        report = parse_report(os.path.join(work_dir, self.coverage_report))

        result = {
            "clean": log.get("clean", False),
            "errors": log.get("errors", 0),
            "fatals": log.get("fatals", 0),
            "warnings": log.get("warnings", 0),
            "coverage_pct": report.get("total_coverage", 0.0),
            "sim_time": log.get("sim_time"),
            "wall_time_s": round(wall, 4),
            "plusargs": plusargs,
            "top_level": self.top_level,
            "unhit": unhit_coverpoints(report),
        }
        logger.info("Run done: coverage=%.2f%% clean=%s wall=%.2fs",
                    result["coverage_pct"], result["clean"], result["wall_time_s"])
        return result

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        ensure_dir(self.output_dir)
        logger.info("Blackbox loop starting (rl=%s, ai=%s, goal=%.1f%%, max_runs=%d)",
                    self.rl_algorithm, self.ai_on, self.coverage_goal, self.max_runs)

        # Compile once.
        if not self.compile():
            logger.error("Compilation failed; aborting blackbox loop")
            return

        work_dir = os.path.abspath(".")
        prev_report: Dict[str, Any] = {"total_coverage": 0.0, "unhit": []}
        prev_reward = 0.0

        for loop in range(1, self.max_runs + 1):
            logger.info("=== Blackbox loop %d/%d ===", loop, self.max_runs)

            if self.ai_on:
                decision = self.seed_manager.next_seed_and_constraints(prev_report, prev_reward)
                plusargs = self.seed_manager.plusargs(decision)
            else:
                decision = {"seed": CFG.fixed_seed + loop, "action": "no_op",
                            "action_index": 0, "constraints": {}}
                plusargs = [f"+ntb_random_seed={decision['seed']}"]

            result = self.run_once(plusargs, work_dir)
            result["loop"] = loop
            result["decision"] = decision
            self.loop_history.append(result)

            prev_report = {
                "total_coverage": result["coverage_pct"],
                "unhit": result["unhit"],
            }
            prev_reward = result["coverage_pct"] - (prev_report["total_coverage"] if loop > 1 else 0.0)

            if result["coverage_pct"] >= self.coverage_goal:
                logger.info("Coverage goal reached (%.2f%%)", result["coverage_pct"])
                break

        self._write_summaries()
        logger.info("Blackbox loop finished %d loops", len(self.loop_history))

    # ------------------------------------------------------------------ #
    # Output
    # ------------------------------------------------------------------ #
    def _write_summaries(self) -> None:
        ensure_dir(self.output_dir)
        rows = []
        for entry in self.loop_history:
            rows.append({
                "loop": entry["loop"],
                "seed": entry["decision"].get("seed"),
                "action": entry["decision"].get("action"),
                "coverage_pct": round(entry["coverage_pct"], 4),
                "goal_reached": entry["coverage_pct"] >= self.coverage_goal,
                "clean": entry["clean"],
                "errors": entry["errors"],
                "fatals": entry["fatals"],
                "wall_time_s": entry["wall_time_s"],
                "plusargs": " ".join(entry["plusargs"]),
            })
        write_csv(os.path.join(self.output_dir, "run_summary.csv"), rows,
                  fieldnames=["loop", "seed", "action", "coverage_pct", "goal_reached",
                              "clean", "errors", "fatals", "wall_time_s", "plusargs"])
        write_csv(os.path.join(self.output_dir, "blackbox_loop.csv"), self.loop_history,
                  fieldnames=["loop", "coverage_pct", "clean", "errors", "fatals",
                              "wall_time_s", "unhit", "plusargs", "decision"])
        model_path = os.path.join(self.output_dir, "model.npz")
        try:
            self.seed_manager.save(model_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Could not save RL model: %s", exc)

    def stats(self) -> Dict[str, Any]:
        return {
            "mode": "blackbox",
            "rl_algorithm": self.rl_algorithm,
            "loops": self.loop_history,
            "final_coverage": self.loop_history[-1]["coverage_pct"] if self.loop_history else 0.0,
        }


__all__ = ["LoopController"]
