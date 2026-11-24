"""Experience replay buffer for DQN.

Stores transitions (state, action, reward, next_state, done) and samples
uniform random mini-batches for off-policy learning.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


class ReplayBuffer:
    """Fixed-size circular replay buffer."""

    def __init__(self, capacity: int = 1000, state_dim: int = 8) -> None:
        self.capacity = int(capacity)
        self.state_dim = int(state_dim)

        self.states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.actions = np.zeros(capacity, dtype=np.int64)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.next_states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=np.bool_)

        self._idx = 0
        self._size = 0

    def add(self, state, action, reward, next_state, done) -> None:
        i = self._idx
        self.states[i] = np.asarray(state, dtype=np.float32)
        self.actions[i] = int(action)
        self.rewards[i] = float(reward)
        self.next_states[i] = np.asarray(next_state, dtype=np.float32)
        self.dones[i] = bool(done)

        self._idx = (i + 1) % self.capacity
        self._size = min(self._size + 1, self.capacity)

    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        if self._size == 0:
            raise ValueError("Replay buffer is empty")
        batch_size = min(batch_size, self._size)
        idx = np.random.choice(self._size, size=batch_size, replace=False)
        return (
            self.states[idx],
            self.actions[idx],
            self.rewards[idx],
            self.next_states[idx],
            self.dones[idx],
        )

    def __len__(self) -> int:
        return self._size


__all__ = ["ReplayBuffer"]
