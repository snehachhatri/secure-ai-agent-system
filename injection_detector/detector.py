"""
Prompt Injection Detector (rule + normalization + scoring).

Output: risk_score 0-100 -> action allow / flag / block.
Fail closed: koi bhi error = block.
NOTE: Ye ek EXTRA layer hai. Asli safety gateway ka policy check hai.
"""
import base64
import re
import unicodedata
from dataclasses import dataclass, field

CONFIG = {
    "max_length": 2000,
    "flag_threshold": 30,      # is score se upar: allow + alert
    "block_threshold": 60,     # is score se upar: block + alert
    "secondary_weight": 0.5,   # baaki matches ka weight
    "obfuscation_bonus": 20,   # chhupa hua attack mile to extra score
    "signal_scores": {"hidden_characters": 15, "homoglyphs": 15, "encoded_content": 15},
}

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
    "і": "i", "ѕ": "s", "ј": "j", "һ": "h", "ԁ": "d", "ɡ": "g", "ո": "n",
})
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

# (id, category, score, regex)
RULES = [
    # --- instruction override ---
    ("override_en", "instruction_override", 70,
     r"\b(ignore|disregard|forget|override|bypass|skip)\b\W+(?:\w+\W+){0,3}?(previous|prior|above|earlier|all|any|your|the|these|those|existing)\W+(?:\w+\W+){0,2}?(instructions?|rules?|prompts?|polic(?:y|ies)|restrictions?|guidelines?|safeguards?|checks?)"),
    ("override_hi", "instruction_override", 70,
     r"\b(purane|pichle|pehle\s?ke|saare|sare|sabhi|ye|yeh|apne)\s+(?:(?:saare|sare|sabhi)\s+)?(rules?|niyam|instructions?|nirdesh|policy)\s+(?:ko\s+)?(bhool|bhul|ignore|ignor|mat\s+mano|hata|tod)"),
    ("override_hi2", "instruction_override", 70,
     r"\b(rules?|niyam|instructions?|policy|security)\s+(?:ko\s+)?(ignore|ignor|bhool|bhul|bypass|hata\s?do|tod\s?do|off\s?kar|band\s?kar)"),
    # --- role hijack ---
    ("role_hijack_en", "role_hijack", 65,
     r"\b(you\s+are\s+now|from\s+now\s+on\s+you\s+are|act\s+as|pretend\s+(?:to\s+be|you\s+are)|behave\s+as|roleplay\s+as|assume\s+the\s+role)\b\W+(?:\w+\W+){0,2}?(admin|administrator|hod|root|superuser|system|principal|developer|dean)"),
    ("role_hijack_hi", "role_hijack", 65,
     r"\b(ab\s+tum|tum\s+ab|ab\s+se\s+tum)\s+(?:\w+\s+){0,2}?(admin|hod|root|system|principal|developer)"),
    ("jailbreak", "role_hijack", 60,
     r"\b(jailbreak|dan\s+mode|developer\s+mode|god\s+mode|do\s+anything\s+now|no\s+restrictions)\b"),
    ("role_claim", "role_hijack", 35,
     r"\b(i\s+am|i'm|im|main|mai|mein)\s+(?:the\s+|ek\s+)?(admin|administrator|hod|principal|dean|root|superuser)\b"),
    # --- prompt leak ---
    ("prompt_leak", "prompt_leak", 65,
     r"\b(reveal|show|print|repeat|display|tell|leak|dump|output)\b\W+(?:\w+\W+){0,3}?(system\s+prompt|your\s+(?:prompt|instructions|rules|configuration|config)|hidden\s+(?:prompt|instructions))"),
    ("prompt_leak_hi", "prompt_leak", 65,
     r"\b(system\s+prompt|hidden\s+instructions?)\b.{0,20}\b(dikha|bata|batao|dikhao|print)"),
    # --- fake system / delimiter ---
    ("fake_delim", "fake_system", 60,
     r"(<\s*/?\s*(system|assistant|admin|instructions?)\s*>|\[\s*/?\s*(system|inst|admin)\s*\]|^\s*#{2,}\s*(system|instructions?)|end\s+of\s+(?:the\s+)?(?:instructions|prompt|rules)|new\s+instructions?\s*:|\bsystem\s*:\s)"),
    # --- security bypass / privilege ---
    ("disable_security", "security_bypass", 65,
     r"\b(disable|turn\s+off|switch\s+off|deactivate|stop|remove|skip)\b\W+(?:\w+\W+){0,2}?(security|gateway|policy|policies|logging|logs?|audit|verification|detector|monitoring|alerts?)"),
    ("no_logging", "security_bypass", 60,
     r"\bwithout\s+(?:any\s+)?(?:logging|checking|verification|permission|approval|audit|telling\s+(?:the\s+)?admin)\b"),
    ("grant_admin", "privilege_escalation", 65,
     r"\b(give|grant|make)\s+(?:me|us|my\s+account|this\s+account)\b\W+(?:\w+\W+){0,3}?(admin|administrator|root|superuser)\b"),
    ("grant_access", "privilege_escalation", 60,
     r"\b(give|grant)\s+(?:me|us)\W+(?:\w+\W+){0,2}?(full|unrestricted|elevated|admin)\s+(access|rights|privileges?|permissions?)"),
    ("role_change", "privilege_escalation", 60,
     r"\b(change|set|update|make|promote)\b\W+(?:\w+\W+){0,3}?(role|permission|access\s+level)\W+(?:\w+\W+){0,2}?(admin|hod|root|superuser)"),
    ("fake_auth", "privilege_escalation", 40,
     r"\b(i\s+have|i've\s+got|already\s+(?:have|got))\s+(?:\w+\s+){0,2}?(permission|authori[sz]ation|approval|clearance)\b|\b(authori[sz]ed|approved)\s+by\s+(?:the\s+)?(admin|hod|principal|dean)\b|\bmujhe\s+(?:\w+\s+){0,2}?permission\s+(?:hai|mili|mil\s+gayi)\b|\b(admin|hod|principal)\s+ne\s+(?:\w+\s+){0,2}?(permission|ijazat|approval)\b"),
    # --- bulk / destructive ---
    ("bulk_modify", "bulk_destructive", 70,
     r"\b(set|update|change|make|modify|edit)\b\W+(?:\w+\W+){0,3}?(all|every|everyone|entire|whole)\b(?!\W+my\b)\W+(?:\w+\W+){0,3}?(students?|records?|marks|users?|faculty|grades?|fees?|data|database|table)"),
    ("bulk_delete", "bulk_destructive", 75,
     r"\b(delete|remove|erase|wipe|drop|truncate|purge|destroy)\b\W+(?:\w+\W+){0,3}?(all|every|everyone|entire|whole|database|table)\b"),
    ("bulk_hi", "bulk_destructive", 70,
     r"\b(sabke|sabhi|saare|sare|poori\s+class\s+ke|puri\s+class\s+ke)\b\W+(?:\w+\W+){0,3}?(marks?|fees?|records?|data|grades?|attendance)\b\W+(?:\w+\W+){0,4}?(100|badal|change|update|set|kar\s?do|delete|hata|mita)"),
    ("destructive_verb", "bulk_destructive", 35,
     r"\b(delete|erase|wipe|drop|truncate|purge|destroy)\b"),
    # --- SQL injection ---
    ("sql", "sql_injection", 70,
     r"('\s*;|;\s*(drop|delete|update|insert|alter|truncate)\b|\bunion\s+select\b|\bor\s+1\s*=\s*1\b|\bor\s+'1'\s*=\s*'1'|--\s*$|/\*.*\*/|\b(drop|truncate)\s+table\b|\bxp_cmdshell\b)"),
    # --- data exfiltration ---
    ("exfil_secret", "data_exfiltration", 50,
     r"\b(show|reveal|dump|print|export|list|give|send|email|leak)\b\W+(?:\w+\W+){0,3}?(passwords?|password\s+hash(?:es)?|hashes|tokens?|jwt|api\s*keys?|secrets?|credentials|\.env|connection\s+string)\b"),
    ("exfil_bulk", "data_exfiltration", 45,
     r"\b(export|dump|download|extract|exfiltrate)\b\W+(?:\w+\W+){0,3}?(everything|entire|whole|database)\b"),
]
_COMPILED = [(i, c, s, re.compile(rx, re.IGNORECASE | re.MULTILINE)) for i, c, s, rx in RULES]

_READ = r"(show|display|list|get|fetch|view|dikha|dikhao|batao|bata|dekho|dikhado)"
_WRITE = r"(update|change|set|delete|remove|modify|edit|badal|badlo|approve|lock|unlock|grant)"
_JOIN = r"(and|also|aur|saath|phir|then|&|,|\.|;)"
_MIXED = re.compile(rf"\b{_READ}\b.{{0,80}}\b{_JOIN}\b.{{0,20}}\b{_WRITE}\b", re.IGNORECASE)


@dataclass
class InjectionResult:
    risk_score: int
    level: str                 # low / medium / high
    action: str                # allow / flag / block
    reason: str
    matches: list = field(default_factory=list)   # [{"rule","category","score","obfuscated"}]
    signals: list = field(default_factory=list)


def _squash_spaced_letters(t: str) -> str:
    """'i g n o r e' / 'i.g.n.o.r.e' -> 'ignore'"""
    return re.sub(r"(?<![a-z])(?:[a-z][ .\-_*]){2,}[a-z](?![a-z])",
                  lambda m: re.sub(r"[ .\-_*]", "", m.group(0)), t)


def _unleet(t: str) -> str:
    def fix(m):
        w = m.group(0)
        return w.translate(_LEET) if re.search(r"[a-z]", w) and re.search(r"[0@$13457]", w) else w
    return re.sub(r"[a-z0-9@$]+", fix, t)


def _collapse(t: str) -> str:
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def _decode_base64(original: str):
    out = []
    for m in re.finditer(r"[A-Za-z0-9+/]{16,}={0,2}", original):
        chunk = m.group(0)
        try:
            raw = base64.b64decode(chunk + "=" * (-len(chunk) % 4), validate=True)
            s = raw.decode("utf-8")
        except Exception:
            continue
        if len(s) >= 8 and sum(c.isalpha() or c == " " for c in s) / len(s) > 0.8:
            out.append(s)
    return out


def detect(text) -> InjectionResult:
    try:
        return _detect(text)
    except Exception as e:   # fail closed
        return InjectionResult(100, "high", "block", f"detector error, isliye block: {e}",
                               signals=["fail_closed"])


def _detect(text) -> InjectionResult:
    if not isinstance(text, str):
        return InjectionResult(100, "high", "block", "input text nahi hai", signals=["bad_input"])
    if len(text) > CONFIG["max_length"]:
        return InjectionResult(100, "high", "block",
                               f"request bahut lambi hai (max {CONFIG['max_length']} chars)",
                               signals=["too_long"])
    if not text.strip():
        return InjectionResult(0, "low", "allow", "empty request")

    signals = []
    t = unicodedata.normalize("NFKC", text)
    stripped = t.translate(_ZERO_WIDTH)
    stripped = "".join(c for c in stripped if c in "\n\t" or unicodedata.category(c) != "Cc")
    if stripped != t:
        signals.append("hidden_characters")
    lowered = stripped.lower()
    mapped = lowered.translate(_HOMOGLYPHS)     # lowercase ke baad, taaki capital lookalike bhi pakde
    if mapped != lowered:
        signals.append("homoglyphs")

    decoded = _decode_base64(stripped)          # base64 case-sensitive hai
    if decoded:
        signals.append("encoded_content")

    lowered = mapped
    views = {"clean": _collapse(lowered),
             "deobfuscated": _collapse(_unleet(_squash_spaced_letters(lowered)))}
    for i, d in enumerate(decoded):
        views[f"base64_{i}"] = _collapse(d.lower())

    hits = {}
    for rid, cat, score, rx in _COMPILED:
        for vname, v in views.items():
            if rx.search(v):
                obf = vname != "clean"
                if rid not in hits or (hits[rid]["obfuscated"] and not obf):
                    hits[rid] = {"rule": rid, "category": cat, "score": score,
                                 "obfuscated": obf, "view": vname}
    # Ek hi category ke sab rules ek saath na gine: category ka sabse bada score lo
    best = {}
    for h in hits.values():
        s = h["score"] + (CONFIG["obfuscation_bonus"] if h["obfuscated"] else 0)
        if h["category"] not in best or s > best[h["category"]][0]:
            best[h["category"]] = (s, h)

    scores = sorted((s for s, _ in best.values()), reverse=True)
    if _MIXED.search(views["clean"]):
        signals.append("mixed_read_write_intent")
        scores.append(20)
    for sig in signals:
        scores.append(CONFIG["signal_scores"].get(sig, 0))
    scores = sorted((s for s in scores if s > 0), reverse=True)

    total = 0.0
    if scores:
        total = scores[0] + CONFIG["secondary_weight"] * sum(scores[1:])
    total = int(min(100, round(total)))

    if total >= CONFIG["block_threshold"]:
        level, action = "high", "block"
    elif total >= CONFIG["flag_threshold"]:
        level, action = "medium", "flag"
    else:
        level, action = "low", "allow"

    matches = [dict(h) for _, h in best.values()]
    cats = ", ".join(sorted(h["category"] for _, h in best.values())) or "none"
    reason = {"allow": "no injection pattern", "flag": f"suspicious ({cats})",
              "block": f"injection detected ({cats})"}[action]
    return InjectionResult(total, level, action, reason, matches, signals)
