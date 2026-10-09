# Contributing to GCP Stimulator

Thanks for your interest in contributing. This project's mission is to become,
for GCP, what [LocalStack](https://github.com/localstack/localstack) is for
AWS — a local server the real, unmodified cloud provider tooling (starting
with the Terraform `google` provider) can be pointed at, with genuine
wire-protocol fidelity. See [README.md](README.md) for the current status and
[PLAN.md](PLAN.md) / [DECISIONS.md](DECISIONS.md) for the roadmap and
engineering rationale.

## Development setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -e ".[test]"
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Or bring up both at once with Docker: `docker compose up --build` (see
[docker-compose.yml](docker-compose.yml)).

## Adding a new GCP service

See the "Adding a New GCP Service" section in [CLAUDE.md](CLAUDE.md) for the
concrete file-by-file pattern this repo already follows.

## Testing

```bash
# Integration tests (from repo root)
python -m pytest tests/integration

# Frontend lint
cd frontend && npm run lint
```

A pull request's CI (`.github/workflows/`) runs both of the above, plus a
frontend production build, on every PR.

## Verification bar for real-provider (Terraform) compatibility work

If your change touches anything under the "Terraform / google-provider
compatibility" effort (see `feature/terraform-google-provider`-style work),
the bar is: a genuine `terraform init -> apply -> destroy` cycle against the
real, unmodified `hashicorp/google` provider, with the result verified via an
independent check (a direct API call, `docker ps`, etc.) — never just
Terraform's own exit code. See `DECISIONS.md`'s "Terraform / google-provider
compatibility" section for worked examples of this bar being met.

## Commit messages and decisions

- Keep commits focused and the message explaining *why*, not just *what*.
- Non-obvious engineering calls (an ambiguous design choice, a workaround, a
  deliberate scope cut) belong in `DECISIONS.md`, not just in a commit
  message — it's the project's running engineering log.

## Code of conduct

Be respectful and constructive. Assume good faith. This is a small project —
most interaction will just be normal collaborative engineering.
