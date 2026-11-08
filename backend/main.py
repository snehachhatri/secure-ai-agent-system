import os
import sys
import time
import json
from collections import defaultdict
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "policy_engine"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "injection_detector"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "anomaly_detector"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agents"))

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from audit import write_alert, write_log
from auth import create_access_token, get_current_user, get_user_by_username, verify_or_dummy
from database import execute, fetch_all, fetch_one
from detector import detect
from models import LoginRequest, RequestPayload
from agent_context import load_agent_context
from mysql_resolver import MySQLResolver
from policy_checker import check_policy
from rule_agent import RuleAgent
from anomaly import Event, evaluate, plan_response

app = FastAPI(title="Secure AI Agent System")
agent = RuleAgent()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Login brute-force roak: 5 galat koshish => 10 minute ke liye us username par rok ----
MAX_FAILS, WINDOW_SEC = 5, 600
_failed = defaultdict(list)


def _recent_fails(username: str):
    now = time.time()
    _failed[username] = [t for t in _failed[username] if now - t < WINDOW_SEC]
    return _failed[username]


@app.get("/")
def root():
    return {"message": "Backend is running!"}


@app.get("/test-db")
def test_db():
    try:
        row = fetch_one("SELECT COUNT(*) AS n FROM students")
        return {"status": "connected", "students": row["n"]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# NOTE: public /signup hata diya gaya hai. Accounts sirf admin ya seed script banati hai.

@app.post("/login")
def login(data: LoginRequest):
    username = data.username.strip()
    if len(_recent_fails(username)) >= MAX_FAILS:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")

    user = get_user_by_username(username)
    ok = verify_or_dummy(data.password, user["password_hash"] if user else None)
    if not ok:
        _failed[username].append(time.time())
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user["is_locked"]:
        raise HTTPException(status_code=403, detail="Account locked. Contact the administrator.")

    _failed.pop(username, None)
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "role": user["role"],
        "username": user["username"],
    }


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    if user["is_locked"]:
        raise HTTPException(status_code=403, detail="Account locked. Contact the administrator.")
    return user


def _check_admin_read(user: dict, action: str):
    if user.get("is_locked"):
        raise HTTPException(status_code=403, detail="Account locked. Contact the administrator.")
    decision = check_policy(user, action, {}, MySQLResolver())
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="Admin access required")


@app.get("/admin/logs")
def get_admin_logs(
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    _check_admin_read(user, "READ_LOGS")
    logs = fetch_all(
        "SELECT l.id, l.user_id, u.username, l.role, l.request_text, l.action, "
        "l.params, l.decision, l.reason, l.rule, l.old_value, l.new_value, l.created_at, "
        "CASE WHEN l.decision = 'allowed' THEN 'none' "
        "WHEN l.action = 'PROMPT_INJECTION' OR l.rule IN "
        "('fail_closed', 'unknown_role', 'protected_field', 'bad_config') THEN 'high' "
        "ELSE 'medium' END AS severity "
        "FROM requests_logs l LEFT JOIN users u ON u.id = l.user_id "
        "WHERE l.action <> 'NONE' "
        "ORDER BY l.id DESC LIMIT %s",
        (limit,),
    )
    return {"logs": logs}


@app.get("/admin/stats")
def get_admin_stats(user: dict = Depends(get_current_user)):
    _check_admin_read(user, "READ_LOGS")
    row = fetch_one(
        "SELECT COUNT(*) AS total_requests, "
        "COALESCE(SUM(decision = 'allowed'), 0) AS allowed_requests, "
        "COALESCE(SUM(decision = 'blocked'), 0) AS blocked_requests, "
        "COALESCE(SUM(decision = 'clarify'), 0) AS clarification_requests "
        "FROM requests_logs WHERE action <> 'NONE'"
    )
    alert_row = fetch_one("SELECT COUNT(*) AS total_alerts FROM alerts")
    return {**row, "total_alerts": alert_row["total_alerts"]}


@app.get("/admin/alerts")
def get_admin_alerts(
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    _check_admin_read(user, "READ_ALERTS")
    alerts = fetch_all(
        "SELECT a.id, a.user_id, u.username, a.action, a.severity, a.message, a.created_at "
        "FROM alerts a LEFT JOIN users u ON u.id = a.user_id "
        "ORDER BY a.id DESC LIMIT %s",
        (limit,),
    )
    return {"alerts": alerts}


class ActionNeedsInput(Exception):
    """Action ko execute karne ke liye required fields missing hain."""


def _event_from_log(row: dict):
    params = row.get("params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except (TypeError, ValueError):
            params = {}
    if not isinstance(params, dict):
        params = {}

    decision = row.get("decision")
    action = row.get("action") or "UNKNOWN"
    rule = row.get("rule") or ""
    high_rules = {"fail_closed", "unknown_role", "protected_field", "bad_config"}
    severity = (
        "none" if decision == "allowed"
        else "high" if action == "PROMPT_INJECTION" or rule in high_rules
        or action.startswith(("DELETE_", "EXPORT_", "DROP_", "GRANT_", "TRUNCATE_"))
        else "medium"
    )
    records = params.get("records", 1)
    if isinstance(records, list):
        records = max(1, len(records))
    try:
        records = max(1, int(records))
    except (TypeError, ValueError):
        records = 1
    try:
        injection_score = max(0, int(params.get("injection_score", 0)))
    except (TypeError, ValueError):
        injection_score = 0
    target_id = params.get("student_id", params.get("target_user_id"))
    try:
        target_id = int(target_id) if target_id is not None else None
    except (TypeError, ValueError):
        target_id = None

    ts = row.get("created_at") or datetime.now()
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    return Event(
        user_id=int(row["user_id"]), role=row.get("role") or "student",
        action=action, decision=decision, severity=severity, ts=ts,
        target_id=target_id, records=records, injection_score=injection_score,
    )


def _load_recent_events(user_id: int):
    rows = fetch_all(
        "SELECT user_id, role, action, params, decision, rule, created_at "
        "FROM requests_logs WHERE user_id = %s "
        "AND created_at >= NOW() - INTERVAL 1 HOUR "
        "AND decision IN ('allowed', 'blocked') AND action <> 'NONE' "
        "ORDER BY created_at, id",
        (user_id,),
    )
    return [_event_from_log(row) for row in rows]


def _assess_anomaly(user: dict, history: list, action_events: list, injection_score: int):
    events = list(history)
    evaluations = []
    now = datetime.now()
    for item in action_events:
        if item["decision"] not in ("allowed", "blocked"):
            continue
        event = Event(
            user_id=user["user_id"], role=user["role"],
            action=item["action"], decision=item["decision"],
            severity=item.get("severity", "none"), ts=now,
            target_id=item.get("target_id"), records=item.get("records", 1),
            injection_score=injection_score,
        )
        anomaly_result = evaluate(events, event)
        events.append(event)
        evaluations.append((anomaly_result, plan_response(anomaly_result)))

    if not evaluations:
        return None

    # Keep the strongest response from this request.
    rank = {"allow": 0, "alert": 1, "throttle": 2, "lock": 3}
    result, response = max(
        evaluations, key=lambda pair: (rank[pair[0].action], pair[0].score),
    )
    if response["create_alert"]:
        write_alert(user["user_id"], "ANOMALY_DETECTED", response["severity"], response["message"])
    if response["lock_user"]:
        execute("UPDATE users SET is_locked = 1 WHERE id = %s", (user["user_id"],))
    return {
        "score": result.score,
        "rule_score": result.rule_score,
        "ml_score": result.ml_score,
        "level": result.level,
        "action": result.action,
        "reasons": result.reasons,
        "reject_request": response["reject_request"],
        "lock_user": response["lock_user"],
    }


def _run_db_action(action: str, params: dict, user: dict):
    """Policy-approved action ka DB kaam. Har value parameterized query se jaati hai."""
    sid = params.get("student_id")
    subject_id = params.get("subject_id")
    semester = params.get("semester")

    if action == "READ_MARKS":
        clauses, values = [], []
        if user["role"] == "student":
            clauses.append("m.student_id = %s")
            values.append(sid)
        elif user["role"] == "faculty":
            if subject_id is None:
                raise ActionNeedsInput("Apna subject specify karein.")
            clauses.append("m.subject_id = %s")
            values.append(subject_id)
            if sid is not None:
                clauses.append("m.student_id = %s")
                values.append(sid)
        elif user["role"] == "hod":
            dept = params.get("department_id", user.get("department_id"))
            if dept is None:
                raise ActionNeedsInput("Department information available nahi hai.")
            clauses.append("s.department_id = %s")
            values.append(dept)
            if sid is not None:
                clauses.append("m.student_id = %s")
                values.append(sid)
        else:
            raise ActionNeedsInput("Is role ke liye marks read supported nahi hai.")

        if subject_id is not None and user["role"] != "faculty":
            clauses.append("m.subject_id = %s")
            values.append(subject_id)
        if semester is not None:
            clauses.append("m.semester = %s")
            values.append(semester)

        rows = fetch_all(
            "SELECT m.student_id, s.name AS student_name, m.subject_id, "
            "sub.subject_name, m.marks, m.semester "
            "FROM marks m JOIN students s ON s.student_id = m.student_id "
            "JOIN subjects sub ON sub.subject_id = m.subject_id WHERE "
            + " AND ".join(clauses)
            + " ORDER BY m.semester, sub.subject_name",
            tuple(values),
        )
        return {"data": rows}

    if action == "READ_FEES":
        if sid is None:
            raise ActionNeedsInput("Student ID resolve nahi hui.")
        rows = fetch_all(
            "SELECT amount, status, due_date, paid_on FROM fees "
            "WHERE student_id = %s ORDER BY due_date",
            (sid,),
        )
        return {"data": rows}

    if action == "READ_ATTENDANCE":
        if sid is None:
            raise ActionNeedsInput("Student ID resolve nahi hui.")
        clauses, values = ["a.student_id = %s"], [sid]
        if subject_id is not None:
            clauses.append("a.subject_id = %s")
            values.append(subject_id)
        rows = fetch_all(
            "SELECT a.subject_id, sub.subject_name, a.classes_held, "
            "a.classes_attended FROM attendance a "
            "JOIN subjects sub ON sub.subject_id = a.subject_id WHERE "
            + " AND ".join(clauses)
            + " ORDER BY sub.subject_name",
            tuple(values),
        )
        return {"data": rows}

    if action == "UPDATE_MARKS":
        required = {"student_id": sid, "subject_id": subject_id,
                    "semester": semester, "value": params.get("value")}
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ActionNeedsInput("Update ke liye ye details chahiye: " + ", ".join(missing))

        row = fetch_one(
            "SELECT id, marks FROM marks WHERE student_id = %s AND subject_id = %s "
            "AND semester = %s ORDER BY id LIMIT 1",
            (sid, subject_id, semester),
        )
        if row is None:
            raise ActionNeedsInput("Is student, subject aur semester ka marks record nahi mila.")
        old_value = row["marks"]
        execute("UPDATE marks SET marks = %s WHERE id = %s", (required["value"], row["id"]))
        return {
            "message": "Marks updated.",
            "old_value": old_value,
            "new_value": required["value"],
        }

    if action == "REGISTER_REVALUATION":
        required = {"student_id": sid, "subject_id": subject_id, "semester": semester}
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ActionNeedsInput("Revaluation ke liye ye details chahiye: " + ", ".join(missing))
        existing = fetch_one(
            "SELECT id, status FROM revaluations WHERE student_id = %s "
            "AND subject_id = %s AND semester = %s AND status = 'pending' LIMIT 1",
            (sid, subject_id, semester),
        )
        if existing:
            return {"message": "Pending revaluation pehle se registered hai.",
                    "revaluation_id": existing["id"], "status": existing["status"]}
        revaluation_id = execute(
            "INSERT INTO revaluations (student_id, subject_id, semester) "
            "VALUES (%s, %s, %s)",
            (sid, subject_id, semester),
        )
        return {"message": "Revaluation registered.", "revaluation_id": revaluation_id,
                "status": "pending"}

    if action == "LIST_FAILING_STUDENTS":
        dept = params.get("department_id", user.get("department_id"))
        if dept is None:
            raise ActionNeedsInput("Department information available nahi hai.")
        clauses, values = ["s.department_id = %s", "m.marks < 40"], [dept]
        if semester is not None:
            clauses.append("m.semester = %s")
            values.append(semester)
        rows = fetch_all(
            "SELECT s.student_id, s.name AS student_name, m.subject_id, "
            "sub.subject_name, m.marks, m.semester "
            "FROM marks m JOIN students s ON s.student_id = m.student_id "
            "JOIN subjects sub ON sub.subject_id = m.subject_id WHERE "
            + " AND ".join(clauses)
            + " ORDER BY s.name, sub.subject_name",
            tuple(values),
        )
        return {"data": rows}

    raise ActionNeedsInput("Is action ka database operation abhi available nahi hai.")


# ---------------- Gateway (Step 1): injection check + audit log ----------------

@app.post("/request")
def handle_request(payload: RequestPayload, user: dict = Depends(get_current_user)):
    if user["is_locked"]:
        raise HTTPException(status_code=403, detail="Account locked. Contact the administrator.")

    text = payload.request_text

    try:
        anomaly_history = _load_recent_events(user["user_id"])
    except Exception as e:
        print("ANOMALY HISTORY READ FAILED:", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    # 1. Prompt injection check (agent se PEHLE)
    inj = detect(text)
    details = {"injection_score": inj.risk_score, "signals": inj.signals,
               "categories": sorted({m["category"] for m in inj.matches})}

    if inj.action == "block":
        try:
            write_log(user, text, "PROMPT_INJECTION", "blocked", inj.reason, "injection_detector", details)
            write_alert(user["user_id"], "PROMPT_INJECTION", "high", inj.reason)
        except Exception as e:      # block to ho hi raha hai; log fail hua to server par dikhao
            print("AUDIT WRITE FAILED (blocked request):", e)
        try:
            anomaly_info = _assess_anomaly(
                user, anomaly_history,
                [{"action": "PROMPT_INJECTION", "decision": "blocked", "severity": "high"}],
                inj.risk_score,
            )
        except Exception as e:
            print("ANOMALY RESPONSE FAILED:", e)
            raise HTTPException(status_code=503, detail="Service temporarily unavailable.")
        # User ko detail nahi (warna attacker seekh jayega ki kya pakda gaya)
        return {"decision": "blocked",
                "message": "Request blocked. This attempt has been logged.",
                "anomaly": anomaly_info}

    # 2. Audit log likhe bina aage nahi badhte (fail closed)
    try:
        write_log(user, text, "NONE", "pending", "passed injection check", "injection_detector", details)
        if inj.action == "flag":
            write_alert(user["user_id"], "SUSPICIOUS_REQUEST", "medium", inj.reason)
    except Exception as e:
        print("AUDIT WRITE FAILED:", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    # 3. Agent sirf actions plan karta hai; har action ko policy engine verify karta hai.
    try:
        plan = agent.plan(text, load_agent_context(), user.get("role"))
    except Exception as e:
        print("AGENT/POLICY PREPARATION FAILED:", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    if plan.clarify:
        return {"decision": "clarify", "message": plan.clarify,
                "results": [], "not_understood": plan.unrecognized}

    if not plan.actions:
        return {"decision": "blocked", "results": [],
                "not_understood": plan.unrecognized,
                "message": "Request mein koi supported action nahi mila."}

    resolver = MySQLResolver()
    results = []
    anomaly_inputs = []
    for planned in plan.actions:
        action = planned.action
        params = dict(planned.params)

        # Agent ka "self" ya naam se mila ID hamesha authenticated user/context se resolve karein.
        for key, id_key in (("student", "student_id"), ("faculty", "faculty_id")):
            target = params.pop(key, None)
            if target == "self":
                params[id_key] = user.get(id_key)
            elif isinstance(target, dict) and target.get("id") is not None:
                params[id_key] = target["id"]
        if params.pop("user", None) == "self":
            params["user_id"] = user.get("user_id")

        # HOD ka default scope uska apna department hai.
        if user.get("role") == "hod":
            if action == "LIST_FAILING_STUDENTS" or (
                action == "READ_MARKS" and params.get("student_id") is None
            ):
                if params.get("department_id") is None:
                    params["department_id"] = user.get("department_id")

        decision = check_policy(user, action, params, resolver)
        action_decision = "allowed" if decision.allowed else "blocked"
        reason = decision.reason
        outcome = {}

        if decision.allowed:
            try:
                outcome = _run_db_action(action, params, user)
            except ActionNeedsInput as e:
                action_decision = "clarify"
                reason = str(e)
            except Exception as e:
                print("DATABASE ACTION FAILED:", e)
                raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

        try:
            write_log(user, text, action,
                      action_decision, reason, decision.rule, params,
                      old_value=outcome.get("old_value"),
                      new_value=outcome.get("new_value"))
            if action_decision == "blocked":
                write_alert(user["user_id"], action, decision.severity,
                            f"{action} blocked: {reason}")
        except Exception as e:
            print("AUDIT WRITE FAILED:", e)
            raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

        item = {"action": action, "decision": action_decision, "reason": reason}
        item.update(outcome)
        results.append(item)
        anomaly_inputs.append({
            "action": action,
            "decision": action_decision,
            "severity": decision.severity if action_decision == "blocked" else "none",
            "target_id": params.get("student_id", params.get("target_user_id")),
            "records": params.get("records", 1),
        })

    all_allowed = all(r["decision"] == "allowed" for r in results)
    any_allowed = any(r["decision"] == "allowed" for r in results)
    any_clarify = any(r["decision"] == "clarify" for r in results)
    overall = ("allowed" if all_allowed else "partial" if any_allowed
               else "clarify" if any_clarify else "blocked")
    try:
        anomaly_info = _assess_anomaly(
            user, anomaly_history, anomaly_inputs, inj.risk_score,
        )
    except Exception as e:
        print("ANOMALY RESPONSE FAILED:", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    response = {"decision": overall,
                "results": results, "not_understood": plan.unrecognized,
                "anomaly": anomaly_info}
    if anomaly_info and anomaly_info["reject_request"]:
        response["decision"] = "blocked"
        response["message"] = "Request rejected due to anomalous activity."
    return response
