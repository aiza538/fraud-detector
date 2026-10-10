# Group false-positive ka regression test — chalane ke liye:
#   python -m tests.test_group_messages   (backend/ directory se)
#
# YE TEST `TextRules.kt` ka PYTHON MIRROR hai, khud rule engine nahi. Kotlin
# native code compile karke test karna is repo me possible nahi (sirf device
# build hai), is liye rules yahan mirror hain. Kotlin me koi rule badle to ye
# mirror bhi update karna zaroori hai — warna test jhooth assure karega.
#
# Ye test tab likha gaya jab EVERY group ka link scam/suspicious alert bana
# deta tha. Sach ye hai:
#   - WhatsApp group notification ka TITLE group ka naam hota hai, member ka
#     number nahi → app ko pata hi nahi chalta ke link kisne bheja.
#   - Job/course/training ke asli ads roz aati hain, aur naye TLD (.top,
#     .xyz, .link, .work) un par lagte hain.
#   - Result: 5 mein se 4 ASLI course/job ad flag ho rahe thay.
#
# Fix: group me sirf TEXT-based scam (OTP mangna, prize/lottery, bank
# impersonation) alert karta hai; link analysis wahan chalti hi nahi.
# 1:1 chat me link analysis chalti hai — wahan sender ki identity hoti hai.
import re

# --- TextRules.kt ka mirror --------------------------------------------------

RULES = [
    (["whatsapp", "ban", "verification", "code", "24 hour", "band", "recover", "forward"], 3,
     ["verification code", "24 hour", "recover", "band"],
     "WhatsApp account ban hoax — verification code mangna hijacking attempt hai"),
    (["invest", "profit", "trading", "group", "dollar", "daily", "return", "fee", "telegram"], 3,
     ["invest", "profit", "trading", "telegram"],
     "Investment group scam — guaranteed daily profit Ponzi fraud hai"),
    (["meri awaz", "voice", "audio message", "beta", "bachi", "loan", "udhaar", "paise bhej",
      "emergency", "hospital"], 3,
     ["meri awaz", "loan", "udhaar", "paise bhej"],
     "Cloned voice / family emergency scam — voice message identity proof nahi"),
    (["otp", "bhij", "bhej", "paise", "jaldi", "foran", "easypaisa", "jazzcash",
      "account detail", "atm card"], 3,
     ["otp", "easypaisa", "jazzcash", "account detail", "atm card"],
     "Money/OTP harvesting message — koi bhi OTP ya payment request verify karke hi bhejein"),
    (["otp", "verification code", "atm card", "card number", "cnic", "account detail",
      "bank account", "account secure", "account block", "account band", "account freeze"], 2,
     ["otp", "verification code", "atm card", "card number", "cnic", "account detail",
      "bank account"],
     "Credential harvesting attempt — bank/authority OTP, ATM details ya CNIC KABHI nahi mangta"),
    (["lucky draw", "luckydraw", "prize bond", "prizebond", "coupon", "win", "won", "jeet",
      "bike", "motorbike", "scooty", "mobile phone", "lottery", "cash price", "cash prize",
      "inam", "mubarak", "rabta", "claim", "winner"], 3,
     ["lucky draw", "luckydraw", "prize bond", "prizebond", "lottery", "cash prize",
      "cash price", "winner", "inam", "rabta"],
     "Lucky draw / prize scam — unknown SMS ka 'bike/cash jeet gaye' nara fake lottery bait hai"),
]

# `.work`, `.loan`, `.cam`, `.rest`, `.monster` nikal diye gaye — ye aaj kal
# bohat se ASLI companies (recruiters, training institutes) use karti hain.
ABUSE_TLDS = [".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click", ".link",
              ".buzz", ".icu", ".vip", ".quest", ".cyou"]
OFFICIAL_SUFFIXES = [".gov.pk", ".gob.pk", ".edu.pk", ".gov", ".gob"]
OFFICIAL_HOSTS = ["hbl.com", "ubl.com.pk", "nbp.com.pk", "mcb.com.pk", "alliedbank.com",
                  "abl.com", "bankalfalah.com", "meezanbank.com", "bop.com.pk", "sc.com",
                  "bankislami.com.pk", "faysalbank.com", "askari.com", "soneribank.com",
                  "hmb.com.pk", "summitbank.com.pk", "karobank.com.pk", "sindhbank.gov.pk",
                  "easypaisa.com.pk", "esappk.com", "jazzcash.com.pk", "jazz.com.pk",
                  "zong.com.pk", "ufone.com", "telia.com.pk", "nadra.gov.pk", "fia.gov.pk",
                  "fbr.gov.pk", "pta.gov.pk", "bisp.gov.pk", "sbp.org.pk",
                  "complaint.sbp.org.pk", "sadapay.pk", "nayapay.com.pk"]
GENERIC_TRUSTED = ["facebook.com", "instagram.com", "whatsapp.com", "google.com",
                   "youtube.com", "twitter.com", "x.com", "linkedin.com", "microsoft.com",
                   "apple.com"]
BRAND_TOKENS = ["hbl", "nbp", "mcb", "ubl", "alfalah", "meezan", "islami", "askari",
                "faysal", "soneri", "jamhoor", "samba", "silkbank", "kmb", "summit", "karo",
                "citi", "standardchartered", "easypaisa", "jazzcash", "jazz", "zong", "ufone",
                "telia", "nadra", "fbr", "fia", "pta", "bisp", "ehsaas", "statebank", "sbp",
                "sadapay", "nepcard", "omnipay", "finja", "police", "court", "tax"]

URL_RE = re.compile(r"""https?://[^\s<>"']+|www\.[^\s<>"']+""", re.I)
IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
OTP_DELIVERY_HINTS = ["do not share", "don't share", "donot share", "never share",
                      "not share", "share na kare", "share mat kare", "share na kr",
                      "kisi ke sath share", "kisi ko na", "for your security",
                      "for the security", "not authorized"]
OTP_WORDS = ["otp", "one time password", "one-time password", "verification code",
             "otp number", "code bata"]
GIVE_SEND = ["bhej", "bhij", "bej", "bheeg", "bhejna", "bhejo", "send", "forward", "share",
             "dena", "deina", "dein", "dijiye", "day", "de", "dy", "di", "do"]
GIVE_DEMAND = ["maang", "mang", "chahiye", "chahe", "milwa", "mila", "bataye", "bataiye"]


def contains_keyword(hay, kw):
    kw = kw.strip()
    if not kw:
        return False
    if any(c.isspace() or c == "/" for c in kw):
        return kw in hay
    if kw[0].isdigit():
        return kw in hay
    return re.search(r"(^|[^a-z0-9])" + re.escape(kw) + r"([^a-z0-9]|$)", hay) is not None


def has_any_word(text, words):
    for w in words:
        if len(w) <= 3:
            if re.search(r"(^|[^a-z])" + re.escape(w) + r"([^a-z]|$)", text):
                return True
        elif w in text:
            return True
    return False


def looks_like_otp_delivery(text):
    return bool(re.search(r"\b\d{4,8}\b", text)) and any(h in text for h in OTP_DELIVERY_HINTS)


def match_rules(text):
    low = text.lower()
    for kws, mn, anchors, label in RULES:
        matched = {k for k in kws if contains_keyword(low, k)}
        if len(matched) < mn:
            continue
        if not any(a in matched for a in anchors):
            continue
        return label
    return None


def match_otp_harvest(text):
    low = text.lower()
    if looks_like_otp_delivery(low) or "do not share" in low:
        return None
    if not has_any_word(low, OTP_WORDS):
        return None
    if has_any_word(low, GIVE_SEND) or has_any_word(low, GIVE_DEMAND):
        return "OTP harvesting attempt"
    return None


def ends_with_any(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def host_of(url):
    auth = url.split("://", 1)[1] if "://" in url else url
    auth = auth.split("/")[0]
    auth = auth.split("@")[0]
    return auth.split(":")[0].lstrip(".")


def has_brand_token(host):
    return any(re.search(r"(^|[^a-z])" + re.escape(t) + r"([^a-z]|$)", host)
               for t in BRAND_TOKENS)


def match_suspicious_link(text):
    for raw in URL_RE.finditer(text):
        url = raw.group().lower().rstrip(".,)]>")
        host = host_of(url)
        if not host:
            continue
        if ends_with_any(host, OFFICIAL_HOSTS) or ends_with_any(host, GENERIC_TRUSTED):
            continue
        if any(host.endswith(s) for s in OFFICIAL_SUFFIXES):
            continue
        auth = url.split("://", 1)[1].split("/")[0] if "://" in url else url
        if IP_RE.match(host):
            return "link direct IP par khula raha hai"
        if "@" in auth:
            return "credentials@host"
        if any(host.endswith(t) for t in ABUSE_TLDS):
            return f"abuse TLD ({host})"
        if has_brand_token(host):
            return f"brand impersonation ({host})"
    return None


def classify(title, body, trusted_sender=False, is_group=False):
    """classifyMessageWithSeverity ka mirror — return (label, severity) ya None."""
    if trusted_sender:
        return None
    full = f"{title} {body}".lower()
    if not looks_like_otp_delivery(full):
        if (r := match_rules(full)):
            return (r, "scam")
        if (o := match_otp_harvest(full)):
            return (o, "scam")
    # --- YAHAN FIX HAI: group me link analysis chalti hi nahi ---
    if not is_group and (l := match_suspicious_link(full)):
        return (l, "suspicious")
    return None


# --- Cases -------------------------------------------------------------------
# (label, title, body, is_group, expected_severity_or_None)

GROUP_LEGIT = [
    ("course ad on .top", "Career Connect Group (12 messages)",
     "Assalam o alaikum. Python Data Science course start ho raha hai. Fee 15000, "
     "monthly 2 classes. Register: www.careercourse.top"),
    ("job ad on .xyz", "Job Alerts PK (30 messages)",
     "Fresh opening: Marketing Executive, Lahore. Salary 45000. Apply before 24 Sept. "
     "Form: http://jobsapply.xyz/register"),
    ("course promo on .link", "Freelancing Group (5 messages)",
     "Bhai aaj ka client project mil gaya hai. Register now: https://smmcourse.link/promo"),
    ("university on .edu.pk", "University Admissions (8 messages)",
     "FAST admissions open. Apply online at https://fast.edu.pk/apply. Fee in brochure."),
    ("training on .work", "IT Training Group (3 messages)",
     "Cisco course batch start ho gaya. Duration 6 months. "
     "Register: www.ccna-course.work"),
    ("sarkari job ad", "Govt Jobs (20 messages)",
     "NADRA me 15 vacancies hain. Apply: https://nadra.gov.pk/jobs"),
    ("normal group chat", "Family (4 messages)",
     "Dinner 8pm pe khana khana? Mummy ne samosay banaye hain"),
    ("legit link, .com", "Study Group (9 messages)",
     "Notes yahan hain: https://drive.google.com/file/d/1Ab"),
]

# Group me link chup ho, magar TEXT-based scam pakda jaaye
GROUP_REAL_SCAMS = [
    ("otp demand in group", "Unknown (1 message)",
     "Bhai OTP number bhej do, account verify karne ke liye foran chahiye", "scam"),
    ("prize bait in group", "Offers (7 messages)",
     "Aap lucky draw ke winner hain! Cash prize 50000 claim karne ke liye coupon "
     "fees bhejein", "scam"),
    ("bank impersonation in group", "Random (1 message)",
     "HBL security: aapka account band ho raha hai, OTP bhejein warna transaction "
     "ruk jayegi", "scam"),
]

# 1:1 chat me link analysis CHALTI hai — wahan sender ki identity hai
DIRECT_LEGIT_LINK = [
    ("shared zoom link", "Ali",
     "Kal meeting ka link hai: https://zoom.us/j/123456789"),
    ("shared drive link", "Ali",
     "Notes: https://drive.google.com/file/d/1Ab"),
]

DIRECT_SUSPICIOUS_LINK = [
    ("brand impersonation 1:1", "03001234567",
     "HBL account verify karein: http://hbl-verify.tk/login"),
    ("direct IP link 1:1", "03001234567",
     "http://192.168.44.12/portal"),
]


def main():
    failed = []

    for label, title, body in GROUP_LEGIT:
        got = classify(title, body, is_group=True)
        if got is not None:
            failed.append(f"GROUP FALSE POSITIVE ({got[1]}): {label}\n"
                          f"  alert: {got[0][:80]}")

    for label, title, body, expected in GROUP_REAL_SCAMS:
        got = classify(title, body, is_group=True)
        if got is None:
            failed.append(f"GROUP MISSED SCAM: {label}")
        elif got[1] != expected:
            failed.append(f"GROUP wrong severity ({got[1]} != {expected}): {label}")

    for label, title, body in DIRECT_LEGIT_LINK:
        got = classify(title, body, is_group=False)
        if got is not None:
            failed.append(f"1:1 FALSE POSITIVE: {label}\n  alert: {got[0][:80]}")

    for label, title, body in DIRECT_SUSPICIOUS_LINK:
        got = classify(title, body, is_group=False)
        if got is None:
            failed.append(f"1:1 MISSED SUSPICIOUS LINK: {label}")
        elif got[1] != "suspicious":
            failed.append(f"1:1 wrong severity ({got[1]}): {label}")

    # Saved contact ki normal baat — koi alert nahi, 1:1 aur group dono me
    for label, title, body in [("saved contact emergency", "0300-1234567",
                                "Beta hospital aa jao, thore paise bhej do")]:
        got = classify(title, body, trusted_sender=True, is_group=False)
        if got is not None:
            failed.append(f"TRUSTED SENDER FALSE POSITIVE: {label}")

    total = len(GROUP_LEGIT) + len(GROUP_REAL_SCAMS) + len(DIRECT_LEGIT_LINK) \
        + len(DIRECT_SUSPICIOUS_LINK) + 1
    if failed:
        raise SystemExit("FAIL:\n" + "\n".join(failed))
    print(f"OK - {total} cases, group me link chup + text scam pakda, "
          "1:1 me link analysis chalti hai")


if __name__ == "__main__":
    main()
