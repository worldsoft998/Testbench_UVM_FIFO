@echo off
rem ---------------------------------------------------------------------------
rem AId-VO : compare baseline vs AI results.
rem   usage: compare.bat [baseline_dir] [ai_dir] [out_dir]
rem Defaults: results\baseline  results\ai  results\comparison
rem Produces comparison_report.md, coverage_progress.csv (+ .png if
rem matplotlib is installed).
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0.."
if not defined AIDVO_PY  set "AIDVO_PY=python"
if not defined AIDVO_CFG set "AIDVO_CFG=config\aidvo_config.yaml"

set "BDIR=%~1"
set "ADIR=%~2"
set "ODIR=%~3"
if not defined BDIR set "BDIR=results\baseline"
if not defined ADIR set "ADIR=results\ai"
if not defined ODIR set "ODIR=results\comparison"

%AIDVO_PY% -m aidvo.cli compare --baseline %BDIR% --ai %ADIR% -o %ODIR%
exit /b %errorlevel%
