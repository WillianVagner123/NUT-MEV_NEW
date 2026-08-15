"""Article 1 reproducible exports.

Canonical manuscript-facing ABCD output is the 34-component ABCD-NutEV matrix.
The historical four-domain guide matrix is retained only as a compatibility
artifact for older runs; it is not the current Article 1 scientific object.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

from nutev.analysis.article1_abcd import (
    ABCD_CODES,
    ABCD_VERSION,
    assert_article1_export_schema_is_safe,
    assert_document_can_close,
    validate_component_decision,
)
from nutev.analysis.domain_states import DOMAINS


def legacy_abcd_matrix_rows(rows: list[dict]) -> list[dict]:
    """Historical 4-domain matrix retained for reproducibility of old runs only."""
    out: list[dict] = []
    for row in rows:
        item = {
            "name": row.get("name", ""),
            "country": row.get("country", row.get("reference_country", "")),
            "reference": row.get("reference", ""),
        }
        for domain in DOMAINS:
            item[f"{domain}_state"] = row.get(f"domain_{domain}_state", "NOT_ASSESSED")
            item[f"{domain}_intensity"] = row.get(f"domain_{domain}_intensity", "")
        out.append(item)
    return out


# Backward-compatible import name. New manuscript code should use
# ``abcd_34_matrix_rows``. The legacy helper no longer emits a global count.
abcd_matrix_rows = legacy_abcd_matrix_rows


def abcd_34_matrix_rows(rows: list[dict]) -> list[dict]:
    """Build a manuscript-safe wide document x 34-component matrix.

    Input is long-form final human coding with at least document_id, code,
    presence and depth. Each document must satisfy the 34/34 closure invariant.
    """
    by_document: dict[str, list[dict]] = defaultdict(list)
    metadata: dict[str, dict] = {}
    for row in rows:
        document_id = str(row.get("document_id") or row.get("Documento_ID") or "").strip()
        if not document_id:
            raise ValueError("canonical ABCD export requires document_id on every row")
        by_document[document_id].append(row)
        metadata.setdefault(document_id, {
            "document_id": document_id,
            "family": row.get("family", row.get("Família", "")),
            "codebook_version": row.get("codebook_version", ABCD_VERSION),
        })

    output: list[dict] = []
    for document_id in sorted(by_document):
        document_rows = by_document[document_id]
        assert_document_can_close(document_rows)
        item = dict(metadata[document_id])
        decisions: dict[str, tuple[str, int | None]] = {}
        for row in document_rows:
            code, presence, depth = validate_component_decision(
                code=row.get("code", row.get("Código")),
                presence=row.get("presence", row.get("Presença?")),
                depth=row.get("depth", row.get("Profundidade 0–3")),
                final=True,
            )
            decisions[code] = (presence, depth)
        for code in ABCD_CODES:
            presence, depth = decisions[code]
            item[f"{code}_presence"] = presence
            item[f"{code}_depth"] = depth
        assert_article1_export_schema_is_safe(item.keys())
        output.append(item)
    return output


def prisma_counts(registries: dict, queue: list[dict]) -> dict:
    """PRISMA-ScR identification/screening-readiness counts.

    Included remains pending here. Formal included counts belong to the formal
    screening/full-text ledger and must never be inferred from PILOT/staging.
    """
    ready = sum(1 for q in queue if q.get("screen_flag") == "ready_to_screen")
    no_text = sum(1 for q in queue if q.get("screen_flag") != "ready_to_screen")
    return {
        "identified_file_assets": len(registries.get("file_assets", [])),
        "unique_document_versions": len(registries.get("versions", [])),
        "document_families": len(registries.get("families", [])),
        "queued_for_screening": len(queue),
        "ready_to_screen": ready,
        "excluded_no_full_text_or_poor_ocr": no_text,
        "included": "pending",
        "note": "Counts are pre-screening. Final inclusion requires the formal two-reviewer full-text workflow.",
    }


def prisma_diagram_mermaid(counts: dict) -> str:
    return "\n".join([
        "```mermaid",
        "flowchart TD",
        f'  A[Arquivos identificados: {counts["identified_file_assets"]}] --> B[Versões únicas de documento: {counts["unique_document_versions"]}]',
        f'  B --> C[Famílias de documento: {counts["document_families"]}]',
        f'  B --> D[Prontos para triagem: {counts["ready_to_screen"]}]',
        f'  B --> E[Sem texto / OCR ruim: {counts["excluded_no_full_text_or_poor_ocr"]}]',
        '  D --> F[Triagem por 2 revisores: PENDENTE]',
        '  F --> G[Incluídos: PENDENTE validação humana]',
        "```",
    ])


_DATA_DICTIONARY = """# Dicionário de dados — saídas do Artigo 1

## Objeto científico canônico

- **ABCD-NutEV v1.1-candidate**: 34 componentes A1-A5, B1-B9, C1-C10, D1-D10.
- Codificação em duas etapas: presença e, quando presente, profundidade 1-3.
- Ausência confirmada = presença NO + profundidade 0.
- Missing/unassessed não é ausência.
- Não existe escore global, média de profundidade, ranking ou maturity score.

## Compatibilidade histórica

As saídas amplas A/B/C/D baseadas em heurística lexical permanecem apenas para
reprodutibilidade de execuções antigas. Elas não são o resultado científico
canônico atual do Artigo 1. O arquivo histórico
`NUTEV_GUIDES_ABCD_MATRIX.csv` é mantido como alias de compatibilidade; o mesmo
conteúdo também é gravado com sufixo `_LEGACY` para tornar sua natureza explícita.

## PRISMA

PILOT, staging e calibração não alimentam contagens formais. O corpus incluído
final depende da triagem humana formal de dois revisores e resolução de conflitos.
"""


def write_article1_abcd_34_export(rows: list[dict], path: Path) -> dict:
    """Write the canonical 34-component manuscript matrix from final human coding."""
    from nutev.export.metadata_tables import write_simple_csv

    matrix = abcd_34_matrix_rows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_simple_csv(matrix, path)
    return {"rows": len(matrix), "path": str(path), "codebook_version": ABCD_VERSION}


def write_article1_exports(rows: list[dict], registries: dict, queue: list[dict], settings) -> dict:
    """Write compatibility guide artifacts plus PRISMA-readiness documentation.

    This function does not fabricate a 34-component human matrix from legacy
    machine-coded guide rows. Canonical ABCD export is produced separately once
    final 34/34 human coding exists.
    """
    from nutev.export.metadata_tables import write_simple_csv

    tables = settings.output_dirs["06_tables"]
    logs = settings.output_dirs["07_logs"]
    curated = settings.output_dirs["10_curated"]
    docs = settings.output_dirs.get("08_docs", curated)

    legacy_matrix = legacy_abcd_matrix_rows(rows)
    legacy_compat_path = tables / "NUTEV_GUIDES_ABCD_MATRIX.csv"
    legacy_explicit_path = tables / "NUTEV_GUIDES_ABCD_MATRIX_LEGACY.csv"
    write_simple_csv(legacy_matrix, legacy_compat_path)
    write_simple_csv(legacy_matrix, legacy_explicit_path)

    counts = prisma_counts(registries, queue)
    (logs / "prisma_counts.json").write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
    (curated / "prisma_diagram.md").write_text(prisma_diagram_mermaid(counts), encoding="utf-8")

    Path(docs).mkdir(parents=True, exist_ok=True)
    (docs / "DATA_DICTIONARY.md").write_text(_DATA_DICTIONARY, encoding="utf-8")

    return {
        # Historical API aliases retained so existing guide-pipeline callers do
        # not break. They refer only to the legacy broad-domain artifact.
        "abcd_matrix_rows": len(legacy_matrix),
        "abcd_matrix_csv": str(legacy_compat_path),
        "legacy_four_domain_matrix_rows": len(legacy_matrix),
        "legacy_four_domain_matrix_csv": str(legacy_explicit_path),
        "canonical_abcd_status": "awaiting final human 34/34 extraction",
        "prisma_counts": counts,
        "prisma_counts_json": str(logs / "prisma_counts.json"),
        "data_dictionary": str(docs / "DATA_DICTIONARY.md"),
    }
