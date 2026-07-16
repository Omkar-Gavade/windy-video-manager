"""Object-key naming and validation helpers.

Responsibilities:
- sanitize an incoming filename into a safe S3 key segment
- build a collision-free object key (timestamp + uuid + sanitized name)
- build a structured key that organizes videos by state/plant/date
- extract metadata (state, plant, recording date, filename) back from a key
- validate a caller-supplied key stays inside the configured prefix

Playwright emits many videos that often share the same default filename, so
keys must be unique to avoid silent overwrites.
"""

import re
import uuid
from datetime import datetime, timezone

# Allow letters, digits, dot, dash, underscore. Everything else -> underscore.
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MULTI_UNDERSCORE = re.compile(r"_{2,}")
# Path segments (state/plant/date) keep only letters, digits, and dashes.
_UNSAFE_SEGMENT = re.compile(r"[^A-Za-z0-9-]+")
# Windy filenames look like "SIRMOUR_satellite_2026-07-15_09-31-55_clean.mp4" —
# the recording time immediately follows a YYYY-MM-DD date segment.
_RECORDING_TIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_(\d{2})-(\d{2})-(\d{2})")
# Document unique-filename segment: "<YYYYMMDD>_<HHMMSS>_<uuid12hex>_<name>".
_DOCUMENT_NAME_PATTERN = re.compile(r"^\d{8}_(\d{2})(\d{2})(\d{2})_[0-9a-f]{12}_(.+)$")


def sanitize_filename(filename: str) -> str:
    """Return a filesystem/URL-safe version of ``filename``.

    Strips any path components and collapses unsafe characters. Falls back to
    ``video`` when nothing usable remains.
    """
    # Drop any path portion a client might send.
    base = filename.replace("\\", "/").split("/")[-1].strip()
    base = _UNSAFE_CHARS.sub("_", base)
    base = _MULTI_UNDERSCORE.sub("_", base).strip("._")
    return base or "video"


def sanitize_segment(value: str) -> str:
    """Return a path-safe key segment (e.g. ``Madhya Pradesh`` -> ``MadhyaPradesh``).

    Removes spaces and any character that isn't a letter, digit, or dash so the
    value is safe to embed as a single S3 "folder" level. Falls back to
    ``unknown`` when nothing usable remains.
    """
    cleaned = _UNSAFE_SEGMENT.sub("", (value or "").strip())
    return cleaned or "unknown"


def unique_filename(filename: str) -> str:
    """Build the unique, collision-free filename segment for a key.

    Format: ``<timestamp>_<uuid>_<sanitized-name>``. The timestamp keeps keys
    roughly sortable; the uuid guarantees uniqueness even for identical
    filenames uploaded in the same instant.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    unique = uuid.uuid4().hex[:12]
    return f"{timestamp}_{unique}_{sanitize_filename(filename)}"


def normalize_prefix(prefix: str) -> str:
    """Ensure a prefix ends with a single trailing slash (empty stays empty)."""
    return prefix if prefix.endswith("/") or prefix == "" else f"{prefix}/"


def build_object_key(prefix: str, filename: str) -> str:
    """Build a flat unique object key: ``<prefix><timestamp>_<uuid>_<name>``.

    Used when no state/plant/date metadata is supplied (legacy layout).
    """
    return f"{normalize_prefix(prefix)}{unique_filename(filename)}"


def build_structured_key(
    prefix: str, state: str, plant: str, recording_date: str, filename: str
) -> str:
    """Build a structured key organized as ``<prefix><state>/<plant>/<date>/<name>``.

    Each metadata level is sanitized into a single safe path segment; the
    filename segment reuses :func:`unique_filename` so uploads never overwrite.
    """
    return (
        f"{normalize_prefix(prefix)}"
        f"{sanitize_segment(state)}/"
        f"{sanitize_segment(plant)}/"
        f"{sanitize_segment(recording_date)}/"
        f"{unique_filename(filename)}"
    )


def extract_recording_time_from_filename(filename: str) -> str | None:
    """Extract the ``HH:MM:SS`` recording time embedded in a Windy filename.

    Filenames look like ``SIRMOUR_satellite_2026-07-15_09-31-55_clean.mp4``;
    the time immediately follows a ``YYYY-MM-DD`` date segment. Returns
    ``None`` when the pattern isn't present (legacy / unrelated filenames) —
    the frontend renders that as "—" without ever parsing the filename itself.
    """
    match = _RECORDING_TIME_PATTERN.search(filename)
    if not match:
        return None
    return f"{match.group(1)}:{match.group(2)}:{match.group(3)}"


def extract_metadata_from_key(key: str, prefix: str) -> dict:
    """Extract ``state``, ``plant``, ``recording_date``, ``recording_time``,
    ``filename`` from a key.

    Structured keys (``<prefix><state>/<plant>/<date>/<file>``) yield state /
    plant / recording_date. Legacy flat keys (``<prefix><file>``) yield those
    as ``None`` so the frontend can render "—" without ever parsing the path
    itself. ``recording_time`` is parsed from the filename independently of
    the key structure (present whenever the filename carries a Windy-style
    date+time, ``None`` otherwise — including for legacy objects).
    """
    normalized_prefix = normalize_prefix(prefix)
    tail = key[len(normalized_prefix):] if key.startswith(normalized_prefix) else key
    parts = tail.split("/")

    filename = original_filename_from_key(key, prefix)
    recording_time = extract_recording_time_from_filename(filename)

    if len(parts) == 4:
        return {
            "state": parts[0],
            "plant": parts[1],
            "recording_date": parts[2],
            "recording_time": recording_time,
            "filename": filename,
        }
    return {
        "state": None,
        "plant": None,
        "recording_date": None,
        "recording_time": recording_time,
        "filename": filename,
    }


def original_filename_from_key(key: str, prefix: str) -> str:
    """Recover the original filename from a generated object key.

    Keys built by :func:`build_object_key` look like
    ``<prefix><timestamp>_<uuid>_<name>``; the timestamp and uuid never contain
    underscores, so splitting the post-prefix segment on ``_`` (max 2 splits)
    yields the original name. Keys that don't match the pattern (e.g. objects
    not created by this app) fall back to the trailing path segment.
    """
    normalized_prefix = prefix if prefix.endswith("/") or prefix == "" else f"{prefix}/"
    tail = key[len(normalized_prefix):] if key.startswith(normalized_prefix) else key
    tail = tail.split("/")[-1]

    parts = tail.split("_", 2)
    if len(parts) == 3 and parts[1]:
        return parts[2]
    return tail


def build_document_key(
    prefix: str,
    state: str,
    plant: str,
    document_date: str,
    document_time: str | None,
    filename: str,
) -> str:
    """Build a structured document key: ``<prefix><state>/<plant>/<date>/<name>``.

    Unlike videos (whose recording time is already embedded in the uploaded
    filename), a document's time is a separate user-supplied field. When
    supplied it is embedded in the unique filename segment (as ``HHMMSS``) so
    it can be recovered on list without a database; the segment is always
    unique (uuid), so uploads never overwrite.
    """
    date_compact = document_date.replace("-", "")
    unique = uuid.uuid4().hex[:12]
    safe_name = sanitize_filename(filename)

    if document_time:
        time_compact = document_time.replace(":", "")[:6].ljust(6, "0")
        name_segment = f"{date_compact}_{time_compact}_{unique}_{safe_name}"
    else:
        name_segment = f"{date_compact}_{unique}_{safe_name}"

    return (
        f"{normalize_prefix(prefix)}"
        f"{sanitize_segment(state)}/"
        f"{sanitize_segment(plant)}/"
        f"{sanitize_segment(document_date)}/"
        f"{name_segment}"
    )


def extract_document_metadata_from_key(key: str, prefix: str) -> dict:
    """Extract ``state``, ``plant``, ``document_date``, ``document_time``,
    ``filename`` from a document key.

    Mirrors :func:`extract_metadata_from_key` for the document hierarchy.
    Legacy / non-structured keys yield ``None`` for all metadata fields.
    """
    normalized_prefix = normalize_prefix(prefix)
    tail = key[len(normalized_prefix):] if key.startswith(normalized_prefix) else key
    parts = tail.split("/")

    if len(parts) == 4:
        state, plant, document_date, name_segment = parts

        match = _DOCUMENT_NAME_PATTERN.match(name_segment)
        if match:
            hh, mm, ss, filename = match.groups()
            return {
                "state": state,
                "plant": plant,
                "document_date": document_date,
                "document_time": f"{hh}:{mm}:{ss}",
                "filename": filename,
            }

        # Structured, but no time was embedded (not supplied at upload).
        no_time_parts = name_segment.split("_", 2)
        filename = no_time_parts[2] if len(no_time_parts) == 3 else name_segment
        return {
            "state": state,
            "plant": plant,
            "document_date": document_date,
            "document_time": None,
            "filename": filename,
        }

    return {
        "state": None,
        "plant": None,
        "document_date": None,
        "document_time": None,
        "filename": tail.split("/")[-1],
    }


def is_key_within_prefix(key: str, prefix: str) -> bool:
    """Return True only if ``key`` is a safe object inside ``prefix``.

    Guards the preview/download endpoints against presigning arbitrary objects
    in the bucket (path traversal / enumeration).
    """
    if not key or ".." in key or key.startswith("/"):
        return False
    normalized_prefix = prefix if prefix.endswith("/") or prefix == "" else f"{prefix}/"
    return key.startswith(normalized_prefix) and key != normalized_prefix
