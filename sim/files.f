// AId-VO QuestaSim compile file list (compile order matters).
// Paths are relative to the repository root (run `vlog -f sim/files.f` there).
// Compiled with:  vlog -sv -mfcu <uvm_pkg.sv> sim/uvm_prelude.sv -f sim/files.f

// RTL (plain Verilog, order irrelevant)
RTL/async_fifo.v
RTL/fifomem.v
RTL/sync_r2w.v
RTL/sync_w2r.v
RTL/wptr_full.v
RTL/rptr_empty.v

// UVM testbench
dv/package/fifo_tb_config_pkg.sv
dv/interface/async_fifo_if.sv
dv/transaction_/fifo_tranx.sv
dv/agents/fifo_sequencers.sv
dv/agents/fifo_write_driver.sv
dv/agents/fifo_read_driver.sv
dv/agents/fifo_write_monitor.sv
dv/agents/fifo_read_monitor.sv
dv/agents/fifo_write_agent.sv
dv/agents/fifo_read_agent.sv
dv/env/fifo_sb.sv
dv/env/fifo_coverage_model.sv
dv/env/fifo_env.sv
dv/sequence/fifo_write_sequence.sv
dv/sequence/fifo_read_sequence.sv
dv/sequence/fifo_single_write_sequence.sv
dv/sequence/fifo_single_read_sequence.sv
dv/tests/fifo_base_test.sv
dv/tests/fifo_reset_test.sv
dv/tests/fifo_single_write_read_test.sv
dv/tests/fifo_multiple_write_read_test.sv
dv/tests/fifo_write_only_test.sv
dv/tests/fifo_read_only_test.sv
dv/tests/fifo_almost_full_test.sv
dv/tests/fifo_almost_empty_test.sv
dv/tests/fifo_fwft_test.sv
dv/tests/fifo_concrnt_rw_test.sv
dv/tests/fifo_clock_ratio_test.sv
dv/fifo_tb.sv
