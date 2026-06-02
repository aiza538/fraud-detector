from flask import Flask, request, jsonify
from flask_cors import CORS
from fraud_detector import analyze_text
from audio_handler import analyze_audio
import os

app = Flask(__name__)

# ✅ More explicit CORS config
CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return jsonify({"status": "Fraud Detector API is running"})

@app.route("/analyze/text", methods=["POST", "OPTIONS"])
def analyze_text_route():
    if request.method == "OPTIONS":
        return jsonify({}), 200          # ✅ handle preflight manually too

    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data["text"].strip()
    if len(text) < 3:
        return jsonify({"error": "Text too short"}), 400

    try:
        result = analyze_text(text)
        return jsonify(result)
    except Exception as e:
        error_msg = str(e)
        # ✅ Give a clear message for quota errors
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return jsonify({
                "error": "Gemini quota exceeded. Wait a few minutes and try again, or test with a message that matches scam patterns (OTP, HBL, block) — those use the rule engine and don't need Gemini."
            }), 429
        return jsonify({"error": error_msg}), 500

@app.route("/analyze/audio", methods=["POST", "OPTIONS"])
def analyze_audio_route():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        result = analyze_audio(file_path)
        return jsonify(result)
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return jsonify({"error": "Gemini quota exceeded. Try again in a few minutes."}), 429
        return jsonify({"error": error_msg}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# main.py mein yeh route add karo — sirf testing ke liye
@app.route("/test-keys")
def test_keys():
    gemini_key = os.getenv("GEMINI_API_KEY")
    assembly_key = os.getenv("ASSEMBLYAI_API_KEY")
    return jsonify({
        "gemini_loaded": gemini_key is not None,
        "gemini_preview": gemini_key[:12] + "..." if gemini_key else "MISSING",
        "assemblyai_loaded": assembly_key is not None,
        "assemblyai_preview": assembly_key[:12] + "..." if assembly_key else "MISSING"
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)