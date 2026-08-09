"""Article 1 analytical coding for tracks, A/B/C/D domains, AACODS and archiving.

This module implements the *documented, reproducible* coding scheme that produces
the central result of Article 1 (the scoping review). It is deliberately
transparent and heuristic, and it never finalizes anything — every output is an
assistive suggestion that enters human review (see docs/SCIENTIFIC_GOVERNANCE.md
and docs/ARTICLE1_DOMAIN_CODING.md).

- **Tracks** (PRISMA 2020 separates "databases/registers" from "other methods")
  are derived from where a record came from.
- The four **analytical domains** (A/B/C/D) are coded with a keyword scheme gated
  by a *substantive* rule — a domain is only marked when it is contemplated in an
  actionable way (recommendation/guidance/strategy), not merely mentioned.
- **AACODS** (Authority, Accuracy, Coverage, Objectivity, Date currency,
  Significance) fields are scaffolded for grey-literature appraisal; only what is
  objectively derivable is auto-filled and the rest carries ``needs_human_review``.
- SHA-256 archiving supports the "links break, guidelines get updated" problem.

Every function is pure and side-effect free except :func:`sha256_of_file`, which
only reads.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

# --------------------------------------------------------------------------- #
# Tracks (P2) — PRISMA 2020 "databases/registers" vs "other methods".
# --------------------------------------------------------------------------- #

TRACKS = (
    "guideline_repository",          # FAO FBDG repository, ministries — NOT indexed
    "indexed_database",              # PubMed, Europe PMC, OpenAlex, Crossref, Scopus, WoS
    "society_website",               # SBC, SBD, ABESO, SBH, ACLM, ADA, AHA, ESPEN…
    "reference_chaining",            # found by following references of included records
    "hand_search",                   # targeted manual search of a known source
    "linked_implementation_material",  # material linked from a Track 1/2 document (A2)
)

# Only "indexed_database" counts as a PRISMA "databases/registers" record; every
# other track is a "other methods" record. Used by the two-track PRISMA report.
PRISMA_DATABASE_TRACK = "indexed_database"

_INDEXED_PROVIDERS = {
    "pubmed", "europepmc", "europe_pmc", "openalex", "crossref", "scopus",
    "web_of_science", "wos", "embase", "doaj",
}
_GUIDELINE_REPO_TOKENS = ("official_web", "official", "fao", "who", "iris")
_SOCIETY_TOKENS = (
    "society", "sociedade", "sbc", "sbd", "abeso", "sbh", "aclm", "ada", "aha",
    "espen", "acp", "easo", "college", "association", "associacao", "academy",
)


def classify_track(record: dict) -> str:
    """Return the PRISMA track for a record from its provenance.

    An explicit ``track`` on the record wins; otherwise it is inferred from the
    provider/institution. Unknown provenance is conservatively ``hand_search`` so
    it is counted under "other methods", never silently as a database hit.
    """
    explicit = str(record.get("track") or "").strip().lower()
    if explicit in TRACKS:
        return explicit

    provider = str(record.get("source_provider") or record.get("source") or "").lower()
    institution = str(record.get("source_institution") or "").lower()
    blob = f"{provider} {institution}"

    if any(tok in provider for tok in ("pubmed", "europepmc", "openalex", "crossref")) or provider in _INDEXED_PROVIDERS:
        return "indexed_database"
    if any(tok in blob for tok in _GUIDELINE_REPO_TOKENS):
        return "guideline_repository"
    if any(tok in blob for tok in _SOCIETY_TOKENS):
        return "society_website"
    return "hand_search"


# --------------------------------------------------------------------------- #
# Provenance fields (P2): issuing body, WHO region, income band.
# --------------------------------------------------------------------------- #

# Compact country -> WHO region map (best-effort; unknown -> ""). WHO regions:
# AFR, AMR, SEAR, EUR, EMR, WPR.
_WHO_REGION = {
    # AMR
    "brazil": "AMR", "brasil": "AMR", "united states": "AMR", "usa": "AMR", "canada": "AMR",
    "mexico": "AMR", "argentina": "AMR", "chile": "AMR", "colombia": "AMR", "peru": "AMR",
    "ecuador": "AMR", "bolivia": "AMR", "paraguay": "AMR", "uruguay": "AMR", "cuba": "AMR",
    "guatemala": "AMR", "honduras": "AMR", "panama": "AMR", "el salvador": "AMR",
    # EUR
    "portugal": "EUR", "spain": "EUR", "france": "EUR", "germany": "EUR", "italy": "EUR",
    "united kingdom": "EUR", "ireland": "EUR", "sweden": "EUR", "denmark": "EUR",
    "norway": "EUR", "finland": "EUR", "netherlands": "EUR", "austria": "EUR", "poland": "EUR",
    "greece": "EUR", "hungary": "EUR", "romania": "EUR", "bulgaria": "EUR", "estonia": "EUR",
    "latvia": "EUR", "lithuania": "EUR", "iceland": "EUR", "malta": "EUR", "israel": "EUR",
    # AFR
    "nigeria": "AFR", "ghana": "AFR", "south africa": "AFR", "kenya": "AFR", "namibia": "AFR",
    "zambia": "AFR", "sierra leone": "AFR", "benin": "AFR", "gabon": "AFR", "ethiopia": "AFR",
    # EMR
    "qatar": "EMR", "saudi arabia": "EMR", "lebanon": "EMR", "oman": "EMR", "pakistan": "EMR",
    # SEAR
    "india": "SEAR", "bangladesh": "SEAR", "nepal": "SEAR", "thailand": "SEAR", "myanmar": "SEAR",
    # WPR
    "china": "WPR", "japan": "WPR", "korea": "WPR", "south korea": "WPR", "vietnam": "WPR",
    "philippines": "WPR", "cambodia": "WPR", "mongolia": "WPR", "fiji": "WPR", "samoa": "WPR",
    "australia": "WPR", "new zealand": "WPR",
}


def who_region(record: dict) -> str:
    """Best-effort WHO region from the record's country. Unknown -> ''."""
    explicit = str(record.get("who_region") or "").strip().upper()
    if explicit:
        return explicit
    country = str(record.get("country") or "").strip().lower()
    return _WHO_REGION.get(country, "")


def provenance_fields(record: dict) -> dict:
    """Return the Track-provenance fields, using explicit values when present.

    ``income_band`` is intentionally NOT guessed (World Bank classification
    changes yearly); it is passed through if present and left blank otherwise for
    a human/config to fill — consistent with the "não invente" rule.
    """
    return {
        "issuing_body": str(record.get("issuing_body") or record.get("source_institution") or ""),
        "country": str(record.get("country") or ""),
        "who_region": who_region(record),
        "income_band": str(record.get("income_band") or ""),  # human/config, never guessed
        "document_version": str(record.get("document_version") or ""),
        "access_date": str(record.get("access_date") or ""),
        "official_url": str(record.get("official_url") or record.get("final_url") or record.get("url") or ""),
    }


# --------------------------------------------------------------------------- #
# A/B/C/D analytical domains (P1).
# --------------------------------------------------------------------------- #

_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "A": (  # composição e qualidade da dieta
        "diet quality", "dietary quality", "nutrient", "food group", "dietary pattern",
        "saturated fat", "sodium", "sugar intake", "fruit and vegetable", "whole grain",
        "ultra-processed", "ultraprocessed", "macronutrient", "micronutrient",
        "qualidade da dieta", "padrão alimentar", "nutriente", "grupo alimentar",
        "gordura saturada", "sódio", "ultraprocessado", "consumo de frutas",
    ),
    "B": (  # literacia alimentar, competências culinárias, planejamento
        "food literacy", "nutrition literacy", "cooking skill", "culinary",
        "meal planning", "meal prep", "label reading", "food label", "budgeting",
        "shopping skill", "food preparation", "literacia alimentar", "habilidade culinária",
        "planejamento de refeições", "leitura de rótulo", "preparo de alimentos",
    ),
    "C": (  # comensalidade, cultura, contexto das refeições
        "commensality", "family meal", "shared meal", "eating context", "mealtime",
        "social eating", "food culture", "cultural", "conviviality", "eating environment",
        "comensalidade", "refeição em família", "cultura alimentar", "contexto da refeição",
        "ambiente alimentar", "convivialidade",
    ),
    "D": (  # adesão, viabilidade, barreiras, facilitadores, implementação
        "adherence", "compliance", "feasibility", "barrier", "facilitator",
        "implementation", "uptake", "acceptability", "sustainability", "engagement",
        "adesão", "viabilidade", "barreira", "facilitador", "implementação",
        "aceitabilidade", "sustentabilidade", "adoção",
    ),
}

# Actionable cues: a domain is only "substantive" when the document says or does
# something about it (recommendation / guidance / strategy / intervention), not
# when the term merely appears. This is the core anti-false-positive rule.
_ACTIONABLE_CUES = (
    "recommend", "should", "guidance", "guideline", "strategy", "strategies",
    "intervention", "advise", "must", "encourage", "recomenda", "deve", "diretriz",
    "estratégia", "intervenção", "orienta", "aconselha",
)

_MIN_SUBSTANTIVE_CHARS = 200


def _record_text(record: dict) -> str:
    parts = [str(record.get(k, "") or "") for k in ("title", "abstract", "extracted_text")]
    return " ".join(parts).lower()


def _has_actionable_cue(text: str) -> bool:
    return any(cue in text for cue in _ACTIONABLE_CUES)


def code_domains(record: dict) -> dict:
    """Code the A/B/C/D domains for a record under the substantive rule.

    A domain is marked only when (a) at least one domain keyword is present AND
    (b) the text is substantive — an actionable cue is present in enough text, or
    the record is a guideline/official document whose purpose is to give guidance.
    Mere rhetorical mention does not count. Returns booleans ``domain_A..D`` plus
    derived ``profile`` (e.g. "AD", "ABCD"), ``n_domains`` and
    ``domain_coding_needs_human_review`` (always True — coding is assistive).
    """
    text = _record_text(record)
    source_type = str(record.get("source_type") or record.get("evidence_type") or "").lower()
    is_guidance_doc = any(t in source_type for t in ("guide", "guideline", "consensus", "statement", "diretriz"))
    substantive_context = (len(text) >= _MIN_SUBSTANTIVE_CHARS and _has_actionable_cue(text)) or is_guidance_doc

    flags: dict[str, bool] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        has_keyword = any(kw in text for kw in keywords)
        flags[f"domain_{domain}"] = bool(has_keyword and substantive_context)

    present = [d for d in ("A", "B", "C", "D") if flags[f"domain_{d}"]]
    return {
        **flags,
        "profile": "".join(present),
        "n_domains": len(present),
        "domain_coding_needs_human_review": True,
    }


# Contextual anchors for the Brazilian argument (P1).
_COST_TERMS = (
    "cost", "affordab", "price", "budget", "expensive", "economic access",
    "custo", "preço", "acessibilidade econômica", "subsídio", "renda",
)
_EQUITY_TERMS = (
    "equity", "inequity", "inequalit", "disparit", "vulnerab", "socioeconomic",
    "equidade", "iniquidade", "desigualdade", "disparidade", "socioeconômic",
)


def code_context_flags(record: dict) -> dict:
    """Flag whether cost and equity are addressed (Brazilian-context anchors)."""
    text = _record_text(record)
    return {
        "mentions_cost": any(t in text for t in _COST_TERMS),
        "mentions_equity": any(t in text for t in _EQUITY_TERMS),
    }


# --------------------------------------------------------------------------- #
# AACODS grey-literature appraisal scaffold (P3).
# --------------------------------------------------------------------------- #

# Institutional-endorsement tiers (1 = strongest, 5 = excluded). See
# docs/GREY_LITERATURE_POLICY.md.
_ENDORSEMENT_TIERS = {
    1: ("who", "fao", "ministry", "ministério", "ministerio", "government", "gov.", ".gov"),
    2: ("society", "sociedade", "college", "association", "associacao", "academy", "espen", "ada", "aha"),
    3: ("university", "universidade", "institute", "instituto", "research center"),
    4: ("ngo", "foundation", "fundação", "think tank"),
    5: ("blog", "industry", "indústria", "commercial", "marketing", "promotional"),
}


def endorsement_tier(record: dict) -> int | None:
    """Best-effort institutional-endorsement tier (1 strongest … 5 excluded)."""
    blob = " ".join(
        str(record.get(k, "") or "")
        for k in ("source_institution", "issuing_body", "official_url", "final_url", "source_provider")
    ).lower()
    for tier in (1, 2, 3, 4, 5):
        if any(tok in blob for tok in _ENDORSEMENT_TIERS[tier]):
            return tier
    return None


def aacods_fields(record: dict) -> dict:
    """Scaffold AACODS appraisal fields for grey literature.

    Only objectively-derivable elements are auto-filled: ``authority`` (from the
    issuing-body endorsement tier) and ``date_currency`` (from the year).
    ``accuracy``, ``coverage``, ``objectivity`` and ``significance`` are appraisal
    judgments left for a human, flagged by ``aacods_needs_human_review``.
    See docs/GREY_LITERATURE_POLICY.md.
    """
    tier = endorsement_tier(record)
    year = record.get("year")
    return {
        "authority": f"tier_{tier}" if tier is not None else "",
        "accuracy": "",        # human
        "coverage": "",        # human
        "objectivity": "",     # human
        "date_currency": str(year) if year else "",
        "significance": "",    # human
        "aacods_needs_human_review": True,
    }


# --------------------------------------------------------------------------- #
# Archiving (P3): SHA-256 of the downloaded artifact.
# --------------------------------------------------------------------------- #

def sha256_of_file(path: str | Path) -> str | None:
    """Return the SHA-256 hex digest of a file, or None if it cannot be read."""
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    try:
        with p.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


# Fields a Track-1 (guideline repository) record MUST carry for the archive to be
# auditable — links break and guidelines are re-issued, so the PDF and its hash
# are the permanent record.
TRACK1_ARCHIVE_FIELDS = (
    "issuing_body", "country", "who_region", "document_version", "access_date",
    "official_url", "archived_pdf_path", "archived_pdf_sha256",
)


def article1_record_fields(record: dict) -> dict:
    """Compute all Article-1 analytical fields for one record, in one call.

    Combines track, provenance, domain coding, context flags and AACODS
    scaffolding, and computes the archive SHA-256 when ``archived_pdf_path`` is
    present. Returns a flat dict ready to merge into the metadata row / CSV.
    """
    out: dict = {"track": classify_track(record)}
    out.update(provenance_fields(record))
    out.update(code_domains(record))
    out.update(code_context_flags(record))
    out.update(aacods_fields(record))
    archived = record.get("archived_pdf_path")
    out["archived_pdf_path"] = str(archived or "")
    out["archived_pdf_sha256"] = sha256_of_file(archived) if archived else ""
    return out
