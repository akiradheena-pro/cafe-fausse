#!/usr/bin/env bash
set -euo pipefail

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

export PORT=${PORT:-8000}

docker compose up -d db

echo "Waiting for DB..."
for i in {1..60}; do
  if docker compose exec -T db pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-cafe_fausse}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Applying DB migrations (one-off container)..."
docker compose run --rm api alembic upgrade head

echo "Starting API..."
docker compose up -d api

echo "Waiting for API health on http://localhost:${PORT}/health ..."
for i in {1..60}; do
  if curl -fsS "http://localhost:${PORT}/health" >/dev/null; then
    echo "API is healthy."
    echo "Ready:"
    echo "  Health:       http://localhost:${PORT}/health"
    echo "  Availability: http://localhost:${PORT}/api/reservations/availability?time=2025-09-10T19:00:00Z"
    exit 0
  fi
  sleep 1
done

echo "API did not become healthy in time."
docker compose logs api
exit 1
