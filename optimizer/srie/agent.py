"""SRIE agent: event-triggered runtime/introspective optimizer.

Connects to the VPI plug-in, listens for coverage-relevant events, encodes
simulator state, queries the local RL policy, and pushes optimized stimulus
back through the introspection interface — all while the simulation runs.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from optimizer.config import CFG
from optimizer.rl import DQNAgent, PPOAgent, QLearningAgent
from optimizer.rl.action_space import ActionSpace
from optimizer.rl.reward import RewardFunction
from optimizer.rl.state_encoder import StateEncoder
from optimizer.coverage.tracker import CoverageTracker
from optimizer.utils.io import write_csv, ensure_dir
from optimizer.utils.logger import get_logger
from optimizer.srie.vpi_client import VPIClient
from optimizer.srie.discovery import Discovery
from optimizer.srie.introspection import Introspection
from optimizer.srie.event_listener import EventListener

logger = get_logger("optimizer.srie.agent")


class SRIEAgent:
    """Event-triggered SRIE optimization agent."""

    def __init__(
        self,
        rl_algorithm: str = "dqn",
        ai_on: bool = True,
        vpi_host: str = "127.0.0.1",
        vpi_port: int = 5555,
        vpi_dll: str = "sim/Questa/vpi/srie_vpi.dll",
        coverage_goal: float = 100.0,
        num_runs: int = 10,
        output_dir: str = "results/srie",
        state_dim: int = 8,
    ) -> None:
        self.rl_algorithm = rl_algorithm
        self.ai_on = ai_on
        self.vpi_host = vpi_host
        self.vpi_port = int(vpi_port)
        self.vpi_dll = vpi_dll
        self.coverage_goal = float(coverage_goal)
        self.num_runs = int(num_runs)
        self.output_dir = output_dir
        self.state_dim = int(state_dim)

        # RL components.
        self.action_space = ActionSpace()
        self.state_encoder = StateEncoder(state_dim=state_dim)
        self.reward_fn = RewardFunction()
        self.agent = self._build_rl_agent()

        # Coverage tracker.
        self.coverage = CoverageTracker()

        # VPI / introspection (set up in run()).
        self.vpi: Optional[VPIClient] = None
        self.discovery: Optional[Discovery] = None
        self.introspection: Optional[Introspection] = None
        self.listener: Optional[EventListener] = None

        # Runtime state.
        self.run_summaries: list = []
        self.events: list = []
        self._latest_observation: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    # RL agent factory
    # ------------------------------------------------------------------ #
    def _build_rl_agent(self):
        num_actions = self.action_space.num_actions
        common = dict(
            state_dim=self.state_dim,
            action_dim=num_actions,
            gamma=CFG.rl_gamma,
            lr=CFG.rl_lr,
            epsilon=CFG.rl_epsilon,
            epsilon_decay=CFG.rl_epsilon_decay,
            epsilon_min=CFG.rl_epsilon_min,
            seed=CFG.fixed_seed,
            name=self.rl_algorithm,
        )
        if self.rl_algorithm == "qlearning":
            return QLearningAgent(**common)
        if self.rl_algorithm == "dqn":
            return DQNAgent(hidden=CFG.rl_hidden,
                            buffer_size=CFG.rl_buffer_size,
                            batch_size=CFG.rl_batch_size, **common)
        if self.rl_algorithm == "ppo":
            return PPOAgent(hidden=CFG.rl_hidden, **common)
        raise ValueError(f"Unknown RL algorithm: {self.rl_algorithm}")

    # ------------------------------------------------------------------ #
    # Run loop
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        ensure_dir(self.output_dir)
        logger.info("SRIE agent starting (rl=%s, ai=%s, goal=%.1f%%)",
                    self.rl_algorithm, self.ai_on, self.coverage_goal)

        for run in range(1, self.num_runs + 1):
            self._run_once(run)

        self._write_summaries()
    def _run_once(self, run: int) -> None:
        logger.info("=== SRIE run %d/%d ===", run, self.num_runs)
        self.state_encoder.reset()
        self.reward_fn.reset()
        self.coverage = CoverageTracker()

        self.vpi = VPIClient(host=self.vpi_host, port=self.vpi_port)
        self.discovery = Discovery(self.vpi)
        self.introspection = Introspection(self.vpi)

        if not self.vpi.connect():
            logger.warning("Could not connect to VPI plug-in; running in observation-only mode")

        if self.vpi.connected:
            self.listener = EventListener(self.vpi, self._on_event)
            self.listener.start()

        # Simulate the run window. In a real deployment the batch file launches
        # QuestaSim; here we run the listener loop for the configured duration.
        start = time.time()
        max_time_s = self._parse_time(CFG.max_sim_time)
        while time.time() - start < max_time_s:
            # Pump the listener briefly so events are processed.
            if self.listener is None and self.vpi.connected:
                # Non-threaded fallback: poll once.
                self._on_event(self.vpi.recv() or {})
            time.sleep(0.05)

            # Check coverage goal.
            if self.coverage.coverage_percent() >= self.coverage_goal:
                logger.info("Coverage goal reached (%.1f%%)", self.coverage.coverage_percent())
                break

        if self.listener is not None:
            self.listener.stop()
        if self.vpi is not None:
            self.vpi.disconnect()

        self._write_summaries()
        logger.info("SRIE agent finished %d runs", self.num_runs)

        obs = self._current_observation()
        cov_pct = obs["coverage_pct"]
        reward = self.reward_fn.coverage_reward(cov_pct)
        reached = cov_pct >= self.coverage_goal
        self.run_summaries.append({
            "run": run,
            "seed": CFG.fixed_seed,
            "mode": "srie",
            "rl": self.rl_algorithm,
            "coverage_pct": round(cov_pct, 4),
            "goal_reached": reached,
            "reward": round(reward, 6),
            "wall_time_s": round(time.time() - start, 4),
            "actions_applied": len(self.introspection.history()) if self.introspection else 0,
        })
        logger.info("Run %d done: coverage=%.2f%% goal_reached=%s", run, cov_pct, reached)

    # ------------------------------------------------------------------ #
    # Event handler
    # ------------------------------------------------------------------ #
    def _on_event(self, event: Dict[str, Any]) -> None:
        """Called by the event listener whenever a simulation event fires."""
        if not event:
            return
        self.events.append(event)
        etype = event.get("type", "")
        logger.debug("SRIE event: %s", etype)

        # Update coverage tracker from the event.
        if etype == "coverage_sample":
            cp = event.get("coverpoint", "")
            val = float(event.get("value", 0.0))
            self.coverage.sample(cp, val, bin_hit=True)
            self._latest_observation = self.coverage.observation()
        elif etype == "value_change":
            self._latest_observation = self._current_observation()

        # Only steer if AI is on and this is a coverage-relevant trigger.
        if not self.ai_on:
            return
        if etype not in ("coverage_sample", "stall", "value_change"):
            return

        # Hierarchical discovery + reflection.
        report = {}
        if self.discovery is not None:
            report = self.discovery.reflect(event)

        # Encode state, select action, apply via introspection.
        state = self.state_encoder.encode(self._latest_observation)
        action_idx = self.agent.select_action(state, explore=True)
        command = self.action_space.to_command(action_idx)
        if self.introspection is not None:
            self.introspection.apply(command)

        # Learn from the transition after the next observation arrives.
        next_obs = self._current_observation()
        reward = self._compute_reward(self._latest_observation, next_obs)
        self.agent.update(state, action_idx, reward,
                          self.state_encoder.encode(next_obs), done=False)

    def _current_observation(self) -> Dict[str, Any]:
        obs = self.coverage.observation()
        obs.update(self._latest_observation)
        return obs

    def _compute_reward(self, before: Dict[str, Any], after: Dict[str, Any]) -> float:
        return self.reward_fn.compute(before, after)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_time(t: str) -> float:
        """Parse a time string like '1ms', '100ns', '1s' into seconds."""
        t = str(t).strip().lower()
        mult = {"ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0}
        for suffix, m in mult.items():
            if t.endswith(suffix):
                try:
                    return float(t[: -len(suffix)]) * m
                except ValueError:
                    return 1.0
        try:
            return float(t)
        except ValueError:
            return 1.0

    def _write_summaries(self) -> None:
        ensure_dir(self.output_dir)
        write_csv(os.path.join(self.output_dir, "run_summary.csv"), self.run_summaries,
                  fieldnames=["run", "seed", "mode", "rl", "coverage_pct", "goal_reached",
                              "reward", "wall_time_s", "actions_applied"])
        write_csv(os.path.join(self.output_dir, "srie_events.csv"), self.events,
                  fieldnames=["type", "path", "value", "coverpoint", "ts"])
        model_path = os.path.join(self.output_dir, "model.npz")
        try:
            self.agent.save(model_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Could not save RL model: %s", exc)

    def stats(self) -> Dict[str, Any]:
        return {
            "mode": "srie",
            "rl_algorithm": self.rl_algorithm,
            "num_runs": self.num_runs,
            "runs": self.run_summaries,
            "rl_stats": self.agent.stats(),
            "final_coverage": self.run_summaries[-1]["coverage_pct"] if self.run_summaries else 0.0,
        }


__all__ = ["SRIEAgent"]
