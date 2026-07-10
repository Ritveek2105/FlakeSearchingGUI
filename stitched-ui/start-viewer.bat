@echo off
setlocal

cd /d "%~dp0"

where npm >nul 2>nul
if errorlevel 1 (
  echo.
  echo ERROR: npm was not found.
  echo Install Node.js 20 or newer, then double-click this file again.
  echo.
  pause
  exit /b 1
)

if not exist "node_modules" goto install_dependencies
if not exist "node_modules\next" goto install_dependencies
goto dependencies_ready

:install_dependencies
  echo.
  echo Installing viewer dependencies. This can take a few minutes...
  echo.
  if exist "package-lock.json" (
    call npm ci
  ) else (
    call npm install
  )
  if errorlevel 1 (
    echo.
    echo ERROR: viewer dependency installation failed.
    echo.
    pause
    exit /b 1
  )

:dependencies_ready

echo.
echo Starting Graphene Sample Viewer...
echo Browser URL: http://localhost:3000
echo Keep this window open while using the viewer.
echo.

start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$url='http://localhost:3000'; for ($i=0; $i -lt 90; $i++) { try { $r=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2; if ($r.StatusCode -ge 200) { Start-Process $url; exit 0 } } catch { Start-Sleep -Seconds 1 } }; Start-Process $url"
call npm run dev

echo.
echo Viewer stopped.
pause
