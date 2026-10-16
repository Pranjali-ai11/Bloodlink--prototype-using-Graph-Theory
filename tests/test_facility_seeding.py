import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app, db
from app.models import BloodBank, BloodInventory, User
from config import DevelopmentConfig
from app.utils import haversine_distance
from tools.seed_facilities import (
    BLOOD_BANKS, BLOOD_GROUPS, LEGACY_DEMO_BLOOD_BANK_NAMES,
    seed_facilities,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FacilitySeedTests(unittest.TestCase):
    def test_seed_is_repeatable_safe_and_uses_database_for_admin_and_public_pages(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "instance") as temp_dir:
            database_path = (Path(temp_dir) / "seed-test.db").resolve()
            database_url = f"sqlite:///{database_path.as_posix()}"
            with patch.dict(os.environ, {"DATABASE_URL": database_url}), \
                    patch.object(DevelopmentConfig, "SQLALCHEMY_DATABASE_URI", database_url):
                app = create_app("development")
                app.config["TESTING"] = True
                with app.app_context():
                    # Set up an earlier demo record so the seeder must update it.
                    legacy = BloodBank(
                        name=LEGACY_DEMO_BLOOD_BANK_NAMES[0], city="Pune",
                        address="Old sample address", is_demo=True,
                    )
                    real = BloodBank(
                        name="Independent Real Blood Bank", city="Pune",
                        address="Real facility address", phone="REAL-CONTACT",
                        latitude=18.51, longitude=73.85, is_demo=False,
                    )
                    db.session.add_all([legacy, real])
                    db.session.flush()
                    db.session.add_all([
                        BloodInventory(blood_bank_id=legacy.id, blood_group="A+",
                                       units=1, is_demo=True),
                        BloodInventory(blood_bank_id=real.id, blood_group="O+",
                                       units=77, is_demo=False),
                    ])
                    db.session.commit()
                    real_id = real.id

                client = app.test_client()
                seed_facilities(app)
                seed_facilities(app)
                with app.app_context():
                    demo_banks = BloodBank.query.filter_by(is_demo=True).all()
                    self.assertEqual(len(demo_banks), len(BLOOD_BANKS))
                    self.assertEqual(
                        BloodInventory.query.filter_by(is_demo=True).count(),
                        len(BLOOD_BANKS) * len(BLOOD_GROUPS),
                    )
                    self.assertEqual(BloodInventory.query.count(), 49)
                    seeded = BloodBank.query.filter_by(
                        name=BLOOD_BANKS[0]["name"], city="Pune", is_demo=True
                    ).one()
                    self.assertEqual(seeded.address, BLOOD_BANKS[0]["address"])
                    self.assertTrue(seeded.latitude and seeded.longitude)
                    self.assertTrue(-90 <= seeded.latitude <= 90)
                    self.assertTrue(-180 <= seeded.longitude <= 180)
                    self.assertGreater(
                        haversine_distance(18.52, 73.86, seeded.latitude, seeded.longitude), 0
                    )
                    self.assertEqual(
                        BloodInventory.query.filter_by(
                            blood_bank_id=seeded.id, blood_group="A+"
                        ).one().units,
                        BLOOD_BANKS[0]["inventory"]["A+"],
                    )
                    real = db.session.get(BloodBank, real_id)
                    self.assertEqual(real.name, "Independent Real Blood Bank")
                    self.assertFalse(real.is_demo)
                    self.assertEqual(real.address, "Real facility address")
                    self.assertEqual(
                        BloodInventory.query.filter_by(
                            blood_bank_id=real_id, blood_group="O+"
                        ).one().units,
                        77,
                    )

                    public_banks = client.get("/api/blood-banks").get_json()["blood_banks"]
                    self.assertEqual(len(public_banks), len(BLOOD_BANKS) + 1)
                    self.assertEqual(
                        sum(1 for bank in public_banks if bank["is_demo"]),
                        len(BLOOD_BANKS),
                    )
                    seeded_public = next(item for item in public_banks if item["id"] == seeded.id)
                    self.assertTrue(seeded_public["is_demo"])
                    self.assertEqual(len(seeded_public["inventory"]), 8)
                    inventory_api = client.get(
                        f"/api/blood-banks/{seeded.id}/inventory"
                    ).get_json()
                    self.assertEqual(len(inventory_api["inventory"]), 8)

                    admin = User(
                        name="Seed Admin", email="seed-admin@example.test",
                        email_normalized="seed-admin@example.test",
                        password_hash="test", phone="1234567890",
                        phone_normalized="1234567890", role="admin",
                    )
                    db.session.add(admin)
                    db.session.commit()
                    with client.session_transaction() as session:
                        session["user_id"] = admin.user_id
                    admin_banks = client.get("/api/admin/blood-banks")
                    self.assertEqual(admin_banks.status_code, 200)
                    admin_body = admin_banks.get_json()
                    self.assertIsInstance(admin_body["blood_banks"], list)
                    self.assertEqual(admin_body["count"], len(BLOOD_BANKS) + 1)
                    self.assertEqual(
                        sum(1 for bank in admin_body["blood_banks"] if bank["is_demo"]),
                        len(BLOOD_BANKS),
                    )
                    banks_page = client.get("/admin/blood-banks")
                    inventory_page = client.get("/admin/inventory")
                    self.assertEqual(banks_page.status_code, 200)
                    self.assertIn(b"BLOODLINK_FACILITY_TYPE", banks_page.data)
                    self.assertIn(b"admin_facilities.js?v=", banks_page.data)
                    self.assertEqual(inventory_page.status_code, 200)
                    self.assertIn(BLOOD_BANKS[0]["name"].encode(), inventory_page.data)
                    db.session.remove()
                    db.engine.dispose()

        frontend_files = list((PROJECT_ROOT / "app" / "templates").glob("*.html"))
        frontend_files += list((PROJECT_ROOT / "app" / "static" / "js").glob("*.js"))
        for bank in BLOOD_BANKS:
            for frontend in frontend_files:
                contents = frontend.read_bytes()
                self.assertNotIn(bank["name"].encode(), contents, frontend.name)
                self.assertNotIn(bank["address"].encode(), contents, frontend.name)
                self.assertNotIn(bank["phone"].encode(), contents, frontend.name)
        public_search_js = (PROJECT_ROOT / "app/static/js/search.js").read_text()
        self.assertIn("item.blood_group === bloodGroup", public_search_js)
        self.assertIn("/api/blood-banks", public_search_js)
        admin_facility_js = (PROJECT_ROOT / "app/static/js/admin_facilities.js").read_text()
        self.assertIn("/api/admin/${kind}", admin_facility_js)
        self.assertIn("const collectionKey = kind === 'blood-banks' ? 'blood_banks' : kind", admin_facility_js)
        self.assertIn("Array.isArray(data[collectionKey])", admin_facility_js)

    def test_admin_blood_bank_endpoint_contract_contains_six_seeded_records(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "instance") as temp_dir:
            database_path = (Path(temp_dir) / "admin-api-test.db").resolve()
            database_url = f"sqlite:///{database_path.as_posix()}"
            with patch.dict(os.environ, {"DATABASE_URL": database_url}), \
                    patch.object(DevelopmentConfig, "SQLALCHEMY_DATABASE_URI", database_url):
                app = create_app("development")
                app.config["TESTING"] = True
                try:
                    seed_facilities(app)
                    with app.app_context():
                        admin = User(
                            name="API Contract Admin", email="api-contract@example.test",
                            email_normalized="api-contract@example.test",
                            password_hash="test", phone="1234567890",
                            phone_normalized="1234567890", role="admin",
                        )
                        db.session.add(admin)
                        db.session.commit()
                        admin_id = admin.user_id

                    client = app.test_client()
                    self.assertEqual(client.get("/api/admin/blood-banks").status_code, 401)
                    with client.session_transaction() as session:
                        session["user_id"] = admin_id
                    response = client.get("/api/admin/blood-banks")
                    self.assertEqual(response.status_code, 200)
                    body = response.get_json()
                    self.assertIsInstance(body["blood_banks"], list)
                    self.assertEqual(len(body["blood_banks"]), 6)
                    self.assertEqual(body["count"], 6)
                finally:
                    with app.app_context():
                        db.session.remove()
                        db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
