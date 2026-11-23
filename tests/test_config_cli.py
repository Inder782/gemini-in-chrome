import json

import pytest

from gemini_in_chrome import cli, config


@pytest.fixture(autouse=True)
def cfg_file(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    monkeypatch.setenv("GEMINI_IN_CHROME_CONFIG", str(p))
    monkeypatch.delenv("GEMINI_IN_CHROME_HOSTS", raising=False)
    return p


def test_defaults_are_safe():
    cfg = config.load()
    assert "*" not in cfg["allowed_hosts"]
    assert cfg["upload_dirs"] == []
    assert cfg["focus_tab"] == "never"
    assert cfg["connect"] == "auto"


@pytest.mark.parametrize("url,ok", [
    ("https://en.wikipedia.org/wiki/Aurora", True),     # subdomain of an allowed host
    ("https://wikipedia.org", True),
    ("https://evilwikipedia.org", False),               # suffix without the dot must not match
    ("https://example.com.evil.io", False),
    ("http://github.com/x", True),
    ("chrome://settings", False),
    ("javascript:alert(1)", False),
    ("file:///etc/passwd", False),
    ("about:blank", True),
])
def test_host_allowed(url, ok):
    assert config.host_allowed(config.load(), url) is ok


def test_star_allows_everything_but_not_non_web_schemes():
    cfg = config.load()
    cfg["allowed_hosts"] = ["*"]
    assert config.host_allowed(cfg, "https://anything.example")
    assert not config.host_allowed(cfg, "chrome://settings")


def test_normalize_host():
    assert config.normalize_host("https://www.YouTube.com/watch?v=1") == "youtube.com"
    assert config.normalize_host("Studio.YouTube.com") == "studio.youtube.com"
    assert config.normalize_host("*") == "*"


def test_allow_and_deny_roundtrip(cfg_file, capsys):
    cli.main(["allow", "https://www.example.org/page", "linkedin.com"])
    assert {"example.org", "linkedin.com"} <= set(config.load()["allowed_hosts"])
    assert set(json.loads(cfg_file.read_text())) == {"allowed_hosts"}     # only differences from the defaults are saved
    cli.main(["deny", "linkedin.com"])
    assert "linkedin.com" not in config.load()["allowed_hosts"]


def test_set_parses_json_and_rejects_unknown_keys(capsys):
    assert cli.main(["set", "upload_dirs", '["C:/clips"]']) == 0
    assert config.load()["upload_dirs"] == ["C:/clips"]
    assert cli.main(["set", "nope", "1"]) == 1


def test_env_hosts_override(monkeypatch):
    monkeypatch.setenv("GEMINI_IN_CHROME_HOSTS", "a.com, b.com")
    assert config.load()["allowed_hosts"] == ["a.com", "b.com"]


def test_print_client_snippet(capsys):
    assert cli.main(["install", "--client", "print"]) == 0
    out = capsys.readouterr().out
    assert '"mcpServers"' in out and "gemini_in_chrome" in out
