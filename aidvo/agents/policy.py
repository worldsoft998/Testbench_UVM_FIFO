"""
AI evaluation rollout - AI/ML ON.

Loads a locally trained stable-baselines3 policy and lets it steer the
simulation boundary run-by-run (deterministic inference).  Records the same
history format as the baseline so `aidvo compare` can produce the
side-by-side report.

The policy's decision latency is measured per step (decision_time_s) and is
explicitly separated from simulation wall time: inference happens *between*
simulations and therefore adds zero delay inside simulated time.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from ..analysis.history import History, RunRecord
from ..config import Config


def rollout(
    cfg: Config,
    model_path: str,
    out_dir: Path,
    runs: Optional[int] = None,
    seed_base: Optional[int] = None,
    goal: Optional[float] = None,
    vary_seeds: bool = False,
    algo_hint: str = "",
) -> History:
    """Evaluate a trained policy for up to `runs` boundary simulations."""
    from ..env.coverage_env import AidvoCoverageEnv
    from .trainer import load_model

    bcfg = cfg.baseline_cfg
    runs = int(runs if runs is not None else bcfg.get("runs", 40))
    seed_base = int(seed_base if seed_base is not None else bcfg.get("seed_base", 1000))
    if goal is not None:
        cfg.set_goal_pct(float(goal))
    goal_pct = cfg.goal_pct

    # Anchor the seed pool at the requested base; by default evaluation uses
    # fixed (episode-independent) seeds so runs are reproducible.
    for knob in cfg.knobs:
        if knob["kind"] == "seed":
            knob["base"] = seed_base
            knob["vary_by_episode"] = bool(vary_seeds)

    model = load_model(model_path)
    env = AidvoCoverageEnv(cfg, mode="ai", worker_id=0)
    history = History(
        mode="ai",
        algo=algo_hint or Path(str(model_path)).parent.name,
        seed_base=seed_base,
        goal_pct=goal_pct,
    )

    print("[AId-VO] AI rollout: model=%s, up to %d runs, seed base %d, goal %.1f%%"
          % (model_path, runs, seed_base, goal_pct))

    obs, _ = env.reset(options={"max_steps": runs})
    while len(history.runs) < runs:
        t_dec = time.monotonic()
        action, _ = model.predict(obs, deterministic=True)
        decision_time = time.monotonic() - t_dec

        obs, _reward, terminated, truncated, info = env.step(int(action))
        rec = RunRecord(
            run=len(history.runs) + 1,
            mode="ai",
            algo=history.algo,
            test=info["test"],
            seed=int(info["seed"]),
            profile=info["profile"],
            coverage_pct=info["coverage_pct"],
            uvm_errors=info["uvm_errors"],
            uvm_warnings=info["uvm_warnings"],
            valid=info["valid"],
            wall_time_s=info["wall_time_s"],
            sim_time_ns=info["sim_time_ns"],
            reward=info["reward"],
            decision_time_s=decision_time,
        )
        history.add(rec)
        history.save(Path(out_dir))
        print("  run %3d | %-28s | seed %8d | cov %s | best %.2f%% | r %+6.2f | dec %.3fs"
              % (rec.run, rec.test, rec.seed,
                 ("%.2f%%" % rec.coverage_pct) if rec.coverage_pct is not None else "n/a",
                 history.best_pct, rec.reward, rec.decision_time_s))

        if terminated:
            print("[AId-VO] Coverage goal %.1f%% reached after %d runs." % (goal_pct, rec.run))
            break
        if truncated and len(history.runs) < runs:
            obs, _ = env.reset(options={"max_steps": runs - len(history.runs)})

    env.close()
    print("[AId-VO] AI rollout finished: %d runs, best coverage %.2f%% -> %s"
          % (len(history.runs), history.best_pct, Path(out_dir)))
    return history
