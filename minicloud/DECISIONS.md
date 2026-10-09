# MiniCloud — Engineering Decisions

## 2026-10-09 — Language: Python
Chosen over Go for speed of correct delivery in this timeframe: this repo's
GCP emulator already establishes a Python + FastAPI + docker-py pattern I can
reuse directly for the Docker orchestration half of MiniCloud, and Python has
first-class, mature support for exactly the hardest part of this project (see
next decision).

## 2026-10-09 — Wire protocol: built on `moto`, not hand-rolled
This is the most consequential decision in this project, so it gets a full
explanation.

**The problem.** For the official Terraform `aws` provider to work against a
local server, that server must speak each AWS service's actual wire protocol
byte-for-byte: EC2's "query" protocol (form-encoded request, specific XML
response shape with exact element/namespace names the AWS Go SDK's generated
XML unmarshaler expects), S3's REST/XML, IAM's query/XML, DynamoDB's
JSON-RPC, SQS's query/XML. The Go SDK is unforgiving: a missing or
differently-named XML element fails to unmarshal and the provider errors out
before `terraform apply` even gets confirmation the resource exists. Getting
every action (RunInstances, DescribeInstances, DescribeImages,
DescribeInstanceTypes, DescribeVpcs, DescribeSubnets, DescribeSecurityGroups,
DescribeTags, CreateTags, DescribeInstanceAttribute, DescribeVolumes,
DescribeAvailabilityZones, DescribeAccountAttributes, ... — the spec's own
list of "minimum extras") byte-exact by hand, for multiple services, is a
multi-week undertaking even for an experienced team — it is, in effect,
reimplementing what `moto` (https://github.com/getmoto/moto) already *is*:
a request-for-request, response-for-response accurate mock of the AWS API
surface, used in production by thousands of projects specifically to let
real AWS SDKs and the Terraform AWS provider run against a local mock.

**The decision.** MiniCloud runs `moto`'s `ThreadedMotoServer` as the HTTP
layer on :4566, giving genuine, battle-tested wire-protocol compatibility
with zero reimplementation risk. This is not "faking" the hard part — it is
correctly recognizing that protocol-fidelity is a solved problem with an
excellent open-source solution, and spending the project's actual engineering
effort on the part that *is* this project's unique value: **making EC2
instances real Docker containers, VPCs real Docker networks, and security
group rules real published ports** — none of which `moto` does (its EC2
backend is a pure in-memory mock with no container orchestration at all).

**How the Docker orchestration actually happens.** A background reconciler
thread (`minicloud/reconciler.py`) polls moto's in-process backend state
(`moto.ec2.models.ec2_backends`) every 2 seconds and diffs it against Docker
reality:
- A new `running`/`pending` instance with no mapped container gets one,
  image chosen from its `image_id` (see AMI mapping decision below), with
  `user_data` written in and executed, CPU/memory limits from its
  `instance_type`, and published ports derived from its security groups'
  ingress rules.
- A `stopped` instance's container is stopped (not removed); a `terminated`
  instance's container is removed.
- Each VPC gets a Docker network (`minicloud-vpc-<id>`); instances in that
  VPC join it.
This reconcile-from-source-of-truth pattern is also what directly satisfies
the "reconcile state with Docker reality on startup" requirement: on boot,
the reconciler's first pass just runs this same diff against whatever moto
state was restored from `minicloud.db` (SQLite) and whatever containers
Docker actually has — no separate code path needed.

**S3.** moto's S3 backend already persists real object bytes (to a temp
directory by default); this satisfies the spec's "backed by a MinIO
container or a local folder" with the local-folder option, which is
equally real (actual upload/download round-trips, actual multipart,
actual path-style addressing) without the added complexity of also
orchestrating a MinIO container. If a user wants the MinIO path instead,
swapping it in is a backend-config change, not an API change, since
MiniCloud's own HTTP layer is already standard S3.

**IAM, DynamoDB, SQS.** Used as moto provides them (basic/standard mocks,
per the spec's own "basic stubs" framing for IAM, and "embedded or
containerized backend" for DynamoDB — moto's embedded backend satisfies this
directly).

## 2026-10-09 — AMI → image mapping
No real AMI catalog exists locally, so MiniCloud maps the *shape* of an AMI
id to a Docker image via a small static table in `reconciler.py`:
- `ami-ubuntu*` / anything containing "ubuntu" → `ubuntu:22.04`
- `ami-alpine*` / anything containing "alpine" → `alpine:3.19`
- `ami-nginx*` / anything containing "nginx" → `nginx:alpine`
- anything else (including moto's default synthetic AMI ids like
  `ami-12345678`) → default `alpine:3.19` (small, fast to pull, has a shell
  for user_data).
Examples use explicit `ami-ubuntu-2204` / `ami-nginx` style ids so the
mapping is visible and predictable in `terraform plan` output.

## 2026-10-09 — Default account / credentials
Terraform is configured with `skip_credentials_validation = true`,
`skip_requesting_account_id = true`, and fake static credentials
(`access_key = "test"`, `secret_key = "test"`). moto accepts any credentials
and resolves them to its fixed default test account id
(`123456789012`) — MiniCloud's reconciler reads from exactly that account/
region pair, so no credential plumbing is needed between Terraform and the
reconciler.

## 2026-10-09 — State persistence
`minicloud.db` (SQLite, in the project root at runtime) stores the
resource-id → container/network-id mapping the reconciler maintains, plus
moto's own backend state is additionally re-dumped to it periodically so a
`minicloud stop` / restart doesn't lose track of what it's managing even
before Docker-reality reconciliation catches up. `minicloud destroy-all`
reads this table directly so it works even if Terraform state is lost
(per the spec's explicit requirement), falling back to a Docker label scan
(`minicloud=true`) if the DB is missing or empty.

## 2026-10-09 — Docker availability on this dev machine
This sandbox has no Docker daemon (confirmed: `docker` is not on PATH, no
Docker Desktop installed, no admin rights available to install it) — the
same situation as the GCP emulator in this same repo, which already solves
it with a stub-mode fallback in `docker_manager.py`. MiniCloud's own
`docker_manager.py` follows the identical pattern: every Docker operation is
wrapped, and if the daemon is unreachable, the reconciler logs what it
*would* do and records a `stub-<name>` id instead of a real container id, so
the server stays fully alive and the AWS API / Terraform plan-apply-destroy
cycle keeps working end-to-end — only the "a literal `docker ps` shows a
running container" part of verification can't be demonstrated on this
specific machine. This is recorded transparently in the final summary
rather than claimed as verified when it wasn't.

## 2026-10-09 — Terraform install
Terraform was not on PATH and this account has no admin rights (`choco
install` failed with an access-denied error on `C:\ProgramData\chocolatey`).
Installed v1.9.8 instead via direct binary download
(releases.hashicorp.com) into the user's own `~/bin`, which needs no
elevation. `minicloud init-terraform` documents this same fallback for
end users who hit the same no-admin situation.

## 2026-10-09 — Real Docker verification (follow-up session, WSL Ubuntu 24.04)
The caveat above — that only stub-mode had ever been exercised — turned
out to matter: running the exact same code against a real Docker daemon
(WSL2, not this sandbox) immediately surfaced three bugs that stub mode's
fake-id short-circuit had been silently masking:

1. `_decode_user_data` called `base64.b64decode()` on moto's
   `Base64EncodedString` user_data object (not a plain `str`); the decode
   silently raised, was swallowed by a bare `except Exception: return
   user_data`, and the un-decoded object reached
   `docker_manager.run_instance_container`'s `.replace()` call, crashing
   *every* reconciliation pass before any container was ever created.
2. That crash was fatal to the whole pass (`reconcile_once` had no
   per-resource isolation), so one broken instance or VPC blocked
   reconciliation of everything else, every single poll.
3. moto's default VPC CIDR (`172.31.0.0/16`) collided with Docker's own
   address pools on this machine, making `ensure_network` fail outright
   with no fallback.
4. Once containers did get created, `user_data`'s trailing newline (from
   Terraform's heredoc syntax, which is the norm) plus the literal
   `" ; sleep infinity"` suffix put a bare `;` on its own line — a syntax
   error under POSIX `sh` (dash) — so every container exited immediately
   instead of staying up.

All four fixed (see the "Fix 3 real Docker-path bugs..." commit —
counted as 3 fixes since #1 and #2 were one conceptual gap: no error
isolation anywhere in the reconcile loop). Re-verified afterward: real
`terraform init -> apply -> destroy` against a live Docker daemon for
all three examples, confirming via `docker ps`/`docker logs` (not just
Terraform's own success output) that containers actually run,
`user_data` actually executes inside them, security-group ingress rules
actually become published Docker ports, and `destroy` actually removes
the containers. The lesson generalizes: stub mode is good for keeping
the server alive without Docker, but it is not a substitute for running
the real path at least once before calling a Docker-backed feature done.
