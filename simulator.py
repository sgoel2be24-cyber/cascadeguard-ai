"""Microservice topology + failure cascade simulator.

Simulates a realistic distributed system: each service emits metrics
(latency, error rate, cpu) and log lines every tick. Failures propagate
along dependency edges, producing cascading outages.
"""

import random
import time
from collections import deque

# service name -> list of services it DEPENDS ON (downstream deps)
TOPOLOGY = {
    "api-gateway": ["auth-service", "order-service", "product-service"],
    "auth-service": ["user-db", "redis-cache"],
    "order-service": ["payment-service", "inventory-service", "order-db"],
    "product-service": ["product-db", "search-service"],
    "payment-service": ["payment-db", "fraud-detector"],
    "inventory-service": ["inventory-db", "message-queue"],
    "search-service": ["elastic-cluster"],
    "fraud-detector": ["ml-model-store"],
    "user-db": [],
    "order-db": [],
    "product-db": [],
    "payment-db": [],
    "inventory-db": [],
    "redis-cache": [],
    "elastic-cluster": [],
    "message-queue": [],
    "ml-model-store": [],
}

# dependents: who depends on X (reverse edges) -> propagation direction
DEPENDENTS = {s: [] for s in TOPOLOGY}
for svc, deps in TOPOLOGY.items():
    for d in deps:
        DEPENDENTS[d].append(svc)


# layer assignment for layout (rough depth from edge)
def _layers():
    depth = {}

    def d(s):
        if s in depth:
            return depth[s]
        depth[s] = 0 if not TOPOLOGY[s] else 1 + max(d(x) for x in TOPOLOGY[s])
        return depth[s]

    for s in TOPOLOGY:
        d(s)
    return depth


LAYERS = _layers()

BASE_LATENCY = {  # ms baseline per service class
    "gateway": 40,
    "service": 60,
    "db": 15,
    "infra": 10,
}


def _base_latency(name):
    if "db" in name or "store" in name:
        return 15
    if "cache" in name or "queue" in name or "elastic" in name:
        return 10
    if "gateway" in name:
        return 40
    return 60


LOG_TEMPLATES = {
    "INFO": [
        "request completed status=200 latency={lat}ms",
        "health check passed",
        "connection pool stable ({pool} active)",
        "cache hit ratio {hit}%",
        "request completed status=201 latency={lat}ms",
    ],
    "WARN": [
        "elevated latency detected p99={lat}ms",
        "retrying upstream call (attempt {n})",
        "connection pool nearing capacity ({pool} active)",
        "slow query detected ({lat}ms)",
        "upstream {dep} responded slowly",
    ],
    "ERROR": [
        "upstream timeout calling {dep}",
        "500 Internal Server Error: {err}",
        "circuit breaker half-open for {dep}",
        "request failed after {n} retries",
        "database connection timeout",
        "OOM warning: memory at {mem}%",
    ],
    "CRITICAL": [
        "SERVICE UNAVAILABLE - all replicas down",
        "cascading failure: dependency {dep} unreachable",
        "fatal: connection pool exhausted",
        "unrecoverable error, entering degraded mode",
    ],
}

ERRORS = [
    "NullPointerException",
    "TimeoutError",
    "ConnectionRefused",
    "DeadlockDetected",
    "DiskFull",
    "TLSHandshakeFailure",
]


# Explicit digital-twin assumptions, not a table of recommended actions.
# The planner still scores complete rollouts under these effects and policy limits.
FAULT_PROFILES = {
    "replica": {
        "label": "Replica process failure",
        "detail": "A failed process can be restarted or replaced by a standby.",
    },
    "capacity": {
        "label": "Capacity exhaustion",
        "detail": "Demand exceeds capacity; moving the same load to another replica does not remove it.",
    },
    "deployment": {
        "label": "Deployment regression",
        "detail": "All replicas run the bad release; rollback removes the regression.",
    },
    "network": {
        "label": "Dependency partition",
        "detail": "Instance actions cannot repair the network; isolate callers while the partition persists.",
    },
}
RECOVERY_EFFECTS = {
    "replica": {
        "restart": (0.45, True),
        "failover": (0.70, True),
        "scale_out": (0.30, False),
        "rollback": (0.20, False),
    },
    "capacity": {
        "restart": (0.20, False),
        "failover": (0.25, False),
        "scale_out": (0.45, True),
        "rollback": (0.10, False),
    },
    "deployment": {
        "restart": (0.15, False),
        "failover": (0.20, False),
        "scale_out": (0.15, False),
        "rollback": (0.70, True),
    },
    "network": {
        "restart": (0, False),
        "failover": (0, False),
        "scale_out": (0, False),
        "rollback": (0, False),
    },
}


def recovery_effect(service, strategy):
    if strategy == "circuit_breaker":
        return {
            "heal": 0,
            "clears_fault": False,
            "note": "Temporarily shields callers; the source remains impaired.",
        }
    if service.fault is None:
        heal = {"restart": 0.45, "failover": 0.70, "scale_out": 0.30, "rollback": 0.55}[
            strategy
        ]
        return {
            "heal": heal,
            "clears_fault": False,
            "note": "No active fault remains; this trial models a health boost only.",
        }
    heal, clears = RECOVERY_EFFECTS[service.fault_kind][strategy]
    label = FAULT_PROFILES[service.fault_kind]["label"].lower()
    return {
        "heal": heal,
        "clears_fault": clears,
        "note": ("Removes the modeled " if clears else "Does not remove the modeled ")
        + label
        + ".",
    }


class Service:
    def __init__(self, name, rng=None, log_rng=None):
        self.rng = rng or random.Random()
        self.log_rng = log_rng or random.Random()
        self.fault_kind = "replica"
        self.fault = None
        self.isolated_until = 0
        self.name = name
        self.state = "healthy"  # healthy | degraded | critical | failed
        self.health = 1.0  # 1.0 perfect -> 0.0 dead
        self.latency = _base_latency(name)
        self.error_rate = 0.005
        self.cpu = self.rng.uniform(15, 35)
        self.mem = self.rng.uniform(20, 45)
        self.history = deque(maxlen=120)  # metric snapshots
        self.last_anomaly_tick = None

    def tick(self, tick_no, dep_health):
        """Advance one tick. dep_health = min health of direct dependencies."""
        base = _base_latency(self.name)
        # Fixed physical draws per tick; action branches do not shift future noise.
        drag_noise = self.rng.uniform(0.4, 1.0)
        fault_noise = self.rng.uniform(0.6, 1.0)
        metric_noise = self.rng.uniform(0.9, 1.1)

        # dependency-driven degradation: bad deps drag us down, but only
        # once they are genuinely unhealthy (gradual, observable cascade)
        if dep_health < 0.70:
            drag = ((0.70 - dep_health) / 0.70) * 0.30
            self.health = max(0.0, self.health - drag * drag_noise)

        # natural recovery toward healthy if deps fine and no injected fault
        if dep_health >= 0.70 and self.fault is None:
            self.health = min(1.0, self.health + 0.08)

        # injected fault decay
        if self.fault is not None:
            severity, ticks_left = self.fault
            self.health = max(0.0, self.health - severity * fault_noise)
            self.fault = (severity, ticks_left - 1)
            if ticks_left <= 0:
                self.fault = None

        h = self.health
        self.refresh_state()

        # metrics derive from health
        noise = metric_noise
        self.latency = base * (1 + (1 - h) ** 2 * 25) * noise
        self.error_rate = min(1.0, 0.005 + (1 - h) ** 2 * 0.9 * noise)
        self.cpu = min(100, 25 + (1 - h) * 70 * noise)
        self.mem = min(100, 35 + (1 - h) * 55 * noise)

        self.history.append(
            {
                "tick": tick_no,
                "latency": round(self.latency, 1),
                "error_rate": round(self.error_rate, 4),
                "health": round(h, 3),
                "cpu": round(self.cpu, 1),
                "mem": round(self.mem, 1),
            }
        )

    def refresh_state(self):
        self.state = (
            "healthy"
            if self.health > 0.8
            else "degraded"
            if self.health > 0.5
            else "critical"
            if self.health > 0.15
            else "failed"
        )

    def log_line(self, tick_no):
        deps = TOPOLOGY[self.name]
        dep = self.log_rng.choice(deps) if deps else "internal"
        lat = int(self.latency)
        ctx = {
            "lat": lat,
            "dep": dep,
            "n": self.log_rng.randint(1, 3),
            "pool": self.log_rng.randint(5, 50),
            "hit": self.log_rng.randint(70, 99),
            "mem": int(self.mem),
            "err": self.log_rng.choice(ERRORS),
        }
        if self.state == "healthy":
            level = "INFO" if self.log_rng.random() < 0.95 else "WARN"
        elif self.state == "degraded":
            level = self.log_rng.choice(["WARN", "WARN", "INFO", "ERROR"])
        elif self.state == "critical":
            level = self.log_rng.choice(["ERROR", "ERROR", "WARN", "CRITICAL"])
        else:
            level = "CRITICAL"
        msg = self.log_rng.choice(LOG_TEMPLATES[level]).format(**ctx)
        ts = time.strftime("%H:%M:%S")
        return {
            "tick": tick_no,
            "ts": ts,
            "level": level,
            "service": self.name,
            "msg": msg,
        }


class Simulator:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.log_rng = random.Random(self.rng.getrandbits(128))
        self.services = {
            name: Service(name, self.rng, self.log_rng) for name in TOPOLOGY
        }
        self.tick_no = 0
        self.logs = deque(maxlen=400)
        self.events = deque(maxlen=60)
        self.warmup()

    def reset(self, seed=None):
        self.__init__(seed)

    def warmup(self):
        # Synthetic healthy reference samples; never presented as observed history.
        for tick in range(-24, 0):
            for svc in self.services.values():
                svc.tick(tick, 1.0)

    def inject_chaos(self, service=None, severity=None, fault_kind="replica"):
        if fault_kind not in FAULT_PROFILES:
            raise ValueError("Unknown fault type")
        service = service or self.rng.choice(
            [s for s in TOPOLOGY if DEPENDENTS[s]]
        )  # pick something with dependents
        severity = severity or self.rng.uniform(0.10, 0.18)
        svc = self.services[service]
        svc.fault_kind = fault_kind
        svc.fault = (severity, self.rng.randint(25, 40))
        self.events.append(
            {
                "tick": self.tick_no,
                "type": "chaos",
                "service": service,
                "severity": round(severity, 2),
                "fault_kind": fault_kind,
            }
        )
        return service

    def apply_fix(self, service, strategy):
        if service not in self.services:
            raise ValueError("Unknown service")
        if strategy not in {
            "restart",
            "failover",
            "scale_out",
            "circuit_breaker",
            "rollback",
        }:
            raise ValueError("Unknown recovery strategy")
        svc = self.services[service]
        effect = recovery_effect(svc, strategy)
        svc.health = min(1.0, svc.health + effect["heal"])
        if effect["clears_fault"]:
            svc.fault = None
        elif strategy == "scale_out" and svc.fault and svc.fault_kind == "replica":
            svc.fault = (svc.fault[0] * 0.5, svc.fault[1])
        if strategy == "circuit_breaker":
            svc.isolated_until = self.tick_no + 20
        svc.refresh_state()
        self.events.append(
            {
                "tick": self.tick_no,
                "type": "fix",
                "service": service,
                "strategy": strategy,
            }
        )

    def tick(self):
        self.tick_no += 1
        previous = {n: s.health for n, s in self.services.items()}
        for name, svc in self.services.items():
            deps = TOPOLOGY[name]
            dep_health = min(
                (
                    previous[d]
                    for d in deps
                    if self.services[d].isolated_until <= self.tick_no
                ),
                default=1.0,
            )
            svc.tick(self.tick_no, dep_health)
            # emit 1-3 log lines per service per tick
            for _ in range(self.log_rng.randint(1, 2) if svc.state == "healthy" else 3):
                self.logs.append(svc.log_line(self.tick_no))

    def snapshot(self):
        return {
            "tick": self.tick_no,
            "services": {
                name: {
                    "state": s.state,
                    "fault_profile": s.fault_kind if s.fault else None,
                    "isolated": s.isolated_until > self.tick_no,
                    "health": round(s.health, 3),
                    "latency": round(s.latency, 1),
                    "error_rate": round(s.error_rate, 4),
                    "cpu": round(s.cpu, 1),
                    "mem": round(s.mem, 1),
                    "layer": LAYERS[name],
                    "deps": TOPOLOGY[name],
                    "dependents": DEPENDENTS[name],
                    "history": list(s.history)[-60:],
                }
                for name, s in self.services.items()
            },
            "logs": list(self.logs)[-80:],
            "events": list(self.events),
        }
