"""Business logic for video operations.

The service layer orchestrates the AWS layer and shapes raw S3 data into the
schemas the frontend consumes. It never talks to boto3 directly and never lets
raw AWS errors escape — they are translated into :class:`AppError`.

New videos are stored as::

    videos/<State>/<Plant>/<Date>/<plant>_YYMMDD_HH_MM.mp4
    videos/<State>/<Plant>/<Date>/<plant>_YYMMDD_HH_MM.json   (metadata sidecar)

Listing reads the JSON sidecar when present and falls back to parsing the key
for older objects (full backward compatibility, no migration required).
"""

import json
import os
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
    build_video_basename,
    build_video_key,
    extract_metadata_from_key,
    is_key_within_prefix,
    normalize_prefix,
    sanitize_segment,
    sidecar_json_key,
)
from app.utils.responses import AppError
from app.utils.validation import SNIFF_BYTES, is_mime_allowed, looks_like_video

METADATA_VERSION = 1
_VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov")


def _stream_size(stream: BinaryIO) -> int:
    """Return the byte length of a seekable stream, leaving it rewound."""
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    return size


def _resolve_recording_time(recording_time: str | None, original_filename: str) -> str:
    """Pick the recording time: explicit value, else parsed from the Windy
    filename, else the current UTC time. Always returns ``HH:MM:SS``."""
    from app.utils.naming import extract_recording_time_from_filename

    if recording_time:
        parts = recording_time.split(":")
        hh = (parts[0] if len(parts) > 0 else "00").zfill(2)
        mm = (parts[1] if len(parts) > 1 else "00").zfill(2)
        ss = (parts[2] if len(parts) > 2 else "00").zfill(2)
        return f"{hh}:{mm}:{ss}"
    parsed = extract_recording_time_from_filename(original_filename)
    if parsed:
        return parsed
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _build_metadata(
    *, filename, state, plant, recording_date, recording_time,
    content_type, file_size, s3_key,
) -> dict:
    """Assemble the extendable metadata document stored beside each video."""
    return {
        "version": METADATA_VERSION,
        "filename": filename,
        "state": state,
        "plant": plant,
        "recording_date": recording_date,
        "recording_time": recording_time,
        "upload_time": to_iso(datetime.now(timezone.utc)),
        "content_type": content_type,
        "file_size": file_size,
        "s3_key": s3_key,
    }


def upload_video(
    filename: str | None,
    content_type: str | None,
    stream: BinaryIO,
    state: str | None = None,
    plant: str | None = None,
    recording_date: str | None = None,
    recording_time: str | None = None,
) -> dict:
    """Validate and upload a video plus its metadata JSON sidecar.

    Flow: validate → generate deterministic name → upload MP4 → upload JSON.
    If the JSON upload fails the MP4 is deleted (no orphans). Returns success
    only when both objects are stored.

    Raises :class:`AppError` 400 / 413 / 502 as appropriate.
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

    # Without full metadata, keep the legacy flat layout (no sidecar).
    if not (state and plant and recording_date):
        key = build_object_key(settings.s3_prefix, filename)
        try:
            s3_client.upload_fileobj(stream, key, content_type)
        except (ClientError, BotoCoreError):
            raise AppError("Could not upload the video to storage.", status_code=502)
        meta = extract_metadata_from_key(key, settings.s3_prefix)
        return UploadResult(
            state=meta["state"], plant=meta["plant"], recording_date=meta["recording_date"],
            recording_time=meta["recording_time"], filename=meta["filename"],
            upload_date=to_iso(datetime.now(timezone.utc)), size=human_size(size),
            s3_path=f"s3://{settings.s3_bucket}/{key}", key=key,
        ).model_dump()

    # New deterministic naming + JSON sidecar.
    rec_time = _resolve_recording_time(recording_time, filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _VIDEO_EXTENSIONS:
        ext = ".mp4"
    basename = build_video_basename(plant, recording_date, rec_time)
    video_filename = f"{basename}{ext}"
    key = build_video_key(settings.s3_prefix, state, plant, recording_date, video_filename)
    json_key = sidecar_json_key(key)

    seg_state = sanitize_segment(state)
    seg_plant = sanitize_segment(plant)
    seg_date = sanitize_segment(recording_date)

    try:
        s3_client.upload_fileobj(stream, key, content_type)
    except (ClientError, BotoCoreError):
        raise AppError("Could not upload the video to storage.", status_code=502)

    metadata = _build_metadata(
        filename=video_filename, state=seg_state, plant=seg_plant,
        recording_date=seg_date, recording_time=rec_time,
        content_type=content_type, file_size=size, s3_key=key,
    )
    try:
        s3_client.put_object(json_key, json.dumps(metadata, indent=2).encode("utf-8"), "application/json")
    except (ClientError, BotoCoreError):
        # Roll back the orphaned MP4 so no partial state remains.
        try:
            s3_client.delete_object(key)
        except (ClientError, BotoCoreError):
            pass
        raise AppError("Could not store video metadata.", status_code=502)

    return UploadResult(
        state=seg_state, plant=seg_plant, recording_date=seg_date,
        recording_time=rec_time, filename=video_filename,
        upload_date=metadata["upload_time"], size=human_size(size),
        s3_path=f"s3://{settings.s3_bucket}/{key}", key=key,
    ).model_dump()


# --- Dynamic States & Plants ------------------------------------------------


def list_states() -> list[str]:
    """Return the States present in the bucket (top-level folders under prefix)."""
    settings = get_settings()
    try:
        return sorted(s3_client.list_common_prefixes(normalize_prefix(settings.s3_prefix)))
    except (ClientError, BotoCoreError):
        raise AppError("Could not retrieve states from storage.", status_code=502)


def list_plants(state: str) -> list[str]:
    """Return the Plants present for ``state``."""
    settings = get_settings()
    if not state:
        return []
    prefix = f"{normalize_prefix(settings.s3_prefix)}{sanitize_segment(state)}/"
    try:
        return sorted(s3_client.list_common_prefixes(prefix))
    except (ClientError, BotoCoreError):
        raise AppError("Could not retrieve plants from storage.", status_code=502)


# --- Preview / Download -----------------------------------------------------


def _download_disposition(filename: str) -> str:
    ascii_fallback = filename.encode("ascii", "ignore").decode() or "video"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


def _presigned_url(key: str, expiry: int, disposition: str) -> dict:
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
    settings = get_settings()
    return _presigned_url(key, settings.preview_expiry_seconds, "inline")


def get_download_url(key: str) -> dict:
    settings = get_settings()
    filename = _metadata_for(key, settings.s3_prefix)["filename"]
    return _presigned_url(key, settings.download_expiry_seconds, _download_disposition(filename))


# --- Listing (JSON-first, key-parse fallback) -------------------------------


def _filter_list_prefix(base_prefix, state, plant, recording_date) -> str:
    prefix = normalize_prefix(base_prefix)
    if state:
        prefix += f"{sanitize_segment(state)}/"
        if plant:
            prefix += f"{sanitize_segment(plant)}/"
            if recording_date:
                prefix += f"{sanitize_segment(recording_date)}/"
    return prefix


def _metadata_for(key: str, prefix: str) -> dict:
    """Resolve a video's metadata: JSON sidecar first, then key parsing."""
    sidecar = sidecar_json_key(key)
    try:
        text = s3_client.get_object_text(sidecar)
    except (ClientError, BotoCoreError):
        text = None

    if text:
        try:
            doc = json.loads(text)
            return {
                "state": doc.get("state"),
                "plant": doc.get("plant"),
                "recording_date": doc.get("recording_date"),
                "recording_time": doc.get("recording_time"),
                "filename": doc.get("filename") or os.path.basename(key),
            }
        except (ValueError, TypeError):
            pass  # corrupt sidecar -> fall through to key parsing

    return extract_metadata_from_key(key, prefix)


def list_videos(
    state: str | None = None,
    plant: str | None = None,
    recording_date: str | None = None,
) -> list[dict]:
    """Return videos under the configured prefix, newest first, filtered.

    Uses the JSON sidecar when available, otherwise parses the key. JSON files
    themselves are excluded from the listing.
    """
    settings = get_settings()

    want_state = sanitize_segment(state) if state else None
    want_plant = sanitize_segment(plant) if plant else None
    want_date = sanitize_segment(recording_date) if recording_date else None

    list_prefix = _filter_list_prefix(settings.s3_prefix, state, plant, recording_date)

    try:
        objects = s3_client.list_objects(list_prefix)
    except (ClientError, BotoCoreError):
        raise AppError("Could not retrieve videos from storage.", status_code=502)

    objects.sort(key=lambda obj: obj["LastModified"], reverse=True)

    videos: list[dict] = []
    for obj in objects:
        key = obj["Key"]
        if key.lower().endswith(".json"):
            continue  # sidecar metadata, not a listable video

        metadata = _metadata_for(key, settings.s3_prefix)

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
