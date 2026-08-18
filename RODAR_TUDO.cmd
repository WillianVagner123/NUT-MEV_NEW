@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo NUTEV REFERENCE ENGINE - BUSCAR E RANQUEAR
echo ============================================================
echo Fluxo: coleta multi-fonte ^> LILACS/BVS + SciELO ^> ranking ^> exportacao.
echo.

set "PY=.venv\Scripts\python.exe"
set "PROJECT_ROOT=.\project_output_reference"
set "OVERALL_EXIT=0"

if not exist "%PY%" (
  echo ERRO: %PY% nao encontrado.
  echo Crie e ative o ambiente virtual antes de executar este comando.
  exit /b 1
)

echo [1/3] COLETA MULTI-FONTE...
call run_everything_now.cmd
set "COLLECT_EXIT=!ERRORLEVEL!"
if not "!COLLECT_EXIT!"=="0" (
  echo AVISO: a coleta geral terminou com codigo !COLLECT_EXIT!.
  echo Falhas de provider permanecem registradas nos manifests.
  set "OVERALL_EXIT=1"
)

echo.
echo [2/3] LILACS/BVS + SCIELO NATIVO...
"%PY%" tools\run_latin_sources.py --project-root "%PROJECT_ROOT%"
set "LATIN_EXIT=!ERRORLEVEL!"
if not "!LATIN_EXIT!"=="0" (
  echo AVISO: uma ou mais rotas latino-americanas falharam ou mudaram de interface.
  echo O ranking continuara com as fontes disponiveis.
  set "OVERALL_EXIT=1"
)

echo.
echo [3/3] RANKING DE REFERENCIAS...
"%PY%" tools\rank_references.py --project-root "%PROJECT_ROOT%" --config-dir ".\config" --top-n 100
set "RANK_EXIT=!ERRORLEVEL!"
if not "!RANK_EXIT!"=="0" (
  echo ERRO: nao foi possivel gerar o ranking de referencias.
  set "OVERALL_EXIT=1"
)

echo.
echo ============================================================
echo NUTEV REFERENCE ENGINE - EXECUCAO CONCLUIDA
echo ============================================================
echo Coleta geral: codigo !COLLECT_EXIT!
echo LILACS/BVS + SciELO: codigo !LATIN_EXIT!
echo Ranking: codigo !RANK_EXIT!
echo.
echo PRINCIPAIS SAIDAS:
echo   %PROJECT_ROOT%\reference_ranking\TOP_REFERENCIAS.md
echo   %PROJECT_ROOT%\reference_ranking\reference_ranking.csv
echo   %PROJECT_ROOT%\reference_ranking\reference_ranking.jsonl
echo   %PROJECT_ROOT%\reference_ranking\latest.json
echo.
echo A/B/C sao niveis de prioridade de leitura. O score nao e recomendacao clinica.
echo.

if "%RANK_EXIT%"=="0" (
  echo SUCESSO: ranking de referencias gerado.
) else (
  echo CONCLUIDO COM ERRO NO RANKING: veja as mensagens acima.
)

exit /b %OVERALL_EXIT%
