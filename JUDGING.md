# Judging evidence map

Aligned with the event’s published 100-point rubric. This maps inspectable evidence to criteria; it does not predict judge scores.

| Criterion | Points | Evidence to demonstrate |
|---|---:|---|
| Functionality and execution | 25 | Run any seeded scenario → inspect leading signals → see dependency risk → apply recovery → observe metrics recover → export incident |
| Innovation and originality | 20 | Five comparable counterfactual trials use the exact recovery implementation and identical random streams, rather than a fixed recommended action |
| Technical implementation | 20 | Robust statistical scoring, synchronous dependency ticks, explicit circuit isolation, cloned forecasts, validated API, shared ticker/cache, WebSocket state, regression tests and CI |
| UI/UX and usability | 15 | Responsive command center, focus mode, visible synthetic mode, service inspection without side effects, labelled controls, keyboard access, action errors, stale/reconnect feedback, paused/filtered logs |
| Problem relevance | 10 | Demonstrate payment-db → payment-service → order-service → api-gateway; explain why treating gateway symptoms misses the origin |
| Presentation and explanation | 10 | Show computed evidence and strategy assumptions; disclose synthetic scope and AI assistance; follow the actual-app recording script in SUBMISSION.md |

## Local evidence recorded during polish

- 20 engine/runtime tests passed. One covers all 17 origins with 3 seeds (51 cases).
- 81 HTTP/WebSocket checks passed on the isolated preview and again through the public HTTPS tunnel, including secure WebSocket streaming.
- JavaScript syntax check passed.
- Browser verified: live stream, nominal overview, scenario injection, inferred origin, dependency forecast, strategy cards, and focus layout. A 390px iframe viewport verified responsive behavior; action wrapping and leaf-label overlap were corrected during visual review.

## Boundaries judges should understand

- Synthetic metrics, logs and actions; no real infrastructure control.
- Risk and evidence strength are heuristic scores; ETA is a slope estimate.
- Recovery simulation has access to current simulated fault state.
- Five-action optimization over 40 seconds, with assumed rather than measured downtime.
- Export is the current buffered snapshot; durable incident storage is future work.
- Shared memory-only sandbox; visitors can affect each other and server restart clears state.
- Public tunnel depends on the local machine and existing tunnel process.

## Additional evidence from the second polish pass

- Playback controls make the full cascade explainable one tick at a time and allow honest, visibly accelerated recovery during short presentations.
- Service health, latency, error rate and CPU trends use observed samples, excluding the seeded reference history.
- Five selectable counterfactual trajectories can be compared visually with no action. The applied-action view preserves the forecast and adds observed samples.
- The incident journal preserves the initial inferred origin and measures detection latency, peak affected/failed counts, recovery duration, and healthy-warning-to-failure lead time.
- 20 engine/runtime tests cover these contracts, including exact stepping, no background advance while paused, retained inferred origin, warning-before-failure ordering, and same-model forecast/observed agreement.
