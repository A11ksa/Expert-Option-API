import asyncio
import json
import os
import re
import time
import base64
import getpass
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

CONFIG_PATH = Path("config.json")
SESSION_PATH = Path("session.json")

def _print(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def _safe_json_dump(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")

def _extract_token_from_payload(payload: str) -> Optional[str]:
    """Try to extract a token from a text payload (JSON or base64-JSON)."""
    # 1) JSON payload
    try:
        obj = json.loads(payload)
        if isinstance(obj, dict):
            tok = obj.get("token")
            if isinstance(tok, str):
                return tok
            msg = obj.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("token"), str):
                return msg["token"]
    except Exception:
        pass

    # 2) base64-encoded JSON payload
    try:
        s = payload.strip()
        if re.fullmatch(r"[A-Za-z0-9_\-+/=]+", s) and len(s) >= 16:
            missing = (-len(s)) % 4
            if missing:
                s += "=" * missing
            decoded = base64.b64decode(s)
            as_text = decoded.decode("utf-8", errors="ignore")
            obj2 = json.loads(as_text)
            if isinstance(obj2, dict):
                tok = obj2.get("token")
                if isinstance(tok, str):
                    return tok
                msg = obj2.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("token"), str):
                    return msg["token"]
            m2 = re.search(r'"token"\s*:\s*"([a-fA-F0-9]{16,})"', as_text)
            if m2:
                return m2.group(1)
    except Exception:
        pass

    # 3) Fallback regex
    m = re.search(r'"token"\s*:\s*"([a-fA-F0-9]{16,})"', payload)
    if m:
        return m.group(1)

    return None

@dataclass
class Credentials:
    email: str
    password: str

class ExpertOptionBot:
    def __init__(self, creds: Credentials, headless: bool = False):
        self.email = creds.email
        self.password = creds.password
        self.headless = headless
        self.ws_url: Optional[str] = None
        self.token: Optional[str] = None

    # persistence
    def save_config(self) -> None:
        """Save login credentials to config.json (email/password ONLY)."""
        _safe_json_dump(CONFIG_PATH, {"email": self.email, "password": self.password})
        _print("Login credentials saved to config.json")

    def save_session(self) -> None:
        """Save ONLY token to session.json."""
        _safe_json_dump(SESSION_PATH, {"token": self.token})
        _print("Session data saved to session.json (token only)")

    # language utilities
    async def _seed_language_preferences(self, context, page) -> None:
        """Ensure English is the preferred locale early."""
        try:
            await context.add_init_script("""() => {
                try {
                  document.documentElement.setAttribute('lang', 'en');
                  localStorage.setItem('NEXT_LOCALE', 'en');
                  localStorage.setItem('language', 'en');
                  localStorage.setItem('locale', 'en');
                  localStorage.setItem('i18nextLng', 'en');
                  document.cookie = 'NEXT_LOCALE=en; path=/; max-age=31536000; SameSite=Lax';
                } catch (e) {}
            }""")
        except Exception:
            pass

        cookies = []
        for domain in ("expertoption.com", "en.expertoption.com"):
            cookies.append({
                "name": "NEXT_LOCALE",
                "value": "en",
                "domain": domain,
                "path": "/",
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax",
            })
        try:
            await context.add_cookies(cookies)
            _print("Seeded NEXT_LOCALE cookies for expertoption.com and en.expertoption.com")
        except Exception as e:
            _print(f"Cookie seeding warning: {e}")

    async def _ensure_next_locale_cookie(self, context, url: str) -> None:
        """Make sure NEXT_LOCALE=en cookie exists for current domain after navigation."""
        try:
            u = urlparse(url)
            domain = u.hostname or "en.expertoption.com"
            await context.add_cookies([{
                "name": "NEXT_LOCALE",
                "value": "en",
                "domain": domain,
                "path": "/",
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax"
            }])
        except Exception:
            pass

    async def _choose_english(self, page) -> None:
        """Handle the language modal (choose English and confirm)."""
        try:
            modal = page.locator("text=Choose your language").first
            await modal.wait_for(state="visible", timeout=5000)
            _print("Language modal detected. Choosing English...")
            await page.get_by_text("English", exact=False).first.click(timeout=5000)
            confirm_btn = page.get_by_role("button", name=re.compile(r"Confirm|OK|Apply", re.I))
            await confirm_btn.click(timeout=5000)
            await modal.wait_for(state="detached", timeout=10000)
            await page.wait_for_timeout(300)
            _print("English selected and confirmed.")
        except PWTimeoutError:
            _print("No language modal appeared (or already closed).")
        except Exception as e:
            _print(f"Language modal warning: {e}. Trying to recover...")
            try:
                await page.keyboard.press("Escape")
                await page.evaluate("""() => { const p = document.querySelector('#portal'); if (p) p.remove(); }""")
            except Exception:
                pass

    # notifications
    async def _grant_notifications(self, context, origin: str) -> None:
        try:
            await context.grant_permissions(["notifications"], origin=origin)
        except Exception:
            pass

    async def _try_click_allow_ui(self, page) -> None:
        candidates = [
            'button:has-text("Allow")',
            'text=/^Allow Notifications?$/i',
            'button:has-text("السماح")',
            'text=/السماح/',
        ]
        for sel in candidates:
            try:
                loc = page.locator(sel)
                if await loc.count():
                    await loc.first.click(timeout=800)
                    _print('Clicked site "Allow" button.')
                    return
            except Exception:
                continue

    # login flow
    async def _fill_login(self, page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await self._choose_english(page)

        email_selectors = [
            'input[name="login"]',
            '#login',
            'input[type="email"]',
            'input[placeholder="Email"]',
            'input[placeholder*="mail" i]',
        ]
        pass_selectors = [
            'input[name="password"]',
            '#password',
            'input[type="password"]',
            'input[placeholder="Password"]',
        ]
        login_btn_selectors = [
            'button[type="submit"]',
            'button:has-text("Log in")',
            'button:has-text("Login")',
            'text=/^Login$/i',
        ]

        # Fill email
        for sel in email_selectors:
            try:
                el = page.locator(sel).first
                await el.wait_for(state="visible", timeout=4000)
                await el.fill(self.email, timeout=4000)
                break
            except Exception:
                continue
        else:
            raise RuntimeError("Could not find email field")

        # Fill password
        for sel in pass_selectors:
            try:
                el = page.locator(sel).first
                await el.wait_for(state="visible", timeout=4000)
                await el.fill(self.password, timeout=4000)
                break
            except Exception:
                continue
        else:
            raise RuntimeError("Could not find password field")

        # Click Login
        for sel in login_btn_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count():
                    await btn.click(timeout=4000)
                    break
            except Exception:
                continue
        else:
            await page.keyboard.press("Enter")

        _print("Submitted login form.")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

    async def _stabilize_language_after_login(self, context, page) -> None:
        await self._ensure_next_locale_cookie(context, page.url)

        try:
            u = urlparse(page.url)
            if u.hostname and not u.hostname.startswith("en.") and "expertoption.com" in u.hostname:
                new_url = f"https://en.expertoption.com{u.path or ''}"
                if u.query:
                    new_url += f"?{u.query}"
                _print(f"Forcing English subdomain: {new_url}")
                await page.goto(new_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            pass

        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                await self._choose_english(page)
            except Exception:
                pass
            await asyncio.sleep(0.5)
        _print("Post-login language stabilization complete.")

    # main
    async def run(self) -> None:
        # Save config (after prompting in main())
        self.save_config()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--ignore-certificate-errors",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                permissions=["notifications"],
                viewport={"width": 1366, "height": 768},
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            # Pre-seed language everywhere
            seed_page = await context.new_page()
            await self._seed_language_preferences(context, seed_page)
            await seed_page.close()

            # Grant notifications
            await self._grant_notifications(context, "https://expertoption.com")
            await self._grant_notifications(context, "https://en.expertoption.com")

            page = await context.new_page()

            # Token-captured event to close immediately
            token_event = asyncio.Event()

            # Capture WebSocket and token
            def on_websocket(ws):
                if not self.ws_url:
                    self.ws_url = ws.url
                    _print(f"WebSocket created: {self.ws_url}")

                async def _handle_payload(payload: str):
                    if self.token:
                        return
                    tok = _extract_token_from_payload(payload)
                    if tok:
                        self.token = tok
                        _print(f"Token captured: {self.token}")
                        # Save token and signal shutdown
                        self.save_session()
                        token_event.set()

                # Wrap sync callbacks to call the async handler
                def _frame_received(payload: str):
                    asyncio.create_task(_handle_payload(payload))

                ws.on("framereceived", _frame_received)
                ws.on("framesent", _frame_received)

            page.on("websocket", on_websocket)

            url = "https://en.expertoption.com/login/"
            _print(f"Navigating to {url} ...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            await self._choose_english(page)
            await self._try_click_allow_ui(page)
            await self._fill_login(page)

            # Wait up to 30s for token, then close immediately
            try:
                await asyncio.wait_for(token_event.wait(), timeout=30)
                _print("Token saved. Closing browser now...")
            except asyncio.TimeoutError:
                _print("Token was not captured within 30s; closing browser anyway.")
            await browser.close()

def prompt_for_credentials(existing_email: str = "", existing_password: str = "") -> Credentials:
    """Always prompt user for email/password.
    If the user presses Enter without input and existing values exist, keep them.
    Otherwise, keep asking until non-empty.
    """
    print("\n=== Enter login credentials (will be saved to config.json) ===")
    # Email
    while True:
        prompt = f"Email [{existing_email}]: " if existing_email else "Email: "
        entered = input(prompt).strip()
        email = entered or existing_email
        if email:
            break
        print("Email cannot be empty. Please try again.")
    # Password (hidden)
    while True:
        pw_prompt = "(input hidden) Password"
        if existing_password:
            pw_prompt += " [press Enter to keep existing]"
        pw_prompt += ": "
        entered_pw = getpass.getpass(pw_prompt)
        password = entered_pw if entered_pw else existing_password
        if password:
            break
        print("Password cannot be empty. Please try again.")
    return Credentials(email=email, password=password)

async def main():
    # Load existing config if any (to show defaults), but ALWAYS prompt
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        existing_email = cfg.get("email", "")
        existing_password = cfg.get("password", "")
    else:
        existing_email = os.environ.get("EO_EMAIL", "")
        existing_password = os.environ.get("EO_PASSWORD", "")
    creds = prompt_for_credentials(existing_email, existing_password)
    bot = ExpertOptionBot(creds, headless=False)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
