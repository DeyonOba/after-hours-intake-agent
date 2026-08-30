"""LLM customer simulator: role-plays one case's customer, holding hidden
facts and following the case's behavior script. The opening message lives in
its system prompt, so its message list starts with the agent's first reply
(user role) and alternates correctly."""
from __future__ import annotations

import anthropic

from agent_core import config, prompts


class CustomerSimulator:
    def __init__(self, case: dict, model: str, client: anthropic.Anthropic | None = None):
        self.case = case
        self.model = model
        self.client = client or config.make_client()
        self.system = prompts.simulator_system(case)
        self.messages: list = []
        self.input_tokens = 0
        self.output_tokens = 0

    def respond(self, agent_text: str) -> str:
        self.messages.append({"role": "user", "content": agent_text})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=self.system,
            messages=self.messages,
        )
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        self.messages.append({"role": "assistant", "content": text})
        return text

    @property
    def cost(self) -> float:
        return config.estimate_cost(self.model, self.input_tokens, self.output_tokens)
