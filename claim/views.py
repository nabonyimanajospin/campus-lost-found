from django.shortcuts import render, redirect

from .models import Claim
from .forms import ClaimForm


def claim_list(request):
    claims = Claim.objects.all()
    return render(request, 'claim/claim_list.html', {'claims': claims})


def claim_create(request):
    if request.method == 'POST':
        form = ClaimForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('claim_list')
    else:
        form = ClaimForm()

    return render(request, 'claim/claim_form.html', {'form': form})
