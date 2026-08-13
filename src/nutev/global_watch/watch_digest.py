import json
from datetime import datetime, timezone

CATS = [
    "guidelines_consensus",
    "lifestyle_medicine",
    "obesity_cardiometabolic",
    "diet_patterns",
    "implementation_behavior",
    "food_literacy_culinary_commensality",
    "frameworks_instruments",
]

WORKSTREAMS = ["policy_systems", "clinical_outcomes", "implementation", "framework"]


def write_digest(rows, run_dir, latest_doc_path):
    digest_date = datetime.now(timezone.utc).date().isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = run_dir / "global_watch_digest.md"
    json_path = run_dir / "global_watch_digest.json"
    top_rows = rows[:10]

    def count_status(status):
        return sum(1 for row in rows if row.get("download_status") == status)

    lines = [
        f"# NutMEV Global Watch — {digest_date}",
        "",
        "## Resumo executivo",
        f"- total de itens: {len(rows)}",
        f"- novos itens: {sum(1 for row in rows if row.get('is_new'))}",
        (
            "- alta prioridade: "
            f"{sum(1 for row in rows if (row.get('watch_score') or 0) >= 80)}"
        ),
        f"- PDFs capturados: {count_status('pdf')}",
        f"- HTML snapshots: {count_status('html_snapshot')}",
        f"- metadata-only: {count_status('metadata_only')}",
        f"- falhas: {count_status('failed')}",
        "",
        "## Top 10 para leitura imediata",
        "| prioridade | título | tipo | provider | categoria | impacto provável | status | link |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for index, row in enumerate(top_rows, 1):
        lines.append(
            "| "
            f"{index} | {row.get('title', '')} | {row.get('evidence_type', '')} | "
            f"{row.get('source_provider', '')} | {row.get('category', '')} | "
            f"{row.get('why_it_matters', '')} | "
            f"{row.get('download_status', 'metadata_only')} | {row.get('url', '')} |"
        )

    lines += ["", "## Atualizações por eixo"]
    for category in CATS:
        lines.append(
            f"- {category}: "
            f"{sum(1 for row in rows if row.get('category') == category)}"
        )

    lines += ["", "## Impacto nos artigos"]
    for workstream in WORKSTREAMS:
        lines.append(
            f"- {workstream}: "
            f"{sum(1 for row in rows if workstream in (row.get('workstream_affinity') or []))}"
        )

    host_failures = {}
    for row in rows:
        if row.get("failure_reason"):
            host = row.get("host", "unknown")
            host_failures[host] = host_failures.get(host, 0) + 1

    lines += [
        "",
        "## Falhas e limitações",
        f"- quantidade metadata_only: {count_status('metadata_only')}",
        (
            "- providers com falha: "
            f"{sum(1 for row in rows if row.get('failure_reason'))}"
        ),
        "- observação: 403/paywall/login podem bloquear captura pública.",
    ]
    for host, total in sorted(
        host_failures.items(), key=lambda item: item[1], reverse=True
    )[:5]:
        lines.append(f"- host com falha: {host} ({total})")

    lines += [
        "",
        "## Ações sugeridas",
        "- Ler agora: top 3 itens de maior score.",
        "- Triagem humana: itens metadata_only de alta prioridade.",
        "- Considerar para Rayyan: revisões/trials/guidelines novos.",
        "- Monitorar próxima rodada: hosts com falhas recorrentes.",
    ]

    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {"date": digest_date, "total": len(rows), "items": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    latest_doc_path.parent.mkdir(parents=True, exist_ok=True)
    latest_doc_path.write_text(
        markdown_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return markdown_path, json_path
