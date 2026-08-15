"""Canonical ABCD-NutEV v1.1-candidate contract for Article 1.

Implements D-098/D-099/D-102. Human decisions remain authoritative; machine
assistance must not infer final absence, depth, consensus or document quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

ABCD_VERSION = "v1.1-candidata"
PRESENCE_STATES = ("YES", "NO", "DOUBT")
DEPTH_VALUES = (0, 1, 2, 3)


@dataclass(frozen=True, slots=True)
class ComponentSpec:
    code: str
    macro: str
    label: str


_COMPONENT_LABELS = (
    ("A1", "Objetivos, adequação e segurança alimentar/nutricional"),
    ("A2", "Alimentos, grupos alimentares e padrões alimentares"),
    ("A3", "Processamento, formulação, textura ou matriz alimentar"),
    ("A4", "Estrutura e forma de expressão da orientação/prescrição alimentar"),
    ("A5", "Individualização, flexibilidade e substituições"),
    ("B1", "Reconhecer, interpretar e avaliar informação alimentar/nutricional"),
    ("B2", "Selecionar, adquirir e navegar escolhas alimentares"),
    ("B3", "Planejar e organizar alimentação/refeições"),
    ("B4", "Preparar, cozinhar, armazenar e usar equipamentos"),
    ("B5", "Compor, porcionar e substituir refeições/alimentos"),
    ("B6", "Auto-monitorar, interpretar e responder ao feedback"),
    ("B7", "Analisar barreiras e resolver problemas"),
    ("B8", "Comunicar, negociar e coordenar socialmente"),
    ("B9", "Generalizar, transferir e sustentar autonomia"),
    ("C1", "Estrutura temporal, rotina e transições"),
    ("C2", "Ambiente físico, disponibilidade e acesso material"),
    ("C3", "Recursos econômicos, custo e segurança alimentar"),
    ("C4", "Contexto social, relações e divisão de responsabilidades"),
    ("C5", "Cultura, identidade, valores e aceitabilidade"),
    ("C6", "Condições corporais, sintomas e limitações funcionais"),
    ("C7", "Condições afetivas, psicológicas e cognitivas"),
    ("C8", "Carga de execução, esforço e fricção"),
    ("C9", "Alternativas concorrentes e consequências explicitamente descritas"),
    ("C10", "Recursos externos, serviços e suportes organizados"),
    ("D1", "Alvo executável, linha de base ou critério de entrada"),
    ("D2", "Acordo, prioridades, metas e critérios de sucesso"),
    ("D3", "Sequência, dose, progressão e agendamento"),
    ("D4", "Componentes da intervenção, materiais, suporte e responsáveis"),
    ("D5", "Monitoramento, feedback, reavaliação e regra de decisão"),
    ("D6", "Adaptação longitudinal do cuidado"),
    ("D7", "Implementação institucional, fidelidade, alcance e qualidade"),
    ("D8", "Manutenção, generalização e retirada planejada de suporte"),
    ("D9", "Rupturas, lapsos, recomposição e retomada"),
    ("D10", "Papéis profissionais, coordenação, encaminhamento e continuidade"),
)

ABCD_COMPONENTS = {
    code: ComponentSpec(code, code[0], label) for code, label in _COMPONENT_LABELS
}
ABCD_CODES = tuple(code for code, _ in _COMPONENT_LABELS)

FORBIDDEN_ARTICLE1_EXPORT_FIELDS = frozenset({
    "profile", "n_domains", "n_domains_positive", "abcd_score", "abcd_total",
    "global_abcd_score", "mean_depth", "mean_abcd_depth", "maturity_score",
    "document_rank",
})


def normalize_presence(value: object) -> str:
    raw = str(value or "").strip().upper()
    aliases = {
        "SIM": "YES", "YES": "YES",
        "NÃO": "NO", "NAO": "NO", "NO": "NO",
        "DÚVIDA": "DOUBT", "DUVIDA": "DOUBT", "DOUBT": "DOUBT",
    }
    if raw not in aliases:
        raise ValueError(
            "presence must be YES/NO/DOUBT (SIM/NÃO/DÚVIDA accepted); "
            "blank and N/A are not valid ABCD decisions"
        )
    return aliases[raw]


def normalize_depth(value: object) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        raise ValueError("depth must be one of 0, 1, 2, 3")
    try:
        depth = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("depth must be one of 0, 1, 2, 3") from exc
    if depth not in DEPTH_VALUES:
        raise ValueError("depth must be one of 0, 1, 2, 3")
    return depth


def validate_component_decision(*, code: object, presence: object, depth: object, final: bool = False) -> tuple[str, str, int | None]:
    normalized_code = str(code or "").strip().upper()
    if normalized_code not in ABCD_COMPONENTS:
        raise ValueError(f"unknown ABCD code: {normalized_code or '<blank>'}")
    normalized_presence = normalize_presence(presence)
    normalized_depth = normalize_depth(depth)
    if normalized_presence == "YES" and normalized_depth not in (1, 2, 3):
        raise ValueError("YES requires depth 1-3")
    if normalized_presence == "NO" and normalized_depth != 0:
        raise ValueError("NO requires depth 0")
    if normalized_presence == "DOUBT":
        if normalized_depth is not None:
            raise ValueError("DOUBT must keep depth blank until resolved")
        if final:
            raise ValueError("DOUBT cannot remain in a closed ABCD extraction")
    return normalized_code, normalized_presence, normalized_depth


def _value(row: Mapping[str, object], *keys: str) -> object:
    for key in keys:
        if key in row:
            return row[key]
    return None


def document_completion(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    normalized: dict[str, tuple[str, int | None]] = {}
    duplicates: list[str] = []
    invalid: list[dict[str, str]] = []
    for row in rows:
        code = str(_value(row, "code", "Código", "codigo") or "").strip().upper()
        if code in normalized:
            duplicates.append(code)
            continue
        try:
            norm_code, presence, depth = validate_component_decision(
                code=code,
                presence=_value(row, "presence", "Presença?", "presenca"),
                depth=_value(row, "depth", "Profundidade 0–3", "profundidade"),
                final=True,
            )
        except ValueError as exc:
            if code:
                normalized[code] = ("INVALID", None)
            invalid.append({"code": code or "<blank>", "error": str(exc)})
            continue
        normalized[norm_code] = (presence, depth)
    present, expected = set(normalized), set(ABCD_CODES)
    missing = [code for code in ABCD_CODES if code not in present]
    unexpected = sorted(present - expected)
    duplicates = sorted(set(duplicates), key=lambda c: ABCD_CODES.index(c) if c in ABCD_COMPONENTS else 999)
    closed = not missing and not unexpected and not duplicates and not invalid and len(normalized) == 34
    return {
        "codebook_version": ABCD_VERSION,
        "expected_components": 34,
        "evaluated_unique_components": len(present & expected),
        "missing_codes": missing,
        "unexpected_codes": unexpected,
        "duplicate_codes": duplicates,
        "invalid_decisions": invalid,
        "closed": closed,
    }


def assert_document_can_close(rows: Iterable[Mapping[str, object]]) -> None:
    status = document_completion(rows)
    if not status["closed"]:
        raise ValueError(f"ABCD extraction cannot close: {status}")


def calibration_metrics(pairs: Sequence[Mapping[str, object]], *, expected_units: int, recurrent_critical_divergence: bool = False) -> dict[str, object]:
    if expected_units <= 0:
        raise ValueError("expected_units must be > 0")
    if len(pairs) > expected_units:
        raise ValueError("paired rows cannot exceed expected_units")
    complete = presence_matches = doubt_r1 = doubt_r2 = depth_pairs = exact_depth = within_one = 0
    invalid: list[dict[str, object]] = []
    for index, row in enumerate(pairs, start=1):
        try:
            _, p1, d1 = validate_component_decision(code=_value(row, "code", "Código"), presence=_value(row, "r1_presence", "R1 presença"), depth=_value(row, "r1_depth", "R1 profundidade"), final=False)
            _, p2, d2 = validate_component_decision(code=_value(row, "code", "Código"), presence=_value(row, "r2_presence", "R2 presença"), depth=_value(row, "r2_depth", "R2 profundidade"), final=False)
        except ValueError as exc:
            invalid.append({"row": index, "error": str(exc)})
            continue
        complete += 1
        doubt_r1 += p1 == "DOUBT"
        doubt_r2 += p2 == "DOUBT"
        presence_matches += p1 == p2
        if p1 == p2 == "YES":
            depth_pairs += 1
            exact_depth += d1 == d2
            within_one += abs(int(d1) - int(d2)) <= 1
    completeness = complete / expected_units
    presence_agreement = presence_matches / complete if complete else None
    exact_agreement = exact_depth / depth_pairs if depth_pairs else None
    within_one_agreement = within_one / depth_pairs if depth_pairs else None
    stability = bool(
        completeness == 1.0 and presence_agreement is not None and presence_agreement >= 0.80
        and exact_agreement is not None and exact_agreement >= 0.70
        and within_one_agreement is not None and within_one_agreement >= 0.90
        and not recurrent_critical_divergence and not invalid
    )
    return {
        "expected_paired_decisions": expected_units,
        "complete_paired_decisions": complete,
        "completeness": completeness,
        "presence_denominator": complete,
        "presence_exact_matches": presence_matches,
        "presence_raw_agreement": presence_agreement,
        "r1_doubt_count": doubt_r1,
        "r2_doubt_count": doubt_r2,
        "depth_denominator_both_yes": depth_pairs,
        "exact_depth_matches": exact_depth,
        "exact_depth_agreement": exact_agreement,
        "depth_within_one_matches": within_one,
        "depth_within_one_agreement": within_one_agreement,
        "recurrent_critical_divergence": bool(recurrent_critical_divergence),
        "invalid_pairs": invalid,
        "stability_signal": stability,
        "interpretation": "Operational calibration signal only; not evidence of validity, quality, maturity or superiority.",
    }


def assert_article1_export_schema_is_safe(columns: Iterable[str]) -> None:
    normalized = {str(column).strip().lower() for column in columns}
    forbidden = sorted(normalized & FORBIDDEN_ARTICLE1_EXPORT_FIELDS)
    if forbidden:
        raise ValueError("canonical Article 1 export contains forbidden fields: " + ", ".join(forbidden))


def codebook_rows() -> list[dict[str, str]]:
    return [{"version": ABCD_VERSION, "code": spec.code, "macro": spec.macro, "label": spec.label} for spec in ABCD_COMPONENTS.values()]
