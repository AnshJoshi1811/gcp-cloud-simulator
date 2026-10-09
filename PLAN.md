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

---

## Deliverable 3 — gcp-cloud-simulator as the GCP equivalent of LocalStack (this branch: `feature/terraform-google-provider`)

Explicit, stated mission (owner's own words): **"we have to do for GCP what
LocalStack is doing for AWS."** LocalStack is the more accurate reference
point than moto — it's a running local server the real, unmodified cloud
provider's Terraform plugin talks to over HTTP, exactly this project's own
architecture, not a Python-only in-process mocking library. moto is still
the right model for individual services that need deep wire-protocol
fidelity (hence adopting `fake-gcs-server`, itself conceptually "moto for
GCS"), but the project-level ambition is LocalStack-shaped: one server,
broad real-provider-verified service coverage, built up resource by
resource. Honest scale context: LocalStack covers 100+ AWS services with
~8 years of community effort behind it; this effort currently has 1
service/2 resource types real-provider-verified (Cloud Storage). This is a
long-term, multi-session roadmap, not a sprint — each milestone below is
one more real brick in that wall.

Full rationale and the Phase 0 research in `DECISIONS.md`'s "Terraform /
google-provider compatibility" section below Deliverable 1's entries.

### Phase 0 — Research (DONE)
- No mature general-purpose "moto for GCP" exists (`drongo` is architecturally
  irrelevant to Terraform — it patches Python clients, not an HTTP server).
- `fake-gcs-server` (fsouza/fake-gcs-server) is a mature, real GCS wire-protocol
  emulator — adopt it for Storage instead of hand-rolling.
- No mature emulator exists for Compute Engine or VPC — must hand-build.
- **Empirically verified, not just researched**: the real `hashicorp/google`
  provider works against a local mock with zero real OAuth — a plain
  `access_token = "dummy-..."` plus a `*_custom_endpoint` override is
  sufficient. Full probe in `terraform-examples/gcs-probe/`, verified via
  `init -> apply -> direct curl verification -> destroy` against a real
  `fake-gcs-server` container. **No blocker.**

### Phase 1 — Build real fidelity, in priority order (finish each with a verified `init -> apply -> destroy` cycle before the next)

1. **Cloud Storage**: wrap this repo's existing `backend/app/api/storage.py` /
   `backend/app/services/storage/` behind (or replace with a proxy to) a
   Docker-managed `fake-gcs-server` instance, so `google_storage_bucket` /
   `google_storage_bucket_object` work via genuine GCS wire-protocol fidelity
   rather than hand-rolled JSON shapes. Reuse `docker_manager.py`'s container
   lifecycle patterns (this repo already has one; MiniCloud's is a close
   cousin) to run/manage the `fake-gcs-server` container itself.
2. **VPC Networks / Subnetworks** (`google_compute_network`,
   `google_compute_subnetwork`): no mature emulator exists; bring
   `backend/app/services/vpc/` into exact GCE REST API conformance
   (`compute_custom_endpoint`), including the async Operation-resource
   pattern described below.
3. **Compute Engine instances** (`google_compute_instance`): the hardest and
   most valuable. GCE's real API is asynchronous — `instances.insert`
   returns a `zone-scoped Operation` resource immediately, and the provider
   polls `GET .../operations/{name}` until `status: DONE`. Getting this
   polling contract exactly right is probably the single biggest fidelity
   gap versus today's synchronous hand-rolled implementation — treat it as
   its own sub-milestone before worrying about instance fields.

Architecture: keep protocol-fidelity logic (request parsing, response
shaping, Operation state machines) separated from FastAPI routing glue,
mirroring moto's own backend/model-vs-server split — apply this per service
as each is brought to conformance, not as a big-bang refactor.

### Verification bar
Every "done" claim needs a real `terraform-examples/<resource>/` config, run
against the real `terraform` binary (in WSL, where Docker also lives) with
actual verification (direct API call or `docker ps`, not just Terraform's own
exit code) — the same bar the `gcs-probe` established and MiniCloud was held
to.
