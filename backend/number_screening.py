"""
Number screening service — scam/legit number verdict.

Ye module pehle `main.py` me inline tha, jahan sirf 2 legit numbers aur ek
khali scam list thi. Isi wajah se mobile ka `syncRules()` fail hota tha
(`/number-lists` route hi nahi tha) aur native rules empty rehte thay —
jis ka seedha asar ye hota tha ke HBL 111-111-425 jaise REAL helpline
numbers bhi "unknown 111 UAN" → SUSPICIOUS lag jate thay.

Verdict ka matlab (ye poori false-positive control ki backbone hai):
    safe       — verified official (bank/govt/wallet/telco) ya saved contact
    scam       — community-reported, ya verified UAN ka copy-cat impersonation
    suspicious — bank-style UAN shape jo verified list me nahi (pakka scam nahi)
    unknown    — "pata nahi". Personal mobile / landline / short code.
                 ❌ KOI ALERT NAHI. Pakistan me ye POORE Jazz/Zong/Tenor/
                 Ufone + delivery + govt helplines ka range hai — inhe
                 "suspicious" kehlaana har dost par alert hai.
"""

import json
import os
import threading
import time
from flask import request

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

with open(os.path.join(_DATA_DIR, "verified_numbers.json"), "r", encoding="utf-8") as f:
    VERIFIED_ENTRIES = json.load(f)

# number -> entity name
DIRECTORY: dict[str, str] = {e["number"]: e["entity"] for e in VERIFIED_ENTRIES}
LEGITIMATE_NUMBERS: list[str] = sorted(DIRECTORY.keys())

# Community-reported scam numbers (runtime me barhti hain)
_SCAM_NUMBERS: set[str] = set()

# Community reports: number -> {reporter_id: timestamp}
_REPORTS: dict[str, dict[str, float]] = {}
REPORTS_NEEDED_FOR_CONSENSUS = 5

# Pakistan landline area codes — bank/government helplines inke saath
# advertise hote hain (021-111-825-888 = UBL Karachi).
AREA_CODES = {
    "021", "022", "025", "031", "032", "033", "034", "041", "042",
    "045", "048", "049", "051", "052", "053", "054", "055", "061",
    "061", "064", "068", "069", "071", "072", "073", "074", "081",
    "082", "083", "091", "092", "093", "094", "095", "099",
}

_lock = threading.Lock()


def request_fingerprint() -> str:
    """Fallback reporter id jab client ne apni device id nahi bheji.

    Weak hai (aik Wi-Fi ke sab devices same), magar aik banda 5 baar tap
    kar ke block karne se behtar. Client device id bhejega to ye use nahi hota.
    """
    try:
        return f"ip:{request.remote_addr or 'unknown'}"
    except RuntimeError:
        # Flask app context ke bahar (e.g. unit tests) — request nahi hai.
        return "ip:no-context"


def clean_number(raw: str) -> str:
    """+92 / 0092 hatao, area-code hatao, aur leading zero EK hatao.

    Sirf ek leading zero — `lstrip('0')` poora zero-strip kar deta tha, jis
    se 0800-55055 (PTA) jaise short UAN galat normalize hote.

    AREA-CODE strip zaroori hai: Pakistani banks apne helpline "021-111-
    825-888" (Karachi), "051-111-111-425" (Islamabad) ke roop me advertise
    karte hain. Bina iske 12-digit number kabhi match hi nahi hota tha aur
    HBL/UBL ka official number "unknown" → SUSPICIOUS ho jata tha — yaani
    bank ka apna helpline hi scam alert de raha tha.
    """
    if not raw:
        return ""
    c = str(raw).replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if c.startswith("+92"):
        c = c[3:]
    elif c.startswith("0092"):
        c = c[4:]
    # "051111111425" (12 digits, landline with area code) → "111111425".
    # Sirf tab jab pehle 3 digits ek known area code hain — 10-digit mobile
    # numbers (3001234567) kabhi affected nahi hote.
    if len(c) >= 12 and c[:3].isdigit() and c[:3] in AREA_CODES:
        c = c[3:]
    if c.startswith("0"):
        c = c[1:]
    return c


def impersonates(cleaned: str, known: set[str] | None = None) -> bool:
    """Verified UAN se 1–2 digit door ka number = bank impersonation.

    Guards (FP bachane ke liye):
      - candidate khud verified list me na ho
      - same prefix family (pehle 3 digits)
      - same length
      - sirf 1–2 digit ka farq
    """
    if len(cleaned) < 7 or not cleaned.isdigit():
        return False
    pool = known if known is not None else set(DIRECTORY.keys())
    for legit in pool:
        if not legit.isdigit() or len(legit) != len(cleaned):
            continue
        if legit == cleaned or legit[:3] != cleaned[:3]:
            continue
        distance = sum(1 for a, b in zip(legit, cleaned) if a != b)
        if 1 <= distance <= 2:
            return True
    return False


def check_number(raw_number: str, is_saved_contact: bool = False) -> dict:
    """4-level verdict. Order wahi hai jo mobile ke `NumberRules.classify()`
    aur `CallerIDService.checkCallerID()` use karte hain — teeno jagah
    online aur offline ka jawab ek jaisa hona chahie.
    """
    cleaned = clean_number(raw_number)
    if not cleaned:
        return {"status": "error", "message": "Invalid number", "confidence": "low"}

    with _lock:
        scam = set(_SCAM_NUMBERS)
        reports = len(_REPORTS.get(cleaned, []))

    # 1. Community-reported scam — sab se authoritative.
    if cleaned in scam:
        return {
            "status": "scam",
            "message": "Ye number community me fraudulent report kiya gaya hai.",
            "confidence": "high",
            "report_count": reports,
            "source": "community",
        }

    # 2. Verified official — bank/govt/wallet helpline.
    if cleaned in DIRECTORY:
        return {
            "status": "safe",
            "entity": DIRECTORY[cleaned],
            "message": f"Verified official number — {DIRECTORY[cleaned]}.",
            "confidence": "high",
        }

    # 3. Saved contact — user ke apne phonebook ka. Is number ko alert karna
    #    hamesha galat hota hai (har dost, har family member).
    if is_saved_contact:
        return {
            "status": "safe",
            "entity": "Saved contact",
            "message": "Aapke phonebook me saved number.",
            "confidence": "high",
        }

    # 4. Chhote random numbers — koi matlab nahi.
    if len(cleaned) < 7:
        return {
            "status": "unknown",
            "message": "Number not in database. Verify independently before sharing information.",
            "confidence": "low",
        }

    # 5. Copy-cat impersonation — verified UAN se 1–2 digit door.
    if impersonates(cleaned):
        return {
            "status": "scam",
            "message": "Ye number kisi verified bank/sarkari helpline se bahut milta hai — impersonation scam hai.",
            "confidence": "high",
            "source": "impersonation_rule",
        }

    # 6. Bank-style UAN shape jo verified list me nahi. Sirf AMBER.
    if len(cleaned) == 9 and cleaned.startswith("111"):
        return {
            "status": "suspicious",
            "message": "UAN-style number jo verified list me nahi — khud verify karein.",
            "confidence": "medium",
        }

    # 7. Personal mobile, landline, short code → UNKNOWN. Koi alert nahi.
    return {
        "status": "unknown",
        "message": "Koi list me nahi — koi alert nahi. Personal number hai, scam ka koi signal nahi.",
        "confidence": "low",
    }


def report_number(raw_number: str, note: str = "", reporter: str = "") -> dict:
    """Community report.

    ✅ Consensus: ek report number ko turant block NAHI karti. 5 alag
    REPORTERS chahiye — warna aik galti se kisi innocent number par block ho
    jata hai (aur user ke paas appeal ka koi rasta nahi).

    ✅ Verified number par report reject (400) — bank helpline ko report
    karna ho to us bank ke helpline se confirm karna chahie.

    ⚠️ `reporter` = device/client id. Iske baghair aik hi banda 5 baar tap
    kar ke number block kar sakta hai (5 "alag users" ka koi matlab nahi).
    Mobile ye id bhejta hai; na bhejne par request-context se fallback.
    """
    cleaned = clean_number(raw_number)
    if not cleaned:
        return {"status": "error", "message": "Invalid number"}

    if cleaned in DIRECTORY:
        return {
            "status": "error",
            "message": f"{DIRECTORY[cleaned]} ka official number hai — is par report nahi ho sakti. "
                       "Agar koi is number se fraud kar raha hai to sirf call recording FIA tak bhejein.",
        }

    # `datetime.now()` ki resolution Windows par ~15ms hai — teen rapid
    # calls ek hi tick me gire to dedupe unhe "same report" samajh leta.
    # `time.time()` GetSystemTimePreciseAsFileTime use karta hai (~100ns).
    now = time.time()
    reporter_key = (reporter or request_fingerprint()).strip()[:64]

    with _lock:
        entries = _REPORTS.setdefault(cleaned, {})
        if reporter_key not in entries:
            entries[reporter_key] = now
        count = len(entries)
        confirmed = count >= REPORTS_NEEDED_FOR_CONSENSUS
        if confirmed:
            _SCAM_NUMBERS.add(cleaned)

    if confirmed:
        return {
            "status": "confirmed",
            "report_count": count,
            "reports_needed": REPORTS_NEEDED_FOR_CONSENSUS,
            "message": "Ye number ab community-confirmed scam hai.",
        }

    remaining = REPORTS_NEEDED_FOR_CONSENSUS - count
    return {
        "status": "pending",
        "report_count": count,
        "reports_needed": REPORTS_NEEDED_FOR_CONSENSUS,
        "message": f"Report darj ho gayi. Block tab banega jab {REPORTS_NEEDED_FOR_CONSENSUS} "
                   f"alag users report karein ({remaining} aur).",
    }


def unreport_number(raw_number: str) -> dict:
    """Appeal — galti se scam-mark ho gaye number ko wapas claim karna."""
    cleaned = clean_number(raw_number)
    if not cleaned:
        return {"status": "error", "message": "Invalid number"}
    with _lock:
        existed = _SCAM_NUMBERS.discard(cleaned)
        had_reports = _REPORTS.pop(cleaned, None) is not None
    if existed or had_reports:
        return {"status": "cleared", "message": "Block hat gaya. Number ab unknown hai."}
    return {"status": "unknown", "message": "Ye number block list me nahi tha."}


def number_lists() -> dict:
    """`/number-lists` ka payload — mobile ka `syncRules()` isi ko consume
    karta hai aur native rules cache me push karta hai."""
    with _lock:
        scam = sorted(_SCAM_NUMBERS)
    return {
        "legitimate": LEGITIMATE_NUMBERS,
        "scam": scam,
        # Copy-cat spoofing ab runtime pe compute hoti hai (verified UAN se
        # 1–2 digit door) — is liye static spoofable list ki zaroorat nahi.
        # Field bheja ja raha hai taake native module ka contract na toote.
        "spoofable": [],
        "directory": dict(DIRECTORY),
        "consensus_required": REPORTS_NEEDED_FOR_CONSENSUS,
    }