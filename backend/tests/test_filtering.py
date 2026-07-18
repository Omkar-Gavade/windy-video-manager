"""Tests for GET /api/videos filtering by state / plant / recording_date."""

from datetime import datetime, timezone

from app.aws import s3_client
from app.services import video_service

WHEN = datetime(2026, 7, 14, tzinfo=timezone.utc)

# Two plants, two dates, plus one legacy flat object.
FAKE = [
    {"Key": "videos/MadhyaPradesh/SIRMOUR/2026-07-14/20260714T101010Z_a1_a.mp4",
     "Size": 1000, "LastModified": WHEN},
    {"Key": "videos/MadhyaPradesh/SIRMOUR/2026-07-15/20260715T101010Z_a2_b.mp4",
     "Size": 1000, "LastModified": WHEN},
    {"Key": "videos/MadhyaPradesh/SATNA/2026-07-14/20260714T101010Z_a3_c.mp4",
     "Size": 1000, "LastModified": WHEN},
    {"Key": "videos/Maharashtra/PUNE/2026-07-14/20260714T101010Z_a4_d.mp4",
     "Size": 1000, "LastModified": WHEN},
    {"Key": "videos/20260101T000000Z_ff_legacy.mp4", "Size": 1000, "LastModified": WHEN},
]


def _stub(monkeypatch):
    """Stub list_objects; ignore prefix so the post-filter is exercised."""
    calls = []

    def fake(prefix):
        calls.append(prefix)
        return list(FAKE)

    monkeypatch.setattr(s3_client, "list_objects", fake)
    monkeypatch.setattr(s3_client, "get_object_text", lambda key: None)  # no sidecar -> key parse
    return calls


def test_no_filter_returns_all(monkeypatch):
    _stub(monkeypatch)
    assert len(video_service.list_videos()) == 5


def test_state_filter(monkeypatch):
    _stub(monkeypatch)
    result = video_service.list_videos(state="Madhya Pradesh")
    assert {v["state"] for v in result} == {"MadhyaPradesh"}
    assert len(result) == 3  # legacy + Maharashtra excluded


def test_plant_filter(monkeypatch):
    _stub(monkeypatch)
    result = video_service.list_videos(state="MadhyaPradesh", plant="SIRMOUR")
    assert len(result) == 2
    assert {v["plant"] for v in result} == {"SIRMOUR"}


def test_date_filter_combined(monkeypatch):
    _stub(monkeypatch)
    result = video_service.list_videos(
        state="MadhyaPradesh", plant="SIRMOUR", recording_date="2026-07-14"
    )
    assert len(result) == 1
    assert result[0]["recording_date"] == "2026-07-14"


def test_empty_results(monkeypatch):
    _stub(monkeypatch)
    assert video_service.list_videos(state="Kerala") == []


def test_filter_excludes_legacy(monkeypatch):
    _stub(monkeypatch)
    result = video_service.list_videos(state="MadhyaPradesh")
    assert all(v["state"] is not None for v in result)


def test_prefix_is_narrowed_for_full_hierarchy(monkeypatch):
    calls = _stub(monkeypatch)
    video_service.list_videos(
        state="Madhya Pradesh", plant="SIRMOUR", recording_date="2026-07-14"
    )
    assert calls[-1] == "videos/MadhyaPradesh/SIRMOUR/2026-07-14/"


def test_prefix_only_state(monkeypatch):
    calls = _stub(monkeypatch)
    video_service.list_videos(state="Madhya Pradesh")
    assert calls[-1] == "videos/MadhyaPradesh/"
