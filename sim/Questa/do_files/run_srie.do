#==============================================================================
# AId-UVO-RT — SRIE run do-file
# Executed inside QuestaSim after the design is loaded.
# Design top-level and plusargs (+ntb_random_seed, +SRIE_PORT, +UVM_TESTNAME)
# are passed on the vsim command line by run_srie.bat.
#==============================================================================

# Run the simulation to completion (or until $finish / timeout).
# The VPI plug-in (loaded via -pli) runs its TCP server concurrently, so the
# Python SRIE agent can connect and steer the simulation while it runs.
run -all

# Keep QuestaSim alive until the batch file stops it (run_srie.bat taskkills
# vsim after the Python agent finishes). Comment out the next line to auto-exit.
# quit -f
