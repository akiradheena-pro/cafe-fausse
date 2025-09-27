from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import Customer
from ..http import jerror
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

bp = Blueprint("newsletter", __name__)

@bp.post("")
def subscribe():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jerror(422, "BAD_EMAIL", "Invalid email format.")

    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()

    t = Customer.__table__

    ins = pg_insert(t).values(
        name=(name or "Subscriber"),
        email=email,
        phone=(phone or ""),
        newsletter_opt_in=True,
    )

    update_set = {
        t.c.newsletter_opt_in: sa.true(),
        t.c.name: sa.func.coalesce(sa.func.nullif(ins.excluded.name, ""), t.c.name),
        t.c.phone: sa.func.coalesce(sa.func.nullif(ins.excluded.phone, ""), t.c.phone),
    }

    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.email],
        set_=update_set,
    ).returning(t.c.id)

    customer_id = db.session.execute(stmt).scalar_one()
    db.session.commit()

    return jsonify(message="Email added to newsletter", customerId=customer_id), 200
