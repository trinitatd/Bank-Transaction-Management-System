from django.shortcuts import render
from .models import Customer

def home(request):
    customers = Customer.objects.all()  # optional: just to test
    return render(request, 'bank/home.html', {'customers': customers})
