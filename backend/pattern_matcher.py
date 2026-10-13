import json, os, re

patterns_path = os.path.join(os.path.dirname(__file__), "data", "scam_patterns.json")

def load_scam_patterns(region: str = None, filepath: str = None):
    """Parses scam patterns and whitelists with root region key filtering ('PK', 'GLOBAL').
    
    If region is provided ('PK', 'GLOBAL'), returns patterns and whitelists relevant for
    that region. If None, returns all patterns and whitelists.
    """
    path = filepath or patterns_path
    with open(path, "r", encoding="utf-8") as f:
        raw_doc = json.load(f)

    loaded_patterns = []
    loaded_whitelists = []
    
    if isinstance(raw_doc, dict) and "regional" in raw_doc:
        for reg_code, reg_info in raw_doc["regional"].items():
            if region:
                reg_clean = str(region).strip().upper()
                if reg_clean == "PK" and reg_code.upper() not in ("PK", "GLOBAL", "ALL"):
                    continue
                elif reg_clean != "PK" and reg_code.upper() not in (reg_clean, "GLOBAL", "ALL"):
                    continue
            
            # Whitelists
            for grp_name, items in reg_info.get("whitelists", {}).items():
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict):
                            loaded_whitelists.append({
                                **it,
                                "region": reg_code.upper(),
                                "group": grp_name
                            })
            
            # Patterns
            for pat in reg_info.get("patterns", []):
                if isinstance(pat, dict):
                    loaded_patterns.append({
                        **pat,
                        "region": pat.get("region", reg_code.upper())
                    })
    
    return {
        "patterns": loaded_patterns,
        "whitelists": loaded_whitelists,
        "raw": raw_doc
    }

with open(patterns_path, "r", encoding="utf-8") as f:
    _RAW_PATTERNS = json.load(f)

# Multi-region architecture: extract patterns and transactional whitelists
PATTERNS = []
WHITELISTS = []

if isinstance(_RAW_PATTERNS, dict):
    # 1. Multi-region architecture under 'regional'
    if "regional" in _RAW_PATTERNS and isinstance(_RAW_PATTERNS["regional"], dict):
        for reg_code, reg_info in _RAW_PATTERNS["regional"].items():
            if not isinstance(reg_info, dict):
                continue
            
            # Extract and precompile whitelists
            wl_groups = reg_info.get("whitelists", {})
            if isinstance(wl_groups, dict):
                for grp_name, items in wl_groups.items():
                    if isinstance(items, list):
                        for it in items:
                            if isinstance(it, dict) and "regex" in it:
                                try:
                                    WHITELISTS.append({
                                        "id": it.get("id"),
                                        "regex": re.compile(it["regex"], re.IGNORECASE),
                                        "region": reg_code.upper()
                                    })
                                except Exception:
                                    pass
            
            # Extract and precompile patterns
            for pat in reg_info.get("patterns", []):
                if isinstance(pat, dict) and "keywords" in pat:
                    if "region" not in pat:
                        pat["region"] = reg_code.upper()
                    if "regex" in pat and "_regex_compiled" not in pat:
                        try:
                            pat["_regex_compiled"] = re.compile(pat["regex"], re.IGNORECASE)
                        except Exception:
                            pat["_regex_compiled"] = None
                    PATTERNS.append(pat)

    # 2. Backward compatibility fallback for top-level sectioned dict
    if not PATTERNS:
        for sec_key, sec_val in _RAW_PATTERNS.items():
            if isinstance(sec_val, list):
                for pat in sec_val:
                    if isinstance(pat, dict) and "keywords" in pat:
                        if "region" not in pat:
                            pat["region"] = "GLOBAL" if "international" in sec_key else "PK"
                        if "regex" in pat and "_regex_compiled" not in pat:
                            try:
                                pat["_regex_compiled"] = re.compile(pat["regex"], re.IGNORECASE)
                            except Exception:
                                pat["_regex_compiled"] = None
                        PATTERNS.append(pat)

elif isinstance(_RAW_PATTERNS, list):
    for pat in _RAW_PATTERNS:
        if isinstance(pat, dict):
            if "region" not in pat:
                pat["region"] = "PK"
            if "regex" in pat and "_regex_compiled" not in pat:
                try:
                    pat["_regex_compiled"] = re.compile(pat["regex"], re.IGNORECASE)
                except Exception:
                    pat["_regex_compiled"] = None
            PATTERNS.append(pat)

# Bank ki APNI OTP/alert SMS scam nahi hoti — "OTP bhij do" maangta hai, scam.
# Ye distinction na hone se official bank SMS bhi "credential harvesting" kehla rahi thi.
OTP_DELIVERY_HINTS = (
    "do not share", "don't share", "donot share", "never share", "not share",
    "share na kare", "share mat kare", "share na kr", "kisi ke sath share",
    "kisi ko na", "for your security", "for the security", "not authorized",
)

def _looks_like_otp_delivery(text_lower: str) -> bool:
    return bool(re.search(r"\b\d{4,8}\b", text_lower)) and any(
        hint in text_lower for hint in OTP_DELIVERY_HINTS
    )

def _matched(pattern, text_lower):
    return [k.lower() for k in pattern["keywords"] if k.lower() in text_lower]

def check_patterns(text: str, region: str = None):
    # ✅ FIX: If the text is massive (like a full WhatsApp export),
    # the rule engine will trigger false positives by finding random
    # words scattered across months of chat.
    # Bypass the rule engine for large files and let Gemini handle it!
    if len(text) > 500:
        return None

    text_lower = text.lower()
    if _looks_like_otp_delivery(text_lower):
        return None

    # Check registered transactional and tech whitelists
    for wl in WHITELISTS:
        if region:
            reg_clean = str(region).strip().upper()
            if wl["region"] not in (reg_clean, "GLOBAL", "ALL"):
                continue
        if wl["regex"].search(text):
            return None

    # Region filter: safe check avoiding any KeyErrors
    if region:
        reg_clean = str(region).strip().upper()
        # Specific region requested: include that region + GLOBAL/ALL ubiquitous patterns
        candidate_patterns = [
            p for p in PATTERNS
            if p.get("region", "PK").upper() in (reg_clean, "GLOBAL", "ALL")
        ]
    else:
        candidate_patterns = PATTERNS

    # `anchors` = wo keywords jo scam ko aam baat se alag karte hain (idare ka
    # naam, OTP mangna, customs clearance). Sirf `link`/`click`/`verify`/`account`
    # jaise aam lafz match hon — jo har zaroori invitation ya shared link mein
    # hote hain — par koi anchor na ho, to rule engine chup rehta hai aur faisla
    # Gemini karta hai. Warna har sachche link par 90%+ "fraud" aa jata tha.
    for pattern in candidate_patterns:
        rgx = pattern.get("_regex_compiled")
        regex_matched = bool(rgx.search(text)) if rgx else False

        matched = _matched(pattern, text_lower)
        anchors = [a.lower() for a in pattern.get("anchors", [])]
        kw_matched = len(matched) >= pattern.get("min_match", 3) and (not anchors or any(a in matched for a in anchors))

        if regex_matched or kw_matched:
            return {
                "fraud": True,
                "type": pattern["type"],
                "confidence": pattern["confidence"],
                "peca": pattern["peca"],
                "statutory_violation": pattern.get("statutory_violation"),
                "attack": pattern["attack"],
                "target": pattern["target"],
                "region": pattern.get("region", "PK"),
                "language": pattern.get("language", "Roman Urdu"),
                "tactics": pattern["tactics"],
                "education": pattern["education"],
                "complaint": pattern["complaint"],
                "transcript": None
            }
    return None
