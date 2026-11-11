"""EXPERTOS WORLD OS — v0.2 Autonomous Platform Milestone Test Suite.
Validates:
1. Versioned Agent Manifests and Zero-Trust Tool Permissions
2. MCP Capability Broker, Token Audience Validation & Human Approval Barrier
3. STRATUM-X Signed Evidence Packages & Bitemporal Causality Assurance
4. Multi-Agent Orchestration, Task Graph (DAG), Checkpointing & Recovery
5. Validated Ephemeral UI Component Registry & Script Injection Prevention
6. SpatialForge Cesium Adapters & Adversarial Verification Benchmark
7. Multi-Feed World Intelligence (Seismic, Economic, Geopolitical)
8. Development Quality Gate Compliance (Branded 404, Favicon, Non-Sensitive Metadata)
"""
import os
os.environ['EXPERTOS_DB'] = '/tmp/expertos-v02-test.db'
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app, db
from app.manifest import AgentManifest, ModelPolicy, EvaluationContract, can_execute_tool
from app.evidence import BitemporalWindow, SignedEvidencePackage, sign_evidence, verify_evidence_package, PLATFORM_SECRET
from app.mcp import ToolExecutionRequest, execute_tool_safely, list_registered_tools, validate_mcp_token
from app.orchestration import decompose_mission, advance_task_graph, recover_checkpoint
from app.ui_registry import generate_ephemeral_view, UiBlock, UiTree, sanitize_string
from app.spatialforge import generate_cesium_scene_config, generate_temporal_replay_path, run_adversarial_benchmark

client = TestClient(app)

# 1. Versioned Agent Manifests & Policies
def test_manifest_versioning_and_permissions():
    r = client.get('/api/manifests')
    assert r.status_code == 200
    manifests = r.json()['manifests']
    assert len(manifests) >= 8  # Core 8 agents initialized
    
    # Create custom versioned manifest
    manifest_data = {
        'id': 'custom-risk-analyst',
        'version': '1.0.0',
        'name': 'Systemic Risk Analyst',
        'domain': 'finance',
        'objective': 'Assess counterparty contagion and liquidity stress under macro shocks',
        'allowed_tools': ['stratumx_evidence_verify'],
        'action_policy': 'approval_required',
        'human_approval_required': True
    }
    r2 = client.post('/api/manifests', json=manifest_data)
    assert r2.status_code == 201
    
    # Retrieve specific manifest
    r3 = client.get('/api/manifests/custom-risk-analyst')
    assert r3.status_code == 200
    assert r3.json()['manifest']['domain'] == 'finance'
    
    # Test zero-trust permission check
    manifest = AgentManifest.model_validate(r3.json()['manifest'])
    # Allowed safe read tool
    decision_ok = can_execute_tool(manifest, 'stratumx_evidence_verify', 'safe_read')
    assert decision_ok['allowed'] is True
    assert decision_ok['requires_human_approval'] is True  # Because manifest.human_approval_required is True
    
    # Unregistered tool rejected by default
    decision_bad = can_execute_tool(manifest, 'arbitrary_network_exploit', 'safe_read')
    assert decision_bad['allowed'] is False

# 2. MCP Capability Broker, Isolation & Human Approvals
def test_mcp_broker_and_token_validation():
    # Valid token audience
    res = validate_mcp_token('bearer:sub123:expertos-world-os:tools:execute')
    assert res['valid'] is True
    assert res['audience'] == 'expertos-world-os'
    
    # Invalid token audience
    bad_res = validate_mcp_token('bearer:sub123:foreign-platform:tools:execute')
    assert bad_res['valid'] is False
    assert 'audience mismatch' in bad_res['error']

def test_mcp_tool_execution_safe():
    r = client.post('/api/mcp/execute', json={
        'agent_id': 'master',
        'tool_name': 'stratumx_evidence_verify',
        'parameters': {'package_id': 'test-pkg-101'}
    })
    assert r.status_code == 200
    data = r.json()
    assert data['success'] is True
    assert data['data']['status'] == 'VERIFIED'

def test_mcp_credential_passthrough_blocked():
    # Attacker tries to pass private API keys through tool parameters
    r = client.post('/api/mcp/execute', json={
        'agent_id': 'master',
        'tool_name': 'stratumx_evidence_verify',
        'parameters': {'leaked_token': 'sk-proj-supersecretkey123'}
    })
    assert r.status_code == 200
    data = r.json()
    assert data['success'] is False
    assert 'Credential passthrough detected' in data['error']

def test_mcp_side_effect_requires_human_approval():
    r = client.post('/api/mcp/execute', json={
        'agent_id': 'security',
        'tool_name': 'system_reconfiguration',
        'parameters': {'target': 'firewall-rule'}
    })
    assert r.status_code == 200
    data = r.json()
    assert data['approval_required'] is True
    appr_id = data['approval_id']
    assert appr_id.startswith('appr-')
    
    # Verify in pending approvals list
    r_list = client.get('/api/mcp/approvals')
    assert r_list.status_code == 200
    assert any(a['request_id'] == appr_id for a in r_list.json()['pending_approvals'])
    
    # Operator approves request
    r_decide = client.post(f'/api/mcp/approvals/{appr_id}/decide', json={'decision': 'approved', 'operator': 'chief-security-officer'})
    assert r_decide.status_code == 200
    assert r_decide.json()['status'] == 'DECIDED'

# 3. STRATUM-X Signed Evidence & Bitemporal Causality
def test_stratum_x_evidence_integrity_and_causality():
    pkg = SignedEvidencePackage(
        id='ev-test-valid-001',
        source_id='usgs-earthquakes',
        source_url='https://earthquake.usgs.gov',
        classification='LIVE_OBSERVATION',
        temporal=BitemporalWindow(
            observed_at='2026-11-11T05:00:00Z',
            available_at='2026-11-11T05:02:00Z',
            ingested_at='2026-11-11T05:05:00Z'
        ),
        payload={'event': 'M6.2 Northern Mid-Atlantic Ridge', 'mag': 6.2}
    )
    sign_evidence(pkg, PLATFORM_SECRET)
    
    # Verification passes
    r_ver = client.post('/api/evidence/verify', json=pkg.model_dump())
    assert r_ver.status_code == 200
    assert r_ver.json()['valid'] is True
    
    # Tamper with payload -> verification fails
    tampered = pkg.model_dump()
    tampered['payload']['mag'] = 7.5
    r_tamper = client.post('/api/evidence/verify', json=tampered)
    assert r_tamper.status_code == 200
    assert r_tamper.json()['valid'] is False
    assert any('mismatch' in issue for issue in r_tamper.json()['issues'])
    
    # Test temporal lookahead violation
    future_leak = SignedEvidencePackage(
        id='ev-test-future-002',
        source_id='synthetic-leak',
        classification='FORECAST',
        temporal=BitemporalWindow(
            observed_at='2026-11-11T12:00:00Z',
            available_at='2026-11-11T12:05:00Z',
            ingested_at='2026-11-11T05:00:00Z'  # Available in future relative to ingestion!
        ),
        payload={'metric': 'lookahead'}
    )
    anomalies = future_leak.temporal.validate_causality()
    assert len(anomalies) > 0
    assert 'Future data leakage' in anomalies[0]

# 4. Multi-Agent Orchestration & Task Graph
def test_multi_agent_orchestration_dag():
    objective = "Analyze geopolitical supply disruptions in the Strait of Malacca with primary shipping data"
    r = client.post('/api/orchestration/decompose', json={'objective': objective})
    assert r.status_code == 200
    graph = r.json()['graph']
    gid = graph['graph_id']
    assert len(graph['nodes']) == 4
    assert 'task-evidence-audit' in graph['nodes']
    assert 'task-synthesis-decision' in graph['nodes']
    
    # Advance graph step
    r_step = client.post(f'/api/orchestration/graphs/{gid}/step')
    assert r_step.status_code == 200
    stepped_graph = r_step.json()['graph']
    assert stepped_graph['status'] in ('in_progress', 'completed')
    assert len(stepped_graph['checkpoints']) > 0
    cp_id = stepped_graph['checkpoints'][0]['checkpoint_id']
    
    # Recover from checkpoint
    r_rec = client.post(f'/api/orchestration/graphs/{gid}/recover?checkpoint_id={cp_id}')
    assert r_rec.status_code == 200
    assert r_rec.json()['recovered_checkpoint'] == cp_id

# 5. Ephemeral UI Security & Script Injection Prevention
def test_ephemeral_ui_blocks_script_injection():
    with pytest.raises(ValueError, match="Untrusted markup or script injection"):
        sanitize_string("<script>alert('xss')</script>")
        
    with pytest.raises(ValueError, match="Untrusted markup or script injection"):
        sanitize_string("javascript:document.cookie")

def test_ephemeral_ui_schema_generation():
    view = generate_ephemeral_view('reviewer', 'research')
    assert view.schema_version == '0.2.0'
    assert view.ttl_seconds == 900
    assert view.is_expired() is False
    assert len(view.blocks) >= 2
    assert all(b.type in ['evidence_table', 'source_graph', 'task_plan'] for b in view.blocks)

# 6. SpatialForge & Adversarial Replay Oracle
def test_spatialforge_adapters_and_benchmark():
    # Cesium scene configuration
    cfg = generate_cesium_scene_config(103.8, 1.3, 500000.0)
    assert 'cesium_version' in cfg
    assert cfg['camera']['destination']['longitude'] == 103.8
    
    # Temporal trajectory generator
    path = generate_temporal_replay_path({'lon': 0.0, 'lat': 51.5}, {'lon': 4.4, 'lat': 51.2}, steps=5)
    assert len(path) == 5
    assert path[0].uncertainty_radius_m >= 15.0
    
    # Adversarial risk-coverage benchmark
    bm = run_adversarial_benchmark()
    assert bm['coverage'] == 1.0
    assert bm['adversarial_precision'] == 1.0
    assert bm['abstention_contract_upheld'] is True

# 7. Multi-Feed World Intelligence
def test_multi_feed_world_intelligence():
    # Test macroeconomic indicators
    r_econ = client.get('/api/world/events?feed=economic')
    assert r_econ.status_code == 200
    data = r_econ.json()
    assert data['total_events'] >= 3
    assert any(e['indicator'] == 'BDI' for e in data['events'])
    
    # Test geopolitical navigation
    r_geo = client.get('/api/world/events?feed=geopolitical')
    assert r_geo.status_code == 200
    data_geo = r_geo.json()
    assert any('Suez' in e['title'] for e in data_geo['events'])
    
    # Feed health overview
    r_health = client.get('/api/world/feeds')
    assert r_health.status_code == 200
    feeds = r_health.json()['feeds']
    assert len(feeds) == 3

# 8. Development Quality Gate Acceptance Checks (Q04, Q08)
def test_branded_404_recovery_page():
    # HTML request -> Branded recovery page with HTTP 404
    r_html = client.get('/nonexistent-document-route', headers={'Accept': 'text/html'})
    assert r_html.status_code == 404
    assert 'Route Not Found (404)' in r_html.text
    assert 'Return to Operations Console' in r_html.text
    
    # JSON API request -> Structured 404
    r_json = client.get('/api/nonexistent-endpoint', headers={'Accept': 'application/json'})
    assert r_json.status_code == 404
    assert r_json.json()['error'] == 'RESOURCE_NOT_FOUND'

def test_branded_favicon():
    r = client.get('/favicon.ico')
    assert r.status_code == 200
    assert 'image/svg+xml' in r.headers['content-type']
    assert '<svg' in r.text

