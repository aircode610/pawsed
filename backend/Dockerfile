FROM python:3.11-slim

# System deps required by MediaPipe + OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libgles2-mesa \
    libegl1-mesa \
    libgbm1 \
    libgomp1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download MediaPipe face landmarker model (~3 MB)
RUN mkdir -p /app/models && \
    curl -fsSL -o /app/models/face_landmarker.task \
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"

# Copy application code
COPY app/ ./app/

# Persistent data lives on a Railway Volume mounted at /data
RUN mkdir -p /data/sessions

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
