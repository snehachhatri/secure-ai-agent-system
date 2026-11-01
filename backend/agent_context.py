"""Agent ko naam/subject pehchanne ke liye DB se non-sensitive reference data."""
from database import fetch_all


def load_agent_context() -> dict:
    return {
        "subjects": fetch_all("SELECT subject_id, subject_name FROM subjects"),
        "students": fetch_all("SELECT student_id, name FROM students"),
    }