"""Tests for the list flow: service mapping + route envelope + error handling.

The AWS layer is monkeypatched so no real S3 account is needed.
"""

from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError

from app.aws import s3_client
from app.routes import videos as videos_route
from app.services import video_service
from app.utils.responses import AppError


def _obj(key: str, size: int, when: datetime) -> dict:
    return {"Key": key, "Size": size, "LastModified": when}


def test_list_maps_and_sorts_newest_first(monkeypatch):
    older = datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc)
    fake = [
        _obj("videos/20260710T080000Z_aaaa1111bbbb_old.mp4", 1024, older),
        _obj("videos/20260714T090000Z_cccc2222dddd_new.mp4", 5 * 1024 * 1024, newer),
    ]
    monkeypatch.setattr(s3_client, "list_objects", lambda prefix: list(fake))
    monkeypatch.setattr(s3_client, "get_object_text", lambda key: None)  # no sidecar -> key parse

    result = video_service.list_videos()

    assert [v["filename"] for v in result] == ["new.mp4", "old.mp4"]  # newest first
    assert result[0]["size"] == "5.0 MB"
    assert result[1]["size"] == "1.0 KB"
    assert result[0]["s3_path"].startswith("s3://test-bucket/videos/")
    assert result[0]["key"].endswith("_new.mp4")
    assert result[0]["upload_date"] == "2026-07-14T09:00:00+00:00"


def test_list_empty_bucket(monkeypatch):
    monkeypatch.setattr(s3_client, "list_objects", lambda prefix: [])
    assert video_service.list_videos() == []


def test_list_wraps_s3_errors_as_app_error(monkeypatch):
    def boom(prefix):
        raise ClientError({"Error": {"Code": "AccessDenied"}}, "ListObjectsV2")

    monkeypatch.setattr(s3_client, "list_objects", boom)

    with pytest.raises(AppError) as exc:
        video_service.list_videos()
    assert exc.value.status_code == 502
    # Message is user-safe, no AWS internals leaked.
    assert "AccessDenied" not in exc.value.message


def test_route_wraps_result_in_success_envelope(monkeypatch):
    monkeypatch.setattr(
        video_service, "list_videos", lambda *a, **k: [{"filename": "x.mp4"}]
    )
    body = videos_route.list_videos(None, None, None)
    assert body == {"success": True, "data": [{"filename": "x.mp4"}]}
