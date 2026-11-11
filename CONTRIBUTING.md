# Contributing to EXPERTOS-OS

We welcome contributions to **EXPERTOS-OS**. To maintain our rigorous standards of safety, scientific reproducibility, and evidence assurance, all contributions must adhere to the following workflow.

---

## Acceptance Quality Gates

Every pull request must comply with the 20 quality checks specified in [`docs/quality/REVIEW.md`](file:///Users/favl/Downloads/expertos-world-os/docs/quality/REVIEW.md) and `/Users/favl/DEVELOPMENT_QUALITY.md`:

1. **Zero Failing Tests**: Run `pytest -q` to ensure 100% of the automated suite passes.
2. **Evidence Integrity**: Never modify verification logic to accept synthetic data as live observations.
3. **Strict Ephemeral UI Constraints**: Never allow models to generate arbitrary JavaScript or executable client code.
4. **No Console Warnings or Errors**: Ensure client-side interactions in `web/` trigger zero uncaught console errors or leftover `console.log` statements.
5. **Responsive Layouts**: Verify UI changes on mobile (360–390px), tablet (768px), and desktop (1440px).

---

## Local Development Workflow

```bash
# 1. Clone and enter repository
git clone https://github.com/FrankAsanteVanLaarhoven/EXPERTOS-OS.git
cd EXPERTOS-OS

# 2. Setup isolated virtualenv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run validation test suite
pytest -q

# 4. Launch development server
./run.sh
```

---

## Pull Request Guidelines

- Branch naming: `feat/<feature-name>`, `fix/<bug-fix>`, `audit/<audit-task>`.
- Commit messages: Use Conventional Commits (e.g. `feat: add AIS vessel telemetry connector`).
- Sign-off: Include Developer Certificate of Origin (DCO) sign-off (`git commit -s`).

