# MiniCloud

A local AWS emulator for learning Terraform (and later Kubernetes) without a real
AWS account. The official Terraform `aws` provider works against it unmodified —
just override the service endpoints and use fake credentials. `terraform apply`
creates real Docker containers for EC2 instances; `terraform destroy` removes them.

Supported today: **EC2** (instances, VPCs, subnets, security groups), **S3**
(buckets + objects), **IAM**, **DynamoDB**, **SQS** (basic/standard operations).

## How it works

MiniCloud runs [`moto`](https://github.com/getmoto/moto)'s AWS mock server on
`:4566` — this is what gives byte-exact wire-protocol compatibility with the
real Terraform AWS provider (see [DECISIONS.md](DECISIONS.md) for why this was
the right call rather than hand-rolling AWS's XML/JSON wire formats). On top of
that, a background **reconciler** thread is MiniCloud's actual contribution:
it polls moto's in-memory EC2 state every 2 seconds and makes Docker reality
match it —

- a new `running` EC2 instance gets a real Docker container (image chosen from
  its AMI id — see the mapping table below), with its security groups' TCP
  ingress rules translated into published ports, and its `user_data` executed
  on container start
- a `stopped` instance's container is stopped; a `terminated` instance's
  container is removed
- each VPC gets its own Docker network, and instances in that VPC join it

This reconcile-from-source-of-truth loop is also exactly what makes MiniCloud
resilient to restarts: the first pass after `minicloud start` is the same diff
as every other pass, so Docker reality catches up to whatever AWS-API state
exists (restored from `minicloud.db`) automatically.

## Quickstart

```bash
pip install -e .
minicloud start --background
minicloud init-terraform --dir examples/ec2-instance
cd examples/ec2-instance
terraform init
terraform apply
minicloud status          # see the container MiniCloud created for it
terraform destroy
minicloud stop
```

## Supported services

| Service | What works | Backing |
|---|---|---|
| EC2 | RunInstances, Describe/Stop/Start/TerminateInstances, tags, DescribeImages/InstanceTypes/Vpcs/Subnets/SecurityGroups/Volumes/Tags, CreateTags | Real Docker containers (reconciler) |
| VPC / Subnet / Security Group | Create/describe; SG ingress → published ports | Real Docker networks (reconciler) |
| S3 | Buckets + objects, path-style addressing | moto's local-folder-backed store |
| IAM | Users, roles, policies (moto's standard mock) | In-memory |
| DynamoDB | Tables, items, queries (moto's standard mock) | In-memory |
| SQS | Queues, send/receive/delete message (moto's standard mock) | In-memory |

### AMI → Docker image mapping

| AMI id contains | Image |
|---|---|
| `ubuntu` | `ubuntu:22.04` |
| `alpine` | `alpine:3.19` |
| `nginx` | `nginx:alpine` |
| anything else | `alpine:3.19` (default) |

## CLI

```
minicloud start [--background] [--port 4566]   # run the API server
minicloud stop                                  # stop a background server
minicloud status                                # list managed resources + containers
minicloud destroy-all [--force]  (alias: reset) # remove ALL managed containers/networks
minicloud logs <resource-id>                    # show a container's logs
minicloud init-terraform [--dir DIR]             # write a ready-to-use provider.tf
```

`destroy-all` reads straight from Docker's own `minicloud=true` labels, so it
works even if `minicloud.db` or your Terraform state is lost.

## Using it with Terraform

Point the AWS provider at MiniCloud and use throwaway credentials:

```hcl
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  endpoints {
    ec2 = "http://localhost:4566"
    s3  = "http://localhost:4566"
  }
}
```

`minicloud init-terraform` generates exactly this. See `examples/` for three
complete, runnable configs (single EC2 instance; EC2 + VPC + security group;
S3 bucket + object) — each has been run through a real
`init → plan → apply → destroy` cycle with `terraform` itself (not just unit
tests) as part of building this project; see `tests/test_terraform_examples.sh`
to re-run that cycle yourself.

## Using it with Kubernetes (future work)

Not implemented yet — EC2 containers are plain Docker containers today, not
pods. A natural next step is a minimal EKS-shaped API in front of a local k3d/
kind cluster, following the same reconciler pattern used for EC2.

## Running MiniCloud itself in Docker

```bash
docker compose up -d
```

This mounts the **host's** Docker socket into the MiniCloud container (see
`docker-compose.yml`) so containers it creates for your EC2 instances are
visible to `docker ps` on your own machine, not nested inside MiniCloud's
container.

## Development

```bash
make install        # pip install -e .
make test           # unit tests (tests/test_api.py)
make test-terraform # full terraform init/plan/apply/destroy cycle for every example
make run-background
make status
make clean
```

## Known limitations

- Docker must be installed and running for containers/networks to actually be
  created; without it, MiniCloud still runs and the AWS API / Terraform cycle
  still works, but falls back to recording stub ids (see DECISIONS.md) — this
  is the situation on the machine this project was built on, so the stub path
  is exercised just as much as the real one.
- EC2 `user_data` is executed as a shell script inside the container at start
  (not full cloud-init — no package manager bootstrapping, SSH key injection,
  etc.).
- Security-group-to-port mapping only handles single-protocol TCP ingress
  rules explicitly (not security-group-to-security-group references).
- IAM/DynamoDB/SQS are moto's standard mocks as-is, not Docker-backed —
  intentional, see DECISIONS.md.
