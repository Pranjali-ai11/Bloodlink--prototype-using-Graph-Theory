"""Seed explicitly labeled demo facilities and blood inventory.
Run from the project root with: python tools/seed_facilities.py
Sample units are not live availability.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db
from app.models import BloodBank, BloodInventory, Hospital

BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
SAMPLE_BANKS = (
    ("City Blood Bank", (4, 2, 3, 1, 2, 1, 5, 2)),
    ("Central Blood Bank", (3, 1, 2, 2, 1, 1, 4, 3)),
)


def seed_facilities():
    app = create_app("development")
    with app.app_context():
        for name in ("City Care Hospital", "General Hospital"):
            if not Hospital.query.filter_by(name=name, city="Demo City").first():
                db.session.add(Hospital(
                    name=name,
                    address="Demo record - replace with verified facility details.",
                    city="Demo City", is_demo=True,
                ))
        for name, sample_units in SAMPLE_BANKS:
            bank = BloodBank.query.filter_by(name=name, city="Demo City").first()
            if not bank:
                bank = BloodBank(
                    name=name,
                    address="Demo record - replace with verified facility details.",
                    city="Demo City", is_demo=True,
                )
                db.session.add(bank)
                db.session.flush()
            for blood_group, units in zip(BLOOD_GROUPS, sample_units):
                existing = BloodInventory.query.filter_by(
                    blood_bank_id=bank.id, blood_group=blood_group
                ).first()
                if not existing:
                    db.session.add(BloodInventory(
                        blood_bank_id=bank.id, blood_group=blood_group,
                        units=units, is_demo=True,
                    ))
        db.session.commit()
        print("Sample facilities and clearly labeled demo inventory are ready.")


if __name__ == "__main__":
    seed_facilities()
