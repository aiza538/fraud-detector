# /check-number ka 4-level flow — chalane ke liye:
#   python -m tests.test_number_screening   (backend/ directory se)
#
# Ye test tab banaya jab EVERY unknown number "suspicious, high confidence"
# aa raha tha. Pakistan me 300-999 POORE Jazz/Zong/Tenor/Ufone ka personal
# mobile range hai, is liye wo heuristic har dost, har delivery rider, har
# hospital ko alert kar rahi thi.
#
# Rule: "unknown" ka matlab "pata nahi" hai — scam ya suspicious NAHI.
# `main` ko `backend` alias se import karo — test file ka apna `main()` function
# hai, jo module-level `main` ko shadow kar deta tha.
import main as backend
from main import (app, REPORTED_SCAM_NUMBERS, REPORT_THRESHOLD, REPORT_DECAY_DAYS,
                  _save_reported)

# Consensus DB ka test data. Ye numbers kisi ASLI number ke nahi hain — test
# har baar apna data set karta hai aur baad me hata deta hai, taake real
# reported_numbers.json ko haath na lagaye.
CONSENSUS_CONFIRMED = "3335551122"   # REPORT_THRESHOLD reports
CONSENSUS_PENDING = "3222233344"     # sirf 2 reports
_ORIGINAL_REPORTED = list(REPORTED_SCAM_NUMBERS)


def _now():
    return int(backend.time.time())


def _reports_for(number, count, start=0):
    """`count` alag reporters ke votes — ek per reporter (asli rule).

    Timestamps ABHI ke hain — decay (180 din) inhe expire kar deti hai, to
    purane timestamps se test kiye gaye votes count hi nahi hote.
    """
    base = _now() - 60
    return [
        {"reporter": f"test-reporter-{i}", "at": base + i + start, "note": "unit-test"}
        for i in range(count)
    ]


def _seed_confirmed():
    now = _now()
    REPORTED_SCAM_NUMBERS[:] = [
        {"number": CONSENSUS_CONFIRMED,
         "reports": _reports_for(CONSENSUS_CONFIRMED, REPORT_THRESHOLD),
         "source": "community", "first_seen": now, "last_seen": now},
        {"number": CONSENSUS_PENDING,
         "reports": _reports_for(CONSENSUS_PENDING, 2),
         "source": "community", "first_seen": now, "last_seen": now},
    ]


# (label, payload, expected_status)
CASES = [
    # --- Verified official numbers (short codes bhi) ---
    ("area-prefixed HBL UAN", {"number": "021-111-111-425"}, "safe"),
    ("HBL UAN with +92", {"number": "+9221111111425"}, "safe"),
    ("bare HBL UAN", {"number": "111-111-425"}, "safe"),
    ("PTA toll-free", {"number": "0800-55055"}, "safe"),
    ("BISP toll-free", {"number": "0800-26477"}, "safe"),
    ("NADRA short code", {"number": "1700"}, "safe"),
    ("FIA short code", {"number": "1717"}, "safe"),
    ("FIA cyber crime 1991", {"number": "1991"}, "safe"),

    # --- Impersonation: verified UAN ka 1-2 digit door ka number ---
    ("HBL spoof (+2)", {"number": "111-111-427"}, "scam"),
    ("Meezan spoof", {"number": "111-331-333"}, "scam"),

    # --- Personal mobiles: UNKNOWN, kabhi suspicious nahi ---
    ("Jazz mobile", {"number": "0300-1234567"}, "unknown"),
    ("Zong mobile", {"number": "03451234567"}, "unknown"),
    ("Telenor mobile", {"number": "03211234567"}, "unknown"),
    ("Ufone mobile", {"number": "03331234567"}, "unknown"),
    ("landline", {"number": "051-1234567"}, "unknown"),
    ("telco short code", {"number": "310"}, "unknown"),

    # --- Genuine suspicious signal: 111 UAN jo verified list me nahi ---
    ("unknown UAN", {"number": "111-999-999"}, "suspicious"),

    # --- Saved contact ---
    ("saved friend", {"number": "03001234567", "saved_contact": True}, "safe"),
    # Reported scam pehle aata hai — saved hone par bhi scam.
    # Ye number consensus DB me confirmed hai (5 distinct reports) — setup
    # ne `_seed_confirmed` se vote daala hai.
    ("saved but reported", {"number": "3335551122", "saved_contact": True}, "scam"),

    # --- Consensus DB: threshold ke neeche = scam NAHI ---
    # Ek/two reports par number block nahi hota — pehle yahi ek report
    # number ko permanent block bana deti thi.
    ("2 reports — pending", {"number": "3222233344", "saved_contact": True}, "safe"),

    # --- Garbage input ---
    ("letters only", {"number": "abc"}, "unknown"),
    ("empty", {"number": ""}, "unknown"),
]


def _check_consensus_behaviour(client, failed):
    """Consensus DB ke naye rules — ye pehle koi test nahi cover karta tha.

    Pehle `report-number` number ko turant permanent block kar deta tha. Ab:
      - 1 report            -> "pending", koi alert nahi
      - REPORT_THRESHOLD    -> "confirmed", number scam
      - verified official   -> report reject
      - /unreport-number    -> block hata deta hai
      - ek reporter         -> do baar report karke threshold cross nahi kar sakta
    """
    fresh = "3099988877"

    r1 = client.post("/report-number", json={"number": fresh})
    body1 = r1.get_json()
    if body1.get("status") != "pending":
        failed.append(f"consensus: 1st report should be pending, got {body1.get('status')}")
    if body1.get("reports_needed") != REPORT_THRESHOLD:
        failed.append("consensus: reports_needed missing from response")

    # Ek hi IP do baar report kare — vote double-count nahi hona chahiye.
    client.post("/report-number", json={"number": fresh})
    count = len(backend._active_reports(
        next(e for e in REPORTED_SCAM_NUMBERS if e.get("number") == fresh)))
    if count != 1:
        failed.append(f"consensus: same reporter double-counted ({count} votes)")

    # Threshold cross karne wale alag reporters add karo (rate limit se bachne
    # ke liye seed, HTTP calls ke bajaye).
    entry = next(e for e in REPORTED_SCAM_NUMBERS if e.get("number") == fresh)
    entry["reports"] = _reports_for(fresh, REPORT_THRESHOLD, start=100)
    if fresh not in backend.reported_numbers():
        failed.append("consensus: threshold met but number not in scam list")

    # /number-lists sirf confirmed numbers push kare — native rules isi par
    # build hote hain, warna pending numbers bhi sab ke phones par alert karte.
    lists = client.get("/number-lists").get_json()
    if fresh not in lists.get("scam", []):
        failed.append("consensus: confirmed number missing from /number-lists scam")
    if fresh in lists.get("pending", []):
        failed.append("consensus: confirmed number still listed as pending")
    if CONSENSUS_PENDING in lists.get("scam", []):
        failed.append("consensus: 2-report number leaked into scam list")
    if CONSENSUS_PENDING not in lists.get("pending", []):
        failed.append("consensus: 2-report number missing from pending list")

    # Appeal path — number owner block hatwa sakta hai.
    up = client.post("/unreport-number", json={"number": fresh})
    if up.status_code != 200:
        failed.append(f"consensus: unreport failed ({up.status_code})")
    if fresh in backend.reported_numbers():
        failed.append("consensus: number still scam after unreport")

    # Jo blocklist me nahi, uska unreport 404 — galat number "ho gaya" nahi batana
    miss = client.post("/unreport-number", json={"number": "03001234567"})
    if miss.status_code != 404:
        failed.append(f"consensus: unreport of clean number should 404 ({miss.status_code})")


def _check_decay(client, failed):
    """Purane reports expire hone chahiye — warna ek saal purana block zinda
    rehta hai aur SIM change ke baad bhi number block rahta hai."""
    stale = "3055566677"
    now = int(backend.time.time())
    entry = {
        "number": stale,
        # REPORT_DECAY_DAYS se zyada purane
        "reports": [{"reporter": f"old-{i}",
                     "at": now - (REPORT_DECAY_DAYS + 30) * 86400}
                    for i in range(REPORT_THRESHOLD + 3)],
        "source": "community", "first_seen": now, "last_seen": now,
    }
    REPORTED_SCAM_NUMBERS.append(entry)
    if len(backend._active_reports(entry)) != 0:
        failed.append("decay: expired reports still counted")
    if stale in backend.reported_numbers():
        failed.append("decay: expired entry still in scam list")
    REPORTED_SCAM_NUMBERS.remove(entry)


def main():
    _seed_confirmed()
    client = app.test_client()
    failed = []
    try:
        for label, payload, expected in CASES:
            resp = client.post("/check-number", json=payload)
            got = resp.get_json().get("status")
            if got != expected:
                failed.append(f"expected {expected}, got {got}\n  case: {label}")

        # Provenance: scam verdict me report count + source aana chahie, warna
        # user ko "community reported" claim par bharosa nahi hoga.
        sc = client.post("/check-number", json={"number": CONSENSUS_CONFIRMED}).get_json()
        if sc.get("report_count") != REPORT_THRESHOLD:
            failed.append("provenance: report_count missing/incorrect in /check-number")
        if sc.get("source") != "community":
            failed.append("provenance: source missing in /check-number")

        # /number-lists me spoofable list bhi honi chahiye, warna native offline
        # impersonation detect hi nahi kar pata.
        lists = client.get("/number-lists").get_json()
        if not lists.get("spoofable"):
            failed.append("/number-lists: spoofable list missing")
        if "111111425" not in [str(x) for x in lists.get("legitimate", [])]:
            failed.append("/number-lists: HBL UAN missing from legitimate")
        if lists.get("threshold") != REPORT_THRESHOLD:
            failed.append("/number-lists: threshold not exposed to client")

        # Verified number ko report nahi kar sakte
        r = client.post("/report-number", json={"number": "111-111-425"})
        if r.status_code != 400:
            failed.append(f"report-number: verified number accepted ({r.status_code})")

        _check_consensus_behaviour(client, failed)
        _check_decay(client, failed)
    finally:
        REPORTED_SCAM_NUMBERS[:] = _ORIGINAL_REPORTED
        _save_reported(REPORTED_SCAM_NUMBERS)

    if failed:
        raise SystemExit("FAIL:\n" + "\n".join(failed))
    print(f"OK - {len(CASES)} screening cases + consensus/decay/provenance, "
          "unknown = no alert, sirf scam/suspicious alert deta hai")


if __name__ == "__main__":
    main()