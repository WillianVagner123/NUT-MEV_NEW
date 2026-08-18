@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo NUTEV REFERENCE ENGINE - BUSCAR E RANQUEAR
echo ============================================================
echo Objetivo: encontrar e priorizar as melhores referencias.
echo Fluxo fechado: coleta -> LILACS/BVS + SciELO -> ranking por taxonomia/palavras-chave.
echo Sem PRISMA, PRESS, FREEZE, triagem formal ou decisao de inclusao/exclusao.
echo.

set "PY=.venv\Scripts\python.exe"
set "PROJECT_ROOT=.\project_output_reference"
set "OVERALL_EXIT=0"

if not exist "%PY%" (
  echo ERRO: %PY% nao encontrado.
  echo O ambiente virtual do projeto precisa existir antes deste comando.
  exit /b 1
)

echo [1/3] COLETA MULTI-FONTE...
call run_everything_now.cmd
set "COLLECT_EXIT=!ERRORLEVEL!"
if not "!COLLECT_EXIT!"=="0" (
  echo AVISO: coleta geral terminou com codigo !COLLECT_EXIT!.
  echo Autosaves foram preservados; o ranking tentara usar o ultimo master valido.
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
echo NUTEV - BUSCA FECHADA CONCLUIDA
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
echo O score organiza referencias por aderencia a taxonomia, palavras-chave, tipo documental,
echo fonte e recencia. Ele nao decide inclusao/exclusao e nao gera PRISMA.
echo.

if "%RANK_EXIT%"=="0" (
  echo SUCESSO: ranking de referencias gerado.
) else (
  echo CONCLUIDO COM ERRO NO RANKING: veja as mensagens acima.
)

exit /b %OVERALL_EXIT%
