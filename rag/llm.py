import json
import os
from typing import Iterator

import httpx


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_GEMMA_MODEL = "gemma3:12b"


def provider() -> str:
    return os.environ.get("LLM_PROVIDER", "ollama").strip().lower()


def model_name() -> str:
    if provider() == "ollama":
        return os.environ.get("OLLAMA_MODEL") or os.environ.get("GEMMA_MODEL", DEFAULT_GEMMA_MODEL)
    return os.environ.get("GEMMA_MODEL", "gemini-2.5-flash")


def ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL).rstrip("/")


def _history_to_messages(
    user_message: str,
    history: list[dict] | None = None,
    system: str | None = None,
) -> list[dict]:
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    for msg in history or []:
        text = str(msg.get("content", "")).strip()
        if not text:
            continue
        role = "assistant" if msg.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": user_message})
    return messages


def _ollama_payload(
    user_message: str,
    history: list[dict] | None = None,
    system: str | None = None,
    stream: bool = False,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict:
    return {
        "model": model_name(),
        "messages": _history_to_messages(user_message, history, system),
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }


def _prompt_with_history(user_message: str, history: list[dict] | None = None, system: str | None = None) -> str:
    parts: list[str] = []
    if system:
        parts.append(f"Systeme:\n{system}")
    for msg in history or []:
        text = str(msg.get("content", "")).strip()
        if not text:
            continue
        label = "Assistant" if msg.get("role") == "assistant" else "Utilisateur"
        parts.append(f"{label}:\n{text}")
    parts.append(f"Utilisateur:\n{user_message}\n\nAssistant:")
    return "\n\n".join(parts)


def _ollama_generate_payload(
    user_message: str,
    history: list[dict] | None = None,
    system: str | None = None,
    stream: bool = False,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict:
    return {
        "model": model_name(),
        "prompt": _prompt_with_history(user_message, history, system),
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }


def ollama_available(timeout: float = 1.5) -> bool:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{ollama_base_url()}/api/tags")
        return response.status_code == 200
    except Exception:
        return False


def call_gemma(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    if provider() == "google":
        return _call_google(prompt, system, temperature, max_tokens)
    return _call_ollama(prompt, system, temperature, max_tokens)


def stream_gemma(
    user_message: str,
    history: list[dict] | None = None,
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> Iterator[str]:
    if provider() == "google":
        yield from _stream_google(user_message, history, system, temperature, max_tokens)
        return
    yield from _stream_ollama(user_message, history, system, temperature, max_tokens)


def _call_ollama(prompt: str, system: str | None, temperature: float, max_tokens: int) -> str:
    chat_url = f"{ollama_base_url()}/api/chat"
    chat_payload = _ollama_payload(
        prompt,
        history=None,
        system=system,
        stream=False,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        with httpx.Client(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
            response = client.post(chat_url, json=chat_payload)
            if response.status_code == 404:
                response = client.post(
                    f"{ollama_base_url()}/api/generate",
                    json=_ollama_generate_payload(
                        prompt,
                        history=None,
                        system=system,
                        stream=False,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                )
            response.raise_for_status()
        data = response.json()
        if "message" in data:
            return str(data.get("message", {}).get("content", "")).strip()
        return str(data.get("response", "")).strip()
    except Exception as exc:
        raise RuntimeError(
            f"Ollama/Gemma local indisponible ({model_name()} sur {ollama_base_url()}). "
            f"Lancez Ollama puis installez le modele avec : ollama pull {model_name()}"
        ) from exc


def _stream_ollama(
    user_message: str,
    history: list[dict] | None,
    system: str | None,
    temperature: float,
    max_tokens: int,
) -> Iterator[str]:
    url = f"{ollama_base_url()}/api/chat"
    payload = _ollama_payload(
        user_message,
        history=history,
        system=system,
        stream=True,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        with httpx.Client(timeout=httpx.Timeout(None, connect=5.0)) as client:
            with client.stream("POST", url, json=payload) as response:
                if response.status_code == 404:
                    yield from _stream_ollama_generate(user_message, history, system, temperature, max_tokens)
                    return
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("done"):
                        break
                    text = data.get("message", {}).get("content", "")
                    if text:
                        yield text
    except Exception:
        yield (
            f"\n\nAttention : Ollama/Gemma local est indisponible "
            f"({model_name()} sur {ollama_base_url()}). "
            f"Lancez Ollama puis executez : ollama pull {model_name()}"
        )


def _stream_ollama_generate(
    user_message: str,
    history: list[dict] | None,
    system: str | None,
    temperature: float,
    max_tokens: int,
) -> Iterator[str]:
    url = f"{ollama_base_url()}/api/generate"
    payload = _ollama_generate_payload(
        user_message,
        history=history,
        system=system,
        stream=True,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    with httpx.Client(timeout=httpx.Timeout(None, connect=5.0)) as client:
        with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if data.get("done"):
                    break
                text = data.get("response", "")
                if text:
                    yield text


def _call_google(prompt: str, system: str | None, temperature: float, max_tokens: int) -> str:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY manquante")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name(),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.text.strip()


def _stream_google(
    user_message: str,
    history: list[dict] | None,
    system: str | None,
    temperature: float,
    max_tokens: int,
) -> Iterator[str]:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        yield "\n\nAttention : GOOGLE_API_KEY manquante."
        return

    contents = []
    for msg in history or []:
        text = msg.get("content", "").strip()
        if text:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    try:
        client = genai.Client(api_key=api_key)
        for chunk in client.models.generate_content_stream(
            model=model_name(),
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        ):
            if chunk.text:
                yield chunk.text
    except Exception as exc:
        yield f"\n\nAttention : erreur Gemini : {str(exc)[:200]}"
