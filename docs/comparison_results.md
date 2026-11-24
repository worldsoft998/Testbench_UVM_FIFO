# Comparison Results — Template

**Side-by-side comparison: Baseline vs SRIE vs Blackbox**

This file is populated when you run `run_sim.bat` in **Compare** mode (mode 4) or run the three modes separately and aggregate. Until then, it contains the template structure below.

---

## 1. Experiment Setup

| Item | Value |
|------|-------|
| Simulator | Siemens QuestaSim (Windows) |
| DUT | async_fifo (SystemVerilog) |
| Testbench | UVM (reference, unchanged) |
| RL engine | Python + numpy (local only) |
| RL algorithms compared | qlearning, dqn, ppo |
| Coverage goal | 100% (functional) |
| Runs per configuration | 10 |
| Seed control | random |

---

## 2. Coverage Closure vs. Simulation Time

Plot data is recorded in `results/<mode>/coverage_curve.csv` and summarized here.

| Time (sim) | Baseline coverage % | SRIE coverage % | Blackbox coverage % |
|------------|---------------------|-----------------|---------------------|
| 10% budget | (fill in)           | (fill in)       | (fill in)           |
| 30% budget | (fill in)           | (fill in)       | (fill in)           |
| 50% budget | (fill in)           | (fill in)       | (fill in)           |
| 70% budget | (fill in)           | (fill in)       | (fill in)           |
| 100% budget| (fill in)           | (fill in)       | (fill in)           |

> Fill in after running the comparison. Use a plotting tool (e.g., Excel, matplotlib) on the CSV files to draw closure curves.

---

## 3. Total Simulation Time to Reach Goal

| Configuration | Avg wall-clock time to goal | Runs to goal | Goal reached? |
|---------------|-----------------------------|--------------|---------------|
| Baseline (no AI) | (fill in) | (fill in) | Y/N |
| SRIE (runtime AI) | (fill in) | (fill in) | Y/N |
| Blackbox (post-run AI) | (fill in) | (fill in) | Y/N |

---

## 4. Runs / Seeds Required

| Configuration | Seeds tested | Goal reached within budget |
|---------------|--------------|----------------------------|
| Baseline | (fill in) | Y/N |
| SRIE | (fill in) | Y/N |
| Blackbox | (fill in) | Y/N |

---

## 5. Hard-to-Hit (Corner-Case) Coverpoints

| Coverpoint | Baseline hit time | SRIE hit time | Blackbox hit time |
|------------|-------------------|---------------|-------------------|
| cp_wfull.full | (fill in) | (fill in) | (fill in) |
| cp_rempty.empty | (fill in) | (fill in) | (fill in) |
| cp_awfull.almost_full | (fill in) | (fill in) | (fill in) |
| cp_arempty.almost_empty | (fill in) | (fill in) | (fill in) |

---

## 6. Summary & Conclusion

- **Acceleration:** SRIE vs Baseline = (fill in)× faster closure
- **Acceleration:** Blackbox vs Baseline = (fill in)× faster closure
- **Best for corner cases:** (fill in)
- **Best overall wall time:** (fill in)

---

## 7. Raw Artifacts

| File | Location |
|------|----------|
| Baseline run summaries | `results/baseline/run_summary.csv` |
| SRIE run summaries | `results/srie/run_summary.csv` |
| Blackbox run summaries | `results/blackbox/run_summary.csv` |
| SRIE event timeline | `results/srie/srie_events.log` |
| Blackbox loop log | `results/blackbox/blackbox_loop.log` |
| RL checkpoints | `results/<mode>/model_*` |

---

*Populate this document after executing the comparison runs. No simulation code runs during repository creation.*
