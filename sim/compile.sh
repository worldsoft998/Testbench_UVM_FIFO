#!/usr/bin/env bash
#------------------------------------------------------------------------------
# AId-VO : compile the async-FIFO RTL + UVM testbench with QuestaSim.
# The testbench sources are compiled UNMODIFIED (sim/uvm_prelude.sv supplies
# the UVM import inside the same compilation unit).
#
# UVM source discovery order:
#   1) $UVM_SRC           (explicit)
#   2) $UVM_HOME/src
#   3) $QUESTA_HOME/verilog_src/uvm-1800.2-2017/src
#   4) $QUESTA_HOME/verilog_src/uvm-1.2/src
#   5) $QUESTA_HOME/verilog_src/uvm-1.1d/src
# If none is found, the script compiles without a local uvm_pkg and relies on
# the Questa installation providing UVM (adjust UVM_SRC if compilation fails).
#------------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."

UVM_SRC="${UVM_SRC:-}"
if [ -z "$UVM_SRC" ] && [ -n "${UVM_HOME:-}" ] && [ -f "$UVM_HOME/src/uvm_pkg.sv" ]; then
  UVM_SRC="$UVM_HOME/src"
fi
if [ -z "$UVM_SRC" ] && [ -n "${QUESTA_HOME:-}" ]; then
  for v in uvm-1800.2-2017 uvm-1.2 uvm-1.1d; do
    if [ -f "$QUESTA_HOME/verilog_src/$v/src/uvm_pkg.sv" ]; then
      UVM_SRC="$QUESTA_HOME/verilog_src/$v/src"
      break
    fi
  done
fi

echo "[AId-VO] Compiling testbench (sources unmodified) ..."
vlib work

if [ -n "$UVM_SRC" ] && [ -f "$UVM_SRC/uvm_pkg.sv" ]; then
  echo "[AId-VO] UVM sources: $UVM_SRC"
  vlog -64 -sv -mfcu "+incdir+$UVM_SRC" "$UVM_SRC/uvm_pkg.sv" sim/uvm_prelude.sv -f sim/files.f
else
  echo "[AId-VO] WARNING: uvm_pkg.sv not found via UVM_SRC/UVM_HOME/QUESTA_HOME."
  echo "[AId-VO]          Compiling against the Questa installation's UVM."
  echo "[AId-VO]          If this fails, set UVM_SRC to your UVM src directory."
  vlog -64 -sv -mfcu sim/uvm_prelude.sv -f sim/files.f
fi

echo "[AId-VO] Compile done."
