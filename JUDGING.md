# Judging evidence map

Every addition targets the supplied 100-point rubric. This maps inspectable evidence, not predicted judge scores.

| Criterion                    | Points | What judges can verify                                                                                                                                                                          |
| ---------------------------- | -----: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Functionality and execution  |     25 | Guided incident → healthy callers at risk → computed recovery → observed result held on screen → export; four functioning fault mechanisms; opt-in guard re-plans                               |
| Innovation and originality   |     20 | Five genuine cloned rollouts; different actions win for different modeled causes; feasible recovery policy; early-vs-reactive experiment with no-action and one-shot controls                   |
| Technical implementation     |     20 | Robust MAD evidence, synchronous graph ticks, separate physics/log random streams, fixed physical draw count, API-enforced constraints, strict inputs, fingerprinted evidence, 32 tests and CI  |
| UI/UX and usability          |     15 | Five-step guided demo, paused diagnosis, explicit 4× playback, focus mode, selectable trajectories, observed dots, constraint controls, blocked-action reasons, responsive evidence comparisons |
| Problem relevance            |     10 | Trace dependency failure into payment, orders and gateway; show why source isolation protects callers while sacrificing a feature                                                               |
| Presentation and explanation |     10 | Actual-app recording script, inspectable assumptions, downloadable case data, reproducible study, explicit synthetic and AI-assistance disclosures                                              |

## Demonstration order

1. Start guided demo; explain the origin and healthy caller exposure.
2. Compare recovery trajectories and policy feasibility, then apply the best feasible action.
3. Show held observed recovery, with same-model consistency described accurately.
4. Open evidence method and download the 40-case experiment.
5. Try cache, search or network to show a different computed recovery; optionally arm predictive guard.

## Evidence and boundaries

- 32 deterministic engine/runtime/planner tests, including 51 synthetic origin cases across all services and three seeds.
- API smoke exercises HTTP and WebSocket flows, invalid requests, policy conflicts, four computed recovery choices, guard actions, and evidence integrity.
- Paired experiment: four faults × ten seeds × four policies × 160 simulated seconds. Identical initial state and physical noise; logs cannot shift the physics stream.
- Report service unavailability including containment costs, not gateway availability alone.
- Fault-response mechanics are explicit simulator assumptions. The evaluator has current simulated fault state; a real twin would need to estimate it.
- Statistical and graph heuristics; no trained classifier, calibrated probabilities or production accuracy claim.
- Forty-second action horizon and assumed downtime costs. Five bounded choices are not global optimization.
- Shared, memory-only synthetic sandbox; public visitors can affect it. No real infrastructure control or durable incident history.
- Same-model forecast agreement is consistency evidence. The paired study compares policies inside that same model.
- Keep the existing tunnel and local machine alive through judging. Record/upload the actual video and complete participant details before submitting.
