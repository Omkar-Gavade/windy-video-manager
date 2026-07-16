"""Business logic for document operations.

Mirrors ``video_service`` for the Documents module: orchestrates the AWS
layer and shapes raw S3 data into the schemas the frontend consumes. Never
talks to boto3 directly; never lets raw AWS errors escape.
"""

from datetime import datetime, timezone
from typing import BinaryIO
from urllib.parse import quote

from botocore.exceptions import BotoCoreError, ClientError

from app.aws import s3_client
from app.config.settings import get_settings
from app.models.document_schema import DocumentItem, DocumentUploadResult
from app.models.schemas import PresignedUrl
from app.utils.formatters import human_size, to_iso
from app.utils.naming import (
    build_document_key,
    build_object_key,
    extract_document_metadata_from_key,
    is_key_within_prefix,
    normalize_prefix,
    sanitize_segment,
)
from app.utils.responses import AppError
from app.utils.validation import is_extension_allowed, is_mime_allowed


def _stream_size(stream: BinaryIO) -> int:
    """Return the byte length of a seekable stream, leaving it rewound."""
    stream.seek(0, 2)  # end
    size = stream.tell()
    stream.seek(0)
    return size


def upload_document(
    filename: str | None,
    content_type: str | None,
    stream: BinaryIO,
    state: str | None = None,
    plant: str | None = None,
    document_date: str | None = None,
    document_time: str | None = None,
) -> dict:
    """Validate and upload a single document, returning its library representation.

    Validation (all must pass):
      - a filename is present
      - the file extension is in the allowlist (.pdf, .doc, .docx, .xls, .xlsx,
        .csv, .txt)
      - the declared MIME type is in the allowlist
      - the file is non-empty and within the configured size limit

    When ``state``, ``plant``, and ``document_date`` are all provided the
    document is stored under a structured key
    (``documents/<state>/<plant>/<date>/<file>``), with ``document_time``
    embedded in the unique filename segment when supplied; otherwise the flat
    legacy layout is used. Both are unique, never overwriting.

    Raises :class:`AppError` with 400 (bad input) / 413 (too large) / 502
    (storage failure) as appropriate.
    """
    settings = get_settings()

    if not filename:
        raise AppError("A filename is required.", status_code=400)

    if not is_extension_allowed(filename, settings.allowed_document_extension_set):
        raise AppError(
            "Unsupported file type. Allowed: PDF, DOC, DOCX, XLS, XLSX, CSV, TXT.",
            status_code=400,
        )

    if not is_mime_allowed(content_type, settings.allowed_document_mime_set):
        raise AppError(
            "Unsupported file type. Allowed: PDF, DOC, DOCX, XLS, XLSX, CSV, TXT.",
            status_code=400,
        )

    size = _stream_size(stream)
    if size == 0:
        raise AppError("The uploaded file is empty.", status_code=400)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size > max_bytes:
        raise AppError(
            f"File exceeds the maximum allowed size of {settings.max_upload_mb} MB.",
            status_code=413,
        )

    if state and plant and document_date:
        key = build_document_key(
            settings.documents_prefix, state, plant, document_date, document_time, filename
        )
    else:
        key = build_object_key(settings.documents_prefix, filename)

    try:
        s3_client.upload_fileobj(stream, key, content_type)
    except (ClientError, BotoCoreError):
        raise AppError("Could not upload the document to storage.", status_code=502)

    metadata = extract_document_metadata_from_key(key, settings.documents_prefix)
    return DocumentUploadResult(
        state=metadata["state"],
        plant=metadata["plant"],
        document_date=metadata["document_date"],
        document_time=metadata["document_time"],
        filename=metadata["filename"],
        upload_date=to_iso(datetime.now(timezone.utc)),
        size=human_size(size),
        s3_path=f"s3://{settings.s3_bucket}/{key}",
        key=key,
    ).model_dump()


def _download_disposition(filename: str) -> str:
    """Build a safe ``attachment`` Content-Disposition for ``filename``."""
    ascii_fallback = filename.encode("ascii", "ignore").decode() or "document"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


def _presigned_url(key: str, expiry: int, disposition: str) -> dict:
    """Validate ``key`` and return a presigned GET URL payload.

    The key must resolve inside the documents prefix (guards against
    presigning arbitrary bucket objects) and the object must exist.
    """
    settings = get_settings()

    if not is_key_within_prefix(key, settings.documents_prefix):
        raise AppError("Document not found.", status_code=404)

    try:
        exists = s3_client.object_exists(key)
    except (ClientError, BotoCoreError):
        raise AppError("Could not access storage.", status_code=502)

    if not exists:
        raise AppError("Document not found.", status_code=404)

    try:
        url = s3_client.generate_presigned_get_url(key, expiry, disposition)
    except (ClientError, BotoCoreError):
        raise AppError("Could not generate a link for this document.", status_code=502)

    return PresignedUrl(url=url).model_dump()


def get_preview_url(key: str) -> dict:
    """Return a short-lived inline presigned URL for browser preview."""
    settings = get_settings()
    return _presigned_url(key, settings.preview_expiry_seconds, "inline")


def get_download_url(key: str) -> dict:
    """Return a short-lived attachment presigned URL for downloading."""
    settings = get_settings()
    metadata = extract_document_metadata_from_key(key, settings.documents_prefix)
    filename = metadata["filename"]
    return _presigned_url(key, settings.download_expiry_seconds, _download_disposition(filename))


def _filter_list_prefix(
    base_prefix: str,
    state: str | None,
    plant: str | None,
    document_date: str | None,
) -> str:
    """Narrow the S3 list prefix using the structured hierarchy.

    Segments are appended only while contiguous from the top (state -> plant ->
    date) so S3 scans as little as possible. Non-contiguous filters are
    handled by the exact post-filter in :func:`list_documents`.
    """
    prefix = normalize_prefix(base_prefix)
    if state:
        prefix += f"{sanitize_segment(state)}/"
        if plant:
            prefix += f"{sanitize_segment(plant)}/"
            if document_date:
                prefix += f"{sanitize_segment(document_date)}/"
    return prefix


def list_documents(
    state: str | None = None,
    plant: str | None = None,
    document_date: str | None = None,
) -> list[dict]:
    """Return documents under the configured prefix, newest first, filtered.

    All filters are optional. Filtering happens against the S3 object keys
    (never in the frontend): the list prefix is narrowed for efficiency and an
    exact match on the extracted metadata guarantees correctness. Legacy
    (flat) objects carry no metadata, so any active filter excludes them.

    Raises :class:`AppError` (502) if S3 cannot be reached or read.
    """
    settings = get_settings()

    want_state = sanitize_segment(state) if state else None
    want_plant = sanitize_segment(plant) if plant else None
    want_date = sanitize_segment(document_date) if document_date else None

    list_prefix = _filter_list_prefix(settings.documents_prefix, state, plant, document_date)

    try:
        objects = s3_client.list_objects(list_prefix)
    except (ClientError, BotoCoreError):
        raise AppError("Could not retrieve documents from storage.", status_code=502)

    objects.sort(key=lambda obj: obj["LastModified"], reverse=True)

    documents: list[dict] = []
    for obj in objects:
        key = obj["Key"]
        metadata = extract_document_metadata_from_key(key, settings.documents_prefix)

        if want_state and metadata["state"] != want_state:
            continue
        if want_plant and metadata["plant"] != want_plant:
            continue
        if want_date and metadata["document_date"] != want_date:
            continue

        documents.append(
            DocumentItem(
                state=metadata["state"],
                plant=metadata["plant"],
                document_date=metadata["document_date"],
                document_time=metadata["document_time"],
                filename=metadata["filename"],
                upload_date=to_iso(obj["LastModified"]),
                size=human_size(obj.get("Size", 0)),
                s3_path=f"s3://{settings.s3_bucket}/{key}",
                key=key,
            ).model_dump()
        )

    return documents
