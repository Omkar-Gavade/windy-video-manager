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


@router.post("/upload")
def upload_video(
    file: UploadFile = File(...),
    state: str | None = Form(None),
    plant: str | None = Form(None),
    recording_date: str | None = Form(None),
) -> dict:
    """Validate and upload a single video to S3.

    Optional ``state`` / ``plant`` / ``recording_date`` organize the object
    under a structured key; omitting them stores it in the flat legacy layout.
    """
    result = video_service.upload_video(
        file.filename, file.content_type, file.file, state, plant, recording_date
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
