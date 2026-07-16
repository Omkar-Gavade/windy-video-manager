"""HTTP routes for document operations.

Separate from the video routes (different endpoint, different service) but
follows the exact same pattern: thin routes, envelope-wrapped responses,
errors handled centrally via ``AppError``.
"""

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.services import document_service
from app.utils.responses import success

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents(
    state: str | None = Query(None),
    plant: str | None = Query(None),
    document_date: str | None = Query(None),
) -> dict:
    """Return documents in the configured bucket/prefix, optionally filtered."""
    return success(document_service.list_documents(state, plant, document_date))


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    state: str | None = Form(None),
    plant: str | None = Form(None),
    document_date: str | None = Form(None),
    document_time: str | None = Form(None),
) -> dict:
    """Validate and upload a single document to S3.

    Optional ``state`` / ``plant`` / ``document_date`` organize the object
    under a structured key; ``document_time`` (when supplied) is embedded in
    the unique filename so it can be recovered on list.
    """
    result = document_service.upload_document(
        file.filename, file.content_type, file.file, state, plant, document_date, document_time
    )
    return success(result)


@router.get("/preview")
def preview_document(key: str = Query(..., min_length=1)) -> dict:
    """Return a presigned URL to preview the document inline."""
    return success(document_service.get_preview_url(key))


@router.get("/download")
def download_document(key: str = Query(..., min_length=1)) -> dict:
    """Return a presigned URL to download the original document file."""
    return success(document_service.get_download_url(key))
