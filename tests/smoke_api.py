"""Exercise a disposable synthetic sandbox, then reset it on success.
Usage: python tests/smoke_api.py http://127.0.0.1:8001
"""

import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
import websockets

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8001"
checks = []


def request(path, body=None, expected=200):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            code = r.status
            data = r.read()
            headers = r.headers
    except urllib.error.HTTPError as e:
        code = e.code
        data = e.read()
        headers = e.headers
    assert code == expected, (path, code, data[:200])
    checks.append((path, code))
    return json.loads(data) if "json" in headers.get("Content-Type", "") else data


request("/healthz")
request("/api/reset", {})
assert request("/api/state")["analysis"]["system_risk"] == 0
request("/api/step", {}, 409)
request("/api/control", {"speed": 3}, 422)
request("/api/control", {"unexpected": True}, 422)
request("/api/chaos", {"service": "bad"}, 422)
request("/api/fix", {"service": "payment-db", "strategy": "bad"}, 422)
request("/api/fix", {"service": "bad", "strategy": "restart"}, 422)
request("/api/scenario", {"scenario": "bad"}, 422)
request("/api/fix", {}, 422)
request("/api/control", {"paused": True, "speed": 4})
before = request("/api/state")["tick"]
time.sleep(0.7)
assert request("/api/state")["tick"] == before, "Paused world advanced"
request("/api/scenario", {"scenario": "payment"})
s = request("/api/state")
assert s["tick"] == 0 and s["playback"] == {
    "paused": True,
    "speed": 4,
    "wall_tick_seconds": 0.5,
}
for _ in range(4):
    request("/api/step", {})
s = request("/api/state")
assert s["tick"] == 4
assert s["analysis"]["root_cause"]["service"] == "payment-db"
assert s["analysis"]["predictions"]
assert len(s["analysis"]["recommendations"]) == 5
for _ in range(12):
    request("/api/step", {})
s = request("/api/state")
assert s["incident"]["initial_origin"] == "payment-db"
assert s["incident"]["verified_leads"], "No warning preceded an observed failure"
strategy = s["analysis"]["recommendations"][0]["strategy"]
request("/api/fix", {"service": "payment-db", "strategy": strategy})
for _ in range(20):
    request("/api/step", {})
s = request("/api/state")
assert s["last_decision"]["status"] == "complete"
assert s["last_decision"]["mean_absolute_error"] == 0
assert len(s["last_decision"]["observed"]) == 20
for _ in range(60):
    if s["incident"]["phase"] == "resolved":
        break
    request("/api/step", {})
    s = request("/api/state")
assert s["incident"]["phase"] == "resolved"
assert s["incident"]["recovery_s"] > 0
report = request("/api/report")
assert report["project"] == "CascadeGuard AI"
assert report["incident"]["resolved_tick"] is not None
assert report["last_decision"]["projected"]


async def websocket_check():
    async with websockets.connect(base.replace("http", "ws", 1) + "/ws") as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), 5))
        second = json.loads(await asyncio.wait_for(ws.recv(), 5))
        assert len(first["services"]) == 17
        assert first["mode"] == "synthetic"
        assert first["playback"]["paused"]
        assert first["tick"] == second["tick"], "Paused WebSocket tick changed"


asyncio.run(websocket_check())
request("/api/reset", {})
print(
    json.dumps(
        {
            "checks": len(checks) + 1,
            "status": "passed",
            "websocket": "passed",
            "origin": report["incident"]["initial_origin"],
            "observed_warning_leads": report["incident"]["verified_leads"],
            "recovery_s": report["incident"]["recovery_s"],
            "forecast_error_risk_pts": report["last_decision"]["mean_absolute_error"],
        },
        indent=2,
    )
)
