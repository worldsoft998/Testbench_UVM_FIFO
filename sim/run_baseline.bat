@echo off
rem ---------------------------------------------------------------------------
rem AId-VO : BASELINE run (AI/ML OFF) - constrained-random regression.
rem   usage: run_baseline.bat [num_runs] [seed_base]
rem Writes results\baseline\history.json / .csv
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0.."
if not defined AIDVO_PY  set "AIDVO_PY=python"
if not defined AIDVO_CFG set "AIDVO_CFG=config\aidvo_config.yaml"

set "RUNS=%~1"
set "SEEDBASE=%~2"
if not defined RUNS     set "RUNS=40"
if not defined SEEDBASE set "SEEDBASE=1000"

echo [AId-VO] Baseline (AI off): %RUNS% runs, seed base %SEEDBASE%
%AIDVO_PY% -m aidvo.cli baseline -c %AIDVO_CFG% --runs %RUNS% --seed-base %SEEDBASE%
exit /b %errorlevel%
