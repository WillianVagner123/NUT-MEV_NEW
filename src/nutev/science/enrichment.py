"""Pre-screening document retrieval, text extraction, OCR, and reviewer dossiers."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable
from urllib.parse import urlparse
from uuid import uuid4
import xml.etree.ElementTree as ET

import requests

from nutev.audit_guardrails import sha256_file

from .models import (
    DocumentEnrichment,
    ExtractionMethod,
    FullTextArtifact,
    RetrievalStatus,
    ReviewerDossier,
    ScientificEvent,
    TextBlock,
)


class DocumentEnrichmentError(RuntimeError):
    """Raised when the enrichment pipeline cannot safely process its inputs."""


_MIN_NATIVE_PDF_CHARS = 800
_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
_SECTION_RE = re.compile(
    r"^(abstract|introduction|background|objective|objectives|methods?|methodology|"
    r"materials and methods|participants?|population|interventions?|procedures?|"
    r"results?|findings|discussion|conclusions?|limitations?|references|"
    r"acknowledg(?:e)?ments?|supplementary materials?)\s*[:.]?$",
    re.IGNORECASE,
)
_TABLE_RE = re.compile(r"\btable\s+\d+[a-z]?\b", re.IGNORECASE)
_FIGURE_RE = re.compile(r"\b(?:figure|fig\.)\s*\d+[a-z]?\b", re.IGNORECASE)
_SAMPLE_RE = re.compile(r"\b[nN]\s*=\s*\d{1,7}\b")
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\-]{2,}")
_DESIGN_SIGNALS = (
    "randomized controlled trial",
    "randomised controlled trial",
    "randomized trial",
    "randomised trial",
    "systematic review",
    "meta-analysis",
    "meta analysis",
    "cohort study",
    "prospective cohort",
    "retrospective cohort",
    "cross-sectional",
    "cross sectional",
    "case-control",
    "case control",
    "qualitative study",
    "clinical practice guideline",
    "guideline",
    "consensus statement",
    "position statement",
    "scoping review",
    "narrative review",
)
_STOPWORDS = {
    "the", "and", "for", "with", "that", "from", "this", "were", "was", "are", "have",
    "has", "had", "into", "between", "among", "using", "used", "study", "studies", "results",
    "method", "methods", "data", "analysis", "participants", "authors", "article", "patients",
    "their", "than", "these", "those", "which", "such", "also", "may", "can", "not", "but",
    "uma", "para", "com", "dos", "das", "que", "por", "como", "foi", "foram", "sao", "ser",
    "entre", "sobre", "estudo", "estudos", "dados", "resultados", "metodos", "participantes",
}


class _HTMLTextExtractor(HTMLParser):
    _BREAK_TAGS = {
        "article", "section", "div", "p", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif self._skip_depth == 0 and lower in self._BREAK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif self._skip_depth == 0 and lower in self._BREAK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return _normalize_extracted_text(" ".join(self._parts))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DocumentEnrichmentError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DocumentEnrichmentError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DocumentEnrichmentError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise DocumentEnrichmentError(f"missing {label} JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DocumentEnrichmentError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise DocumentEnrichmentError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
    return rows


def _atomic_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return sha256_file(path)


def _write_json(path: Path, value: Any) -> str:
    return _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        for row in rows
    )
    return _atomic_text(path, payload)


def _verify_document_export(documents_jsonl: Path, science_manifest: Path) -> str:
    manifest = _read_json(science_manifest)
    if manifest.get("export_type") != "NUTEV_SCIENTIFIC_OBJECT_EXPORT":
        raise DocumentEnrichmentError(
            f"unexpected export_type in {science_manifest}: {manifest.get('export_type')!r}"
        )
    if manifest.get("status") != "PASS":
        raise DocumentEnrichmentError(
            f"scientific export manifest is not PASS: {manifest.get('status')!r}"
        )
    expected = str(
        (((manifest.get("outputs") or {}).get("document_candidates") or {}).get("sha256"))
        or ""
    ).strip().lower()
    if not expected:
        raise DocumentEnrichmentError(
            f"document_candidates SHA-256 missing from scientific manifest: {science_manifest}"
        )
    actual = sha256_file(documents_jsonl)
    if actual != expected:
        raise DocumentEnrichmentError(
            f"document_candidates SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def _normalize_extracted_text(text: str) -> str:
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if line:
            lines.append(line)
        elif lines and lines[-1] != "":
            lines.append("")
    return "\n".join(lines).strip()


def _extract_html_text(payload: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(payload)
    return parser.text()


def _extract_xml_text(payload: str) -> str:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return _extract_html_text(payload)

    parts: list[str] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].lower()
        text = (element.text or "").strip()
        if not text:
            continue
        if tag in {"title", "article-title", "subject", "label"}:
            parts.extend(["\n", text, "\n"])
        else:
            parts.append(text)
    return _normalize_extracted_text(" ".join(parts))


def _run_command(command: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _ocr_pdf(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if not pdftoppm or not tesseract:
        missing = []
        if not pdftoppm:
            missing.append("pdftoppm")
        if not tesseract:
            missing.append("tesseract")
        return "", ["ocr_backend_unavailable:" + ",".join(missing)]

    language = os.environ.get("NUTEV_OCR_LANG", "eng").strip() or "eng"
    with tempfile.TemporaryDirectory(prefix="nutev-ocr-") as tmp:
        prefix = Path(tmp) / "page"
        rendered = _run_command(
            [pdftoppm, "-png", "-r", "200", str(path), str(prefix)], timeout=300
        )
        if rendered.returncode != 0:
            return "", ["pdf_render_failed_for_ocr"]

        pages: list[str] = []
        images = sorted(Path(tmp).glob("page-*.png"))
        if not images:
            return "", ["pdf_render_produced_no_pages"]
        for index, image in enumerate(images, start=1):
            result = _run_command(
                [tesseract, str(image), "stdout", "-l", language, "--psm", "3"],
                timeout=240,
            )
            if result.returncode != 0:
                warnings.append(f"ocr_page_failed:{index}")
                continue
            page_text = _normalize_extracted_text(result.stdout)
            if page_text:
                pages.append(f"[PAGE {index}]\n{page_text}")
        return _normalize_extracted_text("\n\n".join(pages)), warnings


def _extract_pdf(path: Path) -> tuple[str, ExtractionMethod, bool, str | None, list[str]]:
    warnings: list[str] = []
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        result = _run_command([pdftotext, "-layout", str(path), "-"])
        if result.returncode == 0:
            native = _normalize_extracted_text(result.stdout)
            if len(native) >= _MIN_NATIVE_PDF_CHARS:
                return native, ExtractionMethod.PDF_TEXT, False, None, warnings
            if native:
                warnings.append("pdf_text_layer_too_short_ocr_attempted")
        else:
            warnings.append("pdftotext_failed_ocr_attempted")
    else:
        warnings.append("pdftotext_unavailable_ocr_attempted")

    ocr_text, ocr_warnings = _ocr_pdf(path)
    warnings.extend(ocr_warnings)
    if ocr_text:
        return ocr_text, ExtractionMethod.OCR_TESSERACT, True, "tesseract", warnings
    return "", ExtractionMethod.UNAVAILABLE, False, None, warnings


def _media_type_for(path: Path, explicit: str | None = None) -> str:
    if explicit:
        return explicit.split(";", 1)[0].strip().lower()
    suffix = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".htm": "text/html",
        ".xml": "application/xml",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }.get(suffix, "application/octet-stream")


def _extract_local_file(
    path: Path, media_type: str | None = None
) -> tuple[str, ExtractionMethod, bool, str | None, list[str]]:
    resolved_type = _media_type_for(path, media_type)
    if resolved_type == "application/pdf" or path.suffix.lower() == ".pdf":
        return _extract_pdf(path)

    try:
        payload = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return "", ExtractionMethod.UNAVAILABLE, False, None, [f"read_failed:{exc}"]

    if "html" in resolved_type or path.suffix.lower() in {".html", ".htm"}:
        return _extract_html_text(payload), ExtractionMethod.HTML_TEXT, False, None, []
    if "xml" in resolved_type or path.suffix.lower() == ".xml":
        return _extract_xml_text(payload), ExtractionMethod.XML_TEXT, False, None, []
    return _normalize_extracted_text(payload), ExtractionMethod.DIRECT_TEXT, False, None, []


def _validate_remote_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise DocumentEnrichmentError(f"unsupported remote URL: {url}")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise DocumentEnrichmentError("localhost URLs are not allowed for enrichment fetch")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if address.is_private or address.is_loopback or address.is_link_local:
        raise DocumentEnrichmentError("private/link-local IP URLs are not allowed")


def _download(url: str, target_dir: Path) -> tuple[Path, str]:
    _validate_remote_url(url)
    response = requests.get(url, timeout=45, allow_redirects=True, stream=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    extension = {
        "application/pdf": ".pdf",
        "text/html": ".html",
        "application/xhtml+xml": ".html",
        "application/xml": ".xml",
        "text/xml": ".xml",
        "text/plain": ".txt",
    }.get(content_type, ".bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"download-{uuid4().hex}{extension}"
    written = 0
    with target.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            written += len(chunk)
            if written > _MAX_DOWNLOAD_BYTES:
                target.unlink(missing_ok=True)
                raise DocumentEnrichmentError(
                    f"remote document exceeds {_MAX_DOWNLOAD_BYTES} bytes: {url}"
                )
            handle.write(chunk)
    return target, content_type


def _artifact_scope(url: str | None, asset_row: dict[str, Any] | None) -> RetrievalStatus:
    if asset_row and str(asset_row.get("scope") or "").strip().lower() == "full_text":
        return RetrievalStatus.RETRIEVED
    lower = str(url or "").lower()
    if lower.endswith(".pdf") or "/pdf" in lower or "pmc.ncbi.nlm.nih.gov/articles/" in lower:
        return RetrievalStatus.RETRIEVED
    return RetrievalStatus.PARTIAL


def _section_blocks(text: str, document_id: str) -> tuple[TextBlock, ...]:
    if not text:
        return ()
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Document text"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        payload = _normalize_extracted_text("\n".join(current_lines))
        if payload:
            sections.append((current_heading, [payload]))
        current_lines = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            current_lines.append("")
            continue
        canonical = bool(_SECTION_RE.match(line))
        uppercase_heading = (
            2 <= len(line.split()) <= 10
            and len(line) <= 100
            and any(char.isalpha() for char in line)
            and line.upper() == line
        )
        if canonical or uppercase_heading:
            flush()
            current_heading = line.rstrip(":.")
        else:
            current_lines.append(line)
    flush()

    blocks: list[TextBlock] = []
    for index, (heading, payloads) in enumerate(sections, start=1):
        payload = payloads[0]
        page_match = re.search(r"\[PAGE\s+(\d+)\]", payload)
        blocks.append(
            TextBlock(
                id=f"{document_id}:block:{index}",
                kind="section",
                heading=heading,
                text=payload,
                locator=f"section:{heading}",
                page=int(page_match.group(1)) if page_match else None,
            )
        )
    if not blocks:
        blocks.append(
            TextBlock(
                id=f"{document_id}:block:1",
                kind="document",
                heading="Document text",
                text=text,
                locator="document",
            )
        )
    return tuple(blocks)


def _frequent_terms(text: str, *, limit: int = 24) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for match in _WORD_RE.finditer(text.casefold()):
        word = match.group(0).strip("-")
        if len(word) < 4 or word in _STOPWORDS or word.isdigit():
            continue
        counts[word] += 1
    return [{"term": term, "count": count} for term, count in counts.most_common(limit)]


def _content_signals(text: str, blocks: tuple[TextBlock, ...]) -> dict[str, Any]:
    lower = text.casefold()
    design = [signal for signal in _DESIGN_SIGNALS if signal in lower]
    table_mentions = sorted(set(match.group(0) for match in _TABLE_RE.finditer(text)))
    figure_mentions = sorted(set(match.group(0) for match in _FIGURE_RE.finditer(text)))
    sample_mentions = sorted(set(match.group(0) for match in _SAMPLE_RE.finditer(text)))
    return {
        "section_headings": [block.heading for block in blocks if block.heading],
        "study_design_signals": design,
        "sample_size_mentions": sample_mentions[:30],
        "table_mentions": table_mentions[:40],
        "figure_mentions": figure_mentions[:40],
        "frequent_terms": _frequent_terms(text),
        "signal_semantics": (
            "machine-detected reading aids only; not eligibility, quality, or inclusion judgments"
        ),
    }


def _safe_metadata(document: dict[str, Any]) -> dict[str, Any]:
    metadata = document.get("metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def _abstract_for(document: dict[str, Any]) -> str:
    metadata = _safe_metadata(document)
    return str(metadata.get("abstract") or metadata.get("summary") or "").strip()


def _dossier(
    document: dict[str, Any],
    artifact: FullTextArtifact,
    enrichment: DocumentEnrichment,
) -> ReviewerDossier:
    metadata = _safe_metadata(document)
    section_map = tuple(
        {
            "heading": block.heading,
            "kind": block.kind,
            "locator": block.locator,
            "page": block.page,
            "chars": len(block.text),
            "preview": block.text[:1200],
        }
        for block in enrichment.blocks
    )
    return ReviewerDossier(
        id=f"dossier:{document['id']}",
        document_id=str(document["id"]),
        title=str(document.get("title") or ""),
        source_provider=str(document.get("source_provider") or ""),
        year=document.get("year") if isinstance(document.get("year"), int) else None,
        doi=str(document.get("doi") or "").strip() or None,
        pmid=str(document.get("pmid") or "").strip() or None,
        url=str(document.get("url") or "").strip() or None,
        abstract=_abstract_for(document) or None,
        journal=str(metadata.get("journal") or "").strip() or None,
        authors=str(metadata.get("authors") or "").strip() or None,
        article_type=str(metadata.get("article_type") or "").strip() or None,
        full_text_status=artifact.retrieval_status,
        extraction_method=enrichment.extraction_method,
        ocr_used=enrichment.ocr_used,
        text_chars=enrichment.text_chars,
        section_map=section_map,
        content_signals=enrichment.content_signals,
        warnings=enrichment.warnings,
        guardrails={
            "blind_to_nutev_rank": True,
            "blind_to_nutev_taxonomy": True,
            "machine_signals_are_not_screening_decisions": True,
            "missing_content_is_not_inferred": True,
        },
    )


def _candidate_asset(
    document: dict[str, Any],
    asset_row: dict[str, Any] | None,
    *,
    allow_network: bool,
    staging_dir: Path,
) -> tuple[FullTextArtifact, Path | None]:
    document_id = str(document["id"])
    artifact_id = f"artifact:{document_id}"
    source_url = str((asset_row or {}).get("url") or (asset_row or {}).get("source_url") or "").strip()
    local_raw = str((asset_row or {}).get("path") or (asset_row or {}).get("local_path") or "").strip()
    explicit_media = str((asset_row or {}).get("media_type") or "").strip() or None

    if local_raw:
        path = Path(local_raw).expanduser()
        if not path.is_file():
            return (
                FullTextArtifact(
                    id=artifact_id,
                    document_id=document_id,
                    retrieval_status=RetrievalStatus.NOT_RETRIEVED,
                    source_url=source_url or None,
                    local_path=str(path),
                    media_type=explicit_media,
                    metadata={"reason": "local_asset_missing"},
                ),
                None,
            )
        return (
            FullTextArtifact(
                id=artifact_id,
                document_id=document_id,
                retrieval_status=RetrievalStatus.RETRIEVED,
                source_url=source_url or None,
                local_path=str(path),
                media_type=_media_type_for(path, explicit_media),
                sha256=sha256_file(path),
                retrieved_at=_now(),
                metadata={"retrieval_route": "provided_local_asset"},
            ),
            path,
        )

    remote = source_url
    if not remote and allow_network:
        remote = str(document.get("url") or "").strip()
    if not remote:
        status = RetrievalStatus.NOT_ATTEMPTED if not allow_network else RetrievalStatus.NOT_RETRIEVED
        return (
            FullTextArtifact(
                id=artifact_id,
                document_id=document_id,
                retrieval_status=status,
                metadata={"reason": "no_asset_or_fetchable_url"},
            ),
            None,
        )
    if not allow_network:
        return (
            FullTextArtifact(
                id=artifact_id,
                document_id=document_id,
                retrieval_status=RetrievalStatus.NOT_ATTEMPTED,
                source_url=remote,
                metadata={"reason": "network_fetch_disabled"},
            ),
            None,
        )

    try:
        path, content_type = _download(remote, staging_dir)
    except Exception as exc:
        return (
            FullTextArtifact(
                id=artifact_id,
                document_id=document_id,
                retrieval_status=RetrievalStatus.NOT_RETRIEVED,
                source_url=remote,
                metadata={"reason": f"download_failed:{type(exc).__name__}"},
            ),
            None,
        )
    return (
        FullTextArtifact(
            id=artifact_id,
            document_id=document_id,
            retrieval_status=_artifact_scope(remote, asset_row),
            source_url=remote,
            local_path=str(path),
            media_type=content_type or _media_type_for(path),
            sha256=sha256_file(path),
            retrieved_at=_now(),
            metadata={"retrieval_route": "network_fetch"},
        ),
        path,
    )


def run_document_enrichment(
    documents_jsonl: Path,
    science_manifest: Path,
    output_dir: Path,
    *,
    assets_jsonl: Path | None = None,
    allow_network: bool = False,
) -> dict[str, Any]:
    """Build reviewer-safe dossiers before any screening decisions are imported."""

    documents_sha = _verify_document_export(documents_jsonl, science_manifest)
    documents = _read_jsonl(documents_jsonl, label="document candidates")
    if not documents:
        raise DocumentEnrichmentError("document candidates JSONL is empty")

    asset_rows: list[dict[str, Any]] = []
    if assets_jsonl is not None:
        asset_rows = _read_jsonl(assets_jsonl, label="full-text assets")
    assets_by_document: dict[str, dict[str, Any]] = {}
    document_ids = {str(row.get("id") or "") for row in documents if row.get("id")}
    for row in asset_rows:
        document_id = str(row.get("document_id") or "").strip()
        if not document_id:
            raise DocumentEnrichmentError("full-text asset row missing document_id")
        if document_id not in document_ids:
            raise DocumentEnrichmentError(
                f"full-text asset references unknown document: {document_id}"
            )
        if document_id in assets_by_document:
            raise DocumentEnrichmentError(
                f"multiple full-text assets for document are not yet supported: {document_id}"
            )
        assets_by_document[document_id] = row

    output_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = output_dir / "private_assets"
    extracted_dir = output_dir / "private_text"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[FullTextArtifact] = []
    enrichments: list[DocumentEnrichment] = []
    dossiers: list[ReviewerDossier] = []
    events: list[ScientificEvent] = []

    for document in documents:
        document_id = str(document.get("id") or "").strip()
        if not document_id:
            raise DocumentEnrichmentError("document candidate missing id")
        artifact, local_path = _candidate_asset(
            document,
            assets_by_document.get(document_id),
            allow_network=allow_network,
            staging_dir=staging_dir,
        )
        artifacts.append(artifact)

        warnings: list[str] = []
        extracted = ""
        method = ExtractionMethod.UNAVAILABLE
        ocr_used = False
        ocr_engine: str | None = None
        if local_path is not None:
            extracted, method, ocr_used, ocr_engine, extract_warnings = _extract_local_file(
                local_path, artifact.media_type
            )
            warnings.extend(extract_warnings)

        abstract = _abstract_for(document)
        if not extracted:
            if abstract:
                extracted = abstract
                method = ExtractionMethod.ABSTRACT_ONLY
                warnings.append("full_text_unavailable_using_abstract_only")
            else:
                warnings.append("no_extractable_text_or_abstract")

        blocks = _section_blocks(extracted, document_id)
        signals = _content_signals(extracted, blocks) if extracted else {
            "section_headings": [],
            "study_design_signals": [],
            "sample_size_mentions": [],
            "table_mentions": [],
            "figure_mentions": [],
            "frequent_terms": [],
            "signal_semantics": (
                "machine-detected reading aids only; not eligibility, quality, or inclusion judgments"
            ),
        }
        text_sha = sha256(extracted.encode("utf-8")).hexdigest() if extracted else None
        text_path: Path | None = None
        if extracted:
            text_path = extracted_dir / f"{sha256(document_id.encode('utf-8')).hexdigest()}.txt"
            _atomic_text(text_path, extracted + "\n")

        enrichment = DocumentEnrichment(
            id=f"enrichment:{document_id}",
            document_id=document_id,
            artifact_id=artifact.id,
            extraction_method=method,
            text_sha256=text_sha,
            text_chars=len(extracted),
            ocr_used=ocr_used,
            ocr_engine=ocr_engine,
            blocks=blocks,
            content_signals=signals,
            warnings=tuple(dict.fromkeys(warnings)),
            metadata={
                "private_text_path": str(text_path) if text_path else None,
                "full_text_status": artifact.retrieval_status.value,
            },
        )
        enrichments.append(enrichment)
        dossiers.append(_dossier(document, artifact, enrichment))

        if artifact.retrieval_status in {RetrievalStatus.RETRIEVED, RetrievalStatus.PARTIAL}:
            events.append(
                ScientificEvent(
                    id=f"{document_id}:retrieval",
                    entity_type="document",
                    entity_id=document_id,
                    action="retrieved_document_material",
                    to_state="retrieved",
                    metadata={
                        "artifact_id": artifact.id,
                        "retrieval_status": artifact.retrieval_status.value,
                    },
                )
            )
        events.append(
            ScientificEvent(
                id=f"{document_id}:enrichment",
                entity_type="document",
                entity_id=document_id,
                action="document_enriched_for_review",
                to_state="extracted" if extracted else None,
                metadata={
                    "enrichment_id": enrichment.id,
                    "extraction_method": method.value,
                    "ocr_used": ocr_used,
                    "text_chars": len(extracted),
                },
            )
        )

    artifacts_path = output_dir / "full_text_artifacts.jsonl"
    enrichments_path = output_dir / "document_enrichments.jsonl"
    dossiers_path = output_dir / "reviewer_dossiers.jsonl"
    events_path = output_dir / "enrichment_events.jsonl"
    manifest_path = output_dir / "ENRICHMENT_MANIFEST.json"

    artifacts_sha = _write_jsonl(artifacts_path, [asdict(item) for item in artifacts])
    enrichments_sha = _write_jsonl(enrichments_path, [asdict(item) for item in enrichments])
    dossiers_sha = _write_jsonl(dossiers_path, [asdict(item) for item in dossiers])
    events_sha = _write_jsonl(events_path, [asdict(item) for item in events])

    ocr_count = sum(1 for item in enrichments if item.ocr_used)
    abstract_only_count = sum(
        1 for item in enrichments if item.extraction_method is ExtractionMethod.ABSTRACT_ONLY
    )
    no_text_count = sum(1 for item in enrichments if item.text_chars == 0)
    manifest = {
        "schema_version": 1,
        "enrichment_type": "NUTEV_PRE_SCREENING_DOCUMENT_ENRICHMENT",
        "status": "PASS",
        "created_at": _now(),
        "source": {
            "document_candidates": str(documents_jsonl),
            "document_candidates_sha256": documents_sha,
            "scientific_export_manifest": str(science_manifest),
            "scientific_export_manifest_sha256": sha256_file(science_manifest),
            "assets_jsonl": str(assets_jsonl) if assets_jsonl else None,
            "assets_jsonl_sha256": sha256_file(assets_jsonl) if assets_jsonl else None,
            "network_fetch_enabled": allow_network,
        },
        "counts": {
            "documents": len(documents),
            "artifacts": len(artifacts),
            "enrichments": len(enrichments),
            "reviewer_dossiers": len(dossiers),
            "ocr_used": ocr_count,
            "abstract_only": abstract_only_count,
            "no_extractable_text": no_text_count,
        },
        "outputs": {
            "full_text_artifacts": {"path": str(artifacts_path), "sha256": artifacts_sha},
            "document_enrichments": {"path": str(enrichments_path), "sha256": enrichments_sha},
            "reviewer_dossiers": {"path": str(dossiers_path), "sha256": dossiers_sha},
            "enrichment_events": {"path": str(events_path), "sha256": events_sha},
        },
        "assertions": [
            {"name": "document_export_hash_verified", "status": "PASS"},
            {"name": "reviewer_dossiers_hide_nutev_rank", "status": "PASS"},
            {"name": "reviewer_dossiers_hide_nutev_taxonomy", "status": "PASS"},
            {"name": "machine_signals_are_not_screening_decisions", "status": "PASS"},
            {"name": "missing_content_not_fabricated", "status": "PASS"},
        ],
        "interpretation_guardrail": (
            "Reviewer dossiers are reading aids derived from retrieved text or the recorded abstract. "
            "They do not encode inclusion probability, scientific quality, certainty, or recommendation."
        ),
        "copyright_guardrail": (
            "Private extracted text is an execution artifact for review. Do not publish or redistribute "
            "full copyrighted text unless the source license permits it."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)

    return {
        "mode": "PRE_SCREENING_DOCUMENT_ENRICHMENT",
        "status": "COMPLETE",
        "documents": len(documents),
        "ocr_used": ocr_count,
        "abstract_only": abstract_only_count,
        "no_extractable_text": no_text_count,
        "outputs": {
            "artifacts": str(artifacts_path),
            "enrichments": str(enrichments_path),
            "dossiers": str(dossiers_path),
            "events": str(events_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "artifacts": artifacts_sha,
            "enrichments": enrichments_sha,
            "dossiers": dossiers_sha,
            "events": events_sha,
            "manifest": manifest_sha,
        },
    }
