"""Register gemini-in-chrome with agy (Google Antigravity CLI): MCP server, skill, and optional pre-approval."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

NAME = "gemini-in-chrome"


def install_agy(allow: bool = True) -> int:
    agy = shutil.which("agy")
    if not agy:
        print("agy was not found on PATH. For another MCP client run: gemini-in-chrome install --client print")
        return 1
    subprocess.run([agy, "mcp", "remove", NAME], capture_output=True)
    r = subprocess.run([agy, "mcp", "add", NAME, sys.executable, "-m", "gemini_in_chrome", "serve"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"agy could not add the server: {r.stderr or r.stdout}")
        return 1
    print(f"Registered the '{NAME}' MCP server in agy.")

    skill = Path(__file__).parent / "skills" / "SKILL.md"
    dest = Path.home() / ".gemini" / "config" / "skills" / NAME / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(skill.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Installed the agy skill: {dest}")

    if allow:
        settings = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
        rule = f"mcp({NAME}/*)"
        try:
            data = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
            rules = data.setdefault("permissions", {}).setdefault("allow", [])
            if rule not in rules:
                rules.append(rule)
                settings.parent.mkdir(parents=True, exist_ok=True)
                settings.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"agy will not ask before each browser action (added {rule} to {settings}).")
        except (OSError, json.JSONDecodeError) as e:
            print(f"Could not edit {settings} ({e}). Add \"{rule}\" to permissions.allow by hand, or accept agy's prompts.")
    print("\nNext: gemini-in-chrome doctor")
    return 0
