from google import genai
from pattern_matcher import check_patterns
from dotenv import load_dotenv
import os, json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=GEMINI_KEY)

def analyze_text(text: str, channel: str = None):

    logging.info("[🔍 FraudGuard Backend] Received a text analysis request")
    # ✅ TRUNCATE MASSIVE FILES: Protect your 250k token quota!
    # A 2-year WhatsApp log is too huge. We only care about the most recent 
    # messages where the scam actually happens. Keep the last 15,000 characters.
    if len(text) > 15000:
        text = text[-15000:]

    # Layer 1 - rule engine (no API needed)
    pattern_result = check_patterns(text)
    if pattern_result:
        # ✅ DEV FLAG: Mark that this came from Layer 1
        pattern_result["_source"] = "Rule_Engine" 
        return pattern_result

    channel_context = ""
    if channel == "whatsapp":
        channel_context = "\nThe message below was copied from a WhatsApp chat (could be a direct message, group chat, or a forwarded chain message).\n"

    # Layer 2 - Gemini (API needed)
    prompt = f"""
You are a Pakistani cybercrime expert. Analyze this message for fraud.{channel_context}
Message: "{text}"

Reply ONLY with this exact JSON, no extra text, no markdown:
{{
  "fraud": true or false,
  "type": "attack type or Safe Message",
  "confidence": number 0-100,
  "peca": "PECA 2016 section if fraud, else No violation",
  "attack": "attack method or None",
  "target": "targeted entity or General Public",
  "language": "English or Roman Urdu or Urdu",
  "tactics": [],
  "education": ["tip1", "tip2", "tip3"],
  "complaint": "FIA complaint text if fraud, else null",
  "transcript": null
}}
"""
    # ✅ MULTI-MODEL FALLBACK LOOP
    # If the first model hits a quota limit, it automatically tries the next one!
    models_to_try = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.0-flash"]
    
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            if not response or not response.text:
                continue

            clean = response.text.strip()

            if "```" in clean:
                parts = clean.split("```")
                clean = parts[1] if len(parts) > 1 else parts[0]
            if clean.lower().startswith("json"):
                clean = clean[4:]

            result = json.loads(clean.strip())

            result.setdefault("fraud", False)
            result.setdefault("type", "Unknown")
            result.setdefault("confidence", 0)
            result.setdefault("peca", "No violation")
            result.setdefault("attack", "None")
            result.setdefault("target", "Unknown")
            result.setdefault("language", "Unknown")
            result.setdefault("tactics", [])
            result.setdefault("education", [])
            result.setdefault("complaint", None)
            result.setdefault("transcript", None)

            # ✅ DEV FLAG: See exactly which model successfully answered
            result["_source"] = f"Gemini_LLM ({model_name})" 

            return result

        except json.JSONDecodeError:
            print(f"[warn] {model_name} returned unparseable JSON, trying next model...")
            continue

        except Exception as e:
            # 429/503/500/404 sab transient ya model-level issues hain — agla model try karo,
            # yahin "safe" return karna galat assurance dega
            print(f"[warn] {model_name} failed: {str(e)[:120]} -- trying next model...")
            continue

    # Saare models fail ho gaye. Rule engine ne fraud nahi pakda, is liye AI
    # layer ke jaate hi "safe" kehna victim ko risk mein daal deta hai.
    return get_ai_error_response()

def get_ai_error_response():
    return {
        "error": "AI analysis is unavailable right now (all models failed or are busy). This message did NOT match any known scam pattern, but that does not mean it is safe — please try again in a minute.",
        "_source": "AI_Unavailable",
    }