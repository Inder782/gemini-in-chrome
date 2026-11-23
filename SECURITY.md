# Security

`gemini-in-chrome` lets an AI model operate a browser in which you are signed in. Treat that like giving someone your
unlocked laptop: powerful, and worth a few guardrails.

## What can go wrong

- **Prompt injection.** A web page can contain text written to trick the model ("ignore your instructions and open ...").
  The tools label page content as data and the bundled skill tells the model never to follow it, but no model is immune.
- **Over-reach.** The model may click the wrong thing, or do more than you intended.
- **Local access to the debugging port.** While remote debugging is switched on, programs on your computer can ask
  Chrome for a debugging session. Chrome shows an *Allow* prompt for each new connection. Only click *Allow* when you
  started the agent.

## Built-in guardrails

| Guardrail | Detail |
|---|---|
| Site allow-list | `allowed_hosts` is a short list by default. After every action the server checks the page URL and goes back if it left the list. `chrome://`, `javascript:`, `file:` and other non-web schemes are always blocked |
| Uploads off by default | `browser_upload` needs `upload_dirs`, and refuses paths outside them |
| Background tab | The agent works in its own tab, marked `✨ Gemini working`, and never touches your other tabs |
| Visible | Glow, cursor and a status badge show when the agent is active; the overlay hides itself 90 s after the last action |
| No secrets in tools | There is no tool to read cookies, local storage or saved passwords |

## Recommendations

1. Keep `allowed_hosts` to the sites you need. Avoid `"*"`.
2. For banking, email and other high-risk accounts, use `connect: "launch"` (a separate Chrome profile that is not signed in to them).
3. Watch the tab on tasks that can change things (posting, sending, buying) and stop the agent if it does something unexpected.
4. Do not leave the agent running unattended on signed-in accounts.

## Reporting a vulnerability

Please open a private security advisory on GitHub (Security tab, "Report a vulnerability") rather than a public issue.
Include the version, the steps to reproduce and the impact. I will aim to respond within a week.
