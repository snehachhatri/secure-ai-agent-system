"""
RuleAgent: user ke text ko actions ki list mein badalta hai (LLM nahi, rules se).

ZAROORI SECURITY RULE: Agent sirf "irada" batata hai. Wo DB nahi chhuta, aur "self" jaise
shabdon ko asli ID gateway token se badalta hai. Agent ka output hamesha UNTRUSTED maana jata hai:
gateway use policy engine se verify karta hai.

Baad mein LLMAgent isi `plan()` interface ke saath lag sakta hai.
"""
import re
from dataclasses import dataclass, field

MAX_ACTIONS = 5


@dataclass
class PlannedAction:
    action: str
    params: dict = field(default_factory=dict)
    source: str = ""            # text ka kaunsa hissa


@dataclass
class Plan:
    actions: list = field(default_factory=list)
    unrecognized: list = field(default_factory=list)
    clarify: str | None = None  # kuch saaf nahi hai to sawal


_SPLIT = re.compile(r"\s*(?:,|;|&|\band\b|\baur\b|\bthen\b|\bphir\b|\balso\b|\bsaath\b)\s*", re.I)
_FIRST = r"\b(main|mai|mujhe|mera|meri|mere|my|i|i'm|im|me)\b"
_UPDATE = r"\b(update|change|set|badal|badlo|badalna|modify|edit|correct|kar\s*do|karo|kardo)\b"
_PROFILE = {"phone": r"\b(phone|mobile|contact)\b", "address": r"\baddress\b",
            "office_hours": r"\boffice\s*hours?\b", "email": r"\be-?mail\b",
            "role": r"\brole\b", "department_id": r"\bdepartment\b",
            "faculty_id": r"\bfaculty\s*id\b"}
_TITLES = {"sir", "maam", "madam", "mam", "dr", "prof", "professor", "mr", "mrs", "ms"}
# Chhote naam jo students bolte hain
_ALIASES = {"database": ["dbms", "db"], "data structures": ["dsa", "ds"], "computer networks": ["cn"],
            "python": ["py"], "web technologies": ["wt", "web"], "digital electronics": ["de"]}


def _clean(text: str) -> str:
    t = text.lower().replace("’", "'")
    t = re.sub(r"'s\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _person_match(seg: str, people: list, key: str):
    """id | None | 'ambiguous'. Pehle poora naam (word boundary), phir pehla naam."""
    words = set(re.findall(r"[a-z]+", seg))
    full = [p for p in people if re.search(rf"\b{re.escape(p['name'].lower())}\b", seg)]
    if len(full) == 1:
        return full[0][key]
    if len(full) > 1:
        return "ambiguous"
    first = {p[key] for p in people
             if (n := re.findall(r"[a-z]+", p["name"].lower())) and n[0] in words and n[0] not in _TITLES}
    if len(first) == 1:
        return first.pop()
    return "ambiguous" if len(first) > 1 else None


def _subjects_in(seg: str, subjects: list):
    out = []
    for s in subjects:
        name = s["subject_name"].lower()
        aliases = [a for k, al in _ALIASES.items() if k in name for a in al]
        toks = [t for t in re.findall(r"[a-z]+", name) if len(t) >= 5]
        words = name.split()
        initials = "".join(w[0] for w in words) if len(words) > 1 else None
        if (name in seg or any(re.search(rf"\b{a}\b", seg) for a in aliases)
                or any(re.search(rf"\b{t}\b", seg) for t in toks)
                or (initials and re.search(rf"\b{initials}\b", seg))):
            out.append(s["subject_id"])
    return out


def _value(seg: str):
    m = re.search(r"\b(?:to|se|ko)\s+(-?\d+(?:\.\d+)?)\b", seg) or \
        re.search(r"(-?\d+(?:\.\d+)?)\s*(?:kar\s*do|karo|kardo)\b", seg)
    return float(m.group(1)) if m else None


class RuleAgent:
    def plan(self, text: str, ctx: dict, role: str | None = None) -> Plan:
        plan = Plan()
        prev_topic, prev_student = None, None

        for raw in [s for s in _SPLIT.split(_clean(text)) if s.strip()]:
            seg = raw.strip()
            amb = []
            acts, topic = self._segment(seg, ctx, role, prev_topic, prev_student, plan, amb)
            # Student ka naam ambiguous ho to tabhi rukte hain jab action ko student chahiye
            if amb and any("student" in a.params for a in acts):
                plan.clarify = "Kaun sa student? Kai students ke naam milte hain, poora naam likhiye."
            if plan.clarify:
                plan.actions = []
                return plan
            if not acts:
                plan.unrecognized.append(seg)
                continue
            plan.actions.extend(acts)
            prev_topic = topic or prev_topic
            for a in acts:
                if a.params.get("student") is not None:
                    prev_student = a.params["student"]

        if len(plan.actions) > MAX_ACTIONS:
            plan.actions = []
            plan.clarify = f"Ek request mein sirf {MAX_ACTIONS} kaam ho sakte hain."
        return plan

    # ---------------- ek segment ----------------
    def _segment(self, seg, ctx, role, prev_topic, prev_student, plan, amb):
        A = lambda name, **params: PlannedAction(name, params, seg)
        has = lambda rx: re.search(rx, seg) is not None
        is_update = has(_UPDATE)
        has_marks = has(r"\b(marks?|scores?|results?|grades?)\b")
        topic = "marks" if has_marks else None

        # --- student reference ---
        student = None
        if has(_FIRST) and not has(r"\b(my|mere)\s+(students?|class)\b"):
            student = "self"
        pid = _person_match(seg, ctx.get("students", []), "student_id")
        m_id = re.search(r"\b(?:student|roll|id)\s*(?:no\.?|number|#)?\s*(\d+)\b", seg)
        if pid == "ambiguous":
            amb.append(True)
            pid = None
        if pid is not None:
            student = {"id": pid}
        elif m_id:
            student = {"id": int(m_id.group(1))}
        elif student is None and role == "student":
            student = "self"
        if student is None and prev_student is not None and not has(r"\b(students?|class)\b"):
            student = prev_student

        subj_ids = _subjects_in(seg, ctx.get("subjects", []))
        base = {"student": student}
        if subj_ids:
            base["subject_id"] = subj_ids[0]
        sem = re.search(r"\b(?:semester|sem)\s*(\d+)\b", seg)
        if sem:
            base["semester"] = int(sem.group(1))

        # --- 1. khatarnak actions (policy inhe block karegi) ---
        if has(r"\b(delete|remove|erase|hata|mita|drop|wipe)\b") and \
                has(r"\b(student|record|records|data|marks?|account|user|everything|all|database|table)\b"):
            return [A("DELETE_STUDENT", **base)], topic
        if has(r"\b(export|download|dump)\b") and has(r"\b(all|data|database|everything|students?)\b"):
            return [A("EXPORT_DATA")], topic

        # --- 2. admin ---
        m_user = re.search(r"\b(un)?lock\b.*?\b(?:user\s*)?([a-z]+\d{2,3}|\d+)\b", seg)
        if m_user:
            target = m_user.group(2)
            return [A("UNLOCK_USER" if m_user.group(1) else "LOCK_USER",
                      target_username=target.upper() if not target.isdigit() else None,
                      target_user_id=int(target) if target.isdigit() else None)], None

        # --- 3. approve / request marks change ---
        if has(r"\bapprove\b") and has(r"\b(marks?|change|request|correction)\b"):
            return [A("APPROVE_MARKS_CHANGE", **base)], "marks"
        if has(r"\brequest\b") and has_marks and has(r"\b(change|correction|revision|sudhar)\b"):
            return [A("REQUEST_MARKS_CHANGE", **base, value=_value(seg))], "marks"

        # --- 5. profile update ---
        if is_update and has(_FIRST) and not has_marks:
            fields = [f for f, rx in _PROFILE.items() if has(rx)]
            if fields:
                m = re.search(r"\b(?:to|se|ko)\s+(.+)$", seg)
                vals = {fields[0]: m.group(1).strip()[:120]} if m and len(fields) == 1 else {}
                return [A("UPDATE_OWN_PROFILE", faculty="self", fields=fields, values=vals)], None

        # --- 5. marks update ---
        if is_update and (has_marks or prev_topic == "marks") and (subj_ids or student or _value(seg) is not None):
            return [A("UPDATE_MARKS", **base, value=_value(seg))], "marks"

        # --- 7. reads ---
        out = []
        if has(r"\b(fail|failing|failed|failures?)\b") or has(r"\b(below|under|less than)\s*40\b") or has(r"\b40\s*se\s*kam\b"):
            return [A("LIST_FAILING_STUDENTS", department_id=None)], None
        if has(r"\b(revaluation|re-?evaluation|re-?check|rechecking|re-?valuation)\b"):
            out.append(A("REGISTER_REVALUATION", **base))
        elif has_marks:
            out.append(A("READ_MARKS", **base))
        if has(r"\b(fees?|dues?|shulk)\b"):
            out.append(A("READ_FEES", **base))
        if has(r"\b(attendance|hazri|present)\b"):
            out.append(A("READ_ATTENDANCE", **base))
        if has(r"\bnotifications?\b") or has(r"\bnotice\b"):
            out.append(A("READ_NOTIFICATIONS", user="self"))
        if has(r"\blogs?\b"):
            out.append(A("READ_LOGS"))
        if has(r"\balerts?\b"):
            out.append(A("READ_ALERTS"))
        if not out and has(r"\b(details?|profile|info|information)\b") and student is not None:
            out.append(A("READ_STUDENT", student=student))
        return out, topic