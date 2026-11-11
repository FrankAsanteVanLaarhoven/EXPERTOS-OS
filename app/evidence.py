"""EXPERTOS WORLD OS — Evidence Assurance and Provenance Subsystem (STRATUM-X).
Enforces the third fundamental architectural decision:
World intelligence is evidence-first. Live observations, delayed data, simulations,
forecasts, and unsupported assertions must be visibly distinguishable.
The system must never represent a synthetic visualization as a live observation.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

PLATFORM_SECRET = b'expertos-world-os-v0.2-stratum-x-root-key'

EvidenceClassification = Literal[
    'LIVE_OBSERVATION',
    'NEAR_REAL_TIME',
    'HISTORICAL',
    'FORECAST',
    'SIMULATION',
    'SYNTHETIC_REPRESENTATION',
    'UNAVAILABLE'
]

class BitemporalWindow(BaseModel):
    observed_at: str
    available_at: str
    ingested_at: str

    def validate_causality(self) -> List[str]:
        anomalies = []
        try:
            obs = datetime.fromisoformat(self.observed_at)
            avail = datetime.fromisoformat(self.available_at)
            ing = datetime.fromisoformat(self.ingested_at)
            if obs > avail:
                anomalies.append(f"Temporal violation: observed_at ({self.observed_at}) is later than available_at ({self.available_at})")
            if avail > ing:
                anomalies.append(f"Future data leakage: available_at ({self.available_at}) is in the future relative to ingested_at ({self.ingested_at})")
        except Exception as e:
            anomalies.append(f"Timestamp parse error: {e}")
        return anomalies

class SignedEvidencePackage(BaseModel):
    id: str = Field(min_length=8, max_length=120)
    source_id: str = Field(min_length=2, max_length=100)
    source_url: str = Field(default='')
    classification: EvidenceClassification = 'LIVE_OBSERVATION'
    temporal: BitemporalWindow
    payload: Dict[str, Any]
    content_hash: str = Field(default='')
    signature: str = Field(default='')
    signer_id: str = Field(default='expertos-platform-signer')
    provenance_chain: List[str] = Field(default_factory=list)
    falsifiable_claims: List[str] = Field(default_factory=list)
    is_verified: bool = False

def canonical_json(data: Any) -> str:
    """Deterministic, sorted, whitespace-minimized JSON serialization."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def compute_payload_hash(payload: Dict[str, Any]) -> str:
    raw = canonical_json(payload).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def sign_evidence(package: SignedEvidencePackage, secret_key: bytes) -> SignedEvidencePackage:
    content_hash = compute_payload_hash(package.payload)
    package.content_hash = content_hash
    # DSSE-style pre-image: domain separation + canonical payload hash + bitemporal tuple + classification
    preimage = f"EXPERTOS-DSSE-v1:{package.source_id}:{package.classification}:{content_hash}:{package.temporal.observed_at}:{package.temporal.ingested_at}"
    sig = hmac.new(secret_key, preimage.encode('utf-8'), hashlib.sha256).hexdigest()
    package.signature = sig
    package.is_verified = True
    return package

def verify_evidence_package(package: SignedEvidencePackage, secret_key: bytes) -> Dict[str, Any]:
    """Cryptographic and temporal verification of an evidence package."""
    issues = []
    # Check payload hash
    expected_hash = compute_payload_hash(package.payload)
    if package.content_hash != expected_hash:
        issues.append(f"Payload hash mismatch: recorded {package.content_hash} != calculated {expected_hash}")
    
    # Check bitemporal causality
    temporal_issues = package.temporal.validate_causality()
    issues.extend(temporal_issues)

    # Check HMAC signature
    preimage = f"EXPERTOS-DSSE-v1:{package.source_id}:{package.classification}:{expected_hash}:{package.temporal.observed_at}:{package.temporal.ingested_at}"
    expected_sig = hmac.new(secret_key, preimage.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(package.signature, expected_sig):
        issues.append("Cryptographic signature invalid or forged")

    return {
        'valid': len(issues) == 0,
        'package_id': package.id,
        'classification': package.classification,
        'issues': issues,
        'observed_at': package.temporal.observed_at,
        'ingested_at': package.temporal.ingested_at
    }

def init_evidence_tables(con: sqlite3.Connection) -> None:
    con.execute("""
    CREATE TABLE IF NOT EXISTS evidence_packages (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        source_url TEXT NOT NULL,
        classification TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        available_at TEXT NOT NULL,
        ingested_at TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        signature TEXT NOT NULL,
        package_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence_packages(source_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_evidence_classification ON evidence_packages(classification)")

def store_evidence_package(con: sqlite3.Connection, package: SignedEvidencePackage) -> None:
    now = datetime.now(timezone.utc).isoformat()
    raw = package.model_dump_json()
    con.execute("""
    INSERT OR REPLACE INTO evidence_packages 
    (id, source_id, source_url, classification, observed_at, available_at, ingested_at, content_hash, signature, package_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        package.id,
        package.source_id,
        package.source_url,
        package.classification,
        package.temporal.observed_at,
        package.temporal.available_at,
        package.temporal.ingested_at,
        package.content_hash,
        package.signature,
        raw,
        now
    ))

def get_evidence_package(con: sqlite3.Connection, package_id: str) -> Optional[SignedEvidencePackage]:
    row = con.execute("SELECT package_json FROM evidence_packages WHERE id = ?", (package_id,)).fetchone()
    if not row:
        return None
    return SignedEvidencePackage.model_validate_json(row[0])

def replay_evidence_stream(con: sqlite3.Connection, source_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Reproducible replay oracle returning deterministic sequential evidence items."""
    if source_id:
        rows = con.execute(
            "SELECT id, source_id, classification, observed_at, ingested_at, content_hash FROM evidence_packages WHERE source_id = ? ORDER BY observed_at ASC LIMIT ?",
            (source_id, limit)
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT id, source_id, classification, observed_at, ingested_at, content_hash FROM evidence_packages ORDER BY observed_at ASC LIMIT ?",
            (limit,)
        ).fetchall()
    return [
        {
            'id': r[0],
            'source_id': r[1],
            'classification': r[2],
            'observed_at': r[3],
            'ingested_at': r[4],
            'content_hash': r[5]
        }
        for r in rows
    ]
