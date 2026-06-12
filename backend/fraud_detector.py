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

def analyze_text(text: str):

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

    # Layer 2 - Gemini (API needed)
    prompt = f"""
You are a Pakistani cybercrime expert. Analyze this message for fraud.
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
            return get_safe_fallback("AI could not format the result, but it seems safe.", source=f"Error_JSON_{model_name}")
            
        except Exception as e:
            error_msg = str(e)
            # If we hit a quota error, print a warning and let the loop try the next model
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print(f"⚠️ Quota hit for {model_name}, switching to next model...")
                continue 
            
            # For any other random API error, fallback safely
            print(f"Backend Exception Caught: {e}")
            return get_safe_fallback(f"Analysis failed ({str(e)[:20]}). Assuming safe.", source="Error_Catch")
            
    # If the loop finishes and ALL models in the list were exhausted
    return get_safe_fallback("All AI models are currently busy (Quota Exceeded). Please try again in 1 minute.", source="All_Quotas_Exhausted")

def get_safe_fallback(msg, source="Fallback"):
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
        "transcript": None,
        "_source": source 
    }