import os
import logging

from flask import Flask
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
    with app.app_context():
        db.create_all()
        ensure_account_identity_constraints()

        # A bootstrap admin is created only when both credentials are explicitly configured.
        admin_email = normalize_email(os.environ.get("ADMIN_EMAIL"))
        admin_password = os.environ.get("ADMIN_PASSWORD")

        if admin_email and admin_password:
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
    
    
