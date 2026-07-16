"""Small, pure formatting helpers used when shaping S3 data for the frontend."""

from datetime import datetime, timezone


def human_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable string (e.g. ``4.2 MB``)."""
    if num_bytes < 0:
        num_bytes = 0
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            # No decimals for plain bytes; one decimal for larger units.
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def to_iso(value: datetime) -> str:
    """Return an ISO-8601 UTC timestamp string for a datetime."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
