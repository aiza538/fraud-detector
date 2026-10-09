# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from fraud_detector import analyze_text
# from audio_handler import analyze_audio
# import os

# app = Flask(__name__)

# # ✅ More explicit CORS config
# CORS(app, resources={r"/*": {"origins": "*"}})

# UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# @app.route("/")
# def home():
#     return jsonify({"status": "Fraud Detector API is running"})

# @app.route("/analyze/text", methods=["POST", "OPTIONS"])
# def analyze_text_route():
#     if request.method == "OPTIONS":
#         return jsonify({}), 200          # ✅ handle preflight manually too

#     data = request.get_json()

#     if not data or "text" not in data:
#         return jsonify({"error": "No text provided"}), 400

#     text = data["text"].strip()
#     if len(text) < 3:
#         return jsonify({"error": "Text too short"}), 400

#     try:
#         result = analyze_text(text)
#         return jsonify(result)
#     except Exception as e:
#         error_msg = str(e)
#         # ✅ Give a clear message for quota errors
#         if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
#             return jsonify({
#                 "error": "Gemini quota exceeded. Wait a few minutes and try again, or test with a message that matches scam patterns (OTP, HBL, block) — those use the rule engine and don't need Gemini."
#             }), 429
#         return jsonify({"error": error_msg}), 500

# @app.route("/analyze/audio", methods=["POST", "OPTIONS"])
# def analyze_audio_route():
#     if request.method == "OPTIONS":
#         return jsonify({}), 200

#     if "file" not in request.files:
#         return jsonify({"error": "No audio file provided"}), 400

#     file = request.files["file"]
#     if file.filename == "":
#         return jsonify({"error": "Empty filename"}), 400

#     file_path = os.path.join(UPLOAD_FOLDER, file.filename)
#     file.save(file_path)

#     try:
#         result = analyze_audio(file_path)
#         return jsonify(result)
#     except Exception as e:
#         error_msg = str(e)
#         if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
#             return jsonify({"error": "Gemini quota exceeded. Try again in a few minutes."}), 429
#         return jsonify({"error": error_msg}), 500
#     finally:
#         if os.path.exists(file_path):
#             os.remove(file_path)


# # main.py mein yeh route add karo — sirf testing ke liye
# @app.route("/test-keys")
# def test_keys():
#     gemini_key = os.getenv("GEMINI_API_KEY")
#     assembly_key = os.getenv("ASSEMBLYAI_API_KEY")
#     return jsonify({
#         "gemini_loaded": gemini_key is not None,
#         "gemini_preview": gemini_key[:12] + "..." if gemini_key else "MISSING",
#         "assemblyai_loaded": assembly_key is not None,
#         "assemblyai_preview": assembly_key[:12] + "..." if assembly_key else "MISSING"
#     })

# if __name__ == "__main__":
#     app.run(debug=True, port=5000)


from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from fraud_detector import analyze_text
from audio_handler import analyze_audio
import os
import json
import re
import time
import logging
import threading
import hashlib

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, fallback.__class__) else fallback
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback

def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Multipart upload size cap — bina cap ke /analyze/audio unlimited file accept
# karta tha. 25MB audio ke liye kaafi hai.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# ✅ Enable CORS for your local testing AND your live Netlify app
# CORS(app, resources={
#     r"/*": {"origins": [
#         "http://localhost:5173", 
#         "https://frauddetectionsystem.netlify.app"
#     ]}
# })
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "Fraud Detector API is running"}), 200

@app.route('/analyze/text', methods=['POST'])
def handle_text():
    data = request.json
    text = data.get('text', '')
    channel = data.get('channel')  # e.g. "whatsapp" — AI ko extra context milta hai
    if not text:
        return jsonify({"error": "No text provided"}), 400

    result = analyze_text(text, channel=channel)
    return jsonify(result)

@app.route('/analyze/audio', methods=['POST'])
def handle_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Ensure uploads directory exists
    os.makedirs('uploads', exist_ok=True)

    safe_name = secure_filename(os.path.basename(file.filename))
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400

    file_path = os.path.join('uploads', safe_name)
    file.save(file_path)

    # finally: pehle analyze_audio ka exception par file disk par hi reh jati thi
    try:
        result = analyze_audio(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return jsonify(result)

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

def _load_official_directory():
    doc = _load_json(OFFICIAL_DIRECTORY_FILE, {})
    entities = doc.get("entities", {}) if isinstance(doc, dict) else {}
    out = {}
    for entity, meta in entities.items():
        numbers = meta.get("numbers") or []
        if numbers:
            out[entity] = numbers
    return out

LEGITIMATE_DIRECTORY = _load_official_directory()
if not LEGITIMATE_DIRECTORY:
    # JSON missing/corrupt ho to app chup na ho — magar ye fail loudly karein,
    # kyunki khali whitelist = har bank ka number "suspicious" ban jayega.
    raise RuntimeError(
        f"official_directory.json load nahi hui ({OFFICIAL_DIRECTORY_FILE}). "
        "Verified whitelist missing hai — scam screening unreliable ho jayegi."
    )

# --- Community-reported scam numbers: CONSENSUS database --------------------
#
# Pehle ye ek flat list thi: `["3335551122", ...]`. Ek report = number turant
# POORE Pakistan ke liye block, aur koi un-report/appeal path nahi tha. Iska matlab
# ek galti ya ek malicious user kisi bhi asli number ko permanently block kar
# sakta tha, aur victim ke paas koi rasta nahi tha.
#
# Ab har entry poori provenance ke saath store hoti hai:
#   {
#     "number": "3211112223",
#     "reports": [ {"reporter": "<ip-hash>", "at": 1757..., "note": ""} ],
#     "first_seen": 1757..., "last_seen": 1757...
#   }
#
# Rules:
#   - Sirf >= REPORT_THRESHOLD *distinct* reporters ka number scam hota hai.
#   - Purane reports expire (REPORT_DECAY_DAYS) — ek saal purana block nahi jeeta.
#   - Verified official number kabhi report/flag nahi ho sakta.
#   - Number owner / admin `unreport-number` se claim kar sakta hai.
REPORTED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reported_numbers.json")

# Kitne ALAG reporters ke number ko scam kehna hai. 1 bahut kam hai — ek
# galti se galti se number ban jata tha.
REPORT_THRESHOLD = 5
# Report ki age (din) — is se zyada purane reports count nahi hote.
REPORT_DECAY_DAYS = 180
# Admin ke liye: manually verify kiye gaye (FIA press release / court record)
# numbers. Inka threshold nahi lagta — inhe seedha scam maana jaata hai.
VERIFIED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "verified_scam_numbers.json")

# Reporter ki identity store karne ke liye IP ka raw value nahi, uska hash —
# warna DB mein users ke IP addresses accumulate honge. Salt app-wide hai taake
# entries cross-reference na ho sakein.
_REPORTER_SALT = os.environ.get("FRAUDGUARD_SALT", "fraudguard-dev-salt")

def _reporter_id(ip):
    return hashlib.sha256(f"{_REPORTER_SALT}|{ip}".encode()).hexdigest()[:16]

def _load_reported():
    """Legacy flat list ko naye schema mein migrate karo.

    Purani entries ke paas koi reporter provenance nahi hai, is liye unhe
    `legacy_import` source ke saath seed kiya jata hai — REPORT_THRESHOLD se
    kam reports hone ki wajah se wo turant scam NAHI banti. Yaani upgrade ke
    baad bhi koi number bina consensus ke block nahi hoga.
    """
    raw = _load_json(REPORTED_FILE, [])
    migrated, changed = [], False
    for entry in raw:
        if isinstance(entry, str):
            changed = True
            now = int(time.time())
            migrated.append({
                "number": entry,
                # Provenance nahi hai — is liye 0 real reports. Inhe manually
                # verify karne ke liye `source` dekh kar count bharein.
                "reports": [],
                "source": "legacy_import",
                "first_seen": now,
                "last_seen": now,
            })
        elif isinstance(entry, dict) and entry.get("number"):
            migrated.append(entry)
        else:
            changed = True
    if changed:
        _save_json(REPORTED_FILE, migrated)
    return migrated

def _save_reported(numbers):
    _save_json(REPORTED_FILE, numbers)

REPORTED_SCAM_NUMBERS = _load_reported()

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

def _active_reports(entry):
    """Decay ke baad bache reports — distinct reporters, ek per reporter."""
    cutoff = time.time() - REPORT_DECAY_DAYS * 86400
    seen = {r.get("reporter") for r in entry.get("reports", []) if r.get("at", 0) >= cutoff}
    return seen

def reported_numbers(reported=REPORTED_SCAM_NUMBERS):
    """Sirf wo numbers jo ABHI scam hain: threshold ya admin-verified."""
    out = set()
    for entry in reported:
        if entry.get("source") in ("fia_announcement", "court_record", "admin_verified"):
            out.add(entry["number"])
            continue
        if len(_active_reports(entry)) >= REPORT_THRESHOLD:
            out.add(entry["number"])
    for entry in VERIFIED_SCAM_NUMBERS:
        out.add(entry["number"])
    return out

# Simple per-IP rate limit for /report-number (in-memory; dev-scale abuse ke liye kaafi)
_report_lock = threading.Lock()
_report_counts = {}
REPORT_WINDOW_SECONDS = 3600
REPORT_MAX_PER_WINDOW = 20

def _rate_limited(ip):
    now = time.time()
    with _report_lock:
        hits = [t for t in _report_counts.get(ip, []) if now - t < REPORT_WINDOW_SECONDS]
        if len(hits) >= REPORT_MAX_PER_WINDOW:
            _report_counts[ip] = hits
            return True
        hits.append(now)
        _report_counts[ip] = hits
        return False

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

@app.route('/check-number', methods=['POST'])
def check_number():
    """Caller-ID screening.

    Sirf 4 level ka faisla: scam / suspicious / unknown / safe.
    "Unknown" ka matlab "pata nahi" hai — scam ya suspicious NAHI. Client
    (native call-monitor) unknown par koi notification nahi dikhata.

    Client `saved_contact: true` bhej sakta hai jab number user ke phonebook
    me ho. Saved contact ko suspicious/scam kahna galat verdict hai, warna
    har dost / delivery rider alert kar jaata hai.
    """
    data = request.json or {}
    raw_number = data.get('number', '')
    cleaned = clean_number(raw_number or "")
    # Guard 4 digit ka rakha hai, 7 ka nahi — NADRA "1700", FIA "1717",
    # BISP "0800-26477" jaise SHORT CODES bhi verified official numbers hain.
    # (7+ ka guard lagane se ye sab "unknown" ho jate the.)
    if not cleaned or len(cleaned) < 4 or not cleaned.isdigit():
        return jsonify({
            "status": "unknown",
            "message": "Number valid nahi hai.",
            "confidence": "low"
        })

    is_saved = bool(data.get("saved_contact", False))

    # prefixed caller IDs (021-111-...) ko bare UAN tak laao, phir dono check karo
    keys = lookup_keys(cleaned)

    # 1) Community-reported scam list — ye pehle hai kyunke ek scammer khud
    #    kisi saved contact ke naam se bhi call kar sakta hai.
    #    Sirf wahi numbers jo REPORT_THRESHOLD alag reporters par cross kar
    #    chuke hon (ya admin-verified hon).
    confirmed = reported_numbers()
    if any(k in confirmed for k in keys):
        entry = next((e for e in REPORTED_SCAM_NUMBERS
                      if e.get("number") in keys), {})
        source = entry.get("source", "community")
        # Transparency: victim ko pata ho ke ye verdict kahan se aaya.
        if source in ("fia_announcement", "court_record", "admin_verified"):
            msg = (f"FIA/verified record ke mutabiq scam number. "
                   f"Sirf {REPORT_THRESHOLD} logo ke report par bana hai, official record se.")
        else:
            count = len(_active_reports(entry))
            msg = (f"{count} users ne is number ko fraudulent report kiya hai. "
                   f"(Kam se kam {REPORT_THRESHOLD} chahiye — ye threshold cross kar chuka hai.)")
        return jsonify({
            "status": "scam",
            "source": source,
            "report_count": len(_active_reports(entry)),
            "first_seen": entry.get("first_seen"),
            "message": msg,
            "confidence": "high"
        })

    # 2) Verified official number
    verified_entity = next((ALL_LEGITIMATE[k] for k in keys if k in ALL_LEGITIMATE), None)
    if verified_entity:
        return jsonify({
            "status": "safe",
            "entity": verified_entity,
            "message": f"Verified official number — {verified_entity} ki official helpline.",
            "confidence": "high"
        })

    # 3) Saved contact — user ke apne phonebook ka number. Yeh "suspicious"
    #    kabhi nahi hona chahie, warna har dost / delivery rider alert karta.
    if is_saved:
        return jsonify({
            "status": "safe",
            "entity": "Saved contact",
            "message": "Aapke phonebook me saved hai.",
            "confidence": "high"
        })

    # 4) Spoofed official number (edit distance <= 2 of a verified UAN)
    spoofed_entity = next((find_spoof_target(k) for k in keys if find_spoof_target(k)), None)
    if spoofed_entity:
        return jsonify({
            "status": "scam",
            "entity": spoofed_entity,
            "message": f"Impersonation alert — this number mimics {spoofed_entity}'s official helpline but is NOT their real number. Scammers use near-identical UANs to trick victims.",
            "confidence": "high"
        })

# 5) UAN-format (111-xxxxxxx) jo verified list me NAHI hai. Yeh genuine
    #    "suspicious" signal hai: aam corporate UAN spoof ho sakta hai.
    #    bare = area-code prefix hata kar (021-111-... -> 111...)
    bare = keys[-1]
    if len(bare) == 9 and bare.startswith("111"):
        return jsonify({
            "status": "suspicious",
            "message": "UAN-style number not in verified database — scammers can spoof official-looking UANs. Verify independently before sharing information.",
            "confidence": "medium"
        })

    # 6) Baqi sab — personal mobiles (300-999), landlines, short codes — "unknown".
    #
    #    PEHLE yahan `bare.startswith("3") and len == 10` par "suspicious" +
    #    confidence "high" return hota tha. Pakistan me 300-999 POORE Jazz/Zong/
    #    Telenor/Ufone personal mobile range hain, yaani har personal number
    #    "suspicious, high confidence" nikalta tha. "Bank personal mobile se
    #    call nahi karti" wali baat NUMBER se prove nahi hoti — wo sirf tab
    #    valid hai jab number khud bank CLAIM kar raha ho, jo message analysis
    #    me dekha jaata hai, number lookup me nahi.
    return jsonify({
        "status": "unknown",
        "message": "Number kisi bhi list me nahi, aur aapke phonebook me bhi nahi. Koi alert ki zarurat nahi — sirf OTP ya paisa maange to block karein.",
        "confidence": "low"
    })


# Number kya Pakistani caller number ya corporate UAN lag sakta hai? Ye sirf
# /report-number ki sanity check ke liye hai, taake koi bhi random string
# blacklist na kar sake.
def _plausible_caller_number(cleaned):
    return bool(re.fullmatch(r"\d{7,13}", cleaned))


@app.route('/report-number', methods=['POST'])
def report_number():
    data = request.json or {}
    raw_number = data.get('number', '')
    cleaned = clean_number(raw_number or "")

    if not _plausible_caller_number(cleaned):
        return jsonify({"status": "error", "message": "Invalid number"}), 400

    if _rate_limited(request.remote_addr):
        return jsonify({
            "status": "error",
            "message": "Too many reports from this device. Try again later."
        }), 429

    # Verified official number ko koi report na kar sake. Warna ek galti se
    # kisi asli bank ka UAN poori community ke liye block ho jata tha aur
    # /number-lists se sab clients ko push ho jata tha — koi un-report/appeal
    # path bhi nahi tha.
    verified_entity = next((ALL_LEGITIMATE[k] for k in lookup_keys(cleaned)
                            if k in ALL_LEGITIMATE), None)
    if verified_entity:
        return jsonify({
            "status": "error",
            "message": f"{verified_entity} ek verified official number hai — ise report nahi kiya ja sakta."
        }), 400

    reporter = _reporter_id(request.remote_addr)
    now = int(time.time())
    with _report_lock:
        entry = next((e for e in REPORTED_SCAM_NUMBERS if e.get("number") == cleaned), None)
        if entry is None:
            entry = {"number": cleaned, "reports": [], "source": "community",
                     "first_seen": now, "last_seen": now}
            REPORTED_SCAM_NUMBERS.append(entry)
        # Ek reporter ek number par sirf ek vote daal sakta hai — warna wahi
        # banda 5 baar report karke consensus bana sakta tha.
        if not any(r.get("reporter") == reporter for r in entry["reports"]):
            entry["reports"].append({
                "reporter": reporter,
                "at": now,
                "note": str(data.get("note") or "")[:280],
            })
        entry["last_seen"] = now
        _save_reported(REPORTED_SCAM_NUMBERS)

    active = len(_active_reports(entry))
    # Threshold tak user ko honest status batate hain — "abhi tak nahi hua"
    # kehna zyada helpful hai jitna jhooti tasalli dena.
    if active >= REPORT_THRESHOLD:
        return jsonify({
            "status": "confirmed",
            "report_count": active,
            "message": "Ye number ab scam-confirmed hai. Aap ke users ke liye alerts aa rahe hain."
        })
    return jsonify({
        "status": "pending",
        "report_count": active,
        "reports_needed": REPORT_THRESHOLD,
        "message": (f"Report darj ho gaya. {REPORT_THRESHOLD} alag users ke report "
                    f"chahiye — tab ye number sab ke liye block hoga. Abhi koi alert nahi aayega."),
    })


@app.route('/unreport-number', methods=['POST'])
def unreport_number():
    """Number owner / admin ka appeal path.

    Pehle koi un-report route nahi tha — ek baar number block ho gaya to wo
    hamesha ke liye block tha, chahe kitni bhi galti se. Ye wahi rasta hai jisse
    verified official number ya nirdhar number apni block se nikal sakta hai.
    """
    data = request.json or {}
    cleaned = clean_number(data.get('number', '') or "")
    if not _plausible_caller_number(cleaned):
        return jsonify({"status": "error", "message": "Invalid number"}), 400

    # Verified official number ko un-report karne ki zarurat hi nahi — wo
    # report bhi nahi ho sakta. Ye sirf consistency ke liye.
    verified_entity = next((ALL_LEGITIMATE[k] for k in lookup_keys(cleaned)
                            if k in ALL_LEGITIMATE), None)

    with _report_lock:
        remaining = [e for e in REPORTED_SCAM_NUMBERS if e.get("number") != cleaned]
        removed = len(remaining) != len(REPORTED_SCAM_NUMBERS)
        if removed:
            REPORTED_SCAM_NUMBERS[:] = remaining
            _save_reported(REPORTED_SCAM_NUMBERS)

    if not removed:
        return jsonify({"status": "not_found",
                        "message": "Ye number blocklist me nahi tha."}), 404
    return jsonify({
        "status": "unreported",
        "verified_entity": verified_entity,
        "message": "Block hat gaya. Agar ye aap ka apna number hai, dhanyawaad — "
                   "hum ise dobara report hone se bachate hain.",
    })


@app.route('/number-lists', methods=['GET'])
def number_lists():
    # App ke native call-monitor ko sync karne ke liye (offline rules).
    # `spoofable`: verified UANs ke kareeb (edit distance <= 2) numbers —
    # native receiver inhe impersonation samajhta hai bina network ke.
    spoofable = sorted({
        candidate
        for official in LEGITIMATE_LOOKUP
        for candidate in _near_variants(official, LEGITIMATE_LOOKUP)
    })
    scam = sorted(reported_numbers())
    return jsonify({
        "legitimate": list(ALL_LEGITIMATE.keys()),
        "directory": ALL_LEGITIMATE,   # number -> entity (Caller ID ke liye)
        # Sirf consensus-crossed numbers — ek report wali list nahi.
        "scam": scam,
        "spoofable": spoofable,
        # Transparency: client dikha sake ke ye list kitni badi hai aur kitne
        # reports par bani hai (FIA verification ka wait karte hue).
        "pending": sorted(e["number"] for e in REPORTED_SCAM_NUMBERS
                          if e.get("number") not in scam),
        "threshold": REPORT_THRESHOLD,
        "verified_sources": sorted({
            e.get("source") for e in REPORTED_SCAM_NUMBERS
            if e.get("source") in ("fia_announcement", "court_record", "admin_verified")
        }),
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
