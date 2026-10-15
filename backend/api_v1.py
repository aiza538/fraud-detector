"""/v1 API — har route (sirf /auth/anonymous ke siwa) token mangta hai.

Purane bina-token routes (main.py) tab tak rehte hain jab tak mobile app /v1
par shift nahi hoti; uske baad wo delete honge.
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
import tempfile
import time
import uuid

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import delete, distinct, func, select, update
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

import audio_handler
import config
import fraud_detector
import mailer
import number_rules
import phone_rules
from db import EmailChallenge, NumberReport, UsageCounter, User, get_session
from security import (ApiError, client_ip, consume_quota, consume_user_quota, hash_code,
                      hash_email, hash_ip, is_admin, issue_token, normalize_email,
                      require_user)

v1 = Blueprint("v1", __name__, url_prefix="/v1")

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".opus", ".aac", ".amr",
                    ".3gp", ".mp4", ".webm", ".flac"}


@v1.errorhandler(ApiError)
def _api_error(err):
    return jsonify({"error": err.code, "message": err.message}), err.status


@v1.errorhandler(HTTPException)
def _http_error(err):
    # Flask ke apne errors (413 badi file, 400 kharab JSON) bhi JSON me jayein.
    return jsonify({"error": err.name.lower().replace(" ", "_"),
                    "message": err.description}), err.code


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _cacheable_json(payload, etag=None):
    """JSON jawab ETag ke saath. Phone agli baar `If-None-Match` bhejta hai;
    kuch na badla ho to sirf 304 jata hai, poori list dobara nahi."""
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    response = Response(body, mimetype="application/json")
    response.set_etag(etag or hashlib.sha256(body.encode("utf-8")).hexdigest()[:32])
    return response.make_conditional(request)


def _session_payload(user):
    token, expires_at = issue_token(user)
    return {"token": token, "expires_at": expires_at, "verified": user.is_verified}


def _delete_user(session, user):
    # SQLite foreign-key cascade default me band hota hai — is liye explicit.
    for table in (NumberReport, EmailChallenge):
        session.execute(delete(table).where(table.user_id == user.id))
    session.execute(delete(UsageCounter).where(UsageCounter.subject == user.id))
    session.delete(user)


# --- Accounts ---------------------------------------------------------------

@v1.post("/auth/anonymous")
def auth_anonymous():
    """App pehli baar khulne par yahan se apna token leti hai — koi login nahi."""
    session = get_session()
    now = int(time.time())
    ip_hash = hash_ip(client_ip())
    recent = session.scalar(
        select(func.count()).select_from(User)
        .where(User.signup_ip_hash == ip_hash, User.created_at > now - 3600))
    if recent >= config.SIGNUPS_PER_IP_PER_HOUR:
        raise ApiError(429, "too_many_signups",
                       "Too many new accounts from this network. Please try again later.")
    user = User(id=uuid.uuid4().hex, created_at=now, signup_ip_hash=ip_hash)
    session.add(user)
    session.commit()
    # Har naye account par ek line: network ka hash (raw IP kabhi nahi) aur
    # proxy header me kitne addresses aaye. Isi se pata chalta hai ke
    # TRUSTED_PROXY_HOPS host ke hisaab se sahi hai — ghalat ho to sab users ek
    # hi network lagte hain aur per-network limits sab par ek saath lagti hain.
    forwarded = (request.environ.get("werkzeug.proxy_fix.orig", {}).get("HTTP_X_FORWARDED_FOR")
                 or request.headers.get("X-Forwarded-For", ""))
    logging.info("signup network=%s forwarded_entries=%d", ip_hash[:8],
                 len([p for p in forwarded.split(",") if p.strip()]))
    return jsonify(_session_payload(user)), 201


@v1.post("/auth/refresh")
@require_user
def auth_refresh():
    return jsonify(_session_payload(g.user))


@v1.get("/account")
@require_user
def account():
    return jsonify({"verified": g.user.is_verified, "admin": is_admin(g.user),
                    "created_at": g.user.created_at})


@v1.delete("/account")
@require_user
def delete_account():
    session = get_session()
    _delete_user(session, g.user)
    session.commit()
    return "", 204


@v1.post("/auth/email/start")
@require_user
def email_start():
    email = _body().get("email")
    normalized = normalize_email(email)
    if not normalized:
        raise ApiError(400, "invalid_email", "Please enter a valid email address.")
    if normalized.rsplit("@", 1)[1] in config.DISPOSABLE_EMAIL_DOMAINS:
        raise ApiError(400, "disposable_email", "Temporary email addresses are not allowed.")
    if not mailer.is_configured():
        raise ApiError(503, "email_unavailable", "Email verification is not available right now.")

    session = get_session()
    user = g.user
    now = int(time.time())
    ip_hash = hash_ip(client_ip())

    current = session.get(EmailChallenge, user.id)
    if current and now - current.created_at < config.EMAIL_CODE_RESEND_SECONDS:
        raise ApiError(429, "resend_too_soon", "Please wait a moment before asking for a new code.")
    from_ip = session.scalar(
        select(func.count()).select_from(EmailChallenge)
        .where(EmailChallenge.ip_hash == ip_hash, EmailChallenge.created_at > now - 3600))
    if from_ip >= config.EMAIL_CODES_PER_IP_PER_HOUR:
        raise ApiError(429, "too_many_codes", "Too many codes requested from this network. Please try again later.")
    email_hash = hash_email(normalized)
    consume_user_quota(user, "email_code")
    consume_quota("email:" + email_hash[:32], "email_code",
                  config.EMAIL_CODES_PER_EMAIL_PER_DAY)

    code = f"{secrets.randbelow(10 ** 6):06d}"
    if current:
        session.delete(current)
        session.flush()
    session.add(EmailChallenge(
        user_id=user.id, email_hash=email_hash,
        code_hash=hash_code(user.id, code), ip_hash=ip_hash, created_at=now,
        expires_at=now + config.EMAIL_CODE_TTL_SECONDS, attempts=0))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()  # isi user ki doosri request ne abhi code bana liya
        raise ApiError(429, "resend_too_soon", "Please wait a moment before asking for a new code.")
    try:
        # Bheja usi address par jata hai jo user ne likha — normalized roop sirf
        # "ek insaan = ek account" ke liye hai.
        mailer.send_login_code(email.strip(), code)
    except Exception:
        session.execute(delete(EmailChallenge).where(EmailChallenge.user_id == user.id))
        session.commit()
        raise ApiError(502, "email_failed", "The code could not be sent. Please try again.")
    # Jawab hamesha ek jaisa — ye nahi batata ke email pehle se registered hai ya nahi.
    return jsonify({"status": "sent", "expires_in": config.EMAIL_CODE_TTL_SECONDS})


@v1.post("/auth/email/verify")
@require_user
def email_verify():
    code = _body().get("code")
    if not isinstance(code, str) or not code.strip():
        raise ApiError(400, "invalid_code", "Please enter the code.")
    session = get_session()
    user = g.user
    now = int(time.time())

    # Attempt pehle gino (ek hi UPDATE me), phir code dekho — warna ek saath
    # bheji gayi requests 5 se zyada guesses kar leti.
    counted = session.execute(
        update(EmailChallenge)
        .where(EmailChallenge.user_id == user.id, EmailChallenge.expires_at > now,
               EmailChallenge.attempts < config.EMAIL_CODE_MAX_ATTEMPTS)
        .values(attempts=EmailChallenge.attempts + 1)).rowcount
    session.commit()
    if not counted:
        raise ApiError(400, "code_expired", "This code has expired or had too many wrong attempts. Please ask for a new code.")
    challenge = session.get(EmailChallenge, user.id)
    if challenge is None or not hmac.compare_digest(
            challenge.code_hash, hash_code(user.id, code.strip())):
        raise ApiError(400, "wrong_code", "That code is not correct.")

    owner = session.scalar(select(User).where(User.email_hash == challenge.email_hash))
    session.delete(challenge)
    if owner is not None and owner.id != user.id:
        # Ye email pehle se kisi account ka hai (naya phone / reinstall) — user
        # ko wahi purana account wapas milta hai. Sirf KHALI anonymous account
        # hatta hai; verified account (jis ke apne reports hain) kabhi nahi.
        if owner.blocked or user.is_verified:
            session.commit()
            raise ApiError(409, "email_in_use", "This email is already used by another account.")
        _delete_user(session, user)
        user = owner
    else:
        user.email_hash = challenge.email_hash
        user.verified_at = now
    try:
        session.commit()
    except IntegrityError:
        session.rollback()  # do devices ne ek hi email ek saath verify kiya
        raise ApiError(409, "try_again", "Please try again.")
    return jsonify(_session_payload(user))


# --- Analysis ---------------------------------------------------------------

@v1.post("/analyze/text")
@require_user
def analyze_text():
    data = _body()
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "invalid_text", "No text provided")
    channel = data.get("channel") if isinstance(data.get("channel"), str) else None
    consume_user_quota(g.user, "analyze_text")
    return jsonify(fraud_detector.analyze_text(text, channel=channel))


@v1.post("/analyze/audio")
@require_user
def analyze_audio():
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ApiError(400, "invalid_file", "No audio file provided")
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in AUDIO_EXTENSIONS:
        raise ApiError(400, "invalid_file", "This audio format is not supported.")
    consume_user_quota(g.user, "analyze_audio")

    # Client ka filename disk par kabhi use nahi hota: do users ki "audio.mp3"
    # ek doosre ko overwrite/delete kar deti thi.
    fd, path = tempfile.mkstemp(suffix=extension, prefix="fraudguard-")
    os.close(fd)
    try:
        file.save(path)
        return jsonify(audio_handler.analyze_audio(path))
    finally:
        if os.path.exists(path):
            os.remove(path)


# --- Numbers ----------------------------------------------------------------

def _report_counts(session, numbers=None):
    """number -> kitne ALAG networks (IP hash) se qabil-e-shumar reports.

    Report tab ginti hai jab: reporter ka email kam se kam 48 ghante pehle
    verify hua ho, wo block na ho, aur report 180 din se purani na ho.
    Alag users ki ginti unique constraint se aati hai; alag IPs ki ginti ek
    hi jagah se bane 5 accounts ko rokti hai.
    """
    now = int(time.time())
    query = (
        select(NumberReport.number, func.count(distinct(NumberReport.ip_hash)))
        .join(User, User.id == NumberReport.user_id)
        .where(NumberReport.created_at >= now - config.REPORT_DECAY_DAYS * 86400,
               User.blocked.is_(False), User.email_hash.is_not(None),
               User.verified_at <= now - config.REPORTER_MIN_VERIFIED_AGE_SECONDS)
        .group_by(NumberReport.number))
    if numbers is not None:
        query = query.where(NumberReport.number.in_(numbers))
    return dict(session.execute(query).all())


def _confirmed_numbers(session):
    community = {n for n, count in _report_counts(session).items()
                 if count >= config.REPORT_THRESHOLD}
    return community | number_rules.VERIFIED_NUMBERS


@v1.post("/check-number")
@require_user
def check_number():
    data = _body()
    number = data.get("number")
    if not isinstance(number, str):
        number = ""
    session = get_session()

    def scam_info(keys):
        if any(k in number_rules.VERIFIED_NUMBERS for k in keys):
            return {"source": "verified", "report_count": 0}
        count = max(_report_counts(session, keys).values(), default=0)
        if count >= config.REPORT_THRESHOLD:
            return {"source": "community", "report_count": count}
        return None

    return jsonify(number_rules.screen_number(
        number, data.get("saved_contact") is True, scam_info))


@v1.get("/number-lists")
@require_user
def number_lists():
    """Phone ke offline call-monitor ke rules. Sirf confirmed scam numbers —
    threshold se neeche wale (pending) numbers kisi ko nahi bheje jate."""
    return _cacheable_json({
        "legitimate": list(number_rules.ALL_LEGITIMATE),
        "directory": number_rules.ALL_LEGITIMATE,
        "scam": sorted(_confirmed_numbers(get_session())),
        "spoofable": number_rules.SPOOFABLE,
        "threshold": config.REPORT_THRESHOLD,
    })


@v1.get("/rules")
@require_user
def rules():
    """Phone ke background message scanner ke rules (data/phone_rules.json)."""
    return _cacheable_json(phone_rules.PAYLOAD, etag=phone_rules.VERSION)


@v1.post("/report-number")
@require_user
def report_number():
    user = g.user
    if not user.is_verified:
        raise ApiError(403, "email_verification_required",
                       "Please verify your email before reporting a number.")
    data = _body()
    number = data.get("number")
    cleaned = number_rules.clean_number(number) if isinstance(number, str) else ""
    if not number_rules._plausible_caller_number(cleaned):
        raise ApiError(400, "invalid_number", "Invalid number")
    entity = number_rules.official_entity(cleaned)
    if entity:
        raise ApiError(400, "official_number",
                       f"{entity} is a verified official number and cannot be reported.")

    session = get_session()
    already = session.scalar(select(NumberReport.id).where(
        NumberReport.number == cleaned, NumberReport.user_id == user.id))
    if already is None:
        consume_user_quota(user, "report")
        note = data.get("note") if isinstance(data.get("note"), str) else ""
        session.add(NumberReport(number=cleaned, user_id=user.id,
                                 ip_hash=hash_ip(client_ip()), note=note[:280],
                                 created_at=int(time.time())))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()  # isi user ki doosri request pehle pohanch gayi

    count = _report_counts(session, [cleaned]).get(cleaned, 0)
    if count >= config.REPORT_THRESHOLD:
        return jsonify({"status": "confirmed", "report_count": count,
                        "message": "This number is now confirmed as a scam."})
    return jsonify({
        "status": "pending", "report_count": count,
        "reports_needed": config.REPORT_THRESHOLD,
        "message": (f"Report recorded. The number is blocked for everyone once "
                    f"{config.REPORT_THRESHOLD} different users have reported it."),
    })


@v1.post("/admin/unreport-number")
@require_user
def admin_unreport_number():
    """Appeal path: sirf admin kisi number ke community reports hata sakta hai."""
    if not is_admin(g.user):
        raise ApiError(403, "admin_only", "Only an admin can do this.")
    number = _body().get("number")
    cleaned = number_rules.clean_number(number) if isinstance(number, str) else ""
    if not number_rules._plausible_caller_number(cleaned):
        raise ApiError(400, "invalid_number", "Invalid number")
    session = get_session()
    removed = session.execute(delete(NumberReport).where(
        NumberReport.number.in_(number_rules.lookup_keys(cleaned)))).rowcount
    session.commit()
    if not removed:
        raise ApiError(404, "not_found", "There were no reports for this number.")
    return jsonify({"status": "unreported", "removed_reports": removed})
