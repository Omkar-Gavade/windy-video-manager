"""Tests for recording_time extraction (Feature 1: Windy filename time parsing)."""

from datetime import datetime, timezone

from app.aws import s3_client
from app.services import video_service
from app.utils.naming import (
    extract_metadata_from_key,
    extract_recording_time_from_filename,
)


def test_extract_recording_time_from_windy_filename():
    assert (
        extract_recording_time_from_filename(
            "SIRMOUR_satellite_2026-07-15_09-31-55_clean.mp4"
        )
        == "09:31:55"
    )


def test_extract_recording_time_missing_returns_none():
    assert extract_recording_time_from_filename("random_video.mp4") is None
    assert extract_recording_time_from_filename("legacy-clip.mp4") is None


def test_extract_metadata_includes_recording_time_for_structured_key():
    key = (
        "videos/MadhyaPradesh/SIRMOUR/2026-07-15/"
        "20260715T054125Z_733985759da8_SIRMOUR_satellite_2026-07-15_09-31-55_clean.mp4"
    )
    meta = extract_metadata_from_key(key, "videos/")
    assert meta["recording_time"] == "09:31:55"
    assert meta["state"] == "MadhyaPradesh"


def test_extract_metadata_recording_time_none_for_legacy_key():
    meta = extract_metadata_from_key("videos/20260101T000000Z_ff_legacy-clip.mp4", "videos/")
    assert meta["recording_time"] is None
    assert meta["state"] is None  # legacy also has no state/plant/date


def test_list_videos_returns_recording_time(monkeypatch):
    when = datetime(2026, 7, 15, tzinfo=timezone.utc)
    fake = [
        {
            "Key": (
                "videos/MadhyaPradesh/SIRMOUR/2026-07-15/"
                "20260715T054125Z_733985759da8_SIRMOUR_satellite_2026-07-15_09-31-55_clean.mp4"
            ),
            "Size": 1024,
            "LastModified": when,
        },
        {"Key": "videos/20260101T000000Z_ff_legacy.mp4", "Size": 512, "LastModified": when},
    ]
    monkeypatch.setattr(s3_client, "list_objects", lambda prefix: list(fake))

    result = video_service.list_videos()
    structured = next(v for v in result if "SIRMOUR" in v["key"])
    legacy = next(v for v in result if "legacy" in v["key"])

    assert structured["recording_time"] == "09:31:55"
    assert legacy["recording_time"] is None


def test_upload_video_returns_recording_time(monkeypatch):
    import io

    monkeypatch.setattr(s3_client, "upload_fileobj", lambda fileobj, key, content_type: None)
    mp4_bytes = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64

    result = video_service.upload_video(
        "SIRMOUR_satellite_2026-07-15_09-31-55_clean.mp4",
        "video/mp4",
        io.BytesIO(mp4_bytes),
        state="Madhya Pradesh",
        plant="SIRMOUR",
        recording_date="2026-07-15",
    )
    assert result["recording_time"] == "09:31:55"
