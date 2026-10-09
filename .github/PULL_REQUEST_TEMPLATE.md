## What does this change?

<!-- One or two sentences. -->

## Why?

<!-- The motivation — a bug, a missing feature, a fidelity gap vs real GCP. -->

## How was this verified?

<!-- For most changes: which tests you ran (`pytest tests/integration`, manual
gcloud/UI check). For anything touching real-provider (Terraform)
compatibility: paste the actual `init -> apply -> destroy` output, plus how
you independently verified the result (direct API call, `docker ps`, etc.) —
see CONTRIBUTING.md's verification bar. -->

## Checklist

- [ ] Tests pass locally (`python -m pytest tests/integration`)
- [ ] `CLAUDE.md`'s Service Status table / `README.md` updated if service status changed
- [ ] Non-obvious decisions recorded in `CLAUDE.md`'s Engineering Decisions Log
