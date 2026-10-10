"""Ad-hoc scraper: official bank/authority contact pages -> candidate helpline numbers
with surrounding context, so a human (me) can confirm before whitelisting.
Not part of the app; delete after the directory is verified."""
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# 111-xxx-xxx / 021-111-xxx-xxx / +9221-111..., or bare 9/11-digit runs bounded by non-digits
PAT = re.compile(r"(?<!\d)(?:\+?92)?[- ]?(?:0?(?:21|42|51|61|71|81|91))?[- ]?111[- ]?\d{3}[- ]?\d{3}(?!\d)")


def text_of(url):
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=25).read()
    html = raw.decode("utf-8", "replace")
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def probe(name, urls):
    print(f"\n=== {name}")
    for url in urls:
        try:
            txt = text_of(url)
        except Exception as e:
            print(f"  [fail] {url} -> {type(e).__name__} {str(e)[:60]}")
            continue
        hits = {}
        for m in PAT.finditer(txt):
            ctx = txt[max(0, m.start() - 80):m.end() + 40]
            hits.setdefault(m.group().strip(), []).append(ctx.strip())
        if not hits:
            print(f"  [none] {url}")
            continue
        print(f"  [ok] {url}")
        for num, ctxs in sorted(hits.items()):
            print(f"    {num}")
            for c in ctxs[:2]:
                print(f"       ...{c}...")
        return
    print(f"  -> no candidates for {name}")


TARGETS = {
    "Faysal Bank": ["https://faysalbank.com/contact-us/", "https://faysalbank.com/"],
    "Dubai Islamic Bank PK": ["https://www.dibpakistan.com.pk/contact-us/", "https://www.dibpakistan.com.pk/"],
    "Askari Bank": ["https://askari.com/contact-us/", "https://askari.com/"],
    "Habib Metro Bank": ["https://hmb.com.pk/contact-us/", "https://www.hmb.com.pk/"],
    "Soneri Bank": ["https://www.soneribank.com/contact-us", "https://www.soneribank.com/"],
    "First Women Bank": ["https://fwbank.com/contact-us/", "https://fwbank.com/"],
    "Summit Bank": ["https://summitbank.com.pk/contact-us/", "https://summitbank.com.pk/"],
    "KARO Bank": ["https://karobank.com.pk/contact-us/", "https://karobank.com.pk/"],
    "Sindh Bank": ["https://www.sindhbank.gov.pk/contact-us/", "https://www.sindhbank.gov.pk/"],
    "Bank of Khyber": ["https://www.bankofkhyber.com.pk/contact-us/", "https://www.bankofkhyber.com.pk/"],
    "SadaPay": ["https://www.sadapay.pk/contact", "https://www.sadapay.pk/"],
    "Finja": ["https://www.finja.com/contact-us", "https://www.finja.com/"],
    "Pakistan Post": ["https://www.pakistanpost.gov.pk/contact-us/", "https://www.pakistanpost.gov.pk/"],
    "NAB": ["https://www.nab.gov.pk/", "https://www.nab.gov.pk/contact-us"],
    "SECP": ["https://www.secp.gov.pk/contact-us/", "https://www.secp.gov.pk/"],
    "NCCW": ["https://nccw.gov.pk/", "https://ncwc.gov.pk/"],
}

only = set(sys.argv[1:])
for name, urls in TARGETS.items():
    if only and name not in only:
        continue
    probe(name, urls)
