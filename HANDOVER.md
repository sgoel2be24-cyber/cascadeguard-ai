# CascadeGuard AI — operations handover

Updated 25 October 2026 during the professional polish pass.

- Live: https://afford-fairy-mileage-penguin.trycloudflare.com
- Repository: https://github.com/sgoel2be24-cyber/cascadeguard-ai
- Checkout: `/Users/Shikhar/cascadeguard`
- Submission fields, recording script and Q&A: `SUBMISSION.md`
- Judging evidence: `JUDGING.md`; technical scope and tests: `README.md`

## Demo

Healthy dashboard → Focus view → Run scenario → narrate early forecast and suspected origin after about 6–10s → show impact chain and five strategy trials → Apply best recovery → observe gradual recovery → export incident. A scenario resets the shared sandbox. Graph clicks inspect. Scenarios: payment, cache and search.

Telemetry is synthetic. Risk, ETA and evidence strength are heuristic estimates. Do not call the model a trained classifier or claim real-world accuracy. Recovery forecasts use simulated fault state and assumed downtime costs.

## Runtime

One Uvicorn process on port 8000; Cloudflare forwards the existing tunnel URL to it. Keep the tunnel process alive: restarting it may change the URL. Keep the machine awake through judging. Only one worker: world state is shared in memory, and server restarts reset it.

```bash
cd /Users/Shikhar/cascadeguard
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

Health `/healthz`; OpenAPI `/docs`; current state `/api/state`; JSON export `/api/report`; WebSocket `/ws`.

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --check static/app.js
```

Twenty engine/runtime tests passed locally, including 51 seeded origin cases. The expanded 81-check API/WebSocket run passed on the isolated preview. GitHub Actions runs engine and JS checks. Optional `venv/bin/python tests/smoke_api.py http://127.0.0.1:8001` mutates/resets the target sandbox; use a disposable preview.

## Remaining

Record the final actual-app video, upload with judge-accessible permissions, fill the video URL and registered participant details, verify the prior-work timeline, submit and save confirmation. Disclose OpenCode (initial build per handover) and OpenAI Codex (polish).

Deadline conflict: Unstop submission stage says 4:30 PM IST; description/process says 3:15 build and 3:30 final submission. Keep earlier targets unless organizers confirm an extension.

## Second-pass operator workflow

Pause to hold a diagnosis frame, use Step +2s to explain causal propagation, and resume at 4× to show recovery quickly. Scenarios preserve pause/speed; Reset returns to live 1× and clears the incident journal. Telemetry trends exclude seeded reference samples. What if compares strategy trajectories; Applied action retains a fix forecast and overlays observed risk. The incident evidence panel records inferred origin and actual synthetic outcomes. Export before resetting. Runtime logic lives in runtime.py; the interface chart module is static/insights.js.
