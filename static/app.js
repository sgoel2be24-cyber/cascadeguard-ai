"use strict";
const $ = (id) => document.getElementById(id);
const graph = $("graph"),
  ctx = graph.getContext("2d");
const colors = {
  healthy: "#5ee7bb",
  degraded: "#eac16b",
  critical: "#fa7e8b",
  failed: "#e54c69",
};
let state = null,
  selected = "payment-db",
  positions = {},
  frame = 0,
  width = 760,
  height = 570;
let busy = false,
  paused = false,
  lastTick = -1,
  riskHistory = [],
  lastReceived = 0,
  toastTimer;
let socket,
  reconnectTimer,
  stale = false;
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const pretty = (text) => text.replaceAll("_", " ");
function toast(message, error = false) {
  const el = $("toast");
  el.textContent = message;
  el.className = "visible" + (error ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = ""), 5000);
}
function connection(text, mode) {
  $("connection").textContent = text;
  $("connection").className = "connection " + mode;
}
function buttons() {
  for (const id of ["demoBtn", "chaosBtn", "resetBtn"])
    $(id).disabled = busy || !state || stale;
  $("autoFixBtn").disabled =
    busy ||
    stale ||
    !state?.analysis.root_cause ||
    !state?.analysis.recommendations.length;
  document
    .querySelectorAll("[data-strategy]")
    .forEach((b) => (b.disabled = busy || stale));
}
async function refresh() {
  const res = await fetch("/api/state", {
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw Error("Telemetry unavailable");
  receive(await res.json());
}
async function action(path, body, message) {
  if (busy) return;
  busy = true;
  buttons();
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(12000),
    });
    if (!res.ok) {
      const d = await res.json();
      throw Error(typeof d.detail === "string" ? d.detail : "Action rejected");
    }
    if (path === "/api/reset" || path === "/api/scenario") {
      riskHistory = [];
      lastTick = -1;
    }
    await refresh();
    toast(message);
  } catch (error) {
    toast(error.message || "Connection interrupted. Try again.", true);
  } finally {
    busy = false;
    buttons();
  }
}
function receive(data) {
  state = data;
  lastReceived = Date.now();
  stale = false;
  render();
}
function connect() {
  clearTimeout(reconnectTimer);
  socket = new WebSocket(
    `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`,
  );
  socket.onopen = () => connection("Live · 2s", "live");
  socket.onmessage = (e) => {
    try {
      receive(JSON.parse(e.data));
      connection("Live · 2s", "live");
    } catch {
      toast("Unable to read telemetry frame", true);
    }
  };
  socket.onclose = () => {
    stale = true;
    connection("Reconnecting…", "offline");
    buttons();
    reconnectTimer = setTimeout(connect, 1800);
  };
  socket.onerror = () => socket.close();
}
setInterval(() => {
  if (lastReceived && Date.now() - lastReceived > 7000) {
    stale = true;
    connection("Telemetry stale", "offline");
    buttons();
  }
  if (!socket || socket.readyState !== WebSocket.OPEN)
    refresh()
      .then(() => connection("Polling · retrying live", ""))
      .catch(() => {});
}, 5000);
function layout() {
  if (!state) return;
  const layers = {};
  for (const [n, s] of Object.entries(state.services))
    (layers[s.layer] ??= []).push(n);
  const max = Math.max(...Object.keys(layers).map(Number));
  positions = {};
  for (const [l, names] of Object.entries(layers)) {
    names.sort();
    names.forEach(
      (n, i) =>
        (positions[n] = {
          x: 65 + ((max - Number(l)) / max) * (width - 210),
          y: 47 + ((i + 0.5) / names.length) * (height - 90),
        }),
    );
  }
}
function resize() {
  const rect = graph.getBoundingClientRect();
  width = rect.width;
  height = rect.height;
  const dpr = Math.min(devicePixelRatio || 1, 2);
  graph.width = Math.round(width * dpr);
  graph.height = Math.round(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  layout();
}
new ResizeObserver(resize).observe(graph);
const cubic = (a, b, c, d, t) =>
  (1 - t) ** 3 * a +
  3 * (1 - t) ** 2 * t * b +
  3 * (1 - t) * t * t * c +
  t ** 3 * d;
function draw() {
  frame++;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#28425655";
  for (let x = 15; x < width; x += 24)
    for (let y = 22; y < height; y += 24) {
      ctx.beginPath();
      ctx.arc(x, y, 0.65, 0, Math.PI * 2);
      ctx.fill();
    }
  if (state) {
    const a = state.analysis,
      risk = a.risk,
      root = a.root_cause?.service;
    const chain = new Set([root, ...a.cascade_path]);
    const predicted = new Set(a.predictions.map((p) => p.service));
    for (const [name, s] of Object.entries(state.services)) {
      for (const dep of s.deps) {
        const p = positions[name],
          q = positions[dep];
        if (!p || !q) continue;
        const hot = chain.has(name) && chain.has(dep);
        ctx.strokeStyle = state.services[dep].isolated
          ? "#70adce"
          : hot
            ? "#fa7e8b88"
            : "#34465b80";
        ctx.lineWidth = hot ? 1.6 : 1;
        ctx.setLineDash(state.services[dep].isolated ? [4, 5] : []);
        const mx = (p.x + q.x) / 2;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.bezierCurveTo(mx, p.y, mx, q.y, q.x, q.y);
        ctx.stroke();
        ctx.setLineDash([]);
        if (hot && !reducedMotion) {
          const t = 1 - (frame % 130) / 130;
          ctx.fillStyle = "#fa7e8b";
          ctx.beginPath();
          ctx.arc(
            cubic(p.x, mx, mx, q.x, t),
            cubic(p.y, p.y, q.y, q.y, t),
            2.5,
            0,
            Math.PI * 2,
          );
          ctx.fill();
        }
      }
    }
    for (const [name, s] of Object.entries(state.services)) {
      const p = positions[name];
      if (!p) continue;
      const col = colors[s.state],
        r = 15;
      const pulse = reducedMotion ? 0.5 : (Math.sin(frame / 22) + 1) / 2;
      if (predicted.has(name)) {
        ctx.strokeStyle = "#eac16b88";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 5 + pulse * 2, 0, Math.PI * 2);
        ctx.stroke();
      }
      if (name === selected) {
        ctx.strokeStyle = "#bdd9f0";
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 3]);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 25, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
      }
      ctx.shadowColor = col;
      ctx.shadowBlur = s.state === "healthy" ? 5 : 13;
      ctx.fillStyle = "#101c28";
      ctx.strokeStyle = col;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = col;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(
        p.x,
        p.y,
        r - 5,
        -Math.PI / 2,
        -Math.PI / 2 + Math.PI * 2 * s.health,
      );
      ctx.stroke();
      ctx.fillStyle = col;
      ctx.font = "8px ui-monospace,Menlo,monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const codes = {
        "api-gateway": "AG",
        "auth-service": "AU",
        "order-service": "OR",
        "product-service": "PR",
        "payment-service": "PA",
        "inventory-service": "IN",
        "search-service": "SE",
        "fraud-detector": "FD",
        "user-db": "UD",
        "order-db": "OD",
        "product-db": "PG",
        "payment-db": "PD",
        "inventory-db": "ID",
        "redis-cache": "RC",
        "elastic-cluster": "EC",
        "message-queue": "MQ",
        "ml-model-store": "ML",
      };
      ctx.fillText(codes[name], p.x, p.y);
      ctx.textBaseline = "alphabetic";
      ctx.fillStyle = name === selected ? "#fff" : "#b7c7d8";
      ctx.font = "9px ui-monospace,Menlo,monospace";
      ctx.textAlign = s.layer === 0 ? "left" : "center";
      ctx.fillText(
        name,
        s.layer === 0 ? p.x + 25 : p.x,
        s.layer === 0 ? p.y - 2 : p.y + 29,
      );
      ctx.fillStyle = "#6f859d";
      ctx.font = "8px ui-monospace,Menlo,monospace";
      ctx.fillText(
        `${Math.round(s.health * 100)}% health${s.isolated ? " · isolated" : ""}`,
        s.layer === 0 ? p.x + 25 : p.x,
        s.layer === 0 ? p.y + 12 : p.y + 41,
      );
    }
  }
  requestAnimationFrame(draw);
}
function pick(event) {
  const rect = graph.getBoundingClientRect();
  const x = event.clientX - rect.left,
    y = event.clientY - rect.top;
  return Object.keys(positions).find(
    (n) => Math.hypot(positions[n].x - x, positions[n].y - y) < 24,
  );
}
graph.addEventListener("click", (e) => {
  const n = pick(e);
  if (n) {
    selected = n;
    $("serviceSelect").value = n;
    renderInspection();
    renderLogs();
  }
});
graph.addEventListener("mousemove", (e) => {
  const n = pick(e);
  if (!n || !state) {
    $("tooltip").style.display = "none";
    return;
  }
  const s = state.services[n],
    rect = graph.getBoundingClientRect();
  $("tooltip").innerHTML =
    `<b>${esc(n)}</b><br>${esc(s.state)} · ${Math.round(s.health * 100)}% health<br>${s.latency.toFixed(0)} ms · ${(s.error_rate * 100).toFixed(1)}% errors<br>Click to inspect telemetry`;
  $("tooltip").style.display = "block";
  $("tooltip").style.left =
    Math.min(width - 240, Math.max(0, e.clientX - rect.left + 16)) + "px";
  $("tooltip").style.top =
    Math.min(height - 110, e.clientY - rect.top + 12) + "px";
});
graph.addEventListener(
  "mouseleave",
  () => ($("tooltip").style.display = "none"),
);
function renderInspection() {
  if (!state) return;
  const s = state.services[selected];
  $("inspection").innerHTML =
    `<b>${esc(selected)}</b><span style="color:${colors[s.state]}">${esc(s.state.toUpperCase())}</span>${s.isolated ? " · CIRCUIT OPEN" : ""}<br>Health <b>${Math.round(s.health * 100)}%</b> Latency <b>${s.latency.toFixed(0)} ms</b> Errors <b>${(s.error_rate * 100).toFixed(1)}%</b> CPU <b>${s.cpu.toFixed(0)}%</b> Memory <b>${s.mem.toFixed(0)}%</b>`;
}
function render() {
  const a = state.analysis,
    services = Object.values(state.services),
    rc = a.root_cause;
  const healthy = services.filter((s) => s.state === "healthy").length,
    failed = services.filter((s) => s.state === "failed").length,
    risk = (a.system_risk / services.length) * 100;
  $("healthyCount").textContent = healthy;
  $("healthDetail").textContent =
    `${services.length - healthy} affected · ${failed} failed · ${state.tick * 2}s simulated`;
  $("statusPill").textContent = failed
    ? "CASCADE ACTIVE"
    : rc
      ? "ANOMALY DETECTED"
      : "SYSTEM NOMINAL";
  $("statusPill").style.color = failed
    ? "var(--red)"
    : rc
      ? "var(--amber)"
      : "var(--green)";
  $("riskValue").textContent = risk.toFixed(0);
  $("exposureCount").textContent = a.cascade_path.length;
  $("exposureDetail").textContent = rc
    ? `Potential downstream reach from ${rc.service}`
    : "No anomalous origin detected";
  $("recoveryValue").textContent = a.recommendations.length
    ? "−" + a.recommendations[0].risk_reduction.toFixed(1)
    : "—";
  $("recoveryDetail").textContent = a.recommendations.length
    ? `40s mean risk reduction · ${pretty(a.recommendations[0].strategy)}`
    : "Compare actions when an incident is detected";
  $("tickLabel").textContent =
    `T+${String(state.tick * 2).padStart(3, "0")}s · tick ${state.tick}`;
  if (state.tick !== lastTick) {
    riskHistory.push(risk);
    riskHistory = riskHistory.slice(-35);
    lastTick = state.tick;
  }
  $("riskSpark").setAttribute(
    "points",
    riskHistory
      .map(
        (r, i) =>
          `${(i / Math.max(1, riskHistory.length - 1)) * 120},${33 - (r / 100) * 30}`,
      )
      .join(" "),
  );
  if (!$("serviceSelect").options.length) {
    $("serviceSelect").innerHTML = Object.keys(state.services)
      .sort()
      .map((n) => `<option>${esc(n)}</option>`)
      .join("");
    $("serviceSelect").value = selected;
  }
  $("rcaBody").innerHTML = rc
    ? `<div class="overline">SUSPECTED ORIGIN</div><div class="rc-service">${esc(rc.service)}</div><div class="strength"><span>Evidence strength</span><span>${Math.round(rc.confidence * 100)} / 100</span></div><div class="conf-bar"><div class="conf-fill" style="width:${rc.confidence * 100}%"></div></div><ul class="evidence">${rc.evidence.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>`
    : `<div class="empty"><div class="empty-icon">✓</div><strong>No anomalous origin detected</strong>Run a scenario to see evidence build as the dependency degrades.</div>`;
  $("predBody").innerHTML = a.predictions.length
    ? a.predictions
        .map(
          (p) =>
            `<div class="pred-row"><div class="pred-top"><span>${esc(p.service)}</span><span style="color:var(--amber)">${Math.round(p.risk * 100)} / 100</span></div><div class="risk-bar"><div class="risk-fill" style="width:${p.risk * 100}%"></div></div><div class="pred-meta"><span>${esc(p.state)}</span><span>${p.eta_ticks ? "Est. failure " + esc(p.eta_label) : "Dependency exposure"}</span></div></div>`,
        )
        .join("")
    : `<div class="empty"><strong>No imminent cascade signal</strong>Services are within the model’s normal operating range.</div>`;
  $("chainBody").innerHTML = rc
    ? a.cascade_layers
        .map(
          (layer, i) =>
            `<div class="chain-step"><span>${i ? "↑" : "●"} ${String(i).padStart(2, "0")}</span><div>${layer.map((n) => `<b>${esc(n)}</b>`).join("")}</div></div>`,
        )
        .join("")
    : `<div class="empty"><strong>Contain the blast radius</strong>The dependency graph reveals which callers could inherit the failure.</div>`;
  $("recoveryContext").innerHTML = rc
    ? `Target: <b>${esc(rc.service)}</b> · Without intervention: <b>${a.baseline_forecast.toFixed(1)} / 100</b> forecast mean operational risk. Compare the same next 40 seconds under each action.`
    : "An incident unlocks five recovery trials. Each runs the same simulator with a different action.";
  const templates = [
    ["failover", "Switch to a standby replica"],
    ["restart", "Restart unhealthy instances"],
    ["scale_out", "Add service capacity"],
    ["circuit_breaker", "Isolate a failing dependency"],
    ["rollback", "Revert the last deployment"],
  ];
  $("recBody").innerHTML = a.recommendations.length
    ? a.recommendations
        .map(
          (r, i) =>
            `<article class="strategy ${i === 0 ? "best" : ""}"><div class="strategy-top"><span>0${i + 1} / UTILITY ${r.score.toFixed(1)}</span>${i === 0 ? '<span class="badge">BEST</span>' : ""}</div><h3>${esc(pretty(r.strategy))}</h3><p>${esc(r.desc)}</p><div class="strategy-number">−${r.risk_reduction.toFixed(1)}</div><small>mean risk points vs no action</small><div class="strategy-cost">${r.downtime_s}s assumed downtime<br>Projected mean risk ${r.projected_risk.toFixed(1)} / 100</div><button class="button ${i === 0 ? "primary" : "subtle"}" data-strategy="${esc(r.strategy)}" data-target="${esc(rc.service)}">Apply ${esc(pretty(r.strategy))} ↗</button></article>`,
        )
        .join("")
    : templates
        .map(
          ([n, d], i) =>
            `<article class="strategy"><div class="strategy-top">0${i + 1} / STANDBY</div><h3>${pretty(n)}</h3><p>${d}</p><div class="strategy-number" style="color:var(--muted)">—</div><small>Awaiting an incident to evaluate</small></article>`,
        )
        .join("");
  $("eventCount").textContent = `${state.events.length} events`;
  $("tlEvents").innerHTML = state.events.length
    ? state.events
        .slice()
        .reverse()
        .map(
          (e) =>
            `<div class="tl-event ${e.type === "fix" ? "fix" : ""}"><span class="event-type">${e.type === "fix" ? "RECOVERY APPLIED" : "FAULT INJECTED"} · T+${e.tick * 2}s</span><b>${esc(e.service)}</b><br>${e.type === "fix" ? esc(pretty(e.strategy)) : "Synthetic fault · severity " + Math.round(e.severity * 100) + "%"}</div>`,
        )
        .join("")
    : `<div class="empty"><strong>A clean slate.</strong>Injected faults and recovery actions appear here as you work through an incident.</div>`;
  renderInspection();
  renderLogs();
  layout();
  buttons();
}
function renderLogs() {
  if (!state || paused) return;
  let logs = state.logs;
  const filter = $("logFilter").value;
  if (filter === "errors")
    logs = logs.filter((l) => ["ERROR", "CRITICAL"].includes(l.level));
  if (filter === "selected") logs = logs.filter((l) => l.service === selected);
  $("logCount").textContent = logs.length + " lines";
  $("logs").innerHTML = logs.length
    ? logs
        .slice()
        .reverse()
        .map(
          (l) =>
            `<div class="log-line"><span class="log-ts">${esc(l.ts)}</span> <span class="log-${esc(l.level)}">${esc(l.level.padEnd(8))}</span> <span class="log-svc">${esc(l.service)}</span> <span>${esc(l.msg)}</span></div>`,
        )
        .join("")
    : '<div class="empty">No matching log entries yet.</div>';
}
$("demoBtn").onclick = () =>
  action(
    "/api/scenario",
    { scenario: $("scenario").value },
    "Scenario started. Watch the forecast and root-cause evidence.",
  );
$("chaosBtn").onclick = () =>
  action(
    "/api/chaos",
    { service: selected },
    `Fault injected into ${selected}.`,
  );
$("resetBtn").onclick = () =>
  action(
    "/api/reset",
    {},
    "Sandbox reset. Synthetic healthy baseline restored.",
  );
$("autoFixBtn").onclick = () => {
  const a = state?.analysis;
  if (a?.root_cause && a.recommendations.length)
    applyFix(a.root_cause.service, a.recommendations[0].strategy);
};
function applyFix(service, strategy) {
  action(
    "/api/fix",
    { service, strategy },
    `${pretty(strategy)} applied to ${service}. Watch health recover.`,
  );
}
$("recBody").addEventListener("click", (e) => {
  const b = e.target.closest("[data-strategy]");
  if (b) applyFix(b.dataset.target, b.dataset.strategy);
});
$("serviceSelect").onchange = (e) => {
  selected = e.target.value;
  renderInspection();
  renderLogs();
};
$("logFilter").onchange = renderLogs;
$("pauseLogs").onclick = () => {
  paused = !paused;
  $("pauseLogs").textContent = paused ? "Resume" : "Pause";
  $("pauseLogs").setAttribute("aria-pressed", String(paused));
  if (!paused) renderLogs();
};
$("exportBtn").onclick = () => {
  const a = document.createElement("a");
  a.href = "/api/report";
  a.download = "cascadeguard-incident.json";
  a.click();
  toast("Incident report download requested.");
};
for (const id of ["helpBtn", "methodBtn"])
  $(id).onclick = () => $("helpDialog").showModal();
for (const id of ["closeHelp", "startGuide"])
  $(id).onclick = () => $("helpDialog").close();
refresh().catch(() => {
  connection("Unable to connect", "offline");
  toast("Waiting for the telemetry server…", true);
});
connect();
resize();
requestAnimationFrame(draw);

function focusView(on) {
  document.body.classList.toggle("focus-mode", on);
  $("focusBtn").setAttribute("aria-pressed", String(on));
  window.scrollTo({ top: 0 });
  resize();
}
$("focusBtn").onclick = () => focusView(true);
$("focusExit").onclick = () => focusView(false);
