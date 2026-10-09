# Autonomous Build Plan — GCP Emulator completion + MiniCloud

Working autonomously, no stop-and-ask. Decisions logged in `DECISIONS.md` (repo root)
and `minicloud/DECISIONS.md`. Commit + push after every milestone.

## Deliverable 1 — Finish the GCP emulator

Existing live backend wiring: `backend/app/main.py` includes routers from
`backend/app/services/<name>/{models,storage,router}.py`. The old `backend/app/api/*.py`
layer only still serves Cloud Storage (`storage.py`) and is otherwise dead — noted in
DECISIONS.md. Pattern per service: in-memory `storage.py` singleton (not all services
use SQLAlchemy — secretmanager/pubsub/monitoring/autoscaling are in-memory), FastAPI
`router.py`, Pydantic-ish `models.py` with `.to_dict()`, registered in `main.py` with a
GCP-shaped URL prefix, a frontend page under `frontend/src/pages/`, a route in `App.tsx`,
an API client under `frontend/src/api/`, and integration tests under
`tests/integration/test_<service>.py` (+ `_gcloud.py` for CLI-flavored checks), using the
`api_client`/`test_project` fixtures already in conftest.

Tracker reality check (actual code, not the stale table): 11/26 services already done
(Projects, VPC, Compute, Storage, IAM, GKE, Cloud Run, Pub/Sub, Monitoring, Autoscaling,
Artifact Registry-ish). Remaining, in priority order:

1. Cloud KMS (no deps, quick win)
2. Cloud Tasks (no deps, quick win)
3. Cloud SQL (Docker-backed: postgres/mysql containers)
4. Memorystore (Docker-backed: redis container)
5. Firestore (in-memory document store)
6. Cloud Logging (in-memory log sink/query)
7. Cloud Load Balancer (maps to compute+vpc)
8. Cloud Functions (critical — storage/pubsub-triggered, executes in a container)
9. API Gateway (routes to Cloud Functions)
10. Cloud Identity Platform (OAuth2/user mgmt stubs)
11. Cloud CDN (thin layer over Storage + LB)
12. Event Routing (Eventarc-style, cross-service)
13. Deployment Manager (minimal Terraform-shaped apply, lowest priority)

Milestones = one service (or small related group) each: implement, test, update
IMPLEMENTATION_TRACKER.md + README.md, commit, push.

Artifact Registry is marked complete in code already (router exists, wired, full CRUD) —
treat as done; just correct the tracker text.

## Deliverable 2 — MiniCloud (originally built at `/minicloud` in this repo)

> **Update**: MiniCloud has since been extracted to its own repository,
> [AnshJoshi1811/minicloud](https://github.com/AnshJoshi1811/minicloud) — it's
> a separate, unrelated product (AWS, not GCP) that didn't belong mixed into
> this one. The plan below is left as-is as an accurate record of the
> original work; MiniCloud's own `DECISIONS.md`/`PLAN.md` now live in its own
> repo.

Separate AWS-API-shaped emulator so the official Terraform `aws` provider works against
`http://localhost:4566`. Python (FastAPI) for speed of reuse with this repo's own
conventions — see `minicloud/DECISIONS.md`. Priority: EC2 -> VPC/SG -> S3 -> IAM/DynamoDB/SQS.
Each milestone: implement + test against real Terraform examples in `minicloud/examples/`,
commit, push.

## Working rules
- Small, frequent commits; push immediately after each.
- Never crash on unsupported calls — return GCP/AWS-shaped JSON errors.
- Ambiguity -> pick the sensible default, log it, keep moving.
