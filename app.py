"""
Flask Application Factory for Business Loss Detection & Decision Support System.
Registers blueprints, configures error handlers, manages request DB teardown,
and enforces security guidelines.
"""
import os
from flask import Flask, render_template, jsonify
from flask_wtf.csrf import CSRFProtect

from config import Config
from database.connection import close_db

csrf = CSRFProtect()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Initialize CSRF protection
    csrf.init_app(app)

    # Ensure staging directory exists
    os.makedirs(app.config.get("STAGING_DIR", "staging"), exist_ok=True)

    # Register database connection teardown
    app.teardown_appcontext(close_db)

    # Register Route Blueprints
    from routes.dashboard import dashboard_bp
    from routes.upload import upload_bp
    from routes.analysis import analysis_bp
    from routes.alerts import alerts_bp
    from routes.reports import reports_bp
    from routes.data_management import data_mgmt_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(data_mgmt_bp)

    # Custom Error Handlers (Section 8: Never leak stack traces or SQL to user)
    @app.errorhandler(404)
    def handle_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_internal_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(ConnectionError)
    def handle_db_connection_error(e):
        return render_template("errors/500.html"), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Loss Detection System on http://{host}:{port} ...")
    app.run(host=host, port=port, debug=Config.DEBUG)
