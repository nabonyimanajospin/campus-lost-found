from campus_lost_found.testing import APIBase
from claim.forms import ClaimForm
from claim.models import Claim
from item.models import Item

MSG = "It has my student ID and a blue strap inside."


class ClaimWorkflowTests(APIBase):
    def setUp(self):
        super().setUp()
        self.owner, self.owner_s = self.register("owner@example.com", first="Olivia", phone="0780000001")
        self.cara, self.cara_s = self.register("cara@example.com", first="Cara", phone="0780000002")
        self.dan, self.dan_s = self.register("dan@example.com", first="Dan", phone="0780000003")
        self.item = self.make_item(self.owner_s, status="found")

    def claim(self, client, item=None, message=MSG):
        return client.post("/api/v1/claims/", {"item": (item or self.item).id, "message": message}, format="json")

    def test_submit_claim_sets_claimant_and_pending(self):
        resp = self.claim(self.cara)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["status"], "pending")
        self.assertEqual(resp.data["claimant"], self.cara_s.id)
        self.assertIsNone(resp.data["contact"])

    def test_cannot_claim_own_item_twice_or_returned_item_or_with_short_message(self):
        self.assertEqual(self.claim(self.owner).status_code, 400)
        self.assertEqual(self.claim(self.cara).status_code, 201)
        self.assertEqual(self.claim(self.cara).status_code, 400)
        self.assertEqual(self.claim(self.dan, message="mine").status_code, 400)
        done = self.make_item(self.owner_s, title="Done", status="returned")
        self.assertEqual(self.claim(self.dan, item=done).status_code, 400)

    def test_anonymous_cannot_claim(self):
        self.assertEqual(self.claim(self.client).status_code, 401)

    def test_status_cannot_be_set_by_client(self):
        resp = self.cara.post(
            "/api/v1/claims/", {"item": self.item.id, "message": MSG, "status": "approved"}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], "pending")

    def test_claims_are_private_to_parties(self):
        claim_id = self.claim(self.cara).data["id"]
        url = f"/api/v1/claims/{claim_id}/"
        self.assertEqual(self.cara.get(url).status_code, 200)
        self.assertEqual(self.owner.get(url).status_code, 200)
        self.assertEqual(self.dan.get(url).status_code, 404)
        self.assertEqual(self.dan.get("/api/v1/claims/").data["count"], 0)
        self.assertEqual(self.client.get(url).status_code, 401)

    def test_only_item_owner_can_approve_or_reject(self):
        claim_id = self.claim(self.cara).data["id"]
        for action in ("approve", "reject"):
            self.assertEqual(self.cara.post(f"/api/v1/claims/{claim_id}/{action}/").status_code, 403)
            self.assertEqual(self.dan.post(f"/api/v1/claims/{claim_id}/{action}/").status_code, 404)

    def test_approve_returns_item_rejects_rivals_and_reveals_contacts(self):
        cara_id = self.claim(self.cara).data["id"]
        dan_id = self.claim(self.dan).data["id"]

        resp = self.owner.post(f"/api/v1/claims/{cara_id}/approve/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["status"], "approved")
        self.assertEqual(resp.data["contact"]["email"], "cara@example.com")  # owner sees claimant

        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.Status.RETURNED)
        self.assertEqual(Claim.objects.get(pk=dan_id).status, "rejected")

        # Claimant sees the owner's contact; the rejected rival sees nothing.
        self.assertEqual(self.cara.get(f"/api/v1/claims/{cara_id}/").data["contact"]["phone"], "0780000001")
        self.assertIsNone(self.dan.get(f"/api/v1/claims/{dan_id}/").data["contact"])

        # Terminal states: no second approval, no new claims.
        self.assertEqual(self.owner.post(f"/api/v1/claims/{cara_id}/approve/").status_code, 409)
        self.assertEqual(self.owner.post(f"/api/v1/claims/{dan_id}/approve/").status_code, 409)
        self.assertEqual(self.claim(self.dan).status_code, 400)

    def test_reject_then_claimant_can_reclaim(self):
        claim_id = self.claim(self.cara).data["id"]
        self.assertEqual(self.owner.post(f"/api/v1/claims/{claim_id}/reject/").data["status"], "rejected")
        self.assertEqual(self.owner.post(f"/api/v1/claims/{claim_id}/reject/").status_code, 409)
        self.assertEqual(self.claim(self.cara).status_code, 201)  # rejected claims are not "active"

    def test_withdraw_is_claimant_only(self):
        claim_id = self.claim(self.cara).data["id"]
        self.assertEqual(self.owner.post(f"/api/v1/claims/{claim_id}/withdraw/").status_code, 403)
        resp = self.cara.post(f"/api/v1/claims/{claim_id}/withdraw/")
        self.assertEqual(resp.data["status"], "withdrawn")
        self.assertEqual(self.owner.post(f"/api/v1/claims/{claim_id}/approve/").status_code, 409)

    def test_mark_returned_rejects_pending_claims(self):
        claim_id = self.claim(self.cara).data["id"]
        self.assertEqual(self.owner.post(f"/api/v1/items/{self.item.id}/mark-returned/").status_code, 200)
        self.assertEqual(Claim.objects.get(pk=claim_id).status, "rejected")

    def test_role_and_item_filters(self):
        self.claim(self.cara)
        other = self.make_item(self.cara_s, title="Cara's bottle")
        self.claim(self.owner, item=other)
        self.assertEqual(self.owner.get("/api/v1/claims/").data["count"], 2)
        self.assertEqual(self.owner.get("/api/v1/claims/?role=owner").data["count"], 1)
        self.assertEqual(self.owner.get("/api/v1/claims/?role=claimant").data["count"], 1)
        self.assertEqual(self.owner.get(f"/api/v1/claims/?item={self.item.id}").data["count"], 1)

    def test_db_constraints_back_up_the_api(self):
        from django.db import IntegrityError, transaction

        Claim.objects.create(item=self.item, claimant=self.cara_s, message=MSG)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Claim.objects.create(item=self.item, claimant=self.cara_s, message=MSG)
        Claim.objects.filter(item=self.item).update(status="approved")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Claim.objects.create(item=self.item, claimant=self.dan_s, message=MSG, status="approved")

    def test_html_form_obeys_same_rules(self):
        form = ClaimForm({"item": self.item.id, "claimant": self.owner_s.id, "message": MSG})
        self.assertFalse(form.is_valid())
        self.assertIn("claimant", form.errors)
        self.assertNotIn("status", ClaimForm().fields)
