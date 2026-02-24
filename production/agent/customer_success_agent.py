"""
production/agent/customer_success_agent.py
OpenAI Agents SDK Agent definition for the Customer Success Digital FTE.

Model selection via environment:
  AGENT_MODEL     — model name (default: gpt-4o; use grok-2-latest for Grok)
  AGENT_BASE_URL  — API base URL (default: OpenAI; set to https://api.x.ai/v1 for Grok)
  GROK_API_KEY    — xAI API key (used when AGENT_BASE_URL points to x.ai)
"""
from __future__ import annotations

import os

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT
from production.agent.tools import ALL_TOOLS

_model_name = os.getenv("AGENT_MODEL", "gpt-4o")
_base_url = os.getenv("AGENT_BASE_URL")  # None → uses OpenAI default
_api_key = os.getenv("GROK_API_KEY") or os.getenv("OPENAI_API_KEY")

if _base_url:
    # Grok (xAI) or any OpenAI-compatible endpoint
    _client = AsyncOpenAI(api_key=_api_key, base_url=_base_url)
    _model = OpenAIChatCompletionsModel(model=_model_name, openai_client=_client)
else:
    # Default: OpenAI
    _model = _model_name

customer_success_agent = Agent(
    name="Customer Success FTE",
    model=_model,
    instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
    tools=ALL_TOOLS,
    model_settings=ModelSettings(parallel_tool_calls=False),
)

__all__ = ["customer_success_agent"]
