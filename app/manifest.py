"""EXPERTOS WORLD OS — Versioned Agent Manifests and Permission Policies.
Enforces the first fundamental architectural decision:
Every agent has a defined expertise, tools, permissions, model policy, and evaluation contract.
"""
from __future__ import annotations
import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

CATEGORIES = {
    'research', 'geospatial', 'security', 'engineering',
    'finance', 'forecasting', 'code', 'general', 'orchestration'
}

ActionPolicy = Literal['read_only', 'approval_required', 'autonomous_safe']

class ModelPolicy(BaseModel):
    primary_model: str = Field(default='openrouter/auto', max_length=120)
    fallback_models: List[str] = Field(default_factory=lambda: ['openrouter/auto'])
    max_tokens: int = Field(default=1100, ge=100, le=8192)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    cost_budget_usd: float = Field(default=1.0, ge=0.01, le=100.0)

class EvaluationContract(BaseModel):
    suite_id: str = Field(default='core-abstention-v1', max_length=100)
    min_coverage: float = Field(default=0.85, ge=0.0, le=1.0)
    max_error_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    falsification_tests: List[str] = Field(default_factory=lambda: ['unsupported-claim-check', 'temporal-leakage-check'])

class AgentManifest(BaseModel):
    id: str = Field(min_length=2, max_length=100)
    version: str = Field(default='1.0.0', pattern=r'^\d+\.\d+\.\d+$')
    name: str = Field(min_length=2, max_length=80)
    domain: str = Field(default='general')
    objective: str = Field(min_length=5, max_length=600)
    owner: str = Field(default='workspace-admin', max_length=80)
    model_policy: ModelPolicy = Field(default_factory=ModelPolicy)
    expertise_prompt: str = Field(default='', max_length=6000)
    allowed_tools: List[str] = Field(default_factory=list)
    data_scopes: List[str] = Field(default_factory=lambda: ['evidence:read', 'world:read'])
    action_policy: ActionPolicy = Field(default='approval_required')
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    evaluation_contract: EvaluationContract = Field(default_factory=EvaluationContract)
    human_approval_required: bool = True
    memory_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    ui_ttl_seconds: int = Field(default=900, ge=60, le=7200)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator('domain')
    @classmethod
    def domain_valid(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"Domain '{v}' not in supported categories: {sorted(CATEGORIES)}")
        return v

def init_manifest_tables(con: sqlite3.Connection) -> None:
    con.execute("""
    CREATE TABLE IF NOT EXISTS agent_manifests (
        id TEXT NOT NULL,
        version TEXT NOT NULL,
        name TEXT NOT NULL,
        domain TEXT NOT NULL,
        manifest_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (id, version)
    )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_manifest_id ON agent_manifests(id)")

def save_manifest(con: sqlite3.Connection, manifest: AgentManifest) -> AgentManifest:
    raw = manifest.model_dump_json()
    con.execute(
        "INSERT OR REPLACE INTO agent_manifests (id, version, name, domain, manifest_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (manifest.id, manifest.version, manifest.name, manifest.domain, raw, manifest.created_at)
    )
    return manifest

def get_manifest(con: sqlite3.Connection, agent_id: str, version: Optional[str] = None) -> Optional[AgentManifest]:
    if version:
        row = con.execute(
            "SELECT manifest_json FROM agent_manifests WHERE id = ? AND version = ?",
            (agent_id, version)
        ).fetchone()
    else:
        row = con.execute(
            "SELECT manifest_json FROM agent_manifests WHERE id = ? ORDER BY created_at DESC LIMIT 1",
            (agent_id,)
        ).fetchone()
    if not row:
        return None
    return AgentManifest.model_validate_json(row[0])

def list_manifest_versions(con: sqlite3.Connection, agent_id: str) -> List[Dict[str, Any]]:
    rows = con.execute(
        "SELECT id, version, name, domain, created_at FROM agent_manifests WHERE id = ? ORDER BY created_at DESC",
        (agent_id,)
    ).fetchall()
    return [{'id': r[0], 'version': r[1], 'name': r[2], 'domain': r[3], 'created_at': r[4]} for r in rows]

def can_execute_tool(manifest: AgentManifest, tool_id: str, tool_risk: str) -> Dict[str, Any]:
    """Zero-trust policy evaluator for tool invocation by an agent.
    Returns decision dict with allowed (bool), requires_human_approval (bool), reason (str).
    """
    if tool_id not in manifest.allowed_tools:
        return {
            'allowed': False,
            'requires_human_approval': False,
            'reason': f"Tool '{tool_id}' is not in allowed_tools for agent '{manifest.id}' (manifest v{manifest.version})"
        }
    
    if manifest.action_policy == 'read_only' and tool_risk != 'safe_read':
        return {
            'allowed': False,
            'requires_human_approval': False,
            'reason': f"Agent action_policy is 'read_only', rejecting non-read tool '{tool_id}' with risk '{tool_risk}'"
        }
    
    if manifest.human_approval_required or tool_risk in ('side_effect', 'destructive'):
        return {
            'allowed': True,
            'requires_human_approval': True,
            'reason': f"Tool '{tool_id}' requires explicit human verification and approval prior to execution"
        }
    
    return {
        'allowed': True,
        'requires_human_approval': False,
        'reason': "Permitted under autonomous_safe policy"
    }

