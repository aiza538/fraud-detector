import google.generativeai as genai
from pattern_matcher import check_patterns
from dotenv import load_dotenv
import os, json

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

def analyze_text(text: str):
    # Layer 1 — rule engine
    pattern_result = check_patterns(text)
    if pattern_result:
        return pattern_result

    # Layer 2 — Gemini
    prompt = f"""
You are a Pakistani cybercrime expert. Analyze this message for fraud.
Message: "{text}"

Reply ONLY with this exact JSON, no extra text, no markdown:
{{
  "fraud": true or false,
  "type": "attack type",
  "confidence": number 0-100,
  "peca": "PECA 2016 section if fraud, else No violation",
  "attack": "attack method",
  "target": "targeted entity",
  "language": "English or Roman Urdu or Urdu",
  "tactics": ["tactic1", "tactic2"],
  "education": ["tip1", "tip2", "tip3"],
  "complaint": "FIA complaint text if fraud, else null",
  "transcript": null
}}
"""
    response = model.generate_content(prompt)
    clean = response.text.strip()
    if "```" in clean:
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())