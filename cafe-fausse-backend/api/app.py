from .extensions import db, migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)  # <-- Add this line

    with app.app_context():
        from . import models  # noqa: F401

    app.register_blueprint(reservations_bp, url_prefix="/api/reservations")
    app.register_blueprint(newsletter_bp, url_prefix="/api/newsletter")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app

