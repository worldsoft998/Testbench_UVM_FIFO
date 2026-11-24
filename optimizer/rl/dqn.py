"""Deep Q-Network (DQN) implemented purely with numpy.

A small multi-layer perceptron with one hidden layer, ReLU activations, and a
separate target network. Trained via experience replay. Fully local — no
TensorFlow / PyTorch / external AI APIs.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import numpy as np

from optimizer.rl.base_agent import BaseRLAgent
from optimizer.rl.replay_buffer import ReplayBuffer


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


def _relu_grad(z1: np.ndarray) -> np.ndarray:
    return (z1 > 0).astype(np.float32)


class _MLP:
    """Two-layer MLP: state -> hidden (ReLU) -> Q-values (linear)."""

    def __init__(self, state_dim: int, action_dim: int, hidden: int = 32, rng=None) -> None:
        self.rng = rng or np.random.default_rng(0)
        self.W1 = self.rng.normal(0.0, np.sqrt(2.0 / state_dim), size=(state_dim, hidden)).astype(np.float32)
        self.b1 = np.zeros(hidden, dtype=np.float32)
        self.W2 = self.rng.normal(0.0, np.sqrt(2.0 / hidden), size=(hidden, action_dim)).astype(np.float32)
        self.b2 = np.zeros(action_dim, dtype=np.float32)

    def forward(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32)
        z1 = x @ self.W1 + self.b1
        h = _relu(z1)
        q = h @ self.W2 + self.b2
        return q

    def backward(self, x: np.ndarray, h: np.ndarray, dq: np.ndarray, lr: float) -> None:
        # dq: gradient of loss w.r.t. Q output, shape (action_dim,)
        dW2 = np.outer(h, dq)
        db2 = dq.copy()

        dhidden = dq @ self.W2.T
        dz1 = dhidden * _relu_grad(x @ self.W1 + self.b1)
        dW1 = np.outer(x, dz1)
        db1 = dz1.copy()

        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W1 -= lr * dW1
        self.b1 -= lr * db1

    def get_weights(self) -> Dict[str, np.ndarray]:
        return {"W1": self.W1.copy(), "b1": self.b1.copy(), "W2": self.W2.copy(), "b2": self.b2.copy()}

    def set_weights(self, weights: Dict[str, np.ndarray]) -> None:
        self.W1 = weights["W1"].copy()
        self.b1 = weights["b1"].copy()
        self.W2 = weights["W2"].copy()
        self.b2 = weights["b2"].copy()


class DQNAgent(BaseRLAgent):
    """Deep Q-Network with experience replay and a target network."""

    def __init__(self, state_dim: int, action_dim: int, **kwargs) -> None:
        hidden = int(kwargs.pop("hidden", 32))
        buffer_size = int(kwargs.pop("buffer_size", 1000))
        batch_size = int(kwargs.pop("batch_size", 32))
        target_update = int(kwargs.pop("target_update", 50))
        super().__init__(state_dim=state_dim, action_dim=action_dim, **kwargs)

        self.hidden = hidden
        self.buffer_size = buffer_size
        self.batch_size = batch_size
        self.target_update = target_update

        self.q_net = _MLP(state_dim, action_dim, hidden=hidden, rng=self.rng)
        self.target_net = _MLP(state_dim, action_dim, hidden=hidden, rng=self.rng)
        self.target_net.set_weights(self.q_net.get_weights())

        self.buffer = ReplayBuffer(capacity=buffer_size, state_dim=state_dim)

        # Per-step bookkeeping.
        self._last_state: np.ndarray | None = None
        self._last_action: int | None = None
        self._steps_since_target_update = 0

    def select_action(self, state: np.ndarray, explore: bool = True) -> int:
        state = np.asarray(state, dtype=np.float32)
        q = self.q_net.forward(state)
        if explore and self.rng.random() < self.epsilon:
            action = int(self.rng.integers(0, self.action_dim))
        else:
            action = int(np.argmax(q))

        self._last_state = state
        self._last_action = action
        return action

    def observe(
        self,
        reward: float,
        next_state: np.ndarray,
        done: bool = False,
    ) -> None:
        """Store the last transition and optionally learn from a batch."""
        if self._last_state is None or self._last_action is None:
            return
        next_state = np.asarray(next_state, dtype=np.float32)
        self.buffer.add(self._last_state, self._last_action, float(reward), next_state, bool(done))
        self._last_state = next_state
        self._last_action = None

        if len(self.buffer) >= self.batch_size:
            self._replay()

        if done:
            self.decay_epsilon()
            self._steps_since_target_update = 0
        else:
            self._steps_since_target_update += 1
            if self._steps_since_target_update >= self.target_update:
                self.target_net.set_weights(self.q_net.get_weights())
                self._steps_since_target_update = 0

    def update(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool = False,
    ) -> None:
        """Convenience wrapper matching BaseRLAgent.update."""
        self.observe(reward, next_state, done)

    def _replay(self) -> None:
        states, actions, rewards, next_states, dones = self.buffer.sample(self.batch_size)

        q_current = np.array(
            [self.q_net.forward(s)[int(a)] for s, a in zip(states, actions)],
            dtype=np.float32,
        )
        q_next = np.array(
            [np.max(self.target_net.forward(ns)) for ns in next_states],
            dtype=np.float32,
        )
        targets = rewards + (1.0 - dones.astype(np.float32)) * self.gamma * q_next

        for i in range(states.shape[0]):
            dq = np.zeros(self.action_dim, dtype=np.float32)
            dq[int(actions[i])] = 2.0 * (q_current[i] - targets[i])
            s = states[i]
            h = _relu(s @ self.q_net.W1 + self.q_net.b1)
            self.q_net.backward(s, h, dq, self.lr)

        self.update_count += 1

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        q = self.q_net.get_weights()
        t = self.target_net.get_weights()
        flat = {}
        for k, v in q.items():
            flat[f"q_{k}"] = v
        for k, v in t.items():
            flat[f"target_{k}"] = v
        flat["epsilon"] = np.array(self.epsilon)
        flat["update_count"] = np.array(self.update_count)
        np.savez(path, **flat)
        self.logger.info("DQN saved to %s", path)

    def load(self, path: str) -> None:
        data = np.load(path, allow_pickle=True)
        q_keys = ["W1", "b1", "W2", "b2"]
        self.q_net.set_weights({k: data[f"q_{k}"] for k in q_keys if f"q_{k}" in data})
        if all(f"target_{k}" in data for k in q_keys):
            self.target_net.set_weights({k: data[f"target_{k}"] for k in q_keys})
        else:
            self.target_net.set_weights(self.q_net.get_weights())
        if "epsilon" in data:
            self.epsilon = float(data["epsilon"])
        if "update_count" in data:
            self.update_count = int(data["update_count"])
        self.logger.info("DQN loaded from %s", path)

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        s["buffer_size"] = len(self.buffer)
        s["hidden"] = self.hidden
        return s


__all__ = ["DQNAgent", "_MLP"]
