"""Tabular Q-learning agent.

Suitable for small discrete action spaces. Q-values are stored in a dict keyed
by a discretized state representation.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np

from optimizer.rl.base_agent import BaseRLAgent


def _state_key(state: np.ndarray) -> Tuple[int, ...]:
    """Discretize a continuous state vector into a hashable key."""
    # Discretize each feature into 8 bins.
    bins = np.clip(np.round(np.asarray(state, dtype=np.float64) * 8.0).astype(int), 0, 8)
    return tuple(int(b) for b in bins)


class QLearningAgent(BaseRLAgent):
    """Tabular Q-learning with epsilon-greedy exploration."""

    def __init__(self, state_dim: int, action_dim: int, **kwargs) -> None:
        super().__init__(state_dim=state_dim, action_dim=action_dim, **kwargs)
        self.q_table: Dict[Tuple[int, ...], np.ndarray] = {}

    def _get_q(self, state_key: Tuple[int, ...]) -> np.ndarray:
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_dim, dtype=np.float64)
        return self.q_table[state_key]

    def select_action(self, state: np.ndarray, explore: bool = True) -> int:
        state_key = _state_key(state)
        q = self._get_q(state_key)
        if explore and self.rng.random() < self.epsilon:
            return int(self.rng.integers(0, self.action_dim))
        return int(np.argmax(q))

    def update(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool = False,
    ) -> None:
        s_key = _state_key(state)
        s_next_key = _state_key(next_state)

        q_current = self._get_q(s_key)[action]
        q_next = np.max(self._get_q(s_next_key)) if not done else 0.0

        target = float(reward) + self.gamma * q_next
        self._get_q(s_key)[action] += self.lr * (target - q_current)

        self.update_count += 1
        if done:
            self.decay_epsilon()

    def save(self, path: str) -> None:
        import pickle
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        data = {
            "q_table": {k: v.tolist() for k, v in self.q_table.items()},
            "epsilon": self.epsilon,
            "update_count": self.update_count,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        self.logger.info("Q-table saved to %s (%d states)", path, len(self.q_table))

    def load(self, path: str) -> None:
        import pickle
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.q_table = {tuple(k): np.array(v, dtype=np.float64) for k, v in data.get("q_table", {}).items()}
        self.epsilon = float(data.get("epsilon", self.epsilon_min))
        self.update_count = int(data.get("update_count", 0))
        self.logger.info("Q-table loaded from %s (%d states)", path, len(self.q_table))

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        s["q_table_size"] = len(self.q_table)
        return s


__all__ = ["QLearningAgent", "_state_key"]
