"""CascadeGuard AI: an explainable shared synthetic incident sandbox."""

import asyncio
import json
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from time import monotonic
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from runtime import Runtime

ROOT = Path(__file__).resolve().parent
runtime = Runtime()


async def ticker():
    deadline = monotonic() + 2
    playback = None
    while True:
        await asyncio.sleep(0.1)
        now = monotonic()
        current = (runtime.world_id, runtime.paused, runtime.speed)
        if current != playback:
            playback = current
            deadline = now + 2 / runtime.speed
        if runtime.paused:
            continue
        if now >= deadline:
            runtime.advance()
            deadline = monotonic() + 2 / runtime.speed


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(ticker())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="CascadeGuard AI", version="3.0.0", lifespan=lifespan)


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChaosRequest(RequestModel):
    service: Optional[str] = None


class FixRequest(RequestModel):
    service: str
    strategy: str


class ScenarioRequest(RequestModel):
    scenario: Literal["payment", "cache", "search"] = "payment"


class ControlRequest(RequestModel):
    paused: Optional[bool] = None
    speed: Optional[Literal[1, 2, 4]] = None


def execute(callback):
    try:
        return callback()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/")
async def index():
    return FileResponse(
        ROOT / "static/index.html", headers={"Cache-Control": "no-cache"}
    )


@app.get("/healthz")
async def health():
    return {
        "status": "ok",
        "mode": "synthetic",
        "services": len(runtime.sim.services),
        "tick": runtime.sim.tick_no,
        "paused": runtime.paused,
        "speed": runtime.speed,
    }


@app.get("/api/state")
async def state():
    return JSONResponse(runtime.state())


@app.get("/api/report")
async def report():
    return JSONResponse(
        {
            "project": "CascadeGuard AI",
            "disclosure": "Shared synthetic sandbox; heuristic estimates. Forecast consistency uses the same simulator, not independent production evidence.",
            **runtime.state(),
        },
        headers={
            "Content-Disposition": 'attachment; filename="cascadeguard-incident.json"'
        },
    )


@app.post("/api/chaos")
async def chaos(req: ChaosRequest):
    return {"injected": execute(lambda: runtime.inject(req.service))}


@app.post("/api/fix")
async def fix(req: FixRequest):
    execute(lambda: runtime.fix(req.service, req.strategy))
    return {"ok": True}


@app.post("/api/reset")
async def reset():
    runtime.reset()
    return {"ok": True}


@app.post("/api/scenario")
async def scenario(req: ScenarioRequest):
    return {"ok": True, "target": execute(lambda: runtime.scenario(req.scenario))}


@app.post("/api/control")
async def control(req: ControlRequest):
    execute(lambda: runtime.control(req.paused, req.speed))
    return {"ok": True, "paused": runtime.paused, "speed": runtime.speed}


@app.post("/api/step")
async def step():
    if not runtime.paused:
        raise HTTPException(409, "Pause the simulation before stepping")
    runtime.step()
    return {"ok": True, "tick": runtime.sim.tick_no}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    last_revision = None
    last_sent = 0.0
    try:
        while True:
            now = monotonic()
            revision = (runtime.world_id, runtime.revision)
            if revision != last_revision or now - last_sent >= 2:
                await websocket.send_text(json.dumps(runtime.state()))
                last_revision = revision
                last_sent = now
            await asyncio.sleep(0.1)
    except (WebSocketDisconnect, RuntimeError):
        pass


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
