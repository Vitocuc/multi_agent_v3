"""
llm/router.py — model-agnostic LLM caller.
Supports: claude, gemini.
Returns raw text. Parsing and validation happen in llm/retry.py.

Gemini 2.5 Flash specifics handled here:
  - thinkingBudget: 0   disables extended thinking so tokens go to actual output
  - maxOutputTokens: 8192  enough for structured contract/validation responses
  - Retry on 429/503 with exponential backoff (5 attempts)
  - Finish reason guard: raises on truncated or empty responses
"""
from __future__ import annotations
import os
import json
import time
import urllib.request
import urllib.error
from typing import List, Dict
from pathlib import Path

_env_loaded = False

def _load_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=False)
        except ImportError:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip(); v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    _env_loaded = True


CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
GEMINI_API    = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Minimum response length (chars) before we consider it complete.
# Anything shorter is almost certainly a truncated thinking bleed-through.
_MIN_RESPONSE_LENGTH = 100


def _post(url: str, payload: dict, headers: dict, timeout: int = 180) -> dict:
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code}: {e.read().decode()[:400]}")
    except urllib.error.URLError as e:
        raise LLMError(f"Network: {e.reason}")


def _claude(messages: List[Dict], system: str, temperature: float, max_tokens: int) -> str:
    _load_env()
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise LLMError("ANTHROPIC_API_KEY not set in .env")
    last_error: str = ""
    for attempt in range(1, 4):
        try:
            raw = _post(ANTHROPIC_API, {
                "model": CLAUDE_MODEL, "max_tokens": max_tokens,
                "temperature": temperature, "system": system, "messages": messages,
            }, {"Content-Type": "application/json", "x-api-key": key,
                "anthropic-version": "2023-06-01"}, timeout=600)
            try:
                return raw["content"][0]["text"]
            except (KeyError, IndexError) as e:
                raise LLMError(f"Unexpected Claude response: {e}")
        except (LLMError, TimeoutError, OSError) as e:
            err_str = str(e)
            if attempt < 3 and any(m in err_str for m in ("503", "502", "529", "timeout", "reset")):
                wait = 15 * attempt
                print(f"  [claude] {err_str} — retrying in {wait}s (attempt {attempt}/3)")
                time.sleep(wait)
                last_error = err_str
                continue
            raise
    raise LLMError(f"Claude failed after 3 attempts. Last error: {last_error}")


def _gemini(messages: List[Dict], system: str, temperature: float, max_tokens: int) -> str:
    """
    Call Gemini with:
      - thinkingBudget: 0  (prevents 2.5 Flash from consuming tokens on reasoning)
      - maxOutputTokens: 8192
      - 5-attempt retry on 429/503 with 15s × attempt backoff
      - finish reason guard: raises if response is truncated or suspiciously short
    """
    _load_env()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise LLMError("GEMINI_API_KEY not set in .env")

    contents = [
        {"role": "user" if m["role"] == "user" else "model",
         "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {
            "temperature":     temperature,
            "maxOutputTokens": max(max_tokens, 8192),  # never below 8192
            "thinkingConfig":  {"thinkingBudget": 0},  # disable extended thinking
        },
    }
    url = f"{GEMINI_API}?key={key}"

    last_error: str = ""
    for attempt in range(1, 6):
        try:
            raw = _post(url, payload, {"Content-Type": "application/json"})
        except LLMError as e:
            err_str = str(e)
            # Retry on 429 (rate limit) or 503 (high demand)
            if attempt < 5 and any(code in err_str for code in ("429", "503")):
                wait = 15 * attempt
                print(f"  [gemini] {err_str} — retrying in {wait}s (attempt {attempt}/5)")
                time.sleep(wait)
                last_error = err_str
                continue
            raise
        else:
            break
    else:
        raise LLMError(f"Gemini failed after 5 attempts. Last error: {last_error}")

    # Extract candidate
    try:
        candidate     = raw["candidates"][0]
        finish_reason = candidate.get("finishReason", "UNKNOWN")
        text          = candidate["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"Unexpected Gemini response shape: {e}\nRaw: {json.dumps(raw)[:400]}")

    # Guard: reject truncated or empty responses
    # STOP = normal completion, MAX_TOKENS = hit limit but still usable
    if finish_reason not in ("STOP", "MAX_TOKENS"):
        raise LLMError(
            f"Gemini response incomplete (finishReason={finish_reason}, "
            f"length={len(text)} chars). Response: {text[:200]}"
        )
    if len(text) < _MIN_RESPONSE_LENGTH:
        raise LLMError(
            f"Gemini response suspiciously short ({len(text)} chars) — "
            f"likely truncated thinking bleed-through. Response: {text!r}"
        )

    return text.strip()


PROVIDERS = {"claude": _claude, "gemini": _gemini}


def call(provider: str, messages: List[Dict], system: str,
         temperature: float = 0.3, max_tokens: int = 8192) -> str:
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown provider: {provider}. Valid: {list(PROVIDERS)}")
    return PROVIDERS[provider](messages, system, temperature, max_tokens)


def user_msg(content: str) -> Dict:
    return {"role": "user", "content": content}

def assistant_msg(content: str) -> Dict:
    return {"role": "assistant", "content": content}


class LLMError(Exception):
    pass
