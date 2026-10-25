"""Run against a disposable local preview: python tests/smoke_api.py http://127.0.0.1:8001.
Mutates only the specified synthetic sandbox. Not run by offline CI.
"""
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
import websockets

base=sys.argv[1].rstrip('/') if len(sys.argv)>1 else 'http://127.0.0.1:8001'
checks=[]
def request(path,body=None,expected=200):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:
            code=r.status;data=r.read();headers=r.headers
    except urllib.error.HTTPError as e:code=e.code;data=e.read();headers=e.headers
    assert code==expected,(path,code,data[:200])
    checks.append((path,code))
    return json.loads(data) if 'json' in headers.get('Content-Type','') else data

request('/healthz')
request('/api/reset',{})
assert request('/api/state')['analysis']['system_risk']==0
request('/api/chaos',{'service':'bad'},422)
request('/api/fix',{'service':'payment-db','strategy':'bad'},422)
request('/api/fix',{'service':'bad','strategy':'restart'},422)
request('/api/scenario',{'scenario':'bad'},422)
request('/api/fix',{},422)
request('/api/scenario',{'scenario':'payment'})
time.sleep(9)
a=request('/api/state')['analysis']
assert a['root_cause']['service']=='payment-db',a
assert a['predictions']
assert len(a['recommendations'])==5
request('/api/fix',{'service':a['root_cause']['service'],'strategy':a['recommendations'][0]['strategy']})
assert request('/api/report')['project']=='CascadeGuard AI'
async def websocket_check():
    async with websockets.connect(base.replace('http','ws',1)+'/ws') as ws:
        data=json.loads(await asyncio.wait_for(ws.recv(),5))
        assert len(data['services'])==17
        assert data['mode']=='synthetic'
asyncio.run(websocket_check())
request('/api/reset',{})
print(json.dumps({'checks':len(checks)+1,'status':'passed','http_checks':checks,'websocket':'passed'},indent=2))
