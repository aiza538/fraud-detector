"""Number screening ke pure rules — koi Flask, koi database nahi.

Legacy routes (main.py) aur /v1 API (api_v1.py) dono yahin se import karte hain,
taake clean/lookup/spoof ka faisla ek hi jagah ho.
"""
import json
import os
import re

from config import REPORT_THRESHOLD

def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, fallback.__class__) else fallback
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


# Verified legitimate Pakistani bank/telco/authority numbers (entity -> UANs).
#
# DATA AB `data/official_directory.json` MEIN HAI — har number ke saath
# `source_url` + `verified_on`, taake koi bhi waqt dobara check kar sake ke
# number aaj bhi us organisation ka official number hai ya nahi. Ye whitelist
# SECURITY-CRITICAL hai:
#   - galat number "verified official" label dekar victim ko scammer par
#     bharosa karwa dega
#   - missing number asli bank ki helpline ko "suspicious" bana dega
# Is liye naya number add karna = official site par number dekh kar usi page
# ka URL likhna. Guess kabhi nahi.
#
# Short codes (telcos ke 310/345/333/355/1218/3737/4444) yahan JAAN BOOJH kar
# nahi daale: 3-4 digit codes VoIP se asani se spoof ho jate hain, aur telcos
# customer ko call karne ke bajaye SMS bhejte hain.
OFFICIAL_DIRECTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "official_directory.json")

def load_official_directory(region: str = None, filepath: str = None):
    """Loads official directory with root region key filtering ('PK', 'GLOBAL', 'AE', 'UK').
    
    If region is provided, filters entities to that specific region.
    If region is None, loads entities across all regions.
    """
    path = filepath or OFFICIAL_DIRECTORY_FILE
    doc = _load_json(path, {})
    # Multi-region schema support (PK, GLOBAL, AE, UK) with backward-compatible fallback
    if isinstance(doc, dict) and "regions" in doc:
        out = {}
        for region_code, reg_info in doc["regions"].items():
            if region and region_code.upper() != str(region).strip().upper():
                continue
            reg_entities = reg_info.get("entities", reg_info) if isinstance(reg_info, dict) else {}
            for entity, meta in reg_entities.items():
                if isinstance(meta, dict):
                    numbers = meta.get("numbers") or []
                    if numbers:
                        out[entity] = numbers
        if out:
            return out
    entities = doc.get("entities", {}) if isinstance(doc, dict) else {}
    out = {}
    for entity, meta in entities.items():
        numbers = meta.get("numbers") or []
        if numbers:
            out[entity] = numbers
    return out

_load_official_directory = load_official_directory
LEGITIMATE_DIRECTORY = _load_official_directory()
if not LEGITIMATE_DIRECTORY:
    # JSON missing/corrupt ho to app chup na ho — magar ye fail loudly karein,
    # kyunki khali whitelist = har bank ka number "suspicious" ban jayega.
    raise RuntimeError(
        f"official_directory.json load nahi hui ({OFFICIAL_DIRECTORY_FILE}). "
        "Verified whitelist missing hai — scam screening unreliable ho jayegi."
    )


# Admin ke liye: manually verify kiye gaye (FIA press release / court record)
# numbers. Inka threshold nahi lagta — inhe seedha scam maana jaata hai.
VERIFIED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "verified_scam_numbers.json")


def _load_verified():
    """verified_scam_numbers.json ka `numbers` array — har entry dict ya string.

    File ke top par `_comment`/`_how_to_add` jaise documentation keys hain, is liye
    sirf `numbers` key hi padhi jaati hai. Bina source_url ke entry ignore hoti
    hai: "authentic" ka dawa tabhi qeemti hai jab source traceable ho.
    """
    doc = _load_json(VERIFIED_FILE, {})
    entries = doc.get("numbers", []) if isinstance(doc, dict) else doc
    out = []
    for e in entries:
        if isinstance(e, str):
            out.append({"number": e, "source": "admin_verified", "source_url": None})
        elif isinstance(e, dict) and e.get("number") and e.get("source_url"):
            out.append(e)
    return out

VERIFIED_SCAM_NUMBERS = _load_verified()


def clean_number(raw):
    # Spaces, dashes, brackets, +92 hatao for comparison
    cleaned = raw.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if cleaned.startswith("+92"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("0092"):
        cleaned = cleaned[4:]
    # Sirf EK leading zero hatao. lstrip("0") poora zero-strip kar deta tha,
    # jis se "0800-55055" (PTA) aur "0800-26477" (BISP) jaise short UANs
    # galat normalize ho jate the.
    if cleaned.startswith("0"):
        cleaned = cleaned[1:]
    return cleaned

# Pakistani landline area codes. Banks apni official sites par helpline
# "021-111-xxx-xxx" format mein likhte hain aur network caller ID bhi prefixed
# hi bhejta hai — bare "111xxx xxx" se wo match nahi karta tha.
AREA_CODES = {"21", "42", "51", "61", "71", "81", "91"}

def lookup_keys(cleaned):
    keys = [cleaned]
    # 0<area><UAN> / +92<area><UAN> -> bare UAN  (21111627627 -> 111627627)
    if len(cleaned) == 11 and cleaned[:2] in AREA_CODES and cleaned[2:].startswith("111"):
        keys.append(cleaned[2:])
    return keys

# cleaned number -> entity (Caller ID lookup)
LEGITIMATE_LOOKUP = {
    clean_number(n): entity
    for entity, numbers in LEGITIMATE_DIRECTORY.items()
    for n in numbers
}

# Area-code prefixed roop (021-111-xxx-xxx) bhi official hain — inhe alag rakha hai
# taake spoof-check sirf canonical UAN se ho. Warna 042-111-... (doosre sheher ka
# same bank UAN) 021-111-... se edit-distance 2 par "spoof" ghoshit ho jata.
LEGITIMATE_ALIASES = {
    area + number: entity
    for number, entity in LEGITIMATE_LOOKUP.items()
    if len(number) == 9 and number.startswith("111")
    for area in sorted(AREA_CODES)
}

# Direct "ye official number hai" matching — canonical + prefixed
ALL_LEGITIMATE = {**LEGITIMATE_ALIASES, **LEGITIMATE_LOOKUP}

def _levenshtein(a, b):
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]

def find_spoof_target(cleaned):
    # Kisi verified authority ka number jaisa dikhta ho lekin exact na ho — impersonation
    if len(cleaned) < 7:
        return None
    for official, entity in LEGITIMATE_LOOKUP.items():
        if len(cleaned) == len(official) and _levenshtein(cleaned, official) <= 2:
            return entity
    return None

_DIGITS = "0123456789"

def _near_variants(official, whitelist):
    """Har verified UAN ke do-teen digit ke close neighbours.

    Scammer ke paas apna number to hota hai — wo koi bhi *random* 9-digit
    number nahi banata, balki verified UAN se 1-2 digit door ka number banata
    hai (jaise 111-111-425 -> 111-111-427) kyunki wahi "official lagta" hai.
    In sab par distance <= 2 hone se total candidates per UAN sirf ~55 hain,
    is liye ye list mehengi nahi — native receiver inhe impersonation samajh
    leta hai bina network ke.
    """
    n = len(official)
    if n < 7:
        return []
    out = set()
    for i in range(n):
        prefix, suffix = official[:i], official[i + 1:]
        original = official[i]
        for d in _DIGITS:
            if d == original:
                continue
            out.add(prefix + d + suffix)
    return [v for v in out if v not in whitelist]


# Number kya Pakistani caller number ya corporate UAN lag sakta hai? Ye sirf
# /report-number ki sanity check ke liye hai, taake koi bhi random string
# blacklist na kar sake.
def _plausible_caller_number(cleaned):
    return bool(re.fullmatch(r"\d{7,13}", cleaned))


VERIFIED_NUMBERS = frozenset(e["number"] for e in VERIFIED_SCAM_NUMBERS)

# Verified UANs ke 1-digit door ke numbers. Whitelist static hai, is liye ye
# list ek hi baar banti hai — har request par dobara nahi.
SPOOFABLE = sorted({
    candidate
    for official in LEGITIMATE_LOOKUP
    for candidate in _near_variants(official, LEGITIMATE_LOOKUP)
})


def official_entity(cleaned):
    """Verified official number ho to entity ka naam, warna None."""
    return next((ALL_LEGITIMATE[k] for k in lookup_keys(cleaned) if k in ALL_LEGITIMATE), None)


def screen_number(raw_number, is_saved, scam_info):
    """Caller-ID ka 4-level faisla: scam / suspicious / unknown / safe.

    `scam_info(keys)` confirmed scam number ke liye
    `{"source": ..., "report_count": ...}` deta hai, warna None — is tarah ye
    function database ke baghair test ho sakta hai.

    "Unknown" ka matlab "pata nahi" hai — scam ya suspicious NAHI. Client
    unknown par koi notification nahi dikhata.
    """
    cleaned = clean_number(raw_number or "")
    # Guard 4 digit ka hai, 7 ka nahi — NADRA "1700", FIA "1717" jaise SHORT
    # CODES bhi verified official numbers hain.
    if not cleaned or len(cleaned) < 4 or not cleaned.isdigit():
        return {"status": "unknown", "message": "This is not a valid number.", "confidence": "low"}

    # prefixed caller IDs (021-111-...) ko bare UAN tak laao, phir dono check karo
    keys = lookup_keys(cleaned)

    # 1) Confirmed scam — ye pehle hai kyunke scammer kisi saved contact ke
    #    naam se bhi call kar sakta hai.
    scam = scam_info(keys)
    if scam:
        if scam["source"] == "community":
            message = (f"{scam['report_count']} users have reported this number as fraudulent "
                       f"(at least {REPORT_THRESHOLD} reports are needed, and it has crossed that).")
        else:
            message = "Listed as a scam number in an FIA or other official record."
        return {"status": "scam", "source": scam["source"],
                "report_count": scam["report_count"], "message": message,
                "confidence": "high"}

    # 2) Verified official number
    entity = next((ALL_LEGITIMATE[k] for k in keys if k in ALL_LEGITIMATE), None)
    if entity:
        return {"status": "safe", "entity": entity,
                "message": f"Verified official number — {entity}'s official helpline.",
                "confidence": "high"}

    # 3) Saved contact — "suspicious" kabhi nahi, warna har dost alert karta.
    if is_saved:
        return {"status": "safe", "entity": "Saved contact",
                "message": "This number is saved in your contacts.", "confidence": "high"}

    # 4) Spoofed official number (edit distance <= 2 of a verified UAN)
    spoofed = next((e for e in map(find_spoof_target, keys) if e), None)
    if spoofed:
        return {"status": "scam", "entity": spoofed,
                "message": (f"Impersonation alert — this number mimics {spoofed}'s official "
                            "helpline but is NOT their real number. Scammers use "
                            "near-identical UANs to trick victims."),
                "confidence": "high"}

    # 5) UAN-format (111-xxxxxxx) jo verified list me NAHI hai.
    bare = keys[-1]
    if len(bare) == 9 and bare.startswith("111"):
        return {"status": "suspicious",
                "message": ("UAN-style number not in verified database — scammers can spoof "
                            "official-looking UANs. Verify independently before sharing "
                            "information."),
                "confidence": "medium"}

    # 6) Baqi sab — personal mobiles, landlines, short codes — "unknown".
    return {"status": "unknown",
            "message": ("This number is not on any list and not in your contacts. No alert "
                        "is needed — but if the caller asks for an OTP or money, block them."),
            "confidence": "low"}
