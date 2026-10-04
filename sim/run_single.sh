#!/usr/bin/env bash
#------------------------------------------------------------------------------
# AId-VO : run ONE simulation at the simulation boundary (no testbench changes).
#   usage: ./sim/run_single.sh [test] [seed] [wclk_half_ns] [rclk_half_ns]
# Examples:
#   ./sim/run_single.sh fifo_concrnt_rw_test 1234 5 7
#   ./sim/run_single.sh fifo_almost_full_test 42 2 10
#------------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."

TEST="${1:-fifo_base_test}"
SEED="${2:-1}"
WCLK="${3:-5}"
RCLK="${4:-7}"

vsim -64 -c -work "$(pwd)/work" fifo_tb \
  -sv_seed "$SEED" \
  "+UVM_TESTNAME=$TEST" \
  "+WCLK_HALF_NS=$WCLK" \
  "+RCLK_HALF_NS=$RCLK" \
  -do "$(pwd)/sim/run.do"
