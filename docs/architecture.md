# AId-UVO-RT Architecture

**AI-Driven Universal Verification Optimization — Runtime / Instantaneous**

This document describes the architecture of the optimizer framework, the two optimizer modes
(SRIE runtime introspection and simulator blackbox), the local RL/ANN engine, and how they
integrate with Siemens QuestaSim and a SystemVerilog/UVM testbench **without modifying any
RTL or testbench source code**.

## 1. Goals & Design Principles

| Principle | Meaning |
|-----------|---------|
| **Universal** | Agnostic to HDL/HVL/HLS language and verification methodology (UVM/OVM/native SV). |
| **Non-intrusive** | Zero changes to RTL source, UVM TB, sequences, or methodology code. |
| **Runtime / instantaneous** | AI agents act on events mid-simulation, not after the run ends. |
| **Local AI only** | Training & inference run on the local CPU. No external AI model APIs. |
## 2. High-Level Block Diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER / REGRESSION CONTROL                           │
│  run_sim.bat  ◄─── interactive menu (mode, AI on/off, RL algo, runs, seeds) │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 ┌───────────────┐           ┌────────────────┐
 │   BASELINE    │           │    AI MODES    │
 │ (constrained  │           │                │
 │  random, no   │      ┌────┴────┐  ┌───────┴───────┐
 │   AI)         │      │  SRIE   │  │  BLACKBOX     │
 └───────┬───────┘      │ (runtime│  │ (post-run)    │
         │              │  introspection) │           │
         │              └──────┬───────┘  └─────┬─────┘
         │                     │                │
         ▼                     ▼                ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │                      SIMULATOR: QUESTASIM (Windows)                │
 │  ┌─────────────┐     ┌────────────────────────────────────────┐   │
 │  │  tb_top_*.sv│────►│  VPI plug-in: srie_vpi.dll  (SRIE only)│   │
 │  │  (wrapper,  │     │  - reads signal values                 │   │
 │  │   non-intrusive)│  │  - traverses hierarchy (vpi_iterate)   │   │
 │  └──────┬──────┘     │  - registers value-change/coverage CBs │   │
 │         │            │  - forces signal values (vpi_put_value)│   │
 │         │            │  - TCP server (localhost:<port>)       │   │
 │         │            └──────────┬────────────────────────────┘   │
 │         │ TCP socket            │ TCP socket                       │
 │         ▼ (blackbox: logs only) ▼                                │
 │  ┌────────────────────────────────────────────────────────────┐   │
 │  │  RTL + UVM Testbench (UNCHANGED — dv/, RTL/)               │   │
 │  │  async_fifo DUT, agents, drivers, monitors, scoreboard,    │   │
 │  │  coverage model — read-only observation via VPI only       │   │
 │  └────────────────────────────────────────────────────────────┘   │
 └────────────────────────────────────────────────────────────────────┘
                      │
                      ▼ (events / state / actions)
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PYTHON AI OPTIMIZER (optimizer/)                         │
│                                                                             │
│  ┌──────────────┐       ┌──────────────┐      ┌────────────────┐           │
│  │  SRIE AGENT  │◄──────│  VPI CLIENT  │      │ BLACKBOX AGENT │           │
│  │ (event-driven│       │  (TCP client)│      │ (post-run)     │           │
│  │  listener)   │       └──────┬───────┘      └───────┬────────┘           │
│  └──────┬───────┘              │                     │                     │
│         │                      │                     │                     │
│         ▼                      ▼                     ▼                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                LOCAL RL / ANN ENGINE (optimizer/rl/)                │   │
│  │  Q-learning  │  DQN (numpy ANN)  │  PPO  │  Reward  │  State/Action │   │
│  └─────────────┬───────────────────┴───────┴─────────┴───────────────┘   │
│                │                                                          │
│                ▼                                                          │
│       coverage DB, seed log, model checkpoints (results/<mode>/)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Mode Descriptions

### 3.1 SRIE — Simulator Runtime Introspection Engine (runtime / instantaneous)

The SRIE agent is embedded in a **hybrid framework** and acts as an event-driven
runtime peer to the simulator.

1. **Observe (introspection).** The VPI plug-in (`srie_vpi.dll`) is loaded into
   QuestaSim via `-pli`. It registers callbacks for value changes and covergroup
   samples, reads live signal values, and traverses the simulator hierarchy using
   `vpi_iterate` / `vpi_scan` (**hierarchical discovery + reflection**). No RTL or
   TB source is modified; the top-level wrapper `tb_top_srie.sv` only instantiates
   the DUT/TB and a passive VPI hook.
2. **Trigger.** When a coverage-relevant event fires (coverpoint stall, flag
   transition, coverage growth-rate drop), an event is dispatched over a TCP socket
   to the Python SRIE agent **instantly**, mid-simulation.
3. **Decide.** The Python agent encodes simulator state into an RL state vector and
   queries the local RL policy (Q-learning / DQN / PPO).
4. **Steer.** The chosen action is sent back through the **introspection interface**:
   the VPI plug-in forces signal values, re-seeds the random generator, or biases
   sequencer constraints — via `vpi_put_value` / simulator control calls, without
   touching HDL source.
5. **Loop.** Steps 1–4 repeat cycle-by-cycle until the coverage goal is met.

Because decisions are event-triggered and occur inside the running simulation,
there is **no waiting for the simulator to end** — satisfying the runtime /
instantaneous requirement.

### 3.2 Simulator Blackbox Optimizer

Treats QuestaSim as a blackbox. No simulator internals are accessed and nothing is
added to or modified in the HDL/TB/configs.

1. Run a constrained-random simulation.
2. After the run, parse `sim.log`, coverage database, reports, and control scripts.
3. Identify unhit / weakly hit coverpoints and which seeds exercise them.
4. Compute a new seed / constraint bias using the local RL agent.
5. Launch the next run with adjusted `+ntb_random_seed` and constraint plusargs.
6. Repeat until the coverage goal is met or the run budget is exhausted.

### 3.3 Baseline

Plain constrained-random regression with no AI. Serves as the reference for the
side-by-side comparison.

## 4. Python AI Optimizer (optimizer/)

All training and inference run **entirely locally** on the CPU using only
`numpy` (no TensorFlow/PyTorch/cloud APIs).

| Sub-package | Responsibility |
|-------------|----------------|
| `rl/` | RL algorithms: Q-learning, DQN (numpy MLP ANN), PPO; replay buffer; reward shaping; state encoder; action space |
| `srie/` | Event-triggered SRIE agent, VPI TCP client, hierarchical discovery/reflection, introspection (push stimulus back), event listener |
| `blackbox/` | Blackbox agent, log parser, seed manager, loop controller, report parser |
| `coverage/` | Live coverage tracker; coverage-database merge/parse |
| `utils/` | Configuration, logging, CSV/JSON I/O |
| `core.py` | Multi-mode orchestrator (CLI entry point) |

### Data flow (SRIE)

```
sim event (VPI callback)
   │
   ▼
VPI plug-in ───TCP───> Python SRIE agent (vpi_client)
   │                       │
   │                       ▼
   │              state_encoder (sim state → state vector)
   │                       │
   │                       ▼
   │              RL agent (Q-learning / DQN / PPO) → action
   │                       │
   │                       ▼
   │              action_space (action → seed/constraint/stimulus)
   │                       │
   └───────────TCP─────────┘
VPI plug-in applies action (vpi_put_value / re-seed / constraint bias)
```

### Data flow (Blackbox)

```
QuestaSim run N ───► sim.log + coverage DB + report
                           │
                           ▼
                 log_parser / report_parser
                           │
                           ▼
                 seed_manager (RL-guided new seed/constraints)
                           │
                           ▼
                 loop_controller launches run N+1
```

## 5. QuestaSim Integration

| File | Purpose |
|------|---------|
| `sim/Questa/run_sim.bat` | Interactive batch menu (mode, AI on/off, RL algo, runs, seeds, coverage goal) |
| `sim/Questa/run_srie.bat` | Launches SRIE mode (VPI DLL + do-file + Python agent) |
| `sim/Questa/run_blackbox.bat` | Launches blackbox mode (loop controller + runs) |
| `sim/Questa/run_baseline.bat` | Launches baseline constrained-random runs |
| `sim/Questa/build_vpi.bat` | Builds `srie_vpi.dll` with MSVC (requires `QUESTA_HOME`) |
| `sim/Questa/do_files/compile.do` | Compiles RTL + UVM testbench |
| `sim/Questa/do_files/run_*.do` | Per-mode Questa do-files |
| `sim/Questa/tb_top_*.sv` | Non-intrusive top-level wrappers |
| `sim/Questa/vpi/srie_vpi.c` | VPI plug-in source (C) |

The VPI plug-in is compiled separately and loaded by Questa via `-pli`. It does not
require any change to `RTL/` or `dv/`.

## 6. Non-Intrusiveness Guarantee

| Asset | Modified by AId-UVO-RT? |
|-------|-------------------------|
| `RTL/*.v` | ❌ No |
| `dv/**/*.sv` (UVM TB) | ❌ No |
| UVM methodology classes | ❌ No |
| Test sequences | ❌ No |
| QuestaSim binary | ❌ No |

Additions only:
- VPI plug-in (external `.dll`, loaded via `-pli`) — SRIE only.
- Top-level wrappers under `sim/Questa/` — instantiate existing DUT/TB.
- External Python scripts under `optimizer/`.

The optimizer can therefore be dropped in front of **any** QuestaSim /
SystemVerilog / UVM regression with zero changes to existing verification IP.

## 7. Local-Only AI Policy

- ✅ All model training runs locally (CPU).
- ✅ All inference runs locally.
- ❌ No external AI model API calls (Gemini, Claude, Codex, OpenAI, Anthropic, …).
- ❌ No model weights uploaded/downloaded.
- ❌ No telemetry sent to any remote service.

If `numpy` is unavailable, the RL engine falls back to pure-Python tabular
Q-learning so the framework still runs offline.

## 8. Comparison Methodology

Three configurations are compared side-by-side:

1. **Baseline** — constrained-random, no AI
2. **SRIE** — AI + simulator runtime (instantaneous steering)
3. **Blackbox** — AI + simulator blackbox (post-run seed/constraint adjustment)

Recorded per configuration:
- Functional coverage vs. simulation time (closure curves)
- Total simulation wall-clock time to reach the coverage goal
- Number of runs / seeds required
- Hard-to-hit (corner-case) coverpoint hit times
- Runs that failed to reach the goal within budget

Results are written to `results/<mode>/` (CSV + Markdown) and aggregated into
`results/comparison_results.md`.

---

*End of architecture document.*

| **Project-agnostic** | Same optimizer framework reused across ALU, FIFO, SoC, GPU, CPU, Memory, etc. |
