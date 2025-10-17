from django.shortcuts import render, redirect

from .models import Account, Transactions, Loans, Customer

def home(request):
    if request.method == "POST":
        # basic mock login for now
        username = request.POST.get("username")
        password = request.POST.get("password")

        if username == "admin" and password == "1234":
            return redirect('dashboard')
        else:
            return render(request, 'bank/home.html', {"error": "Invalid credentials"})
    return render(request, 'bank/home.html')


from .models import Account, Transactions, Loans, Customer

def dashboard(request):
    customer = Customer.objects.get(aadhaar_no=request.user.aadhaar_no)
    account = Account.objects.get(account_no=customer.account_no)
    transactions = Transactions.objects.filter(account_no=account.account_no).order_by('-date')[:5]
    loans = Loans.objects.filter(branch_number=account.branch_number)
    
    return render(request, 'dashboard.html', {
        'account': account,
        'transactions': transactions,
        'loans': loans
    })
