def pay_loan(request, loan_no):
    """Pay loan: GET shows a form to choose from-account and amount (default to remaining), POST calls sp_pay_loan."""
    aadhaar_no = request.session.get('aadhaar_no')
    if not aadhaar_no:
        return redirect('login')

    # Ownership: ensure the loan is associated with this customer (legacy or ORM)
    owned = False
    try:
        # ORM check via CustomerLoans
        if CustomerLoans.objects.filter(loan__loan_no=loan_no, customer__aadhaar_no=aadhaar_no).exists():
            owned = True
    except Exception:
        pass
    if not owned:
        # fallback to legacy mapping
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM customer_loans WHERE aadhaar_no=%s AND loan_no=%s LIMIT 1", [aadhaar_no, loan_no])
                if cursor.fetchone():
                    owned = True
        except Exception:
            owned = False

    if not owned:
        messages.error(request, 'You do not have this loan.')
        return redirect('dashboard')

    # Determine outstanding amount (attempt ORM then legacy)
    outstanding = None
    try:
        ln = Loans.objects.filter(loan_no=loan_no).first()
        if ln:
            outstanding = ln.amount
    except Exception:
        pass
    if outstanding is None:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT amount FROM loans WHERE loan_no=%s LIMIT 1", [loan_no])
                r = cursor.fetchone()
                if r:
                    outstanding = r[0]
        except Exception:
            outstanding = None

    # gather customer's accounts to choose withdrawal account
    accounts = []
    try:
        for a in Account.objects.filter(customer__aadhaar_no=aadhaar_no):
            accounts.append(a.account_no)
    except Exception:
        pass
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT account_no FROM customer_account WHERE aadhaar_no=%s", [aadhaar_no])
            for r in cursor.fetchall():
                if r and r[0] and r[0] not in accounts:
                    accounts.append(r[0])
    except Exception:
        pass

    if request.method == 'POST':
        from_account = request.POST.get('from_account')
        amount = request.POST.get('amount')
        if not from_account or not amount:
            messages.error(request, 'Please provide source account and amount.')
            return redirect('pay_loan', loan_no=loan_no)
        try:
            amt = float(amount)
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('pay_loan', loan_no=loan_no)

        try:
            with connection.cursor() as cursor:
                cursor.callproc('sp_pay_loan', [loan_no, from_account, amt, aadhaar_no])
                try:
                    while cursor.nextset():
                        pass
                except Exception:
                    pass
            messages.success(request, f'Payment of ₹{amt:.2f} applied to loan {loan_no}.')
            return redirect('dashboard')
        except DatabaseError as db_err:
            messages.error(request, f'Loan payment failed: {db_err}')
            return redirect('pay_loan', loan_no=loan_no)

    return render(request, 'bank/pay_loan.html', {'loan_no': loan_no, 'outstanding': outstanding, 'accounts': accounts})
