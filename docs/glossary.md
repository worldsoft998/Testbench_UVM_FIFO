# Glossary

**AId-UVO-RT terminology**

| Term | Definition |
|------|------------|
| **AId-UVO-RT** | AI-Driven Universal Verification Optimization — Runtime / Instantaneous. The optimization framework described in this repository. |
| **SRIE** | Simulator Runtime Introspection Engine. The runtime/introspective optimization mode that hooks into the simulator via VPI/DPI and steers coverage in real time. |
| **VPI** | Verification Procedural Interface. A standard IEEE PLI interface for accessing simulator internals (signals, hierarchy, callbacks) from C code. |
| **DPI** | Direct Programming Interface. SystemVerilog feature for calling C/C++ functions from SV and vice versa. |
| **PLI** | Program Language Interface. The original Verilog C interface to simulator internals (predecessor to VPI). |
| **VPI plug-in** | A compiled C shared library (`srie_vpi.dll`) loaded into QuestaSim via `-pli` that exposes live simulation state to the Python agent. |
| **Introspection interface** | The channel through which the optimizer reads simulator state and writes stimulus/actions back (VPI `vpi_get_value` / `vpi_put_value`). |
| **Hierarchical discovery & reflection** | Traversing the simulator's design hierarchy at runtime (via `vpi_iterate`/`vpi_scan`) to observe what changed, without reading RTL source. |
| **Blackbox optimizer** | Optimizer mode that treats QuestaSim as a blackbox, adjusting seeds/constraints based on post-run logs and coverage reports only. |
| **Coverage-driven** | Optimization guided by functional coverage: the RL agent targets coverpoints that are unhit or weakly hit. |
| **RL agent** | Reinforcement-learning agent (Q-learning / DQN / PPO) that selects actions (seed, constraint, stimulus bias) to maximize coverage growth. |
| **DQN** | Deep Q-Network — a neural-network-based Q-learning agent implemented here with pure `numpy`. |
| **PPO** | Proximal Policy Optimization — a local policy-gradient RL algorithm. |
| **Coverage closure** | Reaching the target functional coverage percentage (e.g., 100%). |
| **Coverage curve** | Plot of accumulated functional coverage vs. simulation time. |
| **Non-intrusive** | The optimizer does not modify any RTL or testbench source code; it observes and steers through simulator APIs only. |
| **Local AI** | All model training and inference run on the local machine; no external AI model APIs are used. |
| **Plusargs** | Command-line plus arguments passed to the simulator (e.g., `+ntb_random_seed=12345`) used to control seeds and constraints. |
| **Covergroup / coverpoint** | SystemVerilog functional coverage constructs; a coverpoint is a single coverage bin being tracked. |
| **UVM** | Universal Verification Methodology — the SystemVerilog verification methodology used by the reference testbench. |
| **QoR** | Quality of Results — here, measured by coverage closure speed and wall-clock simulation time. |
