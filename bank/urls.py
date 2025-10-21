from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # customers
    path('customers/', views.customers_list, name='customers_list'),
    path('customers/<str:aadhaar_no>/', views.customer_detail, name='customer_detail'),

    # accounts
    path('accounts/', views.accounts_list, name='accounts_list'),
    path('accounts/<str:account_no>/', views.account_detail, name='account_detail'),

    # transactions
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('create-account/', views.create_account, name='create_account'),
    
    # updated: use correct view function
    path('accounts/<str:account_no>/close/', views.close_account, name='close_account'),

    path('loans/<str:loan_no>/pay/', views.pay_loan, name='pay_loan'),
    path('accounts/<str:account_no>/reconcile/', views.reconcile_account, name='reconcile_account'),

    # per-user transaction page
    path('my-transactions/', views.my_transactions, name='my_transactions'),
    path('my-transactions/perform/', views.perform_transaction, name='perform_transaction'),

    # loans
    path('loans/', views.loans_list, name='loans_list'),
    path('loans/<str:loan_no>/', views.loan_detail, name='loan_detail'),
]
