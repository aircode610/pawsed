"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.sessions import router as sessions_router
from app.api.routes.insights import router as insights_router
from app.api.routes.websocket import router as ws_router

app = FastAPI(title="Pawsed API", version="0.1.0")

# Allow requests from the frontend dev server (any common port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)
app.include_router(insights_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
