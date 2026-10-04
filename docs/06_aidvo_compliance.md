# AId-VO Compliance: No Testbench Changes / No Coverage-Model Access

This document states the strict non-modification rules of the AId-VO project
and shows, rule by rule, where each one is enforced in the repository.

---

## 1. The rules

1. **No changes** of any kind may be made to the original testbench source
   (SystemVerilog/UVM or other).
2. **No explicit access, inspection, configuration, manipulation, mirroring or
   reproduction** of the coverage model is allowed - this includes covergroups,
   coverpoints, bins, SystemVerilog classes, sequence items, functions, states,
   metrics, variables, packages, hierarchy paths or any UVM objects.
3. The coverage interface is limited exclusively to:
   * scalar coverage percentages (from reports / UCDB summary),
   * UVM error/warning counts,
   * simulation transcript / log data.
4. Python code must **not** bind to simulator internals, access UVM objects,
   read/write DUT signals, or parse/reconstruct coverage bins or internal data
   structures.
5. Interaction is permitted **only** at the simulation boundary: reading
   coverage reports/logs and controlling simulation parameters (seeds,
   transaction/test selection, run options).
6. The RL environment, agent, coverage monitor/parser and all supporting
   scripts must be **universal** - applicable to any RTL project without
   per-project code modification.
7. These rules apply whether the testbench is supplied by the user or
   generated during the session.

---

## 2. How each rule is enforced

| # | Rule | Enforcement point in this repository |
|---|---|---|
| 1 | No testbench changes | The platform adds files **only** under `aidvo/`, `sim/`, `config/`, `docs/`, `tests/`, `results/`, `models/`. Nothing under `RTL/` or `dv/` is written by any script, batch file or Python module. The single added SystemVerilog file, `sim/uvm_prelude.sv`, is a *compilation-unit prelude outside the testbench* that makes `uvm_pkg` visible so the unmodified TB compiles. |
| 2 | No coverage-model access | No code path opens `fifo_coverage_model.sv` or any other DV source. The parser (`aidvo/boundary/transcript.py`) applies three configured regexes to whole log text and keeps scalar numbers only. It has no notion of covergroups/coverpoints/bins/UVM objects. |
| 3 | Scalar-only interface | Allowlist observed by the platform: (a) one scalar coverage percentage line, (b) `UVM_ERROR/UVM_WARNING/UVM_FATAL` report-summary counts, (c) simulated-time scalar, (d) wall-clock measured by the runner, (e) in `ucdb` mode the **total** row of a vendor summary report. The per-group rows of a report are never matched - `report_total_regex` anchors on `Total` only. |
| 4 | No binding / no DUT access | Interaction with the simulator is **process-level only**: `subprocess.run(argv)` with command templates from the config. There are no DPI/VPI/VHPI calls, no plusargs injected into the DUT, no waveform/signal parsing, no hierarchical references. |
| 5 | Simulation-boundary only | The complete *output* surface of the platform is argv tokens: `-sv_seed`, `+UVM_TESTNAME`, boundary plusargs (`+WCLK_HALF_NS/+RCLK_HALF_NS`), run-timeout, and report/merge tool invocations. The complete *input* surface is the transcript and coverage report files listed above. |
| 6 | Universality | All project-specific knowledge - test list, knob values, command templates, observation regexes, reward weights - lives in `config/aidvo_config.yaml`. `aidvo/` contains zero project-specific constants; porting = editing one YAML file (`check-config` validates it). |
| 7 | Applies to any TB | The same platform works for a testbench supplied by the user or generated later: the configuration contract is the only coupling point. |

---

## 3. The exact observation/actuation contract

```text
                    ┌───────────────────────────────────────────┐
   ACTUATION        │ allowed: -sv_seed, +UVM_TESTNAME,         │
   (Python → sim)   │ boundary plusargs, run options,           │
                    │ vcover merge/report, wall-clock timeout   │
                    └───────────────────────────────────────────┘
                    ┌───────────────────────────────────────────┐
   OBSERVATION      │ allowed: scalar coverage % (transcript    │
   (sim → Python)   │ or UCDB summary "Total"), UVM error/      │
                    │ warning/fatal counts, simulated time,     │
                    │ process exit status, wall-clock duration  │
                    └───────────────────────────────────────────┘
   FORBIDDEN in both directions:
   - reading/parsing HDL/HVL sources, covergroups/coverpoints/bins,
     UVM classes/sequences/config objects, hierarchy paths
   - driving/observing DUT signals, binding to simulator internals,
     mirroring or reconstructing the coverage model
```

---

## 4. Verifying compliance yourself

```bash
# 1) the testbench is byte-identical to the original (no output = unmodified)
git status --porcelain -- RTL dv

# 2) no Python module ever opens an HDL/HVL source file (no output = clean)
grep -rnE "(open|read_text|read_bytes)\([^)]*\.(sv|v)\b" aidvo/

# 3) no Python module parses coverage-model structures (no output = clean)
grep -rnE "covergroup[[:space:]]+[A-Za-z_]|coverpoint[[:space:]]+[A-Za-z_]" aidvo/

# 4) the parser's scalar-only behaviour is asserted by the test suite
python tests/test_parsers.py
```

All four checks were executed when this repository was assembled and produced
empty output / a full pass. `tests/test_parsers.py` also asserts that a
transcript containing message text like `UVM_ERROR file.sv(1) ...` is *not*
misread - only the report-summary counts are used.

---

## 5. Note on the provided sample design

The sample testbench (`RTL/` + `dv/`, async FIFO with UVM) was supplied with
this repository and is treated as a **fixed third-party artifact**: AId-VO
compiles it unchanged, runs it unchanged, and observes only what its report
phase and the vendor tooling publish as scalar summaries. The testbench's own
coverage model remains fully opaque to the platform.
