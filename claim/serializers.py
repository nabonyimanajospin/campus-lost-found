from rest_framework import serializers

from item.models import Item

from .models import Claim


def _contact(student):
    return {"name": student.full_name, "email": student.email, "phone": student.phone}


class ClaimSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source="item.title", read_only=True)
    claimant_name = serializers.CharField(source="claimant.full_name", read_only=True)
    contact = serializers.SerializerMethodField(
        help_text="Revealed to both sides only once the claim is approved."
    )

    class Meta:
        model = Claim
        fields = [
            "id",
            "item",
            "item_title",
            "claimant",
            "claimant_name",
            "message",
            "status",
            "contact",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id", "claimant", "status", "created_at", "updated_at", "resolved_at",
        ]

    def get_contact(self, claim):
        request = self.context.get("request")
        if request is None or claim.status != Claim.Status.APPROVED:
            return None
        user = request.user
        owner = claim.item.created_by
        if user.is_staff or owner.user_id == user.id:
            return _contact(claim.claimant)
        if claim.claimant.user_id == user.id:
            return _contact(owner)
        return None

    def validate_message(self, message):
        message = message.strip()
        if len(message) < 10:
            raise serializers.ValidationError(
                "Describe the item in at least 10 characters so the owner can verify your claim."
            )
        return message

    def validate_item(self, item):
        if item.is_returned:
            raise serializers.ValidationError("This item has already been returned.")
        return item

    def validate(self, attrs):
        student = self.context["request"].user.student
        item = attrs["item"]
        if item.created_by_id == student.id:
            raise serializers.ValidationError({"item": "You cannot claim an item you posted."})
        if Claim.objects.filter(
            item=item, claimant=student, status__in=Claim.ACTIVE_STATUSES
        ).exists():
            raise serializers.ValidationError({"item": "You already have an active claim on this item."})
        return attrs
