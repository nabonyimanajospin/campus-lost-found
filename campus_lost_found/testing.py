"""Shared helpers for API tests."""
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from item.models import Item
from student.models import Student

PASSWORD = "S3cure-pass-phrase!"


class APIBase(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache

    def register(self, email, first="Test", last="Student", phone="0781234567"):
        resp = self.client.post(
            "/api/v1/auth/register/",
            {"email": email, "password": PASSWORD, "first_name": first, "last_name": last, "phone": phone},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {resp.data['token']}")
        return client, Student.objects.get(email=email.lower())

    def make_item(self, owner, **kwargs):
        defaults = dict(title="Black wallet", description="Leather, has ID", location="Library")
        defaults.update(kwargs)
        return Item.objects.create(created_by=owner, **defaults)
