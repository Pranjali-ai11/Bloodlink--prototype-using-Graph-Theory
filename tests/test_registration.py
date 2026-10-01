import unittest

from sqlalchemy.exc import IntegrityError
import werkzeug

# Flask 2.3's test client reads this attribute, removed in Werkzeug 3.1.
if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.1+"

from app import create_app, db
from app.models import User


class RegistrationUniquenessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def payload(self, email="new@example.test", phone="1234567890"):
        return {
            "name": "New User",
            "email": email,
            "password": "StrongPass!",
            "phone": phone,
            "age": 30,
            "role": "seeker",
        }

    def register(self, **overrides):
        return self.client.post("/api/register", json=self.payload(**overrides))

    def test_new_email_and_mobile_register_successfully(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["user"]["email"], "new@example.test")
        user = User.query.one()
        self.assertEqual(user.email_normalized, "new@example.test")
        self.assertEqual(user.phone_normalized, "1234567890")

    def test_existing_email_is_rejected(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.register(email="new@example.test", phone="9876543210")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"],
                         "An account already exists with this email.")

    def test_existing_mobile_is_rejected_after_phone_normalization(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.register(email="other@example.test", phone="123-456-7890")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"],
                         "An account already exists with this mobile number.")

    def test_email_case_and_surrounding_spaces_are_normalized(self):
        self.assertEqual(self.register(email=" Person@Example.Test ").status_code, 201)
        for email in ("person@example.test", "  PERSON@EXAMPLE.TEST  "):
            response = self.register(email=email, phone="9876543210")
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.get_json()["error"],
                             "An account already exists with this email.")
        self.assertEqual(User.query.count(), 1)

    def test_login_still_finds_normalized_email(self):
        self.assertEqual(self.register(email=" Person@Example.Test ").status_code, 201)
        self.client.post("/api/logout")
        response = self.client.post("/api/login", json={
            "email": "  PERSON@EXAMPLE.TEST ",
            "password": "StrongPass!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["email"], "person@example.test")

    def test_database_unique_indexes_reject_duplicate_canonical_keys(self):
        first = User(name="First", email="first@example.test",
                     email_normalized="first@example.test", password_hash="x",
                     phone="1111111111", phone_normalized="1111111111")
        db.session.add(first)
        db.session.commit()

        duplicate_email = User(name="Duplicate Email", email="different@example.test",
                               email_normalized="first@example.test", password_hash="x",
                               phone="2222222222", phone_normalized="2222222222")
        db.session.add(duplicate_email)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        duplicate_phone = User(name="Duplicate Mobile", email="third@example.test",
                               email_normalized="third@example.test", password_hash="x",
                               phone="1111111111", phone_normalized="1111111111")
        db.session.add(duplicate_phone)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        self.assertEqual(User.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
