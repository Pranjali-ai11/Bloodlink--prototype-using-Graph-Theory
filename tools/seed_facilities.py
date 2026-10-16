"""
Seed 6 Pune hospitals and 6 clearly fictional Pune blood banks.

Blood inventory values are DEMO values for the college project.
They are NOT live blood availability.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db
from app.database_info import database_location
from app.models import Hospital, BloodBank, BloodInventory


BLOOD_GROUPS = (
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
    "O+",
    "O-",
)

# Names used by earlier demo seed revisions. They may be renamed only when
# the matched row is explicitly marked as demo data.
LEGACY_DEMO_BLOOD_BANK_NAMES = (
    "Jankalyan Blood Centre",
    "Akshay Blood Centre",
    "Om Blood Bank",
    "Sanjeevan Blood Storage Centre",
    "Deenanath Mangeshkar Hospital Blood Bank",
    "Poona Serological Institute Blood Bank",
)


# ---------------------------------------------------------
# 6 HOSPITALS
# ---------------------------------------------------------

HOSPITALS = [
    {
        "name": "Jehangir Hospital",
        "address": "32, Sassoon Road, Pune, Maharashtra 411001",
        "city": "Pune",
        "latitude": 18.5286,
        "longitude": 73.8744,
        "phone": "+91 20 6681 8801",
    },

    {
        "name": "Sahyadri Super Speciality Hospital - Deccan",
        "address": "Plot No. 30-C, Karve Road, Deccan Gymkhana, Pune, Maharashtra 411004",
        "city": "Pune",
        "latitude": 18.5158,
        "longitude": 73.8380,
        "phone": "+91 20 4713 8766",
    },

    {
        "name": "Jupiter Hospital Pune",
        "address": "Prathamesh Park, Baner, Pune, Maharashtra 411045",
        "city": "Pune",
        "latitude": 18.5590,
        "longitude": 73.7868,
        "phone": "+91 20 6637 5555",
    },

    {
        "name": "Manipal Hospital Kharadi",
        "address": "22/2A, Mundhwa-Kharadi Road, Kharadi, Pune, Maharashtra 411014",
        "city": "Pune",
        "latitude": 18.5510,
        "longitude": 73.9390,
        "phone": "+91 20 6165 6666",
    },

    {
        "name": "MJM Hospital",
        "address": "1194/23, Ghole Road, Shivajinagar, Pune, Maharashtra 411005",
        "city": "Pune",
        "latitude": 18.5280,
        "longitude": 73.8430,
        "phone": "+91 20 4149 9999",
    },

    {
        "name": "Noble Hospitals & Research Centre",
        "address": "153, Magarpatta Road, Hadapsar, Pune, Maharashtra 411013",
        "city": "Pune",
        "latitude": 18.5089,
        "longitude": 73.9270,
        "phone": "+91 20 6628 8888",
    },
]


# ---------------------------------------------------------
# 6 FICTIONAL BLOOD BANKS
# ---------------------------------------------------------

BLOOD_BANKS = [
    {
        "name": "BloodLink Demo Blood Centre - Pune Central",
        "address": "Demo Facility 1, Shivajinagar, Pune, Maharashtra",
        "city": "Pune",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "phone": "+91 20 0000 0101",

        # DEMO inventory
        "inventory": {
            "A+": 18,
            "A-": 5,
            "B+": 14,
            "B-": 4,
            "AB+": 7,
            "AB-": 2,
            "O+": 22,
            "O-": 6,
        },
    },

    {
        "name": "BloodLink Demo Blood Centre - Pune East",
        "address": "Demo Facility 2, Kharadi, Pune, Maharashtra",
        "city": "Pune",
        "latitude": 18.5510,
        "longitude": 73.9390,
        "phone": "+91 20 0000 0102",

        "inventory": {
            "A+": 12,
            "A-": 3,
            "B+": 16,
            "B-": 4,
            "AB+": 8,
            "AB-": 2,
            "O+": 19,
            "O-": 5,
        },
    },

    {
        "name": "BloodLink Demo Blood Centre - Pune West",
        "address": "Demo Facility 3, Baner, Pune, Maharashtra",
        "city": "Pune",
        "latitude": 18.5590,
        "longitude": 73.7868,
        "phone": "+91 20 0000 0103",

        "inventory": {
            "A+": 10,
            "A-": 2,
            "B+": 12,
            "B-": 3,
            "AB+": 6,
            "AB-": 1,
            "O+": 17,
            "O-": 4,
        },
    },

    {
        "name": "BloodLink Demo Blood Centre - Pune South",
        "address": "Demo Facility 4, Hadapsar, Pune, Maharashtra",
        "city": "Pune",
        "latitude": 18.5089,
        "longitude": 73.9270,
        "phone": "+91 20 0000 0104",

        "inventory": {
            "A+": 13,
            "A-": 4,
            "B+": 11,
            "B-": 2,
            "AB+": 5,
            "AB-": 1,
            "O+": 16,
            "O-": 4,
        },
    },

    {
        "name": "BloodLink Demo Blood Centre - Pune North",
        "address": "Demo Facility 5, Aundh, Pune, Maharashtra",
        "city": "Pune",
        "latitude": 18.5600,
        "longitude": 73.8070,
        "phone": "+91 20 0000 0105",

        "inventory": {
            "A+": 15,
            "A-": 4,
            "B+": 17,
            "B-": 5,
            "AB+": 9,
            "AB-": 3,
            "O+": 21,
            "O-": 6,
        },
    },

    {
        "name": "BloodLink Demo Blood Centre - Pune Central East",
        "address": "Demo Facility 6, Mundhwa, Pune, Maharashtra",
        "city": "Pune",
        "latitude": 18.5300,
        "longitude": 73.9100,
        "phone": "+91 20 0000 0106",

        "inventory": {
            "A+": 11,
            "A-": 3,
            "B+": 13,
            "B-": 3,
            "AB+": 7,
            "AB-": 2,
            "O+": 18,
            "O-": 5,
        },
    },
]


# ---------------------------------------------------------
# SEED DATABASE
# ---------------------------------------------------------

def seed_facilities(app=None):
    """Upsert demo facilities into the configured application database."""
    app = app or create_app("development")

    with app.app_context():
        print(f"Seed target database: {database_location(app)}")

        # ---------------------------------------------
        # Add hospitals
        # ---------------------------------------------

        for data in HOSPITALS:

            existing = Hospital.query.filter_by(
                name=data["name"], city=data["city"], is_demo=True
            ).first()

            if existing:
                existing.address = data["address"]
                existing.latitude = data["latitude"]
                existing.longitude = data["longitude"]
                existing.phone = data["phone"]
                existing.is_demo = True
                continue

            if Hospital.query.filter_by(name=data["name"], city=data["city"]).first():
                # Never convert or duplicate a real facility that shares a seed key.
                continue

            hospital = Hospital(
                name=data["name"],
                address=data["address"],
                city=data["city"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                phone=data["phone"],
                is_demo=True,
            )

            db.session.add(hospital)

        # ---------------------------------------------
        # Add blood banks
        # ---------------------------------------------

        for index, data in enumerate(BLOOD_BANKS):

            existing = BloodBank.query.filter_by(
                name=data["name"], city=data["city"], is_demo=True
            ).first()
            if existing is None:
                existing = BloodBank.query.filter_by(
                    name=LEGACY_DEMO_BLOOD_BANK_NAMES[index],
                    city=data["city"], is_demo=True
                ).first()

            if existing is None and BloodBank.query.filter_by(
                    name=data["name"], city=data["city"]).first():
                # Never convert or duplicate a real facility that shares a seed key.
                continue

            if existing:
                bank = existing
                bank.name = data["name"]
                bank.address = data["address"]
                bank.latitude = data["latitude"]
                bank.longitude = data["longitude"]
                bank.phone = data["phone"]
                bank.is_demo = True

            else:
                bank = BloodBank(
                    name=data["name"],
                    address=data["address"],
                    city=data["city"],
                    latitude=data["latitude"],
                    longitude=data["longitude"],
                    phone=data["phone"],
                    is_demo=True,
                )

                db.session.add(bank)
                db.session.flush()

            # -----------------------------------------
            # Add blood inventory
            # -----------------------------------------

            for blood_group in BLOOD_GROUPS:

                units = data["inventory"][blood_group]

                existing_inventory = BloodInventory.query.filter_by(
                    blood_bank_id=bank.id, blood_group=blood_group
                ).first()

                if existing_inventory:
                    if not existing_inventory.is_demo:
                        # Preserve real stock, which is protected by the same
                        # bank/group unique constraint.
                        continue
                    existing_inventory.units = units

                else:
                    inventory = BloodInventory(
                        blood_bank_id=bank.id,
                        blood_group=blood_group,
                        units=units,
                        is_demo=True,
                    )

                    db.session.add(inventory)

        db.session.commit()

        print()
        print("=" * 60)
        print("BloodLink facility database updated successfully!")
        print("=" * 60)
        print("Hospital seed entries : 6")
        print(f"Demo blood banks in seed set : {len(BLOOD_BANKS)}")
        print(f"Inventory records per seeded bank : {len(BLOOD_GROUPS)}")
        print(f"Demo inventory records in seed set : {len(BLOOD_BANKS) * len(BLOOD_GROUPS)}")
        print(f"Blood bank rows in database : {BloodBank.query.count()}")
        print(f"Demo blood bank rows in database : {BloodBank.query.filter_by(is_demo=True).count()}")
        print(f"Inventory rows in database : {BloodInventory.query.count()}")
        print(f"Demo inventory rows in database : {BloodInventory.query.filter_by(is_demo=True).count()}")
        print()
        print("IMPORTANT:")
        print("Blood inventory values are DEMO values.")
        print("They are NOT live blood availability.")
        print("=" * 60)


if __name__ == "__main__":
    seed_facilities()
