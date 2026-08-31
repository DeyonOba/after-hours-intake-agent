"""Discord demo adapter — live transport for the intake agent.

DEMO ONLY: the evaluation never touches Discord (see README.md, "channel-
agnostic"). This adapter shows the same agent core handling a live human:

- a message in the intake channel opens a private thread (one per customer)
- the customer's Discord user id stands in for the phone-number contact ID
- the agent runs with the FINAL config (configs/rung6.yaml)
- an S1 ticket pings the @on-call role in the dispatch channel immediately;
  everything else lands in the dispatch channel as a DRAFT for approval

Setup (see adapters/discord_bot/README.md):
  DISCORD_BOT_TOKEN in .env, channel named 'intake', role named 'on-call',
  channel named 'dispatch'. Run:  .venv/bin/python -m adapters.discord_bot.bot
"""
from __future__ import annotations

import asyncio
import json
import queue
import threading

import discord

from agent_core import config
from agent_core.agent import IntakeSession
from agent_core.config import RungConfig

INTAKE_CHANNEL = "intake"
DISPATCH_CHANNEL = "dispatch"
ONCALL_ROLE = "on-call"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# thread_id -> inbox queue feeding that thread's running session
SESSIONS: dict[int, queue.Queue] = {}


def make_case(user: discord.abc.User, opening: str) -> dict:
    """A live 'case' shell: no hidden facts, no answer key — a real customer."""
    return {
        "id": f"live_{user.id}",
        "contact": {"name": user.display_name, "phone": f"discord:{user.id}",
                    "address": "(collect during intake)"},
        "opening_message": opening,
        "hidden_facts": {}, "sim_notes": "", "answer_key": {},
    }


async def run_session(thread: discord.Thread, user: discord.abc.User, opening: str):
    cfg = config.load_rung_config(config.REPO_ROOT / "configs" / "rung6.yaml")
    case = make_case(user, opening)
    session = IntakeSession(cfg, case)
    inbox: queue.Queue = queue.Queue()
    SESSIONS[thread.id] = inbox
    loop = asyncio.get_running_loop()
    outbox: asyncio.Queue = asyncio.Queue()

    def respond_fn(agent_text: str) -> str:
        # runs in the worker thread: ship the agent's reply to Discord,
        # then block until the customer's next message arrives
        asyncio.run_coroutine_threadsafe(outbox.put(agent_text), loop)
        return inbox.get()

    def worker():
        result = session.run(respond_fn)
        asyncio.run_coroutine_threadsafe(outbox.put(result), loop)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = await outbox.get()
        if isinstance(item, str):                      # agent reply -> thread
            await thread.send(item[:1900] or "…")
            continue
        result = item                                  # session finished
        ticket = result.ticket
        if ticket is None:
            await thread.send("Sorry — handing you to a human, someone will call you shortly.")
            break
        dispatch = discord.utils.get(thread.guild.text_channels, name=DISPATCH_CHANNEL)
        oncall = discord.utils.get(thread.guild.roles, name=ONCALL_ROLE)
        body = f"```json\n{json.dumps(ticket, indent=1)[:1700]}\n```"
        if dispatch:
            if ticket.get("severity") == "S1" and oncall:
                await dispatch.send(f"{oncall.mention} 🚨 **S1 EMERGENCY** — {thread.mention}\n{body}")
            else:
                await dispatch.send(f"📋 DRAFT ticket ({ticket.get('severity')}) — awaiting "
                                    f"morning approval — {thread.mention}\n{body}")
        break
    SESSIONS.pop(thread.id, None)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # customer replying inside their thread
    if isinstance(message.channel, discord.Thread) and message.channel.id in SESSIONS:
        SESSIONS[message.channel.id].put(message.content)
        return
    # new conversation in the intake channel
    if getattr(message.channel, "name", None) == INTAKE_CHANNEL:
        thread = await message.create_thread(name=f"intake-{message.author.display_name}"[:90])
        await thread.send("Sorry we missed your call — I'm the after-hours assistant. "
                          "I'm on it right now.")
        asyncio.create_task(run_session(thread, message.author, message.content))


def main() -> None:
    import os
    config.load_dotenv()
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Set DISCORD_BOT_TOKEN in .env (see adapters/discord_bot/README.md)")
    client.run(token)


if __name__ == "__main__":
    main()
