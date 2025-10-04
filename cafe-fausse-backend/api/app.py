import random
from datetime import datetime, timedelta
import click
from flask import Flask, jsonify
from flask.cli import with_appcontext
from flask_cors import CORS
from .extensions import db, migrate
from .config import Config
from .blueprints.reservations import bp as reservations_bp
from .blueprints.newsletter import bp as newsletter_bp
from .models import Customer, Reservation 

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from . import models 

    app.register_blueprint(reservations_bp, url_prefix="/api/reservations")
    app.register_blueprint(newsletter_bp, url_prefix="/api/newsletter")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @click.command("seed")
    @with_appcontext
    def seed_command():
        """Creates sample data for the database."""
        db.session.query(Reservation).delete()
        db.session.query(Customer).delete()
        db.session.commit()
        print("Cleared existing data.")

        customers = []
        for i in range(10):
            customer = Customer(
                name=f"Customer {i+1}",
                email=f"customer{i+1}@example.com",
                phone=f"123-555-000{i}",
                newsletter_opt_in=random.choice([True, False])
            )
            customers.append(customer)
        db.session.add_all(customers)
        db.session.commit()
        print(f"Created {len(customers)} customers.")
        
        reservations = []
        total_tables = app.config["TOTAL_TABLES"]
        today = datetime.utcnow().date()
        for _ in range(35): 
            customer = random.choice(customers)
            day_offset = random.randint(0, 2)
            res_date = today + timedelta(days=day_offset)
            hour = random.randint(17, 22)
            minute = random.choice([0, 30])
            time_slot = datetime(res_date.year, res_date.month, res_date.day, hour, minute)
            
            if not any(r for r in reservations if r.time_slot == time_slot and r.table_number == table_num):
                 table_num = random.randint(1, total_tables)
                 reservation = Reservation(
                    customer_id=customer.id,
                    time_slot=time_slot,
                    table_number=table_num
                )
                 reservations.append(reservation)

        db.session.add_all(reservations)
        db.session.commit()
        print(f"Created {len(reservations)} reservations.")
        print("Database seeded!")

    app.cli.add_command(seed_command)

    return app