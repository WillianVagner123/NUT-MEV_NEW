from __future__ import annotations

from collections.abc import Iterable

DOCUMENT_CLASS_ONTOLOGY_VERSION = "nutev-document-class-v1"

CANONICAL_DOCUMENT_CLASS_MEMBERS: dict[str, tuple[str, ...]] = {
    "evidence_synthesis": ("evidence_synthesis",),
    "guidance": (
        "guidance",
        "food_based_dietary_guideline",
        "clinical_practice_guideline",
        "consensus_statement",
        "position_statement",
    ),
    "framework_implementation": (
        "framework_implementation",
        "framework_model",
        "competency_curriculum",
        "implementation_evaluation",
    ),
    "primary_randomized": ("primary_randomized",),
    "primary_observational": ("primary_observational",),
    "primary_qualitative": ("primary_qualitative",),
    "review": ("review",),
    "unclassified": ("unclassified",),
}

CANONICAL_DOCUMENT_CLASS_LABELS: dict[str, str] = {
    "evidence_synthesis": "Síntese de evidência",
    "guidance": "Diretriz / orientação",
    "framework_implementation": "Framework / implementação",
    "primary_randomized": "Ensaio randomizado",
    "primary_observational": "Estudo observacional",
    "primary_qualitative": "Estudo qualitativo",
    "review": "Revisão",
    "unclassified": "Não classificado",
}

_MEMBER_TO_CANONICAL = {
    member: canonical
    for canonical, members in CANONICAL_DOCUMENT_CLASS_MEMBERS.items()
    for member in members
}


def canonical_document_class(value: object) -> str:
    return _MEMBER_TO_CANONICAL.get(str(value or "").strip(), "unclassified")


def document_classes_for_canonical(value: object) -> tuple[str, ...]:
    key = str(value or "").strip()
    return CANONICAL_DOCUMENT_CLASS_MEMBERS.get(key, (key,) if key else ())


def canonicalize_document_classes(values: Iterable[object]) -> list[str]:
    output: list[str] = []
    for value in values:
        canonical = canonical_document_class(value)
        if canonical not in output:
            output.append(canonical)
    return output
