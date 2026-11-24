# SRIE Integration Guide

**Simulator Runtime Introspection Engine (SRIE) — VPI plug-in + Python agent**

---

## 1. Overview

SRIE hooks into the running QuestaSim simulator through a **VPI plug-in** (`srie_vpi.dll`) and a **Python SRIE agent** that communicates over a TCP socket. The agent observes live simulation state and pushes optimized stimulus back **instantly** when coverage-relevant events fire.

**Non-intrusive:** no RTL or UVM testbench source is modified. The VPI plug-in is loaded externally via `-pli`, and the top-level wrapper only instantiates the existing DUT/TB.

---

## 2. Components

| File | Role |
|------|------|
| `sim/Questa/vpi/srie_vpi.c` | VPI plug-in source (C). Compiled to `srie_vpi.dll`. |
| `sim/Questa/vpi/srie_vpi.h` | VPI plug-in header. |
| `sim/Questa/vpi/srie_vpi.proto` | VPI routine prototypes. |
| `sim/Questa/tb_top_srie.sv` | Non-intrusive top-level wrapper (instantiates DUT + TB + passive VPI hook). |
| `sim/Questa/build_vpi.bat` | Builds the DLL with MSVC. |
| `sim/Questa/run_srie.bat` | Launches SRIE mode. |
| `sim/Questa/do_files/run_srie.do` | Questa do-file for SRIE. |
| `optimizer/srie/agent.py` | Event-triggered SRIE agent (Python). |
| `optimizer/srie/vpi_client.py` | TCP client to the VPI plug-in. |
| `optimizer/srie/discovery.py` | Hierarchical discovery & reflection. |
| `optimizer/srie/introspection.py` | Push stimulus back into the simulation. |
| `optimizer/srie/event_listener.py` | Event-driven listener loop. |

---

## 3. Build the VPI Plug-in

From a Windows developer command prompt:

```bat
set QUESTA_HOME=C:\Siemens\Questa\<version>
cd sim\Questa
build_vpi.bat
```

`build_vpi.bat` compiles `srie_vpi.c` with `cl.exe` using `${QUESTA_HOME}/include` for VPI headers and produces `sim\Questa\vpi\srie_vpi.dll`.

---

## 4. Run SRIE Mode

```bat
cd sim\Questa
run_sim.bat
# Choose: 2. SRIE
```

What happens:

1. `run_srie.bat` launches QuestaSim with `-pli sim\Questa\vpi\srie_vpi.dll` and `run_srie.do`.
2. The VPI plug-in starts a TCP server on `localhost:<port>` (default 5555).
3. The Python SRIE agent connects as a TCP client.
4. The VPI plug-in registers value-change / coverage-sample callbacks.
5. On a trigger event, the plug-in sends simulator state to the agent over TCP.
6. The agent runs the local RL policy and sends an action back.
7. The plug-in applies the action (`vpi_put_value`, re-seed, constraint bias).
8. Steps 4–7 repeat until the coverage goal is met.

---

## 5. VPI Plug-in Details

### 5.1 Exported routines

- `vpi_start_server(port)` — starts the Winsock TCP server inside the simulator.
- `vpi_poll_events()` — non-blocking poll for queued simulation events.
- `vpi_read_signal(handle)` — reads a signal value by hierarchical path.
- `vpi_force_signal(handle, value)` — forces a signal value (`vpi_put_value`).
- `vpi_register_callback(cb_type, ...)` — registers a VPI callback.

### 5.2 Callback types observed

| Callback | What it signals |
|----------|-----------------|
| `cbValueChange` | A monitored signal changed value |
| `cbStartOfSimulation` | Simulation start |
| `cbEndOfSimulation` | Simulation end |
| coverage sample hooks | Covergroup sampled (vendor-specific) |

---

## 6. Python SRIE Agent Flow

```
VPI callback (event)
   │
   ▼
vpi_client (TCP recv: sim state)
   │
   ▼
discovery (hierarchical reflection — what changed?)
   │
   ▼
state_encoder (→ RL state vector)
   │
   ▼
RL agent (qlearning/dqn/ppo) → action
   │
   ▼
introspection (→ seed/constraint/stimulus command)
   │
   ▼
vpi_client (TCP send: action)
   │
   ▼
VPI plug-in applies (vpi_put_value / re-seed)
```

The agent acts **instantly** on the event — there is no wait for the simulator run to end.

---

## 7. Configuration

SRIE behavior is controlled via environment variables / batch menu:

| Variable | Meaning | Default |
|----------|---------|---------|
| `SRIE_VPI_PORT` | TCP port for VPI ↔ Python agent | `5555` |
| `SRIE_RL_ALGO` | RL algorithm | `dqn` |
| `SRIE_AI_ON` | Enable/disable AI | `1` |
| `SRIE_COVERAGE_GOAL` | Coverage closure target (%) | `100` |
| `SRIE_MAX_RUNS` | Number of regression runs | `10` |

---

## 8. Non-Intrusiveness Checklist

- [ ] `RTL/*.v` — not modified
- [ ] `dv/**/*.sv` — not modified
- [ ] UVM methodology — not modified
- [ ] Only addition: `srie_vpi.dll` (loaded via `-pli`) + `tb_top_srie.sv` wrapper

---

## 9. Troubleshooting

| Issue | Fix |
|-------|-----|
| VPI DLL fails to load | Verify `-pli` path and that `srie_vpi.dll` was built with the matching Questa version |
| Python agent connection refused | Confirm VPI server started (`vpi_start_server`) and port matches `SRIE_VPI_PORT` |
| No events received | Verify callbacks are registered and monitored signals actually toggle |
| Actions not applied | Confirm `vpi_put_value` / force succeeds; check Questa error log |

---

*End of SRIE integration guide.*
