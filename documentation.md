# FraudGuard: Multi-Region Threat Directory & Pattern Matching Documentation

This document records the architectural improvements, schema specifications, dataset verifications, and rule-engine expansions implemented in the FraudGuard repository.

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

Both [data/official_directory.json](file:///c:/Fraud-Guard/fraud-detector/data/official_directory.json) and [backend/data/official_directory.json](file:///c:/Fraud-Guard/fraud-detector/backend/data/official_directory.json) are kept strictly identical.

---

## 2. Directory Schema Specification

Defined in [data/official_directory.schema.json](file:///c:/Fraud-Guard/fraud-detector/data/official_directory.schema.json) adhering to JSON Schema Draft-07.

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
* **`numbers`** *(array of strings)*: Combined array of callable numbers and shortcodes (consumed directly by [backend/main.py](file:///c:/Fraud-Guard/fraud-detector/backend/main.py) for Levenshtein spoof detection and whitelist validation).
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

### 4.1. Pattern Database (`data/scam_patterns.json`)

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

1. **Online Dynamic Analysis**:
   - The Expo client calls `POST /check-number` in [backend/main.py](file:///c:/Fraud-Guard/fraud-detector/backend/main.py#L433).
   - The backend screens numbers against `ALL_LEGITIMATE` (canonical and area-prefixed UANs across all loaded regions) and detects Levenshtein spoofs (distance $\le 2$).
2. **Offline Local Caller ID & Native Android Screening**:
   - The client invokes `GET /number-lists` on the backend (see [FraudGuardExpo/src/services/CallerIDService.js](file:///c:/Fraud-Guard/fraud-detector/FraudGuardExpo/src/services/CallerIDService.js)).
   - The backend pushes down verified numbers (`directory`), confirmed community scam numbers (`scam`), and near-neighbor spoof targets (`spoofable`).
   - The app delegates these rules to the Android native Kotlin module ([CallGuardModule.kt](file:///c:/Fraud-Guard/fraud-detector/FraudGuardExpo/modules/expo-call-guard/android/src/main/java/expo/modules/callguard/CallGuardModule.kt) -> `NumberRules.kt`), allowing native on-device call interception without internet connectivity.

---

## 6. Verification & Test Coverage

All automated test suites pass without regressions:
* **Detection Accuracy & Whitelist Integrity Suite** ([tests/test_detection_accuracy.py](file:///c:/Fraud-Guard/fraud-detector/tests/test_detection_accuracy.py)):
  - **Scam Detection Rate**: **100.00%** (18/18 detected, target: >95.0%).
  - **False Positive Rate**: **0.00%** (0/12 triggered across legitimate Pakistani bank OTPs and Global 2FA codes).
  - **Caller ID / Levenshtein Precision**: **100.00%** (9/9 correct across `OFFICIAL_VERIFIED`, `SPOOF_SUSPECT`, and `UNVERIFIED`).
  - **Multi-Region Loader Validation**: Root region parsing (`PK` and `GLOBAL`) verified for both [data/scam_patterns.json](file:///c:/Fraud-Guard/fraud-detector/data/scam_patterns.json) and [data/official_directory.json](file:///c:/Fraud-Guard/fraud-detector/data/official_directory.json).
* **Caller ID Screening Tests** (22 test cases): Area-code prefixed UANs, bare UANs, shortcodes (`1991`, `8171`, `1700`, `1777`, `1717`), toll-free lines, Levenshtein spoof detections (HBL, Meezan), consensus threshold handling, and personal mobile pass-throughs pass 100%.
* **Pattern Matching Tests** (46 test cases): Validated that normal conversation messages, legitimate bank OTP SMS alerts, and telecom recharge receipts remain silent, while domestic Pakistani scams (Roman Urdu & Urdu script) and global cross-border threats (Crypto drainers, DHL/FedEx holds, Apple ID lockouts) are reliably flagged with statutory PECA citations.
* **Group Chat & Context Screening Tests** (16 test cases): Group link suppression and 1:1 threat identification verified.
