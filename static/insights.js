/* Evidence, trends and recovery trajectories. All plotted values come from the API. */
let comparisonStrategy = null;
let comparisonMode = "whatif";
let impactOnly = false;

function chartPath(points, x, y) {
  return points
    .map((p, i) => `${i ? "L" : "M"}${x(p).toFixed(2)},${y(p).toFixed(2)}`)
    .join(" ");
}

function trajectorySvg(lines, description) {
  const all = lines.flatMap((l) => l.points);
  if (!all.length)
    return '<div class="chart-placeholder"><strong>Your next decision, made visible.</strong><span>Run a scenario to compare forecast trajectories.</span></div>';
  const max = Math.min(
    100,
    Math.max(
      10,
      Math.ceil((Math.max(...all.map((p) => p.risk)) * 1.15) / 10) * 10,
    ),
  );
  const x = (p) => 42 + (p.seconds / 40) * 550,
    y = (p) => 150 - (p.risk / max) * 130;
  const grid = [0, 1, 2, 3, 4]
    .map((i) => {
      const value = (max * i) / 4,
        py = 150 - i * 32.5;
      return `<line x1="42" x2="592" y1="${py}" y2="${py}" stroke="#294052" stroke-opacity=".6"/><text x="32" y="${py + 4}" text-anchor="end" fill="#8299af" font-size="11">${value % 1 ? value.toFixed(1) : value}</text>`;
    })
    .join("");
  const ticks = [0, 10, 20, 30, 40]
    .map(
      (sec) =>
        `<text x="${42 + (sec / 40) * 550}" y="174" text-anchor="middle" fill="#8299af" font-size="11">+${sec}s</text>`,
    )
    .join("");
  const paths = lines
    .map(
      (l) =>
        `<path d="${chartPath(l.points, x, y)}" fill="none" stroke="${l.color}" stroke-width="${l.dots ? 2 : 2.5}" ${l.dash ? 'stroke-dasharray="6 5"' : ""} vector-effect="non-scaling-stroke"/>${l.dots ? l.points.map((p) => `<circle cx="${x(p)}" cy="${y(p)}" r="2.7" fill="${l.color}"/>`).join("") : ""}`,
    )
    .join("");
  return `<svg viewBox="0 0 620 190" role="img" aria-label="${esc(description)}"><title>${esc(description)}</title>${grid}${ticks}${paths}<text x="42" y="10" fill="#8299af" font-size="10">OPERATIONAL RISK · POINTS</text></svg><div class="chart-legend">${lines.map((l) => `<span><i style="background:${l.color}"></i>${esc(l.label)}</span>`).join("")}</div>`;
}

function renderTrends(service) {
  $("telemetryService").textContent = selected;
  const samples = service.history.filter((p) => p.tick >= 0);
  const definitions = [
    {
      key: "health",
      label: "HEALTH",
      scale: 100,
      value: service.health * 100,
      unit: "%",
      max: 100,
      color: "#5ee7bb",
    },
    {
      key: "latency",
      label: "LATENCY",
      scale: 1,
      value: service.latency,
      unit: "ms",
      color: "#87c8e9",
    },
    {
      key: "error_rate",
      label: "ERROR RATE",
      scale: 100,
      value: service.error_rate * 100,
      unit: "%",
      max: 100,
      color: "#fa7e8b",
    },
    {
      key: "cpu",
      label: "CPU LOAD",
      scale: 1,
      value: service.cpu,
      unit: "%",
      max: 100,
      color: "#eac16b",
    },
  ];
  $("trendCharts").innerHTML = definitions
    .map((d) => {
      const sampled = samples.length ? samples.at(-1)[d.key] * d.scale : null;
      let plot =
        '<div class="trend-empty">Waiting for two observed samples…</div>';
      if (samples.length >= 2) {
        const max =
          d.max ||
          Math.max(20, ...samples.map((p) => p[d.key] * d.scale)) * 1.15;
        const x = (p) =>
          ((p.tick - samples[0].tick) /
            Math.max(1, samples.at(-1).tick - samples[0].tick)) *
          240;
        const y = (p) => 76 - (Math.min(max, p[d.key] * d.scale) / max) * 66;
        const line = chartPath(samples, x, y),
          area = `${line} L240,80 L0,80 Z`;
        plot = `<svg viewBox="0 0 240 90" role="img" aria-label="${esc(selected + " " + d.label.toLowerCase() + " trend over the last " + (samples.at(-1).tick - samples[0].tick) * 2 + " simulated seconds")}"><defs><linearGradient id="fill-${d.key}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${d.color}" stop-opacity=".18"/><stop offset="100%" stop-color="${d.color}" stop-opacity="0"/></linearGradient></defs><line x1="0" x2="240" y1="10" y2="10" stroke="#304458" stroke-dasharray="3 4"/><line x1="0" x2="240" y1="76" y2="76" stroke="#304458"/><text x="0" y="7" font-size="8" fill="#7f94aa">${max.toFixed(0)}${d.unit}</text><path d="${area}" fill="url(#fill-${d.key})"/><path d="${line}" fill="none" stroke="${d.color}" stroke-width="1.7"/></svg><div class="trend-axis"><span>T+${samples[0].tick * 2}s</span><span>T+${samples.at(-1).tick * 2}s</span></div>`;
      }
      return `<article class="trend-card"><div class="trend-top"><span>${d.label}</span><b class="trend-current">${sampled === null ? "—" : sampled.toFixed(d.key === "error_rate" ? 1 : 0)}<small> ${d.unit}</small></b></div>${plot}</article>`;
    })
    .join("");
  $("trendNote").textContent =
    `${samples.length} observed synthetic samples for ${selected}. Values and lines use sampled telemetry; step or resume after an action to sample its effect. Seeded reference data is excluded.`;
  $("inspectOriginBtn").disabled = !state.analysis.root_cause;
}

function renderPlayback() {
  const p = state.playback;
  $("pauseSimBtn").textContent = p.paused
    ? "▶ Resume simulation"
    : "Ⅱ Pause simulation";
  $("pauseSimBtn").setAttribute("aria-pressed", String(p.paused));
  $("playbackStatus").textContent = p.paused
    ? "Simulation paused"
    : `Simulation running · ${p.speed}×`;
  $("simClock").textContent = `T+${String(state.tick * 2).padStart(3, "0")}s`;
  $("speedSelect").value = String(p.speed);
  $("graphMode").textContent = p.paused
    ? "PAUSED"
    : p.speed > 1
      ? `${p.speed}× LIVE`
      : "LIVE";
  $("graphMode").classList.toggle("neutral", p.paused);
  $("stepBtn").disabled = busy || stale || !p.paused;
  $("pauseSimBtn").disabled = busy || stale;
  $("speedSelect").disabled = busy || stale;
}

function renderComparison() {
  const a = state.analysis,
    decision = state.last_decision;
  const recommendations = a.recommendations;
  $("appliedBtn").disabled = !decision;
  if (comparisonMode === "applied" && !decision) comparisonMode = "whatif";
  $("whatIfBtn").classList.toggle("active", comparisonMode === "whatif");
  $("whatIfBtn").setAttribute(
    "aria-pressed",
    String(comparisonMode === "whatif"),
  );
  $("appliedBtn").classList.toggle("active", comparisonMode === "applied");
  $("appliedBtn").setAttribute(
    "aria-pressed",
    String(comparisonMode === "applied"),
  );
  if (!$("compareStrategy").options.length) {
    $("compareStrategy").innerHTML = [
      "failover",
      "restart",
      "scale_out",
      "circuit_breaker",
      "rollback",
    ]
      .map((n) => `<option value="${n}">${pretty(n)}</option>`)
      .join("");
  }
  const chosen =
    recommendations.find((r) => r.strategy === comparisonStrategy) ||
    recommendations[0];
  if (chosen) comparisonStrategy = chosen.strategy;
  $("compareStrategy").value = comparisonStrategy || "failover";
  $("compareStrategy").disabled = comparisonMode === "applied" || !chosen;
  document
    .querySelectorAll(".strategy[data-preview], .strategy.previewed")
    .forEach((el) => el.classList.remove("previewed"));
  if (comparisonMode === "applied" && decision) {
    const lines = [
      {
        label: "No action · forecast",
        points: decision.baseline,
        color: "#fa7e8b",
        dash: true,
      },
      {
        label: pretty(decision.strategy) + " · forecast",
        points: decision.projected,
        color: "#5ee7bb",
      },
    ];
    if (decision.observed.length)
      lines.push({
        label: "Observed after action",
        points: decision.observed,
        color: "#8cc8f5",
        dots: true,
      });
    $("forecastChart").innerHTML = trajectorySvg(
      lines,
      `Saved forecast and observed operational risk after ${pretty(decision.strategy)} on ${decision.service}`,
    );
    const observed = decision.observed,
      delta = observed.length
        ? observed.at(-1).risk
        : decision.projected[0].risk;
    const progress = Math.min(
      40,
      Math.max(0, (state.tick - decision.tick) * 2),
    );
    $("forecastNarrative").innerHTML =
      `<div class="overline">APPLIED ${esc(pretty(decision.strategy).toUpperCase())}<br>${esc(decision.service)}</div><div class="comparison-number">${observed.length ? delta.toFixed(1) : "—"} <span>/ 100</span></div><div class="comparison-detail">Latest observed operational risk.<br><b>${observed.length} / 20</b> horizon samples collected.${state.playback.paused ? "<br>Resume or step to observe recovery." : ""}</div><span class="comparison-state ${decision.status === "complete" ? "complete" : ""}">${decision.status === "complete" ? "40s horizon complete" : decision.status === "interrupted" ? "Assumptions changed" : progress + "s / 40s observed"}</span><div class="comparison-detail">${decision.status === "interrupted" ? esc(decision.note) : decision.status === "complete" ? `Mean forecast deviation: <b>${decision.mean_absolute_error.toFixed(3)} risk pts</b>. ` : ""}Same-model consistency only; both paths use this simulator.</div>`;
  } else if (chosen) {
    $("forecastChart").innerHTML = trajectorySvg(
      [
        {
          label: "No action · forecast",
          points: a.baseline_trajectory,
          color: "#fa7e8b",
          dash: true,
        },
        {
          label: pretty(chosen.strategy) + " · forecast",
          points: chosen.trajectory,
          color: "#5ee7bb",
        },
      ],
      `Forty-second operational risk forecast: no action versus ${pretty(chosen.strategy)}`,
    );
    const delta = a.baseline_forecast - chosen.projected_risk;
    $("forecastNarrative").innerHTML =
      `<div class="overline">${esc(pretty(chosen.strategy).toUpperCase())}<br>vs taking no action</div><div class="comparison-number" style="color:${delta >= 0 ? "var(--green)" : "var(--red)"}">${delta >= 0 ? "−" : "+"}${Math.abs(delta).toFixed(1)} <span>risk pts</span></div><div class="comparison-detail">Mean operational risk over 40s.<br><b>${a.baseline_forecast.toFixed(1)}</b> without action → <b>${chosen.projected_risk.toFixed(1)}</b> with action.</div><div class="comparison-detail"><b>${chosen.downtime_s}s</b> assumed downtime · utility <b>${chosen.score.toFixed(1)}</b>.<br>Select another action to compare its path.</div>`;
    const previewButton = document.querySelector(
      `[data-strategy="${comparisonStrategy}"]`,
    );
    previewButton?.closest(".strategy").classList.add("previewed");
  } else {
    $("forecastChart").innerHTML = trajectorySvg([], "No forecast data");
    $("forecastNarrative").innerHTML =
      '<div class="overline">COUNTERFACTUAL EXPLORER</div><div class="comparison-number">5 <span>actions</span></div><div class="comparison-detail">Each strategy starts from the same state. Compare the shape of the recovery, then apply an action and watch its forecast against observed behavior.</div>';
  }
}

function renderIncident() {
  const item = state.incident,
    ribbon = $("incidentRibbon");
  ribbon.hidden = !item;
  if (item) {
    const title = {
      observing: "Waiting for an anomaly signal",
      detected: "Origin identified · compare recovery",
      recovering: "Recovery in progress",
      resolved: "Services healthy · anomaly signals cleared",
    }[item.phase];
    ribbon.className = "incident-ribbon " + item.phase;
    const milestones = [
      ["Signal", item.detected_tick !== null],
      ["Diagnosis", Boolean(item.initial_origin)],
      ["Action", item.first_action_tick !== null],
      ["Recovered", item.phase === "resolved"],
    ];
    ribbon.innerHTML = `<div><div class="incident-key">${esc(item.id)} · ${item.phase.toUpperCase()}</div><div class="incident-origin">${esc(title)}</div><div class="incident-subline">${item.initial_origin ? "Initial inferred origin: " + esc(item.initial_origin) + " · " : ""}${item.duration_s}s simulated elapsed</div></div><div class="phase-steps">${milestones.map(([label, done]) => `<span class="${done ? "complete" : ""}"><i>${done ? "✓" : "○"}</i>${label}</span>`).join("")}</div>`;
  }
  $("evidenceStatus").textContent = item
    ? `${item.id} · ${item.phase}`
    : "Awaiting incident";
  const bestLead = item?.verified_leads.length
    ? Math.max(...item.verified_leads.map((x) => x.lead_s))
    : null;
  const stats = [
    [
      "TIME TO DETECT",
      item?.detection_s != null ? item.detection_s + "s" : "—",
      "From synthetic fault injection to first inferred origin",
    ],
    [
      "PEAK AFFECTED",
      item ? item.peak_affected + " / 17" : "—",
      "Observed services below the healthy threshold",
    ],
    [
      "PEAK FAILED",
      item ? String(item.peak_failed) : "—",
      "Observed failed services during this incident",
    ],
    [
      item?.phase === "resolved" ? "RECOVERY TIME" : "RECOVERY ELAPSED",
      item?.recovery_s != null ? item.recovery_s + "s" : "—",
      "From first action to three consecutive healthy ticks",
    ],
    [
      "LONGEST WARNING LEAD",
      bestLead != null ? bestLead + "s" : "—",
      "Healthy-service warning before a later observed failure",
    ],
  ];
  $("incidentStats").innerHTML = stats
    .map(
      ([label, value, note]) =>
        `<div class="incident-stat"><span>${label}</span><b>${value}</b><small>${note}</small></div>`,
    )
    .join("");
  if (!item) {
    $("leadEvidence").innerHTML =
      "Run a scenario to collect detection latency, observed impact, recovery time, and warning lead time. No benchmark or accuracy score is inferred from these synthetic results.";
    return;
  }
  const leads = item.verified_leads;
  $("leadEvidence").innerHTML = leads.length
    ? `${leads.length} healthy-service warning${leads.length === 1 ? "" : "s"} preceded an observed failure in this incident. These are measured lead times within the synthetic world.<div class="lead-chips">${leads.map((l) => `<button class="lead-chip" data-inspect="${esc(l.service)}">${esc(l.service)} · ${l.lead_s}s ahead ↗</button>`).join("")}</div>`
    : `${Object.keys(item.warnings).length} healthy-service warnings recorded. No warned service has subsequently failed${item.phase === "resolved" ? " before resolution" : " yet"}. Remediation can interrupt the cascade; this does not establish a prediction-accuracy score.`;
}
