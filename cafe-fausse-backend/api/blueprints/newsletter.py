
from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import Customer

bp = Blueprint("newsletter", __name__)

@bp.post("")
def subscribe():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    if not email or "@" not in email:
        return jsonify(error="Invalid email"), 400

    name = payload.get("name") or "Subscriber"
    phone = payload.get("phone")

    cust = Customer.query.filter_by(email=email).one_or_none()
    if cust:
        cust.newsletter_opt_in = True
    else:
        cust = Customer(name=name, email=email, phone=phone, newsletter_opt_in=True)
        db.session.add(cust)

    db.session.commit()
    return jsonify(message="Email added to newsletter"), 200
