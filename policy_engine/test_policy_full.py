from datetime import date, timedelta
from policy_checker import check_policy, Resolver


class FakeResolver(Resolver):
    def faculty_subjects(self, fid): return {1: [10, 11], 2: [20], 4: [30]}.get(fid, [])
    def student_subjects(self, sid): return {101: [10, 11, 12], 102: [20]}.get(sid, [])
    def student_department(self, sid): return {101: 1, 102: 2}.get(sid)
    def result_published(self, sem): return {4: True, 5: False}[sem]

class BrokenResolver(FakeResolver):
    def faculty_subjects(self, fid): raise RuntimeError("DB down")


R = FakeResolver()
student = {"user_id": 1, "role": "student", "student_id": 101, "department_id": 1}
faculty = {"user_id": 2, "role": "faculty", "faculty_id": 1, "department_id": 1}
hod     = {"user_id": 3, "role": "hod", "faculty_id": 4, "department_id": 1}
admin   = {"user_id": 4, "role": "admin"}

today = date.today()
d = lambda n: today + timedelta(days=n)

T, F = True, False
tests = [
    # ---------- STUDENT (Rahul=101, Priya=102) ----------
    ("student: apna marks",            student, "READ_MARKS", {"student_id": 101}, T),
    ("student: apni fees",             student, "READ_FEES", {"student_id": 101}, T),
    ("student: apni attendance",       student, "READ_ATTENDANCE", {"student_id": 101}, T),
    ("student: apna revaluation",      student, "REGISTER_REVALUATION", {"student_id": 101, "subject_id": 10}, T),
    ("student: apne faculty ki availability", student, "READ_FACULTY_AVAILABILITY", {"faculty_id": 1}, T),
    ("student: apni notifications",    student, "READ_NOTIFICATIONS", {"user_id": 1}, T),
    ("student: Priya ka marks",        student, "READ_MARKS", {"student_id": 102}, F),
    ("student: Priya ki fees",         student, "READ_FEES", {"student_id": 102}, F),
    ("student: Priya ka revaluation",  student, "REGISTER_REVALUATION", {"student_id": 102, "subject_id": 20}, F),
    ("student: marks update",          student, "UPDATE_MARKS", {"student_id": 101, "subject_id": 10, "value": 95, "semester": 5}, F),
    ("student: delete record",         student, "DELETE_STUDENT", {"student_id": 101}, F),
    ("student: logs dekhna",           student, "READ_LOGS", {}, F),
    ("student: dusre subject ke faculty", student, "READ_FACULTY_AVAILABILITY", {"faculty_id": 2}, F),
    ("student: dusre ki notifications", student, "READ_NOTIFICATIONS", {"user_id": 99}, F),
    ("student: marks bina student_id", student, "READ_MARKS", {}, F),
    ("student: chutti set karna",      student, "SET_OWN_LEAVE", {"faculty_id": 1, "start_date": d(1), "end_date": d(1)}, F),

    # ---------- FACULTY (id=1, subjects 10, 11; sem 5 unpublished, sem 4 published) ----------
    ("faculty: apna subject marks dekhna", faculty, "READ_MARKS", {"subject_id": 10}, T),
    ("faculty: dusra subject marks",   faculty, "READ_MARKS", {"subject_id": 20}, F),
    ("faculty: marks update (apna)",   faculty, "UPDATE_MARKS", {"subject_id": 10, "value": 18, "semester": 5}, T),
    ("faculty: doosra apna subject",   faculty, "UPDATE_MARKS", {"subject_id": 11, "value": 75, "semester": 5}, T),
    ("faculty: dusre subject update",  faculty, "UPDATE_MARKS", {"subject_id": 20, "value": 60, "semester": 5}, F),
    ("faculty: marks 150",             faculty, "UPDATE_MARKS", {"subject_id": 10, "value": 150, "semester": 5}, F),
    ("faculty: marks -5",              faculty, "UPDATE_MARKS", {"subject_id": 10, "value": -5, "semester": 5}, F),
    ("faculty: marks 'abc'",           faculty, "UPDATE_MARKS", {"subject_id": 10, "value": "abc", "semester": 5}, F),
    ("faculty: marks NaN",             faculty, "UPDATE_MARKS", {"subject_id": 10, "value": float("nan"), "semester": 5}, F),
    ("faculty: 30 records bulk",       faculty, "UPDATE_MARKS", {"subject_id": 10, "value": 100, "semester": 5, "records": list(range(30))}, F),
    ("faculty: result ke baad direct update", faculty, "UPDATE_MARKS", {"subject_id": 10, "value": 52, "semester": 4}, F),
    ("faculty: result ke baad change request", faculty, "REQUEST_MARKS_CHANGE", {"subject_id": 10, "value": 52, "semester": 4}, T),
    ("faculty: result se pehle change request", faculty, "REQUEST_MARKS_CHANGE", {"subject_id": 10, "value": 52, "semester": 5}, F),
    ("faculty: phone update",          faculty, "UPDATE_OWN_PROFILE", {"faculty_id": 1, "fields": ["phone"]}, T),
    ("faculty: address + office hours", faculty, "UPDATE_OWN_PROFILE", {"faculty_id": 1, "fields": ["address", "office_hours"]}, T),
    ("faculty: role badalna",          faculty, "UPDATE_OWN_PROFILE", {"faculty_id": 1, "fields": ["role"]}, F),
    ("faculty: department badalna",    faculty, "UPDATE_OWN_PROFILE", {"faculty_id": 1, "fields": ["department_id"]}, F),
    ("faculty: 'Role' (capital) badalna", faculty, "UPDATE_OWN_PROFILE", {"faculty_id": 1, "fields": ["Role"]}, F),
    ("faculty: dusri faculty ki profile", faculty, "UPDATE_OWN_PROFILE", {"faculty_id": 2, "fields": ["phone"]}, F),
    ("faculty: khaali fields",         faculty, "UPDATE_OWN_PROFILE", {"faculty_id": 1, "fields": []}, F),
    ("faculty: kal ki chutti",         faculty, "SET_OWN_LEAVE", {"faculty_id": 1, "start_date": d(1), "end_date": d(1)}, T),
    ("faculty: 3 din ki chutti",       faculty, "SET_OWN_LEAVE", {"faculty_id": 1, "start_date": d(1), "end_date": d(3)}, T),
    ("faculty: dusri faculty ki chutti", faculty, "SET_OWN_LEAVE", {"faculty_id": 2, "start_date": d(1), "end_date": d(1)}, F),
    ("faculty: 30 din chutti",         faculty, "SET_OWN_LEAVE", {"faculty_id": 1, "start_date": d(1), "end_date": d(30)}, F),
    ("faculty: past date chutti",      faculty, "SET_OWN_LEAVE", {"faculty_id": 1, "start_date": d(-5), "end_date": d(-4)}, F),
    ("faculty: end < start",           faculty, "SET_OWN_LEAVE", {"faculty_id": 1, "start_date": d(3), "end_date": d(1)}, F),
    ("faculty: apni chutti cancel",    faculty, "CANCEL_OWN_LEAVE", {"faculty_id": 1}, T),
    ("faculty: student data dekhna",   faculty, "READ_STUDENT", {"student_id": 101}, F),
    ("faculty: approve change",        faculty, "APPROVE_MARKS_CHANGE", {"student_id": 101}, F),
    ("faculty: delete student",        faculty, "DELETE_STUDENT", {"student_id": 101}, F),

    # ---------- HOD (dept 1) ----------
    ("hod: apne dept ka student",      hod, "READ_STUDENT", {"student_id": 101}, T),
    ("hod: apne dept ka marks",        hod, "READ_MARKS", {"student_id": 101}, T),
    ("hod: failing list apna dept",    hod, "LIST_FAILING_STUDENTS", {"department_id": 1}, T),
    ("hod: failing list dusra dept",   hod, "LIST_FAILING_STUDENTS", {"department_id": 2}, F),
    ("hod: Priya ka marks (dept 2)",   hod, "READ_MARKS", {"student_id": 102}, F),
    ("hod: Priya ki details",          hod, "READ_STUDENT", {"student_id": 102}, F),
    ("hod: apne dept ki change approve", hod, "APPROVE_MARKS_CHANGE", {"student_id": 101}, T),
    ("hod: dusre dept ki change approve", hod, "APPROVE_MARKS_CHANGE", {"student_id": 102}, F),
    ("hod: marks update",              hod, "UPDATE_MARKS", {"subject_id": 30, "value": 50, "semester": 5}, F),
    ("hod: fees dekhna",               hod, "READ_FEES", {"student_id": 101}, F),
    ("hod: apni profile",              hod, "UPDATE_OWN_PROFILE", {"faculty_id": 4, "fields": ["phone"]}, T),
    ("hod: apni chutti",               hod, "SET_OWN_LEAVE", {"faculty_id": 4, "start_date": d(1), "end_date": d(2)}, T),
    ("hod: logs dekhna",               hod, "READ_LOGS", {}, F),

    # ---------- ADMIN ----------
    ("admin: logs",                    admin, "READ_LOGS", {}, T),
    ("admin: alerts",                  admin, "READ_ALERTS", {}, T),
    ("admin: user lock",               admin, "LOCK_USER", {"target_user_id": 5}, T),
    ("admin: user unlock",             admin, "UNLOCK_USER", {"target_user_id": 5}, T),
    ("admin: khud ko lock",            admin, "LOCK_USER", {"target_user_id": 4}, F),
    ("admin: lock bina target",        admin, "LOCK_USER", {}, F),
    ("admin: apni notifications",      admin, "READ_NOTIFICATIONS", {"user_id": 4}, T),
    ("admin: student marks",           admin, "READ_MARKS", {"student_id": 101}, F),
    ("admin: student fees",            admin, "READ_FEES", {"student_id": 101}, F),
    ("admin: marks update",            admin, "UPDATE_MARKS", {"subject_id": 10, "value": 50, "semester": 5}, F),
    ("admin: delete student",          admin, "DELETE_STUDENT", {"student_id": 101}, F),

    # ---------- SPECIAL CASES ----------
    ("locked student",                 {**student, "is_locked": True}, "READ_MARKS", {"student_id": 101}, F),
    ("unknown role (guest)",           {"role": "guest"}, "READ_MARKS", {}, F),
    ("hataya hua role (clerk)",        {"role": "clerk"}, "READ_MARKS", {"student_id": 101}, F),
    ("unknown action EXPORT_ALL",      student, "EXPORT_ALL", {}, F),
    ("unknown action DROP_TABLE",      faculty, "DROP_TABLE", {}, F),
    ("params None",                    student, "READ_MARKS", None, F),
]

passed = 0
for name, user, action, params, expected in tests:
    dec = check_policy(user, action, params, R)
    ok = dec.allowed == expected
    passed += ok
    print(("PASS" if ok else "FAIL"), "|", name, "->", dec.allowed, "|", dec.reason)

# DB down hone par fail closed
dec = check_policy(faculty, "READ_MARKS", {"subject_id": 10}, BrokenResolver())
ok = dec.allowed is False and dec.rule == "fail_closed"
passed += ok
total = len(tests) + 1
print(("PASS" if ok else "FAIL"), "| DB down -> fail closed ->", dec.allowed, "|", dec.reason)

# Severity checks (alert module ke liye)
sev_tests = [
    ("severity: protected field = high",
     check_policy(faculty, "UPDATE_OWN_PROFILE", {"faculty_id": 1, "fields": ["role"]}, R), "high"),
    ("severity: DELETE_STUDENT = high",
     check_policy(student, "DELETE_STUDENT", {}, R), "high"),
    ("severity: dusre ka data = medium",
     check_policy(student, "READ_MARKS", {"student_id": 102}, R), "medium"),
    ("severity: allowed = none",
     check_policy(student, "READ_MARKS", {"student_id": 101}, R), "none"),
]
for name, dec, expected in sev_tests:
    ok = dec.severity == expected
    passed += ok
    total += 1
    print(("PASS" if ok else "FAIL"), "|", name, "->", dec.severity)

print(f"\n{passed}/{total} tests passed")