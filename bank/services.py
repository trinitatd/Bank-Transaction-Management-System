
from django.db import connection
from django.db import DatabaseError

def sp_create_account(aadhaar, account_no, initial_amount, created_by):
    try:
        with connection.cursor() as cursor:
            cursor.callproc('sp_create_account', [aadhaar, account_no, initial_amount, created_by])
            results = cursor.fetchall()  # optional, if your SP returns anything
        return {"success": True, "message": "Account created successfully", "data": results}
    except Exception as e:
        return {"success": False, "message": str(e)}
    
def sp_perform_transaction(p_from_acc, p_to_acc, p_amount, p_type, p_by):
    """Calls the stored procedure sp_perform_transaction in MySQL."""
    with connection.cursor() as cursor:
        cursor.callproc('sp_perform_transaction', [p_from_acc, p_to_acc, p_amount, p_type, p_by])
    return {'success': True, 'message': 'Transaction completed successfully!'}


def sp_close_account(p_account_no, p_transfer_to, p_by):
    """Calls the stored procedure sp_close_account in MySQL."""
    try:
        with connection.cursor() as cursor:
            cursor.callproc('sp_close_account', [p_account_no, p_transfer_to, p_by])
        return {'success': True, 'message': 'Account closed successfully!'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def sp_pay_loan(loan_no, from_account, amount, paid_by):
    """Call stored procedure sp_pay_loan in MySQL."""
    try:
        with connection.cursor() as cursor:
            cursor.callproc("sp_pay_loan", [loan_no, from_account, amount, paid_by])
        return {"success": True, "message": f"Loan {loan_no} paid successfully."}
    except Exception as e:
        return {"success": False, "message": str(e)}
    

def sp_reconcile_account(account_no, fix_flag=0):
    """
    Calls stored procedure sp_reconcile_account to verify/fix balance mismatch.
    Returns dict with account_id, db_balance, computed_balance, discrepancy.
    """
    result = {}
    try:
        with connection.cursor() as cursor:
            cursor.callproc('sp_reconcile_account', [account_no, fix_flag])
            try:
                data = cursor.fetchall()
                if data and len(data[0]) >= 4:
                    row = data[0]
                    result = {
                        'account_id': row[0],
                        'db_balance': row[1],
                        'computed_balance': row[2],
                        'discrepancy': row[3],
                    }
            except Exception:
                # some drivers need nextset to access returned SELECT
                try:
                    while cursor.nextset():
                        pass
                except Exception:
                    pass
    except DatabaseError as e:
        raise e
    return result
