@echo off
rem ---------------------------------------------------------------------------
rem AId-VO : AI RUN (AI/ML ON) - train an RL policy, then evaluate it.
rem   usage: run_ai.bat [algo] [timesteps] [runs] [seed_base] [goal_pct]
rem          algo = ppo | a2c | dqn     (default ppo)
rem Writes models\<algo>\final and results\ai\history.json / .csv
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0.."
if not defined AIDVO_PY  set "AIDVO_PY=python"
if not defined AIDVO_CFG set "AIDVO_CFG=config\aidvo_config.yaml"

set "ALGO=%~1"
set "TIMESTEPS=%~2"
set "RUNS=%~3"
set "SEEDBASE=%~4"
set "GOAL=%~5"
if not defined ALGO      set "ALGO=ppo"
if not defined TIMESTEPS set "TIMESTEPS=2000"
if not defined RUNS      set "RUNS=40"
if not defined SEEDBASE  set "SEEDBASE=1000"
if not defined GOAL      set "GOAL=95"

echo [AId-VO] Training %ALGO% for %TIMESTEPS% steps ...
%AIDVO_PY% -m aidvo.cli train -c %AIDVO_CFG% --algo %ALGO% --timesteps %TIMESTEPS%
if errorlevel 1 exit /b 1

echo [AId-VO] Evaluating trained policy: %RUNS% runs, seed base %SEEDBASE%, goal %GOAL%%% ...
%AIDVO_PY% -m aidvo.cli rollout -c %AIDVO_CFG% --model models\%ALGO%\final --runs %RUNS% --seed-base %SEEDBASE% --goal %GOAL% -o results\ai
exit /b %errorlevel%
