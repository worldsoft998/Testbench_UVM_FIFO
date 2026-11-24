"""Base class for local RL agents used by AId-UVO-RT."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from optimizer.utils.logger import get_logger


class BaseRLAgent:
    """Common interface for all RL algorithms.

    A concrete agent must implement:
      - select_action(state) -> int
      - update(state, action, reward, next_state, done) -> None
      - save(path) / load(path) for checkpointing
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        gamma: float = 0.95,
        lr: float = 0.01,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        seed: int = 42,
        name: str = "base",
    ) -> None:
        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)
        self.gamma = float(gamma)
        self.lr = float(lr)
        self.epsilon = float(epsilon)
        self.epsilon_decay = float(epsilon_decay)
        self.epsilon_min = float(epsilon_min)
        self.seed = int(seed)
        self.name = name

        self.rng = np.random.default_rng(self.seed)
        self.logger = get_logger(f"optimizer.rl.{name}")

        # Training statistics.
        self.episode_rewards: List[float] = []
        self.episode_coverages: List[float] = []
        self.update_count = 0

    # ------------------------------------------------------------------ #
    # Interface (subclasses must implement)
    # ------------------------------------------------------------------ #
    def select_action(self, state: np.ndarray, explore: bool = True) -> int:
        raise NotImplementedError

    def update(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool = False,
    ) -> None:
        raise NotImplementedError

    def save(self, path: str) -> None:
        raise NotImplementedError

    def load(self, path: str) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def record_episode(self, reward: float, coverage: float) -> None:
        self.episode_rewards.append(float(reward))
        self.episode_coverages.append(float(coverage))

    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "gamma": self.gamma,
            "lr": self.lr,
            "epsilon": self.epsilon,
            "updates": self.update_count,
            "episodes": len(self.episode_rewards),
            "avg_reward": float(np.mean(self.episode_rewards[-10:])) if self.episode_rewards else 0.0,
            "avg_coverage": float(np.mean(self.episode_coverages[-10:])) if self.episode_coverages else 0.0,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, state_dim={self.state_dim}, action_dim={self.action_dim})"


__all__ = ["BaseRLAgent"]
