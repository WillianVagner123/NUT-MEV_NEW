"""Optional, non-destructive translation services with full provenance.

Translation is an assistive computational capability. It never overwrites source
text, never changes a frozen search strategy automatically, and never becomes a
human scientific decision. Google Cloud Translation v2 is supported through the
existing ``requests`` dependency; a small generic JSON endpoint contract is also
available for self-hosted/local services.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
import json
import os
from pathlib import Path
import re
from typing import Any, Callable
from uuid import uuid4

import requests

from nutev.language import detect_language, normalize_language_code, translation_record

GOOGLE_TRANSLATE_V2 = "https://translation.googleapis.com/language/translate/v2"
SUPPORTED_PROVIDERS = {"google_cloud_v2", "http_json"}
TranslatorFn = Callable[[str, str, str], dict[str, Any]]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configured_translation_provider(environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    provider = _clean(env.get("NUTEV_TRANSLATION_PROVIDER")).lower()
    return provider if provider in SUPPORTED_PROVIDERS else ""


def translation_configuration(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    provider = configured_translation_provider(env)
    target = normalize_language_code(env.get("NUTEV_TRANSLATION_TARGET") or "pt") or "pt"
    if not provider:
        return {
            "configured": False,
            "provider": None,
            "target_language": target,
            "reason": "NUTEV_TRANSLATION_PROVIDER is not configured",
        }
    if provider == "google_cloud_v2" and not _clean(env.get("GOOGLE_TRANSLATE_API_KEY")):
        return {
            "configured": False,
            "provider": provider,
            "target_language": target,
            "reason": "GOOGLE_TRANSLATE_API_KEY is missing",
        }
    if provider == "http_json" and not _clean(env.get("NUTEV_TRANSLATION_ENDPOINT")):
        return {
            "configured": False,
            "provider": provider,
            "target_language": target,
            "reason": "NUTEV_TRANSLATION_ENDPOINT is missing",
        }
    return {
        "configured": True,
        "provider": provider,
        "target_language": target,
        "reason": "",
    }


def _chunks(text: str, max_chars: int = 4500) -> list[str]:
    """Split text without silently dropping content or changing paragraph order."""
    value = str(text or "")
    if not value:
        return []
    if len(value) <= max_chars:
        return [value]
    paragraphs = re.split(r"(\n\s*\n)", value)
    chunks: list[str] = []
    current = ""
    for part in paragraphs:
        if len(part) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(part), max_chars):
                chunks.append(part[start : start + max_chars])
            continue
        if current and len(current) + len(part) > max_chars:
            chunks.append(current)
            current = part
        else:
            current += part
    if current:
        chunks.append(current)
    return chunks


def _google_translate(
    text: str,
    source_language: str,
    target_language: str,
    *,
    session: requests.Session | None = None,
    timeout: float = 60.0,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    api_key = _clean(env.get("GOOGLE_TRANSLATE_API_KEY"))
    if not api_key:
        raise RuntimeError("GOOGLE_TRANSLATE_API_KEY is missing")
    client = session or requests.Session()
    chunks = _chunks(text)
    translated: list[str] = []
    detected: list[str] = []
    models: list[str] = []
    for chunk in chunks:
        payload: dict[str, Any] = {
            "q": chunk,
            "target": target_language,
            "format": "text",
        }
        if source_language and source_language != "und":
            payload["source"] = source_language
        response = client.post(
            GOOGLE_TRANSLATE_V2,
            params={"key": api_key},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        items = ((body.get("data") or {}).get("translations") or [])
        if len(items) != 1:
            raise RuntimeError("Cloud Translation returned an unexpected response shape")
        item = items[0] or {}
        translated.append(unescape(str(item.get("translatedText") or "")))
        if item.get("detectedSourceLanguage"):
            detected.append(str(item["detectedSourceLanguage"]))
        if item.get("model"):
            models.append(str(item["model"]))
    return {
        "translated_text": "".join(translated),
        "translator": "google_cloud_translation_v2",
        "model_or_version": models[0] if models else "nmt/default",
        "detected_source_language": detected[0] if detected else source_language,
        "chunks": len(chunks),
    }


def _http_json_translate(
    text: str,
    source_language: str,
    target_language: str,
    *,
    session: requests.Session | None = None,
    timeout: float = 60.0,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    endpoint = _clean(env.get("NUTEV_TRANSLATION_ENDPOINT"))
    if not endpoint:
        raise RuntimeError("NUTEV_TRANSLATION_ENDPOINT is missing")
    headers = {"Content-Type": "application/json"}
    token = _clean(env.get("NUTEV_TRANSLATION_TOKEN"))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    client = session or requests.Session()
    response = client.post(
        endpoint,
        json={
            "text": text,
            "source_language": source_language,
            "target_language": target_language,
        },
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    translated = str(body.get("translated_text") or "")
    if not translated:
        raise RuntimeError("translation endpoint returned no translated_text")
    return {
        "translated_text": translated,
        "translator": _clean(body.get("translator")) or "http_json",
        "model_or_version": _clean(body.get("model_or_version")) or "endpoint-declared-unspecified",
        "detected_source_language": _clean(body.get("detected_source_language")) or source_language,
        "chunks": int(body.get("chunks") or 1),
    }


def translate_text(
    text: str,
    *,
    source_language: object = "",
    target_language: object = "pt",
    provider: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 60.0,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    configured = (provider or configured_translation_provider(env)).strip().lower()
    if configured not in SUPPORTED_PROVIDERS:
        raise RuntimeError("no supported translation provider is configured")
    target = normalize_language_code(target_language)
    source = normalize_language_code(source_language)
    if not target:
        raise ValueError("target_language is required")
    if not source:
        source = str(detect_language(text).get("detected_language") or "und")
    if source == target:
        return {
            "translated_text": text,
            "translator": "identity",
            "model_or_version": "same-language",
            "detected_source_language": source,
            "chunks": 0,
            "same_language": True,
        }
    if configured == "google_cloud_v2":
        return _google_translate(
            text,
            source,
            target,
            session=session,
            timeout=timeout,
            environ=env,
        )
    return _http_json_translate(
        text,
        source,
        target,
        session=session,
        timeout=timeout,
        environ=env,
    )


def translate_text_artifact(
    document_id: str,
    original_text_path: Path,
    output_dir: Path,
    *,
    source_language: object = "",
    target_language: object = "pt",
    provider: str | None = None,
    session: requests.Session | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Translate one extracted text into a distinct file; never overwrite source."""
    source_path = Path(original_text_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"original text artifact not found: {source_path}")
    original_bytes = source_path.read_bytes()
    original_text = original_bytes.decode("utf-8", errors="replace")
    source = normalize_language_code(source_language)
    if not source:
        source = str(detect_language(original_text).get("detected_language") or "und")
    target = normalize_language_code(target_language) or "pt"
    config = translation_configuration(environ)
    selected = (provider or str(config.get("provider") or "")).strip().lower()
    created_at = _now()
    original_sha = _sha256_bytes(original_bytes)

    if source == target:
        record = translation_record(
            document_id=document_id,
            source_language=source,
            target_language=target,
            status="SKIPPED",
            original_text_path=str(source_path),
            original_sha256=original_sha,
            created_at=created_at,
        )
        return {**record, "reason": "source_already_target_language"}
    if not config.get("configured") or not selected:
        record = translation_record(
            document_id=document_id,
            source_language=source,
            target_language=target,
            status="SKIPPED",
            original_text_path=str(source_path),
            original_sha256=original_sha,
            created_at=created_at,
        )
        return {**record, "reason": str(config.get("reason") or "translation_not_configured")}

    try:
        result = translate_text(
            original_text,
            source_language=source,
            target_language=target,
            provider=selected,
            session=session,
            environ=environ,
        )
    except Exception as exc:
        record = translation_record(
            document_id=document_id,
            source_language=source,
            target_language=target,
            status="FAILED",
            original_text_path=str(source_path),
            original_sha256=original_sha,
            created_at=created_at,
        )
        return {**record, "reason": str(exc), "translator": selected}

    if result.get("same_language"):
        record = translation_record(
            document_id=document_id,
            source_language=source,
            target_language=target,
            status="SKIPPED",
            original_text_path=str(source_path),
            original_sha256=original_sha,
            created_at=created_at,
        )
        return {**record, "reason": "source_already_target_language"}

    destination = Path(output_dir) / f"{source_path.stem}.{target}.translated.txt"
    if destination.resolve() == source_path.resolve():
        raise RuntimeError("translation destination would overwrite original artifact")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    tmp.write_text(str(result["translated_text"]), encoding="utf-8")
    tmp.replace(destination)
    translated_sha = _sha256_file(destination)
    record = translation_record(
        document_id=document_id,
        source_language=source,
        target_language=target,
        status="COMPLETED",
        original_text_path=str(source_path),
        translated_text_path=str(destination),
        translator=str(result.get("translator") or selected),
        model_or_version=str(result.get("model_or_version") or "unspecified"),
        original_sha256=original_sha,
        translated_sha256=translated_sha,
        created_at=created_at,
    )
    return {
        **record,
        "chunks": int(result.get("chunks") or 1),
        "detected_source_language": str(result.get("detected_source_language") or source),
    }


def translate_metadata_record(
    document_id: str,
    metadata: dict[str, Any],
    *,
    target_language: object = "pt",
    fields: tuple[str, ...] = ("title", "abstract", "keywords"),
    provider: str | None = None,
    session: requests.Session | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return translated metadata alongside, never instead of, the originals."""
    original = {key: metadata.get(key) for key in fields}
    declared = metadata.get("language_original") or metadata.get("language")
    source_text = "\n".join(str(original.get(key) or "") for key in fields)
    source = normalize_language_code(declared) or str(
        detect_language(source_text, declared=declared).get("detected_language") or "und"
    )
    target = normalize_language_code(target_language) or "pt"
    config = translation_configuration(environ)
    selected = (provider or str(config.get("provider") or "")).strip().lower()
    output: dict[str, Any] = {
        "document_id": document_id,
        "source_language": source,
        "target_language": target,
        "original": original,
        "translated": {},
        "status": "SKIPPED",
        "translator": selected,
        "model_or_version": "",
        "created_at": _now(),
        "original_preserved": True,
    }
    if source == target:
        output["reason"] = "source_already_target_language"
        return output
    if not config.get("configured") or not selected:
        output["reason"] = str(config.get("reason") or "translation_not_configured")
        return output
    try:
        for key in fields:
            value = str(original.get(key) or "").strip()
            if not value:
                continue
            result = translate_text(
                value,
                source_language=source,
                target_language=target,
                provider=selected,
                session=session,
                environ=environ,
            )
            output["translated"][key] = str(result["translated_text"])
            output["translator"] = str(result.get("translator") or selected)
            output["model_or_version"] = str(result.get("model_or_version") or "unspecified")
    except Exception as exc:
        output["status"] = "FAILED"
        output["reason"] = str(exc)
        return output
    output["status"] = "COMPLETED"
    output["reason"] = ""
    return output


def translate_strategy_candidate(
    strategy_text: str,
    *,
    source_language: object,
    target_language: object,
    provider: str | None = None,
    session: requests.Session | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Translate strategy text as a NON-EXECUTABLE candidate requiring human review."""
    original = str(strategy_text or "")
    if not original.strip():
        raise ValueError("strategy_text cannot be blank")
    result = translate_text(
        original,
        source_language=source_language,
        target_language=target_language,
        provider=provider,
        session=session,
        environ=environ,
    )
    translated = str(result.get("translated_text") or "")
    return {
        "schema_version": 1,
        "status": "PROVISIONAL_NOT_EXECUTABLE",
        "original_strategy": original,
        "original_sha256": sha256(original.encode("utf-8")).hexdigest(),
        "translated_candidate": translated,
        "translated_sha256": sha256(translated.encode("utf-8")).hexdigest(),
        "source_language": normalize_language_code(source_language),
        "target_language": normalize_language_code(target_language),
        "translator": result.get("translator"),
        "model_or_version": result.get("model_or_version"),
        "created_at": _now(),
        "human_validation_required": True,
        "automatically_applied_to_strategy": False,
    }


def write_translation_manifest(path: Path, rows: list[dict[str, Any]]) -> str:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    tmp.replace(destination)
    return _sha256_file(destination)


__all__ = [
    "configured_translation_provider",
    "translate_metadata_record",
    "translate_strategy_candidate",
    "translate_text",
    "translate_text_artifact",
    "translation_configuration",
    "write_translation_manifest",
]
