"""Business logic for video operations.

The service layer orchestrates the AWS layer and shapes raw S3 data into the
schemas the frontend consumes. It never talks to boto3 directly and never lets
raw AWS errors escape — they are translated into :class:`AppError`.
"""

from datetime import datetime, timezone
from typing import BinaryIO
from urllib.parse import quote

from botocore.exceptions import BotoCoreError, ClientError

from app.aws import s3_client
from app.config.settings import get_settings
from app.models.schemas import PresignedUrl, UploadResult, VideoItem
from app.utils.formatters import human_size, to_iso
from app.utils.naming import (
    build_object_key,
    build_structured_key,
    extract_metadata_from_key,
    is_key_within_prefix,
    normalize_prefix,
    original_filename_from_key,
    sanitize_segment,
)
from app.utils.responses import AppError
from app.utils.validation import SNIFF_BYTES, is_mime_allowed, looks_like_video


def _stream_size(stream: BinaryIO) -> int:
    """Return the byte length of a seekable stream, leaving it rewound."""
    stream.seek(0, 2)  # end
    size = stream.tell()
    stream.seek(0)
    return size


def upload_video(
    filename: str | None,
    content_type: str | None,
    stream: BinaryIO,
    state: str | None = None,
    plant: str | None = None,
    recording_date: str | None = None,
) -> dict:
    """Validate and upload a single video, returning its library representation.

    Validation (all must pass):
      - a filename is present
      - the declared MIME type is in the allowlist
      - the leading bytes look like a supported video container
      - the file is non-empty and within the configured size limit

    When ``state``, ``plant``, and ``recording_date`` are all provided the video
    is stored under a structured key (``<prefix><state>/<plant>/<date>/<file>``);
    otherwise the flat legacy layout is used. Both are unique, never
    overwriting.

    Raises :class:`AppError` with 400 (bad input) / 413 (too large) / 502
    (storage failure) as appropriate.
    """
    settings = get_settings()

    if not filename:
        raise AppError("A filename is required.", status_code=400)

    if not is_mime_allowed(content_type, settings.allowed_video_mime_set):
        raise AppError("Unsupported file type. Please upload a video.", status_code=400)

    header = stream.read(SNIFF_BYTES)
    stream.seek(0)
    if not looks_like_video(header):
        raise AppError("File does not appear to be a valid video.", status_code=400)

    size = _stream_size(stream)
    if size == 0:
        raise AppError("The uploaded file is empty.", status_code=400)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size > max_bytes:
        raise AppError(
            f"File exceeds the maximum allowed size of {settings.max_upload_mb} MB.",
            status_code=413,
        )

    if state and plant and recording_date:
        key = build_structured_key(settings.s3_prefix, state, plant, recording_date, filename)
    else:
        key = build_object_key(settings.s3_prefix, filename)

    try:
        s3_client.upload_fileobj(stream, key, content_type)
    except (ClientError, BotoCoreError):
        raise AppError("Could not upload the video to storage.", status_code=502)

    metadata = extract_metadata_from_key(key, settings.s3_prefix)
    return UploadResult(
        state=metadata["state"],
        plant=metadata["plant"],
        recording_date=metadata["recording_date"],
        recording_time=metadata["recording_time"],
        filename=metadata["filename"],
        upload_date=to_iso(datetime.now(timezone.utc)),
        size=human_size(size),
        s3_path=f"s3://{settings.s3_bucket}/{key}",
        key=key,
    ).model_dump()


def _download_disposition(filename: str) -> str:
    """Build a safe ``attachment`` Content-Disposition for ``filename``.

    Provides both an ASCII ``filename`` fallback and an RFC 5987 ``filename*``
    so unicode / special characters survive without breaking the header.
    """
    ascii_fallback = filename.encode("ascii", "ignore").decode() or "video"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


def _presigned_url(key: str, expiry: int, disposition: str) -> dict:
    """Validate ``key`` and return a presigned GET URL payload.

    The key must resolve inside the configured prefix (guards against
    presigning arbitrary bucket objects) and the object must exist.
    """
    settings = get_settings()

    if not is_key_within_prefix(key, settings.s3_prefix):
        raise AppError("Video not found.", status_code=404)

    try:
        exists = s3_client.object_exists(key)
    except (ClientError, BotoCoreError):
        raise AppError("Could not access storage.", status_code=502)

    if not exists:
        raise AppError("Video not found.", status_code=404)

    try:
        url = s3_client.generate_presigned_get_url(key, expiry, disposition)
    except (ClientError, BotoCoreError):
        raise AppError("Could not generate a link for this video.", status_code=502)

    return PresignedUrl(url=url).model_dump()


def get_preview_url(key: str) -> dict:
    """Return a short-lived inline presigned URL for browser playback."""
    settings = get_settings()
    return _presigned_url(key, settings.preview_expiry_seconds, "inline")


def get_download_url(key: str) -> dict:
    """Return a short-lived attachment presigned URL for downloading."""
    settings = get_settings()
    filename = original_filename_from_key(key, settings.s3_prefix)
    return _presigned_url(key, settings.download_expiry_seconds, _download_disposition(filename))


def _filter_list_prefix(
    base_prefix: str,
    state: str | None,
    plant: str | None,
    recording_date: str | None,
) -> str:
    """Narrow the S3 list prefix using the structured hierarchy.

    Segments are appended only while contiguous from the top (state -> plant ->
    date) so S3 scans as little as possible. Non-contiguous filters (e.g. plant
    without state) are handled by the exact post-filter in :func:`list_videos`.
    """
    prefix = normalize_prefix(base_prefix)
    if state:
        prefix += f"{sanitize_segment(state)}/"
        if plant:
            prefix += f"{sanitize_segment(plant)}/"
            if recording_date:
                prefix += f"{sanitize_segment(recording_date)}/"
    return prefix


def list_videos(
    state: str | None = None,
    plant: str | None = None,
    recording_date: str | None = None,
) -> list[dict]:
    """Return videos under the configured prefix, newest first, filtered.

    All filters are optional. Filtering happens against the S3 object keys
    (never in the frontend): the list prefix is narrowed for efficiency and an
    exact match on the extracted metadata guarantees correctness. Legacy
    (flat) objects carry no metadata, so any active filter excludes them.

    Raises :class:`AppError` (502) if S3 cannot be reached or read.
    """
    settings = get_settings()

    # Sanitize filters the same way keys were built, so they compare equal.
    want_state = sanitize_segment(state) if state else None
    want_plant = sanitize_segment(plant) if plant else None
    want_date = sanitize_segment(recording_date) if recording_date else None

    list_prefix = _filter_list_prefix(settings.s3_prefix, state, plant, recording_date)

    try:
        objects = s3_client.list_objects(list_prefix)
    except (ClientError, BotoCoreError):
        raise AppError("Could not retrieve videos from storage.", status_code=502)

    # Newest first — most relevant for freshly generated Playwright output.
    objects.sort(key=lambda obj: obj["LastModified"], reverse=True)

    videos: list[dict] = []
    for obj in objects:
        key = obj["Key"]
        metadata = extract_metadata_from_key(key, settings.s3_prefix)

        # Exact metadata match (belt-and-suspenders over the prefix narrowing).
        if want_state and metadata["state"] != want_state:
            continue
        if want_plant and metadata["plant"] != want_plant:
            continue
        if want_date and metadata["recording_date"] != want_date:
            continue

        videos.append(
            VideoItem(
                state=metadata["state"],
                plant=metadata["plant"],
                recording_date=metadata["recording_date"],
                recording_time=metadata["recording_time"],
                filename=metadata["filename"],
                upload_date=to_iso(obj["LastModified"]),
                size=human_size(obj.get("Size", 0)),
                s3_path=f"s3://{settings.s3_bucket}/{key}",
                key=key,
            ).model_dump()
        )

    return videos
