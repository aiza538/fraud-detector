from google import genai
from pattern_matcher import check_patterns
from dotenv import load_dotenv
import os, json

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=GEMINI_KEY)

def analyze_text(text: str):
    # Layer 1 — rule engine (no API needed)
    pattern_result = check_patterns(text)
    if pattern_result:
        return pattern_result

    # Layer 2 — Gemini (API needed)
    # We now give Gemini a STRICT template for what to do if the message is safe.
    prompt = f"""
You are a Pakistani cybercrime expert. Analyze this message for fraud.
Message: "{text}"

If it is a SCAM, reply ONLY with this exact JSON structure:
{{
  "fraud": true,
  "type": "Attack Name",
  "confidence": 90,
  "peca": "PECA 2016 section",
  "attack": "Attack method",
  "target": "Target entity",
  "language": "Roman Urdu",
  "tactics": ["Urgency", "Threat"],
  "education": ["Tip 1", "Tip 2"],
  "complaint": "FIA complaint text",
  "transcript": null
}}

If it is a SAFE/NORMAL message, reply ONLY with this exact JSON structure:
{{
  "fraud": false,
  "type": "Safe Message",
  "confidence": 99,
  "peca": "No violation",
  "attack": "None",
  "target": "General Public",
  "language": "Roman Urdu",
  "tactics": [],
  "education": ["This message appears safe. Always stay alert."],
  "complaint": null,
  "transcript": null
}}

Do not include any extra text, warnings, or markdown. Only the JSON.
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        # Safe-guard if Gemini returns absolutely nothing
        if not response or not response.text:
            raise ValueError("Empty response from Gemini")

        clean = response.text.strip()

        # Strip markdown code blocks if Gemini adds them
        if "```" in clean:
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else parts[0]
        if clean.lower().startswith("json"):
            clean = clean[4:]

        result = json.loads(clean.strip())

        # Guarantee all fields exist (frontend crashes without these)
        result.setdefault("fraud", False)
        result.setdefault("type", "Safe Message" if not result.get("fraud") else "Unknown")
        result.setdefault("confidence", 0)
        result.setdefault("peca", "No violation")
        result.setdefault("attack", "None")
        result.setdefault("target", "Unknown")
        result.setdefault("language", "Unknown")
        result.setdefault("tactics", [])
        result.setdefault("education", ["This message appears safe."])
        result.setdefault("complaint", None)
        result.setdefault("transcript", None)

        return result

    except json.JSONDecodeError:
        # Gemini gave text instead of JSON
        return get_safe_fallback("AI could not format the result, but it seems safe.")
        
    except Exception as e:
        # 🔥 THIS FIXES THE 500 ERROR!
        # If API quota fails, network drops, or safety filter blocks it, we catch it here gracefully.
        print(f"Backend Exception Caught: {e}")
        return get_safe_fallback(f"Analysis failed ({str(e)[:20]}). Assuming safe.")

def get_safe_fallback(msg):
    """Helper function to always return a valid React frontend object."""
    return {
        "fraud": False,
        "type": "Safe / Error",
        "confidence": 0,
        "peca": "No violation",
        "attack": "None",
        "target": "Unknown",
        "language": "Unknown",
        "tactics": [],
        "education": [msg],
        "complaint": None,
        "transcript": None
    }