# GCP Stimulator — Project Reference

Single consolidated reference for this repo: architecture, commands, current
service status, the roadmap, and the full engineering-decisions log. (Merged
2026-10-09 from what used to be four separate files — `CLAUDE.md`,
`PLAN.md`, `IMPLEMENTATION_TRACKER.md`, `DECISIONS.md` — see the "Repo
housekeeping" decision near the end of the log for why.)

**Mission** (owner's own words): be for GCP what
[LocalStack](https://github.com/localstack/localstack) is for AWS — a real
local server the official, unmodified Terraform `google` provider (and
eventually other GCP SDKs) can be pointed at via endpoint overrides, with
genuine wire-protocol fidelity per resource, not just enough to satisfy
`gcloud` CLI calls. Long-term, resource-by-resource effort; current
real-provider-verified coverage is in the Decisions Log below.

---

## 1. Tech stack

**Backend**: FastAPI + Uvicorn, SQLAlchemy (SQLite by default; set
`DATABASE_URL` for Postgres), `docker` SDK for container lifecycle, REST/JSON.
**Frontend**: React 18 + TypeScript, Vite, Tailwind CSS, React Router v6, Axios.
**Ports**: backend `:8080`, frontend `:3000`.

## 2. Repo structure

See [README.md](README.md)'s "Project Structure" section for the full tree.
Backend service pattern: `backend/app/services/<name>/{models,storage,router}.py`,
registered in `backend/app/main.py` with a GCP-shaped URL prefix. The old
`backend/app/api/*.py` layer is gone except `storage.py` (still live — see
log entry below) and the new `storage/gcs_proxy.py`.

## 3. Architecture

```
Request → uvicorn/FastAPI → router (app/services/<name>/router.py)
        → storage layer (in-memory singleton, or SQLAlchemy for a few
          services, or Docker-backed for Compute/VPC/SQL/Memorystore/
          Storage-via-fake-gcs-server)
        → Response (JSON)
```

- **Docker Container Mapping**: each VM instance = a real Docker container
  (`ubuntu:22.04` by default); each VPC = a real Docker network.
- **Cloud Storage**: core bucket/object paths proxy to a real,
  Docker-managed `fake-gcs-server` instance for genuine GCS wire-protocol
  fidelity (see log). Everything else Storage does (dashboard stats, signed
  URLs, ACLs) stays on the legacy in-memory handler.
- **Graceful degradation**: if the Docker daemon is unreachable, Docker-backed
  services fall back to a stub record instead of failing the API call — the
  emulator stays usable without its backing infra.

## 4. Commands

```bash
# Backend (from backend/)
pip install -e ".[test]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Frontend (from frontend/)
npm install && npm run dev

# Both together
docker compose up --build        # repo root

# Tests (from repo root)
python -m pytest tests/integration -k "not gcloud"

# Utilities
bash scripts/test-connectivity.sh
python scripts/generate_context.py
source scripts/stimulator.sh {on,off,status}   # redirect gcloud CLI at the emulator
```

## 5. Adding a new GCP service

1. Add any new SQLAlchemy models to `backend/app/models/database.py` (most
   services use an in-memory singleton instead — see log entry below).
2. Create service logic in `backend/app/services/{service_name}/`
   (`models.py`, `storage.py`/business logic, `router.py`).
3. Register the router in `backend/app/main.py`.
4. Create a React page in `frontend/src/pages/`, an API client in
   `frontend/src/api/{service_name}.ts`, a route in `App.tsx`.
5. Integration tests under `tests/integration/test_<service>.py`
   (+ `_gcloud.py` for CLI-flavored checks).
6. Update the Service Status table below.

## 6. Gotchas

1. Docker-backed features need the Docker daemon running — otherwise stub mode.
2. `DATABASE_URL` is optional (defaults to local SQLite).
3. Storage objects (legacy path) persist on the filesystem at `/tmp/gcs-storage/` — ephemeral in containers; the new fake-gcs-server-backed path persists inside that container instead.
4. Docker networks use the bridge driver only — host network mode isn't supported.
5. `.env-gcloud` configures `gcloud` CLI redirection; some `gcloud` commands have limited compatibility (see `tests/gcloud_wrappers/`).

---

## 7. Roadmap

### Deliverable 1 — Finish the GCP emulator (DONE, 24/26 services)
Remaining gaps are deliberate, not oversights: **Service Management**
(billing/quotas) left partial — no real billing to emulate locally.
**Deployment Manager** skipped — see Decisions Log.

### Deliverable 2 — MiniCloud (extracted)
Originally built at `/minicloud` in this repo (a separate AWS-API-shaped
emulator for the real Terraform `aws` provider). Extracted to its own
repository, [AnshJoshi1811/minicloud](https://github.com/AnshJoshi1811/minicloud)
— unrelated product, didn't belong mixed into a GCP emulator. Its own
`DECISIONS.md`/`PLAN.md` now live there.

### Deliverable 3 — Real `hashicorp/google` Terraform-provider compatibility (in progress)
The actual "LocalStack for GCP" effort. Branch: `feature/terraform-google-provider`
(merged into `main` as of 2026-10-09; further work continues on new branches
off `main`). Status, in priority order:

1. **Cloud Storage** — ✅ done, real-provider-verified (proxies to
   `fake-gcs-server`). See Decisions Log for the full verification trail.
2. **VPC Networks/Subnetworks** — not started. No mature emulator exists;
   must be hand-built to real GCE REST API conformance
   (`compute_custom_endpoint`).
3. **Compute Engine instances** — not started. The hardest piece: GCE's
   real API is asynchronous (`insert` returns an Operation resource the
   provider polls until `DONE`) — today's implementation is synchronous.
   Get the Operation-polling contract right before worrying about instance
   fields.

**Verification bar for every "done" claim**: a real
`terraform-examples/<resource>/` config run against the real `terraform`
binary (WSL, where Docker also lives), with independent verification (a
direct API call or `docker ps` — never just Terraform's own exit code), AND
a passing run of the existing `tests/integration` suite (Terraform-cycle
verification alone has already been shown to miss things the test suite
catches, and vice versa).

### Working rules
Small, frequent commits, push after each milestone. Never crash on
unsupported calls — return GCP-shaped JSON errors. Ambiguity → pick the
sensible default, log it in the Decisions Log below, keep moving.

---

## 8. Service Status

**24/26 cataloged services implemented** (92%). 1 intentionally partial
(Service Management), 1 intentionally skipped (Deployment Manager) — both
with rationale in the Decisions Log. This is a **local development tool**,
not a certified GCP replacement: not API-complete, doesn't enforce
IAM/quota limits, and some services use simplified semantics (e.g. Cloud
KMS encryption is a reversible local stand-in, not real cryptography). It
is, however, functionally real where it counts: Compute/VPC/SQL/Memorystore
spin up actual Docker containers and networks, Cloud Functions actually
executes your code, Cloud CDN actually caches real Storage bytes, Event
Routing actually dispatches Pub/Sub messages to Cloud Functions, and Cloud
Storage's core paths proxy to a real `fake-gcs-server` backend.

| # | Service | Status | Notes |
|---|---|---|---|
| 1 | Projects | ✅ Complete | Scopes all resources |
| 2 | Service Management | 🟡 Partial | Billing/quotas — intentionally left partial, no real billing to emulate |
| 3 | VPC Networks | ✅ Complete | Routing, subnets, firewalls — real Docker networks |
| 4 | Compute Engine | ✅ Complete | Instances, zones, machine types — real Docker containers |
| 5 | Cloud Storage | ✅ Complete | Buckets, objects, versioning. Core CRUD proxies to real `fake-gcs-server`, real-provider-verified |
| 6 | IAM & Admin | ✅ Complete | Roles, service accounts |
| 7 | Secret Manager | ✅ Complete | |
| 8 | Cloud KMS | ✅ Complete | Key rings, crypto keys; encryption is a reversible local stand-in, not real crypto |
| 9 | Cloud Tasks | ✅ Complete | Queues + tasks, live dispatcher |
| 10 | Cloud SQL | ✅ Complete | Real Postgres/MySQL via Docker (stub mode without Docker) |
| 11 | Memorystore | ✅ Complete | Real Redis via Docker (stub mode without Docker) |
| 12 | Firestore | ✅ Complete | In-memory document store, typed-value wire format |
| 13 | GKE | ✅ Complete | Kubernetes cluster emulation |
| 14 | Cloud Run | ✅ Complete | Container services |
| 15 | Cloud Pub/Sub | ✅ Complete | Topics/subscriptions |
| 16 | Cloud Logging | ✅ Complete | entries.write/list + sinks |
| 17 | Cloud Monitoring | ✅ Complete | Metrics/alerts |
| 18 | Artifact Registry | ✅ Complete | Image management |
| 19 | Cloud Load Balancer | ✅ Complete | Real round-robin HTTP routing via `:simulate` |
| 20 | Auto-Scaling | ✅ Complete | |
| 21 | Cloud Functions | ✅ Complete | Python-only; real container execution when Docker available, in-process `exec()` fallback otherwise |
| 22 | API Gateway | ✅ Complete | Real proxy to deployed Functions or arbitrary URLs |
| 23 | Cloud Identity Platform | ✅ Complete | Email/password auth, salted-hash storage |
| 24 | Deployment Manager | ⬜ Skipped | Deliberate — see Decisions Log |
| 25 | Event Routing | ✅ Complete | Real Pub/Sub → Cloud Functions dispatch |
| 26 | Cloud CDN | ✅ Complete | Real in-memory cache fronting actual Storage objects |

---

## 9. Engineering Decisions Log

Autonomous/judgment-call decisions, with rationale, in chronological order.

### 2026-10-09 — Authoritative backend layer
`backend/app/main.py` wires routers exclusively from `backend/app/services/<name>/`.
The legacy `backend/app/api/*.py` layer was removed entirely after a
verified-unreferenced audit (dead code: `compute.py`, `firewall.py`,
`gke.py`, `iam.py`, `projects.py`, `routes.py`, and later `vpc.py` too, found
by a second pass) — `storage.py` is the one file in that layer that's still
live (the Cloud Storage dashboard/ACL/signed-URL handlers).

### 2026-10-09 — Tracker vs reality
The old tracker undercounted completed work (e.g. said Secret Manager "not
started" when it was fully implemented and wired). Decision: trust the
actual code in `backend/app/services/` + `main.py` registrations as ground
truth, correct the tracker/README narrative to match, rather than
re-implementing already-done services.

### 2026-10-09 — New services: in-memory storage by default
Most existing services (secretmanager, pubsub, monitoring, autoscaling) use
an in-memory singleton storage class rather than SQLAlchemy. Decision: keep
following that pattern for new services unless the service specifically
needs Docker-backed persistence (Cloud SQL, Memorystore) — consistency with
existing code outweighs strict DB-everywhere purity, and it keeps services
working even without a DB connection.

### 2026-10-09 — Docker-optional services degrade gracefully
Cloud SQL / Memorystore containers follow `docker_manager.py`'s existing
pattern: if the Docker daemon is unavailable, fall back to a stub record
rather than failing the API call, consistent with how Compute/VPC behave.

### 2026-10-09 — Cloud Functions: Python-only, inline source, dual execution path
Real Cloud Functions supports many runtimes and a GCS upload-URL+zip flow.
Decision: Python 3.10/3.11/3.12 only (other runtimes return a clean 400),
inline source as a JSON string field (no real GCS semantics worth
emulating beyond what Storage already does). Execution has two paths:
real container (`python:3.12-slim` + stdlib HTTP shim) when Docker is
available, in-process `exec()` against a fake request object otherwise —
both genuinely execute user code, neither is a canned response.

### 2026-10-09 — Deployment Manager: skipped by design
Real Deployment Manager parses Jinja2/Python-templated YAML and reconciles
arbitrary resource graphs — a full mini-IaC engine. Skipped because: (1)
always flagged lowest priority; (2) building a second IaC reconciler here
would duplicate the real Terraform-compatibility effort (Deliverable 3)
that's a better use of the same budget; (3) nothing else depends on it. If
wanted later: a `deploymentmanager` service parsing a config's `resources:`
list and dispatching to each service's existing `storage.create_*` methods.

### 2026-10-09 — Service Management: left partial
No corresponding `backend/app/services/service_management/` module exists.
Left partial rather than build a fake billing API — no real billing to
emulate locally, and quota enforcement isn't exercised anywhere else in
this codebase, so a stub would add surface area without anything
meaningful to test against.

### 2026-10-09 — Production-style repo restructuring
Owner's explicit request: a "production style repo structure." Landed via
PR (`restructure/production-layout` → `main`), not direct to `main`.
Changes:
- **MiniCloud extracted** to [AnshJoshi1811/minicloud](https://github.com/AnshJoshi1811/minicloud).
  Attempted a history-preserving `git subtree split` first; abandoned after
  45+ minutes with almost no CPU time consumed (a known weakness of that
  command, not a hang) — pushed a fresh snapshot instead. Original history
  stays in *this* repo's log (commits `8dcd1ac`, `62da58f`, `b716540`).
- **Dead code removed**: `backend/database.py` + `backend/core/` (both
  self-documented backward-compat shims, zero real importers, verified via
  grep), `backend/FEATURES_VERIFIED.md` (orphaned status doc), a stub root
  `package-lock.json`.
- **Packaging**: `backend/requirements.txt` → `backend/pyproject.toml`
  (`pip install -e .`). Bumped `docker==7.0.0` → `docker>=7.1.0` (fixes a
  real `urllib3` 2.x incompatibility: `Not supported URL scheme http+docker`).
- **CI/CD added** (none existed before): `.github/workflows/{backend,frontend}-ci.yml`
  + `docker-build.yml`. Added the missing `backend/Dockerfile` and a root
  `docker-compose.yml` (host Docker socket mounted through).
- **Governance**: MIT `LICENSE`, `CONTRIBUTING.md`, issue/PR templates.
- **Repo tree**: loose root scripts moved into `scripts/` (`stimulator` →
  `stimulator.sh`). `.agents/`, `AI_AGENT_BUILD_ALL_PROMPT.md`, `patches/`
  were deliberately kept in an earlier cleanup round at the time, per the
  owner's choice then — later removed in the housekeeping pass below once
  the owner revisited that call.
- Fixed stale docs found along the way: hardcoded `/home/ubuntu/...`
  paths, `requirements.txt` references, a stale "Adding a New GCP Service"
  section pointing at paths that don't match where code actually lives.

### 2026-10-09 — Explicit mission: be for GCP what LocalStack is for AWS
Owner's own words: *"we have to do for GCP what LocalStack is doing for
AWS."* LocalStack is the more accurate reference point than moto for the
project as a whole — a running server the real, unmodified provider's
Terraform plugin talks to over HTTP (this project's own architecture), not
an in-process Python mocking library. moto-style adoption (`fake-gcs-server`)
remains the right per-service tactic where a mature wire-protocol-faithful
emulator already exists. Honest scale context: LocalStack covers 100+ AWS
services over ~8 years of community effort; this effort currently has 1
service/2 resource types real-provider-verified (Cloud Storage). Long-term,
multi-session roadmap, not a sprint.

### 2026-10-09 — Terraform/google-provider compatibility: Phase 0 research (empirically verified, not just researched)

No mature general-purpose "moto for GCP" exists. `drongo` claims the title
but monkey-patches Python `google-cloud-*` client libraries in-process (no
HTTP server) — irrelevant to Terraform, which is a Go binary speaking the
wire protocol directly, never through a Python client. `mock-gcp` is
explicitly "not yet working." **`fake-gcs-server`** (fsouza/fake-gcs-server,
Go) IS a mature, real, widely-used GCS wire-protocol emulator — adopted for
Storage instead of hand-rolling. Google's own official emulators
(Pub/Sub, Firestore, Datastore, Spanner, Bigtable) exist but notably **not**
for Compute Engine or VPC — confirmed no mature emulator exists for either;
that fidelity work has no shortcut and must be hand-built.

**Critical viability question, resolved positively, with a real witnessed
test**: ran real `fake-gcs-server` in WSL, wrote `terraform-examples/gcs-probe/`
using the real `hashicorp/google` provider v5.45.2 with
`access_token = "dummy-access-token"` + `storage_custom_endpoint` pointed at
it. Full `init → apply → destroy` cycle succeeded for real, verified via a
direct unsigned `curl` to fake-gcs-server's own API (not just trusting
Terraform's own success message). **Conclusion: no hard OAuth blocker** —
the provider's `access_token` auth path never validates the token at all;
it's a bearer token our mock can just accept. This applies provider-wide,
not per-service, so the same approach should work for
`compute_custom_endpoint` too (not yet tested empirically).

### 2026-10-09 — Phase 1 milestone 1: Cloud Storage proxy, done and verified

Added `backend/app/services/storage/gcs_proxy.py`: proxies the GCS
wire-protocol paths a Terraform `google_storage_bucket`/
`google_storage_bucket_object` cycle needs to a real, Docker-managed
`fake-gcs-server` container (`docker_manager.py`'s `ensure_fake_gcs_server()`).
Registered in `main.py` BEFORE the legacy `storage.py` router, so these
specific paths are intercepted first — decision: **proxy, don't replace**,
to avoid breaking the frontend dashboard's `storage.py`-only endpoints
(`/dashboard/stats`, signed URLs, ACLs).

Verified for real: real `fake-gcs-server` + real backend server + real
`hashicorp/google` provider + real `terraform` binary —
`terraform-examples/gcs-bucket-and-object/` ran a full
`init → apply → destroy` cycle creating BOTH a bucket and an object,
verified via two independent direct API calls (our proxy's download path
returned the exact uploaded content byte-for-byte; fake-gcs-server's own
API confirmed real metadata), and destroy confirmed via a genuine 404.
Cloud Storage is the first service here with Terraform-provider-verified
fidelity, not just `gcloud` CLI compatibility.

**Post-merge bugs found by CI** (once this branch merged with `main`,
which added real CI in the restructuring PR): two real `gcs_proxy` bugs
that manual Terraform-only testing had missed, both found by the existing
`tests/integration/test_storage.py::test_upload_object` test:
1. `POST /storage/v1/b/{bucket}/o` (GCS's "simple upload" convention,
   `uploadType=media&name=...` — used by `gcloud`/older SDKs, not
   Terraform) wasn't proxied at all, so it fell through to the legacy
   handler's own separate, now-stale bucket registry → 404s against
   buckets that genuinely exist via the proxy.
2. The first fix forwarded that path verbatim to fake-gcs-server — which,
   verified directly via `curl`, does NOT implement inserts on the bare
   path at all (404), only under `/upload/storage/v1/b/{bucket}/o`. Fixed
   by translating the request to the path fake-gcs-server actually serves.

Both confirmed fixed via the same test returning to its pre-existing
passing state, verified in GitHub Actions (not just locally) after each
fix. **Lesson**: Terraform-cycle verification proves Terraform
compatibility specifically — it doesn't substitute for the existing
integration test suite, which exercises conventions Terraform itself never
uses. Having real CI (new as of this same merge) caught this the moment it
existed.

**Known pre-existing, unrelated test failures**: 5 tests fail
(`test_apigateway`, `test_compute::test_list_zones`, `test_functions` x2,
`test_vpc::test_create_firewall_rule`) identically on both `main` and this
branch — confirmed by diffing CI summaries, not assumed. Predate this
work entirely; filed as
[issue #5](https://github.com/AnshJoshi1811/gcp-cloud-simulator/issues/5)
rather than silently merged past.

Next: VPC Networks/Subnetworks (Phase 1, item 2) — no mature emulator
exists; hand-build to real GCE REST API conformance.

### 2026-10-09 — Repo housekeeping: one consolidated reference doc, README shrunk, branch protection
Owner's request: a small README, all the scattered engineering `.md` files
merged into one, and `main` protected. Decisions:
- **Merged** `CLAUDE.md` + `PLAN.md` + `IMPLEMENTATION_TRACKER.md` +
  `DECISIONS.md` into this single file (keeping the `CLAUDE.md` name — most
  recognized, least churn for existing references). Dropped the stale
  week-by-week phase schedules, "next service to implement" sections, and
  progress-dashboard ASCII art from the old tracker — all superseded by the
  (accurate) summary/matrix table, which is what's kept here. `DECISIONS.md`'s
  content is kept close to verbatim since it's the most load-bearing and
  recently-written part.
- **Removed** `AI_AGENT_BUILD_ALL_PROMPT.md` (a 1000-line build-generation
  prompt with no ongoing purpose) and `.agents/` (AI agent-skill scaffolding,
  same reasoning) — revisiting the earlier cleanup round's choice to keep
  them, now that the owner flagged them as "unwanted" directly.
- **README.md** trimmed to: mission blurb, quickstart, service catalog
  table, links to this file for everything else (architecture, full
  decision history, roadmap) — the exhaustive `gcloud` command listings and
  duplicated feature descriptions moved here or cut as redundant with the
  Service Status table above.
- **Branch protection** added to `main` via the GitHub API: PRs required
  (no direct pushes), 1 approving review, the three CI workflows required
  to pass, force-pushes and branch deletion blocked. This repo's own
  working style up to this point — committing straight to feature
  branches and merging via PR — already matched this; protection just
  makes it enforced rather than just habitual.
