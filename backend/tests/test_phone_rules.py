# Phone ke rules (data/phone_rules.json) ke tests — chalane ke liye
# (backend/ directory se):
#   python -m unittest tests.test_phone_rules
import json
import os
import re
import unittest

import phone_rules
from tests import test_group_messages as engine

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KOTLIN_RULES = os.path.join(
    REPO_ROOT, "FraudGuardExpo", "modules", "expo-call-guard", "android", "src", "main",
    "java", "expo", "modules", "callguard", "TextRules.kt")

# Anchor jo rule ke keywords me nahi hai kabhi match nahi ho sakta. Ye ek app
# me pehle se maujood hai; rule ka behaviour badalna team ka faisla hai, is
# liye yahan sirf darj hai. Naye rules me ye ghalti test rok deta hai.
KNOWN_DEAD_ANCHORS = {("whatsapp_ban_hoax", "verification code")}

RULE_IDS = ["whatsapp_ban_hoax", "investment_group", "voice_clone_family_emergency",
            "money_otp_harvest", "credential_harvest", "lucky_draw_prize"]


def rules_from_kotlin(source):
    """TextRules.kt ke hardcoded lists ko usi shape me nikalta hai jo JSON ki hai."""
    code = "\n".join(l for l in source.splitlines() if not l.strip().startswith("//"))
    strings = lambda body: re.findall(r'"([^"]*)"', body)
    lists = {name: strings(body) for name, body in
             re.findall(r"private val ([A-Z_]+) = listOf\(([^()]*)\)", code)}
    rules = [
        {"id": rule_id, "keywords": strings(kw), "min_match": int(n),
         "anchors": strings(anchors), "label": label}
        for rule_id, (kw, n, anchors, label) in zip(RULE_IDS, re.findall(
            r'Rule\(\s*listOf\(([^()]*)\),\s*(\d+),\s*listOf\(([^()]*)\),\s*"([^"]*)",\s*\)',
            code))
    ]
    return {
        "schema": 1,
        "rules": rules,
        "otp": {
            "delivery_hints": lists["OTP_DELIVERY_HINTS"],
            "negation_hints": lists["OTP_NEGATION_HINTS"],
            "words": lists["OTP_WORDS"],
            "give_send": lists["GIVE_WORDS_SEND"],
            "give_demand": lists["GIVE_WORDS_DEMAND"],
            "weak_action": lists["WEAK_ACTION_WORDS"],
            "urgency": lists["URGENCY_WORDS"],
        },
        "links": {
            "abuse_tlds": lists["ABUSE_TLDS"],
            "official_suffixes": lists["OFFICIAL_SUFFIXES"],
            "official_hosts": lists["OFFICIAL_HOSTS"],
            "generic_trusted": lists["GENERIC_TRUSTED"],
            "brand_tokens": lists["BRAND_TOKENS"],
        },
    }


# Roz marra ke aam messages. Background scanner in par CHUP rehna chahiye —
# naya phone rule add karne se pehle ye list pass honi zaroori hai.
EVERYDAY_MESSAGES = [
    "Beta hospital me emergency hai, jaldi aa jao",
    "Ammi ka accident ho gaya hai, hospital pohancho, madad chahiye",
    "mera account block ho gaya, account secure rakhein",
    "Eid Mubarak! Allah aap ko khush rakhe",
    "I claim that this is the winning habit of good students",
    "Bank ja raha hoon, account ka kaam hai, link bhej dena form ka",
    "Aaj office me job ka pehla din tha, salary achi hai, fee bhi jama kar di school ki",
    "Daily routine: gym, phir kaam. Is mahine profit acha hua dukaan par",
    "Sim ka balance khatam, cnic ki copy bhej do admission form ke liye, block B me rehta hoon",
    "Google meet ka link bhej raha hoon, account login kar lena",
    "Parcel aa gaya hai, delivery charges 200 rupay rider ko de dena",
    "Hospital ka bill easypaisa kar diya hai, receipt bhej di",
    "Abbu ne kaha hai paise bhej do bhai ko, emergency nahi hai aaram se",
    "Meezan bank ka naya branch khula hai, account kholna hai kya? link dekh lo",
    "PTA ne naya tax lagaya hai mobile par, news dekhi?",
    "Bhai emergency hai, jazzcash kar do 500, shaam ko de dunga",
    "Aapka DHL parcel deliver ho gaya hai. Shukriya.",
    "Netflix ka account share kar do yar, password bhej",
    "Dollar ka rate aaj phir barh gaya, daily barh raha hai, return ticket mehenga",
]


class PhoneRulesTests(unittest.TestCase):
    def test_json_matches_the_rules_compiled_into_the_app(self):
        # Jab tak Kotlin apne hardcoded lists use karta hai, dono ek jaise rehne
        # chahiye. Kotlin ke JSON load karne ke baad ye test bundled copy ko
        # dekhega.
        with open(KOTLIN_RULES, encoding="utf-8") as f:
            expected = rules_from_kotlin(f.read())
        self.assertEqual(len(expected["rules"]), len(RULE_IDS))
        actual = {k: v for k, v in phone_rules.PAYLOAD.items() if k != "version"}
        self.assertEqual(actual, expected)

    def test_every_rule_is_well_formed(self):
        for rule in phone_rules.PAYLOAD["rules"]:
            self.assertTrue(rule["id"] and rule["label"], rule)
            self.assertGreaterEqual(rule["min_match"], 2, rule["id"])
            self.assertTrue(rule["anchors"], f"{rule['id']}: anchor ke baghair rule aam baat par chalta hai")
            dead = {(rule["id"], a) for a in rule["anchors"] if a not in rule["keywords"]}
            self.assertEqual(dead - KNOWN_DEAD_ANCHORS, set(), "anchor keywords me hona chahiye")
            for word in rule["keywords"]:
                self.assertEqual(word, word.lower().strip(), rule["id"])

    def test_version_follows_the_content(self):
        self.assertRegex(phone_rules.VERSION, r"^[0-9a-f]{16}$")
        with open(phone_rules.RULES_FILE, encoding="utf-8") as f:
            self.assertNotIn("version", json.load(f), "version khud banta hai, file me nahi likhna")

    def test_everyday_messages_stay_silent(self):
        for text in EVERYDAY_MESSAGES:
            for is_group in (False, True):
                got = engine.classify("03001234567", text, is_group=is_group)
                self.assertIsNone(got, f"false alarm: {text!r} -> {got}")


if __name__ == "__main__":
    unittest.main()
