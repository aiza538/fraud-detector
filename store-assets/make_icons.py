"""FraudGuard AI icons: SVG design -> exact-size PNGs via headless Edge (Windows).

Regenerates the app icons in FraudGuardExpo/assets/images/ and the Play Store
assets in store-assets/. Edit the colours or shapes below, then run from the
repo root:
    python store-assets/make_icons.py .
"""
import os
import subprocess
import sys

REPO = sys.argv[1]
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon_work")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
os.makedirs(WORK, exist_ok=True)

NAVY, BLUE, GREEN = "#1e3a8a", "#2563eb", "#22c55e"
SHIELD = "M50 8 L84 20 V46 C84 68 69 84 50 92 C31 84 16 68 16 46 V20 Z"
CHECK = "M34 50 L46 62 L67 38"

DEFS = f"""
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{BLUE}"/>
    <stop offset="1" stop-color="{NAVY}"/>
  </linearGradient>
  <linearGradient id="shieldBlue" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{BLUE}"/>
    <stop offset="1" stop-color="{NAVY}"/>
  </linearGradient>
  <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
    <feDropShadow dx="0" dy="1.6" stdDeviation="1.8" flood-color="#0b1f4d" flood-opacity="0.45"/>
  </filter>
  <mask id="cut">
    <rect width="100" height="100" fill="black"/>
    <path d="{SHIELD}" fill="white"/>
    <path d="{CHECK}" fill="none" stroke="black" stroke-width="8.5" stroke-linecap="round" stroke-linejoin="round"/>
  </mask>
</defs>"""


def white_shield(scale, with_shadow=True):
    """White shield with a blue check and a small green 'AI spark'."""
    flt = ' filter="url(#shadow)"' if with_shadow else ""
    return f"""
<g transform="translate(50 50) scale({scale}) translate(-50 -50)">
  <path d="{SHIELD}" fill="#ffffff"{flt}/>
  <path d="{CHECK}" fill="none" stroke="{BLUE}" stroke-width="8.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="74" cy="29" r="4.6" fill="{GREEN}"/>
</g>"""


def blue_shield(scale):
    """Blue shield with a white check (for light/dark splash backgrounds)."""
    return f"""
<g transform="translate(50 50) scale({scale}) translate(-50 -50)">
  <path d="{SHIELD}" fill="url(#shieldBlue)"/>
  <path d="{CHECK}" fill="none" stroke="#ffffff" stroke-width="8.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="74" cy="29" r="4.6" fill="{GREEN}"/>
</g>"""


BG_RECT = '<rect width="100" height="100" fill="url(#bg)"/>'

ASSETS = {
    # Full square icon (Expo `icon`, Play Store icon base). Google/Android apply their own mask.
    "icon.png": (1024, 1024, BG_RECT + white_shield(0.78)),
    # Adaptive icon: foreground must stay inside the centre ~66% safe zone.
    "android-icon-foreground.png": (512, 512, white_shield(0.56)),
    "android-icon-background.png": (512, 512, BG_RECT),
    # Monochrome (themed icons): one colour, Android tints it. Check is cut out.
    "android-icon-monochrome.png": (432, 432,
        '<g transform="translate(50 50) scale(0.56) translate(-50 -50)">'
        '<rect width="100" height="100" fill="#ffffff" mask="url(#cut)"/></g>'),
    "splash-icon.png": (1024, 1024, blue_shield(0.9)),
    "favicon.png": (48, 48, '<rect width="100" height="100" rx="22" fill="url(#bg)"/>' + white_shield(0.84, False)),
}

STORE = {
    # Play Console hi-res icon: 512x512, full square, no transparency.
    "play-store-icon-512.png": (512, 512, BG_RECT + white_shield(0.78)),
}

FEATURE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1024px;height:500px;overflow:hidden;font-family:'Segoe UI',Arial,sans-serif}
.wrap{width:1024px;height:500px;background:linear-gradient(135deg,#2563eb,#1e3a8a);display:flex;align-items:center;gap:56px;padding:0 80px;box-sizing:border-box;color:#fff}
svg{width:260px;height:260px;flex:none}
h1{font-size:72px;margin:0 0 10px 0;font-weight:800;letter-spacing:-1px}
h1 span{color:#4ade80}
p{font-size:30px;margin:0;line-height:1.35;color:#dbeafe}
</style></head><body><div class="wrap">
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">%s%s</svg>
<div><h1>FraudGuard <span>AI</span></h1><p>Warns you about scam calls<br>and scam messages — on your phone.</p></div>
</div></body></html>""" % (DEFS, white_shield(0.95))


def render(html, width, height, out):
    page = os.path.join(WORK, os.path.basename(out) + ".html")
    with open(page, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--default-background-color=00000000",
                    f"--window-size={width},{height}", f"--user-data-dir={WORK}\\profile",
                    f"--screenshot={out}", "file:///" + page.replace("\\", "/")],
                   check=True, capture_output=True)
    print(f"{out}  ({width}x{height})")


def svg_page(width, height, body):
    return (f"<!doctype html><html><head><style>html,body{{margin:0;background:transparent;overflow:hidden}}"
            f"svg{{display:block}}</style></head><body>"
            f'<svg width="{width}" height="{height}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
            f"{DEFS}{body}</svg></body></html>")


images = os.path.join(REPO, "FraudGuardExpo", "assets", "images")
for name, (w, h, body) in ASSETS.items():
    render(svg_page(w, h, body), w, h, os.path.join(images, name))

store = os.path.join(REPO, "store-assets")
os.makedirs(store, exist_ok=True)
for name, (w, h, body) in STORE.items():
    render(svg_page(w, h, body), w, h, os.path.join(store, name))
render(FEATURE, 1024, 500, os.path.join(store, "play-feature-graphic-1024x500.png"))
