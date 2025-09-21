from flask import Flask, jsonify
from .extensions import db
from flask_migrate import Migrate   # ✅ import this
from .config import Config
from .blueprints.reservations import bp as reservations_bp
from .blueprints.newsletter import bp as newsletter_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)   # ✅ enable flask db commands

    with app.app_context():
        from . import models  # noqa: F401

    app.register_blueprint(reservations_bp, url_prefix="/api/reservations")
    app.register_blueprint(newsletter_bp, url_prefix="/api/newsletter")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app
