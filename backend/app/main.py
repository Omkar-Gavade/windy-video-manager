"""FastAPI application entrypoint.

Milestone 1 scope: application bootstrap, CORS, and health endpoints only.
Feature routes (upload / list / preview / download) are added in later
milestones.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.routes import inputs, videos
from app.utils.responses import AppError, error, success

settings = get_settings()

app = FastAPI(
    title="S3 Video Manager",
    description="Internal tool to upload, list, preview, and download videos in AWS S3.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(videos.router)
app.include_router(inputs.router)


@app.exception_handler(AppError)
def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    """Render domain errors as the standard error envelope."""
    return JSONResponse(status_code=exc.status_code, content=error(exc.message))


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
    """Render request-validation failures without leaking internals."""
    return JSONResponse(status_code=422, content=error("Invalid request."))


@app.exception_handler(Exception)
def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
    """Catch-all so stack traces never reach the client."""
    return JSONResponse(status_code=500, content=error("An unexpected error occurred."))


@app.get("/health", tags=["health"])
def health() -> dict:
    """Liveness probe. Confirms the process is up. No external calls."""
    return success({"status": "ok"})
