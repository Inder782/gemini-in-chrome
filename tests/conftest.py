import functools
import http.server
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from gemini_in_chrome import config
from gemini_in_chrome.browser import Browser, BrowserError, find_chrome

FIXTURES = Path(__file__).parent / "fixtures"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def chrome_endpoint(tmp_path_factory):
    try:
        chrome = find_chrome()
    except BrowserError:
        pytest.skip("Chrome is not installed")
    port = _free_port()
    profile = tmp_path_factory.mktemp("profile")
    proc = subprocess.Popen([chrome, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
                             "--no-first-run", "--no-default-browser-check", "--no-sandbox", "--disable-renderer-backgrounding",
                             "--disable-backgrounding-occluded-windows", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.skip("Chrome did not start")
    yield f"http://127.0.0.1:{port}"
    proc.terminate()


@pytest.fixture(scope="session")
def site():
    """Serve tests/fixtures on 127.0.0.1 (allowed in tests); the same server is 'another site' as localhost."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FIXTURES))
    handler.log_message = lambda *a, **k: None
    class Quiet(http.server.ThreadingHTTPServer):
        def handle_error(self, request, client_address):   # Chrome drops connections; that is not a test failure
            pass

    srv = Quiet(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture
def upload_dir(tmp_path):
    d = tmp_path / "uploads"
    d.mkdir()
    (d / "clip.txt").write_text("hello")
    (tmp_path / "secret.txt").write_text("nope")
    return d


@pytest.fixture
def browser(chrome_endpoint, upload_dir, monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_IN_CHROME_HOME", str(tmp_path / "home"))
    cfg = config.load()
    cfg.update(connect=chrome_endpoint, allowed_hosts=["127.0.0.1"], upload_dirs=[str(upload_dir)],
               save_screenshots=False)
    b = Browser(cfg)
    yield b
    b.close()
