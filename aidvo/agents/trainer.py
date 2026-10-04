"""
Local RL training with stable-baselines3 (pure Python, no external APIs).

Parallel simulation sampling uses SubprocVecEnv: every worker process owns
its own AidvoCoverageEnv and runs its own QuestaSim simulations, so N
simulations progress concurrently while the algorithm trains on the merged
trajectory stream.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..config import Config

ALGORITHMS = ("ppo", "a2c", "dqn")


def _sb3():
    """Lazy import so `aidvo baseline`/`check-config` work without SB3."""
    from stable_baselines3 import A2C, DQN, PPO  # noqa: WPS433 (local import by design)

    return {"ppo": PPO, "a2c": A2C, "dqn": DQN}


def train(
    cfg: Config,
    algo: Optional[str] = None,
    timesteps: Optional[int] = None,
    n_envs: Optional[int] = None,
    out_dir: Optional[Path] = None,
    seed: Optional[int] = None,
) -> Path:
    """Train an RL policy that steers the simulation boundary. Returns the
    path of the saved model (without the .zip suffix)."""
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv

    from ..env.coverage_env import AidvoCoverageEnv

    tcfg = cfg.train_cfg
    algo = str(algo or tcfg.get("algo", "ppo")).lower()
    if algo not in ALGORITHMS:
        raise ValueError("unknown algorithm %r (choose from %s)" % (algo, ", ".join(ALGORITHMS)))
    timesteps = int(timesteps if timesteps is not None else tcfg.get("timesteps", 2000))
    n_envs = int(n_envs if n_envs is not None else tcfg.get("n_envs", 2))
    n_envs = max(1, n_envs)
    seed = int(seed if seed is not None else tcfg.get("seed", 0))

    out = Path(out_dir) if out_dir else cfg.repo_root / "models" / algo
    out.mkdir(parents=True, exist_ok=True)

    def _make(rank: int):
        def _init():
            return AidvoCoverageEnv(cfg, mode="train", worker_id=rank)

        return _init

    print("[AId-VO] Training %s: %d timesteps, %d parallel simulation workers"
          % (algo, timesteps, n_envs))
    vec = SubprocVecEnv([_make(i) for i in range(n_envs)])
    model_cls = _sb3()[algo]

    kwargs = {
        "policy": "MlpPolicy",
        "env": vec,
        "verbose": 1,
        "seed": seed,
    }
    if algo in ("ppo", "a2c"):
        kwargs["learning_rate"] = float(tcfg.get("learning_rate", 3e-4))
    model = model_cls(**kwargs)

    checkpoint_freq = max(int(tcfg.get("checkpoint_freq", 500)), 1)
    callback = CheckpointCallback(
        save_freq=max(checkpoint_freq // n_envs, 1),
        save_path=str(out / "checkpoints"),
        name_prefix=algo,
    )
    try:
        model.learn(total_timesteps=timesteps, callback=callback, progress_bar=False)
    finally:
        vec.close()

    model_path = out / "final"
    model.save(str(model_path))
    with open(out / "train_meta.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "algo": algo,
                "timesteps": timesteps,
                "n_envs": n_envs,
                "seed": seed,
                "goal_pct": cfg.goal_pct,
                "n_actions": cfg.n_actions,
            },
            fh,
            indent=2,
        )
    print("[AId-VO] Model saved: %s.zip" % model_path)
    return model_path


def load_model(model_path: str):
    """Load a saved SB3 model, auto-detecting the algorithm class."""
    path = str(model_path)
    if not path.endswith(".zip"):
        path += ".zip"
    if not Path(path).is_file():
        raise FileNotFoundError(
            "model not found: %s (train one with `aidvo train`)" % path
        )
    classes = _sb3()
    # Prefer the algorithm indicated by the parent directory name.
    parent = Path(path).parent.name.lower()
    ordered = [parent] + [k for k in classes if k != parent]
    errors = []
    for name in ordered:
        if name not in classes:
            continue
        try:
            return classes[name].load(path)
        except Exception as exc:  # noqa: BLE001 - try next algorithm class
            errors.append("%s: %s" % (name, exc))
    raise RuntimeError("could not load model %s (%s)" % (path, "; ".join(errors)))
