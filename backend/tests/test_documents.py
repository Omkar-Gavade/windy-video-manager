"""Tests for the Documents module: naming, upload, list, filter, preview/download."""

import io
from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError

from app.aws import s3_client
from app.routes import documents as documents_route
from app.services import document_service
from app.utils.naming import build_document_key, extract_document_metadata_from_key
from app.utils.responses import AppError

PDF_BYTES = b"%PDF-1.4\n%fake pdf content for testing\n"


# --- naming -----------------------------------------------------------------


def test_build_document_key_embeds_time_and_is_unique():
    a = build_document_key(
        "documents/", "Madhya Pradesh", "SIRMOUR", "2026-07-15", "11:30:00", "Report.pdf"
    )
    b = build_document_key(
        "documents/", "Madhya Pradesh", "SIRMOUR", "2026-07-15", "11:30:00", "Report.pdf"
    )
    assert a.startswith("documents/MadhyaPradesh/SIRMOUR/2026-07-15/")
    assert a.endswith("_Report.pdf")
    assert a != b  # uuid guarantees uniqueness, no overwrite


def test_extract_document_metadata_with_time():
    key = build_document_key(
        "documents/", "MadhyaPradesh", "SIRMOUR", "2026-07-15", "11:30:00", "InspectionReport.pdf"
    )
    meta = extract_document_metadata_from_key(key, "documents/")
    assert meta["state"] == "MadhyaPradesh"
    assert meta["plant"] == "SIRMOUR"
    assert meta["document_date"] == "2026-07-15"
    assert meta["document_time"] == "11:30:00"
    assert meta["filename"] == "InspectionReport.pdf"


def test_extract_document_metadata_hh_mm_input_pads_seconds():
    # <input type="time"> without seconds -> "HH:MM"; padded to HH:MM:00.
    key = build_document_key(
        "documents/", "MadhyaPradesh", "SIRMOUR", "2026-07-15", "11:30", "Report.pdf"
    )
    meta = extract_document_metadata_from_key(key, "documents/")
    assert meta["document_time"] == "11:30:00"


def test_extract_document_metadata_without_time():
    key = build_document_key(
        "documents/", "MadhyaPradesh", "SIRMOUR", "2026-07-15", None, "Report.pdf"
    )
    meta = extract_document_metadata_from_key(key, "documents/")
    assert meta["document_time"] is None
    assert meta["filename"] == "Report.pdf"


def test_extract_document_metadata_legacy_key():
    meta = extract_document_metadata_from_key("documents/20260101T000000Z_ff_old.pdf", "documents/")
    assert meta == {
        "state": None,
        "plant": None,
        "document_date": None,
        "document_time": None,
        "filename": "20260101T000000Z_ff_old.pdf",
    }


# --- upload -------------------------------------------------------------------


def _capture_upload(monkeypatch):
    calls = []

    def fake_upload(fileobj, key, content_type):
        calls.append({"key": key, "content_type": content_type, "body": fileobj.read()})

    monkeypatch.setattr(s3_client, "upload_fileobj", fake_upload)
    return calls


def test_upload_document_success_structured(monkeypatch):
    calls = _capture_upload(monkeypatch)

    result = document_service.upload_document(
        "InspectionReport.pdf",
        "application/pdf",
        io.BytesIO(PDF_BYTES),
        state="Madhya Pradesh",
        plant="SIRMOUR",
        document_date="2026-07-15",
        document_time="11:30:00",
    )

    assert result["state"] == "MadhyaPradesh"
    assert result["plant"] == "SIRMOUR"
    assert result["document_date"] == "2026-07-15"
    assert result["document_time"] == "11:30:00"
    assert result["filename"] == "InspectionReport.pdf"
    assert result["key"].startswith("documents/MadhyaPradesh/SIRMOUR/2026-07-15/")
    assert calls[0]["content_type"] == "application/pdf"


def test_upload_document_rejects_bad_extension(monkeypatch):
    _capture_upload(monkeypatch)
    with pytest.raises(AppError) as exc:
        document_service.upload_document(
            "malware.exe", "application/pdf", io.BytesIO(PDF_BYTES)
        )
    assert exc.value.status_code == 400


def test_upload_document_rejects_bad_mime(monkeypatch):
    _capture_upload(monkeypatch)
    with pytest.raises(AppError) as exc:
        document_service.upload_document(
            "report.pdf", "application/octet-stream", io.BytesIO(PDF_BYTES)
        )
    assert exc.value.status_code == 400


def test_upload_document_rejects_empty(monkeypatch):
    _capture_upload(monkeypatch)
    with pytest.raises(AppError) as exc:
        document_service.upload_document("report.pdf", "application/pdf", io.BytesIO(b""))
    assert exc.value.status_code == 400


def test_upload_document_wraps_s3_errors(monkeypatch):
    def boom(fileobj, key, content_type):
        raise ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")

    monkeypatch.setattr(s3_client, "upload_fileobj", boom)
    with pytest.raises(AppError) as exc:
        document_service.upload_document("report.pdf", "application/pdf", io.BytesIO(PDF_BYTES))
    assert exc.value.status_code == 502
    assert "AccessDenied" not in exc.value.message


def test_upload_document_accepts_all_allowed_extensions(monkeypatch):
    calls = _capture_upload(monkeypatch)
    mime_by_ext = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".txt": "text/plain",
    }
    for ext, mime in mime_by_ext.items():
        document_service.upload_document(f"file{ext}", mime, io.BytesIO(b"x"))
    assert len(calls) == len(mime_by_ext)


# --- list / filter --------------------------------------------------------------


def test_list_documents_maps_and_filters(monkeypatch):
    when = datetime(2026, 7, 15, tzinfo=timezone.utc)
    key1 = build_document_key(
        "documents/", "MadhyaPradesh", "SIRMOUR", "2026-07-15", "11:30:00", "a.pdf"
    )
    key2 = build_document_key(
        "documents/", "MadhyaPradesh", "SATNA", "2026-07-15", "09:00:00", "b.pdf"
    )
    fake = [
        {"Key": key1, "Size": 1024, "LastModified": when},
        {"Key": key2, "Size": 2048, "LastModified": when},
    ]
    monkeypatch.setattr(s3_client, "list_objects", lambda prefix: list(fake))

    all_docs = document_service.list_documents()
    assert len(all_docs) == 2

    sirmour_only = document_service.list_documents(state="MadhyaPradesh", plant="SIRMOUR")
    assert len(sirmour_only) == 1
    assert sirmour_only[0]["plant"] == "SIRMOUR"
    assert sirmour_only[0]["document_time"] == "11:30:00"

    empty = document_service.list_documents(state="Kerala")
    assert empty == []


def test_list_documents_wraps_s3_errors(monkeypatch):
    def boom(prefix):
        raise ClientError({"Error": {"Code": "AccessDenied"}}, "ListObjectsV2")

    monkeypatch.setattr(s3_client, "list_objects", boom)
    with pytest.raises(AppError) as exc:
        document_service.list_documents()
    assert exc.value.status_code == 502


# --- preview / download -----------------------------------------------------------


def test_preview_and_download_url(monkeypatch):
    key = build_document_key(
        "documents/", "MadhyaPradesh", "SIRMOUR", "2026-07-15", "11:30:00", "Report.pdf"
    )
    monkeypatch.setattr(s3_client, "object_exists", lambda k: True)

    calls = []

    def fake_presign(k, expiry, disposition):
        calls.append({"key": k, "expiry": expiry, "disposition": disposition})
        return f"https://s3.example/{k}"

    monkeypatch.setattr(s3_client, "generate_presigned_get_url", fake_presign)

    preview = document_service.get_preview_url(key)
    assert preview["url"].startswith("https://s3.example/")
    assert calls[0]["disposition"] == "inline"

    download = document_service.get_download_url(key)
    assert download["url"].startswith("https://s3.example/")
    assert 'filename="Report.pdf"' in calls[1]["disposition"]


def test_preview_key_guard_blocks_out_of_prefix(monkeypatch):
    called = {"touched": False}
    monkeypatch.setattr(s3_client, "object_exists", lambda k: called.__setitem__("touched", True) or True)

    with pytest.raises(AppError) as exc:
        document_service.get_preview_url("videos/some-video.mp4")  # wrong prefix
    assert exc.value.status_code == 404
    assert called["touched"] is False


def test_preview_missing_object_404(monkeypatch):
    monkeypatch.setattr(s3_client, "object_exists", lambda k: False)
    with pytest.raises(AppError) as exc:
        document_service.get_preview_url("documents/MadhyaPradesh/SIRMOUR/2026-07-15/x_y_z.pdf")
    assert exc.value.status_code == 404


# --- route envelope -----------------------------------------------------------------


def test_list_route_wraps_success_envelope(monkeypatch):
    monkeypatch.setattr(document_service, "list_documents", lambda *a, **k: [{"filename": "x.pdf"}])
    body = documents_route.list_documents(None, None, None)
    assert body == {"success": True, "data": [{"filename": "x.pdf"}]}
