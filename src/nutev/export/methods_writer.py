from __future__ import annotations

import csv
import json
from pathlib import Path

from nutev.utils import write_text


EXECUTION_FIELDS = [
    "run_id",
    "provider",
    "workstream",
    "query_hash",
    "query",
    "status",
    "total_found",
    "rows_returned",
    "duration_seconds",
    "resume_used",
    "checkpoint_path",
]


def _current_run_id(rows: list[dict[str, str]]) -> str:
    return next(
        (
            str(row.get("run_id") or "").strip()
            for row in reversed(rows)
            if str(row.get("run_id") or "").strip()
        ),
        "",
    )


def _archive_generated_querypacks(logs_dir: Path, current_run_id: str) -> None:
    """Preserve the pre-execution query space under truthful generated names.

    The master pipeline historically writes generated query packs to files named
    ``*_executed`` before provider budgets are applied.  At methods-export time
    all provider calls have already finished, so this function first preserves
    those generated artifacts and the execution finalizer can safely replace the
    legacy ``*_executed`` paths with the queries that were actually attempted.

    A run marker makes the operation idempotent: calling the methods writer twice
    for the same run must never overwrite ``*_generated`` with already-finalized
    execution artifacts.
    """

    marker = logs_dir / "query_audit_finalized_run_id.txt"
    marker_value = current_run_id or "__no_run_id__"
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == marker_value:
        return

    for old_name, generated_name in (
        ("querypack_executed.json", "querypack_generated.json"),
        ("querypack_executed.csv", "querypack_generated.csv"),
        ("provider_querypack_executed.json", "provider_querypack_generated.json"),
        ("provider_querypack_executed.csv", "provider_querypack_generated.csv"),
    ):
        source = logs_dir / old_name
        if source.exists():
            (logs_dir / generated_name).write_bytes(source.read_bytes())


def _load_current_execution_rows(logs_dir: Path) -> list[dict[str, str]]:
    """Load real provider attempts for the current/latest run.

    ``provider_performance.csv`` is appended by ``search_provider`` only after a
    provider call has produced a terminal result.  It is therefore the canonical
    generic-pipeline evidence that an expression was actually attempted.  When a
    logs directory contains multiple runs, only the most recently appended run_id
    is selected so manuscript methods cannot accidentally mix executions.
    """

    path = logs_dir / "provider_performance.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if not rows:
        return []

    current_run_id = _current_run_id(rows)
    if current_run_id:
        rows = [
            row
            for row in rows
            if str(row.get("run_id") or "").strip() == current_run_id
        ]
    return rows


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _finalize_query_audit(
    logs_dir: Path,
) -> tuple[dict[str, dict[str, list[str]]], list[dict[str, str]]]:
    """Separate generated query space from the expressions actually attempted.

    Invariants after this function returns:

    * ``*_generated`` contains the pre-budget/pre-routing query space;
    * every expression in ``*_executed`` has a matching provider-performance row;
    * ``query_execution_ledger.*`` is the canonical attempt-level provenance.
    """

    logs_dir.mkdir(parents=True, exist_ok=True)
    execution_rows = _load_current_execution_rows(logs_dir)
    current_run_id = _current_run_id(execution_rows)
    _archive_generated_querypacks(logs_dir, current_run_id)

    (logs_dir / "query_execution_ledger.json").write_text(
        json.dumps(execution_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(logs_dir / "query_execution_ledger.csv", execution_rows, EXECUTION_FIELDS)

    provider_pack: dict[str, dict[str, list[str]]] = {}
    flat_pack: dict[str, list[str]] = {}
    provider_csv_rows: list[dict] = []
    flat_csv_rows: list[dict] = []

    for row in execution_rows:
        workstream = str(row.get("workstream") or "").strip()
        provider = str(row.get("provider") or "").strip()
        query = str(row.get("query") or "").strip()
        if not workstream or not provider or not query:
            continue

        provider_queries = provider_pack.setdefault(workstream, {}).setdefault(provider, [])
        provider_queries.append(query)
        flat_pack.setdefault(workstream, []).append(query)

        provider_csv_rows.append(
            {
                "workstream": workstream,
                "provider": provider,
                "query_order": len(provider_queries),
                "query_text": query,
                "status": row.get("status", ""),
                "query_hash": row.get("query_hash", ""),
                "total_found": row.get("total_found", ""),
                "rows_returned": row.get("rows_returned", ""),
            }
        )
        flat_csv_rows.append(
            {
                "workstream": workstream,
                "query_order": len(flat_pack[workstream]),
                "query_text": query,
            }
        )

    (logs_dir / "provider_querypack_executed.json").write_text(
        json.dumps(provider_pack, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(
        logs_dir / "provider_querypack_executed.csv",
        provider_csv_rows,
        [
            "workstream",
            "provider",
            "query_order",
            "query_text",
            "status",
            "query_hash",
            "total_found",
            "rows_returned",
        ],
    )

    (logs_dir / "querypack_executed.json").write_text(
        json.dumps(flat_pack, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(
        logs_dir / "querypack_executed.csv",
        flat_csv_rows,
        ["workstream", "query_order", "query_text"],
    )
    (logs_dir / "query_audit_finalized_run_id.txt").write_text(
        current_run_id or "__no_run_id__",
        encoding="utf-8",
    )
    return provider_pack, execution_rows


def _provider_section(
    workstream: str,
    provider_querypack: dict[str, dict[str, list[str]]],
) -> str:
    providers = provider_querypack.get(workstream, {})
    if not providers:
        return "## estratégia efetivamente executada por base\nNenhuma tentativa registrada para esta rodada.\n"

    lines = ["## estratégia efetivamente executada por base"]
    for provider, queries in providers.items():
        lines.append(f"### {provider}")
        lines.append(f"Tentativas registradas: {len(queries)}")
        for idx, query in enumerate(queries[:5], start=1):
            lines.append(f"{idx}. {query}")
        if len(queries) > 5:
            lines.append(
                f"Demais {len(queries) - 5} tentativas: ver `07_logs/query_execution_ledger.csv`."
            )
    return "\n".join(lines) + "\n"


def _sources_consulted(
    workstream: str,
    provider_querypack: dict[str, dict[str, list[str]]],
) -> str:
    providers = list(provider_querypack.get(workstream, {}))
    if not providers:
        return "Nenhuma fonte com tentativa de execução registrada para esta rodada."
    return ", ".join(providers) + "."


def _method_doc(
    workstream: str,
    provider_querypack: dict[str, dict[str, list[str]]],
) -> str:
    return f"""# NUTEV METHODS - {workstream.upper()}

## objetivo
Executar captura reprodutível de evidências para {workstream}.

## fontes efetivamente consultadas
{_sources_consulted(workstream, provider_querypack)}

## lógica metodológica
A estratégia é derivada de `config/keyword_taxonomy.json`, mas a execução usa renderização específica por base. O espaço de queries **gerado** é preservado separadamente do conjunto **efetivamente tentado**, depois da aplicação de orçamento, roteamento e disponibilidade de providers.

## camada global de evidência NutEV (integrada)
A classificação não funciona como silos isolados por workstream. Os fluxos `busca1`, `busca2a`, `busca2b` e `a3` são tratados como **lentes de evidência** sobre a mesma base de registros:
- `config/nutev_ontology.json`: ontologia central (domínios, outcomes, tipos de evidência).
- `config/evidence_lenses.json`: mapeamento das lentes e regras multi-rótulo.
- `config/source_registry.json`: registro de provedores/fontes e compatibilidade.
- `src/nutev/analysis/nutev_classifier.py`: classificador unificado aplicado em todos os registros, independentemente do workstream de origem.

Saídas integradas:
- `NUTEV_GLOBAL_EVIDENCE_MATRIX.xlsx`
- `NUTEV_PROTOCOL_TRANSLATION_MATRIX.xlsx`

{_provider_section(workstream, provider_querypack)}## auditoria da busca
A fonte canônica para afirmar que uma expressão foi executada é `07_logs/query_execution_ledger.json`/`.csv`, derivada de `provider_performance.csv`. Cada linha representa uma tentativa real e inclui provider, workstream, hash da query, expressão, status e contagens disponíveis.

Os artefatos `querypack_generated.*` e `provider_querypack_generated.*` registram o espaço **gerado antes da execução** e não devem ser citados como prova de busca realizada. Para compatibilidade, `querypack_executed.*` e `provider_querypack_executed.*` são finalizados após as chamadas aos providers e contêm somente expressões com tentativa correspondente no ledger.

## critérios de captura
Resultados dos providers efetivamente tentados, com status de execução preservado no ledger. Trilhas de busca com lógica diferente (por exemplo, bases indexadas versus fontes oficiais) devem permanecer metodologicamente distinguíveis, mas usar o mesmo princípio mínimo: nenhuma expressão ou regra pode ser descrita como executada sem evidência de tentativa.

## critérios de download
Seleção por relevância, regras de domínio e orçamento operacional, com preservação explícita de falhas em `failed_downloads.csv`.

## lógica de OCR
PDF: texto nativo primeiro; sem texto, OCR por página. Imagens: OCR direto.

## regras de scoring
Scoring por keyword, source e workstream via `config/scoring_rules.json`.

## análise por domínios
Regras `domain_rules_{workstream}.json` quando aplicável.

## outputs gerados
Tabelas 02_metadata, 05_extraction, 06_tables, 10_curated e logs 07_logs.

## limitações reais
O ledger de tentativa prova o que foi submetido ao executor genérico, mas não transforma automaticamente uma rodada em busca definitiva de manuscrito. A prontidão científica depende também dos gates de estratégia congelada, completude das trilhas previstas, snapshots/checksums quando exigidos, deduplicação, recuperação de texto completo e revisão humana.
"""


def write_methods_docs(docs_dir: Path, logs_dir: Path | None = None) -> None:
    provider_querypack: dict[str, dict[str, list[str]]] = {}
    if logs_dir is not None:
        provider_querypack, _ = _finalize_query_audit(logs_dir)

    workstreams = ["busca1", "busca2a", "busca2b", "a3"]
    for ws in workstreams:
        write_text(
            docs_dir / f"NUTEV_METHODS_{ws.upper()}.md",
            _method_doc(ws, provider_querypack),
        )
    write_text(
        docs_dir / "NUTEV_METHODS_MASTER.md",
        "\n\n".join(_method_doc(ws, provider_querypack) for ws in workstreams),
    )
