"""Tests for the AWS-layer ``list_objects`` pagination and filtering."""

from datetime import datetime, timezone

from app.aws import s3_client


class _FakeClient:
    """Minimal stub returning two truncated pages of results."""

    def __init__(self, pages):
        self._pages = pages
        self.calls = []

    def list_objects_v2(self, **kwargs):
        self.calls.append(kwargs)
        token = kwargs.get("ContinuationToken")
        index = 0 if token is None else int(token)
        return self._pages[index]


def test_list_objects_follows_continuation_and_skips_markers(monkeypatch):
    when = datetime(2026, 7, 14, tzinfo=timezone.utc)
    pages = [
        {
            "Contents": [
                {"Key": "videos/", "Size": 0, "LastModified": when},  # marker, skip
                {"Key": "videos/a.mp4", "Size": 10, "LastModified": when},
            ],
            "IsTruncated": True,
            "NextContinuationToken": "1",
        },
        {
            "Contents": [
                {"Key": "videos/sub/", "Size": 0, "LastModified": when},  # marker, skip
                {"Key": "videos/b.mp4", "Size": 20, "LastModified": when},
            ],
            "IsTruncated": False,
        },
    ]
    fake = _FakeClient(pages)
    monkeypatch.setattr(s3_client, "get_s3_client", lambda: fake)

    result = s3_client.list_objects("videos/")

    assert [o["Key"] for o in result] == ["videos/a.mp4", "videos/b.mp4"]
    assert len(fake.calls) == 2  # both pages fetched
    assert fake.calls[1]["ContinuationToken"] == "1"
