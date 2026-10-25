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
The same simulation implements fault propagation, recovery execution, and recovery comparison. Identical physical-noise streams make the five counterfactual trials comparable, with decorative logs isolated from system noise. Four explicit fault mechanisms produce different computed recovery choices. A downtime/standby policy constrains ranking and execution, and an optional predictive guard can act and re-plan. A reproducible paired study compares early, reactive, no-action, and single-action policies across 40 synthetic cases. Predictions, origin evidence, dependency impact, strategy costs, and observed recovery are inspectable in one workspace; the comparison is computed from current state rather than a fixed answer.

**Tools used:**
Python 3.9+, FastAPI, Uvicorn, Pydantic, WebSockets, HTML5 Canvas, vanilla JavaScript, CSS, Cloudflare Tunnel, Git/GitHub. AI-assisted development: OpenCode (initial build, per handover) and OpenAI Codex (polish, validation, tests, documentation). No LLM API, paid AI service, external database, or frontend framework runs in the product.

**Prior work and contribution disclosure:**
The project owner’s handover states that the initial simulator, prediction engine, API, and dashboard were built during the hackathon on 25 October 2026, with no project code written before the event. Those components already existed before the Codex polish pass. During the polish pass, we improved the recovery model and simulator consistency, added seeded scenarios, input validation and regression tests, redesigned the dashboard, and updated documentation. AI-assisted development and third-party libraries were used. Confirm the initial timing and prior-work statement against your own records before submitting; do not claim independently verified authorship history.

**Validation:**
32 engine/runtime/planner tests cover detection across all 17 origins and three seeds, four distinct recovery mechanisms, policy enforcement without partial mutation, independent physics/log RNGs, guard activation/re-planning, incident journal, and forecast consistency. The live API/WebSocket smoke suite also exercises strict inputs, policy conflicts, all four computed choices, evidence downloads, and paused streaming. The evidence lab is a separate 40-case synthetic policy comparison; report its figures with their scope rather than as production accuracy.

## Video script · approximately 2 minutes 40 seconds

Use the final app and keep the simulation clock visible. **Start guided demo** prepares T+16s and pauses; it is explicitly seeded synthetic telemetry. Its recovery step runs at visible 4× playback and automatically holds the result.

| Time      | Show                                                  | Say                                                                                                                                                                                                                                                                               |
| --------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00–0:18 | Healthy overview, then Start guided demo              | “A failing dependency can cascade through payments, orders and the gateway. CascadeGuard predicts exposure, explains the likely origin, and compares recoveries. This is a synthetic 17-service prototype.”                                                                       |
| 0:18–0:45 | Guide steps 1–2: topology, origin and metrics         | “At T+16s, payment-db has anomalous latency and errors. The detector uses metrics and graph relationships, not the injected-target label. Some callers are still healthy but exposed.”                                                                                            |
| 0:45–1:15 | Step 3: recovery lab and constraints                  | “Each action runs in an isolated simulator copy with the same physical noise. The planner compares 40-second outcomes and assumed downtime. Missing standby blocks failover, including at the API. Different fault mechanisms can favor different actions.”                       |
| 1:15–1:40 | Apply best & observe; show blue dots and held outcome | “This is visibly accelerated at four-times simulation playback. Observed points follow the saved forecast. Their agreement checks the shared model; it is not production validation.”                                                                                             |
| 1:40–2:15 | Evidence lab, expand method                           | “We compare four intervention policies across four faults and ten seeds excluded from the demo design. Service-unavailability metrics include isolated services, because keeping the gateway healthy can still sacrifice a feature. Every case is downloadable and reproducible.” |
| 2:15–2:35 | Finish guide; another scenario or guard               | “Capacity exhaustion, a bad deployment and a network partition have different response mechanics. The opt-in guard uses the same feasible-action planner and reconsiders after its horizon. Thirty-two tests cover the core contracts.”                                           |
| 2:35–2:40 | Export / final workspace                              | “Predict the impact. Explain the origin. Compare recovery before acting.”                                                                                                                                                                                                         |

Read the actual evidence figures visible in the final app if you mention them. Do not guarantee an action, ETA or model score across different intervention times. Record the real app; do not substitute a scripted mock video.

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
