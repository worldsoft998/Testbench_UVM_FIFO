@echo off
::==============================================================================
:: AId-UVO-RT — QuestaSim Interactive Runner
:: AI-Driven Universal Verification Optimization (Runtime / Instantaneous)
::
:: Interactive menu for selecting the optimizer mode and running simulations.
::
:: Modes:
::   1. Baseline   — constrained-random, no AI
::   2. SRIE       — AI + simulator runtime (instantaneous, VPI introspection)
::   3. Blackbox   — AI + simulator blackbox (post-run seed/constraint adjust)
::   4. Compare    — all three, side-by-side report
::
:: NOTE: No simulation or training code runs during repository creation.
::       Run this batch file manually in your local environment.
::==============================================================================

setlocal EnableDelayedExpansion

:: ---- Resolve paths ----------------------------------------------------------
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%..\.."
set "PYTHON=python"

:: Defaults
set "MODE=baseline"
set "AI=on"
set "RL=dqn"
set "RUNS=10"
set "SEEDS=random"
set "GOAL=100"
set "MAXTIME=1ms"
set "OUTDIR="

title AId-UVO-RT - QuestaSim Interactive Runner

call :show_banner

::-----------------------------------------------------------------------------
:: [1] Mode
::-----------------------------------------------------------------------------
:menu_mode
echo.
echo [1] Select mode:
echo     1. Baseline   (no AI)
echo     2. SRIE       (AI + simulator runtime)
echo     3. Blackbox   (AI + simulator blackbox)
echo     4. Compare    (all three, side-by-side report)
set /p M_CHOICE="Choice [1-4] [1]: "
if "!M_CHOICE!"=="" set M_CHOICE=1
if "!M_CHOICE!"=="1" set MODE=baseline
if "!M_CHOICE!"=="2" set MODE=srie
if "!M_CHOICE!"=="3" set MODE=blackbox
if "!M_CHOICE!"=="4" set MODE=compare
if not defined MODE goto menu_mode

::-----------------------------------------------------------------------------
:: [2] AI/ML on/off
::-----------------------------------------------------------------------------
:menu_ai
echo.
echo [2] Enable AI/ML? (on/off) [on]:
set /p AI_IN="> "
if "!AI_IN!"=="" set AI_IN=on
set AI_IN=!AI_IN:~0,1!
if "!AI_IN!"=="o" set AI=on
if "!AI_IN!"=="O" set AI=on
if "!AI_IN!"=="n" set AI=off
if "!AI_IN!"=="N" set AI=off
if not "!AI!"=="on" if not "!AI!"=="off" goto menu_ai

::-----------------------------------------------------------------------------
:: [3] RL algorithm
::-----------------------------------------------------------------------------
:menu_rl
echo.
echo [3] RL algorithm: 1=qlearning 2=dqn 3=ppo [2]:
set /p RL_IN="> "
if "!RL_IN!"=="" set RL_IN=2
if "!RL_IN!"=="1" set RL=qlearning
if "!RL_IN!"=="2" set RL=dqn
if "!RL_IN!"=="3" set RL=ppo
::-----------------------------------------------------------------------------
:: [4] Number of runs
::-----------------------------------------------------------------------------
:menu_runs
echo.
echo [4] Number of runs [10]:
set /p R_IN="> "
if "!R_IN!"=="" set R_IN=10
set /a R_TEST=!R_IN! 2>nul
if %R_TEST% LEQ 0 (echo Invalid number. & goto menu_runs)
set RUNS=!R_IN!

::-----------------------------------------------------------------------------
:: [5] Seeds
::-----------------------------------------------------------------------------
:menu_seeds
echo.
echo [5] Seeds: random | fixed:N | list:a,b,c [random]:
set /p S_IN="> "
if "!S_IN!"=="" set S_IN=random
set SEEDS=!S_IN!

::-----------------------------------------------------------------------------
:: [6] Coverage goal
::-----------------------------------------------------------------------------
:menu_goal
echo.
echo [6] Coverage goal in %% [100]:
set /p G_IN="> "
if "!G_IN!"=="" set G_IN=100
set /a G_TEST=!G_IN! 2>nul
if %G_TEST% LSS 0 (echo Invalid percentage. & goto menu_goal)
if %G_TEST% GTR 100 (echo Invalid percentage. & goto menu_goal)
set GOAL=!G_IN!

::-----------------------------------------------------------------------------
:: [7] Max simulation time per run
::-----------------------------------------------------------------------------
:menu_maxtime
echo.
echo [7] Max simulation time per run (e.g. 1ms, 100ns, 1s) [1ms]:
set /p T_IN="> "
if "!T_IN!"=="" set T_IN=1ms
set MAXTIME=!T_IN!

::-----------------------------------------------------------------------------
:: [8] Output directory
::-----------------------------------------------------------------------------
:menu_out
echo.
echo [8] Output directory [results\%MODE%]:
set /p O_IN="> "
if "!O_IN!"=="" set OUTDIR=results\%MODE%
set OUTDIR=!O_IN!

::-----------------------------------------------------------------------------
:: Summary
::-----------------------------------------------------------------------------
echo.
echo ============================================================================
echo  Starting %MODE% mode
echo    AI/ML        : %AI%
echo    RL algorithm : %RL%
echo    Runs         : %RUNS%
echo    Seeds        : %SEEDS%
echo    Coverage goal: %GOAL%%%
echo    Max time/run : %MAXTIME%
echo    Output dir   : %OUTDIR%
echo ============================================================================

:: Set environment variables for the Python optimizer and do-files
set AID_UVO_MODE=%MODE%
set AID_UVO_AI_ON=%AI%
set AID_UVO_RL_ALGO=%RL%
set AID_UVO_NUM_RUNS=%RUNS%
set AID_UVO_SEED_MODE=%SEEDS%
set AID_UVO_COVERAGE_GOAL=%GOAL%
set AID_UVO_MAX_SIM_TIME=%MAXTIME%
set AID_UVO_OUTPUT_DIR=%OUTDIR%
set SRIE_VPI_PORT=5555

:: Dispatch to the selected mode
if "!MODE!"=="baseline" goto run_baseline
if "!MODE!"=="srie" goto run_srie
if "!MODE!"=="blackbox" goto run_blackbox
if "!MODE!"=="compare" goto run_compare

:run_baseline
echo.
echo Launching baseline (constrained-random) runs...
call "%SCRIPT_DIR%\run_baseline.bat"
goto :eof

:run_srie
echo.
echo Launching SRIE mode (AI + simulator runtime)...
call "%SCRIPT_DIR%\run_srie.bat"
goto :eof

:run_blackbox
echo.
echo Launching Blackbox mode (AI + simulator blackbox)...
call "%SCRIPT_DIR%\run_blackbox.bat"
goto :eof

:run_compare
echo.
echo Launching Compare mode (Baseline + SRIE + Blackbox)...
call "%SCRIPT_DIR%\run_baseline.bat"
call "%SCRIPT_DIR%\run_srie.bat"
call "%SCRIPT_DIR%\run_blackbox.bat"
echo.
echo ============================================================================
echo  Compare complete. See %OUTDIR% for per-mode results.
echo  Report template: docs/comparison_results.md
echo ============================================================================
goto :eof

:show_banner
echo.
echo ============================================================================
echo   AId-UVO-RT  —  QuestaSim Interactive Runner
echo   AI-Driven Universal Verification Optimization (Runtime / Instantaneous)
echo ============================================================================
goto :eof

endlocal

if not defined RL goto menu_rl
