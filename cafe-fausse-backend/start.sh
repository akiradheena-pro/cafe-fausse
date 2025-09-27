#!/usr/bin/env bash
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

bootstrap_schema() {
  echo "Bootstrapping schema (idempotent)..."
  # Pipe SQL from host into the DB container; uses container env POSTGRES_USER/POSTGRES_DB
  docker compose exec -T db sh -lc 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
-- customers table
CREATE TABLE IF NOT EXISTS customers (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL DEFAULT 'Subscriber',
  email TEXT NOT NULL,
  phone TEXT NOT NULL DEFAULT '',
  newsletter_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
-- unique email
CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_email ON customers(email);

-- reservations table
CREATE TABLE IF NOT EXISTS reservations (
  id BIGSERIAL PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  time_slot TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  table_number INTEGER NOT NULL,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- FK to customers (add if missing)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'reservations_customer_id_fkey'
      AND table_name = 'reservations'
  ) THEN
    ALTER TABLE reservations
      ADD CONSTRAINT reservations_customer_id_fkey
      FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE;
  END IF;
END$$;

-- unique per time slot/table
CREATE UNIQUE INDEX IF NOT EXISTS uq_reservations_time_table
  ON reservations(time_slot, table_number);

-- useful index for lookups
CREATE INDEX IF NOT EXISTS ix_reservations_time_slot
  ON reservations(time_slot);
SQL
}

apply_migrations() {
  echo "Applying DB migrations (one-off container)..."
  docker compose run --rm api bash -lc '
    set -e
    if [[ -f requirements.txt ]]; then
      python -m pip install -q --disable-pip-version-check -r requirements.txt
    elif [[ -f requerments.txt ]]; then
      python -m pip install -q --disable-pip-version-check -r requerments.txt
    fi
    python -c "import flask_migrate" >/dev/null 2>&1 || { echo "Flask-Migrate still missing"; exit 1; }
    alembic upgrade head
  '
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

  # Optional but recommended: ensure the image reflects current deps
  docker compose build api >/dev/null

  wait_for_db
  apply_migrations
  start_api
}

main "$@"
