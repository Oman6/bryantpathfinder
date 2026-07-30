"""LLM abstraction layer — single text-completion entry point.

Routes calls to either Anthropic Claude or Groq (Llama 3.3 70B) based on the
LLM_PROVIDER environment variable. Lets Pathfinder run on a free LLM during
development without changing call sites.

Provider selection:
  LLM_PROVIDER=anthropic   (default)  — Claude Sonnet, prompt caching enabled
  LLM_PROVIDER=groq                   — Llama 3.3 70B via Groq's free tier

Vision (parse_audit_vision) is NOT routed through here — it stays on Claude
because open-source vision models can't reliably parse a Degree Works layout.

Env vars consumed:
  ANTHROPIC_API_KEY     — required for Anthropic provider
  GROQ_API_KEY          — required for Groq provider
  LLM_PROVIDER          — anthropic | groq (default: anthropic)
  GROQ_MODEL            — default: llama-3.3-70b-versatile
  ANTHROPIC_MODEL       — default: claude-sonnet-5
"""

from __future__ import annotations

import logging
import os

import anthropic
from groq import Groq

logger = logging.getLogger(__name__)


def _provider() -> str:
    return os.environ.get("LLM_PROVIDER", "anthropic").lower()


def _groq_model() -> str:
    return os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def _anthropic_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")


_anthropic_client: anthropic.Anthropic | None = None
_groq_client: Groq | None = None


def _anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _anthropic_client = anthropic.Anthropic(api_key=key)
    return _anthropic_client


def _groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Sign up at https://console.groq.com (free) and add the key to .env."
            )
        _groq_client = Groq(api_key=key)
    return _groq_client


def text_chat(
    *,
    system: str,
    user: str,
    max_tokens: int = 500,
    temperature: float = 0.0,
) -> str:
    """Provider-agnostic text completion. Returns the assistant's text content.

    On the Anthropic path, the system prompt is wrapped with cache_control for
    prompt-caching savings (only takes effect when the system block exceeds
    Sonnet's 1024-token minimum — true for VISION_AUDIT_PROMPT, not for the
    smaller explain/rank system prompts).
    """
    provider = _provider()

    if provider == "groq":
        client = _groq()
        try:
            resp = client.chat.completions.create(
                model=_groq_model(),
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error("llm.groq_error: %s", e)
            raise

    # Default: Anthropic
    client = _anthropic()
    try:
        msg = client.messages.create(
            model=_anthropic_model(),
            max_tokens=max_tokens,
            temperature=temperature,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text
    except anthropic.APIError as e:
        logger.error("llm.anthropic_error: %s", e)
        raise


def provider_label() -> str:
    """Human-readable label of the active provider — for logs and the health endpoint."""
    p = _provider()
    if p == "groq":
        return f"groq:{_groq_model()}"
    return f"anthropic:{_anthropic_model()}"
