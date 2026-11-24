"""Blackbox agent: post-run analysis + RL-guided seed/constraint adjustment."""

from __future__ import annotations

from typing import Any, Dict

from optimizer.config import CFG
from optimizer.utils.logger import get_logger
from optimizer.blackbox.loop_controller import LoopController

logger = get_logger("optimizer.blackbox.agent")


class BlackboxAgent:
    """Blackbox optimizer agent.

    Treats the simulator as a blackbox: after each run it parses logs/reports,
    uses the local RL agent to pick a new seed/constraint, and launches the
    next run. Loops until the coverage goal or run budget is met.
    """

    def __init__(
        self,
        rl_algorithm: str = "dqn",
        ai_on: bool = True,
        coverage_goal: float = 100.0,
        max_runs: int = 10,
        output_dir: str = "results/blackbox",
        **kwargs,
    ) -> None:
        self.rl_algorithm = rl_algorithm
        self.ai_on = ai_on
        self.coverage_goal = float(coverage_goal)
        self.max_runs = int(max_runs)
        self.output_dir = output_dir

        self.controller = LoopController(
            rl_algorithm=rl_algorithm,
            ai_on=ai_on,
            coverage_goal=coverage_goal,
            max_runs=max_runs,
            output_dir=output_dir,
            **kwargs,
        )

    def run(self) -> None:
        logger.info("Blackbox agent starting (rl=%s, ai=%s, goal=%.1f%%)",
                    self.rl_algorithm, self.ai_on, self.coverage_goal)
        self.controller.run()
        logger.info("Blackbox agent finished")

    def stats(self) -> Dict[str, Any]:
        return self.controller.stats()


__all__ = ["BlackboxAgent"]
