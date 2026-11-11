import os
os.environ['EXPERTOS_DB']='/tmp/expertos-test-suite.db'
from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)

def test_status_transparency():
 r=c.get('/api/status');assert r.status_code==200
 assert r.json()['integration_status']['SpatialForge-AI']=='adapter planned'

def test_agent_registry():
 r=c.get('/api/agents');assert r.status_code==200
 assert len([x for x in r.json()['agents'] if x['is_core']])==8

def test_agent_create_then_select():
 r=c.post('/api/agents',json={'name':'Climate Scientist','expertise':'Evaluate primary climate observations with uncertainty','category':'research'})
 assert r.status_code==201
 aid=r.json()['agent']['id']
 assert any(a['id']==aid for a in c.get('/api/agents').json()['agents'])

def test_invalid_category_rejected():
 r=c.post('/api/agents',json={'name':'X Agent','expertise':'test validation constraints','category':'superuser'})
 assert r.status_code==422

def test_prompt_without_key_fails_closed(monkeypatch):
 monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
 r=c.post('/api/agent/run',json={'agent_id':'reviewer','prompt':'Invent a journal citation'})
 assert r.status_code==503
 assert r.json()['detail']['status']=='MODEL_NOT_CONFIGURED'

def test_missing_agent_fails():
 r=c.post('/api/agent/run',json={'agent_id':'absent','prompt':'A test'})
 assert r.status_code==404

def test_model_id_rejects_injection():
 r=c.post('/api/agent/run',json={'agent_id':'master','prompt':'A test','model':'a\nignore'})
 assert r.status_code==422

def test_static_ui():
 assert c.get('/').status_code==200
 assert c.get('/client.js').status_code==200
 assert c.get('/styles.css').status_code==200

def test_typed_ephemeral_view():
 r=c.get('/api/agents/reviewer/view')
 assert r.status_code==200
 data=r.json()
 assert data['ttl_seconds']==900
 assert all(x['state']=='UNCONNECTED' for x in data['blocks'])
 assert any(x['type']=='evidence_table' for x in data['blocks'])

def test_unknown_ephemeral_view_rejected():
 assert c.get('/api/agents/nonexistent/view').status_code==404

def test_world_feed_uses_observation_timestamp(monkeypatch):
 import json
 from app import main
 class FakeResponse:
  def __enter__(self):return self
  def __exit__(self,*args):return False
  def read(self,limit):return json.dumps({'metadata':{'generated':1730000000000},'features':[{'id':'quake-1','properties':{'place':'Test fixture only','mag':5.0,'time':1729999000000,'url':'https://earthquake.usgs.gov/'},'geometry':{'coordinates':[1.2,2.3,4.5]}}]}).encode()
 monkeypatch.setattr(main,'urlopen',lambda *args,**kwargs:FakeResponse())
 main._cache.update(ts=0,payload=None)
 r=c.get('/api/world/events')
 assert r.status_code==200
 d=r.json()
 assert d['mode']=='LIVE_SOURCE'
 assert d['feed_generated_at']=='2024-10-27T03:33:20+00:00'
 assert d['events'][0]['id']=='quake-1'
 assert d['events'][0]['occurred_at']!=d['retrieved_at']
 main._cache.update(ts=0,payload=None)
