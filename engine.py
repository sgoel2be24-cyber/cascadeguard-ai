"""Explainable heuristics on synthetic telemetry, with simulator-backed recovery trials."""
import copy
import math
import statistics
from simulator import TOPOLOGY, DEPENDENTS

TICK_SECONDS = 2
HORIZON = 20
STRATEGIES = {
    'restart': {'downtime_s': 30, 'desc': 'Restart instances and clear the active fault'},
    'failover': {'downtime_s': 8, 'desc': 'Switch to a standby replica and clear the fault'},
    'scale_out': {'downtime_s': 0, 'desc': 'Add capacity and halve fault pressure'},
    'circuit_breaker': {'downtime_s': 0, 'desc': 'Isolate this dependency for 40s; source stays unhealthy'},
    'rollback': {'downtime_s': 20, 'desc': 'Revert deployment and clear the active fault'},
}


def anomaly_score(history, key):
    values = [h[key] for h in history]
    if len(values) < 15:
        return 0.0
    baseline = values[:-4][-40:]
    center = statistics.median(baseline)
    mad = statistics.median(abs(v - center) for v in baseline)
    floor = 0.003 if key == 'error_rate' else max(1.0, center * 0.05)
    z = (statistics.mean(values[-4:]) - center) / max(1.4826 * mad, floor)
    return round(max(0.0, min(1.0, (z - 2) / 8)), 3)


def trend_slope(history, key, window=8):
    vals = [h[key] for h in history][-window:]
    n = len(vals)
    if n < 3:
        return 0.0
    xm = (n - 1) / 2
    ym = sum(vals) / n
    return sum((i - xm) * (v - ym) for i, v in enumerate(vals)) / sum((i - xm)**2 for i in range(n))


def propagate(own, services=None, tick=0):
    risk = dict(own)
    for _ in TOPOLOGY:
        for name, deps in TOPOLOGY.items():
            active = [d for d in deps if services is None or services[d].isolated_until <= tick]
            contribution = 0.75 * max((risk[d] for d in active), default=0)
            risk[name] = own[name] + contribution * (1 - own[name])
    return risk


def cascade_risk(services, tick=0):
    own = {n: min(1, .45 * anomaly_score(s.history, 'error_rate') + .30 * anomaly_score(s.history, 'latency') + .55 * (1-s.health)) for n, s in services.items()}
    return {n: round(r, 3) for n, r in propagate(own, services, tick).items()}, own


def blast_radius(service):
    seen, stack = set(), [service]
    while stack:
        for name in DEPENDENTS[stack.pop()]:
            if name not in seen:
                seen.add(name)
                stack.append(name)
    return seen


def predict_next_failures(services, risk, top=4):
    out = []
    for name, s in services.items():
        if s.state == 'failed' or risk[name] < .18:
            continue
        falling = -trend_slope(s.history, 'health')
        eta = max(1, math.ceil((s.health-.15)/falling)) if falling > .005 else None
        out.append({'service': name, 'risk': risk[name], 'eta_ticks': eta,
                    'eta_label': f'~{eta*TICK_SECONDS}s' if eta else 'Dependency exposure', 'state': s.state})
    return sorted(out, key=lambda p: -p['risk'])[:top]


def root_cause(services, own):
    anomalous = {n for n, a in own.items() if a > .35}
    candidates = []
    for name in anomalous:
        s = services[name]
        explained = any(d in anomalous for d in TOPOLOGY[name])
        downstream = blast_radius(name) & anomalous
        strength = min(.98, .55 + .25 * own[name] + .04 * len(downstream))
        evidence = [f'Error rate {s.error_rate*100:.1f}% · latency {s.latency:.0f} ms',
                    f'Health {s.health*100:.0f}% · CPU {s.cpu:.0f}% · memory {s.mem:.0f}%',
                    'Anomalous dependencies also present' if explained else 'No anomalous direct dependency explains this signal']
        candidates.append({'service':name, 'confidence':round(strength,2),
                           'explained_by_upstream':explained,'affected_downstream':sorted(downstream),'evidence':evidence})
    candidates.sort(key=lambda c: (c['explained_by_upstream'], -c['confidence'], c['service']))
    return candidates[0] if candidates else None


def operational_risk(sim):
    return sum(propagate({n: 1-s.health for n,s in sim.services.items()}, sim.services, sim.tick_no).values()) / len(TOPOLOGY)


def forecast(sim, target=None, strategy=None):
    trial = copy.deepcopy(sim)
    if strategy:
        trial.apply_fix(target, strategy)
    risks = []
    for _ in range(HORIZON):
        trial.tick()
        risks.append(operational_risk(trial))
    return sum(risks)/len(risks), risks[-1]


def recommend_strategies(sim, target):
    baseline, baseline_end = forecast(sim)
    ranked = []
    for name,p in STRATEGIES.items():
        projected, ending = forecast(sim,target,name)
        reduction = max(0, baseline-projected)
        score = reduction / (1+p['downtime_s']/60)
        ranked.append({'strategy':name, **p, 'risk_reduction':round(reduction*100,1),
                       'projected_risk':round(projected*100,1),'end_risk':round(ending*100,1),'score':round(score*100,2)})
    ranked.sort(key=lambda r:-r['score'])
    return ranked, round(baseline*100,1)


def analyze(sim):
    risk, own = cascade_risk(sim.services,sim.tick_no)
    rc = root_cause(sim.services,own)
    recs, baseline = recommend_strategies(sim,rc['service']) if rc else ([],0)
    path = []
    if rc:
        frontier = [rc['service']]
        seen = set(frontier)
        while frontier:
            path.append(frontier)
            frontier = sorted({d for n in frontier for d in DEPENDENTS[n]} - seen)
            seen.update(frontier)
    return {'risk':risk,'own_anomaly':{n:round(v,3) for n,v in own.items()},
            'predictions':predict_next_failures(sim.services,risk),'root_cause':rc,
            'recommendations':recs,'system_risk':round(sum(risk.values()),3),
            'cascade_path':sorted(blast_radius(rc['service'])) if rc else [],
            'cascade_layers':path,'baseline_forecast':baseline,'horizon_s':HORIZON*TICK_SECONDS,
            'method':'Heuristic risk scores, not calibrated failure probabilities. ETA extrapolates recent health slope. Recovery trials use synthetic simulator state and identical random streams; estimates are not production guarantees.'}
