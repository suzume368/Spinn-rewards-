"""
╔══════════════════════════════════════════════════════╗
║       PTCL SPIN THE WHEEL — GITHUB ACTION BOT        ║
║       DDOCR Auto Captcha Solver (No Telegram)        ║
╚══════════════════════════════════════════════════════╝
"""

import requests
import time
import os
import sys
from bs4 import BeautifulSoup
from io import BytesIO

# ── DDOCR (Best for captcha) ──
try:
    import ddddocr
    DDOCR_AVAILABLE = True
except ImportError:
    DDOCR_AVAILABLE = False

# ── Tesseract (Fallback) ──
try:
    from PIL import Image, ImageFilter
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# ═══════════════════════════════════════════════════════
#  ⚙️  CONFIG
# ═══════════════════════════════════════════════════════

TARGET_NUMBER = os.environ.get("TARGET_NUMBER", "03347417367")
BASE_URL      = "https://my.ptcl.net.pk"

# Initialize DDOCR once (global)
_ocr_engine = None


def get_ddocr():
    """Lazy-load DDOCR engine"""
    global _ocr_engine
    if _ocr_engine is None and DDOCR_AVAILABLE:
        print("🧠 Loading DDOCR engine...")
        _ocr_engine = ddddocr.DdddOcr(show_ad=False)
    return _ocr_engine


# ═══════════════════════════════════════════════════════
#  🧩 CAPTCHA SOLVERS
# ═══════════════════════════════════════════════════════

def solve_with_dddocr(image_bytes):
    """⭐ PRIMARY: DDOCR — 85-95% accuracy"""
    if not DDOCR_AVAILABLE:
        return None

    try:
        ocr = get_ddocr()
        code = ocr.classification(image_bytes)
        code = "".join(c for c in code if c.isalnum()).upper().strip()

        if 3 <= len(code) <= 8:
            print(f"  ✅ DDOCR: {code}")
            return code
        print(f"  ⚠️  DDOCR invalid length: '{code}'")
        return None
    except Exception as e:
        print(f"  ❌ DDOCR error: {e}")
        return None


def preprocess_for_tesseract(image_bytes):
    """Tesseract ke liye image clean karo"""
    img = Image.open(BytesIO(image_bytes)).convert("L")
    img = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
    img = img.filter(ImageFilter.SHARPEN)
    img = img.point(lambda x: 0 if x < 140 else 255, "1")
    return img


def solve_with_tesseract(image_bytes):
    """FALLBACK: Tesseract OCR"""
    if not TESSERACT_AVAILABLE:
        return None

    try:
        img = preprocess_for_tesseract(image_bytes)
        for psm in [7, 8, 13]:
            text = pytesseract.image_to_string(
                img,
                config=f"--psm {psm} -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            ).strip()
            text = "".join(c for c in text if c.isalnum()).upper()
            if 3 <= len(text) <= 8:
                print(f"  ✅ Tesseract (PSM {psm}): {text}")
                return text
        return None
    except Exception as e:
        print(f"  ❌ Tesseract error: {e}")
        return None


def solve_captcha(image_bytes, attempt=1):
    """DDOCR → Tesseract fallback"""
    print(f"\n🧩 Solving captcha (attempt {attempt})...")

    code = solve_with_dddocr(image_bytes)
    if code:
        return code

    code = solve_with_tesseract(image_bytes)
    if code:
        return code

    return None


# ═══════════════════════════════════════════════════════
#  🎡 MAIN BOT
# ═══════════════════════════════════════════════════════

class PTCLSpinBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def get_tokens(self):
        print("\n📥 Loading PTCL page...")
        r = self.session.get(f"{BASE_URL}/SpinTheWheel/Default.aspx", timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        tokens = {}
        for field in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
            tag = soup.find("input", {"name": field})
            tokens[field] = tag["value"] if tag else ""

        hidden = soup.find_all("input", {"type": "hidden"})
        for h in hidden:
            name = h.get("name", "")
            if name.startswith("__") and name not in tokens:
                tokens[name] = h.get("value", "")

        print(f"  ✅ Tokens loaded: {list(tokens.keys())}")
        return tokens

    def get_captcha(self):
        print("\n📸 Downloading captcha...")
        url = f"{BASE_URL}/SpinTheWheel/Captcha.aspx?{int(time.time() * 1000)}"
        r = self.session.get(url, timeout=30)
        r.raise_for_status()

        with open("captcha.png", "wb") as f:
            f.write(r.content)
        print(f"  ✅ Captcha: {len(r.content)} bytes")
        return r.content

    def submit_form(self, tokens, captcha_code):
        print(f"\n📤 Submitting captcha: {captcha_code}")
        data = {
            "__VIEWSTATE": tokens.get("__VIEWSTATE", ""),
            "__VIEWSTATEGENERATOR": tokens.get("__VIEWSTATEGENERATOR", ""),
            "__EVENTVALIDATION": tokens.get("__EVENTVALIDATION", ""),
            "txtMobile": TARGET_NUMBER,
            "txtCaptcha": captcha_code,
            "chkTerms": "on",
            "btnNext": "Start Game",
        }
        r = self.session.post(
            f"{BASE_URL}/SpinTheWheel/Default.aspx",
            data=data, timeout=30, allow_redirects=True
        )
        print(f"  Status: {r.status_code} | URL: {r.url}")

        if "SpinWheel.aspx" in r.url:
            print("  ✅ Login success!")
            return True
        return False

    def spin(self):
        print("\n🎡 Spinning the wheel...")
        endpoints = [
            f"{BASE_URL}/SpinTheWheel/SpinWheel.aspx/SpinWheels",
            f"{BASE_URL}/SpinTheWheel/SpinWheel.aspx/Spin",
        ]
        for url in endpoints:
            try:
                r = self.session.post(
                    url, json={},
                    headers={
                        "Content-Type": "application/json; charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": f"{BASE_URL}/SpinTheWheel/SpinWheel.aspx",
                    },
                    timeout=30
                )
                print(f"  {url.split('/')[-1]} → {r.status_code}")
                if r.status_code == 200:
                    result = r.json()
                    d = result.get("d", result)
                    if isinstance(d, dict):
                        reward = d.get("reward") or d.get("Reward") or d.get("message")
                    else:
                        reward = d
                    print(f"  🎉 REWARD: {reward}")
                    return reward
            except Exception as e:
                print(f"  Error: {e}")
        return None

    def run(self):
        print("=" * 55)
        print(f"  🚀 PTCL Spin Bot — {TARGET_NUMBER}")
        print("=" * 55)

        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                tokens = self.get_tokens()
                image_bytes = self.get_captcha()

                code = solve_captcha(image_bytes, attempt)
                if not code:
                    print(f"  ❌ Attempt {attempt}: no code")
                    time.sleep(3)
                    continue

                if self.submit_form(tokens, code):
                    reward = self.spin()
                    if reward:
                        print(f"\n🎉 SUCCESS! Reward: {reward}")
                        return True
                    print("⚠️ Login OK but spin failed")
                    return False
                else:
                    print(f"  ❌ Attempt {attempt}: wrong captcha or already used")
                    time.sleep(3)

            except Exception as e:
                print(f"  ❌ Attempt {attempt} error: {e}")
                time.sleep(5)

        print(f"\n❌ Failed after {max_attempts} attempts")
        return False


# ═══════════════════════════════════════════════════════
#  🚀 ENTRY
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    if not DDOCR_AVAILABLE and not TESSERACT_AVAILABLE:
        print("❌ No captcha solver available!")
        sys.exit(1)

    print(f"  DDOCR: {'✅' if DDOCR_AVAILABLE else '❌'}  "
          f"Tesseract: {'✅' if TESSERACT_AVAILABLE else '❌'}")

    bot = PTCLSpinBot()
    success = bot.run()
    sys.exit(0 if success else 1)
