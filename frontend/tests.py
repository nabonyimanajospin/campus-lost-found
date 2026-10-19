from django.contrib.staticfiles import finders
from django.test import TestCase


class FrontendShellTests(TestCase):
    def test_app_shell_is_served_with_mobile_viewport(self):
        resp = self.client.get("/app/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="viewport"')
        self.assertContains(resp, "frontend/app.js")

    def test_static_assets_exist(self):
        for name in ("frontend/app.js", "frontend/styles.css"):
            self.assertIsNotNone(finders.find(name), name)
