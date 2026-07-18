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

    Retained for the flat/legacy fallback path; new videos use
    :func:`build_video_key` with a deterministic filename.
    """
    return (
        f"{normalize_prefix(prefix)}"
        f"{sanitize_segment(state)}/"
        f"{sanitize_segment(plant)}/"
        f"{sanitize_segment(recording_date)}/"
        f"{unique_filename(filename)}"
    )


# --- New video naming: <plant>_YYMMDD_HH_MM ---------------------------------

_PLANT_SLUG_UNSAFE = re.compile(r"[^a-z0-9]+")


def slug_plant(plant: str) -> str:
    """Normalize a plant name to a filename-safe slug.

    Lowercase, spaces/special characters collapsed to single underscores,
    trimmed. e.g. ``"Madhya Pradesh"`` -> ``"madhya_pradesh"``, ``"SIRMOUR"``
    -> ``"sirmour"``.
    """
    slug = _PLANT_SLUG_UNSAFE.sub("_", (plant or "").lower()).strip("_")
    return slug or "video"


def build_video_basename(plant: str, recording_date: str, recording_time: str) -> str:
    """Build the deterministic video base name ``<plant>_YYMMDD_HH_MM`` (no ext).

    ``recording_date`` is ``YYYY-MM-DD``; ``recording_time`` is ``HH:MM`` or
    ``HH:MM:SS`` (24-hour). Non-conforming inputs are coerced defensively.
    """
    digits_date = re.sub(r"\D", "", recording_date or "")
    yymmdd = digits_date[2:8] if len(digits_date) >= 8 else digits_date.ljust(6, "0")[:6]

    time_parts = (recording_time or "").split(":")
    hh = (time_parts[0] if len(time_parts) >= 1 else "00").zfill(2)[:2]
    mm = (time_parts[1] if len(time_parts) >= 2 else "00").zfill(2)[:2]

    return f"{slug_plant(plant)}_{yymmdd}_{hh}_{mm}"


def build_video_key(prefix: str, state: str, plant: str, recording_date: str, filename: str) -> str:
    """Build a structured video key with an explicit (already-final) filename.

    ``<prefix><State>/<Plant>/<Date>/<filename>`` — no uuid, filename preserved.
    """
    return (
        f"{normalize_prefix(prefix)}"
        f"{sanitize_segment(state)}/"
        f"{sanitize_segment(plant)}/"
        f"{sanitize_segment(recording_date)}/"
        f"{filename}"
    )


def sidecar_json_key(video_key: str) -> str:
    """Return the metadata JSON key beside a video key (same name, .json ext)."""
    dot = video_key.rfind(".")
    slash = video_key.rfind("/")
    if dot > slash:
        return f"{video_key[:dot]}.json"
    return f"{video_key}.json"


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


# ---------------------------------------------------------------------------
# Inputs module — plant-scoped Site_Details + per-date categories
# ---------------------------------------------------------------------------
#
# inputs/<State>/<Plant>/
#     Site_Details/<site_details.json|site_configuration.json|metadata.json>
#     <Date>/
#         Enercast_Data/<file>       -> "Enercast Data"
#         Metered_Data/<file>        -> "Metered Data"
#         WP/Images/<file>           -> "WP", wp_type "Images"
#         WP/Videos/<file>           -> "WP", wp_type "Videos"
#         fetch_manifest.json        -> "Fetch Manifest"
#
# Site_Details lives directly under the plant (one per plant, no date).

SITE_DETAILS = "Site_Details"
MANIFEST_FILENAME = "fetch_manifest.json"
SITE_DETAILS_FILES = {"site_details.json", "site_configuration.json", "metadata.json"}
_WP_TYPE_SEGMENT = {"Videos": "Videos", "Images": "Images"}


def input_basename(filename: str) -> str:
    """Return the original filename unchanged, minus any path components.

    Unlike :func:`sanitize_filename`, the visible name is NOT modified (no
    uuid, no timestamp, no character rewriting) — only leading directory
    parts a client might send are stripped for key safety.
    """
    base = filename.replace("\\", "/").split("/")[-1].strip()
    return base or "file"


def build_input_key(
    prefix: str,
    state: str,
    plant: str,
    input_date: str | None,
    category: str,
    wp_type: str | None,
    sub_category: str | None,
    filename: str,
) -> str:
    """Build a structured Inputs key.

    ``Site Details`` is stored directly under the plant (no date) as the fixed
    ``sub_category`` filename. ``Fetch Manifest`` is always ``fetch_manifest.json``.
    Every other category lives under the input-date folder, filename preserved.
    """
    plant_base = (
        f"{normalize_prefix(prefix)}"
        f"{sanitize_segment(state)}/"
        f"{sanitize_segment(plant)}/"
    )

    if category == "Site Details":
        return f"{plant_base}{SITE_DETAILS}/{sub_category}"

    date_base = f"{plant_base}{sanitize_segment(input_date)}/"

    if category == "Fetch Manifest":
        return f"{date_base}{MANIFEST_FILENAME}"
    if category == "Enercast Data":
        return f"{date_base}Enercast_Data/{input_basename(filename)}"
    if category == "Metered Data":
        return f"{date_base}Metered_Data/{input_basename(filename)}"
    if category == "WP":
        segment = _WP_TYPE_SEGMENT.get(wp_type, "")
        return f"{date_base}WP/{segment}/{input_basename(filename)}"

    # Should not happen (category is validated upstream).
    return f"{date_base}{input_basename(filename)}"


def extract_input_metadata_from_key(key: str, prefix: str) -> dict:
    """Extract state / plant / input_date / category / sub_category / wp_type /
    filename from an Inputs key.

    Non-conforming keys yield ``None`` metadata with the trailing path segment
    as the filename, so nothing crashes on unexpected objects.
    """
    normalized_prefix = normalize_prefix(prefix)
    tail = key[len(normalized_prefix):] if key.startswith(normalized_prefix) else key
    parts = tail.split("/")

    def build(state=None, plant=None, input_date=None, category=None,
              sub_category=None, wp_type=None, filename=parts[-1]):
        return {
            "state": state, "plant": plant, "input_date": input_date,
            "category": category, "sub_category": sub_category,
            "wp_type": wp_type, "filename": filename,
        }

    if len(parts) < 4:
        return build()

    state, plant = parts[0], parts[1]

    # Plant-scoped Site_Details (no date).
    if parts[2] == SITE_DETAILS:
        filename = parts[3]
        return build(state, plant, None, "Site Details", filename, None, filename)

    # Date-scoped categories.
    input_date = parts[2]
    rest = parts[3:]

    if len(rest) == 1:
        filename = rest[0]
        category = "Fetch Manifest" if filename == MANIFEST_FILENAME else None
        return build(state, plant, input_date, category, None, None, filename)

    head = rest[0]
    if head == "Enercast_Data":
        return build(state, plant, input_date, "Enercast Data", None, None, rest[-1])
    if head == "Metered_Data":
        return build(state, plant, input_date, "Metered Data", None, None, rest[-1])
    if head == "WP":
        wp_type = rest[1] if len(rest) >= 3 and rest[1] in _WP_TYPE_SEGMENT else None
        return build(state, plant, input_date, "WP", None, wp_type, rest[-1])

    return build(state, plant, input_date, None, None, None, rest[-1])


def is_key_within_prefix(key: str, prefix: str) -> bool:
    """Return True only if ``key`` is a safe object inside ``prefix``.

    Guards the preview/download endpoints against presigning arbitrary objects
    in the bucket (path traversal / enumeration).
    """
    if not key or ".." in key or key.startswith("/"):
        return False
    normalized_prefix = prefix if prefix.endswith("/") or prefix == "" else f"{prefix}/"
    return key.startswith(normalized_prefix) and key != normalized_prefix
