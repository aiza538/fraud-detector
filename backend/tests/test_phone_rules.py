# Phone ke rules (data/phone_rules.json) ke tests — chalane ke liye
# (backend/ directory se):
#   python -m unittest tests.test_phone_rules
import json
import os
import unittest

import phone_rules
from tests import test_group_messages as engine

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ANDROID_MAIN = os.path.join(REPO_ROOT, "FraudGuardExpo", "modules", "expo-call-guard",
                            "android", "src", "main")
KOTLIN_RULES = os.path.join(ANDROID_MAIN, "java", "expo", "modules", "callguard", "TextRules.kt")
# App ke andar ki copy — internet na ho, ya server se abhi kuch na aaya ho, to yahi chalti hai.
BUNDLED_RULES = os.path.join(ANDROID_MAIN, "assets", "phone_rules.json")

# Anchor jo rule ke keywords me nahi hai kabhi match nahi ho sakta. Ye ek app
# me pehle se maujood hai; rule ka behaviour badalna team ka faisla hai, is
# liye yahan sirf darj hai. Naye rules me ye ghalti test rok deta hai.
KNOWN_DEAD_ANCHORS = {("whatsapp_ban_hoax", "verification code")}


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
    def test_app_ships_the_same_rules_as_the_server(self):
        with open(BUNDLED_RULES, "rb") as bundled, open(phone_rules.RULES_FILE, "rb") as server:
            self.assertEqual(
                bundled.read(), server.read(),
                "backend/data/phone_rules.json badli hai — app ki copy (assets/phone_rules.json) bhi update karein")

    def test_kotlin_has_no_second_copy_of_the_rules(self):
        # Pehle rules Kotlin me haath se likhi thin aur server se alag ho gayi thin.
        with open(KOTLIN_RULES, encoding="utf-8") as f:
            self.assertNotIn('listOf("', f.read(), "rules phone_rules.json me rakhein, Kotlin code me nahi")

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
