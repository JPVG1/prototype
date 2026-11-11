"""
FastAPI Server for Real-Time Streaming Events - Orchestration
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.stream_manager import StreamOrchestrator


class NotificationSettingsPayload(BaseModel):
    notify_yellow: bool = False
    notify_red: bool = True


class TimeSnapshotPayload(BaseModel):
    time_id: str


app = FastAPI(
    title="Real-Time Streaming Events - Orchestration",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = StreamOrchestrator()

FRONTEND_DIR = Path(__file__).parent / "frontend"


@app.get("/api/state")
def get_state(time_id: Optional[str] = Query(default=None)) -> dict:
    return orchestrator.get_full_state(time_id=time_id)


@app.post("/api/time")
def update_time_snapshot(payload: TimeSnapshotPayload) -> dict:
    return orchestrator.set_time_snapshot(payload.time_id)


@app.post("/api/settings")
def update_settings(payload: NotificationSettingsPayload) -> dict:
    return orchestrator.update_settings(
        notify_yellow=payload.notify_yellow,
        notify_red=payload.notify_red,
    )


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
