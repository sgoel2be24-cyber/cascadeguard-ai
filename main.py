"""CascadeGuard AI: shared synthetic incident sandbox and explainable analysis."""
import asyncio
import json
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import engine
from simulator import Simulator, TOPOLOGY

ROOT = Path(__file__).resolve().parent
sim = Simulator(seed=42)
cached = None


def payload():
    global cached
    if cached is None:
        cached = {**sim.snapshot(), 'analysis': engine.analyze(sim), 'mode':'synthetic', 'tick_seconds':2}
    return cached


def invalidate():
    global cached
    cached = None


async def ticker():
    while True:
        sim.tick()
        invalidate()
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(ticker())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title='CascadeGuard AI', version='2.0.0', lifespan=lifespan)


class ChaosRequest(BaseModel):
    service: Optional[str] = None


class FixRequest(BaseModel):
    service: str
    strategy: str


class ScenarioRequest(BaseModel):
    scenario: str = 'payment'


def check_service(service):
    if service not in TOPOLOGY:
        raise HTTPException(422, 'Unknown service')


@app.get('/')
async def index():
    return FileResponse(ROOT / 'static/index.html', headers={'Cache-Control':'no-cache'})


@app.get('/healthz')
async def health():
    return {'status':'ok','mode':'synthetic','services':len(TOPOLOGY),'tick':sim.tick_no}


@app.get('/api/state')
async def state():
    return JSONResponse(payload())


@app.get('/api/report')
async def report():
    return JSONResponse({'project':'CascadeGuard AI', 'disclosure':'Shared synthetic sandbox; heuristic estimates, not production guarantees.', **payload()},
                        headers={'Content-Disposition':'attachment; filename="cascadeguard-incident.json"'})


@app.post('/api/chaos')
async def chaos(req: ChaosRequest):
    if req.service is not None:
        check_service(req.service)
    svc = sim.inject_chaos(req.service)
    invalidate()
    return {'injected':svc}


@app.post('/api/fix')
async def fix(req: FixRequest):
    check_service(req.service)
    if req.strategy not in engine.STRATEGIES:
        raise HTTPException(422, 'Unknown recovery strategy')
    sim.apply_fix(req.service, req.strategy)
    invalidate()
    return {'ok':True}


@app.post('/api/reset')
async def reset():
    sim.reset(seed=42)
    invalidate()
    return {'ok':True}


@app.post('/api/scenario')
async def scenario(req: ScenarioRequest):
    targets = {'payment':'payment-db', 'cache':'redis-cache', 'search':'elastic-cluster'}
    if req.scenario not in targets:
        raise HTTPException(422, 'Unknown scenario')
    sim.reset(seed=42)
    target = targets[req.scenario]
    sim.inject_chaos(target, severity=.13)
    invalidate()
    return {'ok':True,'target':target}


@app.websocket('/ws')
async def ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(json.dumps(payload()))
            await asyncio.sleep(2)
    except (WebSocketDisconnect, RuntimeError):
        pass


app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')
