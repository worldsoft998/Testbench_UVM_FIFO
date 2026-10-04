"""
Side-by-side comparison of the baseline (AI off) and AI campaigns.

Consumes the two history.json records produced by `aidvo baseline` and
`aidvo rollout` and writes:

* coverage_progress.csv - per-run best-coverage trajectories of both runs,
* coverage_progress.png - plot (only when matplotlib is installed),
* comparison_report.md   - the full side-by-side report with metrics:
  coverage reached, runs-to-goal, wall-clock time-to-goal, average best
  coverage, area-under-the-coverage-curve, UVM error/warning totals and the
  resulting speed-up factors.

All numbers are computed from the recorded runs - the report never contains
hand-written or illustrative results.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .history import History


def campaign_metrics(hist: History) -> Dict[str, Any]:
    """Aggregate metrics of one campaign."""
    runs = hist.runs
    n = len(runs)
    goal = hist.goal_pct
    runs_to_goal: Optional[int] = None
    for r in runs:
        if r.best_pct >= goal:
            runs_to_goal = r.run
            break
    wall_total = sum(r.wall_time_s for r in runs)
    sim_time_s = sum((r.sim_time_ns or 0.0) for r in runs) * 1e-9
    decision_total = sum(r.decision_time_s for r in runs)
    errors = sum(int(r.uvm_errors or 0) for r in runs)
    warnings = sum(int(r.uvm_warnings or 0) for r in runs)
    valid_runs = sum(1 for r in runs if r.valid)

    wall_to_goal: Optional[float] = None
    if runs_to_goal is not None:
        wall_to_goal = sum(r.wall_time_s for r in runs if r.run <= runs_to_goal)

    best_series = [r.best_pct for r in runs]
    if n >= 2:
        auc = sum((best_series[i] + best_series[i - 1]) / 2.0 for i in range(1, n)) / (n - 1)
    else:
        auc = best_series[0] if best_series else 0.0

    return {
        "runs": n,
        "goal_pct": goal,
        "final_best_pct": hist.best_pct,
        "runs_to_goal": runs_to_goal,
        "wall_to_goal_s": wall_to_goal,
        "total_wall_s": wall_total,
        "total_sim_time_s": sim_time_s,
        "total_decision_s": decision_total,
        "avg_best_pct": (sum(best_series) / n) if n else 0.0,
        "auc_best_pct": auc,
        "coverage_per_run": (hist.best_pct / n) if n else 0.0,
        "coverage_per_min": (hist.best_pct / (wall_total / 60.0)) if wall_total > 0 else 0.0,
        "uvm_errors": errors,
        "uvm_warnings": warnings,
        "valid_runs": valid_runs,
        "algo": hist.algo or "-",
        "seed_base": hist.seed_base,
        "created": hist.created,
    }


def _progress_rows(base: History, ai: History) -> List[List[str]]:
    n = max(len(base.runs), len(ai.runs))
    rows = [["run", "baseline_best_pct", "ai_best_pct"]]
    for i in range(n):
        b = "%.2f" % base.runs[i].best_pct if i < len(base.runs) else ""
        a = "%.2f" % ai.runs[i].best_pct if i < len(ai.runs) else ""
        rows.append([str(i + 1), b, a])
    return rows


def _plot(base: History, ai: History, png_path: Path) -> Optional[str]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001 - plotting is optional
        return "plot skipped (matplotlib unavailable: %s)" % exc

    xs_b = [r.run for r in base.runs]
    xs_a = [r.run for r in ai.runs]
    plt.figure(figsize=(9, 5))
    plt.plot(xs_b, [r.best_pct for r in base.runs], marker=".", label="Baseline (AI off)")
    plt.plot(xs_a, [r.best_pct for r in ai.runs], marker=".", label="AId-VO (AI on)")
    plt.axhline(base.goal_pct, color="gray", linestyle="--", label="Coverage goal")
    plt.xlabel("Simulation run")
    plt.ylabel("Best cumulative coverage (%)")
    plt.title("Coverage closure: baseline vs AI")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(png_path, dpi=140)
    plt.close()
    return None


def _ratio(a: Optional[float], b: Optional[float]) -> str:
    if a is None or b is None or b == 0:
        return "n/a"
    return "%.2fx" % (a / b)


def compare(baseline_dir: Path, ai_dir: Path, out_dir: Path) -> Path:
    """Generate the side-by-side comparison; returns the report path."""
    base = History.load(Path(baseline_dir))
    ai = History.load(Path(ai_dir))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    mb = campaign_metrics(base)
    ma = campaign_metrics(ai)

    # per-run trajectory CSV
    rows = _progress_rows(base, ai)
    with open(out / "coverage_progress.csv", "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(",".join(row) + "\n")

    plot_note = _plot(base, ai, out / "coverage_progress.png")
    if plot_note:
        print("[AId-VO] %s" % plot_note)

    lines: List[str] = []
    lines.append("# AId-VO Comparison Report - Baseline (AI off) vs AI")
    lines.append("")
    lines.append("Generated: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("")
    lines.append("| Item | Baseline (AI off) | AId-VO (AI on) |")
    lines.append("|---|---:|---:|")
    lines.append("| Mode / algorithm | %s | %s |" % (mb["algo"], ma["algo"]))
    lines.append("| Runs executed | %d | %d |" % (mb["runs"], ma["runs"]))
    lines.append("| Seed base | %d | %d |" % (mb["seed_base"], ma["seed_base"]))
    lines.append("| Coverage goal | %.1f%% | %.1f%% |" % (mb["goal_pct"], ma["goal_pct"]))
    lines.append("| Final best coverage | %.2f%% | %.2f%% |"
                 % (mb["final_best_pct"], ma["final_best_pct"]))
    lines.append("| Runs to reach goal | %s | %s |"
                 % (mb["runs_to_goal"] if mb["runs_to_goal"] else "not reached",
                    ma["runs_to_goal"] if ma["runs_to_goal"] else "not reached"))
    lines.append("| Wall time to goal | %s | %s |"
                 % ("%.1fs" % mb["wall_to_goal_s"] if mb["wall_to_goal_s"] is not None else "n/a",
                    "%.1fs" % ma["wall_to_goal_s"] if ma["wall_to_goal_s"] is not None else "n/a"))
    lines.append("| Total simulation wall time | %.1fs | %.1fs |"
                 % (mb["total_wall_s"], ma["total_wall_s"]))
    lines.append("| Total simulated time | %.3gs | %.3gs |"
                 % (mb["total_sim_time_s"], ma["total_sim_time_s"]))
    lines.append("| AI decision overhead (total) | 0.0s | %.3fs |" % ma["total_decision_s"])
    lines.append("| Average best coverage / run | %.2f%% | %.2f%% |"
                 % (mb["avg_best_pct"], ma["avg_best_pct"]))
    lines.append("| Coverage-vs-runs AUC | %.2f | %.2f |" % (mb["auc_best_pct"], ma["auc_best_pct"]))
    lines.append("| Coverage gained per run | %.2f%% | %.2f%% |"
                 % (mb["coverage_per_run"], ma["coverage_per_run"]))
    lines.append("| Coverage gained per minute | %.2f%% | %.2f%% |"
                 % (mb["coverage_per_min"], ma["coverage_per_min"]))
    lines.append("| UVM errors (total) | %d | %d |" % (mb["uvm_errors"], ma["uvm_errors"]))
    lines.append("| UVM warnings (total) | %d | %d |" % (mb["uvm_warnings"], ma["uvm_warnings"]))
    lines.append("| Valid runs | %d / %d | %d / %d |"
                 % (mb["valid_runs"], mb["runs"], ma["valid_runs"], ma["runs"]))
    lines.append("")
    lines.append("## Speed-up summary")
    lines.append("")
    lines.append("| Metric | Factor |")
    lines.append("|---|---:|")
    lines.append("| Runs-to-goal speed-up (baseline / AI) | %s |"
                 % _ratio(mb["runs_to_goal"], ma["runs_to_goal"]))
    lines.append("| Time-to-goal speed-up (baseline / AI) | %s |"
                 % _ratio(mb["wall_to_goal_s"], ma["wall_to_goal_s"]))
    lines.append("| Coverage-per-run ratio (AI / baseline) | %s |"
                 % _ratio(ma["coverage_per_run"], mb["coverage_per_run"]))
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append("- `coverage_progress.csv` - per-run best coverage of both campaigns")
    lines.append("- `coverage_progress.png` - plotted trajectories (if matplotlib installed)")
    lines.append("- `../baseline/history.json|.csv`, `../ai/history.json|.csv` - raw run records")
    lines.append("")
    lines.append("All values are computed directly from the recorded simulation runs.")
    lines.append("")
    report = out / "comparison_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print("[AId-VO] Comparison report: %s" % report)
    return report
