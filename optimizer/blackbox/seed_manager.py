"""Seed & constraint manager for the blackbox optimizer.

Uses the local RL agent to pick a new seed / constraint bias based on the
coverage report from the previous run. All computation is local.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from optimizer.rl import DQNAgent, PPOAgent, QLearningAgent
from optimizer.rl.action_space import ActionSpace
from optimizer.rl.reward import RewardFunction
from optimizer.rl.state_encoder import StateEncoder
from optimizer.utils.logger import get_logger

logger = get_logger("optimizer.blackbox.seed_manager")


class SeedManager:
    """Selects seeds and constraint biases to close coverage faster.

    The RL state is built from the latest coverage report (unhit coverpoints,
    stalled fraction, coverage %). The RL action selects a seed bias strategy
    and a constraint adjustment, which are converted into plusargs for the
    next QuestaSim run.
    """

    def __init__(
        self,
        rl_algorithm: str = "dqn",
        coverage_goal: float = 100.0,
        state_dim: int = 8,
        seed: int = 42,
    ) -> None:
        self.rl_algorithm = rl_algorithm
        self.coverage_goal = float(coverage_goal)
        self.state_dim = int(state_dim)
        self.seed = int(seed)

        self.action_space = ActionSpace()
        self.state_encoder = StateEncoder(state_dim=state_dim)
        self.reward_fn = RewardFunction()
        self.agent = self._build_rl_agent()

        self.history: List[Dict[str, Any]] = []
        self._last_state: np.ndarray | None = None
        self._last_action: int | None = None

    def _build_rl_agent(self):
        common = dict(
            state_dim=self.state_dim,
            action_dim=self.action_space.num_actions,
            gamma=0.95,
            lr=0.01,
            epsilon=0.1,
            epsilon_decay=0.995,
            epsilon_min=0.01,
            seed=self.seed,
            name="blackbox-" + self.rl_algorithm,
        )
        if self.rl_algorithm == "qlearning":
            return QLearningAgent(**common)
        if self.rl_algorithm == "dqn":
            return DQNAgent(**common)
        if self.rl_algorithm == "ppo":
            return PPOAgent(**common)
        raise ValueError(f"Unknown RL algorithm: {self.rl_algorithm}")

    def encode_state(self, report: Dict[str, Any]) -> np.ndarray:
        obs = {
            "coverage_pct": float(report.get("total_coverage", 0.0)),
            "hit_coverpoints": 0,
            "total_coverpoints": 0,
            "hit_ratio": 0.0,
            "stalled_coverpoints": 0.0,
            "stalled": 0.0,
            "wfull": 0.0,
            "rempty": 0.0,
            "recent_transitions": 0.0,
            "time_budget_remaining": 1.0,
        }
        # Derive stalled fraction from unhit ratio as a proxy.
        total = report.get("total_coverpoints") or 1
        unhit = len(report.get("unhit", []))
        obs["stalled_coverpoints"] = min(1.0, unhit / total)
        obs["stalled"] = obs["stalled_coverpoints"]
        obs["hit_ratio"] = 1.0 - obs["stalled_coverpoints"]
        return self.state_encoder.encode(obs)

    def next_seed_and_constraints(
        self, report: Dict[str, Any], prev_reward: float = 0.0
    ) -> Dict[str, Any]:
        """Return the next seed and constraint plusargs.

        Also records the transition for RL learning (uses previous state/action
        if available).
        """
        state = self.encode_state(report)

        # Learn from previous transition.
        if self._last_state is not None and self._last_action is not None:
            self.agent.update(self._last_state, self._last_action, float(prev_reward),
                              state, done=False)

        # Select next action.
        action_idx = int(self.agent.select_action(state, explore=True))
        command = self.action_space.to_command(action_idx)

        # Derive a concrete seed.
        seed = self._derive_seed(action_idx)

        self._last_state = state
        self._last_action = action_idx

        decision = {
            "seed": int(seed),
            "action": command.get("action", "no_op"),
            "action_index": action_idx,
            "constraints": {k: v for k, v in command.items()
                            if k not in ("action", "action_index")},
            "coverage_pct": report.get("total_coverage", 0.0),
        }
        self.history.append(dict(decision))
        logger.info("SeedManager: seed=%d action=%s coverage=%.2f%%",
                    decision["seed"], decision["action"], decision["coverage_pct"])
        return decision

    def _derive_seed(self, action_idx: int) -> int:
        # Deterministic-but-varied seed derived from action index and base seed.
        return (self.seed * 1000003 + action_idx * 7919 + len(self.history)) % (2 ** 31)

    def plusargs(self, decision: Dict[str, Any]) -> List[str]:
        """Convert a decision into QuestaSim plusargs."""
        args: List[str] = [f"+ntb_random_seed={decision['seed']}"]
        c = decision.get("constraints", {})
        if "winc_bias" in c:
            args.append(f"+winc_bias={c['winc_bias']}")
        if "rinc_bias" in c:
            args.append(f"+rinc_bias={c['rinc_bias']}")
        if "burst_length_bias" in c:
            args.append(f"+burst_length_bias={c['burst_length_bias']}")
        if "clock_ratio" in c:
            args.append(f"+clock_ratio={c['clock_ratio']}")
        if command_reseed := c.get("reseed"):
            args.append(f"+reseed={int(command_reseed)}")
        if decision["action"] == "focus_write_full_corner":
            args.append("+focus_corner=wfull")
        if decision["action"] == "focus_read_empty_corner":
            args.append("+focus_corner=rempty")
        return args

    def save(self, path: str) -> None:
        self.agent.save(path)

    def load(self, path: str) -> None:
        self.agent.load(path)


__all__ = ["SeedManager"]
