"""Email code bhejne ka kaam — ek hi jagah, taake provider badalna aasan ho.

Abhi sirf development sender hai (code server log me chhapta hai). Resend/Brevo
ki keys milne par unka sender yahin add hoga; baqi code nahi badlega.
"""
import logging

import config


def is_configured():
    # Production me code log karna = har log dekhne wala kisi ka account
    # verify kar sakta hai. Jab tak asli provider nahi, feature band rahta hai.
    return not config.IS_PRODUCTION


def send_login_code(email, code):
    if not is_configured():
        raise RuntimeError("Email provider configured nahi hai.")
    logging.info("[dev] FraudGuard email code for %s: %s", email, code)
