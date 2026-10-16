import os
import logging
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Resolve the project environment file independently of the shell's working
# directory. Load it before config.py evaluates environment-backed settings.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    """SQLite does not enforce declared foreign keys unless enabled per connection."""
    if connection.__class__.__module__.split('.', 1)[0] == 'sqlite3':
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

from flask import Flask, jsonify, request, session
from config import config
from .models import User, db
from .account_identity import (ensure_account_identity_constraints,
                               normalize_email, normalize_phone)


logger = logging.getLogger(__name__)

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    app.config.from_object(config[config_name]())
    db.init_app(app)
    from .routes import auth_bp, donor_bp, search_bp, admin_bp, main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(donor_bp, url_prefix='/api')
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')

    @app.before_request
    def reject_cross_origin_mutations():
        if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            return None
        source = request.headers.get('Origin') or request.headers.get('Referer')
        if source:
            source_host = urlsplit(source).netloc.casefold()
            source_scheme = urlsplit(source).scheme.lower()
            if (source_scheme not in {'http', 'https'} or not source_host
                    or source_host != request.host.casefold()):
                return jsonify({'error': 'Cross-origin request blocked.'}), 403
        return None

    @app.context_processor
    def inject_admin_navigation_state():
        user_id = session.get('user_id')
        is_admin = bool(
            user_id and User.query.filter_by(user_id=user_id, role='admin').first()
        )
        return {'is_admin': is_admin}

    @app.after_request
    def prevent_private_response_caching(response):
        private_pages = {
            '/dashboard', '/network', '/medical-history', '/admin/hospitals',
            '/admin/donors', '/admin/requests',
        }
        if request.path.startswith('/api/') or request.path in private_pages:
            response.headers['Cache-Control'] = 'no-store'
        return response

    with app.app_context():
        db.create_all()
        ensure_account_identity_constraints()

        # A bootstrap admin is created only when both credentials are explicitly configured.
        admin_email = normalize_email(os.environ.get("ADMIN_EMAIL"))
        admin_password = os.environ.get("ADMIN_PASSWORD")

        if admin_email and admin_password and not app.config.get("TESTING"):
            admin_phone = normalize_phone("9999999999")
            identifier_exists = any(
                normalize_email(user.email) == admin_email
                or normalize_phone(user.phone) == admin_phone
                for user in User.query.with_entities(User.email, User.phone).all()
            )
            if not identifier_exists:
                admin = User(
                    name="Administrator",
                    email=admin_email,
                    email_normalized=admin_email,
                    phone=admin_phone,
                    phone_normalized=admin_phone,
                    role="admin",
                    is_verified=True
                )
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                print("Default administrator created from environment configuration")
            else:
                logger.warning(
                    "Bootstrap administrator was not created because its email "
                    "or mobile number is already assigned to an account."
                )

    return app
    
    
