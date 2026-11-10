"""
Abstração de provedor de LLM.

Hoje usa o tier gratuito do Google Gemini (LLM_PROVIDER=gemini, padrão), com o
Groq (também gratuito) como backup automático se a Gemini falhar — o tier
gratuito da Gemini tem ficado instável (503/timeout), então isso evita esperar
o cron do dia seguinte sempre que a Gemini engasgar.
Quando o projeto já tiver caixa, troque para LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY
para usar Claude, sem alterar generate_post.py ou discover_topics.py.
"""
import os
import requests

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
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
    try:
        resp = requests.post(
            f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=150,
        )
    except requests.exceptions.RequestException as exc:
        raise LLMError(f"Falha de rede ao chamar a Gemini API: {exc}") from exc
    if resp.status_code != 200:
        raise LLMError(f"Gemini API falhou ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Resposta inesperada da Gemini API: {data}") from exc


def _generate_groq(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise LLMError("GROQ_API_KEY não configurada.")
    model = os.environ.get("GROQ_MODEL") or "openai/gpt-oss-120b"
    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=150,
        )
    except requests.exceptions.RequestException as exc:
        raise LLMError(f"Falha de rede ao chamar a Groq API: {exc}") from exc
    if resp.status_code != 200:
        raise LLMError(f"Groq API falhou ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Resposta inesperada da Groq API: {data}") from exc


def _generate_anthropic(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY não configurada.")
    try:
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
            timeout=150,
        )
    except requests.exceptions.RequestException as exc:
        raise LLMError(f"Falha de rede ao chamar a Anthropic API: {exc}") from exc
    if resp.status_code != 200:
        raise LLMError(f"Anthropic API falhou ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    try:
        return "".join(block["text"] for block in data["content"] if block["type"] == "text")
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Resposta inesperada da Anthropic API: {data}") from exc


_PROVIDERS = {
    "gemini": _generate_gemini,
    "groq": _generate_groq,
    "anthropic": _generate_anthropic,
}


def generate(prompt: str) -> str:
    # .get(..., default) só vale quando a env var não existe; no GitHub Actions uma
    # secret não configurada chega como string vazia, não ausente — por isso o "or".
    provider = (os.environ.get("LLM_PROVIDER") or "gemini").lower()
    fn = _PROVIDERS.get(provider)
    if fn is None:
        raise LLMError(f"LLM_PROVIDER desconhecido: {provider}")

    try:
        return fn(prompt)
    except LLMError as primary_error:
        # Só tenta o backup se for diferente do provedor principal e a chave
        # dele existir — senão é só barulho repetindo o mesmo erro.
        if provider == "gemini" and os.environ.get("GROQ_API_KEY"):
            try:
                return _generate_groq(prompt)
            except LLMError as backup_error:
                raise LLMError(
                    f"Gemini falhou ({primary_error}) e o backup Groq também "
                    f"falhou ({backup_error})"
                ) from backup_error
        raise
