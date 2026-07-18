"""Tests for the preview / download presigned-URL flow.

The AWS layer is monkeypatched so no real S3 account is needed.
"""

import pytest
from botocore.exceptions import ClientError

from app.aws import s3_client
from app.services import video_service
from app.utils.responses import AppError

VALID_KEY = "videos/20260714T090000Z_cccc2222dddd_render_final.mp4"


def _stub_s3(monkeypatch, exists=True):
    """Stub existence + presign, capturing the presign call arguments."""
    calls = []
    monkeypatch.setattr(s3_client, "object_exists", lambda key: exists)
    monkeypatch.setattr(s3_client, "get_object_text", lambda key: None)  # no sidecar -> key parse

    def fake_presign(key, expiry, disposition):
        calls.append({"key": key, "expiry": expiry, "disposition": disposition})
        return f"https://s3.example/{key}?sig=abc"

    monkeypatch.setattr(s3_client, "generate_presigned_get_url", fake_presign)
    return calls


def test_preview_url_is_inline_with_preview_expiry(monkeypatch):
    calls = _stub_s3(monkeypatch)
    from app.config.settings import get_settings

    result = video_service.get_preview_url(VALID_KEY)

    assert result["url"].startswith("https://s3.example/")
    assert calls[0]["disposition"] == "inline"
    assert calls[0]["expiry"] == get_settings().preview_expiry_seconds


def test_download_url_is_attachment_with_encoded_filename(monkeypatch):
    calls = _stub_s3(monkeypatch)
    from app.config.settings import get_settings

    result = video_service.get_download_url(VALID_KEY)

    assert result["url"].startswith("https://s3.example/")
    disposition = calls[0]["disposition"]
    assert disposition.startswith("attachment;")
    assert 'filename="render_final.mp4"' in disposition
    assert "filename*=UTF-8''render_final.mp4" in disposition
    assert calls[0]["expiry"] == get_settings().download_expiry_seconds


@pytest.mark.parametrize(
    "bad_key",
    ["secrets/passwords.txt", "videos/", "../etc/passwd", "/videos/x.mp4"],
)
def test_key_guard_blocks_out_of_prefix(monkeypatch, bad_key):
    called = {"exists": False, "presign": False}
    monkeypatch.setattr(s3_client, "object_exists", lambda key: called.__setitem__("exists", True) or True)
    monkeypatch.setattr(
        s3_client,
        "generate_presigned_get_url",
        lambda *a, **k: called.__setitem__("presign", True) or "x",
    )

    with pytest.raises(AppError) as exc:
        video_service.get_preview_url(bad_key)

    assert exc.value.status_code == 404
    # Never touched S3 for an invalid key.
    assert called == {"exists": False, "presign": False}


def test_missing_object_returns_404(monkeypatch):
    _stub_s3(monkeypatch, exists=False)
    with pytest.raises(AppError) as exc:
        video_service.get_preview_url(VALID_KEY)
    assert exc.value.status_code == 404


def test_presign_s3_error_returns_502(monkeypatch):
    monkeypatch.setattr(s3_client, "object_exists", lambda key: True)

    def boom(key, expiry, disposition):
        raise ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")

    monkeypatch.setattr(s3_client, "generate_presigned_get_url", boom)
    with pytest.raises(AppError) as exc:
        video_service.get_download_url(VALID_KEY)
    assert exc.value.status_code == 502
    assert "AccessDenied" not in exc.value.message
