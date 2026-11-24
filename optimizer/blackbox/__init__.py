"""Simulator blackbox optimizer.

Post-run analysis of simulator logs, coverage databases, and reports, followed by
RL-guided seed and constraint adjustment for the next simulation loop.
"""

__all__ = ["agent", "log_parser", "seed_manager", "loop_controller", "report_parser"]
