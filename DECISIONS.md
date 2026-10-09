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

(Further decisions appended below as work proceeds.)
