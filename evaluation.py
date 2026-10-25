"""Reproducible paired synthetic experiments; no live-sandbox mutation or production claim."""

import copy
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
import engine
from runtime import SCENARIOS
from simulator import Simulator

ROOT = Path(__file__).resolve().parent
EVIDENCE_PATH = ROOT / "data/evaluation.json"
EVALUATION_SEEDS = (101, 203, 307, 409, 503, 607, 709, 811, 907, 1009)
POLICIES = ("predictive", "reactive", "no_action", "single_action")


def implementation_fingerprint():
    digest = hashlib.sha256()
    for name in ("simulator.py", "engine.py", "runtime.py", "evaluation.py"):
        digest.update(name.encode())
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()


def _run_arm(initial, mode, horizon_ticks=80):
    sim = copy.deepcopy(initial)
    action = None
    actions = []
    last_action_tick = None
    isolation_service_s = 0
    service_unavailable_s = 0
    first_origin = None
    gateway_failed_s = 0
    service_failed_s = 0
    peak_failed = 0
    ever_failed = set()
    trajectory = []
    for _ in range(horizon_ticks):
        sim.tick()
        failed = [name for name, s in sim.services.items() if s.state == "failed"]
        isolated = {
            name for name, s in sim.services.items() if s.isolated_until > sim.tick_no
        }
        isolation_service_s += 2 * len(isolated)
        service_unavailable_s += 2 * len(set(failed) | isolated)
        gateway_failed_s += 2 * ("api-gateway" in failed)
        service_failed_s += 2 * len(failed)
        peak_failed = max(peak_failed, len(failed))
        ever_failed.update(failed)
        trajectory.append(
            {
                "seconds": sim.tick_no * 2,
                "failed": len(failed),
                "gateway_failed": "api-gateway" in failed,
            }
        )
        if mode == "no_action" and first_origin is not None:
            continue
        if action is not None and mode == "single_action":
            continue
        if (
            last_action_tick is not None
            and sim.tick_no - last_action_tick < engine.HORIZON
        ):
            continue
        if (
            mode == "reactive"
            and first_origin is not None
            and sim.services["api-gateway"].state != "failed"
        ):
            continue
        # The detector sees metrics and topology only; injected target/type are not passed in.
        risk, own = engine.cascade_risk(sim.services, sim.tick_no)
        origin = engine.root_cause(sim.services, own)
        if first_origin is None and origin:
            first_origin = {"service": origin["service"], "seconds": sim.tick_no * 2}
        exposed_healthy = any(
            p["state"] == "healthy"
            for p in engine.predict_next_failures(sim.services, risk, top=17)
        )
        trigger = (
            mode in ("predictive", "single_action")
            and origin
            and (exposed_healthy or sim.services["api-gateway"].state == "failed")
        ) or (
            mode == "reactive"
            and origin
            and sim.services["api-gateway"].state == "failed"
        )
        if not trigger:
            continue
        ranked, _ = engine.recommend_strategies(sim, origin["service"])
        choice = next(
            (r for r in ranked if r["eligible"] and r["risk_reduction"] > 0), None
        )
        if choice:
            current = {
                "seconds": sim.tick_no * 2,
                "service": origin["service"],
                "strategy": choice["strategy"],
            }
            action = action or current
            actions.append(current)
            last_action_tick = sim.tick_no
            sim.apply_fix(origin["service"], choice["strategy"])
    return {
        "action": action,
        "actions": actions,
        "first_origin": first_origin,
        "isolation_service_s": isolation_service_s,
        "service_unavailable_s": service_unavailable_s,
        "gateway_failed_s": gateway_failed_s,
        "service_failed_s": service_failed_s,
        "peak_failed": peak_failed,
        "ever_failed": sorted(ever_failed),
        "trajectory": trajectory,
    }


def _summary(cases):
    rows = {}
    for mode in POLICIES:
        arms = [case["arms"][mode] for case in cases]
        actions = [a["action"]["seconds"] for a in arms if a["action"]]
        rows[mode] = {
            "mean_gateway_failed_s": round(
                statistics.mean(a["gateway_failed_s"] for a in arms), 2
            ),
            "mean_service_failed_s": round(
                statistics.mean(a["service_failed_s"] for a in arms), 2
            ),
            "mean_isolation_service_s": round(
                statistics.mean(a["isolation_service_s"] for a in arms), 2
            ),
            "mean_service_unavailable_s": round(
                statistics.mean(a["service_unavailable_s"] for a in arms), 2
            ),
            "mean_peak_failed": round(
                statistics.mean(a["peak_failed"] for a in arms), 2
            ),
            "median_action_s": statistics.median(actions) if actions else None,
        }

    def reduction(key):
        reference = rows["reactive"][key]
        return (
            round(100 * (reference - rows["predictive"][key]) / reference, 1)
            if reference
            else None
        )

    first_hits = sum(
        case["arms"]["no_action"]["first_origin"] is not None
        and case["arms"]["no_action"]["first_origin"]["service"] == case["service"]
        for case in cases
    )
    return {
        "policies": rows,
        "gateway_failure_reduction_pct": reduction("mean_gateway_failed_s"),
        "service_failure_reduction_pct": reduction("mean_service_failed_s"),
        "service_unavailability_reduction_pct": reduction("mean_service_unavailable_s"),
        "first_origin_correct": first_hits,
        "case_count": len(cases),
    }


def run_suite(seeds=EVALUATION_SEEDS, scenarios=None, horizon_ticks=80):
    scenarios = tuple(scenarios or SCENARIOS)
    cases = []
    for scenario in scenarios:
        spec = SCENARIOS[scenario]
        for seed in seeds:
            sim = Simulator(seed=seed)
            sim.inject_chaos(
                spec["service"], severity=0.13, fault_kind=spec["fault_kind"]
            )
            arms = {mode: _run_arm(sim, mode, horizon_ticks) for mode in POLICIES}
            cases.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "service": spec["service"],
                    "fault_kind": spec["fault_kind"],
                    "arms": arms,
                }
            )
    grouped = {
        name: _summary([c for c in cases if c["scenario"] == name])
        for name in scenarios
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "implementation_sha256": implementation_fingerprint(),
        "scope": "Paired synthetic experiments. Not a production accuracy or availability benchmark.",
        "method": {
            "seeds": list(seeds),
            "horizon_s": horizon_ticks * 2,
            "design_seed": 42,
            "policy": {"max_downtime_s": 60, "standby_available": True},
            "replanning": "Predictive and reactive re-evaluate after a 40s cooldown. Single-action control intervenes only once.",
            "isolation": "Isolation time is reported separately and counted in unavailable service-seconds; a healthy gateway does not imply every feature works.",
            "predictive_trigger": "Inferred origin plus a still-healthy exposed caller",
            "reactive_trigger": "Wait until the gateway is failed, then use the same planner",
            "comparison": "Same initial state and fixed per-tick physical random draws; logging uses a separate stream.",
            "costs": "Counts modelled failed time; assumed action downtime is used by the planner but is not added as an observed outage.",
        },
        "summary": _summary(cases),
        "by_scenario": grouped,
        "cases": cases,
    }


def load_evidence():
    if not EVIDENCE_PATH.exists():
        return {
            "status": "missing",
            "message": "Run python scripts/evaluate.py to generate the evidence.",
        }
    report = json.loads(EVIDENCE_PATH.read_text())
    report["status"] = (
        "current"
        if report["implementation_sha256"] == implementation_fingerprint()
        else "stale"
    )
    if report["status"] == "stale":
        report["message"] = (
            "The implementation changed. Regenerate this evidence before using its results."
        )
    return report
