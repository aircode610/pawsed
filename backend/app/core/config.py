"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Storage
    sessions_dir: str = "sessions"          # directory for JSON session files

    # MediaPipe
    model_path: str = "models/face_landmarker.task"
    processing_fps: int = 10               # frames to sample per second from video

    # Claude API
    anthropic_api_key: str = ""

    # Upload limits
    max_upload_mb: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
