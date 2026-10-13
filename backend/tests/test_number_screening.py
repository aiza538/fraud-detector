"""
Number screening tests — false-positive control ki regression suite.

Ye file ka maqsad features test karna nahi, balki REGRESSIONS rokna hai.
Har test case ek wo shikayat hai jo real users ne di thi:
  "unknown number par scam/suspicious lag jata hai"
  "groups aur channels par bekaar alerts aate hain"

Run: python -m pytest backend/tests/ -v      (backend/ directory se)
      ya: python backend/tests/test_number_screening.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from number_screening import (
    DIRECTORY,
    REPORTS_NEEDED_FOR_CONSENSUS,
    check_number,
    clean_number,
    impersonates,
    number_lists,
    report_number,
    unreport_number,
)


# --- Normalization ---------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("0300-1234567", "3001234567"),
    ("+92 300 1234567", "3001234567"),
    ("0092-300-1234567", "3001234567"),
    ("111-111-425", "111111425"),
    # Area-code wale format — bank inhi ko advertise karte hain
    ("051-111-111-425", "111111425"),
    ("(051) 111-111-425", "111111425"),
    ("021-111-825-888", "111825888"),
    # Short UAN: leading zero EK hi hatna chahie
    ("0800-55055", "80055055"),
    ("111-124-444", "111124444"),
])
def test_clean_number(raw, expected):
    assert clean_number(raw) == expected


# --- REGRESSION #1: unknown number par alert nahi ----------------------------
#
# Pehle: unknown personal mobile → "suspicious". Ab: UNKNOWN, aur UNKNOWN
# par koi alert/notification nahi (NumberRules.shouldAlert sirf SCAM +
# SUSPICIOUS true karta hai).

@pytest.mark.parametrize("number", [
    "0300-1234567",   # Jazz personal mobile
    "0345-1234567",   # Zong
    "0311-1234567",   # Warid
    "0333-1234567",   # Telenor
    "0321-2222222",   # Ufone
    "0302-1234567",   # delivery rider
    "+92 300 1234567",
    "0300-5551234",   # koi bhi normal mobile
])
def test_personal_numbers_are_unknown_not_alerted(number):
    result = check_number(number)
    assert result["status"] == "unknown", (
        f"{number} -> {result['status']}. Personal numbers UNKNOWN hone chahiye, "
        "suspicious nahi — warna har dost/delivery rider par alert aayega."
    )


# --- REGRESSION #2: REAL bank helpline suspicious nahi ------------------------
#
# Ye sabse bara bug tha: legit list empty hone ki wajah se HBL ka apna
# number "unknown 111 UAN" → SUSPICIOUS ho jata tha.

@pytest.mark.parametrize("number,entity", [
    ("111-111-425", "HBL"),
    ("111-825-888", "UBL"),
    ("051-111-000-622", "MCB Bank"),
    ("111-124-444", "JazzCash"),
    ("111-003-737", "Easypaisa"),
    ("0800-55055", "PTA / PTCL"),
    ("0800-111-111", "NADRA"),
    ("1991", "FIA Cyber Crime Wing"),
    ("9911", "K-Electric"),
])
def test_verified_helplines_are_safe(number, entity):
    result = check_number(number)
    assert result["status"] == "safe", (
        f"{number} ({entity}) -> {result['status']}. Bank/govt ka apna helpline "
        "SCAM ya SUSPICIOUS nahi ho sakta."
    )
    assert result["entity"] == entity


def test_every_verified_number_resolves_safe():
    """Directory ka koi bhi number kabhi suspicious/scam na ho."""
    for number in DIRECTORY:
        assert check_number(number)["status"] == "safe", f"{number} galat verdict"


# --- REGRESSION #3: impersonation (copy-cat spoofing) ----------------------

@pytest.mark.parametrize("number", [
    "111-111-424",   # HBL, 1 digit alag
    "111111434",     # HBL, 2 digit alag
    "111-825-889",   # UBL, 1 digit alag
])
def test_copy_cat_spoof_is_scam(number):
    assert check_number(number)["status"] == "scam"


def test_impersonation_does_not_flag_real_numbers():
    """Do legit banks ke darmiyan 1-2 digit ka farq hone par bhi koi
    legit number SCAM na ho — ye impersonation detector ka sab se khatarna
    failure mode hai."""
    for number in DIRECTORY:
        assert not impersonates(number), f"{number} khud impersonate ho gaya"


def test_unrelated_number_not_impersonation():
    # 0300-1234567 aur 111111425 bilkul alag hain
    assert not impersonates("3001234567")


# --- UAN heuristic ---------------------------------------------------------

def test_unknown_uan_is_amber_not_red():
    # 111999999 verified list me nahi, magar UAN shape hai
    result = check_number("111-999-999")
    assert result["status"] == "suspicious"
    assert result["confidence"] == "medium"


def test_short_random_number_unknown():
    assert check_number("555")["status"] == "unknown"
    assert check_number("123")["status"] == "unknown"


# --- Saved contacts --------------------------------------------------------

def test_saved_contact_is_safe():
    """Bina `saved_contact` flag ke har dost 'unknown' lagta hai aur phir
    community report ka button aa jata hai."""
    assert check_number("03001234567", is_saved_contact=True)["status"] == "safe"
    assert check_number("03001234567", is_saved_contact=False)["status"] == "unknown"


# --- Community reporting / consensus ---------------------------------------

def test_report_requires_consensus():
    number = "03009876543"
    for i in range(1, REPORTS_NEEDED_FOR_CONSENSUS):
        result = report_number(number, reporter=f"device-{i}")
        assert result["status"] == "pending"
        assert result["report_count"] == i

    # Check number block hone se PEHLE
    assert check_number(number)["status"] == "unknown"

    final = report_number(number, reporter=f"device-{REPORTS_NEEDED_FOR_CONSENSUS}")
    assert final["status"] == "confirmed"
    assert check_number(number)["status"] == "scam"


def test_same_device_cannot_reach_consensus():
    """REGRESSION: aik banda 5 baar tap kar ke number block na kar sake.
    Pehle timestamp-dedupe Windows ki 15ms clock resolution ki wajah se
    chalta hi nahi tha."""
    number = "03005556677"
    for _ in range(20):
        result = report_number(number, reporter="device-same")
    assert result["status"] == "pending"
    assert result["report_count"] == 1
    assert check_number(number)["status"] == "unknown"


def test_report_on_verified_number_rejected():
    result = report_number("111-111-425", reporter="device-x")
    assert result["status"] == "error"
    assert "official number" in result["message"]


def test_appeal_clears_block():
    number = "03001112223"
    for i in range(REPORTS_NEEDED_FOR_CONSENSUS):
        report_number(number, reporter=f"dev-{i}")
    assert check_number(number)["status"] == "scam"

    unreport_number(number)
    assert check_number(number)["status"] == "unknown"


def test_appeal_on_unknown_number_is_noop():
    result = unreport_number("03007778888")
    assert result["status"] == "unknown"


# --- /number-lists contract (mobile syncRules ka source) -------------------

def test_number_lists_payload_contract():
    """Mobile ka `syncRules()` isi payload par depend karta hai."""
    data = number_lists()
    for key in ("legitimate", "scam", "spoofable", "directory"):
        assert key in data, f"/number-lists me '{key}' missing"

    assert len(data["legitimate"]) > 5, "legit list khali/bohat choti hai"
    assert data["directory"], "directory map khali hai"

    # Na directory ke number, na legit list me, sab normalize hue hue form me
    # hone chahiye (mobile `cleanNumber()` se match karta hai).
    for number in data["directory"]:
        assert number == clean_number(number), f"{number} normalize nahi hai"


def test_scam_list_never_contains_verified_numbers():
    """Chahe kitni bhi community reports aa jayein, koi VERIFIED number
    scam list me kabhi nahi ja sakta — warna HBL ka apna number community
    block ho jayega.

    (Ye test pehle "fresh backend pe scam list khali hai" check karta tha,
    magar woh test-order par depend karta tha — doosre test ne consensus
    poora karke list bhar di thi. Ab ye state-independent hai.)"""
    scam = number_lists()["scam"]
    assert not set(scam) & set(DIRECTORY.keys()), (
        f"Verified numbers scam list me aa gaye: {set(scam) & set(DIRECTORY.keys())}"
    )