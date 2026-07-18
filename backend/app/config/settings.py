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
    inputs_prefix: str = "inputs/"

    # --- Upload constraints ---
    max_upload_mb: int = 200
    allowed_video_mime: str = "video/mp4,video/webm,video/quicktime"
    # Inputs — extension allowlists per category (lenient, extension-based).
    allowed_data_extensions: str = ".csv,.txt,.json,.xlsx,.xls,.pdf,.dat"
    allowed_input_video_extensions: str = ".mp4,.webm,.mov"
    allowed_input_image_extensions: str = ".png,.jpg,.jpeg,.gif,.webp,.bmp"

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

    @staticmethod
    def _ext_set(value: str) -> set[str]:
        return {ext.strip().lower() for ext in value.split(",") if ext.strip()}

    @property
    def allowed_data_extension_set(self) -> set[str]:
        """Extensions allowed for data categories (Site Details / Enercast / Metered)."""
        return self._ext_set(self.allowed_data_extensions)

    @property
    def allowed_input_video_extension_set(self) -> set[str]:
        """Extensions allowed for WP > Videos."""
        return self._ext_set(self.allowed_input_video_extensions)

    @property
    def allowed_input_image_extension_set(self) -> set[str]:
        """Extensions allowed for WP > Images."""
        return self._ext_set(self.allowed_input_image_extensions)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env once per process)."""
    return Settings()
