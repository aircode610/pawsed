"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database — on Railway set DB_PATH=/data/pawsed.db
    db_path: str = "pawsed.db"

    # Storage — on Railway set SESSIONS_DIR=/data/sessions
    sessions_dir: str = "sessions"

    # MediaPipe
    model_path: str = "models/face_landmarker.task"
    processing_fps: int = 5
    max_workers: int = 2  # parallel video processing workers — keep low on RAM-constrained hosts

    # Claude API
    anthropic_api_key: str = ""

    # Upload limits
    max_upload_mb: int = 300

    # JWT Auth
    jwt_secret: str = "pawsed-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72  # 3 days

    # CORS — comma-separated list of allowed origins
    # On Railway add your frontend URL: CORS_ORIGINS=https://pawsed-frontend.up.railway.app
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080,http://localhost:4173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
