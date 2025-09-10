from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import Reservation, Customer

bp = Blueprint("reservations", __name__)

TOTAL_TABLES = 30

@bp.get("/availability")
def availability():
    time_arg = request.args.get("time") or request.args.get("time_slot")
    if not time_arg:
        return jsonify(error="Missing 'time' query parameter (or 'time slot')"), 400
    try:
        # Parse to timestamp (expect ISO 8601)
        from datetime import datetime
        ts = datetime.fromisoformat(time_arg)
    except ValueError:
        return jsonify(error="Invalid time format, expected ISO 8601"), 422

    booked_count = db.session.execute(
        select(func.count()).select_from(Reservation).where(Reservation.time_slot == ts)
    ).scalar_one()

    return jsonify(totalTables=TOTAL_TABLES, booked=int(booked_count), available=TOTAL_TABLES - int(booked_count))

@bp.post("")
def create_reservation():
    payload = request.get_json(silent=True) or {}

    # Accept either "time" or "time_slot", and "guests" or "guest_count"
    time_value = payload.get("time") or payload.get("time_slot")
    guests_val = payload.get("guests") or payload.get("guest_count")
    name = payload.get("name)
    email = payload.get("email")
    phone = payload.get("phone")
    newsletter = payload.get("newsletter", False)

    required = []
    if not time_val:
        required.append("time or time_slot")
    if not guests_val:
        required.append("guests or guest_count")
    if not name:
        required.append("name")
    if not email:
        required.append("email")

    if required:
        return jsonify(error=f"Missing fields: {', '.join(required)}"), 400

    # parse time
    from datetime import datetime
    try:
        ts = datetime.fromisoformat(time_val)
    except ValueError:
       return jsonify(error="Invalid time format, expected ISO 8601"), 422

    # parse guests
    try:
        guests = int(guests_val)
        if guests <=0:
            raise ValueError()
    except Exception:
        return jsonify(error="Invalid guests value; must be a positive integer"), 422
    
    # Find or create customer
    customer = Customer.query.filter_by(email=email).one_or_none()
    if not customer:
        customer = Customer(name=name, email=email, phone=phone, newsletter_opt_in=boo1(newsletter))
        db.session.add(customer)
        db.session.flush()
    else:
        # If the user asked to subscribe to newsletter in this booking, update flag
        if newsletter and not customer.newsletter_opt_in:
            customer.newsletter_opt_in = True
            db.session.add(customer)

    # Compute available tables
    booked = set(
        t for (t,) in db.session.execute(
            select(Reservation.table_number).where(Reservation.time_slot == ts)
        ).all()
    )
    remaining = [t for t in range(1, TOTAL_TABLES + 1) if t not in booked]
    if not remaining:
        return jsonify(error="Time slot fully booked", message="No tables available, please choose another time."), 409

    import random
    table = random.choice(remaining)

    res = Reservation(customer_id=customer.id, time_slot=ts, table_number=table, guest_count=guests)
    db.session.add(res)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Collision due to race; let client retry
        return jsonify(error="Just booked out. Please pick another time."), 409

    return (
        jsonify(
            reservation_id=res.id, 
            table_number=table), 
            message="Reservation confirmed",
        ),
        201
    )
            
           
