# Caller-ID ka 4-level faisla (number_rules.screen_number) — chalane ke liye:
#   python -m tests.test_number_screening   (backend/ directory se)
#
# Ye test tab banaya jab EVERY unknown number "suspicious, high confidence"
# aa raha tha. Pakistan me 300-999 POORE Jazz/Zong/Tenor/Ufone ka personal
# mobile range hai, is liye wo heuristic har dost, har delivery rider, har
# hospital ko alert kar rahi thi.
#
# Rule: "unknown" ka matlab "pata nahi" hai — scam ya suspicious NAHI.
#
# Ye seedha screening function ko test karta hai (database ke baghair).
# /v1/check-number, reports, consensus aur decay ke tests test_api_v1.py me hain.
import number_rules
from config import REPORT_THRESHOLD

# Is test ke liye "consensus se confirmed" maana gaya number — asli kisi ka nahi.
CONFIRMED = "3335551122"


def scam_info(keys):
    if CONFIRMED in keys:
        return {"source": "community", "report_count": REPORT_THRESHOLD}
    return None


# (label, number, saved_contact, expected_status)
CASES = [
    # --- Verified official numbers (short codes bhi) ---
    ("area-prefixed HBL UAN", "021-111-111-425", False, "safe"),
    ("HBL UAN with +92", "+9221111111425", False, "safe"),
    ("bare HBL UAN", "111-111-425", False, "safe"),
    ("PTA toll-free", "0800-55055", False, "safe"),
    ("BISP toll-free", "0800-26477", False, "safe"),
    ("NADRA short code", "1700", False, "safe"),
    ("FIA short code", "1717", False, "safe"),
    ("FIA cyber crime 1991", "1991", False, "safe"),

    # --- Impersonation: verified UAN ka 1-2 digit door ka number ---
    ("HBL spoof (+2)", "111-111-427", False, "scam"),
    ("Meezan spoof", "111-331-333", False, "scam"),

    # --- Personal mobiles: UNKNOWN, kabhi suspicious nahi ---
    ("Jazz mobile", "0300-1234567", False, "unknown"),
    ("Zong mobile", "03451234567", False, "unknown"),
    ("Telenor mobile", "03211234567", False, "unknown"),
    ("Ufone mobile", "03331234567", False, "unknown"),
    ("landline", "051-1234567", False, "unknown"),
    ("telco short code", "310", False, "unknown"),

    # --- Genuine suspicious signal: 111 UAN jo verified list me nahi ---
    ("unknown UAN", "111-999-999", False, "suspicious"),

    # --- Saved contact ---
    ("saved friend", "03001234567", True, "safe"),
    # Confirmed scam pehle aata hai — saved hone par bhi scam.
    ("saved but reported", "03335551122", True, "scam"),

    # --- Garbage input ---
    ("letters only", "abc", False, "unknown"),
    ("empty", "", False, "unknown"),
    ("None", None, False, "unknown"),
]


def main():
    failed = []
    for label, number, saved, expected in CASES:
        got = number_rules.screen_number(number, saved, scam_info)["status"]
        if got != expected:
            failed.append(f"expected {expected}, got {got}\n  case: {label}")

    # Provenance: scam verdict me report count + source aana chahie, warna
    # user ko "community reported" claim par bharosa nahi hoga.
    sc = number_rules.screen_number(CONFIRMED, False, scam_info)
    if (sc.get("source"), sc.get("report_count")) != ("community", REPORT_THRESHOLD):
        failed.append("provenance: source/report_count missing from a confirmed verdict")

    # Phone ki offline screening ke liye spoofable list honi chahiye, aur koi
    # verified number us me nahi hona chahiye.
    if not number_rules.SPOOFABLE:
        failed.append("SPOOFABLE list is empty")
    if set(number_rules.SPOOFABLE) & set(number_rules.LEGITIMATE_LOOKUP):
        failed.append("a verified number is listed as spoofable")

    if failed:
        raise SystemExit("FAIL:\n" + "\n".join(failed))
    print(f"OK - {len(CASES)} screening cases + provenance + spoofable list, "
          "unknown = no alert, sirf scam/suspicious alert deta hai")


if __name__ == "__main__":
    main()
