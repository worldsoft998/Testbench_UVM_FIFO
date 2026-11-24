# AI-Driven Universal Verification Optimization (AId-UVO-RT)

**Runtime / Instantaneous AI-Based Coverage-Driven Hardware Verification Acceleration**

A project-agnostic, universal, AI (Reinforcement Learning)-based, coverage-driven hardware RTL verification optimization framework. It works with **any** 3rd-party testbench written in any HDL / HVL / HLS language and any verification methodology (UVM, OVM, native SV, etc.) **without modifying or adding a single line of the original HDL or testbench source code**.

> **Status:** Framework complete. Target simulator: **Siemens QuestaSim (Windows)**. Target DUT/TB: **SystemVerilog / UVM**. RL/ANN engine: **Python, 100% local** (no external AI model APIs).

## Table of Contents

- [Overview](#overview)
- [The Two Optimizers](#the-two-optimizers)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Batch File Menu Options](#batch-file-menu-options)
- [SRIE — Simulator Runtime Introspection Engine](#srie---simulator-runtime-introspection-engine)
- [Simulator Blackbox Optimizer](#simulator-blackbox-optimizer)
- [RL / ANN Engine](#rl--ann-engine)
- [Comparison Methodology](#comparison-methodology)
- [Sample Design (Reference)](#sample-design-reference)
- [Non-Intrusiveness Guarantee](#non-intrusiveness-guarantee)
- [Local-Only AI Policy](#local-only-ai-policy)
- [License](#license)

## Overview

**AId-UVO-RT** treats a running logic simulator as a dynamic white-box at runtime. An external Python-based RL agent observes live simulation state (coverage, hierarchy, signal values, event queue, control points) through the simulator's standard introspection interfaces (VPI / DPI / FLI / proprietary vendor APIs), and — the instant a coverage-relevant event fires — pushes an optimized stimulus change back into the simulation.

Because the agent lives **outside** the RTL and testbench, zero source code is touched. The same framework is reused for:

| Mode | Simulator view | How it steers |
|------|----------------|---------------|
| **SRIE** (runtime) | White-box via VPI/DPI introspection hooks | Event-triggered, cycle-accurate, in-sim steering |
| **Blackbox** | Blackbox via logs, coverage DBs, reports, scripts | Post-run analysis, seed/constraint adjustment between runs |
| **Baseline** | None | Plain constrained-random regression |

Both optimizers target **Siemens QuestaSim on Windows**, **SystemVerilog / UVM**, and a **Python-based local RL/ANN engine**.


## The Two Optimizers

### 1. SRIE — Simulator Runtime Introspection Engine (runtime / instantaneous)

A hybrid, coverage-guided optimization framework that inserts a runtime agent into the simulator's execution loop.

- Listens to the simulation via a **Python–VPI/DPI interaction bridge** (TCP socket).
- On a trigger event (coverage sample, flag transition, stalled coverage, etc.) it performs **Hierarchical Discovery + Reflection** to see what changed inside the testbench — without reading RTL source.
- Immediately pushes an **optimized stimulus change** back through the **Introspection interface** (force/adjust signals, bias sequencer constraints, re-seed).
- Acts **instantly**, without waiting for the simulator run to end.

### 2. Simulator Blackbox Optimizer

Treats QuestaSim as a blackbox. No simulator internals are accessed.

- Parses simulator logs, coverage databases, reports, and control scripts after each run.
- Runs **post-run analysis** to identify weak/unhit coverpoints and weak seeds.
- Adjusts **seeds and constraints** for the next simulation loop.
## Repository Structure

```text
AId-UVO-Framework/
│
├── README.md                      # This file
├── LICENSE                        # MIT License
├── requirements.txt               # Python dependencies (local-only)
├── .gitignore
├── build_zip.py                   # Builds a single downloadable ZIP of the repo
│
├── docs/                          # Documentation & architecture
│   ├── architecture.md            # Detailed architecture
│   ├── architecture.mmd           # Mermaid architecture diagrams
│   ├── usage_guide.md             # End-to-end usage guide
│   ├── srie_integration_guide.md  # SRIE + VPI integration guide
│   ├── blackbox_integration_guide.md  # Blackbox integration guide
│   ├── comparison_results.md      # Comparison methodology & results template
│   └── glossary.md                # Terminology
│
├── optimizer/                     # Python AI optimizer (100% local)
│   ├── __init__.py
│   ├── core.py                    # Multi-mode orchestrator
│   ├── config.py                  # Framework configuration
│   ├── logger.py                  # Structured logging
│   │
│   ├── rl/                        # RL / ANN engine
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Base RL agent
│   │   ├── q_learning.py          # Tabular Q-learning
│   │   ├── dqn.py                 # Deep Q-Network (pure-numpy ANN)
│   │   ├── ppo.py                 # Proximal Policy Optimization (local)
│   │   ├── replay_buffer.py       # Experience replay
│   │   ├── reward.py              # Coverage-guided reward shaping
│   │   ├── state_encoder.py       # Encode sim state -> RL state vector
│   │   └── action_space.py        # RL action space (seed/constraint/stimulus)
│   │
│   ├── coverage/                  # Coverage tracking & DB
│   │   ├── __init__.py
│   │   ├── tracker.py             # Live coverage tracker
│   │   └── database.py            # Merge/parse coverage DBs & reports
│   │
│   ├── srie/                      # SRIE (runtime introspection) agent
│   │   ├── __init__.py
│   │   ├── agent.py               # Event-triggered SRIE agent
│   │   ├── vpi_client.py          # TCP client to VPI plug-in
│   │   ├── discovery.py           # Hierarchical discovery & reflection
│   │   ├── introspection.py       # Push stimulus back into sim
│   │   └── event_listener.py      # Event-driven listener loop
│   │
│   ├── blackbox/                  # Simulator blackbox optimizer
│   │   ├── __init__.py
│   │   ├── agent.py               # Blackbox agent
│   │   ├── log_parser.py          # Parse sim logs / reports
│   │   ├── seed_manager.py        # Seed & constraint adjustment
│   │   ├── loop_controller.py     # Control simulation loops
│   │   └── report_parser.py       # Parse coverage reports
│   │
│   └── utils/                     # Helpers
│       ├── __init__.py
│       ├── config.py
│       ├── io.py                  # CSV / JSON / covergroup I/O
│       └── logger.py
│
├── sim/Questa/                    # QuestaSim scripts (Windows)
│   ├── run_sim.bat                # Main interactive batch menu
│   ├── run_srie.bat
│   ├── run_blackbox.bat
│   ├── run_baseline.bat
│   ├── build_vpi.bat              # Builds the VPI plug-in DLL
│   │
│   ├── do_files/
│   │   ├── compile.do             # Compile RTL + UVM TB
│   │   ├── run_srie.do            # SRIE run do-file
│   │   ├── run_blackbox.do        # Blackbox run do-file
│   │   └── run_baseline.do        # Baseline run do-file
│   │
│   ├── tb_top_srie.sv             # SRIE top-level (VPI hook instance, non-intrusive)
│   ├── tb_top_blackbox.sv         # Blackbox top-level
│   └── tb_top_baseline.sv         # Baseline top-level
│
│   └── vpi/                       # VPI / DPI plug-in source (C)
│       ├── srie_vpi.c             # VPI plug-in (compiled to srie_vpi.dll)
│       ├── srie_vpi.h
│       └── srie_vpi.proto
│
├── dv/                            # Existing UVM testbench (UNCHANGED)
│   ├── interface/, agents/, env/, package/, sequence/, tests/, transaction_/
│   └── (see original repository)
│
├── RTL/                           # Existing RTL (UNCHANGED)
│   ├── async_fifo.v, fifomem.v, sync_r2w.v, sync_w2r.v, wptr_full.v, rptr_empty.v
│
├── results/                       # Comparison output (populated by user runs)
│   ├── baseline/, srie/, blackbox/
│   └── README.md
│
└── examples/                      # Sample outputs & diagrams
    └── sample_run_output.txt
```

## Prerequisites

| Item | Requirement |
|------|-------------|
| Simulator | Siemens QuestaSim (Windows) — VPI / PLI / DPI support |
| OS | Windows (batch files) — Python scripts are cross-platform |
| Python | 3.8 or later (for the optimizer) |
| Python packages | `numpy` (local ANN / RL). See `requirements.txt` |
| Build tools | Microsoft Visual C++ (MSVC) for building the VPI `.dll` |
| Reference DUT/TB | The `RTL/` and `dv/` directories (SystemVerilog / UVM async FIFO) |

**No GPU required.** Training and inference run entirely on the CPU, locally.

## Installation

```powershell
# Clone the repository
git clone https://github.com/worldsoft998/Testbench_UVM_FIFO.git
cd Testbench_UVM_FIFO

# Create a Python virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install local-only Python dependencies
pip install -r requirements.txt
```

`requirements.txt`:

```
numpy>=1.21.0
```

> The optimizer uses **only** `numpy`. No TensorFlow / PyTorch / cloud AI APIs are required or used, keeping training and inference 100% local and offline.

## Quick Start

### Step 0 — Build the VPI plug-in (SRIE mode only)

From a Windows developer command prompt with `QUESTA_HOME` set:

```bat
cd sim\Questa
build_vpi.bat
```

This produces `sim\Questa\vpi\srie_vpi.dll`, loaded by QuestaSim via `-pli`.

### Step 1 — Launch the interactive simulator menu

```bat
cd sim\Questa
run_sim.bat
```

### Step 2 — Choose a mode

The batch menu lets you select:

1. **Baseline** — constrained-random, no AI
2. **SRIE** — AI + simulator runtime (instantaneous)
3. **Blackbox** — AI + simulator blackbox (post-run)
4. **Compare** — run all three and produce a side-by-side report

See [Batch File Menu Options](#batch-file-menu-options) for the full set of interactive choices (AI on/off, RL algorithm, number of runs, seeds, coverage goal, etc.).

## Batch File Menu Options

`run_sim.bat` presents an interactive menu. Every prompt has a sensible default (press Enter to accept).

| Prompt | Choices | Default | Meaning |
|--------|---------|---------|---------|
| Mode | `baseline`, `srie`, `blackbox`, `compare` | `baseline` | Which optimizer to run |
| AI/ML | `on`, `off` | `on` | Enable or disable the AI optimizer |
| RL algorithm | `qlearning`, `dqn`, `ppo` | `dqn` | RL algorithm used by the agent |
| Number of runs | integer | `10` | Simulation runs per regression |
| Seeds | `random`, `fixed:<n>`, `list:…` | `random` | Seed control |
| Coverage goal | percentage (0–100) | `100` | Functional coverage closure target |
| Max sim time per run | time string | `1ms` | Per-run simulation time budget |
| Output directory | path | `results/<mode>` | Where run artifacts are written |

Example interactive session:

```
============================================================
  AId-UVO-RT  —  QuestaSim Interactive Runner
============================================================

[1] Select mode:
    1. Baseline (no AI)
    2. SRIE      (AI + simulator runtime)
    3. Blackbox  (AI + simulator blackbox)
    4. Compare   (all three, side-by-side report)
Choice [1-4]: 2

[2] Enable AI/ML? (on/off) [on]:
[3] RL algorithm: 1=qlearning 2=dqn 3=ppo [2]:
[4] Number of runs [10]:
[5] Seeds: random | fixed:N | list:a,b,c [random]:
[6] Coverage goal in %% [100]:
[7] Max simulation time per run [1ms]:

Starting SRIE mode with AI=on, RL=dqn, runs=10, goal=100% ...
```

All selected values are passed through to the Python optimizer and the Questa do-files via plusargs and environment variables.

## SRIE — Simulator Runtime Introspection Engine

### Concept

The SRIE agent lives in a **hybrid framework**:

```
Simulator (QuestaSim, running)
   |
   |  VPI / DPI callbacks (value change, coverage sample, event)
   v
VPI plug-in (srie_vpi.dll)  <--- TCP socket --->  Python SRIE agent
   |                                                          |
   |  read signals / force values                             |  RL decides action
   v                                                          v
live RTL + UVM testbench                                  coverage-guided stimulus
```

### How it works (non-intrusive)

1. **Compile & load.** `srie_vpi.c` is compiled to `srie_vpi.dll` and loaded into QuestaSim via `-pli`. **No RTL or TB source is modified.** The only addition is a passive VPI hook instance in the top-level wrapper (`tb_top_srie.sv`), which does not drive any DUT signal.
2. **Observe.** The VPI plug-in registers callbacks for value changes and covergroup samples. It reads live signal values and traverses the simulator hierarchy via `vpi_iterate` / `vpi_scan` (hierarchical discovery + reflection).
3. **Trigger.** When a coverage-relevant event fires (e.g., a coverpoint stalls, a flag transitions, coverage growth rate drops), an event is dispatched over the TCP socket to the Python agent **instantly** — mid-simulation.
4. **Decide.** The Python RL agent encodes the simulator state into a state vector, queries the local RL policy (Q-learning / DQN / PPO), and selects an action.
5. **Steer.** The action is sent back through the introspection interface: the VPI plug-in forces signal values, adjusts sequencer constraints via plusargs, or re-seeds the random generator — all via VPI `vpi_put_value` / simulator control calls, without touching HDL source.
6. **Loop.** Steps 2–5 repeat cycle-by-cycle until the coverage goal is met.

### Files

- `optimizer/srie/agent.py` — event-triggered SRIE agent (Python)
- `optimizer/srie/vpi_client.py` — TCP client to the VPI plug-in
- `optimizer/srie/discovery.py` — hierarchical discovery & reflection
- `optimizer/srie/introspection.py` — push stimulus back into the simulation
- `optimizer/srie/event_listener.py` — event-driven listener loop
- `sim/Questa/vpi/srie_vpi.c` — VPI plug-in source (C)
- `sim/Questa/tb_top_srie.sv` — non-intrusive SRIE top-level wrapper

## Simulator Blackbox Optimizer

### Concept

Treats QuestaSim as a **blackbox** — no simulator internals are accessed, and nothing is added to or modified in the HDL/TB.

```
Run N  →  QuestaSim  →  logs + coverage DB + reports
                          |
                          v
              Python Blackbox Agent (post-run analysis)
                          |
                          |  adjust seeds / constraints
                          v
                     Run N+1 (new seed/constraints)
```

### How it works

1. Run a constrained-random simulation.
2. Parse `sim.log`, coverage database (`coverage.ucdb` / `test.vcd` / UCDM), and coverage reports.
3. Identify unhit / weakly hit coverpoints and which seeds exercise them.
4. Compute a new seed / constraint bias using the local RL agent.
5. Launch the next run with adjusted `+ntb_random_seed` and constraint plusargs.
6. Repeat until the coverage goal is met or the run budget is exhausted.

### Files

- `optimizer/blackbox/agent.py` — blackbox agent
- `optimizer/blackbox/log_parser.py` — parse sim logs / reports
- `optimizer/blackbox/seed_manager.py` — seed & constraint adjustment
- `optimizer/blackbox/loop_controller.py` — control simulation loops
- `optimizer/blackbox/report_parser.py` — parse coverage reports

## RL / ANN Engine

All training and inference is **entirely local** — no Gemini, Claude, Codex, OpenAI, or any external AI model API.

| Algorithm | File | Notes |
|-----------|------|-------|
| Q-learning (tabular) | `optimizer/rl/q_learning.py` | Good for small discrete action spaces |
| DQN (deep Q-network) | `optimizer/rl/dqn.py` | Pure-numpy MLP ANN with experience replay |
| PPO | `optimizer/rl/ppo.py` | Local policy-gradient method |

- State encoder: `optimizer/rl/state_encoder.py` — maps simulator state (coverage %, stalled coverpoints, flag states, recent transitions) to a fixed RL state vector.
- Action space: `optimizer/rl/action_space.py` — seed bias, constraint weights, write/read incidence, burst length, clock-ratio bias.
- Reward: `optimizer/rl/reward.py` — coverage growth rate + newly-hit coverpoints − time penalty.
- Replay buffer: `optimizer/rl/replay_buffer.py` — experience replay for DQN.

Run entirely offline; model checkpoints are saved to `results/<mode>/models/`.

## Comparison Methodology

Three configurations are compared side-by-side:

1. **Baseline** — constrained-random, no AI
2. **SRIE** — AI + simulator runtime (instantaneous steering)
3. **Blackbox** — AI + simulator blackbox (post-run seed/constraint adjustment)

For each configuration the framework records:

- Functional coverage vs. simulation time (coverage closure curves)
- Total simulation wall-clock time to reach the coverage goal
- Number of runs / seeds required
- Hard-to-hit (corner-case) coverpoint hit times
- Runs that failed to reach the goal within budget

Results are written to `results/<mode>/` as CSV + Markdown, and a combined `results/comparison_results.md` is generated.

> **Important:** No simulation or training code is executed during repository creation. All code is run manually by the user in their local environment. `results/` contains only templates/README until the user executes the batch files.

## Sample Design (Reference)

The `RTL/` and `dv/` directories contain a reference asynchronous FIFO UVM testbench (SystemVerilog / UVM). These files are **reference only** and are **never modified** by the optimizer — satisfying the non-intrusiveness requirement.

- DUT: `async_fifo` (dual-clock, Gray-coded pointers, CDC synchronizers)
- TB: UVM agents, drivers, monitors, scoreboard, coverage model

## Non-Intrusiveness Guarantee

| What | Touched by AId-UVO? |
|------|---------------------|
| RTL source (`RTL/*.v`) | ❌ No |
| UVM testbench (`dv/**/*.sv`) | ❌ No |
| UVM methodology code | ❌ No |
| Test sequences | ❌ No |
| Simulator binary | ❌ No |

The only additions are:

- A **VPI plug-in** (`srie_vpi.c` → `.dll`), loaded externally via `-pli` (SRIE mode only).
- **Top-level wrapper** files in `sim/Questa/` (`tb_top_srie.sv`, etc.) that instantiate the DUT + TB without changing `dv/` sources.
- **External Python scripts** in `optimizer/`.

This means the optimizer can be dropped in front of **any** QuestaSim / SystemVerilog / UVM regression with zero changes to the existing verification IP.

## Local-Only AI Policy

- ✅ All model training runs locally (CPU).
- ✅ All inference runs locally.
- ❌ No external AI model API calls (no Gemini, Claude, Codex, OpenAI, Anthropic, etc.).
- ❌ No model weights are uploaded or downloaded.
- ❌ No telemetry is sent to any remote service.

If `numpy` is unavailable, the RL engine degrades to a pure-Python tabular Q-learning fallback so the framework still runs offline.

## License

MIT License. See `LICENSE`.

---

*Built for the AId-UVO-RT project — Universal, AI-driven, coverage-driven RTL verification optimization. Non-intrusive by design. Local AI by principle.*

- Repeats until coverage goal is met or budget is exhausted.
