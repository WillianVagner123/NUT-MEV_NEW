@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERRO: .venv\Scripts\python.exe nao encontrado.
  echo Ative/crie o ambiente virtual do projeto antes de executar.
  exit /b 1
)
echo.
echo NUTEV REFERENCE ENGINE - COLETA DE REFERENCIAS
echo Busca multi-fonte com autosave para posterior ranking por taxonomia e palavras-chave.
echo.
".venv\Scripts\python.exe" "tools\run_everything_now.py" --project-root ".\project_output_reference"
set EXITCODE=%ERRORLEVEL%
echo.
if "%EXITCODE%"=="0" (
  echo Coleta finalizada. Veja project_output_reference\07_logs\collect_everything\latest.json
) else (
  echo Execucao interrompida ou com erro. Os autosaves existentes foram preservados.
  echo Rode este mesmo arquivo novamente para retomar.
)
exit /b %EXITCODE%
