"""Upload validation helpers: MIME allowlist + magic-byte content sniffing.

The client-supplied ``Content-Type`` is spoofable, so the actual file bytes are
also inspected. Both checks must pass for an upload to be accepted.
"""

# Number of leading bytes needed to identify supported container formats.
SNIFF_BYTES = 16


def is_mime_allowed(content_type: str | None, allowed: set[str]) -> bool:
    """Return True if the declared MIME type is in the allowlist."""
    if not content_type:
        return False
    return content_type.split(";")[0].strip().lower() in {m.lower() for m in allowed}


def is_extension_allowed(filename: str, allowed: set[str]) -> bool:
    """Return True if ``filename``'s extension (lowercased, with dot) is allowed."""
    if "." not in filename:
        return False
    ext = "." + filename.rsplit(".", 1)[-1].strip().lower()
    return ext in {e.lower() for e in allowed}


def looks_like_video(header: bytes) -> bool:
    """Best-effort magic-byte check for common video containers.

    Recognizes:
      - ISO base media (MP4 / MOV / QuickTime): ``ftyp`` box at offset 4
      - Matroska / WebM (EBML): starts with ``1A 45 DF A3``
    """
    if len(header) < 12:
        return False

    # EBML header (WebM / Matroska).
    if header[:4] == b"\x1a\x45\xdf\xa3":
        return True

    # ISO base media file format: 'ftyp' at bytes 4..8.
    if header[4:8] == b"ftyp":
        return True

    return False
