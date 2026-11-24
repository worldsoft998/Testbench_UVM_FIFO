"""Proximal Policy Optimization (PPO) — local, pure-numpy implementation.

An actor-critic method: a categorical policy network (actor) and a value
network (critic). Updated with the clipped surrogate objective over collected
trajectories. Fully local — no external AI APIs.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import numpy as np

from optimizer.rl.base_agent import BaseRLAgent


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


def _softmax(logits: np.ndarray) -> np.ndarray:
    logits = logits - np.max(logits)
    e = np.exp(logits)
    return e / np.sum(e)


def _categorical_sample(probs: np.ndarray, rng: np.random.Generator) -> int:
    return int(rng.choice(len(probs), p=probs))


class _PPOMLP:
    """Shared-architecture MLP used by both actor and critic heads."""

    def __init__(self, state_dim: int, out_dim: int, hidden: int = 32, rng=None) -> None:
        self.rng = rng or np.random.default_rng(0)
        self.W1 = self.rng.normal(0.0, np.sqrt(2.0 / state_dim), size=(state_dim, hidden)).astype(np.float32)
        self.b1 = np.zeros(hidden, dtype=np.float32)
        self.W2 = self.rng.normal(0.0, np.sqrt(2.0 / hidden), size=(hidden, out_dim)).astype(np.float32)
        self.b2 = np.zeros(out_dim, dtype=np.float32)
        self._x = None
        self._hidden = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32)
        self._x = x
        self._hidden = _relu(x @ self.W1 + self.b1)
        return self._hidden @ self.W2 + self.b2

    def get_weights(self) -> Dict[str, np.ndarray]:
        return {"W1": self.W1.copy(), "b1": self.b1.copy(), "W2": self.W2.copy(), "b2": self.b2.copy()}

    def set_weights(self, weights: Dict[str, np.ndarray]) -> None:
        self.W1 = weights["W1"].copy()
        self.b1 = weights["b1"].copy()
        self.W2 = weights["W2"].copy()
        self.b2 = weights["b2"].copy()


class PPOAgent(BaseRLAgent):
    """PPO agent with a categorical actor and a scalar critic."""

    def __init__(self, state_dim: int, action_dim: int, **kwargs) -> None:
        hidden = int(kwargs.pop("hidden", 32))
        clip_eps = float(kwargs.pop("clip_eps", 0.2))
        ent_coef = float(kwargs.pop("ent_coef", 0.01))
        vf_coef = float(kwargs.pop("vf_coef", 0.5))
        epochs = int(kwargs.pop("epochs", 4))
        super().__init__(state_dim=state_dim, action_dim=action_dim, **kwargs)

        self.hidden = hidden
        self.clip_eps = clip_eps
        self.ent_coef = ent_coef
        self.vf_coef = vf_coef
        self.epochs = epochs

        self.actor = _PPOMLP(state_dim, action_dim, hidden=hidden, rng=self.rng)
        self.critic = _PPOMLP(state_dim, 1, hidden=hidden, rng=self.rng)

        # Trajectory buffer for the current rollout.
        self.states: List[np.ndarray] = []
        self.actions: List[int] = []
        self.rewards: List[float] = []
        self.values: List[float] = []
        self.logps: List[float] = []
        self.dones: List[bool] = []

    def select_action(self, state: np.ndarray, explore: bool = True) -> int:
        state = np.asarray(state, dtype=np.float32)
        logits = self.actor.forward(state)
        probs = _softmax(logits)
        value = float(self.critic.forward(state)[0])

        if explore:
            action = _categorical_sample(probs, self.rng)
        else:
            action = int(np.argmax(probs))

        logp = float(np.log(probs[action] + 1e-12))

        self._last_state = state
        self._last_action = action
        self._last_logp = logp
        self._last_value = value
        return action

    def observe(
        self,
        reward: float,
        next_state: np.ndarray,
        done: bool = False,
    ) -> None:
        if not hasattr(self, "_last_state") or self._last_state is None:
            return
        self.states.append(self._last_state)
        self.actions.append(self._last_action)
        self.rewards.append(float(reward))
        self.values.append(self._last_value)
        self.logps.append(self._last_logp)
        self.dones.append(bool(done))
        self._last_state = np.asarray(next_state, dtype=np.float32)

        if done:
            self._learn()
            self.decay_epsilon()
            self._clear_trajectory()

    def _clear_trajectory(self) -> None:
        self.states, self.actions, self.rewards = [], [], []
        self.values, self.logps, self.dones = [], [], []
        self._last_state = None
        self._last_action = None
        self._last_logp = 0.0
        self._last_value = 0.0

    def _compute_returns(self) -> np.ndarray:
        rewards = np.array(self.rewards, dtype=np.float32)
        dones = np.array(self.dones, dtype=np.bool_)
        returns = np.zeros_like(rewards)
        running = 0.0
        for t in reversed(range(len(rewards))):
            if dones[t]:
                running = 0.0
            running = rewards[t] + self.gamma * running
            returns[t] = running
        return returns

    def _learn(self) -> None:
        if len(self.states) == 0:
            return
        states = np.array(self.states, dtype=np.float32)
        actions = np.array(self.actions, dtype=np.int64)
        old_logps = np.array(self.logps, dtype=np.float32)
        returns = self._compute_returns()

        values = np.array(self.values, dtype=np.float32)
        advantages = returns - values
        if advantages.std() > 1e-6:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        for _ in range(self.epochs):
            logits = np.array([self.actor.forward(s) for s in states], dtype=np.float32)
            probs = np.array([_softmax(l) for l in logits], dtype=np.float32)
            new_logps = np.log(probs[np.arange(len(states)), actions] + 1e-12)
            entropy = -np.sum(probs * np.log(probs + 1e-12), axis=1).mean()

            v_pred = np.array([self.critic.forward(s)[0] for s in states], dtype=np.float32)

            ratio = np.exp(new_logps - old_logps)
            surr1 = ratio * advantages
            surr2 = np.clip(ratio, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * advantages
            _ = -np.mean(np.minimum(surr1, surr2)) - self.ent_coef * entropy  # policy_loss (diagnostic)
            vf_loss = float(np.mean((v_pred - returns) ** 2))  # noqa: F841

            self._actor_step(states, actions, advantages, old_logps, probs)
            self._critic_step(states, returns, v_pred)

        self.update_count += 1

    def _actor_step(self, states, actions, advantages, old_logps, probs) -> None:
        lr = self.lr
        for s, a, adv in zip(states, actions, advantages):
            self.actor.forward(s)
            h = self.actor._hidden if self.actor._hidden is not None else _relu(s @ self.actor.W1 + self.actor.b1)
            p = _softmax(self.actor.W2 @ h + self.actor.b2)
            dlogp = np.zeros(self.action_dim, dtype=np.float32)
            dlogp[a] = 1.0
            grad_logits = -adv * (dlogp - p) + self.ent_coef * (np.log(p + 1e-12) + 1.0)
            dhidden = grad_logits @ self.actor.W2.T
            dz1 = dhidden * (h > 0)
            self.actor.W2 -= lr * np.outer(h, grad_logits)
            self.actor.b2 -= lr * grad_logits
            self.actor.W1 -= lr * np.outer(s, dz1)
            self.actor.b1 -= lr * dz1

    def _critic_step(self, states, returns, v_pred) -> None:
        lr = self.lr * self.vf_coef
        for s, ret, vp in zip(states, returns, v_pred):
            self.critic.forward(s)
            h = self.critic._hidden if self.critic._hidden is not None else _relu(s @ self.critic.W1 + self.critic.b1)
            dval = np.array([2.0 * (vp - ret)], dtype=np.float32)
            dhidden = dval[0] * self.critic.W2[0]
            dz1 = dhidden * (h > 0)
            self.critic.W2[0] -= lr * h[0] * dval[0] if h.ndim == 1 else lr * float(h) * dval[0]
            self.critic.b2[0] -= lr * dval[0]
            self.critic.W1 -= lr * np.outer(s, dz1)
            self.critic.b1 -= lr * dz1

    def update(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool = False,
    ) -> None:
        self.observe(reward, next_state, done)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        data = {
            **{f"actor_{k}": v for k, v in self.actor.get_weights().items()},
            **{f"critic_{k}": v for k, v in self.critic.get_weights().items()},
            "epsilon": np.array(self.epsilon),
            "update_count": np.array(self.update_count),
        }
        np.savez(path, **data)
        try:
            self.logger.info("PPO saved to %s", path)
        except Exception:
            pass

    def load(self, path: str) -> None:
        data = np.load(path, allow_pickle=True)
        actor_keys = ["W1", "b1", "W2", "b2"]
        critic_keys = ["W1", "b1", "W2", "b2"]
        aw = {k: data[f"actor_{k}"] for k in actor_keys if f"actor_{k}" in data}
        cw = {k: data[f"critic_{k}"] for k in critic_keys if f"critic_{k}" in data}
        if len(aw) == 4:
            self.actor.set_weights(aw)
        if len(cw) == 4:
            self.critic.set_weights(cw)
        if "epsilon" in data:
            self.epsilon = float(data["epsilon"])
        if "update_count" in data:
            self.update_count = int(data["update_count"])
        try:
            self.logger.info("PPO loaded from %s", path)
        except Exception:
            pass

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        s["trajectory_len"] = len(self.states)
        s["hidden"] = self.hidden
        return s


__all__ = ["PPOAgent", "_PPOMLP"]

