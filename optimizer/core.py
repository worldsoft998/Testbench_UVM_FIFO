"""Multi-mode orchestrator for the AId-UVO-RT optimizer.

CLI entry point that runs the optimizer in one of four modes:
  baseline | srie | blackbox | compare

No simulation or training is triggered by importing this module; a mode must be
selected explicitly (via CLI flags or the QuestaSim batch files).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from optimizer.config import CFG
from optimizer.utils.logger import get_logger
from optimizer.utils.io import write_csv, ensure_dir

logger = get_logger("optimizer.core")

# Lazy imports so the CLI can print help without pulling in heavy submodules.
_SRIE_AGENT = None
_BLACKBOX_AGENT = None


def _import_srie():
    global _SRIE_AGENT
    if _SRIE_AGENT is None:
        from optimizer.srie.agent import SRIEAgent
        _SRIE_AGENT = SRIEAgent
    return _SRIE_AGENT


def _import_blackbox():
    global _BLACKBOX_AGENT
    if _BLACKBOX_AGENT is None:
        from optimizer.blackbox.agent import BlackboxAgent
        _BLACKBOX_AGENT = BlackboxAgent
    return _BLACKBOX_AGENT


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AId-UVO-RT optimizer orchestrator")
    sub = p.add_subparsers(dest="mode", required=True)

    def add_common(sp):
        sp.add_argument("--rl", dest="rl_algorithm", choices=["qlearning", "dqn", "ppo"],
                        default=CFG.rl_algorithm, help="RL algorithm")
        sp.add_argument("--ai", dest="ai_on", choices=["on", "off"],
                        default="on" if CFG.ai_on else "off", help="Enable/disable AI")
        sp.add_argument("--runs", type=int, default=CFG.num_runs, help="Number of runs")
        sp.add_argument("--seed-mode", dest="seed_mode", choices=["random", "fixed", "list"],
                        default=CFG.seed_mode, help="Seed control mode")
        sp.add_argument("--seed", type=int, default=CFG.fixed_seed, help="Fixed seed (mode fixed)")
        sp.add_argument("--seed-list", dest="seed_list", default=CFG.seed_list,
                        help="Comma-separated seeds (mode list)")
        sp.add_argument("--goal", type=float, default=CFG.coverage_goal, help="Coverage goal (%)")
        sp.add_argument("--max-time", dest="max_sim_time", default=CFG.max_sim_time,
                        help="Max sim time per run")
        sp.add_argument("--out", dest="output_dir", default=CFG.output_dir, help="Output directory")

    sp_baseline = sub.add_parser("baseline", help="Constrained-random baseline (no AI)")
    add_common(sp_baseline)
    sp_baseline.set_defaults(func=_run_baseline)

    sp_srie = sub.add_parser("srie", help="SRIE: AI + simulator runtime (instantaneous)")
    add_common(sp_srie)
    sp_srie.add_argument("--vpi-port", type=int, default=CFG.srie_vpi_port, help="VPI TCP port")
    sp_srie.add_argument("--vpi-host", default=CFG.srie_vpi_host, help="VPI TCP host")
    sp_srie.add_argument("--vpi-dll", default=CFG.srie_vpi_dll, help="Path to srie_vpi.dll")
    sp_srie.set_defaults(func=_run_srie)

    sp_bb = sub.add_parser("blackbox", help="Blackbox: AI + simulator blackbox (post-run)")
    add_common(sp_bb)
    sp_bb.set_defaults(func=_run_blackbox)

    sp_cmp = sub.add_parser("compare", help="Compare baseline + SRIE + blackbox side-by-side")
    add_common(sp_cmp)
    sp_cmp.set_defaults(func=_run_compare)

    return p


def _next_seed(args, index: int) -> int:
    if args.seed_mode == "fixed":
        return args.seed
    if args.seed_mode == "list" and args.seed_list:
        parts = [int(x.strip()) for x in args.seed_list.split(",") if x.strip()]
        return parts[index % len(parts)]
    import random
    return random.randrange(0, 2 ** 31)

# --------------------------------------------------------------------------- #
# Mode runners
# --------------------------------------------------------------------------- #
def _run_baseline(args) -> int:
    logger.info("BASELINE mode: runs=%d goal=%.1f%%", args.runs, args.goal)
    out = ensure_dir(os.path.join(args.output_dir, "baseline"))
    rows = []
    for i in range(args.runs):
        seed = _next_seed(args, i)
        # The actual simulation is driven by the Questa batch files. This records
        # the intended run; post-run analysis fills in coverage/wall time.
        rows.append({"run": i + 1, "seed": seed, "mode": "baseline",
                     "coverage_pct": 0.0, "goal_reached": False, "wall_time_s": 0.0})
    write_csv(os.path.join(out, "run_summary.csv"), rows,
              fieldnames=["run", "seed", "mode", "coverage_pct", "goal_reached", "wall_time_s"])
    logger.info("Baseline summary written to %s", out)
    return 0


def _run_srie(args) -> int:
    logger.info("SRIE mode: rl=%s ai=%s runs=%d goal=%.1f%% vpi=%s:%d",
                args.rl_algorithm, args.ai_on, args.runs, args.goal,
                args.vpi_host, args.vpi_port)
    agent_cls = _import_srie()
    agent = agent_cls(
        rl_algorithm=args.rl_algorithm,
        ai_on=(args.ai_on == "on"),
        vpi_host=args.vpi_host,
        vpi_port=args.vpi_port,
        vpi_dll=args.vpi_dll,
        coverage_goal=args.goal,
        num_runs=args.runs,
        output_dir=os.path.join(args.output_dir, "srie"),
    )
    agent.run()
    return 0


def _run_blackbox(args) -> int:
    logger.info("BLACKBOX mode: rl=%s ai=%s runs=%d goal=%.1f%%",
                args.rl_algorithm, args.ai_on, args.runs, args.goal)
    agent_cls = _import_blackbox()
    agent = agent_cls(
        rl_algorithm=args.rl_algorithm,
        ai_on=(args.ai_on == "on"),
        coverage_goal=args.goal,
        max_runs=args.runs,
        output_dir=os.path.join(args.output_dir, "blackbox"),
    )
    agent.run()
    return 0


def _run_compare(args) -> int:
    logger.info("COMPARE mode: runs=%d goal=%.1f%%", args.runs, args.goal)
    _run_baseline(args)
    _run_srie(args)
    _run_blackbox(args)
    _write_comparison_report(args.output_dir, args.runs, args.goal)
    return 0


def _write_comparison_report(out_dir: str, runs: int, goal: float) -> None:
    ensure_dir(out_dir)
    lines = [
        "# Comparison Results — Baseline vs SRIE vs Blackbox",
        "",
        f"Runs per configuration: {runs}  |  Coverage goal: {goal}%",
        "",
        "| Configuration | Mode | AI | Status |",
        "|---------------|------|----|--------|",
        "| Baseline      | Constrained-random | off | See results/baseline/ |",
        "| SRIE          | Runtime introspection | on | See results/srie/ |",
        "| Blackbox      | Post-run analysis | on | See results/blackbox/ |",
        "",
        "Aggregate the per-mode run_summary.csv files to build the side-by-side report.",
        "See docs/comparison_results.md for the results template.",
    ]
    with open(os.path.join(out_dir, "comparison_results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info("Comparison report written to %s/comparison_results.md", out_dir)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())


