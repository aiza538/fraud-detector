"""Premium plan — Google Play subscription, RevenueCat ke zariye.

Phone khareedari karta hai (Google Play), RevenueCat us ki receipt Google se
verify karta hai. Server kabhi phone ki baat par yaqeen nahi karta: wo khud
RevenueCat ki REST API se poochta hai ke is user ka "premium" entitlement kab
tak hai, aur jawab `users.premium_until` me rakhta hai.

Kab poocha jata hai:
  * Khareedne/restore ke foran baad (app `POST /v1/premium/refresh` bhejti hai).
  * Paying user ka record 24 ghante se purana ho to (renewal, cancel, refund).
  * Premium khatam hone ke baad ek dafa (shayad renew ho gaya ho).
Free user (premium_until NULL) par kabhi koi call nahi hoti.
"""
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import config

API_URL = "https://api.revenuecat.com/v1/subscribers/"
# Lifetime purchase (expires_date null) — "kabhi khatam nahi".
FOREVER = 4102444800  # 2100-01-01


class Unavailable(Exception):
    """RevenueCat tak pohanch nahi saki ya key set nahi."""


def is_configured():
    return bool(config.REVENUECAT_SECRET_API_KEY)


def _parse_time(value):
    if value is None:
        return FOREVER
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except (AttributeError, ValueError):
        return None


def fetch_expiry(user_id):
    """RevenueCat se entitlement ki expiry (epoch), ya None agar kabhi khareeda
    hi nahi. Network/key ki ghalti par Unavailable."""
    if not is_configured():
        raise Unavailable("REVENUECAT_SECRET_API_KEY is not set")
    request = urllib.request.Request(
        API_URL + urllib.parse.quote(user_id, safe=""),
        headers={"Authorization": "Bearer " + config.REVENUECAT_SECRET_API_KEY,
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as err:
        # User id ya key log me nahi — sirf ghalti ki qisam.
        logging.warning("revenuecat lookup failed: %s", type(err).__name__)
        raise Unavailable(str(type(err).__name__))
    entitlements = (data.get("subscriber") or {}).get("entitlements") or {}
    entitlement = entitlements.get(config.REVENUECAT_ENTITLEMENT)
    if not isinstance(entitlement, dict):
        return None
    return _parse_time(entitlement.get("expires_date"))


def refresh(session, user, now=None):
    """RevenueCat se taaza haal le kar user par likho. Ghalti par purana haal
    rehta hai (Unavailable upar jata hai)."""
    now = int(now or time.time())
    expiry = fetch_expiry(user.id)
    user.premium_until = expiry
    user.premium_checked_at = now
    session.commit()
    return is_active(user, now)


def is_active(user, now=None):
    now = int(now or time.time())
    return user.premium_until is not None and user.premium_until > now


def current(session, user, now=None):
    """Kya user abhi premium hai? Zarurat ho to RevenueCat se dobara check.

    RevenueCat down ho to jo database me hai wahi maana jata hai — paying user
    ko ek outage ki wajah se free limits par nahi girna chahiye.
    """
    now = int(now or time.time())
    if user.premium_until is None or not is_configured():
        return is_active(user, now)
    checked = user.premium_checked_at or 0
    if is_active(user, now):
        stale = now - checked >= config.PREMIUM_RECHECK_SECONDS
    else:
        # Khatam ho chuka: expiry ke baad ek dafa poocho (renew hua?), phir
        # roz ek dafa — taake har request par call na ho.
        stale = checked < user.premium_until or now - checked >= config.PREMIUM_RECHECK_SECONDS
    if stale:
        try:
            return refresh(session, user, now)
        except Unavailable:
            pass
    return is_active(user, now)
