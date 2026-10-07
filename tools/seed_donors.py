"""Seed 10 synthetic Pune donor profiles for TEST/DEMO use only.

These profiles and contact details are fictional and must not be treated as
real people or contacted. Demo accounts use the reserved .test email domain.
"""

import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Match run.py so this tool uses the project's configured SQLite database.
load_dotenv(PROJECT_ROOT / ".env")

from app import create_app, db
from app.account_identity import normalize_email, normalize_phone
from app.models import Donor, User


# Synthetic TEST/DEMO profiles only; none of these identities are real donors.
DEMO_DONORS = (
    {
        "name": "Rahul Patil",
        "email": "bloodlink.demo.rahul.patil@demo.bloodlink.test",
        "phone": "9000001001",
        "age": 28,
        "gender": "male",
        "blood_group": "A+",
        "address": "Demo residence, Kothrud, Pune, Maharashtra 411038",
        "latitude": 18.5074,
        "longitude": 73.8077,
    },
    {
        "name": "Sneha Kulkarni",
        "email": "bloodlink.demo.sneha.kulkarni@demo.bloodlink.test",
        "phone": "9000001002",
        "age": 25,
        "gender": "female",
        "blood_group": "O+",
        "address": "Demo residence, Deccan Gymkhana, Pune, Maharashtra 411004",
        "latitude": 18.5158,
        "longitude": 73.8380,
    },
    {
        "name": "Aditya Joshi",
        "email": "bloodlink.demo.aditya.joshi@demo.bloodlink.test",
        "phone": "9000001003",
        "age": 31,
        "gender": "male",
        "blood_group": "B+",
        "address": "Demo residence, Baner, Pune, Maharashtra 411045",
        "latitude": 18.5590,
        "longitude": 73.7868,
    },
    {
        "name": "Priya Sharma",
        "email": "bloodlink.demo.priya.sharma@demo.bloodlink.test",
        "phone": "9000001004",
        "age": 24,
        "gender": "female",
        "blood_group": "AB+",
        "address": "Demo residence, Hadapsar, Pune, Maharashtra 411013",
        "latitude": 18.5089,
        "longitude": 73.9270,
    },
    {
        "name": "Aarav Deshmukh",
        "email": "bloodlink.demo.aarav.deshmukh@demo.bloodlink.test",
        "phone": "9000001005",
        "age": 29,
        "gender": "male",
        "blood_group": "O-",
        "address": "Demo residence, Viman Nagar, Pune, Maharashtra 411014",
        "latitude": 18.5679,
        "longitude": 73.9143,
    },
    {
        "name": "Ananya Pawar",
        "email": "bloodlink.demo.ananya.pawar@demo.bloodlink.test",
        "phone": "9000001006",
        "age": 22,
        "gender": "female",
        "blood_group": "A-",
        "address": "Demo residence, Shivajinagar, Pune, Maharashtra 411005",
        "latitude": 18.5308,
        "longitude": 73.8475,
    },
    {
        "name": "Rohan Jadhav",
        "email": "bloodlink.demo.rohan.jadhav@demo.bloodlink.test",
        "phone": "9000001007",
        "age": 34,
        "gender": "male",
        "blood_group": "B-",
        "address": "Demo residence, Kalyani Nagar, Pune, Maharashtra 411006",
        "latitude": 18.5481,
        "longitude": 73.9035,
    },
    {
        "name": "Meera More",
        "email": "bloodlink.demo.meera.more@demo.bloodlink.test",
        "phone": "9000001008",
        "age": 27,
        "gender": "female",
        "blood_group": "AB-",
        "address": "Demo residence, Aundh, Pune, Maharashtra 411007",
        "latitude": 18.5590,
        "longitude": 73.8070,
    },
    {
        "name": "Kunal Shinde",
        "email": "bloodlink.demo.kunal.shinde@demo.bloodlink.test",
        "phone": "9000001009",
        "age": 30,
        "gender": "male",
        "blood_group": "O+",
        "address": "Demo residence, Pimple Saudagar, Pune, Maharashtra 411027",
        "latitude": 18.5980,
        "longitude": 73.7980,
    },
    {
        "name": "Kavya Nair",
        "email": "bloodlink.demo.kavya.nair@demo.bloodlink.test",
        "phone": "9000001010",
        "age": 26,
        "gender": "female",
        "blood_group": "A+",
        "address": "Demo residence, Koregaon Park, Pune, Maharashtra 411001",
        "latitude": 18.5362,
        "longitude": 73.8939,
    },
)


def seed_donors():
    if len(DEMO_DONORS) != 10:
        raise ValueError("The demo donor seed must contain exactly 10 profiles.")

    emails = [normalize_email(donor["email"]) for donor in DEMO_DONORS]
    phones = [normalize_phone(donor["phone"]) for donor in DEMO_DONORS]
    names = [donor["name"] for donor in DEMO_DONORS]
    if len(set(emails)) != 10 or len(set(phones)) != 10 or len(set(names)) != 10:
        raise ValueError("Demo donor names, emails, and phone numbers must be unique.")

    app = create_app("development")
    with app.app_context():
        existing_users = User.query.all()
        users_by_email = {normalize_email(user.email): user for user in existing_users}
        users_by_phone = {normalize_phone(user.phone): user for user in existing_users}
        donors_to_add = []
        skipped = 0

        # Check every identifier before inserting, so a conflict cannot leave a
        # partially seeded set or alter an unrelated account.
        for donor_data, email, phone in zip(DEMO_DONORS, emails, phones):
            existing_demo_user = users_by_email.get(email)
            if existing_demo_user:
                if existing_demo_user.role != "donor" or not existing_demo_user.donor_profile:
                    raise RuntimeError(
                        f"Demo email is already assigned to a non-donor account: {email}"
                    )
                skipped += 1
                continue

            phone_owner = users_by_phone.get(phone)
            if phone_owner:
                raise RuntimeError(
                    f"Demo phone number is already assigned to another account: {phone}"
                )
            donors_to_add.append(donor_data)

        try:
            for donor_data in donors_to_add:
                email = normalize_email(donor_data["email"])
                phone = normalize_phone(donor_data["phone"])
                user = User(
                    name=donor_data["name"],
                    email=email,
                    email_normalized=email,
                    phone=phone,
                    phone_normalized=phone,
                    role="donor",
                    gender=donor_data["gender"],
                    age=donor_data["age"],
                    is_verified=True,
                )
                user.set_password(secrets.token_urlsafe(32))
                db.session.add(user)
                db.session.flush()

                db.session.add(Donor(
                    user_id=user.user_id,
                    blood_group=donor_data["blood_group"],
                    latitude=donor_data["latitude"],
                    longitude=donor_data["longitude"],
                    address=donor_data["address"],
                    city="Pune",
                    is_available=True,
                ))

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        seeded_users = {
            normalize_email(user.email): user
            for user in User.query.all()
            if normalize_email(user.email) in set(emails)
        }
        verified_profiles = [
            seeded_users[email]
            for email in emails
            if email in seeded_users
            and seeded_users[email].role == "donor"
            and seeded_users[email].donor_profile is not None
        ]
        if len(verified_profiles) != 10:
            raise RuntimeError(
                f"Expected 10 demo donor profiles in SQLite; found {len(verified_profiles)}."
            )

        print(f"Demo donor profiles added: {len(donors_to_add)}")
        print(f"Existing demo donor profiles skipped: {skipped}")
        print(f"Total verified demo donor profiles: {len(verified_profiles)}")
        for user in verified_profiles:
            print(f"- {user.name}: {user.donor_profile.blood_group}")


if __name__ == "__main__":
    seed_donors()
