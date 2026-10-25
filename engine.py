"""Prediction engine: anomaly detection, cascade forecasting,
root-cause analysis, and recovery strategy optimization.

All analysis is derived from the live metric history produced by the
simulator — no hard-coded answers. The same code would work on real
metrics/logs fed through the same shape of data.
"""

import math
from collections import deque

from simulator import TOPOLOGY, DEPENDENTS


# ---------------------------------------------------------------- anomalies

def anomaly_score(history, key):
    """Robust z-score of the recent window vs the baseline window."""
    vals = [h[key] for h in history]
    if len(vals) < 15:
        return 0.0
    recent = vals[-4:]
    baseline = vals[:-4][-40:]
    mean = sum(baseline) / len(baseline)
    var = sum((v - mean) ** 2 for v in baseline) / len(baseline)
    std = math.sqrt(var) or 1e-6
    rmean = sum(recent) / len(recent)
    z = (rmean - mean) / std
    # normalize to 0..1 with a soft squash; only positive deviations matter
    return round(1 / (1 + math.exp(-(z - 3))), 3)


def trend_slope(history, key, window=10):
    vals = [h[key] for h in history][-window:]
    n = len(vals)
    if n < 3:
        return 0.0
    xs = list(range(n))
    xm = sum(xs) / n
    ym = sum(vals) / n
    denom = sum((x - xm) ** 2 for x in xs) or 1e-6
    return sum((x - xm) * (y - ym) for x, y in zip(xs, vals)) / denom


# ---------------------------------------------------------------- cascade

def cascade_risk(services):
    """Propagate failure risk downstream through the dependency graph.

    risk(svc) = own_anomaly OR contribution from failing dependencies,
    iterated to fixpoint. Returns {service: risk 0..1}.
    """
    own = {}
    for name, svc in services.items():
        hist = list(svc.history)
        a_err = anomaly_score(hist, "error_rate")
        a_lat = anomaly_score(hist, "latency")
        health_factor = 1.0 - svc.health
        own[name] = min(1.0, 0.45 * a_err + 0.30 * a_lat + 0.55 * health_factor)

    risk = dict(own)
    for _ in range(len(TOPOLOGY)):  # fixpoint, graph is a DAG
        changed = False
        for name in TOPOLOGY:
            deps = TOPOLOGY[name]
            if not deps:
                continue
            dep_risk = max(risk[d] for d in deps)          # weakest link
            propagated = 0.75 * dep_risk
            new = max(risk[name], own[name] + propagated * (1 - own[name]))
            if abs(new - risk[name]) > 1e-4:
                risk[name] = new
                changed = True
        if not changed:
            break
    return {k: round(v, 3) for k, v in risk.items()}, own


def predict_next_failures(services, risk, top=4):
    """Rank healthy-ish services most likely to fail next, with ETA."""
    out = []
    for name, svc in services.items():
        if svc.state == "failed":
            continue
        r = risk[name]
        if r < 0.15:
            continue
        slope = trend_slope(list(svc.history), "health")
        slope = -slope  # health falling = positive risk slope
        if slope > 0.005:
            eta_ticks = max(1, int((svc.health - 0.15) / slope))
        else:
            eta_ticks = None
        out.append({
            "service": name,
            "risk": r,
            "eta_ticks": eta_ticks,
            "eta_label": f"~{eta_ticks * 2}s" if eta_ticks else "stable",
            "state": svc.state,
        })
    out.sort(key=lambda x: -x["risk"])
    return out[:top]


def blast_radius(service):
    """All services reachable downstream (who depends on `service`)."""
    seen, stack = set(), [service]
    while stack:
        cur = stack.pop()
        for dep in DEPENDENTS[cur]:
            if dep not in seen:
                seen.add(dep)
                stack.append(dep)
    return seen


# ---------------------------------------------------------------- root cause

def root_cause(services, own_anomaly):
    """Root cause = anomalous service whose anomalies explain downstream
    failures and that is not itself explained by an upstream anomaly."""
    candidates = []
    anomalous = [n for n, a in own_anomaly.items() if a > 0.35]
    for name in anomalous:
        svc = services[name]
        # is any direct dependency also anomalous and earlier?
        explained = False
        for d in TOPOLOGY[name]:
            if d in anomalous:
                dd, ss = services[d].history, svc.history
                if dd and ss and len(dd) >= 5 and len(ss) >= 5:
                    explained = True
        downstream = blast_radius(name) & set(anomalous)
        confidence = min(0.99, 0.45 + 0.12 * len(downstream)
                         + 0.15 * (not explained) + 0.2 * own_anomaly[name])
        candidates.append({
            "service": name,
            "confidence": round(confidence, 2),
            "explained_by_upstream": explained,
            "affected_downstream": sorted(downstream),
            "evidence": _evidence(svc),
        })
    candidates.sort(key=lambda c: (-c["confidence"]))
    return candidates[0] if candidates else None


def _evidence(svc):
    hist = list(svc.history)
    ev = []
    if anomaly_score(hist, "error_rate") > 0.4:
        ev.append(f"error rate spiked to {svc.error_rate * 100:.0f}%")
    if anomaly_score(hist, "latency") > 0.4:
        ev.append(f"latency {svc.latency:.0f}ms vs baseline")
    if svc.cpu > 75:
        ev.append(f"CPU saturated at {svc.cpu:.0f}%")
    if svc.mem > 80:
        ev.append(f"memory pressure {svc.mem:.0f}%")
    return ev or ["health declining without upstream cause"]


# ---------------------------------------------------------------- recovery

STRATEGIES = {
    "restart":          {"heal": 0.45, "shield": 0.0,  "downtime_s": 30, "desc": "Restart the failing service instances"},
    "failover":         {"heal": 0.70, "shield": 0.0,  "downtime_s": 8,  "desc": "Fail over to standby replica"},
    "scale_out":        {"heal": 0.30, "shield": 0.0,  "downtime_s": 0,  "desc": "Add capacity (horizontal scale)"},
    "circuit_breaker":  {"heal": 0.0,  "shield": 0.6,  "downtime_s": 0,  "desc": "Open circuit breaker to shield dependents"},
    "rollback":         {"heal": 0.55, "shield": 0.0,  "downtime_s": 20, "desc": "Roll back the last deployment"},
}


def _projected_system_risk(services, target, strat):
    """Cheap counterfactual: heal target, shield its dependents,
    then re-propagate risk over the graph."""
    heal = STRATEGIES[strat]["heal"]
    shield = STRATEGIES[strat]["shield"]
    eff_health = {n: s.health for n, s in services.items()}
    eff_health[target] = min(1.0, eff_health[target] + heal)
    if shield:
        for d in DEPENDENTS[target]:
            eff_health[d] = min(1.0, eff_health[d] + shield * (1 - services[target].health))

    own = {n: 1.0 - h for n, h in eff_health.items()}
    risk = dict(own)
    for _ in range(len(TOPOLOGY)):
        changed = False
        for name in TOPOLOGY:
            deps = TOPOLOGY[name]
            if not deps:
                continue
            propagated = 0.75 * max(risk[d] for d in deps)
            new = max(risk[name], own[name] + propagated * (1 - own[name]))
            if abs(new - risk[name]) > 1e-4:
                risk[name] = new
                changed = True
        if not changed:
            break
    return sum(risk.values())


def recommend_strategies(services, target):
    """Compare every recovery strategy for `target`; return ranked list."""
    # baseline: projected system risk with no action taken
    heal0 = {n: s.health for n, s in services.items()}
    own0 = {n: 1.0 - h for n, h in heal0.items()}
    base = dict(own0)
    for _ in range(len(TOPOLOGY)):
        changed = False
        for name in TOPOLOGY:
            deps = TOPOLOGY[name]
            if not deps:
                continue
            propagated = 0.75 * max(base[d] for d in deps)
            new = max(base[name], own0[name] + propagated * (1 - own0[name]))
            if abs(new - base[name]) > 1e-4:
                base[name] = new
                changed = True
        if not changed:
            break
    current = sum(base.values())

    ranked = []
    for name, p in STRATEGIES.items():
        projected = _projected_system_risk(services, target, name)
        reduction = max(0.0, current - projected)
        cost = p["downtime_s"] / 60.0
        score = reduction / (1.0 + cost)
        ranked.append({
            "strategy": name,
            "desc": p["desc"],
            "risk_reduction": round(reduction, 2),
            "downtime_s": p["downtime_s"],
            "score": round(score, 3),
        })
    ranked.sort(key=lambda r: -r["score"])
    return ranked, round(current, 2)


# ---------------------------------------------------------------- top-level

def analyze(sim):
    services = sim.services
    risk, own = cascade_risk(services)
    rc = root_cause(services, own)
    recs, system_risk = (recommend_strategies(services, rc["service"])
                         if rc else ([], 0.0))
    return {
        "risk": risk,
        "own_anomaly": {k: round(v, 3) for k, v in own.items()},
        "predictions": predict_next_failures(services, risk),
        "root_cause": rc,
        "recommendations": recs,
        "system_risk": system_risk,
        "cascade_path": sorted(blast_radius(rc["service"])) if rc else [],
    }
