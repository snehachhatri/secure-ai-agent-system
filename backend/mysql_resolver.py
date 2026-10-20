"""Policy engine ke Resolver ka MySQL version: policy ko DB ke facts yahin se milte hain."""
from database import fetch_all, fetch_one
from policy_checker import Resolver


class MySQLResolver(Resolver):
    def faculty_subjects(self, faculty_id):
        rows = fetch_all("SELECT subject_id FROM faculty_subjects WHERE faculty_id = %s", (faculty_id,))
        return [r["subject_id"] for r in rows]

    def student_subjects(self, student_id):
        rows = fetch_all("SELECT DISTINCT subject_id FROM marks WHERE student_id = %s", (student_id,))
        return [r["subject_id"] for r in rows]

    def student_department(self, student_id):
        row = fetch_one("SELECT department_id FROM students WHERE student_id = %s", (student_id,))
        return row["department_id"] if row else None

    def result_published(self, semester):
        row = fetch_one("SELECT result_published FROM semester_status WHERE semester = %s", (semester,))
        if row is None:
            # pata nahi => exception => policy engine fail closed (block)
            raise LookupError(f"semester {semester} ka result status DB mein nahi hai")
        return bool(row["result_published"])
