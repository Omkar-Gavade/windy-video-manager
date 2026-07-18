"""Tests for the Windy structured-key layout and metadata extraction."""

import io

from app.aws import s3_client
from app.services import video_service
from app.utils.naming import (
    build_structured_key,
    extract_metadata_from_key,
    sanitize_segment,
)

MP4_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


def test_sanitize_segment_removes_spaces_and_unsafe():
    assert sanitize_segment("Madhya Pradesh") == "MadhyaPradesh"
    assert sanitize_segment("SIRMOUR") == "SIRMOUR"
    assert sanitize_segment("2026-07-14") == "2026-07-14"
    assert sanitize_segment("") == "unknown"


def test_build_structured_key_layout_and_uniqueness():
    a = build_structured_key("videos/", "Madhya Pradesh", "SIRMOUR", "2026-07-14", "clip.mp4")
    b = build_structured_key("videos/", "Madhya Pradesh", "SIRMOUR", "2026-07-14", "clip.mp4")
    assert a.startswith("videos/MadhyaPradesh/SIRMOUR/2026-07-14/")
    assert a.endswith("_clip.mp4")
    assert a != b  # never overwrites


def test_extract_metadata_structured():
    key = build_structured_key("videos/", "MadhyaPradesh", "SIRMOUR", "2026-07-14", "render.mp4")
    meta = extract_metadata_from_key(key, "videos/")
    assert meta["state"] == "MadhyaPradesh"
    assert meta["plant"] == "SIRMOUR"
    assert meta["recording_date"] == "2026-07-14"
    assert meta["filename"] == "render.mp4"


def test_extract_metadata_legacy_is_none():
    meta = extract_metadata_from_key("videos/20260714T090000Z_aaaa1111_old.mp4", "videos/")
    assert meta["state"] is None
    assert meta["plant"] is None
    assert meta["recording_date"] is None
    assert meta["filename"] == "old.mp4"


def test_upload_with_metadata_builds_new_key_and_sidecar(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        s3_client, "upload_fileobj",
        lambda fileobj, key, content_type: captured.update(video_key=key),
    )
    monkeypatch.setattr(
        s3_client, "put_object",
        lambda key, body, content_type: captured.update(json_key=key, json_body=body),
    )

    result = video_service.upload_video(
        "SIRMOUR_satellite_2026-07-14_18_30_clean.mp4",
        "video/mp4",
        io.BytesIO(MP4_BYTES),
        state="Madhya Pradesh",
        plant="SIRMOUR",
        recording_date="2026-07-14",
        recording_time="18:30",
    )

    # New deterministic naming + JSON sidecar beside it.
    assert captured["video_key"] == "videos/MadhyaPradesh/SIRMOUR/2026-07-14/sirmour_260714_18_30.mp4"
    assert captured["json_key"] == "videos/MadhyaPradesh/SIRMOUR/2026-07-14/sirmour_260714_18_30.json"
    assert result["state"] == "MadhyaPradesh"
    assert result["plant"] == "SIRMOUR"
    assert result["recording_date"] == "2026-07-14"
    assert result["recording_time"] == "18:30:00"
    assert result["filename"] == "sirmour_260714_18_30.mp4"

    import json
    doc = json.loads(captured["json_body"].decode())
    assert doc["version"] == 1
    assert doc["filename"] == "sirmour_260714_18_30.mp4"
    assert doc["s3_key"] == captured["video_key"]


def test_upload_rolls_back_mp4_when_json_fails(monkeypatch):
    from botocore.exceptions import ClientError

    deleted = {}
    monkeypatch.setattr(s3_client, "upload_fileobj", lambda f, k, c: None)

    def boom(key, body, content_type):
        raise ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")

    monkeypatch.setattr(s3_client, "put_object", boom)
    monkeypatch.setattr(s3_client, "delete_object", lambda key: deleted.update(key=key))

    import pytest
    from app.utils.responses import AppError

    with pytest.raises(AppError) as exc:
        video_service.upload_video(
            "SIRMOUR_2026-07-14_18_30.mp4", "video/mp4", io.BytesIO(MP4_BYTES),
            state="MP", plant="SIRMOUR", recording_date="2026-07-14", recording_time="18:30",
        )
    assert exc.value.status_code == 502
    # The orphaned MP4 was deleted.
    assert deleted["key"] == "videos/MP/SIRMOUR/2026-07-14/sirmour_260714_18_30.mp4"


def test_upload_without_metadata_uses_flat_key(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        s3_client,
        "upload_fileobj",
        lambda fileobj, key, content_type: captured.update(key=key),
    )

    result = video_service.upload_video("clip.mp4", "video/mp4", io.BytesIO(MP4_BYTES))

    # Flat layout: only the filename segment after the prefix.
    assert captured["key"].startswith("videos/")
    assert captured["key"].count("/") == 1
    assert result["state"] is None


def test_list_returns_metadata_for_both_layouts(monkeypatch):
    from datetime import datetime, timezone

    when = datetime(2026, 7, 14, tzinfo=timezone.utc)
    fake = [
        {"Key": "videos/MadhyaPradesh/SIRMOUR/2026-07-14/20260714T103015Z_ab12cd34_a.mp4",
         "Size": 1024, "LastModified": when},
        {"Key": "videos/20260101T000000Z_ffff0000_legacy.mp4", "Size": 2048, "LastModified": when},
    ]
    monkeypatch.setattr(s3_client, "list_objects", lambda prefix: list(fake))
    monkeypatch.setattr(s3_client, "get_object_text", lambda key: None)  # no sidecar

    result = video_service.list_videos()
    structured = next(v for v in result if v["key"].endswith("_a.mp4"))
    legacy = next(v for v in result if v["key"].endswith("_legacy.mp4"))

    assert structured["state"] == "MadhyaPradesh"
    assert structured["plant"] == "SIRMOUR"
    assert structured["recording_date"] == "2026-07-14"
    assert legacy["state"] is None
    assert legacy["filename"] == "legacy.mp4"
