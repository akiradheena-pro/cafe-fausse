set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

copy_env_if_missing() {
  if [[ ! -f "${ROOT_DIR}/.env" && -f "${ROOT_DIR}/.env.example" ]]; then
    cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
    echo "Created .env from .env.example"
  fi
}

wait_for_db() {
  echo "Waiting for DB..."
  docker compose up -d db >/dev/null
  for i in {1..60}; do
    if docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
      echo "DB is ready."
      return 0
    fi
    sleep 1
  done
  echo "Postgres did not become ready in time." >&2
  exit 1
}


apply_migrations() {
  echo "Applying DB migrations (one-off container)..."
  docker compose run --rm --build api alembic upgrade head
}

start_api() {
  echo "Starting API..."
  docker compose up -d api >/dev/null

  local health_url="http://localhost:8000/health"
  echo "Waiting for API health on ${health_url} ..."
  for i in {1..60}; do
    if curl -sSf "${health_url}" >/dev/null 2>&1; then
      echo "API is healthy."
      echo "Ready:"
      echo "  Health:       ${health_url}"
      echo "  Availability: http://localhost:8000/api/reservations/availability?time=2025-09-10T19:00:00Z"
      return 0
    fi
    sleep 1
  done

  echo "API did not report healthy in time." >&2
  exit 1
}

main() {
  cd "${ROOT_DIR}"
  copy_env_if_missing

  docker compose build api >/dev/null

  wait_for_db
  apply_migrations
  start_api
}

main "$@"