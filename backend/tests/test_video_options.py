"""Tests for dynamic states/plants discovery and JSON-sidecar listing."""

import json
from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError

from app.aws import s3_client
from app.services import video_service
from app.utils.responses import AppError


def test_list_states_from_common_prefixes(monkeypatch):
    monkeypatch.setattr(s3_client, "list_common_prefixes", lambda prefix: ["Rajasthan", "MadhyaPradesh"])
    assert video_service.list_states() == ["MadhyaPradesh", "Rajasthan"]  # sorted


def test_list_plants_for_state(monkeypatch):
    seen = {}

    def fake(prefix):
        seen["prefix"] = prefix
        return ["SATNA", "SIRMOUR"]

    monkeypatch.setattr(s3_client, "list_common_prefixes", fake)
    assert video_service.list_plants("Madhya Pradesh") == ["SATNA", "SIRMOUR"]
    assert seen["prefix"] == "videos/MadhyaPradesh/"


def test_list_plants_empty_state_returns_empty():
    assert video_service.list_plants("") == []


def test_list_states_wraps_errors(monkeypatch):
    def boom(prefix):
        raise ClientError({"Error": {"Code": "AccessDenied"}}, "ListObjectsV2")

    monkeypatch.setattr(s3_client, "list_common_prefixes", boom)
    with pytest.raises(AppError) as exc:
        video_service.list_states()
    assert exc.value.status_code == 502


def test_list_uses_json_sidecar_when_present(monkeypatch):
    when = datetime(2026, 7, 17, tzinfo=timezone.utc)
    key = "videos/MadhyaPradesh/SIRMOUR/2026-07-17/sirmour_260717_06_45.mp4"
    fake = [{"Key": key, "Size": 1024, "LastModified": when}]
    sidecar = {
        "version": 1, "filename": "sirmour_260717_06_45.mp4",
        "state": "MadhyaPradesh", "plant": "SIRMOUR",
        "recording_date": "2026-07-17", "recording_time": "06:45:00",
    }
    monkeypatch.setattr(s3_client, "list_objects", lambda prefix: list(fake))
    monkeypatch.setattr(s3_client, "get_object_text", lambda k: json.dumps(sidecar) if k.endswith(".json") else None)

    result = video_service.list_videos()
    assert len(result) == 1
    v = result[0]
    assert v["filename"] == "sirmour_260717_06_45.mp4"
    assert v["recording_time"] == "06:45:00"
    assert v["state"] == "MadhyaPradesh" and v["plant"] == "SIRMOUR"


def test_list_excludes_json_sidecars(monkeypatch):
    when = datetime(2026, 7, 17, tzinfo=timezone.utc)
    fake = [
        {"Key": "videos/MadhyaPradesh/SIRMOUR/2026-07-17/sirmour_260717_06_45.mp4", "Size": 10, "LastModified": when},
        {"Key": "videos/MadhyaPradesh/SIRMOUR/2026-07-17/sirmour_260717_06_45.json", "Size": 5, "LastModified": when},
    ]
    monkeypatch.setattr(s3_client, "list_objects", lambda prefix: list(fake))
    monkeypatch.setattr(s3_client, "get_object_text", lambda k: None)

    result = video_service.list_videos()
    assert len(result) == 1  # the .json is not a listable video
    assert result[0]["key"].endswith(".mp4")


def test_states_plants_routes(monkeypatch):
    from app.routes import videos as videos_route

    monkeypatch.setattr(video_service, "list_states", lambda: ["MadhyaPradesh"])
    monkeypatch.setattr(video_service, "list_plants", lambda state: ["SIRMOUR"])
    assert videos_route.list_states() == {"success": True, "data": ["MadhyaPradesh"]}
    assert videos_route.list_plants("MadhyaPradesh") == {"success": True, "data": ["SIRMOUR"]}
