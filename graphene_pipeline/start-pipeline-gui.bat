@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo.
  echo ERROR: Python launcher 'py' was not found.
  echo Install Python 3.11 or newer, then double-click this file again.
  echo.
  pause
  exit /b 1
)

if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "env_key=%%A"
    if not "!env_key!"=="" if not "!env_key:~0,1!"=="#" set "%%A=%%B"
  )
)

if "%GRAPHENE_PIPELINE_HOME%"=="" set "GRAPHENE_PIPELINE_HOME=%CD%"
if "%GRAPHENE_WEBSITE_DIR%"=="" if exist "%~dp0..\stitched-ui" set "GRAPHENE_WEBSITE_DIR=%~dp0..\stitched-ui"
if "%FIJI_EXE%"=="" if "%FIJI_PATH%"=="" if exist "%~dp0..\fiji-latest-win64-jdk\Fiji\fiji-windows-x64.exe" set "FIJI_EXE=%~dp0..\fiji-latest-win64-jdk\Fiji\fiji-windows-x64.exe"
if "%FIJI_EXE%"=="" if "%FIJI_PATH%"=="" if exist "%USERPROFILE%\Downloads\fiji-latest-win64-jdk\Fiji\fiji-windows-x64.exe" set "FIJI_EXE=%USERPROFILE%\Downloads\fiji-latest-win64-jdk\Fiji\fiji-windows-x64.exe"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo Creating Python environment. This can take a minute...
  echo.
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo.
    echo ERROR: Could not create Python 3.11 environment.
    echo.
    pause
    exit /b 1
  )
)

echo.
echo Installing/updating Graphene Pipeline in this environment...
echo.
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
  echo.
  echo ERROR: Pipeline install failed.
  echo.
  pause
  exit /b 1
)

echo.
echo Starting Graphene Pipeline GUI...
echo Workspace: %GRAPHENE_PIPELINE_HOME%
if not "%GRAPHENE_WEBSITE_DIR%"=="" echo Viewer folder: %GRAPHENE_WEBSITE_DIR%
if not "%FIJI_EXE%"=="" echo Fiji: %FIJI_EXE%
if "%FIJI_EXE%"=="" if not "%FIJI_PATH%"=="" echo Fiji: %FIJI_PATH%
if "%FIJI_EXE%"=="" if "%FIJI_PATH%"=="" echo Fiji: not configured
echo.

call ".venv\Scripts\graphene-pipeline-gui.exe"

echo.
echo Pipeline GUI closed.
pause
