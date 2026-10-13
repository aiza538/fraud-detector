from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from fraud_detector import analyze_text
from audio_handler import analyze_audio
import os
import json
import time
import logging
import threading
import hashlib

import config
import db
from api_v1 import v1
from config import REPORT_THRESHOLD, REPORT_DECAY_DAYS
from number_rules import (
    _load_json, VERIFIED_SCAM_NUMBERS, clean_number, lookup_keys,
    LEGITIMATE_LOOKUP, ALL_LEGITIMATE, find_spoof_target, _near_variants,
    _plausible_caller_number,
)
# tests/test_detection_accuracy.py inhe `main` se import karta hai.
from number_rules import AREA_CODES, _levenshtein, load_official_directory  # noqa: F401

app = Flask(__name__)

# Proxy (Hugging Face / Render) ke peeche `remote_addr` proxy ka IP hota hai —
# sab users ek hi IP lagte the aur IP limits/consensus bekaar ho jate the.
if config.TRUSTED_PROXY_HOPS:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=config.TRUSTED_PROXY_HOPS)

# /v1 API: token-protected, database-backed. Neeche ke purane routes tab tak
# hain jab tak mobile app /v1 par shift nahi hoti.
db.init_engine(config.DATABASE_URL)
if not config.IS_PRODUCTION:
    # Production me schema sirf `alembic upgrade head` se banta hai.
    db.Base.metadata.create_all(db.engine)
app.teardown_appcontext(db.close_session)
app.register_blueprint(v1)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


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
