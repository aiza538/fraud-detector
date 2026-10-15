"""Server settings — sab kuch environment variables se aata hai.

Production (Hugging Face Space ya `APP_ENV=production`) me secrets ZAROORI hain:
server unke baghair start hi nahi hota. Kamzor default ke saath chup chaap chalna
zyada khatarnak hai — tokens forge ho sakte hain aur data ephemeral disk par
likha jata hai.

Local development me kuch set karne ki zarurat nahi: SQLite file aur ek
per-process random token secret khud ban jata hai.
"""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Hugging Face har Space me SPACE_ID set karta hai — wahan APP_ENV bhool bhi
# jayein to production rules hi lagte hain.
IS_PRODUCTION = (
    os.environ.get("APP_ENV", "").strip().lower() == "production"
    or bool(os.environ.get("SPACE_ID"))
)


class ConfigError(RuntimeError):
    pass


def _secret(name, dev_default):
    value = os.environ.get(name, "").strip()
    if len(value) >= 32:
        return value
    if IS_PRODUCTION:
        raise ConfigError(
            f"{name} set nahi hai (ya 32 characters se chhota hai). Production me "
            f"ye secret zaroori hai — host (Render) ki Environment settings me add karein."
        )
    return value or dev_default


def _database_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        if IS_PRODUCTION:
            raise ConfigError(
                "DATABASE_URL set nahi hai. Production me Neon ka POOLED connection "
                "string zaroori hai — Space ki disk har restart par saaf ho jati hai."
            )
        return "sqlite:///" + os.path.join(BASE_DIR, "fraudguard-dev.db").replace("\\", "/")
    # Neon "postgresql://..." deta hai; SQLAlchemy ko driver ka naam bhi chahiye.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise ConfigError(f"{name} ek number hona chahiye.")


DATABASE_URL = _database_url()

# Token sign karne ki key. Dev me har process ka apna random secret — restart
# par purane dev tokens invalid ho jate hain, jo theek hai.
JWT_SECRET = _secret("JWT_SECRET", secrets.token_urlsafe(48))
TOKEN_TTL_SECONDS = 30 * 86400

# IP aur email ko hash karne ki key. Raw IP/email database me kabhi nahi jata.
HASH_SALT = _secret("FRAUDGUARD_SALT", "fraudguard-dev-salt")

# Server ke aage kitne reverse proxies hain (Hugging Face / Render = 1).
# 0 par X-Forwarded-For ignore hota hai — warna koi bhi header bhej kar apna IP
# badal sakta hai aur IP limits bekaar ho jati hain.
TRUSTED_PROXY_HOPS = _int("TRUSTED_PROXY_HOPS", 1 if IS_PRODUCTION else 0)

# Comma-separated emails. Verified user jis ka email is list me ho, admin hai.
ADMIN_EMAILS = [e for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]

# --- Community reports ------------------------------------------------------
# Kitne ALAG reporters ke number ko scam kehna hai. 1 bahut kam hai — ek
# galti se galti se number ban jata tha.
REPORT_THRESHOLD = 5
# Report ki age (din) — is se zyada purane reports count nahi hote.
REPORT_DECAY_DAYS = 180
# Email verify hone ke 48 ghante baad hi vote ginti me aata hai — warna koi 5
# accounts bana kar usi waqt kisi ka number block karwa deta.
REPORTER_MIN_VERIFIED_AGE_SECONDS = 48 * 3600

# --- Limits -----------------------------------------------------------------
# Ek IP se ek ghante me kitne naye anonymous accounts. Pakistani mobile networks
# me bohat se log ek hi public IP share karte hain, is liye ye zyada sakht nahi.
SIGNUPS_PER_IP_PER_HOUR = 30
# Har user ki rozana limit (UTC din). AI aur audio paise kharch karte hain.
DAILY_LIMITS = {
    "analyze_text": 60,
    "analyze_audio": 10,
    "report": 10,
    "email_code": 5,
}
# Ek network (IP) ki rozana limit — naye accounts bana kar per-user limit se
# bachne wale ko yahan rukna parta hai.
DAILY_LIMITS_PER_IP = {
    "analyze_text": 300,
    "analyze_audio": 40,
}

# --- Email codes ------------------------------------------------------------
EMAIL_CODE_TTL_SECONDS = 10 * 60
EMAIL_CODE_MAX_ATTEMPTS = 5
EMAIL_CODE_RESEND_SECONDS = 60
EMAIL_CODES_PER_IP_PER_HOUR = 10
# Ek email address par rozana kitne codes. Har code par 5 guesses milte hain —
# ye cap kisi aur ke email ka code guess karne (account takeover) ko rokta hai.
EMAIL_CODES_PER_EMAIL_PER_DAY = 5
# Throwaway inbox services — in par account verify nahi hota.
DISPOSABLE_EMAIL_DOMAINS = frozenset({
    "mailinator.com", "guerrillamail.com", "guerrillamail.net", "sharklasers.com",
    "10minutemail.com", "tempmail.com", "temp-mail.org", "yopmail.com",
    "trashmail.com", "getnada.com", "dispostable.com", "maildrop.cc",
    "throwawaymail.com", "fakeinbox.com", "mohmal.com", "emailondeck.com",
})
