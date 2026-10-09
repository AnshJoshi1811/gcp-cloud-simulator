FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY minicloud ./minicloud

RUN pip install --no-cache-dir -e .

EXPOSE 4566

ENV MINICLOUD_DB_PATH=/data/minicloud.db
VOLUME ["/data"]

# Needs access to the host's Docker daemon to actually manage containers;
# run with -v /var/run/docker.sock:/var/run/docker.sock (see docker-compose.yml).
CMD ["python", "-m", "minicloud.server"]
