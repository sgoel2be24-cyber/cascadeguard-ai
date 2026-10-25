"""Playback, incident evidence and observed outcomes, independent of the HTTP layer.

The journal records inferred evidence separately from injected-fault ground truth.
It does not feed injection metadata into the detector or change simulation randomness.
"""

import copy
import uuid
from collections import deque
import engine
from simulator import Simulator, TOPOLOGY, FAULT_PROFILES

SCENARIOS = {
    "payment": {
        "service": "payment-db",
        "fault_kind": "replica",
        "label": "Payment replica failure",
    },
    "cache": {
        "service": "redis-cache",
        "fault_kind": "capacity",
        "label": "Cache capacity exhaustion",
    },
    "search": {
        "service": "elastic-cluster",
        "fault_kind": "deployment",
        "label": "Search deployment regression",
    },
    "network": {
        "service": "message-queue",
        "fault_kind": "network",
        "label": "Queue network partition",
    },
}


class PolicyViolation(ValueError):
    pass


class Runtime:
    def __init__(self, seed=42):
        self.sim = Simulator(seed=seed)
        self.paused = False
        self.speed = 1
        self.policy = {"max_downtime_s": 60, "standby_available": True}
        self.guard_enabled = False
        self.guard_last_action_tick = None
        self.world_id = uuid.uuid4().hex
        self.revision = 0
        self.incident = None
        self._incident_sequence = 0
        self.last_decision = None
        self.incidents = deque(maxlen=8)
        self._cached = None
        self._stable_ticks = 0

    def invalidate(self):
        self.revision += 1
        self._cached = None

    def reset(self, preserve_controls=False):
        paused, speed, policy, guard = (
            self.paused,
            self.speed,
            dict(self.policy),
            self.guard_enabled,
        )
        self.__init__()
        if preserve_controls:
            self.paused, self.speed, self.policy, self.guard_enabled = (
                paused,
                speed,
                policy,
                guard,
            )

    def control(self, paused=None, speed=None):
        if speed is not None and (isinstance(speed, bool) or speed not in (1, 2, 4)):
            raise ValueError("Playback speed must be 1, 2, or 4")
        if paused is not None:
            if not isinstance(paused, bool):
                raise ValueError("Paused must be a boolean")
            self.paused = paused
        if speed is not None:
            self.speed = speed
        self.invalidate()

    def scenario(self, name):
        if name not in SCENARIOS:
            raise ValueError("Unknown scenario")
        self.reset(preserve_controls=True)
        spec = SCENARIOS[name]
        return self.inject(
            spec["service"], severity=0.13, fault_kind=spec["fault_kind"]
        )

    def _interrupt_decision(self, reason):
        if self.last_decision and self.last_decision["status"] == "observing":
            self.last_decision["status"] = "interrupted"
            self.last_decision["note"] = reason

    def inject(self, service=None, severity=None, fault_kind="replica"):
        if fault_kind not in FAULT_PROFILES:
            raise ValueError("Unknown fault type")
        if service is not None and service not in TOPOLOGY:
            raise ValueError("Unknown service")
        self._interrupt_decision(
            "Another fault changed the forecast starting assumptions."
        )
        target = self.sim.inject_chaos(service, severity, fault_kind)
        if self.incident is None or self.incident["phase"] == "resolved":
            if self.incident:
                self.incidents.append(copy.deepcopy(self.incident))
            self._incident_sequence += 1
            self.incident = {
                "id": f"INC-{self._incident_sequence:03d}",
                "start_tick": self.sim.tick_no,
                "detected_tick": None,
                "initial_origin": None,
                "origin_evidence": [],
                "phase": "observing",
                "first_action_tick": None,
                "resolved_tick": None,
                "peak_affected": 0,
                "peak_failed": 0,
                "peak_operational_risk": 0,
                "warnings": {},
                "failures": {},
                "actions": [],
                "triggers": [],
            }
        self.incident["triggers"].append(
            {"tick": self.sim.tick_no, "service": target, "fault_kind": fault_kind}
        )
        self._stable_ticks = 0
        self.invalidate()
        return target

    def fix(self, service, strategy, initiated_by="operator"):
        if service not in TOPOLOGY or strategy not in engine.STRATEGIES:
            raise ValueError("Unknown service or recovery strategy")
        blocked = engine.policy_block_reason(strategy, self.policy)
        if blocked:
            raise PolicyViolation(blocked)
        before = engine.forecast_series(self.sim)
        projected = engine.forecast_series(self.sim, service, strategy)
        self._interrupt_decision(
            "Another recovery action changed the forecast assumptions."
        )
        self.sim.apply_fix(service, strategy)
        self.sim.events[-1]["initiated_by"] = initiated_by
        self.guard_last_action_tick = self.sim.tick_no
        self.last_decision = {
            "service": service,
            "strategy": strategy,
            "initiated_by": initiated_by,
            "tick": self.sim.tick_no,
            "baseline": before["trajectory"],
            "policy": dict(self.policy),
            "projected": projected["trajectory"],
            "observed": [],
            "status": "observing",
            "note": "Same-model consistency check; this is not external validation.",
            "mean_absolute_error": None,
        }
        if self.incident and self.incident["phase"] != "resolved":
            item = self.incident
            if item["first_action_tick"] is None:
                item["first_action_tick"] = self.sim.tick_no
            item["actions"].append(
                {
                    "tick": self.sim.tick_no,
                    "service": service,
                    "strategy": strategy,
                    "initiated_by": initiated_by,
                }
            )
            item["phase"] = "recovering"
        self.invalidate()

    def set_policy(self, max_downtime_s=None, standby_available=None):
        if max_downtime_s is not None:
            if (
                isinstance(max_downtime_s, bool)
                or not isinstance(max_downtime_s, int)
                or not 0 <= max_downtime_s <= 120
            ):
                raise ValueError(
                    "Downtime budget must be an integer from 0 to 120 seconds"
                )
        if standby_available is not None and not isinstance(standby_available, bool):
            raise ValueError("Standby availability must be a boolean")
        if max_downtime_s is not None:
            self.policy["max_downtime_s"] = max_downtime_s
        if standby_available is not None:
            self.policy["standby_available"] = standby_available
        self.invalidate()

    def step(self):
        if not self.paused:
            raise ValueError("Pause the simulation before stepping")
        self.advance(force=True)

    def advance(self, force=False):
        if self.paused and not force:
            return False
        self.sim.tick()
        self._observe()
        self._maybe_guard()
        self.invalidate()
        return True

    def set_guard(self, enabled):
        if not isinstance(enabled, bool):
            raise ValueError("Guard enabled must be a boolean")
        self.guard_enabled = enabled
        self.invalidate()

    def prepare_demo(self):
        self.reset()
        self.paused = True
        self.scenario("payment")
        for _ in range(8):
            self.step()

    def _maybe_guard(self):
        if (
            not self.guard_enabled
            or not self.incident
            or self.incident["phase"] == "resolved"
        ):
            return
        if (
            self.guard_last_action_tick is not None
            and self.sim.tick_no - self.guard_last_action_tick < engine.HORIZON
        ):
            return
        risk, own = engine.cascade_risk(self.sim.services, self.sim.tick_no)
        origin = engine.root_cause(self.sim.services, own)
        exposed = any(
            p["state"] == "healthy"
            for p in engine.predict_next_failures(self.sim.services, risk, top=17)
        )
        if not origin or not (
            exposed or self.sim.services["api-gateway"].state == "failed"
        ):
            return
        ranked, _ = engine.recommend_strategies(
            self.sim, origin["service"], policy=self.policy
        )
        choice = next(
            (r for r in ranked if r["eligible"] and r["risk_reduction"] > 0), None
        )
        if choice:
            self.fix(origin["service"], choice["strategy"], initiated_by="guard")

    def _observe(self):
        s = self.sim
        operational = engine.operational_risk(s) * 100
        decision = self.last_decision
        if decision and decision["status"] == "observing":
            elapsed = (s.tick_no - decision["tick"]) * 2
            if elapsed <= engine.HORIZON * 2:
                decision["observed"].append(
                    {"seconds": elapsed, "risk": round(operational, 3)}
                )
            if elapsed >= engine.HORIZON * 2:
                decision["status"] = "complete"
                expected = {x["seconds"]: x["risk"] for x in decision["projected"]}
                differences = [
                    abs(v["risk"] - expected[v["seconds"]])
                    for v in decision["observed"]
                ]
                decision["mean_absolute_error"] = (
                    round(sum(differences) / len(differences), 3)
                    if differences
                    else None
                )
        item = self.incident
        if not item or item["phase"] == "resolved":
            return
        risks, own = engine.cascade_risk(s.services, s.tick_no)
        rc = engine.root_cause(s.services, own)
        if rc and item["detected_tick"] is None:
            item["detected_tick"] = s.tick_no
            item["initial_origin"] = rc["service"]
            item["origin_evidence"] = rc["evidence"]
            if item["phase"] == "observing":
                item["phase"] = "detected"
        affected = sum(x.state != "healthy" for x in s.services.values())
        failed = sum(x.state == "failed" for x in s.services.values())
        item["peak_affected"] = max(item["peak_affected"], affected)
        item["peak_failed"] = max(item["peak_failed"], failed)
        item["peak_operational_risk"] = round(
            max(item["peak_operational_risk"], operational), 3
        )
        for prediction in engine.predict_next_failures(
            s.services, risks, top=len(TOPOLOGY)
        ):
            name = prediction["service"]
            if s.services[name].state == "healthy" and name not in item["warnings"]:
                item["warnings"][name] = {
                    "tick": s.tick_no,
                    "score": prediction["risk"],
                }
        for name, service in s.services.items():
            if service.state == "failed" and name not in item["failures"]:
                item["failures"][name] = {
                    "tick": s.tick_no,
                    "warning_tick": item["warnings"].get(name, {}).get("tick"),
                }
        clear = (
            affected == 0
            and rc is None
            and all(x.fault is None for x in s.services.values())
        )
        self._stable_ticks = self._stable_ticks + 1 if clear else 0
        if self._stable_ticks >= 3:
            item["phase"] = "resolved"
            item["resolved_tick"] = s.tick_no

    def _incident_snapshot(self):
        if not self.incident:
            return None
        item = copy.deepcopy(self.incident)
        end = (
            item["resolved_tick"]
            if item["resolved_tick"] is not None
            else self.sim.tick_no
        )
        item["duration_s"] = (end - item["start_tick"]) * 2
        item["detection_s"] = (
            (item["detected_tick"] - item["start_tick"]) * 2
            if item["detected_tick"] is not None
            else None
        )
        item["recovery_s"] = (
            (end - item["first_action_tick"]) * 2
            if item["first_action_tick"] is not None
            else None
        )
        item["verified_leads"] = [
            {"service": name, "lead_s": (failure["tick"] - failure["warning_tick"]) * 2}
            for name, failure in item["failures"].items()
            if failure["warning_tick"] is not None
            and failure["tick"] > failure["warning_tick"]
        ]
        return item

    def state(self):
        if self._cached is None:
            self._cached = {
                **self.sim.snapshot(),
                "analysis": engine.analyze(self.sim, self.policy),
                "policy": dict(self.policy),
                "guard": {
                    "enabled": self.guard_enabled,
                    "last_action_tick": self.guard_last_action_tick,
                    "cooldown_s": engine.HORIZON * 2,
                },
                "scenarios": SCENARIOS,
                "fault_profiles": FAULT_PROFILES,
                "mode": "synthetic",
                "tick_seconds": 2,
                "world_id": self.world_id,
                "revision": self.revision,
                "playback": {
                    "paused": self.paused,
                    "speed": self.speed,
                    "wall_tick_seconds": 2 / self.speed,
                },
                "incident": self._incident_snapshot(),
                "recent_incidents": list(self.incidents),
                "last_decision": copy.deepcopy(self.last_decision),
            }
        return self._cached
