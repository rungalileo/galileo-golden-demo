"""
LLM and embedding helpers for local (Ollama) and hosted (OpenAI) inference.
"""
import json
import os
import urllib.error
import urllib.request
from contextvars import ContextVar, Token
from typing import List, Literal, Optional

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings

LLMProvider = Literal["local", "hosted"]

DEFAULT_LOCAL_CHAT_MODEL = "gemma4"
DEFAULT_HOSTED_CHAT_MODEL = "gpt-4o"
DEFAULT_LOCAL_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_HOSTED_EMBEDDING_MODEL = "text-embedding-3-large"

_llm_provider_ctx: ContextVar[LLMProvider] = ContextVar("llm_provider", default="local")


def set_llm_provider(provider: LLMProvider) -> Token:
    """Set the active LLM provider for the current async/task context."""
    return _llm_provider_ctx.set(provider)


def reset_llm_provider(token: Token) -> None:
    """Restore the previous LLM provider context."""
    _llm_provider_ctx.reset(token)


def get_llm_provider() -> LLMProvider:
    """Return the active LLM provider ('local' for Ollama, 'hosted' for OpenAI)."""
    return _llm_provider_ctx.get()


def get_ollama_base_url() -> str:
    """Return the Ollama server URL (default: http://localhost:11434)."""
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def get_default_chat_model(*, provider: Optional[LLMProvider] = None) -> str:
    """Return the default chat model for the given or active provider."""
    resolved = provider or get_llm_provider()
    if resolved == "hosted":
        return os.environ.get("OPENAI_DEFAULT_CHAT_MODEL", DEFAULT_HOSTED_CHAT_MODEL)
    return os.environ.get("OLLAMA_DEFAULT_CHAT_MODEL", DEFAULT_LOCAL_CHAT_MODEL)


def get_default_embedding_model(*, provider: Optional[LLMProvider] = None) -> str:
    """Return the default embedding model for the given or active provider."""
    resolved = provider or get_llm_provider()
    if resolved == "hosted":
        return os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_HOSTED_EMBEDDING_MODEL)
    return os.environ.get("OLLAMA_EMBEDDING_MODEL", DEFAULT_LOCAL_EMBEDDING_MODEL)


def get_domain_embedding_model(
    vectorstore_config: dict,
    *,
    provider: Optional[LLMProvider] = None,
) -> str:
    """Return the Ollama embedding model used for pgvector retrieval."""
    return (
        vectorstore_config.get("embedding_model")
        or get_default_embedding_model(provider="local")
    )


def ensure_openai_api_key() -> str:
    """Return OPENAI_API_KEY or raise with setup instructions."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add openai_api_key to .streamlit/secrets.toml "
            "to use the Hosted (OpenAI) provider."
        )
    return api_key


def list_ollama_models() -> List[str]:
    """Return model base names available in the local Ollama instance."""
    url = f"{get_ollama_base_url().rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.URLError as exc:
        raise ConnectionError(
            f"Cannot reach Ollama at {get_ollama_base_url()}. "
            "Make sure Ollama is running."
        ) from exc

    return [
        model.get("name", "").split(":")[0]
        for model in payload.get("models", [])
        if model.get("name")
    ]


def ensure_ollama_model_available(model: str, *, model_kind: str = "model") -> None:
    """Raise a clear error if the requested Ollama model is not installed locally."""
    installed_models = set(list_ollama_models())
    if model not in installed_models:
        raise ValueError(
            f'Ollama {model_kind} "{model}" is not installed. '
            f"Pull it with:\n\n  ollama pull {model}\n\n"
            f"Installed models: {', '.join(sorted(installed_models)) or '(none)'}"
        )


def get_domain_chat_model(domain_config: dict, *, override: Optional[str] = None) -> str:
    """Resolve the chat model for a domain using the active provider."""
    if override:
        return override
    provider = get_llm_provider()
    model_cfg = domain_config.get("model", {})
    if provider == "hosted":
        return (
            model_cfg.get("hosted_default_model")
            or get_default_chat_model(provider="hosted")
        )
    return model_cfg.get("default_model") or get_default_chat_model(provider="local")


def get_chat_model(
    model: str,
    *,
    temperature: float = 0.1,
    name: Optional[str] = None,
    num_ctx: int = 8192,
    provider: Optional[LLMProvider] = None,
) -> BaseChatModel:
    """Create a chat model for the active or specified provider."""
    resolved_provider = provider or get_llm_provider()
    if resolved_provider == "hosted":
        from langchain_openai import ChatOpenAI

        ensure_openai_api_key()
        kwargs = {
            "model": model,
            "temperature": temperature,
        }
        if name:
            kwargs["name"] = name
        return ChatOpenAI(**kwargs)

    ensure_ollama_model_available(model, model_kind="chat model")
    kwargs = {
        "model": model,
        "temperature": temperature,
        "base_url": get_ollama_base_url(),
        "num_ctx": num_ctx,
    }
    if name:
        kwargs["name"] = name
    return ChatOllama(**kwargs)


def get_embeddings(
    model: Optional[str] = None,
    *,
    provider: Optional[LLMProvider] = None,
) -> Embeddings:
    """Create embeddings for the active or specified provider."""
    resolved_provider = provider or get_llm_provider()
    embedding_model = model or get_default_embedding_model(provider=resolved_provider)

    if resolved_provider == "hosted":
        from langchain_openai import OpenAIEmbeddings

        ensure_openai_api_key()
        return OpenAIEmbeddings(model=embedding_model)

    ensure_ollama_model_available(embedding_model, model_kind="embedding model")
    return OllamaEmbeddings(model=embedding_model, base_url=get_ollama_base_url())
