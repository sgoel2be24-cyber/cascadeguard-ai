/* CascadeGuard AI — live dashboard client */

const graphCanvas = document.getElementById("graph");
const gtx = graphCanvas.getContext("2d");
const gaugeCanvas = document.getElementById("riskGauge");
const ggtx = gaugeCanvas.getContext("2d");
const tooltip = document.getElementById("tooltip");

let state = null;          // latest server snapshot
let nodePos = {};          // service -> {x, y}
let animFrame = 0;
let totalLogs = 0;

const STATE_COLORS = {
  healthy: "#2ecc71",
  degraded: "#f5a623",
  critical: "#ff4d5e",
  failed: "#b8002e",
};

// ---------------------------------------------------------------- websocket

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (ev) => {
    state = JSON.parse(ev.data);
    renderSidePanels();
    renderLogs();
    renderHeader();
  };
  ws.onclose = () => setTimeout(connect, 1500);
}
connect();

// ---------------------------------------------------------------- graph layout

function computeLayout() {
  if (!state) return;
  const services = state.services;
  const w = graphCanvas.width, h = graphCanvas.height;
  const byLayer = {};
  for (const [name, s] of Object.entries(services)) {
    (byLayer[s.layer] = byLayer[s.layer] || []).push(name);
  }
  const layers = Object.keys(byLayer).map(Number).sort((a, b) => b - a);
  const maxLayer = Math.max(...layers);
  nodePos = {};
  for (const layer of layers) {
    const names = byLayer[layer].sort();
    const x = 90 + ((maxLayer - layer) / Math.max(1, maxLayer)) * (w - 200);
    names.forEach((n, i) => {
      const y = 50 + ((i + 0.5) / names.length) * (h - 100);
      nodePos[n] = { x, y };
    });
  }
}

function resizeGraph() {
  const r = graphCanvas.getBoundingClientRect();
  graphCanvas.width = r.width * devicePixelRatio;
  graphCanvas.height = r.height * devicePixelRatio;
  gtx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  graphCanvas.width = r.width;
  graphCanvas.height = r.height;
  computeLayout();
}
window.addEventListener("resize", resizeGraph);

// ---------------------------------------------------------------- graph render

function drawGraph() {
  animFrame++;
  const w = graphCanvas.width, h = graphCanvas.height;
  gtx.clearRect(0, 0, w, h);
  if (!state) { requestAnimationFrame(drawGraph); return; }
  if (!Object.keys(nodePos).length) computeLayout();

  const services = state.services;
  const analysis = state.analysis;
  const risk = analysis.risk || {};
  const cascadePath = new Set(analysis.cascade_path || []);
  const predicted = new Set((analysis.predictions || []).map(p => p.service));
  const pulse = (Math.sin(animFrame / 12) + 1) / 2;   // 0..1

  // edges
  for (const [name, s] of Object.entries(services)) {
    for (const dep of s.deps) {
      const a = nodePos[name], b = nodePos[dep];
      if (!a || !b) continue;
      const depRisk = risk[dep] || 0;
      const inCascade = cascadePath.has(name) && cascadePath.has(dep);
      gtx.strokeStyle = inCascade
        ? `rgba(255,77,94,${0.5 + pulse * 0.5})`
        : depRisk > 0.4
          ? `rgba(245,166,35,${0.3 + depRisk * 0.4})`
          : "rgba(60,80,110,.45)";
      gtx.lineWidth = inCascade ? 2.5 : 1.2;
      gtx.beginPath();
      gtx.moveTo(a.x, a.y);
      const mx = (a.x + b.x) / 2;
      gtx.bezierCurveTo(mx, a.y, mx, b.y, b.x, b.y);
      gtx.stroke();

      // animated packet flowing toward dependency when risk high
      if (depRisk > 0.35) {
        const t = (animFrame % 60) / 60;
        const x = cubic(a.x, mx, mx, b.x, t);
        const y = cubic(a.y, a.y, b.y, b.y, t);
        gtx.fillStyle = `rgba(255,77,94,${depRisk})`;
        gtx.beginPath();
        gtx.arc(x, y, 2.5, 0, Math.PI * 2);
        gtx.fill();
      }
    }
  }

  // nodes
  for (const [name, s] of Object.entries(services)) {
    const p = nodePos[name];
    if (!p) continue;
    const r = risk[name] || 0;
    const color = STATE_COLORS[s.state];
    const radius = 15 + r * 7;

    // predicted-at-risk amber ring
    if (predicted.has(name) && s.state !== "failed") {
      gtx.strokeStyle = `rgba(245,166,35,${0.4 + pulse * 0.6})`;
      gtx.lineWidth = 2;
      gtx.beginPath();
      gtx.arc(p.x, p.y, radius + 6 + pulse * 3, 0, Math.PI * 2);
      gtx.stroke();
    }

    // glow
    const grad = gtx.createRadialGradient(p.x, p.y, 2, p.x, p.y, radius * 2.2);
    grad.addColorStop(0, color + "55");
    grad.addColorStop(1, "transparent");
    gtx.fillStyle = grad;
    gtx.beginPath();
    gtx.arc(p.x, p.y, radius * 2.2, 0, Math.PI * 2);
    gtx.fill();

    // body
    gtx.fillStyle = "#111722";
    gtx.strokeStyle = color;
    gtx.lineWidth = 2.5;
    gtx.beginPath();
    gtx.arc(p.x, p.y, radius, 0, Math.PI * 2);
    gtx.fill();
    gtx.stroke();

    // inner health arc
    gtx.strokeStyle = color;
    gtx.lineWidth = 3;
    gtx.beginPath();
    gtx.arc(p.x, p.y, radius - 5, -Math.PI / 2,
            -Math.PI / 2 + Math.PI * 2 * s.health);
    gtx.stroke();

    // labels
    gtx.fillStyle = "#dbe4f0";
    gtx.font = "11px Menlo, monospace";
    gtx.textAlign = "center";
    gtx.fillText(name, p.x, p.y + radius + 15);
    gtx.fillStyle = "#7a8aa0";
    gtx.font = "9px Menlo, monospace";
    gtx.fillText(`${(s.error_rate * 100).toFixed(0)}% err · ${s.latency.toFixed(0)}ms`,
                 p.x, p.y + radius + 27);
  }

  requestAnimationFrame(drawGraph);
}

function cubic(a, b, c, d, t) {
  const mt = 1 - t;
  return mt * mt * mt * a + 3 * mt * mt * t * b + 3 * mt * t * t * c + t * t * t * d;
}

// ---------------------------------------------------------------- interactions

graphCanvas.addEventListener("click", (ev) => {
  const name = pickNode(ev);
  if (name) fetch("/api/chaos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ service: name }),
  });
});

graphCanvas.addEventListener("mousemove", (ev) => {
  const name = pickNode(ev);
  if (!name || !state) { tooltip.style.display = "none"; return; }
  const s = state.services[name];
  const r = (state.analysis.risk || {})[name] || 0;
  tooltip.innerHTML = `
    <h4>${name}</h4>
    <div class="tt-row"><span>state</span><b>${s.state}</b></div>
    <div class="tt-row"><span>health</span><b>${(s.health * 100).toFixed(0)}%</b></div>
    <div class="tt-row"><span>cascade risk</span><b>${(r * 100).toFixed(0)}%</b></div>
    <div class="tt-row"><span>latency</span><b>${s.latency.toFixed(0)} ms</b></div>
    <div class="tt-row"><span>error rate</span><b>${(s.error_rate * 100).toFixed(1)}%</b></div>
    <div class="tt-row"><span>cpu / mem</span><b>${s.cpu.toFixed(0)}% / ${s.mem.toFixed(0)}%</b></div>`;
  const rect = graphCanvas.getBoundingClientRect();
  tooltip.style.display = "block";
  tooltip.style.left = (ev.clientX - rect.left + 18) + "px";
  tooltip.style.top = (ev.clientY - rect.top - 10) + "px";
});
graphCanvas.addEventListener("mouseleave", () => tooltip.style.display = "none");

function pickNode(ev) {
  const rect = graphCanvas.getBoundingClientRect();
  const x = ev.clientX - rect.left, y = ev.clientY - rect.top;
  for (const [name, p] of Object.entries(nodePos)) {
    if (Math.hypot(p.x - x, p.y - y) < 26) return name;
  }
  return null;
}

// ---------------------------------------------------------------- side panels

function renderSidePanels() {
  const a = state.analysis;

  // root cause
  const rca = document.getElementById("rcaBody");
  if (a.root_cause) {
    const rc = a.root_cause;
    rca.innerHTML = `
      <div class="rc-service">⚠ ${rc.service}</div>
      <div class="conf-bar"><div class="conf-fill" style="width:${rc.confidence * 100}%"></div></div>
      <div class="conf-label">confidence ${(rc.confidence * 100).toFixed(0)}%</div>
      <ul class="evidence">${rc.evidence.map(e => `<li>${e}</li>`).join("")}</ul>
      <div class="affected">cascade path: <b>${a.cascade_path.join(" → ") || "—"}</b></div>`;
  } else {
    rca.innerHTML = `<div class="empty">No anomalies detected. System nominal.</div>`;
  }

  // predictions
  const pred = document.getElementById("predBody");
  if (a.predictions && a.predictions.length) {
    pred.innerHTML = a.predictions.map(p => {
      const pct = Math.round(p.risk * 100);
      const col = pct > 70 ? "var(--red)" : pct > 40 ? "var(--amber)" : "var(--green)";
      const eta = p.eta_ticks ? p.eta_label : "upstream";
      return `<div class="pred-row">
        <span class="pred-name">${p.service}</span>
        <div class="risk-bar"><div class="risk-fill" style="width:${pct}%;background:${col}"></div></div>
        <span class="pred-eta">${p.state === "failed" ? "FAILED" : "ETA " + eta}</span>
      </div>`;
    }).join("");
  } else {
    pred.innerHTML = `<div class="empty">No services at risk.</div>`;
  }

  // recommendations
  const rec = document.getElementById("recBody");
  if (a.recommendations && a.recommendations.length && a.root_cause) {
    rec.innerHTML = a.recommendations.map((r, i) => `
      <div class="rec-row ${i === 0 ? "best" : ""}">
        <span class="rec-name">${r.strategy.replace("_", " ")}${i === 0 ? '<span class="tag">BEST</span>' : ""}</span>
        <span class="rec-desc">${r.desc}<br>−${r.risk_reduction.toFixed(1)} risk · ${r.downtime_s}s downtime</span>
        <span class="rec-score">${r.score.toFixed(2)}</span>
        <button onclick="applyFix('${a.root_cause.service}', '${r.strategy}')">Apply</button>
      </div>`).join("");
  } else {
    rec.innerHTML = `<div class="empty">Awaiting incident…</div>`;
  }
}

function applyFix(service, strategy) {
  fetch("/api/fix", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ service, strategy }),
  });
}

// ---------------------------------------------------------------- logs

function renderLogs() {
  const el = document.getElementById("logs");
  totalLogs += 2;
  document.getElementById("logCount").textContent = `${state.logs.length} buffered`;
  el.innerHTML = state.logs.slice().reverse().map(l =>
    `<div class="log-line"><span class="log-ts">${l.ts}</span> ` +
    `<span class="log-${l.level}">[${l.level}]</span> ` +
    `<span class="log-svc">${l.service}:</span> ${l.msg}</div>`
  ).join("");
}

// ---------------------------------------------------------------- header

function renderHeader() {
  const pill = document.getElementById("statusPill");
  const services = Object.values(state.services);
  const failed = services.filter(s => s.state === "failed").length;
  const bad = services.filter(s => s.state === "critical" || s.state === "degraded").length;
  const sysRisk = state.analysis.system_risk / services.length;

  let cls, label;
  if (failed > 0 || sysRisk > 0.45)      { cls = "status-critical"; label = "CASCADE IN PROGRESS"; }
  else if (bad > 0 || sysRisk > 0.2)     { cls = "status-degraded"; label = "ANOMALY DETECTED"; }
  else                                   { cls = "status-healthy";  label = "SYSTEM HEALTHY"; }
  pill.className = "status-pill " + cls;
  pill.textContent = label;
  document.getElementById("tickLabel").textContent = `tick ${state.tick}`;

  // gauge
  const w = gaugeCanvas.width, h = gaugeCanvas.height;
  ggtx.clearRect(0, 0, w, h);
  const pct = Math.min(1, sysRisk);
  ggtx.fillStyle = "#161e2c";
  ggtx.beginPath();
  ggtx.roundRect(0, 10, w, 14, 7);
  ggtx.fill();
  const grad = ggtx.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0, "#2ecc71");
  grad.addColorStop(0.5, "#f5a623");
  grad.addColorStop(1, "#ff4d5e");
  ggtx.fillStyle = grad;
  ggtx.beginPath();
  ggtx.roundRect(0, 10, Math.max(8, w * pct), 14, 7);
  ggtx.fill();
  ggtx.fillStyle = "#dbe4f0";
  ggtx.font = "bold 13px Menlo, monospace";
  ggtx.textAlign = "left";
  ggtx.fillText((pct * 100).toFixed(0) + "%", 4, 8);
}

// ---------------------------------------------------------------- buttons

document.getElementById("chaosBtn").onclick = () =>
  fetch("/api/chaos", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });

document.getElementById("resetBtn").onclick = () =>
  fetch("/api/reset", { method: "POST" });

document.getElementById("autoFixBtn").onclick = () => {
  if (!state || !state.analysis.root_cause || !state.analysis.recommendations.length) return;
  const best = state.analysis.recommendations[0];
  applyFix(state.analysis.root_cause.service, best.strategy);
};

resizeGraph();
requestAnimationFrame(drawGraph);
