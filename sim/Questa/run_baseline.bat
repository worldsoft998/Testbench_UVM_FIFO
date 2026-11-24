@echo off
::==============================================================================
:: AId-UVO-RT — Baseline runner (constrained-random, no AI)
::==============================================================================
@echo off
setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
set "QUESTA_HOME=%QUESTA_HOME%"
if not defined QUESTA_HOME (
    echo WARNING: QUESTA_HOME is not set. vsim/vlog may not be on PATH.
)

:: Compile RTL + UVM testbench
echo [baseline] Compiling RTL + testbench ...
"%SCRIPT_DIR%..\..\sim\Questa\do_files\compile.do" >nul 2>&1
call vlog -f "%SCRIPT_DIR%\do_files\compile.do"
if %errorlevel% neq 0 (
    echo [baseline] Compile failed. Check compile.do.
    goto :eof
)
echo [baseline] Compile OK.

:: Read configured values (set by run_sim.bat) or defaults
set "RUNS=%AID_UVO_NUM_RUNS%"
if "!RUNS!"=="" set RUNS=10
set "GOAL=%AID_UVO_COVERAGE_GOAL%"
if "!GOAL!"=="" set GOAL=100
set "OUTDIR=%AID_UVO_OUTPUT_DIR%"
if "!OUTDIR!"=="" set OUTDIR=results\baseline
set "SEED_MODE=%AID_UVO_SEED_MODE%"
if "!SEED_MODE!"=="" set SEED_MODE=random
set "FIXED_SEED=%AID_UVO_FIXED_SEED%"
if "!FIXED_SEED!"=="" set FIXED_SEED=42
set "SEED_LIST=%AID_UVO_SEED_LIST%"

if not exist "%OUTDIR%\" mkdir "%OUTDIR%"

echo [baseline] Running %RUNS% constrained-random simulations ...
echo run,seed,mode,coverage_pct,goal_reached,wall_time_s > "%OUTDIR%\run_summary.csv"

set /a COUNT=1
:baseline_loop
if %COUNT% GTR %RUNS% goto baseline_done

:: Seed selection
set "SEED="
if "!SEED_MODE!"=="fixed" set SEED=!FIXED_SEED!
if "!SEED_MODE!"=="list" (
    :: Pick seed from comma-separated list by index
    for %%s in (!SEED_LIST!) do (
        if not defined SEED set SEED=%%s
    )
)
if not defined SEED set SEED=!COUNT!

:: Run simulation
echo [baseline] Run !COUNT! seed=!SEED!
set "START=%TIME%"
vsim -c -do "%SCRIPT_DIR%\do_files\run_baseline.do" +ntb_random_seed=!SEED! > "%OUTDIR%\run_!COUNT!.log" 2>&1

:: Extract coverage (heuristic: look for coverage % in sim.log / report)
set "COV=0.0"
for /f "tokens=1,2 delims=:" %%a in ('findstr /i /c:"Coverage" "%OUTDIR%\run_!COUNT!.log" 2^>nul') do (
    set "COV=%%b"
)
echo [baseline] Run !COUNT! coverage=!COV!%

echo !COUNT!,!SEED!,baseline,!COV!,0,0 >> "%OUTDIR%\run_summary.csv"

set /a COUNT=COUNT+1
goto baseline_loop

:baseline_done
echo [baseline] Complete. Results in %OUTDIR%
goto :eof
