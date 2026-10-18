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
