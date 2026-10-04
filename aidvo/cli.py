"""
AId-VO command-line interface.

    python -m aidvo.cli check-config -c config/aidvo_config.yaml
    python -m aidvo.cli compile      -c config/aidvo_config.yaml
    python -m aidvo.cli baseline     -c config/aidvo_config.yaml --runs 40 --seed-base 1000
    python -m aidvo.cli train        -c config/aidvo_config.yaml --algo ppo --timesteps 2000 --n-envs 2
    python -m aidvo.cli rollout      -c config/aidvo_config.yaml --model models/ppo/final --runs 40 --goal 95
    python -m aidvo.cli compare      --baseline results/baseline --ai results/ai -o results/comparison

Only `train` / `rollout` require gymnasium + stable-baselines3; the baseline,
compile, check-config and compare commands run with PyYAML alone.
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .config import Config, ConfigError

DEFAULT_CFG = "config/aidvo_config.yaml"


def _add_cfg(p: argparse.ArgumentParser) -> None:
    p.add_argument("-c", "--config", default=DEFAULT_CFG, help="path to aidvo_config.yaml")
    p.add_argument("--repo-root", default=None, help="repository root (default: parent of config dir)")


def _load(args: argparse.Namespace) -> Config:
    return Config.load(args.config, repo_root=args.repo_root)


def cmd_check_config(args: argparse.Namespace) -> int:
    cfg = _load(args)
    print(cfg.describe())
    decoded = cfg.decode_action(0)
    resolved = cfg.resolve_run(decoded, episode_index=1)
    print("  example action 0 -> seed=%s plusargs=%s extra=%s"
          % (resolved["seed"], resolved["plusargs"], resolved["extra"]))
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    cfg = _load(args)
    from .boundary.runner import SimRunner

    return SimRunner(cfg).compile()


def cmd_baseline(args: argparse.Namespace) -> int:
    cfg = _load(args)
    if args.goal is not None:
        cfg.set_goal_pct(args.goal)
    from .agents.baseline import run_baseline

    run_baseline(cfg, out_dir=args.out, runs=args.runs, seed_base=args.seed_base)
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    cfg = _load(args)
    if args.goal is not None:
        cfg.set_goal_pct(args.goal)
    from .agents.trainer import train

    train(
        cfg,
        algo=args.algo,
        timesteps=args.timesteps,
        n_envs=args.n_envs,
        out_dir=args.out,
        seed=args.seed,
    )
    return 0


def cmd_rollout(args: argparse.Namespace) -> int:
    cfg = _load(args)
    from .agents.policy import rollout

    rollout(
        cfg,
        model_path=args.model,
        out_dir=args.out,
        runs=args.runs,
        seed_base=args.seed_base,
        goal=args.goal,
        vary_seeds=args.vary_seeds,
    )
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from .analysis.compare import compare

    compare(baseline_dir=args.baseline, ai_dir=args.ai, out_dir=args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="aidvo",
        description="AId-VO: AI-Driven Verification Optimization (local RL, "
                    "simulation-boundary only, no testbench modifications).",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check-config", help="validate and describe the configuration")
    _add_cfg(p)
    p.set_defaults(func=cmd_check_config)

    p = sub.add_parser("compile", help="compile the (unmodified) testbench")
    _add_cfg(p)
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("baseline", help="AI/ML OFF: constrained-random campaign")
    _add_cfg(p)
    p.add_argument("--runs", type=int, default=None)
    p.add_argument("--seed-base", type=int, default=None)
    p.add_argument("--goal", type=float, default=None, help="coverage goal %%")
    p.add_argument("-o", "--out", default="results/baseline")
    p.set_defaults(func=cmd_baseline)

    p = sub.add_parser("train", help="AI/ML ON: train an RL policy locally (SB3)")
    _add_cfg(p)
    p.add_argument("--algo", choices=["ppo", "a2c", "dqn"], default=None)
    p.add_argument("--timesteps", type=int, default=None)
    p.add_argument("--n-envs", type=int, default=None, help="parallel simulation workers")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--goal", type=float, default=None)
    p.add_argument("-o", "--out", default=None, help="model output dir (default models/<algo>)")
    p.set_defaults(func=cmd_train)

    p = sub.add_parser("rollout", help="AI/ML ON: evaluate a trained policy")
    _add_cfg(p)
    p.add_argument("--model", required=True, help="path to a saved model (e.g. models/ppo/final)")
    p.add_argument("--runs", type=int, default=None)
    p.add_argument("--seed-base", type=int, default=None)
    p.add_argument("--goal", type=float, default=None)
    p.add_argument("--vary-seeds", action="store_true",
                   help="offset the seed pool per campaign (default: fixed seeds)")
    p.add_argument("-o", "--out", default="results/ai")
    p.set_defaults(func=cmd_rollout)

    p = sub.add_parser("compare", help="side-by-side baseline vs AI report")
    p.add_argument("--baseline", default="results/baseline")
    p.add_argument("--ai", default="results/ai")
    p.add_argument("-o", "--out", default="results/comparison")
    p.set_defaults(func=cmd_compare)

    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except ConfigError as exc:
        print("[AId-VO] configuration error: %s" % exc, file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print("[AId-VO] %s" % exc, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
