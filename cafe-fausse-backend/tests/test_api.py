import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

try:
    from dotenv import dotenv_values
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_path = os.path.abspath(env_path)
    if os.path.exists(env_path):
        _env = dotenv_values(env_path)
    else:
        _env = {}
except Exception:
    _env = {}

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", _env.get("ADMIN_TOKEN", "dev-admin-token"))


def _iso_utc_in_future(minutes: int = 120) -> str:
    dt = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def test_health_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_newsletter_invalid_email_422():
    r = requests.post(
        f"{BASE_URL}/api/newsletter",
        json={"email": "not-an-email"},
        timeout=10,
    )
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "BAD_EMAIL"


def test_newsletter_subscribe_200_returns_customer_id():
    email = _unique_email("newsletter")
    r = requests.post(
        f"{BASE_URL}/api/newsletter",
        json={"email": email, "name": "Tester"},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert "customerId" in body and isinstance(body["customerId"], int)


def test_availability_returns_counts_and_slot():
    slot = _iso_utc_in_future(180)
    r = requests.get(
        f"{BASE_URL}/api/reservations/availability",
        params={"time": slot},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    for key in ("totalTables", "booked", "available", "slot"):
        assert key in body
    assert isinstance(body["totalTables"], int)
    assert isinstance(body["booked"], int)
    assert isinstance(body["available"], int)
    assert isinstance(body["slot"], str)


def test_create_reservation_201_returns_payload():
    slot = _iso_utc_in_future(240)
    email = _unique_email("reserve")
    payload = {
        "time": slot,
        "guests": 2,
        "name": "Integration Tester",
        "email": email,
    }
    r = requests.post(
        f"{BASE_URL}/api/reservations",
        json=payload,
        timeout=15,
    )
    assert r.status_code == 201
    body = r.json()
    assert "reservationId" in body and isinstance(body["reservationId"], int)
    assert "tableNumber" in body and isinstance(body["tableNumber"], int)
    assert "slot" in body and isinstance(body["slot"], str)


def test_admin_list_requires_bearer_token_401():
    day = datetime.now(timezone.utc).date().isoformat()
    r = requests.get(
        f"{BASE_URL}/api/reservations",
        params={"date": day, "page": 1, "page_size": 1},
        timeout=10,
    )
    assert r.status_code == 401
    body = r.json()
    assert body.get("code") == "UNAUTHORIZED"


def test_admin_list_with_token_200_and_contains_new_reservation():
    slot = _iso_utc_in_future(300)
    email = _unique_email("adminlist")
    create = requests.post(
        f"{BASE_URL}/api/reservations",
        json={"time": slot, "guests": 3, "name": "Admin Lister", "email": email},
        timeout=15,
    )
    assert create.status_code == 201
    created_slot = create.json()["slot"]
    day = created_slot.split("T", 1)[0]

    r = requests.get(
        f"{BASE_URL}/api/reservations",
        params={"date": day, "page": 1, "page_size": 100},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    assert "reservations" in data and isinstance(data["reservations"], list)

    # Verify at least one entry matches the email we just booked
    emails = [row["customer"]["email"] for row in data["reservations"]]
    assert email in emails
