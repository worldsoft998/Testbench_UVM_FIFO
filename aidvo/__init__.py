"""
AId-VO - AI-Driven Verification Optimization
============================================

A universal, local-only RL platform that accelerates functional coverage
closure for ANY 3rd-party HDL/HVL testbench by steering simulations purely at
the simulation boundary (seeds, test selection, boundary plusargs).

Hard rules enforced by this package (see docs/06_aidvo_compliance.md):

* Never reads, parses or modifies HDL/HVL testbench sources.
* Never touches the coverage model (no covergroups/coverpoints/bins/UVM objects).
* Observation interface is limited to: scalar coverage percentages from the
  transcript or a UCDB summary report, UVM error/warning counts, and log data.
* All training/inference runs locally (Gymnasium + stable-baselines3) - no
  external AI model APIs are used anywhere in the codebase.
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
