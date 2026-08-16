@echo off
setlocal
cd /d "%~dp0"

echo.
echo NUTEV EVIDENCE ENGINE - LIMPEZA + OCR POS-COLETA
echo RAW preservado. Limpeza deterministica. OCR somente em arquivos ja baixados.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERRO: ambiente virtual nao encontrado em .venv\Scripts\python.exe
  echo Inicie/instale o NutEV primeiro e tente novamente.
  exit /b 1
)

".venv\Scripts\python.exe" tools\process_everything_now.py --project-root .\project_output_scientific
set EXITCODE=%ERRORLEVEL%

if not "%EXITCODE%"=="0" (
  echo.
  echo Pos-processamento terminou com codigo %EXITCODE%.
  echo Os arquivos RAW e autosaves existentes foram preservados.
  exit /b %EXITCODE%
)

echo.
echo Pos-processamento concluido. Veja project_output_scientific\07_logs\postprocess_everything\latest.json
endlocal
