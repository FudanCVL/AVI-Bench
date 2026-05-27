"""Eval-time LLM helper, used by some level_metrics scorers.

Uses any OpenAI-compatible gateway (same config as inference/refine).

Environment variables:
  OPENAI_API_KEY   : required
  OPENAI_BASE_URL  : required
  REFINE_MODEL     : optional (default "gemini-2.5-flash")
"""
import os
import openai

_API_KEY = os.environ.get("OPENAI_API_KEY")
_BASE_URL = os.environ.get("OPENAI_BASE_URL")
if not _API_KEY or not _BASE_URL:
    raise RuntimeError(
        "OPENAI_API_KEY and OPENAI_BASE_URL must be set for eval/level_metrics/agent_eval_formatting.py."
    )
_MODEL = os.environ.get("REFINE_MODEL", "gemini-2.5-flash")

CLIENT_AGENT = openai.OpenAI(api_key=_API_KEY, base_url=_BASE_URL)


def get_response_from_llm_agent(_pmp):
    response = CLIENT_AGENT.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": str(_pmp)}],
    )
    return response.choices[0].message.content
