from django import forms
from .models import Item


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['title', 'description', 'location', 'category', 'image', 'status', 'created_by']

    def clean_status(self):
        status = self.cleaned_data['status']
        if status == Item.Status.RETURNED and not self.instance.is_returned:
            raise forms.ValidationError("Items are marked as returned by approving a claim.")
        return status
