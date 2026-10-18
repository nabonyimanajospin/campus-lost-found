from django import forms
from .models import Claim


class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        # Status is not editable here: it only changes through claim.services.
        fields = ['item', 'claimant', 'message']
