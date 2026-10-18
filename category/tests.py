from django.contrib.auth import get_user_model

from campus_lost_found.testing import APIBase
from category.models import Category


class CategoryApiTests(APIBase):
    def test_public_read_but_only_staff_write(self):
        Category.objects.create(name="Keys")
        self.assertEqual(self.client.get("/api/v1/categories/").status_code, 200)

        student_client, _ = self.register("s@example.com")
        self.assertEqual(student_client.post("/api/v1/categories/", {"name": "Books"}, format="json").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/categories/", {"name": "Books"}, format="json").status_code, 401)

        admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.post("/api/v1/categories/", {"name": "Books"}, format="json").status_code, 201)

    def test_duplicate_names_rejected_case_insensitively(self):
        Category.objects.create(name="Keys")
        admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client.force_authenticate(admin)
        resp = self.client.post("/api/v1/categories/", {"name": " keys "}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_html_form_rejects_duplicates_instead_of_crashing(self):
        Category.objects.create(name="Keys")
        resp = self.client.post("/categories/add/", {"name": "KEYS"})
        self.assertEqual(resp.status_code, 200)  # form re-rendered with an error
        self.assertEqual(Category.objects.count(), 1)
