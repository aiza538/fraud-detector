"""Email code bhejne ka kaam — Resend pehle, Brevo backup.

Provider ki keys set hon to asli email jati hai (local par bhi, testing ke
liye). Keys na hon to development me code server log me chhapta hai; production
me feature band rehta hai — code kabhi production log me nahi likha jata.

Koi naya package nahi: dono providers ka simple HTTP API standard library se.
"""
import json
import logging
import urllib.request
from email.utils import parseaddr

import config

TIMEOUT_SECONDS = 10


def _providers():
    if not config.MAIL_FROM:
        return []
    out = []
    if config.RESEND_API_KEY:
        out.append(("resend", _send_resend))
    if config.BREVO_API_KEY:
        out.append(("brevo", _send_brevo))
    return out


def is_configured():
    return bool(_providers()) or not config.IS_PRODUCTION


def _message(code):
    minutes = config.EMAIL_CODE_TTL_SECONDS // 60
    subject = f"FraudGuard AI code: {code}"
    text = (
        f"Aapka FraudGuard AI verification code: {code}\n\n"
        f"Ye code {minutes} minute tak valid hai.\n"
        "Ye code kisi ko na batayein — FraudGuard kabhi call ya message par ye code nahi maangta.\n\n"
        f"Your FraudGuard AI verification code is {code}. It is valid for {minutes} minutes. "
        "Do not share it with anyone.\n\n"
        "Agar aap ne ye code nahi manga, to is email ko ignore kar dein."
    )
    return subject, text


def _post(url, headers, payload):
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json", **headers})
    # urlopen 4xx/5xx par khud HTTPError raise karta hai.
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.status


def _send_resend(email, subject, text):
    _post("https://api.resend.com/emails",
          {"Authorization": f"Bearer {config.RESEND_API_KEY}"},
          {"from": config.MAIL_FROM, "to": [email], "subject": subject, "text": text})


def _send_brevo(email, subject, text):
    name, address = parseaddr(config.MAIL_FROM)
    _post("https://api.brevo.com/v3/smtp/email",
          {"api-key": config.BREVO_API_KEY},
          {"sender": {"name": name or "FraudGuard AI", "email": address},
           "to": [{"email": email}], "subject": subject, "textContent": text})


def send_login_code(email, code):
    providers = _providers()
    if not providers:
        if config.IS_PRODUCTION:
            raise RuntimeError("Email provider configured nahi hai.")
        logging.info("[dev] FraudGuard email code for %s: %s", email, code)
        return
    subject, text = _message(code)
    for name, send in providers:
        try:
            send(email, subject, text)
            return
        except Exception as err:  # agla provider try karo
            # Code aur poora email log me nahi — sirf provider aur wajah.
            logging.warning("email provider %s failed: %s", name, str(err)[:200])
    raise RuntimeError("Sab email providers fail ho gaye.")
