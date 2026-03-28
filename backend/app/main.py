"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.sessions import router as sessions_router

app = FastAPI(title="EngageSense API", version="0.1.0")

# Allow requests from the frontend dev server and Lovable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
