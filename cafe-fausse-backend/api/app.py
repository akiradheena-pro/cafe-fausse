from flask import Flask, jsonify
from flask_cors import CORS 
from .extensions import db, migrate
from .config import Config
from .blueprints.reservations import bp as reservations_bp
from .blueprints.newsletter import bp as newsletter_bp

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

    return app