from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from ..extensions import db
from ..models import Reservation, Customer
from ..http import jerror
from ..auth import check_admin
from ..utils.time import parse_iso, round_to_slot, db_utc_naive, api_iso_z  # <-- Import from utils

bp = Blueprint("reservations", __name__)

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

# --- Time parsing functions REMOVED from here ---

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
        ts = parse_iso(t)
    except Exception as e:
        return jerror(422, "BAD_TIME", "Invalid time format, expected ISO 8601.", str(e))
    
    slot_minutes = current_app.config["SLOT_MINUTES"]
    ts_rounded = round_to_slot(ts, slot_minutes)
    ts_db = db_utc_naive(ts_rounded)

    booked = db.session.execute(
        select(func.count()).select_from(Reservation).where(Reservation.time_slot == ts_db)
    ).scalar_one()
    
    total_tables = current_app.config["TOTAL_TABLES"]
    
    return jsonify(
        totalTables=total_tables,
        booked=int(booked),
        available=total_tables - int(booked),
        slot=api_iso_z(ts_rounded),
    )

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
        ts = parse_iso(payload["time"])
    except Exception as e:
        return jerror(422, "BAD_TIME", "Invalid time format, expected ISO 8601.", str(e))
    
    slot_minutes = current_app.config["SLOT_MINUTES"]
    ts_rounded = round_to_slot(ts, slot_minutes)
    ts_db = db_utc_naive(ts_rounded)

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

    # --- New, efficient query to find an available table ---
    total_tables = current_app.config["TOTAL_TABLES"]
    find_table_query = text("""
        SELECT s.num
        FROM generate_series(1, :total_tables) AS s(num)
        WHERE NOT EXISTS (
            SELECT 1 FROM reservations r
            WHERE r.time_slot = :time_slot AND r.table_number = s.num
        )
        ORDER BY random()
        LIMIT 1
    """)
    
    available_table = db.session.execute(
        find_table_query,
        {"total_tables": total_tables, "time_slot": ts_db}
    ).scalar_one_or_none()

    if available_table is None:
        return jerror(409, "FULLY_BOOKED", "Time slot fully booked.")

    res = Reservation(customer_id=customer.id, time_slot=ts_db, table_number=available_table)
    db.session.add(res)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jerror(409, "RACE_LOST", "Just booked out. Pick another time.")

    return jsonify(reservationId=res.id, tableNumber=available_table, slot=api_iso_z(ts_rounded)), 201

# ... (list_reservations endpoint remains the same)
@bp.get("")
def list_reservations():
    """
    Admin list for a single day with pagination.
    Query: ?date=YYYY-MM-DD&page=1&page_size=20
    """
    if not check_admin():
        return jerror(401, "UNAUTHORIZED", "Missing or invalid bearer token.")
    date_str = request.args.get("date")
    if not date_str:
        return jerror(400, "MISSING_DATE", "Missing 'date' query parameter (YYYY-MM-DD).")
    try:
        day = datetime.fromisoformat(date_str).date()
    except Exception as e:
        return jerror(422, "BAD_DATE", "Invalid date format. Use YYYY-MM-DD.", str(e))

    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)

    start_utc = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end_utc = start_utc + timedelta(days=1)
    start_db = start_utc.replace(tzinfo=None)
    end_db = end_utc.replace(tzinfo=None)

    q = (
        db.session.query(Reservation, Customer)
        .join(Customer, Reservation.customer_id == Customer.id)
        .filter(Reservation.time_slot >= start_db, Reservation.time_slot < end_db)
        .order_by(Reservation.time_slot.asc(), Reservation.table_number.asc())
    )

    total = q.count()
    rows = q.limit(page_size).offset((page - 1) * page_size).all()

    data = []
    for reservation, customer in rows:
        data.append({
            "id": reservation.id,
            "time": api_iso_z(reservation.time_slot), # Use consistent Z format
            "tableNumber": reservation.table_number,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
            },
        })


    return jsonify(page=page, pageSize=page_size, total=total, reservations=data)