@echo off
setlocal
cd /d "%~dp0"

echo.
echo NUTEV REFERENCE ENGINE - RANQUEAR REFERENCIAS
echo Compatibilidade: este comando agora gera somente a fila priorizada de referencias.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERRO: ambiente virtual nao encontrado em .venv\Scripts\python.exe
  echo Inicie/instale o NutEV primeiro e tente novamente.
  exit /b 1
)

".venv\Scripts\python.exe" tools\rank_references.py --project-root .\project_output_reference --config-dir .\config --top-n 100
set EXITCODE=%ERRORLEVEL%

if not "%EXITCODE%"=="0" (
  echo.
  echo Ranking terminou com codigo %EXITCODE%.
  exit /b %EXITCODE%
)

echo.
echo Ranking concluido. Veja project_output_reference\reference_ranking\TOP_REFERENCIAS.md
endlocal
