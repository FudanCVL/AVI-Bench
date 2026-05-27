"""
Gemini adapter via any OpenAI-compatible API gateway.

Usage in run.py — model_path is the Gemini model id (e.g. "gemini-2.5-pro").

Environment variables:
  OPENAI_API_KEY    : required, API key for the gateway
  OPENAI_BASE_URL   : required, base URL of the gateway (e.g. "https://.../v1")
  GEMINI_MAX_RETRIES: optional, default 5
  GEMINI_TIMEOUT    : optional, default 180 (seconds per request)
"""
import os
import time
import base64
import mimetypes
from pathlib import Path

import openai

_MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", 5))
_TIMEOUT = float(os.environ.get("GEMINI_TIMEOUT", 180))
_RETRYABLE_KEYWORDS = (
    "429", "rate", "RateLimit", "Timeout", "Connection",
    "RemoteProtocol", "ServiceUnavailable", "503", "502", "504",
)


def _is_retryable(exc: Exception) -> bool:
    msg = repr(exc).lower()
    return any(kw.lower() in msg for kw in _RETRYABLE_KEYWORDS)


def _file_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _guess_mime(path: str, default: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or default


def _strip_file_uri(uri: str) -> str:
    """Convert 'file:///abs/path' -> '/abs/path'."""
    return uri[7:] if uri.startswith("file://") else uri


def set_model(model_path=None, multi_gpu=False):  # multi_gpu ignored for API models
    if model_path is None:
        model_path = os.environ.get("MODEL_PATH", "gemini-2.5-pro")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Export it before running the Gemini adapter."
        )
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not base_url:
        raise RuntimeError(
            "OPENAI_BASE_URL is not set. Export the gateway base URL (e.g. https://.../v1)."
        )

    # We don't keep a long-lived client here — get_response builds a fresh one
    # per call to avoid connection-pool corruption when running behind an
    # unreliable proxy / high-latency network. The handle just carries config.
    model_handle = {"api_key": api_key, "base_url": base_url, "model_id": model_path}
    return model_handle, None


def _convert_conversation(conversation):
    """Convert internal conversation format into OpenAI-compatible messages.

    Internal format:
      [{"role": "system"/"user", "content": [
          {"type": "text",  "text": "..."},
          {"type": "image", "image": "file:///abs/path.jpg"},
          {"type": "audio", "audio": "file:///abs/path.wav"},
          {"type": "video", "video": "file:///abs/path.mp4", "nframes": ...},
      ]}]

    OpenAI-compatible format:
      System message: content string
      User message: list of typed parts
        - {"type": "text", "text": ...}
        - {"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}
        - {"type": "input_audio", "input_audio": {"data": "<b64>", "format": "wav"}}
        - Videos go as image_url with data:video/...;base64,...
    """
    out = []
    for msg in conversation:
        role = msg["role"]
        content = msg["content"]

        if role == "system":
            if isinstance(content, list):
                texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                out.append({"role": "system", "content": "\n".join(texts).strip()})
            else:
                out.append({"role": "system", "content": str(content)})
            continue

        # If the message contains a video, mp4 typically carries its own audio track
        # which Gemini will process server-side. Drop any redundant standalone audio
        # parts to avoid uploading them twice.
        has_video = any(it.get("type") == "video" for it in content)

        parts = []
        for item in content:
            t = item.get("type")
            if t == "text":
                parts.append({"type": "text", "text": item["text"]})
            elif t == "image":
                path = _strip_file_uri(item["image"])
                mime = _guess_mime(path, "image/jpeg")
                b64 = _file_to_b64(path)
                parts.append({"type": "image_url",
                              "image_url": {"url": f"data:{mime};base64,{b64}"}})
            elif t == "video":
                path = _strip_file_uri(item["video"])
                mime = _guess_mime(path, "video/mp4")
                b64 = _file_to_b64(path)
                parts.append({"type": "image_url",
                              "image_url": {"url": f"data:{mime};base64,{b64}"}})
            elif t == "audio":
                if has_video:
                    continue  # audio is already inside the mp4
                path = _strip_file_uri(item["audio"])
                ext = Path(path).suffix.lower().lstrip(".") or "wav"
                fmt = "wav" if ext in ("wav", "wave") else ext
                b64 = _file_to_b64(path)
                parts.append({"type": "input_audio",
                              "input_audio": {"data": b64, "format": fmt}})
            else:
                continue
        out.append({"role": role, "content": parts})
    return out


def get_response(conversation, processor, model, USE_AUDIO_IN_VIDEO=False):
    """Run a single multimodal turn against the gateway and return [str].

    Creates a fresh OpenAI client per call so the underlying httpx
    connection pool doesn't accumulate half-broken sockets when running
    behind an unreliable HTTP proxy.
    """
    api_key = model["api_key"]
    base_url = model["base_url"]
    model_id = model["model_id"]
    messages = _convert_conversation(conversation)

    last_exc = None
    for attempt in range(_MAX_RETRIES):
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=_TIMEOUT)
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=messages,
                timeout=_TIMEOUT,
            )
            text = resp.choices[0].message.content
            return [text if text is not None else ""]
        except Exception as e:
            last_exc = e
            if not _is_retryable(e) or attempt == _MAX_RETRIES - 1:
                raise
            sleep = min(2 ** attempt, 30)
            print(f"[gemini] retryable error ({type(e).__name__}); sleep {sleep}s, attempt {attempt+1}/{_MAX_RETRIES}")
            time.sleep(sleep)
        finally:
            try:
                client.close()
            except Exception:
                pass
    raise last_exc  # noqa
