
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import Reservation, Customer

bp = Blueprint("reservations", __name__)

TOTAL_TABLES = 30

@bp.get("/availability")
def availability():
    time = request.args.get("time")
    if not time:
        return jsonify(error="Missing 'time'"), 400
    try:
        # Parse to timestamp (expect ISO 8601)
        from datetime import datetime
        ts = datetime.fromisoformat(time)
    except ValueError:
        return jsonify(error="Invalid time format, expected ISO 8601"), 422

    booked_count = db.session.execute(
        select(func.count()).select_from(Reservation).where(Reservation.time_slot == ts)
    ).scalar_one()

    return jsonify(totalTables=TOTAL_TABLES, booked=int(booked_count), available=TOTAL_TABLES - int(booked_count))

@bp.post("")
def create_reservation():
    payload = request.get_json(silent=True) or {}
    required = ["time", "guests", "name", "email"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    from datetime import datetime
    try:
        ts = datetime.fromisoformat(payload["time"])
    except ValueError:
        return jsonify(error="Invalid time format, expected ISO 8601"), 422

    name = payload["name"]
    email = payload["email"]
    phone = payload.get("phone")
    guests = int(payload["guests"])

    # Find or create customer
    customer = Customer.query.filter_by(email=email).one_or_none()
    if not customer:
        customer = Customer(name=name, email=email, phone=phone)
        db.session.add(customer)
        db.session.flush()

    # Compute available tables
    booked = set(
        t for (t,) in db.session.execute(
            select(Reservation.table_number).where(Reservation.time_slot == ts)
        ).all()
    )
    remaining = [t for t in range(1, TOTAL_TABLES + 1) if t not in booked]
    if not remaining:
        return jsonify(error="Time slot fully booked"), 409

    import random
    table = random.choice(remaining)

    res = Reservation(customer_id=customer.id, time_slot=ts, table_number=table)
    db.session.add(res)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Collision due to race; let client retry
        return jsonify(error="Just booked out. Please pick another time."), 409

    return jsonify(reservationId=res.id, tableNumber=table), 201
