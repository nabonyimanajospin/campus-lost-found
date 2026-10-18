from django.contrib.auth import get_user_model

from campus_lost_found.testing import PASSWORD, APIBase
from student.models import Student


class AuthTests(APIBase):
    def test_register_login_logout_flow(self):
        client, student = self.register("Alice@Example.com")
        self.assertEqual(student.email, "alice@example.com")  # normalised
        self.assertEqual(student.user.username, "alice@example.com")

        login = self.client.post(
            "/api/v1/auth/login/", {"email": "ALICE@example.com", "password": PASSWORD}, format="json"
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("token", login.data)

        self.assertEqual(client.get("/api/v1/auth/me/").data["email"], "alice@example.com")
        self.assertEqual(client.post("/api/v1/auth/logout/").status_code, 204)
        self.assertEqual(client.get("/api/v1/auth/me/").status_code, 401)  # token revoked

    def test_duplicate_email_rejected_case_insensitively(self):
        self.register("bob@example.com")
        resp = self.client.post(
            "/api/v1/auth/register/",
            {"email": "BOB@example.com", "password": PASSWORD, "first_name": "B", "last_name": "B", "phone": "0781234567"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("email", resp.data)

    def test_weak_password_rejected_without_creating_user(self):
        resp = self.client.post(
            "/api/v1/auth/register/",
            {"email": "c@example.com", "password": "12345678", "first_name": "C", "last_name": "C", "phone": "0781234567"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("password", resp.data)
        self.assertFalse(get_user_model().objects.filter(username="c@example.com").exists())

    def test_bad_phone_rejected(self):
        resp = self.client.post(
            "/api/v1/auth/register/",
            {"email": "c@example.com", "password": PASSWORD, "first_name": "C", "last_name": "C", "phone": "abc"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("phone", resp.data)

    def test_login_does_not_reveal_whether_email_exists(self):
        self.register("dan@example.com")
        wrong_pw = self.client.post("/api/v1/auth/login/", {"email": "dan@example.com", "password": "nope"}, format="json")
        unknown = self.client.post("/api/v1/auth/login/", {"email": "ghost@example.com", "password": "nope"}, format="json")
        self.assertEqual(wrong_pw.status_code, 401)
        self.assertEqual(wrong_pw.data, unknown.data)

    def test_login_is_throttled(self):
        codes = [
            self.client.post("/api/v1/auth/login/", {"email": "x@example.com", "password": "bad"}, format="json").status_code
            for _ in range(12)
        ]
        self.assertEqual(codes[-1], 429)

    def test_student_directory_is_staff_only(self):
        client, _ = self.register("eve@example.com")
        self.assertEqual(self.client.get("/api/v1/students/").status_code, 401)
        self.assertEqual(client.get("/api/v1/students/").status_code, 403)

    def test_profile_update_cannot_change_email(self):
        client, student = self.register("fay@example.com")
        resp = client.patch("/api/v1/auth/me/", {"phone": "0789999999", "email": "evil@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200)
        student.refresh_from_db()
        self.assertEqual(student.phone, "0789999999")
        self.assertEqual(student.email, "fay@example.com")

    def test_model_enforces_case_insensitive_unique_email(self):
        Student.objects.create(first_name="A", last_name="A", email="a@x.com", phone="0781234567")
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            Student.objects.create(first_name="B", last_name="B", email="A@X.com", phone="0781234567")
