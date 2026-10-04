@echo off
rem ---------------------------------------------------------------------------
rem AId-VO : run ONE simulation at the simulation boundary (no testbench changes).
rem   usage: run_single.bat [test] [seed] [wclk_half_ns] [rclk_half_ns]
rem Examples:
rem   run_single.bat fifo_concrnt_rw_test 1234 5 7
rem   run_single.bat fifo_almost_full_test 42 2 10
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0.."

set "TEST=%~1"
set "SEED=%~2"
set "WCLK=%~3"
set "RCLK=%~4"
if not defined TEST set "TEST=fifo_base_test"
if not defined SEED set "SEED=1"
if not defined WCLK set "WCLK=5"
if not defined RCLK set "RCLK=7"

vsim -64 -c -work "%cd%\work" fifo_tb -sv_seed %SEED% +UVM_TESTNAME=%TEST% +WCLK_HALF_NS=%WCLK% +RCLK_HALF_NS=%RCLK% -do "%cd%\sim\run.do"

endlocal
