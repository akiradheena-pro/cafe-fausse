
from datetime import datetime
from sqlalchemy import UniqueConstraint, func
from .extensions import db

class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(32))
    newsletter_opt_in = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    reservations = db.relationship("Reservation", back_populates="customer", cascade="all, delete-orphan")

class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    time_slot = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    table_number = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    customer = db.relationship("Customer", back_populates="reservations")

    __table_args__ = (
        UniqueConstraint("time_slot", "table_number", name="uq_reservation_slot_table"),
    )
