"""
Abstração de provedor de LLM.

Hoje usa o tier gratuito do Google Gemini (LLM_PROVIDER=gemini, padrão).
Quando o projeto já tiver caixa, troque para LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY
para usar Claude, sem alterar generate_post.py ou discover_topics.py.
"""
import os
import requests

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class LLMError(RuntimeError):
    pass


def _generate_gemini(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise LLMError("GEMINI_API_KEY não configurada (veja SETUP.md).")
    # Configurável porque a Google aposenta nomes de modelo de tempos em tempos
    # (ex: gemini-2.0-flash foi descontinuado em favor do gemini-3.8-flash).
    model = os.environ.get("GEMINI_MODEL") or "gemini-3.8-flash"
    resp = requests.post(
        f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    if resp.status_code != 200:
        raise LLMError(f"Gemini API falhou ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Resposta inesperada da Gemini API: {data}") from exc


def _generate_anthropic(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY não configurada.")
    resp = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise LLMError(f"Anthropic API falhou ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    try:
        return "".join(block["text"] for block in data["content"] if block["type"] == "text")
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Resposta inesperada da Anthropic API: {data}") from exc


def generate(prompt: str) -> str:
    # .get(..., default) só vale quando a env var não existe; no GitHub Actions uma
    # secret não configurada chega como string vazia, não ausente — por isso o "or".
    provider = (os.environ.get("LLM_PROVIDER") or "gemini").lower()
    if provider == "gemini":
        return _generate_gemini(prompt)
    if provider == "anthropic":
        return _generate_anthropic(prompt)
    raise LLMError(f"LLM_PROVIDER desconhecido: {provider}")
