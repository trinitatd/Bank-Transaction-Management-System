from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Sum
from django.db import connection
from django.db.utils import DatabaseError
from django.conf import settings
from django.utils import timezone
import datetime
from django.contrib.auth.hashers import make_password

from .services import sp_create_account
from .services import sp_perform_transaction
from .services import sp_close_account
from .services import sp_pay_loan
from .services import sp_reconcile_account

from .models import Customer, Account, Transaction, Loans, CustomerLoans
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login


def login_view(request):
    """Login page: supports Django User authentication."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return redirect('login')

        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)

            # Link Customer profile
            customer = Customer.objects.filter(user=user).first()
            if not customer:
                # Create minimal Customer if missing
                customer = Customer(aadhaar_no=username, name=username, phone='', user=user)
                customer.save()

            request.session['aadhaar_no'] = customer.aadhaar_no
            messages.success(request, f'Welcome {customer.name}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials.')
            return redirect('login')

    return render(request, 'bank/login.html')

def logout_view(request):
    request.session.pop('aadhaar_no', None)
    try:
        logout(request)
    except Exception:
        pass
    messages.info(request, 'You have been logged out.')
    return redirect('login')


def dashboard(request):
    aadhaar_no = request.session.get('aadhaar_no')
    if not aadhaar_no:
        return redirect('login')
    customer = get_object_or_404(Customer, aadhaar_no=aadhaar_no)

    # resolve phone: prefer Customer.phone, else fallback to legacy `customer` table
    customer_phone = customer.phone if getattr(customer, 'phone', None) else None
    if not customer_phone:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT phone FROM customer WHERE aadhaar_no=%s LIMIT 1", [aadhaar_no])
                row = cursor.fetchone()
                if row and row[0]:
                    customer_phone = row[0]
        except Exception:
            customer_phone = None

    # helper functions to fetch data from either bank app tables or legacy tables
    def fetch_accounts(aad):
        # gather both modern ORM accounts and legacy mapped accounts
        out = []
        try:
            accounts_qs = Account.objects.filter(customer__aadhaar_no=aad)
            for a in accounts_qs:
                out.append({'account_no': a.account_no, 'balance': a.balance})
        except Exception:
            pass

        # always try to include legacy accounts too (avoid duplicates)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT ca.account_no, a.balance FROM customer_account ca JOIN account a ON ca.account_no = a.account_no WHERE ca.aadhaar_no = %s",
                    [aad],
                )
                for r in cursor.fetchall():
                    if r and r[0] and not any(x['account_no'] == r[0] for x in out):
                        out.append({'account_no': r[0], 'balance': r[1]})
        except Exception:
            pass

        return out

    def fetch_transactions(aad):
        # first try bank.Transaction via bank_account mapping
        txns = []
        try:
            tx_qs = Transaction.objects.filter(account__customer__aadhaar_no=aad).order_by('-date')[:20]
            if tx_qs.exists():
                for t in tx_qs:
                    txns.append({'date': t.date, 'account_no': t.account.account_no, 'transaction_type': t.transaction_type, 'amount': t.amount})
                return txns
        except Exception:
            pass

        # fallback to legacy transactions table
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT transaction_id, account_no, amount, type, date FROM transactions WHERE account_no IN (SELECT account_no FROM customer_account WHERE aadhaar_no=%s) ORDER BY date DESC LIMIT 20",
                [aad],
            )
            rows = cursor.fetchall()
            for r in rows:
                txns.append({'date': r[4], 'account_no': r[1], 'transaction_type': r[3], 'amount': r[2]})
        return txns

    def fetch_loans(aad):
        # prefer bank.CustomerLoans model
        cls = CustomerLoans.objects.filter(customer__aadhaar_no=aad).select_related('loan')
        if cls.exists():
            return [{'loan_no': c.loan.loan_no, 'type': c.loan.type, 'amount': c.loan.amount, 'role': c.role} for c in cls]

        # fallback to legacy customer_loans or loans table
        loans_out = []
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT l.loan_no, l.type, l.amount, cl.role FROM customer_loans cl JOIN loans l ON cl.loan_no = l.loan_no WHERE cl.aadhaar_no = %s",
                [aad],
            )
            rows = cursor.fetchall()
            for r in rows:
                loans_out.append({'loan_no': r[0], 'type': r[1], 'amount': r[2], 'role': r[3]})
        return loans_out

    accounts = fetch_accounts(aadhaar_no)
    total_balance = sum([float(a['balance']) for a in accounts]) if accounts else 0

    recent_transactions = fetch_transactions(aadhaar_no)
    customer_loans = fetch_loans(aadhaar_no)

    context = {
        'customer': customer,
        'accounts': accounts,
        'total_balance': total_balance,
        'recent_transactions': recent_transactions,
        'customer_loans': customer_loans,
        'customer_phone': customer_phone,
    }
    return render(request, 'bank/dashboard.html', context)


def customers_list(request):
    customers = Customer.objects.all().order_by('name')
    return render(request, 'bank/customers.html', {'customers': customers})


def customer_detail(request, aadhaar_no):
    customer = get_object_or_404(Customer, aadhaar_no=aadhaar_no)
    # Collect ORM accounts
    accounts = []
    try:
        for a in Account.objects.filter(customer=customer):
            accounts.append({'account_no': a.account_no, 'balance': a.balance, 'object': a})
    except Exception:
        pass

    # Add legacy mapped accounts
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ca.account_no, a.balance FROM customer_account ca JOIN account a ON ca.account_no = a.account_no WHERE ca.aadhaar_no=%s", [aadhaar_no])
            for r in cursor.fetchall():
                if r and r[0] and not any(x['account_no'] == r[0] for x in accounts):
                    accounts.append({'account_no': r[0], 'balance': r[1]})
    except Exception:
        pass

    # Collect loans: prefer ORM CustomerLoans
    loans = []
    try:
        for cl in CustomerLoans.objects.filter(customer=customer).select_related('loan'):
            loans.append({'loan_no': cl.loan.loan_no, 'type': cl.loan.type, 'amount': cl.loan.amount, 'role': cl.role, 'object': cl})
    except Exception:
        pass

    # Fallback to legacy customer_loans
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT cl.loan_no, l.type, l.amount, cl.role FROM customer_loans cl JOIN loans l ON cl.loan_no = l.loan_no WHERE cl.aadhaar_no=%s", [aadhaar_no])
            for r in cursor.fetchall():
                if r and r[0] and not any(x['loan_no'] == r[0] for x in loans):
                    loans.append({'loan_no': r[0], 'type': r[1], 'amount': r[2], 'role': r[3]})
    except Exception:
        pass

    return render(request, 'bank/customer_detail.html', {'customer': customer, 'accounts': accounts, 'loans': loans})


def accounts_list(request):
    accounts = Account.objects.select_related('customer').all().order_by('-balance')
    return render(request, 'bank/accounts.html', {'accounts': accounts})


def account_detail(request, account_no):
    account = get_object_or_404(Account, account_no=account_no)
    transactions = Transaction.objects.filter(account=account).order_by('-date')
    return render(request, 'bank/account_detail.html', {'account': account, 'transactions': transactions})


def transactions_list(request):
    # New clean implementation: pull ORM txns and legacy txns, normalize and render
    transactions_out = []
    try:
        # ORM transactions
        orm_qs = Transaction.objects.select_related('account', 'account__customer').order_by('-date')[:500]
        for t in orm_qs:
            transactions_out.append({
                'source': 'orm',
                'date': t.date,
                'account_no': t.account.account_no,
                'customer_name': getattr(t.account.customer, 'name', '-') if getattr(t, 'account', None) else '-',
                'transaction_type': t.transaction_type,
                'amount': t.amount,
            })

        # Legacy transactions
        with connection.cursor() as cursor:
            cursor.execute("SELECT transaction_id, account_no, amount, type, date FROM transactions ORDER BY date DESC LIMIT 500")
            rows = cursor.fetchall()
            for r in rows:
                transactions_out.append({
                    'source': 'legacy',
                    'date': r[4],
                    'account_no': r[1],
                    'customer_name': None,
                    'transaction_type': r[3],
                    'amount': r[2],
                })

        # Attempt to resolve customer_name for legacy rows (batch lookup)
        legacy_accs = [x['account_no'] for x in transactions_out if x['source'] == 'legacy']
        legacy_accs = list(dict.fromkeys(legacy_accs))[:200]  # unique, limit
        if legacy_accs:
            # build mapping account_no -> customer name
            mapping = {}
            with connection.cursor() as cursor:
                cursor.execute("SELECT ca.account_no, c.name FROM customer_account ca JOIN customer c ON ca.aadhaar_no = c.aadhaar_no WHERE ca.account_no IN (%s)" % ",".join(["%s"]*len(legacy_accs)), legacy_accs)
                for row in cursor.fetchall():
                    mapping[row[0]] = row[1]
            for x in transactions_out:
                if x['source'] == 'legacy' and x['account_no'] in mapping:
                    x['customer_name'] = mapping.get(x['account_no'])

        # Normalize and prepare display fields
        tz = timezone.get_current_timezone()
        def to_dt(val):
            if val is None:
                return timezone.make_aware(datetime.datetime(1970,1,1), tz)
            if isinstance(val, datetime.datetime):
                return timezone.localtime(val, tz) if timezone.is_aware(val) else timezone.make_aware(val, tz)
            if isinstance(val, datetime.date):
                dt = datetime.datetime.combine(val, datetime.time.min)
                return timezone.make_aware(dt, tz)
            # try parse
            try:
                parsed = datetime.datetime.fromisoformat(str(val))
                return timezone.localtime(parsed, tz) if timezone.is_aware(parsed) else timezone.make_aware(parsed, tz)
            except Exception:
                try:
                    parsed = datetime.datetime.strptime(str(val), '%Y-%m-%d %H:%M:%S')
                    return timezone.make_aware(parsed, tz)
                except Exception:
                    return timezone.make_aware(datetime.datetime(1970,1,1), tz)

        for x in transactions_out:
            x['_sort_dt'] = to_dt(x.get('date'))
            x['date_display'] = x['_sort_dt'].strftime('%Y-%m-%d %H:%M:%S')
            if not x.get('customer_name'):
                x['customer_name'] = '-'
            try:
                x['amount_display'] = f"{float(x.get('amount') or 0):.2f}"
            except Exception:
                x['amount_display'] = str(x.get('amount') or '')

        transactions_out = sorted(transactions_out, key=lambda r: r['_sort_dt'], reverse=True)[:200]
        for x in transactions_out:
            x.pop('_sort_dt', None)

    except Exception as e:
        # Log error and show friendly message
        import traceback as _tb
        tb = _tb.format_exc()
        if settings.DEBUG:
            return render(request, 'bank/transactions.html', {'transactions': [], 'error': str(e), 'error_details': tb})
        return render(request, 'bank/transactions.html', {'transactions': [], 'error': 'Unable to load transactions. Check server logs.'})

    return render(request, 'bank/transactions.html', {'transactions': transactions_out})

def create_account(request):
    """Create a new account using stored procedure and Django User auth."""
    message = None
    error = None

    if request.method == 'POST':
        aadhaar = request.POST.get('aadhaar_no', '').strip()      # matches form's name="aadhaar_no"
        account_no = request.POST.get('username', '').strip()     # matches form's name="username"
        initial = request.POST.get('initial', '0').strip()        # form doesn't have initial, defaults to 0
        password = request.POST.get('password', '').strip()
        created_by = request.POST.get('created_by', 'System').strip()

        # Validate Aadhaar and account_no inputs before proceeding
        if not aadhaar:
            error = "Aadhaar number is required."
        elif not account_no:
            error = "Username (Account number) is required."
        else:
            try:
                # Call your stored procedure (make sure it handles duplicate checks)
                sp_create_account(aadhaar, account_no, float(initial), created_by)

                # Create or get Customer based on Aadhaar number (likely your PK)
                customer, created = Customer.objects.get_or_create(aadhaar_no=aadhaar)
                if password:
                    # Create Django User if it doesn't exist
                    user, user_created = User.objects.get_or_create(username=account_no)
                    if user_created:
                        user.set_password(password)
                        user.save()
                    # Link the Customer to this User
                    customer.user = user
                    customer.save()

                message = f"Account {account_no} created successfully!"
            except Exception as e:
                error = f"Error: {str(e)}"

    return render(request, 'bank/create_account.html', {'message': message, 'error': error})

def close_account(request, account_no):
    """Close an account: GET shows form, POST calls sp_close_account."""
    message = None
    error = None

    # Get all other open accounts for transfer options
    accounts = Account.objects.filter(is_closed=False).exclude(account_no=account_no).values_list('account_no', flat=True)

    if request.method == 'POST':
        transfer_to = request.POST.get('transfer_to')
        closed_by = request.user.username if request.user.is_authenticated else 'admin'

        result = sp_close_account(account_no, transfer_to, closed_by)

        if result['success']:
            message = result['message']
        else:
            error = result['message']

    return render(request, 'bank/close_account.html', {
        'account_no': account_no,
        'accounts': accounts,
        'message': message,
        'error': error
    })

    # check ownership (ORM or legacy mapping)
    def is_owned(a_no, aad):
        try:
            if Account.objects.filter(account_no=a_no, customer__aadhaar_no=aad).exists():
                return True
        except Exception:
            pass
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM customer_account WHERE aadhaar_no=%s AND account_no=%s LIMIT 1", [aad, a_no])
                return bool(cursor.fetchone())
        except Exception:
            return False

    if not is_owned(account_no, aadhaar_no):
        messages.error(request, 'You do not own this account.')
        return redirect('dashboard')

    if request.method == 'POST':
        transfer_to = request.POST.get('transfer_to') or ''
        try:
            with connection.cursor() as cursor:
                cursor.callproc('sp_close_account', [account_no, transfer_to, aadhaar_no])
                try:
                    while cursor.nextset():
                        pass
                except Exception:
                    pass
            messages.success(request, 'Account closed successfully.')
            return redirect('dashboard')
        except DatabaseError as db_err:
            messages.error(request, f'Error closing account: {db_err}')
            return redirect('dashboard')

    # GET: show confirmation and possible transfer targets (other accounts of owner)
    accounts = []
    try:
        for a in Account.objects.filter(customer__aadhaar_no=aadhaar_no):
            if a.account_no != account_no:
                accounts.append(a.account_no)
    except Exception:
        pass

    # include legacy accounts
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ca.account_no FROM customer_account ca WHERE ca.aadhaar_no=%s", [aadhaar_no])
            for r in cursor.fetchall():
                if r and r[0] and r[0] != account_no and r[0] not in accounts:
                    accounts.append(r[0])
    except Exception:
        pass

    return render(request, 'bank/close_account.html', {'account_no': account_no, 'accounts': accounts})


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


def reconcile_account(request, account_no):
    """Run reconciliation for an account. GET shows current discrepancy; POST with fix=1 will attempt to fix the account balance."""
    aadhaar_no = request.session.get('aadhaar_no')
    if not aadhaar_no:
        return redirect('login')

    # Verify ownership
    owned = Account.objects.filter(account_no=account_no, customer__aadhaar_no=aadhaar_no).exists()
    if not owned:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM customer_account WHERE aadhaar_no=%s AND account_no=%s LIMIT 1",
                [aadhaar_no, account_no]
            )
            owned = bool(cursor.fetchone())

    if not owned:
        messages.error(request, 'You do not own this account.')
        return redirect('dashboard')

    result = None
    if request.method == 'POST':
        fix_flag = 1 if request.POST.get('fix') == '1' else 0
        try:
            result = reconcile_account_service(account_no, fix_flag)

            # fetch last audit if available
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT old_balance, new_balance, created_at 
                    FROM reconciliation_audit 
                    WHERE account_id = (SELECT id FROM bank_account WHERE account_no=%s LIMIT 1)
                    ORDER BY created_at DESC LIMIT 1
                """, [account_no])
                audit = cursor.fetchone()
                if audit:
                    result['audit'] = {
                        'old_balance': audit[0],
                        'new_balance': audit[1],
                        'created_at': audit[2]
                    }

            messages.success(request, 'Reconciliation performed successfully.')
        except DatabaseError as db_err:
            messages.error(request, f'Reconciliation failed: {db_err}')
            return redirect('dashboard')

    return render(request, 'bank/reconcile_account.html', {'account_no': account_no, 'result': result})

def loans_list(request):
    loans = Loans.objects.select_related('branch_number').all().order_by('-amount')
    return render(request, 'bank/loans.html', {'loans': loans})


def loan_detail(request, loan_no):
    loan = get_object_or_404(Loans, loan_no=loan_no)
    customers = CustomerLoans.objects.filter(loan=loan).select_related('customer')
    return render(request, 'bank/loan_detail.html', {'loan': loan, 'customers': customers})


def my_transactions(request):
    """Show transactions for the logged-in customer and provide deposit/withdraw form."""
    aadhaar_no = request.session.get('aadhaar_no')
    if not aadhaar_no:
        return redirect('login')
    customer = get_object_or_404(Customer, aadhaar_no=aadhaar_no)

    # gather accounts: include ORM Account objects and legacy customer_account/account rows (deduplicated)
    accounts = []
    try:
        accounts_qs = Account.objects.filter(customer=customer)
        for a in accounts_qs:
            # convert ORM object to a dict for consistent template handling
            accounts.append({'account_no': a.account_no, 'balance': a.balance, 'object': a})
    except Exception:
        pass

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT ca.account_no, a.balance FROM customer_account ca JOIN account a ON ca.account_no = a.account_no WHERE ca.aadhaar_no = %s",
                [customer.aadhaar_no],
            )
            for r in cursor.fetchall():
                if r and r[0] and not any(x['account_no'] == r[0] for x in accounts):
                    accounts.append({'account_no': r[0], 'balance': r[1]})
    except Exception:
        pass

    # get recent transactions across customer's accounts (ORM first, else legacy)
    try:
        tx_qs = Transaction.objects.select_related('account').filter(account__customer=customer).order_by('-date')[:200]
        if tx_qs.exists():
            txns = list(tx_qs)
        else:
            # fallback to legacy transactions
            txns = []
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT t.date, t.account_no, t.amount, t.type FROM transactions t WHERE t.account_no IN (SELECT account_no FROM customer_account WHERE aadhaar_no=%s) ORDER BY t.date DESC LIMIT 200",
                    [customer.aadhaar_no],
                )
                for r in cursor.fetchall():
                    txns.append({'date': r[0], 'account_no': r[1], 'transaction_type': r[3], 'amount': r[2]})
    except Exception:
        txns = []

    return render(request, 'bank/transactions_user.html', {'customer': customer, 'accounts': accounts, 'transactions': txns})


@require_http_methods(['POST'])
def perform_transaction(request):
    """Handle deposit/withdraw/transfer actions by calling the stored procedure sp_perform_transaction.

    Expected POST fields:
      - from_account (optional for deposit)
      - to_account (optional for withdraw)
      - amount
      - type (DEPOSIT, WITHDRAW, TRANSFER)
    """
    aadhaar_no = request.session.get('aadhaar_no')
    if not aadhaar_no:
        return redirect('login')

    p_from = request.POST.get('from_account') or None
    p_to = request.POST.get('to_account') or None
    p_amount = request.POST.get('amount')
    p_type = request.POST.get('type')

    # basic validation
    try:
        amount = float(p_amount)
    except Exception:
        messages.error(request, 'Invalid amount provided.')
        return redirect('my_transactions')

    if amount <= 0:
        messages.error(request, 'Amount must be greater than zero.')
        return redirect('my_transactions')

    if p_type not in ('DEPOSIT', 'WITHDRAW', 'TRANSFER'):
        messages.error(request, 'Invalid transaction type.')
        return redirect('my_transactions')

    # Normalize account inputs
    if isinstance(p_from, str):
        p_from = p_from.strip() or None
    if isinstance(p_to, str):
        p_to = p_to.strip() or None

    def is_owned_by(a_no, aad):
        """Return True if account number a_no belongs to aadhaar aad via ORM or legacy mapping."""
        if not a_no:
            return False
        try:
            # ORM check
            if Account.objects.filter(account_no=a_no, customer__aadhaar_no=aad).exists():
                return True
        except Exception:
            pass
        try:
            # legacy mapping check
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM customer_account WHERE aadhaar_no=%s AND account_no=%s LIMIT 1", [aad, a_no])
                if cursor.fetchone():
                    return True
        except Exception:
            pass
        return False

    # Ownership checks
    if p_type in ('WITHDRAW', 'TRANSFER'):
        if not p_from or not is_owned_by(p_from, aadhaar_no):
            messages.error(request, 'You can only withdraw from your own account.')
            return redirect('my_transactions')

    if p_type == 'DEPOSIT':
        if not p_to or not is_owned_by(p_to, aadhaar_no):
            messages.error(request, 'You can only deposit into your own account.')
            return redirect('my_transactions')

    if p_type == 'TRANSFER':
        # require both from and to to be owned by the same customer
        if not p_to or not is_owned_by(p_to, aadhaar_no):
            messages.error(request, 'You can only transfer between your own accounts.')
            return redirect('my_transactions')
        if p_from == p_to:
            messages.error(request, 'From and To account cannot be the same.')
            return redirect('my_transactions')

    # Call stored procedure using DB connection
    try:
        with connection.cursor() as cursor:
            # CALL sp_perform_transaction(IN p_from_account, IN p_to_account, IN p_amount, IN p_type, IN p_txn_by)
            cursor.callproc('sp_perform_transaction', [p_from, p_to, amount, p_type, aadhaar_no])
            # Some MySQL drivers require fetching results or nextset to finish
            try:
                # consume any result sets to avoid warnings
                while cursor.nextset():
                    pass
            except Exception:
                pass
        messages.success(request, f'{p_type} of {amount:.2f} processed successfully.')
    except Exception as e:
        # show the database error message if available
        msg = str(e)
        messages.error(request, f'Transaction failed: {msg}')

    return redirect('my_transactions')
