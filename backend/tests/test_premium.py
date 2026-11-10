# Premium plan (RevenueCat) ke tests — chalane ke liye (backend/ directory se):
#   python -m unittest tests.test_premium
#
# RevenueCat ko kabhi asli call nahi jati: urlopen mock hai.
import json
import time
import unittest
import urllib.error
from unittest import mock

from tests.test_api_v1 import DAY, ApiTestCase

import config
import db
import premium

KEY = "sk_test_revenuecat"


def _revenuecat(expires_date="2099-01-01T00:00:00Z", entitlement="premium"):
    """RevenueCat /v1/subscribers ka jawab jaisa."""
    entitlements = {}
    if entitlement:
        entitlements[entitlement] = {"expires_date": expires_date,
                                     "product_identifier": "fraudguard_premium"}
    body = json.dumps({"subscriber": {"entitlements": entitlements}}).encode()
    response = mock.MagicMock()
    response.__enter__.return_value.read.return_value = body
    return response


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


class PremiumTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(config, "REVENUECAT_SECRET_API_KEY", KEY)
        patcher.start()
        self.addCleanup(patcher.stop)

    def account(self, headers):
        r = self.call("GET", "/v1/account", headers)
        self.assertEqual(r.status_code, 200)
        return r.get_json()

    def analyze(self, headers, ip="10.0.0.1"):
        return self.call("POST", "/v1/analyze/text", headers, ip, json={"text": "x"})

    # --- free plan -----------------------------------------------------------
    def test_free_users_get_free_limits_and_never_call_revenuecat(self):
        headers = self.signup()
        with mock.patch("urllib.request.urlopen") as urlopen, \
                mock.patch("fraud_detector.analyze_text", return_value={"fraud": False}):
            data = self.account(headers)
            self.assertFalse(data["premium"])
            self.assertEqual(data["id"], self.user_id(headers))
            self.assertEqual(data["limits"], config.FREE_DAILY_LIMITS)
            for _ in range(config.FREE_DAILY_LIMITS["analyze_text"]):
                self.assertEqual(self.analyze(headers).status_code, 200)
            r = self.analyze(headers)
            self.assertEqual((r.status_code, r.get_json()["error"]), (429, "free_limit"))
            used = self.account(headers)["used_today"]["analyze_text"]
            self.assertEqual(used, config.FREE_DAILY_LIMITS["analyze_text"])
        urlopen.assert_not_called()

    def test_phone_protection_is_never_limited_by_the_plan(self):
        # Number check ki koi daily limit nahi; reports ki limit dono plans par same.
        self.assertNotIn("report", config.FREE_DAILY_LIMITS)
        headers = self.signup()
        for _ in range(20):
            r = self.call("POST", "/v1/check-number", headers, json={"number": "03001234567"})
            self.assertEqual(r.status_code, 200)

    # --- buying --------------------------------------------------------------
    def test_refresh_after_purchase_unlocks_premium_limits(self):
        headers = self.signup()
        with mock.patch("urllib.request.urlopen", return_value=_revenuecat()) as urlopen:
            r = self.call("POST", "/v1/premium/refresh", headers)
        self.assertEqual(r.status_code, 200, r.get_json())
        data = r.get_json()
        self.assertTrue(data["premium"])
        self.assertEqual(data["limits"]["analyze_text"], config.DAILY_LIMITS["analyze_text"])
        [request] = [c.args[0] for c in urlopen.call_args_list]
        self.assertEqual(request.full_url, premium.API_URL + self.user_id(headers))
        self.assertEqual(request.get_header("Authorization"), "Bearer " + KEY)

        with mock.patch("urllib.request.urlopen") as urlopen, \
                mock.patch("fraud_detector.analyze_text", return_value={"fraud": False}):
            for _ in range(config.FREE_DAILY_LIMITS["analyze_text"] + 3):
                self.assertEqual(self.analyze(headers).status_code, 200)
        urlopen.assert_not_called()  # 24 ghante tak dobara poochna nahi

    def test_claiming_premium_without_buying_does_nothing(self):
        headers = self.signup()
        with mock.patch("urllib.request.urlopen", return_value=_revenuecat(entitlement=None)):
            data = self.call("POST", "/v1/premium/refresh", headers).get_json()
        self.assertFalse(data["premium"])
        with db.SessionLocal() as s:
            self.assertIsNone(s.get(db.User, self.user_id(headers)).premium_until)

    def test_lifetime_entitlement_has_no_expiry(self):
        headers = self.signup()
        with mock.patch("urllib.request.urlopen", return_value=_revenuecat(expires_date=None)):
            data = self.call("POST", "/v1/premium/refresh", headers).get_json()
        self.assertTrue(data["premium"])
        self.assertEqual(data["premium_until"], premium.FOREVER)

    def test_other_entitlements_do_not_count(self):
        headers = self.signup()
        with mock.patch("urllib.request.urlopen", return_value=_revenuecat(entitlement="pro")):
            self.assertFalse(self.call("POST", "/v1/premium/refresh", headers).get_json()["premium"])

    def test_refresh_is_rate_limited(self):
        headers = self.signup()
        with mock.patch("urllib.request.urlopen", return_value=_revenuecat()) as urlopen:
            codes = [self.call("POST", "/v1/premium/refresh", headers).status_code for _ in range(21)]
        self.assertEqual(codes[-1], 429)
        self.assertEqual(urlopen.call_count, 20)

    def test_without_a_key_premium_is_unavailable(self):
        headers = self.signup()
        with mock.patch.object(config, "REVENUECAT_SECRET_API_KEY", ""), \
                mock.patch("urllib.request.urlopen") as urlopen:
            r = self.call("POST", "/v1/premium/refresh", headers)
            self.assertEqual((r.status_code, r.get_json()["error"]), (503, "premium_unavailable"))
            self.assertFalse(self.account(headers)["premium"])
        urlopen.assert_not_called()

    def test_revenuecat_outage_on_refresh_is_a_clear_error(self):
        headers = self.signup()
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")), \
                self.assertLogs(level="WARNING") as logs:
            r = self.call("POST", "/v1/premium/refresh", headers)
        self.assertEqual((r.status_code, r.get_json()["error"]), (503, "premium_unavailable"))
        self.assertNotIn(self.user_id(headers), "\n".join(logs.output))

    # --- renewals, cancels, refunds -----------------------------------------
    def test_paying_user_is_rechecked_once_a_day(self):
        headers = self.signup()
        now = int(time.time())
        self.edit_user(headers, premium_until=now + 30 * DAY, premium_checked_at=now - 2 * DAY)
        # Refund ho gaya: RevenueCat ab entitlement nahi deta.
        with mock.patch("urllib.request.urlopen", return_value=_revenuecat(entitlement=None)) as urlopen:
            self.assertFalse(self.account(headers)["premium"])
            self.assertFalse(self.account(headers)["premium"])
        self.assertEqual(urlopen.call_count, 1)  # ab free hai — dobara call nahi

    def test_expired_subscription_is_checked_for_renewal(self):
        headers = self.signup()
        now = int(time.time())
        self.edit_user(headers, premium_until=now - 60, premium_checked_at=now - 3 * DAY)
        renewed = _revenuecat(expires_date=_iso(now + 30 * DAY))
        with mock.patch("urllib.request.urlopen", return_value=renewed) as urlopen:
            self.assertTrue(self.account(headers)["premium"])
            self.assertTrue(self.account(headers)["premium"])
        self.assertEqual(urlopen.call_count, 1)

    def test_expired_and_not_renewed_is_checked_only_once_a_day(self):
        headers = self.signup()
        now = int(time.time())
        self.edit_user(headers, premium_until=now - DAY, premium_checked_at=now - 2 * DAY)
        lapsed = _revenuecat(expires_date=_iso(now - DAY))
        with mock.patch("urllib.request.urlopen", return_value=lapsed) as urlopen, \
                mock.patch("fraud_detector.analyze_text", return_value={"fraud": False}):
            self.assertFalse(self.account(headers)["premium"])
            for _ in range(3):
                self.analyze(headers)
        self.assertEqual(urlopen.call_count, 1)

    def test_outage_keeps_a_paying_user_premium(self):
        headers = self.signup()
        now = int(time.time())
        self.edit_user(headers, premium_until=now + 10 * DAY, premium_checked_at=now - 2 * DAY)
        with mock.patch("urllib.request.urlopen", side_effect=OSError("timeout")), \
                self.assertLogs(level="WARNING"):
            self.assertTrue(self.account(headers)["premium"])

    def test_premium_users_skip_the_shared_network_limit(self):
        now = int(time.time())
        with mock.patch.dict(config.DAILY_LIMITS_PER_IP, {"analyze_text": 2}), \
                mock.patch("fraud_detector.analyze_text", return_value={"fraud": False}), \
                mock.patch("urllib.request.urlopen") as urlopen:
            for _ in range(2):
                self.assertEqual(self.analyze(self.signup()).status_code, 200)
            self.assertEqual(self.analyze(self.signup()).status_code, 429)
            paying = self.signup()
            self.edit_user(paying, premium_until=now + DAY, premium_checked_at=now)
            self.assertEqual(self.analyze(paying).status_code, 200)
        urlopen.assert_not_called()


class ParseTests(unittest.TestCase):
    def test_expiry_parsing(self):
        self.assertEqual(premium._parse_time("1970-01-02T00:00:00Z"), 86400)
        self.assertEqual(premium._parse_time("1970-01-02T00:00:00.000Z"), 86400)
        self.assertEqual(premium._parse_time(None), premium.FOREVER)
        self.assertIsNone(premium._parse_time("garbage"))


if __name__ == "__main__":
    unittest.main()
