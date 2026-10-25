# ORCATHON Submission Cheat-Sheet

## Submission Form Answers

- **Project Name:** CascadeGuard AI
- **Live Project Link:** https://afford-fairy-mileage-penguin.trycloudflare.com
- **GitHub Repository:** https://github.com/sgoel2be24-cyber/cascadeguard-ai
- **Tools Used:** Python 3, FastAPI, Uvicorn (WebSockets), vanilla JavaScript + HTML5 Canvas (zero frontend dependencies), Cloudflare Tunnel (hosting), AI-assisted development (OpenCode) — disclosed per rules.
- **Pre-Built Disclosure:** No pre-built code. Entire project (simulator, prediction engine, dashboard) written from scratch during the hackathon window. AI tools were used for development assistance, as permitted.
- **Team:** sgoel2be24-cyber (solo)

## Video Script (~2.5–3 min)

**[0:00–0:20] Hook**
"In modern distributed systems, one failing database silently takes down everything that depends on it — and teams only react after the crash. CascadeGuard AI predicts the cascade *before* it happens, pinpoints the root cause, and tells you the single best recovery action."

**[0:20–0:45] Healthy system tour**
- Show the dashboard: 17-service dependency graph, live logs streaming, system risk gauge at low %.
- "Every node streams metrics — latency, error rate, CPU — just like real telemetry."

**[0:45–1:20] Inject failure → prediction**
- Click a leaf node (e.g. **payment-db**) or the Inject Failure button.
- Narrate as it unfolds: "Within seconds the engine's anomaly detection fires… watch the amber ring — it's predicting payment-service will fail in ~30 seconds, before a single alert has fired. The cascade path lights up in red: payment-db → payment-service → order-service → api-gateway."

**[1:20–1:50] Root cause + optimizer**
- "Root cause analysis: payment-db, 97% confidence, with evidence — CPU saturated, memory pressure. Not the gateway, not the API — the database."
- "Now the recovery optimizer: it simulates every strategy as a counterfactual — restart, failover, scale-out, circuit breaker, rollback — and scores each by risk reduction per second of downtime. Failover wins."

**[1:50–2:20] Remediate live**
- Click **Auto-Remediate**. Nodes go green, gauge drops, timeline logs the fix.
- "System recovered — and the incident timeline has the full audit trail."

**[2:20–2:40] Close**
- "Pure Python prediction engine, FastAPI + WebSockets, zero-dependency canvas frontend — all built from scratch in 3 hours. CascadeGuard AI: stop the cascade before it starts."

## Recording Tips

- Full-screen the browser (hide bookmarks bar), zoom to 100%.
- Use QuickTime (Cmd+Shift+5) to record the screen.
- Do a practice run: Reset → wait healthy → inject → ~40s cascade → remediate.
- Upload to YouTube/Drive as unlisted; paste link in the form.
