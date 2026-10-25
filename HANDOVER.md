# HANDOVER — ORCATHON 2026 / CascadeGuard AI

## Hackathon facts

- **Event:** ORCATHON by Dev Harbour (ORCA CODERS), free online student hackathon
- **Date:** Sunday 25 Oct 2026, 11:00 AM – 3:30 PM IST
- **Hard deadlines:** Build + deployment by 3:15 PM, submission form by 3:30 PM IST
- **Track chosen:** 01 — Software & AI: "Build an AI system that predicts cascading software failures, identifies root causes, and recommends the optimal recovery strategy before the system crashes."
- **Team:** solo — GitHub user `sgoel2be24-cyber` (gh CLI already authenticated on this machine)
- **Judging (100 pts):** Functionality 25 · Innovation 20 · Technical 20 · UI/UX 15 · Problem relevance 10 · Presentation 10
- **Rules notes:** any stack allowed; AI tools allowed (disclosed); pre-built code allowed but we used NONE — everything written from scratch 11:00 AM–12:00 PM today; submission needs: project name, live link, GitHub link, video, tools used, team details, pre-built disclosure.

## Links (put these in the submission form)

- **Live demo:** https://afford-fairy-mileage-penguin.trycloudflare.com
- **GitHub repo (public):** https://github.com/sgoel2be24-cyber/cascadeguard-ai
- **Video:** NOT YET RECORDED — script in `SUBMISSION.md`

## Project location & how to run

- **Path:** `/Users/Shikhar/cascadeguard`
- **Stack:** Python 3.9 + FastAPI + uvicorn (WebSocket) backend; zero-dependency vanilla JS + HTML5 Canvas frontend
- **Run:** `cd /Users/Shikhar/cascadeguard && venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000` → open http://localhost:8000
- **Deps:** `venv/bin/pip install -r requirements.txt` (venv already exists with everything installed)

## Currently running processes (DO NOT KILL before judging ends)

1. **uvicorn server** on port 8000 (started from `/Users/Shikhar/cascadeguard`, log: `server.log`)
2. **cloudflared quick tunnel** — binary at `/var/folders/0b/405jbks913z5sqkzhj8hrs_w0000gn/T/opencode/cloudflared`, log: `tunnel.log` in same dir. Serves https://afford-fairy-mileage-penguin.trycloudflare.com → localhost:8000. The URL changes if tunnel restarts!

### Restart procedures

```bash
# server
pkill -f "uvicorn main:app"
cd /Users/Shikhar/cascadeguard && venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &

# tunnel (NEW URL each time — must update submission form if it changes!)
cd /var/folders/0b/405jbks913z5sqkzhj8hrs_w0000gn/T/opencode
./cloudflared tunnel --url http://localhost:8000 --no-autoupdate &
grep -o "https://[a-z0-9-]*\.trycloudflare\.com" tunnel.log
```

### Git

```bash
cd /Users/Shikhar/cascadeguard
git add -A && git -c user.name="sgoel2be24-cyber" -c user.email="sgoel2be24-cyber@users.noreply.github.com" commit -m "msg" && git push
```

## Architecture (what's built)

- `simulator.py` — 17-service microservice DAG (api-gateway → auth/order/product → … → databases/cache/queue). Each tick (2s) every service emits latency/error-rate/CPU/mem metrics + realistic log lines. Failures propagate along dependency edges with gradual drag; natural recovery when deps healthy. Chaos injection (`inject_chaos`), fixes (`apply_fix` for 5 strategies), reset.
- `engine.py` — pure-Python prediction engine, no hard-coded answers:
  - `anomaly_score`: robust z-score of recent window vs baseline (error rate + latency)
  - `cascade_risk`: risk propagated through dependency graph to fixpoint
  - `predict_next_failures`: ranked at-risk services with ETA from health-decline slope
  - `root_cause`: anomalous service not explained by upstream anomalies, confidence + evidence strings
  - `recommend_strategies`: counterfactual simulation of restart/failover/scale_out/circuit_breaker/rollback; score = risk_reduction / (1 + downtime)
- `main.py` — FastAPI: `GET /` dashboard, `GET /api/state`, `WS /ws` (broadcast every 2s), `POST /api/chaos`, `POST /api/fix`, `POST /api/reset`. Background asyncio ticker advances the sim so any visitor sees a live system.
- `static/index.html` + `styles.css` + `app.js` — dark mission-control dashboard: animated dependency graph (canvas, bezier edges, cascade path pulses red, amber rings = predicted-next, node health arcs + codes, hover tooltips, click node = inject failure), incident timeline bar, system-risk gauge, RCA panel, predictions panel, ranked strategy panel with Apply buttons + BEST tag, live colored log stream.
- `README.md` — judge-facing docs · `SUBMISSION.md` — form answers + 2.5-min video script · `HANDOVER.md` — this file.

## Verified working

- Full flow: inject chaos on leaf DB → predictions populate with ETAs → cascade path lights up → RCA identifies injected service at ~97% confidence → failover ranked BEST → Apply/Auto-Remediate recovers system → timeline logs both events.
- WebSocket works through the Cloudflare tunnel (wss://).
- Multi-client safe (shared ticker).

## What's left (in priority order)

1. **Rehearse demo** (Reset → healthy 30s → Inject Failure → narrate ~40s cascade → Auto-Remediate → recovery)
2. **Record video** ~2.5 min, QuickTime Cmd+Shift+5, follow `SUBMISSION.md` script, upload YouTube-unlisted/Drive
3. **Fill submission form** before 3:30 PM IST — all answers pre-written in `SUBMISSION.md`
4. Optional polish only if time remains — the app is feature-complete

## Caution

- The trycloudflare URL is ephemeral: machine sleep/restart or tunnel death = new URL. If it dies, restart tunnel (above) and update the form.
- Do NOT close the uvicorn/cloudflared terminal processes before results.
