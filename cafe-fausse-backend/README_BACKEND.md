# Café Fausse — Backend (Flask + PostgreSQL)

Backend service for reservations, newsletter signups, and admin listing. This README shows how to run it quickly and tracks progress with a task checklist.

---

## Quick start

```bash
# 1) Ensure Docker is running
# 2) From the repo root:
chmod +x start.sh
./start.sh
````

That will:

* copy `.env.example` → `.env` if missing,
* build and start Postgres + API,
* apply Alembic migrations,
* wait for `/health` to return `{"status":"ok"}`.

### Useful checks

```bash
# Health
curl http://localhost:8000/health

# Availability (note the normalized 'slot' in the response)
curl "http://localhost:8000/api/reservations/availability?time=2025-09-10T19:12:00Z"

# Create a reservation
curl -X POST http://localhost:8000/api/reservations \
  -H "content-type: application/json" \
  -d '{"time":"2025-09-10T19:00:00Z","guests":2,"name":"Alex","email":"alex@example.com"}'

# Admin list for a day (dev/QA; unauthenticated now)
curl "http://localhost:8000/api/reservations?date=2025-09-10&page=1&page_size=10"
```

---

## Configuration

Environment variables (see `.env.example`):

* `DATABASE_URL` — `postgresql+psycopg2://postgres:postgres@db:5432/cafe_fausse`
* `PORT` — default `8000`
* `SLOT_MINUTES` — rounding bucket for reservations (default `30`)

```ini
# .env.example excerpt
PORT=8000
SLOT_MINUTES=30
```

---

## Data model (ORM)

* **customers**: `id, name, email(unique), phone, newsletter_opt_in, created_at`
* **reservations**: `id, customer_id(fk), time_slot(tz), table_number, created_at`
* **Uniqueness**: `(time_slot, table_number)` — prevents double-booking the same table at the same time.

---

## API summary

* `GET /health` → `{"status":"ok"}`
* `GET /api/reservations/availability?time=ISO8601`

  * Returns `{ totalTables, booked, available, slot }`
  * `slot` is the **rounded** time (e.g., 30-minute bucket).
* `POST /api/reservations`

  * Body: `{ time, guests, name, email, phone? }`
  * Responses:

    * `201` `{ reservationId, tableNumber, slot }`
    * `409` `{ code:"FULLY_BOOKED" | "RACE_LOST", ... }`
    * `422` with `code:"BAD_TIME" | "BAD_GUESTS"` etc.
    * `429` `{ code:"RATE_LIMITED" }` (dev-only limiter)
* `GET /api/reservations?date=YYYY-MM-DD&page=&page_size=`

  * Admin list for a single day (dev/QA); **auth TBD**.
* `POST /api/newsletter`

  * Body: `{ email, name?, phone? }`
  * Returns `{ success: true }` (will be upgraded to structured errors later).

---

## Roadmap & status (checklist)

### Week 1 — Foundations

* [x] Repo structure and Flask app factory
* [x] Docker Compose for Postgres + API
* [x] SQLAlchemy models: `customers`, `reservations`
* [x] Alembic migration: tables + unique `(time_slot, table_number)`
* [x] `/health` endpoint
* [x] `GET /api/reservations/availability`
* [x] `POST /api/reservations` (random table assignment, DB-protected against double-booking)
* [x] `POST /api/newsletter` (basic)
* [x] `start.sh` bootstrap script
* [ ] Basic test suite (smoke, race-condition test)
* [ ] Seed script to populate sample data (optional)

### Week 2 — Backend polish (current)

* [x] Slot rounding (configurable via `SLOT_MINUTES`)
* [x] Structured JSON errors (reservations)
* [x] Admin list endpoint for a day with pagination
* [x] Dev-only rate limit for `POST /api/reservations`
* [ ] Apply structured errors to **newsletter**
* [ ] Add admin authentication/authorization
* [ ] Extend admin filters (by email/table/slot)
* [ ] Unit/integration tests for new behaviors
* [ ] E2E tests (Playwright/Cypress)

### Week 3 — Frontend & UX

* [ ] Hook forms to API with clear success/error UI
* [ ] Responsive layout and accessibility pass
* [ ] Menu/About/Gallery content
* [ ] Perf budgets (lazy-loading, image optimization)

### Week 4 — Hardening

* [ ] Observability (structured logs, error tracking)
* [ ] Backups/restore for Postgres
* [ ] Rate limiting with Redis/NGINX/Flask-Limiter (prod-ready)
* [ ] Security headers/CORS tightening

### Week 5–6 — Delivery

* [ ] CI pipeline (lint, test, build)
* [ ] Deploy (Gunicorn + reverse proxy or managed platform)
* [ ] Ops runbook and final README polish
* [ ] UAT checklist mapped to requirements

---

## Development tips

* The **database** enforces correctness for double-bookings via a unique constraint. Even under concurrency, one insert wins, the other gets a 409 response.
* **Slot rounding** guarantees “same time” means the same bucket, preventing “19:12 vs 19:28” drift in availability math.
* **Structured errors** (`code` + `message`) make front-end handling predictable.
* The dev-only **rate limiter** is intentionally simple; don’t rely on it in production.

---

## Scripts & commands

```bash
# Start / rebuild / migrate / health
./start.sh

# Apply migrations manually
docker compose exec api alembic upgrade head

# psql shell
docker compose exec db psql -U postgres -d cafe_fausse
```

---

## What’s next (recommended order)

1. Migrate **newsletter** to structured JSON errors (use `api/http.py`).
2. Add **admin auth** (simple bearer token or JWT) for `GET /api/reservations`.
3. Add tests:

   * error shapes for reservations,
   * slot rounding behavior,
   * admin listing pagination & bounds.
4. Replace dev rate limiter with a **prod-ready** limiter (Redis or edge proxy).
5. Prepare **Gunicorn** entrypoint and deployment recipe.