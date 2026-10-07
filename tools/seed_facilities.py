"""
Seed 6 Pune hospitals and 6 Pune blood banks.

Blood inventory values are DEMO values for the college project.
They are NOT live blood availability.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db
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
# 6 BLOOD BANKS
# ---------------------------------------------------------

BLOOD_BANKS = [
    {
        "name": "Jankalyan Blood Centre",
        "address": "1003, Saras Baug Road, Shukrawar Peth, Pune, Maharashtra 411002",
        "city": "Pune",
        "latitude": 18.5055,
        "longitude": 73.8550,
        "phone": "+91 20 2444 9527",

        # DEMO inventory
        "inventory": {
            "A+": 12,
            "A-": 4,
            "B+": 15,
            "B-": 3,
            "AB+": 8,
            "AB-": 2,
            "O+": 20,
            "O-": 5,
        },
    },

    {
        "name": "Akshay Blood Centre",
        "address": "Survey No. 10, Utkarsh Nagar, Hadapsar, Pune, Maharashtra 411028",
        "city": "Pune",
        "latitude": 18.4980,
        "longitude": 73.9260,
        "phone": "+91 96979 34444",

        "inventory": {
            "A+": 10,
            "A-": 3,
            "B+": 14,
            "B-": 4,
            "AB+": 7,
            "AB-": 2,
            "O+": 18,
            "O-": 4,
        },
    },

    {
        "name": "Om Blood Bank",
        "address": "Baburaoji Sonawane Path, Mangalwar Peth, Pune, Maharashtra 411011",
        "city": "Pune",
        "latitude": 18.5235,
        "longitude": 73.8620,
        "phone": "+91 81495 08080",

        "inventory": {
            "A+": 8,
            "A-": 2,
            "B+": 11,
            "B-": 3,
            "AB+": 6,
            "AB-": 1,
            "O+": 16,
            "O-": 3,
        },
    },

    {
        "name": "Sanjeevan Blood Storage Centre",
        "address": "Medipoint Hospital, Shivraj Chowk, Chandan Nagar, Pune, Maharashtra 411014",
        "city": "Pune",
        "latitude": 18.5530,
        "longitude": 73.9250,
        "phone": "+91 77739 66539",

        "inventory": {
            "A+": 9,
            "A-": 3,
            "B+": 12,
            "B-": 2,
            "AB+": 5,
            "AB-": 1,
            "O+": 17,
            "O-": 4,
        },
    },

    {
        "name": "Deenanath Mangeshkar Hospital Blood Bank",
        "address": "Erandwane, Pune, Maharashtra 411004",
        "city": "Pune",
        "latitude": 18.5035,
        "longitude": 73.8265,
        "phone": "+91 20 4015 1000",

        "inventory": {
            "A+": 14,
            "A-": 4,
            "B+": 16,
            "B-": 4,
            "AB+": 9,
            "AB-": 2,
            "O+": 22,
            "O-": 6,
        },
    },

    {
        "name": "Poona Serological Institute Blood Bank",
        "address": "Dhanwantri Complex, Rasta Peth, Pune, Maharashtra 411002",
        "city": "Pune",
        "latitude": 18.5210,
        "longitude": 73.8645,
        "phone": "+91 20 2613 3387",

        "inventory": {
            "A+": 11,
            "A-": 3,
            "B+": 13,
            "B-": 3,
            "AB+": 7,
            "AB-": 2,
            "O+": 19,
            "O-": 5,
        },
    },
]


# ---------------------------------------------------------
# SEED DATABASE
# ---------------------------------------------------------

def seed_facilities():

    app = create_app("development")

    with app.app_context():

        # ---------------------------------------------
        # Remove the old DEMO facilities only
        # ---------------------------------------------

        old_demo_banks = BloodBank.query.filter_by(is_demo=True).all()

        for bank in old_demo_banks:
            db.session.delete(bank)

        old_demo_hospitals = Hospital.query.filter_by(is_demo=True).all()

        for hospital in old_demo_hospitals:
            db.session.delete(hospital)

        db.session.commit()

        # ---------------------------------------------
        # Add hospitals
        # ---------------------------------------------

        for data in HOSPITALS:

            existing = Hospital.query.filter_by(
                name=data["name"],
                city=data["city"]
            ).first()

            if existing:
                continue

            hospital = Hospital(
                name=data["name"],
                address=data["address"],
                city=data["city"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                phone=data["phone"],
                is_demo=False,
            )

            db.session.add(hospital)

        # ---------------------------------------------
        # Add blood banks
        # ---------------------------------------------

        for data in BLOOD_BANKS:

            existing = BloodBank.query.filter_by(
                name=data["name"],
                city=data["city"]
            ).first()

            if existing:
                bank = existing

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
                    blood_bank_id=bank.id,
                    blood_group=blood_group
                ).first()

                if existing_inventory:
                    existing_inventory.units = units
                    existing_inventory.is_demo = True

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
        print("Hospitals added : 6")
        print("Blood banks added : 6")
        print("Blood groups per bank : 8")
        print()
        print("IMPORTANT:")
        print("Blood inventory values are DEMO values.")
        print("They are NOT live blood availability.")
        print("=" * 60)


if __name__ == "__main__":
    seed_facilities()
