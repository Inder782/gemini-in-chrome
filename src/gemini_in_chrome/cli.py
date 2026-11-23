"""gemini-in-chrome command line."""
import argparse
import json
import shutil
import socket
import sys

from . import __version__, config
from .browser import BrowserError, devtools_endpoint, find_chrome, launch_chrome

HELP = """gemini-in-chrome: let Gemini (or any MCP agent) use your Chrome.

  install [--client agy|print] [--no-allow]   register the tools with agy (or print the config for other clients)
  doctor                                      check that everything is ready
  allow <site...>                             let the agent use these sites (e.g. allow youtube.com), "*" = any site
  deny <site...>                              remove sites from the allow-list
  config                                      show the effective settings and where the config file lives
  set <key> <json-value>                      change a setting, e.g. set upload_dirs '["C:/clips"]'
  launch                                      start the separate Chrome profile (connect="launch") to sign in once
  serve                                       run the MCP server on stdio (agents start this themselves)
"""


def _snippet() -> dict:
    return {"command": sys.executable, "args": ["-m", "gemini_in_chrome", "serve"]}


def cmd_install(client: str, allow: bool):
    from . import install
    if client == "print":
        print("Add this MCP server to your client's config (name: gemini-in-chrome):\n")
        print(json.dumps({"mcpServers": {"gemini-in-chrome": _snippet()}}, indent=2))
        print("\nGemini CLI:  put the block above in ~/.gemini/settings.json")
        print(f'Claude Code: claude mcp add gemini-in-chrome -- "{sys.executable}" -m gemini_in_chrome serve')
        return 0
    return install.install_agy(allow)


def cmd_doctor() -> int:
    cfg = config.load()
    ok = True

    def row(name, good, detail, fatal=True):
        nonlocal ok
        if not good and fatal:
            ok = False
        print(f"  [{'OK' if good else '!!' if fatal else '--'}] {name}: {detail}")

    print(f"gemini-in-chrome {__version__} doctor")
    row("python", sys.version_info >= (3, 10), sys.version.split()[0])
    for mod in ("playwright", "mcp"):
        try:
            __import__(mod)
            row(mod, True, "installed")
        except ImportError:
            row(mod, False, "missing (pip install gemini-in-chrome)")
    mode = cfg["connect"]
    if mode == "auto":
        try:
            ep = devtools_endpoint(cfg)
            port = int(ep.split(":")[2].split("/")[0])
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                pass
            row("your Chrome", True, f"remote debugging is on (port {port})")
        except (BrowserError, OSError):
            row("your Chrome", False, "not reachable. Open chrome://inspect/#remote-debugging and tick 'Allow remote "
                "debugging for this browser instance' (Chrome 144+), keep Chrome open. Older Chrome: set connect=launch")
    elif mode == "launch":
        try:
            row("Chrome", True, find_chrome(cfg["chrome_path"]))
        except BrowserError as e:
            row("Chrome", False, str(e))
    else:
        row("endpoint", True, mode)
    hosts = cfg["allowed_hosts"]
    row("allowed sites", bool(hosts), ", ".join(hosts) if hosts else "none (run: gemini-in-chrome allow <site>)")
    row("uploads", True, ", ".join(cfg["upload_dirs"]) if cfg["upload_dirs"] else "disabled (set upload_dirs to enable)", False)
    agy = shutil.which("agy")
    if agy:
        import subprocess
        out = subprocess.run([agy, "mcp", "list"], capture_output=True, text=True).stdout
        row("agy", "gemini-in-chrome" in out, "registered" if "gemini-in-chrome" in out
            else "found, but not registered (run: gemini-in-chrome install)", False)
    else:
        row("agy", False, "not found (fine if you use another MCP client)", False)
    print("\nAll good." if ok else "\nFix the items marked !!.")
    return 0 if ok else 1


def cmd_allow(sites, remove=False):
    cfg = config.load()
    hosts = list(cfg["allowed_hosts"])
    for s in sites:
        h = config.normalize_host(s)
        if remove and h in hosts:
            hosts.remove(h)
        elif not remove and h not in hosts:
            hosts.append(h)
    cfg["allowed_hosts"] = hosts
    p = config.save(cfg)
    print(f"Allowed sites: {', '.join(hosts) or '(none)'}\n(saved to {p})")
    if "*" in hosts:
        print("Warning: '*' lets the agent open ANY site while you are signed in to your accounts.")


def cmd_set(key, value):
    cfg = config.load()
    if key not in config.DEFAULTS:
        print(f"Unknown setting '{key}'. Known: {', '.join(config.DEFAULTS)}")
        return 1
    try:
        cfg[key] = json.loads(value)
    except json.JSONDecodeError:
        cfg[key] = value
    print(f"{key} = {json.dumps(cfg[key])}\n(saved to {config.save(cfg)})")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gemini-in-chrome", description=HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("install")
    i.add_argument("--client", choices=["agy", "print"], default="agy")
    i.add_argument("--no-allow", action="store_true", help="keep agy's per-tool approval prompts")
    sub.add_parser("doctor")
    sub.add_parser("allow").add_argument("sites", nargs="+")
    sub.add_parser("deny").add_argument("sites", nargs="+")
    sub.add_parser("config")
    s = sub.add_parser("set")
    s.add_argument("key")
    s.add_argument("value")
    sub.add_parser("launch")
    sub.add_parser("serve")
    a = ap.parse_args(argv)

    if a.cmd == "serve":
        from .server import main as serve
        serve()
    elif a.cmd == "install":
        return cmd_install(a.client, not a.no_allow)
    elif a.cmd == "doctor":
        return cmd_doctor()
    elif a.cmd in ("allow", "deny"):
        cmd_allow(a.sites, remove=a.cmd == "deny")
    elif a.cmd == "config":
        print(f"config file: {config.config_path()} ({'exists' if config.config_path().exists() else 'not created yet'})")
        print(json.dumps(config.load(), indent=2))
    elif a.cmd == "set":
        return cmd_set(a.key, a.value)
    elif a.cmd == "launch":
        cfg = config.load()
        cfg["connect"] = "launch"
        print(f"Chrome started with its own profile ({launch_chrome(cfg)}). Sign in to the sites you want the agent to use, "
              'then set "connect": "launch" with: gemini-in-chrome set connect launch')
    return 0


if __name__ == "__main__":
    sys.exit(main())
