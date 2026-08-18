@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "ARTICLE=%~1"
if /I "%ARTICLE%"=="A1" set "ARTICLE=A1"
if /I "%ARTICLE%"=="A2" set "ARTICLE=A2"
if /I "%ARTICLE%"=="A3" set "ARTICLE=A3"
if /I "%ARTICLE%"=="A4" set "ARTICLE=A4"
if not "%ARTICLE%"=="A1" if not "%ARTICLE%"=="A2" if not "%ARTICLE%"=="A3" if not "%ARTICLE%"=="A4" (
  echo.
  echo USO: RODAR_ARTIGO.cmd A1^|A2^|A3^|A4
  echo.
  echo A1 = recomendacoes e direcao alimentar em documentos normativos/estruturantes
  echo A2 = prescricoes/intervencoes dieteticas atuais + pacote operacional + executabilidade
  echo A3 = desenvolvimento do Protocolo Dietetico NutEV
  echo A4 = Framework Conceitual Clinico-Decisorio NutEV
  echo.
  echo CFD-I e CFD-8 nao pertencem ao A4.
  exit /b 2
)

set "PY=.venv\Scripts\python.exe"
set "PROJECT_ROOT=.\project_output_reference"
set "OVERALL_EXIT=0"

if not exist "%PY%" (
  echo ERRO: %PY% nao encontrado.
  echo Crie/ative o ambiente virtual antes de executar este comando.
  exit /b 1
)

echo.
echo ============================================================
echo NUTEV - EXECUCAO GOVERNADA DO %ARTICLE%
echo ============================================================
echo A governanca A1-A4 sera validada e registrada no manifesto da execucao.
echo O ranking prioriza leitura; nao decide inclusao/exclusao cientifica ou conduta clinica.
echo.

echo [1/3] COLETA MULTI-FONTE...
call run_everything_now.cmd
set "COLLECT_EXIT=!ERRORLEVEL!"
if not "!COLLECT_EXIT!"=="0" (
  echo AVISO: coleta geral terminou com codigo !COLLECT_EXIT!.
  echo O ranking tentara usar o ultimo master valido, sem fabricar resultados.
  set "OVERALL_EXIT=1"
)

echo.
echo [2/3] LILACS/BVS + SCIELO NATIVO...
"%PY%" tools\run_latin_sources.py --project-root "%PROJECT_ROOT%"
set "LATIN_EXIT=!ERRORLEVEL!"
if not "!LATIN_EXIT!"=="0" (
  echo AVISO: uma ou mais rotas latino-americanas falharam ou mudaram de interface.
  set "OVERALL_EXIT=1"
)

echo.
echo [3/3] RANKING GOVERNADO DO %ARTICLE%...
"%PY%" tools\run_governed_rank_references.py --article "%ARTICLE%" --project-root "%PROJECT_ROOT%" --config-dir ".\config" --top-n 100
set "RANK_EXIT=!ERRORLEVEL!"
if not "!RANK_EXIT!"=="0" (
  echo ERRO: nao foi possivel gerar o ranking governado do %ARTICLE%.
  set "OVERALL_EXIT=1"
)

echo.
echo ============================================================
echo NUTEV - EXECUCAO DO %ARTICLE% CONCLUIDA
echo ============================================================
echo Coleta geral: codigo !COLLECT_EXIT!
echo LILACS/BVS + SciELO: codigo !LATIN_EXIT!
echo Ranking governado: codigo !RANK_EXIT!
echo.
echo SAIDA CANONICA DO ARTIGO:
echo   %PROJECT_ROOT%\reference_ranking\by_article\%ARTICLE%\latest.json
echo.
echo Cada execucao fica preservada em:
echo   %PROJECT_ROOT%\reference_ranking\by_article\%ARTICLE%\runs\RUN_ID\
echo.

exit /b %OVERALL_EXIT%
