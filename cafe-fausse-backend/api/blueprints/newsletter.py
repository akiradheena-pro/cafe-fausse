from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..extensions import db
from ..models import Customer
from ..http import jerror
from ..schemas import SubscribeRequest  
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from pydantic import ValidationError


bp = Blueprint("newsletter", __name__)

@bp.post("")
def subscribe():
    payload = request.get_json(silent=True)
    if not payload:
        return jerror(400, "INVALID_PAYLOAD", "Missing or invalid JSON payload.")

    try:
        data = SubscribeRequest.model_validate(payload)
    except ValidationError as e:
        return jerror(422, "VALIDATION_ERROR", "Invalid input.", details=e.errors())

    t = Customer.__table__

    ins = pg_insert(t).values(
        name=data.name,
        email=data.email.lower(), 
        phone=data.phone or "",
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