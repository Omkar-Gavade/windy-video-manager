"""Unit tests for the pure utility helpers."""

from datetime import datetime, timezone

from app.utils.formatters import human_size, to_iso
from app.utils.naming import (
    build_object_key,
    is_key_within_prefix,
    original_filename_from_key,
    sanitize_filename,
)
from app.utils.validation import is_mime_allowed, looks_like_video


def test_human_size():
    assert human_size(0) == "0 B"
    assert human_size(1023) == "1023 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"


def test_to_iso_naive_treated_as_utc():
    assert to_iso(datetime(2026, 7, 14, 10, 30)) == "2026-07-14T10:30:00+00:00"


def test_sanitize_filename_strips_path_and_unsafe_chars():
    assert sanitize_filename("../../my weird@name!!.mp4") == "my_weird_name_.mp4"
    assert sanitize_filename("") == "video"


def test_build_object_key_is_unique_and_prefixed():
    a = build_object_key("videos/", "clip.mp4")
    b = build_object_key("videos/", "clip.mp4")
    assert a.startswith("videos/") and a.endswith("_clip.mp4")
    assert a != b  # uuid guarantees no collision


def test_original_filename_roundtrip():
    key = build_object_key("videos/", "render_final.mp4")
    assert original_filename_from_key(key, "videos/") == "render_final.mp4"


def test_original_filename_fallback_for_foreign_key():
    assert original_filename_from_key("videos/legacy.mp4", "videos/") == "legacy.mp4"


def test_key_guard():
    assert is_key_within_prefix("videos/abc_clip.mp4", "videos/") is True
    assert is_key_within_prefix("videos/", "videos/") is False
    assert is_key_within_prefix("secrets/x", "videos/") is False
    assert is_key_within_prefix("videos/../secrets/x", "videos/") is False
    assert is_key_within_prefix("/videos/x", "videos/") is False


def test_mime_allowlist():
    allowed = {"video/mp4", "video/webm"}
    assert is_mime_allowed("video/mp4", allowed) is True
    assert is_mime_allowed("video/mp4; codecs=avc1", allowed) is True
    assert is_mime_allowed("text/plain", allowed) is False
    assert is_mime_allowed(None, allowed) is False


def test_magic_bytes():
    assert looks_like_video(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00") is True
    assert looks_like_video(b"\x1a\x45\xdf\xa3" + b"\x00" * 12) is True
    assert looks_like_video(b"this is not a video") is False
