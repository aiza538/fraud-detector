# /v1 API ke tests — chalane ke liye (backend/ directory se):
#   python -m unittest tests.test_api_v1
#
# Har test apni temporary SQLite file par chalta hai; developer ki
# fraudguard-dev.db ko haath nahi lagta. Gemini/AssemblyAI kabhi call nahi hote.
import io
import os
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("GEMINI_API_KEY", "test-unit-evaluation-key")

import jwt
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

import config
import db
import mailer
import security
from main import app

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAY = 86400


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db", prefix="fraudguard-test-")
        os.close(fd)
        db.init_engine("sqlite:///" + self.db_path.replace("\\", "/"))
        db.Base.metadata.create_all(db.engine)
        self.client = app.test_client()
        self.sent = []  # (email, code) jo "bheje" gaye
        patcher = mock.patch.object(
            mailer, "send_login_code", side_effect=lambda e, c: self.sent.append((e, c)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        db.engine.dispose()
        os.remove(self.db_path)

    # -- helpers --
    def signup(self, ip="10.0.0.1"):
        r = self.client.post("/v1/auth/anonymous", environ_base={"REMOTE_ADDR": ip})
        self.assertEqual(r.status_code, 201, r.get_json())
        return {"Authorization": "Bearer " + r.get_json()["token"]}

    def call(self, method, path, headers=None, ip="10.0.0.1", **kwargs):
        return self.client.open(path, method=method, headers=headers,
                                environ_base={"REMOTE_ADDR": ip}, **kwargs)

    def user_id(self, headers):
        token = headers["Authorization"].split(" ", 1)[1]
        return jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])["sub"]

    def edit_user(self, headers, **fields):
        with db.SessionLocal() as s:
            user = s.get(db.User, self.user_id(headers))
            for name, value in fields.items():
                setattr(user, name, value)
            s.commit()

    def verify_email(self, headers, email, ip="10.0.0.1"):
        r = self.call("POST", "/v1/auth/email/start", headers, ip, json={"email": email})
        self.assertEqual(r.status_code, 200, r.get_json())
        r = self.call("POST", "/v1/auth/email/verify", headers, ip,
                      json={"code": self.sent[-1][1]})
        self.assertEqual(r.status_code, 200, r.get_json())
        return {"Authorization": "Bearer " + r.get_json()["token"]}

    def reporter(self, n, age_days=3):
        """Verified reporter apne alag IP se, email `age_days` pehle verify hua."""
        ip = f"10.1.0.{n}"
        headers = self.verify_email(self.signup(ip), f"reporter{n}@example.com", ip)
        self.edit_user(headers, verified_at=int(time.time()) - age_days * DAY)
        return headers, ip


class AuthTests(ApiTestCase):
    PROTECTED = [
        ("POST", "/v1/auth/refresh"), ("GET", "/v1/account"), ("DELETE", "/v1/account"),
        ("POST", "/v1/auth/email/start"), ("POST", "/v1/auth/email/verify"),
        ("POST", "/v1/analyze/text"), ("POST", "/v1/analyze/audio"),
        ("POST", "/v1/check-number"), ("GET", "/v1/number-lists"), ("GET", "/v1/rules"),
        ("POST", "/v1/report-number"), ("POST", "/v1/admin/unreport-number"),
    ]

    def test_every_route_needs_a_token(self):
        for method, path in self.PROTECTED:
            r = self.call(method, path)
            self.assertEqual(r.status_code, 401, f"{method} {path} is open")
            self.assertEqual(r.get_json()["error"], "unauthorized")

    def test_anonymous_token_works_and_refreshes(self):
        headers = self.signup()
        r = self.call("GET", "/v1/account", headers)
        self.assertEqual(r.get_json()["verified"], False)
        r = self.call("POST", "/v1/auth/refresh", headers)
        self.assertEqual(r.status_code, 200)
        fresh = {"Authorization": "Bearer " + r.get_json()["token"]}
        self.assertEqual(self.user_id(fresh), self.user_id(headers))

    def test_forged_and_expired_tokens_are_rejected(self):
        uid = self.user_id(self.signup())
        now = int(time.time())
        claims = {"sub": uid, "ver": 0, "iat": now, "exp": now + 600}
        bad_tokens = {
            "wrong secret": jwt.encode(claims, "x" * 48, algorithm="HS256"),
            "expired": jwt.encode({**claims, "exp": now - 10}, config.JWT_SECRET, algorithm="HS256"),
            "no expiry": jwt.encode({"sub": uid, "ver": 0}, config.JWT_SECRET, algorithm="HS256"),
            "alg none": jwt.encode(claims, None, algorithm="none"),
            "other algorithm": jwt.encode(claims, config.JWT_SECRET, algorithm="HS512"),
            "unknown user": jwt.encode({**claims, "sub": "f" * 32}, config.JWT_SECRET, algorithm="HS256"),
            "garbage": "not-a-token",
        }
        for label, token in bad_tokens.items():
            r = self.call("GET", "/v1/account", {"Authorization": "Bearer " + token})
            self.assertEqual(r.status_code, 401, label)

    def test_blocked_user_and_revoked_token(self):
        blocked = self.signup()
        self.edit_user(blocked, blocked=True)
        self.assertEqual(self.call("GET", "/v1/account", blocked).status_code, 401)

        revoked = self.signup()
        self.edit_user(revoked, token_version=1)
        self.assertEqual(self.call("GET", "/v1/account", revoked).status_code, 401)

    def test_signup_limit_per_ip_cannot_be_dodged_with_a_header(self):
        with mock.patch.object(config, "SIGNUPS_PER_IP_PER_HOUR", 3):
            for _ in range(3):
                self.signup("10.9.9.9")
            # X-Forwarded-For par bharosa nahi (TRUSTED_PROXY_HOPS=0 in dev/tests)
            r = self.client.post("/v1/auth/anonymous",
                                 environ_base={"REMOTE_ADDR": "10.9.9.9"},
                                 headers={"X-Forwarded-For": "1.2.3.4"})
            self.assertEqual(r.status_code, 429)
            self.signup("10.9.9.10")  # doosra IP theek chalta hai

    def test_delete_account_removes_everything(self):
        headers, ip = self.reporter(1)
        self.call("POST", "/v1/report-number", headers, ip, json={"number": "03099988877"})
        self.assertEqual(self.call("DELETE", "/v1/account", headers).status_code, 204)
        self.assertEqual(self.call("GET", "/v1/account", headers).status_code, 401)
        with db.SessionLocal() as s:
            for table in (db.User, db.NumberReport, db.EmailChallenge):
                self.assertEqual(s.query(table).count(), 0, table.__tablename__)
            # user ki apni ginti gayi; network/email ki ginti (hash) aglay din saaf hoti hai
            left = {row.subject.split(":")[0] for row in s.query(db.UsageCounter)}
            self.assertLessEqual(left, {"ip", "email"})


class EmailCodeTests(ApiTestCase):
    def test_verify_then_same_email_restores_the_account(self):
        first = self.signup()
        verified = self.verify_email(first, "Some.One+promo@Gmail.com")
        self.assertTrue(self.call("GET", "/v1/account", verified).get_json()["verified"])
        self.assertEqual(self.sent[-1][0], "Some.One+promo@Gmail.com")

        # Naya phone: dots/plus ke baghair wahi inbox -> wahi purana account
        second = self.signup("10.0.0.2")
        restored = self.verify_email(second, "someone@googlemail.com", "10.0.0.2")
        self.assertEqual(self.user_id(restored), self.user_id(first))
        # khali anonymous account hat gaya
        self.assertEqual(self.call("GET", "/v1/account", second).status_code, 401)

    def test_verified_account_is_never_merged_away(self):
        a = self.verify_email(self.signup(), "a@example.com")
        b = self.verify_email(self.signup("10.0.0.2"), "b@example.com", "10.0.0.2")
        with mock.patch.object(config, "EMAIL_CODE_RESEND_SECONDS", 0):
            self.call("POST", "/v1/auth/email/start", b, "10.0.0.2", json={"email": "a@example.com"})
        r = self.call("POST", "/v1/auth/email/verify", b, "10.0.0.2", json={"code": self.sent[-1][1]})
        self.assertEqual(r.status_code, 409)
        self.assertTrue(self.call("GET", "/v1/account", a).get_json()["verified"])
        self.assertTrue(self.call("GET", "/v1/account", b).get_json()["verified"])

    def test_wrong_code_locks_after_max_attempts(self):
        headers = self.signup()
        self.call("POST", "/v1/auth/email/start", headers, json={"email": "u@example.com"})
        code = self.sent[-1][1]
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(config.EMAIL_CODE_MAX_ATTEMPTS):
            r = self.call("POST", "/v1/auth/email/verify", headers, json={"code": wrong})
            self.assertEqual(r.get_json()["error"], "wrong_code")
        # ab sahi code bhi kaam nahi karta
        r = self.call("POST", "/v1/auth/email/verify", headers, json={"code": code})
        self.assertEqual(r.get_json()["error"], "code_expired")
        self.assertFalse(self.call("GET", "/v1/account", headers).get_json()["verified"])

    def test_expired_code_is_rejected(self):
        headers = self.signup()
        self.call("POST", "/v1/auth/email/start", headers, json={"email": "u@example.com"})
        with db.SessionLocal() as s:
            s.get(db.EmailChallenge, self.user_id(headers)).expires_at = int(time.time()) - 1
            s.commit()
        r = self.call("POST", "/v1/auth/email/verify", headers, json={"code": self.sent[-1][1]})
        self.assertEqual(r.get_json()["error"], "code_expired")

    def test_code_belongs_to_one_user_only(self):
        a, b = self.signup(), self.signup("10.0.0.2")
        self.call("POST", "/v1/auth/email/start", a, json={"email": "a@example.com"})
        self.call("POST", "/v1/auth/email/start", b, "10.0.0.2", json={"email": "b@example.com"})
        r = self.call("POST", "/v1/auth/email/verify", b, "10.0.0.2", json={"code": self.sent[0][1]})
        if self.sent[0][1] != self.sent[1][1]:
            self.assertEqual(r.get_json()["error"], "wrong_code")

    def test_send_limits(self):
        headers = self.signup()
        self.assertEqual(self.call("POST", "/v1/auth/email/start", headers,
                                   json={"email": "u@example.com"}).status_code, 200)
        # 60 second cooldown
        r = self.call("POST", "/v1/auth/email/start", headers, json={"email": "u@example.com"})
        self.assertEqual(r.get_json()["error"], "resend_too_soon")

        with mock.patch.object(config, "EMAIL_CODE_RESEND_SECONDS", 0):
            # per-user daily limit
            with mock.patch.dict(config.DAILY_LIMITS, {"email_code": 2}):
                self.call("POST", "/v1/auth/email/start", headers, json={"email": "u@example.com"})
                r = self.call("POST", "/v1/auth/email/start", headers, json={"email": "u@example.com"})
                self.assertEqual(r.get_json()["error"], "daily_limit")
            # per-IP hourly limit, alag accounts se bhi
            with mock.patch.object(config, "EMAIL_CODES_PER_IP_PER_HOUR", 2):
                other = self.signup()
                self.call("POST", "/v1/auth/email/start", other, json={"email": "o@example.com"})
                third = self.signup()
                r = self.call("POST", "/v1/auth/email/start", third, json={"email": "t@example.com"})
                self.assertEqual(r.get_json()["error"], "too_many_codes")
        self.assertEqual(len(self.sent), 3)

    def test_one_email_address_gets_a_limited_number_of_codes_per_day(self):
        # Alag accounts aur alag IPs se bhi — warna kisi aur ke email ka code
        # guess karne ke liye naye accounts banate jao.
        with mock.patch.object(config, "EMAIL_CODES_PER_EMAIL_PER_DAY", 2):
            for n in (1, 2):
                r = self.call("POST", "/v1/auth/email/start", self.signup(f"10.3.0.{n}"),
                              f"10.3.0.{n}", json={"email": "victim@example.com"})
                self.assertEqual(r.status_code, 200)
            r = self.call("POST", "/v1/auth/email/start", self.signup("10.3.0.3"),
                          "10.3.0.3", json={"email": "Victim+x@example.com"})
            self.assertEqual((r.status_code, r.get_json()["error"]), (429, "daily_limit"))
        self.assertEqual(len(self.sent), 2)

    def test_bad_emails_are_refused(self):
        headers = self.signup()
        for email, error in [("not-an-email", "invalid_email"), ("", "invalid_email"),
                             (None, "invalid_email"), (["a@b.com"], "invalid_email"),
                             ("x@mailinator.com", "disposable_email")]:
            r = self.call("POST", "/v1/auth/email/start", headers, json={"email": email})
            self.assertEqual(r.get_json()["error"], error, email)
        self.assertEqual(self.sent, [])

    def test_production_without_provider_is_unavailable_and_never_logs_codes(self):
        headers = self.signup()
        with mock.patch.object(config, "IS_PRODUCTION", True):
            r = self.call("POST", "/v1/auth/email/start", headers, json={"email": "u@example.com"})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(self.sent, [])


class NumberTests(ApiTestCase):
    def test_check_number_matches_the_four_levels(self):
        headers = self.signup()
        cases = [
            ({"number": "021-111-111-425"}, "safe"),
            ({"number": "1717"}, "safe"),
            ({"number": "111-111-427"}, "scam"),          # HBL ka spoof
            ({"number": "111-999-999"}, "suspicious"),
            ({"number": "0300-1234567"}, "unknown"),
            ({"number": "03001234567", "saved_contact": True}, "safe"),
            ({"number": "abc"}, "unknown"),
            ({"number": 12345}, "unknown"),               # galat type crash nahi karta
            ({}, "unknown"),
        ]
        for payload, expected in cases:
            r = self.call("POST", "/v1/check-number", headers, json=payload)
            self.assertEqual(r.get_json()["status"], expected, payload)

    def test_anonymous_user_cannot_report(self):
        r = self.call("POST", "/v1/report-number", self.signup(), json={"number": "03099988877"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()["error"], "email_verification_required")

    def test_official_and_invalid_numbers_cannot_be_reported(self):
        headers, ip = self.reporter(1)
        r = self.call("POST", "/v1/report-number", headers, ip, json={"number": "111-111-425"})
        self.assertEqual(r.get_json()["error"], "official_number")
        for bad in ["abc", "", None, 5, "12"]:
            r = self.call("POST", "/v1/report-number", headers, ip, json={"number": bad})
            self.assertEqual(r.get_json()["error"], "invalid_number", bad)

    def test_consensus_needs_five_distinct_verified_reporters(self):
        number = "03099988877"
        viewer = self.signup()
        for n in range(1, config.REPORT_THRESHOLD):
            headers, ip = self.reporter(n)
            r = self.call("POST", "/v1/report-number", headers, ip, json={"number": number})
            self.assertEqual(r.get_json()["status"], "pending")
            # dobara report = koi naya vote nahi
            r = self.call("POST", "/v1/report-number", headers, ip, json={"number": number})
            self.assertEqual(r.get_json()["report_count"], n)

        lists = self.call("GET", "/v1/number-lists", viewer).get_json()
        self.assertNotIn("3099988877", lists["scam"])
        self.assertNotIn("pending", lists)  # pending numbers kisi ko nahi jate
        r = self.call("POST", "/v1/check-number", viewer, json={"number": number})
        self.assertEqual(r.get_json()["status"], "unknown")

        headers, ip = self.reporter(config.REPORT_THRESHOLD)
        r = self.call("POST", "/v1/report-number", headers, ip, json={"number": number})
        self.assertEqual(r.get_json()["status"], "confirmed")
        self.assertIn("3099988877", self.call("GET", "/v1/number-lists", viewer).get_json()["scam"])
        r = self.call("POST", "/v1/check-number", viewer, json={"number": "+92 309 9988877", "saved_contact": True})
        self.assertEqual((r.get_json()["status"], r.get_json()["source"], r.get_json()["report_count"]),
                         ("scam", "community", config.REPORT_THRESHOLD))

    def _reports_confirm(self, number, **reporter_kwargs):
        for n in range(1, config.REPORT_THRESHOLD + 1):
            headers, ip = self.reporter(n, **reporter_kwargs)
            last = self.call("POST", "/v1/report-number", headers, ip, json={"number": number})
        return last.get_json()

    def test_reports_do_not_count_until_48_hours_after_verifying(self):
        body = self._reports_confirm("03099988877", age_days=1)
        self.assertEqual((body["status"], body["report_count"]), ("pending", 0))

    def test_reports_from_one_network_count_once(self):
        number = "03099988877"
        for n in range(1, config.REPORT_THRESHOLD + 1):
            headers, _ = self.reporter(n)
            last = self.call("POST", "/v1/report-number", headers, "10.5.5.5", json={"number": number})
        self.assertEqual((last.get_json()["status"], last.get_json()["report_count"]), ("pending", 1))

    def test_old_reports_and_blocked_reporters_do_not_count(self):
        number = "03099988877"
        self.assertEqual(self._reports_confirm(number)["status"], "confirmed")
        viewer = self.signup()
        with db.SessionLocal() as s:
            blocked = s.query(db.NumberReport).first().user_id
            s.get(db.User, blocked).blocked = True
            s.commit()
        self.assertNotIn("3099988877", self.call("GET", "/v1/number-lists", viewer).get_json()["scam"])
        with db.SessionLocal() as s:
            s.get(db.User, blocked).blocked = False
            s.query(db.NumberReport).update(
                {"created_at": int(time.time()) - (config.REPORT_DECAY_DAYS + 1) * DAY})
            s.commit()
        self.assertNotIn("3099988877", self.call("GET", "/v1/number-lists", viewer).get_json()["scam"])

    def test_daily_report_limit(self):
        headers, ip = self.reporter(1)
        with mock.patch.dict(config.DAILY_LIMITS, {"report": 2}):
            for number in ["03011111111", "03022222222"]:
                self.assertEqual(self.call("POST", "/v1/report-number", headers, ip,
                                           json={"number": number}).status_code, 200)
            r = self.call("POST", "/v1/report-number", headers, ip, json={"number": "03033333333"})
            self.assertEqual((r.status_code, r.get_json()["error"]), (429, "daily_limit"))

    def test_only_admin_can_unreport(self):
        number = "03099988877"
        self.assertEqual(self._reports_confirm(number)["status"], "confirmed")
        normal, ip = self.reporter(50)
        r = self.call("POST", "/v1/admin/unreport-number", normal, ip, json={"number": number})
        self.assertEqual(r.status_code, 403)

        admin = self.verify_email(self.signup("10.7.7.7"), "boss@example.com", "10.7.7.7")
        admins = frozenset({security.hash_email("boss@example.com")})
        with mock.patch.object(security, "ADMIN_EMAIL_HASHES", admins):
            self.assertTrue(self.call("GET", "/v1/account", admin).get_json()["admin"])
            r = self.call("POST", "/v1/admin/unreport-number", admin, json={"number": number})
            self.assertEqual((r.status_code, r.get_json()["removed_reports"]),
                             (200, config.REPORT_THRESHOLD))
            r = self.call("POST", "/v1/admin/unreport-number", admin, json={"number": number})
            self.assertEqual(r.status_code, 404)
        self.assertNotIn("3099988877", self.call("GET", "/v1/number-lists", admin).get_json()["scam"])


class SyncTests(ApiTestCase):
    """Phone ka sync: rules aur number lists, sirf tab download jab kuch badla ho."""

    def test_rules_are_served_with_a_version(self):
        headers = self.signup()
        r = self.call("GET", "/v1/rules", headers)
        body = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(body["schema"], 1)
        self.assertEqual(len(body["rules"]), 6)
        self.assertEqual(r.headers["ETag"], f'"{body["version"]}"')
        self.assertFalse([k for k in body if k.startswith("_")], "documentation keys phone ko nahi jate")

    def test_unchanged_rules_and_lists_return_304(self):
        headers = self.signup()
        for path in ("/v1/rules", "/v1/number-lists"):
            first = self.call("GET", path, headers)
            again = self.call("GET", path, {**headers, "If-None-Match": first.headers["ETag"]})
            self.assertEqual((again.status_code, again.data), (304, b""), path)
            stale = self.call("GET", path, {**headers, "If-None-Match": '"old-version"'})
            self.assertEqual(stale.status_code, 200, path)
        # 304 token ke baghair nahi milta
        self.assertEqual(self.call("GET", "/v1/rules", {"If-None-Match": first.headers["ETag"]}).status_code, 401)

    def test_number_list_version_changes_when_a_number_is_confirmed(self):
        viewer = self.signup()
        before = self.call("GET", "/v1/number-lists", viewer).headers["ETag"]
        for n in range(1, config.REPORT_THRESHOLD + 1):
            headers, ip = self.reporter(n)
            self.call("POST", "/v1/report-number", headers, ip, json={"number": "03099988877"})
        after = self.call("GET", "/v1/number-lists", {**viewer, "If-None-Match": before})
        self.assertEqual(after.status_code, 200)
        self.assertIn("3099988877", after.get_json()["scam"])


class AnalyzeTests(ApiTestCase):
    def test_text_goes_to_the_detector_and_respects_the_daily_limit(self):
        headers = self.signup()
        with mock.patch("fraud_detector.analyze_text", return_value={"fraud": False}) as detector, \
                mock.patch.dict(config.DAILY_LIMITS, {"analyze_text": 2}):
            r = self.call("POST", "/v1/analyze/text", headers, json={"text": "hello", "channel": "whatsapp"})
            self.assertEqual(r.get_json(), {"fraud": False})
            detector.assert_called_once_with("hello", channel="whatsapp")
            self.call("POST", "/v1/analyze/text", headers, json={"text": "again"})
            r = self.call("POST", "/v1/analyze/text", headers, json={"text": "third"})
            self.assertEqual((r.status_code, r.get_json()["error"]), (429, "daily_limit"))
            self.assertEqual(detector.call_count, 2)
            # limit har user ki apni hai
            other = self.signup("10.0.0.2")
            self.assertEqual(self.call("POST", "/v1/analyze/text", other, "10.0.0.2",
                                       json={"text": "x"}).status_code, 200)

    def test_new_accounts_cannot_dodge_the_network_limit(self):
        with mock.patch("fraud_detector.analyze_text", return_value={"fraud": False}) as detector, \
                mock.patch.dict(config.DAILY_LIMITS_PER_IP, {"analyze_text": 3}):
            for _ in range(3):
                r = self.call("POST", "/v1/analyze/text", self.signup(), json={"text": "x"})
                self.assertEqual(r.status_code, 200)
            # chautha naya account, wahi network
            r = self.call("POST", "/v1/analyze/text", self.signup(), json={"text": "x"})
            self.assertEqual((r.status_code, r.get_json()["error"]), (429, "daily_limit"))
            self.assertEqual(detector.call_count, 3)

    def test_yesterdays_counters_are_cleaned_up(self):
        headers = self.signup()
        uid = self.user_id(headers)
        with db.SessionLocal() as s:
            s.add(db.UsageCounter(subject=uid, day="2000-01-01", kind="analyze_text", count=60))
            s.commit()
        with mock.patch("fraud_detector.analyze_text", return_value={"fraud": False}):
            self.assertEqual(self.call("POST", "/v1/analyze/text", headers,
                                       json={"text": "x"}).status_code, 200)
        with db.SessionLocal() as s:
            days = {row.day for row in s.query(db.UsageCounter).filter_by(subject=uid)}
        self.assertNotIn("2000-01-01", days)

    def test_bad_text_bodies_are_refused_without_calling_the_detector(self):
        headers = self.signup()
        with mock.patch("fraud_detector.analyze_text") as detector:
            for kwargs in [{"json": {}}, {"json": {"text": "   "}}, {"json": {"text": 5}},
                           {"json": ["text"]}, {"data": "not json"}]:
                r = self.call("POST", "/v1/analyze/text", headers, **kwargs)
                self.assertEqual(r.status_code, 400, kwargs)
            detector.assert_not_called()

    def test_audio_uses_a_private_temp_file_and_cleans_up(self):
        headers = self.signup()
        seen = {}

        def fake_analyze(path):
            seen["path"] = path
            with open(path, "rb") as f:
                seen["bytes"] = f.read()
            return {"fraud": False, "transcript": "ok"}

        with mock.patch("audio_handler.analyze_audio", side_effect=fake_analyze):
            r = self.call("POST", "/v1/analyze/audio", headers, content_type="multipart/form-data",
                          data={"file": (io.BytesIO(b"voice"), "../../evil name.MP3")})
        self.assertEqual(r.get_json()["transcript"], "ok")
        self.assertEqual(seen["bytes"], b"voice")
        self.assertNotIn("evil", seen["path"])       # client ka naam disk par nahi
        self.assertTrue(seen["path"].endswith(".mp3"))
        self.assertFalse(os.path.exists(seen["path"]))

    def test_audio_rejects_missing_or_wrong_files(self):
        headers = self.signup()
        with mock.patch("audio_handler.analyze_audio") as handler:
            r = self.call("POST", "/v1/analyze/audio", headers)
            self.assertEqual(r.status_code, 400)
            r = self.call("POST", "/v1/analyze/audio", headers, content_type="multipart/form-data",
                          data={"file": (io.BytesIO(b"MZ"), "virus.exe")})
            self.assertEqual(r.status_code, 400)
            handler.assert_not_called()


class LegacyRoutesStillWork(ApiTestCase):
    """Purani app abhi bina token ke purane routes use karti hai — /v1 ke aane
    se wo nahi tootni chahiye."""

    def test_old_routes_are_untouched(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        r = self.client.post("/check-number", json={"number": "111-111-427"})
        self.assertEqual(r.get_json()["status"], "scam")
        self.assertTrue(self.client.get("/number-lists").get_json()["spoofable"])


class ConfigTests(unittest.TestCase):
    def test_production_refuses_to_start_without_secrets(self):
        import subprocess
        import sys
        # Khali string set karna zaroori hai (hatana nahi): python-dotenv pehle se
        # maujood variables ko nahi chherta, is liye developer ki backend/.env
        # is test ka nateeja nahi badal sakti.
        env = dict(os.environ, APP_ENV="production", PYTHONPATH=BACKEND_DIR,
                   JWT_SECRET="", FRAUDGUARD_SALT="", DATABASE_URL="", SPACE_ID="",
                   TRUSTED_PROXY_HOPS="1")
        with tempfile.TemporaryDirectory() as cwd:
            missing = subprocess.run([sys.executable, "-c", "import config"], env=env, cwd=cwd,
                                     capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("ConfigError", missing.stderr)

            env.update(JWT_SECRET="j" * 32, FRAUDGUARD_SALT="s" * 32,
                       DATABASE_URL="postgresql://u:p@host/db")
            ok = subprocess.run(
                [sys.executable, "-c",
                 "import config; print(config.DATABASE_URL, config.TRUSTED_PROXY_HOPS)"],
                env=env, cwd=cwd, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertEqual(ok.stdout.split(), ["postgresql+psycopg://u:p@host/db", "1"])


class MigrationTests(unittest.TestCase):
    def test_migrations_build_exactly_the_tables_the_code_expects(self):
        fd, path = tempfile.mkstemp(suffix=".db", prefix="fraudguard-migrate-")
        os.close(fd)
        url = "sqlite:///" + path.replace("\\", "/")
        try:
            cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
            cfg.set_main_option("sqlalchemy.url", url)
            command.upgrade(cfg, "head")
            engine = create_engine(url)
            with engine.connect() as connection:
                drift = compare_metadata(MigrationContext.configure(connection), db.Base.metadata)
            engine.dispose()
            self.assertEqual(drift, [], "models aur migrations alag ho gaye — naya migration banayein")
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
