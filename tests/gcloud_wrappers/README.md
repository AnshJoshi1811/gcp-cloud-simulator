# gcloud CLI Wrappers

These files contain Python wrappers for gcloud CLI commands, used for testing gcloud compatibility with our GCS Emulator.

## Purpose

The wrappers validate that gcloud commands work correctly against the emulated GCP services.

## Wrappers

- `compute.py` - gcloud compute commands (instances, disks, networks, etc.)
- `storage.py` - gcloud storage commands (buckets, objects, transfers)
- `vpc.py` - gcloud compute networks commands (VPCs, subnets, routes, firewalls)
- `iam.py` - gcloud iam commands (service accounts, roles, policies)
- `monitoring.py` - gcloud monitoring commands (metrics, dashboards, alerts)

## Usage

```python
from tests.gcloud_wrappers.compute import create_instance

result = create_instance(project="my-project", zone="us-central1-a", name="my-vm")
```

## Compatibility

See `CLAUDE.md` at the repo root (Service Status table) for current gcloud/service coverage and known limitations.
