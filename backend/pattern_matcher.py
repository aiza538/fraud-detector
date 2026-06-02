import json, os

patterns_path = os.path.join(os.path.dirname(__file__), "data", "scam_patterns.json")
with open(patterns_path, "r", encoding="utf-8") as f:
    PATTERNS = json.load(f)

def check_patterns(text: str):
    # ✅ FIX: If the text is massive (like a full WhatsApp export), 
    # the rule engine will trigger false positives by finding random 
    # words scattered across months of chat. 
    # Bypass the rule engine for large files and let Gemini handle it!
    if len(text) > 500: 
        return None 

    text_lower = text.lower()
    for pattern in PATTERNS:
        matched = sum(1 for k in pattern["keywords"] if k.lower() in text_lower)
        if matched >= pattern["min_match"]:
            return {
                "fraud": True,
                "type": pattern["type"],
                "confidence": pattern["confidence"],
                "peca": pattern["peca"],
                "attack": pattern["attack"],
                "target": pattern["target"],
                "language": "Roman Urdu",
                "tactics": pattern["tactics"],
                "education": pattern["education"],
                "complaint": pattern["complaint"],
                "transcript": None
            }
    return None