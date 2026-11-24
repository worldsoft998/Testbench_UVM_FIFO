# AId-UVO-RT Usage Guide

**End-to-end guide for running the AI-driven verification optimizer on Siemens QuestaSim.**

---

## 0. Before You Begin

- **No simulation or training code is executed during repository creation.** All commands below are run manually by you in your local environment.
- This guide targets **Windows** (batch files). The Python optimizer is cross-platform.
- The reference DUT/TB under `RTL/` and `dv/` (async FIFO, SystemVerilog/UVM) is **never modified**.

---

## 1. Install Python Dependencies

```powershell
cd <repo-root>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`requirements.txt` contains only `numpy`. No TensorFlow, PyTorch, or cloud AI SDKs are required.

---

## 2. Build the VPI Plug-in (SRIE mode only)

Open a **Windows developer command prompt** (MSVC available) with `QUESTA_HOME` pointing to your QuestaSim installation:

```bat
cd sim\Questa
build_vpi.bat
```

This compiles `sim\Questa\vpi\srie_vpi.c` into `sim\Questa\vpi\srie_vpi.dll`.

## 3. Launch the Interactive Runner

```bat
cd sim\Questa
run_sim.bat
```

The batch file shows a menu:

```
============================================================
  AId-UVO-RT  —  QuestaSim Interactive Runner
============================================================

[1] Select mode:
    1. Baseline (no AI)
    2. SRIE      (AI + simulator runtime)
    3. Blackbox  (AI + simulator blackbox)
    4. Compare   (all three, side-by-side report)
Choice [1-4]:
```

Then:

```
[2] Enable AI/ML? (on/off) [on]:
[3] RL algorithm: 1=qlearning 2=dqn 3=ppo [2]:
[4] Number of runs [10]:
[5] Seeds: random | fixed:N | list:a,b,c [random]:
[6] Coverage goal in %% [100]:
[7] Max simulation time per run [1ms]:
```

Press Enter at any prompt to accept the default.

## 4. Mode-by-Mode Walkthrough

### 4.1 Baseline (no AI)

Runs plain constrained-random regression.

- Select mode **1**.
- AI is implicitly off.
- Each run uses a fresh seed.
- Coverage and runtime are recorded to `results/baseline/`.

Use this as the reference for the side-by-side comparison.

### 4.2 SRIE (AI + simulator runtime)

Runs with the VPI plug-in loaded and the Python SRIE agent connected over TCP.

- Select mode **2**.
- Ensure `srie_vpi.dll` is built (step 2).
- AI on/off, RL algorithm, runs, seeds, coverage goal all apply.
- The SRIE agent observes coverage events **mid-simulation** and pushes optimized stimulus back instantly.

Outputs go to `results/srie/` (coverage curves, model checkpoints, event log).

### 4.3 Blackbox (AI + simulator blackbox)

Treats QuestaSim as a blackbox. No simulator internals accessed.

- Select mode **3**.
- After each run, the blackbox agent parses `sim.log` and coverage reports, then adjusts seed/constraints for the next run.
- Loops until the coverage goal or run budget is met.

Outputs go to `results/blackbox/`.

### 4.4 Compare (all three, side-by-side report)

Runs Baseline, SRIE, and Blackbox sequentially and produces a combined comparison report.

- Select mode **4**.
- Same interactive options apply to each mode.
- Final report: `results/comparison_results.md`.

## 5. Command-Line Alternative (Python optimizer)

You can also drive the optimizer directly from Python (useful for CI/custom flows):

```powershell
# Baseline
python -m optimizer.core --mode baseline --runs 10 --seed random --goal 100

# SRIE
python -m optimizer.core --mode srie --rl dqn --ai on --runs 10 --goal 100 --vpi-port 5555

# Blackbox
python -m optimizer.core --mode blackbox --rl ppo --ai on --runs 10 --goal 100

# Compare
python -m optimizer.core --mode compare --runs 10 --goal 100
```

See `optimizer/core.py --help` for the full option list.

## 6. Interpreting Results

Each mode writes to `results/<mode>/`:

| File | Meaning |
|------|---------|
| `coverage_curve.csv` | Functional coverage vs. simulation time per run |
| `run_summary.csv` | Per-run: seed, coverage %, wall time, goal reached |
| `model_*.pkl / model_*.npy` | Trained RL checkpoint (local only) |
| `srie_events.log` | SRIE event-trigger timeline (SRIE only) |
| `blackbox_loop.log` | Per-loop seed/constraint adjustments (blackbox only) |

The **Compare** mode aggregates these into `results/comparison_results.md`, showing:

- Coverage closure curves side-by-side
- Total simulation time to reach goal (SRIE vs Blackbox vs Baseline)
- Runs/seeds required
- Hard-to-hit corner-case coverpoint hit times

## 7. Batch File Options Reference

| Prompt | Values | Default | Effect |
|--------|--------|---------|--------|
| Mode | baseline / srie / blackbox / compare | baseline | Optimizer configuration |
| AI/ML | on / off | on | Enable/disable RL steering |
| RL algorithm | qlearning / dqn / ppo | dqn | Local RL policy |
| Number of runs | integer | 10 | Runs per regression |
| Seeds | random / fixed:N / list:… | random | Seed control |
| Coverage goal | 0–100 | 100 | Closure target (%) |
| Max sim time/run | time string | 1ms | Per-run time budget |

## 8. Troubleshooting

| Issue | Likely cause / fix |
|-------|--------------------|
| `build_vpi.bat` fails | `QUESTA_HOME` or MSVC not set; run from a developer command prompt |
| SRIE agent can't connect | VPI DLL not loaded (`-pli`), wrong port, or firewall blocking localhost |
| `numpy` not found | Run `pip install -r requirements.txt` in the active venv |
| Coverage stuck at 0% | Check `compile.do` includes the coverage model; raise UVM verbosity for debug |
| No `results/` output | Confirm output directory in the batch menu; results are written under `results/<mode>/` |

## 9. Non-Intrusiveness Reminder

The optimizer does **not** edit `RTL/` or `dv/`. The only Questa-side addition is the externally-built VPI plug-in (loaded via `-pli`) and top-level wrapper files under `sim/Questa/`. You can run the same batch files against a different UVM testbench by pointing `compile.do` / `tb_top_*.sv` at it — no TB source changes required.

---

*End of usage guide.*

> If `QUESTA_HOME` is not set, edit `build_vpi.bat` to point `QUESTA_INC` at your Questa `include` directory and `MSVC` at your `cl.exe`.
