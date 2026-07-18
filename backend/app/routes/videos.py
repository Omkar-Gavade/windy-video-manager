"""HTTP routes for video operations.

Routes are thin: they parse the request, call the service, and wrap the result
in the standard success envelope. Errors raised as ``AppError`` are converted
to error envelopes by the handlers registered in ``app.main``.
"""

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.services import video_service
from app.utils.responses import success

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("")
def list_videos(
    state: str | None = Query(None),
    plant: str | None = Query(None),
    recording_date: str | None = Query(None),
) -> dict:
    """Return videos in the configured bucket/prefix, optionally filtered.

    All filters are optional; omitting them returns everything (including
    legacy objects).
    """
    return success(video_service.list_videos(state, plant, recording_date))


@router.get("/states")
def list_states() -> dict:
    """Return the States present in the bucket (dynamic, from S3)."""
    return success(video_service.list_states())


@router.get("/plants")
def list_plants(state: str = Query(..., min_length=1)) -> dict:
    """Return the Plants present for a given State (dynamic, from S3)."""
    return success(video_service.list_plants(state))


@router.post("/upload")
def upload_video(
    file: UploadFile = File(...),
    state: str | None = Form(None),
    plant: str | None = Form(None),
    recording_date: str | None = Form(None),
    recording_time: str | None = Form(None),
) -> dict:
    """Validate and upload a single video to S3.

    With ``state`` / ``plant`` / ``recording_date`` the object is stored under
    the structured key ``<State>/<Plant>/<Date>/<plant>_YYMMDD_HH_MM.mp4`` with
    a metadata JSON sidecar; without them it uses the flat legacy layout.
    """
    result = video_service.upload_video(
        file.filename, file.content_type, file.file,
        state, plant, recording_date, recording_time,
    )
    return success(result)


@router.get("/preview")
def preview_video(key: str = Query(..., min_length=1)) -> dict:
    """Return a presigned URL to stream the video inline (no download)."""
    return success(video_service.get_preview_url(key))


@router.get("/download")
def download_video(key: str = Query(..., min_length=1)) -> dict:
    """Return a presigned URL to download the original video file."""
    return success(video_service.get_download_url(key))
