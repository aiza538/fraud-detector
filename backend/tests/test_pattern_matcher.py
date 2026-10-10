# Rule engine ke false positives ka check — chalane ke liye:
#   python -m tests.test_pattern_matcher   (backend/ directory se)
from pattern_matcher import check_patterns

# (text, expected_fraud) — expected_fraud False ka matlab rule engine chup rahe,
# faisla Gemini ke paas jaye.
CASES = [
    # Pehle ye sab par 90%+ "fraud" aa raha tha — aam zaroori messages
    (False, "Please click the link to verify your account and upload documents: https://forms.office.com/r/x1"),
    (False, "Meeting ke notes yahan hain, link khol kar dekh lein: https://drive.google.com/file/d/1Ab"),
    (False, "Job ka update: salary 25 USD hai, registration 24 Sept ko, aap selected ho — details group mein"),
    (False, "Aapka order delivery par hai, charges prepaid hain: https://daraz.pk/order/44"),

    # Bank ki APNI OTP SMS — credential harvesting nahi
    (False, "Your one-time password is 884213. Do not share this code with anyone. — HBL"),

    # Asli scam patterns — ye pakke hone chahiye
    (True, "HBL security team: aapka account band ho raha hai, OTP bhejein warna transaction ruk jayegi"),
    (True, "Meezan Bank: account verify karne ke liye is link par OTP enter karein"),
    (True, "SIM block ho jayega, CNIC verify karein: ptcl office link"),
    (True, "BISP ki 25000 rupee ki raqam aapke liye, 8171 wazeefa, paisa lene ke liye fee bhejein"),
    (True, "Congratulations! Aap lucky draw ke winner hain, claim karne ke liye charges send karein"),
    (True, "WhatsApp 24 hour mein band ho jayega, verification code recover karne ke liye ye forward karein"),
    (True, "Parcel customs mein atak gaya hai, dollar clearance fee airport se deni hai"),
    (True, "Beta hospital mein hai, emergency hai, thore paise bhej do"),
    (True, "Daily profit wala trading group, invest karein aur dollar return milega, member fee"),
    (True, "PTA ne kaha aapka IMEI register na hua to dirbs se phone block, fbr se tax payable"),
    (True, "Beta hoon, meri awaz pehchan kar loan de dein, udhaar ki baat hai"),

    # Voice note bhejna aam baat hai — paisa mangne ka lafz na ho to rule chup rahe
    (False, "Emergency ki video thi, beta ka voice note suno, audio message bhej raha hoon"),
    (False, "Trading group join karo, members 200 hain, telegram par updates milte hain"),

    # ---- REGRESSION: Android native mirror ka anchors gate add hua tha ----
    # Ye sab native TextRules par scam the (kyunki mirror ke paas anchors nahi
    # the), lekin backend par pehle bhi the. Anchor gate add hone ke baad bhi
    # backend chup rehna chahiye — ye usi rule ka regression cover hai.
    (False, "Beta emergency me hospital aa jao, jaldi pohanch jana"),
    (False, "Aaj hi paise bhej do, jaldi zaroori hai"),
    (False, "Mera account block ho gaya hai, account secure rakhna please"),
    (False, "Family group me baat kar lo, daily plan discuss karna hai, group meeting 6pm hai"),
    (False, "Bhai loan dena tha, udhaar baad me de dunga"),
    (False, "Aapki bank statement generate ho gayi, account detail share kar do"),
    (False, "Please review and claim your warranty — return within 7 days, daily updates on tracking"),
    (False, "Mubarak ho aapko! Eid ki khushiyan, inam ke taur par paani ki botal lein"),
    (False, "Aap jeet gaye hain jeet ka coupon code: SAVE20 apply karein"),
    (False, "Order confirm karein aur payment JazzCash se bhej dein, invoice attach hai"),
    (False, "Password update ho gaya hai, security ke liye OTP ka maangna nahi chahiye"),
]


def main():
    failed = []
    for expected, text in CASES:
        got = check_patterns(text) is not None
        if got != expected:
            verdict = "fraud" if got else "no-verdict"
            failed.append(f"expected {'fraud' if expected else 'no-verdict'}, got {verdict}\n  text: {text}")
    if failed:
        raise SystemExit("FAIL:\n" + "\n".join(failed))
    print(f"OK - {len(CASES)} cases, rule engine sahi jagah chup hai aur sahi jagah bolta hai")


if __name__ == "__main__":
    main()