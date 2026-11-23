# Contributing

Thanks for helping. This project is small on purpose, so the bar is: keep it simple, keep it safe, keep it tested.

## Set up

```bash
git clone https://github.com/Inder782/gemini-in-chrome
cd gemini-in-chrome
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run the checks

```bash
ruff check .
pytest
```

The tests start a headless Chrome on a random port and drive a local fixture page (`tests/fixtures`), including shadow DOM,
file choosers and a link to a blocked site. You need Chrome installed.

## Where things are

| File | Purpose |
|---|---|
| `src/gemini_in_chrome/browser.py` | The browser layer: connect, background tab, look, click, type, upload, host guard |
| `src/gemini_in_chrome/collect.js` | Finds the visible clickable elements (shadow DOM aware) |
| `src/gemini_in_chrome/overlay.js` | Glow, cursor, badge, highlight, tab marker (DOM calls only, Trusted-Types safe) |
| `src/gemini_in_chrome/server.py` | The MCP tools |
| `src/gemini_in_chrome/cli.py`, `install.py` | `gemini-in-chrome` command and the agy installer |

## Guidelines

- A new tool needs a test and a line in the README table.
- Anything that widens what the agent can reach (sites, files, schemes) must be opt-in and documented in `SECURITY.md`.
- Never print to stdout in the server: it is the MCP channel.
- macOS and Linux reports are especially welcome: please include `gemini-in-chrome doctor` output.
