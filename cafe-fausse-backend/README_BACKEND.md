
# Café Fausse — Backend (Flask + PostgreSQL)

This repo is the Week 1 backend scaffold. It includes:
- Flask app with blueprints
- SQLAlchemy models for `customers` and `reservations`
- Alembic migrations with a unique constraint on `(time_slot, table_number)`
- Docker Compose for Postgres and the API
- `.env.example` for configuration

## Quick start

```bash
# 1) Copy env
cp .env.example .env

# 2) Start Postgres + API
docker compose up --build

# 3) Apply migrations
docker compose exec api alembic upgrade head

# 4) (Optional) Run a basic smoke test
curl http://localhost:8000/health
```

## Useful commands

```bash
# Create a new migration after changing models
docker compose exec api alembic revision -m "your change" --autogenerate

# Upgrade/downgrade
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1

# Open a psql shell
docker compose exec db psql -U postgres -d cafe_fausse
```
