@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 apps\nutev-web\server.py
) else (
  python apps\nutev-web\server.py
)
endlocal
