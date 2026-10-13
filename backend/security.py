"""Tokens, hashing aur daily limits — /v1 API ki security ek jagah."""
import hashlib
import hmac
import re
import time
from functools import wraps

import jwt
from flask import g, request
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

import config
from db import UsageCounter, User, get_session


class ApiError(Exception):
    """Route se raise karein — client ko `{"error": code, "message": ...}` milta hai."""

    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _hmac(purpose, value):
    # `purpose` alag-alag cheezon ke hash ko aapas me match hone se rokta hai.
    return hmac.new(config.HASH_SALT.encode(), f"{purpose}|{value}".encode(),
                    hashlib.sha256).hexdigest()


def hash_ip(ip):
    return _hmac("ip", ip)[:32]


def hash_email(normalized_email):
    return _hmac("email", normalized_email)


def hash_code(user_id, code):
    return _hmac("code", f"{user_id}|{code}")


def consume_user_quota(user, kind):
    """User ki limit, aur jahan set ho wahan us ke network (IP) ki bhi."""
    consume_quota(user.id, kind, config.DAILY_LIMITS[kind])
    if kind in config.DAILY_LIMITS_PER_IP:
        consume_quota("ip:" + hash_ip(client_ip()), kind, config.DAILY_LIMITS_PER_IP[kind])


def client_ip():
    # ProxyFix (main.py) ke baad ye asli client IP hai, proxy ka nahi.
    return request.remote_addr or "unknown"


_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def normalize_email(raw):
    """Ek insaan = ek email. `a.b+x@gmail.com` aur `ab@gmail.com` same inbox hain,
    is liye dono ka ek hi roop banta hai. Invalid ho to None."""
    if not isinstance(raw, str):
        return None
    email = raw.strip().lower()
    if len(email) > 254 or not _EMAIL_RE.fullmatch(email):
        return None
    local, domain = email.rsplit("@", 1)
    local = local.split("+", 1)[0]
    if domain in ("gmail.com", "googlemail.com"):
        local, domain = local.replace(".", ""), "gmail.com"
    return f"{local}@{domain}" if local else None


ADMIN_EMAIL_HASHES = frozenset(
    hash_email(n) for n in map(normalize_email, config.ADMIN_EMAILS) if n)


def is_admin(user):
    return user.email_hash in ADMIN_EMAIL_HASHES


def issue_token(user):
    """(token, expires_at) — HS256 JWT. Har request par user database se dobara
    check hota hai, is liye block/token_version turant asar karte hain."""
    now = int(time.time())
    expires_at = now + config.TOKEN_TTL_SECONDS
    token = jwt.encode(
        {"sub": user.id, "ver": user.token_version, "iat": now, "exp": expires_at},
        config.JWT_SECRET, algorithm="HS256")
    return token, expires_at


def _authenticate():
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "unauthorized", "Token missing hai.")
    try:
        # algorithms pinned — "none" ya kisi aur algorithm ka token reject.
        claims = jwt.decode(token.strip(), config.JWT_SECRET, algorithms=["HS256"],
                            options={"require": ["sub", "ver", "exp"]})
    except jwt.PyJWTError:
        raise ApiError(401, "invalid_token", "Token invalid ya expire ho chuka hai.")
    user = get_session().get(User, claims["sub"])
    if user is None or user.blocked or user.token_version != claims["ver"]:
        raise ApiError(401, "invalid_token", "Token invalid ya expire ho chuka hai.")
    return user


def require_user(fn):
    """Route ko token ke peeche rakhta hai; user `g.user` me milta hai."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.user = _authenticate()
        return fn(*args, **kwargs)
    return wrapper


def consume_quota(subject, kind, limit):
    """`subject` ki aaj ki ginti me 1 jodo; limit par 429.

    Increment ek hi UPDATE me hota hai (`count < limit` shart ke saath), taake
    ek saath aayi requests limit se upar na nikal sakein.
    """
    day = time.strftime("%Y-%m-%d", time.gmtime())
    session = get_session()
    key = (UsageCounter.subject == subject, UsageCounter.day == day,
           UsageCounter.kind == kind)
    for _ in range(2):
        bumped = session.execute(
            update(UsageCounter).where(*key, UsageCounter.count < limit)
            .values(count=UsageCounter.count + 1)).rowcount
        session.commit()
        if bumped:
            return
        if session.get(UsageCounter, (subject, day, kind)) is not None:
            break  # row hai magar update nahi hui = limit poori
        try:
            # Naye din ki pehli entry: sab purane din ki rows hata do. Table
            # chhoti rehti hai, aur delete hue account ke IP/email hash ek din
            # se zyada nahi tikte.
            session.execute(delete(UsageCounter).where(UsageCounter.day < day))
            session.add(UsageCounter(subject=subject, day=day, kind=kind, count=1))
            session.commit()
            return
        except IntegrityError:
            session.rollback()  # doosri request ne row bana di — dobara UPDATE
    raise ApiError(429, "daily_limit",
                   "Aaj ki limit poori ho gayi hai. Kal dobara koshish karein.")
