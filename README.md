# CascadeGuard AI

**Predict cascading software failures before they happen — trace the root cause, and apply the optimal recovery strategy.**

Built for **ORCATHON 2026** (Track 01 — Software & AI) by [@sgoel2be24-cyber](https://github.com/sgoel2be24-cyber).

---

## The Problem

In modern distributed systems, one failing component quietly takes down everything that depends on it. By the time alerts fire, the cascade has already happened. Teams react *after* the crash.

## The Solution

CascadeGuard AI watches a live microservice topology and:

1. **Detects anomalies** per service using robust z-score analysis on streaming error-rate and latency metrics.
2. **Predicts cascading failures** by propagating risk through the dependency graph to a fixpoint — flagging which services will fail *next*, with an estimated time-to-failure.
3. **Traces the root cause** — the earliest anomalous service that explains all downstream failures, with confidence scoring and evidence.
4. **Recommends the optimal recovery strategy** by simulating counterfactuals: every strategy (restart, failover, scale-out, circuit breaker, rollback) is scored by projected system-risk reduction vs. downtime cost.
5. **Live mission-control dashboard** — dependency graph with animated cascade propagation, streaming logs, risk gauge, and one-click remediation.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Dashboard (Canvas + vanilla JS, WebSocket)     │
└──────────────▲──────────────────────────────────┘
               │ live state every 2s
┌──────────────┴──────────────────────────────────┐
│  FastAPI backend (main.py)                      │
│  ┌────────────────┐   ┌───────────────────────┐ │
│  │ Simulator      │──▶│ Prediction Engine     │ │
│  │ (simulator.py) │   │ (engine.py)           │ │
│  │ 17-service DAG │   │ • anomaly z-scores    │ │
│  │ metric + log   │   │ • cascade fixpoint    │ │
│  │ stream, chaos  │   │ • root-cause ranking  │ │
│  │ injection      │   │ • strategy optimizer  │ │
│  └────────────────┘   └───────────────────────┘ │
└─────────────────────────────────────────────────┘
```

- **No hard-coded answers** — the engine works purely from live metric history; the same code generalizes to real telemetry.
- **Counterfactual strategy evaluation** — each recovery option is scored by re-running the cascade model with the fix applied: `score = risk_reduction / (1 + downtime_cost)`.

## Quick Start

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

## Demo Flow

1. Watch the healthy system stream logs and metrics.
2. Click **⚡ Inject Failure** (or click any node on the graph) — a fault begins degrading a service.
3. Within seconds the engine flags **predicted next failures** (amber rings) *before* they go down, highlights the **cascade path**, and names the **root cause** with evidence.
4. Open the **Recovery Strategy Optimizer** — strategies ranked by projected risk reduction per unit of downtime.
5. Click **Apply** (or **🛠 Auto-Remediate**) and watch the system recover in real time.

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3, FastAPI, WebSockets (uvicorn) |
| Prediction engine | Pure Python — statistical anomaly detection, graph risk propagation, counterfactual optimization |
| Frontend | Vanilla JS + HTML5 Canvas (zero dependencies, zero build step) |
| Dev tools | Built with AI-assisted development (disclosed per hackathon rules) |

## Disclosure

This project was created from scratch during ORCATHON 2026 (11:00 AM – 3:30 PM IST, 25 Oct 2026). No pre-built code or templates were used. AI-assisted development tools were used during the build, as permitted by the hackathon rules.

## API

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard |
| `GET /api/state` | Full snapshot + analysis |
| `WS /ws` | Live stream (tick every 2s) |
| `POST /api/chaos` | Inject a failure `{service?}` |
| `POST /api/fix` | Apply a strategy `{service, strategy}` |
| `POST /api/reset` | Reset simulation |
