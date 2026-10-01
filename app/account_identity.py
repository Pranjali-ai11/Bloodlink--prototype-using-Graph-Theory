"""Normalization and safe schema setup for unique account identifiers."""

import logging
from collections import defaultdict

from sqlalchemy import inspect

from .models import User, db


logger = logging.getLogger(__name__)


def normalize_email(email):
    """Return the canonical form used to compare and store email addresses."""
    return str(email or "").strip().lower()


def normalize_phone(phone):
    """Remove surrounding/internal whitespace and hyphens from a mobile number."""
    return "".join(str(phone or "").split()).replace("-", "")


def ensure_account_identity_constraints():
    """Add canonical identifier columns/indexes without discarding legacy users.

    Legacy duplicate values receive NULL canonical keys so all user rows survive.
    Registration checks those legacy values explicitly; the unique indexes then
    serialize concurrent registrations for all canonical keys going forward.
    """
    columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
    if "email_normalized" not in columns:
        db.session.execute(db.text(
            "ALTER TABLE users ADD COLUMN email_normalized VARCHAR(100)"
        ))
    if "phone_normalized" not in columns:
        db.session.execute(db.text(
            "ALTER TABLE users ADD COLUMN phone_normalized VARCHAR(15)"
        ))
    db.session.commit()

    users = User.query.order_by(User.user_id).all()
    groups = {"email": defaultdict(list), "mobile": defaultdict(list)}
    normalized = {}
    for user in users:
        email = normalize_email(user.email)
        phone = normalize_phone(user.phone)
        normalized[user.user_id] = (email, phone)
        if email:
            groups["email"][email].append(user.user_id)
        if phone:
            groups["mobile"][phone].append(user.user_id)

    duplicates = {
        identifier: {value: ids for value, ids in values.items() if len(ids) > 1}
        for identifier, values in groups.items()
    }
    for user in users:
        email, phone = normalized[user.user_id]
        user.email_normalized = (
            email if email and len(groups["email"][email]) == 1 else None
        )
        user.phone_normalized = (
            phone if phone and len(groups["mobile"][phone]) == 1 else None
        )
    db.session.commit()

    db.session.execute(db.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_normalized "
        "ON users (email_normalized)"
    ))
    db.session.execute(db.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_phone_normalized "
        "ON users (phone_normalized)"
    ))
    db.session.commit()

    for identifier, values in duplicates.items():
        if values:
            logger.warning(
                "Existing duplicate normalized %s values found; accounts were "
                "preserved. Resolve these manually: %s", identifier, values
            )
