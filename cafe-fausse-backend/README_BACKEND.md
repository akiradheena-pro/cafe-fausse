# Café Fausse — Backend (Flask + PostgreSQL)

Flask API for reservations, newsletter signups, and a basic admin listing view. Runs locally via Docker Compose with a one-command bootstrap, and includes a black-box test suite that hits the live server.

---

## What changed (and why)

- **Self-healing startup**: `start.sh` now bootstraps the schema if missing, installs deps for Alembic in a one-off container, runs migrations, then waits on health. This prevents “fresh DB” and dependency drift errors.
- **Time handling**: store **UTC-naive** `time_slot` in Postgres; return ISO8601 with `Z` in API responses. Avoids tz/type errors and keeps the contract predictable.
- **Newsletter stability**: atomic Postgres **UPSERT** on `email` with structured errors; only update `name/phone` if provided non-empty.
- **Admin auth**: Bearer token checked via a resilient lookup (env → `.env` → `.env.example` → `dev-admin-token`).
- **Tests**: pytest suite for health/newsletter/availability/create/admin-list; tests read the token from `.env`.

---

## Quick start

```bash
# 1) Ensure Docker Desktop is running
# 2) From backend root:
chmod +x start.sh
./start.sh
````

This will:

* ensure `.env` exists (copy from `.env.example` if missing),
* start Postgres and wait until ready,
* **bootstrap schema** (idempotent) and run Alembic migrations,
* start the API and wait for `/health` → `{"status":"ok"}`.

---

## Configuration

Environment variables (see `.env.example`):

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/cafe_fausse
PORT=8000
SLOT_MINUTES=30
ADMIN_TOKEN=dev-admin-token
```

**Admin token resolution order (server-side):**

1. `ADMIN_TOKEN` from process env
2. `.env` in backend root
3. `.env.example` in backend root
4. default to `dev-admin-token`

Rebuild/refresh API after changing env:

```bash
docker compose up -d --build api
```

---

## Data model

* **customers**: `id, name, email (unique), phone, newsletter_opt_in, created_at`
* **reservations**: `id, customer_id (fk), time_slot (UTC-naive), table_number, created_at`
* **uniqueness**: `(time_slot, table_number)` prevents double-booking

---

## API reference

Base URL: `http://localhost:8000`

### Health

`GET /health` → `200`

```json
{"status":"ok"}
```

### Reservations — availability

`GET /api/reservations/availability?time=ISO8601` → `200`

* Rounds input to `SLOT_MINUTES`.
* Returns `{ totalTables, booked, available, slot }` (`slot` is ISO `Z`).
* Errors: `400 MISSING_TIME`, `422 BAD_TIME`.

### Reservations — create

`POST /api/reservations` → `201`

Request:

```json
{
  "time": "2025-09-10T19:00:00Z",
  "guests": 2,
  "name": "Alex",
  "email": "alex@example.com",
  "phone": "optional"
}
```

Response:

```json
{
  "reservationId": 42,
  "tableNumber": 7,
  "slot": "2025-09-10T19:00:00Z"
}
```

Errors:
`400 MISSING_FIELDS`, `422 BAD_TIME`, `422 BAD_GUESTS`,
`409 FULLY_BOOKED` / `409 RACE_LOST`, `429 RATE_LIMITED` (dev-only)

### Reservations — admin list (Bearer auth)

`GET /api/reservations?date=YYYY-MM-DD&page=1&page_size=20` → `200`

Header: `Authorization: Bearer <ADMIN_TOKEN>`

Response:

```json
{
  "page": 1,
  "pageSize": 10,
  "total": 3,
  "reservations": [
    {
      "id": 42,
      "time": "2025-09-10T19:00:00Z",
      "tableNumber": 7,
      "customer": {
        "id": 1, "name": "Alex", "email": "alex@example.com", "phone": ""
      }
    }
  ]
}
```

Errors: `401 UNAUTHORIZED`, `400 MISSING_DATE`, `422 BAD_DATE`.

### Newsletter — subscribe

`POST /api/newsletter` → `200`

Request:

```json
{"email":"alex@example.com","name":"Alex","phone":"optional"}
```

Success:

```json
{"message":"Email added to newsletter","customerId":1}
```

Errors:

* `422 BAD_EMAIL` for invalid email
* Atomic UPSERT on `email`: if existing, sets `newsletter_opt_in=true` and updates `name/phone` only when provided non-empty

---

## Quick manual tests

```bash
BASE="http://localhost:8000"
TOKEN="${ADMIN_TOKEN:-dev-admin-token}"
DAY="$(date -u +%F)"
SLOT="$(date -u -Iseconds | cut -c1-19)Z"

curl -sS ${BASE}/health | jq .
curl -sS "${BASE}/api/reservations/availability?time=${SLOT}" | jq .
curl -sS -X POST "${BASE}/api/newsletter" -H "content-type: application/json" \
  -d '{"email":"alex+'$(date +%s)'@example.com","name":"Alex"}' | jq .
curl -sS -X POST "${BASE}/api/reservations" -H "content-type: application/json" \
  -d "{\"time\":\"${SLOT}\",\"guests\":2,\"name\":\"Alex\",\"email\":\"alex+$(date +%s)@example.com\"}" | jq .
curl -sS "${BASE}/api/reservations?date=${DAY}&page=1&page_size=10" \
  -H "Authorization: Bearer ${TOKEN}" | jq .
```

---

## Test suite (black-box)

Install dev deps and run:

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

Notes:

* Tests read `ADMIN_TOKEN` from environment; if unset, they load `.env` to stay in sync with the API.

---

## Scripts & commands

```bash
./start.sh                              # start / rebuild / migrate / health
docker compose exec api alembic upgrade head
docker compose exec db psql -U postgres -d cafe_fausse
```

---

## Development tips

* **DB enforces double-booking** via unique `(time_slot, table_number)`; your code races safely: one insert wins, the other gets `409`.
* **Slot rounding** ensures “same time” aligns to the same bucket.
* **Structured errors** (`code` + `message`) make front-end handling deterministic.
* The dev **rate limiter** is intentionally simple; use a real limiter in production.

---

## Roadmap & status (checklist)

### Week 1 — Foundations

* [x] App factory, models, migrations
* [x] Docker Compose for Postgres + API
* [x] Health, availability, create reservation
* [x] Newsletter basic endpoint
* [x] `start.sh` bootstrap
* [ ] Seed script
* [ ] Basic unit tests

### Week 2 — Backend polish (current)

* [x] Slot rounding (configurable)
* [x] Consistent JSON error shape
* [x] Admin list with pagination
* [x] Dev-only rate limit on create
* [x] Newsletter structured errors (`422 BAD_EMAIL`)
* [x] Newsletter atomic UPSERT (no duplicate/race 500s)
* [x] Datetime handling: UTC-naive in DB, ISO `Z` in API
* [x] Robust migrations & schema bootstrap via `start.sh`
* [x] E2E tests (pytest) + token sync via dotenv
* [ ] Admin filters (email/table/slot)
* [ ] Unit & integration tests for error branches

### Week 3 — Frontend & UX

* [ ] Wire forms to API with clear success/error UI
* [ ] Responsive layout & a11y
* [ ] Content pages (Menu/About/Gallery)

### Week 4 — Hardening

* [ ] Observability & logs
* [ ] Backups/restore
* [ ] Production-grade rate limiting
* [ ] Security headers/CORS tightening

### Week 5–6 — Delivery

* [ ] CI pipeline (build → start.sh → pytest)
* [ ] Deploy (Gunicorn + reverse proxy / managed)
* [ ] Ops runbook & UAT checklist
