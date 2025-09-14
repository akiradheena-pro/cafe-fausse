from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from ..extensions import db
from ..models import Reservation, Customer
from ..http import jerror

bp = Blueprint("reservations", __name__)
TOTAL_TABLES = 30

# --- Dev-only rate limiter (very simple) ---
_rate_state: dict[str, tuple[int, int]] = {}
_RATE_WINDOW = 60
_RATE_MAX = 12

def _allow(ip: str) -> bool:
    now = int(datetime.now(tz=timezone.utc).timestamp())
    window = now // _RATE_WINDOW
    count, win = _rate_state.get(ip, (0, window))
    if win != window:
        count, win = 0, window
    count += 1
    _rate_state[ip] = (count, win)
    return count <= _RATE_MAX

# --- Time parsing + slot rounding ---
def _parse_iso(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)

def _round_to_slot(dt: datetime, minutes: int) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    slot = minutes
    total = dt.hour * 60 + dt.minute
    floored = (total // slot) * slot
    return dt.replace(hour=floored // 60, minute=floored % 60, second=0, microsecond=0)

def _client_ip() -> str:
    fwd = request.headers.get("X-Forwarded-For")
    return (fwd.split(",")[0].strip() if fwd else request.remote_addr or "0.0.0.0")

# --- Endpoints ---

@bp.get("/availability")
def availability():
    t = request.args.get("time") or request.args.get("time_slot")
    if not t:
        return jerror(400, "MISSING_TIME", "Missing 'time' query parameter.")
    try:
        ts = _parse_iso(t)
    except Exception as e:
        return jerror(422, "BAD_TIME", "Invalid time format, expected ISO 8601.", str(e))
    slot_minutes = int(current_app.config.get("SLOT_MINUTES", 30))
    ts = _round_to_slot(ts, slot_minutes)

    booked = db.session.execute(
        select(func.count()).select_from(Reservation).where(Reservation.time_slot == ts)
    ).scalar_one()
    return jsonify(totalTables=TOTAL_TABLES, booked=int(booked), available=TOTAL_TABLES - int(booked), slot=ts.isoformat())

@bp.post("")
def create_reservation():
    ip = _client_ip()
    if not _allow(ip):
        return jerror(429, "RATE_LIMITED", "Too many requests. Try again shortly.")

    payload = request.get_json(silent=True) or {}
    required = ["time", "guests", "name", "email"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jerror(400, "MISSING_FIELDS", f"Missing fields: {', '.join(missing)}")

    try:
        ts = _parse_iso(payload["time"])
    except Exception as e:
        return jerror(422, "BAD_TIME", "Invalid time format, expected ISO 8601.", str(e))
    slot_minutes = int(current_app.config.get("SLOT_MINUTES", 30))
    ts = _round_to_slot(ts, slot_minutes)

    try:
        guests = int(payload["guests"])
        if guests < 1:
            return jerror(422, "BAD_GUESTS", "guests must be >= 1.")
    except Exception:
        return jerror(422, "BAD_GUESTS", "guests must be an integer >= 1.")

    name = str(payload["name"]).strip()
    email = str(payload["email"]).strip().lower()
    phone = str(payload.get("phone") or "").strip()

    customer = Customer.query.filter_by(email=email).one_or_none()
    if not customer:
        customer = Customer(name=name, email=email, phone=phone)
        db.session.add(customer)
        db.session.flush()

    booked = {t for (t,) in db.session.execute(
        select(Reservation.table_number).where(Reservation.time_slot == ts)
    ).all()}
    remaining = [t for t in range(1, TOTAL_TABLES + 1) if t not in booked]
    if not remaining:
        return jerror(409, "FULLY_BOOKED", "Time slot fully booked.")

    import random
    table = random.choice(remaining)
    res = Reservation(customer_id=customer.id, time_slot=ts, table_number=table)
    db.session.add(res)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jerror(409, "RACE_LOST", "Just booked out. Pick another time.")

    return jsonify(reservationId=res.id, tableNumber=table, slot=ts.isoformat()), 201

@bp.get("")
def list_reservations():
    """
    Admin list for a single day with pagination.
    Query: ?date=YYYY-MM-DD&page=1&page_size=20
    """
    date_str = request.args.get("date")
    if not date_str:
        return jerror(400, "MISSING_DATE", "Missing 'date' query parameter (YYYY-MM-DD).")
    try:
        day = datetime.fromisoformat(date_str).date()
    except Exception as e:
        return jerror(422, "BAD_DATE", "Invalid date format. Use YYYY-MM-DD.", str(e))

    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)

    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    q = (
        db.session.query(Reservation, Customer)
        .join(Customer, Reservation.customer_id == Customer.id)
        .filter(Reservation.time_slot >= start, Reservation.time_slot < end)
        .order_by(Reservation.time_slot.asc(), Reservation.table_number.asc())
    )

    total = q.count()
    rows = q.limit(page_size).offset((page - 1) * page_size).all()

    data = []
    for reservation, customer in rows:
        data.append({
            "id": reservation.id,
            "time": reservation.time_slot.isoformat(),
            "tableNumber": reservation.table_number,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
            },
        })


    return jsonify(page=page, pageSize=page_size, total=total, reservations=data)
