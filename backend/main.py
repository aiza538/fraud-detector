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
from fraud_detector import analyze_text
from audio_handler import analyze_audio
import os
import logging


app = Flask(__name__)


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
    if not text:
        return jsonify({"error": "No text provided"}), 400

    result = analyze_text(text)
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

    file_path = os.path.join('uploads', file.filename)
    file.save(file_path)

    result = analyze_audio(file_path)

    # Clean up file after processing
    if os.path.exists(file_path):
        os.remove(file_path)

    return jsonify(result)

# Verified legitimate Pakistani bank/telco UAN numbers
LEGITIMATE_NUMBERS = [
    "111124444",   # JazzCash UAN
    "111003737",   # Easypaisa UAN
    # Aur banks ke verified UAN yahan add karte rahna jaise confirm ho
]

# Community-reported scam numbers (yahan grow hoga jaise reports aayenge)
REPORTED_SCAM_NUMBERS = []

@app.route('/check-number', methods=['POST'])
def check_number():
    data = request.json
    raw_number = data.get('number', '')

    # Number ko clean karo (spaces, dashes, +92 hatao for comparison)
    cleaned = raw_number.replace(" ", "").replace("-", "").replace("+92", "").lstrip("0")

    if cleaned in REPORTED_SCAM_NUMBERS:
        return jsonify({
            "status": "scam",
            "message": "This number has been reported as fraudulent by other users.",
            "confidence": "high"
        })

    if cleaned in LEGITIMATE_NUMBERS:
        return jsonify({
            "status": "safe",
            "message": "Verified official number.",
            "confidence": "high"
        })

    # Agar mobile number (03xx) hai aur koi bank claim kar raha ho — unknown/caution
    if cleaned.startswith("3") and len(cleaned) == 10:
        return jsonify({
            "status": "unknown",
            "message": "Personal mobile number — banks typically call from official UAN lines, not personal numbers.",
            "confidence": "medium"
        })

    return jsonify({
        "status": "unknown",
        "message": "Number not in database. Verify independently before sharing information.",
        "confidence": "low"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
