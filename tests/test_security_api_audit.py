import unittest

from app import create_app, db
from app.models import BloodRequest, Report, User


class SecurityAndApiAuditTests(unittest.TestCase):
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

    def make_user(self, email, phone, role="seeker"):
        email = email.lower()
        user = User(
            name=email.split("@")[0], email=email, email_normalized=email,
            password_hash="not-used", phone=phone, phone_normalized=phone,
            role=role, age=30,
        )
        user.set_password("StrongPass!")
        db.session.add(user)
        db.session.commit()
        return user

    def login_as(self, user, email=None):
        return self.client.post("/api/login", json={
            "email": email or user.email, "password": "StrongPass!",
        })

    def test_registration_cannot_self_assign_admin_role(self):
        response = self.client.post("/api/register", json={
            "name": "Attacker", "email": "attacker@example.test",
            "password": "StrongPass!", "phone": "1234567890",
            "age": 30, "role": "admin",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.query.count(), 0)

    def test_registration_rejects_malformed_json_and_missing_donor_blood_group(self):
        malformed = self.client.post("/api/register", data="not-json",
                                     content_type="application/json")
        self.assertEqual(malformed.status_code, 400)
        donor = self.client.post("/api/register", json={
            "name": "Donor", "email": "donor@example.test",
            "password": "StrongPass!", "phone": "1234567890",
            "age": 30, "role": "donor",
        })
        self.assertEqual(donor.status_code, 400)
        self.assertEqual(User.query.count(), 0)

    def test_donor_registration_profile_availability_search_and_logout_workflow(self):
        registration = self.client.post("/api/register", json={
            "name": "Test Donor", "email": "donor@example.test",
            "password": "StrongPass!", "phone": "1234567890",
            "age": 30, "role": "donor", "blood_group": "O+",
            "city": "Pune", "address": "Demo address",
            "latitude": 18.52, "longitude": 73.86,
        })
        self.assertEqual(registration.status_code, 201)
        self.assertNotIn("password_hash", registration.get_json()["user"])

        current = self.client.get("/api/current-user").get_json()
        donor_id = current["donor"]["donor_id"]
        self.assertEqual(current["donor"]["blood_group"], "O+")
        self.assertEqual(self.client.put(f"/api/donors/{donor_id}", json={
            "city": "Pune City", "age": 31,
        }).status_code, 200)
        self.assertEqual(self.client.patch(
            f"/api/donors/{donor_id}/availability", json={"is_available": False}
        ).status_code, 200)
        self.assertEqual(self.client.patch(
            f"/api/donors/{donor_id}/availability", json={"is_available": True}
        ).status_code, 200)
        search = self.client.post("/api/search", json={
            "blood_group": "O+", "latitude": 18.52, "longitude": 73.86,
            "radius_km": 10,
        })
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.get_json()["count"], 1)
        invalid_radius = self.client.post("/api/search", json={
            "blood_group": "O+", "latitude": 18.52, "longitude": 73.86,
            "radius_km": "nan",
        })
        self.assertEqual(invalid_radius.status_code, 400)
        self.assertEqual(self.client.post("/api/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/current-user").status_code, 401)

    def test_medical_history_is_scoped_to_authenticated_user(self):
        owner = self.make_user("owner@example.test", "1111111111")
        self.make_user("other@example.test", "2222222222")
        self.assertEqual(self.login_as(owner).status_code, 200)
        saved = self.client.post("/api/medical-history", json={
            "allergies": "Pollen", "additional_notes": "Test only",
        })
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.get("/api/medical-history").get_json()
                         ["medical_history"]["allergies"], "Pollen")
        self.assertEqual(self.client.get("/api/medical-history").headers.get("Cache-Control"), "no-store")
        self.assertEqual(self.client.get("/api/admin/users/2/medical-history").status_code, 403)

    def test_login_malformed_json_returns_client_error(self):
        response = self.client.post("/api/login", data="not-json",
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_admin_email_update_keeps_normalized_login_identifier_in_sync(self):
        admin = self.make_user("admin@example.test", "1111111111", "admin")
        member = self.make_user("member@example.test", "2222222222")
        self.assertEqual(self.login_as(admin).status_code, 200)

        response = self.client.put(
            f"/api/admin/users/{member.user_id}",
            json={"email": "  MEMBER.NEW@EXAMPLE.TEST  ", "is_verified": True},
        )
        self.assertEqual(response.status_code, 200)
        db.session.refresh(member)
        self.assertEqual(member.email, "member.new@example.test")
        self.assertEqual(member.email_normalized, "member.new@example.test")
        self.client.post("/api/logout")
        self.assertEqual(self.login_as(member, " MEMBER.NEW@EXAMPLE.TEST ").status_code, 200)

    def test_cross_origin_mutating_request_is_rejected(self):
        response = self.client.post(
            "/api/register", json={}, headers={"Origin": "https://attacker.example"}
        )
        self.assertEqual(response.status_code, 403)

    def test_sqlite_foreign_key_enforcement_is_enabled(self):
        enabled = db.session.execute(db.text("PRAGMA foreign_keys")).scalar_one()
        self.assertEqual(enabled, 1)

    def test_admin_navigation_is_shown_only_to_administrator(self):
        admin = self.make_user("admin@example.test", "1111111111", "admin")
        member = self.make_user("member@example.test", "2222222222")
        self.assertEqual(self.login_as(admin).status_code, 200)
        self.assertIn(b"Administration", self.client.get("/").data)
        self.client.post("/api/logout")
        self.assertEqual(self.login_as(member).status_code, 200)
        self.assertNotIn(b"Administration", self.client.get("/").data)

    def test_template_pages_render_for_signed_in_and_public_users(self):
        for path in ("/", "/register", "/login", "/search"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        admin = self.make_user("admin@example.test", "1111111111", "admin")
        self.assertEqual(self.login_as(admin).status_code, 200)
        for path in (
                "/dashboard", "/medical-history", "/network", "/admin/hospitals",
                "/admin/donors", "/admin/requests"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_logout_removes_access_to_protected_api(self):
        member = self.make_user("member@example.test", "1111111111")
        self.assertEqual(self.login_as(member).status_code, 200)
        self.assertEqual(self.client.get("/api/current-user").status_code, 200)
        self.assertEqual(self.client.post("/api/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/current-user").status_code, 401)

    def test_request_creation_validates_fields_and_persists_valid_request(self):
        member = self.make_user("member@example.test", "1111111111")
        self.assertEqual(self.login_as(member).status_code, 200)
        invalid = self.client.post("/api/requests", json={
            "blood_group": "invalid", "location": "Pune",
        })
        self.assertEqual(invalid.status_code, 400)
        valid = self.client.post("/api/requests", json={
            "blood_group": "O+", "urgency_level": "urgent", "location": "Pune",
            "latitude": 18.52, "longitude": 73.86,
        })
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(BloodRequest.query.count(), 1)
        request_id = valid.get_json()["request"]["request_id"]
        self.assertEqual(self.client.get("/api/requests").get_json()["count"], 1)
        updated = self.client.put(f"/api/requests/{request_id}", json={
            "status": "fulfilled", "urgency_level": "critical",
        })
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["request"]["status"], "fulfilled")

    def test_admin_api_requires_admin_role(self):
        self.assertEqual(self.client.get("/api/admin/users").status_code, 401)
        member = self.make_user("member@example.test", "1111111111")
        self.assertEqual(self.login_as(member).status_code, 200)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
        self.client.post("/api/logout")
        admin = self.make_user("admin@example.test", "2222222222", "admin")
        self.assertEqual(self.login_as(admin).status_code, 200)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 200)

    def test_user_with_incoming_report_is_not_deleted_or_orphaned(self):
        admin = self.make_user("admin@example.test", "1111111111", "admin")
        reporter = self.make_user("reporter@example.test", "2222222222")
        reported = self.make_user("reported@example.test", "3333333333")
        self.assertEqual(self.login_as(reporter).status_code, 200)
        report_response = self.client.post("/api/admin/reports", json={
            "reported_user_id": reported.user_id, "reason": "Audit test report",
        })
        self.assertEqual(report_response.status_code, 201)
        self.client.post("/api/logout")
        self.assertEqual(self.login_as(admin).status_code, 200)
        deletion = self.client.delete(f"/api/admin/users/{reported.user_id}")
        self.assertEqual(deletion.status_code, 409)
        self.assertIsNotNone(db.session.get(User, reported.user_id))
        self.assertEqual(Report.query.count(), 1)

    def test_administrator_account_cannot_be_deleted_through_user_api(self):
        admin = self.make_user("admin@example.test", "1111111111", "admin")
        self.assertEqual(self.login_as(admin).status_code, 200)
        response = self.client.delete(f"/api/admin/users/{admin.user_id}")
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(db.session.get(User, admin.user_id))

    def test_blood_request_details_are_private_to_owner_and_admin(self):
        owner = self.make_user("owner@example.test", "1111111111")
        other = self.make_user("other@example.test", "2222222222")
        admin = self.make_user("admin@example.test", "3333333333", "admin")
        blood_request = BloodRequest(
            requester_id=owner.user_id, blood_group="O+", location="Pune",
            urgency_level="normal",
        )
        db.session.add(blood_request)
        db.session.commit()

        self.assertEqual(self.client.get(f"/api/requests/{blood_request.request_id}").status_code, 401)
        self.assertEqual(self.login_as(other).status_code, 200)
        self.assertEqual(self.client.get(f"/api/requests/{blood_request.request_id}").status_code, 403)
        self.client.post("/api/logout")
        self.assertEqual(self.login_as(owner).status_code, 200)
        self.assertEqual(self.client.get(f"/api/requests/{blood_request.request_id}").status_code, 200)
        self.client.post("/api/logout")
        self.assertEqual(self.login_as(admin).status_code, 200)
        self.assertEqual(self.client.get(f"/api/requests/{blood_request.request_id}").status_code, 200)


if __name__ == "__main__":
    unittest.main()
