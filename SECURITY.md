# Security Policy — EXPERTOS-OS

## Threat Model & Security Posture

**EXPERTOS-OS** is engineered for high-integrity, evidence-critical operating environments. Security is established at the protocol and runtime boundary:

1. **Zero-Trust Tool Capability**: Custom agents receive **no tools by default**. Tool capabilities require explicit administrative manifest grants.
2. **Credential Passthrough Prevention**: Model Context Protocol (MCP) tool requests are inspected by the execution broker. Any parameter containing sensitive access tokens, bearer secrets, or private keys is immediately blocked and audited.
3. **Token Audience Validation**: All MCP authorization tokens require explicit audience validation matching `expertos-world-os`. Unscoped or misattributed tokens are rejected.
4. **Human Approval Barrier**: High-risk actions (`side_effect` or `destructive` risk levels) cannot execute autonomously. They are placed in an isolated pending approval queue and require explicit authorization from an operator.
5. **No Executable Frontend Code**: Ephemeral specialist workbenches are constructed exclusively from a server-validated allowlist of typed component blocks. Models **never** generate arbitrary HTML, JavaScript, or inline scripts.
6. **Container Security**: Production container images run under an unprivileged user (`expertos`, UID 10001) with Linux capabilities dropped (`cap_drop: ALL`) and `no-new-privileges: true`.

---

## Supported Versions

| Version | Supported |
|---|---|
| `0.2.x` | :white_check_mark: Active |
| `< 0.2.0` | :x: Prototype (Superseded) |

---

## Reporting a Vulnerability

If you discover a security vulnerability within EXPERTOS-OS, please report it responsibly:

- **Email**: `security@expertos.ai` / `frankleroyvan@gmail.com`
- **PGP Encryption**: Available upon request.
- **Response SLA**: Initial triage within 24 hours; critical mitigation within 72 hours.
- **Public Disclosure**: We coordinate public disclosures after a validated patch has been released.
