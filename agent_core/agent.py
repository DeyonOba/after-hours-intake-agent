"""Intake agent session: runs one after-hours conversation against a customer
(real or simulated) and produces a job ticket + full trajectory.

- rung0-2: plain messages.create conversation (no tools)
- rung3+:  SDK tool runner per agent turn (mirrored history, per docs)
- rung2+:  deterministic safety floor enforced on the final ticket
- rung5+:  programmatic verifier with one revision round-trip
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import anthropic

from . import config, prompts, safety, tools, verifier as verifier_mod


@dataclass
class SessionResult:
    ticket: dict | None = None
    parse_ok: bool = False
    refusal: bool = False
    hit_turn_limit: bool = False
    turns: int = 0
    agent_input_tokens: int = 0
    agent_output_tokens: int = 0
    tool_calls: int = 0
    safety_overrides: list = field(default_factory=list)
    verifier_issues_initial: list = field(default_factory=list)
    verifier_issues_final: list = field(default_factory=list)
    trajectory: list = field(default_factory=list)
    customer_texts: list = field(default_factory=list)

    @property
    def agent_cost(self) -> float:
        return 0.0  # filled by session (needs model name)


TICKET_FENCE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_ticket(text: str) -> dict | None:
    matches = TICKET_FENCE.findall(text)
    candidates = list(matches)
    if not candidates:
        # fallback: largest brace blob that mentions "severity"
        blobs = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        candidates = [b for b in blobs if '"severity"' in b]
    for cand in reversed(candidates):
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict) and "severity" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    return None


class IntakeSession:
    def __init__(self, cfg: config.RungConfig, case: dict, client: anthropic.Anthropic | None = None):
        self.cfg = cfg
        self.case = case
        self.client = client or config.make_client()
        self.system = prompts.build_system(cfg, case)
        self.result = SessionResult()
        self.messages: list = []

    # ---- logging ----
    def _log(self, role: str, kind: str, payload) -> None:
        self.result.trajectory.append({"role": role, "kind": kind, "content": payload})

    def _serialize_blocks(self, content) -> None:
        for block in content:
            btype = getattr(block, "type", None)
            if btype == "text":
                self._log("agent", "text", block.text)
            elif btype == "tool_use":
                self.result.tool_calls += 1
                self._log("agent", "tool_use", {"tool": block.name, "input": block.input})
            elif btype == "thinking":
                pass  # omitted-display thinking blocks carry no text

    # ---- one agent turn ----
    def _agent_turn(self) -> tuple[str, bool]:
        """Returns (reply_text, refusal)."""
        if self.cfg.tools:
            return self._agent_turn_with_tools()
        response = self.client.messages.create(
            model=self.cfg.agent_model,
            max_tokens=self.cfg.max_tokens,
            system=self.system,
            messages=self.messages,
        )
        self.result.agent_input_tokens += response.usage.input_tokens
        self.result.agent_output_tokens += response.usage.output_tokens
        if response.stop_reason == "refusal":
            return "", True
        self.messages.append({"role": "assistant", "content": response.content})
        self._serialize_blocks(response.content)
        text = "".join(b.text for b in response.content if b.type == "text")
        return text, False

    def _agent_turn_with_tools(self) -> tuple[str, bool]:
        runner = self.client.beta.messages.tool_runner(
            model=self.cfg.agent_model,
            max_tokens=self.cfg.max_tokens,
            system=self.system,
            tools=tools.toolset(self.cfg),
            messages=self.messages,
        )
        last = None
        for message in runner:
            last = message
            self.result.agent_input_tokens += message.usage.input_tokens
            self.result.agent_output_tokens += message.usage.output_tokens
            # mirror history: the runner keeps its own copy and does not expose it
            self.messages.append({"role": "assistant", "content": message.content})
            self._serialize_blocks(message.content)
            tool_response = runner.generate_tool_call_response()
            if tool_response is not None:
                self.messages.append(tool_response)
                for tr in tool_response["content"]:
                    self._log("tool", "tool_result",
                              {"tool_use_id": tr.get("tool_use_id"),
                               "content": str(tr.get("content"))[:2000]})
        if last is None:
            return "", False
        if last.stop_reason == "refusal":
            return "", True
        text = "".join(b.text for b in last.content if b.type == "text")
        return text, False

    # ---- full conversation ----
    def run(self, respond_fn) -> SessionResult:
        """respond_fn(agent_text) -> customer reply string (the simulator, or a live adapter)."""
        opening = self.case["opening_message"]
        self.messages.append({"role": "user", "content": opening})
        self.result.customer_texts.append(opening)
        self._log("customer", "text", opening)

        ticket = None
        for _turn in range(self.cfg.max_agent_turns):
            self.result.turns += 1
            text, refused = self._agent_turn()
            if refused:
                self.result.refusal = True
                break
            ticket = parse_ticket(text)
            if ticket is not None:
                break
            reply = respond_fn(text.strip() or "(no reply received)")
            self.messages.append({"role": "user", "content": reply})
            self.result.customer_texts.append(reply)
            self._log("customer", "text", reply)
        else:
            self.result.hit_turn_limit = True

        # rung5: programmatic verification with one revision round-trip
        if ticket is not None and self.cfg.verifier:
            issues = verifier_mod.verify_ticket(ticket)
            self.result.verifier_issues_initial = issues
            if issues:
                self._log("verifier", "issues", issues)
                self.messages.append({
                    "role": "user",
                    "content": prompts.VERIFIER_REVISION.format(issues="\n".join(f"- {i}" for i in issues)),
                })
                self.result.turns += 1
                text, refused = self._agent_turn()
                revised = None if refused else parse_ticket(text)
                if revised is not None:
                    ticket = revised
                self.result.verifier_issues_final = verifier_mod.verify_ticket(ticket)

        # rung2: deterministic safety floor is the final authority
        if ticket is not None and self.cfg.safety_rules:
            finding = safety.scan_customer_text(self.result.customer_texts)
            ticket, overrides = safety.enforce(ticket, finding)
            self.result.safety_overrides = overrides
            if overrides:
                self._log("safety", "overrides", overrides)

        self.result.ticket = ticket
        self.result.parse_ok = ticket is not None
        if ticket is not None:
            self._log("agent", "ticket", ticket)
        return self.result
