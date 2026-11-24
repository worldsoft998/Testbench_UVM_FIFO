#==============================================================================
# AId-UVO-RT — QuestaSim compile script
# Compiles the RTL (unchanged) and the UVM testbench (unchanged).
# Paths are relative to this do-file: sim/Questa/do_files/
#==============================================================================

vlib work
vmap work work

# ---- RTL (reference async FIFO - never modified) ----
vlog -sv ../../RTL/async_fifo.v
vlog -sv ../../RTL/fifomem.v
vlog -sv ../../RTL/sync_r2w.v
vlog -sv ../../RTL/sync_w2r.v
vlog -sv ../../RTL/wptr_full.v
vlog -sv ../../RTL/rptr_empty.v

# ---- UVM testbench (reference - never modified) ----
vlog -sv ../../dv/package/fifo_tb_config_pkg.sv
vlog -sv ../../dv/interface/async_fifo_if.sv
vlog -sv ../../dv/transaction_/fifo_tranx.sv

# Sequences
vlog -sv ../../dv/sequence/fifo_single_write_sequence.sv
vlog -sv ../../dv/sequence/fifo_single_read_sequence.sv
vlog -sv ../../dv/sequence/fifo_write_sequence.sv
vlog -sv ../../dv/sequence/fifo_read_sequence.sv

# Agents
vlog -sv ../../dv/agents/fifo_write_agent.sv
vlog -sv ../../dv/agents/fifo_write_driver.sv
vlog -sv ../../dv/agents/fifo_write_monitor.sv
vlog -sv ../../dv/agents/fifo_read_agent.sv
vlog -sv ../../dv/agents/fifo_read_driver.sv
vlog -sv ../../dv/agents/fifo_read_monitor.sv
vlog -sv ../../dv/agents/fifo_sequencers.sv

# Environment
vlog -sv ../../dv/env/fifo_env.sv
vlog -sv ../../dv/env/fifo_sb.sv
vlog -sv ../../dv/env/fifo_coverage_model.sv

# Tests
vlog -sv ../../dv/tests/fifo_base_test.sv
vlog -sv ../../dv/tests/fifo_reset_test.sv
vlog -sv ../../dv/tests/fifo_single_write_read_test.sv
vlog -sv ../../dv/tests/fifo_multiple_write_read_test.sv
vlog -sv ../../dv/tests/fifo_write_only_test.sv
vlog -sv ../../dv/tests/fifo_read_only_test.sv
vlog -sv ../../dv/tests/fifo_almost_full_test.sv
vlog -sv ../../dv/tests/fifo_almost_empty_test.sv
vlog -sv ../../dv/tests/fifo_fwft_test.sv
vlog -sv ../../dv/tests/fifo_concrnt_rw_test.sv
vlog -sv ../../dv/tests/fifo_clock_ratio_test.sv

echo "=== Compile done ==="
