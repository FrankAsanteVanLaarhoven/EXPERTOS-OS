"""EXPERTOS WORLD OS — Multi-Agent Orchestration Subsystem.
Implements task graphs (DAGs), specialist delegation, state checkpointing, and recovery.
Allows Master Orchestrator to decompose missions, assign typed tasks to specialists,
evaluate intermediate evidence, and aggregate into a unified verifiable conclusion.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

TaskStatus = Literal['pending', 'ready', 'running', 'completed', 'failed', 'blocked_approval']
GraphStatus = Literal['created', 'in_progress', 'completed', 'failed']

class TaskNode(BaseModel):
    id: str
    assigned_agent_id: str
    title: str
    prompt: str
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = 'pending'
    result: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

class TaskGraph(BaseModel):
    graph_id: str
    title: str
    objective: str
    nodes: Dict[str, TaskNode] = Field(default_factory=dict)
    status: GraphStatus = 'created'
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def ready_nodes(self) -> List[TaskNode]:
        """Find pending nodes whose dependencies are all completed."""
        ready = []
        for node in self.nodes.values():
            if node.status != 'pending':
                continue
            deps_met = all(
                dep in self.nodes and self.nodes[dep].status == 'completed'
                for dep in node.dependencies
            )
            if deps_met:
                ready.append(node)
        return ready

    def snapshot(self) -> Dict[str, Any]:
        """Create an immutable checkpoint snapshot for recovery."""
        return {
            'checkpoint_id': 'cp-' + hashlib.sha256(f"{self.graph_id}:{time.time_ns()}".encode()).hexdigest()[:12],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': self.status,
            'node_states': {nid: {'status': n.status, 'result': n.result, 'error': n.error} for nid, n in self.nodes.items()}
        }

def init_orchestration_tables(con: sqlite3.Connection) -> None:
    con.execute("""
    CREATE TABLE IF NOT EXISTS task_graphs (
        graph_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        objective TEXT NOT NULL,
        status TEXT NOT NULL,
        graph_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS task_checkpoints (
        checkpoint_id TEXT PRIMARY KEY,
        graph_id TEXT NOT NULL,
        checkpoint_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

def save_task_graph(con: sqlite3.Connection, graph: TaskGraph) -> None:
    graph.updated_at = datetime.now(timezone.utc).isoformat()
    raw = graph.model_dump_json()
    con.execute(
        "INSERT OR REPLACE INTO task_graphs (graph_id, title, objective, status, graph_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (graph.graph_id, graph.title, graph.objective, graph.status, raw, graph.created_at, graph.updated_at)
    )

def get_task_graph(con: sqlite3.Connection, graph_id: str) -> Optional[TaskGraph]:
    row = con.execute("SELECT graph_json FROM task_graphs WHERE graph_id = ?", (graph_id,)).fetchone()
    if not row:
        return None
    return TaskGraph.model_validate_json(row[0])

def list_task_graphs(con: sqlite3.Connection, limit: int = 20) -> List[Dict[str, Any]]:
    rows = con.execute("SELECT graph_id, title, objective, status, created_at, updated_at FROM task_graphs ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    return [
        {
            'graph_id': r[0],
            'title': r[1],
            'objective': r[2],
            'status': r[3],
            'created_at': r[4],
            'updated_at': r[5]
        }
        for r in rows
    ]

def decompose_mission(objective: str) -> TaskGraph:
    """Master Orchestrator deterministic decomposition of a complex mission into a typed DAG."""
    gid = 'graph-' + hashlib.sha256(f"{objective}:{time.time_ns()}".encode()).hexdigest()[:12]
    
    # Standard multi-specialist decomposition pipeline:
    # 1. Research Reviewer: Evidence & literature provenance
    # 2. World Intelligence: Geospatial & temporal telemetry audit
    # 3. Security Sentinel: Vulnerability & privilege review
    # 4. Master Orchestrator: Synthesize final evidence-backed decision
    node1 = TaskNode(
        id='task-evidence-audit',
        assigned_agent_id='reviewer',
        title='Audit Primary Evidence & Sources',
        prompt=f"Perform rigorous claim extraction and provenance verification for objective: {objective}. Identify ungrounded assertions and primary citations.",
        dependencies=[]
    )
    node2 = TaskNode(
        id='task-world-telemetry',
        assigned_agent_id='world',
        title='Inspect Geospatial & Temporal Telemetry',
        prompt=f"Assess geographic constraints, sensor observation timestamps, and freshness lags relating to: {objective}.",
        dependencies=[]
    )
    node3 = TaskNode(
        id='task-security-boundary',
        assigned_agent_id='security',
        title='Evaluate Authorization & Trust Boundaries',
        prompt=f"Evaluate tool privileges, least-privilege policies, and side-effect risks for: {objective}.",
        dependencies=['task-evidence-audit']
    )
    node4 = TaskNode(
        id='task-synthesis-decision',
        assigned_agent_id='master',
        title='Synthesize Verified Collective Intelligence',
        prompt=f"Integrate findings from research review, geospatial telemetry, and security audit into an evidence-grounded action plan for: {objective}.",
        dependencies=['task-evidence-audit', 'task-world-telemetry', 'task-security-boundary']
    )
    
    graph = TaskGraph(
        graph_id=gid,
        title='Mission Decomposition: ' + (objective[:40] + '…' if len(objective) > 40 else objective),
        objective=objective,
        nodes={n.id: n for n in [node1, node2, node3, node4]},
        status='created'
    )
    return graph

def advance_task_graph(
    con: sqlite3.Connection,
    graph: TaskGraph,
    runner_fn: Callable[[str, str], str]
) -> TaskGraph:
    """Execute available ready nodes in topological order, record checkpoints, and advance state."""
    graph.status = 'in_progress'
    ready = graph.ready_nodes()
    
    for node in ready:
        node.status = 'running'
        try:
            # Build context from dependencies
            dep_contexts = []
            for dep_id in node.dependencies:
                dep_node = graph.nodes.get(dep_id)
                if dep_node and dep_node.result:
                    dep_contexts.append(f"[{dep_node.assigned_agent_id.upper()} OUTPUT]:\n{dep_node.result}")
            
            context_prompt = node.prompt
            if dep_contexts:
                context_prompt += "\n\nPredecessor Specialist Outputs:\n" + "\n---\n".join(dep_contexts)
            
            output = runner_fn(node.assigned_agent_id, context_prompt)
            node.result = output
            node.status = 'completed'
            node.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            node.status = 'failed'
            node.error = str(e)
            graph.status = 'failed'
            break

    # Record checkpoint
    cp = graph.snapshot()
    graph.checkpoints.append(cp)
    con.execute(
        "INSERT INTO task_checkpoints (checkpoint_id, graph_id, checkpoint_json, created_at) VALUES (?, ?, ?, ?)",
        (cp['checkpoint_id'], graph.graph_id, json.dumps(cp), cp['timestamp'])
    )

    # Check overall graph completion
    if all(n.status == 'completed' for n in graph.nodes.values()):
        graph.status = 'completed'
    elif any(n.status == 'failed' for n in graph.nodes.values()):
        graph.status = 'failed'

    save_task_graph(con, graph)
    return graph

def recover_checkpoint(con: sqlite3.Connection, graph_id: str, checkpoint_id: str) -> Optional[TaskGraph]:
    """Roll back or restore graph state to a recorded checkpoint."""
    row = con.execute("SELECT checkpoint_json FROM task_checkpoints WHERE checkpoint_id = ? AND graph_id = ?", (checkpoint_id, graph_id)).fetchone()
    if not row:
        return None
    cp = json.loads(row[0])
    graph = get_task_graph(con, graph_id)
    if not graph:
        return None
    
    # Restore node states
    for nid, state in cp['node_states'].items():
        if nid in graph.nodes:
            graph.nodes[nid].status = state['status']
            graph.nodes[nid].result = state['result']
            graph.nodes[nid].error = state['error']
    graph.status = cp['status']
    save_task_graph(con, graph)
    return graph

