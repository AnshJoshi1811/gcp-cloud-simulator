# GCP Stimulator 🚀

A **local GCP emulator** for development and testing: FastAPI backend with
Docker-backed services that mirror real GCP behavior (VM instances and
Cloud SQL/Memorystore are real Docker containers; VPCs are real Docker
networks; Cloud Storage proxies to a real `fake-gcs-server`), plus a React
+ TypeScript console UI.

**Mission**: be for GCP what [LocalStack](https://github.com/localstack/localstack)
is for AWS — a local server the *official, unmodified* Terraform `google`
provider can be pointed at, with genuine wire-protocol fidelity, not just
enough to satisfy `gcloud` CLI calls. Long-term, resource-by-resource
effort — current progress and the full engineering log are in
[CLAUDE.md](CLAUDE.md).

**Status**: 24/26 cataloged GCP services implemented; this is a **local dev
tool**, not a certified GCP replacement (not API-complete, no IAM/quota
enforcement). It is, however, functionally real where it counts — see the
Service Catalog below and [CLAUDE.md](CLAUDE.md) for details, architecture,
the full roadmap, and the engineering decisions log.

## Quick Start

**Fastest path**: `docker compose up --build`, then open http://localhost:3000.

For local dev with hot-reload:

```bash
# Backend (terminal 1)
cd backend
pip install -e ".[test]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

- Backend: http://localhost:8080 (Swagger docs at `/docs`)
- Frontend: http://localhost:3000
- `DATABASE_URL` is optional (defaults to local SQLite); Docker is optional
  too (degrades gracefully to stub mode — see CLAUDE.md).

**gcloud CLI**: `source scripts/stimulator.sh on` redirects `gcloud` at the
emulator (or `source .env-gcloud` directly). Try:
```bash
gcloud compute instances create test-vm --zone=us-central1-a --machine-type=e2-micro --project=test-project
gcloud storage buckets create gs://my-test-bucket --project=test-project
```

## Service Catalog

| Service | Status | Notes |
|---|---|---|
| Projects, VPC, Compute Engine, IAM | ✅ Complete | Core infra, Docker-backed |
| Cloud Storage | ✅ Complete | Core CRUD proxies to real `fake-gcs-server` — Terraform-provider-verified, not just `gcloud` |
| GKE, Cloud Run, Artifact Registry | ✅ Complete | |
| Pub/Sub, Cloud Monitoring, Autoscaling | ✅ Complete | |
| Secret Manager, Cloud KMS, Cloud Tasks | ✅ Complete | KMS encryption is a local reversible stand-in, not real crypto |
| Cloud SQL, Memorystore | ✅ Complete | Real Postgres/MySQL/Redis containers (stub if Docker unavailable) |
| Firestore, Cloud Logging | ✅ Complete | In-memory |
| Cloud Load Balancing | ✅ Complete | Real round-robin HTTP routing |
| Cloud Functions | ✅ Complete | Real execution: container-backed or in-process; Python only |
| API Gateway | ✅ Complete | Real proxy to deployed Functions or external URLs |
| Cloud Identity Platform | ✅ Complete | Email/password auth, salted-hashed |
| Cloud CDN | ✅ Complete | Real cache fronting actual Storage objects |
| Event Routing | ✅ Complete | Real Pub/Sub → Cloud Functions dispatch |
| Service Management | 🟡 Partial | Deliberate — no real billing to emulate locally |
| Deployment Manager | ⬜ Skipped | Deliberate — real Terraform compatibility is pursued directly instead |

Full architecture, roadmap, and the complete engineering decisions log: **[CLAUDE.md](CLAUDE.md)**.
Contributing / dev setup: **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## Project Structure

```
gcp-cloud-simulator/
├── backend/            # FastAPI (app/services/<name>/, pyproject.toml, Dockerfile)
├── frontend/           # React + TypeScript (Vite, Tailwind)
├── tests/              # Integration test suite
├── scripts/            # Dev/maintenance scripts
├── terraform-examples/ # Real Terraform configs verifying provider compatibility
├── .github/            # CI workflows, issue/PR templates
├── docker-compose.yml  # `docker compose up --build` runs the whole stack
├── LICENSE / CONTRIBUTING.md
├── CLAUDE.md            # Full project reference: architecture, roadmap, decisions log
└── README.md            # This file
```

MiniCloud, a separate AWS-emulator project, used to live at `/minicloud` in
this repo — it's been extracted to its own repository:
[AnshJoshi1811/minicloud](https://github.com/AnshJoshi1811/minicloud).

## License

MIT — see [LICENSE](LICENSE).
