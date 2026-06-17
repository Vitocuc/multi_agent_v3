"""
llm/retry.py — structured output with automatic retry.

Pattern:
  1. Call model → ask for JSON matching a schema
  2. Parse + validate with Pydantic
  3. On failure: send targeted correction prompt with the specific error
  4. Retry up to max_attempts
  5. Raise StructuredOutputError if all attempts fail

This is what removes prompt-dependency: schema enforced by code, not hope.
"""

from __future__ import annotations
import json
import re
from typing import Type, TypeVar, List, Dict, Optional
from pydantic import BaseModel, ValidationError
from llm.router import call, LLMError

T = TypeVar("T", bound=BaseModel)


def extract_json(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    for pat in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
        m = re.search(pat, text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No valid JSON in output (first 300 chars): {text[:300]}")


def call_structured(
    provider: str,
    messages: List[Dict],
    system: str,
    schema: Type[T],
    temperature: float = 0.3,
    max_attempts: int = 3,
    label: str = "",
) -> T:
    label = label or schema.__name__
    history = list(messages)
    last_raw: Optional[str] = None
    last_err: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            raw = call(provider, history, system, temperature)
            last_raw = raw
            return schema.model_validate(extract_json(raw))
        except (ValueError, LLMError) as e:
            last_err = str(e)
        except ValidationError as e:
            last_err = "\n".join(
                f"  {' → '.join(str(x) for x in err['loc'])}: {err['msg']}"
                for err in e.errors()
            )

        correction = (
            f"Your response did not match the required schema (attempt {attempt}/{max_attempts}).\n\n"
            f"Errors:\n{last_err}\n\n"
            f"Your previous response (first 400 chars):\n{(last_raw or '')[:400]}\n\n"
            f"Schema: {schema.__name__}\n"
            f"Fields: {list(schema.model_fields.keys())}\n\n"
            "Return ONLY valid JSON. No prose. No markdown fences."
        )
        history = list(messages) + [
            {"role": "assistant", "content": last_raw or ""},
            {"role": "user", "content": correction},
        ]

    raise StructuredOutputError(label, max_attempts, last_err or "", last_raw or "")


class StructuredOutputError(Exception):
    def __init__(self, schema: str, attempts: int, error: str, raw: str):
        self.schema = schema
        self.attempts = attempts
        self.error = error
        self.raw = raw
        super().__init__(f"Failed {schema} after {attempts} attempts: {error}")
