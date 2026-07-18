"""Tests for the Inputs module.

Structure:
    inputs/<State>/<Plant>/Site_Details/<fixed json>          (no date)
    inputs/<State>/<Plant>/<Date>/Enercast_Data|Metered_Data|WP/<Type>|fetch_manifest.json
"""

import io
from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError

from app.aws import s3_client
from app.routes import inputs as inputs_route
from app.services import input_service
from app.utils.naming import build_input_key, extract_input_metadata_from_key
from app.utils.responses import AppError

PREFIX = "inputs/"


# --- naming -----------------------------------------------------------------


def test_build_site_details_under_plant_no_date():
    k = build_input_key(PREFIX, "Madhya Pradesh", "SIRMOUR", None, "Site Details", None, "site_details.json", "upload.json")
    assert k == "inputs/MadhyaPradesh/SIRMOUR/Site_Details/site_details.json"


def test_build_enercast_under_date():
    k = build_input_key(PREFIX, "MadhyaPradesh", "SIRMOUR", "2026-07-17", "Enercast Data", None, None, "forecast.csv")
    assert k == "inputs/MadhyaPradesh/SIRMOUR/2026-07-17/Enercast_Data/forecast.csv"


def test_build_metered_under_date():
    k = build_input_key(PREFIX, "MadhyaPradesh", "SIRMOUR", "2026-07-17", "Metered Data", None, None, "meter_data.csv")
    assert k == "inputs/MadhyaPradesh/SIRMOUR/2026-07-17/Metered_Data/meter_data.csv"


def test_build_wp_images_and_videos():
    img = build_input_key(PREFIX, "MP", "SIRMOUR", "2026-07-17", "WP", "Images", None, "weather_image.jpg")
    vid = build_input_key(PREFIX, "MP", "SIRMOUR", "2026-07-17", "WP", "Videos", None, "windy_video.mp4")
    assert img.endswith("/2026-07-17/WP/Images/weather_image.jpg")
    assert vid.endswith("/2026-07-17/WP/Videos/windy_video.mp4")


def test_build_fetch_manifest_forces_name_under_date():
    k = build_input_key(PREFIX, "MP", "SIRMOUR", "2026-07-17", "Fetch Manifest", None, None, "anything.json")
    assert k == "inputs/MP/SIRMOUR/2026-07-17/fetch_manifest.json"


def test_original_filename_preserved():
    k = build_input_key(PREFIX, "MP", "SIRMOUR", "2026-07-17", "Enercast Data", None, None, "2026_07_17_SOLAR_INV.csv")
    assert k.endswith("/Enercast_Data/2026_07_17_SOLAR_INV.csv")


@pytest.mark.parametrize(
    "key,cat,sub,wp,fname,date",
    [
        ("inputs/MadhyaPradesh/SIRMOUR/Site_Details/site_details.json", "Site Details", "site_details.json", None, "site_details.json", None),
        ("inputs/MadhyaPradesh/SIRMOUR/Site_Details/metadata.json", "Site Details", "metadata.json", None, "metadata.json", None),
        ("inputs/MadhyaPradesh/SIRMOUR/2026-07-17/Enercast_Data/f.csv", "Enercast Data", None, None, "f.csv", "2026-07-17"),
        ("inputs/MadhyaPradesh/SIRMOUR/2026-07-17/Metered_Data/m.csv", "Metered Data", None, None, "m.csv", "2026-07-17"),
        ("inputs/MadhyaPradesh/SIRMOUR/2026-07-17/WP/Images/i.jpg", "WP", None, "Images", "i.jpg", "2026-07-17"),
        ("inputs/MadhyaPradesh/SIRMOUR/2026-07-17/WP/Videos/v.mp4", "WP", None, "Videos", "v.mp4", "2026-07-17"),
        ("inputs/MadhyaPradesh/SIRMOUR/2026-07-17/fetch_manifest.json", "Fetch Manifest", None, None, "fetch_manifest.json", "2026-07-17"),
    ],
)
def test_extract_metadata(key, cat, sub, wp, fname, date):
    m = extract_input_metadata_from_key(key, PREFIX)
    assert m["state"] == "MadhyaPradesh"
    assert m["plant"] == "SIRMOUR"
    assert m["category"] == cat
    assert m["sub_category"] == sub
    assert m["wp_type"] == wp
    assert m["filename"] == fname
    assert m["input_date"] == date


# --- upload -----------------------------------------------------------------


def _capture(monkeypatch):
    calls = []

    def fake(fileobj, key, content_type, metadata=None):
        calls.append({"key": key, "content_type": content_type, "metadata": metadata})

    monkeypatch.setattr(s3_client, "upload_fileobj", fake)
    return calls


def test_upload_site_details_stores_fixed_name(monkeypatch):
    calls = _capture(monkeypatch)
    result = input_service.upload_input(
        "whatever.json", "application/json", io.BytesIO(b"{}"),
        state="Madhya Pradesh", plant="SIRMOUR", input_date=None,
        input_time="02:05:09 PM", category="Site Details", wp_type=None,
        sub_category="site_configuration.json",
    )
    assert calls[0]["key"] == "inputs/MadhyaPradesh/SIRMOUR/Site_Details/site_configuration.json"
    assert calls[0]["metadata"] == {"input-time": "02:05:09 PM"}
    assert result["category"] == "Site Details"
    assert result["sub_category"] == "site_configuration.json"
    assert result["input_date"] is None


def test_upload_enercast(monkeypatch):
    calls = _capture(monkeypatch)
    result = input_service.upload_input(
        "forecast.csv", "text/csv", io.BytesIO(b"a,b"),
        "Madhya Pradesh", "SIRMOUR", "2026-07-17", "10:00:00 AM", "Enercast Data",
    )
    assert calls[0]["key"] == "inputs/MadhyaPradesh/SIRMOUR/2026-07-17/Enercast_Data/forecast.csv"
    assert result["input_time"] == "10:00:00 AM"


def test_upload_wp_video(monkeypatch):
    calls = _capture(monkeypatch)
    input_service.upload_input(
        "windy_video.mp4", "video/mp4", io.BytesIO(b"x"),
        "MP", "SIRMOUR", "2026-07-17", "10:00:00 AM", "WP", wp_type="Videos",
    )
    assert calls[0]["key"].endswith("/2026-07-17/WP/Videos/windy_video.mp4")


def test_upload_fetch_manifest_forces_name(monkeypatch):
    calls = _capture(monkeypatch)
    result = input_service.upload_input(
        "x.json", "application/json", io.BytesIO(b"{}"),
        "MP", "SIRMOUR", "2026-07-17", "10:00:00 AM", "Fetch Manifest",
    )
    assert calls[0]["key"].endswith("/2026-07-17/fetch_manifest.json")
    assert result["filename"] == "fetch_manifest.json"


def test_upload_wp_requires_type(monkeypatch):
    _capture(monkeypatch)
    with pytest.raises(AppError) as e:
        input_service.upload_input("v.mp4", "video/mp4", io.BytesIO(b"x"), "MP", "SIRMOUR", "2026-07-17", "t", "WP")
    assert e.value.status_code == 400


def test_upload_date_category_requires_date(monkeypatch):
    _capture(monkeypatch)
    with pytest.raises(AppError) as e:
        input_service.upload_input("f.csv", "text/csv", io.BytesIO(b"x"), "MP", "SIRMOUR", None, "t", "Enercast Data")
    assert e.value.status_code == 400


def test_upload_site_details_requires_valid_sub(monkeypatch):
    _capture(monkeypatch)
    with pytest.raises(AppError) as e:
        input_service.upload_input("x.json", "application/json", io.BytesIO(b"{}"), "MP", "SIRMOUR", None, "t", "Site Details", sub_category="bogus.json")
    assert e.value.status_code == 400


def test_upload_rejects_bad_extension(monkeypatch):
    _capture(monkeypatch)
    with pytest.raises(AppError) as e:
        input_service.upload_input("photo.png", "image/png", io.BytesIO(b"x"), "MP", "SIRMOUR", "2026-07-17", "t", "Metered Data")
    assert e.value.status_code == 400


# --- list / filter ----------------------------------------------------------


def _obj(key, when):
    return {"Key": key, "Size": 100, "LastModified": when}


def test_list_and_filters(monkeypatch):
    when = datetime(2026, 7, 17, tzinfo=timezone.utc)
    fake = [
        _obj("inputs/MadhyaPradesh/SIRMOUR/Site_Details/site_details.json", when),
        _obj("inputs/MadhyaPradesh/SIRMOUR/2026-07-17/Enercast_Data/f.csv", when),
        _obj("inputs/MadhyaPradesh/SIRMOUR/2026-07-17/WP/Images/i.jpg", when),
        _obj("inputs/MadhyaPradesh/SIRMOUR/2026-07-17/WP/Videos/v.mp4", when),
    ]
    monkeypatch.setattr(s3_client, "list_objects", lambda prefix: list(fake))
    monkeypatch.setattr(s3_client, "head_object", lambda key: {"Metadata": {"input-time": "09:00:00 AM"}})

    assert len(input_service.list_inputs()) == 4
    assert input_service.list_inputs()[0]["input_time"] == "09:00:00 AM"

    sd = input_service.list_inputs(category="Site Details")
    assert len(sd) == 1 and sd[0]["sub_category"] == "site_details.json"

    wp_imgs = input_service.list_inputs(category="WP", wp_type="Images")
    assert len(wp_imgs) == 1 and wp_imgs[0]["filename"] == "i.jpg"

    by_date = input_service.list_inputs(input_date="2026-07-17")
    assert len(by_date) == 3  # excludes plant-scoped Site_Details (no date)

    assert input_service.list_inputs(state="Kerala") == []


def test_list_wraps_s3_errors(monkeypatch):
    monkeypatch.setattr(
        s3_client, "list_objects",
        lambda prefix: (_ for _ in ()).throw(ClientError({"Error": {"Code": "AccessDenied"}}, "ListObjectsV2")),
    )
    with pytest.raises(AppError) as e:
        input_service.list_inputs()
    assert e.value.status_code == 502


# --- preview / download / guard ---------------------------------------------


def test_preview_download_guard(monkeypatch):
    key = "inputs/MadhyaPradesh/SIRMOUR/2026-07-17/WP/Images/weather_image.jpg"
    monkeypatch.setattr(s3_client, "object_exists", lambda k: True)
    calls = []
    monkeypatch.setattr(s3_client, "generate_presigned_get_url", lambda k, e, d: calls.append(d) or f"https://s3/{k}")

    assert input_service.get_preview_url(key)["url"].startswith("https://s3/")
    assert calls[0] == "inline"
    input_service.get_download_url(key)
    assert 'filename="weather_image.jpg"' in calls[1]


def test_guard_blocks_out_of_prefix(monkeypatch):
    touched = {"v": False}
    monkeypatch.setattr(s3_client, "object_exists", lambda k: touched.__setitem__("v", True) or True)
    with pytest.raises(AppError) as e:
        input_service.get_preview_url("videos/x.mp4")
    assert e.value.status_code == 404
    assert touched["v"] is False


def test_route_success_envelope(monkeypatch):
    monkeypatch.setattr(input_service, "list_inputs", lambda *a, **k: [{"filename": "x"}])
    body = inputs_route.list_inputs(None, None, None, None, None)
    assert body == {"success": True, "data": [{"filename": "x"}]}


# --- dynamic states / plants ------------------------------------------------


def test_list_states(monkeypatch):
    monkeypatch.setattr(s3_client, "list_common_prefixes", lambda prefix: ["Punjab", "MadhyaPradesh"])
    assert input_service.list_states() == ["MadhyaPradesh", "Punjab"]


def test_list_plants(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        s3_client, "list_common_prefixes",
        lambda prefix: seen.update(prefix=prefix) or ["SATNA", "SIRMOUR"],
    )
    assert input_service.list_plants("Madhya Pradesh") == ["SATNA", "SIRMOUR"]
    assert seen["prefix"] == "inputs/MadhyaPradesh/"


def test_list_plants_empty_state():
    assert input_service.list_plants("") == []


def test_states_plants_content_routes(monkeypatch):
    monkeypatch.setattr(input_service, "list_states", lambda: ["MadhyaPradesh"])
    monkeypatch.setattr(input_service, "list_plants", lambda state: ["SIRMOUR"])
    assert inputs_route.list_states() == {"success": True, "data": ["MadhyaPradesh"]}
    assert inputs_route.list_plants("MadhyaPradesh") == {"success": True, "data": ["SIRMOUR"]}


# --- text content for preview -----------------------------------------------


def test_get_content_json(monkeypatch):
    key = "inputs/MadhyaPradesh/SIRMOUR/Site_Details/site_details.json"
    monkeypatch.setattr(s3_client, "get_object_text", lambda k: '{"site": "SIRMOUR"}')
    result = input_service.get_input_content(key)
    assert result["content"] == '{"site": "SIRMOUR"}'
    assert result["filename"] == "site_details.json"


def test_get_content_rejects_binary_type():
    with pytest.raises(AppError) as e:
        input_service.get_input_content("inputs/MP/SIRMOUR/2026-07-17/WP/Images/x.png")
    assert e.value.status_code == 400


def test_get_content_guard_out_of_prefix():
    with pytest.raises(AppError) as e:
        input_service.get_input_content("videos/x.json")
    assert e.value.status_code == 404


def test_get_content_missing_404(monkeypatch):
    monkeypatch.setattr(s3_client, "get_object_text", lambda k: None)
    with pytest.raises(AppError) as e:
        input_service.get_input_content("inputs/MP/SIRMOUR/2026-07-17/Enercast_Data/a.csv")
    assert e.value.status_code == 404
