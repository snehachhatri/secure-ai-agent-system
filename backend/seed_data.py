"""
Demo data seed (idempotent: dobara chalane par duplicate nahi banata).

Kya karta hai:
  1. semester_status table banata hai (result publish hua ya nahi) - policy engine ko chahiye
  2. departments.hod_id bharta hai
  3. fees, attendance, marks ke missing rows bharta hai (kuch fail, kuch pending, kuch low attendance)
  4. users banata hai (10 students, saare faculty/HOD, 1 admin) - passwords RANDOM + HASHED
     Passwords sirf seed_credentials.txt mein jaate hain (gitignore mein hai, GitHub par nahi jaana).

Sab data fake/synthetic hai.
"""
import random
import secrets
from datetime import timedelta

from auth import hash_password
from database import get_conn

random.seed(2026)           # marks/fees/attendance har baar same banein
DEMO_STUDENT_ACCOUNTS = 10
FEE_BY_DEPT = {1: 45000, 2: 42000, 3: 40000}


def main():
    conn = get_conn(autocommit=True)
    cur = conn.cursor()
    added = {}

    # ---- 1. semester_status ----
    cur.execute("""CREATE TABLE IF NOT EXISTS semester_status (
        semester INT PRIMARY KEY,
        result_published TINYINT(1) NOT NULL DEFAULT 0)""")
    cur.execute("SELECT MAX(semester) AS m FROM students")
    current_sem = cur.fetchone()["m"] or 1
    n = 0
    for sem in range(1, current_sem + 1):
        # purane semesters ka result publish ho chuka, chal rahe semester ka nahi
        n += cur.execute("INSERT IGNORE INTO semester_status VALUES (%s, %s)",
                         (sem, 0 if sem == current_sem else 1))
    added["semester_status"] = n

    conn.begin()
    try:
        # ---- 2. HODs ----
        cur.execute("SELECT department_id, hod_id FROM departments")
        n = 0
        for d in cur.fetchall():
            if d["hod_id"] is None:
                cur.execute("SELECT faculty_id FROM faculty WHERE department_id=%s "
                            "ORDER BY (designation='HOD') DESC, faculty_id LIMIT 1", (d["department_id"],))
                f = cur.fetchone()
                if f:
                    cur.execute("UPDATE departments SET hod_id=%s WHERE department_id=%s",
                                (f["faculty_id"], d["department_id"]))
                    n += 1
        added["departments.hod_id"] = n

        # ---- students aur unke dept ke subjects ----
        cur.execute("SELECT student_id, department_id, semester FROM students ORDER BY student_id")
        students = cur.fetchall()
        cur.execute("SELECT subject_id, department_id FROM subjects")
        dept_subjects = {}
        for s in cur.fetchall():
            dept_subjects.setdefault(s["department_id"], []).append(s["subject_id"])

        # ---- 3a. fees ----
        n = 0
        cur.execute("SELECT DISTINCT student_id FROM fees")
        have = {r["student_id"] for r in cur.fetchall()}
        from datetime import date
        for st in students:
            if st["student_id"] in have:
                continue
            due = date(2026, 10, 1) + timedelta(days=random.randint(0, 10))
            pending = random.random() < 0.25
            cur.execute("INSERT INTO fees (student_id, amount, due_date, status, paid_on) VALUES (%s,%s,%s,%s,%s)",
                        (st["student_id"], FEE_BY_DEPT.get(st["department_id"], 40000), due,
                         "pending" if pending else "paid",
                         None if pending else due - timedelta(days=random.randint(1, 10))))
            n += 1
        added["fees"] = n

        # ---- 3b. attendance ----
        n = 0
        cur.execute("SELECT student_id, subject_id FROM attendance")
        have = {(r["student_id"], r["subject_id"]) for r in cur.fetchall()}
        for st in students:
            for sub in dept_subjects.get(st["department_id"], []):
                if (st["student_id"], sub) in have:
                    continue
                attended = random.randint(18, 29) if random.random() < 0.15 else random.randint(30, 40)
                cur.execute("INSERT INTO attendance (student_id, subject_id, classes_held, classes_attended) "
                            "VALUES (%s,%s,40,%s)", (st["student_id"], sub, attended))
                n += 1
        added["attendance"] = n

        # ---- 3c. marks ----
        n = 0
        cur.execute("SELECT student_id, subject_id FROM marks")
        have = {(r["student_id"], r["subject_id"]) for r in cur.fetchall()}
        for st in students:
            for sub in dept_subjects.get(st["department_id"], []):
                if (st["student_id"], sub) in have:
                    continue
                m = max(0, min(100, round(random.gauss(65, 18))))
                cur.execute("INSERT INTO marks (student_id, subject_id, marks, semester) VALUES (%s,%s,%s,%s)",
                            (st["student_id"], sub, m, st["semester"] or current_sem))
                n += 1
        added["marks"] = n

        # ---- 4. users ----
        cur.execute("SELECT hod_id FROM departments WHERE hod_id IS NOT NULL")
        hod_ids = {r["hod_id"] for r in cur.fetchall()}
        cur.execute("SELECT username FROM users")
        existing = {r["username"] for r in cur.fetchall()}
        accounts = []   # (username, role, student_id, faculty_id, label)
        for st in students[:DEMO_STUDENT_ACCOUNTS]:
            accounts.append((f"S{st['student_id']:03d}", "student", st["student_id"], None, f"student {st['student_id']}"))
        cur.execute("SELECT faculty_id, name, department_id FROM faculty ORDER BY faculty_id")
        for f in cur.fetchall():
            if f["faculty_id"] in hod_ids:
                accounts.append((f"HOD{f['department_id']:02d}", "hod", None, f["faculty_id"], f["name"]))
            else:
                accounts.append((f"F{f['faculty_id']:03d}", "faculty", None, f["faculty_id"], f["name"]))
        accounts.append(("admin01", "admin", None, None, "Security officer"))

        creds, n = [], 0
        for username, role, sid, fid, label in accounts:
            if username in existing:
                continue
            password = secrets.token_urlsafe(9)
            cur.execute("INSERT INTO users (username, password_hash, role, student_id, faculty_id) "
                        "VALUES (%s,%s,%s,%s,%s)", (username, hash_password(password), role, sid, fid))
            creds.append(f"{username:10} {password:14} {role:8} {label}")
            n += 1
        added["users"] = n
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if creds:
        with open("seed_credentials.txt", "w", encoding="utf-8") as fh:
            fh.write("username   password       role     name\n" + "\n".join(creds) + "\n")
        print("Naye accounts ke passwords seed_credentials.txt mein hain (GitHub par mat daalna).")

    print("Seed complete. Naye rows:", added)


if __name__ == "__main__":
    main()
