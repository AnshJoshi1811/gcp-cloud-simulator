# Engineering Decisions — Deliverable 1 (GCP Emulator)

Autonomous decisions made while completing the emulator, with rationale.

## 2026-10-09 — Authoritative backend layer
`backend/app/main.py` wires routers exclusively from `backend/app/services/<name>/`.
The legacy `backend/app/api/*.py` layer (compute.py, firewall.py, gke.py, iam.py,
projects.py, routes.py) is NOT imported by main.py except `storage.py`, which remains
the live Cloud Storage implementation (noted in its own main.py comment as "stable,
1100+ lines"). Decision: treat `services/` + `api/storage.py` as authoritative; leave
the rest of `api/*.py` in place but mark deprecated rather than delete, since deleting
dead code isn't needed to finish the task and risks breaking an undiscovered import.

(Update, 2026-10-09, separate cleanup pass on `main`: the dead `api/*.py` files above
were subsequently removed entirely after a verified-unreferenced audit — see `main`
branch commit `8d7fe3c`. Noted here so this entry isn't read as still-current advice
against deleting them.)

## 2026-10-09 — Tracker vs reality
IMPLEMENTATION_TRACKER.md's summary table undercounts completed work (says Secret
Manager "not started" when it's fully implemented and wired). Decision: trust the
actual code in `backend/app/services/` + `main.py` registrations as ground truth,
and correct the tracker/README narrative to match, rather than re-implementing
already-done services.

## 2026-10-09 — New services: in-memory storage by default
Most existing services (secretmanager, pubsub, monitoring, autoscaling) use an
in-memory singleton storage class rather than SQLAlchemy, despite CLAUDE.md citing
Postgres as the DB. Decision: keep following the in-memory pattern for new services
unless the service specifically needs Docker-backed persistence (Cloud SQL,
Memorystore) — consistency with existing code outweighs strict adherence to the
CLAUDE.md tech list, and it keeps services working even without a DB connection
(matches the `docker_manager.py` stub-mode philosophy: emulator stays up without
its backing infra).

## 2026-10-09 — Docker-optional services degrade gracefully
Cloud SQL / Memorystore containers follow `docker_manager.py`'s existing pattern:
if the Docker daemon is unavailable, fall back to a stub record (no real container)
rather than failing the API call, consistent with how Compute/VPC already behave.

## 2026-10-09 — Cloud Functions: Python-only, inline source, dual execution path
Real Cloud Functions supports many runtimes and a GCS-based source upload
flow (`generateUploadUrl` + zip). Decision: support Python 3.10/3.11/3.12
only for now (unsupported runtimes return a clear 400, not a crash), and
accept source code inline as a JSON string field rather than implementing
the upload-URL + zip flow — there's no real GCS bucket semantics worth
emulating here beyond what Cloud Storage already does, and inline source
is enough to prove out deploy/invoke end-to-end. Execution has two paths
mirroring `docker_manager.py`'s existing stub philosophy: when Docker is
available, each function builds a small on-the-fly `python:3.12-slim` image
with a stdlib-only HTTP shim and runs as a real warm container (like Cloud
Run); when Docker is unavailable (true in this dev sandbox — no Docker
Desktop installed), the function executes in-process via `exec()` against a
Flask-like fake request object. Both paths exercise the same HTTP invoke
contract, so this is real execution, not a canned response, in either mode.
Other runtimes (Node, Go, etc.) are a natural follow-up if someone wants to
extend `functions/executor.py`'s shim.

## 2026-10-09 — Deployment Manager: skipped by design
Real Cloud Deployment Manager parses Jinja2/Python-templated YAML and
reconciles arbitrary GCP resource graphs against it — a full mini-IaC engine.
Decision: skip it for this emulator rather than build a second, GCP-flavored
IaC engine, for three reasons: (1) the tracker itself already flagged it
lowest priority / Phase 4 / "skip for now"; (2) Deliverable 2 of this same
engineering effort (MiniCloud, `/minicloud`) requires building real Terraform
support against an AWS-shaped API — building a second IaC reconciler here
would be duplicate, lower-value effort against a budget better spent finishing
MiniCloud's explicit spec; (3) nothing else in this emulator depends on it.
If it's wanted later, the natural entry point is a `deploymentmanager`
service that parses a config's `resources:` list and dispatches to each
service's existing storage.create_* methods already built here.

(Update, 2026-10-09, this branch: reason #2 above is superseded in spirit by
the effort below — gcp-cloud-simulator itself is now pursuing real
Terraform compatibility directly, not just leaving it to MiniCloud. The
decision to skip Deployment Manager specifically still stands on its own
merits — see reasons #1 and #3 — but is no longer leaning on "that's
MiniCloud's job" as a rationale.)

## 2026-10-09 — Service Management: left partial
The tracker's row for Service Management ("billing/quotas") predates this
session and no corresponding `backend/app/services/service_management/`
module exists. Decision: leave it partial rather than build a fake billing
API — there is no real billing to emulate locally, and quota enforcement
isn't exercised by any other service in this codebase, so a stub would add
surface area without adding anything a user could meaningfully test against.
Noted here (rather than silently ignored) so the tracker's "partial" status
is a deliberate call, not an oversight.

## 2026-10-09 — Production-style repo restructuring

Owner's explicit request: a "production style repo structure" — standard
packaging, CI/CD, docs/governance files, repo tree cleanup, and separating
MiniCloud (an unrelated AWS product) out of this GCP-emulator repo. Done on
branch `restructure/production-layout`, landed via PR rather than direct to
`main`. Concrete changes and rationale:

- **MiniCloud extracted** to its own repository,
  [AnshJoshi1811/minicloud](https://github.com/AnshJoshi1811/minicloud).
  Attempted a history-preserving `git subtree split` first; abandoned it
  after it ran for 45+ minutes with almost no CPU time consumed (a known
  weakness of `git subtree split`'s algorithm, not a hang) — pushed a fresh
  snapshot commit instead. MiniCloud's original development history is
  still fully available in *this* repo's git history (commits `8dcd1ac`,
  `62da58f`, `b716540`) for anyone who needs it; only the new repo's own
  history starts fresh.
- **One more dead file found**: `backend/app/api/vpc.py` — unreferenced
  anywhere (verified via grep, same rigor as the earlier dead-code audit
  that caught `compute.py`/`firewall.py`/`gke.py`/`iam.py`/`projects.py`/
  `routes.py`), missed by that audit's search pattern. Removed.
- **Also removed**: `backend/database.py` and `backend/core/` (both
  explicitly self-documented "backward-compatibility shim"s with zero real
  importers — verified via grep), `backend/FEATURES_VERIFIED.md` (another
  orphaned point-in-time status doc, same genre as the ones removed in the
  earlier cleanup pass but missed since it was nested in `backend/` not
  root), and a stub root `package-lock.json` (`{"packages": {}}` — vestigial,
  the real one is `frontend/package-lock.json`).
- **Packaging**: `backend/requirements.txt` replaced by `backend/pyproject.toml`
  as the single source of dependency truth (standard `pip install -e .`
  instead of `pip install -r requirements.txt`). Also fixed `docker==7.0.0`
  → `docker>=7.1.0` here too — the same `urllib3`-2.x incompatibility
  (`Not supported URL scheme http+docker`) already fixed on the
  `feature/terraform-google-provider` branch.
- **CI/CD added** (none existed before): `.github/workflows/backend-ci.yml`
  (installs the package, boots the server, runs `pytest tests/integration`),
  `frontend-ci.yml` (lint + build), `docker-build.yml` (builds both images,
  smoke-tests via `docker compose up`). Added `backend/Dockerfile` (didn't
  exist — only the frontend had one) and a root `docker-compose.yml` wiring
  both together, with the host Docker socket mounted into the backend
  container so its own Docker-management features keep working when
  containerized.
- **Governance**: `LICENSE` (MIT — a permissive default, no stated reason to
  pick anything more restrictive), `CONTRIBUTING.md` (dev setup + the
  Terraform-compatibility verification bar), `.github/ISSUE_TEMPLATE/` (bug
  report + feature/service request), `.github/PULL_REQUEST_TEMPLATE.md`.
- **Repo tree**: loose root scripts (`stimulator`, `generate_context.py`,
  `test-connectivity.sh`) moved into `scripts/`; the `stimulator` script
  renamed to `stimulator.sh` (it had no extension at all). `.agents/`,
  `AI_AGENT_BUILD_ALL_PROMPT.md`, and `patches/` were explicitly NOT removed
  — the owner already decided to keep these in an earlier cleanup round.
- Fixed several stale docs discovered along the way: `README.md`/`CLAUDE.md`
  had hardcoded `/home/ubuntu/gcs-emulator/...`-style absolute paths from
  whoever's dev machine originally generated them, `requirements.txt`
  references throughout, and a `CLAUDE.md` "Adding a New GCP Service"
  section pointing at paths (`backend/database.py`, `backend/services/`,
  `backend/api/{name}.py`) that don't match where code actually lives
  (`backend/app/models/database.py`, `backend/app/services/{name}/router.py`).

(Further decisions appended below as work proceeds.)

---

# Terraform / google-provider compatibility

Engineering decisions for the effort to make gcp-cloud-simulator a genuine,
wire-protocol-faithful GCP API mock — the GCP ecosystem's equivalent of
`moto` — using the real `hashicorp/google` Terraform provider as the
empirical conformance test, mirroring the role moto's AWS-provider
compatibility plays for moto itself.

## 2026-10-09 — Phase 0 finding #1: no mature "moto for GCP" exists, but mature *per-service* emulators do

Searched for an existing general-purpose GCP mock with AWS-moto-level
coverage and maturity. Conclusion: **nothing comparable exists.**

- `drongo` (PyPI, claims to be "the moto for GCP") — works by monkey-patching
  the Python `google-cloud-*` client libraries in-process (no HTTP server at
  all). This architecture is irrelevant to Terraform compatibility: Terraform
  is a compiled Go binary that speaks GCP's REST/JSON wire protocol directly —
  it never goes through a Python client library, so patching one does nothing
  for us. Ruled out entirely for this project's purpose, regardless of its
  maturity.
- `mock-gcp` (PyPI) — explicitly marked "not yet working," storage-only.
  Not viable.
- **`fake-gcs-server`** (github.com/fsouza/fake-gcs-server, Go) — this IS a
  mature, real, widely-used emulator: runs a genuine HTTP(+gRPC) server that
  speaks GCS's actual JSON/XML/resumable-upload wire protocol, used
  extensively in CI pipelines across the Go/GCP ecosystem for years. This is
  the GCS equivalent of what moto is to S3.
- Google's own official emulators (Pub/Sub, Firestore, Datastore, Spanner,
  Bigtable — shipped with `gcloud` SDK, genuinely protocol-faithful) exist
  for several services, but notably **not** for Compute Engine or VPC — the
  services this project's Terraform-compatibility priority order actually
  needs most. Confirmed no official or mature third-party Compute
  Engine/VPC emulator exists anywhere; that fidelity work has no shortcut and
  must be built directly in this repo.

**Decision:** adopt the same strategy MiniCloud used with moto — prefer a
mature, already-correct emulator per service where one exists, and only
hand-build protocol fidelity where it doesn't:
- **Cloud Storage → wrap/proxy `fake-gcs-server`** instead of hand-rolling
  GCS wire-protocol fidelity. This repo's existing Storage service becomes a
  thin layer in front of a real `fake-gcs-server` instance (likely
  Docker-managed, mirroring how MiniCloud manages containers), rather than
  reimplementing GCS's JSON API by hand.
- **VPC Networks/Subnetworks and Compute Engine instances → no mature
  emulator exists; must be hand-built** to real GCP REST API conformance.
  This is genuinely the hard, novel part of the whole effort — same
  conclusion MiniCloud reached about EC2-to-Docker orchestration being its
  real value-add once moto solved AWS protocol fidelity.

## 2026-10-09 — Phase 0 finding #2: the real Terraform google provider CAN be pointed at a local mock with fake credentials — empirically verified, not just researched

This was the critical viability question, and it is **resolved positively**,
with a real, witnessed end-to-end test (not just documentation reading):

- Ran real `fake-gcs-server` (Docker, `fsouza/fake-gcs-server`, `-scheme http`)
  on `localhost:4443` inside WSL Ubuntu-24.04 (the same environment used to
  verify MiniCloud).
- Wrote a minimal `terraform-examples/gcs-probe/main.tf`: real
  `hashicorp/google` provider v5.45.2 (the actual, unmodified provider —
  `terraform init` pulled it from the public registry), configured with:
  ```hcl
  provider "google" {
    project      = "test-project"
    region       = "us-central1"
    access_token = "dummy-access-token"
    storage_custom_endpoint = "http://localhost:4443/storage/v1/"
  }
  ```
- Ran the real `terraform` binary: `init` → `apply` → verified the bucket
  genuinely exists via a direct, unsigned `curl` to fake-gcs-server's own API
  (not just trusting Terraform's "Apply complete" message) → `destroy`.
  **All four steps succeeded for real**, full transcript:
  - `apply`: `google_storage_bucket.probe: Creation complete after 0s
    [id=mock-probe-bucket]`
  - Direct verification: `curl http://localhost:4443/storage/v1/b/mock-probe-bucket`
    returned a real bucket JSON object (`"id":"mock-probe-bucket"`, real
    timestamps, etc.) — not a Terraform-only illusion.
  - `destroy`: `google_storage_bucket.probe: Destruction complete after 0s`

**Conclusion: there is no hard OAuth blocker.** Unlike what might be assumed
(GCP auth is OAuth2/service-account-centric, unlike AWS's simpler
access-key model), the `hashicorp/google` provider accepts a plain
`access_token` string with zero validation against Google's real OAuth
servers, and happily sends all subsequent API calls to whatever
`*_custom_endpoint` you configure. There was no need for AWS-style
`skip_credentials_validation` flags — the `access_token` auth path simply
never validates the token at all; it's used purely as a bearer token sent on
each request, which our mock can (and must) just ignore/accept.

This means: **the entire approach is viable**, for every GCP service the
provider has a `*_custom_endpoint` setting for (this covers the large
majority of resources, including `compute_custom_endpoint` for Compute
Engine/VPC resources — not yet tested empirically but the same auth
mechanism applies, since `access_token` is provider-wide, not
per-service).

## 2026-10-09 — Phase 0 outcome / what's next

No blocker. Phase 1 (building real fidelity for VPC and Compute Engine, and
wrapping fake-gcs-server for Storage) is a green light, but is substantial,
multi-session implementation work — each service needs the exact request/
response JSON schema the real provider sends/expects brought into
conformance, not just enough to pass one trivial probe. Scoped as the next
phase of this effort; see PLAN.md for milestones. The empirical method
established here (real `fake-gcs-server`/real-provider probe, verified via
direct API call rather than trusting Terraform's own output) is the
template every subsequent resource's "done" claim must meet.

## 2026-10-09 — Phase 1 milestone 1: Cloud Storage proxy, DONE and verified

Added `backend/app/services/storage/gcs_proxy.py`: a thin FastAPI proxy for
the exact GCS wire-protocol paths a Terraform `google_storage_bucket` /
`google_storage_bucket_object` cycle needs (`/storage/v1/b`,
`/storage/v1/b/{bucket}`, `/storage/v1/b/{bucket}/o`,
`/storage/v1/b/{bucket}/o/{object}`, `/upload/storage/v1/b/{bucket}/o`,
`/download/storage/v1/b/{bucket}/o/{object}`), forwarding verbatim to a
real, Docker-managed `fake-gcs-server` container
(`backend/app/core/docker_manager.py`'s new `ensure_fake_gcs_server()`,
mirroring the existing `ensure_local_registry()` pattern). Registered in
`main.py` BEFORE the legacy `backend/app/api/storage.py` router, so these
specific path+method combinations are intercepted first; everything else
that router still does (dashboard stats, signed URLs, ACLs, rewrite) is
untouched and keeps working exactly as before — **decision: proxy, don't
replace**, per the plan already written up above, specifically to avoid
breaking the existing frontend dashboard, which depends on
`storage.py`-only endpoints like `/dashboard/stats`.

**Bug fixed along the way**: `docker==7.0.0` (this repo's pinned version)
is incompatible with `urllib3==2.x` (`Error while fetching server API
version: Not supported URL scheme http+docker`) — the same class of
environment issue MiniCloud's own Docker integration could have hit.
Bumped the pin to `docker>=7.1.0` in `backend/requirements.txt`.

**Verified for real**, not just unit-tested: real `fake-gcs-server`
container running via Docker, real backend server (`uvicorn`, this repo's
actual `app.main:app`) on port 8090, real `hashicorp/google` provider
v5.45.2, real `terraform` binary — `terraform-examples/gcs-bucket-and-object/`
ran a full `init -> apply -> destroy` cycle creating BOTH a bucket and an
object (the `gcs-probe` milestone only tested the bucket):
- `apply`: both resources created, object content set to a real string.
- Verified via TWO independent direct API calls (not just Terraform's own
  success message): our own proxy's download path returned the exact
  uploaded content byte-for-byte, and fake-gcs-server's own API directly
  (bypassing our proxy entirely) confirmed the object's real metadata
  (checksums, etag, timestamps).
- `destroy`: both resources removed; confirmed via a direct call to
  fake-gcs-server's API returning a genuine 404, not just trusting
  Terraform's destroy output.

Cloud Storage is the first service in this repo with Terraform-provider-
verified wire-protocol fidelity, not just `gcloud` CLI compatibility.
IMPLEMENTATION_TRACKER.md and README.md updated accordingly.

Next: VPC Networks/Subnetworks (Phase 1, item 2) — no mature emulator
exists for this, so it needs to be hand-built to real GCE REST API
conformance rather than proxied to something else.
