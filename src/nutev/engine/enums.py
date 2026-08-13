from __future__ import annotations

from enum import Enum


class EventKind(str, Enum):
    state = "state"
    progress = "progress"
    warning = "warning"
    error = "error"
    metric = "metric"


class Workstream(str, Enum):
    """Canonical analytical labels emitted by the current runtime.

    Historical ``busca*``/article-framework labels are accepted only through
    explicit import aliases in :func:`nutev.engine.validators.validate_workstream`.
    """

    policy_systems = "policy_systems"
    clinical_outcomes = "clinical_outcomes"
    implementation = "implementation"
    framework = "framework"
    global_watch = "global_watch"


class DownloadStatus(str, Enum):
    pdf = "pdf"
    html_snapshot = "html_snapshot"
    metadata_only = "metadata_only"
    failed = "failed"


class CaptureStatus(str, Enum):
    missing = "missing"
    ok = "ok"
    ok_html_snapshot = "ok_html_snapshot"
    metadata_only = "metadata_only"
    failed = "failed"


class ExtractionStatus(str, Enum):
    missing = "missing"
    ok = "ok"
    ok_native = "ok_native"
    ok_native_low_confidence = "ok_native_low_confidence"
    ok_ocr = "ok_ocr"
    no_text = "no_text"
    ocr_unavailable = "ocr_unavailable"
    failed = "failed"


class FailureReason(str, Enum):
    none = ""
    publisher_forbidden = "publisher_forbidden"
    publisher_blocked_or_paywalled = "publisher_blocked_or_paywalled"
    paywalled_or_blocked = "paywalled_or_blocked"
    invalid_source_metadata = "invalid_source_metadata"
    invalid_url = "invalid_url"
    invalid_doi_metadata = "invalid_doi_metadata"
    filtered_and_no_html_snapshot = "filtered_and_no_html_snapshot"
    not_found = "not_found"
    rate_limited = "rate_limited"
    server_error = "server_error"
    transient_network_error = "transient_network_error"
    download_failed = "download_failed"
    empty_content = "empty_content"
    ocr_unavailable = "ocr_unavailable"
