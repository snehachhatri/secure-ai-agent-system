"""Synthetic logs: normal behaviour (training) + attack scenarios (testing)."""
import random
from datetime import datetime, timedelta

ROLES = {
    # sessions/day, events/session, target pool, records range, block prob
    "student": dict(sessions=(1, 3), events=(1, 6), pool=0, records=(1, 1), block=0.03),
    "faculty": dict(sessions=(1, 4), events=(2, 12), pool=20, records=(1, 3), block=0.03),
    "hod":     dict(sessions=(1, 3), events=(3, 15), pool=50, records=(1, 5), block=0.03),
    "admin":   dict(sessions=(2, 5), events=(3, 20), pool=0, records=(1, 1), block=0.0),
}
ACTIONS = {
    "student": ["READ_MARKS", "READ_FEES", "READ_ATTENDANCE", "READ_FACULTY_AVAILABILITY"],
    "faculty": ["READ_MARKS", "UPDATE_MARKS", "SET_OWN_LEAVE", "UPDATE_OWN_PROFILE"],
    "hod": ["READ_STUDENT", "READ_MARKS", "LIST_FAILING_STUDENTS", "APPROVE_MARKS_CHANGE"],
    "admin": ["READ_LOGS", "READ_ALERTS", "LOCK_USER"],
}


def _import():
    from anomaly import Event
    return Event


def normal_sessions(seed, n_users=60, days=3, base=datetime(2026, 9, 1)):
    """Returns list of sessions; har session = list[Event] (ek user, ek baar baithna)."""
    Event = _import()
    rng = random.Random(seed)
    sessions = []
    roles = list(ROLES)
    for uid in range(1, n_users + 1):
        role = roles[uid % len(roles)]
        p = ROLES[role]
        own_target = 1000 + uid
        for day in range(days):
            for _ in range(rng.randint(*p["sessions"])):
                hour = rng.choices([rng.randint(9, 17), rng.randint(18, 22)], weights=[95, 5])[0]
                t = base + timedelta(days=day, hours=hour, minutes=rng.randint(0, 59))
                sess = []
                for _ in range(rng.randint(*p["events"])):
                    t += timedelta(seconds=rng.randint(5, 90))
                    blocked = rng.random() < p["block"]
                    if role == "student":
                        target = own_target
                    elif p["pool"]:
                        target = rng.randint(1, p["pool"])
                    else:
                        target = None
                    sess.append(Event(
                        user_id=uid, role=role, action=rng.choice(ACTIONS[role]),
                        decision="blocked" if blocked else "allowed",
                        severity="medium" if blocked else "none", ts=t, target_id=target,
                        records=rng.randint(*p["records"]),
                        injection_score=20 if rng.random() < 0.03 else 0))
                sessions.append(sess)
    return sessions


def normal_feature_rows(seed=42):
    from anomaly import extract_features
    rows = []
    history_by_user = {}
    for sess in normal_sessions(seed, n_users=80, days=5):
        for ev in sess:
            h = history_by_user.setdefault(ev.user_id, [])
            rows.append(extract_features(h, ev))
            h.append(ev)
    return rows


# ---------------- Attack scenarios ----------------

def attack_scenarios(seed, base=datetime(2026, 10, 1, 11, 0)):
    """Returns list of (name, list[Event], role)."""
    Event = _import()
    rng = random.Random(seed)
    out = []

    def ev(uid, role, action, dec, sev, t, target=None, rec=1, inj=0):
        return Event(uid, role, action, dec, sev, t, target, rec, inj)

    for k in range(15):
        uid = 5000 + k * 10
        t0 = base + timedelta(minutes=rng.randint(0, 120))
        # 1 Rapid fire
        out.append(("rapid_fire", [ev(uid, "student", "READ_MARKS", "allowed", "none",
                    t0 + timedelta(seconds=i), uid) for i in range(rng.randint(30, 60))], "student"))
        # 2 Repeated blocked
        out.append(("repeated_blocked", [ev(uid + 1, "student", rng.choice(["UPDATE_MARKS", "DELETE_STUDENT"]),
                    "blocked", "medium", t0 + timedelta(seconds=40 * i), uid + 1) for i in range(rng.randint(6, 9))], "student"))
        # 3 Repeated high severity
        out.append(("repeated_high_sev", [ev(uid + 2, "faculty", "DELETE_STUDENT", "blocked", "high",
                    t0 + timedelta(minutes=5 * i), 7) for i in range(3)], "faculty"))
        # 4 Student scraping others
        out.append(("student_scraping", [ev(uid + 3, "student", "READ_MARKS", "blocked", "medium",
                    t0 + timedelta(seconds=30 * i), 2000 + i) for i in range(rng.randint(4, 8))], "student"))
        # 5 Off hours bulk
        night = base.replace(hour=3, minute=rng.randint(0, 59))
        out.append(("offhours_bulk", [ev(uid + 4, "faculty", "UPDATE_MARKS", "allowed", "none",
                    night + timedelta(seconds=20 * i), 100 + i, rec=rng.randint(6, 40)) for i in range(4)], "faculty"))
        # 6 Injection spree
        out.append(("injection_spree", [ev(uid + 5, "student", "PROMPT_INJECTION", "blocked", "high",
                    t0 + timedelta(seconds=50 * i), None, 1, 80) for i in range(rng.randint(3, 5))], "student"))
        # 7 Low and slow (har 8 min mein ek blocked, 1 ghante mein 7)
        out.append(("low_and_slow", [ev(uid + 6, "student", "UPDATE_MARKS", "blocked", "medium",
                    t0 + timedelta(minutes=8 * i), uid + 6) for i in range(8)], "student"))
        # 8 HOD data harvesting (bahut zyada students)
        out.append(("hod_harvesting", [ev(uid + 7, "hod", "READ_MARKS", "allowed", "none",
                    t0 + timedelta(seconds=10 * i), 3000 + i) for i in range(40)], "hod"))
    return out
