# EXPERTOS WORLD OS — architecture and production roadmap

## Core design

User → authenticated workspace → agent registry → policy and task orchestrator → model router (OpenRouter/local) → tool mediation (MCP and native connectors) → evidence provenance → typed UI schema → ephemeral frontend view.

The model **must never generate executable frontend scripts**. It returns validated schemas that select only trusted, versioned components. Separately authorize any tool effects on the server; UI widgets are not a permission boundary. Ephemeral UI means transient rendering state with durable provenance and user-approved outputs.

## Repo integration after compatibility audit

- `SpatialForge-AI`: reuse Cesium geospatial visualization, orbital/AIS/ADS-B connectors, temporal replay, offline local model adapter. Avoid duplicated OpenRouter provider routes. Design a typed `WorldObservation` record including `observed_at`, `available_at`, `ingested_at`, `source_id`, `source_root`, `fidelity`, `uncertainty`, and `licence`.
- `geospatial-evidence-audit`: reuse adversarial test harnesses, spatio-temporal risk-coverage protocol, provenance hash fixtures, replay oracles and abstention contract. Never equate hash integrity with truthfulness of a source.
- `spatialforge-services`: evaluate Go gateway, Rust Ed25519 DSSE, Python kinematics, PostGIS and Redis; fix Compose paths and secret handling first. Do not expose dev DB credentials or mislabel untested service availability.

## Agent contract

`AgentManifest {id, name, domain, objective, owner, model_policy, expertise_prompt, allowed_tools, data_scopes, action_policy, output_schema, evaluation_suite, human_approval_required, memory_ttl, ui_ttl, version}`

A custom agent gets **no tools by default**; scoped MCP grants require a user/admin grant, signed tool manifest, role and resource binding, out-of-band execution broker, explicit audit. Ingestion and inference run in segregated workers. Tools should obey the Model Context Protocol authorization specification and reject token passthrough. External changes require approval and risk-aware checks.

## Ephemeral UI component contract

`UiTree {schema_version, session_id, view_id, ttl_seconds, title, blocks:[{type, props, provenance_refs}]}`. Server allowlist `globe|timeline|evidence_table|agent_feed|forecast_calibration|source_graph|code_diff|task_plan`. Validate component props and enforce budgets. No generated JavaScript or HTML; no inline tool execution. Unmount on TTL, retain logs/evidence subject to data retention policy.

## Suggested agents

Master Orchestrator; Expertos Specialist; World Intelligence; Research Reviewer; Security Sentinel; Build Engineer; Forecast Lab; Economic Analyst. Additional presets: Health/medical (strict scope), Climate, Energy, Supply Chain, Robotics, Legal, Science, Media, Education, Data Engineer, Product Design. Expert credentials are scoped methods and testable performance, not impersonation of licensed professionals.

## Live world-source ladder

Observed (with attested origin and source date) > verified near-real-time (with lag) > retrospective historical > forecast (probability, horizon, baseline) > simulated (explicit) > unavailable. Never silently turn unavailable sources into fake live events. Deduplicate common-origin brokers, compute freshness per feed, distinguish cross-source independence, persist bitemporal snapshots, support replay.

## Research hypotheses

H1: source-grounded responses have higher blind claim-support precision than narrative-only LLM baselines.
H2: specialist routing improves calibrated task quality per dollar over a fixed large-model baseline.
H3: typed ephemeral task workspaces reduce task completion time and correction effort compared with static chat UI.
H4: ingestion provenance and abstention reduce unsupported confident assertions at an acceptable coverage cost.

## Proposed (unmeasured) acceptance gates

1. Critical connector claims include traceable provenance in ≥99% of sampled outputs.
2. Zero unapproved external side effects in 500 red-team tool invocation attempts.
3. p95 render latency <1.0s for predefined UI fixtures on benchmark hardware.
4. p95 live source ingestion-to-display <3s after arrival at our ingress (network source delay measured separately).
5. ≥10% task-completion improvement versus best preregistered static-chat control on blinded study.
6. ≥10% lower task-quality-adjusted inference cost versus fixed model baseline at equivalent quality.
7. Historical replay determinism: 100% identical event selections and decision hashes on fixed fixtures.

## Twelve-week execution

Weeks 1–2: audit repository hashes, licences, integration APIs; create service compatibility matrix and ingress schema.
Weeks 3–4: authenticated tenant model, Vault/OIDC, agent permissions, model router, cost controls, MCP capability broker.
Weeks 5–6: event ingestion bus, PostGIS provenance graph, temporal replay, Cesium globe, live/delayed/simulated badges.
Weeks 7–8: typed ephemeral UI runtime, AG-UI event streaming, human approvals, reproducibility log.
Weeks 9–10: user-authored agent builder, scoped memories, lifecycle management, evaluation harness.
Weeks 11–12: adversarial evaluation, data licensing review, performance and security penetration testing; go/no-go decision.

## Known risks

Prompt injection into tools; web source poisoning; false-live signals; privilege escalation from custom agents; OAuth token reuse; model leakage of secrets; cross-tenant data exposure; stale world events; overconfident forecasts; cost explosion; duplicate/misleading independent-source counts. Tests should measure each directly. The existing repo documentation contains ambitious performance statements; independent hardware reproduction is needed before advertising comparative or SOTA achievements.
