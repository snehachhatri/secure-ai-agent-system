import math
from dataclasses import dataclass
from datetime import date, datetime

from policies import POLICIES, PROTECTED_FIELDS, HIGH_RISK_PREFIXES


@dataclass
class Decision:
    allowed: bool
    reason: str
    rule: str = ""            # audit log ke liye: kaunsa rule match/fail hua
    severity: str = "none"    # none / low / medium / high (alert module use karega)


class Resolver:
    """DB lookups. Abhi interface hai, MySQL wali class baad mein isse inherit karegi."""
    def faculty_subjects(self, faculty_id): raise NotImplementedError
    def student_subjects(self, student_id): raise NotImplementedError
    def student_department(self, student_id): raise NotImplementedError
    def result_published(self, semester): raise NotImplementedError


# ---------------- Data conditions: (ok, reason) ----------------

def cond_any(user, params, resolver, rule):
    return True, "no data restriction"

def cond_own_student(user, params, resolver, rule):
    sid = user.get("student_id")
    if sid is None:
        return False, "token mein student_id nahi hai"
    if params.get("student_id") != sid:
        return False, "sirf apna data allowed hai"
    return True, "apna data"

def cond_own_subject(user, params, resolver, rule):
    fid = user.get("faculty_id")
    sub = params.get("subject_id")
    if fid is None or sub is None:
        return False, "faculty ya subject missing"
    if sub not in resolver.faculty_subjects(fid):
        return False, "ye subject aapka nahi hai"
    return True, "apna subject"

def cond_own_department(user, params, resolver, rule):
    dept = user.get("department_id")
    if dept is None:
        return False, "token mein department nahi hai"
    target = params.get("department_id")
    if target is None and params.get("student_id") is not None:
        target = resolver.student_department(params["student_id"])
    if target is None:
        return False, "department ya student missing"
    if target != dept:
        return False, "dusre department ka data"
    return True, "apna department"

def cond_own_profile(user, params, resolver, rule):
    fid = user.get("faculty_id")
    if fid is None or params.get("faculty_id") != fid:
        return False, "sirf apni profile edit kar sakte hain"
    fields = params.get("fields")
    if not fields:
        return False, "koi field nahi diya"
    bad = [f for f in fields if f not in rule.get("allowed_fields", [])]
    if bad:
        return False, f"ye fields allowed nahi: {bad}"
    return True, "whitelisted fields"

def cond_own_faculty(user, params, resolver, rule):
    fid = user.get("faculty_id")
    if fid is None or params.get("faculty_id") != fid:
        return False, "sirf apni chutti set/cancel kar sakte hain"
    return True, "apni chutti"

def cond_teaches_me(user, params, resolver, rule):
    sid, fid = user.get("student_id"), params.get("faculty_id")
    if sid is None or fid is None:
        return False, "student ya faculty missing"
    if not (set(resolver.faculty_subjects(fid)) & set(resolver.student_subjects(sid))):
        return False, "ye faculty aapko nahi padhate"
    return True, "aapke subject ke faculty"

def cond_own_user(user, params, resolver, rule):
    uid = user.get("user_id")
    if uid is None or params.get("user_id") != uid:
        return False, "sirf apni notifications"
    return True, "apni notifications"

def cond_not_self(user, params, resolver, rule):
    target = params.get("target_user_id")
    if target is None:
        return False, "target user missing"
    if target == user.get("user_id"):
        return False, "khud ko lock nahi kar sakte"
    return True, "dusre user par action"


CONDITIONS = {
    "any": cond_any,
    "own_student": cond_own_student,
    "own_subject": cond_own_subject,
    "own_department": cond_own_department,
    "own_profile": cond_own_profile,
    "own_faculty": cond_own_faculty,
    "teaches_me": cond_teaches_me,
    "own_user": cond_own_user,
    "not_self": cond_not_self,
}


# ---------------- Limits aur result state ----------------

def _is_real_date(x):
    return isinstance(x, date) and not isinstance(x, datetime)

def _check_limits(rule, params):
    n = len(params.get("records", [])) or 1
    if "max_records" in rule and n > rule["max_records"]:
        return False, f"bulk limit: max {rule['max_records']} records, aapne {n} maange"

    if "min_value" in rule or "max_value" in rule:
        v = params.get("value")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            return False, "value valid number honi chahiye"
        if v < rule.get("min_value", float("-inf")) or v > rule.get("max_value", float("inf")):
            return False, f"value {rule.get('min_value')}-{rule.get('max_value')} ke beech honi chahiye"

    if "max_days" in rule:
        s, e = params.get("start_date"), params.get("end_date")
        if not (_is_real_date(s) and _is_real_date(e)):
            return False, "valid dates chahiye"
        if s < date.today():
            return False, "past date ki chutti set nahi ho sakti"
        if e < s:
            return False, "end date start se pehle nahi ho sakti"
        if (e - s).days + 1 > rule["max_days"]:
            return False, f"max {rule['max_days']} din ki chutti allowed hai"
    return True, "limits ok"

def _check_result_state(rule, params, resolver):
    need = rule.get("result_must_be")
    if not need:
        return True, "ok"
    sem = params.get("semester")
    if sem is None:
        return False, "semester missing"
    published = resolver.result_published(sem)
    if need == "unpublished" and published:
        return False, "result publish ho chuka hai, direct update nahi. Marks change request banao"
    if need == "published" and not published:
        return False, "result abhi publish nahi hua, direct update karo"
    return True, "ok"


# ---------------- Main entry ----------------

def check_policy(user, action, params, resolver) -> Decision:
    """Ek action ka final decision. Koi bhi gadbad = BLOCK (fail closed)."""
    try:
        if not isinstance(user, dict) or not isinstance(params, dict):
            return Decision(False, "invalid input", "bad_input", "medium")

        if user.get("is_locked"):
            return Decision(False, "account locked hai", "account_locked", "medium")

        role_rules = POLICIES.get(user.get("role"))
        if role_rules is None:
            return Decision(False, "unknown role", "unknown_role", "high")

        rule = role_rules.get(action)
        if rule is None:
            sev = "high" if str(action).upper().startswith(HIGH_RISK_PREFIXES) else "medium"
            return Decision(False, f"role '{user['role']}' ko '{action}' allowed nahi",
                            "default_deny", sev)

        fields = params.get("fields")
        if fields is not None:
            if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
                return Decision(False, "fields text ki list honi chahiye", "bad_fields", "medium")
            protected = [f for f in fields if f.lower() in PROTECTED_FIELDS]
            if protected:
                return Decision(False, f"protected field badalne ki koshish: {protected}",
                                "protected_field", "high")

        cond = CONDITIONS.get(rule["condition"])
        if cond is None:
            return Decision(False, "policy config galat hai", "bad_config", "high")
        ok, why = cond(user, params, resolver, rule)
        if not ok:
            return Decision(False, why, f"condition:{rule['condition']}", "medium")

        ok, why = _check_limits(rule, params)
        if not ok:
            return Decision(False, why, "limits", "medium")

        ok, why = _check_result_state(rule, params, resolver)
        if not ok:
            return Decision(False, why, "result_state", "low")

        return Decision(True, "allowed", f"{user['role']}:{action}", "none")

    except Exception as e:
        return Decision(False, f"policy error, isliye block: {e}", "fail_closed", "high")

    # ---- Legacy shim: purane demo /request ke liye ----
# Gateway wiring ke time ye hata denge, tab /request naya check_policy use karega.
_LEGACY_POLICIES = {
    "Customer Support Agent": ["READ_CUSTOMER", "CREATE_TICKET"],
    "Malicious Test Agent": [],
}

def check_permission(agent_name, action):
    return "ALLOW" if action in _LEGACY_POLICIES.get(agent_name, []) else "BLOCK"