"""Phone ke background scanner ke rules — `data/phone_rules.json`.

Ye server ke `scam_patterns.json` se JAAN BOOJH kar alag hain. Server ke
patterns tab chalte hain jab user khud koi shak wala message check karta hai;
phone ke rules HAR aane wale message par khud chalte hain, is liye bohat
zyada sakht hain. Server ke patterns phone par chalane se aam messages
("parcel aa gaya, charges rider ko de dena") par scam alert aane lagte hain.

Phone ye file `/v1/rules` se download karta hai, taake rules app ka naya
version release kiye baghair update ho sakein.
"""
import hashlib
import json
import os

RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "phone_rules.json")

with open(RULES_FILE, "r", encoding="utf-8") as f:
    _doc = json.load(f)

# `_about` jaise documentation keys phone ko nahi bheje jate.
PAYLOAD = {k: v for k, v in _doc.items() if not k.startswith("_")}
# Content ka hash: file badalte hi version badal jata hai, haath se number
# barhana bhoolne ka koi khatra nahi. Phone isi se "kuch naya hai?" poochta hai.
VERSION = hashlib.sha256(
    json.dumps(PAYLOAD, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
PAYLOAD["version"] = VERSION
