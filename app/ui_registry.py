"""EXPERTOS WORLD OS — Validated Ephemeral UI Component Registry.
Enforces the second fundamental architectural decision:
Interfaces are generated for the task and unmounted after the session,
while important results remain durably recorded.
The system STRICTLY PROHIBITS executable frontend script generation by models.
Only safe, validated, versioned component schemas from the trusted allowlist can be returned.
"""
from __future__ import annotations
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Set
from pydantic import BaseModel, Field, field_validator

ALLOWED_COMPONENT_TYPES: Set[str] = {
    'globe',
    'timeline',
    'evidence_table',
    'agent_feed',
    'forecast_calibration',
    'source_graph',
    'code_diff',
    'task_plan'
}

DANGEROUS_PATTERNS = re.compile(r'<\s*script|javascript\s*:|onload\s*=|onerror\s*=|onclick\s*=|data\s*:\s*text/html|<iframe', re.IGNORECASE)

def sanitize_string(text: str) -> str:
    if DANGEROUS_PATTERNS.search(text):
        raise ValueError("Untrusted markup or script injection pattern detected in UI component payload")
    return text

class UiBlock(BaseModel):
    type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=500)
    props: Dict[str, Any] = Field(default_factory=dict)
    provenance_refs: List[str] = Field(default_factory=list)
    state: Literal['UNCONNECTED', 'CONNECTED', 'SIMULATED', 'HISTORICAL'] = 'UNCONNECTED'

    @field_validator('type')
    @classmethod
    def type_valid(cls, v: str) -> str:
        if v not in ALLOWED_COMPONENT_TYPES:
            raise ValueError(f"Component type '{v}' rejected. Must be one of: {sorted(ALLOWED_COMPONENT_TYPES)}")
        return v

    @field_validator('title', 'description')
    @classmethod
    def content_sanitized(cls, v: str) -> str:
        return sanitize_string(v)

class UiTree(BaseModel):
    schema_version: str = '0.2.0'
    session_id: str
    view_id: str
    agent_id: str
    ttl_seconds: int = Field(default=900, ge=60, le=7200)
    title: str
    blocks: List[UiBlock] = Field(min_length=1, max_length=8)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    disclaimer: str = 'Safe, validated ephemeral interface generated under strict component schema allowlist.'

    @field_validator('title')
    @classmethod
    def title_sanitized(cls, v: str) -> str:
        return sanitize_string(v)

    def is_expired(self) -> bool:
        try:
            created = datetime.fromisoformat(self.created_at)
            now = datetime.now(timezone.utc)
            return (now - created).total_seconds() > self.ttl_seconds
        except Exception:
            return True

# Component Prop Schemas and Generators
DEFAULT_COMPONENT_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    'research': {
        'title': 'SCIENTIFIC REVIEW WORKBENCH',
        'blocks': [
            {'type': 'evidence_table', 'title': 'Claim Provenance Audit', 'description': 'Extracted falsifiable assertions matched against primary literature hashes', 'state': 'UNCONNECTED', 'props': {'columns': ['Claim ID', 'Primary Source', 'Falsification Test', 'Confidence']}},
            {'type': 'source_graph', 'title': 'Citation Precedence Network', 'description': 'Directed dependency graph of peer-reviewed foundational literature', 'state': 'UNCONNECTED', 'props': {'directed': True, 'metric': 'citation_age'}},
            {'type': 'task_plan', 'title': 'Preregistered Replication Protocol', 'description': 'Stepwise falsification criteria and statistical power constraints', 'state': 'UNCONNECTED', 'props': {'allow_user_edits': False}}
        ]
    },
    'geospatial': {
        'title': 'SPATIAL EVIDENCE WORKBENCH',
        'blocks': [
            {'type': 'globe', 'title': 'Planetary Telemetry & Vector Layers', 'description': 'Orthographic 3D projection with USGS sensor overlays and coordinate fidelity', 'state': 'UNCONNECTED', 'props': {'projection': 'orthographic', 'lens': 'seismic'}},
            {'type': 'timeline', 'title': 'Bitemporal Replay Track', 'description': 'Observation time vs. ingestion time synchronization window', 'state': 'UNCONNECTED', 'props': {'resolution': 'hours', 'replay_rate': '1x'}},
            {'type': 'evidence_table', 'title': 'Telemetry Provenance Register', 'description': 'Sensor payload digests, latency measurements, and coordinate confidence intervals', 'state': 'UNCONNECTED', 'props': {'columns': ['Event ID', 'Magnitude', 'Coordinates', 'Depth (km)', 'Observed At']}}
        ]
    },
    'security': {
        'title': 'TRUST & CONTROL WORKBENCH',
        'blocks': [
            {'type': 'source_graph', 'title': 'MCP Tool Attack Surface', 'description': 'Scrutinize tool permissions, OAuth scopes, and sandbox boundaries', 'state': 'UNCONNECTED', 'props': {'highlight_risk': 'high'}},
            {'type': 'task_plan', 'title': 'Adversarial Evaluation Protocol', 'description': 'Red-team injection harnesses and credential passthrough prevention checks', 'state': 'UNCONNECTED', 'props': {'enforce_barrier': True}},
            {'type': 'evidence_table', 'title': 'Audit Log & Approval Ledger', 'description': 'Cryptographically verified operator approvals and side-effect records', 'state': 'UNCONNECTED', 'props': {'columns': ['Request ID', 'Tool Name', 'Operator', 'Decision', 'Timestamp']}}
        ]
    },
    'engineering': {
        'title': 'ENGINEERING WORKBENCH',
        'blocks': [
            {'type': 'code_diff', 'title': 'Implementation Inspection', 'description': 'Review architectural modifications, contracts, and regression risks', 'state': 'UNCONNECTED', 'props': {'syntax': 'diff', 'show_line_numbers': True}},
            {'type': 'task_plan', 'title': 'Acceptance Quality Gates', 'description': 'Validate against DEVELOPMENT_QUALITY.md 20-point release gate', 'state': 'UNCONNECTED', 'props': {'total_checks': 20}},
            {'type': 'evidence_table', 'title': 'Build Provenance & Hashes', 'description': 'Test suite outcomes, artifact digests, and environment reproducibility', 'state': 'UNCONNECTED', 'props': {'columns': ['Target', 'Suite', 'Passed', 'Elapsed', 'Digest']}}
        ]
    },
    'forecasting': {
        'title': 'PROBABILISTIC CALIBRATION WORKBENCH',
        'blocks': [
            {'type': 'forecast_calibration', 'title': 'Brier Score & Calibration Curve', 'description': 'Measure forecast reliability against historical resolution benchmarks', 'state': 'UNCONNECTED', 'props': {'bins': 10, 'metric': 'brier'}},
            {'type': 'timeline', 'title': 'Temporal Information Horizon', 'description': 'Enforce temporal causality: strictly prevent lookahead and hindsight leakage', 'state': 'UNCONNECTED', 'props': {'cutoff_mode': 'strict_pre_event'}},
            {'type': 'evidence_table', 'title': 'Probabilistic Forecast Ledger', 'description': 'Quantified confidence bands, uncertainty intervals, and baselines', 'state': 'UNCONNECTED', 'props': {'columns': ['Question', 'P(Yes)', 'Confidence Interval', 'Baseline P', 'Outcome Date']}}
        ]
    },
    'finance': {
        'title': 'MACROECONOMIC INTELLIGENCE WORKBENCH',
        'blocks': [
            {'type': 'timeline', 'title': 'Release Vintage Chronology', 'description': 'Distinguish preliminary release dates from subsequent econometric revisions', 'state': 'UNCONNECTED', 'props': {'track_revisions': True}},
            {'type': 'source_graph', 'title': 'Macro Counterparty & Supply Linkages', 'description': 'Interdependency network across commodities, currencies, and sovereign debt', 'state': 'UNCONNECTED', 'props': {'layout': 'force_directed'}},
            {'type': 'evidence_table', 'title': 'Economic Indicator Register', 'description': 'Verified official statistics, provenance hashes, and reporting frequency', 'state': 'UNCONNECTED', 'props': {'columns': ['Indicator', 'Vintage', 'Value', 'Unit', 'Source']}}
        ]
    },
    'orchestration': {
        'title': 'COLLECTIVE OPERATIONS WORKBENCH',
        'blocks': [
            {'type': 'task_plan', 'title': 'Multi-Agent Mission Graph', 'description': 'Visual DAG of decomposed tasks, specialist assignments, and dependencies', 'state': 'UNCONNECTED', 'props': {'interactive_dag': True}},
            {'type': 'source_graph', 'title': 'Specialist Agent Topology', 'description': 'Live routing graph showing data flows between Master Orchestrator and specialists', 'state': 'UNCONNECTED', 'props': {'nodes': ['master', 'reviewer', 'world', 'security']}},
            {'type': 'agent_feed', 'title': 'Specialist Execution Stream', 'description': 'Real-time telemetry and verified output deliveries from subagents', 'state': 'UNCONNECTED', 'props': {'stream_type': 'ag_ui_events'}},
            {'type': 'evidence_table', 'title': 'Unified Decision Ledger', 'description': 'Synthesized evidence packages, audit trails, and checkpoint indices', 'state': 'UNCONNECTED', 'props': {'columns': ['Task ID', 'Agent', 'Evidence Hash', 'Audit Status', 'Timestamp']}}
        ]
    },
    'general': {
        'title': 'SPECIALIST TASK WORKBENCH',
        'blocks': [
            {'type': 'task_plan', 'title': 'Specialist Research Plan', 'description': 'Structured objective decomposition and measurable criteria', 'state': 'UNCONNECTED', 'props': {'allow_user_edits': False}},
            {'type': 'evidence_table', 'title': 'Evidence & Claim Register', 'description': 'Verified source observations, missing data notices, and audit hashes', 'state': 'UNCONNECTED', 'props': {'columns': ['Evidence ID', 'Claim', 'Status', 'Timestamp']}},
            {'type': 'source_graph', 'title': 'Tool & Capability Dependencies', 'description': 'Permitted read-only tools and human approval gates', 'state': 'UNCONNECTED', 'props': {'strict_mode': True}}
        ]
    }
}

def generate_ephemeral_view(agent_id: str, category: str, custom_blocks: Optional[List[Dict[str, Any]]] = None) -> UiTree:
    """Generate a validated, ephemeral UI tree for a specialist agent."""
    blueprint = DEFAULT_COMPONENT_BLUEPRINTS.get(category, DEFAULT_COMPONENT_BLUEPRINTS['general'])
    now = datetime.now(timezone.utc).isoformat()
    session_id = 'sess-' + hashlib.sha256(f"{agent_id}:{time.time_ns()}".encode()).hexdigest()[:12]
    view_id = 'view-' + hashlib.sha256(f"{session_id}:{now}".encode()).hexdigest()[:14]
    
    raw_blocks = custom_blocks if custom_blocks else blueprint['blocks']
    validated_blocks = []
    for b in raw_blocks[:8]:
        validated_blocks.append(UiBlock(
            type=b['type'],
            title=b['title'],
            description=b.get('description', ''),
            props=b.get('props', {}),
            provenance_refs=b.get('provenance_refs', []),
            state=b.get('state', 'UNCONNECTED')
        ))
    
    return UiTree(
        session_id=session_id,
        view_id=view_id,
        agent_id=agent_id,
        ttl_seconds=900,
        title=blueprint['title'],
        blocks=validated_blocks,
        created_at=now
    )
