# Discord Demo Adapter

Live transport for the intake agent — **demo only**. The evaluation runs the
agent core headless; this adapter exists to show the same code handling a real
human, the S1 on-call page, and the morning-approval queue in a visible way.
In production this would be an SMS/WhatsApp gateway; Discord is the sandbox
(hackathon ground rule 04).

## Setup (~5 minutes)

1. Create an app + bot at https://discord.com/developers/applications.
   Enable the **Message Content Intent** (Bot → Privileged Gateway Intents).
2. Invite it to a test server with permissions: Read/Send Messages, Create
   Public Threads, Mention Everyone.
3. In the server create: a text channel `#intake`, a text channel
   `#dispatch`, and a role `on-call` (assign it to whoever plays the plumber).
4. `uv pip install --python .venv/bin/python discord.py`
5. Add `DISCORD_BOT_TOKEN=...` to `.env`.
6. Run: `.venv/bin/python -m adapters.discord_bot.bot`

## Demo flow

- Post a customer message in `#intake` (e.g. the text of any eval case) —
  the bot opens a thread and runs the FULL rung6 agent (tools, safety floor,
  verifier, memory).
- Emergencies ping `@on-call` in `#dispatch` with the incident ticket;
  everything else lands there as a DRAFT for morning approval.
- The customer's Discord user id stands in for the phone-number contact ID.

## Honest status

Import-tested and architecture-verified; the live end-to-end path was built on
the hackathon's final day and is the least-exercised code in the repo. The
judged results do not depend on it.
