# Simulator Blackbox Integration Guide

**AI verification optimizer with simulator as blackbox — post-run seed/constraint adjustment**

---

## 1. Overview

The blackbox optimizer treats QuestaSim as a **blackbox**: no simulator internals are accessed, and nothing is added to or modified in the HDL, testbench, or configuration files.

After each simulation run, the Python blackbox agent parses the simulator log, coverage database, and reports, identifies weakly-hit or unhit coverpoints, computes a new seed/constraint bias using the local RL agent, and launches the next run with adjusted plusargs.

---

## 2. Components

| File | Role |
|------|------|
| `optimizer/blackbox/agent.py` | Blackbox agent (orchestrates post-run analysis + next-run launch) |
| `optimizer/blackbox/log_parser.py` | Parses `sim.log` and simulator reports |
| `optimizer/blackbox/seed_manager.py` | RL-guided seed & constraint adjustment |
| `optimizer/blackbox/loop_controller.py` | Controls the simulation run loop |
| `optimizer/blackbox/report_parser.py` | Parses coverage reports (covergroup hit/miss) |
| `sim/Questa/run_blackbox.bat` | Launches blackbox mode |
| `sim/Questa/do_files/run_blackbox.do` | Questa do-file for a single blackbox run |
| `sim/Questa/tb_top_blackbox.sv` | Blackbox top-level wrapper |

---

## 3. Run Blackbox Mode

```bat
cd sim\Questa
run_sim.bat
# Choose: 3. Blackbox
```

What happens:

1. `run_blackbox.bat` starts the blackbox loop controller.
2. Loop iteration N:
   a. Launch QuestaSim with `run_blackbox.do` and current seed/constraint plusargs (`+ntb_random_seed`, constraint overrides).
   b. Run completes → `sim.log` + coverage database + report produced.
   c. Blackbox agent parses `sim.log` and coverage report.
   d. RL agent computes a new seed / constraint bias.
   e. Loop continues until coverage goal met or run budget exhausted.
3. Outputs written to `results/blackbox/`.

---

## 4. Data Flow

```
Run N  ──►  QuestaSim  ──►  sim.log + coverage DB + report
                                       │
                                       ▼
                              log_parser / report_parser
                                       │
                                       ▼
                              identify unhit / weak coverpoints
                                       │
                                       ▼
                              RL agent (qlearning/dqn/ppo)
                              → new seed / constraint bias
                                       │
                                       ▼
                              loop_controller launches Run N+1
                              with adjusted +ntb_random_seed
```

---

## 5. Configuration

| Variable | Meaning | Default |
|----------|---------|---------|
| `BLACKBOX_RL_ALGO` | RL algorithm | `dqn` |
| `BLACKBOX_AI_ON` | Enable/disable AI | `1` |
| `BLACKBOX_COVERAGE_GOAL` | Coverage closure target (%) | `100` |
| `BLACKBOX_MAX_RUNS` | Maximum loop iterations | `10` |
| `BLACKBOX_SEED_MODE` | `random` / `fixed:N` / `list:a,b,c` | `random` |

Seed/constraint adjustment example:
- Run N used seed `12345`; coverpoint `cp_wfull.full` was unhit.
- RL agent selects a new seed bias and increases write-incidence constraint weight.
- Run N+1 launched with `+ntb_random_seed=67890 +winc_bias=high`.

---

## 6. Non-Intrusiveness Checklist

- [ ] `RTL/*.v` — not modified
- [ ] `dv/**/*.sv` — not modified
- [ ] UVM methodology — not modified
- [ ] No simulator internals accessed
- [ ] Control is via standard plusargs and post-run log/report parsing only

---

## 7. Troubleshooting

| Issue | Fix |
|-------|-----|
| Coverage report not found | Ensure `run_blackbox.do` generates a coverage report; check `coverage report` / `vcover` commands |
| Seed/constraint not applied | Confirm plusargs are passed to `vsim` and the TB reads them (`$value$plusargs`) |
| Loops never terminate | Check `BLACKBOX_MAX_RUNS` and `BLACKBOX_COVERAGE_GOAL` are reachable |

---

*End of blackbox integration guide.*
