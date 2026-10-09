# GCP Stimulator Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2 (PostgreSQL) if DATABASE_URL points at Postgres
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .

EXPOSE 8080

# NOTE: the emulator manages Docker containers/networks on your behalf
# (Compute instances, VPC networks, Cloud SQL/Memorystore, the Cloud
# Storage fake-gcs-server backend, etc). For that to work when the backend
# itself runs in a container, mount the host's Docker socket:
#   -v /var/run/docker.sock:/var/run/docker.sock
# (already wired up in the repo root docker-compose.yml). Without it, the
# backend degrades gracefully to stub mode rather than failing to start.

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
