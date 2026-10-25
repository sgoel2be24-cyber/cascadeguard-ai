/* Feasible recovery policy, reproducible evidence, and a bounded five-step demo. */
let evidenceReport = null;
let evidenceHasLabels = false;
let tourStep = -1;
let tourWorld = null;
let tourStarting = false;
let tourHolding = false;
let previousFocusMode = false;
const tourContent = [
  [
    "Predict the cascade",
    "#graphPanel",
    "The demo has advanced eight real simulation ticks and paused at T+16s. Inspect the failing dependency and look for callers marked at risk while still healthy.",
    "Next: inspect the origin →",
  ],
  [
    "Explain the origin, not just the symptom",
    ".intelligence",
    "The hypothesis comes from observed metrics and dependency relationships. It does not read the injected target label. Trace the impact chain toward the gateway.",
    "Next: compare recoveries →",
  ],
  [
    "Choose a feasible recovery",
    "#recovery",
    "Compare the no-action trajectory with an intervention. The planner evaluates all five actions, explains whether they repair this fault, and excludes options outside the current recovery constraints.",
    "Apply best & observe →",
  ],
  [
    "Observe the outcome",
    "#recovery",
    "Recovery is playing at 4× speed. Blue points are observed values after the action. The saved forecast uses the same model, so agreement is a consistency check. The guide will hold the completed outcome.",
    "View measured evidence →",
  ],
  [
    "Check more than one successful demo",
    "#proofLab",
    "The evidence lab compares four fault mechanisms across previously unused seeds, with no-action and reactive controls. Download every case or reproduce the experiment. Results remain scoped to this synthetic twin.",
    "Finish walkthrough ✓",
  ],
];

function renderPolicy() {
  $("downtimeBudget").value = state.policy.max_downtime_s;
  $("standbyAvailable").checked = state.policy.standby_available;
  $("guardEnabled").checked = state.guard.enabled;
  $("guardStatus").textContent = state.guard.enabled
    ? state.playback.paused
      ? "Armed · simulation paused"
      : "Armed · checks each tick"
    : "Operator-controlled recovery";
  document
    .querySelector(".guard-field")
    .classList.toggle("armed", state.guard.enabled);
}

function wireRubricControls() {
  $("downtimeBudget").onchange = (e) => {
    const value = Number(e.target.value);
    if (
      !e.target.value ||
      !Number.isInteger(value) ||
      value < 0 ||
      value > 120
    ) {
      toast("Use a downtime budget from 0 to 120 seconds.", true);
      renderPolicy();
      return;
    }
    action(
      "/api/policy",
      { max_downtime_s: value },
      "Recovery ranking and execution now use the new downtime limit.",
    );
  };
  $("standbyAvailable").onchange = (e) =>
    action(
      "/api/policy",
      { standby_available: e.target.checked },
      e.target.checked
        ? "Standby enabled: failover can be considered."
        : "No standby: failover is excluded and cannot be applied.",
    );
  $("guardEnabled").onchange = (e) =>
    action(
      "/api/guard",
      { enabled: e.target.checked },
      e.target.checked
        ? "Predictive guard armed. It may apply feasible recoveries in this shared synthetic world."
        : "Predictive guard disarmed. Recovery is operator-controlled.",
    );
  $("guidedDemoBtn").onclick = startGuide;
  $("guideNextBtn").onclick = advanceGuide;
  $("exitGuideBtn").onclick = closeGuide;
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && tourStep >= 0) closeGuide();
  });
}

async function guidePost(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(12000),
  });
  const data = await response.json();
  if (!response.ok)
    throw Error(
      typeof data.detail === "string" ? data.detail : "Demo action failed",
    );
  return data;
}

async function startGuide() {
  if (busy) return;
  busy = true;
  tourStarting = true;
  buttons();
  try {
    previousFocusMode = document.body.classList.contains("focus-mode");
    await guidePost("/api/demo");
    await refresh();
    selected = "payment-db";
    $("serviceSelect").value = selected;
    renderInspection();
    tourWorld = state.world_id;
    tourStep = 0;
    tourHolding = false;
    focusView(true);
    showGuideStep();
  } catch (error) {
    toast(error.message, true);
  } finally {
    busy = false;
    tourStarting = false;
    buttons();
  }
}

function showGuideStep() {
  document
    .querySelectorAll(".tour-highlight")
    .forEach((el) => el.classList.remove("tour-highlight"));
  $("guidedCoach").hidden = tourStep < 0;
  if (tourStep < 0) return;
  const [title, target, body, label] = tourContent[tourStep];
  $("coachProgress").textContent =
    `GUIDED DEMO · ${tourStep + 1} / ${tourContent.length}`;
  $("coachTitle").textContent = title;
  $("coachBody").textContent = body;
  $("guideNextBtn").textContent = label;
  const element = document.querySelector(target);
  element?.classList.add("tour-highlight");
  element?.scrollIntoView({
    behavior: reducedMotion ? "instant" : "smooth",
    block: "start",
  });
  syncGuide();
}

function syncGuide() {
  if (tourStep < 0 || !state) return;
  const done =
    state.incident?.phase === "resolved" &&
    state.last_decision?.status === "complete";
  $("guideNextBtn").disabled = busy || (tourStep === 3 && !done);
  if (tourStep === 3 && done) {
    $("coachTitle").textContent = "Recovery observed · outcome held";
    $("coachBody").textContent =
      "The incident has resolved and the 40-second forecast horizon is complete. Compare the observed blue points with the saved forecast, then inspect the paired experiments across other faults and seeds.";
  }
  if (tourStep === 3 && done && !state.playback.paused && !tourHolding) {
    tourHolding = true;
    guidePost("/api/control", { paused: true })
      .then(refresh)
      .catch((e) => toast(e.message, true));
  }
}

async function advanceGuide() {
  if (busy || tourStep < 0) return;
  if (tourStep === 4) {
    closeGuide();
    return;
  }
  if (tourStep === 2) {
    const best = state.analysis.recommendations.find(
      (r) => r.eligible && r.risk_reduction > 0,
    );
    if (!best || !state.analysis.root_cause) {
      toast(
        "No feasible recovery has a modeled benefit. Adjust the constraints.",
        true,
      );
      return;
    }
    busy = true;
    buttons();
    $("guideNextBtn").disabled = true;
    try {
      await guidePost("/api/fix", {
        service: state.analysis.root_cause.service,
        strategy: best.strategy,
      });
      await guidePost("/api/control", { speed: 4, paused: false });
      comparisonMode = "applied";
      tourStep = 3;
      await refresh();
      showGuideStep();
    } catch (error) {
      toast(error.message, true);
    } finally {
      busy = false;
      buttons();
      syncGuide();
    }
    return;
  }
  tourStep++;
  showGuideStep();
}

function closeGuide() {
  const wasActive = tourStep >= 0;
  tourStep = -1;
  tourWorld = null;
  tourHolding = false;
  document
    .querySelectorAll(".tour-highlight")
    .forEach((el) => el.classList.remove("tour-highlight"));
  $("guidedCoach").hidden = true;
  if (wasActive) focusView(previousFocusMode);
}

async function loadEvidence() {
  try {
    const response = await fetch("/api/evaluation", {
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw Error("Evidence unavailable");
    evidenceReport = await response.json();
    renderEvidenceLab();
  } catch (error) {
    $("evidenceFreshness").textContent = "Evidence unavailable";
    $("proofMetrics").innerHTML =
      '<div class="empty">The experiment report could not be loaded. The live incident workflow remains available.</div>';
  }
}

function renderEvidenceLab() {
  const report = evidenceReport;
  if (report.status !== "current") {
    $("evidenceFreshness").textContent =
      report.status === "stale" ? "Regeneration required" : "Not yet generated";
    $("proofMetrics").innerHTML =
      `<div class="empty">${esc(report.message || "Evidence is not available for this implementation.")}</div>`;
    return;
  }
  $("evidenceFreshness").textContent = "Matches this implementation";
  $("evidenceFreshness").className = "badge";
  evidenceHasLabels = Boolean(state);
  const summary = report.summary;
  const percent = (v) => (v === null ? "—" : v.toFixed(1) + "%");
  $("proofMetrics").innerHTML = [
    [
      "LESS MODELED GATEWAY FAILURE",
      percent(summary.gateway_failure_reduction_pct),
      "Predictive vs reactive intervention",
    ],
    [
      "LESS SERVICE UNAVAILABILITY",
      percent(summary.service_unavailability_reduction_pct),
      "Failed or isolated service-seconds; includes containment cost",
    ],
    [
      "FIRST ORIGIN LOCALIZED",
      summary.first_origin_correct + " / " + summary.case_count,
      "First inferred origin compared with injected ground truth",
    ],
  ]
    .map(
      ([label, value, note]) =>
        `<div><span>${label}</span><b>${value}</b><small>${note}</small></div>`,
    )
    .join("");
  const modeLabels = {
    predictive: "Predictive guard",
    reactive: "React after gateway fails",
    no_action: "No recovery",
  };
  const modeColors = {
    predictive: "#5ee7bb",
    reactive: "#eac16b",
    no_action: "#8198af",
  };
  const max = Math.max(
    1,
    ...Object.values(report.by_scenario).flatMap((v) =>
      ["predictive", "reactive", "no_action"].map(
        (mode) => v.policies[mode].mean_gateway_failed_s,
      ),
    ),
  );
  $("proofCases").innerHTML = Object.entries(report.by_scenario)
    .map(([name, group]) => {
      const title = state?.scenarios[name]?.label || pretty(name);
      const bars = ["predictive", "reactive", "no_action"]
        .map((mode) => {
          const value = group.policies[mode].mean_gateway_failed_s;
          return `<div class="proof-bar-row"><span>${modeLabels[mode]}</span><div><i style="width:${Math.max(value ? 1 : 0, (value / max) * 100)}%;background:${modeColors[mode]}"></i></div><b>${value.toFixed(1)}s</b></div>`;
        })
        .join("");
      const isolation = group.policies.predictive.mean_isolation_service_s;
      return `<article><h4>${esc(title)}</h4><p>Mean gateway-failed time · ${group.case_count} seeds</p>${bars}<small>Predictive source-isolation cost: ${isolation.toFixed(1)} service-seconds.</small></article>`;
    })
    .join("");
  const oneShot = summary.policies.single_action.mean_gateway_failed_s;
  $("proofMethod").innerHTML =
    `<p><b>${summary.case_count} paired cases · ${report.method.seeds.length} seeds · ${report.method.horizon_s}s per rollout.</b> Seeds: ${report.method.seeds.join(", ")}. The design/demo seed (${report.method.design_seed}) is excluded.</p><p>${esc(report.method.comparison)} ${esc(report.method.replanning)}</p><p>Default planning policy: ${report.method.policy.max_downtime_s}s assumed downtime budget, standby available. Changing the live policy does not change this saved experiment.</p><p>Single-action control: ${oneShot.toFixed(2)}s mean gateway-failed time; predictive re-planning: ${summary.policies.predictive.mean_gateway_failed_s.toFixed(2)}s. Temporary isolation can expire before the fault clears, so one early action is not always enough.</p><p>Fingerprint <code>${esc(report.implementation_sha256.slice(0, 16))}</code> · generated ${esc(report.generated_at)}. Download the case-level trajectories to inspect the calculation.</p>`;
}
