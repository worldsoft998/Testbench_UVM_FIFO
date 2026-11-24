@echo off
::==============================================================================
:: AId-UVO-RT — Build the SRIE VPI plug-in (srie_vpi.dll)
::
:: Requires: Microsoft Visual C++ (cl.exe) and Siemens QuestaSim (QUESTA_HOME).
:: Run from a Windows developer command prompt.
::==============================================================================
@echo off
setlocal

if not defined QUESTA_HOME (
    echo ERROR: QUESTA_HOME is not set. Point it at your QuestaSim installation.
    echo Example: set QUESTA_HOME=C:\Siemens\Questa\<version>
    goto :eof
)

set "SCRIPT_DIR=%~dp0"
set "VPI_SRC=%SCRIPT_DIR%\vpi\srie_vpi.c"
set "VPI_DLL=%SCRIPT_DIR%\vpi\srie_vpi.dll"
set "VPI_INC=%QUESTA_HOME%\include"

if not exist "%VPI_SRC%" (
    echo ERROR: VPI source not found: %VPI_SRC%
    goto :eof
)

echo [build_vpi] QUESTA_HOME = %QUESTA_HOME%
echo [build_vpi] Source      = %VPI_SRC%
echo [build_vpi] Output      = %VPI_DLL%

:: Locate cl.exe
where cl.exe >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: cl.exe (MSVC) not found on PATH. Use a developer command prompt.
    goto :eof
)

:: Compile the VPI plug-in as a DLL
cl.exe /LD /I"%VPI_INC%" /O2 "%VPI_SRC%" /link /OUT:"%VPI_DLL%"
if %errorlevel% neq 0 (
    echo [build_vpi] Build FAILED.
    goto :eof
)

echo [build_vpi] Build OK: %VPI_DLL%
echo [build_vpi] Load in QuestaSim with: vsim -pli %VPI_DLL%
goto :eof
