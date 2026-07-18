"""Business logic for input operations.

Orchestrates the AWS layer and shapes raw S3 data into the schemas the frontend
consumes. Never talks to boto3 directly; never lets raw AWS errors escape.

Storage hierarchy:
    inputs/<State>/<Plant>/Site_Details/<fixed json file>          (no date)
    inputs/<State>/<Plant>/<Date>/Enercast_Data/<file>
    inputs/<State>/<Plant>/<Date>/Metered_Data/<file>
    inputs/<State>/<Plant>/<Date>/WP/Images/<file>
    inputs/<State>/<Plant>/<Date>/WP/Videos/<file>
    inputs/<State>/<Plant>/<Date>/fetch_manifest.json

Uploaded filenames are preserved exactly (no uuid, no timestamp). ``input_time``
is captured client-side and stored as S3 user metadata.
"""

import os
from datetime import datetime, timezone
from typing import BinaryIO
from urllib.parse import quote

from botocore.exceptions import BotoCoreError, ClientError

from app.aws import s3_client
from app.config.settings import get_settings
from app.models.input_schema import InputItem, InputUploadResult
from app.models.schemas import PresignedUrl
from app.utils.formatters import human_size, to_iso
from app.utils.naming import (
    SITE_DETAILS_FILES,
    build_input_key,
    extract_input_metadata_from_key,
    is_key_within_prefix,
    normalize_prefix,
    sanitize_segment,
)
from app.utils.responses import AppError
from app.utils.validation import is_extension_allowed

VALID_CATEGORIES = {"Site Details", "Enercast Data", "Metered Data", "WP", "Fetch Manifest"}
VALID_WP_TYPES = {"Videos", "Images"}
DATE_CATEGORIES = {"Enercast Data", "Metered Data", "WP", "Fetch Manifest"}


def _stream_size(stream: BinaryIO) -> int:
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    return size


def _allowed_extensions(category: str, wp_type: str | None) -> set[str]:
    settings = get_settings()
    if category in {"Site Details", "Fetch Manifest"}:
        return {".json"}
    if category == "WP" and wp_type == "Videos":
        return settings.allowed_input_video_extension_set
    if category == "WP" and wp_type == "Images":
        return settings.allowed_input_image_extension_set
    return settings.allowed_data_extension_set


def upload_input(
    filename: str | None,
    content_type: str | None,
    stream: BinaryIO,
    state: str | None,
    plant: str | None,
    input_date: str | None,
    input_time: str | None,
    category: str | None,
    wp_type: str | None = None,
    sub_category: str | None = None,
) -> dict:
    """Validate and upload a single input asset.

    Raises :class:`AppError` with 400 / 413 / 502 as appropriate.
    """
    settings = get_settings()

    if not filename:
        raise AppError("A filename is required.", status_code=400)
    if not (state and plant):
        raise AppError("State and plant are required.", status_code=400)
    if category not in VALID_CATEGORIES:
        raise AppError("A valid input category is required.", status_code=400)

    if category in DATE_CATEGORIES and not input_date:
        raise AppError("An input date is required for this category.", status_code=400)
    if category == "WP" and wp_type not in VALID_WP_TYPES:
        raise AppError("WP uploads require a WP type of Images or Videos.", status_code=400)
    if category == "Site Details" and sub_category not in SITE_DETAILS_FILES:
        raise AppError("A valid Site Details file selection is required.", status_code=400)

    # Choose the extension allowlist against the name that will actually be
    # stored (fixed for Site Details / Fetch Manifest).
    check_name = sub_category if category == "Site Details" else filename
    if not is_extension_allowed(check_name, _allowed_extensions(category, wp_type)):
        raise AppError("Unsupported file type for this category.", status_code=400)

    size = _stream_size(stream)
    if size == 0:
        raise AppError("The uploaded file is empty.", status_code=400)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size > max_bytes:
        raise AppError(
            f"File exceeds the maximum allowed size of {settings.max_upload_mb} MB.",
            status_code=413,
        )

    key = build_input_key(
        settings.inputs_prefix, state, plant, input_date, category, wp_type, sub_category, filename
    )

    metadata = {"input-time": input_time} if input_time else None
    try:
        s3_client.upload_fileobj(stream, key, content_type or "application/octet-stream", metadata)
    except (ClientError, BotoCoreError):
        raise AppError("Could not upload the input to storage.", status_code=502)

    parsed = extract_input_metadata_from_key(key, settings.inputs_prefix)
    return InputUploadResult(
        state=parsed["state"],
        plant=parsed["plant"],
        input_date=parsed["input_date"],
        input_time=input_time,
        uploaded_time=to_iso(datetime.now(timezone.utc)),
        category=parsed["category"],
        sub_category=parsed["sub_category"],
        wp_type=parsed["wp_type"],
        filename=parsed["filename"],
        size=human_size(size),
        s3_path=f"s3://{settings.s3_bucket}/{key}",
        key=key,
    ).model_dump()


# --- Dynamic States & Plants (mirrors the Videos module) --------------------


def list_states() -> list[str]:
    """Return the States present under the inputs prefix (S3 folder discovery)."""
    settings = get_settings()
    try:
        return sorted(s3_client.list_common_prefixes(normalize_prefix(settings.inputs_prefix)))
    except (ClientError, BotoCoreError):
        raise AppError("Could not retrieve states from storage.", status_code=502)


def list_plants(state: str) -> list[str]:
    """Return the Plants present for ``state``."""
    settings = get_settings()
    if not state:
        return []
    prefix = f"{normalize_prefix(settings.inputs_prefix)}{sanitize_segment(state)}/"
    try:
        return sorted(s3_client.list_common_prefixes(prefix))
    except (ClientError, BotoCoreError):
        raise AppError("Could not retrieve plants from storage.", status_code=502)


# --- Text content (for in-browser JSON / CSV / TXT preview, same-origin) -----

_TEXT_PREVIEW_EXTENSIONS = {".json", ".csv", ".txt"}
_MAX_PREVIEW_BYTES = 2 * 1024 * 1024  # cap text fetched through the backend


def get_input_content(key: str) -> dict:
    """Return the text body of a small text input for inline preview.

    Proxied through the backend so the browser fetches same-origin (no S3 CORS
    needed). Only JSON / CSV / TXT are served this way; other types preview via
    a presigned URL directly.
    """
    settings = get_settings()

    if not is_key_within_prefix(key, settings.inputs_prefix):
        raise AppError("Input not found.", status_code=404)

    ext = os.path.splitext(key)[1].lower()
    if ext not in _TEXT_PREVIEW_EXTENSIONS:
        raise AppError("Text preview is not available for this file type.", status_code=400)

    try:
        text = s3_client.get_object_text(key)
    except (ClientError, BotoCoreError):
        raise AppError("Could not access storage.", status_code=502)

    if text is None:
        raise AppError("Input not found.", status_code=404)
    if len(text.encode("utf-8", "ignore")) > _MAX_PREVIEW_BYTES:
        raise AppError("File is too large to preview.", status_code=413)

    return {"content": text, "filename": os.path.basename(key)}


def _download_disposition(filename: str) -> str:
    ascii_fallback = filename.encode("ascii", "ignore").decode() or "file"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


def _presigned_url(key: str, expiry: int, disposition: str) -> dict:
    settings = get_settings()

    if not is_key_within_prefix(key, settings.inputs_prefix):
        raise AppError("Input not found.", status_code=404)

    try:
        exists = s3_client.object_exists(key)
    except (ClientError, BotoCoreError):
        raise AppError("Could not access storage.", status_code=502)
    if not exists:
        raise AppError("Input not found.", status_code=404)

    try:
        url = s3_client.generate_presigned_get_url(key, expiry, disposition)
    except (ClientError, BotoCoreError):
        raise AppError("Could not generate a link for this input.", status_code=502)

    return PresignedUrl(url=url).model_dump()


def get_preview_url(key: str) -> dict:
    settings = get_settings()
    return _presigned_url(key, settings.preview_expiry_seconds, "inline")


def get_download_url(key: str) -> dict:
    settings = get_settings()
    parsed = extract_input_metadata_from_key(key, settings.inputs_prefix)
    return _presigned_url(
        key, settings.download_expiry_seconds, _download_disposition(parsed["filename"])
    )


def _filter_list_prefix(
    base_prefix: str,
    state: str | None,
    plant: str | None,
    input_date: str | None,
    category: str | None,
    wp_type: str | None,
) -> str:
    """Narrow the S3 list prefix for efficiency. Exactness is still guaranteed
    by the post-filter in :func:`list_inputs`."""
    prefix = normalize_prefix(base_prefix)
    if not state:
        return prefix
    prefix += f"{sanitize_segment(state)}/"
    if not plant:
        return prefix
    prefix += f"{sanitize_segment(plant)}/"

    # Site_Details is plant-scoped (no date). Only narrow to it when explicitly
    # requested and no date filter is present.
    if category == "Site Details" and not input_date:
        return prefix + "Site_Details/"

    if not input_date:
        return prefix
    prefix += f"{sanitize_segment(input_date)}/"

    if category == "Enercast Data":
        prefix += "Enercast_Data/"
    elif category == "Metered Data":
        prefix += "Metered_Data/"
    elif category == "WP":
        prefix += "WP/"
        if wp_type in VALID_WP_TYPES:
            prefix += f"{wp_type}/"
    return prefix


def list_inputs(
    state: str | None = None,
    plant: str | None = None,
    input_date: str | None = None,
    category: str | None = None,
    wp_type: str | None = None,
) -> list[dict]:
    """Return input assets under the configured prefix, newest first, filtered.

    ``input_time`` is retrieved per object via HeadObject (S3 user metadata is
    not returned by ListObjectsV2).
    """
    settings = get_settings()

    want_state = sanitize_segment(state) if state else None
    want_plant = sanitize_segment(plant) if plant else None
    want_date = sanitize_segment(input_date) if input_date else None

    list_prefix = _filter_list_prefix(
        settings.inputs_prefix, state, plant, input_date, category, wp_type
    )

    try:
        objects = s3_client.list_objects(list_prefix)
    except (ClientError, BotoCoreError):
        raise AppError("Could not retrieve inputs from storage.", status_code=502)

    objects.sort(key=lambda obj: obj["LastModified"], reverse=True)

    items: list[dict] = []
    for obj in objects:
        key = obj["Key"]
        meta = extract_input_metadata_from_key(key, settings.inputs_prefix)

        if want_state and meta["state"] != want_state:
            continue
        if want_plant and meta["plant"] != want_plant:
            continue
        if want_date and meta["input_date"] != want_date:
            continue
        if category and meta["category"] != category:
            continue
        if wp_type and meta["wp_type"] != wp_type:
            continue

        input_time = None
        try:
            head = s3_client.head_object(key)
            if head:
                input_time = head.get("Metadata", {}).get("input-time")
        except (ClientError, BotoCoreError):
            input_time = None

        items.append(
            InputItem(
                state=meta["state"],
                plant=meta["plant"],
                input_date=meta["input_date"],
                input_time=input_time,
                uploaded_time=to_iso(obj["LastModified"]),
                category=meta["category"],
                sub_category=meta["sub_category"],
                wp_type=meta["wp_type"],
                filename=meta["filename"],
                size=human_size(obj.get("Size", 0)),
                s3_path=f"s3://{settings.s3_bucket}/{key}",
                key=key,
            ).model_dump()
        )

    return items
