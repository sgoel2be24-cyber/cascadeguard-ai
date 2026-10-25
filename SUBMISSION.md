# CascadeGuard AI — submission kit

## Copy-ready form fields

**Project name:** CascadeGuard AI

**Tagline:** See the cascade. Stop the outage.

**Track:** 01 — Software & AI (track assignment supplied in the project handover).

**Live project:** https://afford-fairy-mileage-penguin.trycloudflare.com

**GitHub:** https://github.com/sgoel2be24-cyber/cascadeguard-ai

**Video:** REQUIRED — record the actual final app and replace this field with a publicly accessible / unlisted video URL.

**Participant:** Shikhar · solo · GitHub `sgoel2be24-cyber`. Use your registered full name and required participant details from your registration.

**Description:**
CascadeGuard AI is an explainable reliability command center that demonstrates how a failing dependency can cascade through a distributed system. A live 17-service digital twin emits synthetic metrics and logs. Statistical anomaly detection and graph risk propagation identify a suspected origin and flag exposed callers before they fail. A recovery lab evaluates restart, failover, scale-out, circuit breaker, and rollback using five isolated copies of the same simulator over the next 40 simulated seconds. Operators can compare projected risk reduction against assumed downtime, apply a recovery action, observe the result, and export the incident evidence.

**Problem relevance:**
A database outage often appears as failures in payment processing, ordering, and the gateway. CascadeGuard connects those symptoms to an actionable origin and makes recovery tradeoffs visible. It is a prototype for operator decision support, with synthetic rather than production telemetry.

**What is innovative:**
The same simulation implements fault propagation, recovery execution, and recovery comparison. Identical random streams make the five counterfactual trials comparable. Predictions, origin evidence, dependency impact, strategy costs, and observed recovery are inspectable in one workspace; the comparison is computed from current state rather than a fixed answer.

**Tools used:**
Python 3.9+, FastAPI, Uvicorn, Pydantic, WebSockets, HTML5 Canvas, vanilla JavaScript, CSS, Cloudflare Tunnel, Git/GitHub. AI-assisted development: OpenCode (initial build, per handover) and OpenAI Codex (polish, validation, tests, documentation). No LLM API, paid AI service, external database, or frontend framework runs in the product.

**Prior work and contribution disclosure:**
The project owner’s handover states that the initial simulator, prediction engine, API, and dashboard were built during the hackathon on 25 October 2026, with no project code written before the event. Those components already existed before the Codex polish pass. During the polish pass, we improved the recovery model and simulator consistency, added seeded scenarios, input validation and regression tests, redesigned the dashboard, and updated documentation. AI-assisted development and third-party libraries were used. Confirm the initial timing and prior-work statement against your own records before submitting; do not claim independently verified authorship history.

**Validation:**
Twenty engine/runtime tests passed, including identification of the injected origin across 17 services and three seeds (51 synthetic cases), prediction of a healthy caller before failure, five-strategy forecast/action parity, full-chain recovery, and timed circuit-breaker protection. The expanded local API/WebSocket run passed 81 checks, including explicit single-step requests. These validate the simulator prototype, not real-world prediction accuracy.

## Video script · approximately 2 minutes 40 seconds

Narrate what is visible. Do not promise a fixed evidence score, ETA, or always-winning action. For a compact recording, capture the full genuine recovery first and trim waiting time in editing; keep the on-screen T+ clock visible and never imply that edited elapsed time is real time. Acting within about 24 seconds of injection lets the seeded payment demo return all services to healthy within about one simulated minute. A later intervention can take longer.

**0:00–0:18 — problem and honest scope**
“An unhealthy payment database can take down payments, orders, and eventually the gateway. CascadeGuard AI is an explainable incident command center that helps an operator see the cascade and compare recovery actions. This demo uses a live synthetic 17-service digital twin.”

**0:18–0:35 — orient**
Show the normal overview and enter Focus view. “Here is the topology, with live telemetry every two seconds. Green nodes are healthy. I can inspect any service without changing the system. The payment scenario will inject a reproducible database fault.” Click Run scenario at the end of this segment.

**0:35–0:55 — prediction and evidence**
“Latency and errors rise at payment-db. The model compares recent observations with a robust baseline and propagates risk through the dependency graph. Notice exposed callers can appear in the forecast while still healthy. When a declining health trend is available, the engine adds an approximate time-to-failure.”

Pause the simulation near T+16–24s before continuing the explanation. The transport remains live; only the synthetic world is paused.

**0:55–1:15 — origin and impact**
“Root cause ranking favors an anomalous service whose dependencies do not already explain its symptoms. Here is the metric evidence. The impact chain follows payment-db through payment-service and order-service to the gateway. Evidence strength and risk are heuristic scores, not calibrated probabilities.”

**1:15–1:45 — recovery lab and action**
Scroll to the recovery lab. “Each of these five actions runs through a separate copy of the same simulator for 40 simulated seconds, using the same starting state and random stream. The model compares mean operational risk against taking no action, with an explicit assumed downtime penalty. This is the current best action under those assumptions.” Apply the currently ranked best action before leaving this segment. Do not wait for every caller to fail.

**1:45–2:10 — observed recovery**
Choose **4× accelerated** and **Resume simulation**, then return to the topology. “I am showing recovery at four-times playback speed; the simulated clock remains visible. The action is logged. Now we watch the actual simulated recovery across subsequent ticks. A circuit breaker temporarily shields callers but does not heal the source; scale-out reduces fault pressure. Those distinctions are represented in both the forecast and execution.” If recovery is gradual, state that rather than claiming it has completed.

**2:10–2:30 — technical credibility**
“Recovery forecasts do not mutate the live system. Our tests cover origin detection across every service with three seeds, forecast/action parity, circuit-breaker expiry, and full-chain recovery. The app uses Python, FastAPI, WebSockets, and a dependency-free Canvas interface. AI development tools were used and disclosed.”

**2:30–2:40 — close**
Show export and the final overview. “The exported incident contains the current metrics, analysis, and action history. CascadeGuard AI: predict the dependency impact, explain the origin, and compare recovery before you act.”

## Judge Q&A

**Is this an LLM?** No. It uses statistical anomaly detection, graph propagation, health trends, and simulator-based counterfactual search. No trained ML model or production accuracy claim is presented.

**Is the recovery globally optimal?** It is the best scored action among five choices under a 40-second simulator horizon and assumed downtime costs. Optimality outside those assumptions is not claimed.

**Are predictions hard-coded?** No. The topology and available actions are defined; anomaly evidence, risk, origin ranking, trend ETA, and recovery scores are computed from evolving state. Seeded scenarios make demonstrations repeatable.

**Can it run on real infrastructure?** Not yet. A production version needs telemetry ingestion, fault-state estimation, calibrated uncertainty, persistent storage, authenticated isolation, and controlled remediation integrations. Current recovery trials use simulated fault state.

**Why no cloud database or LLM API?** The core demonstration needs neither. The lightweight stack keeps it reproducible and focuses effort on the judging criteria.

## Final readiness checklist

- [ ] Record the final app and upload the actual demonstration video; test access in a private window.
- [ ] Check the live URL and GitHub URL from another browser/device.
- [ ] Verify the registered participant details and prior-work timeline.
- [ ] Include both OpenCode and OpenAI Codex in AI tools disclosure.
- [ ] Submit all fields and capture the submission confirmation.
- [ ] Keep the machine awake, server running, and current tunnel alive until judging ends.

**Deadline discrepancy:** The official Unstop submission stage says 4:30 PM IST on 25 October 2026, while its long description says 3:30 PM final submission and 3:15 PM build/deployment. Observed during the polish pass. Use the earlier 3:15 / 3:30 targets unless the organizers explicitly confirm otherwise. Source: https://unstop.com/hackathons/orca-coders-orcathon-devharbour-1768929

## Improved recording flow with playback controls

1. Enter Focus view. Run the payment scenario, then pause at roughly T+16–24s. The WebSocket connection stays live while the simulated world holds still.
2. Explain current evidence and the first inferred origin. Use Step +2s to demonstrate a single propagation step. Focus impact dims unrelated services.
3. Inspect the observed service trends. Compare two recovery trajectories using the action selector; comparison alone never executes the action.
4. Apply the chosen recovery while paused. The Applied action chart retains its starting prediction. Choose 4× playback and resume: 40 simulated seconds now take about 10 wall-clock seconds plus computation time. The interface shows acceleration and simulated timestamps explicitly.
5. Show the observed dots on the forecast curve and the incident evidence after recovery. Describe agreement as same-model consistency, not proof of production accuracy. Export before resetting.

New capabilities to highlight: real observed lead time within the synthetic incident, initial inferred-origin retention, pause/step/accelerate controls, four telemetry trend charts, selectable strategy trajectories and forecast-versus-observed outcome replay.
