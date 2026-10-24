"""Audit: har request ka record (requests_logs) aur alerts. Saari queries parameterized."""
import json

from database import execute


def write_log(user: dict, request_text: str, action: str, decision: str,
              reason: str = "", rule: str = "", params: dict | None = None,
              old_value=None, new_value=None):
    return execute(
        "INSERT INTO requests_logs (user_id, role, request_text, action, params, decision, reason, rule, old_value, new_value) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (user["user_id"], user["role"], request_text, action,
         json.dumps(params or {}, default=str), decision, reason, rule,
         None if old_value is None else str(old_value),
         None if new_value is None else str(new_value)),
    )


def write_alert(user_id, action: str, severity: str, message: str):
    return execute(
        "INSERT INTO alerts (user_id, action, severity, message) VALUES (%s,%s,%s,%s)",
        (user_id, action, severity, message),
    )
