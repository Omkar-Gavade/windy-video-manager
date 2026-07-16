"""Application configuration loaded from environment variables.

No secrets or environment-specific values are hardcoded here. All values
come from the process environment (optionally seeded by a local .env file).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application settings.

    AWS credentials are intentionally NOT declared here. The backend relies on
    the standard boto3 credential provider chain (IAM role in production,
    environment / shared config locally), so credentials never pass through
    application code.
    """

    # --- AWS / S3 ---
    aws_region: str
    s3_bucket: str
    s3_prefix: str = "videos/"
    documents_prefix: str = "documents/"

    # --- Upload constraints ---
    max_upload_mb: int = 200
    allowed_video_mime: str = "video/mp4,video/webm,video/quicktime"
    allowed_document_mime: str = (
        "application/pdf,"
        "application/msword,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.ms-excel,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "text/csv,"
        "text/plain"
    )
    allowed_document_extensions: str = ".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"

    # --- Presigned URL expiry (seconds) ---
    preview_expiry_seconds: int = 300
    download_expiry_seconds: int = 600

    # --- CORS ---
    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        """CORS origins as a list (env holds a comma-separated string)."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def allowed_video_mime_set(self) -> set[str]:
        """Allowed video upload MIME types as a set."""
        return {mime.strip() for mime in self.allowed_video_mime.split(",") if mime.strip()}

    @property
    def allowed_document_mime_set(self) -> set[str]:
        """Allowed document upload MIME types as a set."""
        return {mime.strip() for mime in self.allowed_document_mime.split(",") if mime.strip()}

    @property
    def allowed_document_extension_set(self) -> set[str]:
        """Allowed document file extensions as a lowercase set (with leading dot)."""
        return {
            ext.strip().lower()
            for ext in self.allowed_document_extensions.split(",")
            if ext.strip()
        }


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env once per process)."""
    return Settings()
