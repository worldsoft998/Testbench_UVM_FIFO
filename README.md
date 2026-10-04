# AId-VO — AI-Driven Verification Optimization

**A universal, AI-based verification acceleration platform** that accelerates
functional coverage closure and reduces simulation time for *any* third-party
testbench written in HDL/HVL/HLS languages and verification methodologies
(UVM, etc.) — **without any modification to the testbench or its coverage
model**.

The platform treats the entire simulation environment as a **black box** and
runs AI agents exclusively at the **simulation boundary**: it observes only
scalar coverage percentages, UVM error/warning counts and simulation
transcripts, and steers simulations by dynamically adjusting random seeds,
constraint-randomization parameters (boundary plusargs) and test selection
from the regression suite.

> 🎛️ **Windows users:** everything is available from one interactive menu —
> `sim\aidvo_menu.bat` — with selectable options for **AI/ML on or off**,
> **RL algorithm (PPO / A2C / DQN)**, **number of runs, seeds, coverage goal**
> and more.

---

## Key properties

| Property | How |
|---|---|
| 🔒 **No testbench changes** | `RTL/` and `dv/` are never written; the only added SV file is a compilation-unit prelude outside the testbench (`sim/uvm_prelude.sv`) |
| 🙈 **No coverage-model access** | Observation allowlist = scalar coverage % (transcript / UCDB *total*), UVM report-summary counts, log data — parsed by configured regexes, nothing else |
| ⚡ **Zero-delay steering** | Inference happens *between* simulations; decision latency is recorded separately and never enters simulated time |
| 🧠 **Full RL stack in pure Python** | Gymnasium environment + stable-baselines3 (PPO/A2C/DQN) with `SubprocVecEnv` parallel simulation sampling — **100% local, no external AI APIs** |
| 🔌 **Universal** | Tests, knobs, command templates and observation regexes live in one YAML file — porting to another RTL project requires **no code change** |
| 📊 **Proven measurement** | Symmetric baseline-vs-AI campaigns produce `comparison_report.md`, CSV and PNG with runs-to-goal, time-to-goal, AUC and speed-up factors |

---

## Repository structure

```text
.
├── README.md                     ← you are here (AId-VO platform)
├── requirements.txt              ← Python dependencies (local-only RL stack)
├── RTL/                          ← sample design: async FIFO (unmodified)
├── dv/                           ← sample design: UVM testbench (unmodified)
├── config/
│   └── aidvo_config.yaml         ← the ONLY project-specific file (knobs, commands, regexes)
├── sim/                          ← QuestaSim scripts + Windows batch launchers
│   ├── aidvo_menu.bat            ← interactive menu (AI on/off, algorithm, runs, seeds, goal)
│   ├── compile.bat / compile.sh  ← compile the unmodified testbench
│   ├── run_single.bat / .sh      ← one boundary-controlled simulation
│   ├── run_baseline.bat          ← AI/ML OFF campaign
│   ├── run_ai.bat                ← AI/ML ON: train + evaluate
│   ├── compare.bat               ← baseline vs AI report
│   ├── files.f, run.do           ← file list / batch do-file
│   └── uvm_prelude.sv            ← compilation-unit prelude (not part of the TB)
├── aidvo/                        ← Python platform (pure Python + Gymnasium + SB3)
│   ├── config.py                 ← YAML config, action-space decoding
│   ├── boundary/                 ← SimRunner + scalar transcript/report parsers
│   ├── env/coverage_env.py       ← Gymnasium black-box environment
│   ├── agents/                   ← baseline (AI off), SB3 trainer, policy rollout
│   ├── analysis/                 ← history records + comparison report
│   └── cli.py                    ← check-config / compile / baseline / train / rollout / compare
├── docs/
│   ├── 00_original_testbench_readme.md   ← preserved original repository README
│   ├── 01_design_specification.md        ← async FIFO spec (sample design)
│   ├── 02_testplan.md                    ← test plan (sample design)
│   ├── 03_testbench_architecture.md      ← UVM architecture (sample design)
│   ├── 04_aidvo_architecture.md          ← AId-VO architecture + diagrams
│   ├── 05_aidvo_usage_guide.md           ← full usage guide
│   ├── 06_aidvo_compliance.md            ← non-modification rules & enforcement
│   └── 07_aidvo_comparison_methodology.md← with-AI vs without-AI methodology
├── tests/test_parsers.py         ← self-tests (no simulator/training required)
├── results/                      ← campaign outputs (see results/README.md)
├── models/                       ← trained policies (created by `aidvo train`)
└── AId-VO_repository.zip         ← downloadable ZIP of the entire tree
```

---

## Quick start

### Prerequisites

* QuestaSim on `PATH` (`vlib`, `vlog`, `vsim`, `vcover`)
* Python 3.9+: `pip install -r requirements.txt`

### Windows (interactive)

```bat
sim\aidvo_menu.bat
```

Pick `[1]` to compile, `[3]` for the **baseline (AI off)**, `[4]` for an
**AI run** (choose PPO/A2C/DQN, timesteps, workers, runs, seed base, coverage
goal), `[6]` for the **comparison report**.

### Command line (any OS)

```bash
# 0) validate config
python -m aidvo.cli check-config -c config/aidvo_config.yaml

# 1) compile the unmodified testbench
python -m aidvo.cli compile -c config/aidvo_config.yaml

# 2) BASELINE — AI/ML OFF (constrained-random regression)
python -m aidvo.cli baseline -c config/aidvo_config.yaml --runs 40 --seed-base 1000

# 3) TRAIN — AI/ML ON (local stable-baselines3)
python -m aidvo.cli train -c config/aidvo_config.yaml --algo ppo --timesteps 2000 --n-envs 2

# 4) EVALUATE the trained policy
python -m aidvo.cli rollout -c config/aidvo_config.yaml \
    --model models/ppo/final --runs 40 --seed-base 1000 --goal 95 -o results/ai

# 5) SIDE-BY-SIDE report (coverage progress + total simulation time)
python -m aidvo.cli compare --baseline results/baseline --ai results/ai \
    -o results/comparison
```

The deliverable report lands in
`results/comparison/comparison_report.md` (+ `coverage_progress.csv/.png`).

---

## How it works

```text
        action (seed / test / plusargs)              transcript (scalars only)
  agent ───────────────────────────────►  black-box simulation  ─────────────► agent
  PPO / A2C / DQN   ▲                    (unmodified UVM TB,                   reward =
  (stable-baselines3│                     QuestaSim, own work dir)              Δcoverage%
   runs locally) ───┴───────────────────────────────────────────────────────── − errors + …
```

* **Environment** — one Gymnasium step = one boundary simulation
  (`aidvo/env/coverage_env.py`), observation `Box(10)`, action
  `Discrete(320)` = tests(10) × seed-buckets(8) × clock-profiles(4).
* **Reward** — positive for coverage increments and valid runs; penalties for
  UVM errors/warnings, stagnation and (small) wall time; bonus on goal.
* **Parallel sampling** — `SubprocVecEnv` runs N simulations concurrently in
  private working directories.
* **Baseline** — identical pipeline with AI disabled: round-robin tests,
  random seeds, default clock profile.
* **Comparison** — both campaigns write the same `history.json` schema; the
  report is computed purely from recorded runs (see
  `docs/07_aidvo_comparison_methodology.md`).

Full details: [`docs/04_aidvo_architecture.md`](docs/04_aidvo_architecture.md) ·
Usage: [`docs/05_aidvo_usage_guide.md`](docs/05_aidvo_usage_guide.md) ·
Rules: [`docs/06_aidvo_compliance.md`](docs/06_aidvo_compliance.md)

---

## Sample design

The bundled sample is an **asynchronous FIFO verified with a full UVM
environment** (dual clock domains, Gray-code pointers, scoreboard, functional
coverage, 10 tests incl. clock-ratio and boundary-condition tests). Its
documentation is preserved in
[`docs/00_original_testbench_readme.md`](docs/00_original_testbench_readme.md)
plus `docs/01–03`.

The testbench exposes the boundary knobs AId-VO steers:
`+UVM_TESTNAME` (test selection), `-sv_seed` (randomization seed) and
`+WCLK_HALF_NS/+RCLK_HALF_NS` (constraint-randomization clock profiles that
reshape full/empty corner-case traffic).

---

## Running the tests (no simulator needed)

```bash
python tests/test_parsers.py
```

Covers config/action decoding, scalar transcript parsing, report-total
parsing, command expansion, history persistence and the comparison report.

---

## Downloadable ZIP

`AId-VO_repository.zip` at the repository root contains the complete tree
(RTL, testbench, platform, scripts, docs, config) ready to download and run
locally.

---

## License

This project is licensed under the [MIT License](LICENSE).
