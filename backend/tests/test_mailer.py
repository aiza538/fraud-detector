# Email bhejne (mailer.py) ke tests — chalane ke liye (backend/ directory se):
#   python -m unittest tests.test_mailer
#
# Koi asli email nahi jati: network call (urlopen) mock hai.
import json
import os
import unittest
import urllib.error
from unittest import mock

os.environ.setdefault("GEMINI_API_KEY", "test-unit-evaluation-key")

import config
import mailer

SENDER = "FraudGuard AI <no-reply@fraudguard.example>"


def _ok():
    response = mock.MagicMock()
    response.__enter__.return_value.status = 200
    return response


def _http_error(status):
    return urllib.error.HTTPError("https://provider", status, "error", {}, None)


class MailerTests(unittest.TestCase):
    def settings(self, production=False, sender=SENDER, resend="re_test", brevo="xkeysib-test"):
        patches = [
            mock.patch.object(config, "IS_PRODUCTION", production),
            mock.patch.object(config, "MAIL_FROM", sender),
            mock.patch.object(config, "RESEND_API_KEY", resend),
            mock.patch.object(config, "BREVO_API_KEY", brevo),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def sent_requests(self, urlopen):
        return [call.args[0] for call in urlopen.call_args_list]

    def test_development_without_keys_prints_the_code_and_sends_nothing(self):
        self.settings(resend="", brevo="")
        with mock.patch("urllib.request.urlopen") as urlopen, \
                self.assertLogs(level="INFO") as logs:
            mailer.send_login_code("u@example.com", "123456")
        urlopen.assert_not_called()
        self.assertIn("123456", "\n".join(logs.output))
        self.assertTrue(mailer.is_configured())

    def test_production_without_keys_or_sender_is_switched_off(self):
        for kwargs in ({"resend": "", "brevo": ""}, {"sender": ""}):
            self.settings(production=True, **kwargs)
            self.assertFalse(mailer.is_configured(), kwargs)
            with mock.patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises(RuntimeError):
                    mailer.send_login_code("u@example.com", "123456")
            urlopen.assert_not_called()

    def test_resend_is_used_first(self):
        self.settings(production=True)
        self.assertTrue(mailer.is_configured())
        with mock.patch("urllib.request.urlopen", return_value=_ok()) as urlopen:
            mailer.send_login_code("u@example.com", "123456")
        [request] = self.sent_requests(urlopen)
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.get_header("Authorization"), "Bearer re_test")
        body = json.loads(request.data)
        self.assertEqual((body["from"], body["to"]), (SENDER, ["u@example.com"]))
        self.assertIn("123456", body["subject"])
        self.assertIn("123456", body["text"])
        self.assertIn("kisi ko na batayein", body["text"])

    def test_brevo_takes_over_when_resend_fails(self):
        self.settings(production=True)
        with mock.patch("urllib.request.urlopen", side_effect=[_http_error(500), _ok()]) as urlopen, \
                self.assertLogs(level="WARNING") as logs:
            mailer.send_login_code("u@example.com", "654321")
        resend, brevo = self.sent_requests(urlopen)
        self.assertEqual(brevo.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(brevo.get_header("Api-key"), "xkeysib-test")
        body = json.loads(brevo.data)
        self.assertEqual(body["sender"], {"name": "FraudGuard AI", "email": "no-reply@fraudguard.example"})
        self.assertEqual(body["to"], [{"email": "u@example.com"}])
        self.assertIn("654321", body["textContent"])
        # Failure log me na code, na user ka email.
        log = "\n".join(logs.output)
        self.assertNotIn("654321", log)
        self.assertNotIn("u@example.com", log)

    def test_only_brevo_configured(self):
        self.settings(production=True, resend="")
        with mock.patch("urllib.request.urlopen", return_value=_ok()) as urlopen:
            mailer.send_login_code("u@example.com", "111222")
        [request] = self.sent_requests(urlopen)
        self.assertIn("brevo", request.full_url)

    def test_both_failing_raises(self):
        self.settings(production=True)
        with mock.patch("urllib.request.urlopen", side_effect=[_http_error(401), OSError("timeout")]), \
                self.assertLogs(level="WARNING"):
            with self.assertRaises(RuntimeError):
                mailer.send_login_code("u@example.com", "123456")


if __name__ == "__main__":
    unittest.main()
