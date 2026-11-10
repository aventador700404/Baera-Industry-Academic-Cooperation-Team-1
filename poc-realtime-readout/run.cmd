@echo off
rem Windows helper: runs the project with .venv\Scripts\python.exe, no venv activation needed
rem (works regardless of PowerShell execution policy). In PowerShell type .\run <command>
rem   check    call each API once
rem   collect  collect public API data
rem   reparse  recompute blog sentiment/topics from saved raw posts (no API calls)
rem   mock     regenerate assumed data
rem   build    build readout.local.json for the local screen
rem   all      mock + collect + build
rem   publish  build readout.json for deployment
rem   test     run tests
rem   web      start the screen at http://127.0.0.1:5173
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONUTF8=1

if /i "%~1"=="check" (
  "%PY%" -m pipeline.collect.run --check
  goto end
)
if /i "%~1"=="collect" (
  "%PY%" -m pipeline.collect.run
  goto end
)
if /i "%~1"=="reparse" (
  "%PY%" -m pipeline.collect.run --reparse
  goto end
)
if /i "%~1"=="mock" (
  "%PY%" -m pipeline.mock.generate
  goto end
)
if /i "%~1"=="build" (
  "%PY%" -m pipeline.build
  goto end
)
if /i "%~1"=="publish" (
  "%PY%" -m pipeline.build --publish
  goto end
)
if /i "%~1"=="all" (
  "%PY%" -m pipeline.mock.generate || goto end
  "%PY%" -m pipeline.collect.run || goto end
  "%PY%" -m pipeline.build
  goto end
)
if /i "%~1"=="test" (
  "%PY%" -m pytest
  goto end
)
if /i "%~1"=="web" (
  cd web
  npm run dev
  goto end
)
echo usage: .\run [check ^| collect ^| reparse ^| mock ^| build ^| all ^| publish ^| test ^| web]
exit /b 1

:end
exit /b %errorlevel%
