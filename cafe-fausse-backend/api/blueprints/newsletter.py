from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import Customer
from ..http import jerror

bp = Blueprint("newsletter", __name__)

@bp.post("")
def subscribe():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jerror(422, "BAD_EMAIL", "Invalid email format.")

    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()

    # Try to find existing customer
    customer = Customer.query.filter_by(email=email).first()
    if customer:
        # Update opt-in and optional fields if provided
        customer.newsletter_opt_in = True
        if name:
            customer.name = name
        if phone:
            customer.phone = phone
    else:
        # Create new customer
        customer = Customer(
            name=name or "Subscriber",
            email=email,
            phone=phone,
            newsletter_opt_in=True
        )
        db.session.add(customer)

    db.session.commit()

    return jsonify(message="Email added to newsletter", customerId=customer.id), 200
