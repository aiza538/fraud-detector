# FraudGuard: Multi-Region Threat Directory & Pattern Matching Documentation

This document records the architectural improvements, schema specifications, dataset verifications, and rule-engine expansions implemented in the FraudGuard repository.

Sections 1–4 cover the threat directory and the analyzer's scam patterns. Sections 5–13 cover the secure `/v1` API, accounts, the database, the phone's rule sync and the mobile app, added on 13–14 October 2026. Section 13 lists what is still pending and what it is waiting on.

---

## 1. Architectural Overview & Multi-Region Design

FraudGuard screens communications across phone calls, SMS, WhatsApp, and digital services. To protect both local citizens and overseas Pakistani diaspora corridors (UAE, UK), the database has been restructured to support multi-region partitioning without breaking backward compatibility:

```
official_directory.json
├── regions
│   ├── PK       (Pakistan Domestic: 43 Scheduled Banks, Wallets, Regulators, Telcos)
│   ├── GLOBAL   (Ubiquitous Tech Platforms & Cross-Border Couriers)
│   ├── AE       (United Arab Emirates Diaspora Corridor)
│   └── UK       (United Kingdom Diaspora Corridor)
├── entities     (Consolidated Flat Whitelist for Legacy Compatibility)
└── _revoked_or_fraud_alerts (Revoked licenses & active impersonation alerts)
```

The directory lives in one place only: [backend/data/official_directory.json](backend/data/official_directory.json).

---

## 2. Directory Schema Specification

Defined in [backend/data/official_directory.schema.json](backend/data/official_directory.schema.json) adhering to JSON Schema Draft-07.

### Entity Properties:
* **`name`** *(string)*: Official registered institutional display name.
* **`category`** *(string, enum)*:
  * `commercial_bank`
  * `digital_wallet`
  * `law_enforcement`
  * `government_agency`
  * `regulatory_body`
  * `telecom_operator`
  * `global_tech`
  * `international_courier`
* **`website`** *(string, URI)*: Institutional primary homepage.
* **`source_url`** *(string, URI)*: Verification citation page.
* **`web_endpoints`** *(array of URIs)*: Official login portals, tracking endpoints, and complaint centers.
* **`auth_headers`** *(array of strings, optional)*: Approved SMS sender IDs, alphanumeric headers, and gateway IDs (e.g., `WhatsAppCode`, `DHLExpress`, `G-Code`).
* **`uans`** *(array of strings)*: Normalized Universal Access Numbers and primary helplines.
* **`shortcodes`** *(array of strings)*: PTA/carrier approved shortcodes.
* **`numbers`** *(array of strings)*: Combined array of callable numbers and shortcodes (consumed directly by [backend/main.py](backend/main.py) for Levenshtein spoof detection and whitelist validation).
* **`verified_on`** *(string)*: Verification timestamp (`YYYY-MM-DD`).
* **`note`** *(string)*: Security-critical context (in-app chat notices, spoof risks, and operational guidelines).
* **`status`** *(string, enum)*: `verified` | `pending_review`.

---

## 3. Directory Dataset Breakdown

### 3.1. `GLOBAL` — Tech Platforms & International Couriers

| Entity | Category | Official Web Endpoints | Auth Headers / Sender IDs | Official Numbers / Shortcodes | Operational Security Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **WhatsApp** | `global_tech` | `whatsapp.com`, `faq.whatsapp.com`, `web.whatsapp.com` | `WhatsApp`, `WhatsAppCode` | *In-app support only* | WhatsApp NEVER calls users to request 6-digit verification codes. Support is in-app only. |
| **Google** | `global_tech` | `google.com`, `myaccount.google.com`, `support.google.com`, `accounts.google.com` | `Google`, `G-Code` | *Carrier routes* | Google representatives NEVER call demanding passwords or 2-Step Verification codes. |
| **Microsoft** | `global_tech` | `microsoft.com`, `account.microsoft.com`, `support.microsoft.com`, `login.live.com` | `Microsoft`, `MSFT` | *Carrier routes* | Microsoft never places unsolicited tech support calls claiming a computer is infected. |
| **Telegram** | `global_tech` | `telegram.org`, `web.telegram.org`, `t.me` | `Telegram` | `777000` (Verified Chat ID) | Official login codes arrive via Telegram service chat `777000` or SMS sender `Telegram`. |
| **Binance** | `global_tech` | `binance.com`, `binance.com/en/support`, `binance.com/en/official-verification` | `Binance`, `BinanceVerify` | *Live chat only* | Binance has NO inbound phone helpline. Authentic channels can be checked at `binance.com/en/official-verification`. |
| **Apple** | `global_tech` | `apple.com`, `appleid.apple.com`, `support.apple.com`, `icloud.com` | `Apple` | `1-800-275-2273` (1-800-APL-CARE) | Apple never texts or calls requesting Apple ID passwords or two-factor codes to "unlock iCloud". |
| **DHL** | `international_courier` | `dhl.com`, `mydhl.express.dhl`, `dhl.com/global-en/home/tracking.html` | `DHL`, `DHLExpress` | PK: `111-345-111` | Official tracking domain is strictly `dhl.com` or `mydhl.express.dhl`. Beware of shortened link smishing. |
| **FedEx** | `international_courier` | `fedex.com`, `fedex.com/en-us/tracking.html` | `FedEx` | PK: `111-711-111` | Tracking is strictly on `fedex.com`. FedEx never demands credit card details via SMS to release packages. |
| **Aramex** | `international_courier` | `aramex.com`, `aramex.com/track/shipments` | `Aramex` | PK: `111-272-639` | Tracking and package payments occur strictly on `aramex.com`. |

### 3.2. `AE` — United Arab Emirates Corridor

| Entity | Category | Official Web Endpoints | Helplines / Shortcodes | Operational Security Note |
| :--- | :--- | :--- | :--- | :--- |
| **Central Bank of the UAE (CBUAE)** | `regulatory_body` | `centralbank.ae` | `800-22823` (`800-CBUAE`) | CBUAE never calls individuals requesting money transfers or banking credentials. |
| **Emirates Post** | `international_courier` | `emiratespost.ae` | `600-599-999` | Major smishing target: fake parcel delivery fee SMS links demanding 10–25 AED. |
| **Dubai Police** | `law_enforcement` | `dubaipolice.gov.ae` | `901` (Non-emergency), `999` (Emergency) | Dubai Police never demands immediate fine payments via phone calls. |
| **Emirates NBD** | `commercial_bank` | `emiratesnbd.com` | `600-540-000` (`+971-600-540-000`) | 24/7 Call Center helpline. |
| **ADCB** | `commercial_bank` | `adcb.com` | `600-502-030` (`+971-600-502-030`) | Abu Dhabi Commercial Bank contact center. |

### 3.3. `UK` — United Kingdom Corridor

| Entity | Category | Official Web Endpoints | Helplines / Shortcodes | Operational Security Note |
| :--- | :--- | :--- | :--- | :--- |
| **HMRC** | `government_agency` | `gov.uk/government/organisations/hm-revenue-customs` | `+44-300-200-3300` (`0300 200 3300`) | HMRC never threatens arrest over phone calls or requests payments via gift cards / crypto. |
| **Royal Mail** | `international_courier` | `royalmail.com` | `+44-3457-740-740` (`03457 740 740`) | Top UK smishing delivery fee scam vector. Official domain is strictly `royalmail.com`. |
| **Action Fraud / NCSC** | `law_enforcement` | `actionfraud.police.uk`, `ncsc.gov.uk` | `+44-300-123-2040`, `7726` (Free Spam SMS) | UK National Fraud and Cyber Crime Reporting Centre; `7726` forwards spam SMS for network investigation. |
| **Barclays UK** | `commercial_bank` | `barclays.co.uk` | `+44-345-734-5345` (`0345 734 5345`) | Official UK telephone banking helpline. |
| **NatWest** | `commercial_bank` | `natwest.com` | `+44-345-788-8444` (`0345 788 8444`) | Official UK 24/7 telephone banking. |

### 3.4. `PK` — Pakistan Domestic Entities (43 Verified Authorities)

Includes full institutional details for:
* **Commercial Banks**: HBL, Meezan Bank, Bank Alfalah, UBL, MCB, Bank AL Habib, JS Bank, NBP, Allied Bank, Bank of Punjab, Standard Chartered, Soneri Bank, BankIslami, Faysal Bank, Askari Bank, Habib Metro, Dubai Islamic Bank PK, Bank of Khyber, Sindh Bank, Bank Makramah (Summit Bank), First Women Bank, Al Baraka Bank, Samba Bank.
* **Digital Wallets & EMIs**: JazzCash, Easypaisa, SadaPay, NayaPay, UPaisa, Zindigi, Finja EMI, Keenu Wallet.
* **Law Enforcement & Regulators**: FIA (1991 / 1717 / 111-345-786), BISP (8171 / 0800-26477), NADRA (1777 / 1700 / 7000 / 8400 / 8300 / 111-786-100), PTA (0800-55055 / 8282 / 668), State Bank of Pakistan (111-727-111 / Sunwai), SECP (111-117-327 / 0800-88008), NAB (111-622-622), FBR (111-772-772 / 9966), Banking Mohtasib (111-727-273), Pakistan Post (111-111-117).
* **Telecom Operators**: Jazz (111-300-300), Zong (111-222-111).
* **Revoked / Fraud Alert Registry**: TAG Innovation (Pvt.) Ltd. (SBP officially revoked EMI pilot approval in Oct 2022).

---

## 4. Multi-Region Scam Pattern & Whitelist Architecture

### 4.1. Pattern Database (`backend/data/scam_patterns.json`)

The pattern database uses a hierarchical multi-region architecture structured under `regional.PK` and `regional.GLOBAL`, with backward-compatible aliases:

```json
{
  "_version": "3.0.0",
  "regional": {
    "PK": {
      "region_name": "Pakistan",
      "statutory_framework": "Prevention of Electronic Crimes Act (PECA) 2016",
      "statutory_mappings": {
        "Section 13": "Electronic Forgery",
        "Section 14": "Electronic Fraud",
        "Section 16": "Unauthorized Copying or Transmission of Critical Data",
        "Section 17": "Identity Theft / Unauthorized Use of Identity Information",
        "Section 21": "Cyber Harassment & Coercive Communications"
      },
      "whitelists": { ... },
      "patterns": [ ... ]
    },
    "GLOBAL": {
      "region_name": "Global Threat Vectors",
      "statutory_framework": "International Cybercrime Conventions (Budapest Convention / US CFAA / UK CMA / GDPR)",
      "whitelists": { ... },
      "patterns": [ ... ]
    }
  },
  "pakistan_patterns": [ ... ],
  "international_vectors": [ ... ]
}
```

#### A. `regional.PK` Components:
1. **Bilingual Regex Engine (Roman Urdu & Urdu Script)**:
   * **BISP / Ehsaas Program Fraud**: Matches welfare impersonation (`8171`, `bisp`, `ehsaas`, `بے نظیر`, `احساس`, `25000`, `wazeefa`, `رقم`, `وظیفہ`).
   * **Prize / Lottery Scam**: Detects fake prize notifications (`congratulations`, `lucky draw`, `inam`, `مبارک`, `قرعہ اندازی`, `انعام`, `charges`, `فیس`).
   * **Bank / Wallet Block Panic Trigger**: Detects urgent account block extortion (`hbl`, `meezan`, `jazzcash`, `easypaisa`, `band ho`, `block`, `بینک`, `اکاؤنٹ`, `بند ہو`, `بلاک`, `otp`, `او ٹی پی`).
   * **Credential & OTP Harvesting**: Intercepts one-time password extraction attempts (`otp`, `code`, `bhejein`, `bhij do`, `batao`, `او ٹی پی`, `کوڈ`, `ارسال`, `بتائیں`).
   * **Customs / Courier Parcel Hold Phishing**: Detects fake airport customs holds (`parcel`, `customs`, `clearance`, `dollar`, `fee`, `پارسل`, `کسٹمز`, `فیس`).
   * **Fake Daily-Earning Scheme**: Detects task-based Ponzi schemes (`daily`, `rozana`, `profit`, `munafa`, `dollar`, `invest`, `telegram`, `روزانہ`, `منافع`, `کمائی`, `ٹیلیگرام`, `ڈپازٹ`).
   * **SIM Swap Attacks**: Detects CNIC extortion for unauthorized SIM re-issuance (`sim`, `سیم`, `cnic`, `شناختی کارڈ`, `block`, `بلاک`).
   * **WhatsApp Account Ban Hoax**: Detects chain hoax account takeover prompts (`whatsapp`, `ban`, `24 hour`, `band`, `verification code`).
   * **PTA Device Tax Scam**: Detects fake DIRBS/FBR mobile tax links (`pta`, `dirbs`, `imei`, `tax`, `fbr`).
   * **WhatsApp Cloned Voice Scam**: Detects synthetic AI voice extortion (`meri awaz`, `voice note`, `beta`, `hospital`, `emergency`, `paise bhej`, `loan`, `udhaar`).
   * **Fake Job Scam**: Detects recruitment advance fee fraud (`job`, `salary`, `registration fee`, `fee`, `deposit`, `jazzcash`, `easypaisa`).
   * **Meezan Bank Smishing**: Detects phishing URLs spoofing Meezan Bank portal.
   * **WhatsApp Family Emergency**: Detects urgent medical extortion into personal wallet accounts.

2. **Statutory PECA 2016 Mappings**:
   * **Section 13**: Electronic Forgery (falsifying institutional headers, fake notices).
   * **Section 14**: Electronic Fraud (deceptive gain, advance-fee solicitation, Ponzi schemes).
   * **Section 16**: Unauthorized Copying or Transmission of Critical Data (telecom subscriber data extraction).
   * **Section 17**: Identity Theft / Unauthorized Use of Identity Information (harvesting passwords, OTPs, CNICs).
   * **Section 21**: Cyber Harassment & Coercive Communications (panic-inducing extortion, false arrest/block threats).

3. **Local Transactional Whitelists**:
   * **Telecom Recharges**: Automated balance reload confirmations for Jazz, Zong, Telenor, and Ufone.
   * **Local Bank OTP Formats**: Official OTP delivery formats for HBL, Meezan Bank, JazzCash, Easypaisa, UBL Digital, Bank Alfalah Alfa, SadaPay, and NayaPay.

#### B. `regional.GLOBAL` Components:
1. **English Regex Patterns**:
   * **Cryptocurrency & Wallet Drainer Phishing**: Detects seed phrase requests, secret recovery phrases, private key theft for Binance, MetaMask, Trust Wallet, and Phantom.
   * **Global Courier Delivery Fee & Hold Phishing**: Detects smishing for DHL, FedEx, Aramex, and UPS tracking fees, customs clearance charges, and warehouse holds.
   * **Global Tech Account Suspension & Security Alerts**: Detects fake Apple ID locks, Google 2FA compromise warnings, Netflix subscription expiration notices, and Microsoft account security traps.

2. **Global Tech Whitelists**:
   * **Google Verification Codes**: Standard `G-XXXXXX` and automated delivery formats.
   * **WhatsApp Registration Codes**: Official 6-digit registration codes (`XXX-XXX`).
   * **Microsoft 2FA**: Official 6-7 digit account security code formats.
   * **Apple ID Verification Codes**: Official Apple ID 6-digit security codes.

---

### 4.2. Dual-Engine Architecture (`backend/pattern_matcher.py`)

1. **Pre-Evaluation Whitelist Gate**:
   Before pattern evaluation, incoming messages are checked against registered regional whitelists and OTP delivery hints (`do not share`, `never share`, `for your security`). Legitimate automated transactional SMS messages exit immediately (`return None`), eliminating false positives.

2. **Dual Regex & Anchor Matching**:
   Candidate patterns are evaluated using:
   - **Regex Matching**: Pre-compiled regexes matching exact syntactic attack vectors in Roman Urdu, Urdu script, and English.
   - **Keyword & Anchor Verification**: Multi-term frequency threshold (`min_match >= 3`) gated by critical anchors (`anchors`), ensuring benign messages mentioning isolated words (such as casual conversations about hospital visits or work updates) are not falsely flagged.

3. **Safe Regional Filtering**:
   - `region="PK"`: Evaluates Pakistan domestic patterns and ubiquitous `GLOBAL` vectors.
   - `region="GLOBAL"`: Evaluates global threat vectors.
   - `region=None`: Evaluates across all regions for backward compatibility.

---

## 5. Mobile App Synchronization Architecture

The app talks only to the token-protected `/v1` API (section 7). All calls go through [FraudGuardExpo/src/services/api.js](FraudGuardExpo/src/services/api.js).

1. **Identity without a login screen**:
   - On first use the app calls `POST /v1/auth/anonymous` and receives its own token ([session.js](FraudGuardExpo/src/services/session.js)).
   - The token is kept in the phone's secure storage (`expo-secure-store`) and sent with every request.
   - It lasts 30 days and is renewed automatically during its last 7 days. If the server rejects it (401), the app gets a new anonymous token and retries once.
2. **Online Dynamic Analysis**:
   - `POST /v1/check-number`, `POST /v1/analyze/text` and `POST /v1/analyze/audio`.
   - Numbers are screened against `ALL_LEGITIMATE` (canonical and area-prefixed UANs across all loaded regions) and Levenshtein spoofs (distance $\le 2$) are detected. The rules live in [backend/number_rules.py](backend/number_rules.py).
3. **Offline Local Caller ID & Native Android Screening**:
   - The app calls `GET /v1/number-lists` (see [callMonitor.js](FraudGuardExpo/src/services/callMonitor.js)).
   - The backend sends verified numbers (`directory`), confirmed scam numbers (`scam`) and near-neighbour spoof targets (`spoofable`). Numbers below the report threshold are never sent.
   - The app hands these to the Android Kotlin module ([CallGuardModule.kt](FraudGuardExpo/modules/expo-call-guard/android/src/main/java/expo/modules/callguard/CallGuardModule.kt) -> `NumberRules.kt`), so calls are screened on the device without internet.
4. **Background message rules**:
   - `GET /v1/rules` serves the phone's own rule set (section 10).
   - **Not finished:** the Kotlin scanner still uses the copy compiled into the app. A test keeps that copy identical to the server file until the phone is switched to the downloaded rules.
5. **Change detection**: `/v1/number-lists` and `/v1/rules` send an `ETag`. A client that sends it back in `If-None-Match` gets an empty `304` when nothing changed (the number list is about 98 KB).

**Expo Go limitation.** Call screening and WhatsApp/SMS scanning are custom Android code. Expo Go cannot load custom native code, so the app switches those features off there. Only the analyzer, number checker, email verification and account screens run in Expo Go. Testing the protection features needs a development build.

---

## 6. Verification & Test Coverage

All automated test suites pass without regressions:
* **Detection Accuracy & Whitelist Integrity Suite** ([backend/tests/test_detection_accuracy.py](backend/tests/test_detection_accuracy.py)):
  - **Scam Detection Rate**: **100.00%** (18/18 detected, target: >95.0%).
  - **False Positive Rate**: **0.00%** (0/12 triggered across legitimate Pakistani bank OTPs and Global 2FA codes).
  - **Caller ID / Levenshtein Precision**: **100.00%** (9/9 correct across `OFFICIAL_VERIFIED`, `SPOOF_SUSPECT`, and `UNVERIFIED`).
  - **Multi-Region Loader Validation**: Root region parsing (`PK` and `GLOBAL`) verified for both [backend/data/scam_patterns.json](backend/data/scam_patterns.json) and [backend/data/official_directory.json](backend/data/official_directory.json).
* **Caller ID Screening Tests** (22 test cases): Area-code prefixed UANs, bare UANs, shortcodes (`1991`, `8171`, `1700`, `1777`, `1717`), toll-free lines, Levenshtein spoof detections (HBL, Meezan), consensus threshold handling, and personal mobile pass-throughs pass 100%.
* **Pattern Matching Tests** (46 test cases): Validated that normal conversation messages, legitimate bank OTP SMS alerts, and telecom recharge receipts remain silent, while domestic Pakistani scams (Roman Urdu & Urdu script) and global cross-border threats (Crypto drainers, DHL/FedEx holds, Apple ID lockouts) are reliably flagged with statutory PECA citations.
* **Group Chat & Context Screening Tests** (16 test cases): Group link suppression and 1:1 threat identification verified.
* **`/v1` API Tests** (36 test cases, [backend/tests/test_api_v1.py](backend/tests/test_api_v1.py)): every route refuses requests without a token; forged, expired, blocked and revoked tokens are rejected; signup, daily, per-network and per-email limits hold; the email-code flow (wrong code lockout, expiry, account restore); report consensus rules; admin-only removal; delete account; `ETag`/`304` behaviour; the legacy routes still work; production refuses to start without secrets; the migration builds exactly the tables the code expects.
* **Phone Rules Tests** (4 test cases, [backend/tests/test_phone_rules.py](backend/tests/test_phone_rules.py)): the server rule file matches the rules compiled into the app; every rule is well formed; 19 ordinary everyday messages raise no alert.
* **Continuous integration**: [.github/workflows/backend-tests.yml](.github/workflows/backend-tests.yml) runs all suites on every pull request that touches `backend/` or the Android module.

Run everything from `backend/`:
```bash
python -m tests.test_pattern_matcher
python -m tests.test_number_screening
python -m tests.test_group_messages
python -m unittest tests.test_detection_accuracy tests.test_api_v1 tests.test_phone_rules
```

---

## 7. Secure `/v1` API

Defined in [backend/api_v1.py](backend/api_v1.py). Every route needs `Authorization: Bearer <token>` except the one that issues the first token. Errors are returned as `{"error": "<code>", "message": "<text>"}`.

| Method & path | Who can call | Purpose |
| :--- | :--- | :--- |
| `POST /v1/auth/anonymous` | Anyone | Creates an anonymous account and returns its token. |
| `POST /v1/auth/refresh` | Any token | Returns a fresh token for the same account. |
| `GET /v1/account` | Any token | `verified`, `admin`, `created_at`. |
| `DELETE /v1/account` | Any token | Deletes the account, its reports, its pending code and its counters. |
| `POST /v1/auth/email/start` | Any token | Sends a 6-digit code to an email address. |
| `POST /v1/auth/email/verify` | Any token | Checks the code and marks the account verified, or restores the existing account for that email. |
| `POST /v1/analyze/text` | Any token | Rule engine, then Gemini. Same result format as before. |
| `POST /v1/analyze/audio` | Any token | AssemblyAI transcription, then text analysis. Max 25 MB, audio extensions only. |
| `POST /v1/check-number` | Any token | 4-level verdict: `safe`, `scam`, `suspicious`, `unknown`. |
| `GET /v1/number-lists` | Any token | Offline lists for the phone's call screening. |
| `GET /v1/rules` | Any token | The phone's background message rules. |
| `POST /v1/report-number` | Verified email | Records one report per account per number. |
| `POST /v1/admin/unreport-number` | Admin | Removes all community reports for a number. |

**Legacy routes.** The unversioned routes in [backend/main.py](backend/main.py) (`/analyze/text`, `/analyze/audio`, `/check-number`, `/report-number`, `/unreport-number`, `/number-lists`) are unchanged and need no token. The mobile app no longer uses them. They remain only because the web app and the browser extension still call them, and they still store reports in a JSON file. They are to be removed once those clients move to `/v1`.

---

## 8. Accounts, Tokens & Email Verification

Implemented in [backend/security.py](backend/security.py) and [backend/api_v1.py](backend/api_v1.py).

* **Tokens**: HS256 JWT signed with `JWT_SECRET`, valid 30 days. The algorithm is pinned, and the user is re-read from the database on every request, so blocking a user or raising their `token_version` takes effect immediately.
* **Anonymous first**: an account starts with no personal data. Analysis and number checks need nothing more.
* **Email verification** is needed only to report a number:
  - 6-digit code, valid 10 minutes, at most 5 wrong attempts, 60 seconds between sends.
  - Only an HMAC of the normalised email is stored, never the email itself. Normalising lowercases the address, drops `+tags`, and for Gmail drops dots, so one inbox is one account.
  - Throwaway email domains are refused.
  - Verifying an email that already belongs to an account signs the user into that account (new phone or reinstall). A verified account is never merged away.
* **Admins** are the verified accounts whose email is listed in `ADMIN_EMAILS`.
* **Email delivery is not connected yet.** In development the code is printed in the server log ([backend/mailer.py](backend/mailer.py)). In production the feature answers `503` until a real provider (Resend, with Brevo as backup) is added, so codes are never written to production logs.

---

## 9. Community Reports & Limits

**When a number becomes a confirmed scam** (`_report_counts` in [backend/api_v1.py](backend/api_v1.py)). A report counts only if all of these hold:

* the reporter's email is verified, and was verified at least 48 hours ago;
* the reporter is not blocked;
* the report is less than 180 days old.

A number is confirmed when counted reports come from **5 different networks** (distinct hashed IPs). One account can report a number once. Verified official numbers cannot be reported. Numbers in `verified_scam_numbers.json` are always treated as scam.

**Limits** (all in [backend/config.py](backend/config.py)):

| Limit | Value |
| :--- | :--- |
| New anonymous accounts per network per hour | 30 |
| Text analyses per account per day | 60 |
| Audio analyses per account per day | 10 |
| Reports per account per day | 10 |
| Email codes per account per day | 5 |
| Text analyses per network per day | 300 |
| Audio analyses per network per day | 40 |
| Email codes per network per hour | 10 |
| Email codes per email address per day | 5 |

Per-network limits exist because a new anonymous account is free, so a per-account limit alone can be dodged. The per-email limit stops someone guessing another person's code by cycling accounts. Days are UTC.

**Real client IP.** Behind a proxy the server would see the proxy's address for every user. `TRUSTED_PROXY_HOPS` tells it how many proxies to trust (default 1 in production, 0 locally, where `X-Forwarded-For` is ignored so it cannot be faked).

---

## 10. Phone Rules vs Analyzer Patterns

The phone's background scanner and the analyzer use **different rule sets on purpose**.

| | Analyzer patterns | Phone rules |
| :--- | :--- | :--- |
| File | [backend/data/scam_patterns.json](backend/data/scam_patterns.json) | [backend/data/phone_rules.json](backend/data/phone_rules.json) |
| Runs when | A user asks to check a message | Automatically, on every incoming WhatsApp/SMS notification |
| Size | 16 patterns with regexes | 6 keyword rules, OTP word lists, link lists |
| Matching | Substring or regex | Word-boundary keywords, and at least one anchor word |

Tested on 20 ordinary everyday messages, the analyzer patterns raised a scam alert on 12 and the phone rules on 1. Example: "Parcel aa gaya hai, delivery charges 200 rupay rider ko de dena" matches the analyzer's courier pattern. Shipping the analyzer patterns to the phone would flood users with false alarms, so the phone keeps its own stricter set.

* `phone_rules.json` was generated from `TextRules.kt` by script. A test fails if the two differ.
* `GET /v1/rules` serves it with a `version` (a hash of the content) and `schema: 1`.
* Adding or changing a phone rule: edit the JSON, then run the phone rules tests. The 19 everyday messages must stay silent.

**Known issues, left unchanged for a team decision:**

* In the phone's WhatsApp ban-hoax rule, the anchor "verification code" is not in the rule's keyword list, so it can never match and some hoax messages are missed. The obvious fix risks false alarms on real WhatsApp codes.
* The same 12 everyday messages are also reported as fraud by the analyzer when pasted in, because a pattern match returns a verdict without the Gemini check.

---

## 11. Database, Configuration & Deployment

**Tables** ([backend/db.py](backend/db.py)):

| Table | Holds |
| :--- | :--- |
| `users` | Account id, creation time, hashed signup IP, email hash (empty if anonymous), `token_version`, `blocked`. |
| `number_reports` | One row per account per reported number, with hashed IP, note and time. |
| `usage_counters` | Daily counts per account, per network and per email. Yesterday's rows are deleted automatically. |
| `email_challenges` | The one pending email code per account (hashed), with expiry and attempt count. |

Locally the server uses a SQLite file (`backend/fraudguard-dev.db`) and creates tables itself. In production it uses Postgres through `DATABASE_URL`, and tables are created or changed only by Alembic migrations ([backend/migrations/](backend/migrations)).

**Settings** ([backend/config.py](backend/config.py)). Production means `APP_ENV=production` or running inside a Hugging Face Space. There the server **refuses to start** without the first three:

| Variable | Purpose |
| :--- | :--- |
| `DATABASE_URL` | Neon Postgres **pooled** connection string. |
| `JWT_SECRET` | 32+ random characters. Signs tokens. |
| `FRAUDGUARD_SALT` | 32+ random characters. Hashes IPs and emails. |
| `ADMIN_EMAILS` | Comma-separated admin emails. |
| `TRUSTED_PROXY_HOPS` | Proxies in front of the server. |
| `GEMINI_API_KEY`, `ASSEMBLYAI_API_KEY` | As before. |

**Deployment status: not deployed.** The live Hugging Face Space still runs the old code and has no `/v1`. Since the mobile app now needs `/v1`, the app only works against a server running the new code (locally, for now). To deploy: set the secrets above on the Space, run `alembic upgrade head`, then update the Space's code.

The Postgres path has been checked only by generating its SQL; it has not yet run against a real Neon database.

---

## 12. Mobile App Changes

* **App name** is now FraudGuard AI (`app.json` and the home screen). The package ID is still `com.aiza68.FraudGuardExpo` and must be finalised before the first Play upload.
* **[session.js](FraudGuardExpo/src/services/session.js)** and **[api.js](FraudGuardExpo/src/services/api.js)**: token handling and the single `/v1` client. Server error messages (for example a daily limit) are shown to the user.
* **[app/verify-email.tsx](FraudGuardExpo/app/verify-email.tsx)**: opens when an unverified user taps Report. After verifying, the user taps Report again.
* **[app/account.tsx](FraudGuardExpo/app/account.tsx)**: reached from the 👤 icon on the home screen. Shows verified status and deletes the account, the user's reports and the phone's alert history.
* **Removed**: the "this is my number, remove the block" button, which let anyone unblock any number. Removal is admin-only; a user-facing appeal route is not built yet.
* **Removed**: two unused duplicate API files (`constants/api.ts`, `src/services/FraudAPIService.js`).
* **Fixed**: the package lock was out of sync with `package.json`, and web mode crashed on start because the alert-history file was opened at load time.

---

## 13. Pending Work & Change Log

**Pending, and what each item is waiting on:**

| Item | Waiting on |
| :--- | :--- |
| Deploy the new server | Access to the Hugging Face Space, a Neon database, the three secrets |
| Send real email codes | A domain the team owns, Resend and Brevo accounts |
| Kotlin scanner reads the downloaded rules | A development build to test on (needs access to the Expo account) |
| Switch call detection to Android's Call Screening API | A development build to test on |
| Genuine-phone check (Play Integrity) before reports count | A Google Play developer account |
| Remove the legacy open routes | The web app and extension moving to `/v1`, or a decision to retire them |
| User-facing appeal route | A support contact and named admins |
| Onboarding screens that explain each permission | Nothing; not started |
| Privacy policy | Team |
| Final package ID | Team decision |
| iOS app, web dashboard, browser extension | Deferred by the team |

**Change log** (all merged into `dev`):

| Pull request | Summary |
| :--- | :--- |
| #7 `2-Repo_Cleanup` | Removed the unused starter folders and duplicate `data/` and `tests/` folders; stopped tracking `FraudGuardExpo/.env`. |
| #8 `3-Server_Foundations` | `/v1` API, tokens, email codes, database with migrations, limits, admin-only removal, CI. |
| #9 `4-Rules_Sync` | `phone_rules.json`, `GET /v1/rules`, `ETag` change detection, everyday-message test. |
| #10 `5-App_On_V1` | Mobile app on `/v1`: token client, email verification screen, account screen, rename to FraudGuard AI. |
