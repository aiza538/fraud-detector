"""FraudGuard AI server — sirf Flask app ka setup.

Saare API routes token ke peeche /v1 me hain (api_v1.py). Purane bina-token
routes (/analyze/text, /check-number, /report-number, /unreport-number,
/number-lists) hata diye gaye: koi bhi un se Gemini/AssemblyAI keys istemal kar
sakta tha, aur /unreport-number se koi bhi kisi number ke reports mita sakta tha.
"""
import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

import config
import db
from api_v1 import v1

app = Flask(__name__)

# Proxy (Render) ke peeche `remote_addr` proxy ka IP hota hai — sab users ek hi
# IP lagte the aur IP limits/consensus bekaar ho jate the. Render par 3 hops.
if config.TRUSTED_PROXY_HOPS:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=config.TRUSTED_PROXY_HOPS)

db.init_engine(config.DATABASE_URL)
if not config.IS_PRODUCTION:
    # Production me schema sirf `alembic upgrade head` se banta hai.
    db.Base.metadata.create_all(db.engine)
app.teardown_appcontext(db.close_session)
app.register_blueprint(v1)

# Audio upload ki had — 25MB voice note ke liye kaafi hai.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

# Mobile app ko CORS ki zarurat nahi; ye browser se testing ke liye hai. Har
# route token mangta hai aur cookies istemal nahi hotin, is liye "*" theek hai.
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route("/", methods=["GET"])
def health_check():
    # Render ka health check aur uptime monitor yahan aate hain.
    return jsonify({"status": "Fraud Detector API is running"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Flask debugger kabhi production me nahi — wo server par code chalane deta hai.
    debug = not config.IS_PRODUCTION and os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
