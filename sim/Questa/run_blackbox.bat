@echo off
::==============================================================================
:: AId-UVO-RT — Blackbox runner (AI + simulator blackbox)
:: Post-run seed/constraint adjustment. No simulator internals accessed.
::==============================================================================
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

echo [blackbox] Compiling RTL + testbench ...
call vlog -f "%SCRIPT_DIR%\do_files\compile.do"
if %errorlevel% neq 0 (
    echo [blackbox] Compile failed.
    goto :eof
)
echo [blackbox] Compile OK.

echo [blackbox] Launching blackbox optimizer (RL=%AID_UVO_RL_ALGO%, AI=%AID_UVO_AI_ON%)...
python -m optimizer.core blackbox ^
    --rl %AID_UVO_RL_ALGO% ^
    --ai %AID_UVO_AI_ON% ^
    --runs %AID_UVO_NUM_RUNS% ^
    --seed-mode %AID_UVO_SEED_MODE% ^
    --seed %AID_UVO_FIXED_SEED% ^
    --seed-list "%AID_UVO_SEED_LIST%" ^
    --goal %AID_UVO_COVERAGE_GOAL% ^
    --max-time %AID_UVO_MAX_SIM_TIME% ^
    --out %AID_UVO_OUTPUT_DIR%

if %errorlevel% neq 0 (
    echo [blackbox] Optimizer exited with code %errorlevel%.
) else (
    echo [blackbox] Complete. Results in %AID_UVO_OUTPUT_DIR%.
)
goto :eof
