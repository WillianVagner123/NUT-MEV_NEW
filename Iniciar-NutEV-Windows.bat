@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo    NutEV Reference Engine - iniciar
echo ============================================
echo.

REM --- 1) Encontrar Python 3.12+ ---
set "PY="
py -3.12 --version >nul 2>&1 && set "PY=py -3.12"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo [ERRO] Python 3.12+ nao encontrado.
  echo Instale em https://www.python.org/downloads/ e marque "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

REM --- 2) Criar ambiente e instalar na primeira vez ---
if not exist ".venv\Scripts\python.exe" (
  echo ==^> Preparando o ambiente na primeira vez. Isso pode levar alguns minutos...
  %PY% -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -e ".[documents,search]"
  if errorlevel 1 (
    echo [ERRO] Falha na instalacao. Veja as mensagens acima.
    pause
    exit /b 1
  )
)

REM --- 3) Buscar e ranquear referencias ---
echo.
echo ==^> Executando busca fechada e ranking de referencias...
call RODAR_TUDO.cmd
set "EXITCODE=!ERRORLEVEL!"

REM --- 4) Abrir o ranking principal quando existir ---
if exist "project_output_reference\reference_ranking\TOP_REFERENCIAS.md" (
  echo.
  echo ==^> Abrindo TOP_REFERENCIAS.md
  start "" "project_output_reference\reference_ranking\TOP_REFERENCIAS.md"
)

if not "!EXITCODE!"=="0" (
  echo.
  echo Execucao concluida com avisos/erros. Consulte a saida acima.
)

pause
exit /b !EXITCODE!
