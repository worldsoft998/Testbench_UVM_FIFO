"""
Baseline campaign - AI/ML OFF.

Plain constrained-random regression used as the reference point for the
side-by-side comparison:

* tests are scheduled round-robin (or randomly) from the regression suite,
* seeds are drawn from the configured seed pool,
* boundary knobs stay at their default profile (no AI steering).

Runs the exact same boundary interface and records the identical history
format as the AI campaign, so `aidvo compare` is an apples-to-apples report.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, Optional

from ..analysis.history import History, RunRecord
from ..boundary.runner import SimRunner
from ..config import Config


def _decoded_choice(
    cfg: Config, test_idx: int, bucket_idx: int, profile_idx: int, rng: random.Random, strategy: str
) -> Dict[str, Dict[str, Any]]:
    """Hand-build a decoded action for the baseline schedule."""
    decoded: Dict[str, Dict[str, Any]] = {}
    for knob in cfg.knobs:
        card = cfg._cardinality(knob)
        if knob["kind"] == "seed":
            k = bucket_idx % card
        elif knob["kind"] == "uvm_test":
            k = test_idx % card if strategy == "round_robin" else rng.randrange(card)
        elif knob["kind"] == "plusargs":
            k = profile_idx % card
        else:  # extra
            k = 0
        value = k if knob["kind"] == "seed" else knob["values"][k]
        decoded[knob["name"]] = {"knob": knob, "index": k, "value": value}
    return decoded


def run_baseline(
    cfg: Config,
    out_dir: Path,
    runs: Optional[int] = None,
    seed_base: Optional[int] = None,
) -> History:
    """Execute the AI-off campaign and persist history.json / history.csv."""
    bcfg = cfg.baseline_cfg
    runs = int(runs if runs is not None else bcfg.get("runs", 40))
    seed_base = int(seed_base if seed_base is not None else bcfg.get("seed_base", 1000))
    strategy = str(bcfg.get("strategy", "round_robin"))
    randomize_seed = bool(bcfg.get("randomize_seed", True))
    profile_idx = int(bcfg.get("clock_profile_index", 0))
    goal = cfg.goal_pct

    # Keep the seed pool anchored at the requested seed base.
    for knob in cfg.knobs:
        if knob["kind"] == "seed":
            knob["base"] = seed_base
            knob["vary_by_episode"] = False

    rng = random.Random(seed_base)
    runner = SimRunner(cfg)
    history = History(mode="baseline", seed_base=seed_base, goal_pct=goal)

    print("[AId-VO] BASELINE (AI off): %d runs, seed base %d, strategy=%s"
          % (runs, seed_base, strategy))

    for i in range(1, runs + 1):
        test_knob = next((k for k in cfg.knobs if k["kind"] == "uvm_test"), None)
        test_card = cfg._cardinality(test_knob) if test_knob else 1
        test_idx = (i - 1) % test_card
        seed_card = 1
        for kidx, knob in enumerate(cfg.knobs):
            if knob["kind"] == "seed":
                seed_card = cfg.knob_cardinalities[kidx]
                break
        bucket = rng.randrange(seed_card) if randomize_seed else (i - 1)
        decoded = _decoded_choice(cfg, test_idx, bucket, profile_idx, rng, strategy)
        resolved = cfg.resolve_run(decoded, episode_index=0)

        result = runner.run(
            Path(cfg.repo_root) / "results" / "runs" / "baseline" / ("run_%03d" % i),
            seed=int(resolved["seed"]),
            plusargs=resolved["plusargs"],
            extra=resolved["extra"],
        )
        cov = result.stats.coverage_pct
        rec = RunRecord(
            run=i,
            mode="baseline",
            test=str(resolved["labels"].get("test", "-")),
            seed=int(resolved["seed"]),
            profile=resolved["labels"].get("clock_profile", ""),
            coverage_pct=cov,
            uvm_errors=result.stats.uvm_errors,
            uvm_warnings=result.stats.uvm_warnings,
            valid=result.valid,
            wall_time_s=result.wall_time_s,
            sim_time_ns=result.stats.sim_time_ns,
        )
        history.add(rec)
        history.save(Path(out_dir))
        print("  run %3d | seed %8d | cov %s | best %.2f%% | errors %s | %.1fs"
              % (i, rec.seed,
                 ("%.2f%%" % cov) if cov is not None else "n/a",
                 history.best_pct,
                 rec.uvm_errors if rec.uvm_errors is not None else "n/a",
                 rec.wall_time_s))
        if history.best_pct >= goal:
            print("[AId-VO] Coverage goal %.1f%% reached after %d runs." % (goal, i))
            break

    print("[AId-VO] Baseline finished: %d runs, best coverage %.2f%% -> %s"
          % (len(history.runs), history.best_pct, Path(out_dir)))
    return history
