"""Refine-LLM client used by auto_format/run.py.

Calls a small fast LLM via any OpenAI-compatible API gateway to normalize free-form
model outputs into structured formats (JSON, lists, dicts, etc.).

Environment variables:
  OPENAI_API_KEY   : required, key for the gateway
  OPENAI_BASE_URL  : required, base URL of the gateway (e.g. "https://.../v1")
  REFINE_MODEL     : optional model id (default "gemini-2.5-flash")
  REFINE_TIMEOUT   : optional per-request timeout in seconds (default 60)
  REFINE_MAX_RETRIES: optional, default 5
"""
import os
import time

import openai

_API_KEY = os.environ.get("OPENAI_API_KEY")
_BASE_URL = os.environ.get("OPENAI_BASE_URL")
if not _API_KEY or not _BASE_URL:
    raise RuntimeError(
        "OPENAI_API_KEY and OPENAI_BASE_URL must be set for auto_format/agent_format.py."
    )

_REFINE_MODEL = os.environ.get("REFINE_MODEL", "gemini-2.5-flash")
_TIMEOUT = float(os.environ.get("REFINE_TIMEOUT", 60))
_MAX_RETRIES = int(os.environ.get("REFINE_MAX_RETRIES", 5))

CLIENT_AGENT = openai.OpenAI(api_key=_API_KEY, base_url=_BASE_URL, timeout=_TIMEOUT)

_RETRYABLE_KEYWORDS = (
    "429", "rate", "RateLimit", "Timeout", "Connection",
    "RemoteProtocol", "ServiceUnavailable", "503", "502", "504",
)


def _is_retryable(e):
    msg = repr(e).lower()
    return any(kw.lower() in msg for kw in _RETRYABLE_KEYWORDS)


def get_response_from_llm_agent(_pmp):
    for attempt in range(_MAX_RETRIES):
        try:
            response = CLIENT_AGENT.chat.completions.create(
                model=_REFINE_MODEL,
                messages=[{"role": "user", "content": str(_pmp)}],
                timeout=_TIMEOUT,
            )
            return response.choices[0].message.content
        except Exception as e:
            if _is_retryable(e) and attempt < _MAX_RETRIES - 1:
                wait = min(2 ** attempt, 30)
                print(f"    [retry] {type(e).__name__}: {str(e)[:80]}... wait {wait}s ({attempt+1}/{_MAX_RETRIES})")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"refine API failed after {_MAX_RETRIES} retries")
