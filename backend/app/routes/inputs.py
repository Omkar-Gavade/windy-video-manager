"""HTTP routes for input operations.

Thin routes: parse request, call the service, wrap in the standard envelope.
Errors raised as ``AppError`` are converted centrally in ``app.main``.
"""

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.services import input_service
from app.utils.responses import success

router = APIRouter(prefix="/api/inputs", tags=["inputs"])


@router.get("")
def list_inputs(
    state: str | None = Query(None),
    plant: str | None = Query(None),
    input_date: str | None = Query(None),
    category: str | None = Query(None),
    wp_type: str | None = Query(None),
) -> dict:
    """Return inputs in the configured bucket/prefix, optionally filtered."""
    return success(
        input_service.list_inputs(state, plant, input_date, category, wp_type)
    )


@router.post("/upload")
def upload_input(
    file: UploadFile = File(...),
    state: str | None = Form(None),
    plant: str | None = Form(None),
    input_date: str | None = Form(None),
    input_time: str | None = Form(None),
    category: str | None = Form(None),
    wp_type: str | None = Form(None),
    sub_category: str | None = Form(None),
) -> dict:
    """Validate and upload a single input asset to S3 under the category path."""
    result = input_service.upload_input(
        file.filename, file.content_type, file.file,
        state, plant, input_date, input_time, category, wp_type, sub_category,
    )
    return success(result)


@router.get("/states")
def list_states() -> dict:
    """Return the States present under the inputs prefix (dynamic, from S3)."""
    return success(input_service.list_states())


@router.get("/plants")
def list_plants(state: str = Query(..., min_length=1)) -> dict:
    """Return the Plants present for a given State (dynamic, from S3)."""
    return success(input_service.list_plants(state))


@router.get("/content")
def input_content(key: str = Query(..., min_length=1)) -> dict:
    """Return the text body of a JSON/CSV/TXT input for inline preview."""
    return success(input_service.get_input_content(key))


@router.get("/preview")
def preview_input(key: str = Query(..., min_length=1)) -> dict:
    """Return a presigned URL to preview the input inline."""
    return success(input_service.get_preview_url(key))


@router.get("/download")
def download_input(key: str = Query(..., min_length=1)) -> dict:
    """Return a presigned URL to download the original input file."""
    return success(input_service.get_download_url(key))
