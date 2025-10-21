from django.db import connection, transaction
from typing import Optional, Sequence, Any


def call_proc(proc_name: str, params: Optional[Sequence[Any]] = None, atomic: bool = True):
    """Call a stored procedure and return rows if any.

    - proc_name: procedure name (no CALL)
    - params: sequence of parameters (use Python None for SQL NULL)
    - atomic: wrap call in transaction.atomic()
    """
    params = params or ()

    def _call():
        with connection.cursor() as cursor:
            placeholders = ", ".join(["%s"] * len(params)) if params else ""
            sql = f"CALL {proc_name}({placeholders})" if placeholders else f"CALL {proc_name}()"
            cursor.execute(sql, params)
            try:
                return cursor.fetchall()
            except Exception:
                return None

    if atomic:
        with transaction.atomic():
            return _call()
    return _call()


def execute_sql(sql: str, params: Optional[Sequence[Any]] = None):
    """Execute arbitrary SQL and return fetchall() when available."""
    params = params or ()
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        try:
            return cursor.fetchall()
        except Exception:
            return None
