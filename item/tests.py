from campus_lost_found.testing import APIBase
from category.models import Category
from item.models import Item


class ItemApiTests(APIBase):
    def test_anonymous_can_browse_but_not_post(self):
        client, owner = self.register("owner@example.com")
        self.make_item(owner)
        resp = self.client.get("/api/v1/items/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        # No contact details leak through item listings.
        self.assertNotIn("email", str(resp.data))
        self.assertEqual(self.client.post("/api/v1/items/", {}, format="json").status_code, 401)

    def test_create_sets_owner_from_token_and_ignores_spoofing(self):
        alice, alice_student = self.register("alice@example.com")
        _, bob_student = self.register("bob@example.com")
        resp = alice.post(
            "/api/v1/items/",
            {"title": "Keys", "description": "Blue keyring", "location": "Gym", "status": "found", "created_by": bob_student.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Item.objects.get().created_by, alice_student)

    def test_cannot_create_item_directly_as_returned(self):
        alice, _ = self.register("alice@example.com")
        resp = alice.post(
            "/api/v1/items/",
            {"title": "Keys", "description": "d", "location": "l", "status": "returned"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_only_owner_can_edit_delete_or_close(self):
        alice, alice_student = self.register("alice@example.com")
        bob, _ = self.register("bob@example.com")
        item = self.make_item(alice_student)
        url = f"/api/v1/items/{item.id}/"
        self.assertEqual(bob.patch(url, {"title": "Hacked"}, format="json").status_code, 403)
        self.assertEqual(bob.delete(url).status_code, 403)
        self.assertEqual(bob.post(url + "mark-returned/").status_code, 403)
        self.assertEqual(alice.patch(url, {"title": "Brown wallet"}, format="json").status_code, 200)

    def test_returned_items_are_frozen(self):
        alice, alice_student = self.register("alice@example.com")
        item = self.make_item(alice_student)
        url = f"/api/v1/items/{item.id}/"
        self.assertEqual(alice.post(url + "mark-returned/").status_code, 200)
        item.refresh_from_db()
        self.assertIsNotNone(item.returned_at)
        self.assertEqual(alice.patch(url, {"title": "x" * 5}, format="json").status_code, 400)
        self.assertEqual(alice.delete(url).status_code, 400)
        self.assertEqual(alice.post(url + "mark-returned/").status_code, 409)

    def test_filters_and_search(self):
        _, owner = self.register("owner@example.com")
        keys = Category.objects.create(name="Keys")
        self.make_item(owner, title="Car keys", category=keys, status="found")
        self.make_item(owner, title="Umbrella", description="red")
        self.assertEqual(self.client.get("/api/v1/items/?status=found").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/v1/items/?category={keys.id}").data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/items/?search=umbrella").data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/items/?mine=true").data["count"], 0)  # anonymous -> nothing

    def test_mine_filter(self):
        alice, alice_student = self.register("alice@example.com")
        _, bob_student = self.register("bob@example.com")
        self.make_item(alice_student)
        self.make_item(bob_student)
        self.assertEqual(alice.get("/api/v1/items/?mine=true").data["count"], 1)

    def test_model_keeps_returned_at_consistent(self):
        _, owner = self.register("owner@example.com")
        item = self.make_item(owner)
        self.assertIsNone(item.returned_at)
        item.status = Item.Status.RETURNED
        item.save()
        self.assertIsNotNone(item.returned_at)
        item.status = Item.Status.LOST
        item.save()
        self.assertIsNone(item.returned_at)


import io
import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

TMP_MEDIA = tempfile.mkdtemp(prefix="clf-media-")


def make_image(fmt="PNG", name="photo.png", size=(20, 20)):
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, fmt)
    content_type = {"PNG": "image/png", "JPEG": "image/jpeg", "GIF": "image/gif"}[fmt]
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ItemImageTests(APIBase):
    payload = {"title": "Wallet", "description": "Brown", "location": "Gym", "status": "lost"}

    def post_item(self, client, image=None, **extra):
        data = dict(self.payload, **extra)
        if image is not None:
            data["image"] = image
        return client.post("/api/v1/items/", data, format="multipart")

    def test_upload_stores_image_under_random_name(self):
        client, _ = self.register("a@example.com")
        resp = self.post_item(client, make_image(name="../../evil name.PNG"))
        self.assertEqual(resp.status_code, 201, resp.content)
        item = Item.objects.get()
        self.assertRegex(item.image.name, r"^items/[0-9a-f]{32}\.png$")
        self.assertTrue(os.path.exists(item.image.path))
        self.assertTrue(resp.data["image"].startswith("http"))

    def test_image_is_optional(self):
        client, _ = self.register("a@example.com")
        resp = self.post_item(client)
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.data["image"])

    def test_rejects_non_images_and_disallowed_formats(self):
        client, _ = self.register("a@example.com")
        fake = SimpleUploadedFile("shell.png", b"<script>alert(1)</script>", content_type="image/png")
        self.assertEqual(self.post_item(client, fake).status_code, 400)
        gif = make_image("GIF", "a.gif")
        resp = self.post_item(client, gif)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("image", resp.data)
        self.assertEqual(Item.objects.count(), 0)

    def test_dangerous_extensions_never_reach_disk(self):
        client, _ = self.register("a@example.com")
        # Rejected at the API...
        self.assertEqual(self.post_item(client, make_image(name="x.html")).status_code, 400)
        # ...and the storage path itself also refuses to keep unknown extensions.
        from item.models import item_image_path

        self.assertTrue(item_image_path(None, "x.html").endswith(".jpg"))
        self.assertTrue(item_image_path(None, "x.PNG").endswith(".png"))

    @override_settings(IMAGE_MAX_UPLOAD_BYTES=200)
    def test_rejects_oversized_images(self):
        client, _ = self.register("a@example.com")
        resp = self.post_item(client, make_image(size=(200, 200)))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("too large", str(resp.data["image"]))

    def test_files_are_cleaned_up_on_replace_and_delete(self):
        client, _ = self.register("a@example.com")
        resp = self.post_item(client, make_image())
        item = Item.objects.get()
        first = item.image.path
        url = f"/api/v1/items/{item.id}/"
        self.assertEqual(client.patch(url, {"image": make_image(name="b.png")}, format="multipart").status_code, 200)
        self.assertFalse(os.path.exists(first))  # replaced photo removed
        item.refresh_from_db()
        second = item.image.path
        self.assertTrue(os.path.exists(second))
        self.assertEqual(client.delete(url).status_code, 204)
        self.assertFalse(os.path.exists(second))  # deleted with the item

    def test_only_owner_can_change_photo(self):
        alice, _ = self.register("alice@example.com")
        bob, _ = self.register("bob@example.com")
        self.post_item(alice, make_image())
        item = Item.objects.get()
        resp = bob.patch(f"/api/v1/items/{item.id}/", {"image": make_image(name="b.png")}, format="multipart")
        self.assertEqual(resp.status_code, 403)
