"""The hands: one dedicated tab in a real Chrome, driven with real mouse and keyboard events.

All methods must run on ONE thread (Playwright's sync API); server.py guarantees that.
Page content is untrusted. The agent may only stay on `allowed_hosts`; every action is followed by a host check.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from . import config

_HERE = Path(__file__).parent
COLLECT_JS = (_HERE / "collect.js").read_text(encoding="utf-8")
OVERLAY_JS = (_HERE / "overlay.js").read_text(encoding="utf-8")


class BrowserError(Exception):
    """A problem the agent can read and react to (shown to it as 'ERROR: ...')."""


@dataclass
class View:
    text: str        # numbered element list + page info
    jpeg: bytes      # screenshot with the numbered boxes drawn on it
    path: Path | None


# ---------------------------------------------------------------- finding / starting Chrome
def _user_data_dirs():
    home, local = Path.home(), os.environ.get("LOCALAPPDATA", "")
    if sys.platform == "win32":
        base = Path(local) if local else home / "AppData" / "Local"
        return [base / "Google" / "Chrome" / "User Data", base / "Google" / "Chrome Beta" / "User Data",
                base / "Chromium" / "User Data", base / "BraveSoftware" / "Brave-Browser" / "User Data",
                base / "Microsoft" / "Edge" / "User Data"]
    if sys.platform == "darwin":
        s = home / "Library" / "Application Support"
        return [s / "Google" / "Chrome", s / "Google" / "Chrome Beta", s / "Chromium",
                s / "BraveSoftware" / "Brave-Browser", s / "Microsoft Edge"]
    c = home / ".config"
    return [c / "google-chrome", c / "google-chrome-beta", c / "chromium", c / "BraveSoftware" / "Brave-Browser",
            c / "microsoft-edge"]


def find_chrome(preferred: str = "") -> str:
    if preferred and Path(preferred).exists():
        return preferred
    candidates = []
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            if os.environ.get(env):
                candidates.append(Path(os.environ[env]) / "Google" / "Chrome" / "Application" / "chrome.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        if shutil.which(name):
            candidates.append(Path(shutil.which(name)))
    for c in candidates:
        if Path(c).exists():
            return str(c)
    raise BrowserError("Could not find Chrome. Install it, or set \"chrome_path\" in the config.")


def devtools_endpoint(cfg: dict) -> str:
    """ws endpoint of the user's own running Chrome, read from its DevToolsActivePort file."""
    dirs = [Path(cfg["user_data_dir"])] if cfg["user_data_dir"] else _user_data_dirs()
    for d in dirs:
        f = d / "DevToolsActivePort"
        if f.exists():
            lines = f.read_text(encoding="utf-8", errors="ignore").split()
            if len(lines) >= 2:
                return f"ws://127.0.0.1:{lines[0]}{lines[1]}"
    raise BrowserError(
        "Cannot reach your Chrome. Open Chrome, go to chrome://inspect/#remote-debugging, tick 'Allow remote debugging "
        "for this browser instance' (Chrome 144+), keep Chrome open and try again. Click 'Allow' if Chrome asks. "
        "On an older Chrome, set \"connect\": \"launch\" in the config instead.")


def _port_open(port: int) -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
        return True
    except Exception:  # noqa: BLE001
        return False


def launch_chrome(cfg: dict, url: str = "about:blank") -> str:
    """Start (or reuse) a separate Chrome with its own profile and a debugging port. Returns the http endpoint."""
    port = int(cfg["debug_port"])
    if not _port_open(port):
        Path(cfg["launch_profile"]).mkdir(parents=True, exist_ok=True)
        subprocess.Popen([find_chrome(cfg["chrome_path"]), f"--user-data-dir={cfg['launch_profile']}",
                          f"--remote-debugging-port={port}", "--no-first-run", "--no-default-browser-check",
                          "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if _port_open(port):
                break
            time.sleep(0.5)
        else:
            raise BrowserError("Chrome did not start with its debugging port.")
    return f"http://127.0.0.1:{port}"


# ---------------------------------------------------------------- the browser
class Browser:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.pw = self.browser = self.page = None
        self.info: dict = {"elements": []}
        self.n = 0
        self.dir = config.HOME / "logs" / f"{datetime.now():%Y%m%d_%H%M%S}"

    # ---- connection and tab
    def _opts(self, active=False):
        c = self.cfg
        return {"name": c["agent_name"], "colors": c["colors"], "chrome": bool(c["overlay"]), "active": active}

    def open(self, url: str):
        """Open `url` in a NEW tab (in the background) of the connected Chrome."""
        self._check_url(url)
        from playwright.sync_api import sync_playwright
        self.close()
        mode = self.cfg["connect"]
        if mode == "auto":
            endpoint = devtools_endpoint(self.cfg)
        elif mode == "launch":
            endpoint = launch_chrome(self.cfg)
        else:
            endpoint = mode
        self.pw = sync_playwright().start()
        try:
            self.browser = self.pw.chromium.connect_over_cdp(endpoint, timeout=60_000)
        except Exception as e:  # noqa: BLE001
            self.close()
            raise BrowserError("Chrome did not accept the connection (click 'Allow' in Chrome when it asks): "
                               + str(e).splitlines()[0][:160]) from None
        ctx = self.browser.contexts[0]
        try:
            with ctx.expect_page(timeout=10_000) as pi:     # background tab: do not steal the user's focus
                self.browser.new_browser_cdp_session().send("Target.createTarget",
                                                            {"url": "about:blank", "background": True})
            self.page = pi.value
        except Exception:  # noqa: BLE001
            self.page = ctx.new_page()
        if mode == "launch" and self.cfg["viewport"]:
            self.page.set_viewport_size({"width": self.cfg["viewport"][0], "height": self.cfg["viewport"][1]})
        if self.cfg["focus_tab"] == "always":
            self.page.bring_to_front()
        self.page.add_init_script(f"document.addEventListener('DOMContentLoaded', () => ({OVERLAY_JS})({json.dumps(self._opts(True))}));")
        self.page.goto(url, wait_until="domcontentloaded")
        self._settle()

    def close(self):
        for obj, fn in ((self.page, "close"), (self.pw, "stop")):
            try:
                if obj:
                    getattr(obj, fn)()
            except Exception:  # noqa: BLE001
                pass
        self.pw = self.browser = self.page = None

    def _need_page(self):
        if not self.page:
            raise BrowserError("no tab open: call browser_open(url) first")
        if self.cfg["focus_tab"] == "always":
            try:
                self.page.bring_to_front()
            except Exception:  # noqa: BLE001
                pass

    def _check_url(self, url: str):
        if not config.host_allowed(self.cfg, url):
            host = urlparse(url).hostname or url
            raise BrowserError(f"blocked: {host} is not in allowed_hosts. Ask the user to run: "
                               f"gemini-in-chrome allow {host}")

    def _guard(self):
        """After any action: if the page ended up on a disallowed host, step back and say so."""
        url = self.page.url
        if config.host_allowed(self.cfg, url):
            return
        try:
            self.page.go_back(wait_until="domcontentloaded", timeout=5000)
        except Exception:  # noqa: BLE001
            pass
        if not config.host_allowed(self.cfg, self.page.url):
            self.page.goto("about:blank")
        host = urlparse(url).hostname or url
        raise BrowserError(f"blocked: the page moved to {host}, which is not in allowed_hosts; went back. "
                           f"Ask the user to run: gemini-in-chrome allow {host}")

    def _settle(self, quick: bool = False):
        try:
            self.page.wait_for_load_state("domcontentloaded" if quick else "networkidle", timeout=3000 if quick else 8000)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.5 if quick else 0.9)

    def _inject(self):
        self.page.evaluate(OVERLAY_JS, self._opts(False))

    def say(self, note: str):
        if note and self.page:
            try:
                self._inject()
                self.page.evaluate("t => window.__gic && window.__gic.say(t)", note[:140])
            except Exception:  # noqa: BLE001
                pass

    # ---- looking
    def look(self) -> View:
        self._need_page()
        self._guard()
        self._inject()
        self.info = self.page.evaluate(COLLECT_JS, int(self.cfg["max_elements"]))
        self.page.evaluate("m => window.__gic.mark(m)", self.info["elements"])
        self.page.evaluate("window.__gic.capture(true)")
        try:
            shot = self._screenshot()
        finally:
            self.page.evaluate("window.__gic.capture(false); window.__gic.clearMarks()")
        self._guard()          # the page may have moved while we were capturing: never hand back a blocked page
        path = None
        if self.cfg["save_screenshots"]:
            self.n += 1
            self.dir.mkdir(parents=True, exist_ok=True)
            path = self.dir / f"{self.n:03d}.jpg"
            path.write_bytes(shot)
        i = self.info
        more = ""
        if i["scrollH"] > i["viewH"] + 20:
            pct = round(100 * (i["scrollY"] + i["viewH"]) / i["scrollH"])
            more = f" | scrolled {pct}%" + (" (more below)" if pct < 99 else " (bottom)")
        title = re.sub(r"^✨ .*? working · ", "", i["title"])   # hide our own tab marker from the agent
        lines = [f"PAGE: {title} | {i['url']}{more}"]
        for e in i["elements"]:
            kind = e["role"] or e["type"] or e["tag"]
            flags = f" [{','.join(e['flags'])}]" if e["flags"] else ""
            val = f' value="{e["value"]}"' if e["value"] else ""
            lines.append(f'[{e["i"]}] {kind} "{e["label"]}"{val}{flags}')
        if not i["elements"]:
            lines.append("(no interactive elements visible; try browser_scroll, browser_wait or browser_click_at)")
        return View("\n".join(lines), shot, path)

    def _screenshot(self) -> bytes:
        """Chrome can refuse to paint a background tab; if so, bring it to the front once and retry."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        q = int(self.cfg["screenshot_quality"])
        try:
            return self.page.screenshot(type="jpeg", quality=q, timeout=6000)
        except PlaywrightTimeout:
            self.page.bring_to_front()
            return self.page.screenshot(type="jpeg", quality=q, timeout=20000)

    def read(self, max_chars: int = 6000) -> str:
        """Visible text of the page (good for reading articles and results)."""
        self._need_page()
        self._guard()
        text = self.page.evaluate("() => (document.body ? document.body.innerText : '')")
        text = "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())
        return text[:max_chars] + (f"\n... [{len(text) - max_chars} more characters]" if len(text) > max_chars else "")

    # ---- acting
    def _el(self, n: int) -> dict:
        for e in self.info["elements"]:
            if e["i"] == n:
                return e
        raise BrowserError(f"element [{n}] is not in the latest list; call browser_look and use the new numbers")

    def _click_at(self, x: int, y: int, rect: dict | None = None):
        if self.cfg["overlay"] and rect:
            self.page.evaluate("r => window.__gic && window.__gic.highlight(r)", rect)
            time.sleep(0.3)
        self.page.mouse.move(x, y, steps=14)
        time.sleep(0.15)
        self.page.mouse.down()
        self.page.mouse.up()

    def click(self, n: int) -> str:
        self._need_page()
        e = self._el(n)
        self._click_at(e["x"], e["y"], {"l": e["l"], "t": e["t"], "w": e["w"], "h": e["h"]})
        self._settle(quick=True)
        return f'clicked [{n}] "{e["label"]}"'

    def click_at(self, x: int, y: int) -> str:
        """For things that are not in the element list (canvas, charts, maps)."""
        self._need_page()
        w, h = self.page.evaluate("[innerWidth, innerHeight]")
        if not (0 <= x < w and 0 <= y < h):
            raise BrowserError(f"({x}, {y}) is outside the {w}x{h} viewport")
        self._click_at(x, y)
        self._settle(quick=True)
        return f"clicked at ({x}, {y})"

    def type(self, n: int, text: str, submit: bool = False) -> str:
        self._need_page()
        e = self._el(n)
        self._click_at(e["x"], e["y"], {"l": e["l"], "t": e["t"], "w": e["w"], "h": e["h"]})
        self.page.keyboard.press("Meta+A" if sys.platform == "darwin" else "Control+A")
        self.page.keyboard.press("Backspace")
        self.page.keyboard.insert_text(text)
        time.sleep(0.3)
        if submit:
            self.page.keyboard.press("Enter")
            self._settle(quick=True)
        return f'typed into [{n}] "{e["label"]}"' + (" and pressed Enter" if submit else "")

    def press(self, key: str) -> str:
        self._need_page()
        self.page.keyboard.press(key)
        self._settle(quick=True)
        return f"pressed {key}"

    def scroll(self, direction: str, amount: int = 500) -> str:
        self._need_page()
        w, h = self.page.evaluate("[innerWidth, innerHeight]")
        self.page.mouse.move(w // 2, h // 2, steps=8)
        self.page.mouse.wheel(0, -abs(amount) if direction == "up" else abs(amount))
        time.sleep(0.6)
        return f"scrolled {direction}"

    def back(self) -> str:
        self._need_page()
        self.page.go_back(wait_until="domcontentloaded", timeout=8000)
        self._settle(quick=True)
        return "went back"

    def wait(self, seconds: float) -> str:
        self._need_page()
        time.sleep(min(max(seconds, 1), 30))
        return f"waited {seconds:g}s"

    def upload(self, n: int, path: str) -> str:
        """Click element n (a 'Select files'/'Upload' button) and hand `path` to the native file chooser."""
        self._need_page()
        f = Path(path).expanduser().resolve()
        roots = [Path(d).expanduser().resolve() for d in self.cfg["upload_dirs"]]
        if not roots:
            raise BrowserError('uploads are disabled: set "upload_dirs" in the config to the folders you allow')
        if not any(f == r or r in f.parents for r in roots):
            raise BrowserError(f"{f} is outside the allowed upload_dirs")
        if not f.is_file():
            raise BrowserError(f"{f} does not exist")
        e = self._el(n)
        with self.page.expect_file_chooser(timeout=10_000) as fc:
            self._click_at(e["x"], e["y"], {"l": e["l"], "t": e["t"], "w": e["w"], "h": e["h"]})
        fc.value.set_files(str(f))
        time.sleep(2)
        return f'file chooser opened via [{n}] "{e["label"]}" and {f.name} was handed to the page'
