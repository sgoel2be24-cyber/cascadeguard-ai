"""CascadeGuard AI — FastAPI backend.

Serves the dashboard and streams live simulation + analysis over WebSocket.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from pydantic import BaseModel

from simulator import Simulator
import engine

app = FastAPI(title="CascadeGuard AI")
sim = Simulator()

TICK_SECONDS = 2.0


class ChaosRequest(BaseModel):
    service: Optional[str] = None


class FixRequest(BaseModel):
    service: str
    strategy: str


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/state")
async def state():
    return JSONResponse({**sim.snapshot(), "analysis": engine.analyze(sim)})


@app.post("/api/chaos")
async def chaos(req: ChaosRequest):
    svc = sim.inject_chaos(req.service)
    return {"injected": svc}


@app.post("/api/fix")
async def fix(req: FixRequest):
    sim.apply_fix(req.service, req.strategy)
    return {"ok": True}


@app.post("/api/reset")
async def reset():
    sim.reset()
    return {"ok": True}


async def ticker():
    """Single background simulation loop — all clients share one world."""
    while True:
        sim.tick()
        await asyncio.sleep(TICK_SECONDS)


@app.on_event("startup")
async def startup():
    asyncio.create_task(ticker())


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = {**sim.snapshot(), "analysis": engine.analyze(sim)}
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(TICK_SECONDS)
    except (WebSocketDisconnect, RuntimeError):
        pass


app.mount("/static", StaticFiles(directory="static"), name="static")
