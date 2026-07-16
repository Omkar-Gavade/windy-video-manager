"""Pydantic response schemas for the Documents module.

Mirrors ``app.models.schemas`` for videos. ``PresignedUrl`` is generic and
reused as-is from there rather than duplicated here.
"""

from pydantic import BaseModel


class DocumentItem(BaseModel):
    """A single document as shown in the library.

    ``state`` / ``plant`` / ``document_date`` / ``document_time`` are
    extracted from the object key by the backend and are ``None`` for legacy
    (flat) objects.
    """

    state: str | None = None
    plant: str | None = None
    document_date: str | None = None
    document_time: str | None = None
    filename: str  # original filename (for display / download)
    upload_date: str  # ISO-8601 UTC timestamp
    size: str  # human-readable size, e.g. "1.2 MB"
    s3_path: str  # s3://bucket/key
    key: str  # raw object key (used for preview / download calls)


class DocumentUploadResult(BaseModel):
    """Payload returned after a successful document upload."""

    state: str | None = None
    plant: str | None = None
    document_date: str | None = None
    document_time: str | None = None
    filename: str
    upload_date: str
    size: str
    s3_path: str
    key: str
