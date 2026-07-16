"""Pydantic response schemas.

These describe the ``data`` payloads carried inside the success envelope
(see ``app.utils.responses``). Request bodies are handled directly by FastAPI
(multipart form / query params), so no request schemas are needed.
"""

from pydantic import BaseModel


class VideoItem(BaseModel):
    """A single video as shown in the library.

    ``state`` / ``plant`` / ``recording_date`` are extracted from the object
    key by the backend and are ``None`` for legacy (flat) objects.
    """

    state: str | None = None
    plant: str | None = None
    recording_date: str | None = None
    recording_time: str | None = None  # HH:MM:SS, parsed from the filename
    filename: str  # original filename (for display / download)
    upload_date: str  # ISO-8601 UTC timestamp
    size: str  # human-readable size, e.g. "4.2 MB"
    s3_path: str  # s3://bucket/key
    key: str  # raw object key (used for preview / download calls)


class UploadResult(BaseModel):
    """Payload returned after a successful upload."""

    state: str | None = None
    plant: str | None = None
    recording_date: str | None = None
    recording_time: str | None = None
    filename: str
    upload_date: str
    size: str
    s3_path: str
    key: str


class PresignedUrl(BaseModel):
    """A short-lived presigned URL for preview or download."""

    url: str
