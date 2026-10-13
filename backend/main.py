from flask import Flask, request, jsonify
from flask_cors import CORS
from fraud_detector import analyze_text
from audio_handler import analyze_audio
from number_screening import (
    check_number as screen_number,
    report_number,
    unreport_number,
    number_lists,
)
import os


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


# --- Number screening -------------------------------------------------------
#
# Ye teen routes pehle MISSING thay, jabke mobile app inhein call karta hai.
# Isi liye `syncRules()` silently fail hoti thi aur native rules empty
# rehte thay — aur khali legit list ka seedha asar ye hota ke HBL
# 111-111-425 jaise real helpline numbers bhi "unknown 111 UAN" par
# SUSPICIOUS aa jate thay.

@app.route('/check-number', methods=['POST'])
def check_number_route():
    data = request.json or {}
    result = screen_number(
        data.get('number', ''),
        # Mobile phonebook cache se ye flag bhejta hai. Is ke bina har
        # saved contact (dost, family, delivery rider) "unknown" samajh
        # aata tha.
        is_saved_contact=bool(data.get('saved_contact', False)),
    )
    status = 400 if result.get('status') == 'error' else 200
    return jsonify(result), status

@app.route('/report-number', methods=['POST'])
def report_number_route():
    data = request.json or {}
    result = report_number(
        data.get('number', ''),
        data.get('note', ''),
        # Client ki device id — iske baghair aik hi banda 5 baar report
        # kar ke number block kar sakta tha ("5 alag users" ka matlaw hi
        # nahi banta).
        reporter=data.get('reporter', ''),
    )
    # Verified number par report REJECT hota hai — mobile UI ko ye message
    # dikhata hai, is liye 400 zaroori hai (fetch `!response.ok` check karta hai).
    status = 400 if result.get('status') == 'error' else 200
    return jsonify(result), status

@app.route('/unreport-number', methods=['POST'])
def unreport_number_route():
    data = request.json or {}
    result = unreport_number(data.get('number', ''))
    status = 400 if result.get('status') == 'error' else 200
    return jsonify(result), status

@app.route('/number-lists', methods=['GET'])
def number_lists_route():
    return jsonify(number_lists()), 200


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
