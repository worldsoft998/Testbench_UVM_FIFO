@echo off
rem ===========================================================================
rem  AId-VO  -  AI-Driven Verification Optimization
rem  Interactive QuestaSim launcher (Windows)
rem
rem  Offers selectable options for:
rem    - AI/ML ON or OFF
rem    - choice of RL algorithm (PPO / A2C / DQN)
rem    - number of runs, seed base, coverage goal, training timesteps
rem
rem  The testbench under dv\ and RTL\ is NEVER modified by this launcher.
rem
rem  Requirements on PATH: vsim/vlog (QuestaSim) and Python with the packages
rem  from requirements.txt installed.  Override the interpreter with
rem  "set AIDVO_PY=py -3" if needed.
rem ===========================================================================
setlocal EnableDelayedExpansion
title AId-VO QuestaSim Launcher
cd /d "%~dp0.."

if not defined AIDVO_PY  set "AIDVO_PY=python"
if not defined AIDVO_CFG set "AIDVO_CFG=config\aidvo_config.yaml"

:menu
echo.
echo =============================================================
echo   AId-VO  -  AI-Driven Verification Optimization
echo   QuestaSim launcher  (testbench sources are never modified)
echo =============================================================
echo   [1] Compile testbench (QuestaSim)
echo   [2] Run a single simulation
echo   [3] BASELINE  - AI/ML OFF  (constrained-random regression)
echo   [4] AI RUN    - train RL policy, then evaluate it
echo   [5] AI EVAL   - evaluate an existing trained model
echo   [6] COMPARE   - baseline vs AI side-by-side report
echo   [7] Check AId-VO configuration
echo   [8] Exit
echo =============================================================
set "CHOICE="
set /p CHOICE="Select an option [1-8]: "

if "%CHOICE%"=="1" goto compile
if "%CHOICE%"=="2" goto single
if "%CHOICE%"=="3" goto baseline
if "%CHOICE%"=="4" goto ai_train
if "%CHOICE%"=="5" goto ai_eval
if "%CHOICE%"=="6" goto compare
if "%CHOICE%"=="7" goto checkcfg
if "%CHOICE%"=="8" goto eof
echo [AId-VO] Unknown option "%CHOICE%".
goto menu

:compile
call sim\compile.bat
goto menu

:single
set "TEST="
set "SEED="
set "WCLK="
set "RCLK="
set /p TEST="Test name [fifo_base_test]: "
set /p SEED="Random seed [1]: "
set /p WCLK="Write clock half-period ns [5]: "
set /p RCLK="Read clock half-period ns [7]: "
if not defined TEST set "TEST=fifo_base_test"
if not defined SEED set "SEED=1"
if not defined WCLK set "WCLK=5"
if not defined RCLK set "RCLK=7"
call sim\run_single.bat %TEST% %SEED% %WCLK% %RCLK%
goto menu

:baseline
echo --- BASELINE run: AI/ML is OFF (plain constrained-random regression) ---
set "RUNS="
set "SEEDBASE="
set /p RUNS="Number of runs [40]: "
set /p SEEDBASE="Seed base [1000]: "
if not defined RUNS set "RUNS=40"
if not defined SEEDBASE set "SEEDBASE=1000"
call sim\run_baseline.bat %RUNS% %SEEDBASE%
goto menu

:ai_train
echo --- AI RUN: train an RL policy at the simulation boundary ---
set "ALGO="
echo   RL algorithm:  [1] PPO   [2] A2C   [3] DQN
set /p ALGO="Select algorithm [1]: "
if not defined ALGO set "ALGO=1"
if "%ALGO%"=="1" set "ALGONAME=ppo"
if "%ALGO%"=="2" set "ALGONAME=a2c"
if "%ALGO%"=="3" set "ALGONAME=dqn"
if not defined ALGONAME (echo [AId-VO] Invalid algorithm choice.& set "ALGONAME=ppo")
set "TIMESTEPS="
set "NENVS="
set "RUNS="
set "SEEDBASE="
set "GOAL="
set /p TIMESTEPS="Training timesteps (approx. #simulations) [2000]: "
set /p NENVS="Parallel workers for sampling [2]: "
set /p RUNS="Evaluation runs after training [40]: "
set /p SEEDBASE="Seed base [1000]: "
set /p GOAL="Coverage goal % [95]: "
if not defined TIMESTEPS set "TIMESTEPS=2000"
if not defined NENVS set "NENVS=2"
if not defined RUNS set "RUNS=40"
if not defined SEEDBASE set "SEEDBASE=1000"
if not defined GOAL set "GOAL=95"
echo [AId-VO] Training %ALGONAME% for %TIMESTEPS% steps with %NENVS% workers ...
%AIDVO_PY% -m aidvo.cli train -c %AIDVO_CFG% --algo %ALGONAME% --timesteps %TIMESTEPS% --n-envs %NENVS%
if errorlevel 1 (echo [AId-VO] Training failed.& goto menu)
echo [AId-VO] Evaluating the trained policy ...
%AIDVO_PY% -m aidvo.cli rollout -c %AIDVO_CFG% --model models\%ALGONAME%\final --runs %RUNS% --seed-base %SEEDBASE% --goal %GOAL% -o results\ai
goto menu

:ai_eval
echo --- AI EVAL: rollout an existing trained model ---
set "ALGO="
echo   Model of:  [1] PPO   [2] A2C   [3] DQN
set /p ALGO="Select algorithm [1]: "
if not defined ALGO set "ALGO=1"
if "%ALGO%"=="1" set "ALGONAME=ppo"
if "%ALGO%"=="2" set "ALGONAME=a2c"
if "%ALGO%"=="3" set "ALGONAME=dqn"
if not defined ALGONAME (echo [AId-VO] Invalid algorithm choice.& set "ALGONAME=ppo")
set "RUNS="
set "SEEDBASE="
set "GOAL="
set /p RUNS="Number of runs [40]: "
set /p SEEDBASE="Seed base [5000]: "
set /p GOAL="Coverage goal % [95]: "
if not defined RUNS set "RUNS=40"
if not defined SEEDBASE set "SEEDBASE=5000"
if not defined GOAL set "GOAL=95"
%AIDVO_PY% -m aidvo.cli rollout -c %AIDVO_CFG% --model models\%ALGONAME%\final --runs %RUNS% --seed-base %SEEDBASE% --goal %GOAL% -o results\ai
goto menu

:compare
echo --- COMPARE baseline vs AI ---
call sim\compare.bat
goto menu

:checkcfg
%AIDVO_PY% -m aidvo.cli check-config -c %AIDVO_CFG%
goto menu
