@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo NUTEV EVIDENCE ENGINE - RODAR TUDO
echo ============================================================
echo Um comando para executar tudo que o computador pode fazer agora.
echo Coleta real + autosave + limpeza + deduplicacao tecnica + extracao + OCR.
echo Gates humanos/cientificos nao serao inventados.
echo.

set "PY=.venv\Scripts\python.exe"
set "NUTEV=.venv\Scripts\nutev.exe"
set "PROJECT_ROOT=.\project_output_scientific"
set "OVERALL_EXIT=0"

if not exist "%PY%" (
  echo ERRO: %PY% nao encontrado.
  echo O ambiente virtual do projeto precisa existir antes deste comando.
  exit /b 1
)

echo [1/4] Verificando dependencias Python para documentos/OCR...
"%PY%" -c "import fitz, PIL, pytesseract, pypdf" >nul 2>nul
if errorlevel 1 (
  echo Instalando dependencias .[documents] no ambiente virtual...
  "%PY%" -m pip install -e ".[documents]"
  if errorlevel 1 (
    echo AVISO: nao foi possivel instalar todas as dependencias Python de documentos.
    echo A coleta continuara; extracao/OCR registrara a pendencia sem inventar texto.
    set "OVERALL_EXIT=1"
  )
) else (
  echo Dependencias Python de documentos: OK
)

echo.
echo [2/4] Verificando Tesseract para PDFs escaneados...
where tesseract >nul 2>nul
if errorlevel 1 (
  if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    set "PATH=C:\Program Files\Tesseract-OCR;!PATH!"
  ) else if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    set "PATH=C:\Program Files (x86)\Tesseract-OCR;!PATH!"
  ) else (
    where winget >nul 2>nul
    if not errorlevel 1 (
      echo Tesseract nao encontrado. Tentando instalar automaticamente pelo winget...
      winget install --id UB-Mannheim.TesseractOCR --exact --accept-package-agreements --accept-source-agreements --silent
      if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "PATH=C:\Program Files\Tesseract-OCR;!PATH!"
      if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" set "PATH=C:\Program Files (x86)\Tesseract-OCR;!PATH!"
    )
  )
)
where tesseract >nul 2>nul
if errorlevel 1 (
  echo AVISO: Tesseract ainda nao esta disponivel.
  echo O fluxo NAO vai parar: texto nativo sera extraido e scans ficarao marcados como pendentes de OCR.
) else (
  echo Tesseract: OK
  tesseract --version 2>nul | findstr /b /c:"tesseract"
)

echo.
echo [3/4] COLETA REAL COMPLETA - todas as fontes automatizaveis...
call run_everything_now.cmd
set "COLLECT_EXIT=!ERRORLEVEL!"
if not "!COLLECT_EXIT!"=="0" (
  echo AVISO: coleta terminou com codigo !COLLECT_EXIT!.
  echo Autosaves foram preservados. O pos-processamento tentara usar o ultimo master valido.
  set "OVERALL_EXIT=1"
)

echo.
echo [4/4] LIMPEZA + ORGANIZACAO + EXTRACAO/OCR...
call process_everything_now.cmd
set "PROCESS_EXIT=!ERRORLEVEL!"
if not "!PROCESS_EXIT!"=="0" (
  echo AVISO: pos-processamento terminou com codigo !PROCESS_EXIT!.
  echo RAW e autosaves foram preservados.
  set "OVERALL_EXIT=1"
)

echo.
echo ============================================================
echo NUTEV - RODAR TUDO TERMINOU
echo ============================================================
echo Coleta: codigo !COLLECT_EXIT!
echo Pos-processamento/OCR: codigo !PROCESS_EXIT!
echo.
echo Auditorias:
echo   %PROJECT_ROOT%\07_logs\collect_everything\latest.json
echo   %PROJECT_ROOT%\07_logs\postprocess_everything\latest.json
echo.
echo O sistema executou tudo que e computacionalmente permitido agora.
echo Se houver fila humana, ela e o proximo limite real; o software nao inventa INCLUDE/EXCLUDE, PRESS, FREEZE ou PRISMA.
echo.

if "%OVERALL_EXIT%"=="0" (
  echo SUCESSO: etapas automatizaveis concluidas.
) else (
  echo CONCLUIDO COM AVISOS: veja as mensagens acima. Os dados existentes nao foram apagados.
)

exit /b %OVERALL_EXIT%
