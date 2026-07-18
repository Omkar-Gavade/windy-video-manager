"""Pydantic response schemas for the Inputs module.

``PresignedUrl`` is generic and reused from ``app.models.schemas`` rather than
duplicated here.
"""

from pydantic import BaseModel


class InputItem(BaseModel):
    """A single input asset as shown in the library.

    ``state`` / ``plant`` / ``input_date`` / ``category`` / ``wp_type`` are
    extracted from the object key; ``input_time`` is stored as S3 user metadata
    at upload and read back on list. ``wp_type`` is non-null only for the WP
    category.
    """

    state: str | None = None
    plant: str | None = None
    input_date: str | None = None
    input_time: str | None = None  # captured local time (HH:MM:SS AM/PM)
    uploaded_time: str  # ISO-8601 UTC (S3 LastModified)
    category: str | None = None
    sub_category: str | None = None  # Site Details file (non-null only for Site Details)
    wp_type: str | None = None  # Images/Videos (non-null only for WP)
    filename: str
    size: str
    s3_path: str
    key: str


class InputUploadResult(BaseModel):
    """Payload returned after a successful input upload."""

    state: str | None = None
    plant: str | None = None
    input_date: str | None = None
    input_time: str | None = None
    uploaded_time: str
    category: str | None = None
    sub_category: str | None = None
    wp_type: str | None = None
    filename: str
    size: str
    s3_path: str
    key: str
