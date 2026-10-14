"""
Anomaly Detection + Threat Response.

Do layers:
  1. RULES  : seedhe, samajh aane wale (repeated blocks, rate, cross-user access...)
  2. ML     : Isolation Forest, normal behaviour seekhta hai (synthetic logs par)

Output: score 0-100 -> allow / alert / throttle / lock
ML akela kabhi account LOCK nahi karta (false positive ka risk), sirf alert.
Ye module DB se nahi judta: gateway user ke recent events (requests_logs se) deta hai.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest

CONFIG = {
    "alert_threshold": 30,
    "high_threshold": 60,
    "lock_threshold": 80,
    "secondary_weight": 0.5,
    "ml_weight": 0.7,          # ML score ka weight (max 70 -> kabhi akela lock nahi)
    "rate_limit_per_min": 20,
    "blocked_10min_alert": 3,
    "blocked_10min_lock": 5,
    "high_blocked_1h_lock": 3,
    "blocked_1h_alert": 6,
    "max_records": 5,
    "off_hours": (23, 6),      # raat 11 se subah 6
    # ek user 10 minute mein kitne ALAG-ALAG logon ka data maang sakta hai
    "target_limit": {"student": 2, "faculty": 15, "hod": 30, "admin": 0},
}
ROLE_CODE = {"student": 0, "faculty": 1, "hod": 2, "admin": 3}
FEATURES = ["req_1min", "blocked_10min", "blocked_1h", "high_blocked_1h",
            "distinct_targets_10min", "off_hours", "max_records_10min",
            "mean_injection_10min", "distinct_actions_10min", "role_code"]


@dataclass
class Event:
    user_id: int
    role: str
    action: str
    decision: str                 # "allowed" / "blocked"
    severity: str                 # none / low / medium / high
    ts: datetime
    target_id: Optional[int] = None
    records: int = 1
    injection_score: int = 0


@dataclass
class AnomalyResult:
    score: int
    level: str                    # low / medium / high / critical
    action: str                   # allow / alert / throttle / lock
    reasons: list = field(default_factory=list)
    rule_score: int = 0
    ml_score: int = 0
    features: dict = field(default_factory=dict)


# ---------------- Features ----------------

def extract_features(history, new: Event) -> dict:
    now = new.ts
    evs = [e for e in history if e.user_id == new.user_id and e.ts <= now] + [new]

    def within(sec):
        return [e for e in evs if (now - e.ts).total_seconds() <= sec]

    m1, m10, h1 = within(60), within(600), within(3600)
    start, end = CONFIG["off_hours"]
    return {
        "req_1min": len(m1),
        "blocked_10min": sum(e.decision == "blocked" for e in m10),
        "blocked_1h": sum(e.decision == "blocked" for e in h1),
        "high_blocked_1h": sum(e.decision == "blocked" and e.severity == "high" for e in h1),
        "distinct_targets_10min": len({e.target_id for e in m10 if e.target_id is not None}),
        "off_hours": int(now.hour >= start or now.hour < end),
        "max_records_10min": max(e.records for e in m10),
        "mean_injection_10min": sum(e.injection_score for e in m10) / len(m10),
        "distinct_actions_10min": len({e.action for e in m10}),
        "role_code": ROLE_CODE.get(new.role, 0),
    }


# ---------------- Layer 1: Rules ----------------

def rule_scores(f: dict, role: str):
    """[(score, reason, tag)]"""
    out = []
    c = CONFIG
    if f["req_1min"] > c["rate_limit_per_min"]:
        out.append((70, f"bahut tez requests: 1 minute mein {f['req_1min']}", "rate"))
    if f["blocked_10min"] >= c["blocked_10min_lock"]:
        out.append((90, f"10 min mein {f['blocked_10min']} baar blocked", "blocks"))
    elif f["blocked_10min"] >= c["blocked_10min_alert"]:
        out.append((60, f"10 min mein {f['blocked_10min']} baar blocked", "blocks"))
    if f["high_blocked_1h"] >= c["high_blocked_1h_lock"]:
        out.append((90, f"1 ghante mein {f['high_blocked_1h']} high-severity block", "high_blocks"))
    if f["blocked_1h"] >= c["blocked_1h_alert"]:
        out.append((70, f"1 ghante mein {f['blocked_1h']} baar blocked (dheere dheere koshish)", "slow_probe"))
    limit = c["target_limit"].get(role, 5)
    if f["distinct_targets_10min"] > limit:
        out.append((70, f"10 min mein {f['distinct_targets_10min']} alag logon ka data maanga (limit {limit})", "cross_user"))
    if f["max_records_10min"] > c["max_records"]:
        out.append((50, f"ek request mein {f['max_records_10min']} records", "bulk"))
    if f["mean_injection_10min"] >= 30:
        out.append((45, "baar-baar suspicious text bheja", "injection_spree"))
    if f["off_hours"]:
        out.append((20, "raat ke odd hours mein activity", "off_hours"))
    return out


# ---------------- Layer 2: ML (Isolation Forest) ----------------

class _MLModel:
    def __init__(self):
        self.model = None
        self.threshold = 0.0
        self.floor = -1.0

    def fit(self, rows):
        X = np.array([[r[k] for k in FEATURES] for r in rows], dtype=float)
        self.model = IsolationForest(n_estimators=150, contamination="auto", random_state=42)
        self.model.fit(X)
        d = self.model.decision_function(X)
        self.threshold = float(np.percentile(d, 0.5))     # normal data ke sabse ajeeb 0.5%
        self.floor = float(d.min())
        return self

    def score(self, f: dict) -> int:
        x = np.array([[f[k] for k in FEATURES]], dtype=float)
        d = float(self.model.decision_function(x)[0])
        if d >= self.threshold:
            return 0
        span = max(self.threshold - self.floor, 1e-6)
        return int(min(100, 40 + 60 * (self.threshold - d) / span))


_ML = None

def get_ml():
    """Pehli baar synthetic normal logs par train, phir cache."""
    global _ML
    if _ML is None:
        from synthetic import normal_feature_rows
        _ML = _MLModel().fit(normal_feature_rows(seed=42))
    return _ML


# ---------------- Main ----------------

def evaluate(history, new: Event, use_ml: bool = True) -> AnomalyResult:
    try:
        return _evaluate(history, new, use_ml)
    except Exception as e:
        # anomaly module fail ho to bhi policy engine safe hai; yahan alert dete hain
        return AnomalyResult(50, "medium", "alert", [f"anomaly module error: {e}"])


def _evaluate(history, new, use_ml):
    f = extract_features(history, new)
    rules = rule_scores(f, new.role)
    reasons = [r for _, r, _ in rules]
    scores = [s for s, _, _ in rules]
    rule_total = _combine(scores)

    ml_score = 0
    if use_ml:
        try:
            ml_score = int(get_ml().score(f) * CONFIG["ml_weight"])
        except Exception:
            ml_score = 0
        if ml_score >= CONFIG["alert_threshold"]:
            reasons.append("ML: behaviour user ke normal pattern se alag hai")
            scores.append(ml_score)

    total = _combine(scores)
    # ML akela (ya ML ke saath judkar) lock tak nahi pahuncha sakta: lock sirf rules se
    if rule_total < CONFIG["lock_threshold"] and total >= CONFIG["lock_threshold"]:
        total = CONFIG["lock_threshold"] - 1
    tags = {t for _, _, t in rules}

    if total >= CONFIG["lock_threshold"]:
        level, action = "critical", "lock"
    elif "rate" in tags and total < CONFIG["lock_threshold"]:
        level, action = "high", "throttle"
    elif total >= CONFIG["high_threshold"]:
        level, action = "high", "alert"
    elif total >= CONFIG["alert_threshold"]:
        level, action = "medium", "alert"
    else:
        level, action = "low", "allow"
    return AnomalyResult(total, level, action, reasons, rule_total, ml_score, f)


def _combine(scores):
    s = sorted((x for x in scores if x > 0), reverse=True)
    if not s:
        return 0
    return int(min(100, round(s[0] + CONFIG["secondary_weight"] * sum(s[1:]))))


# ---------------- Threat Response ----------------

def plan_response(result: AnomalyResult) -> dict:
    """Gateway ke liye instructions. Ye module khud DB nahi chhuta."""
    sev = {"low": "none", "medium": "medium", "high": "high", "critical": "high"}[result.level]
    return {
        "reject_request": result.action in ("throttle", "lock"),
        "lock_user": result.action == "lock",
        "create_alert": result.action != "allow",
        "severity": sev,
        "message": "; ".join(result.reasons) or "normal",
        "needs_admin_review": result.action in ("lock",) or result.level == "high",
    }
