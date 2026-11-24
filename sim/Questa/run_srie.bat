@echo off
::==============================================================================
:: AId-UVO-RT — SRIE runner (AI + simulator runtime / instantaneous)
:: Loads the VPI plug-in into QuestaSim and drives the Python SRIE agent.
::==============================================================================
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

echo [srie] Compiling RTL + testbench ...
call vlog -f "%SCRIPT_DIR%\do_files\compile.do"
if %errorlevel% neq 0 (
    echo [srie] Compile failed.
    goto :eof
)
echo [srie] Compile OK.

:: Check VPI plug-in exists
set "VPI_DLL=%SCRIPT_DIR%\vpi\srie_vpi.dll"
if not exist "%VPI_DLL%" (
    echo [srie] VPI plug-in not found: %VPI_DLL%
    echo [srie] Build it first with build_vpi.bat
    goto :eof
)

echo [srie] Starting QuestaSim with VPI plug-in (background) ...
start /b "" vsim -c -pli "%VPI_DLL%" -do "%SCRIPT_DIR%\do_files\run_srie.do" > "%SCRIPT_DIR%\..\..\results\srie\vsim_srie.log" 2>&1

:: Wait for the VPI TCP server to come up
timeout /t 4 >nul

echo [srie] Launching SRIE agent (RL=%AID_UVO_RL_ALGO%, AI=%AID_UVO_AI_ON%)...
python -m optimizer.core srie ^
    --rl %AID_UVO_RL_ALGO% ^
    --ai %AID_UVO_AI_ON% ^
    --runs %AID_UVO_NUM_RUNS% ^
    --seed-mode %AID_UVO_SEED_MODE% ^
    --seed %AID_UVO_FIXED_SEED% ^
    --seed-list "%AID_UVO_SEED_LIST%" ^
    --goal %AID_UVO_COVERAGE_GOAL% ^
    --max-time %AID_UVO_MAX_SIM_TIME% ^
    --out %AID_UVO_OUTPUT_DIR% ^
    --vpi-port %SRIE_VPI_PORT%

if %errorlevel% neq 0 (
    echo [srie] Optimizer exited with code %errorlevel%.
)

:: Stop the background QuestaSim instance
taskkill /f /im vsim.exe >nul 2>&1

echo [srie] Complete. Results in %AID_UVO_OUTPUT_DIR%.
goto :eof
