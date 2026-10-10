import json, os, re

patterns_path = os.path.join(os.path.dirname(__file__), "data", "scam_patterns.json")
with open(patterns_path, "r", encoding="utf-8") as f:
    PATTERNS = json.load(f)

# Bank ki APNI OTP/alert SMS scam nahi hoti — "OTP bhij do" maangta hai, scam.
# Ye distinction na hone se official bank SMS bhi "credential harvesting" kehla rahi thi.
OTP_DELIVERY_HINTS = (
    "do not share", "don't share", "donot share", "never share", "not share",
    "share na kare", "share mat kare", "share na kr", "kisi ke sath share",
    "kisi ko na", "for your security", "for the security", "not authorized",
)

def _looks_like_otp_delivery(text_lower: str) -> bool:
    import re
    return bool(re.search(r"\b\d{4,8}\b", text_lower)) and any(
        hint in text_lower for hint in OTP_DELIVERY_HINTS
    )

def _matched(pattern, text_lower):
    return [k.lower() for k in pattern["keywords"] if k.lower() in text_lower]

def check_patterns(text: str):
    # ✅ FIX: If the text is massive (like a full WhatsApp export),
    # the rule engine will trigger false positives by finding random
    # words scattered across months of chat.
    # Bypass the rule engine for large files and let Gemini handle it!
    if len(text) > 500:
        return None

    text_lower = text.lower()
    if _looks_like_otp_delivery(text_lower):
        return None

    # `anchors` = wo keywords jo scam ko aam baat se alag karte hain (idare ka
    # naam, OTP mangna, customs clearance). Sirf `link`/`click`/`verify`/`account`
    # jaise aam lafz match hon — jo har zaroori invitation ya shared link mein
    # hote hain — par koi anchor na ho, to rule engine chup rehta hai aur faisla
    # Gemini karta hai. Warna har sachche link par 90%+ "fraud" aa jata tha.
    for pattern in PATTERNS:
        matched = _matched(pattern, text_lower)
        anchors = [a.lower() for a in pattern.get("anchors", [])]
        if len(matched) >= pattern["min_match"] and (not anchors or any(a in matched for a in anchors)):
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
