"""Configuration: one JSON file (default ~/.gemini-in-chrome/config.json) merged over safe defaults."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

HOME = Path(os.environ.get("GEMINI_IN_CHROME_HOME", Path.home() / ".gemini-in-chrome"))

DEFAULTS = {
    # "auto"   = attach to YOUR running Chrome (turn on chrome://inspect/#remote-debugging, Chrome 144+)
    # "launch" = start a separate Chrome with its own profile (works with any Chrome; sign in once)
    # "http://127.0.0.1:9222" = attach to a Chrome you started with --remote-debugging-port
    "connect": "auto",
    "user_data_dir": "",                       # auto mode: override where Chrome keeps DevToolsActivePort
    "chrome_path": "",                         # launch mode: empty = auto-detect
    "launch_profile": str(HOME / "profile"),
    "debug_port": 9222,                        # launch mode
    "viewport": [1280, 800],                   # launch mode only; null = real window size (your own Chrome always keeps its size)
    # The agent can only open and stay on these sites (a host also matches its subdomains). "*" = anything.
    "allowed_hosts": ["example.com", "wikipedia.org", "github.com", "google.com", "youtube.com", "duckduckgo.com"],
    "allow_file_urls": False,
    # browser_upload may only send files from inside these folders
    "upload_dirs": [],
    "focus_tab": "never",                      # "never" = work in a background tab, "always" = pull it to the front
    "agent_name": "Gemini",                    # text on the cursor, badge and tab title
    "colors": ["#4285f4", "#9b72f2", "#f06292", "#ffb74d", "#34a853"],
    "overlay": True,                           # glow, cursor, badge, tab marker (numbered boxes stay on)
    "max_elements": 120,
    "screenshot_quality": 65,
    "save_screenshots": True,
}


def config_path() -> Path:
    return Path(os.environ.get("GEMINI_IN_CHROME_CONFIG", HOME / "config.json"))


def load() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))
    p = config_path()
    if p.exists():
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    hosts = os.environ.get("GEMINI_IN_CHROME_HOSTS")      # convenience: comma separated, replaces the list
    if hosts:
        cfg["allowed_hosts"] = [h.strip() for h in hosts.split(",") if h.strip()]
    return cfg


def save(cfg: dict) -> Path:
    """Write only the keys that differ from the defaults, so upgrades keep picking up new defaults."""
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({k: v for k, v in cfg.items() if DEFAULTS.get(k) != v}, indent=2) + "\n", encoding="utf-8")
    return p


def normalize_host(value: str) -> str:
    value = value.strip().lower()
    if value == "*":
        return value
    host = urlparse(value if "//" in value else "//" + value).hostname or value
    return host.removeprefix("www.")


def host_allowed(cfg: dict, url: str) -> bool:
    if url == "about:blank":
        return True
    u = urlparse(url)
    if u.scheme == "file":
        return bool(cfg["allow_file_urls"])
    if u.scheme not in ("http", "https"):
        return False
    host = (u.hostname or "").removeprefix("www.")
    return any(h == "*" or host == h or host.endswith("." + h) for h in cfg["allowed_hosts"])
