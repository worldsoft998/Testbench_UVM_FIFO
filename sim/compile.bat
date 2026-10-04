@echo off
rem ---------------------------------------------------------------------------
rem AId-VO : compile the async-FIFO RTL + UVM testbench with QuestaSim (Windows).
rem The testbench sources are compiled UNMODIFIED (sim\uvm_prelude.sv supplies
rem the UVM import inside the same compilation unit).
rem
rem UVM source discovery order:
rem   1) %UVM_SRC%           (explicit)
rem   2) %UVM_HOME%\src
rem   3) %QUESTA_HOME%\verilog_src\uvm-1800.2-2017\src
rem   4) %QUESTA_HOME%\verilog_src\uvm-1.2\src
rem   5) %QUESTA_HOME%\verilog_src\uvm-1.1d\src
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0.."

set "UVM_SRC_DIR="
if defined UVM_SRC if exist "%UVM_SRC%\uvm_pkg.sv" set "UVM_SRC_DIR=%UVM_SRC%"
if not defined UVM_SRC_DIR if defined UVM_HOME if exist "%UVM_HOME%\src\uvm_pkg.sv" set "UVM_SRC_DIR=%UVM_HOME%\src"
if not defined UVM_SRC_DIR if defined QUESTA_HOME (
  if exist "%QUESTA_HOME%\verilog_src\uvm-1800.2-2017\src\uvm_pkg.sv" set "UVM_SRC_DIR=%QUESTA_HOME%\verilog_src\uvm-1800.2-2017\src"
)
if not defined UVM_SRC_DIR if defined QUESTA_HOME (
  if exist "%QUESTA_HOME%\verilog_src\uvm-1.2\src\uvm_pkg.sv" set "UVM_SRC_DIR=%QUESTA_HOME%\verilog_src\uvm-1.2\src"
)
if not defined UVM_SRC_DIR if defined QUESTA_HOME (
  if exist "%QUESTA_HOME%\verilog_src\uvm-1.1d\src\uvm_pkg.sv" set "UVM_SRC_DIR=%QUESTA_HOME%\verilog_src\uvm-1.1d\src"
)

echo [AId-VO] Compiling testbench (sources unmodified) ...
vlib work
if errorlevel 1 exit /b 1

if defined UVM_SRC_DIR (
  echo [AId-VO] UVM sources: %UVM_SRC_DIR%
  vlog -64 -sv -mfcu "+incdir+%UVM_SRC_DIR%" "%UVM_SRC_DIR%\uvm_pkg.sv" sim\uvm_prelude.sv -f sim\files.f
) else (
  echo [AId-VO] WARNING: uvm_pkg.sv not found via UVM_SRC/UVM_HOME/QUESTA_HOME.
  echo [AId-VO]          Compiling against the Questa installation's UVM.
  echo [AId-VO]          If this fails, set UVM_SRC to your UVM src directory.
  vlog -64 -sv -mfcu sim\uvm_prelude.sv -f sim\files.f
)
if errorlevel 1 exit /b 1

echo [AId-VO] Compile done.
endlocal
