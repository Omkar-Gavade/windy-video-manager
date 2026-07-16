"""Tests for the upload flow: validation, unique naming, and error handling.

The AWS upload call is monkeypatched so no real S3 account is needed.
"""

import io

import pytest
from botocore.exceptions import ClientError

from app.aws import s3_client
from app.services import video_service
from app.utils.responses import AppError

# Minimal valid MP4 header (ISO base media 'ftyp' box) + padding.
MP4_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


def _capture_upload(monkeypatch):
    """Replace the AWS upload with a capture and return the recorded calls."""
    calls = []

    def fake_upload(fileobj, key, content_type):
        calls.append({"key": key, "content_type": content_type, "body": fileobj.read()})

    monkeypatch.setattr(s3_client, "upload_fileobj", fake_upload)
    return calls


def test_upload_success(monkeypatch):
    calls = _capture_upload(monkeypatch)

    result = video_service.upload_video("render.mp4", "video/mp4", io.BytesIO(MP4_BYTES))

    assert result["filename"] == "render.mp4"
    assert result["key"].startswith("videos/") and result["key"].endswith("_render.mp4")
    assert result["s3_path"] == f"s3://test-bucket/{result['key']}"
    assert result["size"].endswith("B")
    # Uploaded with the right content type and full body.
    assert len(calls) == 1
    assert calls[0]["content_type"] == "video/mp4"
    assert calls[0]["body"] == MP4_BYTES


def test_upload_rejects_missing_filename(monkeypatch):
    _capture_upload(monkeypatch)
    with pytest.raises(AppError) as exc:
        video_service.upload_video(None, "video/mp4", io.BytesIO(MP4_BYTES))
    assert exc.value.status_code == 400


def test_upload_rejects_bad_mime(monkeypatch):
    _capture_upload(monkeypatch)
    with pytest.raises(AppError) as exc:
        video_service.upload_video("x.txt", "text/plain", io.BytesIO(MP4_BYTES))
    assert exc.value.status_code == 400


def test_upload_rejects_non_video_content(monkeypatch):
    _capture_upload(monkeypatch)
    # MIME claims video, but bytes are not a video container.
    with pytest.raises(AppError) as exc:
        video_service.upload_video("fake.mp4", "video/mp4", io.BytesIO(b"hello world!!"))
    assert exc.value.status_code == 400


def test_upload_rejects_empty_file(monkeypatch):
    _capture_upload(monkeypatch)
    with pytest.raises(AppError) as exc:
        video_service.upload_video("empty.mp4", "video/mp4", io.BytesIO(b""))
    assert exc.value.status_code == 400


def test_upload_rejects_oversize(monkeypatch):
    _capture_upload(monkeypatch)
    from app.config.settings import get_settings

    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    big = io.BytesIO(MP4_BYTES + b"\x00" * (max_bytes + 1))
    with pytest.raises(AppError) as exc:
        video_service.upload_video("big.mp4", "video/mp4", big)
    assert exc.value.status_code == 413


def test_upload_wraps_s3_errors(monkeypatch):
    def boom(fileobj, key, content_type):
        raise ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")

    monkeypatch.setattr(s3_client, "upload_fileobj", boom)
    with pytest.raises(AppError) as exc:
        video_service.upload_video("render.mp4", "video/mp4", io.BytesIO(MP4_BYTES))
    assert exc.value.status_code == 502
    assert "AccessDenied" not in exc.value.message
