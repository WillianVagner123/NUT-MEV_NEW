@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo    NutEV Reference Engine - iniciar
echo ============================================
echo.

set "PY="
py -3.12 --version >nul 2>&1 && set "PY=py -3.12"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo [ERRO] Python 3.12+ nao encontrado.
  echo Instale Python 3.12 ou 3.13 e tente novamente.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo ==^> Preparando o ambiente na primeira execucao...
  %PY% -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -e .
  if errorlevel 1 (
    echo [ERRO] Falha na instalacao.
    pause
    exit /b 1
  )
)

echo.
echo ==^> Executando coleta e ranking de referencias...
call RODAR_TUDO.cmd
set "EXITCODE=!ERRORLEVEL!"

if exist "project_output_reference\reference_ranking\TOP_REFERENCIAS.md" (
  echo.
  echo ==^> Abrindo TOP_REFERENCIAS.md
  start "" "project_output_reference\reference_ranking\TOP_REFERENCIAS.md"
)

if not "!EXITCODE!"=="0" (
  echo.
  echo Execucao concluida com avisos ou falhas de provider. Consulte a saida acima.
)

pause
exit /b !EXITCODE!
