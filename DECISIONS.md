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

## 2026-10-09 — Service Management: left partial
The tracker's row for Service Management ("billing/quotas") predates this
session and no corresponding `backend/app/services/service_management/`
module exists. Decision: leave it partial rather than build a fake billing
API — there is no real billing to emulate locally, and quota enforcement
isn't exercised by any other service in this codebase, so a stub would add
surface area without adding anything a user could meaningfully test against.
Noted here (rather than silently ignored) so the tracker's "partial" status
is a deliberate call, not an oversight.

(Further decisions appended below as work proceeds.)
