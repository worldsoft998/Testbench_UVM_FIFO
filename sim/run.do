# AId-VO batch-mode do-file.
# Runs the selected test to completion, saves the per-run coverage database,
# and exits.  Selection happens entirely at the command line:
#   vsim -c -work <lib> fifo_tb -sv_seed <n> +UVM_TESTNAME=<test> \
#        +WCLK_HALF_NS=<n> +RCLK_HALF_NS=<n> -l <transcript> -do sim/run.do
run -all

# Save this run's coverage database next to the working directory of the run.
# `catch` keeps the run alive when coverage was not enabled (-coverage off),
# which is the normal mode when coverage is read from the transcript instead.
catch {vcover save aidvo_last_run.ucdb}

quit -f
