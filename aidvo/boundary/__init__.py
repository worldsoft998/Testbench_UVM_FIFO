"""Sub-package containing the simulation-boundary interface of AId-VO.

Everything in here talks to the outside world exclusively through:

* simulator command lines (seeds, test selection, boundary plusargs),
* simulation transcripts / logs (UVM report-summary counts, scalar coverage
  percentages printed by the testbench report phase),
* scalar totals from coverage report files produced by the vendor tool.

No testbench source, no coverage-model structure and no simulator internals
are ever read or written.
"""
