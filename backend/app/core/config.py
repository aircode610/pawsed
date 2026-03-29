"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    db_path: str = "pawsed.db"

    # Storage (videos still on disk)
    sessions_dir: str = "sessions"

    # MediaPipe
    model_path: str = "models/face_landmarker.task"
    processing_fps: int = 5

    # Claude API
    anthropic_api_key: str = ""

    # Upload limits
    max_upload_mb: int = 300

    # JWT Auth
    jwt_secret: str = "pawsed-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72  # 3 days

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
