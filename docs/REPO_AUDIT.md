# GitHub preliminary integration audit — 2026-11-11

Inspected using linked GitHub read actions against the main branch:

- `FrankAsanteVanLaarhoven/SpatialForge-AI`: `README.md` and `BENCHMARK.md`. Reported components include Cesium/Vue client, OpenRouter/local model adapter, Go gateway, Rust DSSE enclave and Python intelligence. These claims are derived from repository documentation, **not reproduced or performance-verified**.
- `FrankAsanteVanLaarhoven/geospatial-evidence-audit`: `README.md` and `BENCHMARK.md`, plus root filenames. Found benchmark and adversarial evaluation scripts (e.g., `benchmark_risk_coverage.py`, `antwerp_replay.py`, `adversarial_cases.json`). Metrics require independent rerun and confidence intervals at matched coverage. The reported 0-error result on 202 of 300 decisive episodes must not be represented as zero error at full coverage.
- `FrankAsanteVanLaarhoven/spatialforge-services`: `README.md` and `docker-compose.yml`; root folders `core-gateway`, `crypto-enclave`, `python-intelligence`, `stealth-crawler`. Compose refers to build directories prefixed with `./services/`, and a root web Dockerfile; verify/fix these before using stack. Compose also contains a static developer PostgreSQL password, requiring secrets provisioning prior to production.

No code was copied from these repositories into this prototype and no modifications were pushed. Formal source licensing audit is outstanding.
