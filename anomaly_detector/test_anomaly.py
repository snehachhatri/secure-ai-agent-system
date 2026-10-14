from datetime import datetime, timedelta
from collections import defaultdict
from anomaly import evaluate, plan_response, Event, extract_features, get_ml
from synthetic import normal_sessions, attack_scenarios


def run_session(events, use_ml=True):
    """Gateway ki tarah: ek ek event aaye, history se evaluate. Worst result + pehla alert."""
    hist, worst, first_flag = [], None, None
    order = {"allow": 0, "alert": 1, "throttle": 2, "lock": 3}
    for i, ev in enumerate(events):
        r = evaluate(hist, ev, use_ml)
        hist.append(ev)
        if first_flag is None and r.action != "allow":
            first_flag = i + 1
        if worst is None or order[r.action] > order[worst.action]:
            worst = r
    return worst, first_flag


print("ML model train ho raha hai (synthetic normal logs)...")
get_ml()
t0 = datetime(2026, 10, 1, 11, 0)
E = lambda uid, role, act, dec, sev, t, tg=None, rec=1, inj=0: Event(uid, role, act, dec, sev, t, tg, rec, inj)

# ---------- 1. Handwritten unit cases ----------
cases = []
# (name, events, role, expected_action_set)
cases.append(("normal student: 3 apni requests",
    [E(1, "student", "READ_MARKS", "allowed", "none", t0 + timedelta(seconds=40 * i), 101) for i in range(3)], {"allow"}))
cases.append(("student: 1 galti se blocked",
    [E(1, "student", "READ_MARKS", "allowed", "none", t0, 101),
     E(1, "student", "UPDATE_MARKS", "blocked", "medium", t0 + timedelta(seconds=30), 101)], {"allow"}))
cases.append(("faculty: 6 marks 3 min mein (normal kaam)",
    [E(2, "faculty", "UPDATE_MARKS", "allowed", "none", t0 + timedelta(seconds=30 * i), 200 + i) for i in range(6)], {"allow"}))
cases.append(("hod: 10 students dekhna",
    [E(3, "hod", "READ_MARKS", "allowed", "none", t0 + timedelta(seconds=20 * i), 300 + i) for i in range(10)], {"allow"}))
cases.append(("student: 3 baar blocked 10 min mein",
    [E(4, "student", "UPDATE_MARKS", "blocked", "medium", t0 + timedelta(seconds=60 * i), 104) for i in range(3)], {"alert", "throttle"}))     # lock NAHI, sirf alert
cases.append(("student: 5 baar blocked -> LOCK",
    [E(5, "student", "UPDATE_MARKS", "blocked", "medium", t0 + timedelta(seconds=30 * i), 105) for i in range(5)], {"lock"}))
cases.append(("3 high-severity blocks -> LOCK",
    [E(6, "faculty", "DELETE_STUDENT", "blocked", "high", t0 + timedelta(minutes=10 * i), 9) for i in range(3)], {"lock"}))
cases.append(("rate: 25 requests 25 sec mein -> throttle/lock",
    [E(7, "student", "READ_MARKS", "allowed", "none", t0 + timedelta(seconds=i), 107) for i in range(25)], {"throttle", "lock"}))
cases.append(("student 5 alag logon ka data -> alert",
    [E(8, "student", "READ_MARKS", "allowed", "none", t0 + timedelta(seconds=20 * i), 500 + i) for i in range(5)], {"alert", "lock", "throttle"}))
cases.append(("faculty: ek request mein 30 records",
    [E(9, "faculty", "UPDATE_MARKS", "allowed", "none", t0, 1, rec=30)], {"alert", "lock"}))
cases.append(("raat 3 baje normal single request",
    [E(10, "student", "READ_MARKS", "allowed", "none", t0.replace(hour=3), 110)], {"allow", "alert"}))
cases.append(("injection spree 4 baar",
    [E(11, "student", "PROMPT_INJECTION", "blocked", "high", t0 + timedelta(seconds=40 * i), None, 1, 80) for i in range(4)], {"alert", "lock"}))
cases.append(("alag user ki history mix na ho",
    [E(12, "student", "READ_MARKS", "allowed", "none", t0, 112)], {"allow"}))

passed = 0
print("\n=== UNIT CASES ===")
for name, evs, ok_set in cases:
    r, _ = run_session(evs)
    ok = r.action in ok_set
    passed += ok
    print(("PASS" if ok else "FAIL"), f"| {name} -> {r.action} (score {r.score})", "|", "; ".join(r.reasons)[:80])

# user isolation
hist = [E(99, "student", "UPDATE_MARKS", "blocked", "high", t0 + timedelta(seconds=i), 1) for i in range(6)]
r = evaluate(hist, E(12, "student", "READ_MARKS", "allowed", "none", t0 + timedelta(seconds=10), 112))
ok = r.action == "allow"
passed += ok
print(("PASS" if ok else "FAIL"), "| dusre user ki history is user par asar nahi daalti ->", r.action)

# response plan
r, _ = run_session(cases[5][1])
plan = plan_response(r)
ok = plan["lock_user"] and plan["reject_request"] and plan["create_alert"] and plan["needs_admin_review"]
passed += ok
print(("PASS" if ok else "FAIL"), "| lock case ka response plan sahi ->", plan["lock_user"])
r, _ = run_session(cases[0][1])
plan = plan_response(r)
ok = not plan["lock_user"] and not plan["create_alert"]
passed += ok
print(("PASS" if ok else "FAIL"), "| normal case: koi alert/lock nahi")
total_unit = len(cases) + 3
print(f"Unit: {passed}/{total_unit}")

# ---------- 2. Evaluation: naye (unseen) normal sessions vs attack scenarios ----------
print("\n=== EVALUATION ===")
normal = normal_sessions(seed=777, n_users=60, days=3)      # training se alag seed
fp_sessions = lock_fp = 0
for sess in normal:
    r, _ = run_session(sess)
    fp_sessions += r.action != "allow"
    lock_fp += r.action in ("lock", "throttle")
print(f"Normal sessions: {len(normal)} | galat alert/lock: {fp_sessions} ({fp_sessions/len(normal)*100:.1f}%) | galat LOCK/THROTTLE: {lock_fp}")

attacks = attack_scenarios(seed=1)
by = defaultdict(lambda: [0, 0, 0])      # total, caught(rules+ml), caught(ml only)
for name, evs, role in attacks:
    r, _ = run_session(evs, use_ml=True)
    r_rules, _ = run_session(evs, use_ml=False)
    by[name][0] += 1
    by[name][1] += r.action != "allow"
    by[name][2] += r_rules.action != "allow"
tot = caught = caught_rules = 0
for name, (n, c, cr) in by.items():
    tot += n; caught += c; caught_rules += cr
    print(f"  {name:18} caught {c}/{n} (sirf rules: {cr}/{n})")
print(f"Attack detection: {caught}/{tot} = {caught/tot*100:.1f}% (sirf rules: {caught_rules/tot*100:.1f}%)")
print(f"False positive (normal sessions): {fp_sessions/len(normal)*100:.1f}%")


# ---------- 3. Honest ML test: attacks jo KISI rule ki limit paar nahi karte ----------
print("\n=== ML KA ASLI KAAM: rules se bachne wale ajeeb patterns ===")
import random
rng = random.Random(5)
sneaky = []
for k in range(40):
    uid = 8000 + k
    t1 = datetime(2026, 10, 2, 11, 0) + timedelta(minutes=k)
    kind = k % 4
    if kind == 0:   # student 18 req/min, lagatar 8 minute (rate limit 20 se neeche)
        evs = [E(uid, "student", "READ_MARKS", "allowed", "none", t1 + timedelta(seconds=3.3 * i), uid) for i in range(140)]
    elif kind == 1:  # student: har request alag action, 2 target, 2 blocked, bahut tez
        acts = ["READ_MARKS", "READ_FEES", "READ_ATTENDANCE", "UPDATE_MARKS", "READ_FACULTY_AVAILABILITY"]
        evs = [E(uid, "student", acts[i % 5], "blocked" if i % 6 == 0 else "allowed", "medium" if i % 6 == 0 else "none",
                 t1 + timedelta(seconds=4 * i), uid + (i % 2)) for i in range(60)]
    elif kind == 2:  # faculty 19 req/min lagatar, records 5, raat ko
        evs = [E(uid, "faculty", "UPDATE_MARKS", "allowed", "none", t1.replace(hour=2) + timedelta(seconds=3.1 * i), i % 15, rec=5) for i in range(120)]
    else:            # admin: bahut zyada alag actions, tez
        acts = ["READ_LOGS", "READ_ALERTS", "LOCK_USER", "UNLOCK_USER"]
        evs = [E(uid, "admin", acts[i % 4], "allowed", "none", t1.replace(hour=4) + timedelta(seconds=3 * i)) for i in range(100)]
    sneaky.append(evs)
ml_c = rules_c = 0
for evs in sneaky:
    rm, _ = run_session(evs, use_ml=True)
    rr, _ = run_session(evs, use_ml=False)
    ml_c += rm.action != "allow"
    rules_c += rr.action != "allow"
print(f"Rules + ML : {ml_c}/{len(sneaky)} pakde")
print(f"Sirf rules : {rules_c}/{len(sneaky)} pakde")
