# AId-VO Usage Guide

This guide walks through the full workflow: compile → baseline (AI off) →
train (AI on) → evaluate (AI on) → compare. Nothing in the workflow ever
modifies the testbench.

## 1. Prerequisites

* **QuestaSim** (`vlib`, `vlog`, `vsim`, `vcover`) on `PATH`
  (or adjust the command templates in `config/aidvo_config.yaml`).
* **Python 3.9+** with the platform packages:

```bash
pip install -r requirements.txt
```

> `stable-baselines3` pulls in PyTorch automatically. Everything runs locally;
> no external AI model service is contacted at any point.

## 2. Windows: interactive launcher

```bat
sim\aidvo_menu.bat
```

The menu offers selectable options for:

| Option | Meaning |
|---|---|
| `[1]` | Compile the testbench (unmodified) |
| `[2]` | Run one simulation: test, seed, clock periods |
| `[3]` | **BASELINE - AI/ML OFF**: number of runs, seed base |
| `[4]` | **AI RUN - AI/ML ON**: RL algorithm (PPO/A2C/DQN), timesteps, parallel workers, evaluation runs, seed base, coverage goal |
| `[5]` | **AI EVAL**: rollout an existing trained model |
| `[6]` | **COMPARE**: baseline vs AI report |
| `[7]` | Validate the configuration |

Non-interactive equivalents (also usable from scripts):

```bat
sim\compile.bat
sim\run_single.bat fifo_almost_full_test 42 5 7
sim\run_baseline.bat 40 1000
sim\run_ai.bat ppo 2000 40 1000 95
sim\compare.bat
```

Environment overrides: `set AIDVO_PY=py -3` (interpreter) and
`set AIDVO_CFG=config\aidvo_config.yaml` (config path).

## 3. Linux/macOS: CLI workflow

```bash
# 0) validate the configuration (action space, knobs, regexes)
python -m aidvo.cli check-config -c config/aidvo_config.yaml

# 1) compile the unmodified testbench (or ./sim/compile.sh)
python -m aidvo.cli compile -c config/aidvo_config.yaml

# 2) BASELINE - AI/ML OFF (plain constrained-random regression)
python -m aidvo.cli baseline -c config/aidvo_config.yaml --runs 40 --seed-base 1000

# 3) TRAIN - AI/ML ON (local stable-baselines3; PPO | A2C | DQN)
python -m aidvo.cli train -c config/aidvo_config.yaml --algo ppo --timesteps 2000 --n-envs 2

# 4) EVALUATE the trained policy (AI on)
python -m aidvo.cli rollout -c config/aidvo_config.yaml \
    --model models/ppo/final --runs 40 --seed-base 1000 --goal 95 -o results/ai

# 5) SIDE-BY-SIDE comparison report
python -m aidvo.cli compare --baseline results/baseline --ai results/ai -o results/comparison
```

Open `results/comparison/comparison_report.md` for the final
with-AI vs without-AI table (coverage, runs-to-goal, wall time, speed-up
factors, error totals) plus `coverage_progress.csv/.png`.

## 4. Output layout

```text
results/
├── runs/                     # per-simulation working dirs (transcripts, ucdb)
├── baseline/                 # AI off
│   ├── history.json          # one record per run: seed, test, coverage, times
│   └── history.csv
├── ai/                       # AI on (rollout)
│   ├── history.json
│   └── history.csv
└── comparison/
    ├── comparison_report.md  # side-by-side deliverable
    ├── coverage_progress.csv
    └── coverage_progress.png # when matplotlib is installed
models/
├── ppo/final.zip             # trained policy (+ checkpoints/, train_meta.json)
├── a2c/...
└── dqn/...
```

## 5. Configuration cookbook (`config/aidvo_config.yaml`)

### 5.1 Knobs (the action space)

```yaml
knobs:
  - name: test
    kind: uvm_test            # → +UVM_TESTNAME=<value>
    values: [fifo_reset_test, ...]
  - name: seed_bucket
    kind: seed                # → vsim -sv_seed
    buckets: 8
    base: 1000
    vary_by_episode: true
  - name: clock_profile
    kind: plusargs            # → +WCLK_HALF_NS=.. +RCLK_HALF_NS=..
    values: [{WCLK_HALF_NS: 5, RCLK_HALF_NS: 7}, ...]
```

The flat `Discrete` action count is the product of all knob cardinalities
(here 10 × 8 × 4 = 320). Add a 4th knob (e.g. `kind: extra` for raw run
options) and the space grows automatically - no code change.

### 5.2 Two coverage modes

* `coverage.mode: transcript` (default): the scalar functional-coverage
  percentage printed by the testbench report phase
  (`Average Coverage : NN.NN%`) is read from the transcript. Zero setup.
* `coverage.mode: ucdb`: add `-coverage` to
  `commands.extra_options_default` **and** to the `extra` tokens of a knob
  (or pass it through the `extra` knob), then AId-VO merges each run's UCDB
  with `vcover merge` and reads only the **total** percentage from
  `vcover report -summary`. Cumulative coverage is monotone by construction.

### 5.3 Boundary command templates

All commands are argv-token lists with `{placeholders}` (no shell involved):

```yaml
commands:
  simulate: ["vsim", "-64", "-c", "-work", "{work_lib}", "{top}",
             "-sv_seed", "{seed}", "{plusargs}", "{extra}",
             "-l", "{log_file}", "-do", "{do_file}"]
  timeout_s: 900
```

Each simulation executes with `cwd` = its own run directory, so the
`SubprocVecEnv` workers never step on each other.

### 5.4 Reward shaping

`env.reward` holds all weights (coverage gain, error/warning/fatal penalties,
time penalty, stagnation penalty, goal bonus, valid-run bonus). Defaults are
sensible for most projects; scale `coverage_gain_weight` if your coverage
goals are far from 100%.

## 6. Porting to a different testbench

1. Copy the repo; keep `aidvo/` untouched.
2. Replace `RTL/`, `dv/`, `docs/01-03` with your design/testbench.
3. Edit `config/aidvo_config.yaml`: `project.testbench_root` (use
   `Testbench_UVM` if your checkout keeps the TB in a subdirectory), `top`,
   `knobs`, `commands`, `log_parse` regexes, test list, coverage goal.
4. Re-compile (`sim/compile.bat|sh`) and run `check-config`.

The RL environment, agents, baselines and reports are fully reusable as-is -
this is what makes AId-VO universal.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `uvm_pkg.sv(1): cannot find...` at compile | Set `UVM_SRC` (or `UVM_HOME`/`QUESTA_HOME`) to your UVM `src` directory; `sim/compile.*` auto-detects common layouts |
| `vsim: command not found` | Add QuestaSim `bin` to `PATH`, or edit `commands.*` for your site setup |
| Coverage always 0 / `n/a` | Check `log_parse.coverage_regex` against your transcript (it must match the *summary* scalar line), or switch to `ucdb` mode |
| Runs collide when training | Keep the default per-run working directories (do not force a shared cwd) |
| `No module named 'gymnasium'` (or `stable_baselines3`) | `pip install -r requirements.txt` (only `train`/`rollout` need them) |
| No PNG in comparison | `pip install matplotlib` (the CSV/MD report works without it) |
| Windows: `python` not found | `set AIDVO_PY=py -3` before running the batch files |
| Simulation hangs | `commands.timeout_s` kills each run; raise it for long tests |

## 8. What the platform is forbidden to do (and how that is enforced)

See `docs/06_aidvo_compliance.md`. In short: no testbench file is read or
written, no coverage-model structure is parsed - only scalar percentages,
UVM report counts and transcripts cross the boundary.
