# Sirf rules yahan. Jo action role mein nahi likha wo AUTOMATIC BLOCK (default deny).

# Ye fields koi bhi profile update se nahi badal sakta (privilege escalation)
PROTECTED_FIELDS = {"role", "department_id", "faculty_id", "student_id",
                    "user_id", "is_locked", "password_hash", "password"}

# Inme se koi action unknown ho to severity HIGH (alert ke liye)
HIGH_RISK_PREFIXES = ("DELETE_", "DROP_", "EXPORT_", "GRANT_", "TRUNCATE_")

NOTIFICATION_RULES = {
    "READ_NOTIFICATIONS":     {"condition": "own_user"},
    "MARK_NOTIFICATION_READ": {"condition": "own_user"},
}

PROFILE_FIELDS = ["phone", "address", "office_hours", "email"]

POLICIES = {
    "student": {
        "READ_MARKS":                {"condition": "own_student"},
        "READ_FEES":                 {"condition": "own_student"},
        "READ_ATTENDANCE":           {"condition": "own_student"},
        "REGISTER_REVALUATION":      {"condition": "own_student"},
        "READ_FACULTY_AVAILABILITY": {"condition": "teaches_me"},
        **NOTIFICATION_RULES,
    },
    "faculty": {
        "READ_MARKS":           {"condition": "own_subject"},
        # Result publish hone se PEHLE direct update
        "UPDATE_MARKS":         {"condition": "own_subject", "max_records": 5,
                                 "min_value": 0, "max_value": 100,
                                 "result_must_be": "unpublished"},
        # Result publish hone ke BAAD sirf request (HOD approve karega)
        "REQUEST_MARKS_CHANGE": {"condition": "own_subject", "max_records": 5,
                                 "min_value": 0, "max_value": 100,
                                 "result_must_be": "published"},
        "UPDATE_OWN_PROFILE":   {"condition": "own_profile", "allowed_fields": PROFILE_FIELDS},
        "SET_OWN_LEAVE":        {"condition": "own_faculty", "max_days": 7},
        "CANCEL_OWN_LEAVE":     {"condition": "own_faculty"},
        **NOTIFICATION_RULES,
    },
    "hod": {
        "READ_STUDENT":          {"condition": "own_department"},
        "READ_MARKS":            {"condition": "own_department"},
        "LIST_FAILING_STUDENTS": {"condition": "own_department"},
        "APPROVE_MARKS_CHANGE":  {"condition": "own_department"},
        # HOD bhi faculty hai: apni profile aur chutti
        "UPDATE_OWN_PROFILE":    {"condition": "own_profile", "allowed_fields": PROFILE_FIELDS},
        "SET_OWN_LEAVE":         {"condition": "own_faculty", "max_days": 7},
        "CANCEL_OWN_LEAVE":      {"condition": "own_faculty"},
        **NOTIFICATION_RULES,
    },
    "admin": {
        "READ_LOGS":   {"condition": "any"},
        "READ_ALERTS": {"condition": "any"},
        "LOCK_USER":   {"condition": "not_self"},
        "UNLOCK_USER": {"condition": "any"},
        # Student/marks/fees data par koi action nahi (separation of duties)
        **NOTIFICATION_RULES,
    },
}